# Parses user commands into structured intents

COMMANDS = {
    "open vscode": ("open_app", {"app": "code"}),
    "open chrome": ("open_app", {"app": "chrome"}),
    "run": ("run_file", {}),
    "type": ("type_text", {}),
}

def parse(text: str) -> dict:
    text = text.lower().strip()
    for trigger, (intent, params) in COMMANDS.items():
        if text.startswith(trigger):
            tail = text[len(trigger):].strip()
            return {"intent": intent, "params": {**params, "arg": tail}}
    return {"intent": "unknown", "params": {}}
