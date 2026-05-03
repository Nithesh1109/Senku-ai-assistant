# Smart alias mapping (controlled intelligence)

ALIASES = {
    "browser": "chrome",
    "my browser": "chrome",
    "code": "vscode",
    "vs code": "vscode",
    "editor": "vscode",
    "mail": "outlook",
    "email": "outlook",
    "premiere": "adobe premiere pro",
    "photoshop": "adobe photoshop",
    "files": "explorer",
    "file manager": "explorer",
}


def map_app_name(app_name: str) -> str:
    app_name = app_name.lower().strip()

    # exact alias
    if app_name in ALIASES:
        return ALIASES[app_name]

    # partial controlled match
    for key, value in ALIASES.items():
        if key in app_name:
            return value

    return app_name