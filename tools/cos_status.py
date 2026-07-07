#!/usr/bin/env python3
"""Deterministic context recovery: session, capability, targets, validation."""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def sh(*args):
    return subprocess.run(["git", "-C", str(REPO)] + list(args),
                          capture_output=True, text=True).stdout.strip()


def main():
    print(f"branch: {sh('branch', '--show-current') or '(detached)'}")

    sess_p = REPO / ".cos" / "session.json"
    sess = None
    if sess_p.exists():
        try:
            sess = json.loads(sess_p.read_text())
            print(f"session: transition={sess.get('transition_id')} "
                  f"capability={sess.get('capability_id')}")
        except Exception as e:
            print(f"session: UNREADABLE ({e}) — the write gate will fail closed")
    else:
        print("session: none (start one: python3 tools/cos_new_transition.py ...)")

    targets = []
    if sess and sess.get("transition_id"):
        tr_p = REPO / "transitions" / f"{sess['transition_id']}.yaml"
        if tr_p.exists():
            in_targets = False
            for line in tr_p.read_text().splitlines():
                if re.match(r"^targets:\s*$", line):
                    in_targets = True
                    continue
                if in_targets:
                    m = re.match(r'\s*-\s*"?([^"#]+?)"?\s*$', line)
                    if m:
                        targets.append(m.group(1).strip())
                    else:
                        in_targets = False
            print(f"declared targets: {targets or '(none)'}")
        else:
            print(f"declared targets: transition record missing: {tr_p.name}")

    if sess and sess.get("capability_id"):
        for f in sorted((REPO / "capabilities").glob("*.yaml")):
            txt = f.read_text()
            if re.search(rf"^id:\s*{re.escape(sess['capability_id'])}\s*$", txt, re.M):
                m = re.search(r'expires_at:\s*"?([0-9T:+\-Z]+)"?', txt)
                if m:
                    exp = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
                    left = exp - datetime.now(timezone.utc)
                    state = f"{left}" if left.total_seconds() > 0 else "EXPIRED"
                    print(f"capability: {sess['capability_id']} expires {m.group(1)} ({state})")
                break

    dirty = [l for l in sh("status", "--porcelain").splitlines() if l.strip()]
    print(f"dirty files: {len(dirty)}")
    for l in dirty[:20]:
        path = l[3:].strip()
        drift = ""
        if targets and not any(_glob(p, path) for p in targets + [
                "ledger/events.ndjson", "transitions/**", "evidence/**"]):
            drift = "   <-- OUTSIDE declared targets"
        print(f"  {l}{drift}")

    mark_p = REPO / ".cos" / "last-validation.json"
    if mark_p.exists():
        try:
            m = json.loads(mark_p.read_text())
            print(f"last validation: {m.get('result')} at {m.get('ts')}")
        except Exception:
            print("last validation: unreadable marker")
    else:
        print("last validation: none (run: bash tools/cos_validate.sh)")

    lines = (REPO / "ledger" / "events.ndjson").read_text().splitlines()
    print("last ledger events:")
    for l in lines[-3:]:
        e = json.loads(l)
        print(f"  {e['event_id']} {e['transition_id']} {e['risk_class']} {e['decision']}")


def _glob(pattern, path):
    out, i = "", 0
    while i < len(pattern):
        if pattern[i:i + 3] == "**/":
            out += "(?:.*/)?"; i += 3
        elif pattern[i:i + 2] == "**":
            out += ".*"; i += 2
        elif pattern[i] == "*":
            out += "[^/]*"; i += 1
        elif pattern[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(pattern[i]); i += 1
    return re.match("^" + out + "$", path)


if __name__ == "__main__":
    sys.exit(main())
