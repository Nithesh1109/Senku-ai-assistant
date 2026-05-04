"""
Senku Configuration Module
Centralized configuration management for the entire agent system.
All paths, model settings, and system parameters are defined here.

v3.1 — Added intelligence layer config (retry, learning, scheduling, feedback).
"""

import os
from pathlib import Path


# ─── Project Paths ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SENKU_ROOT = Path(__file__).parent.resolve()
DATA_DIR = SENKU_ROOT / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Data File Paths ──────────────────────────────────────────────
MEMORY_FILE = DATA_DIR / "memory.json"
ALIASES_FILE = DATA_DIR / "aliases.json"
CONTEXT_FILE = DATA_DIR / "context.json"
ACTION_LOG_FILE = DATA_DIR / "action_log.json"
APP_CACHE_FILE = PROJECT_ROOT / "app_cache.json"
CONVERSATION_FILE = DATA_DIR / "conversations.json"
PATTERN_FILE = DATA_DIR / "patterns.json"
SCHEDULE_FILE = DATA_DIR / "scheduled_tasks.json"
FEEDBACK_FILE = DATA_DIR / "feedback_log.json"
CONTACTS_FILE = DATA_DIR / "contacts.json"

# ─── LLM Configuration ───────────────────────────────────────────
OLLAMA_BASE_URL = os.environ.get("SENKU_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("SENKU_MODEL", "llama3")
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 500
LLM_TIMEOUT = 30  # seconds
LLM_MAX_RETRIES = 2

# ─── Resolver Configuration ──────────────────────────────────────
FUZZY_MATCH_CUTOFF = 0.65
MAX_FUZZY_RESULTS = 3

# ─── App Launch Configuration ────────────────────────────────────
# Protocol-based app mappings for Windows
APP_PROTOCOL_MAP = {
    "whatsapp": "whatsapp:",
    "spotify": "spotify:",
    "outlook": "outlook:",
    "mail": "outlook:",
    "settings": "ms-settings:",
    "store": "ms-windows-store:",
    "calculator": "calculator:",
    "calendar": "outlookcal:",
    "maps": "bingmaps:",
    "photos": "ms-photos:",
    "camera": "microsoft.windows.camera:",
    "clock": "ms-clock:",
    "alarms": "ms-clock:",
    "feedback": "feedback-hub:",
}

# Command-line app mappings
APP_COMMAND_MAP = {
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "notepad++": "notepad++",
    "cmd": "cmd",
    "terminal": "wt",
    "windows terminal": "wt",
    "powershell": "powershell",
    "explorer": "explorer",
    "file explorer": "explorer",
    "task manager": "taskmgr",
    "paint": "mspaint",
    "snipping tool": "snippingtool",
    "wordpad": "wordpad",
    "regedit": "regedit",
    "control panel": "control",
}

# URL-based app mappings
APP_URL_MAP = {
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chat.openai.com",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "stackoverflow": "https://stackoverflow.com",
}

# ─── Memory Configuration ────────────────────────────────────────
MAX_CONVERSATION_HISTORY = 50
MAX_ACTION_LOG_ENTRIES = 500
MEMORY_SAVE_INTERVAL = 5  # save after every N operations

# ─── Intelligence / Retry Configuration ──────────────────────────
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_DELAY = 0.5         # seconds
DEFAULT_RETRY_BACKOFF = 2.0
MIN_CONFIDENCE_THRESHOLD = 0.4    # Below this, ask for clarification
AMBIGUITY_THRESHOLD = 0.65        # Below this, flag as ambiguous
PATTERN_MIN_OCCURRENCES = 3       # Min times a command must repeat to become a pattern
PATTERN_MAX_STORED = 200          # Max number of learned patterns

# ─── Scheduling Configuration ────────────────────────────────────
SCHEDULER_POLL_INTERVAL = 10      # seconds between schedule checks
MAX_SCHEDULED_TASKS = 50

# ─── Feedback Configuration ──────────────────────────────────────
FEEDBACK_WEIGHTS = {
    "success": 0.5,
    "speed": 0.2,
    "reliability": 0.3,
}
SPEED_BASELINE_MS = {             # Expected avg execution time per action type
    "open_app": 800,
    "close_app": 500,
    "search_web": 300,
    "play_youtube": 300,
    "screenshot": 500,
    "create_file": 200,
    "open_file": 400,
    "open_folder": 400,
    "open_url": 300,
    "get_weather": 300,
    "send_message": 2000,
    "system_volume": 300,
    "set_timer": 100,
    "run_command": 1000,
}

# ─── WhatsApp Configuration ──────────────────────────────────────
WHATSAPP_SEND_DELAY = 12  # seconds to wait for WhatsApp Web to load before auto-send

# ─── System Configuration ────────────────────────────────────────
DEBUG_MODE = os.environ.get("SENKU_DEBUG", "false").lower() == "true"
LOG_LEVEL = os.environ.get("SENKU_LOG_LEVEL", "INFO")

# ─── Voice Configuration ─────────────────────────────────────────
VOICE_ENABLED = os.environ.get("SENKU_VOICE", "false").lower() == "true"
TTS_RATE = 175
TTS_VOLUME = 0.9
STT_TIMEOUT = 5
STT_PHRASE_LIMIT = 10

# ─── Action System ───────────────────────────────────────────────
# Supported action types and their required parameters
ACTION_SCHEMA = {
    "open_app": {"required": ["app"], "optional": []},
    "close_app": {"required": ["app"], "optional": []},
    "play_youtube": {"required": ["query"], "optional": []},
    "search_web": {"required": ["query"], "optional": ["engine"]},
    "send_message": {"required": ["to", "body"], "optional": ["platform"]},
    "create_file": {"required": ["name"], "optional": ["content", "path"]},
    "open_file": {"required": ["path"], "optional": []},
    "open_folder": {"required": ["path"], "optional": []},
    "get_weather": {"required": [], "optional": ["city"]},
    "screenshot": {"required": [], "optional": ["region"]},
    "system_volume": {"required": ["level"], "optional": []},
    "set_timer": {"required": ["duration"], "optional": ["label"]},
    "run_command": {"required": ["command"], "optional": []},
    "open_url": {"required": ["url"], "optional": []},
}

# ─── Retry Strategies per Action Type ─────────────────────────────
# Maps error patterns to alternative strategies
RETRY_STRATEGIES = {
    "open_app": {
        "fallback_chain": ["start", "command", "search"],
        "max_retries": 2,
    },
    "search_web": {
        "fallback_chain": ["google", "bing", "duckduckgo"],
        "max_retries": 1,
    },
    "open_file": {
        "fallback_chain": ["startfile", "explorer"],
        "max_retries": 1,
    },
}
