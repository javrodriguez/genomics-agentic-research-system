#!/usr/bin/env python3
"""Lane fold2-ld (Gap Study round 4, pre-freeze review 2's fold, lane L-D; FOLD-PLAN-prefreeze-2.md section 3's
MINORs table, approved by glitch-45 under Javier's delegation, Thu 29 Oct 2026): m8, m10, m13 and m16.

  M10-reach   (m10) result.py prints the outside-reach events per half-cell from every committed outcome: the takes,
              how many carry an outside-reach event, the events.outside_reach total, and the takes whose records give
              no count (named, never counted as none).
  M8-verdicts (m8) the flagged check list yields a committed verdict record (labelling/flagged-verdicts.json, one row
              per listed F item with the person's finding), validated against the drawn list, committed once and only
              after the blind labels; result.py publishes its counts per (arm, harness, model, task) beside the views,
              and no longer says every flagged take goes to the list when a cap of 40 stands.
  M16-cross   (m16) walk_native_cross.py re-derives, from each committed vendor walk's own bytes and through the
              accepted readers (drive.codex_cross_check / gemini_cross_check, never a reader source edited), the native
              cross-check its driver ledger records when that is not pending, and names every walk where the two
              differ; one committed agreed Codex walk re-derives agreed.

Synthetic outcomes in memory. No model, network, container or credential.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)
sys.path.insert(0, str(HERE))

import lint_language as ll  # noqa: E402
import result  # noqa: E402
import stats  # noqa: E402
from graders import labels4  # noqa: E402
from labelling import flagged_verdicts  # noqa: E402

sys.path[:] = _PATH

CLAUDE, CODEX = "claude-code", "codex"
DESIGN = {"tasks_that_run": ["t1"], "harness_models": {CLAUDE: ["a1", "a2"], CODEX: ["o1", "o2"]},
          "stronger_weaker": {CLAUDE: ["a1", "a2"], CODEX: ["o1", "o2"]}, "cross_vendor": ["a1", "o1"], "alpha": "0.05",
          "bootstrap": {"seed": 1, "reps": 20},
          "power": {"seed": 2, "sims": 1, "bootstrap_reps": 1, "wordings": 1, "repeats": 1,
                    "grid": [{"stronger": "0.900", "weaker": "0.500", "task_spread": "0.000",
                              "wording_spread": "0.000"}]}, "floors": None}
PRE = {stats.DESIGN_KEY: DESIGN, "deferred_arms": {}, "models": {"A": ["a1", "a2"], "O": ["o1", "o2"]}, "tasks": [{"id": "t1"}],
       "rows": []}


def row(slot, attempt, *, arm="A", task="t1", half="trap", model="a1", harness=CLAUDE):
    return {"slot": slot, "attempt": attempt, "arm": arm, "task": task, "half": half, "model": model,
            "agent": {"harness": harness, "version": "v"}, "half_cell": f"{arm}-{task}-{half}-{model}"}


def outcome(slot, attempt, state, reach, events=None):
    """A committed outcome; reach is the routed records' events.outside_reach (None: records with no count)."""
    records = None if reach is Ellipsis else {"events": {"outside_reach": reach}}
    if events is None:
        events = ["outside-reach"] if isinstance(reach, int) and reach > 0 else []
    return {"slot": slot, "attempt": attempt, "state": state, "records": records, "events": events}


# ---- M10: outside-reach events per half-cell (m10) ------------------------------------------------------------------

