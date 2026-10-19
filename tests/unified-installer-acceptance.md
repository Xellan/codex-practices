# Unified Setup — deferred acceptance matrix

Do **not** run these checks before the final integration acceptance stage agreed with the project owner.

- UI-01: dry-run plan on clean project; no state/config/AGENTS.md changes.
- UI-02: default modules resolve from checked-out package only; #10/#11 missing on master are reported, not fetched from Draft PRs.
- UI-03: dependency closure and install order; no duplicate AGENTS/Behavior interview.
- UI-04: malicious symlink, wrong Skill frontmatter, changed package source and conflicting user-owned skill stop installation.
- UI-05: launch without exact SHA or confirmation fails; approved apply creates only intended new Skills.
- UI-06: existing identical Skill is skipped, existing modified Skill preserved and blocks.
- UI-07: manifest identifies created files and safe rollback refuses edits.
- UI-08: no user global Codex config, AGENTS/overrides, MCP config, fact-owner map, secrets or Handoff content written automatically.
- UI-09: global/project Skill discovery and invocation with real Codex CLI; only then record Verified.
- UI-10: module #10 MCP policy and module #11 fact-owner map configured separately through explicit approvals, once their PRs are present in checkout.
- UI-11: concurrent edits during installation and rollback produce explicit conflicts or manual-review status; no false atomicity claim.
- UI-12: complete end-to-end tests across modules #1–11, including the launcher hardening from PR #12, in a disposable environment.
