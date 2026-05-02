# Opens applications using subprocess

import subprocess
import platform

def open_app(app_name: str):
    system = platform.system()

    try:
        if system == "Windows":
            subprocess.Popen(app_name)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen([app_name])
    except Exception as e:
        print(f"Error opening app: {e}")
