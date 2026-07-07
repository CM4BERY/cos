# Quickstart: your first governed transition

This file itself arrived through the protocol — transition `tr-0001`, event
`evt-0002`, under `cap-0000-genesis`. Reproduce the pattern:

```bash
# 1. Branch
git checkout -b my-change

# 2. Do the work (say, edit docs/notes.md)

# 3. Write the transition record
cat > transitions/tr-0002.yaml <<'EOF'
id: tr-0002
intent: "Describe the change and why."
requested_by: {actor: "agent:your-session", office: executor}
capability_id: cap-0000-genesis   # or a narrower capability issued to you
targets: ["docs/notes.md"]
advisory_risk_class: low
EOF

# 4. Append exactly one ledger event (prev = last event id)
printf '%s\n' '{"event_id": "evt-0003", "prev": "evt-0002", "timestamp": "2026-07-08T12:00:00Z", "type": "transition_committed", "actor": "agent:your-session", "office": "executor", "transition_id": "tr-0002", "capability_id": "cap-0000-genesis", "risk_class": "low", "decision": "allow"}' >> ledger/events.ndjson

# 5. Validate, then open the PR
git add -A
python3 validators/run_all.py --base origin/main --head WORKTREE
```

The risk class you write in the event is checked against the class computed
from your diff, and a mismatch is a denial [locus: validators/validate_capability_scope.py].
Lane rules for what each class demands are in `policy/risk_model.yaml`.
For a worked denial, see `evidence/test_runs/negative-test-denied.txt`: a
policy file edited under a self-declared "low" — caught, denied, five
failures itemized.
