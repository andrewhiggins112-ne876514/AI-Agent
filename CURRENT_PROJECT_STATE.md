# CURRENT PROJECT STATE

**State type:** Current snapshot only; replace this document when verified project state changes.  
**Last verified:** 2026-10-30 23:15 UTC  
**Verification scope:** Git branch, worktree status, latest commit, and comparison with `origin/main`.

## Project Identity

- **Project:** Jarvis.
- **Repository:** AI-Agent.
- **Subsystem:** Developer Agent is a supervised Jarvis subsystem, not a standalone project.

## Authoritative Startup Guidance

[JARVIS_MASTER_HANDOVER_v4.pdf](docs/JARVIS_MASTER_HANDOVER_v4.pdf) is the authoritative agent-startup and next-action document. Follow its startup sequence, constraints, scope boundaries, direction question, and Section 7 reporting format. This file is a current-state snapshot and does not override Version 4.

Persistent agent instructions also live in [.github/copilot-instructions.md](.github/copilot-instructions.md). This file contains the hard constraints, preferred local models, working style, documentation responsibilities, and startup behaviour for agents working on this project. A future Version 5 handover may reference this file.

## Current Development State

- **Latest implemented capability:** Phase 5.2.4 Proposal Review Workflow.
- **Next recommended slice:** Phase 5.3.1 Read-only Testing Awareness.
- **Approval status:** Phase 5.3.1 has not been approved for implementation and has not started. A recommendation is not approval.
- **Latest recorded full test run:** 127 tests passed on 2026-10-30 using `python -m unittest discover -s tests -v`. This was not rerun as part of this state check.
- **Current branch:** `main`.
- **Latest commit:** `656dc36ff46a46aa4e8c201bc805c2494140aa37` — `Project continuity system`.
- **Repository status:** Worktree clean; `main` matches `origin/main` (0 ahead, 0 behind) at verification.
- **Version 4 snapshot note:** Its recorded repository baseline predates the `Project continuity system` commit. The live Git state above was checked on 2026-10-30 and should be used for current branch/revision status.

## Non-Negotiable Constraints

- Use **free models only** and **free/open-source packages only**. Do not introduce paid APIs, commercial SDKs, or paid services. If a capability appears to require one, stop and report the limitation and any free alternatives.
- Design within the recorded PC limits: **Intel i7-8700K, 32 GB RAM, NVIDIA GTX 1080 Ti with 11 GB VRAM, Windows**.
- A microphone exists but is **NOT connected**. Do not undertake voice, wake-word, speech-to-text, or text-to-speech work.
- Stop and ask whenever a request is ambiguous or outside the explicitly approved scope.
- Do not treat a recommendation or design discussion as implementation approval. Commit and push require separate approval.

## Hardware / Scope Notes

- **Microphone:** Present but not currently connected; voice work is out of scope until it is connected and explicitly authorized.
- **Recommended initial Testing Awareness boundary:** Read-only inventory and mapping only. Do not execute tests, commands, subprocesses, or test frameworks. Do not invent runnable commands when configuration is missing or malformed.

## Known Open Questions

- Whether evidence in Testing Awareness should be bound to a Git revision or content hashes.
- Which test configuration formats and platform constraints the initial inventory should support.
- Any changes to hardware or software facts since the Version 4 handover.

## Resume Rule

At the start of a new agent session, read Version 4 completely, perform only non-destructive Git checks, note discrepancies, ask the exact direction question in Version 4, and wait for a clear scoped answer before proceeding.
