#!/usr/bin/env python3
"""Every committed vendor walk's native cross-check re-derived from its own committed bytes, never taken from its ledger.

    python3 evals/gap-study-4/walk_native_cross.py --check     exit 1 on any walk whose re-derived cross-check is not
                                                               the one its driver ledger records, each named

Pre-freeze review 2, m16 (FOLD-PLAN-prefreeze-2.md section 3, lane fold2-ld, Thu 29 Oct 2026, under Javier's
delegation to glitch-45). run.grade_walk and walk_regrade.recheck_doc take a vendor walk's native cross-check from its
driver ledger's cross_check_status when that is not pending, so for the Codex walks committed agreed (the 36 that cover
arm O) no gate re-derived it; the reviewer re-derived all 74 Codex walks by hand and found every one agreed. This gate
does it on every run: for each walk rehearsals/register.json lists, read at HEAD (walk_regrade.materialize_walk, the one
road a regrade reads a walk by), whose driver ledger names a codex or gemini harness and a cross_check_status that is
not pending, it calls the same join the driver ran (drive.codex_cross_check or drive.gemini_cross_check, with the
ledger's own snapshot references, exits, sent lines and requested model, as walk_regrade.regrade_doc calls them)
through the accepted reader registry (native_reader_registration.production_readers), and requires the result to equal
the ledger's record exactly. No reader source is read or edited here: the readers are called.

A pending walk is walk_regrade's (its regrade.json re-derives there) and is counted, not read. A walk whose recorded
native_history did not join never ran the join in the driver (drive.vendor_cross_check_status), so the gate does not
run it either: its ledger status must equal vendor_cross_check_status of that recorded history (review of 4928c592,
MINOR 2; the 36 agreed Codex walks all record a joined history, so the joins re-derived are the same). A claude-code walk has no
native cross-check. A vendor ledger with no cross_check_status is named. The gate prints what it re-derived and refuses
a run that re-derived nothing while vendor walks stand (a vacuous green).

No model, no network, no container; stdlib and git only. Read-only.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import drive  # noqa: E402
import mode_binding  # noqa: E402
import native_reader_registration as nrr  # noqa: E402
import pending_walk  # noqa: E402
import walk_register  # noqa: E402
import walk_regrade  # noqa: E402

VENDOR = ("codex", "gemini")


def rederive(harness: str, base: Path, ledger: dict, readers) -> dict:
    """The walk's native cross-check, through the driver's own join over the walk folder `base`."""
    refs = list(ledger.get("native_snapshots") or [])
    if harness == "gemini":
        return drive.gemini_cross_check(base, refs, len(ledger.get("streams") or []), readers=readers)
    turns = ledger.get("turns") or []
    return drive.codex_cross_check(base, refs, [t.get("exit") for t in turns], sent=[t.get("sent") for t in turns],
                                   model=ledger.get("model_requested"), readers=readers)


def walk_problem(walk: str, base, *, readers, cross=None) -> tuple:
    """(problem or None, what was done: "rederived", "pending", "not-joined", "not-vendor" or "unread") for one walk
    folder.
    `readers` None is the production registry; `cross(harness, base, ledger, readers)` stands in for rederive (tests)."""
    base = Path(base)
    try:
        ledger = json.loads((base / "driver-ledger.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return f"walk {walk!r}: its driver ledger cannot be read: {type(e).__name__}: {e}", "unread"
    harness = (ledger.get("agent") or {}).get("harness") if isinstance(ledger, dict) else None
    if harness not in VENDOR:
        return None, "not-vendor"
    if "cross_check_status" not in ledger:
        return f"walk {walk!r}: a {harness} driver ledger records no cross_check_status", "unread"
    if pending_walk.status(ledger) is not None:
        return None, "pending"
    history = ledger.get("native_history")
    if not (isinstance(history, dict) and history.get("status") == "joined"):
        # review of 4928c592, MINOR 2: the driver ran the join only on a joined native history (drive.py 2613-2620);
        # otherwise the ledger's status is vendor_cross_check_status of that recorded history, and that is what is read
        want, got = ledger["cross_check_status"], None
        try:
            got = drive.vendor_cross_check_status(harness, history, None)
        except (TypeError, KeyError, drive.DriveRefused) as e:
            return f"walk {walk!r}: its recorded native history cannot be read: {type(e).__name__}: {e}", "not-joined"
        if got != want:
            return (f"walk {walk!r}: its native history did not join ({history!r}) and its ledger records the "
                    f"cross-check {want!r}, not {got!r}"), "not-joined"
        return None, "not-joined"
    if readers is None:
        try:
            readers = nrr.production_readers()
        except nrr.RegistrationRefused as e:
            return f"walk {walk!r}: the reader registration refuses: {e}", "unread"
    got = (rederive if cross is None else cross)(harness, base, ledger, readers)
    want = ledger["cross_check_status"]
    if got != want:
        return (f"walk {walk!r}: its driver ledger records the native cross-check {want!r}; re-derived from its "
                f"committed bytes it is {got!r}"), "rederived"
    return None, "rederived"


def report(study: Path = HERE, *, readers=None) -> tuple:
    """(problems, counts) over every registered walk at HEAD; counts {walks, vendor, rederived, pending}."""
    study = Path(study)
    counts = {"walks": 0, "vendor": 0, "rederived": 0, "pending": 0, "not-joined": 0}
    root, prefix = nrr._repo(study)
    if root is None:
        return [f"{study} is not inside a git repository: the walks are read as committed"], counts
    out = []
    for entry in walk_register.registered(study / mode_binding.WALKS_DIR):
        walk = entry["walk"]
        counts["walks"] += 1
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / walk
            try:
                walk_regrade.materialize_walk(root, nrr._rel(prefix, f"{mode_binding.WALKS_DIR}/{walk}"), base)
            except walk_regrade.RegradeRefused as e:
                out.append(f"walk {walk!r}: cannot be read at HEAD: {e}")
                continue
            if not (base / "driver-ledger.json").is_file():
                continue                           # died before turn 1: no ledger, no cross-check (run.grade_walk D3)
            problem, done = walk_problem(walk, base, readers=readers)
        if done != "not-vendor":
            counts["vendor"] += 1
        if done in ("rederived", "pending", "not-joined"):
            counts[done] += 1
        if problem:
            out.append(problem)
    return out, counts


def gate_problems(problems: list, counts: dict) -> list:
    out = list(problems)
    if counts["vendor"] and not (counts["rederived"] or counts["pending"] or counts.get("not-joined")):
        out.append(f"{counts['vendor']} vendor walk(s) are committed and no native cross-check was re-derived: not a "
                   f"pass")
    return out


def counts_line(counts: dict) -> str:
    return (f"re-derived {counts['rederived']} native cross-check(s) of {counts['vendor']} vendor walk(s), over "
            f"{counts['walks']} registered walk(s); {counts['pending']} pending (walk_regrade.py's); "
            f"{counts.get('not-joined', 0)} whose native history did not join, read by its recorded status")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", required=True)
    ap.parse_args(argv)
    problems, counts = report()
    bad = gate_problems(problems, counts)
    for b in bad:
        print(f"walk_native_cross: FAIL {b}")
    print("walk_native_cross: " + counts_line(counts))
    print("walk_native_cross: ok" if not bad else f"walk_native_cross: {len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
