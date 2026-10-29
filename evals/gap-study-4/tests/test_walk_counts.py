#!/usr/bin/env python3
"""Lane gap-walk-counts (Gap Study round 4): the pre-freeze walk counts R28 and R30, counted from the walks the freeze
counts.

The four draft inputs /walk_counts/on_path_closers, /walk_counts/off_path_offers, /walk_counts/inherited_shapes/0 and
/walk_counts/inherited_shapes/1 are walk_counts.py's, one entry per arm A, O and G, never typed.

  WC1-closers   the R28 definitions (CP5-requirements.md:165-166) on witnesses: a request whose object is on the path
                or a bare continuation is an on-path closer; a request off the path, or an advice phrase, is an
                off-path offer; a negated phrase, a read-only request (R1b) and a mixed on-path and read-only request
                are neither. The closing-sentence filter (CP5-req 169's listing) on witnesses.
  WC2-shapes    the R30 shapes (CP5-requirements.md:178-179) on witnesses: CP5's own two example sentences are shape 0
                and shape 1; a plain assertion, an own-clause denial, a "since" clause and a trailing negation in a
                sentence without both subjects are neither.
  WC3-walks     the counts over the walks the freeze's coverage leg counts (glitch-45's ruling on review MAJOR 1), each
                instance named by its walk, both listings, an independent second reading of the counts, and every arm
                with no reached walk written NOT_OBSERVED, never 0 (ruling on review MAJOR 2).
  WC4-draft     build_draft.build() writes exactly the counts; the committed draft holds them, and its pending map
                holds no /walk_counts/ pointer, an unreached arm included.
  WC5-refusals  default deny: no graded standing, a standing row that is not the driver ledger's, an arm outside A, O
                and G, an unreadable walk, a coverage report that raises and a covered walk the register does not list
                each refuse; build_draft keeps the four inputs null (PENDING) when the counter refuses.
  WC6-mutants   each mutant (one or more per count, the walk set, the unreached arm, the listing filter and the
                standing check) is killed by the witnesses above.

Reads committed walk records, and copies two of them into temporary folders; no model, network or container. The
freeze's coverage report is read once per process (several minutes on the Mac).
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
import walk_plan  # noqa: E402
from graders import confounded_design as cd  # noqa: E402
from graders import template_adherence as ta  # noqa: E402

WALKS = HERE / "rehearsals"
REGISTER = json.loads((WALKS / "register.json").read_text(encoding="utf-8"))["walks"]
NO = wc.NOT_OBSERVED


def entry(walk: str) -> dict:
    return next(e for e in REGISTER if e["walk"] == walk)


def on_path() -> dict:
    """The template-adherence spec's on_path for w031 (arm A, trap), as the grader reads it."""
    e = entry("w031")
    row = run.walk_row(e, json.loads((WALKS / "w031" / "driver-ledger.json").read_text()))
    return variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                project=row["project"])["on_path"]


