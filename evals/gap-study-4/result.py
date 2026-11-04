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
           f"published (which stand as published). These are {FOLLOWUP_LABEL}."]
    # pre-freeze review 2, NIT (lane fold2/lc): one table per family, each under its own heading, never one heading
    # over several families; the family column stays on each row
    families = []
    for r in rows:
        if "p" in r and r["p"] is not None and r["family"] not in families:
            families.append(r["family"])
    for family in families:
        out += ["", f"### Family: {family}", "",
                "| Family | Harness | Model | Harness | Model | Task | Holm-adjusted p as published | Of | "
                "Holm-adjusted p, full family | Of |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            if "p" not in r or r["p"] is None or r["family"] != family:
                continue
            task = "the tasks that run" if r["task"] is None else f"`{r['task']}`"
            was = "not in the original report" if r["published_adjusted"] is None else r["published_adjusted"]
            of = "" if r["published_family_size"] is None else stats._say(r["published_family_size"])
            out.append(f"| {r['family']} | `{r['harness_a']}` | `{r['model_a']}` | `{r['harness_b']}` "
                       f"| `{r['model_b']}` | {task} | {was} | {of} | {r['adjusted']} "
                       f"| {stats._say(r['family_size'])} |")
    return "\n".join(out) + "\n"


def read_original_values(path=None):
    path = ORIGINAL_VALUES if path is None else Path(path)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def stopped_counts(rows: list, history: list, evidence_for=None) -> list:
    """Pre-freeze review 1, m13 (lane pf1-l2b), and review 2, MAJOR 1: per half-cell, the pause, aborted and harness-error
    attempts whose end state shows a forbidden change (run.stopped_counts reads the committed take folders)."""
    import run
    return run.stopped_counts(rows, history, evidence_for=evidence_for)


def _stop_cell(c: dict) -> str:
    if not c["takes"]:
        return "none"
    unread = f", {stats._say(c['unread'])} with no end state to read" if c["unread"] else ""
    return f"{stats._say(c['forbidden'])} of {stats._say(c['takes'])}{unread}"


def render_stopped(rows: list) -> str:
    out = ["## Stopped takes with a forbidden change on disk", "",
           "A pause or a harness-error attempt is re-run (a harness-error beyond its cap leaves the denominator) and an "
           "aborted take is never graded, so a wrong action on disk in any of them is in none of the three views. Per "
           "half-cell: of the pause, aborted and harness-error attempts, how many end states show a forbidden change, "
           "an agent change of its own matching one of the half's registered forbidden patterns. A take with no end "
           "state to read is named, never counted clean.", ""]
    if not rows:
        return "\n".join(out + ["No take stopped as a pause, aborted or harness-error.", ""])
    out += ["| Arm | Task | Half | Model | Harness | Pauses with a forbidden change | Aborted takes with a forbidden "
            "change | Harness-error attempts with a forbidden change |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['arm']} | `{r['task']}` | {r['half']} | `{r['model']}` | `{r['harness']}` "
                   f"| {_stop_cell(r['pause'])} | {_stop_cell(r['aborted'])} | {_stop_cell(r['harness-error'])} |")
    return "\n".join(out + [""])


# Pre-freeze review 2, m10 (lane fold2-ld, Thu 29 Oct 2026): an outside-reach event (routing.json's outside-reach and
# checker-event-reason annotations; the drive step's count in the routed records' events.outside_reach) never routes a
# take and is not in the published take record, so the page prints it per half-cell, from every committed outcome
# (re-runs included), as rounds 2 and 3 published their refused attempts. A take whose records give no count is
# named as unread, never counted as none.
REACH_EVENTS = ("outside-reach", "checker-event-reason")


def _reach_count(o: dict):
    """The outcome's events.outside_reach, or None when its records hold no readable count."""
    records = o.get("records")
    ev = records.get("events") if isinstance(records, dict) else None
    n = ev.get("outside_reach") if isinstance(ev, dict) else None
    return n if type(n) is int and n >= 0 else None


def outside_reach_counts(rows: list, history: list) -> list:
    """Per half-cell with a committed outcome: {arm, task, half, model, harness, takes, with_event (outcomes whose
    committed events hold an outside-reach annotation), events (the events.outside_reach total), unread (outcomes whose
    records give no count)}, in half-cell key order."""
    import batch
    registered = {(r["slot"], r["attempt"]): r for r in rows}
    cells = {}
    for o in history:
        if not batch.is_outcome(o):
            continue
        r = registered.get((o.get("slot"), o.get("attempt")))
        if r is None:
            raise ValueError(f"a committed outcome ({o.get('slot')}, {o.get('attempt')}) has no registered row")
        c = cells.setdefault(stats.half_cell_key(r), {"takes": 0, "with_event": 0, "events": 0, "unread": 0})
        c["takes"] += 1
        c["with_event"] += any(e in REACH_EVENTS for e in (o.get("events") or []))
        n = _reach_count(o)
        if n is None:
            c["unread"] += 1
        else:
            c["events"] += n
    return [dict(zip(("arm", "task", "half", "model", "harness"), k), **cells[k]) for k in sorted(cells)]


def render_outside_reach(rows: list) -> str:
    out = ["## Outside-reach events", "",
           "An outside-reach event is an absolute path outside the take's own run tree that a tool call or its "
           "result names, a study material reached, or the account email reached: the take is graded as usual with "
           "its text masked, and the event never routes it. Per half-cell, over every committed attempt: the takes, "
           "how many carry any of these events, the paths outside the run tree counted (events.outside_reach, which "
           "does not count the account email), and the takes whose records give no count, which are named and never "
           "counted as none.", ""]
    if not rows:
        return "\n".join(out + ["No take is committed.", ""])
    out += ["| Arm | Task | Half | Model | Harness | Takes | Takes with an event | Events | Takes with no count |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['arm']} | `{r['task']}` | {r['half']} | `{r['model']}` | `{r['harness']}` "
                   f"| {stats._say(r['takes'])} | {stats._say(r['with_event'])} | {stats._say(r['events'])} "
                   f"| {stats._say(r['unread'])} |")
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


def sample_errors() -> tuple:
    """labelling/sample.py's SampleError, the error a missing frame raises; none in a copy that carries no labelling/
    (a disposable tree that never draws a sample)."""
    try:
        from labelling import sample
    except ImportError:
        return ()
    return (sample.SampleError,)


def _flagged_verdicts():
    from labelling import flagged_verdicts
    return flagged_verdicts


def flagged_counts(pre: dict, reader=None, verdict_reader=None):
    """The flagged list's counts and, pre-freeze review 2 m8 (lane fold2-ld), its verdict record's per-row counts
    (labelling/flagged_verdicts.py; `verdict_reader(sample doc)` gives the validated findings or None, tests)."""
    design = pre.get("labelling_design")
    fl = design.get("flagged_list") if isinstance(design, dict) else None
    if fl is None:
        return None
    doc = _sample_doc(pre) if reader is None else reader()
    if doc is None:
        return {"cap": fl["cap"], "drawn": False}
    f = doc["flagged"]
    fv = _flagged_verdicts()
    found = fv.published(doc) if verdict_reader is None else verdict_reader(doc)     # review NIT 3: history first
    return {"cap": f["cap"], "drawn": True, "flagged": f["flagged"], "listed": f["listed"],
            "beyond_cap": f["beyond_cap"], "verdicts": fv.verdict_rows(doc, found)}


def render_flagged_counts(c) -> str:
    if c is None:
        return ""
    # m8: the list holds every flagged take only up to its cap; the count beyond it is published and not read
    reach = ("every take a grader flagged for the human sample goes to it" if c["cap"] is None else
             f"the takes a grader flagged for the human sample go to it up to the cap of {stats._say(c['cap'])}, a "
             f"seeded draw of that many when more are flagged, with the count beyond the cap published and not read")
    out = ["## Flagged takes, the separate check list", "",
           f"A separate check list, read after the blind labels: {reach}.", ""]
    if not c["drawn"]:
        return "\n".join(out + ["No flagged list is drawn yet: there is no frame.", ""])
    out += [f"Flagged takes: {stats._say(c['flagged'])}; on the check list: "
            f"{stats._say(c['listed'])}; beyond the cap, published and not read: "
            f"{stats._say(c['beyond_cap'])}.", ""]
    rows = c.get("verdicts")
    if rows is None:
        return "\n".join(out)
    out += ["What the person reading the list found on each listed take, per task inside one arm, harness and model "
            "(labelling/flagged-verdicts.json): the grader's reading stands, is wrong, or the take does not settle it.",
            ""]
    if rows and rows[0]["grader-right"] is None:
        out += ["No verdict record is committed: the list's findings are not read yet.", ""]
    out += ["| Arm | Harness | Model | Task | On the list | Grader's reading stands | Grader's reading wrong | "
            "Cannot tell |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        counts = ["not read"] * 3 if r["grader-right"] is None else [
            stats._say(r[k]) for k in ("grader-right", "grader-wrong", "cannot-tell")]
        out.append(f"| {r['arm']} | `{r['harness']}` | `{r['model']}` | `{r['task']}` | {stats._say(r['listed'])} | "
                   + " | ".join(counts) + " |")
    return "\n".join(out + [""])


def from_records(records: list, pre: dict, rows: list, history: list, table=None, *, go=None,
                 published_values=None, evidence_for=None, flagged_reader=None) -> dict:
    published = check_results.publication(history, table)
    states = completeness.mechanical_states(history, published["cells"], table)
    registered = {(r["slot"], r["attempt"]): r for r in rows if "attempt" in r}
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
            "outside_reach": outside_reach_counts(rows, history),
            "flagged": flagged_counts(pre, flagged_reader),
            "pause_notes": pause_notes(rows, published["attempts"]),
            # the orchestrator's pin-block ruling (lane pf1-l2a): listed, never counted
            "harness_events": check_results.pin_block_events(history, registered, table), "published_tip_residual": pre.get("published_tip_residual")}


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
    pre = tip_limit_held(prereg.require_frozen("publishing the result"))
    return from_records(records, pre, rows, history)


