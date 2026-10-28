#!/usr/bin/env python3
"""Lane pf1-walk-cover-strict, OD132 (Javier, 26 Oct 2026, decision.jsonl: "walk-cover-o strict"): a Codex walk counts
as covered only if it rechecks clean under the harness as it will be frozen. Arm G is deferred and stays as coded.

The real records, read-only. Every arm O and arm G walk of this tree's register is regraded (walk_regrade.regrade_doc from its
committed bytes) and rechecked (walk_regrade.recheck_doc, the ordinal after its last committed recheck) in memory, and
the results are written into a scratch copy of the rehearsals folder with their register recheck entries; nothing is
written in the study. A committed regrade.json must be the bytes its in-memory re-derivation gives; a walk whose
regrade is not committed yet is rechecked through the regrade just derived (the only stand-in, counted in the output).
Lane gap-rewalk-fix (glitch-45, 27 Oct 2026): an arm O walk graded at walk time (grade.json graded true, no regrade.json,
the rewalk's w-o49..w-o90) has no regrade to derive: regrade_doc refuses it as not pending. It is read by the recheck
road alone (walk_road), as coverage reads it (pending_walk.coverage_status: graded true goes to checker_standing);
any other arm O walk shape refuses, by name.

  R1.strict     on the scratch copy, walk_plan's coverage (strict_walks, pending_walk.uncounted_walks) counts an arm O
                walk only when its recheck carries no strict hit (pending_walk.strict_hits against
                pending_walk.strict_reasons(), the rule's own set); each arm O walk whose recheck carries one is
                reported with STRICT_WHY; each model's covered figure is the tests' own count of the specs the clean
                walks cover; the instrument is armed (a clean and a non-clean arm O walk both exist)
  R2.arm-g      every arm G walk reads on the scratch copy exactly as it does without the strict rule. Every real arm
                G recheck reads clean, so one rechecked arm G walk's scratch recheck is planted with a reason
                (PLANTED_REASON, the only edit to a reading; the study is never touched): it counts without the
                rule, and must count with it
  R3.committed  every committed arm O or G regrade.json is the bytes its re-derivation gives
  R4.witnesses  the same scratch copy judged with walk_plan's strict arms set to ("A",) turns R1 red, and with
                ("A", "O", "G") turns R2 red
  R6.walk-time  two walks only (WALK_TIME, PENDING_O): the walk-time arm O walk reads by the recheck road with no
                regrade, and the regrade road refuses it as not pending (the old road's R0, the instrument armed); the
                pending arm O walk still reads through its regrade; a walk-time shape carrying a regrade.json, and a
                graded-false grade, refuse by name
  R5.reason-set light, no record read (the review of c6a0a4e1, MINOR): on synthetic readings with a stood-in strict
                set, R1 accepts an arm O walk counted whose only reason is outside the strict set and refuses it left
                uncounted; a reason outside the table's vocabulary is a strict hit, the other way round

The output prints each arm O model's covered figure, the walks that count and the specs still missing.

Heavy (every arm O walk rechecked): run on athena, from checks.d/pf1-walk-cover-strict.txt.

    python3 -B -W ignore evals/gap-study-4/tests/test_walk_cover_o_records.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

READING: dict = {}
PLANTED_REASON = "harness-condition-violated"


def tearDownModule():
    if READING.get("tmp"):
        shutil.rmtree(READING["tmp"], ignore_errors=True)


def machine_for(base: Path, walk: str) -> dict:
    launch = sorted(glob.glob(str(base / walk / "turn-*.jsonl.launch.json")))
    stream = json.loads(Path(launch[0]).read_text())["stream"]
    return {"home": "/home/javier", "temp_root": "/tmp", "checkout": stream.split("/evals/")[0]}


def committed_rechecks(base: Path, walk: str) -> int:
    reg = json.loads((base / "register.json").read_text())
    return sum(1 for e in reg.get("rechecks", []) if e.get("walk") == walk)


WALK_TIME, PENDING_O = "w-o49", "w-o7"     # R6's two walks: graded at walk time; pending, its regrade committed


def walk_road(base: Path, walk: str) -> str:
    """How an arm O walk is read: "regrade" when its committed grade.json is the pending document (pending_walk.status
    of its ledger), "walk-time" when it was graded at walk time (graded true) and carries no regrade.json; anything
    else refuses, by name (fail closed)."""
    import drive
    import pending_walk as pw
    import walk_regrade as wr
    try:
        grade = json.loads((base / walk / drive.WALK_GRADE).read_bytes())
        ledger = json.loads((base / walk / drive.LEDGER_FILE).read_bytes())
    except (OSError, ValueError) as exc:
        raise wr.RegradeRefused(f"{walk}: its grade or ledger cannot be read: {exc}") from None
    if grade == pw.status(ledger):
        return "regrade"
    if isinstance(grade, dict) and grade.get("graded") is True:
        if (base / walk / wr.REGRADE_FILE).exists():
            raise wr.RegradeRefused(f"{walk}: graded at walk time, yet it carries a {wr.REGRADE_FILE}")
        return "walk-time"
    raise wr.RegradeRefused(f"{walk}: its grade.json is neither the pending document nor graded true")


def read_one(base: Path, walk: str, arm: str, cross_for) -> tuple:
    """(road, regrade or None, recheck doc) of one arm O or G walk, in memory. `cross_for(committed)` is the
    _verified_regrade_cross to recheck a regraded walk with."""
    import walk_regrade as wr
    road = walk_road(base, walk) if arm == "O" else "regrade"
    if road == "walk-time":                       # the recheck road alone: no regrade exists or is derived
        return road, None, wr.recheck_doc(walk, committed_rechecks(base, walk) + 1, HERE, machine=machine_for(base, walk))
    regrade = wr.regrade_doc(walk, HERE)
    with mock.patch.object(wr, "_verified_regrade_cross", cross_for((base / walk / wr.REGRADE_FILE).is_file())):
        doc = wr.recheck_doc(walk, committed_rechecks(base, walk) + 1, HERE, machine=machine_for(base, walk))
    return road, regrade, doc


def read_records() -> dict:
    """The arm O regrades and rechecks, once per process, written into a scratch copy kept for the module."""
    if READING:
        return READING
    import walk_plan
    import walk_regrade as wr
    import walk_register
    base = walk_register.REHEARSALS
    design = walk_plan.design_in_force(HERE)
    specs = walk_plan.plan_walks(design)
    entries = walk_plan.read_register(base, design)
    # arm G is rechecked too, so R2 compares readings the strict rule could change (not two "pending" readings)
    o_walks = [e["walk"] for e in entries if e["arm"] in ("O", "G")]
    regrades, docs, stood_in, committed_bad, walk_time = {}, {}, [], [], []
    real_cross = wr._verified_regrade_cross

    def derived_cross(walk, study, root, walk_rel, harness, *, readers, grade):
        """The stand-in for a regrade not committed yet: the regrade just derived from the committed walk, held to
        the same graded, agreed and admission checks; the in-HEAD lookup alone is skipped."""
        doc = wr.regrade_doc(walk, study, readers=readers, grade=grade)
        if doc.get("graded") is not True or (doc.get("cross_check") or {}).get("status") != "agreed":
            raise wr.RegradeRefused("the derived regrade does not grade it")
        wr.admitted(harness, wr.nrr.production_readers(study) if readers is None else readers, doc["cross_check"])
        return []
    arm_of = {e["walk"]: e["arm"] for e in entries}
    for w in o_walks:
        try:
            road, regrade, doc = read_one(base, w, arm_of[w], lambda committed: real_cross if committed else derived_cross)
        except wr.RegradeRefused as exc:
            if arm_of[w] == "O":
                raise                            # an arm O walk the regrade or recheck refuses fails R0, by name
            print(f"test_walk_cover_o_records: arm G {w} not regraded or rechecked: {exc}", flush=True)
            continue
        docs[w] = doc
        if road == "walk-time":
            walk_time.append(w)
            continue
        regrades[w] = regrade
        committed = base / w / wr.REGRADE_FILE
        if committed.is_file():
            if committed.read_bytes() != wr.regrade_bytes(regrade):
                committed_bad.append(w)
        else:
            stood_in.append(w)
    tmp = Path(tempfile.mkdtemp(prefix="cover-o-records-"))
    READING["tmp"] = tmp
    sim = tmp / "rehearsals"
    shutil.copytree(base, sim)
    reg = json.loads((sim / "register.json").read_bytes())
    rechecks = list(reg.get("rechecks", []))
    for w, doc in docs.items():
        if w in regrades and not (sim / w / wr.REGRADE_FILE).is_file():
            (sim / w / wr.REGRADE_FILE).write_bytes(wr.regrade_bytes(regrades[w]))
        name = f"recheck-{doc['n']}.json"
        data = wr.regrade_bytes(doc)
        (sim / w / name).write_bytes(data)
        rechecks.append({"walk": w, "file": name, "n": doc["n"], "checker_constants_sha256": doc["checker_constants_sha256"],
                         "sha256": hashlib.sha256(data).hexdigest()})
    # every real arm G recheck reads clean (26 Oct 2026), so the strict rule could not change one: one arm G walk's
    # scratch recheck is given a reason (PLANTED_REASON), and R2 then compares a reading the rule would change
    planted = next((w for w in sorted(docs) if any(e["walk"] == w and e["arm"] == "G" for e in entries)), None)
    for e in rechecks:
        if planted is not None and e["walk"] == planted and e["n"] == docs[planted]["n"]:
            data = wr.regrade_bytes(dict(docs[planted], checker_reasons=[PLANTED_REASON]))
            (sim / planted / e["file"]).write_bytes(data)
            e["sha256"] = hashlib.sha256(data).hexdigest()
    (sim / "register.json").write_text(json.dumps({"schema": walk_register.SCHEMA_RECHECKS, "walks": reg["walks"],
                                                   "rechecks": rechecks}, indent=2) + "\n")
    READING["planted"] = planted
    READING.update(base=base, sim=sim, docs=docs, arm={e["walk"]: e["arm"] for e in entries}, regrades=regrades, stood_in=stood_in, committed_bad=committed_bad, walk_time=walk_time,
                   entries=entries, specs=specs, design=design, sim_entries=walk_plan.read_register(sim, design))
    return READING


def judge(r) -> dict:
    """walk_plan's strict coverage of the scratch copy, as walk_plan's arms stand now: {strict, strict_why, loose_why}."""
    import pending_walk as pw
    import walk_plan
    # the scratch copy is no repository: a regrade's re-derivation there is the one derived from the committed walk
    state = {w: ("graded" if d.get("graded") is True else "refused") for w, d in r["regrades"].items()}
    real_state = pw._regrade_state
    ids = [e["walk"] for e in r["sim_entries"]]
    with mock.patch.object(pw, "_regrade_state", lambda b, walk: state.get(walk) or real_state(r["base"], walk)):
        strict_why = pw.uncounted_walks(r["sim"], ids, walk_plan.strict_walks(r["sim_entries"]))
        loose_why = pw.uncounted_walks(r["sim"], ids)
    strict = walk_plan.coverage(r["sim_entries"], r["specs"], r["design"], strict_why)
    return {"strict": strict, "strict_why": strict_why, "loose_why": loose_why}


def r1_problems(r, j) -> list:
    import pending_walk as pw
    out = []
    design, got = r["design"], j["strict"]
    o_docs = {w: d for w, d in r["docs"].items() if r["arm"][w] == "O"}
    # the rule's own set (review of c6a0a4e1, MINOR): a walk is dirty only on a strict hit, never on any reason
    strict = pw.strict_reasons()
    clean = {w for w, d in o_docs.items() if not pw.strict_hits(d["checker_reasons"] or [], strict)}
    dirty = set(o_docs) - clean
    if not (clean and dirty):
        out.append(f"R1.strict: the instrument is not armed (clean {sorted(clean)}, not clean {len(dirty)})")
    covering = {w for ws in got["covered"].values() for w in ws}
    if covering & dirty:
        out.append(f"R1.strict: arm O walks counted on a recheck with reasons: {sorted(covering & dirty)}")
    for w in sorted(dirty):
        if not str(j["strict_why"].get(w, "")).startswith(pw.STRICT_WHY):
            out.append(f"R1.strict: {w} reads {j['strict_why'].get(w)!r}, not STRICT_WHY")
    by_entry = {e["walk"]: e for e in r["entries"]}
    want: dict = {}
    for w in clean:
        want.setdefault(by_entry[w]["model"], set()).add((by_entry[w]["task"], by_entry[w]["half"]))
    for model in design["planned"]["O"]:
        mine = [s for s in r["specs"] if (s["arm"], s["model"]) == ("O", model)]
        covered = sum(1 for s in mine if s not in got["missing"])
        own = len({(s["task"], s["half"]) for s in mine} & want.get(model, set()))
        if covered != own:
            out.append(f"R1.strict: arm O {model} reads {covered} covered; its clean walks cover {own}")
    return out


def r2_problems(r, j) -> list:
    g = [e["walk"] for e in r["entries"] if e["arm"] == "G"]
    out = [] if g else ["R2.arm-g: the register holds no arm G walk"]
    if r.get("planted") not in g:
        out.append("R2.arm-g: the instrument is not armed: no rechecked arm G walk carries the planted reason")
    elif j["loose_why"].get(r["planted"]) is not None:
        out.append(f"R2.arm-g: the planted walk {r['planted']} reads {j['loose_why'][r['planted']]!r} without the "
                   f"rule, so the rule could not change it")
    return out +[f"R2.arm-g: {w} reads {j['strict_why'].get(w)!r}, not {j['loose_why'].get(w)!r} as without the rule"
                  for w in g if j["strict_why"].get(w) != j["loose_why"].get(w)]


def report(r, j) -> None:
    import walk_plan
    design, specs, got = r["design"], r["specs"], j["strict"]
    print(f"test_walk_cover_o_records: {len(r['docs'])} arm O and G walks rechecked in memory; regrade stood in for "
          f"{len(r['stood_in'])}, committed for {len(r['regrades']) - len(r['stood_in'])}; graded at walk time, read by "
          f"the recheck road alone, {len(r['walk_time'])}", flush=True)
    g_docs = {w: d for w, d in r["docs"].items() if r["arm"][w] == "G"}
    print(f"arm G (deferred, as coded): {len(g_docs)} rechecked, {sum(1 for d in g_docs.values() if d['checker_reasons'])}"
          f" carrying a reason in fact; {r['planted']} planted with {PLANTED_REASON} in the scratch copy only", flush=True)
    for model in design["planned"]["O"]:
        mine = [s for s in specs if (s["arm"], s["model"]) == ("O", model)]
        walks = sorted({w for s in mine for w in got["covered"].get(walk_plan.cover_key(s, design), [])})
        gaps = [walk_plan.spec_line(s) for s in mine if s in got["missing"]]
        print(f"arm O {model}: {len(mine) - len(gaps)} of {len(mine)} covered by {walks}", flush=True)
        for line in gaps:
            print(f"  needs a new walk: {line}", flush=True)


class Records(unittest.TestCase):
    def reading(self, clause: str):
        try:
            r = read_records()
            return r, judge(r)
        except Exception as exc:                 # noqa: BLE001 - a raise fails the clause, never an error
            self.fail(f"{clause}: the records could not be read: {exc!r}")

    def test_r1_an_arm_o_walk_counts_only_clean(self):
        r, j = self.reading("R1.strict")
        report(r, j)
        self.assertEqual(r1_problems(r, j), [], "R1.strict")

    def test_r2_arm_g_is_untouched(self):
        r, j = self.reading("R2.arm-g")
        self.assertEqual(r2_problems(r, j), [], "R2.arm-g")

    def test_r3_committed_regrades_re_derive(self):
        r, _ = self.reading("R3.committed")
        self.assertEqual(r["committed_bad"], [], "R3.committed: every committed regrade.json is its re-derivation")

    def test_r4_witnesses(self):
        import walk_plan
        r, _ = self.reading("R4.witnesses")
        for arms, check in ((("A",), r1_problems), (("A", "O", "G"), r2_problems)):
            with self.subTest(arms=arms), mock.patch.dict(walk_plan.WALK_COVER_STRICT, arms=arms):
                self.assertTrue(check(r, judge(r)), f"R4.witnesses: strict arms {arms} survive {check.__name__}")


class WalkTimeRoad(unittest.TestCase):
    """R6.walk-time, two walks only: a walk graded at walk time reads by the recheck road; a pending one by its regrade."""

    def test_r6_a_walk_time_graded_walk_reads_by_recheck_alone(self):
        import walk_regrade as wr
        import walk_register
        base = walk_register.REHEARSALS
        with self.assertRaises(wr.RegradeRefused, msg="R6.walk-time: the instrument is armed: the old road (regrade "
                                                      "first) refuses the walk-time walk"):
            wr.regrade_doc(WALK_TIME, HERE)
        road, regrade, doc = read_one(base, WALK_TIME, "O", lambda committed: wr._verified_regrade_cross)
        self.assertEqual((road, regrade), ("walk-time", None), "R6.walk-time: read by the recheck road, no regrade")
        self.assertEqual((doc["walk"], doc["n"]), (WALK_TIME, committed_rechecks(base, WALK_TIME) + 1), "R6.walk-time")
        self.assertIsInstance(doc["checker_reasons"], list, "R6.walk-time: the recheck is a checker reading")
        road, regrade, doc = read_one(base, PENDING_O, "O", lambda committed: wr._verified_regrade_cross)
        self.assertEqual(road, "regrade", "R6.walk-time: a pending arm O walk still reads through its regrade")
        self.assertEqual(wr.regrade_bytes(regrade), (base / PENDING_O / wr.REGRADE_FILE).read_bytes(), "R6.walk-time")

    def test_r6_any_other_shape_refuses(self):
        import drive
        import walk_regrade as wr
        import walk_register
        with tempfile.TemporaryDirectory() as d:
            for name, edit in (("regrade-beside", lambda f: (f / wr.REGRADE_FILE).write_text("{}")),
                               ("graded-false", lambda f: (f / drive.WALK_GRADE).write_text('{"graded": false}'))):
                f = Path(d) / name / WALK_TIME
                f.mkdir(parents=True)
                for n in (drive.WALK_GRADE, drive.LEDGER_FILE):
                    shutil.copy(walk_register.REHEARSALS / WALK_TIME / n, f / n)
                edit(f)
                with self.subTest(name), self.assertRaises(wr.RegradeRefused, msg=f"R6.walk-time: {name} refuses"):
                    walk_road(Path(d) / name, WALK_TIME)


class ReasonSet(unittest.TestCase):
    """R5.reason-set, light (no record is read): R1 judges a walk by the rule's own set, never by any reason."""

    def case(self, reasons, counted: bool):
        import pending_walk as pw
        spec = lambda half: {"arm": "O", "model": "m", "task": "t", "half": half}  # noqa: E731
        r = {"design": {"planned": {"O": ["m"]}}, "specs": [spec("normal"), spec("trap")],
             "docs": {"w-c": {"checker_reasons": []}, "w-d": {"checker_reasons": ["harness-condition-violated"]},
                      "w-x": {"checker_reasons": list(reasons)}},
             "arm": {"w-c": "O", "w-d": "O", "w-x": "O"},
             "entries": [{"walk": "w-c", "model": "m", "task": "t", "half": "normal"},
                         {"walk": "w-d", "model": "m", "task": "t", "half": "normal"},
                         {"walk": "w-x", "model": "m", "task": "t", "half": "trap"}]}
        why = {"w-d": f"{pw.STRICT_WHY}: harness-condition-violated"}
        if counted:
            covered, missing = {"normal": ["w-c"], "trap": ["w-x"]}, []
        else:
            covered, missing = {"normal": ["w-c"]}, [spec("trap")]
            why["w-x"] = f"{pw.STRICT_WHY}: {', '.join(reasons)}"
        return r, {"strict": {"covered": covered, "missing": missing}, "strict_why": why}

    def test_r5_a_reason_outside_the_strict_set_counts(self):
        import pending_walk as pw
        outside = "a-graded-reason"
        strict = pw.StrictReasons({"harness-condition-violated"}, {"harness-condition-violated", outside})
        self.assertNotIn(outside, strict, "R5.reason-set: the case is armed")
        with mock.patch.object(pw, "strict_reasons", lambda: strict):
            self.assertEqual(r1_problems(*self.case([outside], counted=True)), [],
                             "R5.reason-set: a walk whose only reason is outside the strict set counts, and R1 agrees")
            self.assertTrue(r1_problems(*self.case([outside], counted=False)),
                            "R5.reason-set: R1 refuses such a walk left uncounted")
            self.assertTrue(r1_problems(*self.case(["a-reason-the-table-does-not-know"], counted=True)),
                            "R5.reason-set: a reason outside the table's vocabulary is a strict hit (strict_hits)")
            self.assertEqual(r1_problems(*self.case(["a-reason-the-table-does-not-know"], counted=False)), [],
                             "R5.reason-set: R1 accepts such a walk left uncounted")


if __name__ == "__main__":
    unittest.main()
