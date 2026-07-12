# Human ratification — cap-0002-publisher-transition

Ratifier: Boss (human owner, coltonmabery@gmail.com)
Date: 2026-07-12

Instrument: the owner explicitly requested a capability for the COS GitHub
App publisher transition, then approved the corrected issuance form after a
read-only authority audit identified an occupied transition ID and an
allow/deny contradiction.

The owner approved these corrections:

- preserve the existing, unrelated `origin/tr-0016` runner-lock WIP;
- carry capability issuance as `tr-0017` and bind the capability to publisher
  transition `tr-0018`;
- issue to `agent:claude-fable-5` for seven days;
- permit the capability's own exact file so current COS validators can carry
  the issuance, while leaving every other `capabilities/**` file outside the
  allowlist;
- keep `secrets/**` and `constitution/**` explicitly denied; and
- retain the requested action and publisher/governance target scope unchanged.

Scope ratified: `capabilities/cap-0002-publisher-transition.yaml` as carried
by `tr-0017`. This approval authorizes issuance and merge of the capability;
it does not itself authorize `tr-0018` to merge without its computed lane,
validation evidence, and required human review.

Enforcement note: under COS v0, `task_id`, `issued_for_office`, and
`allowed_actions` are documentary schema fields. The validators and write
gate enforce holder identity, validity window, and target paths. The exact
self-path is present only to carry this owner-approved issuance; any later
change to the capability remains elevated-risk and subject to the repository
PR, validation, and human-review gates.
