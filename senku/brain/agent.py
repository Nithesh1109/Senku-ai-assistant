# Senku 2.0 - Agent (LLM Caller + Parser)
import json
import re
import requests

SYSTEM_PROMPT = """
You are Senku, an AI assistant that controls the user's laptop.

Your job is to convert user input into JSON actions.

RULES:
- Output ONLY valid JSON array
- No text, no explanation
- If user wants something → give action
- If user is just talking → return []

ACTIONS:
open_app, close_app, play_youtube, search_web,
set_timer, send_message, create_file,
get_weather, system_volume, screenshot

EXAMPLES:

User: open chrome
[{"action": "open_app", "app": "chrome"}]

User: can you open whatsapp
[{"action": "open_app", "app": "whatsapp"}]

User: play leo song
[{"action": "play_youtube", "query": "leo song"}]

User: hello
[]

Now parse:
"""

CHAT_PROMPT = """
You are Senku, an AI assistant inside the user's laptop.

Talk naturally like a smart assistant.
Keep responses short and helpful.
"""


def call_ollama(user_input, mode="action"):
    try:
        if mode == "action":
            prompt = SYSTEM_PROMPT + user_input
        else:
            prompt = CHAT_PROMPT + user_input

        res = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 300}
        })

        data = res.json()

        # 🔥 Safe handling
        if isinstance(data, dict) and "response" in data:
            return data["response"]

        return str(data)

    except Exception as e:
        return f"ERROR: {str(e)}"


def parse_actions(user_input):
    raw = call_ollama(user_input, mode="action")

    if raw.startswith("ERROR"):
        return []

    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        data = json.loads(raw)
        if isinstance(data, list) and len(data) > 0:
            return data
    except:
        pass

    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list) and len(data) > 0:
                return data
        except:
            pass

    return []
