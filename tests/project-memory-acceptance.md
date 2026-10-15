# Project Memory / Handoff acceptance

| ID | Situation | Required outcome |
| --- | --- | --- |
| PM-01 | Existing ADR/runbook | Reuse it; don't create duplicate decision/lesson stores |
| PM-02 | No recorded knowledge | Do not create empty INDEX/DECISIONS/LESSONS |
| PM-03 | Native Memories disabled | Remain disabled until explicitly approved |
| PM-04 | config.toml has [features] already | No duplicate TOML section, no lost settings |
| PM-05 | User requests project setup | Single adaptive Q&A, no repeated global profile |
| PM-06 | Existing unmanaged HANDOFF.md | Refuse silent overwrite and propose adoption plan |
| PM-07 | Fresh significant milestone | Save complete handoff at confirmed project root |
| PM-08 | Subsequent milestone | Require current SHA before replacement |
| PM-09 | Two sessions attempt stale overwrite | Stale SHA must fail without corruption |
| PM-10 | Symlink or ../ outside root | Reject path |
| PM-11 | Handoff says branch A, actual branch B | Report mismatch before continuing |
| PM-12 | No tests executed | Status NOT RUN, not PASSED |
| PM-13 | A closed task | Mark status closed without live-service claim |
| PM-14 | Trivial operation/ordinary new chat | No automatic save or model-run self-check |
| PM-15 | User chooses local-only notes | Respect policy and do not expose private data to Git |
| PM-16 | User asks to enable RAG | Not installed by this MVP |
| PM-17 | Installed Skill modified by user | Preview before updating, do not wipe modifications |
| PM-18 | User asks to resume | Read handoff and verify references; no fabricated progress |

## Executable unit tests

Run from the package root:

    python3 -m unittest discover -s tests -p test_handoff.py -v

They verify missing/new handoff, SHA-guarded updates, rejection of unmanaged files, blocked status and path/symlink protection. These tests are not substitutes for a real interactive Codex CLI smoke test. Do not run them on every session.

During manual smoke testing, explicitly invoke $project-memory, create one handoff after a real milestone and resume it from a new Codex session. Confirm Git branch and facts were checked.
