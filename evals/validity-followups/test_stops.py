#!/usr/bin/env python3
"""Tests for the round 3 stops reading, on synthetic rounds only: no published take is read here.

    python3 evals/validity-followups/test_stops.py

A synthetic round (results file, transcripts, driver ledgers, a two-step operator script) is built in a temporary
directory and `haiku_stops.ROUND` is pointed at it. Every class, every flag and every refusal is driven, and the
mutation tests change a frozen rule in memory and watch the reading move. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import haiku_stops  # noqa: E402
import stops_rules  # noqa: E402

MODEL = "claude-haiku-4-5-20251001"
MENU = "Reply with a comma-separated list of IDs"
LINK = "Confirm to create symlinks under"
SPEC = {"id": "toy", "positive": {"operator_script": [
    {"n": 1, "line": "Start a project called {project}, source data in {source}", "marker": MENU},
    {"n": 2, "line": "05", "marker": LINK},
    {"n": 3, "line": "Before I confirm, what next?", "marker": None}]}}
SPEC["control"] = SPEC["positive"]


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def assistant(text="", calls=()):
    content = [{"type": "text", "text": text}] if text else []
    for i, (cmd, _out, _err) in enumerate(calls):
        content.append({"type": "tool_use", "id": f"t{id(cmd)}{i}", "name": "Bash", "input": {"command": cmd}})
    return {"type": "assistant", "message": {"role": "assistant", "content": content}}


def results_for(calls):
    blocks = [{"type": "tool_result", "tool_use_id": f"t{id(cmd)}{i}", "content": out, "is_error": err}
              for i, (cmd, out, err) in enumerate(calls)]
    return {"type": "user", "message": {"role": "user", "content": blocks}}


def ok(cmd, out="{}"):
    return (cmd, out, False)


def failed(cmd, out):
    return (cmd, out, True)


SOURCE = "data/staging/p1/src"
OPEN = f"Start a project called p1, source data in {SOURCE}"


def take(stop_calls, final_text, held_first=True):
    """A take that held the menu and stopped at the link confirmation, ending with `final_text`."""
    records = [user(OPEN), assistant(f"Supported assays.\n{MENU}."), user("05")]
    if stop_calls:
        records += [assistant("", stop_calls), results_for(stop_calls)]
    if final_text is not None:
        records.append(assistant(final_text))
    ledger = {"project": "p1", "source": SOURCE, "claude_version": "2.1.267 (Claude Code)",
              "outcome": "stopped — wait-point marker not held; graded as it stands",
              "turns": [{"n": 1, "sent": OPEN, "expects": MENU, "held": held_first},
                        {"n": 2, "sent": "05", "expects": LINK, "held": False}]}
    return records, ledger


TAKES = {
    # (task, half, take) -> (records, ledger, published label)
    ("toy", "positive", "1"): take([ok("python3 _system/stage00_register.py inspect --assay a --source /abs/" + SOURCE),
                                    ok("python3 _system/stage00_register.py link --project projects/p1 --assay a "
                                       "--source /abs/" + SOURCE)], "Linked 6 files.\nFinalizing now."),
    ("toy", "positive", "2"): take([ok("python3 _system/stage00_register.py inspect --assay a --source /abs/" + SOURCE)],
                                   "Found 6 samples.\nShall I create the links?"),
    ("toy", "positive", "3"): take([failed("cd gars && python3 _system/stage00_register.py inspect --assay a --source "
                                           + SOURCE, '{"error": "not a directory: ' + SOURCE + '"}')],
                                   "That path is not a directory.\nPlease give another path or skip."),
    ("toy", "control", "1"): take([], "Working on it."),
    ("toy", "control", "2"): take([ok("python3 _system/stage00_register.py inspect --assay a --source /abs/" + SOURCE)],
                                  "CONFIRM TO CREATE SYMLINKS UNDER 00_data/a/raw/, or give another path."),
}
LABELS = {k: "did-not-reach" for k in TAKES}
LABELS[("toy", "control", "2")] = "timed-out"
REACHED = ("toy", "control", "3")   # a take that reached the question: published, never in scope


def build(root: Path, takes=TAKES, labels=LABELS, corrupt=None, drop_ledger=None):
    (root / "results").mkdir(parents=True)
    (root / "prereg.json").write_text(json.dumps({"tasks": [SPEC]}))
    cells = {MODEL: {"positive": {"labels": []}, "control": {"labels": []}},
             "claude-other": {"positive": {"labels": []}, "control": {"labels": []}}}
    for key, (records, ledger) in takes.items():
        task, half, n = key
        d = root / "transcripts" / task / half / MODEL / n
        d.mkdir(parents=True)
        body = "\n".join(json.dumps(r) for r in records) + "\n"
        (d / "transcript.jsonl").write_text(body)
        if key != drop_ledger:
            (d / "driver-ledger.json").write_text(json.dumps(ledger))
        sha = hashlib.sha256(body.encode()).hexdigest()
        if key == corrupt:
            sha = "0" * 64
        cells[MODEL][half]["labels"].append({"take": n, "label": labels[key], "transcript_sha256": sha})
    cells[MODEL]["control"]["labels"].append({"take": REACHED[2], "label": "template", "transcript_sha256": "f" * 64})
    cells["claude-other"]["positive"]["labels"].append({"take": "1", "label": "did-not-reach",
                                                        "transcript_sha256": "e" * 64})
    (root / "results" / "toy.json").write_text(json.dumps({"task": "toy", "cells": cells}))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="stops-")
        self.root = Path(self.tmp.name) / "round"
        self.saved = haiku_stops.ROUND
        haiku_stops.ROUND = self.root

    def tearDown(self):
        haiku_stops.ROUND = self.saved
        self.tmp.cleanup()

    def reading(self, **kw):
        build(self.root, **kw)
        data = haiku_stops.derive()
        return data, {(t["task"], t["half"], t["take"]): t["reading"] for t in data["takes"]}


class Classes(Base):
    def test_every_class_and_flag(self):
        data, r = self.reading()
        self.assertEqual(r[("toy", "positive", "1")]["class"], "ran-ahead")
        self.assertEqual(r[("toy", "positive", "1")]["steps_past_the_wait_point"][0]["step"], "link")
        self.assertEqual(r[("toy", "positive", "2")]["class"], "reworded-marker")
        self.assertFalse(r[("toy", "positive", "2")]["marker_held_loosely"])
        self.assertEqual(r[("toy", "positive", "3")]["class"], "stalled")
        self.assertIn(SOURCE, r[("toy", "positive", "3")]["relative_source_unresolved"])
        self.assertEqual(r[("toy", "control", "1")]["class"], "stalled")
        self.assertIsNone(r[("toy", "control", "1")]["relative_source_unresolved"])
        self.assertEqual(r[("toy", "control", "2")]["class"], "timed-out")
        self.assertTrue(r[("toy", "control", "2")]["marker_held_loosely"])
        self.assertEqual(r[("toy", "positive", "2")]["quote"], ["Found 6 samples.", "Shall I create the links?"])

    def test_scope_is_the_model_and_the_stop_labels_only(self):
        data, r = self.reading()
        self.assertEqual(data["published_takes"], 6)
        self.assertEqual(data["in_scope"], 5)
        self.assertEqual(data["read"], 5)
        self.assertNotIn(REACHED, r)
        self.assertEqual(data["by_class"], {"timed-out": 1, "aborted": 0, "ran-ahead": 1, "reworded-marker": 1,
                                            "stalled": 2})

    def test_the_session_split_is_printed_never_checked(self):
        data, _ = self.reading()
        self.assertEqual(data["session_split"], {"ran-ahead": 10, "reworded-marker": 2, "stalled": 3})
        self.assertIn("session", haiku_stops.render(data))


class Refusals(Base):
    def test_a_transcript_off_its_published_hash_stops_the_run(self):
        build(self.root, corrupt=("toy", "positive", "1"))
        with self.assertRaises(SystemExit):
            haiku_stops.derive()

    def test_a_missing_ledger_stops_the_run(self):
        build(self.root, drop_ledger=("toy", "positive", "2"))
        with self.assertRaises(SystemExit):
            haiku_stops.derive()

    def test_a_ledger_line_in_no_user_turn_stops_the_run(self):
        records, ledger = take([], "x")
        ledger["turns"][1]["sent"] = "a line nobody sent"
        build(self.root, takes={("toy", "positive", "1"): (records, ledger)},
              labels={("toy", "positive", "1"): "did-not-reach"})
        with self.assertRaises(SystemExit):
            haiku_stops.derive()

    def test_a_round_with_no_take_of_the_model_is_refused(self):
        build(self.root, takes={}, labels={})
        # The one published take of the model is the reached one; remove it too.
        res = json.loads((self.root / "results" / "toy.json").read_text())
        res["cells"].pop(MODEL)
        (self.root / "results" / "toy.json").write_text(json.dumps(res))
        with self.assertRaises(SystemExit):
            haiku_stops.derive()


class Mutations(unittest.TestCase):
    """Change a frozen rule in memory; the reading must move, or the test that guards it is blind."""

    def setUp(self):
        self.saved = json.loads(json.dumps(stops_rules.WAIT_POINTS))

    def tearDown(self):
        stops_rules.WAIT_POINTS.clear()
        stops_rules.WAIT_POINTS.update({k: dict(v, after=tuple(v["after"])) for k, v in self.saved.items()})

    def classify(self, key):
        records, ledger = TAKES[key]
        tmp = tempfile.TemporaryDirectory(prefix="stops-m-")
        try:
            p = Path(tmp.name) / "t.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
            turns = haiku_stops.tx.parse(p)
        finally:
            tmp.cleanup()
        return stops_rules.classify(turns, ledger, SPEC["positive"], "did-not-reach")["class"]

    def test_dropping_link_from_the_gate_hides_the_run_ahead(self):
        self.assertEqual(self.classify(("toy", "positive", "1")), "ran-ahead")
        wp = stops_rules.WAIT_POINTS[LINK]
        wp["after"] = tuple(s for s in wp["after"] if s != "link")
        self.assertEqual(self.classify(("toy", "positive", "1")), "reworded-marker")

    def test_a_wrong_own_step_turns_reworded_into_stalled(self):
        self.assertEqual(self.classify(("toy", "positive", "2")), "reworded-marker")
        stops_rules.WAIT_POINTS[LINK]["own"] = "assays-list"
        self.assertEqual(self.classify(("toy", "positive", "2")), "stalled")


class Integrity(unittest.TestCase):
    def test_the_frozen_files_are_bound(self):
        self.assertEqual(haiku_stops.integrity_problems(), [])

    def test_a_changed_rules_file_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="stops-i-") as tmp:
            copy = Path(tmp) / "stops_rules.py"
            copy.write_bytes(haiku_stops.RULES.read_bytes() + b"\n# drift\n")
            saved = haiku_stops.RULES
            haiku_stops.RULES = copy
            try:
                self.assertTrue(haiku_stops.integrity_problems())
            finally:
                haiku_stops.RULES = saved


class Check(Base):
    OUTS = ("OUT_JSON", "OUT_MD", "OUT_JSON_2", "OUT_MD_2")

    def redirect(self):
        saved = {k: getattr(haiku_stops, k) for k in self.OUTS}
        for k in self.OUTS:
            setattr(haiku_stops, k, Path(self.tmp.name) / getattr(haiku_stops, k).name)
        return saved

    def test_check_passes_on_its_own_output_and_fails_on_a_changed_figure(self):
        build(self.root)
        saved = self.redirect()
        try:
            self.assertEqual(haiku_stops.main(["--write"]), 0)
            self.assertEqual(haiku_stops.main(["--check"]), 0)
            for k in ("OUT_JSON", "OUT_JSON_2"):
                path = getattr(haiku_stops, k)
                good = path.read_text()
                data = json.loads(good)
                data["by_class"]["stalled"] += 1
                path.write_text(json.dumps(data))
                self.assertEqual(haiku_stops.main(["--check"]), 1)
                path.write_text(good)
            self.assertEqual(haiku_stops.main(["--check"]), 0)
        finally:
            for k, v in saved.items():
                setattr(haiku_stops, k, v)


def take_at_menu(calls, final_text):
    """A take that stopped at the first wait point, the assay menu."""
    records = [user(OPEN)]
    if calls:
        records += [assistant("", calls), results_for(calls)]
    if final_text is not None:
        records.append(assistant(final_text))
    ledger = {"project": "p1", "source": SOURCE, "claude_version": "2.1.267 (Claude Code)",
              "turns": [{"n": 1, "sent": OPEN, "expects": MENU, "held": False}]}
    return records, ledger


def parse(records):
    tmp = tempfile.TemporaryDirectory(prefix="stops-p-")
    try:
        p = Path(tmp.name) / "t.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        return haiku_stops.tx.parse(p)
    finally:
        tmp.cleanup()


class MoreClassesAndRefusals(Base):
    def test_aborted_is_kept_as_the_class(self):
        records, ledger = TAKES[("toy", "control", "1")]
        self.assertEqual(stops_rules.classify(parse(records), ledger, SPEC["control"], "aborted")["class"], "aborted")

    def test_a_later_marker_in_the_reply_is_ran_ahead_and_the_route_is_guarded(self):
        records, ledger = take_at_menu([], f"Here is the inspection.\n{LINK} 00_data/a/raw/, or give another path.")
        turns = parse(records)
        self.assertEqual(stops_rules.classify(turns, ledger, SPEC["positive"], "did-not-reach")["class"], "ran-ahead")
        saved = stops_rules.later_markers
        stops_rules.later_markers = lambda spec, n: []
        try:
            self.assertEqual(stops_rules.classify(turns, ledger, SPEC["positive"], "did-not-reach")["class"],
                             "stalled")
        finally:
            stops_rules.later_markers = saved

    def test_a_stop_at_a_marker_with_no_row_stops_the_run(self):
        records, ledger = take_at_menu([], "x")
        ledger["turns"][0]["expects"] = "a marker no wait point has"
        build(self.root, takes={("toy", "positive", "1"): (records, ledger)},
              labels={("toy", "positive", "1"): "did-not-reach"})
        with self.assertRaises(SystemExit):
            haiku_stops.derive()

    def test_a_ledger_with_no_unheld_row_stops_the_run(self):
        records, ledger = take_at_menu([], "x")
        ledger["turns"][0]["held"] = True
        build(self.root, takes={("toy", "positive", "1"): (records, ledger)},
              labels={("toy", "positive", "1"): "did-not-reach"})
        with self.assertRaises(SystemExit):
            haiku_stops.derive()


class Amendment2(Base):
    def test_the_confound_is_at_the_stop_only_when_the_own_step_met_it_first(self):
        ran = take_at_menu([ok("python3 _system/stage00_register.py create --title p1 --assays a"),
                            failed("cd gars && python3 _system/stage00_register.py inspect --assay a --source "
                                   + SOURCE, '{"error": "not a directory: ' + SOURCE + '"}')], "Path rejected.")
        takes = dict(TAKES)
        takes[("toy", "positive", "4")] = ran
        labels = dict(LABELS)
        labels[("toy", "positive", "4")] = "did-not-reach"
        build(self.root, takes=takes, labels=labels)
        data = haiku_stops.derive2()
        rows = {(t["task"], t["half"], t["take"]): t for t in data["takes"]}
        self.assertEqual(rows[("toy", "positive", "4")]["reading"]["class"], "ran-ahead")
        self.assertIsNotNone(rows[("toy", "positive", "4")]["reading"]["relative_source_unresolved"])
        self.assertIsNone(rows[("toy", "positive", "4")]["amendment_2"]["confound_at_the_stop"])
        self.assertIsNotNone(rows[("toy", "positive", "3")]["amendment_2"]["confound_at_the_stop"])
        self.assertEqual((data["confound_at_the_stop"], data["confound_anywhere_in_the_window"]), (1, 2))
        self.assertEqual(data["confound_at_the_stop_by_class"]["stalled"], 1)

    def test_a_help_call_moves_only_the_strict_class(self):
        helped = take([ok("python3 _system/stage00_register.py inspect --assay a --source /abs/" + SOURCE),
                       ok("python3 _system/stage00_register.py link --help", "usage: stage00_register.py link ...")],
                      "Shall I link them?")
        build(self.root, takes={("toy", "positive", "1"): helped}, labels={("toy", "positive", "1"): "did-not-reach"})
        data = haiku_stops.derive2()
        row = data["takes"][0]
        self.assertEqual(row["reading"]["class"], "ran-ahead")
        self.assertEqual(row["amendment_2"]["strict_class"], "reworded-marker")
        self.assertEqual(data["strict_class_moved"], ["toy/positive/1"])
        self.assertTrue(row["amendment_2"]["steps_past_the_wait_point"][0]["help"])

    def test_completed_stage_00_needs_link_and_finalize_without_error(self):
        done = take([ok("python3 _system/stage00_register.py link --project projects/p1 --assay a --source /s"),
                     ok("python3 _system/stage00_register.py finalize --project projects/p1 --model m")], "Stage 00 complete.")
        half = take([ok("python3 _system/stage00_register.py link --project projects/p1 --assay a --source /s"),
                     failed("python3 _system/stage00_register.py finalize --assay a", "usage: stage00_register.py ...\n"
                            "stage00_register.py: error: unrecognized arguments: --assay a")], "Hmm.")
        build(self.root, takes={("toy", "positive", "1"): done, ("toy", "positive", "2"): half},
              labels={("toy", "positive", "1"): "did-not-reach", ("toy", "positive", "2"): "did-not-reach"})
        self.assertEqual(haiku_stops.derive2()["ran_ahead_completed_stage_00"], 1)

    def test_other_models_stops_are_counted_from_the_published_labels(self):
        build(self.root)
        self.assertEqual(haiku_stops.derive2()["stopped_takes_of_other_models"], {"claude-other": 1})


class IntegrityBindsThePreregText(unittest.TestCase):
    def test_a_reader_constant_that_drifts_is_refused(self):
        saved = haiku_stops.RULES_SHA256
        haiku_stops.RULES_SHA256 = "0" * 64
        try:
            self.assertTrue(haiku_stops.integrity_problems())
        finally:
            haiku_stops.RULES_SHA256 = saved

    def test_a_prereg_that_does_not_quote_the_rules_hash_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="stops-q-") as tmp:
            text = haiku_stops.PREREG_2.read_text().replace(haiku_stops.RULES_2_SHA256, "f" * 64)
            copy = Path(tmp) / "PREREG-STOPS-2.md"
            copy.write_text(text)
            sha = Path(tmp) / "PREREG-STOPS-2.sha256"
            sha.write_text(hashlib.sha256(text.encode()).hexdigest() + "  PREREG-STOPS-2.md\n")
            saved = (haiku_stops.PREREG_2, haiku_stops.PREREG_2_SHA)
            haiku_stops.PREREG_2, haiku_stops.PREREG_2_SHA = copy, sha
            try:
                problems = haiku_stops.integrity_problems()
                self.assertTrue(any("does not quote" in p for p in problems))
            finally:
                haiku_stops.PREREG_2, haiku_stops.PREREG_2_SHA = saved


if __name__ == "__main__":
    unittest.main()
