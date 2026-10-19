# Module #11 — Project Inventory & Fact Ownership acceptance

- PI-01: valid TOML map parses with strict schema, unique class IDs and source types.
- PI-02: missing owner is a finding, not evidence a project has stalled.
- PI-03: external source is reported unverified, without model or network calls.
- PI-04: dangerous paths, symlinks, invalid TOML and oversized documents rejected.
- PI-05: targeted event runs check only requested Markdown documents; events must be invoked by a Codex workflow.
- PI-06: full read-only scan reports broken inline links and parser scope limitations.
- PI-07: code fences and inline code do not generate bogus links.
- PI-08: only same-directory unique case-only broken link targets become auto-fix candidates.
- PI-09: moved/renamed ambiguous links never auto-fix; semantic fact duplicates require human decision.
- PI-10: no user project writes unless an explicit --apply-safe-fixes or --save-report flag is supplied.
- PI-11: pre-fix source SHA mismatch stops overwrite and reports conflict.
- PI-12: backup saved outside project with private permissions, atomic replacement and manual rollback.
- PI-13: rollback refuses to overwrite post-fix user changes.
- PI-14: full audits get unique names; later report compares previous finding counts; no permanent background process.
- PI-15: AGENTS.md and Project Memory remain user-owned and untouched by script; install Skill only with consent.
- PI-16: true semantic verification, external status checking, and Codex live event integration are NOT yet E2E tested.
