
# Codex Practices — instructions for contributors

This repository is an incremental adaptation of Claude Code Practices for Codex. The legacy README.md and START.md still describe the original Claude-based installer. For the Codex AGENTS.md module, use CODEX-START.md and recipes/setup-agents-md.md.

## Development contract
- Work on one agreed function at a time: research → design → user approval → implementation → verification.
- Do not modify unrelated recipes or migrate the remaining Claude components without explicit approval.
- Prefer native, currently documented Codex behavior. Verify product-specific claims against official documentation.
- Keep generated AGENTS.md files short and project-specific; separate universal behavior from project facts.
- Never place API keys, credentials, personal secrets, or volatile task state into instruction templates.
- Preserve user-authored configuration, avoid duplicating rules, and ask before any destructive change.
- Do not silently edit a user's CODEX_HOME, global instructions, or an unrelated project.

## Current module
- Entry point: CODEX-START.md
- How-to: recipes/setup-agents-md.md
- Behavior selection: recipes/behavior-rules.md (same Q&A, same managed AGENTS.md block, no second installation flow)
- Background: practices/01-agents-md.md
- Templates: templates/agents/
- Acceptance scenarios: tests/agents-md-acceptance.md
- Project Memory: recipes/setup-project-memory.md (Native Memories opt-in, durable project knowledge, functional Handoff)
- Project Handoff Skill: skills/project-memory/SKILL.md and skills/project-memory/scripts/handoff.py
- Handoff unit tests: tests/test_handoff.py
- Optional Multi-Agent module (#8): recipes/setup-multi-agent.md, skills/multi-agent/scripts/agent_worktrees.py and tests/test_agent_worktrees.py; optional Skill: skills/multi-agent/SKILL.md; worktrees are not security sandboxes.

- Model efficiency (#9): recipes/setup-model-efficiency.md, skills/model-efficiency/SKILL.md + scripts, tests/test_model_efficiency.py. Main model remains user-owned; RTK hooks require a separate, explicit opt-in.

- Permissions & Guardrails (#4): recipes/setup-permissions.md and skills/permissions/; explicit session consent; no system enforcement beyond native sandbox.

- External Content Guardrails (#5): recipes/setup-external-guardrails.md; scanner is heuristic and not a sandbox.

- Skills Management (#6): recipes/setup-skills-management.md; skills/skills-management/ and curated category catalog. Native installation only after explicit consent.

- Verification & TDD (#7): recipes/setup-verification.md, skills/verification/, tests/test_verification_report.py. Checks require real evidence; no fabricated PASS.

## Verification
- Read the affected Markdown files and check relative links.
- Follow the acceptance scenarios relevant to the change.
- Do not run Codex model calls automatically as part of everyday work; installation-only smoke tests require permission.
