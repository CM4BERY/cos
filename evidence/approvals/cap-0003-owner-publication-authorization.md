# Owner-controlled publication authorization — tr-0020 and tr-0021

Authorizer: `human:boss <coltonmabery@gmail.com>`

Authorized tr-0020 invoker: `agent:codex`, limited as stated below.

Authorized tr-0021 invoker: `human:boss` only.

Technical publisher: `cm4bery-cos-executor[bot]`, GitHub App id `4278642`,
installation id `146047322`.

Reviewer and merger: GitHub account `CMABERY`.

Authorization: `AUTHORIZED`, issued in-session on 2026-07-12 as part of the
ratified cap-0003 package and narrowed by a later direct in-session owner
instruction for the tr-0020 invocation only.

## Permitted publication acts

For `tr-0020` only, the human owner directly authorizes `agent:codex` to run
the exact App authentication smoke and then invoke `cos_ship` for the frozen,
revalidated candidate. The permitted acts are limited to authenticating App id
`4278642` at installation id `146047322`, pushing branch `tr-0020`, creating or
resuming its draft pull request against `CM4BERY/cos:main`, and observing the
required checks. The App must stop before merge.

This exception does not authorize `agent:codex` to publish `tr-0021`, merge,
use an administrator or ruleset bypass, mutate a ruleset, publish another
branch, or make repository-file changes after the final push. `human:boss`
remains the only authorized App invoker for `tr-0021`.

## Preconditions and reviewer sequence

1. The tr-0020 candidate is re-frozen, committed, and freshly validated after
   this operator exception is recorded.
2. `agent:codex` runs the App authentication smoke under the direct owner
   authorization above. If exact App, installation, repository, and permission
   scope do not pass, publication stops.
3. The App is the final pusher and pull-request author.
4. `CMABERY`, distinct from the App identity, reviews the exact latest push and
   completes the squash merge only after the required `validate` check passes.
5. Any later push requires a fresh `CMABERY` review.

`tr-0020` must merge before `tr-0021` is scaffolded or edited. This tr-0020
exception expires when its draft PR is created and checks have been observed;
it does not carry forward to any retry that changes the candidate. For `tr-0021`,
the final ruleset after-state evidence must be added and final verification
must pass before the App's final push. No repository file may change after
that push without repeating the App-push and human-review sequence.

This authorization does not permit the App to bypass ruleset 18642527, merge
as administrator, change repository settings, or publish any other branch or
transition.
