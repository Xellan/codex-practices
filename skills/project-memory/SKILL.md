---
name: project-memory
description: Save or restore project context. Use when continuing a previous task, after a significant milestone, or when the user requests a session handoff or wants to preserve a confirmed lesson.
---

# Project Memory and Handoff

Use this skill only inside the **confirmed target project**. It is not a background service and must not be run on every message. Source instructions: recipes/setup-project-memory.md in the codex-practices package.

## Restore

1. Verify the actual project root and read its active AGENTS.md and context pointers.
2. Determine the agreed Handoff path (default: docs/context/HANDOFF.md).
3. Run the helper from the installed skill, using an **absolute --root** path:

    python3 .agents/skills/project-memory/scripts/handoff.py --root /absolute/project show

Exit code 3 means no active Handoff exists. Do not fabricate past state. Compare the saved branch, references and age with live Git/code/service facts; note any mismatch. The dated Handoff is not proof that a service remains healthy.

## Save at milestones or on request

Significant milestones include decisions affecting future work, a tested implementation checkpoint, an unresolved blocker or an explicit transfer request. Do not save after routine messages or every small action.

- Inspect actual changes and test results. Label unrun checks NOT RUN; never invent a PASSED status.
- Exclude secrets, credentials, private URLs, unneeded raw logs and chat transcripts.
- First use 'show' to obtain the current SHA-256. On all subsequent updates pass --expect-sha with that value. If stale, reread and reconcile; never overwrite a newer handoff blindly.
- Save one **complete, concise snapshot**: goal, what completed, next step, blockers, verification and references. An initial save does not need --expect-sha.
- Mark status active / blocked / closed as appropriate; closed is a task state, not live system health.

Example initial save:

    python3 .agents/skills/project-memory/scripts/handoff.py --root /absolute/project save --goal "Implement parser" --done "Added parser module" --check "PASS: unit tests" --next-step "Review error handling" --reference "src/parser.py"

Later save (use the real digest from show):

    python3 .agents/skills/project-memory/scripts/handoff.py --root /absolute/project save --expect-sha SHA_FROM_SHOW --goal "Implement parser" --done "Added validation" --check "NOT RUN: staging test" --next-step "Test on staging"

The helper uses atomic replacement and POSIX directory locking. It refuses unmanaged existing handoff files and symlink paths; it does not create empty Handoffs on install. Requires Python 3.10+ on Linux/macOS.

## Permanent knowledge

- AGENTS.md: short enduring instructions and pointers only, never running status.
- Existing ADR/runbook/documents: authoritative decisions or diagnosed lessons; use them rather than create duplicate stores.
- HANDOFF.md: only current task snapshot. Keep it short, read it when resuming.
- Native Codex Memories: optional helpful recall, **not** authoritative current project state.

If a new decision/lesson merits durable recording, update its existing owner within approved scope, or propose a new DECISIONS.md/LESSONS.md only after user agreement. There is no RAG or vector database.

## Limitations

Milestone detection is best-effort agent behavior guided by AGENTS.md, not guaranteed event hooks. The helper does not run at Codex shutdown, does not handle Windows or synchronize different machines, and never changes Codex configuration on its own.
