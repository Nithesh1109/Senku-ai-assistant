# Opens applications using subprocess (improved Windows handling)

import subprocess
from actions.app_scanner import scan_apps

APPS_CACHE = scan_apps()

BLOCKED_PATHS = ["windowsapps"]

# manual known apps (VERY IMPORTANT)
SPECIAL_APPS = {
    "whatsapp": "start shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
    "calculator": "start calc",
    "notepad": "start notepad",
}

def is_blocked(path: str):
    return "windowsapps" in path.lower()

def open_app(app_name: str):
    app_name = app_name.lower().strip()

    # 1. special apps (highest priority)
    if app_name in SPECIAL_APPS:
        subprocess.Popen(SPECIAL_APPS[app_name], shell=True)
        return

    # 2. dynamic exact match
    if app_name in APPS_CACHE:
        path = APPS_CACHE[app_name]
        if not is_blocked(path):
            subprocess.Popen(path)
            return

    # 3. partial match
    for name, path in APPS_CACHE.items():
        if app_name in name and not is_blocked(path):
            subprocess.Popen(path)
            return

    # 4. fallback (generic)
    try:
        subprocess.Popen(f"start {app_name}", shell=True)
    except Exception as e:
        print(f"Error opening app: {e}")
