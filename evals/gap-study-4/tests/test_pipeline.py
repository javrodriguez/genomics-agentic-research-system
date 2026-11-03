#!/usr/bin/env python3
"""Pipeline contracts on synthetic data and disposable repositories; no model or container.

Mutants are armed in setUpModule, never during module discovery. --mutant NAME
runs this entire file with that production clause removed in memory.
"""
from __future__ import annotations

import copy
import base64
import hashlib
import importlib.util
import io
import inspect
import json
import marshal
import os
import shutil
import types
import subprocess
import sys
import tempfile
import textwrap
import unittest
import uuid
from contextlib import ExitStack, contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import copy_manifest as cm
import freeze
import freeze_rehearsal
import order_beacon
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
        "case-folded-cost-arm": source_mutant(costs, "month_turn_allowed",
            'if arm not in study.ARMS:', 'if arm.upper() not in study.ARMS:'),
        "publication-after-final": source_mutant(cr, "publication",
            'if o["slot"] in final_slots:', 'if False:'),
        "mechanical-error-type": source_mutant(completeness, "mechanical_states",
            'except batch.BatchConfigError as exc:', 'except ValueError as exc:'),
        "pause-count-refusal": source_mutant(cr, "pause_event",   # B19-5: re-anchored on the own-event return
            'return {"event": ("take", *key), "note": STRICT_PAUSE_NOTE if shared else None}',
            'if shared:\n'
            '        raise ValueError("the ruled pause event count is ambiguous")\n'
            '    return {"event": ("take", *key), "note": None}'),
        "strict-pause-note": (cr, "STRICT_PAUSE_NOTE", "missing note"),
        "strict-pause-cell-note": source_mutant(completeness, "mechanical_states",
            'if state.get("note"):', 'if False:'),
        "strict-pause-row-note": source_mutant(result_page, "from_records",
            '"pause_notes": pause_notes(rows, published["attempts"])', '"pause_notes": []'),
        "strict-pause-row-render": source_mutant(result_page, "render",
            'render_pause_notes(rec["pause_notes"])', '""'),
        "unescaped-state": source_mutant(completeness, "render",
            '''state = c["state"].replace("|", "\\\\|").replace("\\n", " ")''',
            'state = c["state"]'),
        "duplicate-state-reason": source_mutant(completeness, "render",
            'if reason and reason in c["state"]:', 'if False:'),
        "rehearsal-problem-count": source_mutant(cr, "check_frozen_content",
            'f"on record, {len(problems)} unrecorded change(s)"',
            'f"on record, {len(problems) + len(rehearsal)} unrecorded change(s)"'),
        "rehearsal-problem-line": source_mutant(cr, "check_frozen_content",
            'print(f"  rehearsal record: {len(rehearsal)} problem(s)")', 'pass'),
        "strict-close-state": source_mutant(completeness, "mechanical_states",
            'strict = batch.Batch(None, None, None, table=table, history=history).closed_cells',
            'strict = {}'),
        "strict-close-label": source_mutant(completeness, "mechanical_states",
            'f"{labels4.INCOMPLETE_MECHANICAL} (strict close: {reason})"', 'labels4.INCOMPLETE_MECHANICAL'),
        "strict-close-precedence": source_mutant(completeness, "mechanical_states",
            'if cell not in states:', 'if True:'),
        "rehearsal-step-identity": (freeze_rehearsal, "step_environment", lambda: dict(os.environ)),
        "rehearsal-env-forwarding": source_mutant(freeze_rehearsal, "run_step",
            'env=step_environment()', 'env=None'),
        "rehearsal-plan-mode": source_mutant(cr, "main",
            'check_frozen_content(rehearsal_plan=args.rehearsal_plan)', 'check_frozen_content()'),
        "rehearsal-default-mode": source_mutant(cr, "check_frozen_content",
            'if rehearsal_plan:', 'if True:'),
        "rehearsal-exact-placeholder": source_mutant(cr, "check_frozen_content",
            'if frozen.get("rehearsal_record") != "rehearsal or preview":', 'if False:'),
        "rehearsal-not-checked": source_mutant(cr, "check_frozen_content",
            'NOT CHECKED: rehearsal record (disposable rehearsal)', 'PASS: rehearsal record'),
        "pause-event-identity": source_mutant(cr, "pause_event",   # B19-5: the block reading, sharing a window
            'return {"event": ("take", *key), "note": STRICT_PAUSE_NOTE if shared else None}',
            'return {"event": next((("window", o["window_event"]) for o in outcomes\n'
            '                           if o["half_cell"] == taken["half_cell"] and o["window_event"] is not None),\n'
            '                          ("take", *key)), "note": None}'),
        "frozen-rehearsal-empty": source_mutant(cr, "rehearsal_record_problems",
            'return ["the frozen rehearsal record is empty"]', 'return []'),
        "registration-pause-dedup": source_mutant(takes, "registration_outcomes",
            'count = len(events[(cell, state)] | {batch.cell_event(o)})',
            'count = len(events[(cell, state)]) if state == labels4.PAUSE else len(events[(cell, state)] | {batch.cell_event(o)})'),
        "active-cost-arms": source_mutant(costs, "month_turn_allowed", 'if arm not in study.ARMS:', 'if False:'),
        "runtime-ruling-trailer": source_mutant(takes, "commit_ruling",
            'msg.write("Record a human ruling\\n")',
            'msg.write("Record a human ruling\\n\\nCo-Authored-By: synthetic\\n")'),
        "runtime-registration-trailer": source_mutant(takes, "commit_registration",
            'message.write("Register one planned take\\n")',
            'message.write("Register one planned take\\n\\nCo-Authored-By: synthetic\\n")'),
        "scratch-identity": (sys.modules[__name__], "scratch_identity", lambda root: None),
        "runtime-identity": (takes, "require_commit_identity", lambda repo: None),
        "finishing-block": source_mutant(takes.RegistrationGuard, "check",   # B19-5: the block rule restored
            'self.live -= done',
            'if self.live & done and not self.live <= done:\n'
            '        raise ValueError("a row is registered with no committed outcome in the finishing block")\n'
            '    self.live -= done'),
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
            'rehearsal += rehearsal_record_problems(frozen)', 'pass'),
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
        "pause-note-other-cell": source_mutant(cr, "pause_event",   # B19-5: replaces pause-candidate-edges
            'any(o["half_cell"] == taken["half_cell"] and o["state"] == labels4.PAUSE',
            'any(o["state"] == labels4.PAUSE'),
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
        "past-max-open": (takes, "OPEN_LIMIT", batch.MAX_OPEN + 1),
        "row-agent": (takes, "agent_problems", lambda row: batch.agent_problems(
            dict(row, agent=row.get("agent", {"harness": hb.CLAUDE_CODE, "version": "0.0.1"})))),
        "final-slot": (takes, "slot_final", lambda outcome: False),
        "closed-cell": (takes, "cell_closed", lambda history, cell: False),
        "recorded-route": (cr, "verify_route", lambda outcome, table: None),
        "pause-block": (cr, "pause_event", lambda history, taken:
                        {"event": ("take", taken["slot"], taken["attempt"]), "note": None}),
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


def scratch_identity(root):
    git(root, "config", "user.name", "synthetic")
    git(root, "config", "user.email", "synthetic@example.invalid")


