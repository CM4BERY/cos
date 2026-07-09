#!/usr/bin/env bash
# Hook + .claude artifact harness. Exits 1 on any failed assertion.
set -uo pipefail
cd "$(dirname "$0")/.."
FAIL=0
PY="${PY:-python3}"

decision() { # decision <hook> <json>
  echo "$2" | "$PY" ".claude/hooks/$1" 2>/dev/null \
    | "$PY" -c "import json,sys
try: print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])
except Exception: print('allow')" 2>/dev/null || echo "error"
}

expect() { # expect <name> <want> <got>
  if [ "$3" = "$2" ]; then echo "PASS  $1"; else echo "FAIL  $1 (want $2, got $3)"; FAIL=1; fi
}

# --- write gate (session-independent cases; session file parked for determinism)
SESS=.cos/session.json; PARKED=0
if [ -f "$SESS" ]; then mv "$SESS" "$SESS.parked"; PARKED=1; fi
expect "gate: ledger deny"        deny  "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"ledger/events.ndjson"}}')"
expect "gate: secrets deny"       deny  "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"secrets/key.pem"}}')"
expect "gate: constitution ask"   ask   "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"constitution/charter.yaml"}}')"
expect "gate: no-session deny"    deny  "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"docs/x.md"}}')"
expect "gate: record path allow"  allow "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"transitions/tr-9999.yaml"}}')"
expect "gate: garbage fail-closed" deny "$(echo garbage | "$PY" .claude/hooks/cos_write_gate.py | "$PY" -c "import json,sys; print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])")"
# --- write gate: declared-targets enforcement (regression: column-0 YAML lists)
mkdir -p .cos
cat > capabilities/cap-9997-harness.yaml <<'Y'
id: cap-9997-harness
issued_by: "harness:fixture"
issued_to_actor: "agent:claude-fable-5"
issued_for_office: executor
allowed_actions: [edit_file]
allowed_targets:
- "docs/**"
issued_at: "2020-01-01T00:00:00Z"
expires_at: "2099-01-01T00:00:00Z"
Y
cat > transitions/tr-9997.yaml <<'Y'
id: tr-9997
targets:
- docs/harness-probe.md
Y
printf '{"transition_id":"tr-9997","capability_id":"cap-9997-harness"}' > "$SESS"
expect "gate: in-target allow (col-0 list)" allow "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"docs/harness-probe.md"}}')"
expect "gate: out-of-target deny"           deny  "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"README.md"}}')"
cat > transitions/tr-9997.yaml <<'Y'
id: tr-9997
targets: []
Y
expect "gate: empty targets fail-closed"    deny  "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"docs/harness-probe.md"}}')"
rm -f transitions/tr-9997.yaml capabilities/cap-9997-harness.yaml "$SESS"
# --- write gate: expired capability denies (cap-9997 above expires 2099 and
#     never exercises the expiry branch; this fixture does)
cat > capabilities/cap-9998-expired.yaml <<'Y'
id: cap-9998-expired
issued_by: "harness:fixture"
issued_to_actor: "agent:claude-fable-5"
issued_for_office: executor
allowed_actions: [edit_file]
allowed_targets:
- "docs/**"
issued_at: "2020-01-01T00:00:00Z"
expires_at: "2020-06-01T00:00:00Z"
Y
cat > transitions/tr-9998.yaml <<'Y'
id: tr-9998
targets:
- docs/harness-probe.md
Y
printf '{"transition_id":"tr-9998","capability_id":"cap-9998-expired"}' > "$SESS"
expect "gate: expired capability deny" deny "$(decision cos_write_gate.py '{"cwd":".","tool_input":{"file_path":"docs/harness-probe.md"}}')"
rm -f transitions/tr-9998.yaml capabilities/cap-9998-expired.yaml "$SESS"
[ "$PARKED" = 1 ] && mv "$SESS.parked" "$SESS"

# --- bash guard
expect "guard: force-push deny"   deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"git push --force origin main"}}')"
expect "guard: ledger redirect deny" deny "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"printf x >> ledger/events.ndjson"}}')"
expect "guard: append tool allow" allow "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"python3 tools/cos_append_event.py --transition tr-0004"}}')"
expect "guard: plain push ask"    ask   "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"git push origin tr-0004"}}')"
expect "guard: pip foreign deny"  deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"pip install requests"}}')"
expect "guard: pip deps allow"    allow "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"pip install pyyaml jsonschema"}}')"
expect "guard: bypass-var deny"   deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"export COS_ALLOW_DANGEROUS=1"}}')"
expect "guard: ship bypass deny"  deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"python3 tools/cos_ship.py --bypass \"x\""}}')"
expect "guard: ship plain allow"  allow "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"python3 tools/cos_ship.py"}}')"
expect "guard: reset-hard deny"   deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"git reset --hard HEAD~1"}}')"
expect "guard: garbage fail-closed" deny "$(echo garbage | "$PY" .claude/hooks/cos_bash_guard.py | "$PY" -c "import json,sys; print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])")"
expect "guard: gh repo delete deny"  deny "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"gh repo delete CM4BERY/cos --yes"}}')"
expect "guard: gh api DELETE deny"   deny "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"gh api -X DELETE /repos/CM4BERY/cos"}}')"
expect "guard: manual gh merge ask"  ask  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"gh pr merge tr-0007 --squash"}}')"
expect "guard: gh auth logout ask"   ask  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"gh auth logout"}}')"
expect "guard: gh pr view allow"     allow "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"gh pr view tr-0007"}}')"

