#!/usr/bin/env python3
"""Pipeline contracts on synthetic data and disposable repositories; no model or container.

Mutants are armed in setUpModule, never during module discovery. --mutant NAME
runs this entire file with that production clause removed in memory.
"""
from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
import shutil
import types
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import copy_manifest as cm
import freeze
import study
import takes
import batch
import routing
import variants
import check_results as cr
import agent_adapter as aa
import harness_bookkeeping as hb
import stats
import result as result_page
import completeness
from graders import labels4

MUTANT = None
_patches = []


def mutations():
    validate_ruling = getattr(takes, "validate_ruling", None)
    runner = get_run()
    return {
        "freeze-claims": (freeze, "output_fragment", lambda: {"lane": "freeze", "files": []}),
        "freeze-once": (freeze, "outputs_exist", lambda root: False),
        "freeze-snapshot": (freeze, "snapshot", lambda manifest, folder: {"files": []}),
        "stale-row": (takes, "outside_live_block", lambda waiting, live: []),
        "four-open": (takes, "OPEN_LIMIT", 4),
        "row-agent": (takes, "agent_problems", lambda row: []),
        "final-slot": (takes, "slot_final", lambda outcome: False),
        "closed-cell": (takes, "cell_closed", lambda history, cell: False),
        "recorded-route": (cr, "verify_route", lambda outcome, table: None),
        "pause-block": (cr, "pause_event", lambda history, taken: ("take", taken["slot"], taken["attempt"])),
        "window-span": (cr, "window_problems", lambda history: []),
        "ruled-state": (cr, "ruling_closes", lambda count, cap: False),
        "ruled-route": (cr, "ruled_route", lambda ruling: labels4.GRADED),
        "ruling-word": (takes, "validate_ruling", lambda r, h: validate_ruling(
            dict(r, ruling=labels4.RULE_RERUN, route=None), h)),
        "ruling-by": (takes, "validate_ruling", lambda r, h: validate_ruling(dict(r, by="synthetic-person"), h)),
        "bare-grader": (runner, "grader_for", lambda name: __import__(name)),
        "stop-view": (runner, "stop_views", lambda: {v: "right" for v in stats.VIEWS}),
        "runner-route": (runner, "verify_route", lambda o, t: None),
        "records-shape": (runner, "record_document", lambda records: {"cells": records}),
        "key-harness": (takes, "half_cell_key", lambda r: (r["arm"], r["task"], r["half"], r["model"])),
        "stats-default": (stats, "RESULTS_DIR", HERE / "results"),
        "task-count": (completeness, "pair_count", lambda pre: 10),
        "committed-state": (completeness, "committed_state", lambda cell, states: None),
        "result-tables": (result_page, "stats_block", lambda derived: stats.STATS_START + stats.STATS_END),
        "empty-result": (result_page, "empty_line", lambda: "0 right of 0"),
        "prior-round": (result_page, "prior_sections", lambda: "\nEarlier round table\n"),
    }


def setUpModule():
    if MUTANT:
        target, name, replacement = mutations()[MUTANT]
        patch = mock.patch.object(target, name, replacement)
        patch.start()
        _patches.append(patch)


def tearDownModule():
    while _patches:
        _patches.pop().stop()


def git(root, *args):
    got = subprocess.run(["git", "-C", str(root), "-c", "maintenance.auto=false",
                          "-c", "user.name=synthetic", "-c", "user.email=synthetic@example.invalid",
                          *args], capture_output=True, text=True)
    if got.returncode:
        raise AssertionError(got.stderr)
    return got.stdout.strip()


def commit(root, paths, message):
    git(root, "add", "--", *paths)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as msg:
        msg.write(message + "\n\nCo-Authored-By: Codex (gpt-6-astra) <noreply@openai.com>\n")
        msg.flush()
        git(root, "commit", "-q", "-F", msg.name)
    return git(root, "rev-parse", "HEAD")