class M10Reach(unittest.TestCase):
    rows = [row("s1", 1), row("s1", 2), row("s2", 1), row("s3", 1, half="normal"),
            row("s4", 1, arm="O", model="o1", harness=CODEX)]
    history = [outcome("s1", 1, labels4.HARNESS_ERROR, 2),          # a re-run attempt is a take too
               outcome("s1", 2, labels4.GRADED, 3),
               {"kind": labels4.RULING, "slot": "s1", "attempt": 1},   # a ruling is never an outcome
               outcome("s2", 1, labels4.GRADED, 0),
               outcome("s3", 1, labels4.ABORTED, Ellipsis, events=None),   # no records: no count to read
               outcome("s4", 1, labels4.GRADED, 0, events=["checker-event-reason"])]

    def test_counts_per_half_cell(self):
        got = result.outside_reach_counts(self.rows, self.history)
        by = {(c["arm"], c["half"]): c for c in got}
        self.assertEqual(len(got), 3)
        self.assertEqual({k: by[("A", "trap")][k] for k in ("takes", "with_event", "events", "unread")},
                         {"takes": 3, "with_event": 2, "events": 5, "unread": 0})
        self.assertEqual({k: by[("A", "normal")][k] for k in ("takes", "with_event", "events", "unread")},
                         {"takes": 1, "with_event": 0, "events": 0, "unread": 1})
        # a checker reason that reached routing as an event is an outside-reach take, though the count is 0
        self.assertEqual({k: by[("O", "trap")][k] for k in ("takes", "with_event", "events", "unread")},
                         {"takes": 1, "with_event": 1, "events": 0, "unread": 0})
        self.assertEqual([tuple(c[k] for k in ("arm", "task", "half", "model", "harness")) for c in got],
                         sorted(tuple(c[k] for k in ("arm", "task", "half", "model", "harness")) for c in got))

    def test_an_unregistered_outcome_refuses(self):
        with self.assertRaises(ValueError):
            result.outside_reach_counts(self.rows[:1], self.history[3:4])

    def test_rendered_and_in_the_page(self):
        got = result.outside_reach_counts(self.rows, self.history)
        text = result.render_outside_reach(got)
        self.assertIn("## Outside-reach events", text)
        self.assertIn("| A | `t1` | trap | `a1` | `claude-code` | 3 | 2 | 5 | 0 |", text)
        self.assertIn("| A | `t1` | normal | `a1` | `claude-code` | 1 | 0 | 0 | 1 |", text)
        self.assertIn("No take is committed", result.render_outside_reach([]))
        for trigger in ("outside the take's own run tree", "study material", "account email"):    # review NIT 2
            self.assertIn(trigger, text)
        self.assertEqual(ll.scan_text(text, "reach.md", []), [])
        self.assertEqual(ll.scan_text(result.render_outside_reach([]), "reach.md", []), [])
        base = {"stats": stats.derive([], DESIGN),
                "completeness": {}, "pause_notes": [], "stopped": [], "outside_reach": got}
        from unittest import mock
        with mock.patch.object(result.completeness, "render", lambda c: "completeness"):
            self.assertIn("## Outside-reach events", result.render(base))

    def test_from_records_carries_it(self):
        from unittest import mock
        with mock.patch.object(result.completeness, "summarize", lambda *a: {}), \
                mock.patch.object(result.check_results, "publication", lambda h, t: {"cells": {}, "attempts": []}), \
                mock.patch.object(result.completeness, "mechanical_states", lambda *a: {}), \
                mock.patch.object(result, "stopped_counts", lambda *a: []), \
                mock.patch.object(result.check_results, "pin_block_events", lambda *a: []):
            got = result.from_records([], PRE, self.rows, self.history, go=[])
        self.assertEqual(got["outside_reach"], result.outside_reach_counts(self.rows, self.history))


# ---- M8: the flagged list's verdict record (m8) --------------------------------------------------------------------

def flagged_doc(n_flagged=3, cap=2):
    def item(i, task, model):
        return {"sheet_id": f"F{i:03d}", "take": f"s{i}/1", "why": ["flag-check"],
                "stratum": {"arm": "A", "harness": CLAUDE, "model": model, "task": task, "verdict": "right",
                            "readers": "agree"}}
    items = [item(1, "t1", "a1"), item(2, "t1", "a1"), item(3, "t2", "a2")][:cap]
    return {"items": [], "flagged": {"cap": cap, "flagged": n_flagged, "listed": len(items),
                                      "beyond_cap": n_flagged - len(items), "items": items}}


