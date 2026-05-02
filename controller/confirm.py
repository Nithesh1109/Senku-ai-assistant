# Handles user confirmation before executing actions

def confirm(intent: str, params: dict) -> bool:
    description = ""

    if intent == "open_app":
        description = f"Open {params.get('app')}?"
    elif intent == "run_file":
        description = f"Run file {params.get('arg')}?"
    elif intent == "type_text":
        description = f"Type '{params.get('arg')}'?"
    else:
        description = "Unknown command. Execute anyway?"

    choice = input(f"{description} (y/n): ").strip().lower()
    return choice == "y"
