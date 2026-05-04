import os
import webbrowser
from actions.launcher import open_app as smart_open_app
from actions.resolver import resolve_app, save_alias, load_alias


def execute(actions):
    for act in actions:
        action = act.get("action")

        # 🔥 OPEN APP WITH SMART FALLBACK
        if action == "open_app":
<<<<<<< HEAD
            raw_app = act.get("app")
            app = resolve_app(raw_app)
            smart_open_app(app)

            # 🔥 Ask user once and learn
            if raw_app != app and raw_app not in load_alias():
                user_input = input(f"Should I remember '{raw_app}' as '{app}'? (y/n): ")

                if user_input.lower() == "y":
                    alias_map = load_alias()
                    alias_map[raw_app] = app
                    save_alias(alias_map)
                    print("[Senku] Learned new app mapping!")
=======
            app = act.get("app")

            try:
                result = os.system(f"start {app}")

                if result != 0:
                    raise Exception("App not found")

                print(f"[Senku] Opened {app}")

            except:
                print(f"[Senku] {app} not found locally → opening in browser")

                if app.lower() == "youtube":
                    webbrowser.open("https://www.youtube.com")
                elif app.lower() == "whatsapp":
                    webbrowser.open("https://web.whatsapp.com")
                elif app.lower() == "google":
                    webbrowser.open("https://www.google.com")
                else:
                    webbrowser.open(f"https://www.google.com/search?q={app}")
>>>>>>> 4071a74d2e291b02dff9a0541f6dcb91ab37a4da

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
