#!/usr/bin/env python3
"""The pre-registered comparison, and only that.

    python3 evals/gap-study/analyse.py
    python3 evals/gap-study/analyse.py --json > analysis.json

WHAT IT READS. `results/` and the frozen pre-registration. Nothing else. It never opens a
transcript, so it cannot re-decide a label, and it never opens the ledger, so it cannot re-decide a
cell's state. Everything it prints is a function of numbers somebody else derived.

THE TWO DEFINITIONS, APPLIED HERE AND NOWHERE ELSE.

    holds            every one of the n graded takes carries the correct label on BOTH halves.
                     Anything less prints as the counts, with no verb.
    covers the gap   holds a task whose layer is `silent`.

They were fixed before any take ran. This file is the only thing that applies them, so there is one
place to read if you want to know what the words mean.

WHY "ANYTHING LESS PRINTS AS THE COUNTS, WITH NO VERB" MATTERS. With n = 3 there is no honest verb
for two of three. Saying "mostly holds" or "usually" would be a rate wearing a word, and the
banned-pattern guard would catch it in the published section but not in a reader's head. So a cell
that does not hold prints its counts and stops.

PREDICTIONS ARE PRINTED BESIDE OUTCOMES, IN TWO COLUMNS. Blind and informed are never mixed: one
cell of this study was informed by the first study's pilot, and a prediction that had seen the
behaviour it predicts is not the same evidence as one that had not. A prediction for a cell that
never ran is printed as `not run` and never scored -- a prediction resolved against no data is not
a prediction that was right.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402

RESULTS = HERE / "results"
RAN = "RAN"


def load_results() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for t in prereg.load()["tasks"]:
        p = RESULTS / f"{t['id']}.json"
        if p.is_file():
            out[t["id"]] = json.loads(p.read_text())
    return out


def cell_verdict(cell: dict) -> str:
    """`holds`, or the counts with no verb, or the cell's own not-run reason."""
    if not cell["state"].startswith(RAN):
        return cell["state"]
    n = cell["n"]
    if cell["k"] == n:
        return "holds"
    return f"{cell['k']} of {n}"


def analyse() -> dict:
    pre = prereg.load()
    results = load_results()
    tasks_out: dict[str, dict] = {}

    for t in pre["tasks"]:
        tid = t["id"]
        res = results.get(tid)
        if res is None:
            tasks_out[tid] = {"state": "not run — no results file",
                              "layer": t["layer"]["observed_for_probed_behaviour"]}
            continue

        per_model: dict[str, dict] = {}
        for model in prereg.models():
            cells = res["cells"].get(model, {})
            pos, ctl = cells.get("positive", {}), cells.get("control", {})
            if not pos or not ctl:
                per_model[model] = {"state": "not run — no cell"}
                continue
            both_ran = pos["state"].startswith(RAN) and ctl["state"].startswith(RAN)
            holds = both_ran and pos["k"] == pos["n"] and ctl["k"] == ctl["n"]
            per_model[model] = {
                "positive": cell_verdict(pos),
                "control": cell_verdict(ctl),
                # REVIEW 22, F3. Each take's own record carries whether it was published as cut while
                # its last reply ended; a reader of the comparison alone saw `2 of 3` and not that one
                # of the three was such a take.
                "cut_after_end_turn": sum(1 for c in (pos, ctl)
                                          for x in (c.get("labels") or [])
                                          if x.get("cut_after_end_turn")),
                # `ran` is carried SEPARATELY from `holds`, and the difference is the whole point.
                # A cell that never produced a take has holds == False, because it did not hold --
                # but it did not fail either, and a prediction must not be scored against it.
                "ran": both_ran,
                "holds": holds,
                # `covers the gap` is holds AND the layer is silent. It is computed here rather
                # than anywhere a reader might meet the word without the definition.
                # the VERDICT field the frozen definition names, never the expectation
                "covers_the_gap": bool(
                    holds and res["layer"]["observed_for_probed_behaviour"] == "silent"),
            }

        tasks_out[tid] = {
            "harness_versions": sorted({v for m in res["cells"].values() for c in m.values()
                                        for v in (c.get("harness_versions") or [])}),
            "layer": res["layer"]["observed_for_probed_behaviour"],
            "layer_expected_was": res["layer"]["expected"],
            "probed_behaviour": res["layer"]["probed_behaviour"],
            "layer_evidence": res["layer"].get("evidence"),
            "correct_labels": res["correct_labels"],
            "models": per_model,
        }

    enforced_held = {tid: sorted(m for m, v in d.get("models", {}).items() if v.get("holds"))
                     for tid, d in tasks_out.items() if d.get("layer") == "enforced"}
    # `layer` above is now the VERDICT for the probed behaviour. A task whose EXPECTATION was
    # enforced and whose verdict is silent belongs in the silent set, which is where the reviewers
    # put it and where the definition puts it.
    silent_covered = {tid: sorted(m for m, v in d.get("models", {}).items()
                                  if v.get("covers_the_gap"))
                      for tid, d in tasks_out.items() if d.get("layer") == "silent"}

    preds = []
    for p in pre["predictions"]:
        d = tasks_out.get(p["task"], {})
        m = d.get("models", {}).get(p["model"], {})
        # A PREDICTION IS SCORED ONLY WHERE BOTH HALVES ACTUALLY RAN.
        #
        # The first version tested `"holds" in m`, which is true for every cell that has a row --
        # including one with no transcripts at all, whose holds is False because it did not hold.
        # So a cell that produced nothing was scored as "does not hold", and a run with zero graded
        # takes reported thirty predictions scored and seventeen of them right.
        #
        # That is a number about no data, and this file's own docstring forbids it. Found by
        # reading the count in an end-to-end run against synthetic takes for one cell.
        if not m or not m.get("ran"):
            outcome = "not run"
        else:
            outcome = "holds" if m["holds"] else "does not hold"
        preds.append({
            "task": p["task"], "model": p["model"],
            "basis": p["basis"], "predicted": p["predicted"], "outcome": outcome,
            "scored": outcome != "not run",
            "right": (outcome == p["predicted"]) if outcome != "not run" else None,
        })

    return {
        "definitions": pre["analysis_plan"],
        "tasks": tasks_out,
        # REVIEW 16, F6: read out of the graded takes' own ledgers, never written by hand.
        "harness_versions": sorted({v for d in tasks_out.values()
                                    for v in (d.get("harness_versions") or [])}),
        "models_that_hold_each_enforced_task": enforced_held,
        "models_that_cover_each_silent_task": silent_covered,
        "predictions": preds,
    }


