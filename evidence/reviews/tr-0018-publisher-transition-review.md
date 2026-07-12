# Independent transition audit — tr-0018

Reviewer: `agent:codex-transition-auditor` (read-only subagent, distinct from
beneficiary `agent:claude-fable-5` and App publisher
`cm4bery-cos-executor[bot]`)

Date: 2026-07-12
Base: `origin/main` at
`263f408e57f08119bc6dc3cced5c363ba7b3c562`
Reviewed substantive-file digest (SHA-256):
`5eca0c8b4dba69d016d43bc8afaf234f2449d9f6f67bc40eabef87f2693eebae`

Digest input: sorted relative path, NUL, file bytes, NUL for the twelve
substantive files below. The transition record, ledger tail, this review, and
final validation output are protocol tail files and are excluded.

- `.github/CODEOWNERS`
- `docs/navigation-layer.md`
- `docs/status.md`
- `evidence/simulations/tr-0018-publisher-identity.md`
- `evidence/test_runs/tr-0018-app-auth-smoke.txt`
- `evidence/test_runs/tr-0018-hook-harness.txt`
- `evidence/test_runs/tr-0018-ruleset-audit.txt`
- `governance/amendments/A-0002.yaml`
- `policy/enforcement_loci.yaml`
- `policy/navigation.yaml`
- `tools/cos_ship.py`
- `tools/test_hooks.sh`

## Verdict

**READY. No remaining high or medium findings.**

## Findings resolved during review

1. Existing-PR resume now verifies the configured App author, draft state,
   base `main`, exact transition head, repository owner, and repository name.
   Positive and six negative resume fixtures fail closed.
2. Read-only ruleset evidence records an active default-branch pull-request
   rule with one approval, CODEOWNER review, the `validate` status check, and
   no Integration/GitHub App bypass actor. The App id is absent from bypass
   actors; the existing RepositoryRole bypass remains external administration.
3. A-0002 now contains literal prior and proposed `policy/navigation.yaml`
   blocks, including App/installation ids, key path, API version, repository
   selection, exact permissions, draft policy, no-admin-merge policy, and all
   four review lanes.
4. The harness covers JWT claims/lifetime, exact App/install/repository/
   permission scope, scope-failure revocation, success and action-exception
   revocation, terminal revocation failure, process-local gh/Git credential
   propagation, and resume invariants.

## Additional checks

- Every reviewed changed path is declared by `tr-0018` and covered by
  `cap-0002-publisher-transition`.
- No PEM, private key, or actual token value appears in the inspected diff or
  evidence; no `.pem` or `.key` file exists in repository state.
- Git configuration remains unchanged; the HTTPS rewrite and Authorization
  header exist only in child-process environments.
- `git diff --check` is clean.

The auditor was read-only and did not run network calls, mint tokens, change
Git state, rerun the harness, or rerun validators. The main executor records
those independently observed results in the test and validation evidence.

Authority-expansion statement: publication authority benefits
`cm4bery-cos-executor[bot]`; approval remains with the distinct human
`CMABERY`, and the App is not its own reviewer or a ruleset bypass actor.
