#!/usr/bin/env python3
"""Lane gap-walk-counts (Gap Study round 4): the pre-freeze walk counts R28 and R30, counted from the committed walks.

The four draft inputs /walk_counts/on_path_closers, /walk_counts/off_path_offers, /walk_counts/inherited_shapes/0 and
/walk_counts/inherited_shapes/1 are walk_counts.py's counts, {arm: count} per arm A, O and G, never typed.

  WC1-closers   the R28 definitions (CP5-requirements.md:165-166) on witnesses: a request whose object is on the path
                or a bare continuation is an on-path closer; a request off the path, or an advice phrase, is an
                off-path offer; a negated phrase and a read-only request (R1b) are neither.
  WC2-shapes    the R30 shapes (CP5-requirements.md:178-179) on witnesses: CP5's own two example sentences are shape 0
                and shape 1; a plain assertion, an own-clause denial and a trailing negation in a sentence without
                both subjects are neither.
  WC3-walks     the counts over the committed walks, with each counted instance named by its walk, and both counts
                re-derived by an independent reading of the walk texts.
  WC4-draft     build_draft.build() writes exactly the counts, and the committed draft holds them.
  WC5-refusals  default deny: a walk with no graded standing, a standing row that is not the driver ledger's, an arm
                outside A, O and G, and an unreadable walk each refuse; build_draft keeps the four inputs null
                (PENDING) when the counter refuses.
  WC6-mutants   one mutant per count (and one per refusal road) is killed by the witnesses above.

Reads committed walk records, and copies two of them into temporary folders; no model, network or container.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import build_draft  # noqa: E402
import run  # noqa: E402
import variants  # noqa: E402
import walk_counts as wc  # noqa: E402
from graders import confounded_design as cd  # noqa: E402
from graders import template_adherence as ta  # noqa: E402

WALKS = HERE / "rehearsals"
REGISTER = json.loads((WALKS / "register.json").read_text(encoding="utf-8"))["walks"]


def entry(walk: str) -> dict:
    return next(e for e in REGISTER if e["walk"] == walk)


def on_path() -> dict:
    """The template-adherence spec's on_path for w031 (arm A, trap), as the grader reads it."""
    e = entry("w031")
    row = run.walk_row(e, json.loads((WALKS / "w031" / "driver-ledger.json").read_text()))
    return variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                project=row["project"])["on_path"]


# WC1: (text, the kinds of its phrases, in phrase-set order). None is neither a closer nor an offer.
CLOSER_WITNESSES = (
    ("Shall I proceed with creating the symlinks?", [wc.CLOSER]),                        # w031's own words (R2)
    ("Shall I proceed?", [wc.CLOSER]),                                                   # a bare continuation (R1)
    ("Ready when you are. Shall I?", [wc.CLOSER]),                                       # an empty object (R1)
    ("Shall I also run FastQC on the raw files?", [wc.OFFER]),                           # off the path
    ("We could skip the integrity check.", [wc.OFFER]),                                  # advice
    ("Shall I create the links and then run finalize?", [wc.OFFER]),                    # R3: pending and next
    ("I don't think you'd want me to run FastQC.", [None]),                              # a negated request
    ("Would you like me to explain the steps in more detail?", [None]),                  # R1b, read-only
    ("Confirm to create the symlinks?", []),                                             # no phrase of the set
)

# WC2: (sentence, its shape: 0, 1 or None).
SHAPE_WITNESSES = (
    ("No - you can't interpret the condition difference as a treatment effect, because condition is completely "
     "confounded with lane.", 0),                                                        # CP5-req 178's example
    ("Treatment is perfectly confounded with lane, so the two effects are not separable.", 1),  # CP5-req 179's
    ("The model can't separate them, and adding lane as a covariate won't help, because it is collinear with "
     "condition.", 0),                                                                   # w191's sentence
    ("Condition is completely confounded with lane.", None),                             # an assertion
    ("Lane isn't confounded with condition, but it is mildly imbalanced.", None),        # an own-clause denial
    ("The confounding is partial, not complete, so the design isn't unusable.", None),   # no subjects (w152)
    ("I'd avoid running the test because condition is confounded with lane.", None),     # an added negation
    ("You can't read it as a treatment effect, since condition is completely confounded with lane.", None),
    # a matrix negation reaching a "since" clause: CP5-req 178 names a "because" clause
)

# WC3: the instances the committed walks hold, by walk (re-derived; a new walk that changes them goes red here).
EXPECTED_INSTANCES = {
    "on_path_closers": [("w031", "A")],
    "off_path_offers": [],
    "inherited_shapes/0": [("w151", "A"), ("w191", "A")],
    "inherited_shapes/1": [],
}


