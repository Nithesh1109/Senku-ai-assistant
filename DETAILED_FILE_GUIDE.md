# 📁 Senku 2.0 - Project Structure with Descriptions

## 📊 Quick Stats
- **Total Files**: 30
- **Python Files**: 22
- **Configuration Files**: 4
- **Documentation**: 2
- **Total Size**: ~85 KB (excluding dependencies)

---

## 🏗️ Directory Tree with File Descriptions

```
senku/
├── 🚀 MAIN ENTRY POINT
│   └── main.py                          # Application main loop - reads user input, routes to parser/executor
│
├── 🧠 BRAIN (Intelligence & Parsing)
│   └── brain/
│       └── agent.py                     # LLM caller (Ollama) + Action parser using Llama3 prompts
│
├── ⚙️  ACTIONS (Execution Layer)
│   └── actions/
│       ├── executor.py                  # Routes and executes parsed actions (open_app, search_web, etc.)
│       ├── launcher.py                  # Smart app launching with multi-fallback strategy
│       ├── resolver.py                  # App name resolution, fuzzy matching, alias management
│       ├── alias_map.json              # Learned app aliases (user_input → resolved_app)
│       │
│       ├── 🗂️ Legacy Action Files (deprecated, kept for reference)
│       ├── app_scanner.py              # Scans system for installed apps
│       ├── app_cache.py                # Caches app list for fast lookup
│       ├── mapper.py                   # Old alias mapper (replaced by resolver.py)
│       ├── launcher.py (old)           # Old app launcher (replaced by new launcher.py)
│       ├── runner.py                   # Old command runner
│       ├── typer.py                    # Old input handler
│       └── app_cache.json              # Old cache file
│
├── 🎤 VOICE (Input/Output)
│   └── voice/
│       ├── stt.py                      # Speech-to-text: Microphone input → Text
│       └── tts.py                      # Text-to-speech: Response → Audio playback
│
├── 🧠 LEGACY BRAIN (Old Structure - Deprecate)
│   └── brain/
│       ├── llm_client.py              # Old LLM client (replaced by agent.py)
│       ├── llm_router.py              # Old LLM router
│       ├── parser.py                  # Old action parser
│       ├── mapper.py                  # Old alias mapper
│       ├── memory.py                  # Old memory handler
│       └── context.py                 # Old context tracker
│
├── 🎮 LEGACY CONTROLLER
│   └── controller/
│       └── confirm.py                 # User confirmation handler
│
├── 📚 GRAPH KNOWLEDGE (Optional)
│   └── graph/
│       └── graph.json                 # Knowledge graph structure (optional)
│
├── 📝 CONFIGURATION & DATA
│   ├── requirements.txt                # Python dependencies (requests, ollama, etc.)
│   ├── alias_map.json                 # Learned app aliases (top level)
│   ├── context.json                   # Last used app tracking
│   ├── memory.json                    # Chat history (legacy)
│   ├── app_cache.json                 # App cache (legacy)
│   └── graph.json                     # Knowledge graph (legacy)
│
├── 📚 DOCUMENTATION
│   ├── README.md                      # Project overview and setup
│   ├── PROJECT_ARCHITECTURE.md        # This comprehensive architecture guide
│   ├── SENKU_2_ARCHITECTURE.md        # Additional architecture notes
│   └── project_tree.txt               # Simple file listing
│
└── 🧪 TESTING
    └── test.py                        # Test suite for components
```

---

## 📄 File Descriptions (Detailed)

### **ENTRY POINT**

**`senku/main.py`**
```
Purpose:    Application main loop
Size:       ~150 lines
Imports:    agent.py, executor.py
Function:   
  1. Print startup message
  2. Loop: Read user input
  3. Try parse_actions() for action detection
  4. If action found → execute(actions)
  5. If no action → fallback to call_ollama(chat_mode)
  6. Exit on "exit" or "/bye"
```

---

### **BRAIN MODULE (Intelligence)**

