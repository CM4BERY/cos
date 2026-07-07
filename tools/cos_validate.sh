#!/usr/bin/env bash
# Single source of local validation truth. Writes the marker the Stop hook reads.
set -uo pipefail
cd "$(dirname "$0")/.."
BASE="${BASE:-$(git rev-parse --verify -q origin/main >/dev/null 2>&1 && echo origin/main || echo HEAD)}"
[ "$BASE" = "HEAD" ] && echo "note: origin/main unavailable; using BASE=HEAD"
git add -A
python3 validators/run_all.py --base "$BASE" --head WORKTREE
rc=$?
mkdir -p .cos
digest=$( (git status --porcelain; git diff HEAD) | python3 -c "import hashlib,sys;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())" )
python3 - "$rc" "$digest" <<'PY'
import datetime, json, sys
rc, digest = int(sys.argv[1]), sys.argv[2]
json.dump({"state_digest": digest,
           "result": "PASS" if rc == 0 else "FAIL",
           "ts": datetime.datetime.now(datetime.timezone.utc).isoformat()},
          open(".cos/last-validation.json", "w"))
PY
exit $rc
