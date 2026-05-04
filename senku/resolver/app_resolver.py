"""
Senku App Resolver
Multi-strategy app name resolution engine.
Combines aliases, exact match, fuzzy match, and system cache for robust resolution.
"""

from difflib import get_close_matches
from typing import Optional

from senku.config import (
    FUZZY_MATCH_CUTOFF,
    MAX_FUZZY_RESULTS,
    APP_PROTOCOL_MAP,
    APP_COMMAND_MAP,
    APP_URL_MAP,
)
from senku.resolver.alias_store import AliasStore
from senku.resolver.app_registry import AppRegistry


class AppResolver:
    """
    Intelligent multi-strategy app name resolution.
    
    Resolution order:
    1. User-learned aliases (highest priority — learned behavior)
    2. Protocol map (whatsapp → whatsapp:)
    3. Command map (vscode → code)
    4. URL map (youtube → https://youtube.com)
    5. System app cache (deep system scan)
    6. Fuzzy matching against all known apps
    7. Return original (fallback)
    """

    def __init__(self, alias_store: AliasStore = None, registry: AppRegistry = None):
        self.alias_store = alias_store or AliasStore()
        self.registry = registry or AppRegistry()

    def resolve(self, app_name: str) -> dict:
        """
        Resolve an app name to a launch target.
        
        Returns a dict with:
        - name: resolved app name
        - target: what to launch (path, protocol, command, or url)
        - method: how to launch (protocol, command, url, path, start, search)
        - confidence: resolution confidence (0.0 - 1.0)
        - source: where the resolution came from
        """
        app = app_name.lower().strip()
        if not app:
            return self._result(app_name, app_name, "search", 0.0, "fallback")

        # ─── 1. Check user-learned aliases ────────────────────
        alias_result = self.alias_store.lookup(app)
        if alias_result:
            self.alias_store.increment_usage(app)
            # Recursively resolve the alias target
            inner = self.resolve(alias_result)
            inner["source"] = "alias"
            inner["confidence"] = max(inner["confidence"], 0.95)
            return inner

        # ─── 2. Check protocol map ───────────────────────────
        protocol = self.registry.get_protocol(app)
        if protocol:
            return self._result(app, protocol, "protocol", 1.0, "protocol_map")

        # ─── 3. Check command map ────────────────────────────
        command = self.registry.get_command(app)
        if command:
            return self._result(app, command, "command", 1.0, "command_map")

        # ─── 4. Check URL map ────────────────────────────────
        url = self.registry.get_url(app)
        if url:
            return self._result(app, url, "url", 1.0, "url_map")

        # ─── 5. Check system app cache ───────────────────────
        exe_path = self.registry.find_executable(app)
        if exe_path:
            return self._result(app, exe_path, "path", 0.9, "app_cache")

        # ─── 6. Fuzzy matching ───────────────────────────────
        all_known = self._get_all_known_names()
        fuzzy_matches = get_close_matches(
            app, all_known,
            n=MAX_FUZZY_RESULTS,
            cutoff=FUZZY_MATCH_CUTOFF,
        )
        if fuzzy_matches:
            best_match = fuzzy_matches[0]
            # Resolve the fuzzy match through normal channels
            inner = self.resolve(best_match)
            # Adjust confidence based on fuzzy match quality
            inner["confidence"] *= 0.8
            inner["source"] = f"fuzzy({best_match})"
            return inner

        # ─── 7. Fallback — try Windows start command ─────────
        return self._result(app, app, "start", 0.3, "fallback")

    def learn_alias(self, alias: str, resolved: str) -> bool:
        """
        Learn a new alias mapping.
        Returns True if the alias was actually new.
        """
        if self.alias_store.has(alias):
            return False
        self.alias_store.add(alias, resolved)
        return True

    def suggest_correction(self, app_name: str) -> Optional[str]:
        """
        Suggest a corrected app name for typos.
        Returns None if no good suggestion found.
        """
        all_known = self._get_all_known_names()
        matches = get_close_matches(
            app_name.lower(),
            all_known,
            n=1,
            cutoff=0.5,  # Lower cutoff for suggestions
        )
        return matches[0] if matches else None

    def _get_all_known_names(self) -> list:
        """Get all known app names from all sources."""
        names = set()
        names.update(APP_PROTOCOL_MAP.keys())
        names.update(APP_COMMAND_MAP.keys())
        names.update(APP_URL_MAP.keys())
        # Add alias targets too
        for alias, value in self.alias_store.get_all().items():
            names.add(alias)
            if isinstance(value, dict):
                names.add(value.get("app", ""))
            elif isinstance(value, str):
                names.add(value)
        return list(names)

    @staticmethod
    def _result(name: str, target: str, method: str,
                confidence: float, source: str) -> dict:
        """Create a resolution result dict."""
        return {
            "name": name,
            "target": target,
            "method": method,
            "confidence": confidence,
            "source": source,
        }
