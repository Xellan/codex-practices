# MCP Servers Management — acceptance (#10)

- Audit reports server names and permissions without revealing secrets or credential URLs.
- Initial install requires explicit consent and matching config/policy hashes.
- Preserve existing TOML and refuse symlinks, unknown managed blocks and collisions.
- Enforce HTTPS remote URLs or exact reviewed local executable SHA-256.
- Auto-update only preapproved local releases with unchanged tool contracts and tool allowlists.
- Reject unknown/missing/modified/symlinked artifacts and edited policies.
- Refuse to overwrite concurrent user edits; save a private, digest-verified backup.
- Auto-disable only optional MCP after repeated recorded failures; never disable required ones silently.
- Permit re-enable after a separately verified healthy observation.
- No automatic downloads, OAuth permission growth, credential deletion or remote provider code update.
- Rollback restores previous local config when no conflict exists.
- Live Codex tools, OAuth and security enforcement must be tested separately.

Local tests: python3 -m unittest discover -s tests -p test_mcp_management.py -v
