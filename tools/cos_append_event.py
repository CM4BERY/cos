#!/usr/bin/env python3
"""Compose, validate, and append one ledger event. The only sanctioned writer."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validators"))
import yaml
from jsonschema import Draft7Validator
from cos_lib import REPO, changed_files, compute_risk, ledger_events, load_yaml, parse_ts

DECISION = {"low": "allow", "medium": "allow_with_constraints",
            "high": "require_review", "critical": "require_human"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transition", required=True)
    ap.add_argument("--type", default="transition_committed")
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--notes", default="")
    a = ap.parse_args()

    tr_path = REPO / "transitions" / f"{a.transition}.yaml"
    if not tr_path.exists():
        sys.exit(f"refused: no transition record at {tr_path}")
    tr = yaml.safe_load(tr_path.read_text())

    ledger_p = REPO / "ledger" / "events.ndjson"
    events = ledger_events(ledger_p.read_text())
    if any(e["transition_id"] == a.transition for e in events):
        sys.exit(f"refused: an event for {a.transition} already exists "
                 f"(one event per transition)")
    last = events[-1]["event_id"] if events else None
    next_id = f"evt-{(int(last[4:]) + 1) if last else 1:04d}"

    caps = {}
    for f in sorted((REPO / "capabilities").glob("*.yaml")):
        c = yaml.safe_load(f.read_text())
        caps[c["id"]] = c
    cap = caps.get(tr["capability_id"])
    if cap is None:
        sys.exit(f"refused: capability not found: {tr['capability_id']} "
                 f"(forbidden: execute_without_capability)")
    now = datetime.now(timezone.utc)
    if not (parse_ts(cap["issued_at"]) <= now <= parse_ts(cap["expires_at"])):
        sys.exit(f"refused: capability {cap['id']} not valid now "
                 f"(forbidden: expired_capability_use)")

    subprocess.run(["git", "-C", str(REPO), "add", "-A"], check=True)
    files = changed_files(a.base, "WORKTREE")
    risk, _ = compute_risk(files, load_yaml("policy/protected_scopes.yaml"),
                           load_yaml("policy/risk_model.yaml"))

    ev = {"event_id": next_id, "prev": last,
          "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "type": a.type,
          "actor": tr["requested_by"]["actor"],
          "office": tr["requested_by"]["office"],
          "transition_id": a.transition, "capability_id": cap["id"],
          "risk_class": risk, "decision": DECISION[risk],
          "targets": tr["targets"]}
    if a.notes:
        ev["notes"] = a.notes

    schema = json.loads((REPO / "schemas" / "ledger_event.schema.json").read_text())
    errs = list(Draft7Validator(schema).iter_errors(ev))
    if errs:
        sys.exit("refused: composed event fails schema: "
                 + "; ".join(e.message for e in errs))

    with open(ledger_p, "a") as f:
        f.write(json.dumps(ev) + "\n")
    print(json.dumps(ev, indent=2))
    print(f"appended {next_id} (computed risk: {risk} -> {ev['decision']})")


if __name__ == "__main__":
    main()