@contextmanager
def manifest_repository():
    """Scratch index and files, with the checker's real historical source/blob readers.

    Only the five required copied builders are copied. Other files are synthetic.
    The source revisions stay the real pinned revisions: no byte guard is mocked.
    """
    builders = {p: (HERE / p).read_bytes() for p in cm.UNEDITABLE}
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp).resolve()
        git(repo, "init", "-q")
        root = repo / study.STUDY_REL
        folder = root / "COPIED.d"
        folder.mkdir(parents=True)
        entries = []
        for path, data in builders.items():
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            entries.append({"path": path, "status": "identical", "source": cm.SOURCE_DIR + "/" + path})
        for path, data in {"instrument.txt": "synthetic instrument\n",
                           "prereg-draft.json": '{"synthetic": true}\n'}.items():
            (root / path).write_text(data)
            entries.append({"path": path, "status": "new", "reason": "synthetic input"})
        entries.append({"path": "COPIED.d/synthetic.json", "status": "new", "reason": "synthetic claims"})
        (folder / "synthetic.json").write_text(json.dumps({"lane": "synthetic", "files": entries}))
        commit(repo, [study.STUDY_REL], "Record synthetic inputs")

        def tracked():
            return {p[len(study.STUDY_REL) + 1:] for p in
                    git(repo, "ls-files", "--", study.STUDY_REL).splitlines()}

        with mock.patch.object(cm, "HERE", root), mock.patch.object(cm, "tracked_here", tracked):
            yield repo, root, folder


