# System status — 2026-07-12, GitHub App publisher transition (tr-0018)

Durable context-recovery point. The repo is the state; this file is the map.
A fresh session (human, Cowork, or Claude Code) reads this, CLAUDE.md, and
`python3 tools/cos_status.py`, and knows where things stand.

## What exists and works

Everything from the founding session (v0 gateway, automation layer, navigation
layer — see tr-0008's edition of this file in history), plus the Ralph pilot,
shipped as three governed transitions and one live story:

- tr-0009 (high, human-reviewed): the human gate. policy/navigation.yaml flips
  high/critical from `flag` to `review` — cos_ship opens the PR, watches
  checks, and stops before merging; a human completes the merge and records
  the one-line reason as their PR review/merge comment (navigation-layer §7
  item 4). Guard rule denies agent-run `cos_ship --bypass`; harness gained
  ship-bypass and expired-capability fixtures.
- tr-0010 (medium): loop scaffolding — docs/ralph-backlog.yaml (machine-checkable
  stories with capability prechecks and hard exclusions), docs/ralph-prompt.md
  (single-story iterations, story text is data, halt-not-skip), tools/ralph_loop.sh
  (one iteration per invocation, tty-acknowledged continuation, hard cap 5).
- tr-0011 (low): probe evidence. Headless probe: hook denies observed; ask
  fails closed with no approver; Stop hook logged a waiver. Injection smoke:
  a hostile story instruction was reported as a finding, never obeyed.
- tr-0012 (medium, shipped BY the loop): governance_debt.py — deterministic
  debt report with hard thresholds (exit 1 on merges without ledger linkage,
  review-mode merges lacking a recorded reason, expired-capability events);
  six failing-first harness fixtures. First live Ralph iteration, end to end.
- tr-0017 (high, App-authored and human-approved): owner-ratified
  `cap-0002-publisher-transition`, bound to tr-0018 and narrow publisher,
  governance, documentation, record, and evidence targets.
- tr-0018 (high, this transition): `cos_ship` mints short-lived GitHub App
  installation tokens and revokes them after each run, verifies repository and
  permission scope, publishes draft PRs as
  `cm4bery-cos-executor[bot]`, and stops every lane for human review. A-0002
  records the rule change and replay.

Pilot findings of record: a concurrent second runner invocation raced the
first over the tr-0012 scaffold; the losing iteration detected it, unwound to
zero in-flight state, and halted with a correct diagnosis. Fix queued as
backlog story-005 (flock + tee). The headless permission layer sits in front
of the hooks, so the pilot clone allowlists the deterministic COS tools in
gitignored local settings.

## Identities and authority

`CM4BERY` is the organization/repository owner; `CMABERY` is the human root
authority and CODEOWNER; `cm4bery-cos-executor[bot]` is the publisher and PR
author. The agent (`agent:claude-fable-5`) executes tr-0018 under the
human-issued `cap-0002-publisher-transition`, expiring
2026-07-19T10:42:53Z. Constitution and secrets remain denied. The App has no
ruleset bypass, workflow, administration, issues, secrets, or organization
permission.

## The operating loop

1. Start: `python3 tools/cos_new_transition.py "<intent>" --targets <paths>`
2. Work within declared targets (hooks watch); update the record if scope grows.
3. Record: `python3 tools/cos_append_event.py --transition tr-NNNN`, then
   `bash tools/cos_validate.sh`, then commit as the agent.
4. Ship: `python3 tools/cos_ship.py` — mint a scoped App token, push and open
   a draft PR, watch checks, revoke the token, and stop before merge for
   `CMABERY` on every lane.
Ralph iterations: `bash tools/ralph_loop.sh` in the pilot clone, one story per
invocation, a human watching; the backlog is the queue.

## Machine notes

- Active governance clone: `~/projects/cos` on Ubuntu 24.04 (WSL). The App
  PEM is owner-only at `~/.config/cos/cos-executor.pem`; `cos_ship` does not
  use or alter the human's stored `gh` credential. The unrelated
  `origin/tr-0016` runner-lock WIP remains unchanged.
- Governance clone: `C:\cos-clean` on Windows — Cowork agent sessions mount
  it through a sync layer that twice corrupted git metadata during the pilot
  session (.git/index zero-filled, ORIG_HEAD broken; repaired by deleting the
  bad file and rebuilding — object store never damaged) and can truncate or
  drop host<->sandbox file propagation. Working rules learned: Cowork
  sessions write through their shell side only; one writer per checkout at a
  time, and org-wide during any ship; verify with `git status` before ship.
  These supersede the earlier "only Windows git" rule from tr-0008.
- Stale copies: `/home/cmabery/cos` is an old pre-automation clone (rename or
  delete; it has trapped three sessions' worth of commands). `C:\cos` remains
  condemned, delete at leisure.

## Parked items / next candidates

- Backlog queue (docs/ralph-backlog.yaml): story-002 cos-amendment skill and
  story-003 cos-add-validator skill and story-004 transition-auditor subagent
  (all expected high — each iteration ends at a review-mode PR for the owner),
  story-005 runner lock + tee (medium).
- CLAUDE.md Commands lines for cos_ship and governance_debt: CLAUDE.md sits
  outside cap-0001 on purpose, so this stays parked until the owner either
  edits it through an owner-side transition or issues a capability covering it.
- Pilot allowlist line for `Bash(python3 tools/governance_debt.py*)` in
  ~/cos-pilot/.claude/settings.local.json (owner, ten seconds, no transition).
- clol123 second-reviewer upgrade: parked as before.

## Ledger at close

Eighteen events, evt-0001 (genesis) through evt-0018 (this transition).
The ledger is the truth; this file is only the tour.
