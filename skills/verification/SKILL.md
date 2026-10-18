---
name: verification
description: Define acceptance criteria, apply risk-adaptive TDD and verify implementation with actual evidence. Use for coding, high-risk configuration changes and final sign-off, not merely for responding to questions.
---

# Verification & adaptive TDD

Classify work by **consequence of error**, not only code size:
- **Light** for documentation or isolated trivial edits: a targeted result check.
- **Standard** for normal features and fixes: criteria + focused tests + relevant regression checks.
- **Strict** for critical configuration, security, wide contracts, irreversible or high-impact changes: documented criteria, meaningful negative/edge scenarios and verified rollback/recovery when safe and authorized.

Before implementation define concise testable acceptance criteria. Prefer RED→GREEN→REFACTOR when correcting a reproducible bug, implementing testable complex logic or changing an API contract. RED must fail for the **expected behavioral reason**; broken imports/env setup do not count. For infrastructure config use config validation, safe staging/smoke tests and real observations instead of contrived unit tests. Never run destructive tests solely to attain full coverage; follow permissions #4.

Start with narrow tests; widen based on risk. Do not run endless retries without a new diagnosis. Differentiate pre-existing failures from regressions where possible.

Use `scripts/verification_report.py --input /path/to/evidence.json` on user-approved evidence data. Statuses are PASS / FAIL / NOT_RUN / BLOCKED and `critical` flags. The script verifies schema and that PASS contains a reference, **not the truth** of the evidence. Every PASS must refer to an actual command/output/artifact; never fabricate. Treat critical unrun tests as Partially Verified or Blocked, not Verified. Keep full logs available separately when safe; don't persist secrets in Handoff.

Only orchestrator (#8) signs off combined result. Project Memory/Handoff (#3) records meaningful milestone status, evidence pointers and outstanding checks; it is not a live test reporter. No compulsory files or extra model calls for tiny tasks.
