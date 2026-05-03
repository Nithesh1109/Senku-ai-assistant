import json
import os

CONTEXT_FILE = "context.json"


def load_context():
    if os.path.exists(CONTEXT_FILE):
        with open(CONTEXT_FILE, "r") as f:
            return json.load(f)
    return {}


def save_context(data):
    with open(CONTEXT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def set_last_app(app: str):
    context = load_context()
    context["last_app"] = app
    save_context(context)


def get_last_app():
    context = load_context()
    return context.get("last_app")