# --- ship tool: refuses to run off a transition branch (offline check)
"$PY" tools/cos_ship.py --render-only >/dev/null 2>&1
[ "$?" = "1" ] && echo "PASS  ship: refuses on main" || { echo "FAIL  ship: should refuse on main"; FAIL=1; }
"$PY" -c "
import sys; sys.path.insert(0, 'tools')
from cos_ship import classify_checks as c
assert c('0 cancelled, 0 failing, 1 successful, 0 skipped, and 0 pending checks') == 'green'
assert c('0 cancelled, 0 failing, 1 successful, 0 skipped, and 2 pending checks') == 'pending'
assert c('0 cancelled, 1 failing, 0 successful, 0 skipped, and 0 pending checks') == 'failing'
assert c('1 cancelled, 0 failing, 1 successful, 0 skipped, and 0 pending checks') == 'failing'
assert c('gibberish') == 'unknown'
" >/dev/null 2>&1 && echo "PASS  ship: classify_checks" || { echo "FAIL  ship: classify_checks"; FAIL=1; }

# --- governance debt tool: seeded breach detected FIRST (failing-first),
#     then the healthy repo, then byte-determinism (story-001 acceptance).
#     Seeded temp repo carries two breaches: a ledger event stamped outside
#     its capability window, and a review-mode PR merge whose event evidence
#     has no evidence/reviews/ file.
GD_TMP=$(mktemp -d)
git -C "$GD_TMP" init -q
git -C "$GD_TMP" checkout -q -b main
mkdir -p "$GD_TMP/ledger" "$GD_TMP/capabilities" "$GD_TMP/policy"
cat > "$GD_TMP/capabilities/cap-9001-lapsed.yaml" <<'Y'
id: cap-9001-lapsed
issued_at: "2020-01-01T00:00:00Z"
expires_at: "2020-02-01T00:00:00Z"
Y
cat > "$GD_TMP/policy/navigation.yaml" <<'Y'
bypass:
  low: auto
  medium: auto
  high: review
  critical: review
Y
printf '%s\n' '{"event_id": "evt-9001", "timestamp": "2026-01-01T00:00:00Z", "transition_id": "tr-9001", "capability_id": "cap-9001-lapsed", "risk_class": "high", "decision": "require_review", "evidence": []}' > "$GD_TMP/ledger/events.ndjson"
git -C "$GD_TMP" add -A
git -C "$GD_TMP" -c user.name=harness -c user.email=h@cos.local -c commit.gpgsign=false commit -qm "seed state"
git -C "$GD_TMP" -c user.name=harness -c user.email=h@cos.local -c commit.gpgsign=false commit -q --allow-empty -m "tr-9001: seeded review merge, no reason [evt-9001] (#1)"
GD_SEEDED=$("$PY" tools/governance_debt.py --repo "$GD_TMP" 2>&1)
expect "debt: seeded breach rc 1 (failing-first)" 1 "$?"
echo "$GD_SEEDED" | grep -q "outside cap-9001-lapsed window" \
  && echo "PASS  debt: expired-capability event named" \
  || { echo "FAIL  debt: expired-capability event not named"; FAIL=1; }
echo "$GD_SEEDED" | grep -q "no existing evidence/reviews/ file" \
  && echo "PASS  debt: review merge lacking reason named" \
  || { echo "FAIL  debt: review merge lacking reason not named"; FAIL=1; }
rm -rf "$GD_TMP"
GD_A=$("$PY" tools/governance_debt.py 2>&1)
expect "debt: healthy repo rc 0" 0 "$?"
GD_B=$("$PY" tools/governance_debt.py 2>&1)
expect "debt: healthy verdict line" "GOVERNANCE DEBT: OK (0 breaches)" "$(echo "$GD_A" | tail -1)"
[ "$GD_A" = "$GD_B" ] && echo "PASS  debt: deterministic output (two runs identical)" \
  || { echo "FAIL  debt: output differs across runs"; FAIL=1; }

# --- stop gate polarity
echo garbage | "$PY" .claude/hooks/cos_stop_evidence.py >/dev/null 2>&1
expect "stop: garbage fail-open (rc 0)" 0 "$?"

# --- settings + artifact hygiene
"$PY" -c "import json; json.load(open('.claude/settings.json'))" 2>/dev/null
expect "settings.json parses" 0 "$?"
for s in .claude/skills/*/SKILL.md; do
  [ -e "$s" ] || continue
  head -5 "$s" | grep -q "^---$" || head -5 "$s" | grep -q "cos:locus-exempt-file" || { echo "FAIL  $s: no frontmatter"; FAIL=1; }
  grep -q "^description:" "$s" || sed -n '1,10p' "$s" | grep -q "description:" || { echo "FAIL  $s: no description"; FAIL=1; }
  if grep -qiE "^## Repo map|^\| *constitution/|Package manager:|Build system:" "$s"; then
    echo "FAIL  $s: contains static repo facts that belong in CLAUDE.md"; FAIL=1
  else
    echo "PASS  skill hygiene: $s"
  fi
done
if [ -d .claude/agents ]; then
  for agmd in .claude/agents/*.md; do
    [ -e "$agmd" ] || continue
    grep -qi "forbidden" "$agmd" && grep -qi "output contract" "$agmd" \
      && echo "PASS  agent hygiene: $agmd" \
      || { echo "FAIL  $agmd: missing Forbidden/Output contract sections"; FAIL=1; }
  done
fi

[ "$FAIL" = 0 ] && echo "HARNESS: ALL PASS" || echo "HARNESS: FAILURES"
exit $FAIL
