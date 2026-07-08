# COS v0 — Git-native Constitutional Operating System

[![cos-validate](https://github.com/CM4BERY/cos/actions/workflows/cos-validate.yml/badge.svg)](https://github.com/CM4BERY/cos/actions/workflows/cos-validate.yml)

Merge is the only door. Every state change arrives as a pull request carrying
a transition record, a capability, exactly one ledger event, and evidence.
Risk is computed from the diff, never from the requester's declaration
[locus: validators/validate_capability_scope.py]. The ledger is append-only
[locus: validators/validate_ledger.py]. Normative claims in documentation
need an enforcement locus or they fail CI [locus: validators/validate_enforcement_claims.py].
The threat model this defends is stated in `constitution/threat_model.md`.

## How a change happens

1. Hold a capability: a YAML in `capabilities/` issued to you by someone
   else. Self-issuance without a human-approval artifact fails validation
   [locus: validators/validate_no_self_approval.py], and `capabilities/` is
   an elevated scope so merging one takes the owner's review [locus: codeowners].
2. Branch and do the work.
3. Write `transitions/tr-NNNN.yaml`: intent, targets, capability id, and a
   rollback plan for medium risk and above [locus: validators/validate_capability_scope.py].
4. Append exactly one event to `ledger/events.ndjson` with `prev` linking the
   last event [locus: validators/validate_ledger.py].
5. Validate locally, then open a PR (CI runs the same command) [locus: ci:cos-validate.yml]:

```bash
git add -A
python3 validators/run_all.py --base origin/main --head WORKTREE
```

Merging is gated by risk lane: high risk takes an independent review and
critical risk takes the human owner [locus: branch-protection, codeowners].
See `policy/autonomy_lanes.yaml`.

## One-time setup after pushing to a host

Branch protection and CODEOWNERS live in the hosting platform, so three
manual steps complete the gateway [locus: manual]:

1. Replace `@OWNER` in `.github/CODEOWNERS` with the owner's username.
2. Protect `main`: make `cos-validate` a passing status check before merge,
   demand one approving review (CODEOWNERS for protected paths), and disable
   force pushes and deletions.
3. Allow only squash merge, so one merge = one transition = one ledger event.

Until those are set, only the CI half of the gateway is live — treat lanes 3
and 4 as not yet open.

## Layout

```text
constitution/   identity, principles, threat model      (critical scope)
policy/         risk model, scopes, lanes, loci         (elevated scope)
schemas/        transition, capability, event, amendment (elevated scope)
capabilities/   issued authority, narrow and expiring   (elevated scope)
transitions/    one record per transition                (record path)
ledger/         events.ndjson, append-only               (record path)
evidence/       approvals, reviews, test runs            (record path)
validators/     the five checks below + run_all.py       (elevated scope)
docs/           narrative documentation                  (low risk)
```

## The five validators

`validate_ledger` (append-only history, one event per transition),
`validate_schemas` (every governed record matches its schema),
`validate_capability_scope` (scope, expiry, computed risk, artifacts per lane),
`validate_enforcement_claims` (no rule without a locus),
`validate_no_self_approval` (no self-issued authority).

## Genesis

`evt-0001` records the constitution's ratification by the human owner;
the ratification evidence is `evidence/approvals/tr-0000-human-ratification.md`.
Every commit after genesis is a governed transition — including changes to
COS itself, which enter as amendments (`schemas/amendment.schema.json`)
through protected paths [locus: codeowners].

The architecture this implements, and the v1/v2 growth path, are in
`docs/target-architecture.md`.
