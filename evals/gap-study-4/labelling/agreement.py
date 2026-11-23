#!/usr/bin/env python3
"""CP8's agreement table: Javier's blind labels against the grader's, per task inside each model, arm and harness.

    python3 evals/gap-study-4/labelling/agreement.py --check        re-derive every number from the committed labels
                                                                    and compare AGREEMENT.md byte for byte
    python3 evals/gap-study-4/labelling/agreement.py --write        write AGREEMENT.md (CP8, once the labels land)
    python3 evals/gap-study-4/labelling/agreement.py --unmeasured   print the D6 B sentence and nothing else

WHAT IT READS. sample.py's derivation (frame, design and sample, re-derived and compared with sample.json), the
labels Javier wrote (labels.json: {"labels": [{"sheet_id", "label", "stop_cause"}]}, every sampled sheet id exactly
once, each label one of its task's defined labels, each stop cause one of labels4.STOPS or blank) and the definitions
(definitions.json, sheet.validate_definitions). The grader's label is read from the frame's record, never from the
sheet.

ONE ROW PER (arm, harness, model, task), NEVER ACROSS THEM. A row counts only takes of its own arm, harness and model,
and every row prints those three beside its task; pool_problems() refuses a row missing one, or holding a take of
another, and render() refuses rows with any such problem. There is no row, line or figure over two models, arms or
harnesses. Each row prints:
  - x agreeing of n labelled, with intervals.clopper_pearson's exact two-sided 0.95 bounds (stats.bound);
  - the agreement carried back to the frame: each stratum (verdict, readers) of the row weighted by its frame size,
    sum over strata of (frame size of the stratum, divided by the row's frame size) times (x of the stratum, divided
    by its drawn count), on the 0.001 grid; its bounds are each stratum's exact bounds at alpha divided by the number
    of strata (Bonferroni), carried back by the same weights, lower floored and upper ceiled. A row whose frame holds
    a stratum the draw left empty prints "a stratum unsampled" and no carried-back figure;
  - the confusion matrix, grader label against Javier's label, as counts.

WHAT --check BINDS. The sample re-derives (sample.py's rules), the labels validate, every number of AGREEMENT.md
re-derives from them byte for byte, and labels.json is published as read: exactly one commit in HEAD's history
touches it, and the file on disk is that commit's (history_problems; a shallow clone refuses). No labels on disk:
"no labels; nothing measured", exit 0 and not a pass on data, only while no AGREEMENT.md stands and no commit ever
touched labels.json (gone_problems, review W11D-R1-1).

EVERY CELL IS SEEN. A (arm, harness, model, task) cell of the frame that the draw left empty prints its own line,
"unsampled: no take drawn", so an absent row is never silent.

UNDER D6 B (no labelling), the result says "grader agreement unmeasured" (plan line 1065): --unmeasured prints exactly
that line.

No model, no network, standard library only. Writes only AGREEMENT.md, and only under --write.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from fractions import Fraction

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
for _p in (_STUDY, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sample  # noqa: E402
import sheet  # noqa: E402
import stats  # noqa: E402

LABELS = os.path.join(_HERE, "labels.json")
PAGE = os.path.join(_HERE, "AGREEMENT.md")
REPO = os.path.dirname(os.path.dirname(_STUDY))
UNMEASURED = "grader agreement unmeasured"
LABEL_FIELDS = ("sheet_id", "label", "stop_cause")
ROW_KEY = ("arm", "harness", "model", "task")
CELL = ("verdict", "readers")
NO_STOP = ""


class AgreementError(Exception):
    """Labels, rows or a page the agreement table refuses."""


def validate_labels(doc, smp: dict, defs: dict) -> dict:
    """{sheet_id: (label, stop cause)} for every sampled sheet id, or AgreementError."""
    if not isinstance(doc, dict) or set(doc) != {"labels"} or not isinstance(doc["labels"], list):
        raise AgreementError('labels.json is {"labels": [...]}')
    tasks = {i["sheet_id"]: i["stratum"]["task"] for i in smp["items"]}
    out = {}
    for e in doc["labels"]:
        if not isinstance(e, dict) or set(e) != set(LABEL_FIELDS):
            raise AgreementError(f"a label entry holds exactly {LABEL_FIELDS}")
        sid = e["sheet_id"]
        if sid not in tasks:
            raise AgreementError(f"{sid!r} is not a sampled sheet id")
        if sid in out:
            raise AgreementError(f"{sid} is labelled twice")
        if e["label"] not in defs[tasks[sid]]:
            raise AgreementError(f"{sid}: {e['label']!r} is not a defined label of task {tasks[sid]}")
        if e["stop_cause"] != NO_STOP and e["stop_cause"] not in sheet.STOP_CAUSES:
            raise AgreementError(f"{sid}: stop cause {e['stop_cause']!r} is not a pre-registered stop or blank")
        out[sid] = (e["label"], e["stop_cause"])
    missing = sorted(set(tasks) - set(out))
    if missing:
        raise AgreementError(f"sheet ids not labelled: {missing}")
    return out


def carried_back(strata: list, alpha=stats.intervals.ALPHA):
    """(estimate, lower, upper) as Fractions on the 0.001 grid, or None when a stratum of the frame was not drawn."""
    if any(s["drawn"] == 0 for s in strata):
        return None
    total = sum(s["frame"] for s in strata)
    est = lo = hi = Fraction(0)
    for s in strata:
        w = Fraction(s["frame"], total)
        a, b = stats.intervals.clopper_pearson(s["agree"], s["drawn"], alpha / len(strata))
        est += w * Fraction(s["agree"], s["drawn"])
        lo += w * a
        hi += w * b
    return (stats.intervals.round3(est), stats.intervals.floor3(lo), -stats.intervals.floor3(-hi))


def rows(frame, smp: dict, labels: dict) -> list:
    """One row per (arm, harness, model, task) of the sample, with its counts, bounds, carried-back figure and matrix."""
    record = {e["take"]: e["record"] for e in frame}
    frame_sizes = {}
    for e in frame:
        frame_sizes.setdefault(sample.stratum(e), 0)
        frame_sizes[sample.stratum(e)] += 1
    out = {}
    cells = sorted({sample.stratum(e)[:4] for e in frame})
    for key in cells:
        out[key] = {**dict(zip(ROW_KEY, key)), "takes": [], "n": 0, "agree": 0, "matrix": {}, "cells": {}}
    for it in smp["items"]:
        st = it["stratum"]
        key = tuple(st[k] for k in ROW_KEY)
        row = out[key]
        mine, stop = labels[it["sheet_id"]]
        theirs = record[it["take"]]["label"]
        row["takes"].append(it["take"])
        row["n"] += 1
        row["agree"] += mine == theirs
        row["matrix"][(theirs, mine, stop)] = row["matrix"].get((theirs, mine, stop), 0) + 1
        c = row["cells"].setdefault(tuple(st[k] for k in CELL), {"drawn": 0, "agree": 0})
        c["drawn"] += 1
        c["agree"] += mine == theirs
    for key, row in out.items():
        strata = []
        for sk, size in sorted(frame_sizes.items()):
            if sk[:4] == key:
                c = row["cells"].get(sk[4:], {"drawn": 0, "agree": 0})
                strata.append({"verdict": sk[4], "readers": sk[5], "frame": size, **c})
        row["strata"] = strata
        row["bounds"] = stats.bound(row["agree"], row["n"]) if row["n"] else None
        row["carried"] = carried_back(strata)
        del row["cells"]
    return [out[k] for k in sorted(out)]


def pool_problems(rs: list, frame) -> list:
    """Every row names its arm, harness, model and task, and holds only takes of those; no key is repeated."""
    record = {e["take"]: e["record"] for e in frame}
    out, seen = [], set()
    for r in rs:
        key = tuple(r.get(k) for k in ROW_KEY)
        if not all(isinstance(v, str) and v for v in key):
            out.append(f"POOL: a row does not name its {ROW_KEY}: {key}")
            continue
        if key in seen:
            out.append(f"POOL: two rows for {key}")
        seen.add(key)
        for t in r["takes"]:
            rec = record[t]
            if (rec["arm"], rec["agent"]["harness"], rec["model"], rec["task"]) != key:
                out.append(f"POOL: take {t} is not of the row {key}")
    return out


def _f(v: Fraction) -> str:
    return stats.intervals.fmt(v)


def render(rs: list, frame) -> str:
    bad = pool_problems(rs, frame)
    if bad:
        raise AgreementError("; ".join(bad))
    out = ["# Blind labels against the grader", "",
           "One row per task inside one arm, harness and model. Agreement is the panel's label equal to the grader's. "
           "Bounds are exact two-sided 0.95 (Clopper-Pearson); the carried-back figure weights each stratum by its "
           "frame size, with per-stratum exact bounds at the Bonferroni level.", "",
           "The labels are a Fable panel's, not a human's: on Javier's word a panel of Fable labellers, each labelling the sampled takes alone from the same blind sheet, with a majority deciding, stood in for his own labels. This page gives the code grader's agreement with a model panel, not with a person. Fable is a Claude model and the study has a Claude arm; this is disclosed as a limit.", "",
           "| Arm | Harness | Model | Task | Agreeing | Exact bounds | Carried back to the frame | Its bounds |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rs:
        if not r["n"]:
            out.append(f"| {r['arm']} | {r['harness']} | {r['model']} | {r['task']} | unsampled: no take drawn |  |  |  |")
            continue
        cb = r["carried"]
        back = ("a stratum unsampled", "") if cb is None else (_f(cb[0]), f"{_f(cb[1])} to {_f(cb[2])}")
        out.append(f"| {r['arm']} | {r['harness']} | {r['model']} | {r['task']} | {r['agree']} of {r['n']} | "
                   f"{r['bounds'][0]} to {r['bounds'][1]} | {back[0]} | {back[1]} |")
    out.append("")
    for r in (r for r in rs if r["n"]):
        out += [f"## Confusion, {r['arm']} {r['harness']} {r['model']} {r['task']}", "",
                "| Grader label | The panel's label | The panel's stop cause | Takes |", "|---|---|---|---|"]
        out += [f"| {g} | {h} | {s or 'blank'} | {k} |" for (g, h, s), k in sorted(r["matrix"].items())]
        out += ["", "| Verdict | Readers | In the frame | Drawn | Agreeing |", "|---|---|---|---|---|"]
        out += [f"| {s['verdict']} | {s['readers']} | {s['frame']} | {s['drawn']} | {s['agree']} |" for s in r["strata"]]
        out.append("")
    return "\n".join(out)


def _git(*args):
    got = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    return got.returncode, got.stdout


def history_problems(path=None, git=None) -> list:
    """labels.json published as read: exactly one commit in HEAD's history touches it, and the disk is that commit's."""
    path = LABELS if path is None else path
    git = _git if git is None else git
    rel = os.path.relpath(path, REPO).replace(os.sep, "/")
    rc, shallow = git("rev-parse", "--is-shallow-repository")
    if rc != 0 or shallow.strip() != "false":
        return ["HISTORY: the history cannot be read in full (a shallow clone or no git); refused"]
    rc, log = git("log", "--full-history", "--format=%H", "--", rel)
    shas = log.split()
    if rc != 0 or len(shas) != 1:
        return [f"HISTORY: {rel} is touched by {len(shas)} commits; the labels are committed once, as read"]
    rc, blob = git("show", f"{shas[0]}:{rel}")
    with open(path, encoding="utf-8") as fh:
        disk = fh.read()
    if rc != 0 or blob != disk:
        return [f"HISTORY: {rel} on disk is not the one commit's"]
    return []


def gone_problems(path=None, git=None, page=None) -> list:
    """With no labels.json on disk (review W11D-R1-1): no AGREEMENT.md may stand, and no commit in HEAD's history may
    ever have touched labels.json (labels once committed may not vanish). A shallow clone refuses."""
    path = LABELS if path is None else path
    git = _git if git is None else git
    out = []
    if os.path.isfile(PAGE if page is None else page):
        out.append("PAGE: AGREEMENT.md stands with no labels.json behind it")
    rel = os.path.relpath(path, REPO).replace(os.sep, "/")
    rc, shallow = git("rev-parse", "--is-shallow-repository")
    if rc != 0 or shallow.strip() != "false":
        return out + ["HISTORY: the history cannot be read in full (a shallow clone or no git); refused"]
    rc, log = git("log", "--full-history", "--format=%H", "--", rel)
    if rc != 0:
        return out + ["HISTORY: the history cannot be read in full (a shallow clone or no git); refused"]
    shas = log.split()
    if shas:
        out.append(f"HISTORY: {rel} was committed in {len(shas)} commit(s) and is gone; committed labels may not vanish")
    return out


def derive(labels_path=None, defs_path=None, frame_path=None, prereg=None, results=None, sample_path=None,
           glabels=None):
    """The page the committed labels give, or None when no sample or no labels are committed."""
    labels_path = LABELS if labels_path is None else labels_path
    if not os.path.isfile(labels_path):
        return None
    got = sample.derive(frame_path, prereg, results)
    if got is None:
        raise AgreementError("labels.json is committed and there is no sample to read it against")
    frame, design, smp = got
    with open(sample.SAMPLE if sample_path is None else sample_path, encoding="utf-8") as fh:
        if fh.read() != sample.render(smp):
            raise AgreementError("sample.json differs from the draw; run sample.py --check")
    with open(sheet.DEFINITIONS if defs_path is None else defs_path, encoding="utf-8") as fh:
        defs = json.load(fh)
    tasks = [i["stratum"]["task"] for i in smp["items"]]
    if glabels is None:
        glabels = {t: sheet.grader_labels(t) for t in set(tasks)}
    sheet.validate_definitions(defs, tasks, glabels)
    with open(labels_path, encoding="utf-8") as fh:
        labels = validate_labels(json.load(fh), smp, defs)
    return render(rows(frame, smp, labels), frame)


def check(page=None, labels_path=None, git=None, **kw) -> int:
    try:
        text = derive(labels_path, **kw)
    except (AgreementError, sheet.SheetError, sample.SampleError, stats.StatsError, OSError, ValueError) as err:
        print(f"agreement: FAIL {err}")
        return 1
    if text is None:
        gone = gone_problems(labels_path, git, page)
        for b in gone:
            print(f"agreement: FAIL {b}")
        if gone:
            return 1
        print("agreement: no labels; nothing measured. Not a pass on data.")
        return 0
    page = PAGE if page is None else page
    bad = history_problems(labels_path, git)
    if not os.path.isfile(page):
        bad.append("PAGE: no AGREEMENT.md; write it with --write")
    else:
        with open(page, encoding="utf-8") as fh:
            if fh.read() != text:
                bad.append("PAGE: AGREEMENT.md differs from what the committed labels give")
    for b in bad:
        print(f"agreement: FAIL {b}")
    if bad:
        return 1
    print("agreement: ok, every number re-derived from the committed labels")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    g.add_argument("--unmeasured", action="store_true")
    args = ap.parse_args(argv)
    if args.unmeasured:
        print(UNMEASURED)
        return 0
    if args.check:
        return check()
    try:
        text = derive()
    except (AgreementError, sheet.SheetError, sample.SampleError, stats.StatsError, OSError, ValueError) as err:
        print(f"agreement: FAIL {err}")
        return 1
    if text is None:
        print("agreement: no labels; nothing written")
        return 1
    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("agreement: wrote AGREEMENT.md")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
