<!-- cos:locus-exempt-file -->
> Owner-resolved design for the navigation layer (decisions in section 7).
> Narrative spec: binding rules live in policy/navigation.yaml and the hooks.

# COS Navigation Layer — Design for Reaction

Working name: `cos-ship`. Purpose: after tonight, no COS change should ever again require a human to navigate GitHub's web UI on the happy path. Everything between "transition validated locally" and "squash commit on main, verified" becomes one deterministic command; everything that can't be a command becomes an explicit, named exception with a URL.

Design rule carried over from the automation layer: automate the **correctness** of deliberate acts, not their occurrence. You still decide to ship; nothing inside the shipping is left to hands.

## 1. The failure catalog this design answers

Every element below maps to something that actually happened tonight, which makes this the rare design doc with an empirical basis:

| Observed failure | Design answer |
|---|---|
| git commands run in the wrong folder (`git init` in `C:\cos`) | The tool locates the repo itself and refuses to run anywhere else |
| Three identities (CMABERY / CM4BERY-org / clol123) confused across sessions | Identity pinning: every run starts with `gh auth status`, asserts the account is `CMABERY`, and refuses otherwise |
| Web upload silently dropped `.github/**` and history — twice | The web UI is never used for content, period; `git push` is the only writer |
| Review requirement structurally unsatisfiable (solo human, org CODEOWNERS) | Merge policy encoded as configuration, not discovered at merge time (§4) |
| Two-step merge confirm missed; "merged" believed but not true | The tool completes the merge atomically and then **verifies** the remote: main's new SHA must contain the transition's event before it reports success |
| Closed-vs-open-vs-merged PR state guessed from memory | State is always read (`gh pr view --json state,mergedAt`), never inferred |
| PR body hand-typed, drifting from the record | PR body generated from `transitions/tr-NNNN.yaml` — single source |

## 2. Architecture: three layers

**L1 — `gh`, the GitHub CLI (backbone).** One-time setup: `winget install GitHub.cli`, then `gh auth login` in a terminal, browser handshake as CMABERY, done forever. From then on the tool speaks to GitHub exclusively through `gh` — deterministic, scriptable, account-pinned, no sessions, no pixels. This is the entire reason tonight can't recur.

**L2 — `tools/cos_ship.py`, the navigator.** One command: `python3 tools/cos_ship.py` (optionally `--transition tr-NNNN`). Pipeline, stop-on-first-failure, every step printing its evidence:

1. Preflight: correct repo; `gh` authenticated as the pinned account; working tree clean; current branch is a transition branch; the transition record exists; exactly one ledger event appended for it; `tools/cos_validate.sh` marker fresh and PASS.
2. Idempotency: if a PR already exists for this branch, resume it (re-attach to checks/merge) rather than creating a duplicate.
3. `git push -u origin <branch>` — the only push verb the tool owns.
4. `gh pr create` — title from the transition id + intent; body rendered from the record, matching `.github/pull_request_template.md`.
5. `gh pr checks --watch` — blocks until `cos-validate / validate` resolves; failure stops the world with the log excerpt.
6. Merge step per policy (§4).
7. Post-verify: fetch; assert `origin/main` now contains the event id (grep the ledger at `origin/main`); assert the squash commit title carries `tr-NNNN … [evt-NNNN]`.
8. Housekeeping: sync local main, delete the merged branch locally and remotely (config-controlled).

**L3 — the escape hatch, named not hidden.** Some surfaces are web-only by GitHub's design: org settings, ruleset edits, capability-adjacent account administration. When the tool needs one of these changed, it does not attempt automation — it prints the exact settings URL and the exact change required, then exits nonzero. (Optionally, with the Claude in Chrome extension connected, those become drivable too — deferred, per scope decision.)

## 3. What deliberately stays human

