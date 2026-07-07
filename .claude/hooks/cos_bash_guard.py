#!/usr/bin/env python3
"""COS bash guard: denies destructive/forbidden shell actions. Fails CLOSED.

Human-only bypass: COS_ALLOW_DANGEROUS=1 set before launching Claude Code.
Setting it inside the session is itself denied.
"""
import json
import os
import re
import subprocess
import sys


def decide(decision, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason}}))
    sys.exit(0)


RULES = [
    (r"\bCOS_ALLOW_DANGEROUS\s*=", "deny",
     "COS bash guard: the bypass variable is human-only, set outside the session."),
    (r"\bgit\s+push\b[^\n|;&]*(\s--force\b|\s--force-with-lease\b|\s-f\b)", "deny",
     "COS bash guard: force push denied (forbidden: ledger_history_rewrite)."),
    (r"\bgit\s+(filter-branch|filter-repo)\b", "deny",
     "COS bash guard: history rewrite denied (forbidden: ledger_history_rewrite)."),
    (r"\bgit\s+reset\s+--hard\b", "deny",
     "COS bash guard: hard reset discards work; ask the user."),
    (r"\bgit\s+clean\b[^\n|;&]*-[a-zA-Z]*[fdxX]", "deny",
     "COS bash guard: destructive clean; ask the user."),
    (r"\bgit\s+branch\s+(-D|-d)\s+main\b", "deny",
     "COS bash guard: deleting main is denied."),
    (r">>?\s*[^\s|;&]*ledger/events\.ndjson", "deny",
     "COS bash guard: ledger writes go through tools/cos_append_event.py."),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+[^\n|;&]*(constitution|policy|validators|schemas|capabilities|ledger|transitions|evidence|\.github|\.claude)\b", "deny",
     "COS bash guard: recursive delete of governed paths is denied."),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+(/|~|\.\.|\*)\s*$", "deny",
     "COS bash guard: broad recursive delete is denied."),
    (r"\b(cat|less|more|head|tail|grep|rg|sed|awk|type|Get-Content|gc)\b[^\n|;&]*\bsecrets/", "deny",
     "COS bash guard: secrets/** reads are denied."),
    (r"\bpip3?\s+install\b(?![^\n|;&]*(pyyaml|jsonschema))", "deny",
     "COS bash guard: dependencies are constitutional (pyyaml + jsonschema only); amend policy to add."),
    (r"\bgit\s+push\b", "ask",
     "COS bash guard: pushing is a stop-and-ask action; confirm."),
]

try:
    payload = json.load(sys.stdin)
    cmd = ((payload.get("tool_input") or {}).get("command") or "")
    cwd = payload.get("cwd") or "."

    if os.environ.get("COS_ALLOW_DANGEROUS") == "1":
        sys.exit(0)  # human-authorized session

    for pattern, decision, reason in RULES:
        if re.search(pattern, cmd):
            decide(decision, reason + f" Command: {cmd[:200]}")

    if re.search(r"\bgit\s+commit\b", cmd):
        r = subprocess.run(["git", "-C", cwd, "branch", "--show-current"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip() == "main":
            decide("deny", "COS bash guard: commit on main — work on a "
                           "transition branch (merge is the only door).")
    sys.exit(0)
except SystemExit:
    raise
except Exception as e:
    decide("deny", f"COS bash guard failed closed: {e}")
