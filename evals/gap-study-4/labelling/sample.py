#!/usr/bin/env python3
"""CP8's blind sample: a fixed, seeded, stratified draw of about 80 graded takes for Javier's own labels (D6 A).

    python3 evals/gap-study-4/labelling/sample.py --pin      print the proposed design, its seed, its strata and its
                                                             sha256, for the freeze to pin
    python3 evals/gap-study-4/labelling/sample.py --check    re-derive the sample from the committed frame, results and
                                                             pre-registered design, and refuse any drift
    python3 evals/gap-study-4/labelling/sample.py --write    draw the sample and write sample.json (CP8 only)

WHAT IT READS. The frame, labelling/frame.json: one entry per graded take, {"take": <the take's id, slot and attempt>,
"readers": "agree" | "disagree", "record": <the take's results record, stats.TAKE_FIELDS, unchanged>}. `readers` is
"disagree" when scope_read's two readers disagree, else "agree" by registered rule (labelling_rules), not measured. The frame binds to the committed
results (records/*.json, read through stats.load_results) both ways: every results record with standing is in the
frame exactly once and unchanged, and nothing else is. A harness-error record has no standing and is never in it.
The design, the frozen pre-registration's `labelling_design` (prereg.json, never the draft):

    {"seed": int, "about_n": int, "oversample": {"failure": int, "disagree": int}, "flagged_list": None | {"cap": ...},
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
to carry each stratum back to the frame. A sample.json with no frame and no results to derive it from fails --check
(review W11D-R1-1): a drawn sample never stands without what it was drawn from. Every design model must have a take in the frame (the sample is stratified
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
SAMPLE_FOLLOWUP = os.path.join(HERE, "sample-followup.json")      # lane gemini-defer, R4
PREREG = os.path.join(STUDY, "prereg.json")
DRAFT = os.path.join(STUDY, "prereg-draft.json")
RESULTS = os.path.join(STUDY, "records")
DESIGN_KEY = "labelling_design"

STRATA = ("arm", "harness", "model", "task", "verdict", "readers")
READERS = ("agree", "disagree")
DESIGN_FIELDS = ("seed", "about_n", "oversample", "strata", "harness_models", "flagged_list")
OVERSAMPLE_FIELDS = ("failure", "disagree")
ENTRY_FIELDS = ("take", "readers", "record")
STRICT_VIEW = "failures"
FAILED = "wrong"
ORIGINAL, FOLLOWUP = "original", "followup"                         # lane gemini-defer, R4: the two parts of a draw
DEFERRED = "deferred"
TAKE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
# THE FLAGGED LIST (pre-freeze review 1, MAJOR 6 item 3; lane pf1-l2b, Sat 24 Oct 2026). A take its grader sent to the
# human sample (its record's human_sample, carried from the grade by run.record_for) is seen by a person only if it is
# drawn. Whether every flagged take goes to Javier as a separate, non-blind check list beside the blind draw, and how
# many at most, is his (ask gap-flag-list: he is the labeller). This one switch holds his answer and nothing else
# reads another: None (OFF, the default until he answers) draws no list and leaves every sample byte as before; a
# dict {"cap": <a positive int, or None for no cap>} draws the list (see draw()). It enters the pre-registered design
# as `flagged_list` (PROPOSED below, which build_draft registers as labelling_design), so either answer changes this
# one line and the draft is rebuilt from it.
FLAGGED_LIST = {"cap": 40}  # Javier's yes to ask gap-flag-list, OD127 (Sat 24 Oct 2026): the non-blind list, cap 40
FLAGGED_PREFIX = "F"                    # the flagged list's sheet ids, F001, F002, ...; the blind draw's are L001, ...
# The proposed design (glitch-2f's to rule at the freeze; Q-w11d-1). The seed is a date, chosen before any take exists.
PROPOSED = {"seed": 20261012, "about_n": 80, "oversample": {"failure": 3, "disagree": 3}, "strata": list(STRATA),
            "flagged_list": FLAGGED_LIST}


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
    fl = d["flagged_list"]
    if fl is not None and (not isinstance(fl, dict) or set(fl) != {"cap"} or
                           (fl["cap"] is not None and not _count(fl["cap"], 1))):
        raise SampleError("flagged_list is None (no flagged list) or {'cap': a positive int or None}")
    return d


def canonical(d) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def design_sha(d) -> str:
    """The sha256 of the design's canonical text: what the freeze pins and every sample carries."""
    return hashlib.sha256(canonical(validate_design(d)).encode()).hexdigest()


