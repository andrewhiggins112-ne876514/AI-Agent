# NEW AI STARTUP CHECKLIST

Use this short checklist at the start of a new Jarvis agent session. Version 4 is authoritative.

## Startup Checklist

1. **Read** [JARVIS_MASTER_HANDOVER_v4.pdf](docs/JARVIS_MASTER_HANDOVER_v4.pdf) completely. Follow its page 2 instructions and Section 3 startup sequence.
2. **Check Git non-destructively:** inspect live status, current branch, and HEAD. Do not stage, modify, discard, reset, clean, commit, or push.
3. **Note discrepancies** between the live repository and Version 4’s snapshot in your first reply. Do not silently reconcile or overwrite the snapshot.
4. **Apply the hard constraints:**
   - Free models and free/open-source packages only; no paid services or APIs.
   - Stay within the recorded PC limits: i7-8700K, 32 GB RAM, GTX 1080 Ti 11 GB, Windows.
   - Microphone exists but is **NOT connected**; no voice work.
   - Stop and ask if anything is ambiguous or outside the approved slice.
5. **Ask exactly this question, then wait for a clear answer:**

   > Would you like me to continue from the last recommended milestone (Phase 5.3.1 Read-only Testing Awareness), or would you like to change direction? Please state any scope limits or new constraints.

6. **Wait.** Until the human gives a clear scoped instruction, do not implement, change files, run tests, install packages, or expand scope. After approval, work only within the approved scope.

## Required Reporting Format

After approved work, or when stopping, report using Version 4 Section 7:

```text
FILES CHANGED:
[list or “none”]

WHAT WAS DONE:
[concrete summary]

WHAT WAS NOT DONE / LEFT FOR LATER:
[list]

TESTS PERFORMED:
[exact commands and results, or “none – not approved”]

TESTS NOT PERFORMED:
[list]

RISKS / OPEN QUESTIONS:
[list]

NEXT RECOMMENDED STEP (not started):
[one clear recommendation]

WAITING FOR YOUR APPROVAL ON: [specific item or “none”]
```
