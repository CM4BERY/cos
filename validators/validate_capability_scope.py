"""V1 -- Capability scope, expiry, computed risk, and required artifacts.

The transition is identified by the single ledger event this diff appends.
Risk is computed from the diff; the event's recorded risk_class is checked
against the computation (forbidden: risk_class_self_declaration_override),
and the decision recorded is checked against the risk lane.
"""
import sys

from cos_lib import (REPO, appended_events, changed_files, compute_risk,
                     load_capabilities, load_yaml, match_any, parse_ts,
                     report)

DECISION_FOR_RISK = {
    "low": "allow",
    "medium": "allow_with_constraints",
    "high": "require_review",
    "critical": "require_human",
}


def _evidence_files(tr, kind, failures, requirement):
    listed = (tr.get("evidence") or {}).get(kind) or []
    if not listed:
        failures.append(f"requirement '{requirement}': transition lists no evidence.{kind}")
        return
    for p in listed:
        if not (REPO / p).exists():
            failures.append(f"requirement '{requirement}': evidence file missing: {p}")


def run(base, head):
    failures, warnings = [], []
    scopes = load_yaml("policy/protected_scopes.yaml")
    risk_model = load_yaml("policy/risk_model.yaml")

    _, new_ev, prefix_ok = appended_events(base, head)
    if not prefix_ok or len(new_ev) != 1:
        failures.append("cannot identify the transition: expected exactly one appended ledger event (see validate_ledger)")
        return report("validate_capability_scope", failures)
    ev = new_ev[0]

    tr_path = f"transitions/{ev['transition_id']}.yaml"
    if not (REPO / tr_path).exists():
        failures.append(f"transition record missing: {tr_path}")
        return report("validate_capability_scope", failures)
    tr = load_yaml(tr_path)

    caps = load_capabilities()
    cap = caps.get(ev["capability_id"])
    if cap is None:
        failures.append(f"capability not found: {ev['capability_id']} (forbidden: execute_without_capability)")
        return report("validate_capability_scope", failures)

    if ev["actor"] != cap["issued_to_actor"]:
        failures.append(f"event actor {ev['actor']!r} does not hold capability {cap['id']} (holder: {cap['issued_to_actor']!r})")

    ts = parse_ts(ev["timestamp"])
    if not (parse_ts(cap["issued_at"]) <= ts <= parse_ts(cap["expires_at"])):
        failures.append(f"capability {cap['id']} not valid at {ev['timestamp']} (forbidden: expired_capability_use)")

    files = changed_files(base, head)
    computed, substantive = compute_risk(files, scopes, risk_model)
    for f in substantive:
        if not match_any(f, cap.get("allowed_targets")):
            failures.append(f"file outside capability scope: {f}")
        if match_any(f, cap.get("denied_targets")):
            failures.append(f"file in capability denied_targets: {f}")

    if ev["risk_class"] != computed:
        failures.append(f"recorded risk_class {ev['risk_class']!r} != computed {computed!r} (forbidden: risk_class_self_declaration_override)")
    if tr.get("advisory_risk_class") and tr["advisory_risk_class"] != computed:
        warnings.append(f"advisory_risk_class {tr['advisory_risk_class']!r} != computed {computed!r} (advisory ignored)")
    expected_decision = DECISION_FOR_RISK[computed]
    if ev["decision"] != expected_decision:
        failures.append(f"decision {ev['decision']!r} does not match risk lane {computed!r} (expected {expected_decision!r})")

    checks = {
        "valid_capability": lambda: None,   # this validator
        "ledger_event": lambda: None,       # validate_ledger
        "rollback_plan": lambda: None if (tr.get("rollback_plan") or "").strip()
            else failures.append("requirement 'rollback_plan': missing or empty in transition record"),
        "verification_note": lambda: None if (tr.get("verification_note") or "").strip()
            else failures.append("requirement 'verification_note': missing or empty in transition record"),
        "independent_review": lambda: _evidence_files(tr, "reviews", failures, "independent_review"),
        "human_approval": lambda: _evidence_files(tr, "approvals", failures, "human_approval"),
    }
    for requirement in risk_model["risk_classes"][computed]["requires"]:
        if requirement not in checks:
            failures.append(f"requirement {requirement!r} has no computable check in this validator (violates enforceability)")
        else:
            checks[requirement]()

    return report("validate_capability_scope", failures, warnings)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