@contextmanager
def empty_identity_home():
    """Only child git commands see this empty HOME; never read host login files."""
    with tempfile.TemporaryDirectory() as home:
        isolated = {k: v for k, v in os.environ.items()
                    if not k.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_", "GIT_CONFIG")) and k != "EMAIL"}
        isolated.update(HOME=home, XDG_CONFIG_HOME=home, GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=os.devnull)
        with mock.patch.dict(os.environ, isolated, clear=True):
            yield


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
        scratch_identity(repo)
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



def full_rehearsal_steps() -> list:
    """Pre-freeze review 2, m2 (lane fold2-lb): every step line a green rehearsal record names
    (freeze.rehearsal_required_steps), the live-box step ending on a closed pass line."""
    import freeze_rehearsal as fr
    live = ("live-box record " + "e" * 64 + ": walk lb1, budget 10 s of 20 s, turn 2 cut (end timed-out, exit 124), "
            "stream 3 unit(s), session 3 unit(s), shape equal, content problems 0, session torn no; files 4 re-read "
            "equal; adapter, check_take and checker digests this tree's; within the bound")
    out = []
    for name in freeze.rehearsal_required_steps():
        out += [f"[0] {name}", "    " + (live if name == fr.LIVE_BOX_STEP else "ok")]
    return out

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
        # W8A (ruling W8A-gap4-1): run.py moved to lane w8a-walk-layout; W8B (ruling W8B-gap4-1 and glitch-1b's Q7/Q8):
        # freeze.py and freeze_rehearsal.py moved to lane w8b-holdout-digests; the other five stay
        moved = {"run.py": "w8a-walk-layout", "freeze.py": "w8b-holdout-digests",
                 "freeze_rehearsal.py": "w8b-holdout-digests"}
        own = {e["path"]: e for lane, e in entries if lane == moved.get(e["path"], "w5b-cp5-pipeline")}
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
        scratch_identity(root)
        yield FakeRepo(root)


class ScratchIdentity(unittest.TestCase):
    def test_empty_home_uses_only_each_scratch_repos_local_identity(self):
        with empty_identity_home():
            with manifest_repository() as (repo, _root, _folder):
                self.assertEqual(takes._git_at(repo, "config", "--local", "--get", "user.name", missing=True),
                                 "synthetic")
                self.assertEqual(takes._git_at(repo, "config", "--local", "--get", "user.email", missing=True),
                                 "synthetic@example.invalid")
            with repository() as repo:
                self.assertEqual(takes._git_at(repo.root, "config", "--local", "--get", "user.name", missing=True),
                                 "synthetic")
                r = row()
                (repo.root / "prereg.json").write_text(json.dumps({"rows": [r]}))
                commit(repo.root, ["prereg.json"], "Record synthetic design")
                takes.commit_registration(r, 1, root=repo.root, repo=repo.root, pre={"rows": [r]})
                repo.commit_records(r, 1, outcome(r, state=labels4.FAILED, final=False))
                takes.commit_ruling(slot=r["slot"], attempt=1, word=labels4.RULE_ROUTE,
                    route=labels4.ABORTED, by="synthetic-person", why="synthetic", cite="synthetic", root=repo.root, repo=repo.root)
                self.assertEqual(git(repo.root, "show", "-s", "--format=%an <%ae>"),
                                 "synthetic <synthetic@example.invalid>")

    def test_missing_runtime_identity_refuses_before_writing(self):
        with empty_identity_home():
            for door in ("registration", "ruling"):
                with self.subTest(door=door), repository() as repo:
                    r = row()
                    repo.commit_records(r, 1, outcome(r, state=labels4.FAILED, final=False))
                    for key in ("user.name", "user.email"):
                        takes._git_at(repo.root, "config", "--local", "--unset-all", key, missing=True)
                    before = git(repo.root, "rev-parse", "HEAD")
                    with self.assertRaisesRegex(ValueError, "commit identity missing"):
                        if door == "registration":
                            other = row(2)
                            takes.commit_registration(other, 1, root=repo.root, repo=repo.root, pre={"rows": [other]})
                        else:
                            takes.commit_ruling(slot=r["slot"], attempt=1, word=labels4.RULE_ROUTE,
                                route=labels4.ABORTED, by="synthetic-person", why="synthetic", cite="synthetic", root=repo.root, repo=repo.root)
                    self.assertEqual(git(repo.root, "rev-parse", "HEAD"), before)
                    self.assertEqual(git(repo.root, "status", "--porcelain"), "")


class Registration(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(takes, "guard_registration", None)), "repo-callable registration guard")

    def test_partly_finished_live_set_allows_another_registration(self):
        # B19-5 (batch.py's rolling window): a row leaves the live set at its commit, so a registration lands while
        # other rows are still open; the finishing-block refusal is gone (its mutant restores it and goes red).
        with repository() as repo:
            for n in (1, 2, 3):
                repo.register(row(n), 1)
            repo.commit_records(row(1), 1, outcome(row(1)))
            repo.register(row(4), 1)
            self.assertEqual(len(repo.rows()), 4)
            self.assertEqual(repo.guard.live, {("s2", 1), ("s3", 1), ("s4", 1)})

    def test_live_set_max_open_restart_requires_reconciliation(self):
        with repository() as repo:
            for n in range(1, batch.MAX_OPEN + 1):
                repo.register(row(n), 1)
            with self.assertRaisesRegex(ValueError, f"at most {batch.MAX_OPEN} open"):
                repo.register(row(batch.MAX_OPEN + 1), 1)
            for n in range(1, batch.MAX_OPEN):
                repo.commit_records(row(n), 1, outcome(row(n)))
            restarted = FakeRepo(repo.root)
            with self.assertRaisesRegex(ValueError, "registered.*outcome"):
                restarted.register(row(batch.MAX_OPEN + 1), 1)
            with mock.patch.object(takes, "outside_live_block", lambda waiting, live: []):
                takes.guard_registration(row(batch.MAX_OPEN + 1), 1, restarted.rows(), restarted.history())
            restarted.commit_records(row(batch.MAX_OPEN), 1, outcome(row(batch.MAX_OPEN)))
            restarted.register(row(batch.MAX_OPEN + 1), 1)
            self.assertEqual(len(restarted.rows()), batch.MAX_OPEN + 1)

    def test_past_max_open_mutant(self):
        self.assertEqual(takes.OPEN_LIMIT, batch.MAX_OPEN)
        rows = [dict(row(n), attempt=1) for n in range(1, batch.MAX_OPEN + 1)]
        live = {(r["slot"], r["attempt"]) for r in rows}
        with self.assertRaises(ValueError):
            takes.guard_registration(row(batch.MAX_OPEN + 1), 1, rows, [], live=live)
        with mock.patch.object(takes, "OPEN_LIMIT", batch.MAX_OPEN + 1):
            takes.guard_registration(row(batch.MAX_OPEN + 1), 1, rows, [], live=live)

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
            "ruling": word, "route": route, "by": by,
            "why": "synthetic", "cite": "synthetic"}      # pre-freeze review 1, MAJOR 8


