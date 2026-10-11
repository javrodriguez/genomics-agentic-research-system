#!/usr/bin/env python3
"""The permission mode each session RECORDED, re-derived from its own transcript and held to the design.

    python3 evals/gap-study-3/mode_binding.py            what every committed attempt recorded
    python3 evals/gap-study-3/mode_binding.py --check    exit 1 on any drift from the pre-registration
    python3 evals/gap-study-3/mode_binding.py --walks    the same over the pre-freeze walks

WHY THIS FILE, AND NOT THE COPIED CHECKER. Round 2 passed `--permission-mode auto` to all three models and
wrote that constant into its ledgers. Its take checker then compared the ledger's copy of the constant with
the pre-registration's copy of the same constant -- a constant compared with itself, which no session could
ever fail. Reading round 2's own transcripts afterwards showed 34 of the smallest model's 36 recording
`default`, so the rule had been green over exactly the thing it was written to catch.

The checker is pinned byte-identical for this round, so the fix could not go there. It goes here.

WHAT IS ASSERTED. For every committed attempt: the mode its transcript records, re-derived HERE from the
transcript bytes rather than read out of the ledger, equals the value the pre-registration pins for that
attempt's model (`driver_constants.permission_mode_expected`). The ledger's own copy is compared with the
re-derivation as well, so a driver that recorded one thing and published another is caught rather than
trusted.

WHY THE EXPECTATION IS ONE VALUE (Ruling 7, 20 September 2026, superseding Ruling 2). Round 2 passed
`auto` and the smallest model recorded `default` anyway -- 34 of round 2's 36, and four of this round's four
walks -- so the axis carried two permission conditions. Ruling 2 answered that by making the expectation per
model, because one value would have routed every take of that model as a rehearsal. Ruling 7 removed the
reason instead: `default` is passed to every model, the allowlist is the whole permission surface, and one
value covers the axis. From there the COPIED checker carries the rule itself, because the driver writes the
recorded mode into the ledger field its constant-binding comparison reads. This file re-derives the same
reading from the transcript independently and routes nothing.

A SESSION IS HELD TO THE DESIGN IT WAS DRIVEN UNDER. A walk driven before the design pinned an expectation
is reported as superseded rather than graded: an anachronism is not a finding. It is named and counted, and
its leak verdict still stands, because which paths a session reads does not depend on the permission mode.

No model, no network, stdlib only. Read-only.

ROUND 4 (lane w6i, slice S6b, Q2; this file moved from lane w1a's copy record to lane w6i under glitch-1b's ruling
S6b-gap4-1). The expectation is the take's routing pin (ruling D1: routing.json's pin_profiles, the profile
batch.expected_pin hands the driver), keyed by the harness and the model the take ran, never by the model alone and
never one constant: a mode still PENDING (or absent) is never an expectation, so a take under it is a problem and
--check exits 1 naming it. The takes are read from round 4's take folders (TAKE_ROOTS); with none committed the
empty gate still prints that nothing was graded.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import routing  # noqa: E402
import study  # noqa: E402

# The same reading drive.py makes, spelled here independently: a re-derivation that imported the driver's
# reader would be checking the driver against itself.
ROOTS = ("transcripts", "rehearsals", "pauses")
# ROUND 4: the folders round 4's take records are committed under (drive.py's take_folder; named question Q-w6i-1:
# the production take_folder is not fixed yet, so this is the reading the plan supports, to be confirmed).
TAKE_ROOTS = ("takes",)
PENDING = "PENDING"


def modes_recorded(transcript: Path) -> set[str]:
    """Every value of the record-level `permissionMode` field, read from each JSON record and not by a
    pattern over the file's text (review 2, NIT). The field sits at the top of the harness's own user-type
    records; a tool result that echoed the same JSON would sit inside a record's content and is not read."""
    out: set[str] = set()
    try:
        lines = transcript.read_text(errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and isinstance(rec.get("permissionMode"), str):
            out.add(rec["permissionMode"])
    return out


def mode_precedence(modes: set[str]) -> str:
    """`default` when every record that carries the field says so; any other value wins over it;
    `unrecorded` when none carries it. REVIEW 3, NIT 6: under this round `default` is the expectation,
    so the anomaly is any other value, and a session that recorded one anywhere is read as it. Spelled
    here independently of the driver's reader, as the rest of this file is."""
    others = sorted(m for m in modes if m != "default")
    if others:
        return "auto" if "auto" in others else others[0]
    return "default" if "default" in modes else "unrecorded"


def mode_of(transcript: Path) -> str:
    return mode_precedence(modes_recorded(transcript))


def expected(table: dict | None = None) -> dict[tuple, str]:
    """ROUND 4 (Q2, D1): {(harness, model): the pinned permission mode} from routing.json's pin_profiles; a mode that
    is missing, empty or PENDING is kept as PENDING, which judge() never reads as an expectation."""
    t = routing.load_table() if table is None else table
    out: dict[tuple, str] = {}
    for harness, models in (t.get("pin_profiles") or {}).items():
        for model, profile in (models or {}).items():
            mode = (profile or {}).get("permission_mode")
            out[(harness, model)] = mode if isinstance(mode, str) and mode and mode != PENDING else PENDING
    return out


def attempts(walks: bool = False, base: Path | None = None) -> list[Path]:
    base = HERE if base is None else Path(base)
    if walks:
        return sorted((base / "walks").glob("*/*/transcript.jsonl")) if (base / "walks").is_dir() else []
    out: list[Path] = []
    for root in TAKE_ROOTS:
        folder = base / root
        if folder.is_dir():
            out += sorted(folder.rglob("transcript.jsonl"))
    return out


def judge(ledger: dict, derived: str, exp: dict, walks: bool) -> tuple[bool, list[str]]:
    """The whole per-session judgement, as a pure function of the ledger and the derived mode.

    Returned as (superseded, problems). It is a function rather than a branch inside the loop so the
    mutations that prove it can be driven on synthetic input instead of on committed evidence -- and so
    they keep biting when every committed session happens to be superseded, which is exactly the state
    that made two of them pass over nothing.
    """
    model = ledger.get("model_requested") or "?"
    harness = ledger.get("harness") or "?"
    if walks and ledger.get("permission_mode_expected") is None:
        return True, []
    want = exp.get((harness, model))           # ROUND 4 (Q2): keyed by the harness and the model the take ran
    problems = []
    if want is None:
        problems.append(f"routing.json pins no profile for {model!r} under harness {harness!r}")
    elif want == PENDING:
        problems.append(f"the pin for {model!r} under {harness!r} is PENDING; a pending mode is never an "
                        f"expectation")
    elif derived != want:
        problems.append(f"the session recorded {derived!r}; {model} under {harness} is pinned to record {want!r}")
    recorded = ledger.get("permission_mode_recorded")
    if recorded is not None and recorded != derived:
        problems.append(f"the ledger publishes {recorded!r} where the transcript records {derived!r}")
    # REVIEW 2, SHOULD. `permission_mode` is the field the copied checker reads, and this round's driver
    # writes the recorded mode into it too; an edit to that field alone left this check green.
    compared = ledger.get("permission_mode")
    if compared is not None and compared != derived:
        problems.append(f"the ledger's permission_mode, the field the copied checker reads, is "
                        f"{compared!r} where the transcript records {derived!r}")
    return False, problems


def rows(walks: bool = False, base: Path | None = None, table: dict | None = None) -> list[dict]:
    exp = expected(table)
    base = HERE if base is None else Path(base)
    out = []
    for t in attempts(walks, base):
        ledger_path = t.parent / "driver-ledger.json"
        ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {}
        model = ledger.get("model_requested") or "?"
        derived = mode_of(t)
        superseded, problems = judge(ledger, derived, exp, walks)
        recorded = ledger.get("permission_mode_recorded")
        out.append({
            "attempt": str(t.parent.relative_to(base)),
            "task": ledger.get("task"), "half": ledger.get("half"), "model": model,
            "harness": ledger.get("harness"),
            "passed": ledger.get("permission_mode_passed") or ledger.get("permission_mode"),
            "recorded": derived, "expected": None if superseded else exp.get((ledger.get("harness") or "?", model)),
            "ledger_agrees": recorded is None or recorded == derived,
            "superseded": superseded, "problems": problems,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--walks", action="store_true", help="grade the pre-freeze walks instead of the takes")
    args = ap.parse_args()
    got = rows(args.walks)
    what = "walk" if args.walks else "attempt"
    for r in got:
        flag = "  <-- " + "; ".join(r["problems"]) if r["problems"] else ""
        if r.get("superseded"):
            flag = "  <-- driven before the design pinned an expectation; superseded, not graded"
        print(f"  {r['attempt']:46} {str(r['model']):30} passed={r['passed']} "
              f"recorded={r['recorded']} expected={r['expected']}{flag}")
    bad = [r for r in got if r["problems"]]
    sup = [r for r in got if r.get("superseded")]
    if sup:
        print(f"\n{len(sup)} {what}(s) superseded: driven under a condition the design has since replaced, "
              f"named here and never silently dropped. Their leak verdicts still stand.")
    if not got:
        # An empty gate is said out loud. Nothing has been graded, and that is not a pass.
        print(f"ok, having graded 0 {what}s: none is committed yet, so nothing here is evidence about any "
              f"session's permission mode.")
        return 0
    if bad and args.check:
        print(f"\nFAIL {len(bad)} of {len(got)} {what}(s) drift from the pre-registration")
        return 1
    graded_n = len(got) - len(sup)
    if graded_n == 0:
        print(f"\nok, having graded 0 {what}s: all {len(got)} are superseded, so nothing here is evidence "
              f"about the condition now in force.")
        return 0
    print(f"\nok: {graded_n} {what}(s) graded, every one recording the mode its model is pinned to")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