def design_pin(d) -> str:
    """The text the freeze pins: the seed, the strata, the canonical design and its sha256 (design_sha validates)."""
    return f"seed {d['seed']}\nstrata {', '.join(d['strata'])}\ndesign {canonical(d)}\nsha256 {design_sha(d)}"


def validate_frame(frame, design, exempt=()) -> list:
    """The frame's entries, or SampleError. `exempt` names design models that may have no take (lane gemini-defer:
    a deferred arm's models in the original draw, the run models in a follow-up)."""
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
    missing = sorted(set(models) - set(exempt) - {e["record"]["model"] for e in frame})
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


# A DEFERRED ARM (lane gemini-defer, ruling R4, glitch-f1 under Javier's standing delegation, 22 Oct 2026). An arm in
# the frozen pre-registration's `deferred_arms` (arm G, deferred by Javier on 22 Oct 2026) is registered in full and not
# run in the original report. Its cells are withheld: the quota is still computed over every (arm, harness, model) cell
# of the full design (the frame's cells and the withheld ones, steps 1 above unchanged), so each run cell keeps the share
# it has in the full seven-model design, and only the run cells are drawn (part "original"). A follow-up, only after a
# committed go record (prereg.GO_KEYS, read at HEAD), draws the withheld cells under the same design and the same quota
# (part "followup", written to sample-followup.json; --check reads it beside sample.json once a go exists). With nothing
# deferred the draw and its bytes are exactly as before.
def deferred_cells(doc: dict, design: dict) -> tuple:
    """The (arm, harness, model) cells of the pre-registration's deferred arms (lane gemini-defer, R4), sorted; each
    model of a deferred arm (the design's `models[arm]`, else the entry's own `models`) must be a design model."""
    table = doc.get("deferred_arms") or {}
    if not isinstance(table, dict):
        raise SampleError("deferred_arms maps an arm to its deferral")
    harness_of = {m: h for h, ms in design["harness_models"].items() for m in ms}
    arms = doc.get("models") if isinstance(doc.get("models"), dict) else {}
    out = set()
    for arm, entry in table.items():
        if not isinstance(entry, dict) or entry.get("status") != DEFERRED:
            raise SampleError(f"deferred_arms.{arm} is not a deferral")
        models = arms.get(arm) or entry.get("models")
        if not models:
            raise SampleError(f"the deferred arm {arm} names no models")
        for m in models:
            if m not in harness_of:
                raise SampleError(f"the deferred model {m!r} is not in the design")
            out.add((arm, harness_of[m], m))
    return tuple(sorted(out))