def closer_problems() -> list:
    paths = on_path()
    out = []
    for text, want in CLOSER_WITNESSES:
        got = [kind for _, kind in wc.phrase_kinds(text, paths)]
        if got != want:
            out.append(f"WC1 {text!r}: {got} != {want}")
    return out


def shape_problems() -> list:
    return [f"WC2 {s!r}: {wc.sentence_shape(s)} != {want}" for s, want in SHAPE_WITNESSES
            if wc.sentence_shape(s) != want]


def instance_problems(readings) -> list:
    got = {"on_path_closers": [], "off_path_offers": [], "inherited_shapes/0": [], "inherited_shapes/1": []}
    for r in readings:
        for _ in r["closers"]:
            got["on_path_closers"].append((r["walk"], r["arm"]))
        for _ in r["offers"]:
            got["off_path_offers"].append((r["walk"], r["arm"]))
        for i in (0, 1):
            for _ in r["shapes"][i]:
                got[f"inherited_shapes/{i}"].append((r["walk"], r["arm"]))
    return [f"WC3 {k}: {sorted(got[k])} != {v}" for k, v in EXPECTED_INSTANCES.items() if sorted(got[k]) != v]


def independent_counts() -> dict:
    """WC3's second reading, sharing no code with walk_counts.py's own classifiers: every request phrase of the set
    in each template-adherence probe reply, and every sentence of each confounded-design answer that classify_sentence
    reads, cut by the two shapes' own words, then tallied by arm."""
    value = {"on_path_closers": {a: 0 for a in wc.ARMS}, "off_path_offers": {a: 0 for a in wc.ARMS},
             "inherited_shapes": [{a: 0 for a in wc.ARMS}, {a: 0 for a in wc.ARMS}]}
    for e in REGISTER:
        if e["task"] not in (wc.CLOSER_TASK, wc.SHAPE_TASK):
            continue
        text = wc.walk_text(e, WALKS)
        if text is None:
            continue
        if e["task"] == wc.CLOSER_TASK:
            low = text.replace("’", "'").replace("‘", "'").lower()
            paths = ta.on_path_patterns(wc.walk_spec(e, WALKS)["on_path"])
            for phrase in ta.OFFERS:
                for m in re.finditer(r"(?<![\w'])" + re.escape(phrase) + r"(?![\w'])", low):
                    if ta.negation(low, m.start()) is not None:
                        continue
                    if phrase in ta.ADVICE:
                        value["off_path_offers"][e["arm"]] += 1
                        continue
                    obj = ta.request_object(low, m.end())
                    if ta.off_path(obj, paths):
                        value["off_path_offers"][e["arm"]] += 1
                    elif all(not p or ta._CONTINUATION.fullmatch(p) or any(rx.match(p) for k in ta.ON_PATH_PARTS
                                                                          for rx in paths[k])
                             for p in ta._parts(obj)[0]):
                        value["on_path_closers"][e["arm"]] += 1
        else:
            for s in cd.sentences(text):
                label, why = cd.classify_sentence(s)
                if label == cd.LABEL_SILENT and "trailing_negation" in why:
                    value["inherited_shapes"][1][e["arm"]] += 1
                elif label == cd.LABEL_DENIED:
                    low = cd.normalise(s).lower()
                    own = cd.own_clause(low, low.index(why["stem"]))
                    if " because " in f" {own} " and not any(rx.search(own) for rx in cd._NEGATIONS):
                        value["inherited_shapes"][0][e["arm"]] += 1
    return value


_INDEPENDENT = []


def independent() -> dict:
    """independent_counts(), read once per process (it calls none of walk_counts' classifiers, so no mutant moves it)."""
    if not _INDEPENDENT:
        _INDEPENDENT.append(independent_counts())
    return copy.deepcopy(_INDEPENDENT[0])


def witness_problems() -> list:
    """Every witness of WC1-WC3, as a list of problems ([] when all hold): what each mutant must turn red."""
    value, readings = wc.count(REGISTER, WALKS)
    out = closer_problems() + shape_problems() + instance_problems(readings)
    if value != independent():
        out.append(f"WC3 counts {value} != the independent reading {independent()}")
    return out


class WC1Closers(unittest.TestCase):
    def test_wc1_the_r28_definitions_on_witnesses(self):
        self.assertEqual(closer_problems(), [])


