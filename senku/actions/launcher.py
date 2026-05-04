import os
import subprocess
import webbrowser

# 🔥 Common app mappings
APP_MAP = {
    "whatsapp": "whatsapp:",
    "youtube": "https://www.youtube.com",
    "spotify": "spotify:",
    "outlook": "outlook:",
    "settings": "ms-settings:",
    "vscode": "code",
    "vs code": "code",
    "code": "code"
}


def open_app(app_name):
    app = app_name.lower()

    # 🔥 1. Special mappings (URLs / protocols)
    if app in APP_MAP:
        target = APP_MAP[app]

        try:
            if target.startswith("http"):
                webbrowser.open(target)
            else:
                os.system(f"start {target}")

            print(f"[Senku] Opened {app} (mapped)")
            return
        except:
            pass

    # 🔥 2. Try Start Menu / System search
    try:
        result = os.system(f'start "" "{app}"')
        if result == 0:
            print(f"[Senku] Opened {app} (start menu / system)")
            return
    except:
        pass

    # 🔥 3. Try direct launch
    try:
        subprocess.Popen(app)
        print(f"[Senku] Opened {app}")
        return
    except:
        pass

    # 🔥 4. Fallback → browser search
    print(f"[Senku] {app} not found locally → opening in browser")
    webbrowser.open(f"https://www.google.com/search?q={app}")