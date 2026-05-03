import json
import os
from actions.app_scanner import scan_apps

CACHE_FILE = "app_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return None

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_apps():
    cache = load_cache()
    if cache:
        return cache

    apps = scan_apps()
    save_cache(apps)
    return apps