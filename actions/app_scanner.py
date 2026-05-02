# Dynamically scan installed apps on Windows

import os

COMMON_PATHS = [
    "C:\\Program Files",
    "C:\\Program Files (x86)",
]


def scan_apps():
    apps = {}

    for base in COMMON_PATHS:
        if not os.path.exists(base):
            continue

        for root, _, files in os.walk(base):
            for file in files:
                if file.endswith(".exe"):
                    name = file.replace(".exe", "").lower()
                    path = os.path.join(root, file)
                    apps[name] = path

    return apps
