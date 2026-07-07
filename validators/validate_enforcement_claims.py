"""V4 -- No normative claim without an enforcement locus.

Markdown files (outside evidence/) that use must/required/enforced/validated
need a [locus: ...] tag on the same line pointing at a repo path or a known
mechanism. Files may declare `<!-- cos:locus-exempt-file -->` (reported as a
visible warning -- exemptions are never silent). Also checks that every risk
class and forbidden rule in policy/risk_model.yaml has a resolvable entry in
policy/enforcement_loci.yaml.
"""
import re
import sys

from cos_lib import REPO, load_yaml, report

TRIGGER = re.compile(r"\b(must|required|enforced|validated)\b", re.IGNORECASE)
LOCUS_TAG = re.compile(r"\[locus:\s*([^\]]+)\]")
KNOWN_MECHANISMS = {"branch-protection", "codeowners", "human-approval", "manual", "git"}
EXEMPT_MARKER = "cos:locus-exempt-file"


def _locus_ok(locus):
    for item in (x.strip() for x in locus.split(",")):
        if item.split(":")[0] in KNOWN_MECHANISMS:
            continue
        if item.startswith("ci:"):
            if not (REPO / ".github" / "workflows" / item[3:]).exists():
                return False, item
            continue
        if not (REPO / item).exists():
            return False, item
    return True, None


def run(base, head):
    failures, warnings = [], []

    for md in sorted(REPO.rglob("*.md")):
        rel = md.relative_to(REPO).as_posix()
        if rel.startswith("evidence/") or rel.startswith(".git/"):
            continue
        text = md.read_text()
        if EXEMPT_MARKER in text:
            warnings.append(f"{rel}: locus-exempt file (non-normative by declaration)")
            continue
        in_fence = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or not TRIGGER.search(line):
                continue
            m = LOCUS_TAG.search(line)
            if not m:
                failures.append(f"{rel}:{n}: normative claim without [locus: ...] tag")
                continue
            ok, bad = _locus_ok(m.group(1))
            if not ok:
                failures.append(f"{rel}:{n}: locus does not resolve: {bad!r}")

    risk_model = load_yaml("policy/risk_model.yaml")
    loci = load_yaml("policy/enforcement_loci.yaml")
    for rc in risk_model.get("risk_classes", {}):
        entries = (loci.get("risk_classes") or {}).get(rc)
        if not entries:
            failures.append(f"enforcement_loci.yaml: no locus for risk class {rc!r}")
            continue
        for item in entries:
            ok, bad = _locus_ok(item)
            if not ok:
                failures.append(f"enforcement_loci.yaml: risk class {rc!r}: locus does not resolve: {bad!r}")
    for rule in risk_model.get("forbidden", []):
        entries = (loci.get("forbidden") or {}).get(rule)
        if not entries:
            failures.append(f"enforcement_loci.yaml: no locus for forbidden rule {rule!r}")
            continue
        for item in entries:
            ok, bad = _locus_ok(item)
            if not ok:
                failures.append(f"enforcement_loci.yaml: forbidden rule {rule!r}: locus does not resolve: {bad!r}")

    return report("validate_enforcement_claims", failures, warnings)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
