# Smarter parser with fuzzy matching and typo handling

import difflib

ALIASES = {
    "vs code": "vscode",
    "vs-code": "vscode",
    "visual studio code": "vscode",
    "browser": "chrome",
    "browers": "chrome",
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


def fuzzy_match(word, choices):
    match = difflib.get_close_matches(word, choices, n=1, cutoff=0.6)
    return match[0] if match else None


def parse(text: str) -> dict:
    text = normalize(text)
    words = text.split()

    # open command (fuzzy)
    if "open" in words:
        for word in words:
            match = fuzzy_match(word, APPS.keys())
            if match:
                return {"intent": "open_app", "params": {"app": APPS[match]}}

    # run command
    if text.startswith("run"):
        return {"intent": "run_file", "params": {"arg": text.replace("run", "").strip()}}

    # type command
    if text.startswith("type"):
        return {"intent": "type_text", "params": {"arg": text.replace("type", "").strip()}}

    return {"intent": "unknown", "params": {}}
