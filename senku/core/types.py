"""
Senku Core Types
Structured data models for the entire agent system.
Uses dataclasses for clear, type-safe data flow between components.

v3.1 — Added ExecutionPlan, ActionNode, FeedbackScore, RetryPolicy
for reasoning engine, decision layer, and self-healing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, List
from datetime import datetime
import uuid


class ActionStatus(Enum):
    """Status of an action execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class IntentType(Enum):
    """Classification of user intent."""
    ACTION = "action"        # User wants to perform an action
    CHAT = "chat"            # User wants to have a conversation
    QUERY = "query"          # User is asking a question
    COMPOUND = "compound"    # Multiple actions in one request
    UNCLEAR = "unclear"      # Intent is ambiguous
    GOAL = "goal"            # Long-running objective
    SCHEDULE = "schedule"    # Scheduled / deferred action


class Severity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorClass(Enum):
    """Classification of error recoverability — drives retry logic."""
    RECOVERABLE = "recoverable"         # Retry with same strategy
    RECOVERABLE_ALT = "recoverable_alt" # Retry with alternative strategy
    TRANSIENT = "transient"             # Retry after delay
    FATAL = "fatal"                     # Don't retry


@dataclass
class RetryPolicy:
    """Defines how an action should be retried on failure."""
    max_attempts: int = 2
    delay_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    fallback_action_type: str = ""  # Alternative action to try
    fallback_params: dict = field(default_factory=dict)

    def get_delay(self, attempt: int) -> float:
        """Get delay for the Nth retry attempt (exponential backoff)."""
        return self.delay_seconds * (self.backoff_multiplier ** attempt)


@dataclass
class Action:
    """
    Represents a single executable action.
    This is the fundamental unit of work in the Senku system.
    """
    action_type: str
    params: dict = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "llm"  # llm, rule, memory, pattern, retry
    id: str = ""
    # v3.1 — reasoning & retry fields
    depends_on: str = ""                                      # ID of action this depends on
    fallback_for: str = ""                                    # ID of action this is a fallback for
    retry_policy: Optional[RetryPolicy] = None
    priority: int = 0                                         # Higher = execute first
    condition: str = ""                                       # e.g. "previous_success", "previous_failed"

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.action_type}_{uuid.uuid4().hex[:8]}"

    def get_param(self, key: str, default: Any = None) -> Any:
        """Safely get a parameter value."""
        return self.params.get(key, default)

    def to_dict(self) -> dict:
        return {
            "action": self.action_type,
            "params": self.params,
            "confidence": self.confidence,
            "source": self.source,
            "id": self.id,
            "depends_on": self.depends_on,
            "priority": self.priority,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        """Create an Action from a raw dict (e.g., LLM output)."""
        try:
            data = dict(data)  # avoid mutating the original

            # Safely extract action type — avoid double-pop bug
            if "action" in data:
                action_type = data.pop("action")
            elif "action_type" in data:
                action_type = data.pop("action_type")
            else:
                action_type = "unknown"

            # Ensure action_type is a string
            if not isinstance(action_type, str):
                action_type = str(action_type) if action_type else "unknown"

            confidence = float(data.pop("confidence", 1.0))
            source = str(data.pop("source", "llm"))
            depends_on = str(data.pop("depends_on", ""))
            priority = int(data.pop("priority", 0))
            condition = str(data.pop("condition", ""))
            data.pop("id", None)
            data.pop("params", None)  # Don't nest params inside params
            params = {k: v for k, v in data.items()}
            return cls(
                action_type=action_type,
                params=params,
                confidence=confidence,
                source=source,
                depends_on=depends_on,
                priority=priority,
                condition=condition,
            )
        except Exception:
            # If anything goes wrong, return a safe default
            return cls(action_type="unknown", params=dict(data) if data else {})


@dataclass
class ActionResult:
    """
    The outcome of executing an action.
    Tracks success/failure, messages, and metadata for learning.
    """
    action: Action
    status: ActionStatus
    message: str = ""
    error: Optional[str] = None
    error_class: ErrorClass = ErrorClass.RECOVERABLE
    duration_ms: float = 0.0
    timestamp: str = ""
    metadata: dict = field(default_factory=dict)
    attempt: int = 1  # Which attempt this result is for

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def success(self) -> bool:
        return self.status == ActionStatus.SUCCESS

    @property
    def retryable(self) -> bool:
        return self.error_class in (
            ErrorClass.RECOVERABLE, ErrorClass.RECOVERABLE_ALT, ErrorClass.TRANSIENT
        )

    def to_dict(self) -> dict:
        return {
            "action": self.action.to_dict(),
            "status": self.status.value,
            "message": self.message,
            "error": self.error,
            "error_class": self.error_class.value,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "attempt": self.attempt,
        }


@dataclass
class FeedbackScore:
    """
    Post-action evaluation score.
    Quantifies how well an action or plan performed.
    """
    success_score: float = 0.0     # 0.0 to 1.0
    speed_score: float = 0.0       # 0.0 to 1.0 (relative to historical average)
    reliability_score: float = 0.0 # 0.0 to 1.0 (success rate history)
    overall: float = 0.0           # weighted combination
    suggestions: list = field(default_factory=list)  # improvement hints

    def compute_overall(self, weights: dict = None):
        w = weights or {"success": 0.5, "speed": 0.2, "reliability": 0.3}
        self.overall = (
            self.success_score * w["success"]
            + self.speed_score * w["speed"]
            + self.reliability_score * w["reliability"]
        )

    def to_dict(self) -> dict:
        return {
            "success_score": round(self.success_score, 3),
            "speed_score": round(self.speed_score, 3),
            "reliability_score": round(self.reliability_score, 3),
            "overall": round(self.overall, 3),
            "suggestions": self.suggestions,
        }


@dataclass
class ExecutionPlan:
    """
    A multi-step execution plan with dependency graph.
    The output of the reasoning engine.
    """
    plan_id: str = ""
    goal: str = ""
    steps: List[Action] = field(default_factory=list)
    is_sequential: bool = True
    created_at: str = ""
    feedback: Optional[FeedbackScore] = None

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def get_next_executable(self, completed_ids: set, failed_ids: set) -> Optional[Action]:
        """
        Get the next action that is ready to execute.
        Respects dependencies and conditions.
        """
        for step in self.steps:
            if step.id in completed_ids or step.id in failed_ids:
                continue

            # Check dependency
            if step.depends_on and step.depends_on not in completed_ids:
                # Dependency not met — check if it failed
                if step.depends_on in failed_ids:
                    # Check condition
                    if step.condition == "previous_failed":
                        return step  # This is a fallback action
                    continue  # Skip — dependency failed
                continue  # Dependency not done yet

            # Check condition
            if step.condition == "previous_success":
                if step.depends_on and step.depends_on not in completed_ids:
                    continue
            elif step.condition == "previous_failed":
                if step.depends_on and step.depends_on not in failed_ids:
                    continue

            return step

        return None  # All done or blocked

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "is_sequential": self.is_sequential,
            "created_at": self.created_at,
        }


