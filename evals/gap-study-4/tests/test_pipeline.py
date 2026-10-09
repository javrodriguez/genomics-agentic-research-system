#!/usr/bin/env python3
"""Pipeline contracts on synthetic data and disposable repositories; no model or container.

Mutants are armed in setUpModule, never during module discovery. --mutant NAME
runs this entire file with that production clause removed in memory.
"""
from __future__ import annotations

import copy
import importlib.util
import io
import inspect
import json
import os
import shutil
import types
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import copy_manifest as cm
import freeze
import freeze_rehearsal
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
import costs
from datetime import datetime, timezone
from decimal import Decimal
from graders import labels4

MUTANT = None
_patches = []


def source_mutant(module, name, old, new):
    """Replace one production clause in memory, retaining its module globals."""
    original = getattr(module, name)
    source = textwrap.dedent(inspect.getsource(original))
    assert old in source, (name, old)
    namespace = dict(original.__globals__)
    exec(compile(source.replace(old, new, 1), original.__code__.co_filename, "exec"), namespace)
    altered = namespace[name]
    replacement = types.FunctionType(altered.__code__, original.__globals__, name, altered.__defaults__)
    replacement.__kwdefaults__ = altered.__kwdefaults__
    return module, name, replacement


def review_mutations():
    return {
        "finishing-block": source_mutant(takes.RegistrationGuard, "check",
            'elif self.live & done:', 'elif False:'),
        "one-history-record": source_mutant(takes, "read_history",
            'if len(added) != 1:', 'if len(added) < 1:'),
        "ruling-clean-tree": source_mutant(takes, "commit_ruling",
            'if _git_at(repo, "status", "--porcelain"):', 'if False:'),
        "ledger-committed": source_mutant(takes, "load_rows",
            'if _git_at(repo, "status", "--porcelain", "--", rel):', 'if False:'),
        "freeze-runtime-output": source_mutant(cr, "runtime_timing_problems",
            'frozen is not None and commit != frozen', 'frozen is not None'),
        "future-trim": source_mutant(costs, "month_turn_allowed",
            'utc(trimmed["at"]) > now or ', ''),
        "frozen-rehearsal-draft": source_mutant(cr, "rehearsal_record_problems",
            'if lines[0] != frozen.get("draft_sha256_at_freeze"):', 'if False:'),
        "frozen-rehearsal-tree": source_mutant(cr, "rehearsal_record_problems",
            'if trees != [freeze.REHEARSAL_TREE_PREFIX + str(frozen.get("rehearsed_study_tree_sha256"))]:',
            'if False:'),
        "frozen-rehearsal-green": source_mutant(cr, "rehearsal_record_problems",
            'if lines[-1] != freeze.REHEARSAL_LAST_LINE:', 'if False:'),
        "frozen-rehearsal-placeholder": source_mutant(cr, "check_frozen_content",
            'problems += rehearsal_record_problems(frozen)', 'pass'),
        "ledger-cell-bijection": source_mutant(cr, "validate_ledger",
            'if cell_ids.setdefault(cell, row["half_cell"]) != row["half_cell"]:', 'if False:'),
        "publication-cell-states": source_mutant(cr, "publication",
            "bad += batch.Batch.cell_history_problems(SimpleNamespace(table=table), history)", "pass"),
        "publication-final": source_mutant(cr, "publication",
            'if o["state"] in (labels4.GRADED, labels4.ABORTED) and not o["final"]:', 'if False:'),
        "month-outside-hold": source_mutant(costs, "month_turn_allowed",
            "return True  # outside the month-turn hold", "return False  # demands a current-month record"),
        "door-default-by": source_mutant(takes, "commit_ruling", "route=route, by=by)",
            'route=route, by=by or "synthetic-person")'),
        "pause-candidate-edges": source_mutant(cr, "pause_event",
            "if not candidates:", "if len(candidates) != 1:"),
        "registration-publication": (takes, "registration_outcomes",
            lambda history: cr.publication(history)["attempts"]),
    }


def mutations():
    validate_ruling = getattr(takes, "validate_ruling", None)
    runner = get_run()
    accounting = costs.account
    fragments = cm.load_fragments
    return {
        "claims-eight": (cm, "load_fragments", lambda *a, **k: (
            [(lane, e) for lane, e in fragments(*a, **k)[0] if e["path"] != "run.py"], fragments(*a, **k)[1])),
        "foreign-module": (takes, "__file__", "/synthetic/old/takes.py"),
        "printed-cost": (costs, "account", lambda c, p: dict(accounting(c, p), total_cost_usd=None)),
        "token-sums": (costs, "account", lambda c, p: dict(accounting(c, p), usage={})),
        "wall-time": (costs, "account", lambda c, p: dict(accounting(c, p), wall_seconds=None)),
        "vendor-prices": (costs, "account", lambda c, p: dict(accounting(c, p), priced_cost_usd=Decimal(0))),
        "vendor-caps": (costs, "CAPS", {"openai": Decimal(400), "google": Decimal(400)}),
        "total-cap": (costs, "TOTAL_CAP", Decimal(401)),
        "runtime-timing": (cr, "runtime_timing_problems", lambda: []),
        "attempt-identity": (runner, "require_registered_outcome", lambda o, registered: None),
        "evidence-identity": (runner, "require_evidence_identity", lambda row, evidence: None),
        "rehearsal-evidence": (freeze, "rehearsal_evidence", lambda record, digest, tree: {}),
        "registration-ruling": (takes, "registration_outcomes", lambda history: [o for o in history if not batch.is_ruling(o)]),
        "freeze-identity": (freeze, "planned_order", lambda draft, seed: []),
        "output-pins": (freeze, "generated_pins", lambda outputs: []),
        "pin-all": (freeze, "owned_paths", lambda manifest, folder: [e["path"] for lane, e in manifest.load_fragments(folder)[0] if e["path"].endswith(".py")]),
        "rehearsal-commands": (freeze_rehearsal, "COMMANDS", ()),
        "rehearsal-runtime": (freeze_rehearsal, "rehearsal_plan", lambda pre, row_file: ({}, ())),
        "freeze-claims": (freeze, "output_fragment", lambda: {"lane": "freeze", "files": []}),
        "freeze-once": (freeze, "outputs_exist", lambda root: False),
        "freeze-snapshot": (freeze, "snapshot", lambda manifest, folder: {"files": []}),
        "stored-records": (cr, "records_equal", lambda actual, wanted: True),
        "published-page": (cr, "page_equal", lambda actual, wanted: True),
        "design-row": (takes, "require_planned_row", lambda row, pre: None),
        "stale-row": (takes, "outside_live_block", lambda waiting, live: []),
        "four-open": (takes, "OPEN_LIMIT", 4),
        "row-agent": (takes, "agent_problems", lambda row: batch.agent_problems(
            dict(row, agent=row.get("agent", {"harness": hb.CLAUDE_CODE, "version": "0.0.1"})))),
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
        "per-call": (costs, "unique_calls", lambda calls: calls),
        "price-date": (costs, "require_price_date", lambda table: None),
        "round-spend": (costs, "spent_since", lambda spend, start: {"openai": Decimal(0), "google": Decimal(0)}),
        "walk-cap": (costs, "over_cap", lambda totals: False),
        "month-hold": (costs, "month_turn_allowed", lambda arm, now, trimmed: True),
        "prior-round": (result_page, "prior_sections", lambda: "\nEarlier round table\n"),
    }


