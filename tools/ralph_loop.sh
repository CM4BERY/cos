#!/usr/bin/env bash
# Ralph runner: one governed iteration per invocation, human-gated continuation.
#
# Usage:
#   bash tools/ralph_loop.sh              exactly ONE iteration, then exit
#   bash tools/ralph_loop.sh --continue   further iterations only after an
#                                         interactive acknowledgment read from
#                                         the tty between iterations; hard cap
#                                         MAX_ITER per invocation as backstop
#
# The per-iteration prompt is docs/ralph-prompt.md, fed on stdin to the agent
# command in RALPH_AGENT_CMD (default: "claude -p"). This runner sets no
# environment overrides and carries no bypass flags of any kind; lane
# enforcement lives in policy/navigation.yaml and the hooks, not here.
#
# Exit codes:
#   0  sentinel-complete   backlog empty: agent emitted the completion promise
#   2  human-halt          --continue without a tty, or acknowledgment declined
#   3  stop-condition halt agent emitted COS-RALPH HALT, appended a waiver to
#                          .cos/waivers.log, or exited nonzero (fail closed)
#   4  cap-reached         MAX_ITER iterations ran without a terminal marker
#   5  iteration-done      single iteration finished; backlog work may remain
#   6  usage error
set -uo pipefail
cd "$(dirname "$0")/.."

MAX_ITER=5
SENTINEL='<promise>COS-RALPH COMPLETE</promise>'
HALT_MARK='COS-RALPH HALT:'
PROMPT_FILE=docs/ralph-prompt.md
AGENT_CMD="${RALPH_AGENT_CMD:-claude -p}"
WAIVERS=.cos/waivers.log

CONTINUE=0
case "${1:-}" in
  "") ;;
  --continue) CONTINUE=1 ;;
  *) echo "ralph: unknown argument: $1 (only --continue is accepted)"; exit 6 ;;
esac
[ -f "$PROMPT_FILE" ] || { echo "ralph: missing $PROMPT_FILE"; exit 6; }

mkdir -p .cos/ralph
RUN_TS=$(date -u +%Y%m%dT%H%M%SZ)

waiver_size() { [ -f "$WAIVERS" ] && wc -c < "$WAIVERS" || echo 0; }

i=1
while :; do
  LOG=".cos/ralph/${RUN_TS}-iter-${i}.txt"
  W_BEFORE=$(waiver_size)
  echo "ralph: iteration ${i}/${MAX_ITER} (transcript: ${LOG})"

  bash -c "$AGENT_CMD" < "$PROMPT_FILE" > "$LOG" 2>&1
  RC=$?
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
