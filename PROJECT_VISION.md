# AI-Agent Project

## Current Project Status

- Phase 2 - Structured Actions: Complete
- Current Milestone: Phase 3 - Task Execution Engine

Phase 2 established JSON action output, validation and execution results, legacy
action compatibility, and a responsive GUI request flow using Ollama's local
HTTP API. Multi-step task planning and execution verification remain Phase 3
work.

## Purpose

AI-Agent is a personal desktop AI assistant designed to operate as an intelligent layer on top of Windows.

The goal is to create a system capable of:

- Understanding natural language
- Planning tasks
- Executing actions
- Controlling Windows applications
- Using both local and cloud AI models
- Understanding screen contents
- Maintaining memory across sessions
- Becoming a long-term personal assistant

The vision is similar to a "Jarvis" style assistant that can carry out tasks rather than simply answer questions.

---

# Current Hardware

## Computer

- CPU: Intel i7-8700K
- RAM: 32 GB
- GPU: NVIDIA GTX 1080 Ti (11 GB VRAM)
- SSD: 1 TB

## GPU Driver

- NVIDIA Driver: 582.78
- CUDA: 13.0

---

# Software Environment

## Development

- Windows
- Python 3.15
- VS Code
- Git
- GitHub Account

## AI

- Ollama
- Llama 3.2 (local)

## Python Libraries

Currently used:

- pyautogui
- pillow
- pywin32
- tkinter

---

# Current Project Structure

AI-Agent/

- logs/
- memory/
- prompts/
- scripts/

Important files:

- agent_ui.py
- tools.py
- ai_agent.py

---

# Current Capabilities

## AI Reasoning

Working:

- Natural language understanding
- Local Llama 3.2 integration
- Ollama local API integration with JSON-constrained response generation

Example:

User:
Open notepad and type hello

AI:
{"actions":[{"action":"OPEN_NOTEPAD","params":{}},{"action":"TYPE_TEXT","params":{"text":"hello"}}]}

---

## Tool Execution

Working:

### OPEN_NOTEPAD

Can launch Notepad.

### TAKE_SCREENSHOT

Can capture desktop screenshot.

### MOVE_MOUSE

Can move mouse cursor.

### LIST_WINDOWS

Can list visible windows.

### TYPE_TEXT

Can type supplied text into active application.

---

## GUI

Working:

- Custom AI Agent window
- Request text box
- Execute button
- AI response display
- Result display

---

# Current Architecture

User
↓
Agent UI
↓
Ollama local API
↓
Llama 3.2 JSON action response
↓
Action parser and validation
↓
Tools
↓
Windows

---

## Current Milestone

Phase 3 - Task Execution Engine

Phase 2 structured action support is complete. The next milestone is to build
reliable task execution around the existing action interface, including
sequencing, progress tracking, and verification.

# Immediate Goals

## Short Term

1. Clean up GUI
2. Fix layout issues
3. Improve plan formatting
4. Support more complex multi-step actions
5. Create memory system
6. Create configuration system

---

## Example Supported Tasks

Current:

- Open Notepad
- Take Screenshot
- Move Mouse
- List Open Windows
- Type Text

Target:

- Open Notepad and create notes
- Open VS Code and continue project
- Open Spotify
- Create shopping lists
- Organise files

---

# Memory System

Planned

Agent should remember:

- User preferences
- Favourite applications
- Current projects
- Previous conversations
- Long-term goals

Storage location:

memory/

---

# Vision System

Planned

Agent should be capable of:

- Taking screenshots
- Understanding screenshots
- Understanding application state
- Navigating interfaces

Future flow:

User
↓
Request
↓
Screenshot
↓
Vision Analysis
↓
Plan
↓
Action

---

# Hybrid Intelligence

Long-term goal

The system should support multiple AI models.

Examples:

### Local

- Llama 3.2

Used for:

- Fast actions
- Offline usage
- Privacy

### Cloud

Potential:

- Copilot
- Claude
- GPT
- Codex

Used for:

- Complex planning
- Coding
- Architecture
- Research

Future architecture:

User
↓
Agent
↓
Model Router
├── Local LLM
└── Cloud AI
↓
Tools
↓
Windows

---

# Long-Term Goal

Create a personal desktop AI assistant capable of:

- Understanding intent
- Creating plans
- Executing actions
- Learning from history
- Working across applications
- Using multiple AI systems
- Operating as an intelligent operating-system layer

End state:

User
↓
AI Agent
↓
Windows

instead of:

User
↓
Windows