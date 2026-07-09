#!/usr/bin/env python3
"""Deterministic governance-debt report (automation-layer section 7, Stage 3).

Reads ONLY repo-local state — no network, no gh:
  - git history of main (ref resolution: origin/main, then main, then HEAD;
    the report names the ref it used)
  - ledger/events.ndjson
  - capabilities/*.yaml (validity windows)
  - policy/navigation.yaml AS RECORDED AT EACH MERGE COMMIT (git show), so a
    later policy flip cannot reclassify history
  - evidence file existence in the current worktree
  - .cos/waivers.log (optional, gitignored, local)

Sections and polarity:
  bypass-merged PRs by lane        informational — auto lanes merge with
                                   --admin by design (navigation-layer §4)
  pre-navigation PR merges         informational — merged before
                                   policy/navigation.yaml existed
  direct-to-main commits           informational — bootstrap/pre-gateway
  PR merges with no ledger link    HARD 0 — one PR = one transition = one
                                   event (validators/validate_ledger.py)
  review-mode merges lacking a     HARD 0 — drift per navigation-layer §7
    recorded reason                item 4. The reason itself is a GitHub PR
                                   review/merge comment, which is not
                                   repo-local; the deterministic local proxy
                                   is an existing evidence/reviews/ file
                                   recorded on the event (evidence or
                                   targets — the append tool folds evidence
                                   paths into targets) or in the transition
                                   record's evidence block.
  expired-capability events        HARD 0 — event timestamped outside its
                                   capability's [issued_at, expires_at]
                                   window, or referencing a missing
                                   capability file
  logged waivers                   informational — fresh-waiver halts are the
                                   stop hook's locus (.claude/hooks/
                                   cos_stop_evidence.py); surfaced for audit

Exit codes: 0 = no hard-threshold breach; 1 = at least one breach;
2 = unreadable repo state. Output is byte-deterministic for a given repo
state: no clock reads, stable iteration order.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # policy: python3 + pyyaml + jsonschema only
    print("governance_debt: pyyaml is required", file=sys.stderr)
    sys.exit(2)

HARD_MAX_UNLINKED_PR_MERGES = 0
HARD_MAX_REVIEW_MERGES_MISSING_REASON = 0
HARD_MAX_EXPIRED_CAPABILITY_EVENTS = 0

PR_MERGE_RE = re.compile(r"\(#\d+\)$")
EVT_TAG_RE = re.compile(r"\[evt-(\d{4})\]")
LANES = ("low", "medium", "high", "critical")


def die(msg):
    print(f"governance_debt: {msg}", file=sys.stderr)
    sys.exit(2)


def git(repo, *args):
    """Run git in repo; return (rc, stdout)."""
    proc = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


def parse_ts(raw, context):
    if not isinstance(raw, str) or not raw:
        die(f"unparsable timestamp in {context}: {raw!r}")
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        die(f"unparsable timestamp in {context}: {raw!r}")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def resolve_ref(repo, explicit):
    candidates = [explicit] if explicit else ["origin/main", "main", "HEAD"]
    for ref in candidates:
        rc, _ = git(repo, "rev-parse", "--verify", "--quiet", ref)
        if rc == 0:
            return ref
    die(f"no usable ref among {candidates}")


def load_ledger(repo):
    path = repo / "ledger" / "events.ndjson"
    if not path.is_file():
        die(f"missing {path}")
    events = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            die(f"ledger line {n} is not valid JSON")
    return events


def load_capabilities(repo):
    caps = {}
    cap_dir = repo / "capabilities"
    for path in sorted(cap_dir.glob("*.yaml")) if cap_dir.is_dir() else []:
        try:
            doc = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            die(f"unparsable capability {path.name}")
        if isinstance(doc, dict) and doc.get("id"):
            caps[doc["id"]] = {
                "issued_at": parse_ts(doc.get("issued_at"), path.name),
                "expires_at": parse_ts(doc.get("expires_at"), path.name),
            }
    return caps


def has_recorded_reason(repo, event):
    """Deterministic local proxy for the review-mode one-line reason
    (navigation-layer §7 item 4). The GitHub PR comment is not repo-local,
    so recorded review evidence stands in: an existing evidence/reviews/
    file listed on the event (evidence or targets — the append tool folds
    evidence paths into targets) or in the transition record's evidence
    block."""
    listed = list(event.get("evidence") or []) + list(event.get("targets") or [])
    tr_path = repo / "transitions" / f"{event.get('transition_id')}.yaml"
    if tr_path.is_file():
        try:
            doc = yaml.safe_load(tr_path.read_text())
            block = (doc or {}).get("evidence")
            if isinstance(block, dict):
                for paths in block.values():
                    if isinstance(paths, list):
                        listed.extend(paths)
            elif isinstance(block, list):
                listed.extend(block)
        except yaml.YAMLError:
            pass  # an unparsable record cannot supply a reason
    return any(isinstance(p, str) and p.startswith("evidence/reviews/")
               and (repo / p).is_file() for p in listed)


def lane_mode_at(repo, sha, lane):
    """Bypass mode for lane per policy/navigation.yaml as committed at sha.

    Returns None when the policy file did not exist at that commit
    (pre-navigation history). Unknown lane or unparsable policy fails
    closed to 'review' — the strictest mode.
    """
    rc, text = git(repo, "show", f"{sha}:policy/navigation.yaml")
    if rc != 0:
        return None
    try:
        doc = yaml.safe_load(text)
        mode = doc["bypass"][lane]
    except Exception:
        return "review"
    return mode if mode in ("auto", "flag", "review") else "review"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", help="repo root (default: discovered via git)")
    ap.add_argument("--ref", help="history ref (default: origin/main, main, HEAD)")
    args = ap.parse_args()

    if args.repo:
        repo = Path(args.repo)
        if not (repo / ".git").exists():
            die(f"{repo} is not a git repository")
    else:
        rc, top = git(Path.cwd(), "rev-parse", "--show-toplevel")
        if rc != 0:
            die("not inside a git repository (or pass --repo)")
        repo = Path(top.strip())

    ref = resolve_ref(repo, args.ref)
    events = load_ledger(repo)
    events_by_id = {e.get("event_id"): e for e in events}
    caps = load_capabilities(repo)

    rc, log = git(repo, "log", "--format=%H%x1f%s", ref)
    if rc != 0:
        die(f"git log {ref} failed")
    commits = [line.split("\x1f", 1) for line in log.splitlines() if "\x1f" in line]

    bypass_by_lane = {lane: 0 for lane in LANES}
    flag_merges = []          # (sha7, subject) — bypass with typed reason on GitHub
    pre_navigation = []       # (sha7, subject)
    direct_pushes = []        # (sha7, subject)
    unlinked_merges = []      # breach: (sha7, why)
    review_merges = []        # (sha7, evt, has_reason)

    for sha, subject in commits:
        if not PR_MERGE_RE.search(subject):
            direct_pushes.append((sha[:7], subject))
            continue
        m = EVT_TAG_RE.search(subject)
        event = events_by_id.get(f"evt-{m.group(1)}") if m else None
        if event is None:
            why = "no [evt-NNNN] tag" if not m else f"evt-{m.group(1)} not in ledger"
            unlinked_merges.append((sha[:7], why))
            continue
        lane = event.get("risk_class")
        mode = lane_mode_at(repo, sha, lane)
        if mode is None:
            pre_navigation.append((sha[:7], subject))
        elif mode == "auto":
            bypass_by_lane[lane] = bypass_by_lane.get(lane, 0) + 1
        elif mode == "flag":
            bypass_by_lane[lane] = bypass_by_lane.get(lane, 0) + 1
            flag_merges.append((sha[:7], subject))
        else:  # review
            review_merges.append(
                (sha[:7], event["event_id"], has_recorded_reason(repo, event)))

    expired_events = []  # breach: (event_id, why)
    for event in events:
        cap_id = event.get("capability_id")
        cap = caps.get(cap_id)
        if cap is None:
            expired_events.append(
                (event.get("event_id"), f"references missing capability {cap_id}"))
            continue
        ts = parse_ts(event.get("timestamp"), event.get("event_id", "event"))
        if not (cap["issued_at"] <= ts <= cap["expires_at"]):
            expired_events.append(
                (event.get("event_id"),
                 f"timestamp {event.get('timestamp')} outside {cap_id} window"))

    waivers = []
    waiver_path = repo / ".cos" / "waivers.log"
    if waiver_path.is_file():
        for line in waiver_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                waivers.append((doc.get("ts", "?"), doc.get("type", "?")))
            except json.JSONDecodeError:
                waivers.append(("?", "unparsable line"))

    missing_reason = [(sha, evt) for sha, evt, ok in review_merges if not ok]

    print(f"governance debt report — ref {ref}, {len(commits)} commits, "
          f"{len(events)} ledger events")
    print()
    print("bypass-merged PRs by lane (informational; auto/flag lanes per "
          "policy at each merge commit):")
    for lane in LANES:
        print(f"  {lane:<8} {bypass_by_lane[lane]}")
    for sha, subject in flag_merges:
        print(f"  flag-mode merge {sha}: reason lives on the PR (not repo-local)")
    print(f"pre-navigation PR merges (informational): {len(pre_navigation)}")
    print(f"direct-to-main commits (informational, bootstrap/pre-gateway): "
          f"{len(direct_pushes)}")
    print()
    print(f"PR merges with no ledger link (hard max "
          f"{HARD_MAX_UNLINKED_PR_MERGES}): {len(unlinked_merges)}")
    for sha, why in unlinked_merges:
        print(f"  BREACH {sha}: {why}")
    print(f"review-mode merges: {len(review_merges)}; lacking recorded reason "
          f"(hard max {HARD_MAX_REVIEW_MERGES_MISSING_REASON}): "
          f"{len(missing_reason)}")
    for sha, evt in missing_reason:
        print(f"  BREACH {sha} ({evt}): no existing evidence/reviews/ file in "
              f"event evidence (drift per navigation-layer §7 item 4)")
    print(f"expired-capability events (hard max "
          f"{HARD_MAX_EXPIRED_CAPABILITY_EVENTS}): {len(expired_events)}")
    for evt, why in expired_events:
        print(f"  BREACH {evt}: {why}")
    print()
    print(f"logged waivers (informational; halt locus is the stop hook): "
          f"{len(waivers)}")
    for ts, wtype in waivers:
        print(f"  {ts} {wtype}")

    breaches = (
        max(0, len(unlinked_merges) - HARD_MAX_UNLINKED_PR_MERGES)
        + max(0, len(missing_reason) - HARD_MAX_REVIEW_MERGES_MISSING_REASON)
        + max(0, len(expired_events) - HARD_MAX_EXPIRED_CAPABILITY_EVENTS)
    )
    print()
    if breaches:
        print(f"GOVERNANCE DEBT: BREACH ({breaches})")
        return 1
    print("GOVERNANCE DEBT: OK (0 breaches)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