class FreezeOutputs(unittest.TestCase):
    def writer(self):
        self.assertTrue(callable(getattr(freeze, "write_outputs", None)),
                        "freeze must write and claim its outputs together")
        return freeze.write_outputs

    def test_build_and_frozen_manifest_and_snapshot(self):
        writer = self.writer()
        with manifest_repository() as (repo, root, folder):
            self.assertEqual(cm.problems(folder, pinned=False), [])
            before = cm.derive(folder)
            writer({"synthetic": True, "status": "frozen"}, root=root, manifest=cm)
            commit(repo, [study.STUDY_REL], "Freeze synthetic inputs")
            self.assertEqual(cm.problems(folder, pinned=False), [])
            self.assertEqual(json.loads((root / "COPIED.json").read_text()), before)
            fragment = json.loads((folder / "freeze.json").read_text())
            self.assertEqual(fragment["lane"], "freeze")
            self.assertEqual({e["path"] for e in fragment["files"]},
                             {"COPIED.json", "prereg.json", "COPIED.d/freeze.json"})
            self.assertTrue(all(e["status"] == "new" and e["reason"] ==
                                "written once by freeze.py at the freeze" for e in fragment["files"]))
            paths = git(repo, "show", "--format=", "--name-only", "HEAD").splitlines()
            self.assertEqual(set(paths), {study.rel(p) for p in
                                         ("COPIED.json", "prereg.json", "COPIED.d/freeze.json")})

    def test_second_freeze_refused_before_any_write(self):
        writer = self.writer()
        with manifest_repository() as (_repo, root, _folder):
            writer({"synthetic": True}, root=root, manifest=cm)
            original = (root / "prereg.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "already exists"):
                writer({"synthetic": False}, root=root, manifest=cm)
            self.assertEqual((root / "prereg.json").read_bytes(), original)

    def test_missing_claim_mutant_is_refused(self):
        writer = self.writer()
        with manifest_repository() as (_repo, root, folder):
            with mock.patch.object(freeze, "output_fragment", lambda: {"lane": "freeze", "files": []}):
                writer({"synthetic": True}, root=root, manifest=cm)
            bad = cm.problems(folder, pinned=False)
            for path in ("COPIED.json", "prereg.json", "COPIED.d/freeze.json"):
                self.assertTrue(any(b.startswith(path + " is under") and "no fragment" in b for b in bad), bad)


def row(n=1, **kw):
    cell = variants.task_cells({"factor": None}, {"wordings": [{"id": "w1"}, {"id": "w2"}]})
    r = {"arm": "A", "task": "synthetic-task", "model": "synthetic-model",
         "agent": {"harness": "synthetic-harness", "version": "0.0.1"}, **cell[(n - 1) % len(cell)],
         "slot": f"s{n}", "half_cell": "c1"}
    r.update(kw)
    return r


def outcome(r, attempt=1, state=labels4.GRADED, **kw):
    o = batch.Batch._outcome(r, attempt, None, state=state)
    o.update(batch.Batch._fate(final=True))
    o.update(kw)
    return o


class FakeRepo:
    """The register/commit_records/history seam on committed scratch files only."""
    def __init__(self, root):
        self.root = root
        self.guard = takes.RegistrationGuard()
        self.fail_commit = False

    def rows(self):
        p = self.root / "takes.json"
        return json.loads(p.read_text()) if p.exists() else []

    def history(self):
        p = self.root / "outcomes.json"
        return json.loads(p.read_text()) if p.exists() else []

    def register(self, r, attempt):
        rows = self.rows()
        self.guard.check(r, attempt, rows, self.history())
        rows.append(dict(r, attempt=attempt))
        (self.root / "takes.json").write_text(json.dumps(rows))
        commit(self.root, ["takes.json"], "Register synthetic row")
        self.guard.registered(r, attempt)

    def commit_records(self, r, attempt, o):
        if self.fail_commit:
            raise RuntimeError("synthetic lost outcome")
        rows = self.history() + [o]
        (self.root / "outcomes.json").write_text(json.dumps(rows))
        commit(self.root, ["outcomes.json"], "Record synthetic outcome")


@contextmanager
def repository():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        git(root, "init", "-q")
        yield FakeRepo(root)


class Registration(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(takes, "guard_registration", None)), "repo-callable registration guard")

    def test_live_block_three_restart_requires_reconciliation(self):
        with repository() as repo:
            for n in range(1, 4):
                repo.register(row(n), 1)
            with self.assertRaisesRegex(ValueError, "three|3"):
                repo.register(row(4), 1)
            for n in (1, 2):
                repo.commit_records(row(n), 1, outcome(row(n)))
            restarted = FakeRepo(repo.root)
            with self.assertRaisesRegex(ValueError, "registered.*outcome"):
                restarted.register(row(4), 1)
            with mock.patch.object(takes, "outside_live_block", lambda waiting, live: []):
                takes.guard_registration(row(4), 1, restarted.rows(), restarted.history())
            restarted.commit_records(row(3), 1, outcome(row(3)))
            restarted.register(row(4), 1)
            self.assertEqual(len(restarted.rows()), 4)

    def test_four_open_mutant(self):
        rows = [dict(row(n), attempt=1) for n in range(1, 4)]
        live = {(r["slot"], r["attempt"]) for r in rows}
        with self.assertRaises(ValueError):
            takes.guard_registration(row(4), 1, rows, [], live=live)
        with mock.patch.object(takes, "OPEN_LIMIT", 4):
            takes.guard_registration(row(4), 1, rows, [], live=live)

    def test_lost_drive_and_lost_pause_never_launch_on_restart(self):
        for state in (labels4.GRADED, labels4.PAUSE):
            with self.subTest(state=state), repository() as repo:
                r = row()
                repo.register(r, 1)
                repo.fail_commit = True
                with self.assertRaisesRegex(RuntimeError, "lost outcome"):
                    repo.commit_records(r, 1, outcome(r, state=state, drive_started=True))
                launches = []
                restarted = FakeRepo(repo.root)
                with self.assertRaises(ValueError):
                    restarted.register(r, 1)
                    launches.append(r)
                self.assertEqual(launches, [])
                with self.assertRaises(ValueError):
                    restarted.register(row(2), 1)

    def test_routes_free_slots_only_with_committed_rerun(self):
        r = row()
        for state in batch.RERUN_ROUTES:
            with self.subTest(state=state):
                o = outcome(r, state=state, final=False, rerun=True,
                            window_event=1 if state == labels4.PAUSE else None)
                takes.guard_registration(r, 2, [dict(r, attempt=1)], [o])
                final = dict(o, rerun=False, final=True, beyond_cap=True)
                with self.assertRaisesRegex(ValueError, "final"):
                    takes.guard_registration(r, 2, [dict(r, attempt=1)], [final])
                with mock.patch.object(takes, "slot_final", lambda o: False):
                    takes.guard_registration(r, 2, [dict(r, attempt=1)], [final])

    def test_committed_cell_state_refuses_new_slot(self):
        o = outcome(row(), cell_state=labels4.INCOMPLETE_MECHANICAL, cell_reason="synthetic cap")
        with self.assertRaisesRegex(ValueError, "closed"):
            takes.guard_registration(row(2), 1, [dict(row(), attempt=1)], [o])
        with mock.patch.object(takes, "cell_closed", lambda history, cell: False):
            takes.guard_registration(row(2), 1, [dict(row(), attempt=1)], [o])

    def test_row_agent_required_never_defaulted(self):
        r = row()
        del r["agent"]
        with self.assertRaisesRegex(ValueError, "agent"):
            takes.guard_registration(r, 1, [], [])
        with mock.patch.object(takes, "agent_problems", lambda row: []):
            takes.guard_registration(r, 1, [], [])


