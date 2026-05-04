"""
Senku Feedback Loop
Post-action evaluation and scoring system.

Quantifies how well each action and plan performed,
generates improvement suggestions, and feeds scores
back into the learning system.
"""

from typing import List, Optional
from datetime import datetime

from senku.core.types import (
    Action, ActionResult, ActionStatus, ExecutionPlan, FeedbackScore,
)
from senku.core.events import event_bus, Events
from senku.config import (
    FEEDBACK_FILE, FEEDBACK_WEIGHTS, SPEED_BASELINE_MS, DEBUG_MODE,
)
from senku.memory.store import MemoryStore


class FeedbackLoop:
    """
    Post-execution evaluation engine.
    
    After every action/plan execution:
    1. Compute a multi-dimensional score
    2. Compare against historical performance
    3. Generate improvement suggestions
    4. Log feedback for trend analysis
    """

    def __init__(self, pattern_learner=None):
        self._store = MemoryStore(FEEDBACK_FILE, default_data=[])
        self.pattern_learner = pattern_learner

    def evaluate_action(self, result: ActionResult) -> FeedbackScore:
        """Evaluate a single action result."""
        score = FeedbackScore()

        # ─── Success Score ───────────────────────────────────
        score.success_score = 1.0 if result.success else 0.0

        # ─── Speed Score ─────────────────────────────────────
        baseline = SPEED_BASELINE_MS.get(result.action.action_type, 500)
        if result.duration_ms > 0:
            ratio = baseline / result.duration_ms
            score.speed_score = min(ratio, 1.0)
        else:
            score.speed_score = 1.0

        # ─── Reliability Score ───────────────────────────────
        if self.pattern_learner:
            historical_rate = self.pattern_learner.get_success_rate(
                result.action.action_type
            )
            score.reliability_score = historical_rate
        else:
            score.reliability_score = 0.5  # No data

        # ─── Compute Overall ─────────────────────────────────
        score.compute_overall(FEEDBACK_WEIGHTS)

        # ─── Generate Suggestions ────────────────────────────
        score.suggestions = self._generate_suggestions(result, score)

        return score

    def evaluate_plan(self, plan: ExecutionPlan,
                      results: List[ActionResult]) -> FeedbackScore:
        """Evaluate an entire execution plan."""
        if not results:
            return FeedbackScore()

        # Average individual scores
        scores = [self.evaluate_action(r) for r in results]

        plan_score = FeedbackScore()
        plan_score.success_score = sum(s.success_score for s in scores) / len(scores)
        plan_score.speed_score = sum(s.speed_score for s in scores) / len(scores)
        plan_score.reliability_score = sum(
            s.reliability_score for s in scores
        ) / len(scores)
        plan_score.compute_overall(FEEDBACK_WEIGHTS)

        # Plan-level suggestions
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            plan_score.suggestions.append(
                f"{failed_count}/{len(results)} actions failed in this plan"
            )

        # Check if retries were used
        retried = [r for r in results if r.attempt > 1]
        if retried:
            plan_score.suggestions.append(
                f"{len(retried)} actions required retries"
            )

        # Aggregate child suggestions (deduplicate)
        all_suggestions = set()
        for s in scores:
            all_suggestions.update(s.suggestions)
        plan_score.suggestions.extend(
            s for s in all_suggestions if s not in plan_score.suggestions
        )

        # Store plan feedback
        plan.feedback = plan_score

        return plan_score

    def record_feedback(self, action_type: str, score: FeedbackScore):
        """Persist feedback for trend analysis."""
        entry = {
            "action_type": action_type,
            "score": score.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
        self._store.append(entry, max_items=500)

        event_bus.emit(Events.FEEDBACK_COMPUTED,
                       action_type=action_type, score=score)

    def get_trend(self, action_type: str, last_n: int = 20) -> dict:
        """
        Get performance trend for an action type.
        Returns avg scores over the last N feedback entries.
        """
        entries = self._store.all()
        if not isinstance(entries, list):
            return {"avg_overall": 0, "trend": "unknown", "count": 0}

        relevant = [
            e for e in entries
            if e.get("action_type") == action_type
        ][-last_n:]

        if not relevant:
            return {"avg_overall": 0, "trend": "unknown", "count": 0}

        scores = [e.get("score", {}).get("overall", 0) for e in relevant]
        avg = sum(scores) / len(scores) if scores else 0

        # Determine trend
        if len(scores) >= 4:
            first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            if second_half > first_half + 0.05:
                trend = "improving"
            elif second_half < first_half - 0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "avg_overall": round(avg, 3),
            "trend": trend,
            "count": len(relevant),
        }

    def _generate_suggestions(self, result: ActionResult,
                              score: FeedbackScore) -> list:
        """Generate actionable improvement suggestions."""
        suggestions = []

        # Slow execution
        baseline = SPEED_BASELINE_MS.get(result.action.action_type, 500)
        if result.duration_ms > baseline * 2:
            suggestions.append(
                f"'{result.action.action_type}' is slow "
                f"({result.duration_ms:.0f}ms vs {baseline}ms baseline)"
            )

        # Failed action
        if not result.success:
            error = result.error or "unknown error"
            if "not found" in error.lower():
                suggestions.append(
                    f"App/file not found — consider learning an alias"
                )
            elif "permission" in error.lower():
                suggestions.append(
                    f"Permission error — may need admin elevation"
                )
            elif "timeout" in error.lower():
                suggestions.append(
                    f"Timeout — service may be slow or unavailable"
                )

        # Low reliability
        if score.reliability_score < 0.5:
            suggestions.append(
                f"'{result.action.action_type}' has low reliability "
                f"({score.reliability_score:.0%}) — investigate root causes"
            )

        return suggestions
