#!/usr/bin/env python3
"""The environment record on the ledger side (CP3, fix 4): loaded by test_harness.py, run by name like any class there.

    python3 evals/gap-study-2/test_harness.py TheLedgerCountsEnvironmentRecords

WHAT IS BOUND HERE. The take checker's `environment_problems` decides whether one record is valid. These tests bind
everything around it that a ledger reader does with records: --ledger counts them in one line and names the graded
takes that carry none; attempt_problems refuses a graded take without a valid one, exactly as run.py refuses to grade
it; a rehearsal carries its record into the ledger-made re-run and cannot be founded on a deleted one; and the two
readers that walk attempt folders (takes.unattributed_attempts, the language guard) know environment.json as a take's
record. The graded takes come from test-fixtures/environment-ledger/ (build_take.py), rendered into a repository
each test builds: no test reads this study's live ledger, attempts or history.

No model, no network, stdlib only. Each end-to-end test runs its CLI in a throwaway copy of the study.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path

import test_harness as th

HERE = th.HERE
BUILD = th.FIXTURES / "environment-ledger" / "build_take.py"
# A row commit for takes built outside a repository: the checker reads a row commit as 40 hex, so a stand-in is too.
FAKE_ROW_COMMIT = "c" * 40
# The instruction file a take built in a copy records. study_copy's own placeholder says "under test", a leak word,
# and the checker rightly refuses a take whose loaded context says it; this says nothing about the study.
NEUTRAL_CLAUDE_MD = "A checkout of the system.\n"


def build():
    spec = importlib.util.spec_from_file_location("environment_ledger_build_take", BUILD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git_commit(root: Path, message: str) -> str:
    def git(*args):
        return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                               "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    git("add", "-A")
    r = git("commit", "-q", "--allow-empty", "-m", message)
    if r.returncode != 0:
        raise AssertionError(f"the scratch commit failed: {r.stderr.strip()}")
    return git("rev-parse", "HEAD").stdout.strip()


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class TheLedgerCountsEnvironmentRecords(unittest.TestCase):
    """--ledger says how many graded takes carry an environment record and which do not, and every reader of an
    attempt folder treats the record as the take's."""

    ROW = {"task": "number-fidelity", "half": "control", "model": "claude-opus-5", "take": 1}

    # ------------------------------------------------------------------ helpers

    def study(self, subscription_source):
        """A copy of the study in its own repository, its gars tree neutral and pinned, its subscription value as given."""
        root, dest = th.study_copy(self, git=True)
        (root / "gars" / "CLAUDE.md").write_text(NEUTRAL_CLAUDE_MD)
        sha = _git_commit(root, "a neutral instruction file")
        tree = subprocess.run(["git", "-C", str(root), "rev-parse", f"{sha}:gars"],
                              capture_output=True, text=True).stdout.strip()
        draft = json.loads((dest / "prereg-draft.json").read_text())
        self.assertIn("environment_record", draft, "the draft carries no environment_record block")
        draft["system_under_test"]["gars_tree_sha"] = tree
        draft["environment_record"]["subscription_source"] = subscription_source
        (dest / "prereg-draft.json").write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n")
        _git_commit(root, "the copy's draft names its subscription value")
        return root, dest, draft

    def scratch_take(self, row_commit=FAKE_ROW_COMMIT, record=True):
        """One graded take rendered into a scratch folder, bound to a made-up row commit: (take folder, pre)."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "gars").mkdir()
        (tmp / "gars" / "CLAUDE.md").write_text(NEUTRAL_CLAUDE_MD)
        study = tmp / "study"
        study.mkdir()
        pre = th.prereg.load()
        d = build().build_take(study, tmp, pre, row=0, take=1, row_commit=row_commit, record=record)
        return d, pre

    def ledger_line(self, out: str) -> list[str]:
        return [ln.strip() for ln in out.splitlines() if "graded takes carry an environment record" in ln]

    # ------------------------------------------------------------------ the --ledger line, end to end

    def test_the_ledger_line_names_the_takes_that_carry_no_record(self):
        """Three graded takes, the second without its record: counted, named, and refused, through the CLI."""
        root, dest, draft = self.study("fixture-source")
        build().build_study(root, dest, draft, lambda m: _git_commit(root, m), takes=(1, 2, 3), lacking=(2,))
        r = th.run_py(dest / "check_results.py", "--ledger", cwd=root)
        self.assertEqual(self.ledger_line(r.stdout),
                         ['2 of 3 graded takes carry an environment record; 2 record no API-key variable set; '
                          '2 record apiKeySource "fixture-source" on every turn; rows [1]'], r.stdout + r.stderr)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        problems = [ln for ln in r.stdout.splitlines() if ln.startswith("  - ")]
        self.assertTrue(any(ln.startswith("  - row 1: the graded take carries no valid environment record: ")
                            and "[environment-record]" in ln for ln in problems), problems)
        # the two takes that carry their record are otherwise clean: the fixture measures only the record
        self.assertEqual([ln for ln in problems if not ln.startswith("  - row 1: ")], [], problems)

    def test_with_no_subscription_value_pinned_the_line_names_the_reported_values(self):
        root, dest, draft = self.study(None)
        build().build_study(root, dest, draft, lambda m: _git_commit(root, m), takes=(1, 2), lacking=(1,),
                            api_key_source="fixture-source")
        r = th.run_py(dest / "check_results.py", "--ledger", cwd=root)
        self.assertEqual(self.ledger_line(r.stdout),
                         ['1 of 2 graded takes carry an environment record; 1 record no API-key variable set; '
                          '1 record one apiKeySource reported on every turn, values ["fixture-source"] '
                          '(no subscription value is pinned yet); rows [0]'], r.stdout + r.stderr)

    def test_the_empty_study_prints_the_line_and_passes(self):
        root, dest = th.study_copy(self, git=True)
        value = (json.loads((dest / "prereg-draft.json").read_text()).get("environment_record") or {}).get(
            "subscription_source")
        plain = th.run_py(dest / "check_results.py", cwd=root)
        self.assertEqual(plain.returncode, 0, plain.stdout + plain.stderr)
        r = th.run_py(dest / "check_results.py", "--ledger", cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tail = (f'0 record apiKeySource "{value}" on every turn; rows []' if value is not None
                else "0 record one apiKeySource reported on every turn, values [] (no subscription value is "
                     "pinned yet); rows []")
        self.assertEqual(self.ledger_line(r.stdout),
                         [f"0 of 0 graded takes carry an environment record; 0 record no API-key variable set; {tail}"])

    # ------------------------------------------------------------------ the count, record by record

    def test_the_count_reads_each_record_it_counts(self):
        """Carried means readable and bound by the ledger's sha; the key and the per-turn source read from each."""
        cr = th.gap_module("check_results")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)

        def take(name, rec, bind=True):
            d = tmp / name
            d.mkdir()
            led = {"kind": "take"}
            if rec is not None:
                (d / "environment.json").write_text(json.dumps(rec))
                led["environment"] = {"file": "environment.json",
                                      "sha256": _sha(d / "environment.json") if bind else "0" * 64}
            (d / "driver-ledger.json").write_text(json.dumps(led))
            return d

        def rec(key_set, sources):
            per_turn = [{"n": n, "recovery": False, "exit": 0, "apiKeySource": s} for n, s in enumerate(sources, 1)]
            one = set(sources)
            return {"api_key_set": key_set,
                    "credential_source": {"per_turn": per_turn,
                                          "reported": next(iter(one)) if len(one) == 1 and None not in one else None}}

        graded = {0: take("a", rec(False, ["v", "v"])), 1: take("b", rec(True, ["v"])),
                  2: take("c", rec(False, ["v", None])), 3: take("d", rec(False, ["v"]), bind=False),
                  4: take("e", None), 5: take("f", rec(False, ["w"]))}
        self.assertEqual(cr.environment_count_line(graded, {"environment_record": {"subscription_source": "v"}}),
                         '4 of 6 graded takes carry an environment record; 3 record no API-key variable set; '
                         '2 record apiKeySource "v" on every turn; rows [3, 4]')
        self.assertEqual(cr.environment_count_line(graded, {"environment_record": {"subscription_source": None}}),
                         '4 of 6 graded takes carry an environment record; 3 record no API-key variable set; '
                         '3 record one apiKeySource reported on every turn, values ["v", "w"] '
                         '(no subscription value is pinned yet); rows [3, 4]')

    # ------------------------------------------------------------------ rehearsals

    def rehearsal(self, reasons):
        d, pre = self.scratch_take()
        led = json.loads((d / "driver-ledger.json").read_text())
        led["attempt"] = {"kind": "rehearsal", "reasons": reasons}
        (d / "driver-ledger.json").write_text(json.dumps(led))
        (d / "WHY.md").write_text("why\n")
        return d, pre

    def checker_refusing(self, *problems):
        ct = th.gap_check_take()
        ct.check = lambda *a, **k: list(problems)
        return ct

    def test_a_rehearsal_founded_on_a_take_carries_its_record_into_the_re_run(self):
        """The ledger-made re-run reads the record beside the transcript, byte for byte."""
        cr = th.gap_module("check_results")
        d, _pre = self.rehearsal(["operator-lines"])
        seen = []
        ct = th.gap_check_take()

        def spy(path, *a, **k):
            env = Path(path).parent / "environment.json"
            seen.append(env.read_bytes() if env.is_file() else None)
            return ["[operator-lines] x"]
        ct.check = spy
        with contextlib.redirect_stdout(io.StringIO()):
            made = cr._ledger_made_reasons(d, d / "transcript.jsonl", self.ROW, 0, ct, ["[operator-lines] x"])
        self.assertEqual(made, [])
        self.assertEqual(seen, [(d / "environment.json").read_bytes()], "the re-run did not carry the record")

    def test_a_rehearsal_founded_on_a_deleted_record_is_refused(self):
        cr = th.gap_module("check_results")
        phrase = "cannot be founded on a deleted one"

        d, _pre = self.rehearsal(["operator-lines"])
        ct = self.checker_refusing("[operator-lines] x")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.attempt_problems("rehearsal", d, 0, self.ROW, ct), [], "the control is refused")
        (d / "environment.json").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            got = cr.attempt_problems("rehearsal", d, 0, self.ROW, ct)
        self.assertTrue(any(phrase in p for p in got), f"a rehearsal founded on a deleted record was admitted: {got}")

        # other bytes in its place are the same edit
        d, _pre = self.rehearsal(["operator-lines"])
        with (d / "environment.json").open("a") as fh:
            fh.write(" ")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(any(phrase in p for p in cr.attempt_problems("rehearsal", d, 0, self.ROW, ct)))

        # a pause is routed with its record too
        d, _pre = self.scratch_take()
        led = json.loads((d / "driver-ledger.json").read_text())
        led.update(attempt={"kind": "pause"}, outcome="PAUSE — rate limited before the first agent turn")
        (d / "driver-ledger.json").write_text(json.dumps(led))
        (d / "environment.json").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(any(phrase in p for p in cr.attempt_problems("pause", d, 0, self.ROW, ct)))

        # deleted with its ledger entry: the checker's own refusal, which no rehearsal may record
        d, _pre = self.rehearsal(["environment-record"])
        led = json.loads((d / "driver-ledger.json").read_text())
        del led["environment"]
        (d / "driver-ledger.json").write_text(json.dumps(led))
        (d / "environment.json").unlink()
        self.assertIn("environment-record", th.prereg.load()["driver_decided_reasons"])
        ct = self.checker_refusing("[environment-record] no environment record beside the transcript")
        with contextlib.redirect_stdout(io.StringIO()):
            got = cr.attempt_problems("rehearsal", d, 0, self.ROW, ct)
        self.assertTrue(any("cannot have written this record" in p for p in got), got)

    # ------------------------------------------------------------------ the graded take, both sides

    def test_a_graded_take_without_a_record_is_refused_by_the_ledger_check(self):
        cr = th.gap_module("check_results")
        ct = th.gap_check_take()
        d, _pre = self.scratch_take()
        ct.check = lambda *a, **k: []
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.attempt_problems("graded", d, 0, self.ROW, ct, row_commit=FAKE_ROW_COMMIT), [])
        (d / "environment.json").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            got = cr.attempt_problems("graded", d, 0, self.ROW, ct, row_commit=FAKE_ROW_COMMIT)
        self.assertTrue(any("carries no valid environment record" in p and "[environment-record]" in p
                            for p in got), got)

    def test_run_refuses_to_grade_a_take_without_a_record(self):
        """The grading side of the same refusal, at its call site in grade_cell, with the real take checker."""
        d, _pre = self.scratch_take()
        study = d.parents[4]  # <study>/transcripts/<task>/<half>/<model>/<take>

        run = th.gap_module("run")
        run.HERE = study
        run.TRANSCRIPTS = study / "transcripts"
        takes = th.gap_module("takes")
        run.takes_mod = types.SimpleNamespace(row_commits=lambda: {0: FAKE_ROW_COMMIT},
                                              session_id_for=takes.session_id_for)
        spec = th.prereg.task("number-fidelity")
        cell = run.grade_cell("number-fidelity", "control", "claude-opus-5", spec, 3)
        self.assertEqual(len(cell["labels"]), 1, "the take that carries its record is graded")

        (d / "environment.json").unlink()
        run._ROW_COMMIT_BY_SESSION = None
        with self.assertRaises(SystemExit) as caught:
            run.grade_cell("number-fidelity", "control", "claude-opus-5", spec, 3)
        self.assertIn("carries no valid environment record", str(caught.exception))
        self.assertIn("[environment-record]", str(caught.exception))

    # ------------------------------------------------------------------ the readers of attempt folders

    def test_unattributed_attempts_reads_environment_json_as_a_take_record(self):
        takes = th.gap_module("takes")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        takes.HERE = tmp
        for rel, name in (("transcripts/number-fidelity/control/claude-opus-5/1", "environment.json"),
                          ("rehearsals/number-fidelity/control/claude-opus-5/row-1", "environment.json"),
                          ("pauses/number-fidelity/control/claude-opus-5/row-2", "notes.json")):
            (tmp / rel).mkdir(parents=True)
            (tmp / rel / name).write_text("{}\n")
        self.assertEqual([str(p.relative_to(tmp)) for p in takes.unattributed_attempts()],
                         ["rehearsals/number-fidelity/control/claude-opus-5/row-1",
                          "transcripts/number-fidelity/control/claude-opus-5/1"])

    def test_the_language_guard_reads_environment_json_as_a_take_record(self):
        lint = th.gap_module("lint_language")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        files = {"transcripts/number-fidelity/control/claude-opus-5/1/environment.json": False,
                 "rehearsals/number-fidelity/control/claude-opus-5/row-2/environment.json": False,
                 "pauses/number-fidelity/control/claude-opus-5/row-3/environment.json": False,
                 "walks/number-fidelity/1/environment.json": True,
                 "verification/env-smoke/environment.json": True}
        for rel in files:
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_text("{}\n")
        got = {str(f.relative_to(tmp)) for f in lint.iter_files([str(tmp)])}
        self.assertEqual({rel for rel, scanned in files.items() if scanned}, got)
