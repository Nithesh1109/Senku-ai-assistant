from brain.agent import parse_actions
from actions.executor import execute


def main():
    print("🚀 Senku 2.0 Started")

    while True:
        text = input(">> ")

        if text.lower() == "exit":
            break

        actions = parse_actions(text)

        if not actions:
            print("❌ Could not understand")
            continue

        print("🧠 Actions:", actions)
        execute(actions)


if __name__ == "__main__":
    main()
