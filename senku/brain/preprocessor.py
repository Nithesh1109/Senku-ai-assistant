"""
Senku Input Preprocessor
Normalizes and cleans user input before LLM processing.
Reduces noise, handles common patterns, and extracts shortcuts.
"""

import re
from typing import Optional
from senku.core.types import Action


class Preprocessor:
    """
    Input preprocessing pipeline.
    
    Steps:
    1. Normalize whitespace and casing
    2. Expand abbreviations
    3. Detect shortcut commands (bypass LLM)
    4. Clean noise words
    """

    # Common abbreviations and expansions
    ABBREVIATIONS = {
        "vs code": "vscode",
        "vs": "vscode",
        "yt": "youtube",
        "wp": "whatsapp",
        "wa": "whatsapp",
        "calc": "calculator",
        "cmd": "command prompt",
        "ppt": "powerpoint",
        "ss": "screenshot",
        "vol": "volume",
    }

    # Noise words that don't add meaning
    NOISE_WORDS = {
        "please", "can you", "could you", "would you",
        "hey", "hi", "hello", "yo", "bro",
        "just", "quickly", "now", "right now",
        "for me", "will you", "do",
    }

    # Regex patterns for shortcut detection (bypass LLM entirely)
    SHORTCUT_PATTERNS = [
        # "open X" — direct app launch
        (r"^(?:open|launch|start|run)\s+(.+)$",
         lambda m: Action("open_app", {"app": m.group(1).strip()})),
        # "close X"
        (r"^(?:close|kill|stop|quit|exit)\s+(.+)$",
         lambda m: Action("close_app", {"app": m.group(1).strip()})),
        # "play X" — youtube
        (r"^(?:play|listen to|put on)\s+(.+?)(?:\s+on\s+youtube)?$",
         lambda m: Action("play_youtube", {"query": m.group(1).strip()})),
        # "search X" / "google X"
        (r"^(?:search|google|look up|find)\s+(?:for\s+)?(.+)$",
         lambda m: Action("search_web", {"query": m.group(1).strip()})),
        # "screenshot"
        (r"^(?:screenshot|take\s+(?:a\s+)?screenshot|screen\s+capture|ss)$",
         lambda m: Action("screenshot", {})),
        # "weather [city]"
        (r"^(?:weather|what(?:'s|s)?\s+(?:the\s+)?weather)\s*(?:in\s+)?(.*)$",
         lambda m: Action("get_weather", {"city": m.group(1).strip()} if m.group(1).strip() else {})),
        # "send a message to Y saying X" (MUST be before generic "send X to Y")
        (r"^send\s+(?:a\s+)?message\s+to\s+(.+?)\s+(?:saying|with|that)\s+(.+)$",
         lambda m: Action("send_message", {"to": m.group(1).strip(), "body": m.group(2).strip()})),
        # "message Y saying X"
        (r"^message\s+(.+?)\s+(?:saying|with|that)\s+(.+)$",
         lambda m: Action("send_message", {"to": m.group(1).strip(), "body": m.group(2).strip()})),
        # "send X to Y" — generic (after specific patterns)
        (r"^(?:send|text|msg)\s+(.+?)\s+to\s+(.+)$",
         lambda m: Action("send_message", {"to": m.group(2).strip(), "body": m.group(1).strip()})),
        # "text Y X" (short form)
        (r"^text\s+(\w+)\s+(.+)$",
         lambda m: Action("send_message", {"to": m.group(1).strip(), "body": m.group(2).strip()})),
        # "volume up/down/mute"
        (r"^(?:volume|vol)\s+(up|down|mute)$",
         lambda m: Action("system_volume", {"level": m.group(1).strip()})),
        # "increase/decrease volume"
        (r"^(?:increase|raise|turn up)\s+(?:the\s+)?volume$",
         lambda m: Action("system_volume", {"level": "up"})),
        (r"^(?:decrease|lower|turn down|reduce)\s+(?:the\s+)?volume$",
         lambda m: Action("system_volume", {"level": "down"})),
        # "mute" standalone
        (r"^mute$",
         lambda m: Action("system_volume", {"level": "mute"})),
        # "set timer X" / "timer X"
        (r"^(?:set\s+(?:a\s+)?)?timer\s+(?:for\s+)?(.+)$",
         lambda m: Action("set_timer", {"duration": m.group(1).strip(), "label": "Timer"})),
        # "remind me in X"
        (r"^remind\s+(?:me\s+)?in\s+(.+?)(?:\s+to\s+(.+))?$",
         lambda m: Action("set_timer", {"duration": m.group(1).strip(), "label": m.group(2).strip() if m.group(2) else "Reminder"})),
    ]

    def process(self, text: str) -> dict:
        """
        Process user input.
        
        Returns:
            {
                "original": original text,
                "cleaned": cleaned text,
                "shortcut_action": Action or None (if shortcut detected),
                "is_exit": bool,
            }
        """
        original = text.strip()

        # Check for exit commands
        if original.lower() in ("exit", "/bye", "quit", "/quit", "/exit", "bye"):
            return {
                "original": original,
                "cleaned": original,
                "shortcut_action": None,
                "is_exit": True,
            }

        # Normalize
        cleaned = self._normalize(original)

        # Try shortcut patterns (bypass LLM for simple commands)
        shortcut = self._detect_shortcut(cleaned)

        return {
            "original": original,
            "cleaned": cleaned,
            "shortcut_action": shortcut,
            "is_exit": False,
        }

    def _normalize(self, text: str) -> str:
        """Normalize whitespace, apply abbreviations."""
        # Lowercase
        result = text.lower().strip()

        # Collapse multiple spaces
        result = re.sub(r"\s+", " ", result)

        # Remove trailing punctuation that doesn't add meaning
        result = result.rstrip("!.")

        # Expand abbreviations (only if they are complete words)
        words = result.split()
        expanded = []
        i = 0
        while i < len(words):
            # Check two-word abbreviations first
            if i + 1 < len(words):
                two_word = f"{words[i]} {words[i + 1]}"
                if two_word in self.ABBREVIATIONS:
                    expanded.append(self.ABBREVIATIONS[two_word])
                    i += 2
                    continue
            # Check single-word abbreviations
            if words[i] in self.ABBREVIATIONS:
                expanded.append(self.ABBREVIATIONS[words[i]])
            else:
                expanded.append(words[i])
            i += 1

        result = " ".join(expanded)

        return result

    def _detect_shortcut(self, text: str) -> Optional[Action]:
        """
        Detect if the input matches a shortcut pattern.
        Returns an Action if matched, None otherwise.
        """
        for pattern, builder in self.SHORTCUT_PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return builder(match)
                except Exception:
                    continue
        return None

    def remove_noise(self, text: str) -> str:
        """Remove noise words from text."""
        result = text.lower()
        for noise in sorted(self.NOISE_WORDS, key=len, reverse=True):
            result = result.replace(noise, "")
        return re.sub(r"\s+", " ", result).strip()
