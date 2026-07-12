# Human ruleset-mutation authorization — tr-0021

Mutator: `human:boss <coltonmabery@gmail.com>`, acting through GitHub account
`CMABERY`.

Repository: `CM4BERY/cos`

Ruleset: id `18642527`, active default-branch ruleset.

Authorization: `AUTHORIZED`, issued in-session on 2026-07-12 as part of the
ratified cap-0003 package.

## Forward mutation

Only the named human mutator may update the ruleset. The update is limited to
these two pull-request-rule fields:

```yaml
dismiss_stale_reviews_on_push: false -> true
require_last_push_approval: false -> true
```

The mutator must first confirm both preconditions are still `false`, capture
the complete before-state, preserve every other ruleset field, apply both
changes, and capture the complete after-state. The evidence is recorded at
`evidence/test_runs/tr-0021-ruleset-before-after.txt` before final validation
and owner-controlled App publication.

The forward mutation may occur only after `tr-0020` is merged, `tr-0021` is
otherwise ready for final evidence, and the owner-operated App authentication
smoke proves `cm4bery-cos-executor[bot]` can be the distinct final pusher.
`agent:codex` may perform read-only GETs but may not send the update.

## Provisional-state rollback

The hardened state remains provisional until `tr-0021` is approved and merged.
The named human mutator must restore only these two booleans to `false` if any
of the following occurs:

- final validator, harness, historical replay, or debt verification fails;
- the pull request is closed without merge;
- App publication cannot complete; or
- `tr-0021` is not approved and merged before
  `2026-07-15T14:20:47Z`, the capability expiry.

All other ruleset fields must remain unchanged. A complete GET after rollback
must be captured. If expiry or closure prevents that output from joining
`tr-0021`, it becomes mandatory input to the next owner-governed recovery
transition. The agent receives no forward or rollback mutation authority from
this artifact.
