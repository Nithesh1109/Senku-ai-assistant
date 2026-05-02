# Real LLM client using Ollama with stricter prompt + fallback

import requests
import json
from brain.parser import parse

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"

SYSTEM_PROMPT = """
You are a command parser. Convert user commands into STRICT JSON.
- Output ONLY valid JSON.
- No explanations, no text outside JSON.
- Use one of intents: open_app, run_file, type_text.
- If app is VS Code, return app as 'code'.
- Keep params minimal.
"""


def query_llm(text: str) -> dict:
    print("[LLM] Processing with Ollama...")

    prompt = f"""
{SYSTEM_PROMPT}

Command: "{text}"

Return EXACT JSON like:
{{
  "intent": "open_app|run_file|type_text",
  "params": {{
    "app": "string (only if open_app)",
    "arg": "string (only if needed)"
  }}
}}

Examples:
- open vscode -> {{"intent":"open_app","params":{"app":"code"}}}
- run test.py -> {{"intent":"run_file","params":{"arg":"test.py"}}}
- type hello -> {{"intent":"type_text","params":{"arg":"hello"}}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0}
            }
        )

        output = response.json().get("response", "")

        # Extract JSON safely
        start = output.find("{")
        end = output.rfind("}") + 1

        if start == -1 or end == -1:
            return parse(text)

        json_str = output[start:end]
        result = json.loads(json_str)

        # Fallback safety
        if result.get("intent") == "unknown":
            return parse(text)

        return result

    except Exception as e:
        print("LLM Error:", e)
        return parse(text)