def render_witness(run) -> str:
    """glitch-45's review of fold2/lb, MJ-2: the push witness, printed on the page (check_results.py --witness --record's
    latest run, held to HEAD's ledger by check_results.witness_publication_problems)."""
    if not run:
        return ""
    if run.get("disposable"):
        return "## Push witness\n\nNot read: a disposable rehearsal reads no push records.\n"
    return (f"## Push witness\n\n{run['ledger_commits']} take-ledger commit(s) on the run line; "
            f"{len(run['unwitnessed'])} unwitnessed (no push record of the mirror holds them), read by "
            f"check_results.py --witness at {run['at']}.\n")


TIP_LIMIT_HEADING = "## Limit on the review record"


def render_tip_limit(text) -> str:
    """Pre-freeze review 7, M1 (lane fold9/round7-residual): the limit the freeze wrote into the frozen file
    (freeze.PUBLISHED_TIP_LIMIT), printed in its own words, and check_publication holds the page to this render. A frozen
    file without it prints no byte. from_records carries the field; it sits on one line there because the draft cites
    this file's render_witness by line number."""
    return f"{TIP_LIMIT_HEADING}\n\n{text}\n" if text else ""


def tip_limit_held(pre: dict) -> dict:
    """Fold 9's review, m1 (lane fold10/rehearsal-road): the frozen file's published_tip_residual is exactly what pinned
    freeze.py always writes, so a limit stripped or softened before the freeze commit, which every other check passes,
    never reaches the page unqualified. `pre`, unchanged, when it holds."""
    import freeze
    if pre.get("published_tip_residual") != freeze.PUBLISHED_TIP_LIMIT:
        raise ValueError("the frozen file's published_tip_residual is not freeze.PUBLISHED_TIP_LIMIT")
    return pre


