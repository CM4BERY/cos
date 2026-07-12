# Independent scope review — tr-0017

Reviewer: `agent:codex` (read-only authority audit; distinct from beneficiary
`agent:claude-fable-5`)

Date: 2026-07-12
Base: `origin/main` at
`075020978d1b5c6577e277474cc876af68e9e8ef`
Authority instrument SHA-256:
`d69a0b3a7003650115853c662fdfbda8346739910537a782dfd47f4be9135471`

Conclusion: **READY.** No substantive scope blocker was found.

## Checks

1. The issuer is the human owner and differs from the beneficiary.
2. `allowed_actions` exactly matches the four owner-approved action names.
3. `allowed_targets` contains the eleven owner-requested targets plus only the
   capability's exact self-path needed to carry this issuance. Glob matching
   permits that file and does not permit a sibling capability file.
4. `denied_targets` contains exactly `secrets/**` and `constitution/**`; no
   allowed target overlaps either denial.
5. The declared actor, office, and task are `agent:claude-fable-5`,
   `executor`, and `tr-0018`. The validity interval is exactly 604,800 seconds
   (seven days), from 2026-07-12T10:42:53Z through
   2026-07-19T10:42:53Z.
6. The issuance computes high risk because `capabilities/**` is elevated and
   carries both owner-ratification and independent-review evidence.
7. The branch is based exactly on `origin/main`; the unrelated
   `origin/tr-0016` runner-lock WIP is unchanged and none of its files appears
   in this transition.

## Enforcement caveat

COS v0 behavior was inspected directly. It enforces beneficiary identity,
validity time, and allowed/denied target paths. The schema validates
`task_id`, `issued_for_office`, and `allowed_actions`, but the current
validators and write gate do not behaviorally enforce those three fields.
The instrument and ratification disclose that limitation instead of claiming
hard task isolation. Elevated-scope PR validation and human review remain the
compensating enforcement gate, including for any proposed later edit to the
capability's exact self-path.

The append-only `evt-0017` event records computed `high` / `require_review`.
The complete five-validator suite passes on the transition diff. The hook
harness passes in its intended clean-`origin/main` fixture context; its
embedded ship test specifically asserts refusal on `main`. Exact results and
contexts are recorded in `evidence/test_runs/tr-0017-validation.txt`.
