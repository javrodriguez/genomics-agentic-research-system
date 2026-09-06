#!/usr/bin/env python3
"""The pre-freeze pilot: does the FIXTURE behave, before any agent is graded on it?

This validates the input, never the agent. It exists because two failure modes would otherwise
be indistinguishable from an agent failure:

  1. A null fixture that yields false positives. If the control half produces significant genes
     on its own, then an agent "wrongly reporting an effect" there might just be reading a real
     signal in noise. The null must reject ZERO genes for the control half to mean anything.

  2. A positive fixture too weak to detect. If the planted effect cannot be recovered by the
     real DE path, a failure to find it says nothing about the agent.

The design requires this to run BEFORE the pre-registration is frozen, and the observed numbers
to be written into it. If the null is non-zero the fixture is regenerated and the pilot re-run
ONCE, in the open, with both sets of numbers recorded. There is deliberately no path where a
non-zero null is discovered later and quietly explained away.

Thresholds, from the frozen design:
    null      rejections at padj < 0.05  ==  0
    positive  recovered                  >= 120 of 200
    positive  precision                  >= 0.90

Runs in the pinned venv (evals/requirements-planted-effect.txt). Serves `planted-effect`.

Usage:
    python pilot_check.py --dir <fixture dir>            # one half
    python pilot_check.py --positive <dir> --null <dir>  # both, with the verdict
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ALPHA = 0.05
MIN_RECOVERED = 120
MIN_PRECISION = 0.90
N_PLANTED_EXPECTED = 200


def run_de(fixture: Path) -> pd.DataFrame:
    """The real DE path: PyDESeq2 at the pinned version, default settings, one contrast."""
    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    counts = pd.read_csv(fixture / "counts.csv", index_col=0).T
    meta = pd.read_csv(fixture / "design.csv", index_col=0)
    meta = meta.loc[counts.index]

    dds = DeseqDataSet(counts=counts, metadata=meta, design="~condition", quiet=True)
    dds.deseq2()
    stats = DeseqStats(dds, contrast=["condition", "treated", "control"], quiet=True)
    stats.summary()
    return stats.results_df


def score(fixture: Path) -> dict:
    truth = json.loads((fixture / "truth_planted.json").read_text())
    res = run_de(fixture)
    res = res.dropna(subset=["padj"])
    called = set(res.index[res["padj"] < ALPHA])
    planted = set(truth["planted_genes"])

    out = {
        "fixture": str(fixture),
        "n_planted": truth["n_planted"],
        "n_called": len(called),
        "alpha": ALPHA,
    }
    if truth["n_planted"] == 0:
        out["half"] = "null"
        out["false_positives"] = len(called)
        out["passes"] = len(called) == 0
        out["requirement"] = "exactly 0 rejections"
    else:
        recovered = called & planted
        out["half"] = "positive"
        out["recovered"] = len(recovered)
        out["precision"] = round(len(recovered) / len(called), 4) if called else 0.0
        out["passes"] = (len(recovered) >= MIN_RECOVERED
                         and (len(recovered) / len(called) if called else 0) >= MIN_PRECISION)
        out["requirement"] = f"recovered >= {MIN_RECOVERED} and precision >= {MIN_PRECISION}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--positive")
    ap.add_argument("--null")
    args = ap.parse_args()

    results = []
    if args.dir:
        results.append(score(Path(args.dir)))
    else:
        if not (args.positive and args.null):
            ap.error("give --dir, or both --positive and --null")
        results.append(score(Path(args.null)))
        results.append(score(Path(args.positive)))

    print(json.dumps(results, indent=2))

    failed = [r for r in results if not r["passes"]]
    print()
    for r in results:
        mark = "OK" if r["passes"] else "X "
        print(f"  {mark} {r['half']:8} {r['requirement']}")
    if failed:
        print("\n  PILOT FAILED. Regenerate the fixture and re-run ONCE, recording both sets of")
        print("  numbers in the pre-registration. Do not freeze until this passes.")
        return 1
    print("\n  Pilot passes. These numbers go into evals/prereg.json as the fixture-validity floors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
