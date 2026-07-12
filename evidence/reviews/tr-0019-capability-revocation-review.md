# Independent capability-revocation review — tr-0019

Reviewer: `agent:codex` (read-only authority audit, distinct from beneficiary
`agent:claude-fable-5`)

Date: 2026-07-12
Base: `origin/main` at
`ba6d437980123a1e22d187266018de662f76accc`
Revoked capability SHA-256:
`b44dbe457502d55c5d0ab13b0128ee2c1a3ad0abd307543a068df8336a81645e`

Conclusion: **READY.** The change strictly reduces authority and has no
substantive scope blocker.

## Checks

1. `cap-0002-publisher-transition.expires_at` and `evt-0019.timestamp` are
   byte-identical: `2026-07-12T12:38:08Z`.
2. COS uses an inclusive validity interval. `evt-0019` is valid at the upper
   boundary, and the earlier `evt-0017` and `evt-0018` timestamps remain
   inside the shortened interval.
3. The capability delta changes only `expires_at` and its audit note. Issuer,
   beneficiary, office, task, actions, targets, denials, issuance time, and
   revocability remain unchanged. No authority expands and no denial weakens.
4. Event chain, actor, office, capability, transition, risk, decision, and
   targets are coherent. The capability edit computes `high`; the recorded
   decision is `require_review`.
5. The exact capability file is allowed by the instrument. All other changed
   paths are protocol record paths covered by `transitions/**`,
   `ledger/events.ndjson`, or `evidence/**`; no denied target is touched.
6. Human ratification authorizes only the expiry shortening and annotation.
   The rollback plan prohibits automatic reactivation and requires a new
   owner-issued capability for any future authority.

## Sequencing note

COS v0 deliberately checks capability validity against the recorded event
timestamp rather than wall-clock publication time, as documented in
`constitution/threat_model.md`. The candidate branch is therefore frozen
after the expiry edit: no further substantive capability change is permitted.
`cos_ship` may publish the already-recorded transition because it reruns the
merge-time validators against `evt-0019`; until merge, authoritative `main`
still carries the prior live instrument. App publication creates a draft PR
and stops for distinct human review.

The complete five-validator suite, 40-assertion hook harness, and clean-diff
checks pass. Their exact results are recorded in
`evidence/test_runs/tr-0019-validation.txt`; governance debt is checked on the
committed candidate before publication.
