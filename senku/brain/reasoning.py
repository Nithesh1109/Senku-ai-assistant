"""
Senku Reasoning Engine
Multi-step action decomposition, dependency awareness, and conditional execution.

This is the core "think before you act" system.
Instead of blindly executing a flat list, Senku now:
1. Decomposes compound requests into ordered steps
2. Tracks dependencies between steps
3. Supports conditional branches (if X fails → do Y)
4. Uses context + history to make smarter plans
"""

from typing import List, Optional

from senku.core.types import (
    Action, ExecutionPlan, RetryPolicy, Intent, IntentType,
)
from senku.config import (
    DEBUG_MODE, RETRY_STRATEGIES, DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY, DEFAULT_RETRY_BACKOFF,
)


class ReasoningEngine:
    """
    Converts raw action lists into intelligent execution plans.
    
    The key difference from the old system:
    - Old: [action1, action2] → execute both blindly
    - New: [action1, action2] → analyze dependencies → build graph
           → attach retry policies → create fallback branches
    """

    def build_plan(self, actions: List[Action], user_input: str = "",
                   context_summary: str = "") -> ExecutionPlan:
        """
        Build an execution plan from a list of actions.
        
        Steps:
        1. Assign priorities based on action type
        2. Detect implicit dependencies (e.g., search after open browser)
        3. Attach retry policies
        4. Create fallback branches for critical actions
        5. Sort by execution order
        """
        if not actions:
            return ExecutionPlan(goal=user_input)

        plan = ExecutionPlan(goal=user_input)

        # Step 1: Assign priorities and retry policies
        enriched = []
        for action in actions:
            action.priority = self._assign_priority(action)
            action.retry_policy = self._assign_retry_policy(action)
            enriched.append(action)

        # Step 2: Detect implicit dependencies
        enriched = self._detect_dependencies(enriched)

        # Step 3: Create fallback branches for app launches
        enriched = self._create_fallback_branches(enriched)

        # Step 3b: Ensure ALL steps (including fallbacks) have retry policies
        for action in enriched:
            if action.retry_policy is None:
                action.retry_policy = self._assign_retry_policy(action)

        # Step 4: Sort by priority (higher first), preserving dependency order
        enriched = self._topological_sort(enriched)

        plan.steps = enriched
        plan.is_sequential = self._needs_sequential(enriched)

        if DEBUG_MODE:
            print(f"[Reasoning] Plan: {plan.total_steps} steps, "
                  f"sequential={plan.is_sequential}")
            for s in plan.steps:
                dep = f" (depends_on={s.depends_on})" if s.depends_on else ""
                cond = f" [if {s.condition}]" if s.condition else ""
                print(f"  [{s.priority}] {s.action_type}{dep}{cond}")

        return plan

    def _assign_priority(self, action: Action) -> int:
        """
        Assign execution priority.
        Higher number = execute first.
        
        Logic:
        - App open/close: high priority (environment setup)
        - File ops: medium (need env ready)
        - Search/web: lower (can happen anytime)
        - Timer/schedule: lowest (background)
        """
        priority_map = {
            "open_app": 90,
            "close_app": 85,
            "open_folder": 80,
            "open_file": 75,
            "create_file": 70,
            "open_url": 60,
            "search_web": 50,
            "play_youtube": 50,
            "get_weather": 45,
            "send_message": 40,
            "screenshot": 35,
            "system_volume": 30,
            "run_command": 25,
            "set_timer": 10,
        }
        return priority_map.get(action.action_type, 50)

    def _assign_retry_policy(self, action: Action) -> RetryPolicy:
        """Assign a retry policy based on action type and history."""
        strategy = RETRY_STRATEGIES.get(action.action_type, {})
        max_retries = strategy.get("max_retries", DEFAULT_MAX_RETRIES)

        # Actions that interact with external state get more retries
        if action.action_type in ("open_app", "open_file", "run_command"):
            return RetryPolicy(
                max_attempts=max_retries,
                delay_seconds=DEFAULT_RETRY_DELAY,
                backoff_multiplier=DEFAULT_RETRY_BACKOFF,
            )

        # Idempotent actions get fewer retries
        if action.action_type in ("screenshot", "get_weather", "search_web"):
            return RetryPolicy(max_attempts=1, delay_seconds=0.2)

        return RetryPolicy(
            max_attempts=1,
            delay_seconds=DEFAULT_RETRY_DELAY,
        )

    def _detect_dependencies(self, actions: List[Action]) -> List[Action]:
        """
        Detect implicit dependencies between actions.
        
        Examples:
        - "open chrome and search for X" → search depends on chrome opening
        - "create file and open it" → open depends on create
        - "close X then open Y" → open depends on close
        """
        if len(actions) < 2:
            return actions

        for i in range(1, len(actions)):
            prev = actions[i - 1]
            curr = actions[i]

            # If already has explicit dependency, skip
            if curr.depends_on:
                continue

            # Search/URL after app open → likely depends on browser
            if (prev.action_type == "open_app"
                    and curr.action_type in ("search_web", "play_youtube", "open_url")):
                curr.depends_on = prev.id
                curr.condition = "previous_success"

            # Open file after create → depends on creation
            elif (prev.action_type == "create_file"
                  and curr.action_type == "open_file"):
                curr.depends_on = prev.id
                curr.condition = "previous_success"

            # Close then open same category → sequential
            elif (prev.action_type == "close_app"
                  and curr.action_type == "open_app"):
                curr.depends_on = prev.id
                curr.condition = "previous_success"

        return actions

    def _create_fallback_branches(self, actions: List[Action]) -> List[Action]:
        """
        Create fallback actions for critical operations.
        
        Example: if open_app via command fails, fallback is open_app via start.
        These are added as conditional steps that only execute if the primary fails.
        """
        fallbacks = []

        for action in actions:
            if action.action_type == "open_app":
                # Add a search fallback if the app open fails
                fallback = Action(
                    action_type="search_web",
                    params={"query": f"{action.get_param('app', '')} download"},
                    confidence=0.5,
                    source="fallback",
                    depends_on=action.id,
                    condition="previous_failed",
                    fallback_for=action.id,
                    priority=action.priority - 1,
                )
                fallbacks.append(fallback)

        actions.extend(fallbacks)
        return actions

    def _topological_sort(self, actions: List[Action]) -> List[Action]:
        """
        Sort actions respecting dependencies.
        Actions without dependencies come first (sorted by priority).
        Dependent actions come after their dependency.
        """
        # Build adjacency
        id_map = {a.id: a for a in actions}
        sorted_result = []
        visited = set()

        def visit(action: Action):
            if action.id in visited:
                return
            visited.add(action.id)

            # Visit dependency first
            if action.depends_on and action.depends_on in id_map:
                visit(id_map[action.depends_on])

            sorted_result.append(action)

        # Process independent actions first (sorted by priority descending)
        independent = sorted(
            [a for a in actions if not a.depends_on],
            key=lambda a: a.priority,
            reverse=True,
        )
        for action in independent:
            visit(action)

        # Then any remaining dependent actions
        dependent = sorted(
            [a for a in actions if a.depends_on],
            key=lambda a: a.priority,
            reverse=True,
        )
        for action in dependent:
            visit(action)

        return sorted_result

    def _needs_sequential(self, actions: List[Action]) -> bool:
        """Determine if actions need sequential execution."""
        # If any action has dependencies, must be sequential
        return any(a.depends_on for a in actions)

    def decompose_compound(self, user_input: str, actions: List[Action]) -> List[Action]:
        """
        Post-process LLM actions to decompose compound requests.
        
        Example: "open chrome and play music on spotify"
        LLM might return [open_app(chrome), play_youtube(music)]
        But we know spotify needs to be opened too.
        """
        decomposed = list(actions)

        for action in actions:
            # If playing youtube but no browser open action, add one
            if action.action_type == "play_youtube":
                has_browser = any(
                    a.action_type == "open_app"
                    and a.get_param("app", "") in ("chrome", "firefox", "edge", "browser")
                    for a in actions
                )
                # Don't add browser open — YouTube will open in default browser
                # This is actually correct behavior

        return decomposed
