#!/usr/bin/env python3
"""The CP2 process tools, each driven through its own command line (structural lesson 12).

    python3 evals/gap-study-2/tests_tools.py [ClassName ...]
    python3 evals/gap-study-2/test_harness.py CommitMsgRefusesASolidusCount   # once the loader lands

commit_msg.py, ci_conclusion.py, clean_clone_battery.sh and check_checklist_names.py are run as a
subprocess, never imported, so a check that exists only inside a function nobody calls cannot pass here.
Canned inputs live in test-fixtures/tools/. The full clean-clone run (a clone of the real repository,
the real suite and battery) is run by the lead, not here; what is driven here is its argument parsing,
its skip check, its skip-naming wrapper, its shallow-clone refusal, and a whole run over a synthetic
two-commit repository whose own suite and battery take a second.

No model, no network. stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import scratch_git  # noqa: E402
REPO = HERE.parent.parent
FIX = HERE / "test-fixtures" / "tools"
COMMIT_MSG = HERE / "commit_msg.py"
CI = HERE / "ci_conclusion.py"
BATTERY = HERE / "clean_clone_battery.sh"
CHECKLIST = HERE / "check_checklist_names.py"

TRAILER = "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
EXPECTED_SKIPS = ("TheCopiedFixtureBuildsToItsPin.test_the_fixture_builds_and_hashes_to_its_pin",
                  "TheFixtureNamesNoPathOutsideTheRunTree.test_the_copied_tree_hashes_to_its_pin_at_two_roots",
                  "TheFixtureNamesNoPathOutsideTheRunTree.test_the_real_copied_tree_names_no_checkout_path")
ORIGIN_REASON = ("the origin project is not on this machine (workspaces/gars-demo-v2/_runs/epigenome-a/20260903-1654/"
                 "ws/projects/epigenome-a); plan-gate cannot be driven from this clone")


def _py(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *argv], capture_output=True, text=True)


def _bash(*argv: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(BATTERY), *argv], capture_output=True, text=True, env=env)


class _MessageFile:
    """A mixin, not a TestCase, so the loader registers no empty class."""

    def lint(self, text: str) -> subprocess.CompletedProcess:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "msg.txt"
        path.write_text(text)
        return _py(str(COMMIT_MSG), str(path))


class CommitMsgRefusesASolidusCount(_MessageFile, unittest.TestCase):
    def test_a_count_in_the_subject_is_refused(self):
        r = self.lint(f"take: row 3/108 recorded\n\n{TRAILER}\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("[solidus-count] line 1", r.stdout)

    def test_a_count_in_the_body_is_refused_with_spaces_around_the_solidus(self):
        r = self.lint("slice 03: the tools\n\nthe battery went red in 12 / 12 runs\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("[solidus-count] line 3", r.stdout)

    def test_a_model_path_segment_is_refused(self):
        r = self.lint("takes: one attempt\n\ntranscripts/plan-gate/control/claude-opus-5/2 filed\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("[solidus-count]", r.stdout)

    def test_an_iso_date_is_not_a_count_and_a_slashed_date_is(self):
        """Decided: 2026-09-13 has no solidus and passes; 13/09/2026 has the shape and is refused."""
        ok = self.lint("ruling: recorded on 2026-09-13\n")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        bad = self.lint("ruling: recorded on 13/09/2026\n")
        self.assertEqual(bad.returncode, 1, bad.stdout)
        self.assertIn("[solidus-count]", bad.stdout)


class CommitMsgRefusesAnUnlistedPrefix(_MessageFile, unittest.TestCase):
    def test_every_listed_prefix_passes(self):
        for subject in ("slice 03: the tools", "take: a row", "takes: an attempt", "walk: plan-gate",
                        "rehearsal: a dry run", "ruling: a word from Javier",
                        "review: pre-freeze review 1, committed as it stands"):
            r = self.lint(subject + "\n")
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "clean"), subject)

    def test_an_unlisted_or_misshapen_prefix_is_refused(self):
        for subject in ("feat: the tools", "slice 3: one digit", "Slice 03: capital", "slice 03:no space",
                        "slice 03:", "take 3: a number before the colon", "the tools, no prefix"):
            r = self.lint(subject + "\n")
            self.assertEqual(r.returncode, 1, subject)
            self.assertIn("[subject-prefix]", r.stdout, subject)


class CommitMsgRunsTheLanguageGuard(_MessageFile, unittest.TestCase):
    def test_a_banned_word_in_the_body_is_refused_by_name(self):
        r = self.lint("slice 03: the tools\n\nThe guard holds reliably.\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("[language:reliab] line 3", r.stdout)
        self.assertNotIn("[solidus-count]", r.stdout)
        self.assertNotIn("[subject-prefix]", r.stdout)

    def test_a_percentage_is_refused(self):
        r = self.lint("slice 03: the tools\n\nnine in ten, or 90% of them\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("[language:percentage]", r.stdout)


class CommitMsgPassesACleanMessage(_MessageFile, unittest.TestCase):
    def test_a_clean_slice_message_with_its_trailer_prints_clean(self):
        r = self.lint("slice 03: round 1's process lessons as guards\n\nLands goal item 4 bullets 3 to 6.\n"
                      f"Evidence: suite OK on 2026-09-13.\n\n{TRAILER}\n")
        self.assertEqual((r.returncode, r.stdout), (0, "clean\n"))

    def test_an_empty_message_and_a_missing_argument_are_not_clean(self):
        empty = self.lint("\n\n")
        self.assertEqual(empty.returncode, 1)
        self.assertIn("[empty-message]", empty.stdout)
        self.assertEqual(_py(str(COMMIT_MSG)).returncode, 2)
        self.assertEqual(_py(str(COMMIT_MSG), str(FIX / "no-such-message.txt")).returncode, 2)


class CommitMsgPassesTheSlicesAlreadyCommitted(unittest.TestCase):
    """The two slices committed before the tool existed are read from history and must be clean. A clone
    without those commits fails here rather than skipping: a skipped check reads like a passed one."""

    def test_slice_one_and_slice_two_are_clean(self):
        for sha in ("e6bda4a", "5d58684"):
            body = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%B", sha],
                                  capture_output=True, text=True)
            self.assertEqual(body.returncode, 0, f"{sha} is not in this history: {body.stderr.strip()}")
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "msg.txt"
                path.write_text(body.stdout)
                r = _py(str(COMMIT_MSG), str(path))
            self.assertEqual((r.returncode, r.stdout), (0, "clean\n"), f"{sha}: {r.stdout}")


class CiConclusionReadsEveryOutcome(unittest.TestCase):
    def conclude(self, name: str) -> subprocess.CompletedProcess:
        return _py(str(CI), "0123456789ab", "--gh-json", str(FIX / f"gh-{name}.json"))

    def test_every_run_completed_with_success_is_exit_0(self):
        r = self.conclude("success")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("every one completed with success", r.stdout)

    def test_a_failed_run_is_exit_1(self):
        r = self.conclude("failure")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("completed    failure          gap-study-2", r.stdout)

    def test_a_run_in_progress_is_exit_3(self):
        r = self.conclude("in-progress")
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("not yet completed", r.stdout)

    def test_no_run_is_exit_2_and_not_a_pass(self):
        r = self.conclude("no-run")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("not a pass", r.stdout)

    def test_a_cancelled_run_beside_a_queued_one_is_exit_1(self):
        r = self.conclude("mixed")
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_unreadable_json_and_usage_errors_are_exit_4(self):
        with tempfile.TemporaryDirectory() as tmp:
            for body in ("not json", '{"status": "completed"}', '[{"name": "no status"}]'):
                path = Path(tmp) / "gh.json"
                path.write_text(body)
                self.assertEqual(_py(str(CI), "abc", "--gh-json", str(path)).returncode, 4, body)
        self.assertEqual(_py(str(CI)).returncode, 4)


FAKE_GH = '''#!{python}
import json, sys
from pathlib import Path
Path({log!r}).write_text(json.dumps(sys.argv[1:]))
sys.stdout.write(Path({canned!r}).read_text())
'''


class CiConclusionResolvesTheCommitFirst(unittest.TestCase):
    """`gh run list --commit` matches a full sha only, so a short sha read as "no run" beside a run that
    had succeeded. The tool is copied into a synthetic repository and run there, against a gh on PATH that
    records the argv it was handed and prints a canned success."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        repo = self.tmp / "src"
        (repo / "evals" / "gap-study-2").mkdir(parents=True)
        self.tool = repo / "evals" / "gap-study-2" / "ci_conclusion.py"
        shutil.copy2(CI, self.tool)
        scratch_git.init(repo)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "one")
        self.full = _tip(repo)
        bindir = self.tmp / "bin"
        bindir.mkdir()
        self.log = self.tmp / "gh-argv.json"
        gh = bindir / "gh"
        gh.write_text(FAKE_GH.format(python=sys.executable, log=str(self.log),
                                     canned=str(FIX / "gh-success.json")))
        gh.chmod(0o755)
        self.env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get("PATH", ""))

    def conclude(self, arg: str, tool: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(tool or self.tool), arg], capture_output=True, text=True,
                              env=self.env)

    def commit_gh_received(self) -> str:
        argv = json.loads(self.log.read_text())
        return argv[argv.index("--commit") + 1]

    def test_a_short_sha_reaches_gh_as_its_full_sha_and_reads_as_the_full_sha_does(self):
        short = self.conclude(self.full[:7])
        self.assertEqual(short.returncode, 0, short.stdout + short.stderr)
        self.assertEqual(self.commit_gh_received(), self.full)
        self.log.unlink()
        full = self.conclude(self.full)
        self.assertEqual(full.returncode, 0, full.stdout + full.stderr)
        self.assertEqual(self.commit_gh_received(), self.full)
        self.assertEqual(short.stdout, full.stdout)
        self.assertIn(f"{self.full[:12]}: 2 run(s), every one completed with success (exit 0)", full.stdout)

    def test_an_argument_that_resolves_to_no_commit_is_exit_4_and_gh_is_never_run(self):
        for arg in ("0000000", "not-a-commit", self.full[:39] + ("0" if self.full[39] != "0" else "1")):
            r = self.conclude(arg)
            self.assertEqual(r.returncode, 4, arg + ": " + r.stdout)
            self.assertEqual(len(r.stdout.splitlines()), 1, r.stdout)
            self.assertIn(repr(arg), r.stdout)
            self.assertFalse(self.log.exists(), f"gh was run for {arg}")

    def test_a_copy_without_its_own_repository_does_not_resolve_against_an_enclosing_one(self):
        outer = self.tmp / "outer"
        (outer / "inner" / "evals" / "gap-study-2").mkdir(parents=True)
        tool = outer / "inner" / "evals" / "gap-study-2" / "ci_conclusion.py"
        shutil.copy2(CI, tool)
        scratch_git.init(outer)
        _git(outer, "add", "-A")
        _git(outer, "commit", "-qm", "outer")
        r = self.conclude(_tip(outer), tool)
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertFalse(self.log.exists())


