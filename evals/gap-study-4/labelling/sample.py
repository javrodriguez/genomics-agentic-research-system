#!/usr/bin/env python3
"""CP8's blind sample: a fixed, seeded, stratified draw of about 80 graded takes for Javier's own labels (D6 A).

    python3 evals/gap-study-4/labelling/sample.py --pin      print the proposed design, its seed, its strata and its
                                                             sha256, for the freeze to pin
    python3 evals/gap-study-4/labelling/sample.py --check    re-derive the sample from the committed frame, results and
                                                             pre-registered design, and refuse any drift
    python3 evals/gap-study-4/labelling/sample.py --write    draw the sample and write sample.json (CP8 only)

WHAT IT READS. The frame, labelling/frame.json: one entry per graded take, {"take": <the take's id, slot and attempt>,
"readers": "agree" | "disagree", "record": <the take's results record, stats.TAKE_FIELDS, unchanged>}. `readers` says
whether the access log and the tool-call reader saw the same actions in that take. The frame binds to the committed
results (records/*.json, read through stats.load_results) both ways: every results record with standing is in the
frame exactly once and unchanged, and nothing else is. A harness-error record has no standing and is never in it.
The design, the frozen pre-registration's `labelling_design` (prereg.json, never the draft):

    {"seed": int, "about_n": int, "oversample": {"failure": int, "disagree": int},
     "strata": ["arm", "harness", "model", "task", "verdict", "readers"], "harness_models": {harness: [model, ...]}}

THE DRAW. A stratum is (arm, harness, model, task, verdict, readers); the verdict is the record's standing under the
strict view (stats.standing, "failures"), so a stop is a failure. One random.Random(seed) drives every random step.
  1 Every (arm, harness, model) cell in the frame gets an equal share of about_n; the remainder goes to cells the
    seeded generator picks. A cell smaller than its share gives every take it has (the sample can be under about_n).
  2 Inside a cell, the share is split over its strata in proportion to the stratum's size times its factor
    (oversample.failure for a failed take, oversample.disagree where the readers disagree, both for both), by largest
    remainder with ties broken on the stratum's sorted key, never past a stratum's size (the excess is split again
    among the strata still open).
  3 Each stratum's takes are sorted by id and the generator draws its count from them.
  4 The drawn takes are shuffled by the same generator and numbered L001, L002, ... in that order, so the sheet's
    order says nothing about the strata.
Every item carries its stratum and the stratum's size in the frame and its drawn count: the weights agreement.py uses
to carry each stratum back to the frame. Every design model must have a take in the frame (the sample is stratified
over each one), else the draw refuses.

WHAT THE SHEET RECEIVES. Nothing from here directly: sheet.py takes from each item its sheet id and task, and nothing
else, and sample.json itself (which names model, harness and arm) is the key the labeller never opens.

No model, no network, standard library only. Writes only sample.json, and only under --write.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
from fractions import Fraction

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
for _p in (_STUDY, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import stats  # noqa: E402

HERE = _HERE
STUDY = _STUDY
FRAME = os.path.join(HERE, "frame.json")
SAMPLE = os.path.join(HERE, "sample.json")
PREREG = os.path.join(STUDY, "prereg.json")
DRAFT = os.path.join(STUDY, "prereg-draft.json")
RESULTS = os.path.join(STUDY, "records")
DESIGN_KEY = "labelling_design"

STRATA = ("arm", "harness", "model", "task", "verdict", "readers")
READERS = ("agree", "disagree")
DESIGN_FIELDS = ("seed", "about_n", "oversample", "strata", "harness_models")
OVERSAMPLE_FIELDS = ("failure", "disagree")
ENTRY_FIELDS = ("take", "readers", "record")
STRICT_VIEW = "failures"
FAILED = "wrong"
TAKE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
# The proposed design (glitch-2f's to rule at the freeze; Q-w11d-1). The seed is a date, chosen before any take exists.
PROPOSED = {"seed": 20261012, "about_n": 80, "oversample": {"failure": 3, "disagree": 3}, "strata": list(STRATA)}


class SampleError(Exception):
    """A design, frame or sample the draw refuses."""


def _count(v, least: int) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= least


def validate_design(d) -> dict:
    """The design, or SampleError naming what is wrong with it."""
    if not isinstance(d, dict) or set(d) != set(DESIGN_FIELDS):
        raise SampleError(f"the design holds exactly {DESIGN_FIELDS}")
    if not _count(d["seed"], 0):
        raise SampleError("seed is a non-negative int")
    if not _count(d["about_n"], 1):
        raise SampleError("about_n is a positive int")
    o = d["oversample"]
    if not isinstance(o, dict) or set(o) != set(OVERSAMPLE_FIELDS):
        raise SampleError(f"oversample holds exactly {OVERSAMPLE_FIELDS}")
    for k in OVERSAMPLE_FIELDS:
        if not _count(o[k], 1):
            raise SampleError(f"oversample.{k} is an int of at least 1")
    if d["strata"] != list(STRATA):
        raise SampleError(f"strata is exactly {list(STRATA)}")
    hm = d["harness_models"]
    if not isinstance(hm, dict) or not hm:
        raise SampleError("harness_models names at least one harness")
    seen = set()
    for harness, models in hm.items():
        if not stats._id(harness) or not isinstance(models, list) or not models:
            raise SampleError(f"harness {harness!r} lists at least one model")
        for m in models:
            if not stats._id(m) or m in seen:
                raise SampleError(f"model {m!r} is not an id, or is listed twice")
            seen.add(m)
    return d


def canonical(d) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def design_sha(d) -> str:
    """The sha256 of the design's canonical text: what the freeze pins and every sample carries."""
    return hashlib.sha256(canonical(validate_design(d)).encode()).hexdigest()


