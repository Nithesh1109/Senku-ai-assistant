"""
Senku Alias Store
Persistent storage for user-learned app name aliases.
"""

from senku.config import ALIASES_FILE
from senku.memory.store import MemoryStore


class AliasStore:
    """
    Manages learned app name aliases.
    
    When a user says "open my editor" and Senku resolves it to "code",
    the mapping "my editor" → "code" is stored here for instant future lookups.
    """

    def __init__(self):
        self._store = MemoryStore(ALIASES_FILE, default_data={})

    def lookup(self, alias: str) -> str | None:
        """Look up an alias. Returns resolved name or None."""
        data = self._store.load()
        if isinstance(data, dict):
            # Case-insensitive lookup
            alias_lower = alias.lower().strip()
            for key, value in data.items():
                if key.lower() == alias_lower:
                    if isinstance(value, dict):
                        return value.get("app", None)
                    return value
        return None

    def add(self, alias: str, resolved: str, auto_save: bool = True):
        """Add a new alias mapping."""
        data = self._store.load()
        if isinstance(data, dict):
            data[alias.lower().strip()] = {
                "app": resolved,
                "count": 1,
            }
            if auto_save:
                self._store.save()

    def increment_usage(self, alias: str):
        """Increment usage count for an alias."""
        data = self._store.load()
        if isinstance(data, dict):
            key = alias.lower().strip()
            if key in data:
                entry = data[key]
                if isinstance(entry, dict):
                    entry["count"] = entry.get("count", 0) + 1
                else:
                    # Migrate old format
                    data[key] = {"app": entry, "count": 1}
                self._store.save()

    def remove(self, alias: str):
        """Remove an alias."""
        self._store.delete(alias.lower().strip())

    def get_all(self) -> dict:
        """Get all aliases."""
        data = self._store.load()
        return data if isinstance(data, dict) else {}

    def has(self, alias: str) -> bool:
        """Check if an alias exists."""
        return self.lookup(alias) is not None

    def get_most_used(self, limit: int = 10) -> list:
        """Get the most frequently used aliases."""
        data = self._store.load()
        if not isinstance(data, dict):
            return []

        entries = []
        for alias, value in data.items():
            if isinstance(value, dict):
                entries.append((alias, value.get("app", ""), value.get("count", 0)))
            else:
                entries.append((alias, value, 0))

        entries.sort(key=lambda x: x[2], reverse=True)
        return entries[:limit]
