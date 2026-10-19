# Unified Codex Practices Installer — guided setup

This is the primary entry point for installing **bundled Skills** into a confirmed project. It does not execute untrusted project scripts, run tests, download MCP packages, overwrite existing Skills, or edit AGENTS.md/config.toml automatically. Python 3.11+, Linux/macOS.

## Single setup workflow

1. Confirm the actual target project, review existing global/project instructions, Codex CLI version, existing Skills and project trust. Do not assume the current directory is the target. Never run an untrusted repository's scripts as part of discovery.
2. Run the unified plan. Module #1 (AGENTS.md) and #2 (Behavior Rules) use the **same guided interview** from recipes/setup-agents-md.md; reuse existing answers and settings rather than prompting a second time. Approve their exact generated instructions separately; this mechanical installer intentionally does not synthesize/edit them.
3. Select bundled modules and inspect the explicit file/destination list. Dependencies #5→#4, #8→#3, #10→#4+#5, #11→#3 are included in the proposed plan and need one confirmation. Project and global scope are fixed by the approved package manifest.
4. Apply once using the printed plan hash and installation token (or use a TTY wizard). Existing identical Skills are skipped. Existing differing Skills, duplicate scope names, symlinks and unavailable modules **block installation**, rather than being overwritten.
5. Apply per-project policy **only separately**: #4 requires user approval to launch profiles, #10 requires an approved trust policy and a separate MCP config transaction, #11 requires a reviewed fact-owners.toml and optional approved AGENTS.md pointer. #3 does not create Handoff state until needed. No implicit RTK, hooks, network access or automatic infrastructure elevation.
6. Save the generated private rollback manifest. Perform the combined real Codex CLI smoke tests and full unit/integration tests **at the final acceptance milestone**, not on every install or session.

## Commands

Read-only plan for modules included in this checkout (currently #3–9 in master; #10/#11 become available only after their PR sources are integrated into the package):

    python3 scripts/codex_practices_setup.py --project /absolute/project plan

Plan the complete declared module set, including missing modules (apply refuses unavailable entries):

    python3 scripts/codex_practices_setup.py --project /absolute/project --modules all plan

Pin a subset, with automatically displayed dependencies:

    python3 scripts/codex_practices_setup.py --project /absolute/project --modules 3,4,5,7,10,11 plan

Apply the **same selected module set** after inspecting the exact preview:

    python3 scripts/codex_practices_setup.py --project /absolute/project --modules 3,4,5,7 apply --expected-plan-sha PRINTED_SHA256 --confirm INSTALL_APPROVED_CODEX_PRACTICES

Single interactive approval (not a replacement for the AGENTS.md interview):

    python3 scripts/codex_practices_setup.py --project /absolute/project wizard

Rollback only newly-created, unchanged Skills; previously existing files are never touched:

    python3 scripts/codex_practices_setup.py --project /absolute/project rollback --manifest /absolute/private/manifest.json --confirm ROLLBACK_CODEX_PRACTICES

## Scope and limitations

- Global: #4 permissions-guardrails, #5 external-guardrails, #6 skills-management → ~/.agents/skills.
- Project: #3 project-memory, #7 verification, #8 multi-agent, #9 model-efficiency, #10 mcp-management, #11 project-inventory → PROJECT/.agents/skills.
- The two new draft modules #10/#11 and launcher hardening PR #12 are **not silently imported** into this PR or installed from remote sources. Their currently available source depends on the checked-out package revision.
- The plan SHA pins source contents, destinations, requested modules and observed conflict statuses. This is a review/consent mechanism, not a cryptographic signature or OS sandbox.
- A successful copy does not guarantee Codex Skill discovery or safe invocation. Those require the deferred live verification.
- The installer is non-destructive: no automatic in-place updates; if a user customized a Skill, inspect and explicitly reconcile changes rather than silently replacing them.
- Rollback refuses changed Skills. Concurrent unrelated filesystem writers are not globally serialized; exclusive locks coordinate only instances of this installer. Review/stop concurrent installers or editors during apply.
- No cross-project user profiles, duplicate answer database, standing process, cron, RAG, or unsanctioned API calls.
