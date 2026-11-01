# CURRENT PROJECT STATE

**State type:** Current snapshot only; replace this document when verified project state changes.  
**Last verified:** 2026-11-01
**Verification scope:** Git branch, worktree status, HEAD, static read-only test inventory, and the initial Testing Awareness implementation. No tests or scripts were run.

## Project Identity

- **Project:** Jarvis.
- **Repository:** AI-Agent.
- **Subsystem:** Developer Agent is a supervised Jarvis subsystem, not a standalone project.

## Authoritative Startup Guidance

[JARVIS_MASTER_HANDOVER_v4.pdf](docs/JARVIS_MASTER_HANDOVER_v4.pdf) is the authoritative agent-startup and next-action document. Follow its startup sequence, constraints, scope boundaries, direction question, and Section 7 reporting format. This file is a current-state snapshot and does not override Version 4.

Persistent agent instructions also live in [.github/copilot-instructions.md](.github/copilot-instructions.md). This file contains the hard constraints, preferred local models, working style, documentation responsibilities, and startup behaviour for agents working on this project. A future Version 5 handover may reference this file.

## Current Development State

- **Latest implemented capability:** Initial Phase 5.3.1 read-only test inventory; latest completed milestone remains Phase 5.2.4 Proposal Review Workflow.
- **Next recommended slice:** Phase 5.3.1 Read-only Testing Awareness.
- **Phase 5.3.1 status:** The initial read-only inventory function is implemented in `scripts/testing_awareness.py`. It reports test-file paths and conventional test-configuration filename candidates from a supplied `RepositoryIndex`; it does not inspect configuration contents or execute commands/tests. Missing configuration candidates and incomplete source indexes are reported as incomplete/unknown. Fixture/platform discovery and proposal-to-test mapping are not implemented.
- **Test inventory:** Nine `unittest` files under `tests/` contain 127 statically declared test methods. The latest recorded full-suite result is 127 tests passed on 2026-10-30 using `python -m unittest discover -s tests -v`; this historical result was not rerun.
- **Additional test-related scripts:** `scripts/test.py` is a print-only script. `scripts/mouse_test.py`, `scripts/typing_test.py`, and `scripts/ui_test.py` are separate GUI-oriented scripts; the mouse and typing scripts can interact with the desktop.
- **Platform and dependencies:** Tests import Windows-facing dependencies through `scripts.tools`, including `pyautogui`, `win32gui`, and `win32process`. No dependency manifest or test-runner configuration was found in the repository inventory.
- **Next recommended step (not started):** After review, decide whether to add focused tests for the inventory function and/or expand read-only fixture and platform-constraint reporting. Proposal-to-test mapping remains deferred.
- **Current branch:** `main`.
- **Latest commit:** `e5484bb43194cbbda747679b474b33f097708435`.
- **Repository status:** Worktree was clean at the pre-change check; the approved implementation and state update are now uncommitted.
- **Version 4 snapshot note:** Its recorded repository baseline (`31b4dd8d059bcc56733622b20aa7f3f9b94f999d`) differs from the live HEAD above.

## Non-Negotiable Constraints

- Use **free models only** and **free/open-source packages only**. Do not introduce paid APIs, commercial SDKs, or paid services. If a capability appears to require one, stop and report the limitation and any free alternatives.
- Design within the recorded PC limits: **Intel i7-8700K, 32 GB RAM, NVIDIA GTX 1080 Ti with 11 GB VRAM, Windows**.
- A microphone exists but is **NOT connected**. Do not undertake voice, wake-word, speech-to-text, or text-to-speech work.
- Stop and ask whenever a request is ambiguous or outside the explicitly approved scope.
- Do not treat a recommendation or design discussion as implementation approval. Commit and push require separate approval.

## Hardware / Scope Notes

- **Microphone:** Present but not currently connected; voice work is out of scope until it is connected and explicitly authorized.
- **Testing Awareness boundary:** Read-only inventory and mapping only. No tests, commands, subprocesses, or test frameworks may be executed without explicit approval. Do not invent runnable commands when configuration is missing or malformed. Individual proposal-to-test mapping remains deferred.

## Known Open Questions

- Whether evidence in Testing Awareness should be bound to a Git revision or content hashes.
- Which test configuration formats and platform constraints the initial inventory should support.
- How fixture and platform constraints should be represented in the inventory.
- Any changes to hardware or software facts since the Version 4 handover.

## Resume Rule

At the start of a new agent session, read Version 4 completely, perform only non-destructive Git checks, note discrepancies, ask the exact direction question in Version 4, and wait for a clear scoped answer before proceeding.
