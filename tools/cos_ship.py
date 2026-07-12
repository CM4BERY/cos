#!/usr/bin/env python3
"""COS navigator: one command from a validated transition to a verified merge.

Pipeline: preflight -> push -> PR from the transition record -> watch checks
-> merge per policy/navigation.yaml -> verify remote -> sync and clean up.
Fail-closed at every step. Headless: prints URLs, never opens a browser.

Modes:
  (default)      full run; mints a short-lived GitHub App installation token
  --dry-run      everything except push/create/comment/merge (needs gh)
  --render-only  offline: preflights that need no network + PR body preview
  --auth-smoke   mint, verify, probe, and immediately revoke one App token
"""
import argparse
import base64
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validators"))
import yaml
from cos_lib import REPO, ledger_events

LANES = {"low", "medium", "high", "critical"}
GITHUB_API = "https://api.github.com"
DEFAULT_API_VERSION = "2026-03-10"

SUMMARY_RE = re.compile(
    r"(\d+) cancelled, (\d+) failing, (\d+) successful, (\d+) skipped, and (\d+) pending")


def classify_checks(text):
    """Classify `gh pr checks` summary output: green | failing | pending | unknown.

    gh exits nonzero for BOTH failing and merely-pending checks; the ship
    pipeline needs the distinction (observed live on PR #2, 2026-07-08).
    unknown is treated as failing by callers -- action gates fail closed.
    """
    m = SUMMARY_RE.search(text)
    if not m:
        return "unknown"
    cancelled, failing, successful, skipped, pending = map(int, m.groups())
    if failing or cancelled:
        return "failing"
    if pending:
        return "pending"
    return "green" if successful else "unknown"


def sh(args, check=True, cwd=None, env=None):
    r = subprocess.run(args, capture_output=True, text=True, cwd=cwd or str(REPO),
                       env=env)
    if check and r.returncode != 0:
        die(f"command failed: {' '.join(args)}\n{r.stderr.strip() or r.stdout.strip()}")
    return r


def die(msg):
    print(f"SHIP: REFUSED: {msg}")
    sys.exit(1)


def step(msg):
    print(f"SHIP: {msg}")


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _github_json(path, token, method="GET", api_version=DEFAULT_API_VERSION):
    data = b"{}" if method == "POST" else None
    request = urllib.request.Request(
        f"{GITHUB_API}{path}", data=data, method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": api_version,
            "User-Agent": "cos-ship",
        })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("message", "")
        except Exception:
            detail = ""
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(
            f"GitHub API {method} {path} failed with HTTP {exc.code}{suffix}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API {method} {path} failed: {exc.reason}") from None
    return json.loads(raw.decode("utf-8")) if raw else None


def _publisher_config(cfg):
    publisher = cfg.get("publisher") or {}
    required = {
        "kind", "app_id", "installation_id", "slug", "bot_login", "pr_author_login",
        "repository", "private_key_path", "api_version", "repository_selection",
        "permissions",
    }
    missing = sorted(required - set(publisher))
    if missing:
        raise ValueError(f"publisher configuration missing: {', '.join(missing)}")
    if publisher["kind"] != "github_app":
        raise ValueError("publisher.kind must be github_app")
    if publisher["repository_selection"] != "selected":
        raise ValueError("publisher.repository_selection must be selected")
    if "/" not in publisher["repository"]:
        raise ValueError("publisher.repository must be OWNER/REPO")
    return publisher


def _private_key(publisher):
    key = Path(os.path.expanduser(publisher["private_key_path"])).resolve()
    if not key.is_file():
        raise ValueError(f"GitHub App private key is missing: {key}")
    if key == REPO.resolve() or REPO.resolve() in key.parents:
        raise ValueError("GitHub App private key must remain outside the repository")
    info = key.stat()
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ValueError(f"GitHub App private key is not owned by uid {os.getuid()}: {key}")
    mode = stat.S_IMODE(info.st_mode)
    if mode != 0o600:
        raise ValueError(f"GitHub App private key mode is {mode:04o}, expected 0600: {key}")
    if not shutil.which("openssl"):
        raise ValueError("openssl is required to sign the GitHub App JWT")
    return key


