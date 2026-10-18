---
name: skills-management
description: Audit existing Codex Skills, detect conflicts and recommend focused new skills with explicit installation consent. Use during project setup or when user asks to manage skills, not for routine coding.
---

# Codex Skills Management

Use `scripts/skills_audit.py --project /actual/project` to inspect existing global and project skills **read-only**. Resolve warnings manually: duplicate names across scopes, missing frontmatter, symlink targets and user-modified scripts. The helper does not install packages or fully parse YAML; it is an advisory inventory.

Consult `catalog/recommended-skills.json` in the codex-practices package for *workflow categories*, not verified third-party downloads. Reuse existing Project Memory/Handoff (#3), External Content Guardrails (#5), Multi-Agent (#8), Verification (#7) and built-in `$skill-creator` / `$skill-installer` before creating new procedures. Avoid semantic duplicates and bulk installs.

Propose only 1–3 specific, useful skills. For safe analysis/research skills allow implicit invocation; for install, infrastructure, secrets or destructive operations require explicit invocation via `agents/openai.yaml` policy `allow_implicit_invocation: false` when supported. This policy does not enforce OS permissions; #4 owns those.

Before writing: inspect source, scripts, dependencies and selected scope; show diff/backups; obtain explicit consent; use native installers or deliberate copy into `.agents/skills/`. After installation verify discovery and activation with positive, negative and explicit invocations **only on user-approved test session**. Do not overwrite customized skills or edit global Codex configuration without separate consent. No duplicate state store, daemon or automatic updates.