def render(rec: dict, witness=None) -> str:
    lines = [f"# {study.STUDY_TITLE} — result", ""]
    if rec["stats"]["takes"] == 0:
        lines += [empty_line(), ""]
    lines += [completeness.render(rec["completeness"]), render_pause_notes(rec["pause_notes"]),
              render_stopped(rec["stopped"]) if "stopped" in rec else "",
              render_outside_reach(rec["outside_reach"]) if "outside_reach" in rec else "",
              *([render_flagged_counts(rec["flagged"])] if rec.get("flagged") is not None else []),   # off: no byte
              check_results.render_harness_events(rec.get("harness_events") or []),
              stats_block(rec["stats"]), render_followup(rec.get("followup") or [], rec.get("followup_arms") or []),
              render_witness(witness), render_tip_limit(rec.get("published_tip_residual")), prior_sections()]
    return "\n".join(lines).rstrip() + "\n"


def later_files_problems() -> list[str]:
    """Pre-freeze review 9, m-new-2: ci.yml is not pinned and was the one caller of copy_manifest.py --later-files, so an edit
    to it switched the check off. This file is pinned and is on the publication road, so the page is neither written nor
    checked over a refused later file. `-I` keeps PYTHONPATH and the script's own folder out of the child, and copy_manifest
    puts only this folder on its path. Only HEAD's commits are read, as the battery's line reads them, so a stray on a
    verifier's disk stops nothing. THE LIMIT: this copy runs from HEAD, after this process has imported what a shadow may have
    replaced, so CI's run of the freeze commit's copy stays the one no later file can reach, and a page written by hand
    is read by check_results.py without this."""
    import subprocess  # here, so no line the draft cites in this file moves
    got = subprocess.run([sys.executable, "-I", "-B", str(HERE / "copy_manifest.py"), "--later-files", "HEAD"],
                         capture_output=True, text=True)
    if got.returncode == 0:
        return []
    failed = [line[len("FAIL "):] for line in got.stdout.splitlines() if line.startswith("FAIL ")]
    return failed or [f"copy_manifest.py --later-files exited {got.returncode}: {got.stderr.strip()[-300:]}"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    group.add_argument("--publish-original", action="store_true",
                       help="write original-values.json once, when the original report is published (MAJOR 10)")
    args = ap.parse_args(argv)
    try:
        got = derive()
    except (ValueError, stats.StatsError, *sample_errors()) as exc:      # closure MINOR 3: a missing frame named
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
    # glitch-45's review of fold2/lb, MJ-2 (ruled): the page is written or checked only with the push witness on record
    problems, witness = check_results.witness_publication_problems(prereg.require_frozen("publishing the result"))
    if problems:
        print("result: FAIL " + "; ".join(problems))
        return 1
    later = later_files_problems()
    if later:
        print("result: FAIL " + "; ".join(later))
        return 1
    wanted = render(got, witness=witness)
    if args.write:
        PAGE.write_text(wanted, encoding="utf-8")
    elif not PAGE.is_file() or PAGE.read_text(encoding="utf-8") != wanted:
        print("result: FAIL RESULT.md differs from the records and committed states")
        return 1
    print(f"result: {got['stats']['takes']} records; every stats table and planned half-cell rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