def jwt_claims(publisher, now):
    return {
        "iat": int(now) - 60,
        "exp": int(now) + 540,
        "iss": int(publisher["app_id"]),
    }


def _app_jwt(publisher, now=None):
    now = int(time.time() if now is None else now)
    header = _b64url(json.dumps(
        {"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(json.dumps(
        jwt_claims(publisher, now), separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode("ascii")
    result = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(_private_key(publisher))],
        input=signing_input, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"openssl could not sign the GitHub App JWT: {detail}")
    return f"{header}.{payload}.{_b64url(result.stdout)}"


def validate_installation_scope(publisher, app, installation, token_payload):
    expected_repo = publisher["repository"]
    expected_owner = expected_repo.split("/", 1)[0]
    if app.get("id") != int(publisher["app_id"]) or app.get("slug") != publisher["slug"]:
        raise ValueError("GitHub App identity does not match policy/navigation.yaml")
    account = (installation.get("account") or {}).get("login")
    if installation.get("id") != int(publisher["installation_id"]):
        raise ValueError("GitHub App installation ID does not match policy/navigation.yaml")
    if installation.get("app_id") != int(publisher["app_id"]):
        raise ValueError("installation belongs to a different GitHub App")
    if installation.get("app_slug") != publisher["slug"] or account != expected_owner:
        raise ValueError("installation App slug or owner does not match the governed repository")
    if installation.get("repository_selection") != publisher["repository_selection"]:
        raise ValueError("installation is not limited to selected repositories")

    actual_permissions = token_payload.get("permissions") or {}
    expected_permissions = publisher["permissions"]
    if actual_permissions != expected_permissions:
        raise ValueError(
            f"installation permissions differ from policy: expected {expected_permissions}, "
            f"got {actual_permissions}")
    repositories = sorted(
        r.get("full_name") for r in token_payload.get("repositories", []) if r.get("full_name"))
    total_count = token_payload.get("repository_total_count", len(repositories))
    if total_count != 1 or repositories != [expected_repo]:
        raise ValueError(
            f"installation token repository scope differs from policy: {repositories}")


def validate_resume_pr(pr, publisher, branch):
    owner, repository = publisher["repository"].split("/", 1)
    actual = {
        "author": (pr.get("author") or {}).get("login"),
        "draft": pr.get("isDraft"),
        "base": pr.get("baseRefName"),
        "head": pr.get("headRefName"),
        "head_owner": (pr.get("headRepositoryOwner") or {}).get("login"),
        "head_repository": (pr.get("headRepository") or {}).get("name"),
    }
    expected = {
        "author": publisher["pr_author_login"],
        "draft": True,
        "base": "main",
        "head": branch,
        "head_owner": owner,
        "head_repository": repository,
    }
    mismatches = [key for key in expected if actual[key] != expected[key]]
    if mismatches:
        detail = ", ".join(
            f"{key}={actual[key]!r} (expected {expected[key]!r})" for key in mismatches)
        raise ValueError(f"existing PR violates governed resume invariants: {detail}")


def mint_installation_token(cfg):
    publisher = _publisher_config(cfg)
    jwt = _app_jwt(publisher)
    version = publisher["api_version"]
    app = _github_json("/app", jwt, api_version=version)
    installation = _github_json(
        f"/app/installations/{int(publisher['installation_id'])}", jwt,
        api_version=version)
    payload = _github_json(
        f"/app/installations/{int(publisher['installation_id'])}/access_tokens",
        jwt, method="POST", api_version=version)
    token = payload.get("token")
    if not token:
        raise RuntimeError("GitHub did not return an installation token")
    try:
        repository_scope = _github_json(
            "/installation/repositories?per_page=100", token, api_version=version)
        verified_payload = dict(payload)
        verified_payload["repositories"] = repository_scope.get("repositories", [])
        verified_payload["repository_total_count"] = repository_scope.get("total_count")
        validate_installation_scope(publisher, app, installation, verified_payload)
    except Exception:
        try:
            _github_json("/installation/token", token, method="DELETE",
                         api_version=version)
        finally:
            payload["token"] = ""
        raise
    return {
        "token": token,
        "expires_at": payload.get("expires_at", "unknown"),
        "publisher": publisher,
    }


def revoke_installation_token(credentials):
    token = credentials.get("token")
    if not token:
        return
    publisher = credentials["publisher"]
    try:
        _github_json("/installation/token", token, method="DELETE",
                     api_version=publisher["api_version"])
    finally:
        credentials["token"] = ""


def authenticated_environments(token):
    gh_env = os.environ.copy()
    gh_env.update({"GH_TOKEN": token, "GH_HOST": "github.com", "GH_PROMPT_DISABLED": "1"})
    git_env = gh_env.copy()
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode("ascii")
    git_env.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {basic}",
        "GIT_CONFIG_KEY_1": "url.https://github.com/.insteadOf",
        "GIT_CONFIG_VALUE_1": "git@github.com:",
    })
    return gh_env, git_env


