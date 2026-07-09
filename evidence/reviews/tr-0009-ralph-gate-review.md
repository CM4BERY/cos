# Independent review — tr-0009 (Ralph gate: high/critical lanes flip to review)

Reviewer: Boss (human owner) — independent of executor agent:claude-fable-5
Date: 2026-07-08 (decision given in-session, 2026-07-09T02:19Z)

Change reviewed: 36 insertions / 5 deletions across exactly the declared
targets — policy/navigation.yaml (high and critical bypass lanes flip from
`flag` to `review`; C3 primary locus), .claude/hooks/cos_bash_guard.py
(deny rule for agent-run `cos_ship.py … --bypass`, defense-in-depth),
tools/test_hooks.sh (three fixtures: ship-bypass deny, plain-ship allow
control, write-gate expired-capability deny via cap-9998), and
docs/navigation-layer.md §7 item 4 (review-mode audit trail: the one-line
reason becomes the human's PR review/merge comment).

Basis: not the executor's self-report. A separate verification session
re-executed the evidence on this working tree: tools/test_hooks.sh
reproduced `HARNESS: ALL PASS`; tools/cos_validate.sh reproduced
`RESULT: FAIL -- transition is denied` with the sole failure being this
file's absence — the gate blocking exactly as designed. The expired-capability
fixture was traced through cos_write_gate.py's decision order: for cap-9998
no branch other than the expiry check (which precedes target parsing) can
produce the deny, so the fixture covers the previously unexercised branch
specifically. cos_ship.py mechanics were confirmed at source: it loads
policy/navigation.yaml from the checked-out branch and refuses to ship from
a non-transition branch, so this transition ships under its own flipped
policy; the flag/--bypass code path is dead for every configured lane.

Deviation accepted (repo-wins): the work order expected a typed `--bypass`
under pre-flip policy; mechanically this merge runs review-mode instead.
The human gate is preserved and strengthened — the tool stops before merge,
and the owner's one-line reason is recorded as the PR review/merge comment
per docs/navigation-layer.md §7 item 4.

Environment findings acknowledged, non-blocking, noted for follow-up
transitions: harness cleanup silently fails on the sandbox mount (deletes
require an out-of-band permission grant), so a green run can still litter
capabilities/ until cleaned — the harness should verify its own cleanup so
ALL PASS implies a clean tree. Review-mode ships exit before cos_ship's
post-merge ledger verification (P11); that check currently rests on CI for
review lanes.

Provenance: the approval decision is the owner's, given in the Cowork
session after reading the independent verification memo; this file was
recorded at the owner's direction by the verifying agent session. The
platform half of the gate — the review-mode merge on GitHub under the
pinned account CMABERY — is completed by the owner, not the agent.

Disposition: approved.