def table():
    t = copy.deepcopy(routing.load_table())
    harness = hb.CLAUDE_CODE
    t["pin_profiles"] = {harness: {"synthetic-model": {"permission_mode": "synthetic-mode", "version": "0.0.1"}}}
    t["pin_profiles_status"] = "RULED: synthetic profile"
    t["spend_cap_markers_status"] = "RULED: synthetic fixture"
    return t


def recorded(state, r=None, attempt=1, window=1):
    """Drive-side synthetic records; the real routing function records their decision."""
    r = row() if r is None else r
    pin = dict(table()["pin_profiles"][hb.CLAUDE_CODE]["synthetic-model"],
               harness=hb.CLAUDE_CODE, model="synthetic-model")
    turn = aa.TurnResult(exit_code=0, text="synthetic", stream_path=None, end_reason=labels4.END_TURN,
                         init=pin, api_errors=[], counters={"oom_kill_delta": 0, "pids_max_delta": 0},
                         started_at=1.0, ended_at=2.0, agent_output=True)
    box = {"preflight_ok": True, "container_started": True, "container_exited": False,
           "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False},
           "unexplained_operator_diffs": 0, "checker_reasons": [], "quiescence_kill": False,
           "outside_reach_events": 0, "finalize_abort": False, "committed": False,
           "unreadable_consequential": [], "quiescence_cap_survivors": 0}
    turns = [turn]
    if state == labels4.REHEARSAL:
        turns = []
        box["preflight_ok"] = False
    elif state == labels4.HARNESS_ERROR:
        box["sidecar"]["queue_overflow"] = True
    elif state == labels4.ABORTED:
        turn.counters["oom_kill_delta"] = 1
    raw = aa.harness_records(turns, pin=pin, box=box)
    if state == labels4.PAUSE:
        markers = table()["rate_limit_markers"][hb.CLAUDE_CODE]
        raw["api_errors"] = [{"status": markers["status"][0], "type": None, "text": None}]
    decision = routing.route(raw, table())
    assert decision["route"] == state
    return outcome(r, attempt, state, records=raw, decision=decision,
                   events=decision["events"], mask=decision["mask"], mask_basis="annotations",
                   final=state not in batch.RERUN_ROUTES, rerun=state in batch.RERUN_ROUTES,
                   window_event=window if state == labels4.PAUSE else None)


def ruling(r, attempt=1, route=labels4.PAUSE, word=labels4.RULE_ROUTE, by="synthetic-person"):
    return {"kind": labels4.RULING, "slot": r["slot"], "attempt": attempt,
            "ruling": word, "route": route, "by": by}


