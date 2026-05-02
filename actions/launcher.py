# Opens applications using subprocess (improved Windows handling)

import subprocess
import platform

# Map common app names to actual system commands
APP_ALIASES = {
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "whatsapp": "start whatsapp",
}


def open_app(app_name: str):
    system = platform.system()

    # normalize app name
    app_name = app_name.lower().strip()
    command = APP_ALIASES.get(app_name, app_name)

    try:
        if system == "Windows":
            subprocess.Popen(command, shell=True)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", command])
        else:
            subprocess.Popen([command])
    except Exception as e:
        print(f"Error opening app: {e}")
