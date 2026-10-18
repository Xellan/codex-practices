---
name: permissions-guardrails
description: Review and launch Codex with a user-approved Review, Development or Infrastructure permission profile. Use for starting a new session or auditing permission risk, not for routine coding.
---

# Permission profile workflow

Use the project-confirmed `scripts/codex_start.py` helper for a read-only preview. Check effective permissions, installed Codex version, existing user settings and managed restrictions. Discuss the risks of broad infrastructure access; it lasts only for that session and is not an automatic escalation.

Never silently launch, overwrite `config.toml`, install hooks, alter user permissions or use `--yolo`. For a real launch require explicit user approval and the helper's confirmation flag. A chosen profile does not replace hard limits on SSH, MCP, root privileges and network access. If high-risk external material is found later, respect the current External Content Guardrails workflow (#5).