def with_installation_token(cfg, action):
    try:
        credentials = mint_installation_token(cfg)
    except (RuntimeError, ValueError) as exc:
        die(str(exc))
    try:
        return action(credentials)
    finally:
        try:
            revoke_installation_token(credentials)
            step("installation token revoked")
        except (RuntimeError, ValueError) as exc:
            die(f"installation token revocation failed: {exc}")


def auth_smoke(cfg):
    def probe(credentials):
        publisher = credentials["publisher"]
        if not shutil.which("gh"):
            die("GitHub CLI not found; auth smoke cannot verify the gh child process")
        repository = _github_json(
            f"/repos/{publisher['repository']}", credentials["token"],
            api_version=publisher["api_version"])
        if repository.get("full_name") != publisher["repository"]:
            die("authenticated repository identity does not match policy")
        gh_env, git_env = authenticated_environments(credentials["token"])
        gh_repo = sh(["gh", "api", f"/repos/{publisher['repository']}",
                      "--jq", ".full_name"], env=gh_env).stdout.strip()
        if gh_repo != publisher["repository"]:
            die("gh did not resolve the governed repository under the App token")
        remote_head = sh(["git", "ls-remote", "origin", "HEAD"],
                         env=git_env).stdout.strip()
        if not re.match(r"^[0-9a-f]{40}\s+HEAD$", remote_head):
            die("Git HTTPS authentication did not return the remote HEAD")
        step(f"auth smoke: {publisher['bot_login']} -> {publisher['repository']} "
             f"(selected repository; exact permissions; gh + Git HTTPS verified; expires "
             f"{credentials['expires_at']})")
        return 0
    return with_installation_token(cfg, probe)


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
    ap.add_argument("--auth-smoke", action="store_true",
                    help="mint, scope-check, probe, and revoke one installation token")
    a = ap.parse_args()

    cfg = yaml.safe_load((REPO / "policy" / "navigation.yaml").read_text())

    if a.auth_smoke:
        return auth_smoke(cfg)

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
    if mode != "review" and not cfg.get("allow_admin_merge", False):
        die(f"lane {lane!r} requests merge mode {mode!r}, but policy forbids "
            "the publisher from admin/bypass merging")

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
        step(f"planned: gh pr create --draft --title <title> --body-file <tmp>")
        step(f"planned: gh pr checks {branch} --watch --fail-fast")
        if mode == "flag":
            step(f"planned: gh pr comment {branch} --body 'BYPASS ({lane}): {a.bypass}'")
        if mode != "review":
            step(f"planned: gh pr merge {branch} --squash --admin --subject <title>"
                 + (" --delete-branch" if cfg.get("delete_branch_after_merge") else ""))
        return 0

    def ship(credentials):
        # P5: gh presence + short-lived, scope-checked App identity
        if not shutil.which("gh"):
            die("GitHub CLI not found. Install gh without authenticating it as a human; "
                "cos_ship supplies a short-lived App token per process.")
        publisher = credentials["publisher"]
        repository = publisher["repository"]
        gh_env, git_env = authenticated_environments(credentials["token"])
        step(f"identity: {publisher['bot_login']} (App and installation scope pinned OK; "
             f"token expires {credentials['expires_at']})")

        # P6: idempotency -- resume, never duplicate; respect human closures
        r = sh(["gh", "pr", "list", "--repo", repository, "--head", branch,
                "--state", "all", "--json",
                "number,state,url,author,isDraft,baseRefName,headRefName,"
                "headRepository,headRepositoryOwner"], env=gh_env)
        try:
            prs = json.loads(r.stdout) if r.stdout.strip() else []
        except json.JSONDecodeError:
            die("gh returned invalid JSON while checking for an existing PR")
        if len(prs) > 1:
            die(f"multiple PRs exist for head {branch!r}; refusing ambiguous resume")
        pr = prs[0] if prs else None
        if pr and pr["state"] == "MERGED":
            die(f"PR #{pr['number']} for {branch} is already merged: {pr['url']}")
        if pr and pr["state"] == "CLOSED":
            die(f"PR #{pr['number']} was closed by a human: {pr['url']} -- reopen it "
                f"deliberately or delete the branch; the tool will not override that decision.")
        if pr:
            try:
                validate_resume_pr(pr, publisher, branch)
            except ValueError as exc:
                die(str(exc))

        if a.dry_run:
            step(f"dry-run: would push {branch}, "
                 + (f"resume PR #{pr['number']}" if pr else "create a draft PR")
                 + f", watch checks, then merge mode={mode}. Stopping here.")
            return 0

        # P7: push. A process-local URL rewrite keeps the stored origin SSH URL
        # untouched while the App token authenticates HTTPS Git.
        sh(["git", "push", "-u", "origin", branch], env=git_env)
        step(f"pushed {branch} as {publisher['bot_login']}")

        # P8: create or resume
        if not pr:
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
                f.write(body)
                body_file = f.name
            try:
                command = ["gh", "pr", "create", "--repo", repository,
                           "--head", branch, "--base", "main", "--title", title,
                           "--body-file", body_file]
                if cfg.get("draft_pull_requests"):
                    command.append("--draft")
                sh(command, env=gh_env)
            finally:
                Path(body_file).unlink(missing_ok=True)
            step("draft PR created")
        else:
            step(f"resuming existing PR #{pr['number']}")
        url = sh(["gh", "pr", "view", branch, "--repo", repository,
                  "--json", "url", "--jq", ".url"], env=gh_env).stdout.strip()
        step(f"PR: {url}")

        # P9: checks
        step("watching checks (cos-validate)...")
        r = sh(["gh", "pr", "checks", branch, "--repo", repository,
                "--watch", "--fail-fast"], check=False, env=gh_env)
        if r.returncode != 0:
            # nonzero means failing OR pending; classify before concluding anything
            for attempt in range(8):
                s = sh(["gh", "pr", "checks", branch, "--repo", repository],
                       check=False, env=gh_env)
                state = classify_checks(s.stdout + s.stderr)
                if state == "green":
                    break
                if state in ("failing", "unknown"):
                    die(f"checks {state} on the PR -- nothing merged.\n{s.stdout}\nSee {url}")
                step(f"checks pending (none failing) -- waiting 15s ({attempt + 1}/8)...")
                time.sleep(15)
            else:
                die(f"checks still pending after 2 minutes -- rerun cos_ship to resume.\nSee {url}")
        step("checks: green")

        # P10: merge per policy. Initial App policy maps every lane to review,
        # so this returns before any merge or ruleset bypass.
        if mode == "review":
            step(f"stopping before merge (review lane). Human reviewer completes at: {url}")
            return 0
        if mode == "flag":
            sh(["gh", "pr", "comment", branch, "--repo", repository, "--body",
                f"BYPASS ({lane}): {a.bypass} -- logged per policy/navigation.yaml"],
               env=gh_env)
            step("bypass reason posted to PR")
        merge_cmd = ["gh", "pr", "merge", branch, "--repo", repository,
                     "--squash", "--admin", "--subject", title]
        if cfg.get("delete_branch_after_merge"):
            merge_cmd.append("--delete-branch")
        sh(merge_cmd, env=gh_env)
        step("merged (squash, admin bypass)")

        # P11: verify the remote actually changed
        sh(["git", "fetch", "origin", "main"], env=git_env)
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
        sh(["git", "pull", "--ff-only", "origin", "main"], env=git_env)
        sh(["git", "branch", "-D", branch], check=False)
        step(f"main synced; local {branch} removed. Done: {url}")
        return 0

    return with_installation_token(cfg, ship)


if __name__ == "__main__":
    sys.exit(main())
