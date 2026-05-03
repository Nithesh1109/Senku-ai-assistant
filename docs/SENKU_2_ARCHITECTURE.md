# 🚀 Senku 2.0 Architecture (Agent-Based System)

## 🎯 Vision
Senku 2.0 is not a command runner. It is an AI agent that:
- Understands natural language
- Breaks tasks into steps
- Executes actions on the system

---

## 🧠 Core Flow

User Input (Text / Voice)
        ↓
Cleaner (normalize input)
        ↓
Agent (LLM - Llama 3 via Ollama)
        ↓
Planner (JSON action list)
        ↓
Executor (runs actions)
        ↓
System + Web Actions
        ↓
Feedback

---

## 📁 Project Structure

senku/
├── main.py

├── brain/
│   ├── agent.py          # LLM interaction (Ollama)
│   ├── planner.py        # parse LLM output → actions
│   ├── cleaner.py        # remove noise words
│   ├── memory.py         # learned mappings
│   └── context.py        # last used state

├── actions/
│   ├── executor.py       # runs actions
│   ├── launcher.py       # open apps/files
│   └── web_actions.py    # youtube, google, whatsapp

├── voice/
│   ├── stt.py            # speech → text
│   └── tts.py            # optional speech output

├── data/
│   ├── memory.json
│   └── context.json

---

## ⚙️ Action Types

1. open_app
2. open_file
3. open_folder
4. search_google
5. play_youtube
6. send_whatsapp

---

## 🧠 Example Flow

Input:
"open chrome and play interstellar bgm"

LLM Output:
[
  {"action": "open_app", "app": "chrome"},
  {"action": "play_youtube", "query": "interstellar bgm"}
]

Executor:
1. open chrome
2. open youtube search

---

## 🔥 Design Principles

- Keep execution deterministic
- Use LLM only for planning
- No overengineering
- Fast response > perfect response

---

## 🚀 Phase Plan

Phase 1 → Agent + Executor
Phase 2 → Web actions
Phase 3 → Voice stability
Phase 4 → Multi-step automation

---

## ✅ Goal Outcome

User can say:
- "open vscode and run test.py"
- "play lo-fi music"
- "send whatsapp hi"

And Senku executes intelligently.
