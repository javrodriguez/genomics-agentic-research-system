#!/usr/bin/env python3
"""The flagged check list's verdict record: what the person who reads the list finds on each listed take.

    python3 evals/gap-study-4/labelling/flagged_verdicts.py --check    validate the committed record against the drawn
                                                                       list and its history; no record, said out loud

Pre-freeze review 2, m8 (FOLD-PLAN-prefreeze-2.md section 3, lane fold2-ld, Thu 29 Oct 2026, under Javier's
delegation to glitch-45). The flagged list (sample.flagged_list, OD127: on, a cap of 40) is the only safeguard of the
routed residuals, and before this record nothing committed or published what a person found on it, so the safeguard
measured nothing visible. Javier's load is unchanged: the same list, up to the same cap, read in the same order.

THE RECORD. labelling/flagged-verdicts.json: {"verdicts": [{"sheet_id", "finding", "note"}]}, one row for every item
the drawn list holds (F001, ...), each exactly once and no other id; `finding` is one of FINDINGS, read against the
take's grader reading as the flagged sheet shows it:
  grader-right   the grader's reading of the take stands;
  grader-wrong   the grader's reading of the take is wrong;
  cannot-tell    the take's text and actions do not settle it;
and `note` is free text (may be empty), never read by any number. A partial record is refused: a list read in part
would let the findings shown be chosen.

COMMITTED ONCE, AFTER THE BLIND LABELS. history_problems: exactly one commit in HEAD's history touches the record, the
file on disk is that commit's, the history is read in full (a shallow clone refuses), and the blind sheet's labels
(labels.json) are already committed as read (sheet.blind_labels_problems), the order the draft registers
(labelling_rules.order). The record is run output: check_results.RUNTIME_PATHS names it, so none sits in the build or
freeze commit.

PUBLISHED. result.py prints, per (arm, harness, model, task) of the list and never across them, the listed takes and
the count of each finding, beside the views; with no record, each row prints its listed count and "not read".

No model, no network, standard library only. Read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
for _p in (_STUDY, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agreement  # noqa: E402
import sample  # noqa: E402

VERDICTS_NAME = "flagged-verdicts.json"
VERDICTS = os.path.join(_HERE, VERDICTS_NAME)
VERDICT_FIELDS = ("sheet_id", "finding", "note")
FINDINGS = ("grader-right", "grader-wrong", "cannot-tell")
ROW_KEY = ("arm", "harness", "model", "task")


class VerdictError(ValueError):
    """A verdict record the flagged list refuses."""


def listed_items(smp: dict) -> list:
    fl = smp.get("flagged") if isinstance(smp, dict) else None
    if not isinstance(fl, dict) or not isinstance(fl.get("items"), list):
        raise VerdictError("the sample carries no flagged list: labelling_design.flagged_list is null")
    return fl["items"]


def validate_verdicts(doc, smp: dict) -> dict:
    """{sheet_id: finding} for every item of the sample's flagged list, or VerdictError."""
    items = {i["sheet_id"]: i for i in listed_items(smp)}
    if not isinstance(doc, dict) or set(doc) != {"verdicts"} or not isinstance(doc["verdicts"], list):
        raise VerdictError('flagged-verdicts.json is {"verdicts": [...]}')
    out = {}
    for e in doc["verdicts"]:
        if not isinstance(e, dict) or set(e) != set(VERDICT_FIELDS):
            raise VerdictError(f"a verdict row holds exactly {VERDICT_FIELDS}")
        sid = e["sheet_id"]
        if sid not in items:
            raise VerdictError(f"{sid!r} is not an item of the drawn flagged list")
        if sid in out:
            raise VerdictError(f"{sid} has two verdict rows")
        if e["finding"] not in FINDINGS:
            raise VerdictError(f"{sid}: finding {e['finding']!r} is not one of {FINDINGS}")
        if not isinstance(e["note"], str):
            raise VerdictError(f"{sid}: the note is text")
        out[sid] = e["finding"]
    missing = sorted(set(items) - set(out))
    if missing:
        raise VerdictError(f"listed items with no verdict row: {missing}; the list is read whole or not recorded")
    return out


def verdict_rows(smp: dict, found) -> list:
    """Per (arm, harness, model, task) of the list, in key order: {arm, harness, model, task, listed, and each finding's
    count}, every count None when `found` is None (no record yet)."""
    rows = {}
    for it in listed_items(smp):
        st = it["stratum"]
        key = tuple(st[k] for k in ROW_KEY)
        r = rows.setdefault(key, {**dict(zip(ROW_KEY, key)), "listed": 0,
                                  **{f: (None if found is None else 0) for f in FINDINGS}})
        r["listed"] += 1
        if found is not None:
            r[found[it["sheet_id"]]] += 1
    return [rows[k] for k in sorted(rows)]


def read(smp: dict, path=None):
    """The validated findings of the record on disk, or None when there is no record."""
    path = VERDICTS if path is None else path
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        try:
            doc = json.load(fh)
        except ValueError as err:
            raise VerdictError(f"{VERDICTS_NAME} is not JSON: {err}") from None
    return validate_verdicts(doc, smp)


def history_problems(path=None, git=None, *, labels_problems=None) -> list:
    """The record committed once, as read, after the blind labels (agreement.history_problems' rule on this path, plus
    the blind labels committed first)."""
    path = VERDICTS if path is None else path
    if labels_problems is None:
        labels_problems = (["no labels.json: the blind sheet is not labelled yet"]
                           if not os.path.isfile(agreement.LABELS) else agreement.history_problems())
    out = [f"ORDER: the verdict record stands before the blind labels are committed: {p}" for p in labels_problems]
    return out + [p.replace("the labels are committed once", "the verdicts are committed once")
                  for p in agreement.history_problems(path, git)]


def check(path=None, git=None, smp=None) -> int:
    path = VERDICTS if path is None else path
    if not os.path.isfile(path):
        print("flagged_verdicts: no verdict record; the flagged list's findings are not read. Not a pass on data.")
        return 0
    try:
        if smp is None:
            got = sample.derive()
            if got is None:
                raise VerdictError("a verdict record is on disk and there is no sample to read it against")
            smp = got[2]
        read(smp, path)
    except (VerdictError, OSError, ValueError, KeyError, TypeError) as err:
        print(f"flagged_verdicts: FAIL {err}")
        return 1
    bad = history_problems(path, git)
    for b in bad:
        print(f"flagged_verdicts: FAIL {b}")
    if bad:
        return 1
    print(f"flagged_verdicts: ok, {len(listed_items(smp))} listed item(s), each with one committed finding")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", required=True)
    ap.parse_args(argv)
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
