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
    return memory.get(query.lower())


def learn_app(query: str, app: str):
    memory = load_memory()
    memory[query.lower()] = app.lower()
    save_memory(memory)
