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
file on disk is that commit's, the history is read in full (a shallow clone refuses), labels.json is committed once
as read (agreement.history_problems), and the record's one commit descends from labels.json's one commit and is not
it (git merge-base --is-ancestor), the order the draft registers (labelling_rules.order). NEVER GONE (gone_problems,
agreement.gone_problems' rule): with no record on disk, no commit may ever have touched it, so findings once committed
cannot vanish and read as "not read". The page publishes only through published(): the record when its history
holds, "not read" only when none was ever committed, and a refusal otherwise. The record is run output: check_results.RUNTIME_PATHS names it, so none sits in the build or
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


def _rel(path) -> str:
    return os.path.relpath(path, agreement.REPO).replace(os.sep, "/")


def _one_commit(git, path):
    """The one commit in HEAD's full history that touches `path`, or None (none, several, or unreadable)."""
    rc, log = git("log", "--full-history", "--format=%H", "--", _rel(path))
    shas = log.split() if rc == 0 else []
    return shas[0] if len(shas) == 1 else None


def history_problems(path=None, git=None, *, labels_problems=None, labels_path=None) -> list:
    """The record committed once, as read (agreement.history_problems' rule on this path), and after the blind labels:
    labels.json is committed as read (sheet's order), and the record's one commit descends from labels.json's one
    commit and is not that commit (review of 4928c592, MINOR 1: an order read from history, not from what stands at
    check time)."""
    path = VERDICTS if path is None else path
    git = agreement._git if git is None else git
    labels_path = agreement.LABELS if labels_path is None else labels_path
    if labels_problems is None:
        labels_problems = (["no labels.json: the blind sheet is not labelled yet"]
                           if not os.path.isfile(labels_path) else agreement.history_problems(labels_path, git))
    out = [f"ORDER: the verdict record stands before the blind labels are committed: {p}" for p in labels_problems]
    out += [p.replace("the labels are committed once", "the verdicts are committed once")
            for p in agreement.history_problems(path, git)]
    mine, labels = _one_commit(git, path), _one_commit(git, labels_path)
    if mine is not None:
        if labels is None:
            out.append("ORDER: labels.json is not committed once in HEAD's history, so the record cannot follow it")
        elif labels == mine:
            out.append(f"ORDER: the verdict record and labels.json are committed together ({mine[:12]}); the blind "
                       f"labels are committed first")
        elif git("merge-base", "--is-ancestor", labels, mine)[0] != 0:
            out.append(f"ORDER: the verdict record's commit {mine[:12]} does not descend from labels.json's commit "
                       f"{labels[:12]}")
    return out


def gone_problems(path=None, git=None) -> list:
    """Review of 4928c592, MAJOR 1 (agreement.gone_problems' rule, review W11D-R1-1): with no record on disk, no commit
    in HEAD's full history may ever have touched it (findings once committed may not vanish and read as not read); a
    shallow clone refuses."""
    path = VERDICTS if path is None else path
    git = agreement._git if git is None else git
    rc, shallow = git("rev-parse", "--is-shallow-repository")
    if rc != 0 or shallow.strip() != "false":
        return ["HISTORY: the history cannot be read in full (a shallow clone or no git); refused"]
    rc, log = git("log", "--full-history", "--format=%H", "--", _rel(path))
    if rc != 0:
        return ["HISTORY: the history cannot be read in full (a shallow clone or no git); refused"]
    shas = log.split()
    if shas:
        return [f"HISTORY: {_rel(path)} was committed in {len(shas)} commit(s) and is gone; committed findings may "
                f"not vanish"]
    return []


def published(smp: dict, path=None, *, history=None, gone=None):
    """What the page may publish (review of 4928c592, NIT 3): the validated findings only when the record's history
    holds, None only when no record ever was; anything else is VerdictError, never shown as read or as not read.
    `history(path)` and `gone(path)` stand in for history_problems and gone_problems (tests)."""
    path = VERDICTS if path is None else path
    if not os.path.isfile(path):
        bad = (gone_problems if gone is None else gone)(path)
        if bad:
            raise VerdictError("; ".join(bad))
        return None
    found = read(smp, path)
    bad = (history_problems if history is None else history)(path)
    if bad:
        raise VerdictError("; ".join(bad))
    return found


def check(path=None, git=None, smp=None) -> int:
    path = VERDICTS if path is None else path
    if not os.path.isfile(path):
        bad = gone_problems(path, git)
        for b in bad:
            print(f"flagged_verdicts: FAIL {b}")
        if bad:
            return 1
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
