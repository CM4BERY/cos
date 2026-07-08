#!/usr/bin/env python3
"""COS navigator: one command from a validated transition to a verified merge.

Pipeline: preflight -> push -> PR from the transition record -> watch checks
-> merge per policy/navigation.yaml -> verify remote -> sync and clean up.
Fail-closed at every step. Headless: prints URLs, never opens a browser.

Modes:
  (default)      full run; needs gh installed and authenticated
  --dry-run      everything except push/create/comment/merge (needs gh)
  --render-only  offline: preflights that need no network + PR body preview
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validators"))
import yaml
from cos_lib import REPO, ledger_events

LANES = {"low", "medium", "high", "critical"}


def sh(args, check=True, cwd=None):
    r = subprocess.run(args, capture_output=True, text=True, cwd=cwd or str(REPO))
    if check and r.returncode != 0:
        die(f"command failed: {' '.join(args)}\n{r.stderr.strip() or r.stdout.strip()}")
    return r


def die(msg):
    print(f"SHIP: REFUSED: {msg}")
    sys.exit(1)


def step(msg):
    print(f"SHIP: {msg}")


def render_body(tr, ev, result_line):
    intent = " ".join(str(tr["intent"]).split())
    return f"""# Transition

One PR = one transition. CI recomputes risk from the diff.

- Transition record: transitions/{tr['id']}.yaml
- Ledger event appended: {ev['event_id']} (exactly one)
- Capability: {ev['capability_id']}
- Computed risk class: {ev['risk_class']} -> {ev['decision']}
- Rollback plan: {' '.join(str(tr.get('rollback_plan', '')).split())}

## Intent

{intent}

