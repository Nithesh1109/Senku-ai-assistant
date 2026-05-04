"""
Senku System Handlers
Handles system-level actions: screenshot, volume, timer, shell commands.
"""

import os
import time
import subprocess
import threading

from senku.core.types import Action, ActionResult, ActionStatus
from senku.actions.registry import registry


@registry.register("screenshot", "Takes a screenshot")
def handle_screenshot(action: Action) -> ActionResult:
    """Take a screenshot using the system snipping tool."""
    start_time = time.time()

    try:
        # Use Windows Snipping Tool / Snip & Sketch
        # Try modern Snip & Sketch first, fall back to snippingtool
        try:
            subprocess.Popen(["explorer", "ms-screenclip:"])
        except Exception:
            os.system("snippingtool")

        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.SUCCESS,
            message="Screenshot tool launched",
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="Failed to take screenshot",
            error=str(e),
            duration_ms=duration,
        )


@registry.register("system_volume", "Controls system volume")
def handle_system_volume(action: Action) -> ActionResult:
    """Control system volume using nircmd or PowerShell."""
    level = action.get_param("level", "")
    if not level:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No volume level specified",
            error="Missing 'level' parameter (use: up, down, mute, or 0-100)",
        )

    start_time = time.time()

    try:
        level_lower = str(level).lower().strip()

        if level_lower == "mute":
            # Toggle mute via PowerShell + audio cmdlet
            ps_cmd = (
                'powershell -Command "'
                '$audio = New-Object -ComObject WScript.Shell; '
                '$audio.SendKeys([char]173)"'
            )
            os.system(ps_cmd)
            msg = "Toggled mute"

        elif level_lower == "up":
            # Volume up
            ps_cmd = (
                'powershell -Command "'
                '$audio = New-Object -ComObject WScript.Shell; '
                '$audio.SendKeys([char]175)"'
            )
            for _ in range(5):  # Press 5 times for noticeable change
                os.system(ps_cmd)
            msg = "Volume up"

        elif level_lower == "down":
            ps_cmd = (
                'powershell -Command "'
                '$audio = New-Object -ComObject WScript.Shell; '
                '$audio.SendKeys([char]174)"'
            )
            for _ in range(5):
                os.system(ps_cmd)
            msg = "Volume down"

        else:
            # Try to parse as a number (0-100)
            try:
                vol = int(level_lower)
                vol = max(0, min(100, vol))
                # Use PowerShell to set volume
                ps_cmd = (
                    f'powershell -Command "'
                    f'Set-AudioDevice -PlaybackVolume {vol}"'
                )
                result = os.system(ps_cmd)
                if result != 0:
                    # Fallback message
                    msg = f"Volume control attempted (level: {vol}%)"
                else:
                    msg = f"Volume set to {vol}%"
            except ValueError:
                return ActionResult(
                    action=action,
                    status=ActionStatus.FAILED,
                    message=f"Invalid volume level: {level}",
                    error="Use: up, down, mute, or 0-100",
                )

        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.SUCCESS,
            message=msg,
            duration_ms=duration,
        )

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="Volume control failed",
            error=str(e),
            duration_ms=duration,
        )


@registry.register("set_timer", "Sets a timer with notification")
def handle_set_timer(action: Action) -> ActionResult:
    """Set a timer that notifies when complete."""
    duration_str = action.get_param("duration", "")
    label = action.get_param("label", "Timer")

    if not duration_str:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No duration specified",
            error="Missing 'duration' parameter (e.g., '5m', '30s', '1h')",
        )

    # Parse duration string
    seconds = _parse_duration(str(duration_str))
    if seconds is None:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Invalid duration format: {duration_str}",
            error="Use format: 5m, 30s, 1h, or just seconds",
        )

    start_time = time.time()

    # Run timer in background thread
    def timer_callback():
        time.sleep(seconds)
        # Notify user
        try:
            # Windows toast notification
            ps_cmd = (
                f'powershell -Command "'
                f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                f"[System.Windows.Forms.MessageBox]::Show('{label}: Time is up!', 'Senku Timer')"
                f'"'
            )
            os.system(ps_cmd)
        except Exception:
            print(f"\n⏰ TIMER: {label} — Time's up! ({duration_str})")

    thread = threading.Thread(target=timer_callback, daemon=True)
    thread.start()

    duration_ms = (time.time() - start_time) * 1000
    minutes = seconds / 60

    if minutes >= 1:
        msg = f"Timer set: {label} — {minutes:.0f} minute(s)"
    else:
        msg = f"Timer set: {label} — {seconds} second(s)"

    return ActionResult(
        action=action,
        status=ActionStatus.SUCCESS,
        message=msg,
        duration_ms=duration_ms,
        metadata={"seconds": seconds, "label": label},
    )


@registry.register("run_command", "Runs a shell command")
def handle_run_command(action: Action) -> ActionResult:
    """Run a shell command and return the output."""
    command = action.get_param("command", "")

    if not command:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No command provided",
            error="Missing 'command' parameter",
        )

    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        duration = (time.time() - start_time) * 1000
        output = result.stdout.strip() or result.stderr.strip()

        if result.returncode == 0:
            return ActionResult(
                action=action,
                status=ActionStatus.SUCCESS,
                message=f"Command executed: {command}",
                duration_ms=duration,
                metadata={"output": output[:500], "exit_code": 0},
            )
        else:
            return ActionResult(
                action=action,
                status=ActionStatus.FAILED,
                message=f"Command failed with code {result.returncode}",
                error=output[:200],
                duration_ms=duration,
            )

    except subprocess.TimeoutExpired:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="Command timed out (30s limit)",
            error="Timeout",
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Command error",
            error=str(e),
            duration_ms=duration,
        )


def _parse_duration(s: str) -> int | None:
    """Parse a duration string into seconds."""
    s = s.strip().lower()

    # Pure number → assume seconds
    try:
        return int(s)
    except ValueError:
        pass

    # Parse formatted duration
    import re
    match = re.match(r"^(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hr|hours?)$", s)
    if match:
        value = int(match.group(1))
        unit = match.group(2)[0]
        if unit == "s":
            return value
        elif unit == "m":
            return value * 60
        elif unit == "h":
            return value * 3600

    return None
