#!/usr/bin/env bash
# Ralph runner: one governed iteration per invocation, human-gated continuation.
#
# Usage:
#   bash tools/ralph_loop.sh              exactly ONE iteration, then exit
#   bash tools/ralph_loop.sh --continue   further iterations only after an
#                                         interactive acknowledgment read from
#                                         the tty between iterations; hard cap
#                                         MAX_ITER per invocation as backstop
#   bash tools/ralph_loop.sh --selftest   offline smoke fixtures for the lock
#                                         and tee behaviors; stub agents only,
#                                         run in a temp sandbox, never invokes
#                                         a real agent or touches this repo
#
# The per-iteration prompt is docs/ralph-prompt.md, fed on stdin to the agent
# command in RALPH_AGENT_CMD (default: "claude -p"). This runner sets no
# environment overrides and carries no bypass flags of any kind; lane
# enforcement lives in policy/navigation.yaml and the hooks, not here.
#
# One invocation at a time: the runner holds an exclusive flock on
# .cos/ralph/lock for its whole life. On 2026-07-09 two concurrent invocations
# raced over the same scaffold (tr-0012) until one halted itself. A silent
# terminal invited the second launch, so agent output now streams to the
# terminal as well as the transcript.
#
# Exit codes:
#   0  sentinel-complete   backlog empty: agent emitted the completion promise
#   2  human-halt          --continue without a tty, or acknowledgment declined
#   3  stop-condition halt agent emitted COS-RALPH HALT, appended a waiver to
#                          .cos/waivers.log, or exited nonzero (fail closed)
#   4  cap-reached         MAX_ITER iterations ran without a terminal marker
#   5  iteration-done      single iteration finished; backlog work may remain
#   6  usage error         bad argument, missing prompt, or no flock(1)
#   7  lock-contended      another invocation already holds .cos/ralph/lock
set -uo pipefail
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
cd "$(dirname "$0")/.."

MAX_ITER=5
SENTINEL='<promise>COS-RALPH COMPLETE</promise>'
HALT_MARK='COS-RALPH HALT:'
PROMPT_FILE=docs/ralph-prompt.md
AGENT_CMD="${RALPH_AGENT_CMD:-claude -p}"
WAIVERS=.cos/waivers.log
LOCK=.cos/ralph/lock
CURRENT=.cos/ralph/current

