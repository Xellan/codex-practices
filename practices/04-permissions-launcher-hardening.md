# Permissions Launcher Hardening (№4)

The existing permissions launcher now supports a TTY consent flow via `--launch --interactive`. When no `--profile` is provided, it recommends a profile based on filenames and **asks** for an explicit selection. It also asks for exact confirmation before launching. Noninteractive usage with `--profile ... --launch --confirm ...` remains supported.

## Commands

Preview (no execution or configuration edits):

```bash
python3 skills/permissions/scripts/codex_start.py --project /path/to/project
```

Interactive launch (requires a terminal):

```bash
python3 skills/permissions/scripts/codex_start.py --project /path/to/project --launch --interactive
```

Infrastructure broad access, if knowingly accepted:

```bash
python3 skills/permissions/scripts/codex_start.py --project /path/to/project --profile infrastructure --broad-infra --launch --interactive
```

The launcher reads global and project `config.toml` without modifying them; it refuses launch when either inspected file is malformed or a symlink. It reports that **effective permissions are not verified**, since managed policy, project trust, SSH, MCP, credentials, and external access may differ from local CLI flags.

**Security limitation:** `--broad-infra` requests `danger-full-access`. Neither the `on-request` approval flag nor this launcher guarantees per-operation approval for critical commands under that sandbox, especially via SSH/MCP/root. Use independently enforced remote permissions or isolation for that guarantee. The launcher never claims such enforcement. No new hooks or filters are silently installed.

Unit tests (offline): `python3 -m unittest discover -s tests -p 'test_codex_start*.py' -v`. Live Codex CLI validation is separate.
