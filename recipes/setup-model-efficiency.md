# Model Tiering & Token Efficiency — Codex module №9

**Design:** user owns the primary model/effort; adaptively select subagent settings from a *verified allowlist*; minimize context without losing evidence; RTK is strictly optional, project-scoped and installed only after explicit approval. No daemon, model API calls, automatic edits to Codex config, or compulsory RTK.

## Boundaries

- This module extends [Multi-Agent (#8)](setup-multi-agent.md). The coordinator decides **whether** to delegate; this policy advises **which verified model and effort** to request for a delegated task. The primary Codex model is never changed.
- Codex version, provider/plan entitlements, supported model names, spawn-time override support and reasoning levels differ. Read current local config and product docs before choosing. This tool cannot discover entitlements; **do not invent model availability**.
- Role definitions and `agents.default_subagent_model`/`agents.default_subagent_reasoning_effort` are native Codex facilities when supported. Per-agent launch overrides may depend on runtime. If an override cannot actually be applied, disclose that and inherit the parent. Do not silently edit `~/.codex/config.toml` or the selected project's Codex config.
- Higher reasoning is not a permission grant. Cost and token counts may be unavailable for subscription-backed Codex; never report fake monetary savings.

## 1. Initial audit, with no changes

Confirm target project; inspect active Codex version, model UI/config, subagent support, installed Skills, existing roles, existing `AGENTS.md`, `.codex/hooks.json`, `RTK.md`, RTK version and any user/global RTK hooks **read-only**. Do not follow links to secrets. Do not re-run the initial AGENTS Q&A. Ask only for essential choices absent from the existing setup.

A small optional JSON catalog may be kept **outside** the codex-practices package, at a user-approved path. It is user-owned and never created implicitly:

```json
{
  "version": 1,
  "tiers": {
    "routine": [{"model": "CONFIRMED_FAST_MODEL", "effort": "low"}],
    "balanced": [{"model": "CONFIRMED_GENERAL_MODEL", "effort": "medium"}],
    "advanced": [{"model": "CONFIRMED_STRONG_MODEL", "effort": "high"}]
  }
}
```

Replace example identifiers with *models actually verified in this Codex environment*. Each tier may instead be an empty array; with no verified candidates selection returns `inherit`. The catalog is only a local policy input, not an assertion of account availability.

## 2. Model selection for a delegated task

- Classify: **routine** = lookup/collect/format; **balanced** = normal coding, debugging/review; **advanced** = complex architecture, security, high-consequence decisions.
- Run the packaged stdlib-only chooser with explicit known available names:

```sh
python3 /path/to/codex-practices/skills/model-efficiency/scripts/model_policy.py \
  --tier routine --catalog /path/to/approved/models.json \
  --available CONFIRMED_FAST_MODEL CONFIRMED_GENERAL_MODEL
```

It emits a single JSON decision, either `selected` (`model`, `reasoning_effort`, `selected_tier`) or `inherit`. It **never silently downgrades** a requested class; if no compatible option is confirmed it recommends inheriting the parent's setting. It does not launch agents, infer availability, call models, edit files or enforce a new model on the host.
- The orchestrator passes these settings through **native spawn/role configuration, if confirmed supported**. Verify the effective model of a sample child session where available; if the runtime ignores the requested override, report that and fall back to inherited settings. No self-invented Codex command-line flags or API schemas.
- If a cheaper model demonstrably fails a task or verification from #7, diagnose and escalate within available settings. No retries without new information.

## 3. Context discipline

Search narrow files and symbols first; read required ranges; avoid sending full history to every subagent; reuse Handoff (#3) rather than copying transient status into AGENTS.md or Skills. Summarize large command output **only after preserving** access to the original evidence. For safety checks, incident logs, recovery tests and structured downstream input, prefer complete originals. Treat shortened command output as potentially incomplete and validate counts/diagnostics explicitly.

## 4. RTK evaluation — no hook yet

This module does **not** install RTK. If available, compare **safe, read-only** commands with and without RTK in a disposable/project-approved environment. Capture stdout and stderr together (do not paste private logs into public PRs), and retain each real exit code.

Inspect side effects, hashes/records where relevant, warnings, total item counts, truncation, JSON structure, and whether details can be retrieved. For saved text outputs:

```sh
python3 /path/to/codex-practices/skills/model-efficiency/scripts/rtk_audit.py \
  --raw /safe/raw-output.txt --compressed /safe/rtk-output.txt \
  --raw-rc 0 --compressed-rc 0
```

The audit never executes commands. `identical` or `equivalent_json` are exact equivalence findings for the **saved output only**, not blanket Hook approval. A changed exit code, missing important signal, or changed JSON structure returns `reject`. Arbitrary changed text returns `review_required`, even if smaller. This conservative check cannot prove completeness of all command types. Review independently before installation.

## 5. Optional project-scoped Hook (separate explicit approval)

**Not installed or enabled by this module.** RTK's native project installer is `rtk init --codex`. When the installed RTK/Codex versions support it, first:
1. Confirm a *trusted* target repository and inspect `AGENTS.md`, `RTK.md`, `.codex/hooks.json` including symlinks, existing hooks and their precedence. RTK may modify all three, and unknown/symlink targets can be hazardous. Never blindly initialize it inside untrusted repos.
2. Inspect actual rewriting rules and exclusions; standard RTK Codex rewriting is **not** a guaranteed read-only command allowlist. This module adds **no custom hook filter**. If mutating commands can be rewritten against policy, leave the hook disabled and use RTK manually for audited commands instead.
3. Take versioned backups of affected user-authored configuration; preview each expected diff and obtain explicit user approval. Never edit global `config.toml` or relax the sandbox for RTK history DB as part of this step.
4. Only after audit/approval run the vendor's `rtk init --codex` from the confirmed project (without `-g`). Restart Codex, approve the project hook trust prompt if appropriate, compare effective hooks, and perform one safe smoke test. Inspect actual output, not just installer exit status.
5. To undo, use `rtk init --codex --uninstall`, inspect actual files, compare backups and restore only carefully reconciled user changes. Do not overwrite concurrent edits or claim removal success solely from a command's zero exit code.

RTK's Codex `PreToolUse.updatedInput` changes a command *before* normal Codex approval/sandbox checks. The command classifier may see the `rtk` wrapper instead of the original tool. Hooks can fail open and are **not an enforcement boundary**. For high-risk commands, production, destructive Git operations, changes to firewall, secrets or deployment, use raw commands and the future Permissions (#4) and External Content Guardrails (#5) where implemented; those modules are not yet present.

## 6. Validation, rollback, status

Run the isolated automated unit tests during development/installation (not every session):

```sh
python3 -m unittest discover -s tests -p test_model_efficiency.py -v
```

Manual smoke tests: verified model candidate selected on a supported Codex version; unsupported candidate falls back without changing the parent; RTK absent; audit returns review/reject on lost content; optional project hook installs only with consent and restores exact effective configuration on removal. Record actual evidence, test scope and any untested scenarios. See [acceptance matrix](../tests/model-efficiency-acceptance.md).

Docs: https://developers.openai.com/codex/config-reference , https://developers.openai.com/codex/multi-agent , https://github.com/rtk-ai/rtk/blob/develop/hooks/codex/README.md .
