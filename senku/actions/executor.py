import os
import webbrowser


def execute(actions):
    for act in actions:
        action = act.get("action")

        if action == "open_app":
            app = act.get("app")
            os.system(f"start {app}")

        elif action == "close_app":
            app = act.get("app")
            os.system(f"taskkill /IM {app}.exe /F")

        elif action == "play_youtube":
            query = act.get("query")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")

        elif action == "search_web":
            query = act.get("query")
            webbrowser.open(f"https://www.google.com/search?q={query}")

        elif action == "send_message":
            to = act.get("to")
            body = act.get("body")
            webbrowser.open(f"https://wa.me/{to}?text={body}")

        elif action == "create_file":
            name = act.get("name")
            content = act.get("content", "")
            with open(name, "w") as f:
                f.write(content)

        elif action == "get_weather":
            city = act.get("city", "")
            webbrowser.open(f"https://www.google.com/search?q=weather+{city}")

        elif action == "system_volume":
            print("Volume control not implemented yet")

        elif action == "screenshot":
            os.system("snippingtool")

        else:
            print("Unknown action:", action)
