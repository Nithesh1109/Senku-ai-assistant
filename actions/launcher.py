# Opens applications using subprocess (improved Windows handling)

import subprocess
from actions.app_scanner import scan_apps

APPS_CACHE = scan_apps()

def open_app(app_name: str):
    app_name = app_name.lower().strip()

    # exact match
    if app_name in APPS_CACHE:
        subprocess.Popen(APPS_CACHE[app_name])
        return

    # partial match
    for name, path in APPS_CACHE.items():
        if app_name in name:
            subprocess.Popen(path)
            return

    print(f"App '{app_name}' not found")
