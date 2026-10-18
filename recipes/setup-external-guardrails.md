# External Content Guardrails — module №5

Read-only heuristic preflight: [script](../skills/external-guardrails/scripts/external_scan.py). Python 3.10+, no dependencies, no commands from repository executed. Inspect AGENTS.md, AGENTS.override.md, CLAUDE.md, README and relevant external instructions *before starting Codex* through [permissions launcher](../skills/permissions/scripts/codex_start.py). Limit scan by file count and bytes; skip symlinks/binaries; report only source/category/risk, not injection payload.

```sh
python3 /path/to/codex-practices/skills/external-guardrails/scripts/external_scan.py --root /external/repo
```

Return code 3 = HIGH, 0 = LOW/MEDIUM, 2 = scanner failure. The script is a heuristic, not malware analysis and not proof of trust. Skipped files/truncated scans reduce confidence. It does not parse all formats or all languages and does not monitor external web/MCP outputs continuously.

## Optional integration with #4

When both Skills are installed alongside one another in `.agents/skills/`, updated `codex_start.py` calls the scanner once before launching. On scanner error it refuses to launch. On HIGH risk it requires the separate `--risk-ack HIGH_RISK_REVIEWED` **after** the user has reviewed the report; permission-profile consent remains mandatory. This protects only launches **through the helper**, not direct `codex` invocations. If scanner is absent, preflight is reported unavailable, not as clean.

During an already running broadly empowered Infrastructure session, user may acknowledge and continue after warning, but no heuristic can guarantee blocking all SSH/MCP/root operations. Prompt text never confers real capability restrictions. Ordinary read-only analysis can continue. Request a new confirmation for truly critical irreversible operations wherever actual native approval boundaries permit.

## Optional runtime Hooks

Codex `PreToolUse` with supported `permissionDecision: deny` can block specific local tool calls; `permissionDecision: ask` is unsupported and malformed hooks may fail open. Tools such as hosted WebSearch and privileged external systems may fall outside coverage. **No Hook is installed automatically** by this module; site-specific rules require separate documented consent, isolated tests and permission checks.

No background scanning, remote model calls, memory poisoning or automatic installation. Test using `python3 -m unittest discover -s tests -p test_external_scan.py -v`; see [acceptance](../tests/external-guardrails-acceptance.md).
