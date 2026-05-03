# Entry point for Senku AI Assistant

from brain.parser import parse
from brain.llm_router import needs_llm
from brain.llm_client import query_llm
from brain.memory import get_learned_app, learn_app
from brain.context import get_last_app, set_last_app

from controller.confirm import confirm

from actions.launcher import open_app
from actions.runner import run_python
from actions.typer import type_text

from voice.stt import listen
from voice.tts import speak


def execute(intent, params):
    if intent == "open_app":
        open_app(params.get("app"))
    elif intent == "run_file":
        run_python(params.get("arg"))
    elif intent == "type_text":
        type_text(params.get("arg"))
    else:
        print("Unknown command")


def main():
    print("Senku v1.0 Started")

    while True:
        mode = input("Choose input (text/voice/exit): ").strip().lower()

        if mode == "exit":
            break

        if mode == "voice":
            text = listen()
            if not text:
                continue
        else:
            text = input(">> ")

        # routing logic
        command = parse(text)

        # check memory before execution
        learned = get_learned_app(text)
        if learned:
            command["intent"] = "open_app"
            command["params"]["app"] = learned

        if command["intent"] == "unknown":
            command = query_llm(text)

        intent = command["intent"]
        params = command["params"]

        # Use context BEFORE execution
        if command["intent"] == "open_app":
            app = command["params"].get("app")

            # if vague command → use context
            if app in ["browser", "app", "something"]:
                last = get_last_app()
                if last:
                    command["params"]["app"] = last

        if intent == "unknown":
            print("I didn't understand that.")
            continue

        if confirm(intent, params):
            execute(intent, params)

            # 🔥 learn mapping
            if intent == "open_app":
                learn_app(text, params.get("app"))
                set_last_app(params.get("app"))

            print(f"[Senku] Opened {params.get('app')}")
        else:
            print("Cancelled")


if __name__ == "__main__":
    main()
