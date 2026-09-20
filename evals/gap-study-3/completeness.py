#!/usr/bin/env python3
"""Every planned cell is complete, or published unmeasured with its reason. There is no third state.

    python3 evals/gap-study-3/completeness.py            what state each planned cell is in
    python3 evals/gap-study-3/completeness.py --check    exit 1 if any cell is neither

WHY THIS IS A FILE AND NOT A SENTENCE IN THE RESULT. The pressure at the end of a round is to publish the
cells that came out and say nothing about the ones that did not, and the result of that reads as a smaller
study that went well. Every cell the frozen design PLANNED is enumerated here from the frozen file, not
from what is on disk, so a cell cannot go missing by not being written: the plan is the denominator.

A cell is complete when it holds its full complement of graded takes. Otherwise it is unmeasured, and
unmeasured is only a legal state WITH a reason that names what happened -- capped with its rehearsal
reasons, a partial count, or never run. A cell that is neither is this check's whole point.

No model, no network, stdlib only. Read-only.
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
import result  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rec = result.derive()
    if args.json:
        print(json.dumps(rec["cells"], indent=2))
    else:
        for c in rec["cells"]:
            mark = "complete" if c["state"] == "complete" else f"unmeasured — {c['reason']}"
            print(f"  {c['task']:20} {c['half']:9} {c['model']:30} {c['graded']} of {c['n']}   {mark}")

    planned = rec["planned_cells"]
    complete = rec["complete_cells"]
    nameless = [c for c in rec["cells"] if c["state"] != "complete" and not c["reason"]]
    unmeasured = [c for c in rec["cells"] if c["state"] != "complete"]

    print(f"\ncomplete cells {complete} of {planned}; "
          f"{len(unmeasured)} unmeasured, every one of them named with a reason"
          if not nameless else
          f"\ncomplete cells {complete} of {planned}; {len(nameless)} unmeasured cell(s) name no reason")

    if planned == 0:
        # An empty gate is said out loud: the frozen design plans no cell, so this has graded nothing.
        print("ok, having graded 0 cells: the design plans none, so this check is evidence about nothing.")
        return 1 if args.check else 0

    if not prereg.is_frozen():
        print("not applicable — not frozen. The denominator is the frozen plan, and there is not one yet, "
              "so this green claims nothing about any cell.")
        return 0

    if nameless:
        for c in nameless:
            print(f"FAIL {c['task']}/{c['half']}/{c['model']} is neither complete nor published unmeasured "
                  f"with a reason")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
