# Human ratification — revoke cap-0002-publisher-transition

Ratifier: Boss (human owner, coltonmabery@gmail.com)
Date: 2026-07-12

Instrument: after `tr-0018` merged and local `main` synchronized, the owner
was advised to revoke `cap-0002-publisher-transition` rather than leave its
seven-day target authority active until 2026-07-19. The owner explicitly
directed: “proceed.”

Scope ratified: transition `tr-0019` may shorten the capability's
`expires_at` to the exact `evt-0019` timestamp and annotate the completed
revocation. The capability is not deleted because the ledger event must retain
an auditable instrument to reference. No target, action, beneficiary, issuer,
or denial is broadened.

This approval authorizes publication and merge of the revocation after the
computed high-risk requirements pass. It does not authorize reactivation by
revert; any future authority requires a newly issued capability.
