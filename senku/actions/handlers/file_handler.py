"""
Senku File Handlers
Handles file and folder operations.
"""

import os
import time
import subprocess
from pathlib import Path

from senku.core.types import Action, ActionResult, ActionStatus
from senku.actions.registry import registry


@registry.register("create_file", "Creates a new file")
def handle_create_file(action: Action) -> ActionResult:
    """Create a new file with optional content."""
    name = action.get_param("name", "")
    content = action.get_param("content", "")
    file_path = action.get_param("path", "")

    if not name:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No filename provided",
            error="Missing 'name' parameter",
        )

    start_time = time.time()

    try:
        # Determine full path
        if file_path:
            full_path = Path(file_path) / name
        else:
            # Default to user's Desktop
            desktop = Path.home() / "Desktop"
            if desktop.exists():
                full_path = desktop / name
            else:
                full_path = Path.cwd() / name

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.SUCCESS,
            message=f"Created file: {full_path}",
            duration_ms=duration,
            metadata={"path": str(full_path)},
        )

    except PermissionError:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Permission denied creating {name}",
            error="Permission denied",
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Failed to create {name}",
            error=str(e),
            duration_ms=duration,
        )


@registry.register("open_file", "Opens a file with its default application")
def handle_open_file(action: Action) -> ActionResult:
    """Open a file with its default system application."""
    file_path = action.get_param("path", "")

    if not file_path:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No file path provided",
            error="Missing 'path' parameter",
        )

    start_time = time.time()

    try:
        path = Path(file_path).expanduser()

        if not path.exists():
            # Try common locations
            for base in [Path.home() / "Desktop", Path.home() / "Documents", Path.cwd()]:
                candidate = base / file_path
                if candidate.exists():
                    path = candidate
                    break

        if path.exists():
            os.startfile(str(path))
            duration = (time.time() - start_time) * 1000
            return ActionResult(
                action=action,
                status=ActionStatus.SUCCESS,
                message=f"Opened {path.name}",
                duration_ms=duration,
            )
        else:
            duration = (time.time() - start_time) * 1000
            return ActionResult(
                action=action,
                status=ActionStatus.FAILED,
                message=f"File not found: {file_path}",
                error="File does not exist",
                duration_ms=duration,
            )

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Failed to open file",
            error=str(e),
            duration_ms=duration,
        )


@registry.register("open_folder", "Opens a folder in File Explorer")
def handle_open_folder(action: Action) -> ActionResult:
    """Open a folder in the file explorer."""
    folder_path = action.get_param("path", "")

    if not folder_path:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No folder path provided",
            error="Missing 'path' parameter",
        )

    start_time = time.time()

    try:
        # Handle common folder names
        folder_aliases = {
            "desktop": str(Path.home() / "Desktop"),
            "documents": str(Path.home() / "Documents"),
            "downloads": str(Path.home() / "Downloads"),
            "pictures": str(Path.home() / "Pictures"),
            "music": str(Path.home() / "Music"),
            "videos": str(Path.home() / "Videos"),
            "home": str(Path.home()),
        }

        resolved = folder_aliases.get(folder_path.lower(), folder_path)
        path = Path(resolved).expanduser()

        if path.exists() and path.is_dir():
            subprocess.Popen(["explorer", str(path)])
            duration = (time.time() - start_time) * 1000
            return ActionResult(
                action=action,
                status=ActionStatus.SUCCESS,
                message=f"Opened folder: {path}",
                duration_ms=duration,
            )
        else:
            duration = (time.time() - start_time) * 1000
            return ActionResult(
                action=action,
                status=ActionStatus.FAILED,
                message=f"Folder not found: {folder_path}",
                error="Directory does not exist",
                duration_ms=duration,
            )

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Failed to open folder",
            error=str(e),
            duration_ms=duration,
        )
