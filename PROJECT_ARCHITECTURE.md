# 🚀 Senku 2.0 - AI Assistant Architecture

## 📋 Project Overview

**Senku** is an intelligent AI-powered desktop automation assistant that converts natural language commands into executable system actions. Built with **Ollama (Llama3)** for offline LLM inference, it provides:

- **Voice & Text Input**: Speak or type commands
- **Smart App Launching**: Learn and remember app aliases
- **Web Automation**: YouTube search, web search, WhatsApp messaging
- **System Control**: File creation, screenshot, weather lookup
- **Intelligent Fallback**: Unknown commands fallback to chat mode
- **Context-Aware**: Tracks last used apps and learns user preferences

---

## ✨ Key Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Smart App Launching** | Fuzzy matching, alias learning, multi-fallback strategy | ✅ Implemented |
| **Action Parser** | Converts natural language to JSON actions via LLM | ✅ Implemented |
| **Offline LLM** | Ollama Llama3 integration for privacy | ✅ Implemented |
| **Voice Input** | Speech-to-text using system STT | ✅ Implemented |
| **Voice Output** | Text-to-speech responses | ✅ Implemented |
| **Web Integration** | YouTube, Google search, WhatsApp, web browser | ✅ Implemented |
| **File Operations** | Create files with content | ✅ Implemented |
| **System Commands** | Screenshot, volume control, task killing | ✅ Implemented |
| **Alias Mapping** | Learn and remember app aliases | ✅ Implemented |
| **Context Memory** | Track last used apps | 🔄 In Progress |
| **Web UI** | Frontend dashboard (optional future) | ⏳ Planned |

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                          │
│  (Text Input / Voice Input via Microphone)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   senku/main.py              │
        │   (Main Entry Point)         │
        │   - Read user input          │
        │   - Route to parser/executor │
        └──────────────┬───────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
   ┌──────────────┐          ┌──────────────────┐
   │  ACTION MODE │          │   CHAT MODE      │
   │              │          │                  │
   │  parse_      │          │  call_ollama()   │
   │  actions()   │          │  (Chat Prompt)   │
   │              │          │                  │
   │  Returns:    │          │  Returns:        │
   │  JSON array  │          │  Chat response   │
   │  of actions  │          │                  │
   └──────┬───────┘          └────────┬─────────┘
          │                           │
          ▼                           ▼
   ┌────────────────────┐      ┌─────────────┐
   │  execute(actions)  │      │   OUTPUT    │
   │                    │      │   (Print)   │
   │  Routes each action│      └─────────────┘
   │  to handler        │
   └────────┬───────────┘
            │
     ┌──────┴──────┬──────────┬──────────┬─────────┐
     │             │          │          │         │
     ▼             ▼          ▼          ▼         ▼
┌─────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐
│ OPEN    │ │ CLOSE  │ │ YOUTUBE  │ │SEARCH  │ │ MESSAGE │
│ APP     │ │ APP    │ │ PLAY     │ │ WEB    │ │ SEND    │
└────┬────┘ └───┬────┘ └────┬─────┘ └───┬────┘ └────┬────┘
     │          │           │           │          │
     ▼          ▼           ▼           ▼          ▼
┌──────────────────────────────────────────────────────┐
│          SYSTEM ACTION HANDLERS                      │
│                                                      │
│ • launcher.py   - App launching strategy            │
│ • resolver.py   - Alias resolution & learning       │
│ • executor.py   - Action execution logic            │
│ • executor.py   - Other system commands             │
└──────────────────────────────────────────────────────┘
     │
     └──► System APIs (os.system, webbrowser, subprocess)
