<!-- cos:locus-exempt-file -->
---
name: cos-transition
description: Execute a governed COS change end-to-end - scaffold the transition, edit within declared targets, append the ledger event, validate, and prepare the PR. Use for any change to files in this repo.
---

# Purpose
Carry one repository change through the COS transition protocol with evidence.

# When to use
Any request that changes any file in this repository, however small. If unsure
whether a change needs a transition, assume it does.

# Inputs
- The user's change request (intent).
- Output of `python3 tools/cos_status.py` (branch, active transition,
  capability, validation state).

# Workflow
1. Run `python3 tools/cos_status.py`. If a transition is already in flight,
   resume it; never nest transitions.
2. Restate scope: one-sentence intent, exact target paths, and what is
   explicitly out of scope. If targets are ambiguous, propose and ask first.
3. Check capability: an unexpired YAML in capabilities/ issued to you that
   covers every target and denies none. If none exists, STOP and ask the
   owner to issue one. Never issue authority for yourself.
4. Scaffold: `python3 tools/cos_new_transition.py "<intent>" --targets <paths>`
   (creates the branch, transitions/tr-NNNN.yaml, and .cos/session.json).
5. Do the work. Edit only declared targets — the write gate enforces this.
   If scope legitimately grows, update the transition record's target list
   first; that record edit is the auditable scope-change act.
6. If the diff may score medium or above, fill in rollback_plan and
   verification_note in the transition record.
7. Append the event: `python3 tools/cos_append_event.py --transition tr-NNNN`.
   The tool computes the risk class from the diff; never hand-write it.
8. Validate: `bash tools/cos_validate.sh`. On FAIL, fix the cause and rerun.
   Never adjust recorded risk to silence a mismatch — the computed class wins.
9. Delegate to the transition-auditor subagent if available; address findings.
10. Commit with agent authorship:
    `git commit --author="claude-fable-5 (agent) <agent@cos.local>"`.
11. Ask the user before pushing (the bash guard will ask anyway).
12. Produce a PR body matching .github/pull_request_template.md.

# Stop conditions
Stop and ask the user if: no covering capability exists; the change touches
constitution/, capabilities/, or secrets/**; computed risk is high or
critical (name the lane's requirements); validators fail twice on the same
cause; or the next action would push, publish, delete, or force anything.

# Output
Branch, commit hash, transition id, event id, computed risk class, the
validator RESULT line, evidence paths, auditor verdict, PR body.

# Verification
The final response quotes the RESULT line from tools/cos_validate.sh run in
this session — or states exactly what was not run and why.
