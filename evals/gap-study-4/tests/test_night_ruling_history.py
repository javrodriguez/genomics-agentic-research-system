#!/usr/bin/env python3
"""Step-4 fix review finding 1: a committed night ruling through the REAL history reader and door.

takes.read_history (git log over outcomes.json and rulings.json, one record per commit) and Batch.history_problems
must read a night ruling as what it is, takes.commit_night_ruling is its one door (the commit discipline of
commit_ruling), and every reader that told outcomes from take rulings by `not is_ruling` now uses batch.is_outcome,
so a night ruling is never read as an outcome. A throwaway git repository in a temporary folder; no network.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import batch  # noqa: E402
import check_results  # noqa: E402
import takes  # noqa: E402
import test_batch as tb  # noqa: E402
import test_nightly_stop as tns  # noqa: E402

ENV = {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test",
       "GIT_COMMITTER_EMAIL": "test@example.invalid", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


class RealHistory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.dict(os.environ, ENV)
        patch.start()
        self.addCleanup(patch.stop)
        self.repo = Path(self.tmp.name).resolve()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "maintenance.auto", "false")
        b, out, w, d, r, win = tb.run(3, plan={(s, 1): tns.HE for s in (1, 2, 3)}, row_list=tns.cells(3),
                                      cls=batch.Batch)
        self.assertTrue(b.stopped["reason"].startswith(batch.NIGHTLY_STOP))
        self.reaching = b.night_reaching
        records = []
        for o in r.history():                        # one committed outcome per commit, as CP2 commits them
            records.append(o)
            (self.repo / "outcomes.json").write_text(json.dumps(records, indent=2) + "\n")
            git(self.repo, "add", "outcomes.json")
            git(self.repo, "commit", "-q", "-m", "an outcome")

    def read(self):
        return takes.read_history(root=self.repo, repo=self.repo)

    def test_the_reader_reads_a_committed_night_ruling(self):
        rec = {"kind": batch.NIGHT_RULING, "slot": self.reaching[0], "attempt": self.reaching[1], "by": "Javier"}
        (self.repo / "rulings.json").write_text(json.dumps([rec], indent=2) + "\n")
        git(self.repo, "add", "rulings.json")
        git(self.repo, "commit", "-q", "-m", "a night ruling")
        try:
            history = self.read()
        except ValueError as exc:
            self.fail(f"the real history reader refused a committed night ruling: {exc}")
        self.assertEqual(history[-1], rec)

    def test_the_door_commits_a_night_ruling_the_reader_reads(self):
        self.assertTrue(callable(getattr(takes, "commit_night_ruling", None)), "no night-ruling door")
        before = self.read()
        with self.assertRaises(batch.BatchConfigError):
            batch.Batch(tb.FakeDriver(tb.World()), tb.FakeRepo(tb.World(), prior=before),
                        tb.FakeWindow(tb.World()), table=tb.test_table())
        with self.assertRaises(ValueError):
            takes.commit_night_ruling(slot=2, attempt=1, by="Javier", root=self.repo, repo=self.repo)
        with self.assertRaises(ValueError):
            takes.commit_night_ruling(slot=self.reaching[0], attempt=self.reaching[1], by=" ",
                                      root=self.repo, repo=self.repo)
        rec = takes.commit_night_ruling(slot=self.reaching[0], attempt=self.reaching[1], by="Javier",
                                        root=self.repo, repo=self.repo)
        self.assertEqual(rec["kind"], batch.NIGHT_RULING)
        history = self.read()
        self.assertEqual(history[-1], rec)
        self.assertEqual(batch.Batch.history_problems(history), [])
        w = tb.World()
        b = batch.Batch(tb.FakeDriver(w), tb.FakeRepo(w, prior=history), tb.FakeWindow(w), table=tb.test_table())
        self.assertEqual(b.night_counts["harness_error"], 0)
        with self.assertRaises(ValueError):          # a second ruling on the same stop
            takes.commit_night_ruling(slot=self.reaching[0], attempt=self.reaching[1], by="Javier",
                                      root=self.repo, repo=self.repo)

    def test_every_outcome_reader_skips_a_night_ruling(self):
        takes.commit_night_ruling(slot=self.reaching[0], attempt=self.reaching[1], by="Javier",
                                  root=self.repo, repo=self.repo)
        history = self.read()
        self.assertFalse(batch.is_outcome(history[-1]))
        self.assertTrue(all(batch.is_outcome(o) for o in history[:-1]))
        self.assertIsNone(batch.effective_route(history[-1]))
        self.assertFalse(batch.restart_waits(history))
        self.assertEqual(check_results.window_problems(history), [])
        outcomes = takes.registration_outcomes(history)
        self.assertEqual(len(outcomes), len(history) - 1)
        self.assertEqual(takes.registration_outcomes(history[:-1]), outcomes)

    def test_publication_reads_a_history_holding_a_night_ruling(self):
        """Batch-5 review finding 3: cell_history_problems read a night ruling as an outcome (KeyError)."""
        takes.commit_night_ruling(slot=self.reaching[0], attempt=self.reaching[1], by="Javier",
                                  root=self.repo, repo=self.repo)
        history = self.read()
        table = tb.test_table()
        try:
            got = check_results.publication(history, table)
        except KeyError as exc:
            self.fail(f"publication read a night ruling as an outcome: KeyError {exc}")
        self.assertEqual(got, check_results.publication(history[:-1], table),
                         "a night ruling changes no take's publication")


if __name__ == "__main__":
    unittest.main()
