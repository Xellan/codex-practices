# Permissions acceptance (#4)

| ID | Scenario | Expected |
| --- | --- | --- |
| PG-01 | Read-only preview | No Codex session, no file/config mutations |
| PG-02 | No --profile supplied for noninteractive launch | Refuses |
| PG-03 | TTY --interactive | Proposes a profile, waits for actual selection and confirmation |
| PG-04 | No TTY with --interactive | Refuses rather than silently selecting |
| PG-05 | Review / Development / Infrastructure restricted | read-only / workspace-write / workspace-write |
| PG-06 | Broad Infrastructure chosen | Distinct BROAD + BROAD_INFRA_THIS_SESSION for interactive flow |
| PG-07 | Invalid/symlinked TOML user/project file | Redacted failure on launch; preview stays read-only |
| PG-08 | TOML includes secrets and MCP config | Audit prints only fixed metadata, not secrets/servers |
| PG-09 | Mixed native permissions and sandbox keys | Emits conflict warning, makes no writes |
| PG-10 | No #5 scanner or truncated/skipped files | Reports incomplete, requires INCOMPLETE_SCAN_REVIEWED before launch |
| PG-11 | HIGH-risk external instructions | Requires HIGH_RISK_REVIEWED independently |
| PG-12 | Unsupported Codex CLI / missing flags | Refuses launch before any normal session |
| PG-13 | Mock supported Codex CLI | Receives exactly the approved sandbox and approval args |
| PG-14 | Broad privilege and destructive SSH/MCP/root | **Not guaranteed to be approved**; no misleading security promise |
| PG-15 | Saved global config / shortcuts | Unmodified after preview and launch |
| PG-16 | Live Codex plus actual privilege policy | Manual disposable-environment E2E required before claiming effective protection |

Execute the isolated offline tests:

    python3 -m unittest discover -s tests -p test_codex_start.py -v

The helper uses logical launch presets, not guaranteed native --profile files. The risk scanner is heuristic, and acknowledgements (particularly via CLI flags) are not independent authorization. Test the real CLI in a disposable project; do not use production machines for destructive verification.