def after_ruled_final_history():
    cap = batch.half_cell_cap(table(), labels4.PAUSE)
    history = [recorded(labels4.PAUSE, attempt=i, window=i) for i in range(1, cap)]
    history += [outcome(row(), cap, labels4.FAILED, final=False, drive_started=True),
                ruling(row(), cap)]
    later = recorded(labels4.GRADED, attempt=cap + 1)
    later.update(cell_state=labels4.INCOMPLETE_MECHANICAL, cell_reason="synthetic closed cell")
    return history + [later]


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

    def test_publication_refuses_outcome_after_ruled_or_committed_final(self):
        ruled = after_ruled_final_history()
        self.assertEqual(batch.Batch.history_problems(ruled), [])
        self.assertEqual(batch.Batch.cell_history_problems(types.SimpleNamespace(table=table()), ruled), [])
        committed = [recorded(labels4.GRADED), recorded(labels4.GRADED, attempt=2)]
        for history in (ruled, committed):
            with self.subTest(history=history), self.assertRaisesRegex(ValueError, "after.*final"):
                cr.publication(history, table())

    def test_ruled_pause_counts_as_its_own_event(self):
        # B19-5 (proposal 7) and B19-6: a ruled pause counts as its own event, with the note, where a block run
        # would have merged it with its block's window event; publication's count is batch's strict count.
        stopped = outcome(row(2), state=labels4.FAILED, final=False)
        history = [recorded(labels4.PAUSE, row(1)), stopped, recorded(labels4.PAUSE, row(3)), ruling(row(2))]
        got = cr.publication(history, table())
        self.assertEqual(set(got["window_events"]["c1"]), {("window", 1), ("take", "s2", 1)})
        strict = batch.Batch(None, None, None, table=table(), history=history)
        self.assertEqual(set(got["window_events"]["c1"]), strict.cell_events[("c1", labels4.PAUSE)])
        self.assertEqual(next(o for o in got["attempts"] if o["slot"] == "s2").get("note"), cr.STRICT_PAUSE_NOTE)
        self.assertEqual(got["cells"], {})
        with mock.patch.object(cr, "pause_event", lambda h, o: {"event": ("window", 1), "note": None}):
            self.assertEqual(len(cr.publication(history, table())["window_events"]["c1"]), 1)   # the block reading

    def test_ruled_pause_requires_existing_take(self):
        absent = [ruling(row())]
        with self.assertRaises(ValueError):
            cr.publication(absent, table())

    def test_q2_ambiguous_count_publishes_strict_with_note(self):
        history = [recorded(labels4.PAUSE), outcome(row(2), state=labels4.FAILED, final=False), ruling(row(2))]
        try:
            published = cr.publication(history, table())
        except ValueError as exc:
            self.fail(f"ambiguous count must publish strictly: {exc}")
        self.assertEqual(set(published["window_events"]["c1"]), {("window", 1), ("take", "s2", 1)})
        strict = batch.Batch(None, None, None, table=table(), history=history)
        self.assertEqual(set(published["window_events"]["c1"]), strict.cell_events[("c1", labels4.PAUSE)])
        self.assertEqual(published["cells"], {})
        self.assertEqual(published["attempts"][-1].get("note"), "ruled pause counted strictly")

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

    def assert_other_cell_pause_count(self, stopped_first):
        stopped = outcome(row(2, half_cell="c2"), state=labels4.FAILED,
                          final=False, drive_started=True)
        paused = recorded(labels4.PAUSE, row(1), window=1)
        history = ([stopped, paused] if stopped_first else [paused, stopped])
        history.append(ruling(row(2, half_cell="c2")))
        self.assertEqual(batch.Batch.history_problems(history), [])
        try:
            got = cr.publication(history, table())
        except ValueError as exc:
            self.fail(f"both candidates give c2 one event: {exc}")
        self.assertEqual(got["window_events"],
                         {"c1": [("window", 1)], "c2": [("take", "s2", 1)]})
        self.assertEqual(got["cells"], {})
        self.assertTrue(all("note" not in o for o in got["attempts"]),
                        "equal candidate counts must not acquire a strict-count note")

    def test_q1_ruled_pause_after_other_cell_window(self):
        self.assert_other_cell_pause_count(False)

    def test_q1b_ruled_pause_before_other_cell_window(self):
        self.assert_other_cell_pause_count(True)

    def test_new_slot_after_legal_pause_ruling_uses_batch_count(self):
        # Both readers use the strict count when candidates disagree; a legal
        # ruling must still allow registration in a different cell.
        history = [recorded(labels4.PAUSE, row(1)),
                   outcome(row(2), state=labels4.FAILED, final=False), ruling(row(2))]
        rows = [dict(row(n), attempt=1) for n in (1, 2)]
        native = table()
        try:
            with mock.patch.object(routing, "load_table", return_value=native):
                takes.guard_registration(row(4, half_cell="c2"), 1, rows, history)
        except ValueError as exc:
            self.fail(f"a legal ruling cannot stop registration in another cell: {exc}")
        cap = batch.half_cell_cap(native, labels4.PAUSE)
        history = [recorded(labels4.PAUSE, row(1), attempt=i, window=i) for i in range(1, cap)]
        history += [outcome(row(2), state=labels4.FAILED, final=False),
                    recorded(labels4.PAUSE, row(3), window=cap - 1), ruling(row(2))]
        rows = [dict(row(1), attempt=i) for i in range(1, cap)] + [dict(row(n), attempt=1) for n in (2, 3)]
        # B19-5 (proposal 7): publication counts the ruled pause as its own event too, so both readers close c1.
        self.assertEqual(cr.publication(history, native)["cells"]["c1"]["state"], labels4.INCOMPLETE_MECHANICAL)
        with self.assertRaisesRegex(ValueError, "closed"):
            takes.guard_registration(row(4), 1, rows, history)
        takes.guard_registration(row(4, half_cell="c2"), 1, rows, history)

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
                    route=labels4.ABORTED, by="synthetic-person", why="synthetic", cite="synthetic", root=repo.root, repo=repo.root)
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
                                          route=labels4.ABORTED, by=who, why="synthetic", cite="synthetic", root=repo.root, repo=repo.root)
            self.assertEqual(set(got), set(batch.RULING_KEYS))
            self.assertTrue(batch.is_ruling(got))
            self.assertEqual(got["by"], who)
            self.assertEqual(takes.read_history(root=repo.root, repo=repo.root), [o, got])
            self.assertEqual(git(repo.root, "show", "--format=", "--name-only", "HEAD"), "rulings.json")
            self.assertEqual(json.loads((repo.root / "rulings.json").read_text()), [got])
            self.assertNotIn("Co-Authored-By:", git(repo.root, "show", "-s", "--format=%B"))

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
                        route=labels4.ABORTED, by=by, why="synthetic", cite="synthetic", root=repo.root, repo=repo.root)
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
             views={v: "right" for v in stats.VIEWS},
             agent_events=[], ruled=False,            # pre-freeze review 1, MAJOR 5 and 8 (stats.TAKE_FIELDS)
             human_sample=False, human_why=[])     # MAJOR 6 (lane pf1-l2b)
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
        ev = types.SimpleNamespace(harness=r["agent"]["harness"])    # review r13 NIT 4: the evidence's harness
        with mock.patch.dict(sys.modules, {"number_fidelity": fake}):
            graded, path = self.run.regrade("number_fidelity", r, s, [], ev)
            self.assertEqual(Path(path).resolve(), HERE / "graders/number_fidelity.py")
            self.assertEqual(graded["label"], labels4.DID_NOT_REACH)
            with mock.patch.object(self.run, "grader_for", lambda name: __import__(name)):
                _graded, wrong = self.run.regrade("number_fidelity", r, s, [], ev)
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
    # Lane run-launcher (ruling 2): a frozen pre-registration always carries take_order (freeze.prepare), which
    # check_publication's order check reads; here it is the rows' own order.
    return {"tasks": [{"id": task} for task in tasks], "rows": rows, stats.DESIGN_KEY: design(tasks),
            "take_order": copy.deepcopy(rows)}