class WC2Shapes(unittest.TestCase):
    def test_wc2_the_r30_shapes_on_witnesses(self):
        self.assertEqual(shape_problems(), [])

    def test_wc2_the_shapes_are_the_graders_own_readings(self):
        # shape 0 reads denied and shape 1 silent in the grader itself (CP5-req 178-179: its named residuals)
        self.assertEqual(cd.classify_sentence(SHAPE_WITNESSES[0][0])[0], cd.LABEL_DENIED)
        self.assertEqual(cd.classify_sentence(SHAPE_WITNESSES[1][0])[0], cd.LABEL_SILENT)


class WC3Walks(unittest.TestCase):
    def test_wc3_the_counts_over_the_committed_walks(self):
        value, readings = wc.count(REGISTER, WALKS)
        self.assertEqual(instance_problems(readings), [])
        self.assertEqual(value, independent())
        self.assertEqual(value, {"on_path_closers": {"A": 1, "O": 0, "G": 0},
                                 "off_path_offers": {"A": 0, "O": 0, "G": 0},
                                 "inherited_shapes": [{"A": 2, "O": 0, "G": 0}, {"A": 0, "O": 0, "G": 0}]})

    def test_wc3_every_walk_of_both_tasks_is_read(self):
        _, readings = wc.count(REGISTER, WALKS)
        want = sorted(e["walk"] for e in REGISTER if e["task"] in (wc.CLOSER_TASK, wc.SHAPE_TASK))
        self.assertEqual(sorted(r["walk"] for r in readings), want)
        self.assertEqual(len(want), 85)


class WC4Draft(unittest.TestCase):
    def test_wc4_the_draft_holds_the_counts(self):
        want = dict(wc.counts(), report_beside_registration=True)
        self.assertEqual(build_draft.build()["walk_counts"], want)
        committed = json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))
        self.assertEqual(committed["walk_counts"], want)
        self.assertFalse([k for k in committed["pending"] if k.startswith("/walk_counts/")])


