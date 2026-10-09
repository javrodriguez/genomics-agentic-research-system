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
from graders import labels4

MUTANT = None
_patches = []


def mutations():
    return {
        "freeze-claims": (freeze, "output_fragment", lambda: {"lane": "freeze", "files": []}),
        "freeze-once": (freeze, "outputs_exist", lambda root: False),
        "freeze-snapshot": (freeze, "snapshot", lambda manifest, folder: {"files": []}),
        "stale-row": (takes, "outside_live_block", lambda waiting, live: []),
        "four-open": (takes, "OPEN_LIMIT", 4),
        "row-agent": (takes, "agent_problems", lambda row: []),
        "final-slot": (takes, "slot_final", lambda outcome: False),
        "closed-cell": (takes, "cell_closed", lambda history, cell: False),
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
