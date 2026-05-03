import os
import webbrowser


def execute(actions):
    for act in actions:
        action = act.get("action")

        # 🔥 OPEN APP WITH SMART FALLBACK
        if action == "open_app":
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
