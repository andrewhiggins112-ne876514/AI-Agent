# Architectural Decisions

This document records the architectural decisions made during Phases 1 and 2,
plus the approved verification approach for Phase 3. Proposed Phase 3 behavior
is identified as design-only until implemented.

## Phase 1 - Local desktop assistant foundation

### Use local Llama 3.2

**Decision:** Use Llama 3.2 running locally through Ollama as the initial
language model.

**Rationale:** A local model supports private, offline-capable experimentation
and is sufficient for the prototype's initial Windows desktop tasks.

**Status:** Implemented in the GUI path.

### Build on direct Windows desktop tools

**Decision:** Use small Python functions for desktop actions, including
launching Notepad, taking screenshots, moving the mouse, listing visible
windows, and typing text.

**Rationale:** Direct tools provide a simple way to demonstrate desktop
automation without introducing a larger automation framework.

**Status:** Implemented in `scripts/tools.py`.

## Phase 2 - Structured action execution

### Use the Ollama HTTP API instead of the CLI

**Decision:** The GUI calls Ollama's local `/api/generate` HTTP endpoint rather
than launching `ollama run` for model responses.

**Rationale:** Captured CLI output showed terminal-style cursor-control
sequences and malformed fragments in testing. The HTTP API returns a response
field without relying on terminal rendering behavior.

**Request settings:** The GUI sends model `llama3.2`, the prompt, JSON format,
and `stream: false`.

**Status:** Implemented in the GUI.

### Use one JSON action envelope

**Decision:** The preferred model response is a JSON object with one
top-level `actions` array:

```json
{
  "actions": [
    {
      "action": "ACTION_NAME",
      "params": {}
    }
  ]
}
```

**Rationale:** A single envelope gives single-action and multi-action
responses one consistent shape for parsing and execution.

**Compatibility:** The parser also accepts direct action objects, action
arrays, and legacy text commands such as `OPEN_NOTEPAD` and `TYPE_TEXT: hello`.
All supported forms are normalized to an internal action list.

**Status:** Implemented in the parser and used as the preferred GUI prompt
schema.

### Validate actions before execution

**Decision:** Validate action names and parameters before invoking tools.

**Rationale:** Rejecting unknown actions, missing parameters, unexpected
parameters, and invalid values before dispatch reduces malformed model output
from reaching desktop functions.

**Status:** Implemented in `scripts/tools.py` for individual actions.

### Run model requests off the Tkinter thread

**Decision:** Run the Ollama HTTP request in a worker thread. Return the
result through a thread-safe queue, which the Tkinter main thread polls with
`root.after`.

**Rationale:** Synchronous inference on Tk's event thread made the UI appear
unresponsive and prevented timely handling of input.

**Status:** Implemented for model requests. Current action execution still
runs in the GUI response-processing path.

### Isolate requests

**Decision:** Process one GUI request at a time. Disable the Execute button and
request entry while a request is active, and guard the execution function
against duplicate submissions.

**Rationale:** Concurrent requests could interleave model results or trigger
overlapping desktop actions. Each worker result is associated with its
request before it is handled.

**Status:** Implemented in the GUI.

### Add a finite model request timeout

**Decision:** Limit each Ollama API request to 120 seconds and report timeout
or failure through the GUI lifecycle.

**Rationale:** A bounded wait prevents a stalled model request from leaving
the request UI disabled indefinitely.

**Status:** Implemented in the GUI.

## Phase 3 - Verification model

### Distinguish invocation success from outcome verification

**Decision:** Treat a tool returning without an exception as evidence that the
call completed, not necessarily proof that the requested desktop outcome
occurred.

**Proposed result states:** A verifier should report `VERIFIED`,
`UNVERIFIED`, or `FAILED`, with concise evidence or an explanation.

**Rationale:** Desktop actions have different observability. For example,
typing text cannot currently be reliably read back, so success should not be
claimed solely because the typing function returned.

**Proposed examples:**

- Verify Notepad launch by observing a visible Notepad window.
- Verify screenshot capture by checking that the output exists and is
  non-empty.
- Verify mouse movement by checking the observed pointer position.
- Treat a valid window-list result as the result of the listing action.
- Report typing as `UNVERIFIED` unless a deterministic read-back mechanism is
  available.

**Status:** Approved design in `PHASE3_DESIGN.md`; not yet implemented.

## Related Phase 3 execution principles

The approved Phase 3 design also specifies that verification runs after each
sequential action, a task is not reported as fully successful when a required
step is unverified or failed, and failures stop later steps by default.
Automatic retries are bounded and action-aware; actions that could duplicate
side effects, such as opening an application or typing text, are not retried
automatically.

These are design decisions for the upcoming Task Execution Engine, not claims
about current runtime behavior.