class CleanCloneBatteryChecksItsSkips(unittest.TestCase):
    def check_lines(self, lines: list[str]) -> subprocess.CompletedProcess:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "suite.txt"
        path.write_text("".join(lines))
        return _bash("--check-skips", str(path))

    def expected_lines(self) -> list[str]:
        return (FIX / "suite-expected.txt").read_text().splitlines(keepends=True)

    def test_the_expected_skips_pass_and_are_named(self):
        r = _bash("--check-skips", str(FIX / "suite-expected.txt"))
        self.assertEqual(r.returncode, 0, r.stdout)
        for name in EXPECTED_SKIPS:
            self.assertEqual(r.stdout.count(f"skip (expected, the origin project is not on this machine): {name}\n"),
                             1, name)
        self.assertEqual(r.stdout.count("skip (live class"), 3)
        self.assertIn("skips as expected", r.stdout)

    def test_any_other_skip_fails_by_name(self):
        r = _bash("--check-skips", str(FIX / "suite-extra-skip.txt"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SKIP NOT EXPECTED: SomeOtherCheck.test_something", r.stdout)
        self.assertNotIn("[expected-skip-count]", r.stdout)

    def test_each_expected_skip_missing_or_repeated_fails_by_name(self):
        for name in EXPECTED_SKIPS:
            r = self.check_lines([x for x in self.expected_lines() if not x.startswith(f"SKIPPED {name}:")])
            self.assertEqual(r.returncode, 1, name + ": " + r.stdout)
            self.assertIn(f"[expected-skip-count] {name} skipped 0 time(s)", r.stdout)
            self.assertEqual(r.stdout.count("[expected-skip-count]"), 1, r.stdout)
            twice = self.expected_lines() + [f"SKIPPED {name}: {ORIGIN_REASON}\n"]
            r = self.check_lines(twice)
            self.assertEqual(r.returncode, 1, name + ": " + r.stdout)
            self.assertIn(f"[expected-skip-count] {name} skipped 2 time(s)", r.stdout)
        r = _bash("--check-skips", str(FIX / "suite-missing-expected.txt"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(r.stdout.count("skipped 0 time(s)"), 3, r.stdout)

    def test_an_expected_name_skipping_for_another_reason_fails(self):
        others = ("outside a workspaces folder",
                  "the origin project is expected beside this repository and is missing: workspaces/x",
                  "the origin project is not on this machine ()",
                  "the origin project is not on this machine")
        for name in EXPECTED_SKIPS:
            for why in others:
                lines = [f"SKIPPED {name}: {why}\n" if x.startswith(f"SKIPPED {name}:") else x
                         for x in self.expected_lines()]
                r = self.check_lines(lines)
                self.assertEqual(r.returncode, 1, f"{name} / {why}: {r.stdout}")
                self.assertIn(f"SKIP FOR ANOTHER REASON: {name}: {why}", r.stdout)

    def test_bad_arguments_are_usage_errors(self):
        for argv in (["--bogus"], ["--source"], ["--out"], ["--check-skips"], ["--source", ""]):
            self.assertEqual(_bash(*argv).returncode, 2, argv)
        self.assertEqual(_bash("--check-skips", str(FIX / "no-such-output.txt")).returncode, 1)

    def test_the_script_parses(self):
        self.assertEqual(subprocess.run(["bash", "-n", str(BATTERY)], capture_output=True).returncode, 0)


FAKE_HARNESS = '''import sys, unittest
WHY = {why!r}
class TheCopiedFixtureBuildsToItsPin(unittest.TestCase):
    def test_the_fixture_builds_and_hashes_to_its_pin(self):
        self.skipTest(WHY)
    def test_a_sibling_runs(self):
        pass
class TheFixtureNamesNoPathOutsideTheRunTree(unittest.TestCase):
    def test_the_copied_tree_hashes_to_its_pin_at_two_roots(self):
        self.skipTest(WHY)
    def test_the_real_copied_tree_names_no_checkout_path(self):
        self.skipTest(WHY)
{extra}
if __name__ == "__main__":
    if "--mutations" in sys.argv:
        print("every one of the guards went red when broken")
        raise SystemExit(0)
    r = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    raise SystemExit(0 if r.wasSuccessful() else 1)
'''


def _git(cwd: Path, *argv: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv], cwd=str(cwd),
                   capture_output=True, check=True)


def _tip(repo: Path) -> str:
    """The full sha a repository the test built is checked out at; never this repository."""
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


class CleanCloneBatteryRunsInACleanClone(unittest.TestCase):
    """The whole script over a synthetic two-commit repository whose harness takes a second."""

    def make_repo(self, extra: str = "") -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name) / "src"
        (repo / "evals" / "gap-study-2").mkdir(parents=True)
        scratch_git.init(repo)
        (repo / "README").write_text("one\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "one")
        (repo / "evals" / "gap-study-2" / "test_harness.py").write_text(FAKE_HARNESS.format(why=ORIGIN_REASON, extra=extra))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "two")
        self.out = Path(tmp.name) / "out.txt"
        return repo

    def harness_reachable(self) -> bool:
        return any(Path(d, t).exists() for d in ("/usr/bin", "/bin") for t in ("claude", "gh"))

    def test_a_shallow_source_is_refused_before_anything_runs(self):
        repo = self.make_repo()
        shallow = repo.parent / "shallow"
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(shallow)],
                       capture_output=True, check=True)
        r = _bash("--source", str(shallow), "--out", str(self.out))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("[shallow-clone]", r.stdout)
        self.assertNotIn("== suite", self.out.read_text())

    def test_a_full_clone_proves_no_harness_names_its_skip_and_writes_its_output(self):
        repo = self.make_repo()
        r = _bash("--source", str(repo), "--out", str(self.out))
        text = self.out.read_text()
        self.assertIn("interpreter: ", text)
        self.assertRegex(text, r"clone: [0-9a-f]{40}, full depth, 2 commits")
        if self.harness_reachable():
            # Where /usr/bin or /bin carries gh or claude (a CI runner does), the proof must fail loudly.
            self.assertEqual(r.returncode, 3, text)
            self.assertIn("[harness-on-path]", text)
            return
        self.assertEqual(r.returncode, 0, text + r.stderr)
        for tool in ("claude", "gh"):
            self.assertIn(f"command -v {tool} inside the cleared environment: not found", text)
        for name in EXPECTED_SKIPS:
            self.assertIn(f"SKIPPED {name}: {ORIGIN_REASON}\n", text)
        self.assertIn("skips as expected", text)
        self.assertIn("suite OK, skips as expected, battery green", text)

    def test_an_unexpected_skip_in_the_clone_fails_the_run(self):
        repo = self.make_repo(extra="class AnotherCheck(unittest.TestCase):\n"
                                    "    def test_x(self):\n        self.skipTest('no reason')\n")
        r = _bash("--source", str(repo), "--out", str(self.out))
        text = self.out.read_text()
        if self.harness_reachable():
            # The harness proof stops the run before the suite there; that stop is what is asserted.
            self.assertEqual(r.returncode, 3, text)
            self.assertIn("[harness-on-path]", text)
            return
        self.assertEqual(r.returncode, 1, text)
        self.assertIn("SKIP NOT EXPECTED: AnotherCheck.test_x", text)


