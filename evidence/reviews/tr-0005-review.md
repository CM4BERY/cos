# Independent review — tr-0005 (write-gate target-parsing fix)

Reviewer: Boss (human owner) — independent of executor agent:claude-fable-5
Date: 2026-07-07

Defect: docs/automation-layer.md section 5 rule 7 states the gate confirms
"the target file is inside the transition's declared targets". The shipped
parser only recognized indented YAML list items; records written by
tools/cos_new_transition.py emit column-0 items, so targets parsed empty and
the check silently passed (fail-open) — contrary to the spec's fail-closed
requirement for action gates.

Fix reviewed: parser accepts column-0 and indented items; an empty parsed
target list now denies (fail-closed); tools/cos_status.py parser aligned;
three regression fixtures added to tools/test_hooks.sh with a synthetic
harness capability so the fixtures outlive cap-0000-genesis.

Evidence: evidence/test_runs/tr-0005-hook-harness.txt (21/21 PASS, including
the regression cases). Defect was caught by the verification step the spec
mandates, before any push — the process worked as designed.

Disposition: approved.
