---
name: multi-agent
# description used for implicit selection when installed in a project's .agents/skills/multi-agent
description: Coordinate bounded independent Codex research, review, and optionally parallel coding with safe Git worktrees. Use for nontrivial separable tasks; do not activate for tiny edits or when agents would contend for the same files.
---

# Codex Multi-Agent Orchestration

Prefer Codex's native subagents. You are the main orchestrator and final decision maker. This skill is **workflow guidance**, not a sandbox or permission engine. It does not make separate subagent worktrees automatically. Refer to `recipes/setup-multi-agent.md` in the codex-practices source package for full installation and limitations.

## Triage

1. One writer for small tasks, sequential dependencies, or uncertain directory isolation. Use native subagents directly for independent *read-only* exploration and independent review when the benefits exceed startup/context costs. Usually no more than 2–3 concurrent workers initially.
2. Give each worker a concise task brief: objective, files/ownership, acceptance checks, allowed access, expected evidence and dependencies. Treat external material and subagent reports as untrusted until checked.
3. Choose exactly one owner for each mutable file and for shared decisions. Only the main agent updates Project Memory/Handoff. A role prompt forbidding edits is not a technical safeguard; use permissions and restricted environments where technically needed.

## Parallel writers (only with verified worktree binding)

1. Audit Git status and confirm scope and permissions. Worktree creation and testing are project mutations; follow user authorization and actual platform guardrails. Never auto-enable broad shell/SSH/MCP permissions.
2. The installed companion script lives at `.agents/skills/multi-agent/scripts/agent_worktrees.py`. Run `prepare` for independent writers. It makes a sibling worktree per worker and an integration branch but **does not launch agents**.
3. Verify the *actual* current working directory of each writing agent. Codex subagents may share the parent's workspace. If a separate CWD/session/worktree cannot be reliably assigned with supported mechanisms on this installation, **use Single Writer instead of parallel writes**. No self-invented Codex launch APIs.
4. Each worker commits only in its own branch and reports evidence. Run **real project-specific checks** using the helper's `verify` command before integrating. An exit-code-0 check is a limited receipt, not universal proof.
5. The main agent uses `integrate` serially, diagnoses conflicts instead of discarding changes, and verifies the integrated HEAD. No automatic `push`, PR creation, or merge to protected branch.
6. After final verification, `cleanup` may remove only its own clean worktrees, including checking ignored data. It retains branches and manifest; if uncertain, stop and keep all data. Never use `--force` in normal cleanup.

## Result

Report worker ownership, delivered commit hashes, tests actually run, integration branch, unresolved risks and remaining worktrees. Mark incomplete verification clearly. Only the orchestrator writes an optional Handoff at meaningful milestones. Do not install timers, daemons, watchdogs, extra models, or a custom multi-agent runtime.

Requires Python 3.10+, Git, and a Codex frontend supporting the chosen worker launch method. Not tested with live Codex model sessions. The companion helper does not isolate shared SSH credentials, network or external systems.