Capability issuance (constitutionally the owner's act), `gh auth login` (credentials are yours), org/ruleset administration (L3 names them), and the decision to run `cos_ship` at all. The navigator removes navigation, not judgment.

## 4. Merge policy: solo bypass, logged (as chosen)

Encoded in a new governed file, `policy/navigation.yaml` (elevated scope, like all policy):

```yaml
expected_account: CMABERY
merge_method: squash
delete_branch_after_merge: true
bypass:
  low: auto        # gh pr merge --squash --admin, no ceremony
  medium: auto
  high: flag       # requires --bypass "one-line reason"; reason posted as PR comment
  critical: flag   # same, and the tool restates the lane's requirements before accepting
```

Where the bypass evidence lives — a deliberate decision worth your reaction: **the bypass is logged where it happens.** GitHub's PR timeline and audit surface record every rule-bypassing merge; for high/critical the tool additionally posts the typed reason as a PR comment via `gh`. COS-side, `governance_debt.py` (Stage 3) gains a collector that counts bypass-merged PRs by lane and flags drift (e.g., a critical bypassed without a reason comment). No post-merge commits are made to store bypass notes — that would spawn a recursive transition for every merge, and the information already has a durable, queryable home.

Upgrade path, one config value away: when/if `clol123` joins the org as a real reviewer, `high`/`critical` flip from `flag` to `review`, CODEOWNERS gets pointed at `@clol123` (one governed transition), and the hybrid lane model is live. Nothing else changes.

## 5. Guardrails (amendments to the shipped hooks)

The bash guard gains three rules: `gh repo delete` and destructive `gh api` verbs → deny; `gh pr merge` typed manually → `ask` (same philosophy as `git push`: fine, but deliberate); `gh auth logout` → ask. The ship tool itself is invoked via one allowed command, and its internal subprocess calls don't pass through the agent's Bash tool — the same trusted-deterministic-path pattern as `cos_append_event.py`. The hook harness gains fixtures for each new rule, same as before.

New refusals inside the tool (fail-closed, like everything action-shaped): wrong `gh` account; branch behind `origin/main` (stale base — rebase first, deliberately); validators marker stale; PR exists in `closed` state for this branch (a human decision happened; surface it, don't override it).

## 6. Rollout

One governed transition (tr-0007, computed high — touches `policy/**`, `.claude/**`, `tools/**`): `policy/navigation.yaml`, `tools/cos_ship.py`, bash-guard amendments + harness fixtures, and the `cos-transition` skill's steps 11–12 collapsing into "run `cos_ship`". Prerequisite, and the first thing to do regardless: **a fresh capability** — `cap-0000-genesis` expires 2026-07-08T18:00Z, after which the agent holds no authority until you issue one (suggested: a 30-day capability scoped to `tools/**`, `docs/**`, `policy/navigation.yaml`, `.claude/**`, record paths — issued by you, merged through the gateway per the capabilities/ CODEOWNERS rule).

Acceptance test — pleasingly circular: the transition that ships `cos_ship` is the last one ever shipped by hand, and the first thing `cos_ship` ships is its own follow-up fix, because there will be one.

## 7. Decisions (resolved by the owner, 2026-07-07)

1. High/critical bypass evidence: **typed one-line reason**, posted to the PR by the tool; `governance_debt.py` counts and inspects bypasses for drift.
2. The tool stays **fully headless**; it prints the merged PR URL and never opens a browser.
3. The `clol123` second-reviewer upgrade is **parked indefinitely**; the hybrid lane config remains a one-value flip whenever wanted.

One consequence of solo bypass to engineer around, recorded here so the build honors it: `--admin` bypasses *all* platform requirements, including the required status check. The check-gate therefore moves into the tool for bypassed merges — step 5 (`gh pr checks --watch`) is mandatory and the tool refuses to reach the merge step on anything but green. The platform guarantees it for reviewed merges; the deterministic tool guarantees it for bypassed ones; both paths are auditable after the fact by replaying validators over history.
