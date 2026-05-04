# 🧪 Senku 3.0 — AI Agent System

A production-grade local AI assistant that understands natural language, converts it into structured actions, and controls your system intelligently.

## 🚀 Quick Start

```bash
# 1. Ensure Ollama is running with Llama3
ollama serve
ollama pull llama3

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run Senku
python main.py
```

## 🎯 What Can Senku Do?

```
🧪 >> open chrome
✅ Opened chrome

🧪 >> play lofi music on youtube
✅ Playing on YouTube: lofi music

🧪 >> search for python tutorials
✅ Searching for: python tutorials

🧪 >> take a screenshot
✅ Screenshot tool launched

🧪 >> what's the weather in Tokyo?
✅ Weather for Tokyo

🧪 >> create a file called notes.txt with content hello world
✅ Created file: C:\Users\...\Desktop\notes.txt

🧪 >> open my downloads folder
✅ Opened folder: C:\Users\...\Downloads

🧪 >> what is machine learning?
💬 Machine Learning is a subset of AI that...
```

## 🏗️ Architecture

```
senku/
├── main.py              # Master orchestrator
├── config.py            # Centralized configuration
├── core/                # Types, events, exceptions
├── brain/               # Intelligence layer (LLM + planning)
│   ├── llm_client.py    # Robust Ollama client
│   ├── planner.py       # Intent classification + action planning
│   ├── parser.py        # JSON action extraction
│   ├── preprocessor.py  # Input normalization + shortcuts
│   └── prompts.py       # Versioned prompt templates
├── actions/             # Modular execution layer
│   ├── executor.py      # Action execution engine
│   ├── registry.py      # Plugin-based handler system
│   ├── launcher.py      # Smart app launching
│   └── handlers/        # Individual action handlers
├── resolver/            # Multi-strategy app resolution
│   ├── app_resolver.py  # 7-tier resolution engine
│   ├── app_registry.py  # System app discovery
│   └── alias_store.py   # Learned alias management
├── memory/              # Structured learning system
│   ├── store.py         # Persistent storage engine
│   ├── conversation.py  # Chat history tracking
│   ├── action_log.py    # Action outcome learning
│   └── context.py       # Session context
└── voice/               # Speech I/O
    ├── stt.py           # Speech-to-text
    └── tts.py           # Text-to-speech
```

## ⚡ 14 Supported Actions

| Action | Description | Example |
|--------|------------|---------|
| `open_app` | Opens any application | "open spotify" |
| `close_app` | Closes a running app | "close notepad" |
| `play_youtube` | Plays content on YouTube | "play lofi music" |
| `search_web` | Web search (Google/Bing/DDG) | "search for AI news" |
| `send_message` | WhatsApp messaging | "send message to +1234" |
| `create_file` | Creates a new file | "create notes.txt" |
| `open_file` | Opens a file | "open report.pdf" |
| `open_folder` | Opens a folder | "open downloads" |
| `get_weather` | Shows weather | "weather in London" |
| `screenshot` | Takes a screenshot | "take a screenshot" |
| `system_volume` | Volume control | "volume up" |
| `set_timer` | Sets a timer | "set timer 5 minutes" |
| `run_command` | Shell commands | "run dir" |
| `open_url` | Opens a URL | "open github.com" |

## 🧠 Intelligence Features

- **Shortcut Detection**: Simple commands bypass the LLM for instant execution
- **Multi-Strategy Resolution**: 7-tier app name resolution (aliases → protocols → commands → URLs → cache → fuzzy → fallback)
- **Learning System**: Automatically learns app aliases from usage patterns
- **Context Awareness**: Tracks session state for smarter responses
- **Conversation Memory**: Multi-turn context for natural interactions
- **Action Logging**: Records outcomes for pattern analysis and improvement

## 🔧 Configuration

Environment variables:
- `SENKU_OLLAMA_URL` — Ollama URL (default: `http://localhost:11434`)
- `SENKU_MODEL` — LLM model (default: `llama3`)
- `SENKU_DEBUG` — Debug mode (default: `false`)
- `SENKU_VOICE` — Voice I/O (default: `false`)

## 📊 System Commands

| Command | Description |
|---------|------------|
| `/help` | Show help |
| `/health` | System status |
| `/actions` | List available actions |
| `/history` | Recent conversation |
| `/bye` | Exit Senku |