def draw(frame, design, deferred=(), part=ORIGINAL) -> dict:
    """The sample document for this frame and design (validated); the same inputs give the same bytes.

    `deferred` (lane gemini-defer, R4) names the withheld (arm, harness, model) cells: the quota covers them as cells
    of the full design, the original part draws every other cell and the follow-up part only them."""
    validate_design(design)
    deferred = tuple(sorted(tuple(c) for c in deferred))
    if part not in (ORIGINAL, FOLLOWUP) or (part == FOLLOWUP and not deferred):
        raise SampleError(f"a draw is the original part, or a follow-up of deferred cells; got {part!r}")
    held_models = {c[2] for c in deferred}
    run_models = {m for ms in design["harness_models"].values() for m in ms} - held_models
    validate_frame(frame, design, exempt=held_models if part == ORIGINAL else run_models)
    rng = random.Random(design["seed"])
    groups = {}
    for e in frame:
        groups.setdefault(stratum(e), []).append(e["take"])
    cells = sorted({k[:3] for k in groups} | set(deferred))
    quota = {c: design["about_n"] // len(cells) for c in cells}
    for c in rng.sample(cells, design["about_n"] % len(cells)):
        quota[c] += 1
    drawn = [c for c in cells if (c in deferred) == (part == FOLLOWUP)]
    groups = {k: v for k, v in groups.items() if k[:3] in drawn}
    counts = {}
    for c in drawn:
        keys = [k for k in groups if k[:3] == c]
        counts.update(split(quota[c], {k: len(groups[k]) * factor(k, design) for k in keys},
                            {k: len(groups[k]) for k in keys}))
    picked = []
    for k in sorted(groups):
        picked += [(t, k) for t in rng.sample(sorted(groups[k]), counts[k])]
    rng.shuffle(picked)
    items = [{"sheet_id": f"L{i:03d}", "take": t, "stratum": dict(zip(STRATA, k)),
              "frame": len(groups[k]), "drawn": counts[k]} for i, (t, k) in enumerate(picked, start=1)]
    doc = {"design_sha256": design_sha(design), "seed": design["seed"], "strata": list(STRATA), "items": items}
    if deferred:
        doc.update(part=part, withheld=[list(c) for c in deferred])
    if design["flagged_list"] is not None:                  # MAJOR 6 item 3: only when the switch is on
        doc["flagged"] = flagged_list(frame, design, drawn)
    return doc


def flagged_list(frame, design, drawn) -> dict:
    """MAJOR 6 item 3: every flagged take (record human_sample True) of the drawn (arm, harness, model) cells, outside
    the blind draw and drawn whole: sorted by take id and numbered F001, F002, ...; when design.flagged_list.cap is an
    int below their number, a draw of cap of them by random.Random(f"{seed}|flagged") (never the blind draw's
    generator, so the blind draw is the same either way), with the count beyond the cap published beside the list.
    Each item carries its take, its human_why and its stratum: the list is not blind, and a take may sit in both."""
    cells = set(drawn)
    flagged = sorted((e for e in frame if e["record"]["human_sample"] is True and stratum(e)[:3] in cells),
                     key=lambda e: e["take"])
    cap = design["flagged_list"]["cap"]
    chosen = flagged
    if cap is not None and len(flagged) > cap:
        keep = set(random.Random(f"{design['seed']}|flagged").sample([e["take"] for e in flagged], cap))
        chosen = [e for e in flagged if e["take"] in keep]
    items = [{"sheet_id": f"{FLAGGED_PREFIX}{i:03d}", "take": e["take"], "why": list(e["record"]["human_why"]),
              "stratum": dict(zip(STRATA, stratum(e)))} for i, e in enumerate(chosen, start=1)]
    return {"cap": cap, "flagged": len(flagged), "listed": len(items), "beyond_cap": len(flagged) - len(items),
            "items": items}


def render(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=True) + "\n"


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_prereg(prereg=None) -> tuple:
    """(the labelling design, the deferred cells) from the frozen pre-registration."""
    prereg = PREREG if prereg is None else prereg
    if not os.path.isfile(prereg):
        raise SampleError("no frozen pre-registration (prereg.json): the labelling design is pinned at the freeze")
    d = _read(prereg)
    if DESIGN_KEY not in d:
        raise SampleError(f"prereg.json carries no {DESIGN_KEY}")
    design = validate_design(d[DESIGN_KEY])
    return design, deferred_cells(d, design)


def read_design(prereg=None) -> dict:
    return read_prereg(prereg)[0]


def released(deferred, go=None) -> bool:
    """True when every deferred arm has a committed go record (prereg.deferred_arm_go); `go` None reads the records
    committed at HEAD (prereg.committed_go_records)."""
    import prereg as prereg_door
    return bool(deferred) and all(prereg_door.deferred_arm_go(arm, go) for arm in {c[0] for c in deferred})


def derive(frame_path=None, prereg=None, results=None, part=ORIGINAL, go=None):
    """(frame, design, sample document), or None when there is no frame and no results: nothing to draw from.
    A path left None is the study's own (the module's FRAME, PREREG and RESULTS, read when called). The follow-up
    part (lane gemini-defer, R4) is refused until every deferred arm has a committed go record."""
    frame_path = FRAME if frame_path is None else frame_path
    recs = stats.load_results(RESULTS if results is None else results)
    if not os.path.isfile(frame_path) and not recs:
        return None
    if not os.path.isfile(frame_path):
        raise SampleError("results are committed and no frame is: frame.json binds the sample to them")
    frame = _read(frame_path)
    design, deferred = read_prereg(prereg)
    if part == FOLLOWUP and not released(deferred, go):
        raise SampleError("the follow-up draw of the deferred arm waits for a committed go record by Javier "
                          "(deferred-arm-go.json)")
    # the frame's shape before it is bound; draw() then requires the part's own models
    validate_frame(frame, design, exempt={c[2] for c in deferred})
    bad = frame_problems(frame, recs)
    if bad:
        raise SampleError("; ".join(bad))
    return frame, design, draw(frame, design, deferred, part)


def check_followup(frame_path, prereg, results, followup_path, go) -> int:
    """Lane gemini-defer, R4: once a go is committed, sample-followup.json must be the follow-up draw."""
    try:
        doc = derive(frame_path, prereg, results, FOLLOWUP, go)[2]
    except (SampleError, stats.StatsError, TypeError) as err:
        print(f"sample: FAIL follow-up: {err}")
        return 1
    followup_path = SAMPLE_FOLLOWUP if followup_path is None else followup_path
    if not os.path.isfile(followup_path):
        print("sample: FAIL a go record is committed and there is no sample-followup.json; draw it with "
              "--write-followup")
        return 1
    with open(followup_path, encoding="utf-8") as fh:
        held = fh.read()
        if held != render(doc):
            print("sample: FAIL sample-followup.json differs from the follow-up draw")
            return 1
    print(f"sample: follow-up ok, {len(doc['items'])} takes drawn from the deferred cells")
    return 0


def check(frame_path=None, prereg=None, results=None, sample_path=None, go=None, followup_path=None) -> int:
    try:
        got = derive(frame_path, prereg, results, go=go)
    except (SampleError, stats.StatsError) as err:
        print(f"sample: FAIL {err}")
        return 1
    if got is None:
        if os.path.isfile(SAMPLE if sample_path is None else sample_path):
            print("sample: FAIL sample.json stands with no frame or results to derive it from")
            return 1
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
    deferred = [tuple(c) for c in doc.get("withheld") or []]
    if released(deferred, go):              # False at once when nothing is deferred: no go record is read
        return check_followup(frame_path, prereg, results, followup_path, go)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pin", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    g.add_argument("--write-followup", action="store_true")       # lane gemini-defer, R4
    args = ap.parse_args(argv)
    if args.pin:
        design = dict(PROPOSED, harness_models=_read(DRAFT)["stats_design_inputs"]["harness_models"])
        print(design_pin(design))
        return 0
    if args.check:
        return check()
    try:
        got = derive(part=FOLLOWUP if args.write_followup else ORIGINAL)
    except (SampleError, stats.StatsError) as err:
        print(f"sample: FAIL {err}")
        return 1
    if got is None:
        print("sample: no takes; nothing drawn or written")
        return 1
    with open(SAMPLE_FOLLOWUP if args.write_followup else SAMPLE, "w", encoding="utf-8") as fh:
        fh.write(render(got[2]))
    print(f"sample: wrote {len(got[2]['items'])} takes; seed {got[2]['seed']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
