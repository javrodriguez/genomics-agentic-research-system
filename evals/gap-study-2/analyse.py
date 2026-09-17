#!/usr/bin/env python3
"""The pre-registered comparison, and only that.

    python3 evals/gap-study-2/analyse.py
    python3 evals/gap-study-2/analyse.py --json > analysis.json

WHAT IT READS. `results/`, the frozen pre-registration, and for the round-1-beside-round-2
comparison, round 1's published results and the committed regrade records under
`verification/round1-regrade/`, as data. Nothing else. It never opens a transcript, so it cannot
re-decide a label, and it never opens the ledger, so it cannot re-decide a cell's state. Everything
it prints is a function of numbers somebody else derived.

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

THE ROUND-1-BESIDE-ROUND-2 COMPARISON (amendment 9). The frozen plan names two tasks whose
instrument round 2 fixed, and asks for round 1's published `k of n` per half beside round 2's, under
one heading, with no sentence comparing them. Three columns per row: round 1 as published (round 1's
results file), round 1's takes under round 2's instrument (the regrade record's per-take verdicts,
counted), and round 2 (this study's results file, in the published cell's spelling). The rows are
printed and carried in the JSON; the heading is the plan's, read from it, never typed here.

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


# ROUND 2, CP4. The order the reserved counts are printed in, fixed so a published cell has one spelling.
RESERVED_PRINT_ORDER = ("did-not-reach", "asked-to-proceed", "timed-out", "aborted")


def reserved_counts(cell: dict) -> dict[str, int]:
    """How many of the cell's graded takes carry each reserved label, in the fixed order, zeros kept."""
    got = [lab.get("label") for lab in (cell.get("labels") or [])]
    return {name: got.count(name) for name in RESERVED_PRINT_ORDER}


def published_cell(cell: dict) -> str:
    """The cell as the published table prints it: `k of n`, then each non-zero reserved count in the fixed order.

    The one spelling of a cell. The published-table check reads it from here, so a reserved count the table
    omits cannot pass as `k of n` alone.
    """
    parts = [f"{cell['k']} of {cell['n']}"]
    parts += [f"{c} {name}" for name, c in reserved_counts(cell).items() if c]
    return ", ".join(parts)


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
                # ROUND 2, CP4: each half's reserved labels counted, asked-to-proceed beside did-not-reach.
                "reserved_counts": {"positive": reserved_counts(pos), "control": reserved_counts(ctl)},
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
        # ROUND 2, AMENDMENT 9: the pre-registered side-by-side, carried here so the published table can be read
        # against a file that is regenerated, and printed under its heading below.
        "round_1_beside_round_2": round_1_beside_round_2(pre, results),
    }


# ROUND 2, AMENDMENT 9. Round 1's tree is read as data only (`round_1_data_paths`), and the regrade record
# for each fixed task is the committed one under verification/round1-regrade/.
ROUND_1_RESULTS = HERE.parent / "gap-study" / "results"
REGRADE_RECORDS = {"scope-read": HERE / "verification" / "round1-regrade" / "scope-read-control.json",
                   "plan-gate": HERE / "verification" / "round1-regrade" / "plan-gate.json"}


def round_1_beside_round_2(pre: dict, results: dict[str, dict]) -> dict:
    """The pre-registered side-by-side for the two fixed tasks: per model and half, round 1's published count,
    the count of round 1's takes the round-2 instrument reads as correct, and round 2's published cell.

    Counts only, in `k of n`; no verdict, no verb, no sentence comparing the rounds. A missing input is an
    error, never an empty row: the plan promised the comparison and a blank would read as one.
    """
    plan = pre["analysis_plan"]["round_1_beside_round_2"]
    rows = []
    for tid in plan["tasks"]:
        r1_path = ROUND_1_RESULTS / f"{tid}.json"
        rg_path = REGRADE_RECORDS.get(tid)
        if not r1_path.is_file() or rg_path is None or not rg_path.is_file():
            raise SystemExit(f"round-1-beside-round-2: no round 1 results file or regrade record for {tid}")
        r1 = json.loads(r1_path.read_text())
        regrade = json.loads(rg_path.read_text())
        r2 = results.get(tid)
        for model in prereg.models():
            for half in ("positive", "control"):
                c1 = r1["cells"].get(model, {}).get(half)
                under = [x for x in regrade["takes"] if x["model"] == model and x["half"] == half]
                c2 = (r2 or {}).get("cells", {}).get(model, {}).get(half) if r2 else None
                rows.append({
                    "task": tid, "model": model, "half": half,
                    "round_1_as_published": f"{c1['k']} of {c1['n']}" if c1 else "not run",
                    "round_1_takes_under_round_2_instrument":
                        f"{sum(1 for x in under if x['round_2_verdict'] == 'correct')} of {len(under)}" if under else "not run",
                    "round_2": (published_cell(c2) if c2["state"].startswith(RAN) else c2["state"]) if c2
                               else "not run — no cell",
                })
    return {"heading": plan["heading"], "tasks": list(plan["tasks"]), "rows": rows}


def round_1_beside_round_2_lines(block: dict) -> list[str]:
    """The comparison as printed: the plan's heading, then one row per task, model and half, counts only."""
    lines = [block["heading"]]
    lines.append(f"  {'task':20} {'model':28} {'half':9} {'round 1 as published':22} "
                 f"{'round 1 under round 2 instrument':34} round 2")
    for r in block["rows"]:
        lines.append(f"  {r['task']:20} {r['model']:28} {r['half']:9} {r['round_1_as_published']:22} "
                     f"{r['round_1_takes_under_round_2_instrument']:34} {r['round_2']}")
    return lines


def prediction_lines(preds: list[dict]) -> list[str]:
    """Every prediction beside its outcome, in the two columns the plan fixes: blind, then informed."""
    lines = ["predictions beside outcomes"]
    for basis in ("blind", "informed"):
        rows = [p for p in preds if p["basis"] == basis]
        lines.append(f"  {basis}: " + ("none" if not rows else ""))
        for p in rows:
            verdict = "not scored" if not p["scored"] else ("right" if p["right"] else "wrong")
            lines.append(f"    {p['task']:20} {p['model']:28} predicted {p['predicted']:14} "
                         f"outcome {p['outcome']:14} {verdict}")
    return lines


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
            for half in ("positive", "control"):
                rc = {k: v for k, v in m["reserved_counts"][half].items() if v}
                if rc:
                    print(f"      {half} reserved: " + ", ".join(f"{v} {k}" for k, v in rc.items()))
        print()

    for line in comparison_lines(out):
        print(line)
    print()

    for line in round_1_beside_round_2_lines(out["round_1_beside_round_2"]):
        print(line)
    print()

    vs = out["harness_versions"]
    print("harness versions across every graded take: "
          + (", ".join(vs) if vs else "none — no take has been graded"))
    print()

    for line in prediction_lines(out["predictions"]):
        print(line)
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
