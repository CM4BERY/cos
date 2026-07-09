# Independent review — tr-0014 (cos-amendment skill: the automation-layer §4 amendment procedure)

Reviewer: independent review sub-agent — independent of executor
agent:claude-fable-5. Spawned in a separate context with no access to the
executor's reasoning; verdict reached from primary sources only.
Date: 2026-07-09

Change reviewed: 135 insertions / 2 deletions across exactly the two declared
targets — `.claude/skills/cos-amendment/SKILL.md` (new, 125 insertions: the
§4 procedure as a skill — problem-with-ledger-evidence, `A-NNNN.yaml` record,
simulation note, loci update, one governed transition, explicit
authority-expansion statement, constitution handed to the owner) and
`docs/ralph-backlog.yaml` (10 insertions / 2 deletions: story-002 `passes`
flipped false→true and a learnings note added). The remaining diff is the
two record paths this transition writes by protocol: one appended ledger
event (`evt-0015`) and the transition record `transitions/tr-0014.yaml`.
Nothing lies outside the declared targets plus record paths.

Basis — my own re-execution, not the executor's self-report. On this working
tree (HEAD == origin/main == 32c1f9a; the change is uncommitted, so I reviewed
the working tree, which is what `cos_validate.sh --head WORKTREE` scores) I
re-ran `bash tools/cos_validate.sh` (reproduced `RESULT: FAIL -- transition is
denied`, sole failure `requirement 'independent_review': transition lists no
evidence.reviews`; every other validator PASS) and `bash tools/test_hooks.sh`
(reproduced `HARNESS: ALL PASS`, including `PASS skill hygiene:
.claude/skills/cos-amendment/SKILL.md` and the ship-bypass deny fixture). I
inspected the append with `git diff HEAD -- ledger/events.ndjson` (exactly one
line, `evt-0015`, `prev: evt-0014`, append-only) and `git diff HEAD --
docs/ralph-backlog.yaml` (the passes-flip rides inside this transition's own
diff, not added after the fact). I read in full: the new SKILL.md,
`transitions/tr-0014.yaml`, `docs/ralph-backlog.yaml`, `policy/risk_model.yaml`,
`policy/navigation.yaml`, `policy/protected_scopes.yaml`,
`schemas/amendment.schema.json`, `validators/validate_capability_scope.py`,
`validators/cos_lib.py`, `capabilities/cap-0001-agent-standing.yaml`,
`docs/automation-layer.md` (§4/§6), `tools/test_hooks.sh`,
`.claude/hooks/cos_bash_guard.py`, `.claude/skills/cos-transition/SKILL.md`,
and the merge-control section of `tools/cos_ship.py`. None of this rests on the
executor's assertions; each was re-derived from the file or command output.

What I confirmed at source: computed risk is `high` and correctly so —
`compute_risk` scores `.claude/skills/cos-amendment/SKILL.md` against elevated
`.claude/**` while `docs/ralph-backlog.yaml` is low `docs/**` and record paths
are exempt (`validators/cos_lib.py` lines 110-125); the recorded `risk_class`
equals the computed class, so the tool computed it (a hand-written class would
have tripped `risk_class_self_declaration_override`). `cap-0001-agent-standing`
covers both targets (`.claude/**`, `docs/**`), denies neither, was unexpired at
the event timestamp (issued 2026-07-08, expires 2026-08-07; stamped
2026-07-09), and no target touches the hard excludes `constitution/**`,
`secrets/**`, `capabilities/**`. `policy/navigation.yaml` maps `high` and
`critical` to `review`, and `tools/cos_ship.py` (lines 126-128, 227-228) stops
before merge on a review lane; `.claude/hooks/cos_bash_guard.py` (lines 25-28)
denies agent-run `cos_ship.py --bypass`. Read as a reviewer and not a linter,
the skill's procedure is correct and safe: it reinforces the write gate, the
no-self-approval rule, and codeowners; it hands constitution changes to the
owner rather than executing them; and its central rule — "loosening the checker
instead of amending the rule is the failure this skill exists to prevent" —
is exactly right. Nothing in the diff weakens a gate, expands authority, or
edits an enforcement mechanism; the only substantive file is a procedure doc.

The gate is my verdict, not the validator. `validators/validate_capability_scope.py::_evidence_files`
satisfies the `independent_review` requirement by the mere existence of a file
listed under `transition.evidence.reviews`: it checks the list is non-empty and
that each path exists on disk, and it never opens the file, never inspects its
content, and never checks its authorship. A future auditor must not read a
green `validate_capability_scope` as evidence that a review happened or that a
reviewer agreed — the check would pass on an empty or adversarial file just the
same. The substantive judgement recorded in this document, not the validator's
PASS, is the real independent-review gate for tr-0014.

Non-blocking observations:
- `schemas/amendment.schema.json` sets `additionalProperties: false` and
  defines no `expected_effect` property, so §4's "expected effect" cannot be a
  standalone amendment field. The skill handles this correctly (SKILL.md lines
  62-65): it routes expected effect into a `reason[]` entry that predicts what
  changes for whom and expands it in the simulation note under `evidence/`.
  This is the only schema-valid way to carry it and is faithful to §4; I flag
  it only so a later reader does not expect a literal `expected_effect:` key in
  A-NNNN records.
- Every locus and tool the skill names resolves to a file that exists
  (`policy/enforcement_loci.yaml`, `validators/validate_enforcement_claims.py`,
  `validators/validate_no_self_approval.py`, `.claude/hooks/cos_write_gate.py`,
  `tools/governance_debt.py`, `tools/cos_status.py`, and an existing
  `governance/amendments/A-0001.yaml` exemplar). The skill points at no phantom
  files.
- The `cos_validate.sh` RESULT is FAIL, but solely for the expected
  `independent_review` placeholder; recording this file under
  `evidence/reviews/` and listing it in the transition's `evidence.reviews`
  is what flips it to PASS. That is a mechanical follow-up, not a defect in the
  work.

Provenance — stated precisely, without flattery. This is not owner
ratification. Unlike tr-0009, where the reviewer was the human owner and the
artifact recorded the owner's own decision, I am a sub-agent spawned by the
executor's own session. The owner directed that a sub-agent review occur, but
the owner has not personally reviewed this diff. My independence is procedural
— a separate context, primary sources, and no access to the executor's
reasoning — and not organizational: I am not a different party from the
executor in any accountability sense, only a different context. Do not read
this file as the owner's approval. The platform half of the gate — the
review-mode merge on GitHub under the pinned account CMABERY — remains the
owner's act and is not completed by this review.

Disposition: READY. Confidence: high. The single thing that would change it:
if the workflow intended "expected effect" to be a literal field of the
amendment schema — but I read `schemas/amendment.schema.json` directly and its
`additionalProperties: false` forbids that, making the skill's routing into
`reason[]` plus the simulation note the correct and only schema-valid design,
so I do not expect this to change.
