"""Shared library for COS validators.

Diff conventions:
  base  -- a git ref, or "GENESIS" (the empty tree).
  head  -- a git ref, or "WORKTREE" (the index; run `git add -A` first).
"""
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
LEDGER = "ledger/events.ndjson"


def _git(args):
    return subprocess.run(["git", "-C", str(REPO)] + args,
                          capture_output=True, text=True)


def resolve_base(base):
    return EMPTY_TREE if base == "GENESIS" else base


def changed_files(base, head="HEAD"):
    base = resolve_base(base)
    if head == "WORKTREE":
        r = _git(["diff", "--name-only", "--cached", base])
    else:
        r = _git(["diff", "--name-only", base, head])
    if r.returncode != 0:
        raise RuntimeError(f"git diff failed: {r.stderr.strip()}")
    return [l for l in r.stdout.splitlines() if l.strip()]


def read_at(ref, path):
    """File content at ref, or None if absent. WORKTREE reads the disk."""
    if ref == "WORKTREE":
        p = REPO / path
        return p.read_text() if p.exists() else None
    r = _git(["show", f"{resolve_base(ref)}:{path}"])
    return r.stdout if r.returncode == 0 else None


def glob_to_re(pattern):
    out, i = "", 0
    while i < len(pattern):
        if pattern[i:i + 3] == "**/":
            out += "(?:.*/)?"
            i += 3
        elif pattern[i:i + 2] == "**":
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$")


def match_any(path, patterns):
    return any(glob_to_re(p).match(path) for p in patterns or [])


def load_yaml(relpath):
    return yaml.safe_load((REPO / relpath).read_text())


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def ledger_events(text):
    return [json.loads(l) for l in text.splitlines() if l.strip()]


def appended_events(base, head="HEAD"):
    """(old_events, appended_events, prefix_ok) for the ledger across the diff."""
    old = read_at(base, LEDGER) or ""
    new = read_at(head, LEDGER) or ""
    prefix_ok = new.startswith(old)
    old_ev = ledger_events(old)
    new_tail = ledger_events(new[len(old):]) if prefix_ok else []
    return old_ev, new_tail, prefix_ok


def load_capabilities():
    caps = {}
    cap_dir = REPO / "capabilities"
    if cap_dir.exists():
        for f in sorted(cap_dir.glob("*.yaml")):
            data = yaml.safe_load(f.read_text())
            if isinstance(data, dict) and "id" in data:
                caps[data["id"]] = data
    return caps


RISK_ORDER = ["low", "medium", "high", "critical"]


def compute_risk(files, scopes, risk_model):
    record = risk_model.get("record_paths", [])
    substantive = [f for f in files if not match_any(f, record)]
    worst = "low"
    for f in substantive:
        if match_any(f, scopes.get("critical", [])):
            r = "critical"
        elif match_any(f, scopes.get("elevated", [])):
            r = "high"
        elif match_any(f, risk_model.get("low_risk_paths", [])):
            r = "low"
        else:
            r = "medium"
        if RISK_ORDER.index(r) > RISK_ORDER.index(worst):
            worst = r
    return worst, substantive


def report(name, failures, warnings=()):
    ok = not failures
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    for w in warnings:
        print(f"       warn: {w}")
    for f in failures:
        print(f"       - {f}")
    return 0 if ok else 1