def design_pin(d) -> str:
    """The text the freeze pins: the seed, the strata, the canonical design and its sha256 (design_sha validates)."""
    return f"seed {d['seed']}\nstrata {', '.join(d['strata'])}\ndesign {canonical(d)}\nsha256 {design_sha(d)}"


def validate_frame(frame, design) -> list:
    """The frame's entries, or SampleError."""
    if not isinstance(frame, list):
        raise SampleError("the frame is a list of entries")
    models = {m: h for h, ms in design["harness_models"].items() for m in ms}
    takes = set()
    for e in frame:
        if not isinstance(e, dict) or set(e) != set(ENTRY_FIELDS):
            raise SampleError(f"a frame entry holds exactly {ENTRY_FIELDS}")
        if not isinstance(e["take"], str) or not TAKE_ID.fullmatch(e["take"]):
            raise SampleError(f"take {e['take']!r} is not a take id")
        if e["take"] in takes:
            raise SampleError(f"take {e['take']} is in the frame twice")
        takes.add(e["take"])
        if e["readers"] not in READERS:
            raise SampleError(f"readers {e['readers']!r} is not one of {READERS}")
        try:
            r = stats.validate_record(e["record"])
        except stats.StatsError as err:
            raise SampleError(f"take {e['take']}: {err}") from err
        if r["route"] in stats.LEAVES_DENOMINATOR:
            raise SampleError(f"take {e['take']} has no standing ({r['route']}) and is never in the frame")
        if models.get(r["model"]) != r["agent"]["harness"]:
            raise SampleError(f"take {e['take']}: model {r['model']} under {r['agent']['harness']} is not in the design")
    try:
        stats.check_records([e["record"] for e in frame])
    except stats.StatsError as err:
        raise SampleError(str(err)) from err
    missing = sorted(set(models) - {e["record"]["model"] for e in frame})
    if missing:
        raise SampleError(f"no take in the frame for {missing}: the sample is stratified over every design model")
    return frame


def frame_problems(frame, results) -> list:
    """The frame against the committed results, both ways: every record with standing exactly once, unchanged."""
    want = [r for r in results if r["route"] not in stats.LEAVES_DENOMINATOR]
    have = [e["record"] for e in frame]
    out = [f"BIND: results record {stats.try_key(r)} is not in the frame" for r in want if r not in have]
    out += [f"BIND: frame record {stats.try_key(r)} is not a committed results record" for r in have if r not in want]
    if len(have) != len(want):
        out.append(f"BIND: the frame holds {len(have)} records, the results {len(want)} with standing")
    return out


def verdict(e: dict) -> str:
    return stats.standing(e["record"], STRICT_VIEW)


def stratum(e: dict) -> tuple:
    r = e["record"]
    return (r["arm"], r["agent"]["harness"], r["model"], r["task"], verdict(e), e["readers"])


def factor(key: tuple, design: dict) -> int:
    f = design["oversample"]["failure"] if key[4] == FAILED else 1
    return f * (design["oversample"]["disagree"] if key[5] == "disagree" else 1)


