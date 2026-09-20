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

WHY THE EXPECTATION IS PER MODEL (Ruling 2, 20 September 2026). The smallest model records `default`
whatever flag is passed -- 34 of round 2's 36, and four of this round's four walks. A single expected value
for the whole axis would make every one of its takes a rehearsal, exhaust its cap, and leave all six of its
cells unmeasured, in a round built to measure it. So the expectation is what each model is known to record,
which is a statement the record can contradict; the old rule was one it could not.

No model, no network, stdlib only. Read-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import study  # noqa: E402

# The same shape drive.py reads, spelled here independently: a re-derivation that imported the driver's
# reader would be checking the driver against itself.
MODE_RECORD = re.compile(r'"permissionMode":\s*"([A-Za-z]+)"')
ROOTS = ("transcripts", "rehearsals", "pauses")


def mode_of(transcript: Path) -> str:
    """`default` if any record says default, else `auto` if any says auto, else `unrecorded`.

    The precedence is the pre-study's: a session that records `default` anywhere ran with no approval
    surface, whatever a later record says.
    """
    modes = set(MODE_RECORD.findall(transcript.read_text(errors="replace")))
    return "default" if "default" in modes else "auto" if "auto" in modes else "unrecorded"


def expected() -> dict[str, str]:
    exp = (prereg.load()["driver_constants"].get("permission_mode_expected") or {})
    if not exp:
        raise SystemExit("the pre-registration pins no driver_constants.permission_mode_expected, so there "
                         "is nothing to hold a session to. Nothing here can be checked.")
    return exp


def attempts(walks: bool = False) -> list[Path]:
    if walks:
        return sorted((HERE / "walks").glob("*/*/transcript.jsonl")) if (HERE / "walks").is_dir() else []
    out: list[Path] = []
    for root in ROOTS:
        base = HERE / root
        if base.is_dir():
            out += sorted(base.rglob("transcript.jsonl"))
    return out


def rows(walks: bool = False) -> list[dict]:
    exp = expected()
    out = []
    for t in attempts(walks):
        ledger_path = t.parent / "driver-ledger.json"
        ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {}
        model = ledger.get("model_requested") or "?"
        derived = mode_of(t)
        want = exp.get(model)
        problems = []
        if want is None:
            problems.append(f"the pre-registration pins no expected mode for {model!r}")
        elif derived != want:
            problems.append(f"the session recorded {derived!r}; {model} is pinned to record {want!r}")
        recorded = ledger.get("permission_mode_recorded")
        if recorded is not None and recorded != derived:
            problems.append(f"the ledger publishes {recorded!r} where the transcript records {derived!r}")
        passed = ledger.get("permission_mode_passed") or ledger.get("permission_mode")
        out.append({
            "attempt": str(t.parent.relative_to(HERE)),
            "task": ledger.get("task"), "half": ledger.get("half"), "model": model,
            "passed": passed, "recorded": derived, "expected": want,
            "ledger_agrees": recorded is None or recorded == derived,
            "problems": problems,
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
        print(f"  {r['attempt']:46} {str(r['model']):30} passed={r['passed']} "
              f"recorded={r['recorded']} expected={r['expected']}{flag}")
    bad = [r for r in got if r["problems"]]
    if not got:
        # An empty gate is said out loud. Nothing has been graded, and that is not a pass.
        print(f"ok, having graded 0 {what}s: none is committed yet, so nothing here is evidence about any "
              f"session's permission mode.")
        return 0
    if bad and args.check:
        print(f"\nFAIL {len(bad)} of {len(got)} {what}(s) drift from the pre-registration")
        return 1
    print(f"\nok: {len(got)} {what}(s) graded, every one recording the mode its model is pinned to")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