Local validator RESULT: {result_line}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transition", default=None)
    ap.add_argument("--bypass", default=None, metavar="REASON",
                    help="one-line reason; demanded for flag lanes (high/critical)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    a = ap.parse_args()

    cfg = yaml.safe_load((REPO / "policy" / "navigation.yaml").read_text())

    # P1: repo, branch, cleanliness
    branch = sh(["git", "branch", "--show-current"]).stdout.strip()
    if not re.match(r"^tr-\d{4}", branch):
        die(f"current branch {branch!r} is not a transition branch (tr-NNNN). "
            f"Ship runs from the transition's own branch.")
    tr_id = a.transition or branch
    if sh(["git", "status", "--porcelain"]).stdout.strip():
        die("worktree is dirty. Commit the transition first (validate, then commit).")

    # P2: record + exactly one ledger event
    tr_path = REPO / "transitions" / f"{tr_id}.yaml"
    if not tr_path.exists():
        die(f"no transition record: {tr_path.name}")
    tr = yaml.safe_load(tr_path.read_text())
    events = [e for e in ledger_events((REPO / "ledger" / "events.ndjson").read_text())
              if e["transition_id"] == tr_id]
    if len(events) != 1:
        die(f"expected exactly one ledger event for {tr_id}, found {len(events)}")
    ev = events[0]

    # P3: lane -> merge mode (checked early so --render-only exercises it)
    lane = ev["risk_class"]
    mode = (cfg.get("bypass") or {}).get(lane)
    if mode not in ("auto", "flag", "review"):
        die(f"policy/navigation.yaml has no bypass mode for lane {lane!r}")
    if mode == "flag" and not a.bypass:
        die(f"lane {lane!r} requires --bypass \"one-line reason\" "
            f"(posted to the PR, counted by governance_debt).")
    if mode == "review":
        step(f"lane {lane!r} is review-mode: the tool will open the PR and stop "
             f"before merging; a human reviewer completes it.")

    # P4: revalidate committed state (self-contained; no marker dependency)
    base = "origin/main" if sh(["git", "rev-parse", "--verify", "-q", "origin/main"],
                               check=False).returncode == 0 else "HEAD~1"
    r = sh([sys.executable, str(REPO / "validators" / "run_all.py"),
            "--base", base, "--head", "HEAD"], check=False)
    result_line = next((l for l in r.stdout.splitlines() if l.startswith("RESULT:")),
                       "RESULT: (missing)")
    if r.returncode != 0:
        die(f"validators fail on the committed transition ({base}..HEAD):\n{r.stdout}")
    step(f"validators: {result_line}")

    title = f"{tr_id}: {' '.join(str(tr['intent']).split())[:80]} [{ev['event_id']}]"
    body = render_body(tr, ev, result_line)

    if a.render_only:
        step("render-only: preflights above passed; PR body follows")
        print("-" * 60)
        print(f"TITLE: {title}")
        print(body)
        print("-" * 60)
        step(f"planned: git push -u origin {branch}")
        step(f"planned: gh pr create --title <title> --body-file <tmp>")
        step(f"planned: gh pr checks {branch} --watch --fail-fast")
        if mode == "flag":
            step(f"planned: gh pr comment {branch} --body 'BYPASS ({lane}): {a.bypass}'")
        if mode != "review":
            step(f"planned: gh pr merge {branch} --squash --admin --subject <title>"
                 + (" --delete-branch" if cfg.get("delete_branch_after_merge") else ""))
        return 0

    # P5: gh presence + pinned identity
    if not shutil.which("gh"):
        die("GitHub CLI not found. Install: winget install GitHub.cli "
            "(new terminal after), then: gh auth login")
    r = sh(["gh", "auth", "status"], check=False)
    who = re.search(r"account\s+(\S+)", r.stdout + r.stderr)
    if r.returncode != 0 or not who:
        die("gh is not authenticated. Run: gh auth login")
    if who.group(1) != cfg["expected_account"]:
        die(f"gh is authenticated as {who.group(1)!r}; policy pins "
            f"{cfg['expected_account']!r}. Run: gh auth login")
    step(f"identity: {who.group(1)} (pinned OK)")

    # P6: idempotency -- resume, never duplicate; respect human closures
    r = sh(["gh", "pr", "list", "--head", branch, "--state", "all",
            "--json", "number,state,url"], check=False)
    prs = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else []
    pr = prs[0] if prs else None
    if pr and pr["state"] == "MERGED":
        die(f"PR #{pr['number']} for {branch} is already merged: {pr['url']}")
    if pr and pr["state"] == "CLOSED":
        die(f"PR #{pr['number']} was closed by a human: {pr['url']} -- reopen it "
            f"deliberately or delete the branch; the tool will not override that decision.")

    if a.dry_run:
        step(f"dry-run: would push {branch}, "
             + (f"resume PR #{pr['number']}" if pr else "create the PR")
             + f", watch checks, then merge mode={mode}. Stopping here.")
        return 0

    # P7: push
    sh(["git", "push", "-u", "origin", branch])
    step(f"pushed {branch}")

    # P8: create or resume
    if not pr:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(body)
            body_file = f.name
        sh(["gh", "pr", "create", "--head", branch,
            "--title", title, "--body-file", body_file])
        step("PR created")
    else:
        step(f"resuming existing PR #{pr['number']}")
    url = sh(["gh", "pr", "view", branch, "--json", "url",
              "--jq", ".url"]).stdout.strip()
    step(f"PR: {url}")

    # P9: checks
    step("watching checks (cos-validate)...")
    r = sh(["gh", "pr", "checks", branch, "--watch", "--fail-fast"], check=False)
    if r.returncode != 0:
        die(f"checks failed on the PR -- nothing merged.\n{r.stdout}\nSee {url}")
    step("checks: green")

    # P10: merge per policy
    if mode == "review":
        step(f"stopping before merge (review lane). Reviewer completes at: {url}")
        return 0
    if mode == "flag":
        sh(["gh", "pr", "comment", branch, "--body",
            f"BYPASS ({lane}): {a.bypass} -- logged per policy/navigation.yaml"])
        step("bypass reason posted to PR")
    merge_cmd = ["gh", "pr", "merge", branch, "--squash", "--admin",
                 "--subject", title]
    if cfg.get("delete_branch_after_merge"):
        merge_cmd.append("--delete-branch")
    sh(merge_cmd)
    step("merged (squash, admin bypass)")

    # P11: verify the remote actually changed
    sh(["git", "fetch", "origin", "main"])
    remote_ledger = sh(["git", "show", "origin/main:ledger/events.ndjson"]).stdout
    last = ledger_events(remote_ledger)[-1]
    if last["event_id"] != ev["event_id"]:
        die(f"post-merge verification FAILED: origin/main newest event is "
            f"{last['event_id']}, expected {ev['event_id']}. Investigate before continuing.")
    subject = sh(["git", "log", "origin/main", "-1", "--format=%s"]).stdout.strip()
    if tr_id not in subject:
        die(f"post-merge verification FAILED: merge commit subject {subject!r} "
            f"does not carry {tr_id}.")
    step(f"verified: origin/main carries {ev['event_id']} ({subject})")

    # P12: housekeeping
    sh(["git", "checkout", "main"])
    sh(["git", "pull", "--ff-only", "origin", "main"])
    sh(["git", "branch", "-D", branch], check=False)
    step(f"main synced; local {branch} removed. Done: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