def split(quota: int, weights: dict, caps: dict) -> dict:
    """quota over the keys in proportion to weights, by largest remainder (ties on the sorted key), never past a cap."""
    out = {k: 0 for k in weights}
    open_ = sorted(k for k in weights if caps[k] > 0)
    left = quota
    while left > 0:                    # with every stratum capped, one pass with nothing open ends the loop
        total = sum(weights[k] for k in open_)
        share = {k: Fraction(left * weights[k], total) for k in open_}
        give = {k: int(share[k]) for k in open_}
        rest = left - sum(give.values())
        for k in sorted(open_, key=lambda k: (give[k] - share[k], k))[:rest]:
            give[k] += 1
        capped = [k for k in open_ if give[k] >= caps[k]]
        if not capped:
            for k in open_:
                out[k] = give[k]
            left = 0
        for k in capped:
            out[k] = caps[k]
            left -= caps[k]
        open_ = [k for k in open_ if k not in capped]
    return out


def draw(frame, design) -> dict:
    """The sample document for this frame and design (validated); the same inputs give the same bytes."""
    validate_design(design)
    validate_frame(frame, design)
    rng = random.Random(design["seed"])
    groups = {}
    for e in frame:
        groups.setdefault(stratum(e), []).append(e["take"])
    cells = sorted({k[:3] for k in groups})
    quota = {c: design["about_n"] // len(cells) for c in cells}
    for c in rng.sample(cells, design["about_n"] % len(cells)):
        quota[c] += 1
    counts = {}
    for c in cells:
        keys = [k for k in groups if k[:3] == c]
        counts.update(split(quota[c], {k: len(groups[k]) * factor(k, design) for k in keys},
                            {k: len(groups[k]) for k in keys}))
    picked = []
    for k in sorted(groups):
        picked += [(t, k) for t in rng.sample(sorted(groups[k]), counts[k])]
    rng.shuffle(picked)
    items = [{"sheet_id": f"L{i:03d}", "take": t, "stratum": dict(zip(STRATA, k)),
              "frame": len(groups[k]), "drawn": counts[k]} for i, (t, k) in enumerate(picked, start=1)]
    return {"design_sha256": design_sha(design), "seed": design["seed"], "strata": list(STRATA), "items": items}


def render(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=True) + "\n"


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_design(prereg=None) -> dict:
    prereg = PREREG if prereg is None else prereg
    if not os.path.isfile(prereg):
        raise SampleError("no frozen pre-registration (prereg.json): the labelling design is pinned at the freeze")
    d = _read(prereg)
    if DESIGN_KEY not in d:
        raise SampleError(f"prereg.json carries no {DESIGN_KEY}")
    return validate_design(d[DESIGN_KEY])


def derive(frame_path=None, prereg=None, results=None):
    """(frame, design, sample document), or None when there is no frame and no results: nothing to draw from.
    A path left None is the study's own (the module's FRAME, PREREG and RESULTS, read when called)."""
    frame_path = FRAME if frame_path is None else frame_path
    recs = stats.load_results(RESULTS if results is None else results)
    if not os.path.isfile(frame_path) and not recs:
        return None
    if not os.path.isfile(frame_path):
        raise SampleError("results are committed and no frame is: frame.json binds the sample to them")
    frame = _read(frame_path)
    design = read_design(prereg)
    validate_frame(frame, design)
    bad = frame_problems(frame, recs)
    if bad:
        raise SampleError("; ".join(bad))
    return frame, design, draw(frame, design)


def check(frame_path=None, prereg=None, results=None, sample_path=None) -> int:
    try:
        got = derive(frame_path, prereg, results)
    except (SampleError, stats.StatsError) as err:
        print(f"sample: FAIL {err}")
        return 1
    if got is None:
        print("sample: no takes (no frame and no results); nothing was drawn. Not a pass on data.")
        return 0
    doc = got[2]
    sample_path = SAMPLE if sample_path is None else sample_path
    print(f"sample: seed {doc['seed']}; strata {', '.join(doc['strata'])}; design sha256 {doc['design_sha256']}")
    if not os.path.isfile(sample_path):
        print("sample: FAIL no sample.json; draw it with --write")
        return 1
    with open(sample_path, encoding="utf-8") as fh:
        if fh.read() != render(doc):
            print("sample: FAIL sample.json differs from the draw the frame and the design give")
            return 1
    print(f"sample: ok, {len(doc['items'])} takes drawn as the design gives them")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pin", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    if args.pin:
        design = dict(PROPOSED, harness_models=_read(DRAFT)["stats_design_inputs"]["harness_models"])
        print(design_pin(design))
        return 0
    if args.check:
        return check()
    try:
        got = derive()
    except (SampleError, stats.StatsError) as err:
        print(f"sample: FAIL {err}")
        return 1
    if got is None:
        print("sample: no takes; nothing drawn or written")
        return 1
    with open(SAMPLE, "w", encoding="utf-8") as fh:
        fh.write(render(got[2]))
    print(f"sample: wrote {len(got[2]['items'])} takes; seed {got[2]['seed']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