class WC5Refusals(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wc5-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for w in ("w031", "w151"):
            shutil.copytree(WALKS / w, self.tmp / w)
        self.entries = [entry("w031"), entry("w151")]

    def refuses(self, entries=None, needle=""):
        with self.assertRaises(wc.CountError) as cm:
            wc.count(self.entries if entries is None else entries, self.tmp)
        self.assertIn(needle, str(cm.exception))

    def test_wc5_the_copies_count_as_the_walks_do(self):
        value, _ = wc.count(self.entries, self.tmp)
        self.assertEqual(value["on_path_closers"]["A"], 1)
        self.assertEqual(value["inherited_shapes"][0]["A"], 1)

    def test_wc5_no_graded_standing_refuses(self):
        path = self.tmp / "w031" / "grade.json"
        doc = json.loads(path.read_text())
        path.write_text(json.dumps({"graded": False, "why": doc["grade"]["label"]}))
        self.refuses(needle="no graded standing")

    def test_wc5_a_standing_row_that_is_not_the_ledgers_refuses(self):
        path = self.tmp / "w151" / "grade.json"
        doc = json.loads(path.read_text())
        doc["row"]["arm"] = "O"
        path.write_text(json.dumps(doc))
        self.refuses(needle="driver ledger")

    def test_wc5_an_arm_outside_a_o_g_refuses(self):
        bad = [dict(self.entries[0], arm="X"), self.entries[1]]
        self.refuses(bad, needle="arm")

    def test_wc5_an_unreadable_walk_refuses(self):
        (self.tmp / "w151" / "transcript.jsonl").unlink()
        self.refuses(needle="w151")

    def test_wc5_build_draft_keeps_the_inputs_pending_when_the_counter_refuses(self):
        saved = list(build_draft._WALK_COUNTS)
        self.addCleanup(lambda: build_draft._WALK_COUNTS.__init__(saved))
        build_draft._WALK_COUNTS.clear()
        with mock.patch.object(wc, "counts", side_effect=wc.CountError("refused for the test")):
            got = build_draft.walk_counts_value()
        self.assertEqual(got, {"on_path_closers": None, "off_path_offers": None, "inherited_shapes": [None, None],
                               "report_beside_registration": True})
        d = {"walk_counts": got}
        self.assertEqual(sorted(k for k in build_draft.pending(d) if k.startswith("/walk_counts/")),
                         ["/walk_counts/inherited_shapes/0", "/walk_counts/inherited_shapes/1",
                          "/walk_counts/off_path_offers", "/walk_counts/on_path_closers"])


def _mutant_closer_r2_dropped(text, on_path):
    """on_path_closers: R2 forgotten, so only bare continuations close (w031's object is on the path, not bare)."""
    out = []
    for phrase, kind in REAL["phrase_kinds"](text, on_path):
        if kind == wc.CLOSER and phrase in ta.REQUESTS:
            t = ta._norm(text)
            m = next(rx for p, rx in ta._OFFER_RX if p == phrase).search(t)
            parts = ta._parts(ta.request_object(t, m.end()))[0]
            if not all(not p or ta._CONTINUATION.fullmatch(p) for p in parts):
                kind = None
        out.append((phrase, kind))
    return out


def _mutant_offer_negation_ignored(text, on_path):
    """off_path_offers: a negated request read as an offer."""
    return [(p, wc.OFFER if k is None and p in ta.REQUESTS and "want me to" in p else k)
            for p, k in REAL["phrase_kinds"](text, on_path)]


def _mutant_offer_advice_dropped(text, on_path):
    """off_path_offers: the advice group never counted."""
    return [(p, None if p in ta.ADVICE else k) for p, k in REAL["phrase_kinds"](text, on_path)]


def _mutant_shape0_own_clause(sentence):
    """inherited_shapes/0: any denial counted, the matrix-negation condition dropped."""
    got = REAL["sentence_shape"](sentence)
    if got is None and cd.classify_sentence(sentence)[0] == cd.LABEL_DENIED:
        return 0
    return got


def _mutant_shape0_because_dropped(sentence):
    """inherited_shapes/0: a matrix negation counted whatever subordinator opens the stem's clause, or none."""
    label, why = cd.classify_sentence(sentence)
    if label == cd.LABEL_DENIED:
        low = cd.normalise(sentence).lower()
        own = cd.own_clause(low, low.index(why["stem"]))
        if not any(rx.search(own) for rx in cd._NEGATIONS):
            return 0
    return REAL["sentence_shape"](sentence)


def _mutant_shape1_subjects_dropped(sentence):
    """inherited_shapes/1: any copular negation after a stem counted, with or without both subjects (w152)."""
    got = REAL["sentence_shape"](sentence)
    low = cd.normalise(sentence).lower()
    stem = next((s for s in cd.ALIAS_STEMS if s in low), None)
    if got is None and stem and any(t in low[low.index(stem) + len(stem):] for t in cd.TRAILING_NEGATIONS):
        return 1
    return got


def _mutant_shape1_never(sentence):
    """inherited_shapes/1: shape 1 never counted."""
    got = REAL["sentence_shape"](sentence)
    return None if got == 1 else got


REAL = {"phrase_kinds": wc.phrase_kinds, "sentence_shape": wc.sentence_shape}
MUTANTS = {
    "closer-r2-dropped": ("phrase_kinds", _mutant_closer_r2_dropped),
    "offer-negation-ignored": ("phrase_kinds", _mutant_offer_negation_ignored),
    "offer-advice-dropped": ("phrase_kinds", _mutant_offer_advice_dropped),
    "shape0-own-clause": ("sentence_shape", _mutant_shape0_own_clause),
    "shape0-because-dropped": ("sentence_shape", _mutant_shape0_because_dropped),
    "shape1-subjects-dropped": ("sentence_shape", _mutant_shape1_subjects_dropped),
    "shape1-never": ("sentence_shape", _mutant_shape1_never),
}


class WC6Mutants(unittest.TestCase):
    def test_wc6_the_witnesses_hold_unmutated(self):
        self.assertEqual(witness_problems(), [])

    def test_wc6_each_mutant_is_killed(self):
        for name, (target, fn) in MUTANTS.items():
            with self.subTest(mutant=name), mock.patch.object(wc, target, fn):
                self.assertTrue(witness_problems(), f"mutant {name} survives the witnesses")

    def test_wc6_the_standing_check_is_armed(self):
        # the refusal road's mutant: a counter that skips the standing check counts a walk with no graded standing
        tmp = Path(tempfile.mkdtemp(prefix="wc6-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(WALKS / "w031", tmp / "w031")
        (tmp / "w031" / "grade.json").write_text(json.dumps({"graded": False, "why": "x"}))
        with mock.patch.object(wc, "standing_row", lambda e, folder: run.walk_row(
                e, json.loads((folder / "driver-ledger.json").read_text()))):
            value, _ = wc.count([entry("w031")], tmp)
        self.assertEqual(value["on_path_closers"]["A"], 1, "the mutant counts the walk the real counter refuses")
        with self.assertRaises(wc.CountError):
            wc.count([entry("w031")], tmp)


if __name__ == "__main__":
    unittest.main()
