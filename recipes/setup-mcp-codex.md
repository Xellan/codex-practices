# Codex MCP Servers Management — module 10

**Architecture:** adaptive recommendations, manual approval for installation/expanded rights, risk-aware tool use, and autonomous *session-triggered* maintenance of already trusted local versions.

## Audit and first setup

Inspect the actual target project, its trust state, installed Codex version and effective MCP entries. Codex supports project .codex/config.toml in trusted projects, but other sources can take precedence. Run a read-only, redacted inventory:

    python3 /path/to/codex-practices/skills/mcp-management/scripts/mcp_manager.py --project /absolute/project audit

Use official/vetted server providers where possible, narrow enabled_tools, and approval modes supported by the user's actual Codex version. Never assume a server-declared read-only hint protects sensitive data. For public HTTPS endpoints use minimal requested scopes; for local stdio audit the executable and dependencies with External Guardrails.

Create a project-owned **approved trust policy JSON** outside this package. The schema requires version=1 and a list of servers. Each server has name, transport, enabled_tools, approval (auto/prompt/writes/approve), required and auto_disable_after. HTTP entries specify an HTTPS url without embedded credentials. A stdio server specifies an absolute trusted root, initial_version, contract_sha256, auto_update and releases. Each release has version, file basename, sha256 and the same contract_sha256. Hashes and the tool-contract fingerprint are supplied by a trusted operator; this tool cannot verify live MCP schemas. Preapprove only versions and rights already independently reviewed. No unpinned package latest or arbitrary dynamic downloads.

Read-only preview:

    python3 /path/to/codex-practices/skills/mcp-management/scripts/mcp_manager.py --project PROJECT --policy TRUST.json plan

Show the source, permissions, affected files and diff to the user, obtain explicit approval. Initial install requires SHA256 of the current config (from audit) and trust policy (from plan):

    python3 /path/to/codex-practices/skills/mcp-management/scripts/mcp_manager.py --project PROJECT --policy TRUST.json apply --expected-config-sha CONFIG_SHA --expected-policy-sha POLICY_SHA --confirm INSTALL_APPROVED_MCP

The helper modifies ONLY its fenced MCP block, rejects user-owned name collisions or symlinks, validates TOML, locks writes and stores private mode-0600 backups outside the project. It never changes global ~/.codex/config.toml, signs in to OAuth or installs unreviewed software.

## Automatic maintenance within preapproved trust

At approved session entry or on demand:

    python3 /path/to/codex-practices/skills/mcp-management/scripts/mcp_manager.py --project PROJECT --policy TRUST.json maintain

Only already listed, staged immutable local stdio releases with matching executable SHA and unchanged declared contract are promoted. If policy or config changed outside the manager, automation refuses. Remote HTTPS MCP software is managed by its provider: the helper cannot upgrade or revert that server. No background daemon/timer, no network download and no automatic permission expansion.

After an independently observed problem, record a redacted unique evidence file:

    python3 /path/to/codex-practices/skills/mcp-management/scripts/mcp_manager.py --project PROJECT --policy TRUST.json record --server docs --result fail --evidence /safe/probe.txt

Repeated recorded failures can disable an optional MCP at the next maintain; required servers remain enabled. A separately verified pass can re-enable an optional MCP. The helper does NOT independently execute or authenticate probes; evidence must be checked elsewhere. The command itself cannot establish service health.

## Rollback

With separate user consent:

    python3 /path/to/codex-practices/skills/mcp-management/scripts/mcp_manager.py --project PROJECT --policy TRUST.json rollback --confirm RESTORE_PREVIOUS_MCP

Hash-guarded private backups restore the preceding config bytes if there is no concurrent change. Rollback does not undo remote side effects, revoke OAuth access or uninstall packages. Any removal requires approval.

## Validation and limits

Run unit tests only when developing or installing:

    python3 -m unittest discover -s tests -p test_mcp_management.py -v

Review tests/mcp-management-acceptance.md. Live Codex permissions, tool schemas, health probes and OAuth are NOT RUN until final integration acceptance. Integration with modules #4–9 is advisory unless their installed runtime mechanisms enforce it.

Official docs: https://developers.openai.com/codex/mcp and https://developers.openai.com/codex/config-reference.