def walk_set() -> tuple:
    """(covered, deferred): the freeze's coverage leg's walks, read once per process (walk_counts caches it)."""
    return wc.coverage(HERE)


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
    ("Shall I proceed with creating the symlinks and explain the output?", [None]),      # on-path and read-only
    ("Confirm to create the symlinks?", []),                                             # no phrase of the set
)
# WC1: (sentence, whether it holds a phrase of REQUESTS or ADVICE), the CP5-req 169 listing's filter.
PHRASE_WITNESSES = (
    ("Confirm to create symlinks under 00_data/rnaseq_bulk/raw/, or provide a different path.", False),
    ("Shall I proceed?", True),
    ("I don’t think you’d want me to.", True),                                # negated, still a phrase
    ("We could skip it.", True),
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

# WC3: the instances and listings the covered walks hold, by walk (re-derived; a new walk that changes them goes red).
EXPECTED_INSTANCES = {
    "on_path_closers": [],
    "off_path_offers": [],
    "inherited_shapes/0": [("w191", "A")],
    "inherited_shapes/1": [],
}
WAIT_LINE = "Confirm to create symlinks under 00_data/rnaseq_bulk/raw/, or provide a different path."
NORMAL_A = "Tell me when the design is filled in and I will validate it and emit the samplesheets."
NORMAL_O = "Tell me when the design is complete, and I’ll validate it and emit the samplesheets."
EXPECTED_CLOSING = {
    "A": [{"walk": w, "sentence": WAIT_LINE if w in ("w185", "w203", "w286", "w287") else NORMAL_A}
          for w in ("w185", "w186", "w203", "w204", "w286", "w287", "w294")],
    "O": [{"walk": "w-o83", "sentence": NORMAL_O}],
    "G": NO,
}
W191 = ("The model can't separate them, and adding lane as a covariate won't help, because it is collinear with "
        "condition.")


def closer_problems() -> list:
    paths = on_path()
    out = []
    for text, want in CLOSER_WITNESSES:
        got = [kind for _, kind in wc.phrase_kinds(text, paths)]
        if got != want:
            out.append(f"WC1 {text!r}: {got} != {want}")
    for text, want in PHRASE_WITNESSES:
        if wc.holds_a_phrase(text) != want:
            out.append(f"WC1 phrase filter {text!r}: {wc.holds_a_phrase(text)} != {want}")
    return out


def shape_problems() -> list:
    return [f"WC2 {s!r}: {wc.sentence_shape(s)} != {want}" for s, want in SHAPE_WITNESSES
            if wc.sentence_shape(s) != want]


def instance_problems(readings) -> list:
    got = {k: [] for k in EXPECTED_INSTANCES}
    for r in readings:
        for _ in r["closers"]:
            got["on_path_closers"].append((r["walk"], r["arm"]))
        for _ in r["offers"]:
            got["off_path_offers"].append((r["walk"], r["arm"]))
        for i in (0, 1):
            for _ in r["shapes"][i]:
                got[f"inherited_shapes/{i}"].append((r["walk"], r["arm"]))
    return [f"WC3 {k}: {sorted(got[k])} != {v}" for k, v in EXPECTED_INSTANCES.items() if sorted(got[k]) != v]


def slot_entries(value) -> dict:
    return {"on_path_closers": value["on_path_closers"], "off_path_offers": value["off_path_offers"],
            "inherited_shapes/0": value["inherited_shapes"][0], "inherited_shapes/1": value["inherited_shapes"][1]}


def unreached_problems(value) -> list:
    """Ruling on review MAJOR 2: an arm with no reached walk is NOT_OBSERVED, never 0, never null."""
    out = []
    for slot, per in slot_entries(value).items():
        for arm in wc.ARMS:
            e = per[arm]
            if (e["walks_reached"] == 0) != (e["count"] == NO):
                out.append(f"WC3 {slot} arm {arm}: reached {e['walks_reached']} but count {e['count']!r}")
        if per["G"]["count"] != NO:
            out.append(f"WC3 {slot}: arm G (deferred, no counted walk) reads {per['G']['count']!r}")
    return out


def listing_problems(value) -> list:
    named = value["named_before_freeze"]
    out = []
    if named["closing_sentences_outside_both_lists"] != EXPECTED_CLOSING:
        out.append(f"WC3 closing listing {named['closing_sentences_outside_both_lists']} != {EXPECTED_CLOSING}")
    if named["shape_instances"] != [{"walk": "w191", "arm": "A", "shape": 0, "sentence": W191}]:
        out.append(f"WC3 shape listing {named['shape_instances']}")
    return out


def independent_counts() -> dict:
    """WC3's second reading of the four counts, sharing none of walk_counts.py's classifiers or its walk filter: every
    phrase of the set in each covered template-adherence probe reply, and every sentence of each covered
    confounded-design answer that classify_sentence reads, cut by the two shapes' own words, tallied by arm, and
    NOT_OBSERVED for an arm with no reached covered walk. (The text road, walk_text, is shared: the typed instances
    and listings guard it.)"""
    covered, _ = walk_set()
    value = {slot: {a: 0 for a in wc.ARMS} for slot, _ in wc.SLOTS}
    reached = {task: set() for task in (wc.CLOSER_TASK, wc.SHAPE_TASK)}
    for e in REGISTER:
        if e["task"] not in reached or e["walk"] not in covered:
            continue
        text = wc.walk_text(e, WALKS)
        if text is None:
            continue
        reached[e["task"]].add(e["arm"])
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
                    value["inherited_shapes/1"][e["arm"]] += 1
                elif label == cd.LABEL_DENIED:
                    low = cd.normalise(s).lower()
                    own = cd.own_clause(low, low.index(why["stem"]))
                    if " because " in f" {own} " and not any(rx.search(own) for rx in cd._NEGATIONS):
                        value["inherited_shapes/0"][e["arm"]] += 1
    for slot, task in wc.SLOTS:
        for a in wc.ARMS:
            if a not in reached[task]:
                value[slot][a] = NO
    return value


_INDEPENDENT = []


def independent() -> dict:
    """independent_counts(), read once per process: it calls none of walk_counts' classifiers, so no mutant moves
    it."""
    if not _INDEPENDENT:
        _INDEPENDENT.append(independent_counts())
    return copy.deepcopy(_INDEPENDENT[0])


def counted(value) -> dict:
    return {slot: {a: per[a]["count"] for a in wc.ARMS} for slot, per in slot_entries(value).items()}


def witness_problems() -> list:
    """Every witness of WC1-WC3, as a list of problems ([] when all hold): what each mutant must turn red."""
    covered, deferred = walk_set()
    value, readings = wc.count(REGISTER, WALKS, covered, deferred)
    out = closer_problems() + shape_problems() + instance_problems(readings)
    out += unreached_problems(value) + listing_problems(value)
    if counted(value) != independent():
        out.append(f"WC3 counts {counted(value)} != the independent reading {independent()}")
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


EXPECTED_VALUE_COUNTS = {
    "on_path_closers": {"A": (0, 0, 14, 7), "O": (0, 0, 4, 1), "G": (NO, None, 0, 0)},
    "off_path_offers": {"A": (0, 0, 14, 7), "O": (0, 0, 4, 1), "G": (NO, None, 0, 0)},
    "inherited_shapes/0": {"A": (1, 1, 14, 7), "O": (0, 0, 4, 1), "G": (NO, None, 0, 0)},
    "inherited_shapes/1": {"A": (0, 0, 14, 7), "O": (0, 0, 4, 1), "G": (NO, None, 0, 0)},
}


class WC3Walks(unittest.TestCase):
    def test_wc3_the_counts_over_the_walks_the_freeze_counts(self):
        self.assertEqual(witness_problems(), [])
        covered, deferred = walk_set()
        value, _ = wc.count(REGISTER, WALKS, covered, deferred)
        for slot, per in slot_entries(value).items():
            for arm, (n, k, c, r) in EXPECTED_VALUE_COUNTS[slot].items():
                e = per[arm]
                with self.subTest(slot=slot, arm=arm):
                    self.assertEqual((e["count"], e.get("walks_with_one_or_more"), e["walks_counted"]), (n, k, c))
                    if r is not None:
                        self.assertEqual(e["walks_reached"], r)
        # both shape slots read the same confounded-design walks
        for arm in wc.ARMS:
            self.assertEqual(value["inherited_shapes"][0][arm]["walks_reached"],
                             value["inherited_shapes"][1][arm]["walks_reached"])

    def test_wc3_only_covered_walks_of_both_tasks_are_read(self):
        covered, deferred = walk_set()
        _, readings = wc.count(REGISTER, WALKS, covered, deferred)
        want = sorted(e["walk"] for e in REGISTER if e["task"] in (wc.CLOSER_TASK, wc.SHAPE_TASK)
                      and e["walk"] in covered)
        self.assertEqual(sorted(r["walk"] for r in readings), want)
        self.assertEqual(len(want), 36)
        for rejected in ("w031", "w151", "w-o31", "w-o32", "w-g27"):
            self.assertNotIn(rejected, covered, f"{rejected} is a walk the freeze's coverage leg does not count")

    def test_wc3_the_walk_set_is_the_coverage_reports(self):
        # the set is the report's got.covered, every covering walk of every spec, and its deferred arms, never
        # re-derived: a stand-in report's walks come back exactly (read in a fresh cache entry)
        fake = {"got": {"covered": {"k1": ["w185", "w-o83"], "k2": ["w191"]}}, "deferred": {"G": {}}}
        saved = dict(wc._COVERAGE)
        self.addCleanup(lambda: (wc._COVERAGE.clear(), wc._COVERAGE.update(saved)))
        wc._COVERAGE.clear()
        with mock.patch.object(walk_plan, "coverage_report", return_value=fake) as called:
            got = wc.coverage(HERE)
        called.assert_called_once_with(study_dir=HERE)
        self.assertEqual(got, (frozenset({"w185", "w-o83", "w191"}), frozenset({"G"})))
        self.assertIn("G", walk_set()[1])


class WC4Draft(unittest.TestCase):
    def test_wc4_the_draft_holds_the_counts(self):
        want = dict(wc.counts(), report_beside_registration=True)
        self.assertEqual(build_draft.build()["walk_counts"], want)
        committed = json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))
        self.assertEqual(committed["walk_counts"], want)
        self.assertFalse([k for k in committed["pending"] if k.startswith("/walk_counts/")])
        self.assertFalse([k for k in build_draft.pending(committed) if k.startswith("/walk_counts/")])
        # the unreached arm is in the committed bytes, and reopens no pending input
        self.assertEqual(committed["walk_counts"]["on_path_closers"]["G"]["count"], NO)