class CheckChecklistNamesReadsTheDoneLines(unittest.TestCase):
    def check(self, draft: str) -> subprocess.CompletedProcess:
        return _py(str(CHECKLIST), str(FIX / "goal.md"), "--draft", str(FIX / f"draft-{draft}.json"))

    def test_every_done_line_name_listed_or_pending_is_exit_0(self):
        r = self.check("all-listed")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Done-line names (4): AlphaCheck, BetaCheck, DeltaCheck, GammaCheck", r.stdout)
        self.assertIn("listed but named by no Done line (1): ExtraListedCheck", r.stdout)
        self.assertIn("pending: DeltaCheck", r.stdout)
        self.assertNotIn("OutsideTheSection", r.stdout)
        self.assertNotIn("EpsilonAfterTheSection", r.stdout)

    def test_every_unlisted_name_is_printed_and_is_exit_1(self):
        r = self.check("none-listed")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("named by a Done line but not listed (4): AlphaCheck, BetaCheck, DeltaCheck, GammaCheck",
                      r.stdout)
        self.assertIn("[unlisted-name]", r.stdout)

    def test_a_draft_without_the_key_is_a_clear_exit_1(self):
        r = self.check("no-key")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("[no-key]", r.stdout)
        self.assertEqual(r.stderr, "")

    def test_a_goal_with_no_done_section_or_no_names_is_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            none = Path(tmp) / "none.md"
            none.write_text("# a goal\n\n## What gets built\n\n`test_harness.py AlphaCheck`\n")
            r = _py(str(CHECKLIST), str(none), "--draft", str(FIX / "draft-all-listed.json"))
            self.assertEqual(r.returncode, 1)
            self.assertIn("[no-done-section]", r.stdout)
            empty = Path(tmp) / "empty.md"
            empty.write_text("# a goal\n\n## Done means\n\n1. verify: `check_results.py` exits 0\n")
            r = _py(str(CHECKLIST), str(empty), "--draft", str(FIX / "draft-all-listed.json"))
            self.assertEqual(r.returncode, 1)
            self.assertIn("[no-names-read]", r.stdout)


