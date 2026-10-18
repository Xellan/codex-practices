---
name: model-efficiency
description: Optimize Codex subagent model choice and task context without changing the main model; optionally assess saved RTK output safety. Use for multi-agent resource optimization or requested token audits, not for routine tiny edits.
---

# Model tiering and context efficiency

Only operate in a confirmed project and with user-approved settings. This Skill is **guidance**, not a live model router, cost meter, command interceptor or security policy. Reference recipe: `recipes/setup-model-efficiency.md` in the codex-practices package.

## Subagent choice

1. Let the main Codex (#8) decide whether to delegate. Keep the parent's chosen model/effort unchanged.
2. Classify proposed child work: routine (search/extract), balanced (coding/debug/review), advanced (architecture/critical risk). Risk overrides apparent task size. Avoid excessive delegation.
3. With a user-approved catalog and **confirmed available** models, optionally run the packaged `scripts/model_policy.py` with `--tier`, `--catalog`, `--available`. Its JSON is a *proposal*. Apply an override via the actual native Codex subagent/role interface **only when supported**; verify effective settings when possible. Otherwise inherit. Never invent models or alter config.toml silently.
4. Poor observed quality may justify escalation after diagnosis; not infinite retry loops. Use Verification (#7) criteria even though that module is not yet implemented.

## Context and optional RTK

Search narrow content; avoid duplicate instructions; preserve original diagnostic evidence and distinguish unknown from verified results. Do not truncate essential errors or silently reduce counts.

If RTK is user-requested, check its version and existing hook config **read-only**. The packaged `scripts/rtk_audit.py` compares saved raw/compact output and exit codes without running shell commands. `review_required` is *not* approval; loss returns `reject`. Never install a hook automatically. The RTK project hook is an **explicit separate opt-in** after a safe trial, inspection, backups and user approval. If wrapper reclassification or data loss is unacceptable, use raw commands. No automatic global RTK or permissions changes.

## Final report

State effective/unknown model selection, tests actually run, measured (not estimated) token costs if available, any RTK files or hooks changed, rollback evidence, and unresolved limits. A success in this Skill cannot override project permissions. No background jobs, API calls, or persistent duplicate catalog.
