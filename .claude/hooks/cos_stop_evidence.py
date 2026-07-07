#!/usr/bin/env python3
"""COS stop gate: no ending the turn on unvalidated governed changes.

Blocks once (exit 2). An identical second stop is allowed but logged to
.cos/waivers.log — the bypass exists and is never silent. Fails OPEN:
gates on actions fail closed, gates on stopping fail open.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        print(f"COS stop gate warning (unparseable input, failing open): {e}",
              file=sys.stderr)
        sys.exit(0)
    repo = Path(payload.get("cwd") or ".").resolve()
    if not (repo / "ledger" / "events.ndjson").exists():
        sys.exit(0)  # not a COS repo

    def run(*args):
        return subprocess.run(["git", "-C", str(repo)] + list(args),
                              capture_output=True, text=True).stdout

    status = run("status", "--porcelain")
    if not status.strip():
        sys.exit(0)  # clean tree, nothing to prove

    digest = hashlib.sha256(
        (status + run("diff", "HEAD")).encode()).hexdigest()

    mark_p = repo / ".cos" / "last-validation.json"
    if mark_p.exists():
        try:
            mark = json.loads(mark_p.read_text())
            if mark.get("state_digest") == digest and mark.get("result") == "PASS":
                sys.exit(0)  # validated in exactly this state
        except Exception:
            pass

    warned_p = repo / ".cos" / "stop-warned"
    if warned_p.exists() and warned_p.read_text().strip() == digest:
        with open(repo / ".cos" / "waivers.log", "a") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": "stop_without_validation",
                "state_digest": digest}) + "\n")
        print("COS stop gate: waiver recorded in .cos/waivers.log — surface "
              "this to the user.", file=sys.stderr)
        sys.exit(0)

    (repo / ".cos").mkdir(exist_ok=True)
    warned_p.write_text(digest)
    print("COS stop gate: uncommitted governed changes without fresh "
          "validation. Run: bash tools/cos_validate.sh — then report its "
          "RESULT line verbatim, or state explicitly that validation was "
          "not run and why.", file=sys.stderr)
    sys.exit(2)
except SystemExit:
    raise
except Exception as e:
    print(f"COS stop gate warning (failing open): {e}", file=sys.stderr)
    sys.exit(0)
