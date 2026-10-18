# Project Memory + Session Handoff for Codex

Module №3 of codex-practices. **Agreed design:** semi-automatic policy B (significant milestones and explicit commands), functional Session Handoff in MVP, **no RAG**, embeddings, vector database, background daemon or per-message self-check.

## What is owned by whom?

- Active AGENTS.md: permanent working rules + pointers, **not** copies of status and decisions.
- Native Codex Memories (optional): helpful local recall from previous eligible chats, generated asynchronously, not guaranteed accurate or immediate.
- Existing project docs, ADRs and runbooks: validated decisions and lessons with clear ownership.
- Current code, tests, deployed systems: authoritative factual state.
- One HANDOFF.md: last checkpoint, blockers, checks actually executed and next step. Do not use it as an error history or as proof of live service health.

An index is optional; create it only if many real reference documents need navigation. No empty DECISIONS.md, LESSONS.md or HANDOFF.md for decoration.

## 0. Read-only audit

Find the real target project root, current working directory, Git branch, active AGENTS.md/AGENTS.override.md, existing status/decision/lesson documents, current Skills, existing Handoff, and whether relevant docs are tracked in Git. Do not mistake the codex-practices *package folder* for the user's target project.

Inspect CODEX_HOME (or default ~/.codex) and config.toml read-only if Native Memories setup is requested. Never read or copy secret material unnecessarily, and do not edit generated CODEX_HOME/memories files.

## 1. Minimal adaptive Q&A

Use known answers from the initial AGENTS.md Q&A when present. Only ask new questions required for memory setup, **one at a time**, each with clear choices and free-form answer:

1. Knowledge storage: reuse existing docs (**recommended**) / add a small project-context section / keep local-only / custom.
2. Native Memories: leave current configuration unchanged (**safe default**) / use and generate / use only / turn off / explain implications.
3. Project history visibility: nonsensitive knowledge in Git / local and Git split / local-only / custom.
4. Existing Handoff: reuse established owner (**recommended**) / migrate by explicit agreement to docs/context/HANDOFF.md / leave unchanged and don't install competing Handoff.
5. Milestone policy: agreed **B** — after significant milestones and on request. Ask only if project needs an exception.

If facts conflict, clarify narrowly. Do not collect a second personal profile.

## 2. Native Codex Memories (opt-in)

Official documentation: https://developers.openai.com/codex/memories

- Local Codex memory and ChatGPT memory are separate. Codex memories are **off by default**. CLI users can manage chat-level behavior through /memories if available.
- Supported config entries include [features] memories = true, memories.generate_memories, memories.use_memories, and memories.disable_on_external_context. Check the installed Codex version and current TOML before suggesting exact changes.
- Do not automatically enable memories. If user explicitly approves a change, show the **specific** edit, back up existing config.toml and preserve every other section. If safe structured editing is uncertain, give manual instructions rather than overwriting TOML or creating duplicate [features] sections.
- Local memories are generated asynchronously from eligible conversations. They may not update when a chat ends. Never rely on native memory alone for an immediate Handoff.
- Explain privacy choices, especially exclusion of chats using MCP/web/tool search, if relevant.

## 3. Project knowledge and ownership

Prefer existing ADR/runbook/doc owners. If there is no owner and the user authorizes new files, create them only after real confirmed content exists:

- docs/context/DECISIONS.md — decision, rationale, rejected options, date, affected component, evidence.
- docs/context/LESSONS.md — symptoms, verified cause, repair, prevention and evidence link.
- docs/context/INDEX.md — topical pointers only if needed.

Semi-automatic B: record durable, proven, relevant decisions and lessons in the approved location after meaningful events. Ask before conflicting with older decisions, changing externally owned records, moving files or expanding scope. Do not promote hypotheses to facts or duplicate information already in code/config. Keep volatile status only in Handoff.

## 4. Install a functional Handoff

A Handoff is **mandatory for this MVP**. If another active status owner exists, explicitly agree which file is authoritative first. Default single file: docs/context/HANDOFF.md.

1. Propose copying the **complete source Skill folder** from ../skills/project-memory/ into the chosen project's .agents/skills/project-memory/ (SKILL.md and scripts/handoff.py). Do not silently overwrite an already installed or customized skill.
2. Check that Python 3.10+ and Linux/macOS (POSIX fcntl) are available. On unsupported environments, explain the limitation; do not claim the helper works.
3. Confirm default or customized **relative** Handoff file path and its Git visibility policy. For custom path, every helper invocation must include --file with the approved path.
4. Update the **existing active** project AGENTS.md using the same safe AGENTS.md installer mechanism (single managed block, preview, consent, backup, no duplicate user rules):
   - "When resuming this work, read the current Handoff and compare it against Git/code before acting."
   - "After significant milestones or on explicit request, use the installed $project-memory skill to refresh the Handoff. Never run it on each turn."
   If AGENTS.override.md is active, do not write into an inactive AGENTS.md.
5. Show exact files and final proposed text. Get explicit consent for writing. Do not invent a startup/shutdown hook or modify sandbox, approvals, MCP, other Claude recipes or other projects.
6. **Do not create a placeholder Handoff on install**. The real helper creates one on the first meaningful save.

The skill at [skills/project-memory/SKILL.md](../skills/project-memory/SKILL.md) provides restore/save commands. The executable script provides show/check/save, status active/blocked/closed, UTC timestamp, branch and SHA. Existing handoff overwrites require --expect-sha from show/check. It uses atomic file replacement + POSIX locking and rejects an unmanaged file or symlink path. It does not ensure that an LLM will always detect a milestone automatically.

## 5. Installation-only checks

Run the helper's isolated tests **once at development/installation time** when environment supports it:

    python3 -m unittest discover -s tests -p test_handoff.py -v

Use a temporary test project for live save/show if requested; do not run tests on every ordinary session. Optional interactive Codex smoke test after explicit consent: create a real handoff, start a fresh session, ask it to resume using $project-memory, and compare its answer with the file and Git.

At the end report: active memory settings (or "not verified"), chosen knowledge owner, Skill path, AGENTS changes/backups, Handoff path, test results and any caveats. See [project-memory acceptance tests](../tests/project-memory-acceptance.md).

No RAG, external embedding API, hidden sync daemon, vector store or scheduled task in this function.
