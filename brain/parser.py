# Smarter parser with normalization and aliases

ALIASES = {
    "vs code": "vscode",
    "vs-code": "vscode",
    "visual studio code": "vscode",
}

COMMANDS = {
    "open vscode": ("open_app", {"app": "code"}),
    "open chrome": ("open_app", {"app": "chrome"}),
    "run": ("run_file", {}),
    "type": ("type_text", {}),
}


def normalize(text: str) -> str:
    text = text.lower().strip()

    for k, v in ALIASES.items():
        text = text.replace(k, v)

    return text


def parse(text: str) -> dict:
    text = normalize(text)

    for trigger, (intent, params) in COMMANDS.items():
        if text.startswith(trigger):
            tail = text[len(trigger):].strip()
            return {"intent": intent, "params": {**params, "arg": tail}}

    return {"intent": "unknown", "params": {}}
