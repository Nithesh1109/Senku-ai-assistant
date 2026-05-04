"""
Senku Conversation Memory
Tracks conversation history for context-aware interactions.
"""

from senku.config import CONVERSATION_FILE, MAX_CONVERSATION_HISTORY
from senku.memory.store import MemoryStore
from senku.core.types import ConversationTurn


class ConversationMemory:
    """
    Manages conversation history with sliding window.
    Provides context for multi-turn interactions.
    """

    def __init__(self):
        self._store = MemoryStore(CONVERSATION_FILE, default_data=[])

    def add_turn(self, role: str, content: str, actions: list = None):
        """Add a conversation turn."""
        turn = ConversationTurn(
            role=role,
            content=content,
            actions_taken=[a.to_dict() for a in (actions or [])],
        )
        self._store.append(
            turn.to_dict(),
            max_items=MAX_CONVERSATION_HISTORY,
        )

    def add_user_input(self, text: str):
        """Record user input."""
        self.add_turn("user", text)

    def add_assistant_response(self, text: str, actions: list = None):
        """Record assistant response."""
        self.add_turn("assistant", text, actions)

    def get_recent(self, n: int = 10) -> list:
        """Get the N most recent conversation turns."""
        history = self._store.all()
        if isinstance(history, list):
            return history[-n:]
        return []

    def get_context_string(self, n: int = 5) -> str:
        """
        Format recent conversation as a string for LLM context.
        Keeps it concise to avoid token waste.
        """
        recent = self.get_recent(n)
        if not recent:
            return ""

        lines = []
        for turn in recent:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."
            prefix = "User" if role == "user" else "Senku"
            lines.append(f"{prefix}: {content}")

        return "\n".join(lines)

    def clear(self):
        """Clear conversation history."""
        self._store.clear()

    @property
    def turn_count(self) -> int:
        """Number of conversation turns."""
        data = self._store.all()
        return len(data) if isinstance(data, list) else 0
