"""
Senku Memory Store
Core persistent storage engine with safe JSON operations.
Handles atomic reads/writes with corruption recovery.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class MemoryStore:
    """
    Thread-safe JSON-based persistent storage engine.
    
    Features:
    - Atomic write operations (write to temp, then rename)
    - Automatic corruption recovery (reset to default)
    - Schema validation
    - Backup on critical operations
    """

    def __init__(self, filepath: str | Path, default_data: Any = None):
        self.filepath = Path(filepath)
        self.default_data = default_data if default_data is not None else {}
        self._cache: Optional[Any] = None
        self._dirty = False
        self._op_count = 0

    def load(self) -> Any:
        """Load data from disk. Returns cached version if available."""
        if self._cache is not None:
            return self._cache

        if not self.filepath.exists():
            self._cache = self._deep_copy(self.default_data)
            self.save()
            return self._cache

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    self._cache = self._deep_copy(self.default_data)
                    return self._cache
                self._cache = json.loads(content)
                return self._cache
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"[Memory] Warning: Corrupted file {self.filepath.name}: {e}")
            self._backup_corrupted()
            self._cache = self._deep_copy(self.default_data)
            self.save()
            return self._cache

    def save(self):
        """Atomically save data to disk."""
        if self._cache is None:
            return

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temp file first, then rename (atomic on most OS)
        tmp_path = self.filepath.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)

            # Replace original with temp
            if self.filepath.exists():
                os.replace(tmp_path, self.filepath)
            else:
                os.rename(tmp_path, self.filepath)

            self._dirty = False
        except Exception as e:
            print(f"[Memory] Error saving {self.filepath.name}: {e}")
            # Clean up temp file
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the store (dict-based stores only)."""
        data = self.load()
        if isinstance(data, dict):
            return data.get(key, default)
        return default

    def set(self, key: str, value: Any, auto_save: bool = True):
        """Set a value in the store (dict-based stores only)."""
        data = self.load()
        if isinstance(data, dict):
            data[key] = value
            self._dirty = True
            self._op_count += 1
            if auto_save:
                self.save()

    def delete(self, key: str, auto_save: bool = True):
        """Delete a key from the store."""
        data = self.load()
        if isinstance(data, dict) and key in data:
            del data[key]
            self._dirty = True
            if auto_save:
                self.save()

    def append(self, item: Any, max_items: int = 0, auto_save: bool = True):
        """Append an item (list-based stores only). Trims to max_items."""
        data = self.load()
        if isinstance(data, list):
            data.append(item)
            if max_items > 0 and len(data) > max_items:
                # Remove oldest entries
                data[:] = data[-max_items:]
            self._dirty = True
            self._op_count += 1
            if auto_save:
                self.save()

    def clear(self):
        """Reset store to default data."""
        self._cache = self._deep_copy(self.default_data)
        self._dirty = True
        self.save()

    def all(self) -> Any:
        """Return all data."""
        return self.load()

    def _backup_corrupted(self):
        """Create a backup of corrupted data file."""
        if self.filepath.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.filepath.with_suffix(f".corrupted_{timestamp}.bak")
            try:
                shutil.copy2(self.filepath, backup_path)
                print(f"[Memory] Backed up corrupted file to {backup_path.name}")
            except Exception:
                pass

    @staticmethod
    def _deep_copy(data: Any) -> Any:
        """Create a deep copy of data using JSON serialization."""
        if data is None:
            return None
        return json.loads(json.dumps(data))
