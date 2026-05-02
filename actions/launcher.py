# Opens applications using subprocess (improved Windows handling)

import subprocess
from actions.app_scanner import scan_apps

APPS_CACHE = scan_apps()

BLOCKED_KEYWORDS = ["windowsapps", "pythonsoftwarefoundation"]

def is_valid_exe(path: str):
    path = path.lower()
    return (
        path.endswith(".exe")
        and not any(b in path for b in BLOCKED_KEYWORDS)
    )

def open_app(app_name: str):
    app_name = app_name.lower().strip()

    # ✅ 1. SAFE exact match only
    if app_name in APPS_CACHE:
        path = APPS_CACHE[app_name]
        if is_valid_exe(path):
            subprocess.Popen(path)
            return

    # ❌ REMOVE dangerous loose matching
    # (this was causing your crashes)

    # ✅ 2. Controlled fallback (Windows commands)
    try:
        subprocess.Popen(f"start {app_name}", shell=True)
        return
    except Exception:
        pass

    print(f"App '{app_name}' not found")
