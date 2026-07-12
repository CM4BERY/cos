# A-0002 simulation — publisher identity separation

Date: 2026-07-12
Amendment: `governance/amendments/A-0002.yaml`
Target rule: `policy/navigation.yaml`

## Problem grounded in the ledger

- `evt-0003` carried `.github/CODEOWNERS` with `@CM4BERY`, conflating the
  organization owner with the human reviewer account `@CMABERY`.
- `evt-0008` installed a navigation layer pinned to the human account. That
  made the publisher and intended reviewer the same GitHub identity.
- `evt-0010` moved high and critical lanes to human review but left low and
  medium lanes on the publisher's admin-merge path.
- `evt-0017` recorded the owner's narrow capability for this transition. Its
  App-authored PR was approved by the human account and normally merged,
  demonstrating that the separated identities are usable without bypass.

Governance debt was `GOVERNANCE DEBT: OK (0 breaches)` before scaffolding
`tr-0018`; this amendment addresses an identity/design defect, not an attempt
to excuse existing debt.

## Replay against recorded history

| Event | Recorded outcome | Outcome under A-0002 |
|---|---|---|
| `evt-0003` / `tr-0002` | High, human review; protected scopes named `@CM4BERY` | Risk decision unchanged; the protected reviewer becomes the valid human account `@CMABERY`. |
| `evt-0008` / `tr-0007` | High, human-reviewed navigation layer; publisher pinned to `CMABERY` | Risk decision unchanged; the PR publisher would be `cm4bery-cos-executor[bot]`, leaving `CMABERY` eligible to review. |
| `evt-0009` / `tr-0008` | Medium, autonomous merge path | Changed: App opens a draft PR and stops after checks for human review. |
| `evt-0010` / `tr-0009` | High, review mode | Merge decision unchanged; publisher identity becomes the App and no bypass path exists. |
| `evt-0013` / `tr-0012` | Medium, autonomous merge path | Changed: draft PR plus human review replaces admin auto-merge. |
| `evt-0016` / `tr-0015` | Low, autonomous merge path | Changed: draft PR plus human review replaces admin auto-merge. |
| `evt-0017` / `tr-0017` | High, App-authored and human-approved | Same review outcome; this is the live feasibility example for the amended identity model. |

The replay changes outcomes for low and medium history, so the amendment is
substantive. It also repairs the CODEOWNER identity without changing the
computed risk classes of earlier events.

## Expected effect and beneficiaries

- `cm4bery-cos-executor[bot]`, executor: gains only branch/PR publication
  through an installation token whose exact repository and permission set is
  checked before use.
- `CMABERY`, human root and CODEOWNER: gains a structurally distinct review
  role for every App-authored PR.
- `CM4BERY/cos`, governed repository: gains audit attribution, short-lived
  credentials, draft-first publication, and removal of the publisher's
  admin-merge path.
- Other organization repositories and actors: no new access or authority.

Authority-expansion statement: A-0002 grants publication authority to
`cm4bery-cos-executor[bot]`; the beneficiary does not approve it, and
`CMABERY` is the distinct human approver and reviewer.

## External-state boundary

The App installation already exists outside repository state and is limited
to `CM4BERY/cos`. A-0002 does not edit workflows, organization settings,
rulesets, or bypass actors. Reverting `tr-0018` stops repository code from
using the App; the separately governed installation can then be suspended or
removed by the human owner if desired.
