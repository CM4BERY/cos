# Human ratification — cap-0003-review-integrity-amendment

Ratifier: Boss (human owner, coltonmabery@gmail.com)

Ratification: `AUTHORIZED`, issued in-session on 2026-07-12 before this
candidate was created. The first grounded UTC read after authorization fixed
the authority window at 2026-07-12T14:20:47Z through
2026-07-15T14:20:47Z, exactly 72 hours.

## Instrument ratified

The owner authorizes `agent:codex`, office `executor`, to carry the capability
issuance transition `tr-0020` and, only after that transition merges, the
single review-integrity amendment `A-0003` in `tr-0021`.

The exact repository targets are those written in
`capabilities/cap-0003-review-integrity-amendment.yaml`. They cover the one
amendment record; its risk and enforcement policy; the capability-scope
validator; the deterministic governance-debt tool and harness; the two named
documentation files; the two transition records; the append-only ledger; and
the named approval, review, simulation, and test evidence files. Every other
target remains outside the allowlist. `constitution/**` and `secrets/**` are
explicitly denied.

The owner also authorizes this identity exception for `tr-0020` and
`tr-0021` only:

- transition and event actor: `agent:codex`;
- scaffold `tr-0021` with `--actor agent:codex`;
- Git author: `codex (agent) <agent@cos.local>`.

This narrow exception supersedes the repository's default
`agent:claude-fable-5` scaffold and authorship values only for these two
transitions. The current scaffolder cannot bootstrap a capability that is not
already present in a clean worktree, so the owner expressly ratifies the
manual `tr-0020` issuance candidate. Normal tool scaffolding resumes for
`tr-0021` after `tr-0020` is merged and visible on `main`.

## External-action boundary

The initial package did not authorize the agent to publish. After the frozen
candidate was presented, `human:boss` issued a direct in-session addendum for
`tr-0020` only: `agent:codex` may authenticate the exact configured App and
invoke `cos_ship` to push `tr-0020`, create or resume its draft pull request,
and observe checks. The App must stop before merge. This addendum grants no
tr-0021 publication, merge, administrator or ruleset bypass, or ruleset-update
action. Owner-controlled publication and the exact ruleset mutation remain
recorded separately in:

- `evidence/approvals/cap-0003-owner-publication-authorization.md`; and
- `evidence/approvals/tr-0021-ruleset-mutation-authorization.md`.

For `tr-0021`, only `human:boss` may invoke the App. The agent may make
read-only ruleset GETs for evidence. Under COS v0,
`task_id`, `issued_for_office`, and `allowed_actions` remain documentary;
holder identity, validity time, and repository target paths are the fields
enforced by current validators. The owner's signature supplies the controlling
authority for the explicitly separated external actions.

## Amendment boundary

The owner ratifies `A-0003` as one coherent amendment: make review evidence
bind a canonical substantive diff, keep governance-debt reporting repo-local
while auditing every event-linked governed commit, and harden approval after
push at the platform locus.

Bound-review v1 activates only when `governance/amendments/A-0003.yaml` exists
in the validated head tree. Historical heads and `tr-0020` retain legacy
review semantics. The bound validator must resolve its `--base` to the exact
recorded `base_sha`, recompute changed paths, and use one byte-identical local
and CI digest implementation. A distinct declared reviewer proves structural
separation only; the final `CMABERY` approval of the App's latest push is the
authoritative identity-binding locus.

Scope ratified: the capability and the two external-action approval artifacts
as written in `tr-0020`. This approval does not waive computed risk,
validation, independent review, the phase boundary, or the owner-controlled
publication gate.