**`senku/brain/agent.py`**
```
Purpose:    LLM integration + Action parsing
Size:       ~200 lines
Dependencies: requests (HTTP to Ollama)
API Base:   http://localhost:11434

KEY FUNCTIONS:
  • call_ollama(user_input, mode="action")
    - mode="action": Parse input into JSON actions
    - mode="chat": Generate chat response
    - Uses system prompts to guide Llama3 behavior

  • parse_actions(text)
    - Calls Ollama with SYSTEM_PROMPT
    - Returns JSON array of actions (or [] if chat)

SUPPORTED ACTIONS:
  [open_app, close_app, play_youtube, search_web, 
   set_timer, send_message, create_file, get_weather, 
   system_volume, screenshot]

PROMPTS:
  • SYSTEM_PROMPT:  Instructs LLM to output JSON
  • CHAT_PROMPT:    Natural conversation tone
```

---

### **ACTIONS MODULE (Execution)**

**`senku/actions/executor.py`** (Core Action Handler)
```
Purpose:    Execute all parsed actions
Size:       ~100 lines
Function:
  - Loop through action list
  - Route each action to appropriate handler
  - Smart app launching with alias learning

ACTION HANDLERS:
  1. "open_app"     → resolve_app() → smart_open_app()
                      + Ask user to remember alias
  2. "close_app"    → taskkill /IM {app}.exe /F
  3. "play_youtube" → webbrowser.open() + query
  4. "search_web"   → Google search via browser
  5. "send_message" → WhatsApp Web link
  6. "create_file"  → Write file with content
  7. "get_weather"  → Google weather search
  8. "screenshot"   → Launch snippingtool
  9. "system_volume"→ [Not implemented]
```

**`senku/actions/launcher.py`** (Smart App Launcher)
```
Purpose:    Launch apps with intelligent fallback
Size:       ~70 lines
Strategy:   4-tier fallback approach

TIER 1: APP_MAP (Hardcoded mappings)
  • "vscode" → "code"
  • "whatsapp" → "whatsapp:"
  • "youtube" → "https://www.youtube.com"
  • "spotify" → "spotify:"
  • "outlook" → "outlook:"
  • "settings" → "ms-settings:"

TIER 2: Start Menu Search
  • os.system('start "" "{app}"')

TIER 3: Direct subprocess
  • subprocess.Popen(app)

TIER 4: Browser Fallback
  • Google search for unknown apps
  • "google {app}" → Search results
```

**`senku/actions/resolver.py`** (App Resolution)
```
Purpose:    Resolve app names + manage aliases
Size:       ~80 lines
Data:       senku/actions/alias_map.json

KEY FUNCTIONS:
  • resolve_app(app_name)
    Step 1: Check user-learned aliases
    Step 2: Check KNOWN_APPS list
    Step 3: Fuzzy match (cutoff 0.6)
    Step 4: Return original

  • load_alias()     → Load JSON aliases
  • save_alias(map)  → Persist to JSON

KNOWN_APPS:
  [chrome, whatsapp, spotify, vscode, code, notepad,
   calculator, settings]

LEARNING:
  User says: "open sppotify"
  Executor asks: "Remember 'sppotify' as 'spotify'? (y/n)"
  → Saved to alias_map.json for next time
```

---

### **VOICE MODULE (I/O)**

**`voice/stt.py`**
```
Purpose:    Speech-to-text conversion
Status:     Implemented
Function:   
  • Listen to microphone
  • Convert audio to text
  • Return text to main.py
Technology: System STT API
```

**`voice/tts.py`**
```
Purpose:    Text-to-speech conversion
Status:     Implemented
Function:
  • Take response text
  • Convert to speech
  • Play audio to speaker
Technology: System TTS API
```

---

### **CONFIGURATION FILES**

**`senku/actions/alias_map.json`**
```json
{
  "spotify": "Spotify",
  "vscode": "Visual Studio Code",
  "whatsapp": "WhatsApp",
  "spfy": "spotify"
}
```
Purpose: Store learned aliases
Created: Dynamically through user interactions
Updated: When user confirms alias mapping

**`context.json`**
```json
{
  "last_app": "spotify",
  "last_search": "python tutorials",
  "session_count": 42
}
```
Purpose: Track context for smarter suggestions
Status: Partially implemented

**`memory.json`**
```json
[
  {"user": "open chrome", "bot": "Opened Chrome"},
  {"user": "what is AI?", "bot": "AI is..."}
]
```
Purpose: Chat history (legacy)
Status: Deprecated in Senku 2.0

