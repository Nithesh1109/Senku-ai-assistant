"""
Senku Decision Layer
Intelligent decision-making for ambiguous, multi-option, and low-confidence scenarios.

Responsibilities:
1. Choose action vs chat when ambiguous
2. Rank actions by confidence when multiple interpretations exist
3. Detect ambiguity and generate clarification questions
4. Apply learned patterns to boost confidence
"""

from typing import List, Optional
from senku.core.types import Action, Intent, IntentType
from senku.config import (
    DEBUG_MODE, MIN_CONFIDENCE_THRESHOLD, AMBIGUITY_THRESHOLD,
)


class DecisionLayer:
    """
    The 'should I or shouldn't I?' layer.
    
    Sits between the parser output and the executor.
    Catches situations where blind execution would be wrong:
    - Low confidence actions
    - Ambiguous phrasing ("play" could mean youtube or spotify)
    - Missing critical parameters
    - Conflicting actions
    """

    def __init__(self, pattern_learner=None):
        self.pattern_learner = pattern_learner  # Injected — avoids circular imports

    def evaluate(self, intent: Intent, context_summary: str = "") -> Intent:
        """
        Evaluate and potentially modify an intent before execution.
        
        v3.2 Philosophy: EXECUTE FIRST, ASK LATER.
        Only block execution when absolutely necessary.
        
        Returns the intent — possibly modified with:
        - Reranked actions
        - Removed low-confidence actions
        - Changed intent type (only for truly broken cases)
        """
        if intent.is_chat or not intent.has_actions:
            return intent

        # ─── Step 1: Filter out garbage actions ──────────────
        intent.actions = self._filter_low_confidence(intent.actions)

        if not intent.actions:
            # Everything was filtered — treat as chat
            intent.intent_type = IntentType.CHAT
            intent.reasoning = "All actions below confidence threshold"
            return intent

        # ─── Step 2: Boost from learned patterns ─────────────
        if self.pattern_learner:
            intent.actions = self._apply_pattern_boost(
                intent.actions, intent.raw_input
            )

        # ─── Step 3: Check for conflicts (not blocking) ──────
        intent.actions = self._resolve_conflicts(intent.actions)

        # ─── Step 4: Rank by composite score ─────────────────
        intent.actions = self._rank_actions(intent.actions)

        # ─── Step 5: Only block for duplicate ambiguity ──────
        # Do NOT ask for confirmation on normal commands
        # Only ask when there are truly ambiguous duplicate actions
        clarification = self._detect_critical_ambiguity(intent.actions, intent.raw_input)
        if clarification:
            intent.clarification_needed = clarification
            intent.intent_type = IntentType.UNCLEAR
            intent.reasoning = f"Ambiguity detected: {clarification}"
            if DEBUG_MODE:
                print(f"[Decision] Ambiguous: {clarification}")
            return intent

        intent.reasoning = "All checks passed — executing directly"
        return intent

    def _filter_low_confidence(self, actions: List[Action]) -> List[Action]:
        """Remove actions below the confidence threshold."""
        filtered = [a for a in actions if a.confidence >= MIN_CONFIDENCE_THRESHOLD]

        if DEBUG_MODE and len(filtered) < len(actions):
            removed = len(actions) - len(filtered)
            print(f"[Decision] Filtered {removed} low-confidence actions")

        return filtered

    def _apply_pattern_boost(self, actions: List[Action],
                             raw_input: str) -> List[Action]:
        """
        Boost confidence of actions that match learned patterns.
        If the user has run "open chrome" 50 times successfully,
        we should be very confident about it.
        """
        if not self.pattern_learner:
            return actions

        for action in actions:
            pattern_confidence = self.pattern_learner.get_confidence(
                raw_input, action.action_type, action.params
            )
            if pattern_confidence > 0:
                # Blend: 70% LLM confidence + 30% pattern confidence
                original = action.confidence
                action.confidence = (0.7 * original) + (0.3 * pattern_confidence)
                action.source = "llm+pattern"
                if DEBUG_MODE:
                    print(f"[Decision] Pattern boost: {action.action_type} "
                          f"{original:.2f} -> {action.confidence:.2f}")

        return actions

    def _detect_critical_ambiguity(self, actions: List[Action],
                                    raw_input: str) -> str:
        """
        Only detect CRITICAL ambiguity that requires user input.
        
        v3.2: Much less aggressive than before. Only blocks when:
        - Multiple actions of the same type (true ambiguity)
        - open_app with completely empty app name
        
        Does NOT block for:
        - Low confidence (just execute and see)
        - Missing optional params
        - Contact names vs phone numbers
        """
        if not actions:
            return ""

        # Case 1: Multiple actions of same type with different params
        type_counts = {}
        for a in actions:
            type_counts[a.action_type] = type_counts.get(a.action_type, 0) + 1
        for action_type, count in type_counts.items():
            if count > 1:
                return (
                    f"I found multiple '{action_type}' interpretations. "
                    f"Which one did you mean?"
                )

        # Case 2: open_app with empty app name
        for a in actions:
            if a.action_type == "open_app" and not a.get_param("app", ""):
                return "Which app would you like me to open?"

        return ""

    def _resolve_conflicts(self, actions: List[Action]) -> List[Action]:
        """
        Resolve conflicting actions.
        
        Example: open_app(chrome) + close_app(chrome) = contradictory
        """
        to_remove = set()

        for i, a in enumerate(actions):
            for j, b in enumerate(actions):
                if i >= j:
                    continue

                # Open + close same app -> keep only the last one mentioned
                if (a.action_type == "open_app" and b.action_type == "close_app"
                        and a.get_param("app") == b.get_param("app")):
                    to_remove.add(i)
                    if DEBUG_MODE:
                        print(f"[Decision] Conflict: open + close {a.get_param('app')}"
                              f" -> keeping close")

                elif (a.action_type == "close_app" and b.action_type == "open_app"
                      and a.get_param("app") == b.get_param("app")):
                    # Close then open same app = restart
                    pass  # This is intentional, keep both

        return [a for i, a in enumerate(actions) if i not in to_remove]

    def _rank_actions(self, actions: List[Action]) -> List[Action]:
        """Rank actions by composite confidence score."""
        return sorted(actions, key=lambda a: a.confidence, reverse=True)
