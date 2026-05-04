import json
import os
from difflib import get_close_matches

ALIAS_FILE = "senku/data/alias_map.json"

# Known apps (expand later)
KNOWN_APPS = [
    "chrome", "whatsapp", "spotify",
    "vscode", "code", "notepad",
    "calculator", "settings"
]


def load_alias():
    if not os.path.exists(ALIAS_FILE):
        return {}
    with open(ALIAS_FILE, "r") as f:
        return json.load(f)


def save_alias(alias_map):
    os.makedirs(os.path.dirname(ALIAS_FILE), exist_ok=True)
    with open(ALIAS_FILE, "w") as f:
        json.dump(alias_map, f, indent=2)


def resolve_app(app_name):
    app = app_name.lower()
    alias_map = load_alias()

    # 🔥 1. Check alias memory
    if app in alias_map:
        return alias_map[app]

    # 🔥 2. Exact match
    if app in KNOWN_APPS:
        return app

    # 🔥 3. Fuzzy match
    match = get_close_matches(app, KNOWN_APPS, n=1, cutoff=0.6)
    if match:
        return match[0]

    # 🔥 4. Unknown → return original
    return app