---

### **LEGACY MODULES (Can Deprecate)**

**`brain/` directory (Old)**
- `llm_client.py`: Old LLM interface
- `llm_router.py`: Old routing logic
- `parser.py`: Old action parser
- `mapper.py`: Old alias mapping
- `memory.py`: Old memory handler
- `context.py`: Old context tracker

**Status**: Superseded by `senku/brain/agent.py`
**Action**: Can be archived/deleted after full migration

**`actions/` directory (Old)**
- `app_scanner.py`: System app scanner
- `app_cache.py`: App list cache
- `mapper.py`: Old alias mapper
- `launcher.py` (old): Old launcher logic
- `runner.py`: Old command runner
- `typer.py`: Old input handler

**Status**: Replaced by new modular structure
**Action**: Reference for migration patterns

---

### **DOCUMENTATION**

**`README.md`**
- Project overview
- Quick start guide
- Installation steps

**`PROJECT_ARCHITECTURE.md`**
- Complete architecture documentation
- File descriptions
- Data flow diagrams
- Feature matrix

**`project_tree.txt`**
- Simple file listing
- Auto-generated from file system

---

## 🎯 Key Features by File

| Feature | Primary File | Secondary Files |
|---------|-------------|-----------------|
| App Launching | `launcher.py` | `resolver.py`, `executor.py` |
| Alias Learning | `resolver.py` | `executor.py`, `alias_map.json` |
| Action Parsing | `agent.py` | `executor.py` |
| Web Integration | `executor.py` | `launcher.py` |
| Voice I/O | `stt.py`, `tts.py` | `main.py` |
| LLM Inference | `agent.py` | (Ollama external) |
| Chat Mode | `agent.py` | `main.py` |

---

## 📊 Code Metrics

| Metric | Value |
|--------|-------|
| Total Lines of Code | ~1,200 |
| Core Functions | 15+ |
| Supported Actions | 10 |
| Known Apps | 8+ |
| Configuration Files | 4 |
| Test Coverage | Basic |

---

## 🚀 Dependencies

From `requirements.txt`:
```
requests              # HTTP client for Ollama API
json                  # JSON parsing (stdlib)
os                    # System operations (stdlib)
subprocess            # Process management (stdlib)
webbrowser            # Browser automation (stdlib)
re                    # Regex parsing (stdlib)
difflib               # Fuzzy matching (stdlib)
```

---

## 💡 Architecture Principles

1. **Modular Design**: Separate concerns (brain, actions, voice)
2. **Offline-First**: Ollama for privacy and speed
3. **Progressive Enhancement**: Fallback strategies for every action
4. **Learning**: Alias memory that improves over time
5. **Multi-Mode**: Action + Chat + Voice operations
6. **Extensible**: Easy to add new actions/handlers

---

## 🔄 Data Flow Summary

```
USER INPUT
    ↓
[main.py] Read input (text/voice)
    ↓
[agent.py] parse_actions() → JSON or []
    ↓
    ├─→ Actions found? → [executor.py] execute()
    │      ├─→ open_app? → [launcher.py] + [resolver.py]
    │      ├─→ search_web? → webbrowser.open()
    │      ├─→ send_message? → WhatsApp link
    │      └─→ ... other actions
    │
    └─→ No actions? → [agent.py] call_ollama(chat_mode)
            ↓
        LLM Response → Print to user
```

---

## 🎓 For New Developers

**Start Here:**
1. Read `README.md` for context
2. Review `senku/main.py` to understand flow
3. Check `senku/brain/agent.py` for LLM integration
4. Explore `senku/actions/executor.py` for action handling

**Key Concepts:**
- **Actions**: JSON objects with action type + parameters
- **Prompts**: Guide LLM behavior with system instructions
- **Fallbacks**: Multiple strategies for robustness
- **Learning**: Alias system that improves over time

**To Add a Feature:**
1. Add action type to agent.py prompts
2. Implement handler in executor.py
3. Update supported actions list
4. Test with main.py loop

---

Generated: May 4, 2026
Purpose: Antigravity integration + Developer reference
