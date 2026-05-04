"""
Senku Context Manager
Manages session context for context-aware interactions.
Persists state between sessions and within sessions.
"""

from senku.config import CONTEXT_FILE
from senku.memory.store import MemoryStore
from senku.core.types import SessionContext, Action, ActionResult


class ContextManager:
    """
    Tracks session state and provides contextual information
    to the brain for smarter decision-making.
    """

    def __init__(self):
        self._store = MemoryStore(CONTEXT_FILE, default_data={})
        self._session = SessionContext()
        self._load_persistent_context()

    def _load_persistent_context(self):
        """Load persistent context from last session."""
        data = self._store.load()
        if isinstance(data, dict):
            self._session.last_app = data.get("last_app", "")
            self._session.last_query = data.get("last_query", "")
            self._session.active_apps = data.get("active_apps", [])

    def save(self):
        """Save current context to disk."""
        data = self._session.to_dict()
        for key, value in data.items():
            self._store.set(key, value, auto_save=False)
        self._store.save()

    def update_after_action(self, action: Action, result: ActionResult):
        """Update context after an action is executed."""
        self._session.update_after_action(action, result)
        self.save()

    def update_last_input(self, text: str):
        """Update context with the latest user input."""
        self._session.last_query = text

    @property
    def session(self) -> SessionContext:
        """Get the current session context."""
        return self._session

    @property
    def last_app(self) -> str:
        return self._session.last_app

    @property
    def last_action(self) -> str:
        return self._session.last_action

    @property
    def last_query(self) -> str:
        return self._session.last_query

    @property
    def active_apps(self) -> list:
        return self._session.active_apps

    def get_context_summary(self) -> str:
        """Generate a concise context summary for the LLM."""
        parts = []
        if self._session.last_app:
            parts.append(f"Last opened app: {self._session.last_app}")
        if self._session.last_query:
            parts.append(f"Last search: {self._session.last_query}")
        if self._session.active_apps:
            apps = ", ".join(self._session.active_apps[-5:])
            parts.append(f"Recently opened: {apps}")
        if self._session.action_count > 0:
            parts.append(f"Actions this session: {self._session.action_count}")

        return "; ".join(parts) if parts else "New session"

    def reset(self):
        """Reset session context."""
        self._session = SessionContext()
        self.save()
