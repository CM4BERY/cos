# Threat model

COS v0 defends against **honest-but-fallible actors**: agents and humans who
make mistakes, lose context, drift out of scope, or forget procedure. It does
not contain adversarial actors. An agent with direct shell access can bypass
any in-process check by construction, so v0 places enforcement at the one
point such an actor cannot route around — the merge. All state changes are
enforced at merge time [locus: branch-protection] with CI as the policy
engine [locus: ci:cos-validate.yml].

Consequences of this model:

Risk class is computed from the diff and a self-declared class is never
trusted; a mismatch fails validation [locus: validators/validate_capability_scope.py].
Capability expiry is checked against recorded event timestamps rather than
wall-clock execution time, which is sound for fallible actors and unsound for
adversarial ones — a known, accepted limit of v0.

Side effects that produce no diff (shell commands, network calls, external
API writes) are outside v0's perimeter entirely. The v1 tool-mediation proxy
exists to close exactly this gap; until then, unattended agent operation
should be limited accordingly [locus: manual].

Adversarial containment is a different system — OS-level sandboxing and
mediated I/O — and is out of scope for v0 and v1 by design.
