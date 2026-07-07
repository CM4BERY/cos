<!-- cos:locus-exempt-file -->
> Owner-approved implementation specification for the Claude Code automation
> layer (cleaned by the owner, 2026-07-07). Narrative spec: binding rules live
> in policy/ and are enforced by validators and hooks, not by this document.

# Claude Code Automation Layer for the COS Repository

This document designs a practical automation layer for `CM4BERY/cos`, the Git-native Constitutional Operating System. The core design choice is to use Claude Code's hooks, skills, subagents, and deterministic tooling as an execution-time enforcement layer for COS.

COS v0 enforces governance at merge time. Claude Code hooks add enforcement at tool-call time. That makes hooks a practical implementation path for COS v1's deferred tool-mediation proxy without building a separate proxy service.

The portfolio is intentionally small. It uses: `CLAUDE.md` for stable repo facts and standing rules; skills for repeatable procedures; hooks for hard enforcement; subagents for noisy read-only investigation; deterministic tools for checks, scaffolds, and state recovery; and explicit rejections for artifacts that would add prompt theater rather than reliability.

## 1. Repo assumptions and observed facts

Observed: Python 3 runtime; dependencies limited to stdlib + `pyyaml` + `jsonschema`; YAML policy, JSON Schema draft-07, ndjson ledger; validation entrypoint `validators/run_all.py`; CI entrypoint `.github/workflows/cos-validate.yml` (checkout → install two deps → run validators against PR base SHA); local validation command `git add -A && python3 validators/run_all.py --base <ref> --head WORKTREE`. Protocol per merge: exactly one ledger event, one `transitions/tr-NNNN.yaml`, a valid capability, evidence, and a diff-derived risk class. Risk model: critical = `constitution/**`, `secrets/**`; elevated/high = `policy/**`, `capabilities/**`, `schemas/**`, `validators/**`, `.github/**`; record paths exempt = `ledger/events.ndjson`, `transitions/**`, `evidence/**`; low = `docs/**`, `README.md`; default medium. Before this layer: no CLAUDE.md, no .claude/, no tests/, no formatter, no linter, no agent automation.

Observed recurring agent failure modes, from this repo's own evidence store: hand-written ledger JSON is error-prone; `__pycache__` polluted the genesis commit before `.gitignore` existed; a self-declared low risk on a policy change was caught only by the validator; a web-UI upload silently dropped `.github/**`.

Assumptions to verify against the installed Claude Code version before relying on them: project skills at `.claude/skills/<name>/SKILL.md`; skill auto-activation may be unreliable (explicit invocation documented in CLAUDE.md); Stop-hook output behavior varies across docs/versions, so exit-code blocking semantics are used; skill `allowed-tools` is not treated as a safety boundary; project-level hooks are expected to apply to subagent tool calls; development spans Windows and Linux, so hooks are Python with a local launcher override; branch protection and CODEOWNERS are assumed active on `main` — hooks do not replace merge-time controls.

## 2. Recommended portfolio

| Name | Type | Trigger | Failure mode reduced | Control gate | Priority |
|---|---|---|---|---|---|
| COS operating contract | CLAUDE.md | Every session | Context loss, stale assumptions, drift | Facts and standing rules only | P0 |
| `cos-transition` | Skill | Any repo file change | Forgotten protocol steps, ambiguous scope | Scope restatement + validator evidence | P0 |
| `cos-amendment` | Skill | Rule changes | Ad-hoc governance drift | Amendment record + ratification path | P1 |
| `cos-add-validator` | Skill | Prose rule needs enforcement | Unenforceable policy accumulation | Failing-first fixture | P2 |
| `cos-write-gate` | Hook | PreToolUse on write tools | Ledger corruption, scope drift, capability bypass | Deny/ask by target, session, capability | P0 |
| `cos-bash-guard` | Hook | PreToolUse on Bash | Destructive commands, shell ledger writes, secret reads | Deny list; human-only bypass | P0 |
| `cos-stop-evidence` | Hook | Stop with unvalidated changes | Premature "done"/"passes" claims | Fresh validation marker or logged waiver | P1 |
| `transition-auditor` | Subagent | Before PR | Self-review blindness | Read-only verdict | P1 |
| `ledger-analyst` | Subagent | Governance health review | Debt invisibility | Must quote deterministic report | P2 |
| `cos_new_transition.py` | Tool | Start of transition | Wrong IDs, missing records, context loss | Refuses unsafe state | P0 |
| `cos_append_event.py` | Tool | Ledger append | Hand-written ledger JSON errors | Schema-validate before append | P0 |
| `cos_validate.sh` | Tool | Before PR / completion claim | Unverified completion | Writes marker consumed by Stop hook | P0 |
| `cos_status.py` | Tool | Session start / recovery | Context loss | Deterministic state print | P1 |
| `governance_debt.py` | Tool | On demand / scheduled | Debt invisibility | Thresholds exit nonzero | P2 |
| `test_hooks.sh` | Tool | CI + before `.claude/**` edits | Silent hook regression | Fixture allow/ask/deny assertions | P1 |

