# Smarter parser with normalization, aliases, and flexible matching

ALIASES = {
    "vs code": "vscode",
    "vs-code": "vscode",
    "visual studio code": "vscode",
}

APPS = {
    "vscode": "code",
    "chrome": "chrome",
    "whatsapp": "whatsapp",
    "terminal": "cmd",
}


def normalize(text: str) -> str:
    text = text.lower().strip()

    for k, v in ALIASES.items():
        text = text.replace(k, v)

    return text


def parse(text: str) -> dict:
    text = normalize(text)

    # open command (flexible)
    if text.startswith("open"):
        for name, app in APPS.items():
            if name in text:
                return {"intent": "open_app", "params": {"app": app}}

    # run command
    if text.startswith("run"):
        return {"intent": "run_file", "params": {"arg": text.replace("run", "").strip()}}

    # type command
    if text.startswith("type"):
        return {"intent": "type_text", "params": {"arg": text.replace("type", "").strip()}}

    return {"intent": "unknown", "params": {}}
