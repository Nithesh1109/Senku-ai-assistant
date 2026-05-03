# Phase 1: Stable Windows launcher (no crashes)

import os
import subprocess
from pathlib import Path

# ✅ Fast alias layer (fix broken apps)
ALIASES = {
    "whatsapp": "shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
    "settings": "ms-settings:",
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
}

# ✅ Start Menu paths
START_MENU_PATHS = [
    Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs",
    Path(os.environ["PROGRAMDATA"]) / "Microsoft/Windows/Start Menu/Programs",
]

def find_in_start_menu(app_name: str):
    app_name = app_name.lower()

    for base in START_MENU_PATHS:
        if not base.exists():
            continue

        for lnk in base.rglob("*.lnk"):
            if app_name in lnk.stem.lower():
                return str(lnk)

    return None

def open_app(app_name: str):
    app_name = app_name.lower().strip()

    # 🔥 1. Alias (fast + reliable)
    if app_name in ALIASES:
        target = ALIASES[app_name]

        if target.startswith("shell:") or target.endswith(":"):
            subprocess.Popen(f"start {target}", shell=True)
        else:
            os.startfile(target)

        return

    # 🔥 2. Start Menu (.lnk)
    lnk_path = find_in_start_menu(app_name)
    if lnk_path:
        os.startfile(lnk_path)
        return

    # 🔥 3. Fallback (basic Windows)
    try:
        subprocess.Popen(f"start {app_name}", shell=True)
        return
    except Exception:
        pass

    print(f"App '{app_name}' not found")