class Reporting(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(result_page, "from_records", None)), "result renders stats tables")

    def test_strict_close_state_is_escaped_and_reason_printed_once(self):
        reason = "synthetic | reason\ncontinued"
        escaped = "synthetic \\| reason continued"
        for state in (f"{labels4.INCOMPLETE_MECHANICAL} (strict close: {reason})",
                      labels4.INCOMPLETE_MECHANICAL):
            with self.subTest(state=state):
                summary = completeness.summarize(pre_registration(), [],
                    {"c1": {"state": state, "reason": reason}}, [])
                text = completeness.render(summary)
                self.assertIn(state.replace("|", "\\|").replace("\n", " "), text)
                self.assertEqual(text.count(escaped), 1)
                self.assertNotIn(reason, text)

    def test_mechanical_replay_error_is_value_error_and_cli_refusal(self):
        history = after_ruled_final_history()
        def replay(*args, **kwargs):
            return completeness.mechanical_states(history, {}, table())
        try:
            replay()
        except Exception as exc:
            self.assertIsInstance(exc, ValueError)
            self.assertIn("after its final attempt", str(exc))
        else:
            self.fail("invalid replay must refuse")
        with ExitStack() as stack:
            for module, name, value in (
                (cr, "is_shallow", False), (cr, "runtime_timing_problems", []),
                (takes, "load_rows", [dict(row(), attempt=1)]), (takes, "read_history", history),
                (stats, "load_results", []), (cr.prereg, "is_frozen", True),
                (cr.prereg, "require_frozen", {}), (cr, "check_pins", []),
                (cr, "check_frozen_content", []),
                (cr, "pipeline", types.SimpleNamespace(grade_committed=None))):
                stack.enter_context(mock.patch.object(module, name, return_value=value))
            stack.enter_context(mock.patch.object(cr, "HERE", Path("/synthetic/publication")))
            stack.enter_context(mock.patch.object(cr, "check_publication", side_effect=replay))
            output = stack.enter_context(redirect_stdout(io.StringIO()))
            try:
                code = cr.main(["--check"])
            except Exception as exc:
                self.fail(f"checker must print REFUSE instead of raising: {exc}")
            self.assertEqual(code, 1)
            self.assertIn("check_results: REFUSE:", output.getvalue())
            self.assertIn("after its final attempt", output.getvalue())
            self.assertNotIn("Traceback", output.getvalue())

    def test_strict_batch_close_is_named_in_completeness_and_result(self):
        native = table()
        cap = batch.half_cell_cap(native, labels4.PAUSE)
        history = [recorded(labels4.PAUSE, row(1), attempt=i, window=i) for i in range(1, cap)]
        history += [outcome(row(2), state=labels4.FAILED, final=False, drive_started=True),
                    recorded(labels4.PAUSE, row(3), window=cap - 1), ruling(row(2))]
        published = cr.publication(history, native)
        # B19-5 (proposal 7): publication now counts the ruled pause strictly and closes c1 with its note, as batch
        # does; the strict-close label is still checked, on publication's former block reading of the ruled pause.
        self.assertEqual(published["cells"]["c1"]["note"], cr.STRICT_PAUSE_NOTE)
        block_reading = mock.patch.object(cr, "pause_event", lambda h, o: {"event": ("window", cap - 1), "note": None})
        block_reading.start()
        self.addCleanup(block_reading.stop)
        published = cr.publication(history, native)
        self.assertEqual(published["cells"], {})
        strict = batch.Batch(None, None, None, table=native, history=history)
        reason = strict.closed_cells["c1"]
        expected = f"{labels4.INCOMPLETE_MECHANICAL} (strict close: {reason})"
        pre = pre_registration()
        pre["rows"] = [row(i) for i in (1, 2, 3, 4)]
        rows = [dict(row(1), attempt=i) for i in range(1, cap)] + [dict(row(i), attempt=1) for i in (2, 3)]
        got = result_page.from_records([], pre, rows, history, native)
        self.assertEqual(got["completeness"]["cells"][0]["state"], expected)
        self.assertIn(expected, completeness.render(got["completeness"]))
        self.assertIn(expected, result_page.render(got))

    def test_q2_strict_pause_note_on_take_row_until_it_closes_cell(self):
        cap = batch.half_cell_cap(table(), labels4.PAUSE)
        for count in (1, cap - 1):
            with self.subTest(prior_events=count):
                history = [recorded(labels4.PAUSE, attempt=i, window=i) for i in range(1, count + 1)]
                history += [outcome(row(2), state=labels4.FAILED, final=False, drive_started=True), ruling(row(2))]
                rows = [dict(row(), attempt=i) for i in range(1, count + 1)] + [dict(row(2), attempt=1)]
                pre = pre_registration(); pre["rows"] = [row(), row(2)]
                try:
                    got = result_page.from_records([], pre, rows, history, table())
                except ValueError as exc:
                    self.fail(f"strict count must be publishable: {exc}")
                text = result_page.render(got)
                self.assertIn("ruled pause counted strictly", text)
                if count + 1 == cap:
                    expected = f"{labels4.INCOMPLETE_MECHANICAL} (ruled pause counted strictly)"
                    self.assertEqual(got["completeness"]["cells"][0]["state"], expected)
                    self.assertIn(expected, text)
                    self.assertEqual(got.get("pause_notes"), [])
                    published = cr.publication(history, table())
                    self.assertEqual(published["cells"]["c1"]["state"], labels4.INCOMPLETE_MECHANICAL)
                    with self.assertRaisesRegex(ValueError, "closed"):
                        takes.guard_registration(row(3), 1, rows, history)
                else:
                    notes = got.get("pause_notes")
                    self.assertIsInstance(notes, list)
                    self.assertEqual(len(notes), 1)
                    self.assertEqual(notes[0]["slot"], "s2")
                    self.assertEqual(notes[0]["attempt"], 1)
                    self.assertEqual(notes[0]["agent"], row(2)["agent"])
                    self.assertIn("| s2 | 1 |", text)
                    self.assertIn(row(2)["model"], text)

    def test_publication_close_keeps_its_committed_reason(self):
        self.assertTrue(callable(getattr(completeness, "mechanical_states", None)))
        native = table()
        history = []
        for i in range(1, batch.half_cell_cap(native, labels4.REHEARSAL) + 1):
            history += [outcome(row(), i, labels4.FAILED, final=False),
                        ruling(row(), i, route=labels4.REHEARSAL)]
        states = cr.publication(history, native)["cells"]
        self.assertEqual(completeness.mechanical_states(history, states, native), states)

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

    def test_a_deferred_arms_half_cells_read_deferred(self):
        # Lane gemini-defer, ruling R3 (glitch-f1, 22 Oct 2026): a deferred arm's unmeasured half-cells read the frozen
        # deferral, "deferred (Javier, 22 Oct 2026)", never "no takes"; other arms keep "no takes".
        pre = pre_registration(("synthetic-a", "synthetic-b"))
        pre["rows"][1].update(arm="G", half_cell="c-g")
        pre["deferred_arms"] = {"G": {"status": "deferred", "by": "Javier",
                                      "words": "Javier's reply \"gemini-defer yes\", Thu 22 Oct 2026 09:19:59 EDT"}}
        cells = {c["arm"]: c for c in completeness.summarize(pre, [], {}, [])["cells"]}
        self.assertEqual(cells["G"]["state"], "deferred (Javier, 22 Oct 2026)")
        self.assertIn("deferred_arms", cells["G"]["reason"])
        self.assertEqual(cells["A"]["state"], stats.NO_TAKES)
        self.assertEqual(cells["A"]["reason"], "no committed graded take")
        self.assertIn("| deferred (Javier, 22 Oct 2026) |", completeness.render({"task_pairs": 2,
                                                                                 "cells": list(cells.values())}))
        # a committed mechanical state keeps its precedence
        states = {"c-g": {"state": labels4.INCOMPLETE_MECHANICAL, "reason": "synthetic committed state"}}
        cells = {c["arm"]: c for c in completeness.summarize(pre, [], states, [])["cells"]}
        self.assertEqual(cells["G"]["state"], labels4.INCOMPLETE_MECHANICAL)
        # review NIT-2: after Javier's committed go, a G half-cell with no take yet reads "no takes", not "deferred";
        # a record that is not his go for arm G changes nothing
        go = {"kind": "deferred arm go", "arm": "G", "by": "Javier", "decision": "OD-synthetic",
              "ask": "synthetic-go", "at": "2026-12-01T14:00:00Z"}
        cells = {c["arm"]: c for c in completeness.summarize(pre, [], {}, [], go_records=[go])["cells"]}
        self.assertEqual(cells["G"]["state"], stats.NO_TAKES)
        self.assertEqual(cells["G"]["reason"], "no committed graded take")
        for bad in ([], [dict(go, arm="O")], [dict(go, by="glitch-f1")]):
            with self.subTest(records=bad):
                cells = {c["arm"]: c for c in completeness.summarize(pre, [], {}, [], go_records=bad)["cells"]}
                self.assertEqual(cells["G"]["state"], "deferred (Javier, 22 Oct 2026)")
        import prereg
        with mock.patch.object(prereg, "committed_go_records", lambda *a: [go]):
            cells = {c["arm"]: c for c in completeness.summarize(pre, [], {}, [])["cells"]}
        self.assertEqual(cells["G"]["state"], stats.NO_TAKES)

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
    def setUp(self):
        # The design lane adds the vendor arms to study; exercise that future
        # design here without editing study.py from this lane.
        patch = mock.patch.object(study, "ARMS", tuple(dict.fromkeys((*study.ARMS, "O", "G"))))
        patch.start()
        self.addCleanup(patch.stop)

    def test_month_turn_uses_active_study_arms(self):
        at = datetime(2026, 10, 31, 23, 31, tzinfo=timezone.utc)
        with mock.patch.object(study, "ARMS", ("A", "G")):
            self.assertFalse(costs.month_turn_allowed("O", at, None))
            self.assertFalse(costs.month_turn_allowed("G", at, None))
        with mock.patch.object(study, "ARMS", ("A", "O")):
            self.assertFalse(costs.month_turn_allowed("O", at, None))
            self.assertFalse(costs.month_turn_allowed("G", at, None))

    def test_unknown_and_lowercase_arms_fail_closed(self):
        for at in (datetime(2026, 10, 31, 23, 31, tzinfo=timezone.utc),
                   datetime(2026, 10, 15, 12, tzinfo=timezone.utc)):
            with mock.patch.object(study, "ARMS", ("A", "C")):
                for arm in ("O", "G", "o", "g", "synthetic-unknown"):
                    with self.subTest(arm=arm, at=at):
                        self.assertFalse(costs.month_turn_allowed(arm, at, None))
                self.assertTrue(costs.month_turn_allowed("A", at, None))
                self.assertTrue(costs.month_turn_allowed("C", at, None))

    def test_lowercase_vendor_arms_refused_when_uppercase_arms_are_active(self):
        with mock.patch.object(study, "ARMS", ("A", "C", "O", "G")):
            for at in (datetime(2026, 10, 31, 23, 31, tzinfo=timezone.utc),
                       datetime(2026, 10, 15, 12, tzinfo=timezone.utc)):
                for arm in ("o", "g"):
                    with self.subTest(arm=arm, at=at):
                        self.assertFalse(costs.month_turn_allowed(arm, at, None))

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
        # Javier's "gcap-220 yes" (OD107, Thu 22 Oct 2026 14:43:19Z, ask gcap-220): Google 220, OpenAI 180 (arm O runs
        # on the Codex subscription and spends nothing), the 400 total unchanged. The spends keep each vendor one
        # step under its cap, so the projection passes the total by one, as with the 260 and 140 caps before.
        self.assertEqual(costs.CAPS, {"openai": Decimal(180), "google": Decimal(220)})
        self.assertEqual(costs.TOTAL_CAP, Decimal(400))
        start = datetime(2026, 9, 1, tzinfo=timezone.utc)
        spend = [{"vendor": "openai", "at": "2026-09-10T00:00:00Z", "usd": "100"},
                 {"vendor": "openai", "at": "2026-10-01T00:00:00Z", "usd": "70"},
                 {"vendor": "google", "at": "2026-10-01T00:00:00Z", "usd": "219"},
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
            # lane pf1-l4-close (25 Oct 2026): the frozen file carries the price variants the cost step prices by, and
            # the page opens with the statement generated from them (tests/test_pf1_cost_step.py holds the cases)
            variants = {"source": {}, "labels": {v: "API-equivalent, not billed: synthetic" for v in ("anthropic",
                                                                                                     "openai")},
                        "cache_write": {"openai": {"synthetic-model": {"30m": "1", "12h": "1"}}}, "over": {}}
            def frozen(what):
                self.assertTrue(what)
                return {"price_table": self.fake_prices(), "price_variants": variants}
            with mock.patch.object(costs, "CALLS", calls), mock.patch.object(costs, "PAGE", page), \
                    mock.patch.object(costs.prereg, "require_frozen", frozen), redirect_stdout(io.StringIO()):
                try:
                    self.assertEqual(costs.main(["--write"]), 0)
                    self.assertEqual(costs.main(["--check"]), 0)
                except TypeError as exc:
                    self.fail(f"the nonempty cost path must request the frozen design: {exc}")
                self.assertEqual(page.read_text(), costs.render(costs.account([self.call()], self.fake_prices(),
                                                                              variants), costs.cost_statement(variants)))
                page.write_text("synthetic stale costs\n")
                self.assertEqual(costs.main(["--check"]), 1)


class FreezeCoverage(unittest.TestCase):
    def test_rehearsal_problems_are_counted_separately_from_changes(self):
        for changed in (False, True):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                frozen = {"rehearsal_record": "rehearsal or preview"}
                now = dict(frozen, synthetic_change=True) if changed else frozen
                (root / "prereg.json").write_text(json.dumps(now))
                with mock.patch.object(cr, "HERE", root), \
                        mock.patch.object(cr, "frozen_bytes", return_value=(frozen, "")), \
                        mock.patch.object(cr, "freeze_commit", return_value="synthetic"), \
                        mock.patch.object(cr, "frozen_commit_problems", return_value=[]), \
                        mock.patch.object(cr, "take_order_problems", return_value=[]), \
                        mock.patch.object(cr, "freeze_recheck_problems", return_value=[]), \
                        redirect_stdout(io.StringIO()) as output:      # fold2/lb: the order recompute stood in
                    problems = cr.check_frozen_content()
                self.assertEqual(len(problems), 1 + int(changed))
                lines = output.getvalue().splitlines()
                self.assertIn(f"  rehearsal record: 1 problem(s)", lines)
                self.assertTrue(any(f"{int(changed)} unrecorded change(s)" in line for line in lines))

    @contextmanager
    def rehearsal_clone(self, mirror=False):
        claims = {entry["path"]: entry for _lane, entry in cm.load_fragments()[0]}
        names = ("takes.py", "run.py", "result.py", "completeness.py", "check_results.py",
                 "freeze.py", "copy_manifest.py", "prereg.py", "study.py", "stats.py",
                 "batch.py", "routing.py", "routing.json", "variants.py", "intervals.py",
                 "transcript_view.py", "agent_adapter.py", "harness_bookkeeping.py", "graders/labels4.py",
                 "mode_binding.py", "walk_register.py",       # W8A: run.py and copy_manifest.py import these
                 "pending_walk.py",                           # live harness (15429361): run.py imports it
                 "graders/delegation.py",                     # the d7107255 battery ruling: run.py imports it
                 "delegated_take.py",                         # the pre-freeze ruling: graders/delegation.py imports it
                 "run_builders.py",                           # lane run-launcher: check_publication's order check
                 "order_beacon.py",                           # lane pf1-l1-freeze-gates: freeze.py imports it
                 "order_reference.py")                        # lane fold2/lb (m3): check_results runs it by path
        with manifest_repository() as (repo, root, folder), tempfile.TemporaryDirectory() as tmp:
            fragment = json.loads((folder / "synthetic.json").read_text())
            entries = {e["path"]: e for e in fragment["files"]}
            for name in names:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((HERE / name).read_bytes())
                entries[name] = claims[name]
            # lane pf1-l1-freeze-gates (pre-freeze review 1): the synthetic draft registers a drand round (MAJOR 9),
            # and the review's line 1 names the draft's bytes, which the freeze now requires (MAJOR 3)
            draft = dict(pre_registration(), session_namespace={"derived_from": "synthetic",
                "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, "synthetic"))},
                take_order_beacon=dict(order_beacon.registration(), round=33356692))
            # pre-freeze review 2, m3 (lane fold2/lb's leg; this rig's draft by lane fold2/lc): a draft carries the
            # order function's hash, at the value this tree computes, as a built draft does
            draft[freeze.ORDER_FUNCTION_HASH_KEY] = freeze.take_order_function_sha256()
            (root / "prereg-draft.json").write_text(json.dumps(draft))
            # lane fold8/review-binding (pre-freeze review 6, M1 and M2, and the reviews of the fold): the rig seeds the way
            # a real rehearsal will. Rounds 1-4 and 7 never seed, so its round is 8, the next after the seven registered. The
            # instrument is committed first (the launch commit), the row alone next, whose launch_commit is that commit,
            # then the report with a blindness record stating its digest, then the claims appended to the review-records
            # fragment, the one copy-record change the launch binding admits.
            review_name = study.REVIEW_DIR + "/prefreeze-8.md"
            review = root / review_name
            review.parent.mkdir(parents=True, exist_ok=True)
            rounds_name, blind_name = study.REVIEW_DIR + "/rounds.json", study.REVIEW_DIR + "/prefreeze-8-blindness.txt"
            (root / rounds_name).write_text(json.dumps({"rows": []}) + "\n")
            entries[rounds_name] = {"path": rounds_name, "status": "new", "reason": "synthetic registered round"}
            fragment["files"] = list(entries.values())
            (folder / "synthetic.json").write_text(json.dumps(fragment))
            records_name = freeze.REVIEW_CLAIMS_FRAGMENT
            records = {"lane": "review-records", "files": [{"path": records_name, "status": "new",
                                                            "reason": "synthetic review records"}]}
            (root / records_name).write_text(json.dumps(records))
            launch_commit = commit(repo, [study.STUDY_REL], "Record the synthetic instrument")
            (root / rounds_name).write_text(json.dumps({"rows": [{"n": 8, "kind": "prefreeze", "voids": None,
                                                                  "launch_commit": launch_commit}]}) + "\n")
            row_commit = commit(repo, [study.rel(rounds_name)], "Register synthetic review round 8")
            digest = hashlib.sha256((root / "prereg-draft.json").read_bytes()).hexdigest()
            text = f"{freeze.REVIEW_DIGEST_PREFIX}{digest}\n\n" + freeze.RULING_LINE + "\n"
            review.write_text(text)
            (root / blind_name).write_text(f"session id: {takes.session_id_for(row_commit)}\n"
                                           + freeze._blindness().REPORT_DIGEST
                                           + hashlib.sha256(text.encode()).hexdigest() + "\n")
            review_commit = commit(repo, [study.rel(review_name), study.rel(blind_name)], "Record the synthetic review")
            records["files"] += [{"path": name, "status": "new", "reason": "synthetic registered round"}
                                 for name in (review_name, blind_name)]
            (root / records_name).write_text(json.dumps(records))
            commit(repo, [study.rel(records_name)], "Claim the synthetic review's records")
            problems, writer = cm.problems, freeze.write_outputs
            with ExitStack() as stack:
                for module, name, value in ((freeze, "HERE", root), (freeze, "REPO", repo),
                    (freeze, "DRAFT", root / "prereg-draft.json"),
                    (freeze, "PINNED", [study.rel(p) for p in entries] + [study.rel(records_name)])):
                    stack.enter_context(mock.patch.object(module, name, value))
                stack.enter_context(mock.patch.object(cm, "problems", lambda *a, **k: problems(folder, **k)))
                stack.enter_context(mock.patch.object(freeze, "write_outputs", lambda pre: writer(pre, root=root)))
                # lane pf1-l1-freeze-gates (pre-freeze review 1, m2 and MAJOR 4 part 3): the synthetic design is no
                # registered design, so the draft's PENDING map and the real walks' coverage are not read for it here
                # (tests/test_pf1_freeze_gates.py binds both gates)
                stack.enter_context(mock.patch.object(freeze, "draft_pending", lambda d: {}))
                stack.enter_context(mock.patch.object(freeze, "coverage_problem", lambda *a, **k: None))
                if mirror:      # lane fold9/round7-residual: the limit is recorded with a mirror remote too
                    stack.enter_context(mock.patch.object(freeze, "published_tip_problem", lambda: (None, None)))
                output = stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(freeze.main(["--review-commit", review_commit, "--rehearsal", "--write"]),
                                 0, output.getvalue())
            commit(repo, [study.STUDY_REL], "Freeze disposable synthetic design")
            clone = Path(tmp) / "repo"
            git(repo, "clone", "-q", "--no-local", str(repo), str(clone))
            git(clone, "remote", "remove", "origin")
            scratch_identity(clone)
            yield clone, clone / study.STUDY_REL

    def rehearsal_command(self, clone, command):
        self.assertTrue(callable(getattr(freeze_rehearsal, "run_step", None)))
        script = clone / study.rel(command[0])
        if command[0] == "check_results.py":
            # Propagate the whole-file run's in-memory checker mutant into the
            # child interpreter without changing any pinned source on disk.
            functions = {name: base64.b64encode(marshal.dumps(getattr(cr, name).__code__)).decode()
                         for name in ("main", "check_frozen_content", "rehearsal_record_problems")}
            launcher = ('import sys,json,marshal,base64,types; sys.path.insert(0,sys.argv[1]); '
                        'import check_results as m; '
                        # lane fold11/freeze-recheck: this rig's synthetic design is no registered design, as its own
                        # freeze's PENDING and coverage stand-ins say; test_fold11_freeze_recheck reads the recheck
                        'm.freeze_recheck_problems = (lambda *a, **k: []); '
                        '[(setattr(m,n,types.FunctionType(marshal.loads(base64.b64decode(c)), '
                        'm.__dict__,n,getattr(m,n).__defaults__))) for n,c in json.loads(sys.argv[2]).items()]; '
                        'sys.exit(m.main(sys.argv[3:]))')
            argv = [sys.executable, "-B", "-W", "ignore", "-c", launcher, str(script.parent),
                    json.dumps(functions), *command[1:]]
        else:
            argv = [sys.executable, "-B", "-W", "ignore", str(script), *command[1:]]
        code, output = freeze_rehearsal.run_step(argv, clone)
        return types.SimpleNamespace(returncode=code, stdout=output, stderr="")

    def test_rehearsal_plan_commands_receive_fixed_fake_identity(self):
        self.assertTrue(callable(getattr(freeze_rehearsal, "run_step", None)))
        pre = pre_registration(); pre["take_order"] = copy.deepcopy(pre["rows"])
        _first, commands = freeze_rehearsal.rehearsal_plan(pre, "/synthetic/row.json")
        with empty_identity_home(), mock.patch.object(freeze_rehearsal, "sh", return_value=(0, "")) as sh:
            for command in commands:
                freeze_rehearsal.run_step(command, "/synthetic/repo")
                env = sh.call_args.kwargs.get("env")
                self.assertIsInstance(env, dict)
                for role in ("AUTHOR", "COMMITTER"):
                    self.assertEqual(env.get(f"GIT_{role}_NAME"), "rehearsal")
                    self.assertEqual(env.get(f"GIT_{role}_EMAIL"), "rehearsal@example.invalid")

    def test_rehearsal_plan_runtime_commands_accept_only_disposable_placeholder(self):
        with self.rehearsal_clone() as (clone, root), empty_identity_home():
            for key in ("user.name", "user.email"):
                takes._git_at(clone, "config", "--local", "--unset-all", key, missing=True)
            pre = json.loads((root / "prereg.json").read_text())
            self.assertEqual(pre["rehearsal_record"], "rehearsal or preview")
            row_file = clone.parent / "row.json"
            first, commands = freeze_rehearsal.rehearsal_plan(pre, row_file)
            row_file.write_text(json.dumps(first))
            for command in commands:
                got = self.rehearsal_command(clone, command)
                self.assertEqual(got.returncode, 0, (command, got.stdout, got.stderr))
                if command[0] == "check_results.py":
                    self.assertIn("NOT CHECKED: rehearsal record (disposable rehearsal)", got.stdout)
                    self.assertNotIn("PASS", got.stdout)

    def test_the_frozen_file_records_the_published_tip_limit(self):
        # lane fold9/round7-residual (pre-freeze review 7, M1): written always, with or without a mirror remote, and
        # the unedited check_results.frozen_content_problems passes it and refuses it removed or edited
        for mirror in (False, True):
            with self.subTest(mirror=mirror), self.rehearsal_clone(mirror=mirror) as (_clone, root):
                frozen = json.loads((root / "prereg.json").read_text())
                self.assertEqual(frozen.get("published_tip_residual"), freeze.PUBLISHED_TIP_LIMIT)
                self.assertIn("round_4_limitations[10]", freeze.PUBLISHED_TIP_LIMIT)
                self.assertEqual(cr.frozen_content_problems(frozen, copy.deepcopy(frozen)), [])
                removed = copy.deepcopy(frozen); del removed["published_tip_residual"]
                self.assertTrue(cr.frozen_content_problems(frozen, removed), "the limit removed after the freeze")
                edited = dict(frozen, published_tip_residual="nothing to see")
                self.assertTrue(cr.frozen_content_problems(frozen, edited), "the limit edited after the freeze")

    def test_default_checker_refuses_disposable_frozen_state(self):
        with self.rehearsal_clone() as (clone, _root):
            for flags in ((), ("--check",), ("--ledger",)):
                got = self.rehearsal_command(clone, ("check_results.py", *flags))
                self.assertEqual(got.returncode, 1, got.stdout + got.stderr)
                self.assertIn("never a placeholder", got.stdout)

    def test_frozen_content_reads_the_drafts_amendment_dict(self):
        # Lane gemini-defer, ruling R7 (glitch-f1, 22 Oct 2026): the draft's `amendments` is a dict keyed by arm
        # (build_draft.assemble), and frozen_content_problems sliced it as a list (KeyError slice(None, 2, None)).
        # The draft's own shape compared with itself is no change; every refusal still holds on the dict.
        draft = json.loads((HERE / "prereg-draft.json").read_text())
        self.assertIsInstance(draft["amendments"], dict)
        self.assertEqual(cr.frozen_content_problems(draft, copy.deepcopy(draft)), [])
        edited = copy.deepcopy(draft)
        edited["amendments"]["O"] = "synthetic edit"
        self.assertIn("an amendment present at the freeze was edited or removed",
                      cr.frozen_content_problems(draft, edited))
        removed = copy.deepcopy(draft)
        del removed["amendments"]["G"]
        self.assertIn("an amendment present at the freeze was edited or removed",
                      cr.frozen_content_problems(draft, removed))
        as_list = dict(copy.deepcopy(draft), amendments=list(draft["amendments"].values()))
        self.assertIn("an amendment present at the freeze was edited or removed",
                      cr.frozen_content_problems(draft, as_list))
        # A pinned file that moves after the freeze: refused bare, accepted when a new dict entry chains it.
        frozen = dict(copy.deepcopy(draft), pinned_files=[{"path": "x.py", "sha256": "a" * 64}])
        moved = dict(copy.deepcopy(frozen), pinned_files=[{"path": "x.py", "sha256": "b" * 64}])
        self.assertIn("x.py: its pinned sha256 moved after the freeze and no amendment records it",
                      cr.frozen_content_problems(frozen, moved))
        moved["amendments"]["synthetic-1"] = {"files": [{"path": "x.py", "sha256_before": "a" * 64,
                                                         "sha256_after": "b" * 64}]}
        self.assertEqual(cr.frozen_content_problems(frozen, moved), [])
        moved["amendments"]["synthetic-1"]["files"][0]["sha256_after"] = "c" * 64
        self.assertIn("x.py: the last amendment's sha256_after is not the pin in force",
                      cr.frozen_content_problems(frozen, moved))
        # The list shape keeps its own reading.
        listed = {"amendments": [{"files": []}], "pinned_files": []}
        self.assertEqual(cr.frozen_content_problems(listed, copy.deepcopy(listed)), [])
        self.assertIn("an amendment present at the freeze was edited or removed",
                      cr.frozen_content_problems(listed, {"amendments": [], "pinned_files": []}))

    def test_rehearsal_mode_refuses_any_other_record(self):
        self.assertIn("rehearsal_plan", inspect.signature(cr.check_frozen_content).parameters)
        frozen = {"rehearsal_record": "rehearsal or preview"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in ("rehearsal", None, {}, {"text": "all green"}):
                bad = dict(frozen, rehearsal_record=record)
                (root / "prereg.json").write_text(json.dumps(bad))
                with mock.patch.object(cr, "HERE", root), \
                        mock.patch.object(cr, "frozen_bytes", return_value=(bad, "")), \
                        mock.patch.object(cr, "freeze_commit", return_value="synthetic"), \
                        mock.patch.object(cr, "frozen_commit_problems", return_value=[]), \
                        redirect_stdout(io.StringIO()):
                    self.assertTrue(cr.check_frozen_content(rehearsal_plan=True))

    def frozen_rehearsal_check(self, record):
        frozen = {"draft_sha256_at_freeze": "a" * 64, "rehearsed_study_tree_sha256": "b" * 64,
                  "rehearsal_record": record}
        with repository() as repo:
            (repo.root / "prereg.json").write_text(json.dumps(frozen))
            commit(repo.root, ["prereg.json"], "Freeze synthetic evidence")
            with mock.patch.object(cr, "HERE", repo.root), \
                    mock.patch.object(cr, "REPO", repo.root), \
                    mock.patch.object(study, "rel", lambda name: name), \
                    mock.patch.object(cr, "take_order_problems", return_value=[]), \
                    mock.patch.object(cr, "freeze_recheck_problems", return_value=[]), \
                    redirect_stdout(io.StringIO()):     # fold2/lb: the order recompute stood in (test_fold2_lb's)
                return cr.check_frozen_content()

    def test_frozen_rehearsal_three_lines_and_placeholder(self):
        # pre-freeze review 2, m2 (lane fold2-lb): the record names every step; the three bound lines stay first,
        # second-to-first and last, and a three-line record alone is refused
        lines = ["a" * 64, freeze.REHEARSAL_TREE_PREFIX + "b" * 64, *full_rehearsal_steps(), freeze.REHEARSAL_LAST_LINE]
        def record(content):
            text = "\n".join(content) + "\n"
            return {"name": "synthetic.txt", "text": text,
                    "sha256": __import__("hashlib").sha256(text.encode()).hexdigest()}
        self.assertEqual(self.frozen_rehearsal_check(record(lines)), [])
        self.assertTrue(self.frozen_rehearsal_check(record([lines[0], lines[1], lines[-1]])))
        for index, replacement in ((0, "c" * 64), (1, freeze.REHEARSAL_TREE_PREFIX + "d" * 64),
                                   (len(lines) - 1, "failed")):
            changed = list(lines); changed[index] = replacement
            with self.subTest(index=index):
                self.assertTrue(self.frozen_rehearsal_check(record(changed)))
        self.assertTrue(self.frozen_rehearsal_check("rehearsal or preview"))
        self.assertTrue(self.frozen_rehearsal_check(record([])))
        self.assertTrue(self.frozen_rehearsal_check({}))

    def test_external_rehearsal_record_binds_draft_tree_and_green_result(self):
        self.assertTrue(callable(getattr(freeze, "rehearsal_evidence", None)))
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "freeze-rehearsal-1.txt"
            body = ("a" * 64 + "\nDisposable rehearsal\n" + freeze.REHEARSAL_TREE_PREFIX + "b" * 64 + "\n"
                    + "\n".join(full_rehearsal_steps()) + "\nall green\n")     # pre-freeze review 2, m2
            record.write_text(body)
            got = freeze.rehearsal_evidence(record, "a" * 64, "b" * 64)
            self.assertEqual(set(got), {"name", "sha256", "text"})
            self.assertEqual(got["text"], body)
            self.assertEqual(got["sha256"], __import__("hashlib").sha256(body.encode()).hexdigest())
            self.assertNotIn(str(Path(tmp)), json.dumps(got))
            for bad in (body.replace("\nall green", "\nNOT all green"), body.replace("a" * 64, "c" * 64),
                        body.replace("b" * 64, "c" * 64),
                        "a" * 64 + "\n" + freeze.REHEARSAL_TREE_PREFIX + "b" * 64 + "\nall green\n"):
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
        self.assertIn(("check_results.py", "--ledger", "--rehearsal-plan"), commands)
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
                    ("review_kit/rounds.py", "--check"),
                    # W8A (ruling W8-layout-1): the four walk checks
                    ("walk_register.py", "--check"), ("mode_binding.py", "--walks", "--check"),
                    ("fixture_walk.py", "--check"), ("run.py", "--walks", "--check"),
                    # glitch-6b's recheck-coverage ruling (15 Oct 2026): a counted recheck is re-derived at freeze
                    ("walk_regrade.py", "--check"),
                    # lane pf1-l1-freeze-gates (pre-freeze review 1, MAJOR 4 part 3 and m6): the walk coverage of the
                    # arms the freeze runs, and every walk held to its pins
                    ("walk_plan.py", "--coverage", "--require-run-arms"), ("walk_pins.py", "--check"))
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
            self.assertNotIn("Co-Authored-By:", git(repo.root, "show", "-s", "--format=%B"))
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
            folder = root / "takes/s1/1"          # W8A (L5): run.py grades take folders under takes/ only
            evidence = folder / "evidence"
            (evidence / endstate.SNAPSHOTS).mkdir(parents=True)
            r = row(record_dir="takes/s1/1", project="synthetic-project")
            ledger = [{"kind": endstate.TAKE, "model": r["model"], "agent": r["agent"],
                       "run_tree": "repo", "home": "home"},
                      {"kind": endstate.TURN, "n": 1, "started_at": 1, "ended_at": 2}]
            (evidence / endstate.LEDGER).write_text("\n".join(json.dumps(x) for x in ledger) + "\n")
            for name in (endstate.ACCESS, endstate.HEALTH):
                (evidence / name).write_text("")
            (evidence / endstate.WATCHED).write_text(json.dumps({"paths": ["synthetic/watched.txt"]}))
            for label, at in (("pre-1", 0), ("post-1", 3)):
                (evidence / endstate.SNAPSHOTS / (label + ".json")).write_text(
                    json.dumps({"label": label, "taken_at": at, "entries": {}}))
            (folder / "transcript.jsonl").write_text("")
            commit(repo.root, [study.rel("takes/s1/1")], "Record synthetic take artifacts")
            spec = {"true_counts": {"raw": 2, "samples": 1}, "probe_counts": {"raw": 4, "samples": 3},
                    "pushback_counts": {"raw": 4, "samples": 3}, "probe_line": "step-p", "pushback_line": "step-q"}
            rows, history = [dict(r, attempt=1)], [recorded(labels4.GRADED, r)]
            pre = pre_registration(); pre["rows"] = [r]
            pre["published_tip_residual"] = freeze.PUBLISHED_TIP_LIMIT      # lane fold10/rehearsal-road: derive holds it
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
                # fold2/lb (glitch-45's review, MJ-2): the push-witness gate stood in on this synthetic state, as the
                # frozen file is; tests/test_fold2_lb.py binds the gate
                stack.enter_context(mock.patch.object(result_page.check_results, "witness_publication_problems",
                                                      lambda *a, **k: ([], None)))
                stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(runner.main(["--all"]), 0)
                self.assertEqual(runner.main(["--check"]), 0)
                self.assertEqual(result_page.main(["--write"]), 0)
                self.assertEqual(result_page.main(["--check"]), 0)
                records = stats.load_results(root / "records")
                self.assertEqual(records[0]["views"], stats.STOP_VIEWS)
                self.assertEqual(cr.check_publication(rows, history, records, pre,
                                 (root / "RESULT.md").read_text(), runner.grade_committed, native_table), [])
                # lane fold9/round7-residual (pre-freeze review 7, M1): the frozen file's limit is on the written page
                self.assertIn(pre["published_tip_residual"], (root / "RESULT.md").read_text())
                self.assertTrue(cr.check_publication(rows, history, records, pre,
                                (root / "RESULT.md").read_text().replace(pre["published_tip_residual"], "removed"),
                                runner.grade_committed, native_table), "a tampered page without the limit passes")
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
        pre = dict(pre_registration(), published_tip_residual=freeze.PUBLISHED_TIP_LIMIT)    # fold 10's review, m1
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
        pre = dict(pre_registration(), published_tip_residual=freeze.PUBLISHED_TIP_LIMIT)
        page = result_page.render(result_page.from_records(records, pre, rows, history, table()))
        self.assertEqual(cr.check_publication(rows, history, records, pre, page, grader, table()), [])
        # lane fold9/round7-residual (pre-freeze review 7, M1): a frozen file's limit is printed on the page, and the
        # unedited check_publication refuses a page without it
        self.assertIn(result_page.TIP_LIMIT_HEADING, page)
        self.assertIn(freeze.PUBLISHED_TIP_LIMIT, page)
        stripped = {k: v for k, v in pre.items() if k != "published_tip_residual"}
        bare = result_page.render(result_page.from_records(records, stripped, rows, history, table()))
        self.assertTrue(cr.check_publication(rows, history, records, pre, bare, grader, table()),
                        "a page without the limit passes")
        # lane fold11/freeze-recheck (fold 10's review, m1): a frozen file without the limit, or with another, and the page
        # it renders, were read as agreeing; result.derive's hold is held here too
        self.assertTrue(cr.check_publication(rows, history, records, stripped, bare, grader, table()),
                        "a frozen file without the limit passes")
        softer = dict(pre, published_tip_residual="synthetic limit on the review record")
        soft_page = result_page.render(result_page.from_records(records, softer, rows, history, table()))
        self.assertTrue(cr.check_publication(rows, history, records, softer, soft_page, grader, table()),
                        "a frozen file with another limit passes")
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
        # lane pf1-l1-freeze-gates (pre-freeze review 1, m2 and MAJOR 9): the synthetic design registers a drand
        # round and is handed a reading of it; it is no registered design, so its PENDING map is not read here
        # (tests/test_pf1_freeze_gates.py binds both)
        pre = dict(pre_registration(), take_order_beacon=dict(order_beacon.registration(), round=33356692))
        beacon = freeze.synthetic_beacon_reading(33356692)
        before = copy.deepcopy(pre)
        with mock.patch.object(freeze, "draft_pending", lambda d: {}):
            got = freeze.prepare(pre, review="a" * 40, parent="b" * 40, pins=[],
                                 frozen_at="2026-10-01T00:00:00+00:00", beacon=beacon)
            self.assertEqual(pre, before)
            self.assertEqual(got["rows"], before["rows"])
            self.assertEqual(got["take_order"], before["rows"])
            self.assertEqual(got["take_order"][0]["agent"], row()["agent"])
            self.assertEqual(freeze.keys_outside_the_freeze(pre, got), [])
            with mock.patch.object(freeze, "planned_order", lambda draft, seed: []):
                self.assertNotEqual(freeze.prepare(pre, review="a" * 40, parent="b" * 40, pins=[],
                                                 frozen_at="2026-10-01T00:00:00+00:00", beacon=beacon)["take_order"],
                                    pre["rows"])

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

    def test_a_go_record_before_or_with_the_freeze_is_refused(self):
        # Review MINOR-1 on lane gemini-defer (glitch-f1, 22 Oct 2026): a deferred arm's go record committed before or
        # with the freeze would release the arm with the first counted run, so it is refused like any run output;
        # one committed after the freeze is allowed.
        import prereg
        self.assertIn(prereg.GO_RECORD.name, cr.RUNTIME_PATHS)
        with repository() as repo:
            root = repo.root / study.STUDY_REL
            root.mkdir(parents=True)
            (root / "prereg.json").write_text("{}\n")
            (root / prereg.GO_RECORD.name).write_text("[]\n")
            commit(repo.root, [study.rel("prereg.json"), study.rel(prereg.GO_RECORD.name)], "Freeze with a go record")
            with mock.patch.object(cr, "REPO", repo.root):
                got = cr.runtime_timing_problems()
                self.assertEqual(len(got), 1)
                self.assertIn("run output committed before or with the freeze", got[0])
        with repository() as repo:
            root = repo.root / study.STUDY_REL
            root.mkdir(parents=True)
            (root / prereg.GO_RECORD.name).write_text("[]\n")
            commit(repo.root, [study.rel(prereg.GO_RECORD.name)], "Record a go before the freeze")
            (root / "prereg.json").write_text("{}\n")
            commit(repo.root, [study.rel("prereg.json")], "Freeze synthetic design")
            with mock.patch.object(cr, "REPO", repo.root):
                self.assertTrue(cr.runtime_timing_problems())
        with repository() as repo:
            root = repo.root / study.STUDY_REL
            root.mkdir(parents=True)
            (root / "prereg.json").write_text("{}\n")
            commit(repo.root, [study.rel("prereg.json")], "Freeze synthetic design")
            (root / prereg.GO_RECORD.name).write_text("[]\n")
            commit(repo.root, [study.rel(prereg.GO_RECORD.name)], "Record a go after the freeze")
            with mock.patch.object(cr, "REPO", repo.root):
                self.assertEqual(cr.runtime_timing_problems(), [])

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
