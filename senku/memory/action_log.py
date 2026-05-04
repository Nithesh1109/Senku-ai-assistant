"""
Senku Action Log
Records action execution outcomes for learning and analytics.
Enables Senku to learn which actions succeed/fail and improve over time.
"""

from senku.config import ACTION_LOG_FILE, MAX_ACTION_LOG_ENTRIES
from senku.memory.store import MemoryStore
from senku.core.types import Action, ActionResult, ActionStatus


class ActionLog:
    """
    Persistent action execution log.
    
    Tracks:
    - What actions were attempted
    - Success/failure rates
    - Common error patterns
    - Frequently used actions
    """

    def __init__(self):
        self._store = MemoryStore(ACTION_LOG_FILE, default_data=[])

    def record(self, result: ActionResult):
        """Record an action result."""
        entry = {
            "action_type": result.action.action_type,
            "params": result.action.params,
            "status": result.status.value,
            "message": result.message,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "timestamp": result.timestamp,
        }
        self._store.append(entry, max_items=MAX_ACTION_LOG_ENTRIES)

    def get_success_rate(self, action_type: str) -> float:
        """Get the success rate for a specific action type."""
        entries = self._store.all()
        if not isinstance(entries, list):
            return 0.0

        relevant = [e for e in entries if e.get("action_type") == action_type]
        if not relevant:
            return 0.0

        successful = sum(1 for e in relevant if e.get("status") == "success")
        return successful / len(relevant)

    def get_common_failures(self, action_type: str = None, limit: int = 5) -> list:
        """Get the most common failure patterns."""
        entries = self._store.all()
        if not isinstance(entries, list):
            return []

        failures = [
            e for e in entries
            if e.get("status") == "failed"
            and (action_type is None or e.get("action_type") == action_type)
        ]

        # Group by error message
        error_counts = {}
        for f in failures:
            error = f.get("error", "unknown")
            error_counts[error] = error_counts.get(error, 0) + 1

        # Sort by frequency
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_errors[:limit]

    def get_frequent_actions(self, limit: int = 10) -> list:
        """Get the most frequently used action types."""
        entries = self._store.all()
        if not isinstance(entries, list):
            return []

        counts = {}
        for e in entries:
            action_type = e.get("action_type", "unknown")
            counts[action_type] = counts.get(action_type, 0) + 1

        sorted_actions = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_actions[:limit]

    def get_recent(self, n: int = 10) -> list:
        """Get the N most recent action log entries."""
        entries = self._store.all()
        if isinstance(entries, list):
            return entries[-n:]
        return []

    def get_app_launch_history(self) -> dict:
        """Get history of app launches with success counts."""
        entries = self._store.all()
        if not isinstance(entries, list):
            return {}

        app_stats = {}
        for e in entries:
            if e.get("action_type") == "open_app":
                app = e.get("params", {}).get("app", "unknown")
                if app not in app_stats:
                    app_stats[app] = {"success": 0, "fail": 0}
                if e.get("status") == "success":
                    app_stats[app]["success"] += 1
                else:
                    app_stats[app]["fail"] += 1

        return app_stats
