# Model Tiering & Token Efficiency — acceptance matrix (#9)

- MT-01 — Parent model/effort untouched; only child candidates selected.
- MT-02 — Routine tier selects an available verified economy candidate.
- MT-03 — Balanced fallback may escalate to Advanced, never silently downgrade.
- MT-04 — Advanced with no confirmed candidate returns inherit, not fabricated model.
- MT-05 — Corrupt, oversized or symlinked catalog refused.
- MT-06 — Codex without child model override support remains operational (inherit).
- MT-07 — Important diagnostics, counts and full evidence remain accessible.
- MT-08 — Changed process exit code: RTK comparison rejects.
- MT-09 — Modified JSON structure/value/type: rejects.
- MT-10 — Removed warning/error markers: rejects; changed arbitrary text requires human review.
- MT-11 — RTK absent: Model Tiering works with no hook or dependency.
- MT-12 — Project RTK hook never installed automatically; preflight inspects symlinks, current hooks and user config.
- MT-13 — If hook cannot be constrained to approved operations, skip hook and use manual audited RTK.
- MT-14 — Hook uninstall and rollback checked against original effective config (including user edits).
- MT-15 — No default changes to ~/.codex/config.toml, global hooks, production or external services.
- MT-16 — Live Codex spawn and real RTK integration only after separate installation approval.

Automated tests: `python3 -m unittest discover -s tests -p test_model_efficiency.py -v`.
Neither actual Codex subagent invocation nor RTK installation is covered by these offline unit tests.
