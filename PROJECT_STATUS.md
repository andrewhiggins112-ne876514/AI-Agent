# Project Status

## Date

18 October 2026

---

## Repository Hygiene

Generated screenshots and runtime logs remain local. Python bytecode caches
and temporary files are not committed.

---

## Achievements

### Development Environment

- Python installed
- VS Code installed
- GitHub account created
- Ollama installed
- Llama 3.2 installed

---

### Automation

Working:

- Launch Notepad
- Type text
- Move mouse
- Take screenshots
- List windows

---

### Agent

Working:

User Request
↓
Llama 3.2
↓
Action Plan
↓
Tool Execution

Example:

Request:
open notepad and type hello

Plan:
OPEN_NOTEPAD
TYPE_TEXT: hello

Result:
Notepad launched
Text entered

---

## Current Main Files

tools.py
agent_ui.py
PROJECT_VISION.md
ROADMAP.md

---

## Known Issues

- UI BUG #1 (Execute button hidden unless window manually resized)
- GUI layout needs improvement.
- Tool system still simplistic.
- The separate CLI prototype does not use the GUI's current Ollama API and structured-action flow.

---

## Testing Results

### Phase 2 Retest Results

PASS
- open notepad
- take a screenshot

PARTIAL
- open notepad and type hello
  Returned only OPEN_NOTEPAD; no TYPE_TEXT action was produced.

FAIL
- open notepad and type hello world
  ANSI control characters detected in model output, resulting in invalid JSON.

### Phase 2 Retest #2

PASS
- open notepad
- take a screenshot

FAIL
- open notepad and type hello
- open notepad and type hello world

FAIL
- Enter key execution

Status:
Multi-step planning reliability under investigation.

### Phase 2 Retest #3

PASS
- open notepad
- take a screenshot

FAIL
- open notepad and type hello
  Returned LIST_WINDOWS.

FAIL
- open notepad and type hello world
  Returned {"actions":[...]}.

Status:
Action schema consistency under investigation.

### Phase 2 Completion Verification

PASS
- open notepad
- take a screenshot
- open notepad and type hello

Phase 2 Structured Actions is complete. The GUI uses Ollama's local API with JSON mode, action schema normalization, validation, structured execution results, and legacy parser compatibility. The GUI request flow also uses a worker thread, timeout, and duplicate-submission guard.

Earlier failed and partial retest results above are historical; they were resolved sufficiently to complete Phase 2's core acceptance tasks. Longer compound-request planning and verification are Phase 3 work.

## Phase 2 Schema Alignment

Purpose:
Standardise on:

{
  "actions":[...]
}

while maintaining backward compatibility.

---

## Current Milestone

Phase 3 - Task Execution Engine

---

## Milestones

✅ Local LLM Running

✅ Desktop Automation

✅ AI Tool Execution

✅ Multi-Step Action Execution

✅ Structured Actions

⬜ Memory

⬜ Vision

⬜ Hybrid Models

⬜ Personal Assistant Layer

---

## Architecture Snapshot

Current Runtime Flow

User
↓
AI Agent UI
↓
Ollama
↓
Llama 3.2
↓
Action Parser
↓
tools.py
↓
Windows

Example

User:
open notepad and type hello

Llama:
OPEN_NOTEPAD
TYPE_TEXT: hello

Executor:
open_notepad()
type_text("hello")

Result:
Notepad opened
Text entered