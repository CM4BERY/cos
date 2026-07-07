"""COS gateway entry point: run all five validators against a diff.

Usage:
  python validators/run_all.py --base <ref|GENESIS> [--head <ref|WORKTREE>]

WORKTREE validates the index -- run `git add -A` first.
"""
import argparse
import sys

import validate_capability_scope
import validate_enforcement_claims
import validate_ledger
import validate_no_self_approval
import validate_schemas

VALIDATORS = [
    validate_ledger,             # V2: append-only, one event per transition
    validate_schemas,            # V3: every governed record matches schema
    validate_capability_scope,   # V1: scope, expiry, computed risk, artifacts
    validate_enforcement_claims, # V4: no rule without a locus
    validate_no_self_approval,   # V5: no self-issued authority
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args()

    print(f"cos-validate: base={args.base} head={args.head}")
    rc = 0
    for v in VALIDATORS:
        rc |= v.run(args.base, args.head)
    print("RESULT:", "ALL PASS -- transition may commit" if rc == 0
          else "FAIL -- transition is denied")
    return rc


if __name__ == "__main__":
    sys.exit(main())