class PublicationHistory(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(cr, "publication", None)), "publication reads committed outcomes and rulings")

    def test_every_route_is_reverified_without_replacement(self):
        routes = {r["route"] for r in table()["rows"]}
        self.assertEqual(routes, set(labels4.ROUTES))
        for state in labels4.ROUTES:
            with self.subTest(state=state):
                o = recorded(state)
                original = copy.deepcopy(o)
                cr.verify_route(o, table())
                self.assertEqual(o, original)
                broken = copy.deepcopy(o)
                broken["decision"]["rows"] = []
                with self.assertRaisesRegex(ValueError, "recorded route"):
                    cr.verify_route(broken, table())
                with mock.patch.object(cr, "verify_route", lambda o, t: None):
                    cr.publication([broken], table())

    def test_ruled_pause_counts_its_existing_block_once(self):
        stopped = outcome(row(2), state=labels4.FAILED, final=False)
        history = [recorded(labels4.PAUSE, row(1)), stopped, recorded(labels4.PAUSE, row(3)), ruling(row(2))]
        got = cr.publication(history, table())
        self.assertEqual(len(got["window_events"]["c1"]), 1)
        self.assertEqual(got["cells"], {})
        with mock.patch.object(cr, "pause_event", lambda h, o: ("take", o["slot"], o["attempt"])):
            self.assertEqual(len(cr.publication(history, table())["window_events"]["c1"]), 2)

    def test_ruled_pause_requires_unique_block_and_existing_take(self):
        absent = [ruling(row())]
        with self.assertRaises(ValueError):
            cr.publication(absent, table())
        ambiguous = [recorded(labels4.PAUSE), outcome(row(2), state=labels4.FAILED, final=False), ruling(row(2))]
        with self.assertRaisesRegex(ValueError, "uniquely"):
            cr.publication(ambiguous, table())

    def test_ruled_half_cell_closes_from_the_ruling(self):
        history = []
        cap = batch.half_cell_cap(table(), labels4.REHEARSAL)
        for attempt in range(1, cap + 1):
            history.extend([outcome(row(), attempt, labels4.FAILED, final=False),
                            ruling(row(), attempt, route=labels4.REHEARSAL)])
        got = cr.publication(history, table())
        self.assertEqual(got["cells"]["c1"]["state"], labels4.INCOMPLETE_MECHANICAL)
        self.assertTrue(all(o.get("cell_state") is None for o in history if not batch.is_ruling(o)))
        with mock.patch.object(cr, "ruling_closes", lambda count, cap: False):
            self.assertNotIn("c1", cr.publication(history, table())["cells"])

    def test_ruled_take_publishes_under_the_ruled_route(self):
        history = [outcome(row(), state=labels4.FAILED, final=False), ruling(row(), route=labels4.ABORTED)]
        got = cr.publication(history, table())
        self.assertEqual(got["outcomes"][0]["state"], labels4.ABORTED)
        with mock.patch.object(cr, "ruled_route", lambda r: labels4.GRADED):
            self.assertEqual(cr.publication(history, table())["outcomes"][0]["state"], labels4.GRADED)

    def test_window_event_must_fit_one_block(self):
        too_many = [recorded(labels4.PAUSE, row(i)) for i in range(1, batch.BLOCK + 2)]
        with self.assertRaisesRegex(ValueError, "window event"):
            cr.publication(too_many, table())
        with mock.patch.object(cr, "window_problems", lambda h: []):
            cr.publication(too_many, table())
        repeated = [recorded(labels4.PAUSE, row(), 1), recorded(labels4.PAUSE, row(), 2)]
        with self.assertRaises(ValueError):
            cr.publication(repeated, table())
        interleaved = [recorded(labels4.PAUSE, row(1), window=1),
                       recorded(labels4.PAUSE, row(2), window=2), recorded(labels4.PAUSE, row(3), window=1)]
        with self.assertRaises(ValueError):
            cr.publication(interleaved, table())


class RulingDoor(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(takes, "commit_ruling", None)), "one human door commits a closed ruling")

    def test_door_commits_one_closed_record_with_callers_by(self):
        with repository() as repo:
            r = row()
            repo.register(r, 1)
            o = outcome(r, state=labels4.FAILED, final=False)
            repo.commit_records(r, 1, o)
            who = "synthetic-person"
            with mock.patch.dict(os.environ, {"GIT_AUTHOR_NAME": who, "GIT_COMMITTER_NAME": who,
                                             "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
                                             "GIT_COMMITTER_EMAIL": "synthetic@example.invalid"}):
                got = takes.commit_ruling(slot=r["slot"], attempt=1, word=labels4.RULE_ROUTE,
                                          route=labels4.ABORTED, by=who, root=repo.root, repo=repo.root)
            self.assertEqual(set(got), set(batch.RULING_KEYS))
            self.assertTrue(batch.is_ruling(got))
            self.assertEqual(got["by"], who)
            self.assertEqual(takes.read_history(root=repo.root, repo=repo.root), [o, got])
            self.assertEqual(git(repo.root, "show", "--format=", "--name-only", "HEAD"), "rulings.json")
            self.assertEqual(json.loads((repo.root / "rulings.json").read_text()), [got])

    def test_door_refuses_unknown_word_and_empty_by_with_mutants(self):
        history = [outcome(row(), state=labels4.FAILED, final=False)]
        good = ruling(row(), word=labels4.RULE_RERUN, route=None)
        takes.validate_ruling(good, history)
        real = takes.validate_ruling
        for bad, repair in ((dict(good, ruling="outside"), lambda r: dict(r, ruling=labels4.RULE_RERUN)),
                            (dict(good, by="  "), lambda r: dict(r, by="synthetic-person"))):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    takes.validate_ruling(bad, history)
                with mock.patch.object(takes, "validate_ruling", lambda r, h: real(repair(r), h)):
                    takes.validate_ruling(bad, history)
        with self.assertRaises(ValueError):
            takes.validate_ruling(dict(good, block=1), history)
        with self.assertRaises(ValueError):
            takes.validate_ruling(good, [])


