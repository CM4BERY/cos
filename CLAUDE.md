# CLAUDE.md — COS repository

## What this repo is
A Git-native Constitutional Operating System: the repo is the state, merge is
the only transition, CI validators are the policy engine. Every merged change
carries one ledger event, one transition record, one valid capability, and
evidence. Architecture: docs/target-architecture.md. Protocol walkthrough:
docs/quickstart.md. Automation layer spec: docs/automation-layer.md.

## Commands (confirmed)
- Validate staged work:   bash tools/cos_validate.sh
  (wraps: git add -A && python3 validators/run_all.py --base origin/main --head WORKTREE)
- Start a transition:     python3 tools/cos_new_transition.py "<intent>" --targets <paths>
- Append a ledger event:  python3 tools/cos_append_event.py --transition tr-NNNN
- Recover session state:  python3 tools/cos_status.py
- Governance debt report: python3 tools/governance_debt.py   (Stage 3; may not exist yet)
- CI validation:          .github/workflows/cos-validate.yml
- Dependencies: python3 + pyyaml + jsonschema. Do not add dependencies
  without an amendment (policy change).

## Repo map
- constitution/  identity, principles, threat model — critical scope, owner-ratified
- policy/        risk model, scopes, lanes, loci    — elevated scope
- schemas/       four JSON Schemas (draft-07)       — elevated scope
- capabilities/  issued authority, expiring YAMLs   — elevated scope; only the owner merges these
- validators/    five checks + run_all.py + cos_lib — elevated scope
- .github/       CI gateway, CODEOWNERS, template   — elevated scope
- .claude/       agent automation (hooks, skills)   — elevated scope (amendment A-0001)
- transitions/ ledger/ evidence/                    — record paths (exempt from scope risk)
- docs/ README.md                                   — low risk
- tools/                                            — medium risk (default)
- .cos/                                             — local session state, gitignored, never commit

## Risk lanes (computed from the diff; declarations are advisory only)
- low: allow
- medium: allow with rollback plan and verification note [locus: validators/validate_capability_scope.py]
- high: independent review to merge [locus: branch-protection]
- critical: human ratification to merge [locus: codeowners]
Details: policy/risk_model.yaml.

## Standing rules
- Never edit ledger/events.ndjson by hand or via shell redirection. Use
  tools/cos_append_event.py. The write gate denies everything else
  [locus: .claude/hooks/cos_write_gate.py].
- Never write the risk class from judgment alone; the tool records what the
  policy computes [locus: tools/cos_append_event.py].
- One PR = one transition = exactly one appended ledger event
  [locus: validators/validate_ledger.py].
- Commit as the agent: git commit --author="claude-fable-5 (agent) <agent@cos.local>"
- Do not claim validators pass unless bash tools/cos_validate.sh ran in this
  session and its RESULT line is quoted verbatim. If validation was not run,
  say exactly what was not run and why.
- Before touching more than one non-record file, restate scope as the target
  list in the transition record; the write gate holds you to it afterward
  [locus: .claude/hooks/cos_write_gate.py].
- Stop and ask before: pushing, touching capabilities/ or constitution/ or
  secrets/**, issuing or modifying agent authority, or proceeding without an
  unexpired capability covering the targets.
- Skill auto-activation is not a safety boundary. Invoke explicitly:
  /cos-transition for any repo change; /cos-amendment for rule changes;
  /cos-add-validator to make prose rules computable.
- Static facts go in this file. Procedures go in .claude/skills/. Hard
  enforcement goes in hooks, validators, and deterministic tools. Noisy
  investigation goes to subagents.
