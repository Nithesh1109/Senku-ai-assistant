# Real LLM client using Ollama with fallback safety

import requests
import json
from brain.parser import parse

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"

def query_llm(text: str) -> dict:
    print("[LLM] Processing with Ollama...")

    prompt = f"""
Convert this command into JSON.

Command: "{text}"

Return ONLY JSON in this format:
{{
  "intent": "...",
  "params": {{
    "app": "...",
    "arg": "..."
  }}
}}

Examples:
- "open vscode" → {{ "intent": "open_app", "params": {{ "app": "code" }} }}
- "run test.py" → {{ "intent": "run_file", "params": {{ "arg": "test.py" }} }}
- "type hello" → {{ "intent": "type_text", "params": {{ "arg": "hello" }} }}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
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

        # fallback if LLM fails
        if result.get("intent") == "unknown":
            return parse(text)

        return result

    except Exception as e:
        print("LLM Error:", e)
        return parse(text)
