# Independent owner review — tr-0020 capability issuance

Reviewer: `human:boss <coltonmabery@gmail.com>`, distinct from transition actor
`agent:codex`.

Review decision: `AUTHORIZED`, issued in-session on 2026-07-12 after the exact
capability, publication, mutation, rollback, identity, digest, and compatibility
clauses were developed and before this issuance candidate was created.

## Scope reviewed

The reviewer approved a 72-hour capability issued to `agent:codex` for the
single A-0003 review-integrity amendment. The allowlist names each validator,
policy, governance, tooling, documentation, transition, ledger, and evidence
path. Unnamed targets are not authorized; constitution and secrets remain
denied.

The initial review stopped agent actions at local commit. After that candidate
was presented, the same human owner directly authorized and reviewed one
narrow operator exception: `agent:codex` may authenticate
`cm4bery-cos-executor[bot]` and invoke `cos_ship` for the frozen tr-0020
candidate only. The App may push/open the draft PR and observe checks, then
must stop before merge. tr-0021 publication remains human-only; ruleset
mutation belongs to `human:boss` acting as `CMABERY`; final review and merge
belong to `CMABERY` after the App's latest push.

The review accepts the explicit bootstrap constraint: current tooling cannot
scaffold issuance of a capability that is not already in a clean worktree.
The owner therefore ratifies this manual `tr-0020` candidate and requires
normal `--actor agent:codex` scaffolding for `tr-0021` after issuance merges.

## Compatibility reviewed

`tr-0020` uses the legacy independent-review rule. Bound-review v1 activates
only when A-0003 exists in the validated head, so this issuance and all
historical heads retain legacy semantics. The future amendment must require
exact resolved-base equality, recomputed paths, one byte-identical local/CI
digest routine, and an explicit statement that local reviewer inequality is
structural rather than authenticating. GitHub's final latest-push approval is
the authoritative identity locus.

This is owner review of the exact ratified issuance package, including the
tr-0020-only App invocation addendum, not a claim that the future A-0003
implementation already exists or passes. The only authorized tr-0020 external
state changes are the App push and draft-PR creation described above.

Disposition: **AUTHORIZED for issuance and agent-invoked App publication of
tr-0020 only; human review and merge remain required.**
