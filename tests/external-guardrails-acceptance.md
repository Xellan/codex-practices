# External Content Guardrails acceptance (#5)

- EX-01: high-risk role-spoofing plus instruction override detected before Codex launch.
- EX-02: benign documentation describing prompt injection does not trigger HIGH.
- EX-03: hidden Unicode and encoded blocks raise signals.
- EX-04: symlinks, oversized files, binaries and capped scans handled without execution.
- EX-05: report records source and signal only, never full malicious instructions.
- EX-06: launcher with installed scanner refuses to launch on scanner failure.
- EX-07: HIGH requires risk acknowledgement in addition to chosen permission profile.
- EX-08: missing scanner never reported as verified clean.
- EX-09: direct Codex starts, hosted web tools and arbitrary root/SSH/MCP remain outside guaranteed enforcement.
- EX-10: external source is never promoted into trusted AGENTS instructions or Handoff automatically.
