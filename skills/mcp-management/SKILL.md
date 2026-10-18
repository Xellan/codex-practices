---
name: mcp-management
description: Audit Codex MCP integrations, propose least-privilege access, and maintain approved pinned local releases.
---

# Codex MCP Management

Read the package recipe recipes/setup-mcp-codex.md first. Confirm the real target project; never silently edit global configuration.

1. Audit Codex version, available MCP commands, user/project configuration and server names. Use scripts/mcp_manager.py --project PROJECT audit for a redacted inventory. Never copy secrets, OAuth credentials, private URLs or raw configuration into Git or Handoff.
2. Recommend only needed, independently vetted MCP servers and minimum enabled_tools allowlists. Treat advertised read-only annotations as untrusted. New servers, tools, OAuth scopes and privilege changes require explicit user consent.
3. A user-approved, immutable trust policy can preapprove exact local stdio release SHA-256 hashes and an unchanged tool contract fingerprint. The helper manages only its own bounded project TOML block. Initial installation requires matching configuration/policy hashes and explicit confirmation.
4. After setup, an authorized session-entry or on-demand invocation may run maintain. It changes only to staged, already approved executable versions and never downloads arbitrary packages, runs tools, or updates hosted remote server software. No daemon or scheduled tasks.
5. Record real independently observed health failures from sanitized local evidence files. Repeated distinct failures may disable optional MCPs during maintain. Required MCPs remain enabled. A verified success can re-enable an optional MCP. Record is not itself proof of health.
6. Rollback needs explicit consent and a hash-verified private backup. Never replace concurrent edits, remove servers or revoke OAuth credentials automatically.
7. Check actual runtime permissions in a later user-approved live Codex test. This helper does not guarantee remote restrictions, call-time approvals or runtime tool-schema validation.

Use Permissions #4, External Guardrails #5 and Verification #7 as separate safeguards; no textual instruction replaces their actual execution mechanisms.
