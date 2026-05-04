"""
Senku Response Parser
Extracts structured actions from LLM responses.
Handles malformed JSON, markdown artifacts, and partial responses.

v3.1.1 — Stability hardened:
- Validates every parsed item is a proper action dict
- Rejects chat-like text that accidentally matches JSON patterns
- Debug logging for parsed output inspection
- Never returns non-Action objects
"""

import json
import re
from typing import List
from senku.core.types import Action
from senku.config import ACTION_SCHEMA, DEBUG_MODE


# All known action types for validation
KNOWN_ACTION_TYPES = set(ACTION_SCHEMA.keys())


class ResponseParser:
    """
    Robust parser for LLM action responses.
    
    Handles:
    - Clean JSON arrays
    - JSON wrapped in markdown code blocks
    - Partial JSON with extra text
    - Single action objects (wraps in array)
    - Malformed responses (extracts what it can)
    
    Safety guarantees:
    - Always returns List[Action] or empty list
    - Never raises exceptions
    - Validates every item has a valid "action" key
    """

    def parse_actions(self, raw: str) -> List[Action]:
        """
        Parse LLM response into a list of Action objects.
        
        Returns empty list if no valid actions found (indicates chat mode).
        NEVER raises — always returns a safe result.
        """
        try:
            if not raw or not raw.strip():
                return []

            # Quick check: if the response doesn't contain any action keyword,
            # it's almost certainly chat text — skip expensive parsing
            if not self._could_contain_actions(raw):
                if DEBUG_MODE:
                    print(f"[Parser] No action keywords found — treating as chat")
                return []

            # Clean up the response
            cleaned = self._clean_response(raw)

            # Try parsing as JSON
            actions_data = self._extract_json_array(cleaned)

            if not actions_data:
                if DEBUG_MODE:
                    print(f"[Parser] No JSON extracted from response")
                return []

            # Convert raw dicts to Action objects with validation
            actions = []
            for item in actions_data:
                action = self._safe_build_action(item)
                if action:
                    actions.append(action)

            if DEBUG_MODE:
                print(f"[Parser] DEBUG ACTIONS: {[a.action_type for a in actions]}")

            return actions

        except Exception as e:
            # Parser should NEVER crash the system
            if DEBUG_MODE:
                print(f"[Parser] Unexpected error during parsing: {e}")
            return []

    def _could_contain_actions(self, raw: str) -> bool:
        """
        Quick heuristic check: does this response look like it could
        contain action JSON? This avoids wasting time parsing pure chat text.
        """
        raw_lower = raw.lower()

        # Must contain "action" as a key AND a known action type
        if '"action"' not in raw_lower and "'action'" not in raw_lower:
            return False

        # Check for at least one known action type
        for action_type in KNOWN_ACTION_TYPES:
            if action_type in raw_lower:
                return True

        return False

    def _clean_response(self, raw: str) -> str:
        """Remove markdown artifacts and noise from LLM response."""
        result = raw.strip()

        # Remove markdown code block markers
        result = re.sub(r"```json\s*", "", result)
        result = re.sub(r"```\s*", "", result)

        # Remove leading/trailing prose
        # Look for JSON array boundaries
        first_bracket = result.find("[")
        last_bracket = result.rfind("]")

        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            result = result[first_bracket:last_bracket + 1]

        return result.strip()

    def _extract_json_array(self, text: str) -> list:
        """
        Extract a JSON array from text using multiple strategies.
        Returns list of dicts, or empty list.
        """
        # Strategy 1: Direct parse
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [data]
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: Find JSON array with regex
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 3: Find individual JSON objects
        objects = re.findall(r"\{[^{}]+\}", text)
        if objects:
            results = []
            for obj_str in objects:
                try:
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict):
                        results.append(obj)
                except (json.JSONDecodeError, ValueError):
                    continue
            if results:
                return results

        # Strategy 4: Try to fix common JSON issues
        fixed = self._fix_json(text)
        if fixed:
            try:
                data = json.loads(fixed)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
            except (json.JSONDecodeError, ValueError):
                pass

        return []

    def _fix_json(self, text: str) -> str:
        """Attempt to fix common JSON formatting issues."""
        result = text.strip()

        # Fix single quotes → double quotes
        result = result.replace("'", '"')

        # Fix trailing commas before closing brackets
        result = re.sub(r",\s*\]", "]", result)
        result = re.sub(r",\s*\}", "}", result)

        # Ensure array wrapping
        if result.startswith("{"):
            result = "[" + result + "]"

        return result

    def _safe_build_action(self, item) -> Action:
        """
        Safely build an Action from any parsed item.
        Returns None if the item is not a valid action.
        
        This is the critical validation gate — nothing invalid
        gets past this function.
        """
        try:
            # Must be a dict
            if not isinstance(item, dict):
                if DEBUG_MODE:
                    print(f"[Parser] Rejected non-dict item: {type(item)}")
                return None

            # Must have "action" key with a non-empty string value
            action_type = item.get("action")
            if not action_type or not isinstance(action_type, str):
                if DEBUG_MODE:
                    print(f"[Parser] Rejected item without valid 'action' key: {item}")
                return None

            action_type = action_type.strip()
            if not action_type:
                return None

            # Extract parameters (everything except 'action')
            params = {}
            for k, v in item.items():
                if k == "action":
                    continue
                # Ensure all param values are safe types
                if isinstance(v, (str, int, float, bool)):
                    params[k] = v
                elif isinstance(v, (list, dict)):
                    params[k] = v
                elif v is None:
                    params[k] = ""
                else:
                    params[k] = str(v)

            # Validate against schema if available — fill missing required params
            if action_type in ACTION_SCHEMA:
                schema = ACTION_SCHEMA[action_type]
                required = schema.get("required", [])
                missing = [p for p in required if p not in params or not params[p]]

                if missing and DEBUG_MODE:
                    print(f"[Parser] Warning: {action_type} missing params: {missing}")

                # Fill defaults for missing params
                for param in missing:
                    if param not in params:
                        params[param] = ""

            return Action(
                action_type=action_type,
                params=params,
                confidence=0.9,
                source="llm",
            )

        except Exception as e:
            if DEBUG_MODE:
                print(f"[Parser] Error building action from {item}: {e}")
            return None
