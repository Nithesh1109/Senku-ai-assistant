# Routes commands between rule-based parser and LLM (future AI brain)

# For now: simple placeholder logic

def needs_llm(text: str) -> bool:
    text = text.lower()

    # simple heuristic
    complex_keywords = [
        "please", "can you", "do this", "figure out", "automatically"
    ]

    return any(word in text for word in complex_keywords)
