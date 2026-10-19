---
name: permissions-guardrails
description: Audit and launch Codex with a user-approved Review, Development or Infrastructure session. Use before a new session or when checking permission risks, not after every code edit.
---

# Permission profile workflow (#4)

This is a **recommendation and launch helper**, not an independent sandbox or a guarantee of per-command human approval.

Use the read-only local helper at scripts/codex_start.py, with an explicit target project:

    python3 scripts/codex_start.py --project /absolute/project

To use the guided TTY flow:

    python3 scripts/codex_start.py --project /absolute/project --interactive

It recommends a logical Review / Development / Infrastructure preset based on filenames, displays a redacted partial config audit, inspects external-instruction risk using optional #5, requests a profile choice and an explicit confirmation, checks the installed Codex CLI supports required flags, and then starts Codex. The helper does not silently change CODEX_HOME, user or project files, credentials, global profiles, Hooks or permissions.

**Distinguish logical launcher presets from native Codex named --profile files.** The helper uses explicit native --sandbox and --ask-for-approval flags; it does not create config profiles. Managed policies, native permission profiles and SSH/MCP/tool permissions may behave differently: no claim of full effective-policy inspection.

Broad Infrastructure deliberately uses danger-full-access **only if separately chosen for this launch**; it still uses on-request but approvals are **not enforced for every critical operation**. A powerful shell or preexisting root/SSH/MCP capability can bypass all text-only confirmation guidance. If critical-action confirmation is a hard requirement, use scoped credentials, remote-side approval gates or external isolation. Do not claim broad mode is safe for unsupervised destructive operations.

External guardrails integration: HIGH findings and incomplete scans each require separate acknowledgement. Missing scanner is **not clean**. In non-interactive scripted use, --risk-ack values are acknowledgement tokens, not authenticated human consent.

Never silently launch, rewrite user config, auto-install Hooks, grant elevation, or use --yolo. A launch is not proof that the chosen sandbox truly constrains every tool. Do not test against production servers; require real Codex E2E checks in a disposable workspace before claiming completion.
