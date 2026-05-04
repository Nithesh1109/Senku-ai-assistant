"""
Senku Web Handlers
Handles web-related actions: search, youtube, messaging, weather, URLs.

v3.2 — WhatsApp upgrade:
- Contact name resolution (contacts.json)
- Auto-send via keyboard simulation (ctypes on Windows)
- Real message delivery, not just URL opening
"""

import json
import time
import threading
import webbrowser
import ctypes
from urllib.parse import quote_plus
from pathlib import Path

from senku.core.types import Action, ActionResult, ActionStatus
from senku.actions.registry import registry
from senku.config import CONTACTS_FILE, WHATSAPP_SEND_DELAY, DEBUG_MODE


# ─── Contact Resolution ──────────────────────────────────────────

def _load_contacts() -> dict:
    """Load contacts from contacts.json."""
    try:
        if CONTACTS_FILE.exists():
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter out help keys and empty values
            return {
                k.lower(): v for k, v in data.items()
                if k != "_help" and isinstance(v, str) and v.strip()
            }
    except Exception:
        pass
    return {}


def _resolve_contact(name: str) -> dict:
    """
    Resolve a contact name to a phone number.

    Returns:
        {"phone": "919876543210", "name": "amma", "resolved": True}
        or
        {"phone": "", "name": "amma", "resolved": False, "error": "..."}
    """
    contacts = _load_contacts()
    name_lower = name.lower().strip()

    # Direct match
    if name_lower in contacts:
        return {"phone": contacts[name_lower], "name": name, "resolved": True}

    # Fuzzy match (substring)
    for key, phone in contacts.items():
        if name_lower in key or key in name_lower:
            return {"phone": phone, "name": name, "resolved": True}

    # If it looks like a phone number already (digits only), use it directly
    digits = name.replace(" ", "").replace("-", "").replace("+", "")
    if digits.isdigit() and len(digits) >= 10:
        return {"phone": digits, "name": name, "resolved": True}

    return {
        "phone": "",
        "name": name,
        "resolved": False,
        "error": f"Contact '{name}' not found. Add it to senku/data/contacts.json",
    }


def _auto_send_enter(delay: int):
    """
    After a delay, simulate pressing Enter to send the WhatsApp message.
    Uses Windows ctypes — no external dependencies needed.
    """
    try:
        time.sleep(delay)

        VK_RETURN = 0x0D
        KEYEVENTF_KEYUP = 0x0002

        # Press Enter
        ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)

        if DEBUG_MODE:
            print(f"[WhatsApp] Auto-send Enter pressed after {delay}s delay")
    except Exception as e:
        if DEBUG_MODE:
            print(f"[WhatsApp] Auto-send failed: {e}")


def save_contact(name: str, phone: str):
    """Save a new contact to contacts.json for future use."""
    try:
        contacts = {}
        if CONTACTS_FILE.exists():
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                contacts = json.load(f)

        contacts[name.lower()] = phone

        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=4, ensure_ascii=False)

        if DEBUG_MODE:
            print(f"[Contacts] Saved: {name} -> {phone}")
    except Exception as e:
        if DEBUG_MODE:
            print(f"[Contacts] Save failed: {e}")


# ─── Handlers ────────────────────────────────────────────────────

@registry.register("search_web", "Searches the web using Google")
def handle_search_web(action: Action) -> ActionResult:
    """Search the web using Google."""
    query = action.get_param("query", "")
    if not query:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No search query provided",
            error="Missing 'query' parameter",
        )

    start_time = time.time()
    engine = action.get_param("engine", "google")

    search_urls = {
        "google": f"https://www.google.com/search?q={quote_plus(query)}",
        "bing": f"https://www.bing.com/search?q={quote_plus(query)}",
        "duckduckgo": f"https://duckduckgo.com/?q={quote_plus(query)}",
    }

    url = search_urls.get(engine, search_urls["google"])

    try:
        webbrowser.open(url)
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.SUCCESS,
            message=f"Searching for: {query}",
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Failed to search for: {query}",
            error=str(e),
            duration_ms=duration,
        )


