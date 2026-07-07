"""V2 -- Ledger integrity.

Append-only: prior ledger content is a byte prefix of the new content.
Exactly one event is appended per transition. Event ids are monotonic and
each appended event's `prev` links the previous event id.
"""
import sys

from cos_lib import appended_events, report


def run(base, head):
    failures = []
    old_ev, new_ev, prefix_ok = appended_events(base, head)

    if not prefix_ok:
        failures.append("ledger is not append-only: existing bytes were rewritten (forbidden: ledger_history_rewrite)")
        return report("validate_ledger", failures)

    if len(new_ev) != 1:
        failures.append(f"every transition appends exactly one ledger event; found {len(new_ev)}")

    last_old_id = old_ev[-1]["event_id"] if old_ev else None
    prev_id = last_old_id
    for ev in new_ev:
        eid = ev.get("event_id", "")
        if prev_id is not None and eid <= prev_id:
            failures.append(f"event_id {eid} is not monotonically greater than {prev_id}")
        if ev.get("prev") != prev_id:
            failures.append(f"event {eid} prev={ev.get('prev')!r}, expected {prev_id!r}")
        prev_id = eid

    return report("validate_ledger", failures)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
