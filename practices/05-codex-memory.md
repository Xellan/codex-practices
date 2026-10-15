# Codex Project Memory — knowledge and continuity

Unlike Claude Code MEMORY.md, Codex has its own **optional local Native Memories**, which are asynchronous and are not a real-time status tracker.

Use three non-duplicating layers:
1. Native Memories — opt-in recall.
2. Existing project docs — verified durable decisions, runbooks and lessons.
3. **One current Handoff** — snapshot of task state and next step, written after significant milestones or explicit transfer.

AGENTS.md has concise references and behavioral instructions, never an entire memory archive. Do not duplicate facts, invent documents or copy a live service's status into static memory. Source code, Git and live service checks override stale handoff notes.

No RAG, vector DB, daemon or periodic memory audits.

Setup: [project-memory recipe](../recipes/setup-project-memory.md). Functional Skill: [project-memory SKILL.md](../skills/project-memory/SKILL.md).