_RUN = None


def get_run():
    global _RUN
    if _RUN is None:
        saved_path = list(sys.path)
        try:
            spec = importlib.util.spec_from_file_location("pipeline_run", HERE / "run.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _RUN = mod
        finally:
            sys.path[:] = saved_path
    return _RUN


def take_record(**kw):
    r = {k: row()[k] for k in stats.TAKE_FIELDS[:8]}
    r.update(route=labels4.GRADED, cell_state=None, label="synthetic-right",
             views={v: "right" for v in stats.VIEWS})
    r.update(kw)
    return r


def design(tasks=("synthetic-task",)):
    return {"tasks_that_run": list(tasks), "harness_models": {"synthetic-harness": ["synthetic-model"]},
            "stronger_weaker": {}, "cross_vendor": [], "alpha": "0.05",
            "bootstrap": {"seed": 1, "reps": 1},
            "power": {"seed": 2, "sims": 1, "bootstrap_reps": 1, "wordings": 1, "repeats": 1,
                      "grid": [{"stronger": "0.900", "weaker": "0.500", "task_spread": "0.100", "wording_spread": "0.050"}]},
            "floors": None}


class InterfaceRecords(unittest.TestCase):
    def setUp(self):
        try:
            self.run = get_run()
        except ImportError as exc:
            self.fail(f"round 4 runner must import: {exc}")
        self.assertTrue(callable(getattr(self.run, "record_for", None)), "runner produces interface 11")

    def test_keys_include_arm_half_wording_level_and_harness(self):
        r = row()
        self.assertEqual(takes.half_cell_key(r), stats.half_cell_key(r))
        self.assertEqual(takes.try_key(r), stats.try_key(r))
        for key, value in (("arm", "C"), ("task", "another"), ("half", variants.HALVES[1]),
                           ("model", "another"), ("wording", "w3"), ("repeat", 3),
                           ("agent", {"harness": "another", "version": "0.0.1"})):
            changed = dict(r, **{key: value})
            self.assertNotEqual(takes.try_key(r), takes.try_key(changed), key)
        self.assertNotEqual(takes.try_key(r), takes.try_key(dict(r, repeat=None, pressure=True)))
        with mock.patch.object(takes, "half_cell_key", lambda r: (r["arm"], r["task"], r["half"], r["model"])):
            self.assertEqual(takes.try_key(r), takes.try_key(dict(r, agent={"harness": "another", "version": "0.0.1"})))

    def test_every_stop_has_three_views_and_aborted_counts_against_holding(self):
        for label in labels4.RESERVED:
            r = row()
            state = labels4.ABORTED if label == labels4.ABORTED else labels4.GRADED
            o = recorded(state, r)
            rec = self.run.record_for(r, o, {"label": label, "correct": False})
            self.assertEqual(set(rec), set(stats.TAKE_FIELDS))
            self.assertEqual(rec["views"], stats.STOP_VIEWS)
            self.assertEqual(rec["agent"], r["agent"])
        self.assertEqual(self.run.stop_views(), stats.STOP_VIEWS)
        with mock.patch.object(self.run, "stop_views", lambda: {v: "right" for v in stats.VIEWS}):
            self.assertNotEqual(self.run.stop_views(), stats.STOP_VIEWS)

    def test_regrade_uses_v4_file_even_with_same_named_module_cached(self):
        fake = types.ModuleType("number_fidelity")
        fake.__file__ = "/synthetic/old/number_fidelity.py"
        fake.grade = lambda *a, **k: {"label": "synthetic-wrong", "correct": True}
        s = {"true_counts": {"raw": 2, "samples": 1}, "probe_counts": {"raw": 4, "samples": 3},
             "pushback_counts": {"raw": 4, "samples": 3}, "probe_line": "step-p", "pushback_line": "step-q"}
        r = row(agent={"harness": hb.CLAUDE_CODE, "version": "0.0.1"})
        with mock.patch.dict(sys.modules, {"number_fidelity": fake}):
            graded, path = self.run.regrade("number_fidelity", r, s, [], None)
            self.assertEqual(Path(path).resolve(), HERE / "graders/number_fidelity.py")
            self.assertEqual(graded["label"], labels4.DID_NOT_REACH)
            with mock.patch.object(self.run, "grader_for", lambda name: __import__(name)):
                _graded, wrong = self.run.regrade("number_fidelity", r, s, [], None)
                self.assertNotEqual(Path(wrong).resolve(), HERE / "graders/number_fidelity.py")

    def test_runner_reverifies_in_addition_to_publication_checker(self):
        o = recorded(labels4.GRADED)
        broken = copy.deepcopy(o)
        broken["decision"]["rows"] = []
        with self.assertRaisesRegex(ValueError, "recorded route"):
            self.run.verify_route(broken, table())
        with mock.patch.object(self.run, "verify_route", lambda o, t: None):
            self.run.verify_route(broken, table())

    def test_every_route_reaches_only_its_allowed_interface_shape(self):
        seen = set()
        for state in labels4.ROUTES:
            r, grade = row(), {"label": "synthetic-right", "correct": True}
            o = recorded(state, r)
            o.update(final=True, rerun=False, beyond_cap=state in batch.RERUN_ROUTES)
            rec = self.run.record_for(r, o, grade)
            seen.add(state)
            if state in stats.NEVER_IN_RESULTS:
                self.assertIsNone(rec)
            else:
                stats.validate_record(rec)
                self.assertEqual(rec["route"], state)
                if state == labels4.HARNESS_ERROR:
                    self.assertIsNone(rec["views"])
                    self.assertEqual(rec["label"], labels4.HARNESS_ERROR)
        self.assertEqual(seen, set(labels4.ROUTES))

    def test_record_lists_written_only_in_records_and_legacy_shape_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run.write_records([take_record()], root=root)
            self.assertFalse((root / "results").exists())
            paths = list((root / "records").glob("*.json"))
            self.assertEqual(len(paths), 1)
            self.assertEqual(stats.load_results(root / "records"), [take_record()])
            with mock.patch.object(self.run, "record_document", lambda records: {"cells": records}):
                self.run.write_records([take_record()], root=root)
                with self.assertRaises(stats.StatsError):
                    stats.load_results(root / "records")

    def test_agent_missing_refused_by_ledger_and_records(self):
        r = row()
        del r["agent"]
        with self.assertRaisesRegex(ValueError, "agent"):
            cr.validate_ledger([dict(r, attempt=1)])
        rec = take_record()
        del rec["agent"]
        with self.assertRaises(stats.StatsError):
            stats.validate_record(rec)


def pre_registration(tasks=("synthetic-task",)):
    rows = [row(task=task, slot=f"s{i}", half_cell=f"c{i}") for i, task in enumerate(tasks, 1)]
    return {"tasks": [{"id": task} for task in tasks], "rows": rows, stats.DESIGN_KEY: design(tasks)}


class Reporting(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(result_page, "from_records", None)), "result renders stats tables")

    def test_empty_records_print_no_takes_never_zeros(self):
        got = result_page.from_records([], pre_registration(), [], [], table())
        text = result_page.render(got)
        self.assertIn("no takes", text)
        self.assertNotIn("0 of 0", text)
        self.assertEqual(result_page.empty_line(), stats.NO_TAKES)
        for name in stats.TABLES:
            self.assertIn(stats.TABLE_HEADINGS[name], text)
        with mock.patch.object(result_page, "empty_line", lambda: "0 right of 0"):
            self.assertIn("0 right of 0", result_page.render(got))

    def test_every_table_comes_from_stats_and_no_prior_round(self):
        records, pre = [take_record()], pre_registration()
        got = result_page.from_records(records, pre, [], [], table())
        rendered = result_page.render(got)
        self.assertIn(stats.render_block(stats.derive(records, pre[stats.DESIGN_KEY])), rendered)
        self.assertEqual(result_page.prior_sections(), "")
        self.assertNotIn("Earlier round", rendered)
        with mock.patch.object(stats, "render_md", return_value="synthetic stats output\n"):
            self.assertIn("synthetic stats output", result_page.render(got))
        with mock.patch.object(result_page, "stats_block", lambda d: "missing tables"):
            self.assertNotIn(stats.TABLE_HEADINGS[stats.TABLES[0]], result_page.render(got))
        self.assertIn("0.0.1", rendered)
        self.assertIn("synthetic-harness", rendered)

    def test_excluded_dict_no_takes_and_only_stops_all_render(self):
        pre = pre_registration()
        for records in ([], [take_record()], [take_record(label=labels4.DID_NOT_REACH, views=stats.STOP_VIEWS)]):
            with self.subTest(records=records):
                got = result_page.from_records(records, pre, [], [], table())
                text = result_page.render(got)
                self.assertIn(stats.render_block(stats.derive(records, pre[stats.DESIGN_KEY])), text)
        only = result_page.render(result_page.from_records(
            [take_record(label=labels4.DID_NOT_REACH, views=stats.STOP_VIEWS)], pre, [], [], table()))
        self.assertIn("1 stops excluded, none counted", only)

    def test_pair_count_comes_from_nine_task_design(self):
        pre = pre_registration(tuple(f"synthetic-{i}" for i in range(9)))
        got = completeness.summarize(pre, [], {}, [])
        self.assertEqual(got["task_pairs"], 9)
        with mock.patch.object(completeness, "pair_count", lambda pre: 10):
            self.assertEqual(completeness.summarize(pre, [], {}, [])["task_pairs"], 10)

    def test_mechanical_state_read_even_without_a_graded_record(self):
        pre = pre_registration()
        states = {"c1": {"state": labels4.INCOMPLETE_MECHANICAL, "reason": "synthetic committed state"}}
        got = completeness.summarize(pre, [], states, [])
        self.assertEqual(got["cells"][0]["state"], labels4.INCOMPLETE_MECHANICAL)
        with mock.patch.object(completeness, "committed_state", lambda cell, states: None):
            self.assertNotEqual(completeness.summarize(pre, [], states, [])["cells"][0]["state"],
                                labels4.INCOMPLETE_MECHANICAL)


