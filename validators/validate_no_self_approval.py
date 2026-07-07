"""V5 -- No actor approves its own authority expansion.

Every capability's issuer differs from its beneficiary. If a transition adds
or modifies a capability whose beneficiary is the transition's own actor
(self-issuance), an explicit human-approval artifact is demanded (forbidden:
self_issued_capability_without_human_approval). PR author != approver is the
hosting platform's half of this invariant (locus: branch-protection).
"""
import sys

import yaml

from cos_lib import REPO, appended_events, changed_files, load_yaml, report


def run(base, head):
    failures = []

    for capfile in sorted((REPO / "capabilities").glob("*.yaml")):
        cap = yaml.safe_load(capfile.read_text())
        if cap.get("issued_by") == cap.get("issued_to_actor"):
            failures.append(f"{capfile.name}: issued_by == issued_to_actor ({cap.get('issued_by')!r})")

    _, new_ev, prefix_ok = appended_events(base, head)
    ev = new_ev[0] if (prefix_ok and len(new_ev) == 1) else None

    changed_caps = [f for f in changed_files(base, head)
                    if f.startswith("capabilities/") and f.endswith(".yaml")]
    for f in changed_caps:
        p = REPO / f
        if not p.exists():
            continue
        cap = yaml.safe_load(p.read_text())
        if ev and cap.get("issued_to_actor") == ev["actor"]:
            tr_path = REPO / f"transitions/{ev['transition_id']}.yaml"
            approvals = []
            if tr_path.exists():
                approvals = (load_yaml(f"transitions/{ev['transition_id']}.yaml")
                             .get("evidence") or {}).get("approvals") or []
            ok = approvals and all((REPO / a).exists() for a in approvals)
            if not ok:
                failures.append(
                    f"{f}: transition actor {ev['actor']!r} is the capability's beneficiary "
                    f"and no human-approval artifact is recorded "
                    f"(forbidden: self_issued_capability_without_human_approval)")

    return report("validate_no_self_approval", failures)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
