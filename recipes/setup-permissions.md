# Permissions & Guardrails — Codex module №4

**Read-only by default; explicit consent before launching.** Tested helper: Python 3.11+, no external packages. This is an opt-in launcher, not an OS policy broker or a substitute for restricted remote credentials.

## Launch policy

The launcher has three **logical presets** (not pre-written native --profile TOML files):

| Preset | CLI sandbox | Approval |
| --- | --- | --- |
| Review | read-only | on-request |
| Development | workspace-write | on-request |
| Infrastructure | workspace-write | on-request |
| Infrastructure, broad session | danger-full-access, only when separately selected | on-request, but this cannot guarantee separate approval of critical operations |

Even broad sessions **must never** be described as technically enforcing critical-action approval. The agent may have unrestricted SSH/root/MCP/cloud access or commands may run inside already-allowed processes. To enforce approvals use capabilities outside the unrestricted session: narrow accounts, delegated services, remote-side access gates, or an isolated agent environment.

## Preflight and interactive launch

First inspect without starting Codex:

~~~sh
python3 /path/to/codex-practices/skills/permissions/scripts/codex_start.py --project /absolute/project
~~~

This reports the recommended preset from local directory entries, planned CLI flags, a **redacted and partial** audit of user + project TOML files, and external scan risk. It never executes scripts found in the project or outputs secret TOML values. It does not prove the effective Codex policy (managed restrictions, system settings, project trust and runtime tool permissions require a separate check).

Start guided selection on a real terminal:

~~~sh
python3 /path/to/codex-practices/skills/permissions/scripts/codex_start.py --project /absolute/project --interactive
~~~

Select Review / Development / Infrastructure. For broad Infrastructure, type BROAD when asked and then the separate session phrase BROAD_INFRA_THIS_SESSION. For normal presets type LAUNCH_PROFILE. If #5 scanning reports HIGH risk, also type HIGH_RISK_REVIEWED; if it was incomplete or unavailable, type INCOMPLETE_SCAN_REVIEWED. Cancelling or omitting required phrases prevents launch.

Non-interactive use still requires explicit parameters and confirmations:

~~~sh
python3 /path/to/codex-practices/skills/permissions/scripts/codex_start.py --project /absolute/project --profile development --launch --confirm LAUNCH_PROFILE
~~~

For a high-risk/incomplete preflight, --risk-ack can be repeated (one token per outstanding warning). Such CLI tokens are **not authenticated proof of human approval**; don't use them to silently escalate automated jobs.

The launcher only probes the installed Codex binary with --help to check --cd, --sandbox and --ask-for-approval before it launches; this avoids invoking a model just to test compatibility. Do not supply an untrusted --codex-bin path. A malformed/symlinked local config or failed external scan blocks launch rather than making a misleading safety claim. The preflight performs no persistent writes.

## Installation and rollback

If installation of a convenient shortcut is desired, preview its destination and ask permission before copying or linking any helper. Never replace a user executable or modify ~/.codex/config.toml automatically. The default is calling the repository helper directly, so **nothing must be installed** for preview or launching. Removing an explicitly installed shortcut restores the previous entry from backup; no global Codex setting is changed by a normal session.

## Tests and limitations

~~~sh
python3 -m unittest discover -s tests -p test_codex_start.py -v
~~~

Test scenarios include interactive selection, broad-session confirmations, local configuration redaction and conflict warnings, incomplete / HIGH external scan acknowledgement, and fake CLI compatibility checks. Full interactive Codex E2E, actual managed policies, shell/SSH/MCP reach and remote critical-operation enforcement remain **NOT TESTED** until user-approved tests in an isolated environment.

See [acceptance scenarios](../tests/permissions-acceptance.md) and [native Skill](../skills/permissions/SKILL.md). External scanner (#5) is optional, but missing scanner never equals a clean scan. No background daemon, hooks or automatic privilege changes.