Rejected: repo-map skill (static facts belong in CLAUDE.md); "follow best practices" skill (vague, unenforceable); auto-append ledger hook (the append stays a deliberate audit act — automate correctness, not occurrence); test-triage subagent (no test framework; validator output is short and structured); formatter hook (no formatter configured; manufactures over-editing); standalone secret hook (covered by permissions deny + write gate + bash guard).

## 3. CLAUDE.md

Shipped at repo root (Stage 1). Contents: what the repo is, confirmed commands, repo map with scopes, risk lanes with loci, and standing rules — including: never hand-edit the ledger; never self-declare risk; one PR = one transition = one event; quote the validator RESULT line or state what was not run; restate scope in the transition record before multi-file edits; stop-and-ask actions; explicit skill invocation; and the classification rule (facts here, procedures in skills, enforcement in hooks/validators/tools, noisy investigation in subagents).

## 4. Skills

`cos-transition` (Stage 2): carry one change through the protocol — status check, scope restatement, capability check (never self-issue), scaffold via tool, edit only declared targets (record edit is the auditable scope-change act), rollback/verification notes for medium+, append via tool, validate via wrapper, auditor pass, agent-authored commit, PR body from template. Stop conditions: no covering capability; touches constitution/, capabilities/, secrets/**; computed high/critical; validators fail twice on one cause; any push/publish/destructive action. Verification: quote the RESULT line or state what was not run.

`cos-amendment` (Stage 3): rule changes as governed amendments — problem with ledger evidence, `governance/amendments/A-NNNN.yaml` (from/to, reason, expected effect, rollback), simulation note (replayed outcomes + who benefits), loci updates, one governed transition, explicit authority-expansion statement (beneficiary is not the sole approver). Hand constitution changes to the owner.

`cos-add-validator` (Stage 3): prose rule → computable check — failing-first fixture in `tools/fixtures/`, validator per `cos_lib` conventions, registration in `run_all.py`, locus entry, both runs quoted (fixture FAIL proving detection, clean PASS proving repo validity). Stop if the rule is not computable from repo state or diff — it needs a different locus, not a fake validator.

## 5. Hooks

Wired from `.claude/settings.json`: PreToolUse `^(Edit|Write|MultiEdit|NotebookEdit)$` → `cos_write_gate.py`; PreToolUse `^Bash$` → `cos_bash_guard.py`; Stop → `cos_stop_evidence.py`; plus `permissions.deny: Read(./secrets/**)`. POSIX users may override the `python` launcher in gitignored local settings.

`cos-write-gate` — rules in order: (1) deny writes to `ledger/events.ndjson` (only `tools/cos_append_event.py` writes it); (2) allow record paths `transitions/**`, `evidence/**`, `.cos/**` and paths outside the repo; (3) deny `secrets/**`; (4) `ask` for `constitution/**` (lane-4 authority live; merge-time protocol still applies); (5) deny governed writes with no `.cos/session.json`; (6–8) target must be in the transition record's declared targets and the session capability must exist, be unexpired, allow the path, not deny it; (9) fail closed on any internal error. No agent bypass; humans bypass by editing files themselves or via local settings.

`cos-bash-guard` — deny: force push and history rewrite (`ledger_history_rewrite`), `git reset --hard`, destructive `git clean`, commit on `main`, deleting `main`, shell redirection into the ledger, recursive deletion of governed paths, `secrets/**` reads, dependency installs beyond pyyaml/jsonschema, and setting the bypass variable in-session. `ask` for non-force `git push`. Bypass: only `COS_ALLOW_DANGEROUS=1` set by the human before launch. Fail closed.

`cos-stop-evidence` — with uncommitted governed changes, require `.cos/last-validation.json` whose state digest (`git status --porcelain` + `git diff HEAD`) matches now and whose result is PASS; otherwise block once (exit 2) with the remediation command; an identical second stop is allowed but appends to `.cos/waivers.log` — the bypass exists and is never silent. Fail open with a stderr warning: gates on actions fail closed, gates on stopping fail open.

## 6. Subagents (Stage 3)

`transition-auditor`: read-only pre-PR audit — diff ⊆ targets, intent↔diff coherence, exactly-one event with consistent fields, evidence existence, risk expectation vs recorded. Returns READY/NOT READY + numbered findings with paths + confidence. Escalates immediately on constitution/capabilities/secrets diffs, non-append ledger diffs, missing evidence, or failing validators. `ledger-analyst`: read-only governance-health sweep; must quote `governance_debt.py`; at most three amendment candidates phrased problem → change → beneficiary; explicit no-signal statements; escalates on integrity violations (rewrite, expired-capability use, missing referenced evidence).

## 7. Tooling

`cos_append_event.py` — the only sanctioned ledger writer: composes event_id/prev/timestamp, recomputes risk from the diff via `cos_lib` (self-declared risk becomes unrepresentable), schema-validates, refuses duplicates/missing records/expired capabilities, never writes a partial line. `cos_validate.sh` — single source of validation truth: add-all, run validators, write the digest marker the Stop hook consumes; falls back from origin/main to HEAD and says so. `cos_new_transition.py` — all-or-nothing scaffold: refuses dirty worktree, duplicate ids, empty targets, missing unexpired capability; creates branch record + session. `cos_status.py` — read-only context recovery: branch, session, capability expiry, declared targets vs dirty files, marker age/result, last three events. `governance_debt.py` (Stage 3) — deterministic debt report with hard thresholds. `test_hooks.sh` — pipes fixture payloads through each hook asserting allow/ask/deny and fail-closed/fail-open polarity; parses settings; lints skills for frontmatter and static-fact drift. Gitignored: `.cos/`, `.claude/settings.local.json`, `.claude/logs/`.

## 8. Implementation order

Everything ships through COS itself. Stage 1 (one transition, medium): CLAUDE.md, append/validate/status tools, .gitignore, this spec. Stage 2 (one transition, high): amendment A-0001 making `.claude/**` elevated, settings, three hooks, scaffold tool, hook harness + CI step, `cos-transition` skill. Stage 3 (separate small transitions, adopt when the trigger appears): auditor, amendment skill, ledger-analyst + debt tool, add-validator skill.

## 9. Verification plan

(1) Normal workflow: docs edit flows through scaffold → append → validate; RESULT quoted; PR body from template. (2) Ambiguous scope: targets proposed and confirmed before any successful edit; gate blocks target-less governed edits. (3) Destructive request: force-push denied citing `ledger_history_rewrite`; nothing pushed. (4) Premature done: Stop gate blocks; real RESULT reported or explicit non-validation statement; forced second stop logs a waiver. (5) Static-fact skill misuse: harness fails naming the file. (6) Hook failure: garbage input → gate and guard deny (closed), stop exits 0 with warning (open). (7) Broken session: invalid session.json cannot crash the gate open. (8) Subagent handoff: seeded bad transition returns NOT READY with both findings and no writes. (9) Cross-cutting: no message claims validators passed, work is complete, risk was computed, or a PR is ready without command output or file evidence from the current session.
