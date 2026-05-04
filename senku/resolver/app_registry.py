"""
Senku App Registry
System app discovery and cache integration.
Leverages the existing 1200+ entry app_cache.json for deep app resolution.
"""

import json
from pathlib import Path
from typing import Optional

from senku.config import (
    APP_CACHE_FILE,
    APP_PROTOCOL_MAP,
    APP_COMMAND_MAP,
    APP_URL_MAP,
)


class AppRegistry:
    """
    Comprehensive app registry combining:
    1. System app cache (auto-scanned executables)
    2. Protocol mappings (whatsapp:, spotify:, etc.)
    3. Command mappings (code, notepad, etc.)
    4. URL mappings (youtube, gmail, etc.)
    """

    def __init__(self):
        self._app_cache: dict = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy-load the app cache."""
        if self._loaded:
            return

        if APP_CACHE_FILE.exists():
            try:
                with open(APP_CACHE_FILE, "r", encoding="utf-8") as f:
                    self._app_cache = json.load(f)
                self._loaded = True
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"[Registry] Warning: Failed to load app cache: {e}")
                self._app_cache = {}
                self._loaded = True
        else:
            self._loaded = True

    def find_executable(self, app_name: str) -> Optional[str]:
        """
        Find an executable path from the system app cache.
        Returns the full path or None.
        """
        self._ensure_loaded()
        app_lower = app_name.lower().strip()

        # Direct match
        if app_lower in self._app_cache:
            return self._app_cache[app_lower]

        # Partial match — search for key containing the app name
        for key, path in self._app_cache.items():
            if app_lower in key or key in app_lower:
                # Prefer user-facing apps over system internals
                if self._is_user_app(path):
                    return path

        return None

    def get_protocol(self, app_name: str) -> Optional[str]:
        """Get a protocol URI for an app (e.g., 'whatsapp:')."""
        return APP_PROTOCOL_MAP.get(app_name.lower().strip())

    def get_command(self, app_name: str) -> Optional[str]:
        """Get a command-line name for an app (e.g., 'code')."""
        return APP_COMMAND_MAP.get(app_name.lower().strip())

    def get_url(self, app_name: str) -> Optional[str]:
        """Get a URL for a web-based app (e.g., 'youtube')."""
        return APP_URL_MAP.get(app_name.lower().strip())

    def get_all_known_apps(self) -> list:
        """Get a list of all known app names (from all sources)."""
        self._ensure_loaded()
        apps = set()
        apps.update(APP_PROTOCOL_MAP.keys())
        apps.update(APP_COMMAND_MAP.keys())
        apps.update(APP_URL_MAP.keys())
        # Add top user-facing apps from cache
        for key, path in self._app_cache.items():
            if self._is_user_app(path):
                apps.add(key)
        return sorted(apps)

    def search(self, query: str, limit: int = 10) -> list:
        """
        Search for apps matching a query.
        Returns list of (name, source) tuples.
        """
        self._ensure_loaded()
        query_lower = query.lower().strip()
        results = []

        # Check protocol apps
        for name in APP_PROTOCOL_MAP:
            if query_lower in name:
                results.append((name, "protocol"))

        # Check command apps
        for name in APP_COMMAND_MAP:
            if query_lower in name:
                results.append((name, "command"))

        # Check URL apps
        for name in APP_URL_MAP:
            if query_lower in name:
                results.append((name, "url"))

        # Check system cache
        for name, path in self._app_cache.items():
            if query_lower in name and self._is_user_app(path):
                results.append((name, "system"))
                if len(results) >= limit:
                    break

        return results[:limit]

    @staticmethod
    def _is_user_app(path: str) -> bool:
        """
        Heuristic to determine if an executable is a user-facing application.
        Filters out system utilities, services, and helper processes.
        """
        path_lower = path.lower()
        # Exclude common non-user paths
        exclude_patterns = [
            "\\usr\\bin\\",
            "\\usr\\lib\\",
            "\\mingw64\\",
            "\\libexec\\",
            "helper",
            "service",
            "updater",
            "uninstall",
            "crashpad",
            "installer",
            "setup",
        ]
        for pattern in exclude_patterns:
            if pattern in path_lower:
                return False
        return True
