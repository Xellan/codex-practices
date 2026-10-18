# Skills Management — module №6

The companion [read-only inventory](../skills/skills-management/scripts/skills_audit.py) finds direct `~/.agents/skills` / project `.agents/skills` Skills and detects name collisions, symlinks and missing/invalid frontmatter. It is **not** a comprehensive resolver for all Codex scope hierarchies, native built-in skills or installed third-party plugins. Inspect parent repository folders, active permissions and native discovery as appropriate.

```sh
python3 /path/to/codex-practices/skills/skills-management/scripts/skills_audit.py --project /actual/project
```

Use [small category catalog](../catalog/recommended-skills.json); do not misrepresent suggested categories as confirmed downloadable packages. Primary recommendations: built-in `$skill-creator`, `$skill-installer`, existing project-memory Skill, debugging/review only when not already present. Do not duplicate modules #3–5, #7–9 as fresh Skills.

## Installation with consent

1. Audit scope, existing skills, actual project target and version capabilities. No repeated global AGENTS Q&A.
2. Match current tasks against already available skills. Show 1–3 useful suggestions, explain scope Global vs Project and expected dependencies. Nothing auto-installed.
3. Preview complete `SKILL.md`, any scripts and external dependencies; apply External Content Guardrails (#5) to unfamiliar sources.
4. After user consent, invoke native `$skill-installer` or `$skill-creator`, or safely copy vetted folder. Never replace a customized skill silently. Back up existing files before explicit update.
5. Verify actual recognition in one approved Codex session; test matching query, nonmatching query and explicit `$name`. Automatic choice is best effort and can vary.
6. Sensitive skills: place `agents/openai.yaml` inside the skill with `policy.allow_implicit_invocation: false` **if supported**; it is an activation hint, not privilege control. Use #4 permissions for real actions.
7. For updates, compare versions/contents, review any new scripts, test then offer rollback. Prefer native disable to irreversible delete when supported.

Python local tests: `python3 -m unittest discover -s tests -p test_skills_audit.py -v`. See [acceptance](../tests/skills-management-acceptance.md). No background sync, automatic download, fabricated installation guarantees or per-turn scanner.
