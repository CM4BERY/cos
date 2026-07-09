---
name: cos-amendment
description: Change a governing rule as a governed amendment - problem statement with ledger evidence, an A-NNNN amendment record, a simulation note, locus updates, and one transition. Use when a policy, schema, validator, or constitutional rule would change rather than be obeyed.
---
<!-- cos:locus-exempt-file -->

# Purpose
Turn friction with a rule into a ratified change of that rule, carrying the
evidence that justified it and the loci that will enforce it, through one
governed transition.

# When to use
Any request that would change a governing rule rather than comply with it:
policy, schemas, validators, enforcement loci, or the constitution. The usual
symptoms are a validator that blocks work which ought to be legal, a rule that
names no enforcement locus, or the same waiver recurring in `.cos/waivers.log`.

Loosening the checker instead of amending the rule is the failure this skill
exists to prevent. If you are editing a validator to make your own change
pass, stop: that is an amendment wearing a disguise.

# Inputs
- The rule to change and the friction that motivated it.
- `python3 tools/cos_status.py` - branch, active transition, capability.
- `ledger/events.ndjson` and `.cos/waivers.log` - the evidence base.
- `python3 tools/governance_debt.py` - recurring bypasses, drift, expired-capability use.

# Workflow

1. **State the problem, grounded in the ledger.** Name the rule as it stands
   today, then cite the recorded events that show it failing: event ids from
   `ledger/events.ndjson`, waiver lines, blocked transitions, debt-report
   findings. An amendment with no ledger evidence behind it is a preference,
   not a finding — say so plainly and stop. Never open with the proposed
   change; the problem earns the change.

2. **Check scope and capability before editing.** An amendment usually touches
   elevated scope. Confirm an unexpired capability issued to you covers every
   target and denies none; every write is re-checked at write time
   [locus: .claude/hooks/cos_write_gate.py]. If no capability covers the
   targets, stop and ask the owner to issue one. Never issue authority for
   yourself [locus: validators/validate_no_self_approval.py].

3. **Scaffold exactly one transition** via /cos-transition, declaring the
   amendment record, the rule file, and the loci file as targets. The
   amendment and the rule change ride in the same transition; a rule that
   changes without its amendment record is unexplained, and an amendment that
   never lands is a wish.

4. **Write the amendment record** at `governance/amendments/A-NNNN.yaml`,
   using the next unused id. Its fields are fixed by
   `schemas/amendment.schema.json`, which admits no additional properties
   [locus: validators/validate_schemas.py] — read the schema and do not invent
   keys. The record carries:
   - `proposed_change` as literal `from`/`to` text, quoting the rule before
     and after, so a reader can diff the rule without leaving the record;
   - `reason` as the argument from the evidence in step 1;
   - `rollback` as the concrete act that undoes it, naming the transition to
     revert and any state outside the repo it would leave behind;
   - `target` and `evidence` pointing at the rule file and the artifacts.

   The schema has no field for the expected effect. Put it in the record as a
   `reason` entry that predicts what changes for whom, and expand it in the
   simulation note. An expected effect that cannot be stated as a prediction
   is not understood well enough to ratify.

5. **Write the simulation note** under `evidence/`, referenced from the
   record's `evidence` list. Replay the amended rule against real history:
   walk the relevant ledger events and, for each, say whether the amended rule
   would have changed the recorded decision. Then name who benefits — actor by
   actor, office by office. A simulation that finds no changed outcome argues
   the amendment is unnecessary; a simulation whose only beneficiary is the
   proposer argues it is self-serving. Both are results worth reporting rather
   than reasons to bury the note.

6. **Make the authority-expansion statement explicit.** State in one line
   whether the amendment expands anyone's authority, who the beneficiary is,
   and who approves. When the beneficiary is the proposing actor, the approver
   is a human who is not the beneficiary — an actor never ratifies its own
   authority expansion [locus: validators/validate_no_self_approval.py,
   branch-protection]. If you cannot name an approver who is not the
   beneficiary, stop and hand the amendment to the owner.

7. **Update the enforcement loci.** A rule that changes usually changes what
   enforces it. Update `policy/enforcement_loci.yaml` in the same transition
   so every risk class and forbidden rule still resolves to a locus that
   exists [locus: validators/validate_enforcement_claims.py]. If the amended
   rule has no computable locus, it needs a different locus — a human gate, a
   branch protection — not a validator that pretends to check it. Making a
   prose rule computable is /cos-add-validator's job, not this skill's.

8. **Constitutional changes are handed to the owner, not executed.** Writes
   under `constitution/` are ask-gated at the hook [locus:
   .claude/hooks/cos_write_gate.py] and require human ratification to merge
   [locus: codeowners]. Prepare the amendment record, the simulation note, and
   the diff you would make; present them; let the owner act. Preparing the
   argument is in scope. Merging the change is not.

9. **Close the transition through /cos-transition's tail** - append the event
   with the tool, validate, commit with agent authorship, ship. The computed
   risk class governs the merge mode [locus: policy/navigation.yaml]; on a
   review lane the ship tool opens the PR and stops before merging, and you
   present the URL rather than completing it.

# Stop conditions
Stop and ask the user if: the amendment has no ledger evidence behind it; no
capability covers the targets; the change touches `constitution/`,
`capabilities/`, or `secrets/**`; the only beneficiary of the change is the
actor proposing it and no other approver can be named; the simulation shows no
replayed outcome would have changed; the amended rule has no resolvable
enforcement locus; validators fail twice on the same cause; or the next action
would push, publish, delete, or force anything.

# Output
The amendment id and record path, the problem statement with the ledger event
ids it rests on, the from/to text, the expected effect, the simulation note
path with its replayed outcomes and named beneficiaries, the
authority-expansion statement with its approver, the loci updated, the
transition id, the computed risk class, the validator RESULT line, and the PR
URL.

# Verification
The final response quotes the RESULT line from `bash tools/cos_validate.sh`
run in this session - or states exactly what was not run and why. An amendment
presented without a fresh validation is a draft, and must be labelled one.