class StatsDestination(unittest.TestCase):
    def test_no_argument_cli_reads_records_and_legacy_shape_is_refused(self):
        self.assertEqual(stats.RESULTS_DIR, HERE / "records")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / study.STUDY_REL
            (root / "graders").mkdir(parents=True)
            for rel in ("stats.py", "intervals.py", "graders/labels4.py"):
                shutil.copyfile(HERE / rel, root / rel)
            (root / "records").mkdir()
            (root / "records/r.json").write_text(json.dumps([take_record()]))
            (root / "prereg.json").write_text(json.dumps({stats.DESIGN_KEY: design()}))
            (root / "RESULT.md").write_text(stats.render_block(stats.derive([take_record()], design())))
            code = ('import sys; p=sys.argv[1]; s=open(p).read(); '
                    's=s.replace(\'HERE / "records"\', \'HERE / "results"\') if sys.argv[2] == "mutant" else s; '
                    'sys.argv=[p,"--check"]; exec(compile(s,p,"exec"), {"__name__":"__main__","__file__":p})')
            def cli(which):
                return subprocess.run([sys.executable, "-B", "-W", "ignore", "-c", code, str(root / "stats.py"), which],
                                      capture_output=True, text=True)
            got = cli("actual")
            self.assertEqual(got.returncode, 0, got.stdout + got.stderr)
            self.assertIn("PASS (1 records from 1 results files", got.stdout)
            wrong = cli("mutant")
            self.assertIn("no takes", wrong.stdout)
            self.assertNotIn("PASS", wrong.stdout)
            (root / "records/r.json").write_text(json.dumps({"cells": []}))
            refused = cli("actual")
            self.assertEqual(refused.returncode, 1)
            self.assertIn("a results file is a JSON list", refused.stdout)


if __name__ == "__main__":
    if "--mutant" in sys.argv:
        at = sys.argv.index("--mutant")
        MUTANT = sys.argv[at + 1]
        del sys.argv[at:at + 2]
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"test_pipeline: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped", flush=True)
    sys.exit(0 if result.wasSuccessful() else 1)
