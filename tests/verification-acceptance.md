# Verification & TDD acceptance (#7)

- VE-01 README-only edit selects Light without artificial RED/GREEN.
- VE-02 reproducible bug follows RED for expected reason, then GREEN.
- VE-03 API contract/critical behavior gets meaningful tests and negative cases.
- VE-04 Infrastructure/firewall task uses Strict but no unsafe live test without permission.
- VE-05 PASS with missing evidence is rejected; evidence itself requires human/tool confirmation.
- VE-06 FAIL outranks unrun checks; BLOCKED and NOT_RUN do not become Verified.
- VE-07 critical NOT_RUN in Strict reports Partially Verified.
- VE-08 previous failures separated from current regressions if possible.
- VE-09 no separate compulsory test framework or empty plan files.
- VE-10 Handoff includes honest check status and references for resuming.
