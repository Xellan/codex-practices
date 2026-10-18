# Project Inventory & Fact Ownership — Codex module #11

## Purpose

One evolving fact class → one authoritative owner. `fact-owners.toml` stores **where** facts live; it must never duplicate mutable values. A short AGENTS.md pointer makes the owner map discoverable. Status is read from its owner, never guessed from filesystem timestamps, file existence or another session's logs. Reuse #3 Project Memory/Handoff rather than creating a second state store. `review_in` names suspected secondary locations for manual audit, not automatic proof of duplication.

## Installation (interactive, consent-based)

1. Confirm actual target project and effective Git/AGENTS.md inheritance. If there is already a user-defined source-of-truth map, reconcile rather than duplicate it.
2. Inspect `fact-owners.toml` read-only. If absent, adapt [template](../templates/project-inventory/fact-owners.toml) to real owner paths and review it with the user. Do not overwrite an existing map.
3. Obtain consent to place `skills/project-inventory/` into the approved project's `.agents/skills/project-inventory/` directory and to add one short AGENTS.md line: `For current mutable facts consult fact-owners.toml and read the designated owner, never copies or mtime.` Back up user files before editing. This Skill's standalone Python helper can also run from the cloned codex-practices package without installing it.
4. Validate Python 3.11+ and, if present, verify existing `audits/` handling and `.gitignore` policy without assuming reports may be published. No global Codex configuration changes or daemon.

## Fact owner map

TOML v1:

```toml
schema_version = 1

[[facts]]
id = "release_version"
description = "Current project release version"
source_type = "file"
source = "VERSION.md"
review_in = ["README.md"]

[[facts]]
id = "release_tracker"
description = "External release status"
source_type = "external"
source = "tracker:project-alpha"
```

`source_type=file` requires a normalized path under project root. Missing owner is reported; an owner is not fabricated. `source_type=external` is an unverified reference label, never a live status check or token. The tool validates duplicate IDs, traversal, symlinks and malformed structure.

## Modes and trigger policy

- **Targeted event audit:** after a documented milestone, changed documentation, or pre-PR checklist, invoke on the affected Markdown files. There is no hidden filesystem watcher, no per-session compulsory full scan, and no automatic on-change Hook.

```bash
python3 /path/to/codex-practices/skills/project-inventory/scripts/inventory.py --root /absolute/project --changed README.md docs/architecture.md
```

- **Full audit:** requested by user or planned at a major milestone. First run without writes; after explicit consent pass `--save-report` to persist a timestamped summary in `audits/` and compare previous finding counts.

```bash
python3 /path/to/codex-practices/skills/project-inventory/scripts/inventory.py --root /absolute/project --save-report
```

- **Safe mechanical fixes:** only after a consented scope, run `--apply-safe-fixes`, optionally specifying an absolute `--backup-dir` outside the project. The helper fixes only case-only, unique same-directory link target mismatches. It **cannot** decide whether a moved file is the intended destination and never rewrites a value copied from its real fact owner.

```bash
python3 /path/to/codex-practices/skills/project-inventory/scripts/inventory.py --root /absolute/project --changed README.md --apply-safe-fixes
```

- **Restore:** an explicit operation with the generated manifest path; refuses if source bytes were altered after the fix.

```bash
python3 /path/to/codex-practices/skills/project-inventory/scripts/inventory.py --root /absolute/project --restore /absolute/backup/manifest.json
```

## Permissions and preservation

This command does not execute checked project files, call a model, access the network or install global hooks. Backups default to `~/.local/state/codex-practices/inventory-backups/<project-hash>/` with user-private filesystem permissions; deletion is **never automatic**. Make sure local backups are not unintentionally included in source control or sent to third parties. Before a fix the helper compares content SHA-256 and rechecks immediately before atomic replace; advisory `flock` serializes this tool's concurrent writers. External editors not using the lock can still race with it. Rollback checks both saved and current content hashes. Writing the report is an explicit option and reports contain paths/classifications, not full document bodies.

## Acceptance criteria and caveats

See [test matrix](../tests/project-inventory-acceptance.md). Offline stdlib unit tests: `python3 -m unittest discover -s tests -p test_project_inventory.py -v`. They cover malformed ownership maps, unsafe traversal/symlinks, case-only correction, backup/restore, edit conflicts and report history. Live Codex-trigger integration and mixed-tool concurrent editing remain for final end-to-end evaluation.

The reference-style Markdown link parser, rich Markdown/HTML parser, automatic semantic duplicate detection and automatic owner selection are explicitly **out of scope**. No promises of correctness for documents excluded by limits. The selected implementation is conservative rather than pretending semantic differences are mechanically resolvable.
