# Temporary LLM client with smart fallback to parser

from brain.parser import parse


def query_llm(text: str) -> dict:
    print("[LLM] Processing complex command...")

    # TEMP: simulate intelligence by cleaning text
    cleaned = text.lower()

    for word in ["please", "can you", "could you", "would you"]:
        cleaned = cleaned.replace(word, "")

    cleaned = cleaned.strip()

    # fallback to parser
    return parse(cleaned)