def verdicts(*rows):
    return {"verdicts": [{"sheet_id": sid, "finding": f, "note": ""} for sid, f in rows]}


class M8Verdicts(unittest.TestCase):
    def fv(self):
        return flagged_verdicts

    def test_the_claim_follows_the_cap(self):
        on = {"labelling_design": {"flagged_list": {"cap": 2}}}
        text = result.render_flagged_counts(result.flagged_counts(on, reader=lambda: flagged_doc(),
                                                                  verdict_reader=lambda d: None))
        self.assertNotIn("Every take a grader flagged for the human sample goes to a separate check list", text)
        self.assertIn("up to the cap of 2", text)
        self.assertIn("beyond the cap", text)

    def test_the_record_validates_against_the_drawn_list(self):
        fv = self.fv()
        doc = flagged_doc()
        got = fv.validate_verdicts(verdicts(("F001", "grader-right"), ("F002", "grader-wrong")), doc)
        self.assertEqual(got, {"F001": "grader-right", "F002": "grader-wrong"})
        bad = {"a missing item": verdicts(("F001", "grader-right")),
               "an item twice": verdicts(("F001", "grader-right"), ("F001", "grader-wrong"), ("F002", "cannot-tell")),
               "an id off the list": verdicts(("F001", "grader-right"), ("F002", "grader-right"),
                                              ("F003", "grader-right")),
               "a finding off the vocabulary": verdicts(("F001", "fine"), ("F002", "grader-right")),
               "a blind id": verdicts(("L001", "grader-right"), ("F002", "grader-right")),
               "an extra key": {"verdicts": [{"sheet_id": "F001", "finding": "grader-right", "note": "", "by": "x"},
                                             {"sheet_id": "F002", "finding": "grader-right", "note": ""}]},
               "a note that is not text": {"verdicts": [{"sheet_id": "F001", "finding": "grader-right", "note": 3},
                                                        {"sheet_id": "F002", "finding": "grader-right", "note": ""}]},
               "not the record's shape": {"rows": []}}
        for why, rec in bad.items():
            with self.assertRaises(fv.VerdictError, msg=why):
                fv.validate_verdicts(rec, doc)
        with self.assertRaises(fv.VerdictError, msg="a sample with no flagged list"):
            fv.validate_verdicts(verdicts(), {"items": []})

    def test_counts_per_row_never_pooled(self):
        fv = self.fv()
        doc = flagged_doc(n_flagged=3, cap=3)
        rows = fv.verdict_rows(doc, fv.validate_verdicts(
            verdicts(("F001", "grader-right"), ("F002", "grader-wrong"), ("F003", "cannot-tell")), doc))
        self.assertEqual(rows, [
            {"arm": "A", "harness": CLAUDE, "model": "a1", "task": "t1", "listed": 2, "grader-right": 1,
             "grader-wrong": 1, "cannot-tell": 0},
            {"arm": "A", "harness": CLAUDE, "model": "a2", "task": "t2", "listed": 1, "grader-right": 0,
             "grader-wrong": 0, "cannot-tell": 1}])
        unread = fv.verdict_rows(doc, None)
        self.assertEqual([r["listed"] for r in unread], [2, 1])
        self.assertTrue(all(r[f] is None for r in unread for f in fv.FINDINGS))

    def test_published_beside_the_views(self):
        fv = self.fv()
        on = {"labelling_design": {"flagged_list": {"cap": 2}}}
        doc = flagged_doc()
        rec = verdicts(("F001", "grader-right"), ("F002", "grader-wrong"))
        got = result.flagged_counts(on, reader=lambda: doc, verdict_reader=lambda d: fv.validate_verdicts(rec, d))
        self.assertEqual(got["verdicts"], fv.verdict_rows(doc, fv.validate_verdicts(rec, doc)))
        text = result.render_flagged_counts(got)
        self.assertIn("| A | `claude-code` | `a1` | `t1` | 2 | 1 | 1 | 0 |", text)
        self.assertEqual(ll.scan_text(text, "flagged.md", []), [])
        none = result.render_flagged_counts(result.flagged_counts(on, reader=lambda: doc,
                                                                  verdict_reader=lambda d: None))
        self.assertIn("No verdict record is committed", none)
        self.assertEqual(ll.scan_text(none, "flagged.md", []), [])
        self.assertIsNone(result.flagged_counts({"labelling_design": {"flagged_list": None}},
                                                verdict_reader=lambda d: self.fail("read with the switch off")))

    def test_committed_once_and_after_the_blind_labels(self):
        fv = self.fv()
        rel = "evals/gap-study-4/labelling/" + fv.VERDICTS_NAME

        def git(log_shas, blob="x", shallow="false"):
            def run(*args):
                if args[:1] == ("rev-parse",):
                    return 0, shallow + "\n"
                if args[:1] == ("log",):
                    return 0, "".join(f"{s}\n" for s in log_shas)
                if args[:1] == ("show",):
                    return 0, blob
                raise AssertionError(args)
            return run
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / fv.VERDICTS_NAME
            path.write_text("x")
            self.assertEqual(fv.history_problems(path, self.paths_git({fv.VERDICTS_NAME: ["a" * 40],
                                                                      "labels.json": ["c" * 40]}),
                                                 labels_problems=[]), [])
            self.assertTrue(fv.history_problems(path, git(["a" * 40, "b" * 40]), labels_problems=[]))
            self.assertTrue(fv.history_problems(path, git(["a" * 40], blob="y"), labels_problems=[]))
            self.assertTrue(fv.history_problems(path, git(["a" * 40], shallow="true"), labels_problems=[]))
            self.assertTrue(fv.history_problems(path, git(["a" * 40]), labels_problems=["HISTORY: no labels"]))
        self.assertTrue(rel.endswith("flagged-verdicts.json"))
        import check_results as cr
        self.assertIn("labelling/" + fv.VERDICTS_NAME, cr.RUNTIME_PATHS)

    # ---- review of 4928c592 (fold2-ld-REVIEW.md) --------------------------------------------------------------------
    @staticmethod
    def paths_git(logs: dict, *, ancestor=0, shallow="false", blob="x"):
        """A fake git whose `log -- <rel>` answers per path (by the path's last name) and whose merge-base
        --is-ancestor returns `ancestor`; every call is recorded in .calls."""
        calls = []

        def run(*args):
            calls.append(args)
            if args[:1] == ("rev-parse",):
                return 0, shallow + "\n"
            if args[:1] == ("log",):
                name = args[-1].rsplit("/", 1)[-1]
                return 0, "".join(f"{x}\n" for x in logs.get(name, []))
            if args[:1] == ("show",):
                return 0, blob
            if args[:2] == ("merge-base", "--is-ancestor"):
                return ancestor, ""
            raise AssertionError(args)
        run.calls = calls
        return run

    def test_review_major1_a_committed_record_may_not_vanish(self):
        """MAJOR 1: an absent record that HEAD's history ever committed refuses, as agreement.gone_problems does for
        labels.json; a shallow clone refuses; a record never committed is said out loud and passes."""
        fv = self.fv()
        import io
        import contextlib
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            gone = Path(t) / fv.VERDICTS_NAME
            twice = self.paths_git({fv.VERDICTS_NAME: ["a" * 40, "b" * 40]})
            self.assertTrue(fv.gone_problems(gone, twice))
            self.assertTrue(fv.gone_problems(gone, self.paths_git({fv.VERDICTS_NAME: ["a" * 40]}, shallow="true")))
            self.assertEqual(fv.gone_problems(gone, self.paths_git({})), [])
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(fv.check(path=gone, git=twice, smp=flagged_doc()), 1, "a deleted record passed")
            self.assertIn("FAIL", out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(fv.check(path=gone, git=self.paths_git({}), smp=flagged_doc()), 0)

    def test_review_minor1_committed_after_the_blind_labels_by_history(self):
        """MINOR 1: the record's one commit descends from labels.json's one commit, and is not that commit."""
        fv = self.fv()
        import tempfile
        L, V = "1" * 40, "2" * 40
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / fv.VERDICTS_NAME
            path.write_text("x")
            logs = {fv.VERDICTS_NAME: [V], "labels.json": [L]}
            self.assertEqual(fv.history_problems(path, self.paths_git(logs, ancestor=0), labels_problems=[]), [])
            before = fv.history_problems(path, self.paths_git(logs, ancestor=1), labels_problems=[])
            self.assertTrue(any("ORDER" in p for p in before), before)
            same = fv.history_problems(path, self.paths_git({fv.VERDICTS_NAME: [V], "labels.json": [V]}),
                                       labels_problems=[])
            self.assertTrue(any("ORDER" in p for p in same), same)
            none = fv.history_problems(path, self.paths_git({fv.VERDICTS_NAME: [V]}), labels_problems=[])
            self.assertTrue(any("ORDER" in p for p in none), none)

    def test_review_nit3_the_page_publishes_only_a_record_whose_history_holds(self):
        """NIT 3: result.flagged_counts' default reader is flagged_verdicts.published, which refuses a record whose
        history check fails (and a vanished one), never showing it as read or as not read."""
        fv = self.fv()
        from unittest import mock
        import tempfile
        doc = flagged_doc()
        rec = verdicts(("F001", "grader-right"), ("F002", "grader-wrong"))
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / fv.VERDICTS_NAME
            import json
            path.write_text(json.dumps(rec))
            self.assertEqual(fv.published(doc, path, history=lambda p: []), {"F001": "grader-right",
                                                                             "F002": "grader-wrong"})
            with self.assertRaises(fv.VerdictError):
                fv.published(doc, path, history=lambda p: ["HISTORY: twice"])
            gone = Path(t) / "absent.json"
            self.assertIsNone(fv.published(doc, gone, gone=lambda p: []))
            with self.assertRaises(fv.VerdictError):
                fv.published(doc, gone, gone=lambda p: ["HISTORY: was committed"])
        on = {"labelling_design": {"flagged_list": {"cap": 2}}}
        with mock.patch.object(fv, "published", side_effect=fv.VerdictError("synthetic")), \
                self.assertRaises(fv.VerdictError):
            result.flagged_counts(on, reader=lambda: doc)


# ---- M16: the covering Codex walks' native cross-check, re-derived (m16) --------------------------------------------

def walk_folder(root: Path, walk: str, harness: str, status, history=Ellipsis):
    import json
    base = root / walk
    base.mkdir(parents=True)
    if history is Ellipsis:
        history = {"status": "joined", "why": None, "interactions": 1, "basis": "b"}
    ledger = {"agent": {"harness": harness, "version": "v"}, "first_agent_turn": True, "turns": [], "streams": [],
              "native_snapshots": [], "model_requested": "m", "native_history": history}
    if status is not None:
        ledger["cross_check_status"] = status
    (base / "driver-ledger.json").write_text(json.dumps(ledger))
    return base


class M16Cross(unittest.TestCase):
    def wnc(self):
        import importlib
        sys.path.insert(0, str(HERE))
        try:
            return importlib.import_module("walk_native_cross")
        finally:
            sys.path[:] = _PATH

    def test_a_walk_whose_ledger_and_rederivation_differ_is_named(self):
        import tempfile
        wnc = self.wnc()
        agreed, refused = {"status": "agreed", "why": None}, {"status": "refused", "why": "synthetic"}
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            cases = {"w-o1": ("codex", agreed, agreed, None), "w-o2": ("codex", agreed, refused, "w-o2"),
                     "w-o3": ("codex", {"status": "pending", "why": "x"}, refused, None),
                     "w-g1": ("gemini", agreed, refused, "w-g1"), "w001": ("claude-code", None, refused, None),
                     "w-o4": ("codex", None, agreed, "w-o4")}
            for walk, (harness, status, again, named) in cases.items():
                base = walk_folder(root, walk, harness, status)
                got = wnc.walk_problem(walk, base, readers={}, cross=lambda h, b, led, rd, a=again: dict(a))
                if named is None:
                    self.assertIsNone(got[0], walk)
                else:
                    self.assertIn(named, got[0] or "", walk)
            self.assertEqual(wnc.walk_problem("w-o3", root / "w-o3", readers={}, cross=None)[1], "pending")
            self.assertEqual(wnc.walk_problem("w001", root / "w001", readers={}, cross=None)[1], "not-vendor")

    def test_review_minor2_a_walk_whose_join_never_ran_is_read_by_its_recorded_history(self):
        """MINOR 2: when the ledger's native_history is not joined the driver never ran the join (drive.py 2613-2620,
        vendor_cross_check_status), so the gate does not run it either: the ledger's status must be what
        vendor_cross_check_status gives for that recorded history, and the walk is counted not-joined."""
        import json
        import tempfile
        wnc = self.wnc()
        never = lambda *a: self.fail("the join ran for a walk whose native history did not join")
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            hist = {"status": "refused", "why": "x", "interactions": None, "basis": "b"}
            for walk, history, status, named in (
                    ("w-o1", hist, {"status": "refused", "why": "native snapshots: x"}, False),
                    ("w-o2", hist, {"status": "agreed", "why": None}, True),
                    ("w-o3", None, {"status": "refused", "why": "the codex adapter retained no native snapshot "
                                                                 "record"}, False)):
                base = walk_folder(root, walk, "codex", status, history=history)
                led = json.loads((base / "driver-ledger.json").read_text())
                if history is None:
                    led.pop("native_history", None)
                    (base / "driver-ledger.json").write_text(json.dumps(led))
                got = wnc.walk_problem(walk, base, readers={}, cross=never)
                self.assertEqual(got[1], "not-joined", walk)
                self.assertEqual(bool(got[0]), named, (walk, got))
        self.assertEqual(wnc.gate_problems([], {"walks": 2, "vendor": 1, "rederived": 0, "pending": 0,
                                                "not-joined": 1}), [])

    def test_the_gate_refuses_a_vacuous_read(self):
        wnc = self.wnc()
        self.assertTrue(wnc.gate_problems([], {"walks": 3, "vendor": 2, "rederived": 0, "pending": 0}))
        self.assertEqual(wnc.gate_problems([], {"walks": 3, "vendor": 2, "rederived": 1, "pending": 1}), [])
        self.assertEqual(wnc.gate_problems(["x"], {"walks": 3, "vendor": 2, "rederived": 2, "pending": 0}), ["x"])

    def test_a_committed_agreed_codex_walk_rederives_agreed(self):
        import json
        wnc = self.wnc()
        walks = HERE / "rehearsals"
        self.assertTrue((walks / "register.json").is_file(), f"NIT 1: no walk register at {walks}: this test reads a "
                        f"committed walk and fails rather than skip in a tree without them")
        for base in sorted(walks.glob("w-o*")):
            led = base / "driver-ledger.json"
            if led.is_file() and (json.loads(led.read_text()).get("cross_check_status") or {}).get("status") == \
                    "agreed":
                break
        else:
            self.fail("NIT 1: the walk register stands and no committed Codex walk records an agreed cross-check")
        sys.path.insert(0, str(HERE))          # the driver's join imports its study modules as it reads
        try:
            got = wnc.walk_problem(base.name, base, readers=None)
        finally:
            sys.path[:] = _PATH
        self.assertEqual(got, (None, "rederived"), base.name)


if __name__ == "__main__":
    unittest.main()
