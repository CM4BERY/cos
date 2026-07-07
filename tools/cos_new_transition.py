#!/usr/bin/env python3
"""All-or-nothing transition scaffold: branch + record + session state."""
import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validators"))
import yaml
from cos_lib import REPO, compute_risk, load_yaml, match_any, parse_ts


def sh(*args, check=True):
    r = subprocess.run(["git", "-C", str(REPO)] + list(args),
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("intent")
    ap.add_argument("--targets", nargs="+", required=True)
    ap.add_argument("--capability", default=None)
    ap.add_argument("--actor", default="agent:claude-fable-5")
    ap.add_argument("--office", default="executor")
    a = ap.parse_args()

    if not a.targets:
        sys.exit("refused: empty target list")
    if sh("status", "--porcelain"):
        sys.exit("refused: worktree is dirty — commit, or finish the current "
                 "transition first (python3 tools/cos_status.py)")

    ids = set()
    for f in (REPO / "transitions").glob("tr-*.yaml"):
        ids.add(int(f.stem[3:7]))
    for line in (REPO / "ledger" / "events.ndjson").read_text().splitlines():
        if '"transition_id": "tr-' in line:
            ids.add(int(line.split('"transition_id": "tr-')[1][:4]))
    tr_id = f"tr-{max(ids) + 1 if ids else 0:04d}"
    if sh("branch", "--list", tr_id):
        sys.exit(f"refused: branch {tr_id} already exists")

    now = datetime.now(timezone.utc)
    candidates = []
    for f in sorted((REPO / "capabilities").glob("*.yaml")):
        cap = yaml.safe_load(f.read_text())
        if a.capability and cap["id"] != a.capability:
            continue
        if cap.get("issued_to_actor") != a.actor:
            continue
        if not (parse_ts(cap["issued_at"]) <= now <= parse_ts(cap["expires_at"])):
            continue
        if all(match_any(t, cap.get("allowed_targets")) for t in a.targets) and \
                not any(match_any(t, cap.get("denied_targets")) for t in a.targets):
            candidates.append(cap)
    if not candidates:
        sys.exit(f"refused: no unexpired capability issued to {a.actor} covers "
                 f"all targets — ask the owner to issue one; never self-issue "
                 f"(forbidden: self_issued_capability_without_human_approval)")
    cap = sorted(candidates, key=lambda c: c["expires_at"])[-1]

    risk, _ = compute_risk(list(a.targets),
                           load_yaml("policy/protected_scopes.yaml"),
                           load_yaml("policy/risk_model.yaml"))

    sh("checkout", "-b", tr_id)
    record = {
        "id": tr_id,
        "intent": a.intent,
        "requested_by": {"actor": a.actor, "office": a.office},
        "capability_id": cap["id"],
        "targets": list(a.targets),
        "advisory_risk_class": risk,
        "rollback_plan": f"git revert the {tr_id} commit; no state outside the repo is touched.",
        "verification_note": "",
    }
    (REPO / "transitions" / f"{tr_id}.yaml").write_text(
        yaml.safe_dump(record, sort_keys=False, width=76))
    (REPO / ".cos").mkdir(exist_ok=True)
    (REPO / ".cos" / "session.json").write_text(
        __import__("json").dumps({"transition_id": tr_id,
                                  "capability_id": cap["id"]}, indent=2))
    print(f"scaffolded {tr_id} on branch {tr_id}")
    print(f"  capability: {cap['id']} (expires {cap['expires_at']})")
    print(f"  advisory risk from targets: {risk}")
    print(f"  record: transitions/{tr_id}.yaml — fill verification_note before validating")


if __name__ == "__main__":
    main()
