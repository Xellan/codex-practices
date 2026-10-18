# Permissions & Guardrails — Codex module №4

This recipe is **opt-in**, not an OS security boundary. Read the actual Codex CLI `--help` first. The companion [launcher](../skills/permissions/scripts/codex_start.py) is Python 3.11+, stdlib only.

## Session policy

- **Review**: `read-only`; **Development**: `workspace-write`; **Infrastructure**: `workspace-write` unless broad access is explicitly chosen for this session.
- The launcher recommends a profile from local filenames **as a hint** only. It never selects a profile and launches silently.
- Every launch needs `--profile`, `--launch`, and `--confirm LAUNCH_PROFILE`. Broad Infrastructure additionally needs `--broad-infra --confirm BROAD_INFRA_THIS_SESSION`. In broad mode it passes `--sandbox danger-full-access --ask-for-approval on-request`, **never --yolo**. This broad sandbox can permit shell/root/SSH/MCP operations that no textual rule or simple Hook can reliably intercept. Approvals are not a guarantee for all already-allowed actions. For hard boundaries use external privilege, network and credential isolation.
- No permanent edits to `CODEX_HOME`, no background daemon, no secret collection and no automatic elevation. Managed config may take precedence; inspect active policies. To revoke broad access, end the session and launch again in a narrower sandbox.

## Workflow

Run read-only preview before any launch:

```sh
python3 /path/to/codex-practices/skills/permissions/scripts/codex_start.py --project /absolute/project
```

Launch after reviewing recommended vs chosen profile:

```sh
python3 /path/to/codex-practices/skills/permissions/scripts/codex_start.py --project /absolute/project --profile development --launch --confirm LAUNCH_PROFILE
```

Infrastructure broad access should only be offered after explaining that critical operations cannot all be intercepted in an unrestricted environment. Explicitly approved broad access remains valid **for the current session**. User instructions and optional Hooks can request separate confirmation for critical actions but do not create guaranteed approval gates for all shells/MCP/SSH.

Read existing config, user/project instructions and hooks read-only. Never replace a customized config. Verify the actual CLI version and `--sandbox` / `--ask-for-approval` support before live use. If a native permissions profile is available use it; don't invent a new format.

## Tests

```sh
python3 -m unittest discover -s tests -p test_codex_start.py -v
```

See [acceptance](../tests/permissions-acceptance.md). No live Codex or external server tests have been performed. Dependencies #5 and later can add preflight controls, but are not implied by this module alone.
