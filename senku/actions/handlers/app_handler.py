"""
Senku App Handlers
Handles open_app and close_app actions.
"""

import os
import time

from senku.core.types import Action, ActionResult, ActionStatus
from senku.actions.registry import registry
from senku.actions.launcher import AppLauncher
from senku.resolver.app_resolver import AppResolver


# Shared instances
_resolver = AppResolver()
_launcher = AppLauncher()


@registry.register("open_app", "Opens an application")
def handle_open_app(action: Action) -> ActionResult:
    """Open an application using the multi-strategy resolver + launcher."""
    app_name = action.get_param("app", "")
    if not app_name:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No app name provided",
            error="Missing 'app' parameter",
        )

    start_time = time.time()

    # Resolve the app name
    resolution = _resolver.resolve(app_name)

    # Launch the app
    result = _launcher.launch(resolution)
    duration = (time.time() - start_time) * 1000

    if result["success"]:
        return ActionResult(
            action=action,
            status=ActionStatus.SUCCESS,
            message=result["message"],
            duration_ms=duration,
            metadata={
                "resolved_to": resolution["target"],
                "method": result["method_used"],
                "confidence": resolution["confidence"],
                "source": resolution["source"],
            },
        )
    else:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=result["message"],
            error=result.get("error", "Unknown launch error"),
            duration_ms=duration,
        )


@registry.register("close_app", "Closes a running application")
def handle_close_app(action: Action) -> ActionResult:
    """Close a running application."""
    app_name = action.get_param("app", "")
    if not app_name:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No app name provided",
            error="Missing 'app' parameter",
        )

    start_time = time.time()

    # Try to kill the process
    try:
        # Try common executable names
        exe_names = [
            f"{app_name}.exe",
            f"{app_name}",
        ]

        # Handle common aliases
        close_map = {
            "chrome": "chrome.exe",
            "vscode": "Code.exe",
            "vs code": "Code.exe",
            "notepad": "notepad.exe",
            "spotify": "Spotify.exe",
            "whatsapp": "WhatsApp.exe",
            "discord": "Discord.exe",
            "slack": "slack.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "explorer": "explorer.exe",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE",
        }

        target = close_map.get(app_name.lower(), f"{app_name}.exe")
        result = os.system(f'taskkill /IM "{target}" /F 2>nul')
        duration = (time.time() - start_time) * 1000

        if result == 0:
            return ActionResult(
                action=action,
                status=ActionStatus.SUCCESS,
                message=f"Closed {app_name}",
                duration_ms=duration,
            )
        else:
            return ActionResult(
                action=action,
                status=ActionStatus.FAILED,
                message=f"Could not close {app_name} — it may not be running",
                error=f"taskkill returned code {result}",
                duration_ms=duration,
            )

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Error closing {app_name}",
            error=str(e),
            duration_ms=duration,
        )


def get_resolver() -> AppResolver:
    """Get the shared AppResolver instance (for alias learning)."""
    return _resolver
