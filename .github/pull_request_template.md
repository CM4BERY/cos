# Transition

One PR = one transition. The branch carries a transition record, a ledger
event, and evidence; CI recomputes risk from the diff and checks all of it
[locus: ci:cos-validate.yml].

- Transition record: `transitions/tr-NNNN.yaml`
- Ledger event appended: `evt-NNNN` (exactly one) [locus: validators/validate_ledger.py]
- Capability: `cap-...` (unexpired, scope covers every changed file) [locus: validators/validate_capability_scope.py]
- Advisory risk class: low / medium / high / critical (CI's computation wins) [locus: validators/validate_capability_scope.py]
- Rollback plan: in the transition record for medium risk and above [locus: validators/validate_capability_scope.py]

## Intent

<!-- What this transition changes and why. -->
