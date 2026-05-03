# Senku 2.0 - Agent (LLM Caller + Parser)
import json
import re
import requests

SYSTEM_PROMPT = """
You are an action parser. Convert user input to JSON actions only.

RULES:
- Output ONLY valid JSON array
- No explanation
- Use only allowed actions
- If impossible return []

ACTIONS:
open_app, close_app, play_youtube, search_web,
send_message, create_file, get_weather

FORMAT:
[{"action":"type"}]

EXAMPLE:
User: open chrome and play music
[{"action":"open_app","app":"chrome"},{"action":"play_youtube","query":"music"}]

Now parse:
"""


def call_ollama(user_input):
    res = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3",
        "prompt": SYSTEM_PROMPT + user_input,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 300}
    })
    return res.json()["response"]


def parse_actions(user_input):
    raw = call_ollama(user_input)

    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except:
        pass

    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return []