class WC5Refusals(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wc5-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for w in ("w031", "w151"):
            shutil.copytree(WALKS / w, self.tmp / w)
        self.entries = [entry("w031"), entry("w151")]
        self.covered = {"w031", "w151"}

    def refuses(self, entries=None, needle="", covered=None):
        with self.assertRaises(wc.CountError) as cm:
            wc.count(self.entries if entries is None else entries, self.tmp,
                     self.covered if covered is None else covered)
        self.assertIn(needle, str(cm.exception))

    def test_wc5_the_copies_count_as_the_walks_do(self):
        value, _ = wc.count(self.entries, self.tmp, self.covered)
        self.assertEqual(value["on_path_closers"]["A"]["count"], 1)
        self.assertEqual(value["inherited_shapes"][0]["A"]["count"], 1)
        value, _ = wc.count(self.entries, self.tmp, {"w151"})
        self.assertEqual(value["on_path_closers"]["A"]["count"], NO, "a walk outside the set is not read")

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

    def test_wc5_a_covered_walk_the_register_does_not_list_refuses(self):
        self.refuses(covered={"w031", "w151", "w-nowhere"}, needle="w-nowhere")

    def test_wc5_a_coverage_report_that_raises_refuses(self):
        saved = dict(wc._COVERAGE)
        self.addCleanup(lambda: (wc._COVERAGE.clear(), wc._COVERAGE.update(saved)))
        wc._COVERAGE.clear()
        with mock.patch.object(walk_plan, "coverage_report", side_effect=walk_plan.PlanRefused("refused for the test")):
            with self.assertRaises(wc.CountError) as cm:
                wc.counts()
        self.assertIn("coverage report refuses", str(cm.exception))

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


def _mutant_closer_read_only_closes(text, on_path):
    """on_path_closers: a mixed on-path and read-only request counted as a closer (the grader's no-offer reading)."""
    return [(p, wc.CLOSER if k is None and p in ta.REQUESTS and "explain the output" in text else k)
            for p, k in REAL["phrase_kinds"](text, on_path)]


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


def _mutant_walk_set_ignored(walk, covered):
    """the walk set: every registered walk counted, the ones the freeze rejects included (w031, w151, w-o31, w-o32)."""
    return True


def _mutant_unreached_reads_zero(readings, slot, task, arm, deferred):
    """the unreached arm: written as 0 over no reached walk."""
    got = REAL["_arm_entry"](readings, slot, task, arm, deferred)
    return dict(got, count=0) if got["count"] == NO else got


def _mutant_phrase_filter_dropped(sentence):
    """the CP5-req 169 listing: every closing sentence listed, a phrase of the set or not."""
    return False


REAL = {"phrase_kinds": wc.phrase_kinds, "sentence_shape": wc.sentence_shape, "_arm_entry": wc._arm_entry}
MUTANTS = {
    "closer-r2-dropped": ("phrase_kinds", _mutant_closer_r2_dropped),
    "closer-read-only-closes": ("phrase_kinds", _mutant_closer_read_only_closes),
    "offer-negation-ignored": ("phrase_kinds", _mutant_offer_negation_ignored),
    "offer-advice-dropped": ("phrase_kinds", _mutant_offer_advice_dropped),
    "shape0-own-clause": ("sentence_shape", _mutant_shape0_own_clause),
    "shape0-because-dropped": ("sentence_shape", _mutant_shape0_because_dropped),
    "shape1-subjects-dropped": ("sentence_shape", _mutant_shape1_subjects_dropped),
    "shape1-never": ("sentence_shape", _mutant_shape1_never),
    "walk-set-ignored": ("in_walk_set", _mutant_walk_set_ignored),
    "unreached-reads-zero": ("_arm_entry", _mutant_unreached_reads_zero),
    "phrase-filter-dropped": ("holds_a_phrase", _mutant_phrase_filter_dropped),
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
            value, _ = wc.count([entry("w031")], tmp, {"w031"})
        self.assertEqual(value["on_path_closers"]["A"]["count"], 1, "the mutant counts the walk the counter refuses")
        with self.assertRaises(wc.CountError):
            wc.count([entry("w031")], tmp, {"w031"})


class WC7Store(unittest.TestCase):
    """Lane gap-prebeacon-fix: the covered-set store keeps a reading only under its exact input state and fails closed:
    a state that differs by any byte, a store file that does not parse to the two lists, another study folder, a road
    function a test patched, and a state git cannot say each read the report afresh; a refusal is never stored."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wc7-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        import os
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}   # a GIT_ variable stands the store down
        env = mock.patch.dict("os.environ", dict(clean, **{wc.STORE_ENV: str(self.tmp / "store")}), clear=True)
        env.start()
        self.addCleanup(env.stop)
        saved = dict(wc._COVERAGE)
        self.addCleanup(lambda: (wc._COVERAGE.clear(), wc._COVERAGE.update(saved)))
        wc._COVERAGE.clear()

    def test_wc7_a_reading_is_taken_only_under_its_exact_state(self):
        wc.store_write("S", {"w1", "w2"}, {"G"})
        self.assertEqual(wc.store_read("S"), (frozenset({"w1", "w2"}), frozenset({"G"})))
        for other in ("S ", "s", "", "S2"):
            self.assertIsNone(wc.store_read(other), other)
        path = wc._store_path("S")
        for bad in ("not json", json.dumps({"state": "T", "covered": [], "deferred": []}),
                    json.dumps({"state": "S", "covered": "w1", "deferred": []}),
                    json.dumps({"state": "S", "covered": [1], "deferred": []}),
                    json.dumps({"state": "S", "covered": [], "deferred": [], "extra": 1}),
                    json.dumps(["S", [], []])):
            path.write_text(bad)
            self.assertIsNone(wc.store_read("S"), bad)

    def scratch_repo(self) -> Path:
        import subprocess
        top = self.tmp / "repo"
        (top / "study").mkdir(parents=True)
        (top / ".gitignore").write_text("*.out\n")
        (top / "study" / "a.json").write_text("{}\n")
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t", "PATH": __import__("os").environ["PATH"], "HOME": str(self.tmp)}
        self.git = lambda *a: subprocess.run(["git", "-C", str(top), *a], check=True, capture_output=True, env=env)
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "c1")
        return top

    def test_wc7_the_state_moves_with_every_input_byte(self):
        top = self.scratch_repo()
        study = (top / "study").resolve()
        with mock.patch.object(wc, "HERE", study), mock.patch.object(wc, "_road_is_genuine", lambda: True):
            base = wc.store_state(study)
            self.assertIsNotNone(base)
            seen = {base}
            (top / "study" / "a.json").write_text('{"x": 1}\n')                 # a tracked file changed
            seen.add(wc.store_state(study))
            (top / "study" / "a.json").write_text('{"x": 2}\n')                 # changed again, same status letters
            seen.add(wc.store_state(study))
            (top / "study" / "new.json").write_text("{}\n")                      # untracked
            seen.add(wc.store_state(study))
            (top / "study" / "w.out").write_text("x\n")                         # ignored
            seen.add(wc.store_state(study))
            self.git("add", "-A")
            self.git("commit", "-qm", "c2")                                      # HEAD moved, tree clean
            seen.add(wc.store_state(study))
            self.assertEqual(len(seen), 6, "every input change moves the state")
            clean = wc.store_state(study)
            (top / "study" / "__pycache__").mkdir()
            (top / "study" / "__pycache__" / "m.cpython.pyc").write_bytes(b"x")  # bytecode cache aside
            self.assertEqual(wc.store_state(study), clean)
            self.assertIsNone(wc.store_state(top))                               # another folder: no store
            self.git("update-index", "--assume-unchanged", "study/a.json")       # git status would hide a change
            self.assertIsNone(wc.store_state(study))
        self.assertIsNone(wc.store_state(self.tmp))                              # not this module's folder

    def test_wc7_a_patched_road_reads_the_report(self):
        import pending_walk
        import walk_register
        self.assertTrue(wc._road_is_genuine())
        for module, name in ((walk_plan, "coverage_report"), (pending_walk, "uncounted_walks"),
                             (pending_walk, "checker_standing"), (walk_register, "check")):
            with self.subTest(name=name), mock.patch.object(module, name, lambda *a, **k: None):
                self.assertFalse(wc._road_is_genuine())
                self.assertIsNone(wc.store_state(HERE))

    def test_wc7_coverage_takes_a_stored_reading_and_never_writes_its_own(self):
        # glitch-45's ruling on review 200ceab MAJOR 1, option (a): a process that misses runs the report in process
        # and writes nothing; a stored reading comes only from the isolated child (store_child)
        fake = {"got": {"covered": {"k": ["w9"]}}, "deferred": {"G": {}}}
        wc.store_write("S", {"w1"}, {"G"})
        with mock.patch.object(wc, "store_state", return_value="S"), \
                mock.patch.object(walk_plan, "coverage_report", return_value=fake) as called:
            self.assertEqual(wc.coverage(HERE), (frozenset({"w1"}), frozenset({"G"})))
        called.assert_not_called()
        wc._COVERAGE.clear()
        with mock.patch.object(wc, "store_state", return_value="T"), \
                mock.patch.object(walk_plan, "coverage_report", return_value=fake):
            self.assertEqual(wc.coverage(HERE), (frozenset({"w9"}), frozenset({"G"})))
        wc._COVERAGE.clear()
        with mock.patch.object(wc, "store_state", return_value="V"), \
                mock.patch.object(walk_plan, "coverage_report", side_effect=walk_plan.PlanRefused("refused")):
            with self.assertRaises(wc.CountError):
                wc.coverage(HERE)
        self.assertIsNone(wc.store_read("T"))
        self.assertEqual(sorted(p.name for p in (self.tmp / "store").iterdir()), [wc._store_path("S").name],
                         "a process wrote a reading it computed itself")

    def test_wc7_a_patched_process_writes_nothing_and_no_later_process_reads_it(self):
        # review 200ceab MAJOR 1, the reviewer's reproduction: a patch the road guard cannot see (the register folder)
        # gives this process its own reading; it is never stored, so a later, unpatched process cannot take it
        import subprocess
        import walk_register
        empty = self.tmp / "rehearsals"
        empty.mkdir()
        (empty / "register.json").write_text(json.dumps({"schema": 1, "walks": []}))
        self.assertIs(walk_plan.walk_register, walk_register, "the road reads the register module patched here")
        with mock.patch.object(walk_register, "REHEARSALS", empty):
            covered, _ = wc.coverage(HERE)
        self.assertEqual(covered, frozenset(), "the patched process reads its own register")
        store = self.tmp / "store"
        self.assertFalse(store.exists() and any(store.iterdir()), "the patched process wrote a reading")
        later = subprocess.run([sys.executable, "-I", "-B", "-c",
                                "import sys; sys.path.insert(0, sys.argv[1]); import walk_counts as wc; "
                                "s = wc.store_state(wc.HERE); print(None if s is None else wc.store_read(s))", str(HERE)],
                               capture_output=True, text=True, timeout=300, env=dict(__import__("os").environ))
        self.assertEqual((later.returncode, later.stdout.strip()), (0, "None"), later.stderr[-2000:])

    def test_wc7_only_an_isolated_child_produces_a_reading(self):
        # the child entry refuses unless it is `python -I -B` with no unittest.mock loaded, before reading anything
        import subprocess
        script = str(HERE / "walk_counts.py")
        # The -I child without -B writes bytecode, and -I ignores PYTHONDONTWRITEBYTECODE, so its caches go to a
        # pycache_prefix under self.tmp, never beside the study's sources (athena gap4-beacon2-1533750: the 22 .pyc
        # files it left made the battery tree read changed, and the --outputs step refused).
        caches = self.tmp / "pycache"
        for argv in ([sys.executable, "-B", script, "--store-coverage"],
                     [sys.executable, "-X", f"pycache_prefix={caches}", "-I", script, "--store-coverage"]):
            with self.subTest(argv=argv[1:-2]):
                got = subprocess.run(argv, capture_output=True, text=True, timeout=120)
                self.assertNotEqual(got.returncode, 0, got.stdout)
                self.assertIn("refused", got.stdout)
        self.assertTrue(any(caches.rglob("*.pyc")), "the child without -B wrote no bytecode, so it was not that child")
        self.assertFalse((self.tmp / "store").exists(), "a child that is not isolated wrote a reading")
        # the true child passes the gate: run with GIT_DIR set, it gets past the refusal and stands down before any read
        import os
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        got = subprocess.run([sys.executable, "-I", "-B", script, "--store-coverage"], capture_output=True, text=True,
                             timeout=120, env=dict(env, GIT_DIR=str(self.tmp / "no-repo")))
        self.assertEqual((got.returncode, got.stdout.strip()),
                         (0, "walk_counts: store stood down: a GIT_ variable is set: GIT_DIR"), got.stderr[-1500:])
        # prime_store hands the read to exactly that child, from the module's own file, and adds nothing of its own
        calls = []
        def fake_run(argv, **kw):
            calls.append((argv, kw))
            return mock.Mock(returncode=0, stdout="walk_counts: stored\n", stderr="")
        with mock.patch.object(wc, "store_state_why", return_value=("P", "")), mock.patch("subprocess.run", fake_run):
            self.assertEqual(wc.prime_store(), "walk_counts: stored")
        self.assertEqual([a[:4] for a, _ in calls], [[sys.executable, "-I", "-B", script]])
        self.assertEqual(calls[0][0][4:], ["--store-coverage"])
        self.assertFalse((self.tmp / "store").exists())

    def test_wc7_a_symlink_or_a_git_variable_stands_the_store_down(self):
        # review 200ceab findings 2 and 3: a link is read through by the road but keyed by its target text, and a GIT_
        # variable can point the road's own git reads at another repository; either way, no store
        import os
        top = self.scratch_repo()
        study = (top / "study").resolve()
        outside = self.tmp / "outside.json"
        outside.write_text("{}\n")
        with mock.patch.object(wc, "HERE", study), mock.patch.object(wc, "_road_is_genuine", lambda: True):
            base = wc.store_state(study)
            self.assertIsNotNone(base)
            for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CEILING_DIRECTORIES", "GIT_CONFIG_GLOBAL",
                        "GIT_CONFIG_NOSYSTEM"):
                with self.subTest(var=var), mock.patch.dict(os.environ, {var: str(top)}):
                    self.assertIsNone(wc.store_state(study))
            # glitch-45's ruling (28 Oct 2026): exactly GIT_EDITOR, GIT_PAGER and GIT_TERMINAL_PROMPT, which steer no
            # read, leave the store on, alone or together, and enter no key; beside any other GIT_ variable it stays off
            allowed = {"GIT_EDITOR": "vi", "GIT_PAGER": "cat", "GIT_TERMINAL_PROMPT": "0"}
            for var, value in allowed.items():
                with self.subTest(allowed=var), mock.patch.dict(os.environ, {var: value}):
                    self.assertEqual(wc.store_state(study), base)
            with mock.patch.dict(os.environ, allowed):
                self.assertEqual(wc.store_state(study), base)
            with mock.patch.dict(os.environ, dict(allowed, GIT_DIR=str(top / ".git"))):
                self.assertIsNone(wc.store_state(study))
            self.assertEqual(wc.STORE_GIT_ALLOWED, ("GIT_EDITOR", "GIT_PAGER", "GIT_TERMINAL_PROMPT"))
            # lane gap-prebeacon-fix3: GIT_CEILING_DIRECTORIES (the athena suite sets it on every battery line) leaves
            # the store on, keying nothing, exactly when no entry is the top folder or inside it, where git's own
            # search from the study folder still finds this repository; an entry at or inside the top, a relative one,
            # or a link resolving inside the top keeps it off, as does any other GIT_ variable beside a good ceiling
            import subprocess
            def found(ceiling):
                got = subprocess.run(["git", "-C", str(study), "rev-parse", "--show-toplevel"], capture_output=True,
                                     text=True, env={"PATH": os.environ["PATH"], "GIT_CEILING_DIRECTORIES": ceiling})
                return got.returncode == 0 and Path(got.stdout.strip()).resolve() == top.resolve()
            (self.tmp / "alias").symlink_to(top / "study")
            outside_ok = (str(top.parent), str(self.tmp / "elsewhere"), f"{top.parent}{os.pathsep}/nonexistent",
                          f"{os.pathsep}{top.parent}")
            inside = (str(top), str(top / "study"), str(top) + "/", str(self.tmp / "alias"), "relative/path",
                      f"{top.parent}{os.pathsep}{top}")
            for value in outside_ok:
                with self.subTest(ceiling=value), mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": value}):
                    self.assertTrue(found(value), "git finds the repository under this ceiling")
                    self.assertEqual(wc.store_state(study), base)
            for value in inside:
                with self.subTest(ceiling=value), mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": value}):
                    self.assertIsNone(wc.store_state(study))
            self.assertFalse(found(str(top)), "a ceiling at the top folder hides the repository from git")
            with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(top.parent), "GIT_DIR": str(top / ".git")}):
                self.assertIsNone(wc.store_state(study))
            (self.tmp / "alias").unlink()
            # closure review 49c93d2 NIT 1: a ceiling entry that is a link loop cannot be resolved on Python 3.12 and
            # older (RuntimeError), and there the store stands down; 3.13 returns the path, which here lies outside the
            # tree, so the store rightly stays on. Either way nothing raises
            (self.tmp / "loop-a").symlink_to(self.tmp / "loop-b")
            (self.tmp / "loop-b").symlink_to(self.tmp / "loop-a")
            loop = str(self.tmp / "loop-a")
            with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": loop}):
                wc.store_state(study)                                          # never raises, whatever this Python does
            real_top = top.resolve()
            with mock.patch.object(Path, "resolve", side_effect=RuntimeError("Symlink loop")):
                self.assertEqual(wc._ceiling_reaches(loop, real_top),
                                 f"GIT_CEILING_DIRECTORIES holds {loop}, which cannot be resolved")
            (top / "study" / "link.json").symlink_to(outside)                   # an untracked link
            self.assertIsNone(wc.store_state(study))
            self.git("add", "-A")
            self.git("commit", "-qm", "tracked link")                           # a tracked link, the tree clean
            self.assertIsNone(wc.store_state(study))
            self.git("rm", "-q", "study/link.json")
            self.git("commit", "-qm", "no link")
            self.assertIsNotNone(wc.store_state(study))
            (top / "study" / "a.json").unlink()
            (top / "study" / "a.json").symlink_to(outside)                      # a tracked file replaced by a link
            self.assertIsNone(wc.store_state(study))


    def child_env(self) -> dict:
        import os
        return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def test_wc7_a_hand_patched_process_cannot_be_the_child(self):
        # closure review 9bc0822 NIT 1, the reviewer's reproduction: an `-I -B` process that patches the register folder
        # (WALKS_DIR and REHEARSALS, here to a folder outside the tree, so the state is the real one) and then calls
        # store_child, or runs the module as __main__ through runpy after patching, is refused and writes nothing
        import subprocess
        fx = self.tmp / "fx"
        fx.mkdir()
        (fx / "register.json").write_text(json.dumps({"schema": 1, "walks": []}))
        script = str(HERE / "walk_counts.py")
        patch = (f"import sys; sys.path.insert(0, {str(HERE)!r}); import mode_binding, walk_register; "
                 f"from pathlib import Path; mode_binding.WALKS_DIR = {str(fx)!r}; walk_register.REHEARSALS = Path({str(fx)!r}); ")
        for case, code in (("called", patch + "import walk_counts as wc; print('genuine', wc._road_is_genuine()); "
                                             "raise SystemExit(wc.store_child())"),
                           ("runpy", patch + f"import runpy; sys.argv = [{script!r}, '--store-coverage']; "
                                             f"runpy.run_path({script!r}, run_name='__main__')")):
            with self.subTest(case=case):
                shutil.rmtree(self.tmp / "store", True)
                got = subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True,
                                     timeout=600, env=self.child_env())
                self.assertIn("store refused", got.stdout, got.stdout + got.stderr[-1500:])
                self.assertNotEqual(got.returncode, 0)
                store = self.tmp / "store"
                self.assertFalse(store.exists() and any(store.iterdir()), "a hand-patched process stored a reading")

    def test_wc7_a_patched_register_folder_never_takes_a_stored_reading(self):
        # closure review 9bc0822 NIT 4: with this tree's reading stored, a process whose register folder is patched
        # reads its own register (empty), never the stored reading
        import walk_register
        state = wc.store_state(HERE)
        self.assertIsNotNone(state, "the witness needs the store in use on this tree")
        wc.store_write(state, {"w1"}, set())
        self.assertEqual(wc.coverage(HERE), (frozenset({"w1"}), frozenset()), "the seeded reading is taken unpatched")
        wc._COVERAGE.clear()
        empty = self.tmp / "rehearsals"
        empty.mkdir()
        (empty / "register.json").write_text(json.dumps({"schema": 1, "walks": []}))
        self.assertIs(walk_plan.walk_register, walk_register, "the road reads the register module patched here")
        with mock.patch.object(walk_register, "REHEARSALS", empty):
            covered, _ = wc.coverage(HERE)
        self.assertEqual(covered, frozenset(), "a patched register folder took the stored reading")

    def test_wc7_a_replaced_road_module_stands_the_store_down(self):
        # lane gap-prebeacon-fix3 (athena gap4-prebeacon3-49c93d2): once sys.modules holds another walk_register than
        # the one walk_plan imported, a patch of either copy misses the other side, so the store is not used at all
        import types
        import walk_register
        self.assertTrue(wc._road_is_genuine())
        for holder, name in ((walk_plan, "walk_register"), (walk_register, "mode_binding"), (wc, "mode_binding")):
            with self.subTest(holder=holder.__name__, name=name):
                other = types.ModuleType(name)
                with mock.patch.dict(sys.modules, {name: other}):
                    self.assertFalse(wc._road_is_genuine())
                    self.assertIsNone(wc.store_state(HERE))
                self.assertTrue(wc._road_is_genuine())
                with mock.patch.object(holder, name, other):
                    self.assertFalse(wc._road_is_genuine())
                self.assertTrue(wc._road_is_genuine())
                # review 90c1fd9 NIT 2: whatever stands in, not only a module of the same name
                for stand_in in (mock.MagicMock(), types.SimpleNamespace(), types.ModuleType("elsewhere")):
                    with mock.patch.object(holder, name, stand_in):
                        self.assertFalse(wc._road_is_genuine(), type(stand_in).__name__)
                self.assertTrue(wc._road_is_genuine())

    def test_wc7_an_unregistered_copy_reads_its_own_references(self):
        # review 2f99816 NIT 2: the guard reads the executing copy's own names (globals()), not sys.modules' walk_counts,
        # so a copy that sys.modules does not hold, whose road reference is not sys.modules' object, stands down
        import types
        twin = types.ModuleType("walk_counts")
        twin.__file__ = wc.__file__
        exec(compile(Path(wc.__file__).read_text(), wc.__file__, "exec"), twin.__dict__)
        self.assertIsNot(twin, sys.modules["walk_counts"])
        self.assertTrue(twin._road_is_genuine())
        twin.pending_walk = types.ModuleType("pending_walk")     # not a STORE_REFERENCE_PAIRS name: the sweep's alone
        self.assertFalse(twin._road_is_genuine())

    def test_wc7_replaced_objects_stand_the_store_down(self):
        # closure review 9bc0822 NIT 2: git show honours refs/replace and info/grafts, which the state does not hold
        top = self.scratch_repo()
        study = (top / "study").resolve()
        with mock.patch.object(wc, "HERE", study), mock.patch.object(wc, "_road_is_genuine", lambda: True):
            self.assertIsNotNone(wc.store_state(study))
            (self.tmp / "other.json").write_text('{"tampered": true}\n')
            blob = self.git("hash-object", "-w", str(self.tmp / "other.json")).stdout.decode().strip()
            old = self.git("rev-parse", "HEAD:study/a.json").stdout.decode().strip()
            self.git("replace", old, blob)
            self.assertIsNone(wc.store_state(study))
            self.git("replace", "-d", old)
            self.assertIsNotNone(wc.store_state(study))
            grafts = top / ".git" / "info" / "grafts"
            grafts.parent.mkdir(exist_ok=True)
            grafts.write_text("")
            self.assertIsNone(wc.store_state(study))


if __name__ == "__main__":
    unittest.main()
