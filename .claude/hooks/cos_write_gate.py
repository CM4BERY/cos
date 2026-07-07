#!/usr/bin/env python3
"""COS write gate: execution-time enforcement for Edit/Write tools.

Order: ledger deny -> record allow -> secrets deny -> constitution ask ->
session required -> declared targets -> capability scope/expiry. Fails CLOSED.
Stdlib only (no pyyaml dependency in the hook environment).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def decide(decision, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason}}))
    sys.exit(0)


def glob_re(p):
    out, i = "", 0
    while i < len(p):
        if p[i:i + 3] == "**/":
            out += "(?:.*/)?"; i += 3
        elif p[i:i + 2] == "**":
            out += ".*"; i += 2
        elif p[i] == "*":
            out += "[^/]*"; i += 1
        elif p[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(p[i]); i += 1
    return re.compile("^" + out + "$")


def match(path, pats):
    return any(glob_re(p).match(path) for p in (pats or []))


try:
    payload = json.load(sys.stdin)
    ti = payload.get("tool_input") or {}
    raw = ti.get("file_path") or ti.get("notebook_path") or ""
    repo = Path(payload.get("cwd") or ".").resolve()
    if not raw:
        decide("deny", "COS write gate: no file path in tool input.")
    target = Path(raw)
    if not target.is_absolute():
        target = repo / raw
    target = target.resolve()
    try:
        rel = target.relative_to(repo).as_posix()
    except ValueError:
        decide("allow", "outside repository — not COS-governed state")

    if rel == "ledger/events.ndjson":
        decide("deny", "COS write gate: ledger/events.ndjson is append-only via "
                       "tools/cos_append_event.py — never Edit/Write it directly.")
    if match(rel, ["transitions/**", "evidence/**", ".cos/**"]):
        decide("allow", "record path")
    if match(rel, ["secrets/**"]):
        decide("deny", "COS write gate: secrets/** is a critical scope with no "
                       "agent write path.")
    if match(rel, ["constitution/**"]):
        decide("ask", "COS write gate: constitution/** is lane 4 (human "
                      "ratification). Confirm this edit; the merge-time "
                      "protocol still applies.")

    sess_p = repo / ".cos" / "session.json"
    if not sess_p.exists():
        decide("deny", f"COS write gate: no active transition. Run "
                       f"tools/cos_new_transition.py (or /cos-transition) "
                       f"before editing {rel}.")
    sess = json.loads(sess_p.read_text())

    tr_id = sess.get("transition_id", "")
    tr_p = repo / "transitions" / f"{tr_id}.yaml"
    targets = []
    if tr_p.exists():
        in_targets = False
        for line in tr_p.read_text().splitlines():
            if re.match(r"^targets:\s*$", line):
                in_targets = True
                continue
            if in_targets:
                m = re.match(r'\s+-\s*"?([^"#]+?)"?\s*$', line)
                if m:
                    targets.append(m.group(1).strip())
                else:
                    in_targets = False
    if targets and not match(rel, targets):
        decide("deny", f"COS write gate: {rel} is outside declared targets of "
                       f"{tr_id}. Update the transition record's targets first "
                       f"(auditable), then retry.")

    cap_id, cap_txt = sess.get("capability_id", ""), None
    for f in sorted((repo / "capabilities").glob("*.yaml")):
        txt = f.read_text()
        if re.search(rf"^id:\s*{re.escape(cap_id)}\s*$", txt, re.M):
            cap_txt = txt
            break
    if cap_txt is None:
        decide("deny", f"COS write gate: session capability {cap_id!r} not "
                       f"found in capabilities/.")
    m = re.search(r'expires_at:\s*"?([0-9T:+\-Z]+)"?', cap_txt)
    if m and datetime.fromisoformat(m.group(1).replace("Z", "+00:00")) \
            < datetime.now(timezone.utc):
        decide("deny", f"COS write gate: capability {cap_id} is expired "
                       f"(forbidden: expired_capability_use). Ask the owner.")
    allowed, denied, key = [], [], None
    for line in cap_txt.splitlines():
        if re.match(r"^allowed_targets:\s*$", line):
            key = allowed
            continue
        if re.match(r"^denied_targets:\s*$", line):
            key = denied
            continue
        if re.match(r"^\S", line):
            key = None
        mm = re.match(r'\s+-\s*"?([^"#]+?)"?\s*$', line)
        if key is not None and mm:
            key.append(mm.group(1).strip())
    if allowed and not match(rel, allowed):
        decide("deny", f"COS write gate: {rel} is outside capability "
                       f"{cap_id}'s allowed_targets.")
    if match(rel, denied):
        decide("deny", f"COS write gate: {rel} is in capability {cap_id}'s "
                       f"denied_targets.")
    decide("allow", "within declared targets under a live capability")
except SystemExit:
    raise
except Exception as e:
    decide("deny", f"COS write gate failed closed: {e}")
