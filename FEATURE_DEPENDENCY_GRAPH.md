# 🔗 Senku 2.0 - Feature Graph & Dependencies

## 🎯 Feature Matrix & Implementation Status

### **Core Features**

```
┌─────────────────────────────────────────────────────────────┐
│ FEATURE                  │ STATUS    │ IMPLEMENTATION       │
├─────────────────────────────────────────────────────────────┤
│ Text Input              │ ✅ Done   │ main.py input()      │
│ Voice Input (STT)       │ ✅ Done   │ voice/stt.py         │
│ Voice Output (TTS)      │ ✅ Done   │ voice/tts.py         │
│ Offline LLM             │ ✅ Done   │ agent.py (Ollama)    │
│ Action Parsing          │ ✅ Done   │ agent.py             │
│ Chat Fallback           │ ✅ Done   │ main.py fallback     │
├─────────────────────────────────────────────────────────────┤
│ Smart App Launch        │ ✅ Done   │ launcher.py          │
│ App Name Resolution     │ ✅ Done   │ resolver.py          │
│ Alias Learning          │ ✅ Done   │ resolver.py          │
│ Web Search              │ ✅ Done   │ executor.py          │
│ YouTube Search          │ ✅ Done   │ executor.py          │
│ WhatsApp Messaging      │ ✅ Done   │ executor.py          │
│ File Creation           │ ✅ Done   │ executor.py          │
│ Screenshot              │ ✅ Done   │ executor.py          │
│ App Closing             │ ✅ Done   │ executor.py          │
│ Weather Lookup          │ ✅ Done   │ executor.py          │
│ Volume Control          │ ⏳ Planned│ Not implemented      │
│ Timer Setting           │ ⏳ Planned│ Not implemented      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Component Dependency Graph

```
┌──────────────────────────────────────────────────────────┐
│                    SENKU MAIN (main.py)                  │
└────────────────┬─────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
   ┌─────────────┐   ┌─────────────────┐
   │   BRAIN     │   │    ACTIONS      │
   │ (agent.py)  │   │  (executor.py)  │
   └────┬────────┘   └────────┬────────┘
        │                     │
        │ Uses Ollama         ├─→ launcher.py
        │ for LLM             ├─→ resolver.py
        │                     ├─→ webbrowser
        │                     ├─→ os.system
        │                     └─→ subprocess
        │
        └─────────────────────────────────┐
                                          │
                            ┌─────────────┴──────────────┐
                            │                            │
                            ▼                            ▼
                      ┌──────────────┐           ┌──────────────┐
                      │  VOICE I/O   │           │   CONFIG     │
                      ├──────────────┤           ├──────────────┤
                      │ voice/stt.py │           │ alias_map.json
                      │ voice/tts.py │           │ context.json
                      └──────────────┘           │ memory.json
                                                 └──────────────┘
```

---

## 🔀 Action Execution Flow

```
┌────────────────────────┐
│ User Input Text/Voice  │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ main.py                            │
│ → read input (text or STT voice)   │
└───────────┬────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ agent.py: parse_actions(text)               │
│ Call Ollama with SYSTEM_PROMPT              │
│ Output: JSON array or empty []              │
└───────────┬─────────────────────────────────┘
            │
        ┌───┴──────────────┐
        │ Actions found?   │
        └───┬──────────────┘
            │
        Yes│       No
       ┌────┴────┬──────────────┐
       │          │              │
       ▼          ▼              ▼
  ┌──────────┐ ┌──────────────────────┐
  │execute() │ │ agent.py: chat mode  │
  │          │ │ call_ollama(mode)    │
  └────┬─────┘ │ Return: response     │
       │        └──────────┬───────────┘
       │                   │
       ├─ open_app ────┐   └─→ Print to user
       ├─ close_app    │
       ├─ search_web ──┤  /resolver.py\
       ├─ play_youtube │  /launcher.py \
       ├─ send_message │─→ System APIs
       ├─ create_file  │
       ├─ get_weather  │
       └─ screenshot ──┘
