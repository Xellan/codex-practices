# Multi-Agent Architecture for Codex — module №8

**Agreed policy:** adaptive delegation; separate Git worktrees for parallel writers; one local integration branch; verification of worker revisions; conservative cleanup. This module deliberately does not modify permissions, models, Codex configuration or AGENTS.md in user projects. The designed modules #4–#7 are **not implemented enforcement**.

## Boundaries and prerequisites

- Python 3.10+ and Git. Tests run locally on Linux; Windows and a real multi-agent Codex session are not yet verified.
- Codex is the orchestrator. The helper [agent_worktrees.py](../scripts/agent_worktrees.py) does not launch models/subagents, run a background daemon, push, create PRs or touch main/master.
- Native subagents **do not automatically get a separate worktree**. Before allowing a worker to write, launch or attach that worker to its actual worktree via a Codex frontend mechanism supported by the installed version; verify the worker's real current directory with `pwd` and `git rev-parse --show-toplevel`. If this is not possible, use **Single Writer**, not shared concurrent editing.
- Worktrees isolate the working checkout, **not** process privileges or network access; Git object storage, credentials, caches, tooling and external services can still be shared. The future Permissions (#4) and External Guardrails (#5) are required for stronger protections. Do not claim role prompts technically forbid writes.
- Explicit verification commands run locally and may have side effects. Review and authorize them. Git filters, helpers and project configuration may affect Git commands; the helper disables hooks for its own Git operations, not all effects of untrusted repositories.

## When to delegate

Use one writer for simple tasks and coupled changes. Read-only exploration may use native subagents without any worktrees. For independent writing tasks, assign an exclusive file/component scope, expected result, relevant context, evidence requirements and constraints to each worker. Start with 2–3 subagents only if practical and economical. One orchestrator owns integration, global decisions, final tests and Project Memory/Handoff.

## Stage 1 — prepare

Inspect the **actual target repository** and user approval before using this recipe. Do not mistake the codex-practices package for the target. Refuse dirty source state; never stash, reset or silently commit someone else's changes.

```sh
python3 /path/to/codex-practices/scripts/agent_worktrees.py --repo /absolute/project prepare --run auth-refactor --workers api client
```

The helper creates a sibling directory `.<project>-codex-worktrees/auth-refactor/` with separate `integration`, `api`, and `client` worktrees. Branch names are `codex-ma/auth-refactor/{integration,api,client}`. All are rooted at the same commit. It keeps a run manifest outside the target repository. Only letters, digits, underscore and hyphen are valid in run/worker IDs.

Make each writing agent work only in its own confirmed worktree. Worker agents create local commits; never push or modify protected branches. If the installation cannot route subagent tool calls to different directories, use separate explicitly launched Codex sessions or **Single Writer**.

## Stage 2 — verify, integrate, verify

Use **real project-specific test commands**. These are only illustrations:

```sh
python3 /path/to/codex-practices/scripts/agent_worktrees.py --repo /absolute/project verify --run auth-refactor --worker api -- python3 -m unittest discover -s tests
python3 /path/to/codex-practices/scripts/agent_worktrees.py --repo /absolute/project verify --run auth-refactor --worker client -- python3 -m unittest discover -s tests
python3 /path/to/codex-practices/scripts/agent_worktrees.py --repo /absolute/project integrate --run auth-refactor --workers api client
python3 /path/to/codex-practices/scripts/agent_worktrees.py --repo /absolute/project verify --run auth-refactor --worker integration -- python3 -m unittest discover -s tests
```

Each successful verification receipt records the tested `HEAD` SHA and test argv. Commits after verification invalidate the receipt. Integrate refuses dirty or unverified workers and merges **serially into a local integration branch**. On conflicts it aborts the current merge and preserves previously integrated work. Confirm actual file ownership, test coverage and risk beyond the helper's mechanical receipts; even a successful process exit does not establish full correctness. If needed verification cannot run, report **Partially Verified** or **Blocked** and keep worktrees.

## Stage 3 — status and safe cleanup

```sh
python3 /path/to/codex-practices/scripts/agent_worktrees.py --repo /absolute/project status --run auth-refactor
python3 /path/to/codex-practices/scripts/agent_worktrees.py --repo /absolute/project cleanup --run auth-refactor
```

Cleanup requires the final verified integration `HEAD`, all worker branch commits contained in integration, and no tracked, untracked **or ignored** files in any run-owned worktree. It uses plain `git worktree remove`, **never --force**. All Git branches and the manifest are preserved. Unknown or partial state is never deleted automatically; after an interrupted prepare, recover manually instead of force-cleaning.

The manifest is local coordination metadata, not a tamper-proof security audit. Only one orchestrator should operate on the same run; this lightweight helper does not provide a multiprocess transaction manager.

## Handoff, acceptance and limitations

The orchestrator reports task→agent ownership, commit IDs, actual checks, remaining worktrees, unresolved risks, and a single result. If already installed, use the Project Memory Skill (#3) for significant milestones; do not let workers concurrently write HANDOFF.md.

Installation-time tests (in codex-practices, **not** the target project):

```sh
python3 -m unittest discover -s tests -p 'test_agent_worktrees.py' -v
```

See [acceptance matrix](../tests/multi-agent-acceptance.md). Live Codex sessions, real permissions isolation and platform variations remain **not tested**. No scheduled monitoring, model calls or background workers are created by the helper.