```

---

## 📁 File Structure & Descriptions

### **Core Entry Point**

#### `senku/main.py`
- **Purpose**: Main application loop
- **Functionality**:
  - Reads user input (text or voice)
  - Calls `parse_actions()` to detect if input is an action or chat
  - Executes actions via `execute()` or falls back to chat mode
  - Handles exit commands (`exit`, `/bye`)
- **Dependencies**: `agent.py`, `executor.py`

---

### **Brain Module** (Intelligence & Parsing)

#### `senku/brain/agent.py`
- **Purpose**: LLM interaction and action parsing
- **Key Functions**:
  - `call_ollama(user_input, mode)`: Calls Ollama Llama3 API
  - `parse_actions(text)`: Detects and extracts actions from natural language
- **System Prompts**:
  - `SYSTEM_PROMPT`: Instructs LLM to output JSON actions
  - `CHAT_PROMPT`: Natural conversation mode
- **Supported Actions**:
  - `open_app`, `close_app`, `play_youtube`, `search_web`
  - `set_timer`, `send_message`, `create_file`
  - `get_weather`, `system_volume`, `screenshot`

---

### **Actions Module** (Execution Layer)

#### `senku/actions/executor.py`
- **Purpose**: Executes parsed actions on the system
- **Functionality**:
  - Iterates through action list and routes to specific handlers
  - Implements smart app launching with alias learning
  - Handles 10+ action types
- **Key Features**:
  - Asks user to remember app aliases ("Should I remember 'spotify' as 'Spotify'?")
  - Saves learned aliases to `alias_map.json`

#### `senku/actions/launcher.py`
- **Purpose**: Intelligent app launching with multi-fallback strategy
- **Launch Strategy** (in order):
  1. Check `APP_MAP` for special mappings (URLs, protocols)
  2. Try Windows Start Menu search
  3. Direct subprocess launch
  4. Fallback to browser search (Google)
- **Supported Apps**: Chrome, WhatsApp, Spotify, VS Code, Settings, Notepad, etc.

#### `senku/actions/resolver.py`
- **Purpose**: App name resolution and alias management
- **Functions**:
  - `load_alias()`: Load learned aliases from JSON
  - `save_alias()`: Persist new aliases
  - `resolve_app()`: Intelligent app name matching via:
    1. Exact alias lookup
    2. Known apps list
    3. Fuzzy matching (cutoff 0.6)
    4. Return original if no match
- **Storage**: `senku/actions/alias_map.json`

---

### **Voice Module** (Input/Output)

#### `voice/stt.py`
- **Purpose**: Speech-to-text conversion
- **Functionality**: Capture audio from microphone and convert to text
- **Technology**: System STT API (Windows/Linux/Mac compatible)

#### `voice/tts.py`
- **Purpose**: Text-to-speech conversion
- **Functionality**: Convert Senku responses to speech and play audio
- **Technology**: System TTS API

---

### **Legacy Modules** (Old Structure - Can Deprecate)

#### `actions/launcher.py` (old)
- Old version of app launching logic
- Replaced by `senku/actions/launcher.py`

#### `brain/` directory (old)
- `llm_client.py`, `llm_router.py`, `parser.py`, `mapper.py`, `memory.py`, `context.py`
- Legacy brain components
- Superseded by `senku/brain/agent.py`

---

### **Configuration & Data Files**

#### `senku/actions/alias_map.json`
```json
{
  "spotify": "Spotify",
  "vscode": "code",
  "whatsapp": "WhatsApp"
}
```
- Stores learned app aliases
- Built dynamically through user interactions

#### `graph/graph.json`
- Legacy knowledge graph structure (optional)

#### `requirements.txt`
- Project dependencies (requests, ollama SDK, etc.)

---

## 🔄 Data Flow

### **Scenario 1: Action Command**
```
User Input: "open spotify"
    ↓
parse_actions() → Detects "open_app" action
    ↓
execute([{"action": "open_app", "app": "spotify"}])
    ↓
resolve_app("spotify") → Fuzzy match or alias lookup
    ↓
smart_open_app(resolved_app) → Try multiple strategies
    ↓
System launches Spotify
    ↓
[Optional] User agrees to remember alias → Save to JSON
```

### **Scenario 2: Chat Command**
```
User Input: "what is machine learning?"
    ↓
parse_actions() → Returns [] (no action detected)
    ↓
Fallback: call_ollama(text, mode="chat")
    ↓