```

---

## 🎯 Feature Dependency Map

### **1. App Launching Feature**

```
app_launching
├── launcher.py
│   ├── APP_MAP (hardcoded mappings)
│   ├── os.system() (Start Menu)
│   ├── subprocess.Popen() (Direct)
│   └── webbrowser.open() (Fallback)
│
└── resolver.py
    ├── load_alias() → alias_map.json
    ├── KNOWN_APPS list
    ├── difflib.get_close_matches() (Fuzzy)
    └── save_alias() → alias_map.json
```

### **2. Web Integration Feature**

```
web_integration
├── executor.py (Routes web actions)
│
├── search_web
│   └── webbrowser.open(google.com/search?q=...)
│
├── play_youtube
│   └── webbrowser.open(youtube.com/results?search_query=...)
│
├── send_message
│   └── webbrowser.open(wa.me/{number}?text=...)
│
└── get_weather
    └── webbrowser.open(google.com/search?q=weather+...)
```

### **3. Voice I/O Feature**

```
voice_io
├── STT (Speech-to-Text)
│   └── voice/stt.py
│       ├── Listen to microphone
│       └── Return text to main.py
│
└── TTS (Text-to-Speech)
    └── voice/tts.py
        ├── Take response text
        └── Play audio
```

### **4. LLM Integration Feature**

```
llm_integration
├── agent.py: call_ollama()
│   ├── HTTP POST to Ollama API
│   ├── SYSTEM_PROMPT (action mode)
│   ├── CHAT_PROMPT (chat mode)
│   └── Return parsed response
│
└── Ollama Llama3
    └── Local inference (offline)
```

### **5. Alias Learning Feature**

```
alias_learning
├── executor.py
│   └── Ask user: "Remember X as Y?"
│
├── resolver.py
│   ├── load_alias() from JSON
│   └── save_alias() to JSON
│
└── alias_map.json
    └── Persistent storage
```

---

## 🔌 External Dependencies

### **System APIs (Built-in)**
```
os.system()          → Launch apps via Start Menu
subprocess.Popen()   → Direct process launch
webbrowser.open()    → Open URLs in browser
os.mkdir()           → Create directories
open()               → File I/O
json.load/dump()     → JSON persistence
difflib              → Fuzzy string matching
re                   → Regex parsing
requests             → HTTP to Ollama
```

### **External Services**
```
Ollama (localhost:11434)
├── Llama3 model
├── Action parsing
└── Chat generation
```

### **System Services**
```
Windows/Linux/Mac APIs
├── microphone (STT)
├── speaker (TTS)
├── Start Menu
├── Process management
└── Desktop
```

---

## 📊 Data Flow Between Components

```
┌─────────────────────────────────────────────────────────┐
│                       DATA STORE                         │
│                                                          │
│  alias_map.json   ← User-learned aliases               │
│  context.json     ← Last used apps                      │
│  memory.json      ← Chat history (legacy)              │
│  graph.json       ← Knowledge graph (optional)          │
└────────────────┬──────────────────────────────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
        ▼        ▼        ▼
    ┌──────┐ ┌───────┐ ┌────────┐
    │Brain │ │Action │ │Voice   │
    │      │ │       │ │        │
    │Parse │ │Launch │ │STT/TTS │
    │Chat  │ │Resolve│ │        │
    └──┬───┘ └───┬───┘ └───┬────┘
       │         │         │
       └────┬────┴────┬────┘
            │ User I/O │
            └──────────┘
```

---

## 🎓 Call Sequence Examples

### **Example 1: Open Spotify**

```
main.py: input(">> ") → "open spotify"
  │
  ├─→ agent.py: parse_actions("open spotify")
  │   └─→ Ollama: "Please parse..." → [{"action": "open_app", "app": "spotify"}]
  │
  ├─→ executor.py: execute(actions)
  │   │
  │   ├─→ resolver.py: resolve_app("spotify")
  │   │   ├─ Check alias_map.json → Not found
  │   │   ├─ Check KNOWN_APPS → Found!
  │   │   └─ Return "spotify"
  │   │
  │   └─→ launcher.py: open_app("spotify")
  │       ├─ Check APP_MAP → Found: "spotify:"
  │       ├─ os.system("start spotify:")
  │       └─ Spotify launches ✅
  │
  └─→ Ask: "Remember 'spotify' as 'spotify'? (y/n)"
      → User says "y"
      → Save to alias_map.json ✅
