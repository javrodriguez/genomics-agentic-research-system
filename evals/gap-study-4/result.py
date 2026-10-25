#!/usr/bin/env python3
"""Render the round's result from stats and committed completeness, without pooling.

Every statistical table, including the excluded view's three possible shapes,
is emitted by stats.render_md through render_block. This module never recomputes
one. Empty records print no takes, never a measured zero. The frozen task list
and planned rows are the denominator; committed outcomes and rulings carry the
mechanical states. No model, network or earlier-round table is read.

Pre-freeze review 1 (lane pf1-l2b): the original report's tables come from the arms that are not deferred, and a
deferred arm's values print only in the follow-up after its committed go, beside the published ones (MAJOR 10); the
pause and aborted takes whose end state shows a forbidden change are counted per half-cell (m13).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_results
import completeness
import prereg
import stats
import study
import takes

RECORDS = HERE / "records"
PAGE = HERE / "RESULT.md"
# PRE-FREEZE REVIEW 1, MAJOR 10 (lane pf1-l2b, Sat 24 Oct 2026): deferred_arms.G.analysis as registered (OD105). The
# original report's tables are derived from the records of the arms that are not deferred (stats.original_records),
# under the full design, so arm G's contrast stays untested and counted in m. `--publish-original` writes those
# values once into ORIGINAL_VALUES (run output, committed after the freeze), and check_results refuses any later change
# to that file or to the values the original records give. Only after Javier's committed go record for a deferred arm
# (prereg.deferred_arm_go, the record batch's deferred_go reads) does the follow-up section print the full-family
# values beside the published ones, labelled FOLLOWUP_LABEL.
ORIGINAL_VALUES = HERE / "original-values.json"
ORIGINAL_KIND = "the original report's comparison values"
VALUE_KEYS = ("family", "harness_a", "model_a", "harness_b", "model_b", "task", "p", "adjusted", "family_size")
FOLLOWUP_LABEL = "the registered full-design computation, never a correction"


def empty_line() -> str:
    return stats.NO_TAKES


def prior_sections() -> str:
    """The not_poolable rule: no comparative section from any earlier round."""
    return ""


def stats_block(derived: dict) -> str:
    return stats.render_block(derived)


def deferred_arm_names(pre: dict) -> list:
    return sorted(prereg.deferred_arms(pre))


def original_values(derived: dict, deferred: list) -> dict:
    """The original report's comparison values (table 5's tested and descriptive rows, VALUE_KEYS only)."""
    rows = derived["tables"]["comparisons"]
    keep = stats.NO_TAKES if rows == stats.NO_TAKES else [{k: r.get(k) for k in VALUE_KEYS} for r in rows]
    return {"kind": ORIGINAL_KIND, "deferred_arms": list(deferred), "comparisons": keep}


def value_key(r: dict) -> tuple:
    return tuple(r[k] for k in VALUE_KEYS[:6])


def followup_rows(published: dict, full: dict) -> list:
    """Each comparison row of the full family beside the published original value (None where the original report
    had no such row); never a replacement of one."""
    old = {} if published["comparisons"] == stats.NO_TAKES else {value_key(r): r for r in published["comparisons"]}
    rows = full["tables"]["comparisons"]
    out = []
    for r in ([] if rows == stats.NO_TAKES else rows):
        was = old.get(value_key(r))
        out.append({**{k: r.get(k) for k in VALUE_KEYS}, "published_adjusted": was.get("adjusted") if was else None,
                    "published_family_size": was.get("family_size") if was else None})
    return out


def render_followup(rows: list, arms: list) -> str:
    if not rows:
        return ""
    out = [f"## Follow-up: arm {', '.join(arms)}, {FOLLOWUP_LABEL}", "",
           f"After Javier's committed go, the comparison values over every arm, beside the values the original report "
           f"published (which stand as published). These are {FOLLOWUP_LABEL}.", "",
           "| Family | Harness | Model | Harness | Model | Task | Holm-adjusted p as published | Of | "
           "Holm-adjusted p, full family | Of |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "p" not in r or r["p"] is None:
            continue
        task = "the tasks that run" if r["task"] is None else f"`{r['task']}`"
        was = "not in the original report" if r["published_adjusted"] is None else r["published_adjusted"]
        of = "" if r["published_family_size"] is None else stats._say(r["published_family_size"])
        out.append(f"| {r['family']} | `{r['harness_a']}` | `{r['model_a']}` | `{r['harness_b']}` | `{r['model_b']}` "
                   f"| {task} | {was} | {of} | {r['adjusted']} | {stats._say(r['family_size'])} |")
    return "\n".join(out) + "\n"


def read_original_values(path=None):
    path = ORIGINAL_VALUES if path is None else Path(path)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def stopped_counts(rows: list, history: list, evidence_for=None) -> list:
    """Pre-freeze review 1, m13 (lane pf1-l2b): per half-cell, the pause and aborted takes whose end state shows a
    forbidden change (run.stopped_counts reads the committed take folders)."""
    import run
    return run.stopped_counts(rows, history, evidence_for=evidence_for)


def _stop_cell(c: dict) -> str:
    if not c["takes"]:
        return "none"
    unread = f", {stats._say(c['unread'])} with no end state to read" if c["unread"] else ""
    return f"{stats._say(c['forbidden'])} of {stats._say(c['takes'])}{unread}"


def render_stopped(rows: list) -> str:
    out = ["## Stopped takes with a forbidden change on disk", "",
           "A pause is re-run and never becomes a record, and an aborted take is never graded, so a wrong action on "
           "disk in either is in none of the three views. Per half-cell: of the pause and aborted takes, how many end "
           "states show a forbidden change, an agent change of its own matching one of the half's registered "
           "forbidden patterns. A take with no end state to read is named, never counted clean.", ""]
    if not rows:
        return "\n".join(out + ["No take stopped as a pause or aborted.", ""])
    out += ["| Arm | Task | Half | Model | Harness | Pauses with a forbidden change | Aborted takes with a forbidden "
            "change |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['arm']} | `{r['task']}` | {r['half']} | `{r['model']}` | `{r['harness']}` "
                   f"| {_stop_cell(r['pause'])} | {_stop_cell(r['aborted'])} |")
    return "\n".join(out + [""])


# Lane review 1 (pf1-l2b): with labelling_design.flagged_list on, the page prints how many takes were flagged, how
# many the check list holds and how many fell beyond its cap; with it off (null) nothing is added, byte for byte.
def _sample_doc(pre: dict):
    """The original part's sample document, drawn under the labelling design of `pre` (closure NIT 4), from the
    committed frame and records, bound both ways as sample.derive binds them; None with no frame and no records."""
    from labelling import sample
    recs = stats.load_results(sample.RESULTS)
    if not os.path.isfile(sample.FRAME) and not recs:
        return None
    if not os.path.isfile(sample.FRAME):
        raise sample.SampleError("results are committed and no frame is: frame.json binds the sample to them")
    with open(sample.FRAME, encoding="utf-8") as fh:
        frame = json.load(fh)
    design = sample.validate_design(pre["labelling_design"])
    deferred = sample.deferred_cells(pre, design)
    sample.validate_frame(frame, design, exempt={c[2] for c in deferred})
    bad = sample.frame_problems(frame, recs)
    if bad:
        raise sample.SampleError("; ".join(bad))
    return sample.draw(frame, design, deferred, sample.ORIGINAL)


def flagged_counts(pre: dict, reader=None):
    design = pre.get("labelling_design")
    fl = design.get("flagged_list") if isinstance(design, dict) else None
    if fl is None:
        return None
    doc = _sample_doc(pre) if reader is None else reader()
    if doc is None:
        return {"cap": fl["cap"], "drawn": False}
    f = doc["flagged"]
    return {"cap": f["cap"], "drawn": True, "flagged": f["flagged"], "listed": f["listed"],
            "beyond_cap": f["beyond_cap"]}


def render_flagged_counts(c) -> str:
    if c is None:
        return ""
    cap = "no cap" if c["cap"] is None else f"a cap of {stats._say(c['cap'])}"
    out = ["## Flagged takes, the separate check list", "",
           f"Every take a grader flagged for the human sample goes to a separate check list, read after the blind "
           f"labels, with {cap}.", ""]
    if not c["drawn"]:
        return "\n".join(out + ["No flagged list is drawn yet: there is no frame.", ""])
    return "\n".join(out + [f"Flagged takes: {stats._say(c['flagged'])}; on the check list: "
                            f"{stats._say(c['listed'])}; beyond the cap, published and not read: "
                            f"{stats._say(c['beyond_cap'])}.", ""])


def from_records(records: list, pre: dict, rows: list, history: list, table=None, *, go=None,
                 published_values=None, evidence_for=None, flagged_reader=None) -> dict:
    published = check_results.publication(history, table)
    states = completeness.mechanical_states(history, published["cells"], table)
    deferred = deferred_arm_names(pre)
    original = stats.original_records(records, deferred)
    derived = stats.derive(original, pre[stats.DESIGN_KEY])
    held = sorted({r["arm"] for r in records} & set(deferred))
    unreleased = [a for a in held if not prereg.deferred_arm_go(a, go)]      # lane review 10: per arm with records
    if unreleased:
        raise ValueError(f"records of the deferred arm(s) {unreleased} exist and no committed go record releases "
                         f"them ({prereg.GO_RECORD.name})")
    followup = []
    if held:
        values = read_original_values() if published_values is None else published_values
        if values is None:
            raise ValueError(f"records of the released arm(s) {held} exist and the original report's values were never "
                             f"published ({ORIGINAL_VALUES.name}): the follow-up prints beside them only")
        followup = followup_rows(values, stats.derive(records, pre[stats.DESIGN_KEY]))
    return {"stats": derived,
            "original_values": original_values(derived, deferred),
            "followup": followup, "followup_arms": held,
            "completeness": completeness.summarize(pre, records, states, rows),
            "stopped": stopped_counts(rows, history, evidence_for),
            "flagged": flagged_counts(pre, flagged_reader),
            "pause_notes": pause_notes(rows, published["attempts"])}


def pause_notes(rows, attempts):
    """Attach non-closing strict pause notes to the registered take identity."""
    registered = {(r["slot"], r["attempt"]): r for r in rows}
    return [dict(registered[(o["slot"], o["attempt"])], route=o["state"], note=o["note"])
            for o in attempts if o.get("note") and o["cell_state"] is None]


def render_pause_notes(notes):
    if not notes:
        return ""
    lines = ["## Ruled pause notes", "",
             "| Slot | Attempt | Arm | Task | Half | Model | Harness | Version | Wording | Repeat | Pressure | Route | Note |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in notes:
        fields = [row[k] for k in ("slot", "attempt", "arm", "task", "half", "model")]
        fields += [row["agent"]["harness"], row["agent"]["version"]]
        fields += [row[k] for k in ("wording", "repeat", "pressure", "route", "note")]
        lines.append("| " + " | ".join((str(v) if v is not None else "").replace("|", "\\|").replace("\n", " ")
                                        for v in fields) + " |")
    return "\n".join(lines) + "\n"


def derive() -> dict | None:
    records = stats.load_results(RECORDS)
    rows, history = takes.load_rows(), takes.read_history()
    if not records and not rows and not history:
        return None
    pre = prereg.require_frozen("publishing the result")
    return from_records(records, pre, rows, history)


def render(rec: dict) -> str:
    lines = [f"# {study.STUDY_TITLE} — result", ""]
    if rec["stats"]["takes"] == 0:
        lines += [empty_line(), ""]
    lines += [completeness.render(rec["completeness"]), render_pause_notes(rec["pause_notes"]),
              render_stopped(rec["stopped"]) if "stopped" in rec else "",
              *([render_flagged_counts(rec["flagged"])] if rec.get("flagged") is not None else []),   # off: no byte
              stats_block(rec["stats"]), render_followup(rec.get("followup") or [], rec.get("followup_arms") or []),
              prior_sections()]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    group.add_argument("--publish-original", action="store_true",
                       help="write original-values.json once, when the original report is published (MAJOR 10)")
    args = ap.parse_args(argv)
    from labelling import sample as _sample
    try:
        got = derive()
    except (ValueError, _sample.SampleError, stats.StatsError) as exc:      # closure MINOR 3: a missing frame named
        print(f"result: FAIL {exc}")
        return 1
    if got is None:
        print("result: no takes; no table measured or written")
        return 0
    if args.publish_original:
        if ORIGINAL_VALUES.exists():
            print(f"result: FAIL {ORIGINAL_VALUES.name} exists: the original report's values are published once and "
                  f"stand as published")
            return 1
        ORIGINAL_VALUES.write_text(json.dumps(got["original_values"], indent=1, sort_keys=True) + "\n",
                                   encoding="utf-8")
        print(f"result: wrote {ORIGINAL_VALUES.name}, the original report's values, once")
        return 0
    wanted = render(got)
    if args.write:
        PAGE.write_text(wanted, encoding="utf-8")
    elif not PAGE.is_file() or PAGE.read_text(encoding="utf-8") != wanted:
        print("result: FAIL RESULT.md differs from the records and committed states")
        return 1
    print(f"result: {got['stats']['takes']} records; every stats table and planned half-cell rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