def main() -> int:
    loader = unittest.defaultTestLoader
    module = sys.modules[__name__]
    suite = (loader.loadTestsFromNames(sys.argv[1:], module) if len(sys.argv) > 1
             else loader.loadTestsFromModule(module))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if result.testsRun == 0:
        print("\nno test ran. That is not a pass.")
        return 2
    return 0 if result.wasSuccessful() else 1


class TheScrubSplitsOnTheNewlineOnly(unittest.TestCase):
    """Review 1 (round 2) follow-up: a record carrying U+2028 or a form feed is one record, not two."""

    def test_a_record_with_a_unicode_line_separator_survives_whole(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("gap_scrub", HERE / "scrub.py")
        scrub = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scrub)
        # the separators as raw characters, the way the transcript writer emits them (json.dumps would escape them
        # to ASCII and the fixture would carry no separator at all; the first version of this test did exactly that)
        rec = json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "one\u2028two\u0085three\u2029four"}]}},
                         ensure_ascii=False)
        self.assertIn("\u2028", rec)
        raw = rec + "\n" + json.dumps({"type": "user", "message": {"content": "x"}}) + "\n"
        body, removed = scrub.scrub_text(raw)
        self.assertEqual(body.count("\n"), 2, "a record was split at a character that is not a newline")
        self.assertEqual(body, raw, "the scrub changed a record it had no reason to touch")


if __name__ == "__main__":
    raise SystemExit(main())
