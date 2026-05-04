"""
Senku Pattern Learner
Learns behavioral patterns from repeated commands and action outcomes.

This is NOT just logging — it's actual learning logic:
1. Detects repeated command → action mappings
2. Builds confidence scores from historical success rates
3. Can predict what the user wants based on past behavior
4. Improves alias resolution over time
5. Adapts to individual user vocabulary
"""

import re
from datetime import datetime
from typing import Optional

from senku.config import (
    PATTERN_FILE, PATTERN_MIN_OCCURRENCES, PATTERN_MAX_STORED, DEBUG_MODE,
)
from senku.memory.store import MemoryStore
from senku.core.types import Action, ActionResult
from senku.core.events import event_bus, Events


class PatternLearner:
    """
    Learns from user behavior to predict future actions.
    
    Storage structure:
    {
        "patterns": {
            "normalized_input_hash": {
                "input": "open chrome",
                "action_type": "open_app",
                "params": {"app": "chrome"},
                "success_count": 47,
                "fail_count": 2,
                "last_used": "2026-05-04T12:00:00",
                "total_duration_ms": 38400,
            }
        },
        "vocab": {
            "my editor": "vscode",
            "browser": "chrome",
            ...
        },
        "command_frequency": {
            "open_app": 120,
            "search_web": 45,
            ...
        }
    }
    """

    def __init__(self):
        self._store = MemoryStore(PATTERN_FILE, default_data={
            "patterns": {},
            "vocab": {},
            "command_frequency": {},
        })

    def learn_from_result(self, raw_input: str, action: Action,
                          result: ActionResult):
        """
        Learn from an action result.
        This is called after every action execution via the event bus.
        """
        data = self._store.load()
        key = self._make_key(raw_input, action.action_type)

        patterns = data.get("patterns", {})

        if key not in patterns:
            patterns[key] = {
                "input": raw_input.lower().strip(),
                "action_type": action.action_type,
                "params": action.params,
                "success_count": 0,
                "fail_count": 0,
                "last_used": "",
                "total_duration_ms": 0,
            }

        entry = patterns[key]
        if result.success:
            entry["success_count"] += 1
        else:
            entry["fail_count"] += 1

        entry["last_used"] = datetime.now().isoformat()
        entry["total_duration_ms"] += result.duration_ms

        # Update params with the latest successful params
        if result.success:
            entry["params"] = action.params

        patterns[key] = entry
        data["patterns"] = patterns

        # Update command frequency
        freq = data.get("command_frequency", {})
        freq[action.action_type] = freq.get(action.action_type, 0) + 1
        data["command_frequency"] = freq

        # Trim if too many patterns
        if len(patterns) > PATTERN_MAX_STORED:
            self._trim_patterns(patterns)

        self._store.save()

        # Emit learning event if pattern is now strong enough
        total = entry["success_count"] + entry["fail_count"]
        if total == PATTERN_MIN_OCCURRENCES:
            event_bus.emit(Events.PATTERN_LEARNED,
                           input_text=raw_input,
                           action_type=action.action_type)
            if DEBUG_MODE:
                print(f"[Pattern] New pattern learned: '{raw_input}' "
                      f"→ {action.action_type}")

    def learn_vocabulary(self, user_term: str, resolved_term: str):
        """
        Learn user-specific vocabulary.
        e.g., user says "my editor" → resolves to "vscode"
        """
        data = self._store.load()
        vocab = data.get("vocab", {})
        vocab[user_term.lower().strip()] = resolved_term.lower().strip()
        data["vocab"] = vocab
        self._store.save()

    def get_confidence(self, raw_input: str, action_type: str,
                       params: dict = None) -> float:
        """
        Get confidence score for a command → action mapping based on history.
        
        Returns 0.0 if no pattern exists, up to 1.0 for very reliable patterns.
        """
        data = self._store.load()
        key = self._make_key(raw_input, action_type)
        patterns = data.get("patterns", {})

        if key not in patterns:
            return 0.0

        entry = patterns[key]
        total = entry["success_count"] + entry["fail_count"]

        if total < PATTERN_MIN_OCCURRENCES:
            return 0.0  # Not enough data

        success_rate = entry["success_count"] / total if total > 0 else 0
        # Scale confidence: 3 occurrences = 0.5 base, scales up to 0.95
        volume_factor = min(total / 20, 1.0)  # Caps at 20 occurrences
        confidence = success_rate * (0.5 + 0.45 * volume_factor)

        return round(confidence, 3)

    def predict_action(self, raw_input: str) -> Optional[Action]:
        """
        Predict an action from learned patterns.
        Only returns if confidence is very high (pattern-based shortcut).
        """
        data = self._store.load()
        patterns = data.get("patterns", {})
        input_lower = raw_input.lower().strip()

        best_match = None
        best_confidence = 0.0

        for key, entry in patterns.items():
            if entry.get("input", "") == input_lower:
                total = entry["success_count"] + entry["fail_count"]
                if total >= PATTERN_MIN_OCCURRENCES:
                    success_rate = entry["success_count"] / total
                    if success_rate > best_confidence:
                        best_confidence = success_rate
                        best_match = entry

        if best_match and best_confidence >= 0.85:
            return Action(
                action_type=best_match["action_type"],
                params=dict(best_match.get("params", {})),
                confidence=best_confidence,
                source="pattern",
            )

        return None

    def resolve_vocabulary(self, text: str) -> str:
        """
        Resolve user-specific vocabulary in the input text.
        e.g., "open my editor" → "open vscode"
        """
        data = self._store.load()
        vocab = data.get("vocab", {})
        result = text.lower()

        for user_term, resolved in vocab.items():
            if user_term in result:
                result = result.replace(user_term, resolved)

        return result

    def get_avg_duration(self, action_type: str) -> float:
        """Get average execution duration for an action type (in ms)."""
        data = self._store.load()
        patterns = data.get("patterns", {})

        total_duration = 0
        total_count = 0
        for entry in patterns.values():
            if entry.get("action_type") == action_type:
                count = entry["success_count"] + entry["fail_count"]
                if count > 0:
                    total_duration += entry.get("total_duration_ms", 0)
                    total_count += count

        return total_duration / total_count if total_count > 0 else 0

    def get_success_rate(self, action_type: str) -> float:
        """Get historical success rate for an action type."""
        data = self._store.load()
        patterns = data.get("patterns", {})

        total_success = 0
        total_count = 0
        for entry in patterns.values():
            if entry.get("action_type") == action_type:
                total_success += entry.get("success_count", 0)
                total_count += entry["success_count"] + entry["fail_count"]

        return total_success / total_count if total_count > 0 else 0.5

    def get_top_patterns(self, limit: int = 10) -> list:
        """Get the most frequently used patterns."""
        data = self._store.load()
        patterns = data.get("patterns", {})

        sorted_patterns = sorted(
            patterns.values(),
            key=lambda e: e["success_count"] + e["fail_count"],
            reverse=True,
        )
        return sorted_patterns[:limit]

    def _make_key(self, raw_input: str, action_type: str) -> str:
        """Create a stable key for a command → action mapping."""
        # Normalize: lowercase, strip, collapse whitespace
        normalized = re.sub(r"\s+", " ", raw_input.lower().strip())
        return f"{normalized}::{action_type}"

    def _trim_patterns(self, patterns: dict):
        """Remove least-used patterns to stay within limits."""
        if len(patterns) <= PATTERN_MAX_STORED:
            return

        # Sort by total usage (ascending) — remove least used
        sorted_keys = sorted(
            patterns.keys(),
            key=lambda k: patterns[k]["success_count"] + patterns[k]["fail_count"],
        )

        to_remove = len(patterns) - PATTERN_MAX_STORED
        for key in sorted_keys[:to_remove]:
            del patterns[key]
