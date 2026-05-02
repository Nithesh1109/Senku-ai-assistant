# Dynamically scan installed apps on Windows

import os

COMMON_PATHS = [
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    os.path.expanduser("~\\AppData\\Local"),
    os.path.expanduser("~\\AppData\\Roaming"),
]

START_MENU = [
    "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
    os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs"),
]


def scan_apps():
    apps = {}

    for base in COMMON_PATHS:
        if not os.path.exists(base):
            continue

        for root, dirs, files in os.walk(base):
            # limit depth (very important)
            if root.count("\\") > 6:
                continue

            for file in files:
                if file.endswith(".exe"):
                    name = file.replace(".exe", "").lower()
                    path = os.path.join(root, file)
                    apps[name] = path

    for base in START_MENU:
        if not os.path.exists(base):
            continue

        for root, _, files in os.walk(base):
            for file in files:
                if file.endswith(".lnk"):
                    name = file.replace(".lnk", "").lower()
                    path = os.path.join(root, file)
                    apps[name] = path

    return apps
