# AI-Agent Roadmap

This roadmap is intentionally grounded in the current repository and its actual implementation. It reflects what exists today in the codebase: a simple local AI desktop automation prototype, not an idealized future architecture.

## Current milestone

Phase 3 - Task Execution Engine

## Current state

The project currently provides a local Windows desktop automation prototype. Its GUI sends requests to Ollama's local `/api/generate` endpoint, requests JSON-formatted action plans, normalizes supported response formats, validates actions, and executes them through the existing desktop tools.

What is already implemented:

- CLI-based agent loop in [scripts/ai_agent.py](scripts/ai_agent.py)
- Tkinter GUI in [scripts/agent_ui.py](scripts/agent_ui.py)
- Tool registry and desktop actions in [scripts/tools.py](scripts/tools.py)
- Single-action automation using pyautogui and win32gui
- Local model usage through Ollama's HTTP API in the GUI
- JSON action schema, ANSI response cleanup, asynchronous model requests, request timeout, and duplicate-request guard
- Simple examples for Notepad, screenshots, mouse control, typing, and window listing

What is already working:

- Open Notepad
- Take a screenshot
- Move the mouse
- List visible windows
- Type text into the active app
- Execute single and multi-action JSON responses from a natural-language request
- Preserve compatibility with direct JSON objects, JSON arrays, and legacy action text in the parser

What is still missing or weak:

- persistent memory
- configuration system
- unified structured-action support across every prototype entry point
- task-level orchestration, progress tracking, and reliable multi-step verification
- success verification after actions
- vision-based desktop understanding
- safe execution checks
- stable project structure beyond prototype scripts

---

## Phase 1: Stabilize the current prototype

Status: In progress / immediate priority

Goal:

Reduce brittleness in the existing agent loop and make the current desktop automation reliable.

Tasks:

- keep one clear primary execution path for the agent
- standardize the action format returned by the model
- handle unknown actions and model failures gracefully
- add visible output for tool success/failure
- treat the current scripts as examples and not as the main runtime path

Deliverable:

A stable base where the existing actions consistently work without crashing or silently failing.

---

## Phase 2: Structured action execution

Status: Complete

Goal:

Use a consistent JSON action envelope as the preferred format while retaining compatibility with supported legacy formats.

Tasks:

- [x] JSON actions using the `{"actions": [...]}` envelope
- [x] Normalize wrapped objects, direct action objects, arrays, and legacy text into an action list
- [x] Validate supported action names and parameters before execution
- [x] Return structured execution results
- [x] Display raw/sanitized model output, parsed actions, and execution results in the GUI
- [x] Use Ollama's local HTTP API with JSON mode
- [x] Run inference off the Tkinter UI thread, with a timeout and duplicate-request guard
- [x] Confirm core GUI tasks: open Notepad, take a screenshot, and open Notepad and type `hello`

Deliverable:

The GUI uses the normalized action-list interface, validates actions before execution, reports structured results, and retains parser compatibility with older response formats. Phase 2 is complete; model action selection and task-level planning remain opportunities for Phase 3 improvement.

---

## Phase 3: Task Execution Engine

Status: Current milestone

Goal:

Turn the existing validated actions into dependable task execution. This phase builds task lifecycle and verification around the current tool interface; it does not imply that full task orchestration already exists.

Tasks:

- split a user request into ordered steps
- handle simple tasks such as:
  - open a program and type content
  - open Notepad and create a short note
  - capture a screenshot after an action
- track pending, running, completed, failed, and cancelled task states
- verify completion after each step before reporting success
- stop safely, retry, or request clarification when a step fails or the plan is incomplete

Deliverable:

A lightweight task execution engine that sequences validated actions, tracks progress, and verifies outcomes.

---

## Phase 4: Persistent memory

Status: Planned

Goal:

Add memory in the simplest useful form so the assistant feels less stateless.

Tasks:

- store recent requests and outcomes
- store recurring app preferences
- store user-specific habits or repeated commands
- remember the last-used application or project context
- create a basic memory directory and data store

Deliverable:

An initial memory layer that adds continuity across sessions without needing a heavy semantic system yet.

---

## Phase 5: Configuration and personalization

Status: Planned

Goal:

Make the prototype easier to run and adapt.

Tasks:

- add configuration for model name, paths, and app defaults
- add basic user profile settings
- store log and screenshot paths in one place
- add toggles for verbose output and safety checks
- improve the UI layout and readability

Deliverable:

A more usable desktop agent that can be configured beyond a single machine-specific setup.

---

## Phase 6: Screenshot-based verification

Status: Planned

Goal:

Use the current screenshot capability as a verification layer, not just a demo action.

Tasks:

- capture screenshots before and after key actions
- compare images to determine whether the expected result occurred
- detect whether an app opened
- check if a window is visible or active
- use results to decide whether to retry or continue

Deliverable:

A basic visual confirmation system that reduces blind execution and improves reliability.

---

## Phase 7: Tool expansion and practical workflows

Status: Planned

Goal:

Add the next most useful desktop tools without abandoning the current prototype.

Suggested expansions:

- file browser tools
- folder creation and organization
- browser opening and simple navigation
- app switching and focus management
- clipboard support
- more window-management actions

Deliverable:

The agent can handle more real-world personal desktop tasks beyond the current toy examples.

---

## Phase 8: Hybrid model support

Status: Future

Goal:

Allow use of both local and cloud models while keeping local Ollama as the default.

Tasks:

- add model abstraction
- route simple tasks to local models
- allow heavier reasoning tasks to use a stronger provider when needed
- keep fallback logic for model failures

Deliverable:

The project becomes more flexible without losing privacy and speed benefits from local inference.

---

## Phase 9: Long-term personal assistant

Status: Future

Goal:

Move from automation to an assistant that can maintain goals, learn preferences, and support ongoing work.

Tasks:

- long-term user goals
- project context tracking
- routine task automation
- recurring daily workflows
- smarter memory and planning over time

Deliverable:

The system behaves less like a command executor and more like a personal desktop assistant.

---

## Recommended sequence for the next milestones

The next practical milestone order is:

1. Phase 3: build task execution, progress tracking, and verification on the completed structured-action foundation
2. add persistent memory
3. add screenshot-based verification and desktop understanding
4. improve configuration and usability
5. expand workflow tools
6. add hybrid model support

This order respects the current codebase and avoids jumping too far ahead of the working implementation.

## Summary

The repository is a local desktop automation prototype with Phase 2 Structured Actions complete. The current milestone is Phase 3 - Task Execution Engine. The next work is to make multi-step requests reliable through explicit task state, ordered execution, and outcome verification before advancing to memory, vision, or hybrid models.
