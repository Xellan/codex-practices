# Verification & TDD — module №7

Adaptive checks with **risk priority**: Light (local/low risk), Standard (typical development), Strict (high impact/security/infrastructure). Acceptance criteria precede changes, but TDD is required only where behavioral tests genuinely help: reproducible defects, complex business logic and API contracts. A failed import is not meaningful RED. For configuration/infra use syntax/behavior checks in an authorized safe environment.

## Execution

1. Audit actual project tests, build system, scope, current Git state and expected acceptance criteria. Reuse native pytest, unittest, Vitest, Go tests etc.; do **not** create a parallel test framework.
2. Decide Light/Standard/Strict by impact; note why Strict applies. Prefer targeted tests, then relevant regressions, then extended checks when needed. User can explicitly raise or lower requested depth, but skipped critical checks must remain visible.
3. Save actual evidence and command outcomes; avoid inventing PASS. No automatic production tests, firewall disruption, remote deployments or extra permission grants.
4. Optional machine-readable final report via [script](../skills/verification/scripts/verification_report.py). Example **illustrative data**, not an executed result:

```json
{"level":"strict","checks":[
 {"name":"unit tests","status":"PASS","evidence":"build/test-log.txt, exit 0","critical":true},
 {"name":"staging rollback","status":"NOT_RUN","evidence":"Staging environment unavailable","critical":true}
]}
```

```sh
python3 /path/to/codex-practices/skills/verification/scripts/verification_report.py --input /safe/evidence.json
```

The script computes Verified / Partially Verified / Failed / Blocked based on **user-supplied evidence**. It cannot confirm whether an asserted command truly ran or whether tests cover requirements. Before publishing the result, Codex must independently inspect actual output or records. Script exit 0 means all statuses PASS; exit 1 indicates incomplete/failed/blocked; exit 2 means invalid evidence. For Strict, no Verified if a critical check is not PASS.

5. Report concise results for Light/Standard and detailed Evidence Report for Strict or incomplete outcomes; Handoff (#3) stores only current state and evidence pointers, not raw logs.
6. On test failure determine whether it predates the change; diagnose before additional attempts. No infinite retries and no unattended production tests.

Run isolated tests: `python3 -m unittest discover -s tests -p test_verification_report.py -v`. See [acceptance scenarios](../tests/verification-acceptance.md). Integration with existing AGENTS.md is a short durable rule, not a new mandatory document per task.
