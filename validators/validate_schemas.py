"""V3 -- Every governed record matches its schema.

capabilities/*.yaml, transitions/*.yaml, every ledger event, and any
governance/amendments/*.yaml are validated against schemas/.
"""
import json
import sys

import yaml
from jsonschema import Draft7Validator

from cos_lib import LEDGER, REPO, ledger_events, report


def _schema(name):
    return json.loads((REPO / "schemas" / name).read_text())


def _check(instance, validator, label, failures):
    errs = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    for e in errs:
        loc = "/".join(str(p) for p in e.path) or "<root>"
        failures.append(f"{label}: {loc}: {e.message}")


def run(base, head):
    failures = []
    pairs = [
        ("capabilities", "capability.schema.json"),
        ("transitions", "transition_request.schema.json"),
        ("governance/amendments", "amendment.schema.json"),
    ]
    for dirname, schema_name in pairs:
        d = REPO / dirname
        if not d.exists():
            continue
        v = Draft7Validator(_schema(schema_name))
        for f in sorted(d.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text())
            except yaml.YAMLError as e:
                failures.append(f"{f.relative_to(REPO)}: unparseable YAML: {e}")
                continue
            _check(data, v, str(f.relative_to(REPO)), failures)

    ledger_path = REPO / LEDGER
    if ledger_path.exists():
        v = Draft7Validator(_schema("ledger_event.schema.json"))
        try:
            for i, ev in enumerate(ledger_events(ledger_path.read_text()), 1):
                _check(ev, v, f"{LEDGER}:{i}", failures)
        except json.JSONDecodeError as e:
            failures.append(f"{LEDGER}: unparseable line: {e}")
    else:
        failures.append(f"{LEDGER} does not exist")

    return report("validate_schemas", failures)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