Ollama Llama3 (with CHAT_PROMPT) → Generates response
    ↓
Print response to user
```

### **Scenario 3: Web Action**
```
User Input: "search for python tutorials"
    ↓
parse_actions() → Detects "search_web" action
    ↓
execute([{"action": "search_web", "query": "python tutorials"}])
    ↓
webbrowser.open("https://www.google.com/search?q=python+tutorials")
    ↓
Browser opens with search results
```

---

## 🧠 Smart Features

### **1. Alias Learning**
- User says: "open spotify"
- System resolves to: "Spotify"
- Asks: "Should I remember 'spotify' as 'Spotify'?"
- Next time user says "spotify" → Direct resolution

### **2. Fuzzy Matching**
- User says: "open chrm" (typo)
- Fuzzy matcher → Matches to "chrome" (cutoff 0.6)
- Opens Chrome

### **3. Multi-Fallback Strategy**
- Try 1: APP_MAP (predefined mappings)
- Try 2: Start Menu search
- Try 3: Direct subprocess launch
- Try 4: Browser search as last resort

### **4. Offline Operation**
- Ollama Llama3 runs locally
- No cloud dependency
- Privacy-first approach
- Fast inference on local hardware

---

## 🔌 Integration Points

### **External Services**
- **Ollama API**: Local LLM inference
- **Windows/Linux/Mac APIs**: `os.system()`, `subprocess`
- **webbrowser module**: Browser automation
- **System STT/TTS**: Voice capabilities

### **Data Persistence**
- `alias_map.json`: Learned app aliases
- `context.json`: Last used app tracking
- `memory.json`: Chat history (legacy)

---

## 🚀 Execution Modes

| Mode | Trigger | Output | Use Case |
|------|---------|--------|----------|
| **Action** | Parseable command | System action executed | App launch, web search, file creation |
| **Chat** | Conversational input | LLM response | Questions, explanations, casual talk |
| **Voice** | Microphone input | Execute action + TTS response | Hands-free operation |

---

## 📊 Feature Matrix

| Component | Feature | Implementation | Status |
|-----------|---------|-----------------|--------|
| **Parser** | Action detection | LLM + prompt engineering | ✅ Working |
| **Launcher** | App resolution | Fuzzy matching + aliases | ✅ Working |
| **Executor** | Action routing | Switch/case handlers | ✅ Working |
| **Voice** | STT | System APIs | ✅ Working |
| **Voice** | TTS | System APIs | ✅ Working |
| **Memory** | Alias learning | JSON persistence | ✅ Working |
| **Memory** | Context tracking | JSON tracking | 🔄 Partial |
| **LLM** | Ollama integration | HTTP API | ✅ Working |
| **UI** | CLI | Terminal interface | ✅ Working |
| **UI** | Web Dashboard | Planned | ⏳ Planned |

---

## 🔧 Technology Stack

- **Language**: Python 3.8+
- **LLM**: Ollama Llama3 (Local)
- **Voice**: System STT/TTS APIs
- **Web**: `requests`, `webbrowser`
- **OS**: Cross-platform (`os`, `subprocess`)
- **Data**: JSON for persistence

---

## 📈 Future Enhancements

1. **Context-Aware Responses**: Track conversation context across sessions
2. **Web UI Dashboard**: Visual interface for app control
3. **Advanced Scheduling**: Cron-like task scheduling
4. **Multi-User Support**: Different user profiles
5. **Plugin System**: Allow custom action handlers
6. **Advanced Voice**: Continuous voice listening mode
7. **Mobile Integration**: Control from phone
8. **Database**: SQLite for scalable data storage

---

## 🎯 Quick Reference

**Main Entry**: `senku/main.py`  
**Parser**: `senku/brain/agent.py`  
**Executor**: `senku/actions/executor.py`  
**Launcher**: `senku/actions/launcher.py`  
**Resolver**: `senku/actions/resolver.py`  
**Config**: `senku/actions/alias_map.json`  

---

Generated for Antigravity integration. Last updated: May 4, 2026