@dataclass
class Intent:
    """
    Parsed user intent with extracted actions.
    The output of the brain's analysis phase.
    """
    intent_type: IntentType
    raw_input: str
    actions: list = field(default_factory=list)  # List[Action]
    plan: Optional[ExecutionPlan] = None
    chat_response: str = ""
    confidence: float = 1.0
    clarification_needed: str = ""  # If non-empty, ask user this question
    reasoning: str = ""             # Explanation of decision

    @property
    def has_actions(self) -> bool:
        return len(self.actions) > 0

    @property
    def is_chat(self) -> bool:
        return self.intent_type in (IntentType.CHAT, IntentType.QUERY)

    @property
    def needs_clarification(self) -> bool:
        return bool(self.clarification_needed)

    @property
    def is_goal(self) -> bool:
        return self.intent_type == IntentType.GOAL

    @property
    def is_scheduled(self) -> bool:
        return self.intent_type == IntentType.SCHEDULE


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""
    actions_taken: list = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "actions_taken": self.actions_taken,
        }


@dataclass
class SessionContext:
    """
    Tracks the current session state.
    Enables context-aware responses and action chaining.
    """
    session_id: str = ""
    last_app: str = ""
    last_action: str = ""
    last_query: str = ""
    active_apps: list = field(default_factory=list)
    conversation_history: list = field(default_factory=list)
    session_start: str = ""
    action_count: int = 0
    last_result_status: str = ""  # "success" / "failed"
    pending_goals: list = field(default_factory=list)

    def __post_init__(self):
        if not self.session_start:
            self.session_start = datetime.now().isoformat()
        if not self.session_id:
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def update_after_action(self, action: Action, result: ActionResult):
        """Update context after an action is executed."""
        self.last_action = action.action_type
        self.action_count += 1
        self.last_result_status = result.status.value

        if action.action_type == "open_app":
            app = action.get_param("app", "")
            self.last_app = app
            if app and app not in self.active_apps:
                self.active_apps.append(app)
        elif action.action_type == "close_app":
            app = action.get_param("app", "")
            if app in self.active_apps:
                self.active_apps.remove(app)

        if action.action_type in ("search_web", "play_youtube"):
            self.last_query = action.get_param("query", "")

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "last_app": self.last_app,
            "last_action": self.last_action,
            "last_query": self.last_query,
            "active_apps": self.active_apps,
            "session_start": self.session_start,
            "action_count": self.action_count,
            "last_result_status": self.last_result_status,
        }
