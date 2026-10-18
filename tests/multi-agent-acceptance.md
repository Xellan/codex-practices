# Multi-Agent Architecture — acceptance matrix (#8)

- MA-01 — Simple task: no unnecessary subagents or worktrees.
- MA-02 — Parallel read-only exploration: agents use bounded scope, orchestrator checks evidence.
- MA-03 — Dirty source repo: prepare refuses without stash/reset or data loss.
- MA-04 — Prepare: branches/worktrees share one base; original HEAD remains unchanged.
- MA-05 — Worker launched in wrong CWD: do not write; switch to verified worktree/session or Single Writer.
- MA-06 — Nonzero verification exit cannot issue a PASS receipt.
- MA-07 — New commit after verification invalidates receipt.
- MA-08 — Independent workers integrate only into the new local integration branch.
- MA-09 — Overlapping changes conflict: abort current merge; retain prior integration and branches.
- MA-10 — Final check incomplete: do not cleanup; report Partially Verified / Blocked.
- MA-11 — Agent failure or interrupted setup: keep partial work for manual recovery.
- MA-12 — Dirty, untracked and ignored files block automatic cleanup.
- MA-13 — Verified clean run: remove run-owned worktrees without --force; branches remain.
- MA-14 — No unattended push, PR creation, protected branch changes or privilege escalation.
- MA-15 — Single Handoff writer: orchestrator only; evidence and blockers included.
- MA-16 — Worktree is not a security sandbox: validate real permission boundaries separately.

Automated checks: `python3 -m unittest discover -s tests -p 'test_agent_worktrees.py' -v`.
Live Codex execution remains untested; test only in a disposable project after explicit approval.
