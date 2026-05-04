from brain.agent import parse_actions, call_ollama
from actions.executor import execute


def main():
    print("🚀 Senku 2.0 Started")

    while True:
        text = input(">> ")

        if text.lower() in ["exit", "/bye"]:
            break

        # 🔥 Try action first
        actions = parse_actions(text)

        if actions:
            print("🧠 Actions:", actions)
            execute(actions)
        else:
            # 🔥 fallback to chat
            print("💬 Thinking...")
            response = call_ollama(text, mode="chat")
            print(response)


if __name__ == "__main__":
    main()
