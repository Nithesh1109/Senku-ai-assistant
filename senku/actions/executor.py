"""
Senku Action Executor
Central execution engine with self-healing, retry intelligence,
plan-aware execution, and feedback integration.

v3.1 — Upgraded with:
- Plan-based execution (dependency-aware step ordering)
- Retry with exponential backoff and alternative strategies
- Error classification (recoverable vs fatal)
- Post-action feedback scoring
- Pattern learning integration
"""

import time
from typing import List, Optional

from senku.core.types import (
    Action, ActionResult, ActionStatus, ErrorClass,
    ExecutionPlan, RetryPolicy,
)
from senku.core.events import event_bus, Events
from senku.core.exceptions import ActionNotFoundError, ActionExecutionError
from senku.actions.registry import registry
from senku.config import DEBUG_MODE, DEFAULT_MAX_RETRIES

# ─── Import all handlers to register them ────────────────────────
import senku.actions.handlers.app_handler
import senku.actions.handlers.web_handler
import senku.actions.handlers.file_handler
import senku.actions.handlers.system_handler


class Executor:
    """
    The action execution engine.
    
    v3.1 Responsibilities:
    1. Execute plans (dependency graph) or flat action lists
    2. Retry failed actions with exponential backoff
    3. Try fallback strategies when primary fails
    4. Classify errors for intelligent recovery
    5. Track results and emit events for learning
    6. Provide execution summaries
    """

    def __init__(self):
        self.results: List[ActionResult] = []

    def execute_plan(self, plan: ExecutionPlan) -> List[ActionResult]:
        """
        Execute an intelligent plan with dependency awareness.
        
        Walks through the plan's dependency graph:
        - Executes independent steps first
        - Waits for dependencies before continuing
        - Triggers fallback branches on failure
        - Respects conditions (previous_success, previous_failed)
        """
        self.results = []
        completed_ids = set()
        failed_ids = set()

        if DEBUG_MODE:
            print(f"[Executor] Executing plan: {plan.total_steps} steps")

        while True:
            next_action = plan.get_next_executable(completed_ids, failed_ids)
            if next_action is None:
                break  # All done or blocked

            result = self._execute_with_retry(next_action)
            self.results.append(result)

            if result.success:
                completed_ids.add(next_action.id)
                event_bus.emit(Events.PLAN_STEP_COMPLETED,
                               action=next_action, result=result)
            else:
                failed_ids.add(next_action.id)
                event_bus.emit(Events.PLAN_STEP_FAILED,
                               action=next_action, result=result)

        # Emit plan-level events
        if failed_ids and not completed_ids:
            event_bus.emit(Events.PLAN_FAILED, plan=plan, results=self.results)
        else:
            event_bus.emit(Events.PLAN_COMPLETED, plan=plan, results=self.results)

        return self.results

    def execute_all(self, actions: List[Action]) -> List[ActionResult]:
        """
        Execute a flat list of actions with retry intelligence.
        Backwards-compatible with v3.0.
        """
        self.results = []

        for action in actions:
            result = self._execute_with_retry(action)
            self.results.append(result)

            # Emit event for learning systems
            if result.success:
                event_bus.emit(Events.ACTION_COMPLETED,
                               action=action, result=result)
            else:
                event_bus.emit(Events.ACTION_FAILED,
                               action=action, result=result)

        return self.results

    def _execute_with_retry(self, action: Action) -> ActionResult:
        """
        Execute an action with intelligent retry logic.
        
        Retry behavior:
        1. Try primary execution
        2. On failure, classify the error
        3. If recoverable: retry with backoff
        4. If recoverable_alt: try fallback strategy
        5. If transient: wait and retry
        6. If fatal: stop immediately
        """
        policy = action.retry_policy or RetryPolicy(max_attempts=1)
        last_result = None

        for attempt in range(1, policy.max_attempts + 1):
            if attempt > 1:
                delay = policy.get_delay(attempt - 2)
                if DEBUG_MODE:
                    print(f"[Executor] Retry {attempt}/{policy.max_attempts} "
                          f"for {action.action_type} (delay: {delay:.1f}s)")
                time.sleep(delay)
                event_bus.emit(Events.ACTION_RETRYING,
                               action=action, attempt=attempt)

            result = self.execute_one(action)
            result.attempt = attempt
            last_result = result

            if result.success:
                return result

            # Classify the error
            result.error_class = self._classify_error(
                action.action_type, result.error or ""
            )

            if result.error_class == ErrorClass.FATAL:
                if DEBUG_MODE:
                    print(f"[Executor] Fatal error for {action.action_type}: "
                          f"{result.error}")
                return result

            if result.error_class == ErrorClass.RECOVERABLE_ALT:
                # Don't retry same way — the fallback branch in the plan
                # will handle the alternative strategy
                break

        # All retries exhausted
        if last_result and not last_result.success:
            event_bus.emit(Events.ACTION_RETRY_EXHAUSTED,
                           action=action, result=last_result)
            if DEBUG_MODE:
                print(f"[Executor] Retries exhausted for {action.action_type}")

        return last_result

    def execute_one(self, action: Action) -> ActionResult:
        """Execute a single action with error handling (no retry)."""
        if DEBUG_MODE:
            print(f"[Executor] Executing: {action.action_type} "
                  f"params={action.params}")

        event_bus.emit(Events.ACTION_STARTED, action=action)
        start_time = time.time()

        try:
            if not registry.has_handler(action.action_type):
                return ActionResult(
                    action=action,
                    status=ActionStatus.FAILED,
                    message=f"Unknown action: {action.action_type}",
                    error=f"No handler registered for '{action.action_type}'",
                    error_class=ErrorClass.FATAL,
                    duration_ms=(time.time() - start_time) * 1000,
                )

            result = registry.execute(action)
            return result

        except ActionNotFoundError as e:
            return ActionResult(
                action=action,
                status=ActionStatus.FAILED,
                message=str(e),
                error="Handler not found",
                error_class=ErrorClass.FATAL,
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ActionResult(
                action=action,
                status=ActionStatus.FAILED,
                message=f"Unexpected error executing {action.action_type}",
                error=str(e),
                error_class=self._classify_error(action.action_type, str(e)),
                duration_ms=(time.time() - start_time) * 1000,
            )

    def _classify_error(self, action_type: str, error: str) -> ErrorClass:
        """
        Classify an error to determine retry strategy.
        
        This is the intelligence layer for self-healing:
        - "not found" → try alternative strategy
        - "permission denied" → fatal (won't work on retry)
        - "timeout" → transient (might work later)
        - "connection refused" → transient
        - Unknown → recoverable (try again)
        """
        error_lower = error.lower()

        # Fatal — won't work no matter how many times we retry
        fatal_patterns = [
            "permission denied", "access denied", "not supported",
            "no handler registered", "invalid", "corrupt",
        ]
        for pattern in fatal_patterns:
            if pattern in error_lower:
                return ErrorClass.FATAL

        # Recoverable with alternative — try different method
        alt_patterns = [
            "not found", "file not found", "command not found",
            "no such file", "does not exist",
        ]
        for pattern in alt_patterns:
            if pattern in error_lower:
                return ErrorClass.RECOVERABLE_ALT

        # Transient — retry after delay
        transient_patterns = [
            "timeout", "timed out", "connection refused",
            "connection error", "network", "unavailable",
            "busy", "try again",
        ]
        for pattern in transient_patterns:
            if pattern in error_lower:
                return ErrorClass.TRANSIENT

        # Default: recoverable
        return ErrorClass.RECOVERABLE

    def get_summary(self) -> dict:
        """Get a summary of the last execution batch."""
        if not self.results:
            return {"total": 0, "success": 0, "failed": 0, "retried": 0}

        return {
            "total": len(self.results),
            "success": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success),
            "retried": sum(1 for r in self.results if r.attempt > 1),
            "actions": [
                {
                    "type": r.action.action_type,
                    "status": r.status.value,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "attempt": r.attempt,
                    "error_class": r.error_class.value if not r.success else None,
                }
                for r in self.results
            ],
        }

    @staticmethod
    def list_available_actions() -> list:
        """List all available action types."""
        return registry.list_actions()