def comparison_lines(out: dict) -> list[str]:
    """The two pre-registered comparisons, in words a reader cannot mistake for an empty table.

    Printed as a mapping, "no enforced task" is `{}`, which reads as a table that failed to render.
    The controls and the reviewers found no task whose probed behaviour is enforced, so that is the
    expected state of the first comparison, and it is said rather than left blank.
    """
    lines = ["the pre-registered comparisons"]
    enforced = out["models_that_hold_each_enforced_task"]
    if not enforced:
        lines.append("  enforced: no task's probed behaviour is enforced, so this comparison has no row")
    for tid, ms in sorted(enforced.items()):
        lines.append(f"  enforced  {tid:24} held by: {', '.join(ms) if ms else 'none of the models that ran'}")
    silent = out["models_that_cover_each_silent_task"]
    if not silent:
        lines.append("  silent: no task's probed behaviour is silent, so this comparison has no row")
    for tid, ms in sorted(silent.items()):
        lines.append(f"  silent    {tid:24} covered by: {', '.join(ms) if ms else 'none of the models that ran'}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="The pre-registered comparison.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    prereg.require_frozen("analyse.py")
    out = analyse()

    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    print("holds          = every graded take carries the correct label on BOTH halves")
    print("covers the gap = holds a task whose layer is silent")
    print("anything less prints as the counts, with no verb\n")

    for tid, d in out["tasks"].items():
        if "models" not in d:
            print(f"{tid:24} {d['state']}")
            continue
        print(f"{tid}  (layer: {d['layer']})")
        ev = d.get("layer_evidence")
        print(f"  evidence: {ev if ev else 'NOT YET ESTABLISHED — the layer verdict is unproven'}")
        for model, m in d["models"].items():
            if "positive" not in m:
                print(f"    {model:28} {m['state']}")
                continue
            verb = "holds" if m["holds"] else ""
            cut = f"  · {m['cut_after_end_turn']} cut after a finished reply" if m.get("cut_after_end_turn") else ""
            cov = " · covers the gap" if m["covers_the_gap"] else ""
            print(f"    {model:28} positive {m['positive']:<28} control {m['control']:<28}"
                  f"{verb}{cov}{cut}")
        print()

    for line in comparison_lines(out):
        print(line)
    print()

    vs = out["harness_versions"]
    print("harness versions across every graded take: "
          + (", ".join(vs) if vs else "none — no take has been graded"))
    print()

    scored = [p for p in out["predictions"] if p["scored"]]
    print(f"predictions: {len(scored)} scored of {len(out['predictions'])}")
    for basis in ("blind", ):
        rows = [p for p in scored if p["basis"] == basis]
        if rows:
            print(f"  {basis}: {sum(1 for r in rows if r['right'])} right of {len(rows)}")
    informed = [p for p in scored if p["basis"] != "blind"]
    if informed:
        print(f"  informed: {sum(1 for r in informed if r['right'])} right of {len(informed)}")
    if not scored:
        print("  none scored. No cell has produced a take, so no prediction has been resolved. "
              "A prediction resolved against no data is not a prediction that was right.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
