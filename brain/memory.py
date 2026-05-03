# Simple learning memory system (Phase 2.5)

import json
import os

MEMORY_FILE = "memory.json"


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def get_learned_app(query: str):
    memory = load_memory()
    data = memory.get(query.lower())

    if data:
        return data["app"]

    return None


def learn_app(query: str, app: str):
    memory = load_memory()

    query = query.lower()
    app = app.lower()

    if query not in memory:
        memory[query] = {"app": app, "count": 1}
    else:
        memory[query]["count"] += 1
        memory[query]["app"] = app

    save_memory(memory)
