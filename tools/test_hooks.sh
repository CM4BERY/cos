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
[ "$PARKED" = 1 ] && mv "$SESS.parked" "$SESS"

# --- bash guard
expect "guard: force-push deny"   deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"git push --force origin main"}}')"
expect "guard: ledger redirect deny" deny "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"printf x >> ledger/events.ndjson"}}')"
expect "guard: append tool allow" allow "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"python3 tools/cos_append_event.py --transition tr-0004"}}')"
expect "guard: plain push ask"    ask   "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"git push origin tr-0004"}}')"
expect "guard: pip foreign deny"  deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"pip install requests"}}')"
expect "guard: pip deps allow"    allow "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"pip install pyyaml jsonschema"}}')"
expect "guard: bypass-var deny"   deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"export COS_ALLOW_DANGEROUS=1"}}')"
expect "guard: reset-hard deny"   deny  "$(decision cos_bash_guard.py '{"cwd":".","tool_input":{"command":"git reset --hard HEAD~1"}}')"
expect "guard: garbage fail-closed" deny "$(echo garbage | "$PY" .claude/hooks/cos_bash_guard.py | "$PY" -c "import json,sys; print(json.load(sys.stdin)['hookSpecificOutput']['permissionDecision'])")"

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
