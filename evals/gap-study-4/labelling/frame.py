#!/usr/bin/env python3
"""The labelling frame, labelling/frame.json, built from the committed takes (pre-freeze review 1, MAJOR 6 item 2).

    python3 evals/gap-study-4/labelling/frame.py --check    re-build the frame from the committed takes and refuse a
                                                            frame.json that differs (no takes and no frame: says so)
    python3 evals/gap-study-4/labelling/frame.py --write    write frame.json (after the freeze, once takes exist)

WHAT IT BUILDS. One entry per graded take with standing, in sample.py's closed shape: {"take": "<slot>/<attempt>",
"readers": "agree" | "disagree", "record": <the take's results record, unchanged>}. The records and their take ids
come from run.produce over the committed rows and history (the same road `run.py` writes records/ by): produce's
`records` and `audit` are parallel, one audit entry (slot, attempt) per record. A harness-error record has no
standing and is never in the frame (sample.validate_frame refuses one). Entries are sorted by take id.

THE FLAG. Each record carries its grader's human_sample and human_why (stats.TAKE_FIELDS, MAJOR 6 item 1), so the
frame carries the flag sample.py's flagged list reads.

READERS. "disagree" exactly when the record's human_why holds run.READERS_DISAGREE: scope_read's own evidence line
that the access log and the tool-call reader disagree, the comparison sample.py's docstring names. No other grader
compares those two readers, so every other take reads "agree". This is the lane's rule (pf1-l2b), written before any
take exists.

No model, no network, standard library only. Writes only frame.json, and only under --write.
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

import stats  # noqa: E402

FRAME = os.path.join(_HERE, "frame.json")
# The readers rule, registered in the draft as labelling_rules.readers (lane review 4): what the frame's `readers`
# means, which sets the sample's `disagree` oversampling factor.
READERS_RULE = ("A frame entry's readers is \"disagree\" exactly when its record's human_why holds readers-disagree, "
                "scope_read's own evidence that the access log and the tool-call reader disagree. Every other take, "
                "including every take outside scope_read, whose grader does not compare those two readers, reads "
                "\"agree\" by this registered rule, not by a measurement; the sample's disagree factor applies only "
                "to the first.")
AGREE, DISAGREE = "agree", "disagree"
READERS_DISAGREE = "readers-disagree"      # run.READERS_DISAGREE (a test binds the two)


class FrameError(ValueError):
    """A produced set of records the frame cannot be built from."""


def readers(record: dict) -> str:
    return DISAGREE if READERS_DISAGREE in record["human_why"] else AGREE


def build_frame(produced: dict) -> list:
    """The frame entries for run.produce's output: its records and its parallel audit (slot, attempt)."""
    records, audit = produced.get("records"), produced.get("audit")
    if not isinstance(records, list) or not isinstance(audit, list) or len(records) != len(audit):
        raise FrameError("run.produce's records and audit are two parallel lists")
    out, seen = [], set()
    for record, entry in zip(records, audit):
        stats.validate_record(record)
        if record["route"] in stats.LEAVES_DENOMINATOR:
            continue
        take = f"{entry['slot']}/{entry['attempt']}"
        if take in seen:
            raise FrameError(f"take {take} is produced twice")
        seen.add(take)
        out.append({"take": take, "readers": readers(record), "record": record})
    return sorted(out, key=lambda e: e["take"])


def render(frame: list) -> str:
    return json.dumps(frame, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def produced_now() -> dict | None:
    """run.produce over the committed rows and history, or None when there are no takes (nothing to build from)."""
    import prereg
    import run
    import takes
    rows, history = takes.load_rows(), takes.read_history()
    if not rows and not history:
        return None
    prereg.require_frozen("building the labelling frame")
    return run.produce(rows, history, run.grade_committed)


def check(frame_path=None, produced=None) -> int:
    frame_path = FRAME if frame_path is None else frame_path
    try:
        got = produced_now() if produced is None else produced
        if got is None:
            if os.path.isfile(frame_path):
                print("frame: FAIL frame.json stands with no takes to build it from")
                return 1
            print("frame: no takes; no frame built. Not a pass on data.")
            return 0
        text = render(build_frame(got))
    except (FrameError, stats.StatsError, ValueError, KeyError) as err:
        print(f"frame: FAIL {err}")
        return 1
    if not os.path.isfile(frame_path):
        print("frame: FAIL no frame.json; build it with --write")
        return 1
    with open(frame_path, encoding="utf-8") as fh:
        if fh.read() != text:
            print("frame: FAIL frame.json differs from the frame the committed takes give")
            return 1
    print(f"frame: ok, {len(json.loads(text))} takes, every one as the committed takes give it")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    try:
        got = produced_now()
        if got is None:
            print("frame: no takes; nothing built or written")
            return 1
        text = render(build_frame(got))
    except (FrameError, stats.StatsError, ValueError, KeyError) as err:
        print(f"frame: FAIL {err}")
        return 1
    with open(FRAME, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"frame: wrote {len(json.loads(text))} takes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