@registry.register("play_youtube", "Plays/searches content on YouTube")
def handle_play_youtube(action: Action) -> ActionResult:
    """Search and play on YouTube."""
    query = action.get_param("query", "")
    if not query:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No search query provided",
            error="Missing 'query' parameter",
        )

    start_time = time.time()
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"

    try:
        webbrowser.open(url)
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.SUCCESS,
            message=f"Playing on YouTube: {query}",
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Failed to play: {query}",
            error=str(e),
            duration_ms=duration,
        )


@registry.register("send_message", "Sends a message via WhatsApp Web (auto-send)")
def handle_send_message(action: Action) -> ActionResult:
    """
    Send a message via WhatsApp Web with AUTO-SEND.

    Flow:
    1. Resolve contact name → phone number (via contacts.json)
    2. Open WhatsApp Web with message pre-filled
    3. Wait for page to load
    4. Simulate Enter key press to send

    Requirements:
    - WhatsApp Web must be logged in on default browser
    - Contact must be in contacts.json OR be a phone number
    """
    to = action.get_param("to", "")
    body = action.get_param("body", "")

    if not to:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No recipient specified",
            error="Missing 'to' parameter",
        )

    if not body:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No message body provided",
            error="Missing 'body' parameter. What should I send?",
        )

    start_time = time.time()

    # ─── Step 1: Resolve contact ─────────────────────────────
    contact = _resolve_contact(to)

    if not contact["resolved"]:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Contact '{to}' not found",
            error=contact.get("error", f"Add '{to}' to senku/data/contacts.json with their phone number"),
            duration_ms=(time.time() - start_time) * 1000,
        )

    phone = contact["phone"]

    # ─── Step 2: Open WhatsApp Web with message ──────────────
    try:
        # Use web.whatsapp.com/send for direct chat + message pre-fill
        url = f"https://web.whatsapp.com/send?phone={phone}&text={quote_plus(body)}"
        webbrowser.open(url)

        if DEBUG_MODE:
            print(f"[WhatsApp] Opened: {url}")

        # ─── Step 3: Auto-send after delay ───────────────────
        # Launch background thread to press Enter after WhatsApp loads
        send_thread = threading.Thread(
            target=_auto_send_enter,
            args=(WHATSAPP_SEND_DELAY,),
            daemon=True,
        )
        send_thread.start()

        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.SUCCESS,
            message=f"Message sent to {to}: \"{body}\" (auto-sending in {WHATSAPP_SEND_DELAY}s)",
            duration_ms=duration,
            metadata={
                "recipient": to,
                "phone": phone,
                "body": body,
                "auto_send": True,
                "send_delay": WHATSAPP_SEND_DELAY,
            },
        )

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Failed to send message to {to}",
            error=str(e),
            duration_ms=duration,
        )


@registry.register("get_weather", "Shows weather information")
def handle_get_weather(action: Action) -> ActionResult:
    """Get weather info by opening Google weather search."""
    city = action.get_param("city", "")
    start_time = time.time()

    query = f"weather {city}" if city else "weather"
    url = f"https://www.google.com/search?q={quote_plus(query)}"

    try:
        webbrowser.open(url)
        duration = (time.time() - start_time) * 1000
        msg = f"Weather for {city}" if city else "Current weather"
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
            message="Failed to get weather",
            error=str(e),
            duration_ms=duration,
        )


@registry.register("open_url", "Opens a URL in the browser")
def handle_open_url(action: Action) -> ActionResult:
    """Open a URL directly in the browser."""
    url = action.get_param("url", "")
    if not url:
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message="No URL provided",
            error="Missing 'url' parameter",
        )

    start_time = time.time()

    # Ensure URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        webbrowser.open(url)
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.SUCCESS,
            message=f"Opened {url}",
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ActionResult(
            action=action,
            status=ActionStatus.FAILED,
            message=f"Failed to open URL",
            error=str(e),
            duration_ms=duration,
        )
