# System status — 2026-07-08, close of the founding session (tr-0008)

Durable context-recovery point. The repo is the state; this file is the map.
A fresh session (human, Cowork, or Claude Code) reads this, CLAUDE.md, and
`python3 tools/cos_status.py`, and knows where things stand.

## What exists and works

The v0 gateway: five validators + CI (`cos-validate`, green since genesis),
org ruleset on `main` (PR + 1 review + status check; admin bypass for the
solo owner), squash-only merges. The automation layer (tr-0003/0004/0005):
CLAUDE.md operating contract, three Claude Code hooks (write gate and bash
guard fail closed; stop gate fails open, waivers logged), cos-transition
skill, deterministic tools (scaffold, append, validate, status), 27+ fixture
harness in CI. The navigation layer (tr-0007/0008): `tools/cos_ship.py` — one
command from a validator-clean transition to a verified merge — with
policy/navigation.yaml and `gh` guard rules. First live run merged tr-0007;
its first self-shipped fix (pending-vs-failing check classification) is this
transition.

## Identities and authority

`CM4BERY` is an organization (no login exists for it). `CMABERY` is the sole
human: author, org owner, `gh`-pinned account. `clol123` owns the commit
email, appears as co-author cosmetically, and is the parked future reviewer.
The agent (`agent:claude-fable-5`) acts under `cap-0001-agent-standing`
(expires 2026-08-07T05:00Z): tools/**, docs/**, README.md,
policy/navigation.yaml, .claude/**, and record paths; constitution/ and
secrets/** denied. cap-0000-genesis retired 2026-07-08T18:00Z.

## Decisions of record

Solo bypass, logged: merges use the owner's admin bypass; high/critical
lanes take a typed one-line reason posted to the PR; GitHub's PR timeline is
the bypass ledger and a future governance_debt.py counts it. Fully headless
tooling. clol123 second-reviewer upgrade parked (one config flip + a
CODEOWNERS transition when wanted). Threat model unchanged: honest-but-
fallible actors, not adversarial ones.

## The operating loop

1. Start: `python3 tools/cos_new_transition.py "<intent>" --targets <paths>`
2. Work within declared targets (hooks watch); update the record if scope grows.
3. Record: `python3 tools/cos_append_event.py --transition tr-NNNN`, then
   `bash tools/cos_validate.sh`, then commit as the agent.
4. Ship: `python3 tools/cos_ship.py` (add `--bypass "reason"` on high/critical).

## Machine notes (Windows)

Home clone: `C:\cos-clean` (cloned with core.autocrlf=false — keep it that
way). `C:\cos` is condemned: mixed WSL-git/Windows-git history made its
status output untrustworthy; delete at leisure. Rule: only Windows git
touches the Windows clone; Ubuntu work lives separately (~/OS). `gh` is
installed and authenticated as CMABERY.

## Parked items / next candidates

Stage 3 pieces, adopt when their trigger appears: governance_debt.py (first
consumer of the bypass ledger), transition-auditor and ledger-analyst
subagents, cos-amendment and cos-add-validator skills. Housekeeping: add the
ship command to CLAUDE.md's Commands section — parked because cap-0001
deliberately does not cover CLAUDE.md (an owner edit or a broader capability
does it); a stray "asdf" comment on PR #1 (cosmetic); delete C:\cos.

## Ledger at close

Nine events, evt-0001 (genesis, constitution ratified) through evt-0009
(this transition). Every commit on main replays clean through
`validators/run_all.py`. The ledger is the truth; this file is only the tour.