```

### **Example 2: Search for Python**

```
main.py: input(">> ") → "search python tutorials"
  │
  ├─→ agent.py: parse_actions("search python tutorials")
  │   └─→ Ollama: [...SYSTEM_PROMPT...] → [{"action": "search_web", "query": "python tutorials"}]
  │
  └─→ executor.py: execute(actions)
      └─→ webbrowser.open("https://www.google.com/search?q=python+tutorials")
          └─→ Browser opens with results ✅
```

### **Example 3: Ask a Question (Chat)**

```
main.py: input(">> ") → "what is machine learning?"
  │
  ├─→ agent.py: parse_actions("what is machine learning?")
  │   └─→ Ollama: [... SYSTEM_PROMPT ...] → []  (empty = chat mode)
  │
  ├─→ Fallback: agent.py: call_ollama("what is machine learning?", mode="chat")
  │   └─→ Ollama: [...CHAT_PROMPT...] → "Machine Learning is a subset of AI that..."
  │
  └─→ main.py: print(response) ✅
```

---

## 🔄 Integration Points

| Component | Integrates With | Data Format |
|-----------|-----------------|-------------|
| main.py | agent.py, executor.py | Text strings, JSON |
| agent.py | Ollama API, executor.py | JSON actions, responses |
| executor.py | launcher.py, resolver.py, webbrowser, os | JSON actions, app names |
| launcher.py | resolver.py, OS APIs | App names, URLs, protocols |
| resolver.py | alias_map.json, KNOWN_APPS | Aliases, app names |
| stt.py | main.py | Audio → Text |
| tts.py | executor.py | Text → Audio |

---

## 📈 Scalability Considerations

### **Current Limits**
- **Actions**: 10 supported types
- **Known Apps**: ~8 hardcoded
- **Aliases**: Unlimited (JSON based)
- **LLM Context**: Limited by Ollama memory
- **User Sessions**: Single-threaded

### **Growth Path**
1. **Add Actions**: Add to agent.py prompts + executor.py handlers
2. **Expand Apps**: Add to KNOWN_APPS + APP_MAP
3. **Improve Learning**: Add ML model for action prediction
4. **Scale Voice**: Continuous listening mode
5. **Multi-User**: User profiles + separate alias files
6. **Database**: Replace JSON with SQLite for scalability

---

## 🚀 Performance Metrics

| Operation | Typical Time | Notes |
|-----------|------------|-------|
| Action Parse | 1-3 seconds | Ollama inference |
| Chat Response | 2-5 seconds | Depends on model |
| App Launch | 0.5-2 seconds | OS dependent |
| Alias Resolution | <50ms | JSON lookup + fuzzy |
| STT | 2-5 seconds | Hardware dependent |
| TTS | 0.5-1 second | Audio generation |

---

## 🎯 For Antigravity Integration

**Key Files to Understand First:**
1. `senku/main.py` - Main loop
2. `senku/brain/agent.py` - LLM integration
3. `senku/actions/executor.py` - Action routing
4. `senku/actions/launcher.py` - App launching
5. `senku/actions/resolver.py` - Alias learning

**API Entry Points:**
- `main()` - Start the assistant
- `parse_actions(text)` - Parse user input
- `execute(actions)` - Run actions
- `call_ollama(text, mode)` - LLM calls
- `resolve_app(name)` - App resolution

**Configuration:**
- Ollama running on `localhost:11434`
- Model: Llama3
- Aliases stored in `senku/actions/alias_map.json`
- Context in `context.json`

---

Created: May 4, 2026  
For: Antigravity AI Integration  
Version: Senku 2.0