def setUpModule():
    if MUTANT:
        available = mutations()
        if MUTANT not in available:
            available = review_mutations()
        target, name, replacement = available[MUTANT]
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


class PipelineOwnership(unittest.TestCase):
    def test_eight_edited_sources_and_local_module_files(self):
        names = ("takes.py", "run.py", "result.py", "completeness.py", "check_results.py",
                 "costs.py", "freeze.py", "freeze_rehearsal.py")
        entries, bad = cm.load_fragments()
        self.assertEqual(bad, [])
        own = {e["path"]: e for lane, e in entries if lane == "w5b-cp5-pipeline"}
        self.assertTrue(set(names) <= set(own))
        for name in names:
            self.assertEqual(own[name]["status"], "edited")
            self.assertEqual(own[name]["source"], cm.SOURCE_DIR + "/" + name)
            self.assertTrue(own[name]["reason"].strip())
        for module in (takes, get_run(), result_page, completeness, cr, costs, freeze, freeze_rehearsal,
                       stats, routing, batch, variants):
            self.assertEqual(Path(module.__file__).resolve().parent, HERE.resolve())


def row(n=1, **kw):
    cell = variants.task_cells({"factor": None}, {"wordings": [{"id": "w1"}, {"id": "w2"}]})
    r = {"arm": "A", "task": "synthetic-task", "model": "synthetic-model",
         "agent": {"harness": hb.CLAUDE_CODE, "version": "0.0.1"}, **cell[(n - 1) % len(cell)],
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

    def test_partly_finished_live_block_refuses_another_registration(self):
        with repository() as repo:
            for n in (1, 2, 3):
                repo.register(row(n), 1)
            repo.commit_records(row(1), 1, outcome(row(1)))
            before = git(repo.root, "rev-parse", "HEAD")
            with self.assertRaisesRegex(ValueError, "finishing block"):
                repo.register(row(4), 1)
            self.assertEqual(git(repo.root, "rev-parse", "HEAD"), before)
            self.assertEqual(len(repo.rows()), 3)

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

    def test_route_rulings_release_or_close_registration(self):
        self.assertTrue(callable(getattr(takes, "registration_outcomes", None)))
        r = row()
        for route in labels4.ROUTES:
            with self.subTest(route=route):
                history = [outcome(r, state=labels4.FAILED, final=False), ruling(r, route=route)]
                if route in batch.RERUN_ROUTES:
                    try:
                        takes.guard_registration(r, 2, [dict(r, attempt=1)], history)
                    except ValueError as exc:
                        self.fail(f"a committed route ruling permits this re-run: {exc}")
                else:
                    with self.assertRaisesRegex(ValueError, "final"):
                        takes.guard_registration(r, 2, [dict(r, attempt=1)], history)
        history = []
        for attempt in range(1, batch.half_cell_cap(table(), labels4.REHEARSAL) + 1):
            history += [outcome(r, attempt, labels4.FAILED, final=False),
                        ruling(r, attempt, route=labels4.REHEARSAL)]
        rows = [dict(r, attempt=i) for i in range(1, 4)]
        with self.assertRaisesRegex(ValueError, "closed"):
            takes.guard_registration(row(2), 1, rows, history)
        with mock.patch.object(takes, "registration_outcomes", lambda h: [o for o in h if not batch.is_ruling(o)]):
            with self.assertRaises(ValueError):
                takes.guard_registration(r, 2, rows[:1], history[:2])


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

    def test_publication_refuses_forged_or_missing_committed_cell_states(self):
        forged = recorded(labels4.GRADED)
        forged.update(cell_state=labels4.INCOMPLETE_MECHANICAL, cell_reason="synthetic cap")
        missing = [recorded(labels4.REHEARSAL, attempt=i)
                   for i in range(1, batch.half_cell_cap(table(), labels4.REHEARSAL) + 1)]
        for history in ([forged], missing):
            with self.subTest(history=history), self.assertRaisesRegex(ValueError, "cell state"):
                cr.publication(history, table())

    def test_publication_refuses_nonfinal_graded_and_aborted_outcomes(self):
        for route in (labels4.GRADED, labels4.ABORTED):
            o = recorded(route)
            o["final"] = False
            with self.subTest(route=route), self.assertRaisesRegex(ValueError, "final"):
                cr.publication([o], table())

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

    def test_ruled_pause_without_any_window_has_own_event(self):
        history = [recorded(labels4.GRADED, row(1)), recorded(labels4.GRADED, row(2)),
                   outcome(row(3), state=labels4.FAILED, final=False), ruling(row(3))]
        self.assertEqual(batch.Batch.history_problems(history), [])
        try:
            got = cr.publication(history, table())
        except ValueError as exc:
            self.fail(f"all admissible blocks give the same own-event count: {exc}")
        self.assertEqual(got["window_events"], {"c1": [("take", "s3", 1)]})
        self.assertEqual(got["cells"], {})

    def test_new_slot_after_legal_pause_ruling_uses_batch_count(self):
        # Publication cannot choose between one and two events, but registration
        # uses batch's strict two-event count and must allow this different cell.
        history = [recorded(labels4.PAUSE, row(1)),
                   outcome(row(2), state=labels4.FAILED, final=False), ruling(row(2))]
        rows = [dict(row(n), attempt=1) for n in (1, 2)]
        try:
            takes.guard_registration(row(4, half_cell="c2"), 1, rows, history)
        except ValueError as exc:
            self.fail(f"a legal ruling cannot stop registration in another cell: {exc}")

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

    def test_history_refuses_two_records_introduced_in_one_commit(self):
        with repository() as repo:
            (repo.root / "outcomes.json").write_text(json.dumps([outcome(row(1)), outcome(row(2))]))
            commit(repo.root, ["outcomes.json"], "Record synthetic doubled history")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                takes.read_history(root=repo.root, repo=repo.root)

    def test_door_refuses_a_dirty_tree_without_committing(self):
        with repository() as repo:
            r = row()
            repo.register(r, 1)
            repo.commit_records(r, 1, outcome(r, state=labels4.FAILED, final=False))
            before = git(repo.root, "rev-parse", "HEAD")
            (repo.root / "pending.txt").write_text("synthetic pending work\n")
            with self.assertRaisesRegex(ValueError, "existing changes"):
                takes.commit_ruling(slot=r["slot"], attempt=1, word=labels4.RULE_ROUTE,
                    route=labels4.ABORTED, by="synthetic-person", root=repo.root, repo=repo.root)
            self.assertEqual(git(repo.root, "rev-parse", "HEAD"), before)
            self.assertFalse((repo.root / "rulings.json").exists())

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

    def test_door_refuses_missing_caller_by_without_a_commit(self):
        for by in (None, ""):
            with self.subTest(by=by), repository() as repo:
                r = row()
                repo.register(r, 1)
                repo.commit_records(r, 1, outcome(r, state=labels4.FAILED, final=False))
                before = git(repo.root, "rev-parse", "HEAD")
                with self.assertRaisesRegex(ValueError, "by"):
                    takes.commit_ruling(slot=r["slot"], attempt=1, word=labels4.RULE_ROUTE,
                        route=labels4.ABORTED, by=by, root=repo.root, repo=repo.root)
                self.assertEqual(git(repo.root, "rev-parse", "HEAD"), before)
                self.assertEqual(git(repo.root, "status", "--porcelain"), "")
                self.assertFalse((repo.root / "rulings.json").exists())


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
    return {"tasks_that_run": list(tasks), "harness_models": {hb.CLAUDE_CODE: ["synthetic-model"]},
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

    def test_half_cell_ids_and_identities_are_one_to_one(self):
        first = dict(row(), attempt=1)
        same_cell = dict(row(), slot="s2", wording="w2", attempt=1)
        self.assertEqual(len(cr.validate_ledger([first, same_cell])), 2)
        split = dict(same_cell, half_cell="c2")
        with self.assertRaisesRegex(ValueError, "identity.*ids"):
            cr.validate_ledger([first, split])
        merged = dict(same_cell, model="synthetic-other")
        with self.assertRaisesRegex(ValueError, "id.*identities"):
            cr.validate_ledger([first, merged])

    def test_every_stop_has_three_views_and_aborted_counts_against_holding(self):
        self.assertEqual(self.run.stop_views(), stats.STOP_VIEWS)
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
        self.assertIsInstance(self.run.record_document([take_record()]), list)
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
        self.assertIn(hb.CLAUDE_CODE, rendered)

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



class CostAccounting(unittest.TestCase):
    def test_future_dated_trim_record_cannot_release_hold(self):
        at = datetime(2026, 10, 31, 23, 31, tzinfo=timezone.utc)
        trimmed = {"kind": "caps trimmed", "by": "Javier", "month": "2026-11",
                   "at": "2026-10-31T23:32:00Z", "figures": {"openai": "10", "google": "1"}}
        self.assertFalse(costs.month_turn_allowed("O", at, trimmed))
        self.assertTrue(costs.month_turn_allowed("O", at, dict(trimmed, at="2026-10-31T23:31:00Z")))

    def api(self):
        self.assertTrue(callable(getattr(costs, "account", None)), "cost accounting must operate per call")
        return costs.account

    def fake_prices(self):
        # Deliberately invented prices, never usable as vendor quotations.
        return {"as_of": "2026-10-01", "fake": True, "vendors": {
            "openai": {"synthetic-model": {"input_tokens": "2", "output_tokens": "3"}},
            "google": {"synthetic-model": {"input_tokens": "5", "output_tokens": "7"}}}}

    def call(self):
        return {"call_id": "c1", "vendor": "openai", "model": "synthetic-model",
                "agent": {"harness": "synthetic", "version": "0.0.1"},
                "usage": {"input_tokens": 1000000, "output_tokens": 1000000},
                "total_cost_usd": "4.25", "started_at": "2026-10-01T00:00:00Z",
                "ended_at": "2026-10-01T00:00:03Z"}

    def test_per_call_usage_printed_cost_and_wall_time(self):
        account = self.api()
        c = self.call()
        got = account([c, copy.deepcopy(c)], self.fake_prices())
        self.assertEqual(got["calls"], 1)
        self.assertIn("input_tokens", got["usage"])
        self.assertEqual(got["usage"]["input_tokens"], 1000000)
        self.assertEqual(got["total_cost_usd"], Decimal("4.25"))
        self.assertEqual(got["priced_cost_usd"], Decimal("5"))
        self.assertEqual(got["wall_seconds"], 3)
        with mock.patch.object(costs, "unique_calls", lambda calls: calls):
            self.assertNotEqual(account([c, c], self.fake_prices())["calls"], 1)
        bad = dict(c, total_cost_usd="9")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            account([c, bad], self.fake_prices())
        self.assertFalse(account([], self.fake_prices())["measured"])
        c["usage"] = None
        self.assertIsNone(account([c], self.fake_prices())["priced_cost_usd"])

    def test_each_vendor_prices_its_calls_from_the_supplied_fake_table(self):
        c = self.call()
        other = dict(c, vendor="google")
        got = costs.account([c, c, other, other], self.fake_prices())
        self.assertEqual(got["calls"], 2)
        self.assertEqual(got["priced_cost_usd"], Decimal(17))
        self.assertEqual(got["vendors"]["openai"]["priced_cost_usd"], Decimal(5))
        self.assertEqual(got["vendors"]["google"]["priced_cost_usd"], Decimal(12))

    def test_pricing_requires_dated_table_and_agent(self):
        account = self.api()
        prices = self.fake_prices()
        del prices["as_of"]
        with self.assertRaisesRegex(ValueError, "dated"):
            account([self.call()], prices)
        with mock.patch.object(costs, "require_price_date", lambda table: None):
            self.assertEqual(account([self.call()], prices)["calls"], 1)
        bad = self.call(); del bad["agent"]
        with self.assertRaisesRegex(ValueError, "agent"):
            account([bad], self.fake_prices())

    def test_round_caps_use_all_months_and_all_models(self):
        self.api()
        self.assertEqual(costs.CAPS, {"openai": Decimal(260), "google": Decimal(140)})
        self.assertEqual(costs.TOTAL_CAP, Decimal(400))
        start = datetime(2026, 9, 1, tzinfo=timezone.utc)
        spend = [{"vendor": "openai", "at": "2026-09-10T00:00:00Z", "usd": "100"},
                 {"vendor": "openai", "at": "2026-10-01T00:00:00Z", "usd": "150"},
                 {"vendor": "google", "at": "2026-10-01T00:00:00Z", "usd": "139"},
                 {"vendor": "google", "at": "2026-08-01T00:00:00Z", "usd": "900"}]
        walks = [{"vendor": "openai", "model": "synthetic-one", "agent": row()["agent"],
                  "cost_per_try": "1", "tries_left": 11},
                 {"vendor": "google", "model": "synthetic-two", "agent": row()["agent"],
                  "cost_per_try": "1", "tries_left": 1}]
        got = costs.walk_gate(walks, spend, start)
        self.assertEqual(got["remaining"], {"openai": Decimal(10), "google": Decimal(1)})
        self.assertEqual(got["decision"], costs.STOP_FOR_WORD)
        with mock.patch.object(costs, "spent_since", lambda s, d: dict.fromkeys(costs.CAPS, Decimal(0))):
            self.assertNotEqual(costs.walk_gate(walks, spend, start)["decision"], costs.STOP_FOR_WORD)
        with mock.patch.object(costs, "over_cap", lambda totals: False):
            self.assertNotEqual(costs.walk_gate(walks, spend, start)["decision"], costs.STOP_FOR_WORD)

    def test_month_turn_refuses_until_both_figures_recorded(self):
        self.api()
        at = datetime(2026, 10, 31, 23, 31, tzinfo=timezone.utc)
        for arm in ("O", "G"):
            self.assertFalse(costs.month_turn_allowed(arm, at, None))
            self.assertTrue(costs.month_turn_allowed(arm, datetime(2026, 11, 1, tzinfo=timezone.utc), None))
        self.assertTrue(costs.month_turn_allowed("A", at, None))
        trimmed = {"kind": "caps trimmed", "by": "Javier", "month": "2026-11",
                   "at": "2026-10-31T23:30:00Z", "figures": {"openai": "10", "google": "1"}}
        self.assertTrue(costs.month_turn_allowed("O", at, trimmed))
        bad = copy.deepcopy(trimmed); del bad["figures"]["google"]
        self.assertFalse(costs.month_turn_allowed("O", at, bad))
        bad = dict(trimmed, by="synthetic-person")
        self.assertFalse(costs.month_turn_allowed("O", at, bad))
        with mock.patch.object(costs, "month_turn_allowed", lambda arm, now, trimmed: True):
            self.assertTrue(costs.month_turn_allowed("O", at, None))

    def test_month_turn_boundary_and_next_month_record(self):
        trimmed = {"kind": "caps trimmed", "by": "Javier", "month": "2026-11",
                   "at": "2026-10-31T23:29:00Z", "figures": {"openai": "10", "google": "1"}}
        for arm in ("O", "G"):
            for at in (datetime(2026, 10, 15, 12, tzinfo=timezone.utc),
                       datetime(2026, 10, 31, 23, 29, tzinfo=timezone.utc)):
                with self.subTest(arm=arm, at=at):
                    self.assertTrue(costs.month_turn_allowed(arm, at, None))
            at = datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc)
            self.assertFalse(costs.month_turn_allowed(arm, at, None))
            self.assertFalse(costs.month_turn_allowed(arm, at, dict(trimmed, month="2026-10")))
            self.assertTrue(costs.month_turn_allowed(arm, at, trimmed))

    def test_nonempty_cost_cli_writes_then_checks_the_frozen_prices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls, page = root / "cost-calls.json", root / "COSTS.md"
            calls.write_text(json.dumps([self.call(), self.call()]))
            def frozen(what):
                self.assertTrue(what)
                return {"price_table": self.fake_prices()}
            with mock.patch.object(costs, "CALLS", calls), mock.patch.object(costs, "PAGE", page), \
                    mock.patch.object(costs.prereg, "require_frozen", frozen), redirect_stdout(io.StringIO()):
                try:
                    self.assertEqual(costs.main(["--write"]), 0)
                    self.assertEqual(costs.main(["--check"]), 0)
                except TypeError as exc:
                    self.fail(f"the nonempty cost path must request the frozen design: {exc}")
                self.assertEqual(page.read_text(), costs.render(costs.account([self.call()], self.fake_prices())))
                page.write_text("synthetic stale costs\n")
                self.assertEqual(costs.main(["--check"]), 1)


class FreezeCoverage(unittest.TestCase):
    def frozen_rehearsal_check(self, record):
        frozen = {"draft_sha256_at_freeze": "a" * 64, "rehearsed_study_tree_sha256": "b" * 64,
                  "rehearsal_record": record}
        with repository() as repo:
            (repo.root / "prereg.json").write_text(json.dumps(frozen))
            commit(repo.root, ["prereg.json"], "Freeze synthetic evidence")
            with mock.patch.object(cr, "HERE", repo.root), \
                    mock.patch.object(cr, "REPO", repo.root), \
                    mock.patch.object(study, "rel", lambda name: name), redirect_stdout(io.StringIO()):
                return cr.check_frozen_content()

    def test_frozen_rehearsal_three_lines_and_placeholder(self):
        lines = ["a" * 64, freeze.REHEARSAL_TREE_PREFIX + "b" * 64, freeze.REHEARSAL_LAST_LINE]
        def record(content):
            text = "\n".join(content) + "\n"
            return {"name": "synthetic.txt", "text": text,
                    "sha256": __import__("hashlib").sha256(text.encode()).hexdigest()}
        self.assertEqual(self.frozen_rehearsal_check(record(lines)), [])
        for index, replacement in ((0, "c" * 64), (1, freeze.REHEARSAL_TREE_PREFIX + "d" * 64),
                                   (2, "failed")):
            changed = list(lines); changed[index] = replacement
            with self.subTest(index=index):
                self.assertTrue(self.frozen_rehearsal_check(record(changed)))
        self.assertTrue(self.frozen_rehearsal_check("rehearsal or preview"))

    def test_external_rehearsal_record_binds_draft_tree_and_green_result(self):
        self.assertTrue(callable(getattr(freeze, "rehearsal_evidence", None)))
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "freeze-rehearsal-1.txt"
            body = "a" * 64 + "\nDisposable rehearsal\n" + freeze.REHEARSAL_TREE_PREFIX + "b" * 64 + "\nall green\n"
            record.write_text(body)
            got = freeze.rehearsal_evidence(record, "a" * 64, "b" * 64)
            self.assertEqual(set(got), {"name", "sha256", "text"})
            self.assertEqual(got["text"], body)
            self.assertEqual(got["sha256"], __import__("hashlib").sha256(body.encode()).hexdigest())
            self.assertNotIn(str(Path(tmp)), json.dumps(got))
            for bad in (body.replace("all green", "NOT all green"), body.replace("a" * 64, "c" * 64),
                        body.replace("b" * 64, "c" * 64)):
                record.write_text(bad)
                with self.assertRaisesRegex(ValueError, "rehearsal"):
                    freeze.rehearsal_evidence(record, "a" * 64, "b" * 64)
                with mock.patch.object(freeze, "rehearsal_evidence", lambda r, d, t: {}):
                    self.assertEqual(freeze.rehearsal_evidence(record, "a" * 64, "b" * 64), {})

    def test_rehearsal_uses_full_rows_and_copy_gate_only_on_frozen_state(self):
        self.assertTrue(callable(getattr(freeze_rehearsal, "rehearsal_plan", None)))
        pre = pre_registration()
        pre["take_order"] = copy.deepcopy(pre["rows"])
        first, commands = freeze_rehearsal.rehearsal_plan(pre, "/synthetic/input.json")
        self.assertEqual(first, pre["rows"][0])
        self.assertEqual(commands[0], ("takes.py", "--add", "--row", "/synthetic/input.json", "--attempt", "1"))
        self.assertIn(("run.py", "--all"), commands)
        self.assertIn(("result.py", "--write"), commands)
        self.assertIn(("check_results.py", "--ledger"), commands)
        self.assertFalse(any(c[0] in ("copy_manifest.py", "test_round4.py") for c in commands))
        self.assertIn(("copy_manifest.py", "--check"), freeze_rehearsal.COMMANDS)
        with mock.patch.object(freeze_rehearsal, "rehearsal_plan", lambda pre, row_file: ({}, ())):
            self.assertNotEqual(freeze_rehearsal.rehearsal_plan(pre, "/synthetic/input.json")[0], first)

    def test_every_owned_path_is_pinned_including_fragments_and_prose(self):
        self.assertTrue(callable(getattr(freeze, "owned_paths", None)), "pins must use the complete ownership record")
        with manifest_repository() as (repo, root, folder):
            paths = freeze.owned_paths(cm, folder)
            self.assertIn("COPIED.d/synthetic.json", paths)
            self.assertIn("instrument.txt", paths)
            self.assertIn("prereg-draft.json", paths)
            expected = {entry["path"].removeprefix(study.STUDY_REL + "/") for entry in cm.derive(folder)["files"]}
            self.assertEqual(set(paths), expected)
            with mock.patch.object(freeze, "owned_paths", lambda m, f: []):
                self.assertNotEqual(set(freeze.owned_paths(cm, folder)), expected)

    def test_rehearsal_keeps_every_required_command_even_when_missing(self):
        self.assertTrue(hasattr(freeze_rehearsal, "COMMANDS"), "rehearsal needs an explicit round 4 gate")
        expected = (("test_round4.py",), ("copy_manifest.py", "--check"),
                    ("tests/test_box_integration.py",), ("tests/test_pipeline.py",),
                    ("probes4.py", "--check"), ("build_draft.py", "--check"),
                    ("leak_grep.py", "--check"), ("holdout.py", "--check"),
                    ("review_kit/rounds.py", "--check"))
        self.assertEqual(freeze_rehearsal.COMMANDS, expected)
        with mock.patch.object(freeze_rehearsal, "COMMANDS", ()):
            self.assertNotEqual(freeze_rehearsal.COMMANDS, expected)
        for name in ("freeze", "scratch_git", "study"):
            self.assertEqual(Path(getattr(freeze_rehearsal, name).__file__).resolve().parent, HERE.resolve())


class LedgerDoor(unittest.TestCase):
    def test_ledger_reader_refuses_uncommitted_rows(self):
        with repository() as repo:
            r = dict(row(), attempt=1)
            path = repo.root / "takes.json"
            path.write_text(json.dumps({"rows": [r]}))
            commit(repo.root, ["takes.json"], "Record synthetic ledger")
            self.assertEqual(takes.load_rows(root=repo.root, repo=repo.root), [r])
            path.write_text(json.dumps({"rows": [r, dict(r, slot="s2", wording="w2")]}))
            for staged in (False, True):
                if staged:
                    git(repo.root, "add", "takes.json")
                with self.subTest(staged=staged), self.assertRaisesRegex(ValueError, "uncommitted"):
                    takes.load_rows(root=repo.root, repo=repo.root)

    def test_registration_commits_the_full_planned_identity_and_audits_it(self):
        self.assertTrue(callable(getattr(takes, "commit_registration", None)), "the ledger door must use the live guard")
        with repository() as repo:
            r = row()
            pre = {"rows": [r]}
            (repo.root / "prereg.json").write_text(json.dumps(pre))
            commit(repo.root, ["prereg.json"], "Record synthetic design")
            guard = takes.RegistrationGuard()
            got = takes.commit_registration(r, 1, guard=guard, root=repo.root, repo=repo.root, pre=pre)
            rows = takes.load_rows(root=repo.root, repo=repo.root)
            self.assertEqual(rows, [dict(r, attempt=1)])
            self.assertEqual(rows[0]["agent"], r["agent"])
            self.assertEqual(takes.row_commits(root=repo.root, repo=repo.root), {0: got})
            with self.assertRaisesRegex(ValueError, "earlier row|already registered"):
                takes.commit_registration(r, 1, root=repo.root, repo=repo.root, pre=pre)
        with repository() as repo:
            (repo.root / "prereg.json").write_text(json.dumps(pre))
            commit(repo.root, ["prereg.json"], "Record synthetic design")
            wrong = dict(r, model="synthetic-other")
            with self.assertRaisesRegex(ValueError, "pre-registered"):
                takes.commit_registration(wrong, 1, root=repo.root, repo=repo.root, pre=pre)
            with mock.patch.object(takes, "require_planned_row", lambda row, pre: None):
                takes.commit_registration(wrong, 1, root=repo.root, repo=repo.root, pre=pre)


class PublishedArtifacts(unittest.TestCase):
    def test_committed_artifacts_regrade_and_publish_through_cli(self):
        from contextlib import ExitStack
        from graders import endstate
        runner = get_run()
        self.assertTrue(callable(getattr(runner, "require_evidence_identity", None)))
        with repository() as repo:
            root = repo.root / study.STUDY_REL
            folder = root / "artifacts/s1"
            evidence = folder / "evidence"
            (evidence / endstate.SNAPSHOTS).mkdir(parents=True)
            r = row(record_dir="artifacts/s1", project="synthetic-project")
            ledger = [{"kind": endstate.TAKE, "model": r["model"], "agent": r["agent"],
                       "run_tree": "repo", "home": "home"},
                      {"kind": endstate.TURN, "n": 1, "started_at": 1, "ended_at": 2}]
            (evidence / endstate.LEDGER).write_text("\n".join(json.dumps(x) for x in ledger) + "\n")
            for name in (endstate.ACCESS, endstate.HEALTH):
                (evidence / name).write_text("")
            for label, at in (("pre-1", 0), ("post-1", 3)):
                (evidence / endstate.SNAPSHOTS / (label + ".json")).write_text(
                    json.dumps({"label": label, "taken_at": at, "entries": {}}))
            (folder / "transcript.jsonl").write_text("")
            commit(repo.root, [study.rel("artifacts/s1")], "Record synthetic take artifacts")
            spec = {"true_counts": {"raw": 2, "samples": 1}, "probe_counts": {"raw": 4, "samples": 3},
                    "pushback_counts": {"raw": 4, "samples": 3}, "probe_line": "step-p", "pushback_line": "step-q"}
            rows, history = [dict(r, attempt=1)], [recorded(labels4.GRADED, r)]
            pre = pre_registration(); pre["rows"] = [r]
            with ExitStack() as stack:
                for module, key, value in ((runner, "HERE", root), (runner, "REPO", repo.root),
                                          (runner, "RECORDS", root / "records"),
                                          (result_page, "RECORDS", root / "records"),
                                          (result_page, "PAGE", root / "RESULT.md")):
                    stack.enter_context(mock.patch.object(module, key, value))
                stack.enter_context(mock.patch.object(variants, "load_task", return_value={"grader_halves": None}))
                stack.enter_context(mock.patch.object(variants, "grader_name", return_value="number_fidelity"))
                stack.enter_context(mock.patch.object(variants, "grader_spec", return_value=spec))
                # Grader source remains the real local v4 file; only the data root is scratch.
                original_loader = runner.grader_for
                def local_grader(name):
                    with mock.patch.object(runner, "HERE", HERE):
                        return original_loader(name)
                stack.enter_context(mock.patch.object(runner, "grader_for", local_grader))
                stack.enter_context(mock.patch.object(takes, "load_rows", return_value=rows))
                stack.enter_context(mock.patch.object(takes, "read_history", return_value=history))
                stack.enter_context(mock.patch.object(runner.prereg, "require_frozen", return_value=pre))
                native_writer = runner.write_records
                stack.enter_context(mock.patch.object(runner, "write_records", lambda records: native_writer(records, root=root)))
                native_table = table()
                stack.enter_context(mock.patch.object(routing, "load_table", return_value=native_table))
                stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(runner.main(["--all"]), 0)
                self.assertEqual(runner.main(["--check"]), 0)
                self.assertEqual(result_page.main(["--write"]), 0)
                self.assertEqual(result_page.main(["--check"]), 0)
                records = stats.load_results(root / "records")
                self.assertEqual(records[0]["views"], stats.STOP_VIEWS)
                self.assertEqual(cr.check_publication(rows, history, records, pre,
                                 (root / "RESULT.md").read_text(), runner.grade_committed, native_table), [])
                loaded = endstate.Evidence.load(evidence)
                runner.require_evidence_identity(r, loaded)
                for name, wrong in (("model", "synthetic-other"), ("version", "0.0.2"), ("harness", "synthetic-other")):
                    with mock.patch.object(loaded, name, wrong):
                        with self.assertRaisesRegex(ValueError, "evidence"):
                            runner.require_evidence_identity(r, loaded)
                        with mock.patch.object(runner, "require_evidence_identity", lambda r, e: None):
                            runner.require_evidence_identity(r, loaded)

    def test_every_attempt_binds_its_registration_model_and_agent(self):
        runner = get_run()
        self.assertTrue(callable(getattr(runner, "require_registered_outcome", None)))
        r = row(); rows = [dict(r, attempt=1)]
        grader = lambda r, o: {"label": "synthetic-right", "correct": True}
        for route in labels4.ROUTES:
            o = recorded(route, r)
            with self.subTest(route=route):
                with self.assertRaisesRegex(ValueError, "registered"):
                    runner.produce([], [o], grader, table=table())
                for broken in (dict(rows[0], model="synthetic-other"),
                               dict(rows[0], agent={"harness": "synthetic-other", "version": "0.0.1"}),
                               dict(rows[0], agent={"harness": hb.CLAUDE_CODE, "version": "0.0.2"}),
                               dict(rows[0], half_cell="c2")):
                    with self.assertRaisesRegex(ValueError, "registered"):
                        runner.produce([broken], [o], grader, table=table())
        with mock.patch.object(runner, "require_registered_outcome", lambda o, rows: None):
            self.assertEqual(runner.produce([], [recorded(labels4.REHEARSAL)], grader, table=table())["records"], [])

    def test_checker_binds_complete_identity_to_the_frozen_plan(self):
        r = row(); rows = [dict(r, attempt=1)]
        history = [recorded(labels4.GRADED, r)]
        grade = lambda r, o: {"label": "synthetic-right", "correct": True}
        records = get_run().produce(rows, history, grade, table=table())["records"]
        pre = pre_registration()
        pre["rows"][0]["agent"]["version"] = "0.0.2"
        page = result_page.render(result_page.from_records(records, pre, rows, history, table()))
        with self.assertRaisesRegex(ValueError, "pre-registered"):
            cr.check_publication(rows, history, records, pre, page, grade, table())
        with mock.patch.object(takes, "require_planned_row", lambda r, pre: None):
            self.assertEqual(cr.check_publication(rows, history, records, pre, page, grade, table()), [])

    def test_checker_binds_records_page_agent_and_final_route(self):
        self.assertTrue(callable(getattr(cr, "check_publication", None)), "checker must read interface 11 records")
        runner = get_run()
        r = row(); rows = [dict(r, attempt=1)]
        history = [recorded(labels4.GRADED, r)]
        grader = lambda r, o: {"label": "synthetic-right", "correct": True}
        records = runner.produce(rows, history, grader, table=table())["records"]
        pre = pre_registration()
        page = result_page.render(result_page.from_records(records, pre, rows, history, table()))
        self.assertEqual(cr.check_publication(rows, history, records, pre, page, grader, table()), [])
        corrupt = copy.deepcopy(records); corrupt[0]["label"] = "synthetic-other"
        self.assertTrue(cr.check_publication(rows, history, corrupt, pre, page, grader, table()))
        with mock.patch.object(cr, "records_equal", lambda actual, wanted: True):
            self.assertEqual(cr.check_publication(rows, history, corrupt, pre, page, grader, table()), [])
        without_agent = page.replace(hb.CLAUDE_CODE, "missing")
        self.assertTrue(cr.check_publication(rows, history, records, pre, without_agent, grader, table()))
        with mock.patch.object(cr, "page_equal", lambda actual, wanted: True):
            self.assertEqual(cr.check_publication(rows, history, records, pre, without_agent, grader, table()), [])
        corrupt = copy.deepcopy(records); del corrupt[0]["agent"]
        with self.assertRaises(stats.StatsError):
            cr.check_publication(rows, history, corrupt, pre, page, grader, table())

    def test_produce_drives_fake_takes_through_all_routes(self):
        runner = get_run()
        for state in labels4.ROUTES:
            r = row(); o = recorded(state, r)
            if state == labels4.HARNESS_ERROR:
                # First permitted re-run, then a final error on the same slot.
                first = copy.deepcopy(o)
                second = recorded(state, r, attempt=2)
                second.update(final=True, rerun=False, beyond_cap=True)
                history, rows = [first, second], [dict(r, attempt=n) for n in (1, 2)]
            else:
                history, rows = [o], [dict(r, attempt=1)]
            got = runner.produce(rows, history, lambda r, o: {"label": "synthetic-right", "correct": True}, table=table())
            self.assertEqual(len(got["records"]), 0 if state in stats.NEVER_IN_RESULTS else 1)
            if got["records"]:
                self.assertEqual(got["records"][0]["route"], state)


class FreezeDesign(unittest.TestCase):
    def test_freeze_preserves_design_and_orders_full_identity_without_vendor_cli(self):
        self.assertTrue(callable(getattr(freeze, "prepare", None)), "freeze must consume round 4 rows")
        pre = pre_registration()
        before = copy.deepcopy(pre)
        got = freeze.prepare(pre, review="a" * 40, parent="b" * 40, pins=[],
                             frozen_at="2026-10-01T00:00:00+00:00")
        self.assertEqual(pre, before)
        self.assertEqual(got["rows"], before["rows"])
        self.assertEqual(got["take_order"], before["rows"])
        self.assertEqual(got["take_order"][0]["agent"], row()["agent"])
        self.assertEqual(freeze.keys_outside_the_freeze(pre, got), [])
        with mock.patch.object(freeze, "planned_order", lambda draft, seed: []):
            self.assertNotEqual(freeze.prepare(pre, review="a" * 40, parent="b" * 40, pins=[],
                                             frozen_at="2026-10-01T00:00:00+00:00")["take_order"], pre["rows"])

    def test_generated_outputs_are_pinned_in_the_frozen_file(self):
        self.assertTrue(callable(getattr(freeze, "generated_pins", None)), "generated outputs need byte pins")
        with manifest_repository() as (repo, root, folder):
            freeze.write_outputs({"pinned_files": []}, root=root, manifest=cm)
            frozen = json.loads((root / "prereg.json").read_text())
            pins = {entry["path"]: entry for entry in frozen["pinned_files"]}
            self.assertEqual(set(pins), {study.rel("COPIED.json"), study.rel("COPIED.d/freeze.json")})
            for name, pin in pins.items():
                data = (repo / name).read_bytes()
                self.assertEqual(pin["sha256"], __import__("hashlib").sha256(data).hexdigest())
                self.assertEqual(pin["git_blob_sha"], git(repo, "hash-object", name))


class RuntimeTiming(unittest.TestCase):
    def test_runtime_output_inside_freeze_commit_is_refused(self):
        with repository() as repo:
            root = repo.root / study.STUDY_REL
            root.mkdir(parents=True)
            (root / "prereg.json").write_text("{}\n")
            (root / "takes.json").write_text('{"rows": []}\n')
            commit(repo.root, [study.rel("prereg.json"), study.rel("takes.json")], "Freeze synthetic outputs")
            with mock.patch.object(cr, "REPO", repo.root):
                self.assertTrue(cr.runtime_timing_problems())

    def test_pre_freeze_outputs_refused_even_when_removed_before_freeze(self):
        self.assertTrue(callable(getattr(cr, "runtime_timing_problems", None)),
                        "the publication checker must inspect output commit timing")
        names = ("takes.json", "outcomes.json", "rulings.json", "records/synthetic-task.json",
                 "RESULT.md", "cost-calls.json", "COSTS.md")
        for name in names:
            with self.subTest(name=name), repository() as repo:
                root = repo.root / study.STUDY_REL
                path = root / name
                path.parent.mkdir(parents=True)
                path.write_text("synthetic output\n")
                commit(repo.root, [study.rel(name)], "Record synthetic early output")
                with mock.patch.object(cr, "REPO", repo.root):
                    self.assertTrue(cr.runtime_timing_problems())
                    path.unlink()
                    commit(repo.root, [study.rel(name)], "Remove synthetic early output")
                    (root / "prereg.json").write_text("{}\n")
                    commit(repo.root, [study.rel("prereg.json")], "Freeze synthetic design")
                    self.assertTrue(cr.runtime_timing_problems())
                    with mock.patch.object(cr, "runtime_timing_problems", lambda: []):
                        self.assertEqual(cr.runtime_timing_problems(), [])

    def test_only_post_freeze_outputs_are_allowed_and_cli_enforces_timing(self):
        self.assertTrue(callable(getattr(cr, "runtime_timing_problems", None)))
        with repository() as repo:
            root = repo.root / study.STUDY_REL
            root.mkdir(parents=True)
            (root / "prereg.json").write_text("{}\n")
            commit(repo.root, [study.rel("prereg.json")], "Freeze synthetic design")
            with mock.patch.object(cr, "REPO", repo.root):
                self.assertEqual(cr.runtime_timing_problems(), [])
                (root / "cost-calls.json").write_text("[]\n")
                commit(repo.root, [study.rel("cost-calls.json")], "Record synthetic later output")
                self.assertEqual(cr.runtime_timing_problems(), [])
        with mock.patch.object(cr, "is_shallow", return_value=False), \
                mock.patch.object(cr, "runtime_timing_problems", return_value=["synthetic early output"]), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cr.main(["--check"]), 1)
            self.assertIn("synthetic early output", output.getvalue())


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
