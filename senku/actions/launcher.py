"""
Senku Smart App Launcher
Intelligent multi-strategy app launching with error recovery.
"""

import os
import subprocess
import webbrowser
from typing import Optional

from senku.core.exceptions import AppLaunchError
from senku.config import DEBUG_MODE


class AppLauncher:
    """
    Multi-strategy app launcher with fallback chain.
    
    Launch strategies (in order):
    1. Protocol URI (whatsapp:, spotify:, ms-settings:)
    2. URL (https://...)
    3. Command line (code, notepad, etc.)
    4. Direct executable path
    5. Windows Start Menu search
    6. Subprocess direct launch
    7. Browser search (last resort)
    """

    def launch(self, resolution: dict) -> dict:
        """
        Launch an app based on resolver output.
        
        Args:
            resolution: dict from AppResolver.resolve() with keys:
                - name: app name
                - target: what to launch
                - method: how to launch (protocol, command, url, path, start, search)
                - confidence: resolution confidence
                
        Returns:
            dict with:
                - success: bool
                - method_used: str
                - message: str
                - error: str or None
        """
        name = resolution.get("name", "unknown")
        target = resolution.get("target", name)
        method = resolution.get("method", "start")

        if DEBUG_MODE:
            print(f"[Launcher] Launching '{name}' via {method}: {target}")

        # Route to appropriate launch method
        strategies = {
            "protocol": self._launch_protocol,
            "url": self._launch_url,
            "command": self._launch_command,
            "path": self._launch_path,
            "start": self._launch_start,
            "search": self._launch_search,
        }

        launcher = strategies.get(method, self._launch_start)

        try:
            result = launcher(name, target)
            if result.get("success"):
                return result
        except Exception as e:
            if DEBUG_MODE:
                print(f"[Launcher] {method} failed: {e}")

        # Fallback chain: try other methods
        fallback_order = ["start", "command", "protocol", "search"]
        for fallback in fallback_order:
            if fallback == method:
                continue
            try:
                fb_launcher = strategies.get(fallback)
                if fb_launcher:
                    result = fb_launcher(name, target)
                    if result.get("success"):
                        result["method_used"] = f"fallback({fallback})"
                        return result
            except Exception:
                continue

        return {
            "success": False,
            "method_used": "none",
            "message": f"Could not launch '{name}' — all strategies failed",
            "error": f"No launch method worked for '{name}'",
        }

    def _launch_protocol(self, name: str, target: str) -> dict:
        """Launch via protocol URI (e.g., whatsapp:, spotify:)."""
        try:
            os.system(f'start "" "{target}"')
            return self._success(name, "protocol")
        except Exception as e:
            return self._failure(name, "protocol", str(e))

    def _launch_url(self, name: str, target: str) -> dict:
        """Launch via URL in default browser."""
        try:
            webbrowser.open(target)
            return self._success(name, "url")
        except Exception as e:
            return self._failure(name, "url", str(e))

    def _launch_command(self, name: str, target: str) -> dict:
        """Launch via command line."""
        try:
            subprocess.Popen(
                target,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return self._success(name, "command")
        except FileNotFoundError:
            return self._failure(name, "command", f"Command '{target}' not found")
        except Exception as e:
            return self._failure(name, "command", str(e))

    def _launch_path(self, name: str, target: str) -> dict:
        """Launch via direct executable path."""
        if os.path.exists(target):
            try:
                subprocess.Popen(
                    [target],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return self._success(name, "path")
            except Exception as e:
                return self._failure(name, "path", str(e))
        else:
            # Try as a Start Menu search
            return self._launch_start(name, target)

    def _launch_start(self, name: str, target: str) -> dict:
        """Launch via Windows Start Menu / shell search."""
        try:
            result = os.system(f'start "" "{target}"')
            if result == 0:
                return self._success(name, "start")
            return self._failure(name, "start", f"Exit code {result}")
        except Exception as e:
            return self._failure(name, "start", str(e))

    def _launch_search(self, name: str, target: str) -> dict:
        """Last resort: open browser search for the app."""
        try:
            webbrowser.open(f"https://www.google.com/search?q={target}+download")
            return {
                "success": True,
                "method_used": "search",
                "message": f"'{name}' not found locally — opened browser search",
                "error": None,
            }
        except Exception as e:
            return self._failure(name, "search", str(e))

    @staticmethod
    def _success(name: str, method: str) -> dict:
        return {
            "success": True,
            "method_used": method,
            "message": f"Opened {name}",
            "error": None,
        }

    @staticmethod
    def _failure(name: str, method: str, error: str) -> dict:
        return {
            "success": False,
            "method_used": method,
            "message": f"Failed to open {name} via {method}",
            "error": error,
        }