# Offline fixtures. Each runs a copy of this script in a temp sandbox with a
# stub agent, so no fixture can reach the real .cos/, ledger, or agent command.
selftest() {
  local sandbox term log live holder waited rc fails=0

  if ! command -v flock >/dev/null 2>&1; then
    echo "FAIL selftest: flock(1) not found — the lock fixture cannot run."
    return 1
  fi
  sandbox=$(mktemp -d "${TMPDIR:-/tmp}/ralph-selftest.XXXXXX") || {
    echo "FAIL selftest: mktemp failed"; return 1; }
  mkdir -p "$sandbox/tools" "$sandbox/docs"
  cp "$SELF" "$sandbox/tools/ralph_loop.sh"
  printf 'stub prompt\n' > "$sandbox/docs/ralph-prompt.md"

  # Fixture 1 — tee: the terminal and the transcript carry identical agent bytes.
  term="$sandbox/terminal.txt"
  RALPH_AGENT_CMD='printf "alpha\nbeta\ngamma\n"' \
    bash "$sandbox/tools/ralph_loop.sh" > "$term" 2>&1
  rc=$?
  log=$(ls "$sandbox"/.cos/ralph/*-iter-1.txt 2>/dev/null | head -1)
  if [ "$rc" -ne 5 ]; then
    echo "FAIL tee: expected exit 5 (iteration-done), got ${rc}"; fails=1
  elif [ -z "$log" ]; then
    echo "FAIL tee: no transcript was written"; fails=1
  else
    grep -v '^ralph: ' "$term" > "$sandbox/terminal.agent.txt"
    if cmp -s "$sandbox/terminal.agent.txt" "$log"; then
      echo "PASS tee: terminal and transcript agent bytes identical ($(wc -c < "$log") bytes)"
    else
      echo "FAIL tee: terminal bytes differ from transcript bytes"; fails=1
    fi
  fi

  # Fixture 2 — lock: a second concurrent invocation is refused, names the
  # live transcript, and never reaches the agent.
  RALPH_AGENT_CMD='sleep 4' bash "$sandbox/tools/ralph_loop.sh" \
    > "$sandbox/holder.txt" 2>&1 &
  holder=$!
  waited=0
  while [ ! -s "$sandbox/$CURRENT" ] && [ "$waited" -lt 40 ]; do
    sleep 0.1
    waited=$((waited + 1))
  done
  live=$(cat "$sandbox/$CURRENT" 2>/dev/null)
  RALPH_AGENT_CMD='printf "SHOULD-NOT-RUN\n"' \
    bash "$sandbox/tools/ralph_loop.sh" > "$sandbox/contender.txt" 2>&1
  rc=$?
  kill "$holder" 2>/dev/null
  wait "$holder" 2>/dev/null

  if [ -z "$live" ]; then
    echo "FAIL lock: holder never published its transcript to ${CURRENT}"; fails=1
  elif [ "$rc" -ne 7 ]; then
    echo "FAIL lock: expected exit 7 (lock-contended), got ${rc}"; fails=1
  elif [ "$(wc -l < "$sandbox/contender.txt")" -ne 1 ]; then
    echo "FAIL lock: refusal was not a single line"; fails=1
  elif ! grep -qF -- "$live" "$sandbox/contender.txt"; then
    echo "FAIL lock: refusal does not name the live transcript ${live}"; fails=1
  elif grep -rqF -- 'SHOULD-NOT-RUN' "$sandbox/.cos/ralph"; then
    echo "FAIL lock: the refused invocation still ran its agent"; fails=1
  else
    echo "PASS lock: contender refused with exit 7, naming ${live}"
  fi

  rm -rf "$sandbox"
  if [ "$fails" -ne 0 ]; then
    echo "RUNNER: FAIL"
    return 1
  fi
  echo "RUNNER: ALL PASS"
  return 0
}

CONTINUE=0
case "${1:-}" in
  "") ;;
  --continue) CONTINUE=1 ;;
  --selftest) selftest; exit $? ;;
  *) echo "ralph: unknown argument: $1 (only --continue and --selftest are accepted)"; exit 6 ;;
esac
[ -f "$PROMPT_FILE" ] || { echo "ralph: missing $PROMPT_FILE"; exit 6; }
command -v flock >/dev/null 2>&1 || {
  echo "ralph: flock(1) not found — refusing to run without the single-invocation lock."
  exit 6
}

mkdir -p .cos/ralph
RUN_TS=$(date -u +%Y%m%dT%H%M%SZ)

# Held for the whole invocation: fd 9 stays open until this process exits.
exec 9>"$LOCK" || { echo "ralph: cannot open $LOCK"; exit 6; }
if ! flock -n 9; then
  LIVE=$([ -s "$CURRENT" ] && cat "$CURRENT")
  echo "ralph: another invocation holds $LOCK (live transcript: ${LIVE:-unknown}) — refusing to start."
  exit 7
fi
# Only the lock holder gets here, so CURRENT is ours to publish and clear.
trap 'rm -f "$CURRENT"' EXIT
: > "$CURRENT"

waiver_size() { [ -f "$WAIVERS" ] && wc -c < "$WAIVERS" || echo 0; }

i=1
while :; do
  LOG=".cos/ralph/${RUN_TS}-iter-${i}.txt"
  W_BEFORE=$(waiver_size)
  echo "ralph: iteration ${i}/${MAX_ITER} (transcript: ${LOG})"
  printf '%s\n' "$LOG" > "$CURRENT"

  bash -c "$AGENT_CMD" < "$PROMPT_FILE" 2>&1 | tee "$LOG"
  RC=${PIPESTATUS[0]}
  W_AFTER=$(waiver_size)

  if grep -qF "$SENTINEL" "$LOG"; then
    echo "ralph: backlog complete (sentinel seen)."
    exit 0
  fi
  if grep -qF "$HALT_MARK" "$LOG"; then
    echo "ralph: stop-condition halt:"
    grep -F "$HALT_MARK" "$LOG" | tail -1
    exit 3
  fi
  if [ "$W_AFTER" -gt "$W_BEFORE" ]; then
    echo "ralph: a waiver was appended to ${WAIVERS} this iteration — halting."
    exit 3
  fi
  if [ "$RC" -ne 0 ]; then
    echo "ralph: agent command exited ${RC} — halting (fail closed)."
    exit 3
  fi

  echo "ralph: iteration ${i} finished (see ${LOG})."

  if [ "$CONTINUE" -ne 1 ]; then
    exit 5
  fi
  if [ "$i" -ge "$MAX_ITER" ]; then
    echo "ralph: hard cap of ${MAX_ITER} iterations reached."
    exit 4
  fi
  if [ ! -r /dev/tty ]; then
    echo "ralph: no tty — a further iteration needs an interactive human acknowledgment."
    exit 2
  fi
  printf 'ralph: run iteration %s/%s? [y/N] ' "$((i + 1))" "$MAX_ITER"
  if ! read -r ANS < /dev/tty; then
    echo; echo "ralph: no acknowledgment — halting."
    exit 2
  fi
  case "$ANS" in
    y|Y) ;;
    *) echo "ralph: human declined — halting."; exit 2 ;;
  esac
  i=$((i + 1))
done
