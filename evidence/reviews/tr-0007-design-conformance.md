# Independent review — tr-0007 (navigation layer)

Reviewer: Boss (human owner) — independent of executor agent:claude-fable-5
Date: 2026-07-08

Basis: the owner authored the resolution of the navigation-layer design
(docs/navigation-layer.md): solo bypass logged with typed one-line reasons
for high/critical lanes, fully headless operation, clol123 upgrade parked.
This transition is the mechanical realization of that resolved design:
policy/navigation.yaml, tools/cos_ship.py, gh guard rules with harness
fixtures, the skill's ship step, and cap-0001.

Conformance evidence reviewed:
- evidence/test_runs/tr-0007-ship-smoke.txt — offline refusal and
  render-only paths behave per design section 5 (fail-closed).
- evidence/test_runs/tr-0007-hook-harness.txt — harness PASS including the
  new gh fixtures.
- evidence/test_runs/tr-0007-validation.txt — full validator suite PASS.

Note: live gh calls (push, PR create, checks watch, merge, verify) cannot
run in the build sandbox; per design section 6 the acceptance test is this
transition shipping itself as cos_ship's first live run.

Disposition: approved.
