#!/usr/bin/env python3
"""Lane fold2/lb (glitch-45's fold of pre-freeze review 2, FOLD-PLAN-prefreeze-2.md section 1 and section 3, L-B): the
freeze and witness gates, red first.

    python3 -B -W ignore evals/gap-study-4/tests/test_fold2_lb.py

MAJOR 3   the seed review's ruling is read from exactly one anchored ruling line (freeze.read_ruling, imported by
          commit_review, read by freeze.review_file_problems and so by run_builders.py rehearse); zero or several read "ambiguous",
          which commit_review commits unedited and records, and which the freeze refuses.
m5        the round-4 section lints (lint_language and lint_pooling --section-of) exit NOT_RUN (3) when the page has no
          round-4 section, and 0 only under an explicit --allow-absent, which CI passes only while no RESULT.md exists.
m2        the real freeze (freeze.rehearsal_evidence) and check_results (rehearsal_record_problems) read every step of
          the rehearsal record by name: each freeze_rehearsal.COMMANDS step, the holdout check run by --holdout-tool,
          the freeze, holdout-digest and take-order beacon steps, the live-box step with its closed pass line, and the
          runtime steps, each "[0]"; the reviewer's hand-written three-line record is refused.
m3        the draft carries take_order_function_sha256, the sha256 of the source of freeze.planned_order and of every
          study function it calls, found by an ast walk (json_bytes, check_results.validate_ledger and theirs); the
          freeze and --check refuse a draft whose value is not HEAD's.
MAJOR 2   check_results.py --witness (network, on the Mac at publication and each batch fetch) reads GitHub's push
          records of the mirror: a pushed commit off HEAD's line that changes takes.json, outcomes.json or rulings.json
          (an abandoned take history: registered, run, reset and re-run) is refused; every take-ledger commit on HEAD's
          line that no push record holds is printed as the unwitnessed count.
A+ / m1   (section 1's option A+, the beacon code only: no round is registered here) order_beacon.SUPERSEDED_ROUNDS,
          append-only across history; history_problem accepts exactly [None, *superseded rounds, the round]; the
          draft's take_order_beacon carries `superseded`; each entry passes the freeze only by GitHub's push record of
          its swap commit at least SWAP_LEAD_S before the superseded round publishes (before_publication), or by a
          committed owner decision row (owner_decisions.jsonl) that answers the entry's ask with the round's swap
          phrase after the round published, cited by no other entry. SEED_RULE, residual and REGISTRATION_ORDER say
          the true push rule (m1).
ORDER     (glitch-45's item 1, the m3 residual's closing check) check_results.take_order_problems recomputes the seed
          from the frozen beacon reading and take_order from the frozen rows in an isolated interpreter (-I -S, stdlib
          only, no study module), so a study-file monkey-patch that leaves take_order_function_sha256 unchanged cannot
          reach the recompute; any mismatch with the recorded seed or order is refused.
OD160     (glitch-45's item 2) Javier's recorded T199 answer, owner_decisions.jsonl's only row, byte-identical to
          decision.jsonl line 160, binds round 33496978's prepared entry through a simulated swap commit.
ORCH      glitch-45's review of bc207c0a (fold2-lb-REVIEW-orch.md), its reproductions as red tests: MJ-1 (a merge that
          puts the abandoned outcome first), MJ-2 (the witness wired into publication, its record and count), MJ-3 (a
          loose or second ruling-like line), mn-1 (the reading bound to the registered round), mn-2 (the recompute's
          verdict in a standalone isolated file), mn-3 (a superseded, re-answered or expired decision), mn-5 (the
          section lints in the local publication gate).
RECHECK   glitch-45's re-check of 24fa9be6 (PASS, four items): R-1 (the witness record read from HEAD, its counts
          recomputed), R-2 (quicknet pinned in order_reference.py, the round held to the committed draft's), R-3 (a
          canonical ruling line in a fence or behind '>' never counts and makes the report ambiguous), R-4 (a same-ask
          row with no readable time refuses).
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import freeze  # noqa: E402
import study  # noqa: E402


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                          "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {args}: {out.stderr}")
    return out.stdout.strip()


def load_commit_review():
    spec = importlib.util.spec_from_file_location("fold2_commit_review", HERE / "review_kit" / "commit_review.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DO = "**Ruling: DO FREEZE.**"
DO_NOT = "**Ruling: DO NOT FREEZE.**"


def report(digest: str, *body: str) -> str:
    return "\n".join((f"prereg.json sha256: {digest}", "", "# synthetic review", "", *body)) + "\n"


# The reviewer's shape (review 2, MAJOR 3): a correct line 1, the bold DO NOT FREEZE line, and the DO FREEZE literal
# quoted inside a sentence, as the review brief's "name both rulings" invites.
QUOTED = (DO_NOT, "", f"The brief names both rulings; the other would have read {DO} on its own line.")
TWO_LINES = (DO, "", "Second thoughts:", "", DO_NOT)


@contextlib.contextmanager
def review_repo(*bodies):
    """A scratch repository whose study folder holds a draft and one committed review per body (prefreeze-5.md, ...);
    yields (repo, draft path, [commit per review])."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q")
        study_dir = repo / study.STUDY_REL
        (study_dir / study.REVIEW_DIR).mkdir(parents=True)
        draft = study_dir / "prereg-draft.json"
        draft.write_bytes(b'{"synthetic": "draft"}\n')
        digest = hashlib.sha256(draft.read_bytes()).hexdigest()
        shas = []
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "draft")      # lane fold8/review-binding: round 5's launch commit
        # lane fold8/review-binding (review 6, M1): rounds 1-4 no longer seed (REPORT_DIGEST_GRANDFATHERED), so the
        # rig's rounds start at 5, each blindness record stating its report's digest as fold5's rule needs
        for n, body in enumerate(bodies, 5):
            register_round(repo, study_dir / study.REVIEW_DIR, n)      # lane fold3/m1 (review 3, m2): its row first
            text = report(digest, *body)
            (study_dir / study.REVIEW_DIR / f"prefreeze-{n}.md").write_text(text)
            with (study_dir / study.REVIEW_DIR / f"prefreeze-{n}-blindness.txt").open("a") as fh:
                fh.write(freeze._blindness().REPORT_DIGEST + hashlib.sha256(text.encode()).hexdigest() + "\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", f"review {n}")
            shas.append(git(repo, "rev-parse", "HEAD"))
        # lane fold8/review-binding (review 6, M2): the launch binding compares the pinned paths; the rig pins its draft
        with mock.patch.object(freeze, "PINNED", [study.rel("prereg-draft.json")]):
            yield repo, draft, shas


def register_round(repo: Path, review_dir: Path, n: int) -> None:
    """Lane fold3/m1 (pre-freeze review 3, m2): the round's row committed alone in review_kit/rounds.json, then its
    blindness record naming the session id that commit derives, written for the review's own commit to carry."""
    import json
    import takes
    reg = review_dir / "rounds.json"
    rows = json.loads(reg.read_text())["rows"] if reg.is_file() else []
    # lane fold8/review-binding (review 6, M2): the launch commit, None in a repository with no commit yet
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "-q", "--verify", "HEAD"], capture_output=True, text=True)
    launch = head.stdout.strip() or None
    reg.write_text(json.dumps({"rows": rows + [{"n": n, "kind": "prefreeze", "launch_commit": launch,
                                                "voids": None}]}) + "\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"register round {n}")
    sid = takes.session_id_for(git(repo, "rev-parse", "HEAD"))
    (review_dir / f"prefreeze-{n}-blindness.txt").write_text(f"session id: {sid}\n")


def seed_problems(body):
    with review_repo(body) as (repo, draft, shas), \
            mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft):
        bad, _ = freeze.review_file_problems(shas[0])
    return bad


class TestMajor3Ruling(unittest.TestCase):
    def test_quoted_literal_beside_a_do_not_freeze_line_is_refused(self):
        self.assertTrue(seed_problems(QUOTED), "MAJOR 3: a DO NOT FREEZE report quoting the literal seeds a freeze")

    def test_two_anchored_ruling_lines_are_refused(self):
        self.assertTrue(seed_problems(TWO_LINES), "MAJOR 3: a report with two ruling lines seeds a freeze")

    def test_plain_do_freeze_still_passes(self):
        self.assertEqual(seed_problems((DO,)), [])

    def test_do_not_freeze_and_no_line_are_refused(self):
        self.assertTrue(seed_problems((DO_NOT,)))
        self.assertTrue(seed_problems(("No ruling here.",)))

    def test_read_ruling_reads_exactly_one_anchored_line(self):
        cr = load_commit_review()
        cases = {(DO,): "DO FREEZE", (DO_NOT,): "DO NOT FREEZE", QUOTED: cr.AMBIGUOUS,     # MJ-3: quoted is ambiguous
                 TWO_LINES: cr.AMBIGUOUS, (DO, DO): cr.AMBIGUOUS, ("none",): cr.AMBIGUOUS,
                 (f"> {DO}",): cr.AMBIGUOUS, (DO + " ",): cr.AMBIGUOUS}
        for body, want in cases.items():
            with self.subTest(body=body):
                self.assertEqual(cr.read_ruling(report("0" * 64, *body)), want)

    def test_freeze_reads_the_ruling_through_commit_review(self):
        # one reader: commit_review's read_ruling is freeze's, and the gate reads through it
        cr = load_commit_review()
        self.assertIs(cr.read_ruling.__code__, freeze.read_ruling.__code__)
        with review_repo((DO,)) as (repo, draft, shas), \
                mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft), \
                mock.patch.object(freeze, "read_ruling", lambda text: cr.AMBIGUOUS):
            bad, _ = freeze.review_file_problems(shas[0])
        self.assertTrue(bad and "ambiguous" in bad[0], bad)

    def test_rehearse_latest_review_uses_the_same_gate(self):
        # run_builders.py rehearse's no-pre-freeze-review path calls freeze.review_file_problems
        import run_builders
        with review_repo(QUOTED) as (repo, draft, shas), \
                mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft):
            self.assertIsNone(run_builders.latest_review(repo))
        with review_repo((DO,)) as (repo, draft, shas), \
                mock.patch.object(freeze, "REPO", repo), mock.patch.object(freeze, "DRAFT", draft):
            self.assertEqual(run_builders.latest_review(repo), shas[0])

    def test_commit_review_commits_an_ambiguous_report_unedited(self):
        """commit_review never refuses a report for its ruling (a refused report is a voided round and a second draw
        of the review): two ruling lines, or none, are committed unedited and recorded as ambiguous."""
        for body in (TWO_LINES, ("No ruling line at all.",), QUOTED):
            with self.subTest(body=body[0]):
                msg, committed, text = self.run_commit_review(body)
                self.assertIsNotNone(committed, msg)
                self.assertEqual(committed, text, "the report is committed unedited")
                want = "ambiguous"     # MJ-3 (glitch-45's review): the quoted shape reads ambiguous too
                self.assertIn(f"ruled: {want}", msg)

    def run_commit_review(self, body):
        cr = load_commit_review()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            study_dir = repo / study.STUDY_REL
            (study_dir / study.REVIEW_DIR).mkdir(parents=True)
            git(repo, "init", "-q")
            git(repo, "config", "user.name", "t")
            git(repo, "config", "user.email", "t@example.invalid")
            # a link: commit_msg.py resolves its own folder, so it lints with the real lint_language and study
            (study_dir / "commit_msg.py").symlink_to(HERE / "commit_msg.py")
            (study_dir / "prereg-draft.json").write_bytes(b'{"synthetic": "draft"}\n')
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
            folder = Path(tmp) / "round"
            launch = Path(tmp) / "round-launch"
            folder.mkdir()
            launch.mkdir()
            kit = b'{"synthetic": "kit"}\n'
            (folder / "prereg.json").write_bytes(kit)
            text = report(hashlib.sha256(kit).hexdigest(), *body)
            (folder / "prefreeze-3.md").write_text(text)
            # lane fold5/report-binding (pre-freeze review 5, M1, and the review of f3ae7772): commit_review re-derives
            # the record from the reviewer's session file, so the rig gives it one whose one Write is the report
            import json
            import takes
            # the re-check of 0beda082, MINOR 1: SESSION must be round 3's registered session
            (study_dir / study.REVIEW_DIR / "rounds.json").write_text(json.dumps(
                {"rows": [{"n": k, "kind": "prefreeze", "voids": None} for k in (1, 2, 3)]}) + "\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "register")
            sid = takes.session_id_for(git(repo, "rev-parse", "HEAD"))
            projects = Path(tmp) / "projects"
            (projects / "-round").mkdir(parents=True)
            (launch / "SESSION").write_text(sid + "\n")
            path = str(folder.resolve() / "prefreeze-3.md")
            (projects / "-round" / f"{sid}.jsonl").write_text("\n".join((
                json.dumps({"type": "assistant", "cwd": str(folder.resolve()), "message": {"content": [
                    {"type": "tool_use", "id": "w1", "name": "Write", "input": {"file_path": path, "content": text}}]}}),
                json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "w1",
                                                                     "is_error": False, "content": "ok"}]}}))) + "\n")
            (launch / "blindness.txt").write_text(cr.blindness.report(folder.resolve(), sid, projects))
            out = io.StringIO()
            with mock.patch.object(cr, "STUDY_DIR", study_dir), mock.patch.object(cr, "REPO", repo), \
                    mock.patch.object(cr.blindness, "PROJECTS", projects), \
                    mock.patch.object(sys, "argv", ["commit_review.py", str(folder), "3"]), \
                    contextlib.redirect_stdout(out):
                code = cr.main()
            dest = study_dir / study.REVIEW_DIR / "prefreeze-3.md"
            if code != 0 or not dest.is_file():
                return out.getvalue(), None, text
            msg = git(repo, "log", "-1", "--format=%B")
            return msg, dest.read_text(), text


REPO_ROOT = HERE.parent.parent


def run_lint(script: str, page: Path, *extra: str):
    got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(HERE / script), "--section-of", str(page), *extra],
                         capture_output=True, text=True, cwd=str(REPO_ROOT))
    return got.returncode, got.stdout + got.stderr


LIVE_BOX_PASS = ("live-box record " + "e" * 64 + ": walk lb1, budget 10 s of 20 s, turn 2 cut (end timed-out, exit "
                 "124), stream 3 unit(s), session 3 unit(s), shape equal, content problems 0, session torn no; files 4 "
                 "re-read equal; adapter, check_take and checker digests this tree's; within the bound")


def rehearsal_lines(digest="a" * 64, tree="b" * 64, *, drop=(), tails=None, codes=None):
    """A full green rehearsal record in freeze_rehearsal.main's shape, every step named; `drop` leaves steps out,
    `tails` and `codes` override a step's tail line or code."""
    import freeze_rehearsal as fr
    tails, codes = tails or {}, codes or {}
    names = ["freeze", "holdout digests", "take-order beacon", fr.LIVE_BOX_STEP]
    names += [fr.HOLDOUT_STEP_LABEL if c == fr.HOLDOUT_GATE else " ".join(c) for c in fr.COMMANDS]
    names += [" ".join(c) for c in fr.runtime_commands("<scratch>/row.json")]
    lines = [digest, "Disposable rehearsal; no takes driven.", freeze.REHEARSAL_TREE_PREFIX + tree]
    for name in names:
        if name in drop:
            continue
        default = LIVE_BOX_PASS if name == fr.LIVE_BOX_STEP else "ok"
        lines += [f"[{codes.get(name, 0)}] {name}", "    " + tails.get(name, default)]
    return lines + ["all green"]


class TestM2RehearsalSteps(unittest.TestCase):
    def evidence(self, lines):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "freeze-rehearsal-1.txt"
            record.write_text("\n".join(lines) + "\n")
            try:
                freeze.rehearsal_evidence(record, "a" * 64, "b" * 64)
                return None
            except ValueError as e:
                return str(e)

    def published(self, lines):
        import check_results as cr
        text = "\n".join(lines) + "\n"
        frozen = {"draft_sha256_at_freeze": "a" * 64, "rehearsed_study_tree_sha256": "b" * 64,
                  "rehearsal_record": {"name": "r.txt", "text": text,
                                       "sha256": hashlib.sha256(text.encode()).hexdigest()}}
        return cr.rehearsal_record_problems(frozen)

    def test_the_reviewers_three_line_record_is_refused(self):
        three = ["a" * 64, freeze.REHEARSAL_TREE_PREFIX + "b" * 64, freeze.REHEARSAL_LAST_LINE]
        self.assertIsNotNone(self.evidence(three), "m2: a hand-written three-line record passes the freeze")
        self.assertTrue(self.published(three), "m2: a hand-written three-line record passes check_results")

    def test_a_full_record_passes(self):
        self.assertIsNone(self.evidence(rehearsal_lines()))
        self.assertEqual(self.published(rehearsal_lines()), [])

    def test_a_report_written_by_freeze_rehearsal_main_passes(self):
        """The fold's review, m-4: the reader against a report the real freeze_rehearsal.main writes (clone, git and
        each step stood in for, the runtime steps kept), so the <scratch> masking, the holdout label and the live-box
        tail are read as main writes them, not as this test's own fixture names them."""
        import json
        import freeze_rehearsal as fr
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp).resolve()
            scratch, draft = tmp / "scratch", tmp / "prereg-draft.json"
            scratch.mkdir()
            draft.write_bytes((HERE / "prereg-draft.json").read_bytes())
            tool = tmp / "tool" / "holdout.py"
            tool.parent.mkdir()
            tool.write_text("# stand-in, never run\n")
            record = tmp / "live-box-record.json"
            record.write_text("{}\n")
            sha = hashlib.sha256(record.read_bytes()).hexdigest()

            def sh(argv, cwd, env=None, timeout=3600):
                if argv[:2] == ["git", "clone"]:
                    (Path(argv[-1]) / study.STUDY_REL).mkdir(parents=True)
                    (Path(argv[-1]) / study.STUDY_REL / "prereg-draft.json").write_bytes(draft.read_bytes())
                return 0, ""

            def run_step(command, clone):
                command = [str(c) for c in command]
                if command[4].endswith("freeze.py"):
                    source = json.loads(Path(command[command.index("--holdout-digests") + 1]).read_text())
                    digests = source["salted_sha256"]
                    frozen = {"take_order": [{}], "take_order_beacon_reading": {"signature": "ab"},
                              "holdout_salted_digests": digests,
                              "holdout_wordings_per_task_version": len(next(iter(digests.values())))}
                    (Path(clone) / study.STUDY_REL / "prereg.json").write_text(json.dumps(frozen))
                    return 0, "freeze: wrote prereg.json"
                if command[4].endswith("live_box_cut.py"):
                    return 0, LIVE_BOX_PASS.replace("e" * 64, sha) + "\n"
                return 0, "ok"

            patches = ((fr, "DRAFT", draft), (fr, "sh", sh), (fr, "run_step", run_step),
                       (fr, "git", lambda clone, *a: (0, "a" * 40 + "\n") if a[:2] == ("rev-parse", "HEAD") else (0, "")),
                       (fr, "rehearsal_plan", lambda pre, row: ({}, fr.runtime_commands(row))),
                       (fr.tempfile, "mkdtemp", lambda *a, **k: str(scratch)),
                       (fr.freeze, "outputs_exist", lambda *a: False),
                       (fr.freeze, "review_file_problems", lambda commit: ([], "review/prefreeze-3.md")),
                       (fr.freeze, "study_tree_sha", lambda *a, **k: "c" * 64))
            with contextlib.ExitStack() as stack:
                for mod, name, value in patches:
                    stack.enter_context(mock.patch.object(mod, name, value))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                code = fr.main(["--review-commit", "a" * 40, "--holdout-tool", str(tool), "--live-box-record",
                                str(record), "--live-box-sha256", sha])
            report = scratch / "freeze-rehearsal-1.txt"
            text = report.read_text()
            self.assertEqual((code, text.rstrip().splitlines()[-1]), (0, "all green"), text)
            self.assertIn("[0] takes.py --add --row <scratch>/row.json --attempt 1", text)
            self.assertEqual(freeze.rehearsal_step_problems(text.rstrip().splitlines()), [], text)
            digest = hashlib.sha256(draft.read_bytes()).hexdigest()
            self.assertEqual(freeze.rehearsal_evidence(report, digest, "c" * 64)["text"], text)

    def test_each_missing_or_red_step_is_refused(self):
        import freeze_rehearsal as fr
        holdout = fr.HOLDOUT_STEP_LABEL
        cases = {
            "live-box missing": rehearsal_lines(drop=(fr.LIVE_BOX_STEP,)),
            "live-box not its closed pass line": rehearsal_lines(tails={fr.LIVE_BOX_STEP: "looks fine"}),
            "holdout run without the tool (OWED)": rehearsal_lines(drop=(holdout,)) [:-1]
            + ["[0] holdout.py --check", "    " + fr.OWED["holdout.py"], "all green"],
            "a COMMANDS step missing": rehearsal_lines(drop=(" ".join(fr.COMMANDS[0]),)),
            "the take-order beacon step missing": rehearsal_lines(drop=("take-order beacon",)),
            "a runtime step missing": rehearsal_lines(drop=(" ".join(fr.runtime_commands("<scratch>/row.json")[2]),)),
            "a step with a non-zero code": rehearsal_lines(codes={"freeze": 1}),
            "a step named twice": rehearsal_lines()[:-1] + ["[0] freeze", "    ok", "all green"],
        }
        for name, lines in cases.items():
            with self.subTest(case=name):
                self.assertIsNotNone(self.evidence(lines), f"m2: the freeze accepts a record with {name}")
                self.assertTrue(self.published(lines), f"m2: check_results accepts a record with {name}")


@contextlib.contextmanager
def study_copy():
    """The study's top-level .py files copied into a scratch folder (the order function's walk reads only those)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for f in HERE.glob("*.py"):
            shutil.copy2(f, root / f.name)
        yield root


def edit(path: Path, old: str, new: str):
    text = path.read_text()
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new))


class TestM3OrderFunction(unittest.TestCase):
    def test_the_walk_finds_the_called_study_functions(self):
        names = [name for name, _ in freeze.order_function_sources()]
        for want in ("freeze.planned_order", "freeze.json_bytes", "check_results.validate_ledger", "order_beacon.seed",
                     "order_beacon.SEED_PREFIX="):
            self.assertIn(want, names)
        self.assertEqual(names, sorted(names), "a fixed order")
        self.assertRegex(freeze.take_order_function_sha256(), r"^[0-9a-f]{64}$")

    def test_a_change_to_any_called_helper_changes_the_hash(self):
        base = freeze.take_order_function_sha256()
        with study_copy() as root:
            self.assertEqual(freeze.take_order_function_sha256(root), base, "a copy hashes as the study")
            mutants = {
                "planned_order": ("freeze.py", "    if not rows:\n        raise ValueError(\"the design has no planned rows\")",
                                  "    if not rows:\n        raise ValueError(\"no rows\")"),
                "json_bytes": ("freeze.py", "json.dumps(value, indent=2, ensure_ascii=False)",
                               "json.dumps(value, indent=1, ensure_ascii=False)"),
                "validate_ledger": ("check_results.py", "def validate_ledger(rows: list) -> dict:\n",
                                    "def validate_ledger(rows: list) -> dict:\n    rows = rows[:]\n"),
            }
            for name, (f, old, new) in mutants.items():
                with self.subTest(mutant=name):
                    text = (root / f).read_text()
                    edit(root / f, old, new)
                    try:
                        self.assertNotEqual(freeze.take_order_function_sha256(root), base, f"m3: {name} unwitnessed")
                    finally:
                        (root / f).write_text(text)
            # the fold's review, m-1: a decorator, a module-level rebinding (plain, conditional, or by attribute from
            # another module), and the seed's derivation all move it
            more = {
                "decorator": ("freeze.py", "def planned_order(draft, seed):\n",
                              "@(lambda f: f)\ndef planned_order(draft, seed):\n"),
                "rebinding": ("freeze.py", "\n\ndef generated_pins(outputs):",
                              "\n\njson_bytes = lambda value: b'x'\n\n\ndef generated_pins(outputs):"),
                "conditional rebinding": ("freeze.py", "\n\ndef generated_pins(outputs):",
                                          "\n\nif True:\n    json_bytes = len\n\n\ndef generated_pins(outputs):"),
                "attribute rebinding": ("freeze.py", "\n\ndef generated_pins(outputs):",
                                        "\n\nimport check_results\ncheck_results.validate_ledger = len\n\n\n"
                                        "def generated_pins(outputs):"),
                "seed text": ("order_beacon.py", 'SEED_PREFIX = "gap-study-4 take order\\n"',
                              'SEED_PREFIX = "gap-study-4 take order 2\\n"'),
                "seed function": ("order_beacon.py", "hexdigest()[:40]", "hexdigest()[-40:]"),
            }
            for name, (f, old, new) in more.items():
                with self.subTest(mutant=name):
                    text = (root / f).read_text()
                    edit(root / f, old, new)
                    try:
                        self.assertNotEqual(freeze.take_order_function_sha256(root), base, f"m3: {name} unwitnessed")
                    finally:
                        (root / f).write_text(text)
            # a function the order never reaches, and lines moved above it, do not move it
            edit(root / "freeze.py", "def outputs_exist(root: Path) -> bool:\n",
                 "def outputs_exist(root: Path) -> bool:\n    root = root\n\n\n\n")
            self.assertEqual(freeze.take_order_function_sha256(root), base)

    def test_the_draft_carries_it_and_the_freeze_holds_it_to_head(self):
        import build_draft
        d = build_draft.assemble()
        self.assertEqual(d.get(freeze.ORDER_FUNCTION_HASH_KEY), freeze.take_order_function_sha256(),
                         "m3: build_draft does not register the order function's hash")
        keys = list(d)
        self.assertEqual(keys.index(freeze.ORDER_FUNCTION_HASH_KEY), keys.index("take_order_function") + 1)
        good = {freeze.ORDER_FUNCTION_HASH_KEY: freeze.take_order_function_sha256()}
        self.assertIsNone(freeze.order_function_problem(good))
        for bad in ({}, {freeze.ORDER_FUNCTION_HASH_KEY: "0" * 64}, {freeze.ORDER_FUNCTION_HASH_KEY: None}):
            with self.subTest(bad=bad):
                self.assertTrue(freeze.order_function_problem(bad), "m3: a draft not holding HEAD's order function")


class TestM5SectionAbsent(unittest.TestCase):
    def test_absent_section_is_not_run_unless_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "EVALS.md"
            page.write_text("Earlier rounds only.\n")
            for script in ("lint_language.py", "lint_pooling.py"):
                with self.subTest(script=script):
                    code, out = run_lint(script, page)
                    self.assertEqual(code, 3, f"m5: {script} passes a page with no round-4 section: {out}")
                    self.assertIn("Not a pass", out)
                    code, out = run_lint(script, page, "--allow-absent")
                    self.assertEqual(code, 0, out)
                    self.assertIn("Not a pass", out)
            missing = Path(tmp) / "no-such-page.md"
            for script in ("lint_language.py", "lint_pooling.py"):
                self.assertEqual(run_lint(script, missing)[0], 3, script)

    def test_a_present_section_is_linted_either_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "EVALS.md"
            page.write_text(f"{study.SUMMARY_START}\nOpus outperforms Sonnet.\n{study.SUMMARY_END}\n")
            for extra in ((), ("--allow-absent",)):
                self.assertEqual(run_lint("lint_language.py", page, *extra)[0], 1, extra)
            page.write_text(f"{study.SUMMARY_START}\nA plain sentence.\n{study.SUMMARY_END}\n")
            for script in ("lint_language.py", "lint_pooling.py"):
                self.assertEqual(run_lint(script, page, "--allow-absent")[0], 0, script)

    def test_section_main_returns_not_run(self):
        import lint_language
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "EVALS.md"
            page.write_text("nothing\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(lint_language.section_main(page), lint_language.NOT_RUN)
                self.assertEqual(lint_language.section_main(page, allow_absent=True), 0)

    def test_ci_allows_absence_only_before_a_result_exists(self):
        ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
        for script in ("lint_pooling.py", "lint_language.py"):
            want = (f"run: python3 evals/gap-study-4/{script} --section-of docs/EVALS.md "
                    f"$(test -f evals/gap-study-4/RESULT.md || echo --allow-absent)")
            self.assertIn(want, ci, f"m5: CI's {script} section step")
            self.assertNotIn(f"run: python3 evals/gap-study-4/{script} --section-of docs/EVALS.md\n", ci)


class LedgerScratch:
    """A scratch repository whose study folder holds the three take-ledger files."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        self.dir = self.repo / study.STUDY_REL
        self.dir.mkdir(parents=True)
        (self.dir / "build.txt").write_text("frozen\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "freeze")
        self.base = git(self.repo, "rev-parse", "HEAD")

    def append(self, name, record, msg) -> str:
        f = self.dir / name
        rows = __import__("json").loads(f.read_text()) if f.is_file() else ({"rows": []} if name == "takes.json" else [])
        (rows["rows"] if name == "takes.json" else rows).append(record)
        f.write_text(__import__("json").dumps(rows) + "\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)
        return git(self.repo, "rev-parse", "HEAD")

    def check(self, pushes):
        import check_results as cr
        with mock.patch.object(cr, "REPO", self.repo), mock.patch.object(cr, "HERE", self.dir):
            return cr.take_ledger_witness(pushes)


class TestMajor2TakeWitness(unittest.TestCase):
    def test_a_pushed_outcome_reset_away_and_rerun_is_refused(self):
        sc = LedgerScratch()
        sc.append("takes.json", {"slot": "s1", "attempt": 1}, "register s1")
        bad = sc.append("outcomes.json", {"slot": "s1", "route": "graded", "holding": False}, "outcome s1")
        git(sc.repo, "reset", "-q", "--hard", sc.base)
        sc.append("takes.json", {"slot": "s1", "attempt": 1}, "register s1 again")
        good = sc.append("outcomes.json", {"slot": "s1", "route": "graded", "holding": True}, "outcome s1 again")
        problems, _, _ = sc.check([(100, bad), (200, good)])
        self.assertTrue(problems and "abandoned take history" in problems[0], f"MAJOR 2: {problems}")

    def test_every_commit_pushed_passes_and_an_unpushed_one_is_printed(self):
        sc = LedgerScratch()
        r1 = sc.append("takes.json", {"slot": "s1", "attempt": 1}, "register s1")
        o1 = sc.append("outcomes.json", {"slot": "s1"}, "outcome s1")
        problems, ledger, unwitnessed = sc.check([(100, o1)])
        self.assertEqual((problems, sorted(ledger), unwitnessed), ([], sorted([r1, o1]), []))
        r2 = sc.append("takes.json", {"slot": "s2", "attempt": 1}, "register s2")
        u = sc.append("rulings.json", {"slot": "s2"}, "ruling s2")
        problems, ledger, unwitnessed = sc.check([(100, o1)])
        self.assertEqual(problems, [])
        self.assertEqual(sorted(unwitnessed), sorted([r2, u]))

    def test_a_pushed_history_merged_back_with_ours_is_refused(self):
        # the fold's review, M-1: reset is not the only verb; `git merge -s ours` keeps the abandoned outcome an
        # ancestor of HEAD while takes.read_history's simplified log never reads it
        sc = LedgerScratch()
        sc.append("takes.json", {"slot": "s1", "attempt": 1}, "register s1")
        bad = sc.append("outcomes.json", {"slot": "s1", "holding": False}, "outcome s1")
        git(sc.repo, "checkout", "-q", "-b", "redo", sc.base)
        sc.append("takes.json", {"slot": "s1", "attempt": 1}, "register s1 again")
        sc.append("outcomes.json", {"slot": "s1", "holding": True}, "outcome s1 again")
        git(sc.repo, "merge", "-q", "-s", "ours", "-m", "keep the rerun", bad)
        problems, _, _ = sc.check([(100, bad)])
        self.assertTrue(problems and "merged back" in problems[-1], f"M-1: {problems}")

    def test_a_pushed_sha_missing_from_the_clone_is_refused(self):
        sc = LedgerScratch()
        problems, _, _ = sc.check([(100, "1" * 40)])
        self.assertTrue(problems and "not in this clone" in problems[0], problems)

    def test_main_witness_prints_the_unwitnessed_count(self):
        import check_results as cr
        sc = LedgerScratch()
        r1 = sc.append("takes.json", {"slot": "s1", "attempt": 1}, "register s1")
        out = io.StringIO()
        with mock.patch.object(cr, "REPO", sc.repo), mock.patch.object(cr, "HERE", sc.dir), \
                mock.patch.object(freeze, "push_records", lambda: []), contextlib.redirect_stdout(out):
            code = cr.main(["--witness"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("1 take-ledger commit(s) on HEAD's line, 1 unwitnessed", out.getvalue())
        self.assertIn(r1[:12], out.getvalue())


import order_beacon as ob  # noqa: E402

R0 = 33496978                       # the burned round (published 2026-10-29T17:18:18Z)
R2 = R0 + 50000                     # a later round, about 41.7 h later
R3 = R2 + 50000


def published(r):
    return ob.published_text(r)


def before_entry(r, registering):
    return {"round": r, "published": published(r), "registering_commit": registering, "push": "synthetic push",
            "why": "synthetic: a fold changed the draft after the round's push deadline", "record": "synthetic",
            "before_publication": True}


def decision_entry(r, registering, decision="OD200", ask="T199"):
    return {"round": r, "published": published(r), "registering_commit": registering, "push": "synthetic push",
            "why": "synthetic: DO NOT FREEZE after the round's push deadline", "record": "synthetic",
            "decision": decision, "ask": ask}


def decision_row(**edits):
    row = {"action": "ask.answer", "actor_label": "Javier", "actor_role": "principal",
           "created_at": "2026-10-30T14:00:00Z", "expires_at": None, "id": "OD200", "outcome": "aplus",
           "principal_match": "beacon-r4 aplus", "principal_record_uuid": "00000000-0000-0000-0000-000000000000",
           "principal_session_id": "00000000-0000-0000-0000-000000000000", "principal_turn_at": "2026-10-30T13:59:00Z",
           "principal_turn_sha256": "c" * 64, "rationale": "synthetic", "supersedes_id": None, "target_id": "T199",
           "target_type": "task", "verified_at": "2026-10-30T14:00:00Z"}
    row.update(edits)
    return row


# OD147 as decision.jsonl line 147 holds it (Javier's "mirror-early yes", the early push, not the swap)
OD147 = decision_row(created_at="2026-10-29T14:07:19Z", id="OD147", outcome="yes", principal_match="mirror-early yes",
                     target_id="T181")


class BeaconScratch:
    """A scratch repository with evals/gap-study-4/order_beacon.py (REGISTERED_ROUND and SUPERSEDED_ROUNDS) and
    prereg-draft.json."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / study.STUDY_REL).mkdir(parents=True)
        self.superseded = ()

    def commit(self, *, round_no="keep", superseded="keep", draft=None, other=None, msg="c") -> str:
        d = self.repo / study.STUDY_REL
        if round_no != "keep" or superseded != "keep":
            if round_no != "keep":
                self.round = round_no
            if superseded != "keep":
                self.superseded = tuple(superseded)
            (d / "order_beacon.py").write_text(f"x = 1\nREGISTERED_ROUND: int | None = {self.round}\n"
                                               f"SUPERSEDED_ROUNDS = {self.superseded!r}\n")
        if draft is not None:
            (d / "prereg-draft.json").write_text(f'{{"draft": "{draft}"}}\n')
        if other is not None:
            (d / "other.txt").write_text(other + "\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)
        return git(self.repo, "rev-parse", "HEAD")

    def contains(self, commit, sha) -> bool:
        return subprocess.run(["git", "-C", str(self.repo), "merge-base", "--is-ancestor", commit, sha],
                              capture_output=True).returncode == 0


@contextlib.contextmanager
def registered_as(round_no, superseded):
    with mock.patch.object(ob, "REGISTERED_ROUND", round_no), \
            mock.patch.object(ob, "SUPERSEDED_ROUNDS", tuple(superseded)):
        yield dict(ob.registration())


def witness(sc, draft_beacon, pushes, decisions):
    with mock.patch.object(freeze, "REPO", sc.repo):
        try:
            return freeze.take_order_witness({"take_order_beacon": draft_beacon}, pushes=pushes, contains=sc.contains,
                                             decisions=decisions)
        except ValueError as e:
            return f"refused: {e}"


def burned_then_r2(*, decision="OD200", swap_draft=True):
    """None -> R0 (6190a00c's shape) -> the swap commit to R2 that adds R0's decision entry and re-derives the draft."""
    sc = BeaconScratch()
    sc.commit(round_no=None, draft="v0")
    reg0 = sc.commit(round_no=R0, draft="v1")
    entry = decision_entry(R0, reg0, decision=decision)
    swap = sc.commit(round_no=R2, superseded=(entry,), draft="v2" if swap_draft else None)
    return sc, reg0, entry, swap


T0 = ob.round_time(R0)


class TestBeaconSupersession(unittest.TestCase):
    # ------------------------------------------------------------------------------------------- history_problem
    def test_history_accepts_exactly_none_then_superseded_then_the_round(self):
        e0 = decision_entry(R0, "a" * 40)
        self.assertIsNone(ob.history_problem([None, R0, R2], R2, superseded=(e0,)))
        self.assertIsNone(ob.history_problem([None, R0, R0, R2, R2], R2, superseded=(e0,)))
        self.assertIsNotNone(ob.history_problem([None, R0, R2], R2), "a round left without an entry passes")
        for name, values, rnd in (("skipped the superseded round", [None, R2], R2),
                                  ("an unlisted round between", [None, R0, R3, R2], R2),
                                  ("back to the superseded round", [None, R2, R0], R0),
                                  ("the registered round is superseded", [None, R0], R0),
                                  ("set back to None", [None, R0, None, R2], R2)):
            with self.subTest(case=name):
                self.assertIsNotNone(ob.history_problem(values, rnd, superseded=(e0,)), name)

    def test_registration_carries_superseded_and_refuses_a_superseded_round(self):
        e0 = decision_entry(R0, "a" * 40)
        with registered_as(R2, (e0,)) as reg:
            self.assertEqual(reg["superseded"], [e0])
            self.assertEqual(ob.registered_round(reg), R2)
            for bad in ([], [dict(e0, why="rewritten")], None):
                with self.subTest(superseded=bad):
                    with self.assertRaises(ob.BeaconRefused):
                        ob.registered_round(dict(reg, superseded=bad))
        with mock.patch.object(ob, "REGISTERED_ROUND", R0), mock.patch.object(ob, "SUPERSEDED_ROUNDS", (e0,)):
            with self.assertRaises(ob.BeaconRefused):
                ob.registration()

    def test_entry_shape(self):
        good = (decision_entry(R0, "a" * 40), before_entry(R2, "b" * 40))
        self.assertEqual(ob.superseded_problems(good), [])
        bads = {"published is not the round's time": dict(good[0], published="2026-10-29T17:18:19Z"),
                "both kinds": dict(good[0], before_publication=True),
                "neither kind": {k: v for k, v in good[0].items() if k not in ("decision", "ask")},
                "an empty decision id": dict(good[0], decision=""),
                "before_publication not true": dict(good[1], before_publication=False),
                "a short registering commit": dict(good[0], registering_commit="6190a00c"),
                "an unknown key": dict(good[0], extra=1)}
        for name, bad in bads.items():
            with self.subTest(case=name):
                self.assertTrue(ob.superseded_problems((bad,)), name)
        self.assertTrue(ob.superseded_problems((good[0], good[0])), "a round superseded twice")

    def test_superseded_value_reads_the_literal(self):
        e0 = decision_entry(R0, "a" * 40)
        self.assertEqual(ob.superseded_value("x = 1\n"), ())
        self.assertEqual(ob.superseded_value(f"SUPERSEDED_ROUNDS = {(e0,)!r}\n"), (e0,))
        for bad in ("SUPERSEDED_ROUNDS = tuple()\n", "SUPERSEDED_ROUNDS = ()\nSUPERSEDED_ROUNDS = ()\n"):
            with self.assertRaises(ob.BeaconRefused):
                ob.superseded_value(bad)

    # ---------------------------------------------------------------------------------------- the witness (A, A+)
    def test_a_decision_swap_passes_and_the_new_draft_needs_its_own_lead(self):
        sc, reg0, entry, swap = burned_then_r2()
        rows = [decision_row()]
        with registered_as(R2, (entry,)) as reg:
            ok = witness(sc, reg, [(T0 - 7200, reg0), (T0 + 1000, swap)], rows)
            self.assertIsInstance(ok, dict, ok)
            self.assertEqual(ok["registering_commit"], swap)
            self.assertEqual(ok["superseded"], [{"round": R0, "swap_commit": swap, "decision": "OD200", "ask": "T199"}])
            late = ob.round_time(R2) - ob.WITNESS_LEAD_S + 10
            got = witness(sc, reg, [(T0 - 7200, reg0), (late, swap)], rows)
            self.assertIn("refused", got, "a draft pushed after r2's deadline passes")

    def test_a_second_registration_with_its_entry_passes(self):
        # plan step 5's pair: [None, 33496978, r2] was refused on the base whatever the records said, and passes now
        sc, reg0, entry, swap = burned_then_r2()
        with registered_as(R2, (entry,)) as reg:
            got = witness(sc, reg, [(T0 - 7200, reg0), (T0 + 1000, swap)], [decision_row()])
        self.assertIsInstance(got, dict, got)

    def test_before_publication_swap_needs_no_decision(self):
        sc = BeaconScratch()
        sc.commit(round_no=None, draft="v0")
        reg2 = sc.commit(round_no=R2, draft="v1")
        entry = before_entry(R2, reg2)
        swap = sc.commit(round_no=R3, superseded=(entry,), draft="v2")
        t2 = ob.round_time(R2)
        with registered_as(R3, (entry,)) as reg:
            ok = witness(sc, reg, [(t2 - 7200, reg2), (t2 - ob.SWAP_LEAD_S - 1, swap)], [])
            self.assertIsInstance(ok, dict, ok)
            self.assertEqual(ok["superseded"][0]["swap_push"], {"sha": swap, "stamp": t2 - ob.SWAP_LEAD_S - 1})
            got = witness(sc, reg, [(t2 - 7200, reg2), (t2 - ob.SWAP_LEAD_S + 1, swap)], [])
            self.assertIn("refused", got, "a swap pushed inside the lead passes with no decision")
            got = witness(sc, reg, [(t2 - 7200, reg2), (t2 + 5, swap)], [])
            self.assertIn("refused", got, "a swap pushed after the round published passes with no decision")

    def test_decision_rows_are_bound_to_the_swap(self):
        cases = {
            "OD147 (mirror-early yes, before the round)": ("OD147", [OD147]),
            "dated before the round published": ("OD200", [decision_row(created_at="2026-10-29T17:18:00Z")]),
            "outcome not the reply's key": ("OD200", [decision_row(outcome="yes")]),
            "another ask": ("OD200", [decision_row(target_id="T181")]),
            "option c (keep the old roll)": ("OD200", [decision_row(outcome="c", principal_match="beacon-r4 c")]),
            "not the principal": ("OD200", [decision_row(actor_role="chief_of_staff")]),
            "not an answer": ("OD200", [decision_row(action="ask.supersede")]),
            "no turn hash": ("OD200", [decision_row(principal_turn_sha256=None)]),
            "an id the list does not hold": ("OD999", [decision_row()]),
            "an id the list holds twice": ("OD200", [decision_row(), decision_row()]),
        }
        for name, (decision, rows) in cases.items():
            with self.subTest(case=name):
                sc, reg0, entry, swap = burned_then_r2(decision=decision)
                with registered_as(R2, (entry,)) as reg:
                    got = witness(sc, reg, [(T0 - 7200, reg0), (T0 + 1000, swap)], rows)
                self.assertIsInstance(got, str, f"A+: a decision {name} passes")
                self.assertIn("refused", got)

    def test_a_later_swap_needs_its_own_phrase(self):
        e0 = decision_entry(R0, "a" * 40)
        e2 = decision_entry(R2, "b" * 40, decision="OD201", ask="T300")
        right = decision_row(id="OD201", outcome="yes", principal_match=f"beacon-swap-{R2} yes", target_id="T300",
                             created_at=ob.published_text(R2 + 100))
        self.assertIsNone(ob.decision_problem(e2, [right], (e0, e2)))
        for name, row in (("the beacon-r4 phrase", dict(right, principal_match="beacon-r4 aplus", outcome="aplus")),
                          ("another round's phrase", dict(right, principal_match=f"beacon-swap-{R0} yes"))):
            with self.subTest(case=name):
                self.assertIsNotNone(ob.decision_problem(e2, [row], (e0, e2)), name)
        self.assertIsNotNone(ob.decision_problem(e2, [right], (e0, dict(e2), dict(e2, round=R3))),
                             "one decision cited by two entries")

    def test_entries_are_append_only_and_added_by_the_swap_commit(self):
        # an entry added in a commit after the swap
        sc = BeaconScratch()
        sc.commit(round_no=None, draft="v0")
        reg0 = sc.commit(round_no=R0, draft="v1")
        entry = decision_entry(R0, reg0)
        swap = sc.commit(round_no=R2, draft="v2")
        late = sc.commit(superseded=(entry,))
        with registered_as(R2, (entry,)) as reg:
            got = witness(sc, reg, [(T0 - 7200, reg0), (T0 + 1000, late)], [decision_row()])
        self.assertIn("refused", got, "an entry added outside its swap commit passes")
        # an entry rewritten after the swap
        sc, reg0, entry, swap = burned_then_r2()
        rewritten = dict(entry, why="a better story")
        tip = sc.commit(superseded=(rewritten,))
        with registered_as(R2, (rewritten,)) as reg:
            got = witness(sc, reg, [(T0 - 7200, reg0), (T0 + 1000, tip)], [decision_row()])
        self.assertIn("refused", got, "a rewritten entry passes")
        # an entry removed after the swap (and the round left): history no longer matches
        sc, reg0, entry, swap = burned_then_r2()
        tip = sc.commit(superseded=())
        with registered_as(R2, ()) as reg:
            got = witness(sc, reg, [(T0 - 7200, reg0), (T0 + 1000, tip)], [decision_row()])
        self.assertIn("refused", got, "a removed entry passes")

    def test_entry_registering_commit_is_the_commit_that_set_the_round(self):
        sc = BeaconScratch()
        sc.commit(round_no=None, draft="v0")
        reg0 = sc.commit(round_no=R0, draft="v1")
        entry = decision_entry(R0, "d" * 40)
        swap = sc.commit(round_no=R2, superseded=(entry,), draft="v2")
        with registered_as(R2, (entry,)) as reg:
            got = witness(sc, reg, [(T0 - 7200, reg0), (T0 + 1000, swap)], [decision_row()])
        self.assertIn("refused", got)

    def test_a_superseding_registration_only_on_a_mirror_branch_is_refused(self):
        sc = BeaconScratch()
        sc.commit(round_no=None, draft="v0")
        reg0 = sc.commit(round_no=R0, draft="v1")
        tip = sc.commit(other="main moves on")
        git(sc.repo, "checkout", "-q", "-b", "cand", reg0)
        entry = decision_entry(R0, reg0)
        cand = sc.commit(round_no=R2, superseded=(entry,), draft="v2")
        git(sc.repo, "checkout", "-q", "main")
        with registered_as(R2, (entry,)) as reg:
            got = witness(sc, reg, [(T0 - 7200, tip), (T0 + 1000, cand)], [decision_row()])
        self.assertIn("refused", got)

    # ---------------------------------------------------------------------------------------------- m1's words
    def test_the_rule_texts_say_the_true_push_rule(self):
        for name, text in (("SEED_RULE", ob.SEED_RULE), ("residual", ob.residual()),
                           ("REGISTRATION_ORDER", " ".join(ob.REGISTRATION_ORDER))):
            with self.subTest(text=name):
                self.assertNotIn("that push is the mirror of a verified wave", text)
                self.assertNotIn("witnessing pushes are mirrors of verified", text)
                self.assertIn("passed the whole athena battery", text)
                self.assertIn("a push Javier named by a recorded word", text)
                self.assertIn("mirror every verified gap study wave", text)
        self.assertIn("superseded", ob.residual())
        self.assertIn("SUPERSEDED_ROUNDS", " ".join(ob.REGISTRATION_ORDER))

    def test_the_branch_registers_nothing(self):
        # lane fold2/lc's swap commit (option A+, OD160): R0 is superseded by ENTRY_33496978, in this commit, and the
        # registered round is r2; the entry is the literal above, byte for byte
        self.assertEqual(ob.REGISTERED_ROUND, 33536472)
        self.assertEqual(ob.SUPERSEDED_ROUNDS, (ENTRY_33496978,))
        self.assertEqual(ob.published_text(R0), "2026-10-29T17:18:18Z")


READING_ROUND = 33356692   # drand quicknet round 33356692 as the relays answered it (test_pf1_freeze_gates' ROUND)
READING = {"chain_hash": ob.CHAIN["chain_hash"], "round": READING_ROUND, "round_time": 1792873440,
           "randomness": "ba6557025dd415aa63a9247283a8d471e877b8f9ab51d18acaf84abdbdcd53db",
           "signature": "923de5ea6ff8d8702585b65f992a8a991da6a8d37f6b8d9e6817b5be0b27b75c"
                        "93d944a935689e1eec7985c5fb782ffc", "relays": list(ob.RELAYS)}


def frozen_with(order_fn=None):
    """A frozen-file fragment over the committed draft's first 40 rows, its order made by freeze.planned_order (or
    `order_fn`) from the reading's seed."""
    import copy
    import json
    rows = json.loads((HERE / "prereg-draft.json").read_text())["rows"][:40]
    seed = ob.seed(READING)
    order = (order_fn or freeze.planned_order)({"rows": copy.deepcopy(rows)}, seed)
    return {"rows": rows, "take_order_seed": seed, "take_order_beacon_reading": dict(READING), "take_order": order,
            "take_order_beacon": registered_beacon()}


DRAFT_STUB = {"take_order_beacon": {"round": READING_ROUND}}    # R-2: the draft whose round these frozen files hold


def top(frozen):
    import check_results as cr
    return cr.take_order_problems(frozen, draft=DRAFT_STUB)


class TestTakeOrderRecompute(unittest.TestCase):
    def test_an_honest_order_passes(self):
        import check_results as cr
        self.assertEqual(top(frozen_with()), [])

    def test_a_monkey_patched_helper_is_caught_while_the_hash_stands(self):
        import json
        import check_results as cr
        before = freeze.take_order_function_sha256()
        real = json.dumps
        # the reviewer's re-check road 1: a module-level patch of json.dumps in a study file, in force in every process
        # that imports it (the freeze's and, here, the checker's own)
        with mock.patch.object(json, "dumps", lambda v, **k: real(v, **dict(k, sort_keys=True, indent=1))):
            frozen = frozen_with()
            self.assertEqual(freeze.take_order_function_sha256(), before, "the hash does not see the patch")
            got = top(frozen)
        self.assertNotEqual(frozen["take_order"], frozen_with()["take_order"], "the patch changed the order")
        self.assertTrue(got and "take_order" in got[0], f"ORDER: a patched order passes: {got}")

    def test_the_seed_and_reading_are_recomputed_too(self):
        import check_results as cr
        bad = dict(frozen_with(), take_order_seed="0" * 40)
        self.assertTrue(top(bad))
        bad = frozen_with()
        bad["take_order_beacon_reading"] = dict(READING, randomness="0" * 64)
        self.assertTrue(top(bad))
        bad = frozen_with()
        bad["take_order"] = list(reversed(bad["take_order"]))
        self.assertTrue(top(bad))
        self.assertTrue(top({"rows": []}), "a frozen file with no order is refused")

    def test_the_recompute_reads_no_study_module(self):
        import check_results as cr
        src = cr.ORDER_REFERENCE_FILE.read_text()
        self.assertNotIn("import freeze", src)
        self.assertNotIn("sys.path", src)
        for flag in ("-I", "-S"):
            self.assertIn(flag, cr.ORDER_REFERENCE_ARGV)
        self.assertIn(str(cr.ORDER_REFERENCE_FILE), cr.ORDER_REFERENCE_ARGV)

    def test_publication_reads_it(self):
        import inspect
        import check_results as cr
        self.assertIn("take_order_problems(frozen)", inspect.getsource(cr.check_frozen_content))


DECISION_LOG = Path("/Users/javrodher/glitch/workspaces/aegis/orgos/records/decision.jsonl")
# sha256 of decision.jsonl line 160 with its newline (`sed -n 160p decision.jsonl | shasum -a 256`, 29 Oct 2026)
OD160_SHA256 = "295e85ece9cd78f727cda5b79263cc41dd3e838b62e4bdfb04855b299a050bc0"
ENTRY_33496978 = {
    "round": 33496978, "published": "2026-10-29T17:18:18Z",
    "registering_commit": "6190a00cf322432bc4ec8b12e03adb3fbbd315b2",
    "push": "gars-cloud-mirror freeze/r4-20261021, branch_creation 2026-10-29T14:12:25Z, under OD147",
    "why": "0f634fc3 (pre-freeze review 2): DO NOT FREEZE; MAJORs 1-2 change the draft after the round's push "
           "deadline (2026-10-29T16:18:18Z)",
    "record": "6190a00c, the last commit to change the draft and the one that set the round, was pushed under "
              "Javier's recorded word OD147 before its athena battery, which then failed one test-only check (fixed "
              "in 1533750a and ef31e4a9, neither of which changed the draft or order_beacon.py); ef31e4a9 passed the "
              "whole battery. The round's order can be computed by anyone with prereg.py --order <seed of round "
              "33496978> against prereg-draft.json at 6190a00c (byte-identical at ef31e4a9); no record shows anyone "
              "in the study computed it.",
    "decision": "OD160", "ask": "T199"}


class TestOD160(unittest.TestCase):
    def rows(self):
        import json
        return [json.loads(ln) for ln in (HERE / ob.OWNER_DECISIONS).read_text().splitlines() if ln.strip()]

    def test_the_committed_row_is_decision_log_line_160_byte_for_byte(self):
        data = (HERE / ob.OWNER_DECISIONS).read_bytes()
        self.assertEqual(data.count(b"\n"), 1, "one row, newline-terminated")
        self.assertEqual(hashlib.sha256(data).hexdigest(), OD160_SHA256)
        if DECISION_LOG.is_file():      # the private log, on the Mac only
            line = DECISION_LOG.read_bytes().split(b"\n")[159]
            self.assertEqual(line + b"\n", data)

    def test_the_prepared_entry_is_well_formed_and_od160_binds_it(self):
        self.assertEqual(ob.superseded_problems((ENTRY_33496978,)), [])
        self.assertIsNone(ob.decision_problem(ENTRY_33496978, self.rows(), (ENTRY_33496978,)))
        self.assertEqual(freeze.owner_decisions(), self.rows())

    def test_a_swap_commit_with_the_entry_passes_the_witness(self):
        # the swap commit's shape (L-C's): REGISTERED_ROUND leaves 33496978 for a later round and adds the entry
        sc = BeaconScratch()
        sc.commit(round_no=None, draft="v0")
        reg0 = sc.commit(round_no=R0, draft="v1")
        entry = dict(ENTRY_33496978, registering_commit=reg0)
        swap = sc.commit(round_no=R2, superseded=(entry,), draft="v2")
        with registered_as(R2, (entry,)) as reg:
            got = witness(sc, reg, [(T0 - 7200, reg0), (T0 + 1000, swap)], self.rows())
        self.assertIsInstance(got, dict, got)
        self.assertEqual(got["superseded"][0]["decision"], "OD160")


# ------------------------------------------------------------------------------------------------ the orchestrator
class TestOrchMJ3LooseRuling(unittest.TestCase):
    """The review's probe1 shapes: a refusing line that is not byte-canonical beside a canonical DO FREEZE line (often
    in a fence quoting the gate) read DO FREEZE. Each must read anything but DO FREEZE."""

    SHAPES = {
        "trailing space": f"x\n{DO_NOT} \n```\n{DO}\n```\n",
        "emphasis moved": f"x\nRuling: **DO NOT FREEZE.**\n```\n{DO}\n```\n",
        "heading": f"## Ruling: DO NOT FREEZE\n```\n{DO}\n```\n",
        "NBSP": f"**Ruling: DO NOT\u00a0FREEZE.**\n```\n{DO}\n```\n",
        "zero-width": f"**Ruling: DO NOT\u200b FREEZE.**\n{DO}\n",
        "lower case": f"**Ruling: do not freeze.**\n{DO}\n",
        "an earlier report's line quoted": f"> {DO_NOT}\n{DO}\n",
        "two DO FREEZE-like lines": f"{DO}\nRuling: DO FREEZE\n",
    }

    def test_each_loose_shape_is_not_do_freeze(self):
        for name, text in self.SHAPES.items():
            with self.subTest(shape=name):
                self.assertEqual(freeze.read_ruling(text), freeze.AMBIGUOUS, f"MJ-3: {name}")

    def test_the_canonical_lines_alone_still_read(self):
        self.assertEqual(freeze.read_ruling(f"x\n{DO}\nThe freeze may proceed.\n"), "DO FREEZE")
        self.assertEqual(freeze.read_ruling(f"x\n{DO_NOT}\n"), "DO NOT FREEZE")
        # a sentence about freezing that is no ruling line does not count
        self.assertEqual(freeze.read_ruling(f"{DO}\nNothing found blocks the freeze; do not delay it.\n"),
                         "DO FREEZE")

    def test_the_quoted_shape_is_now_ambiguous(self):
        self.assertEqual(freeze.read_ruling(report("0" * 64, *QUOTED)), freeze.AMBIGUOUS)


class TestOrchMJ1MergeFirstParent(unittest.TestCase):
    """The review's probe5: commit-tree <T's tree> -p X -p T puts the pushed, abandoned outcome X on HEAD's first-parent
    line and resets the ledger to T, so the re-run Y read as the only outcome."""

    def scratch(self):
        sc = LedgerScratch()
        t = sc.append("takes.json", {"slot": "s1", "attempt": 1}, "reg")
        x = sc.append("outcomes.json", {"o": "bad"}, "outcome X (pushed)")
        tree = git(sc.repo, "rev-parse", f"{t}^{{tree}}")
        m = git(sc.repo, "commit-tree", tree, "-p", x, "-p", t, "-m", "merge: tree of T, X first parent")
        git(sc.repo, "reset", "-q", "--hard", m)
        y = sc.append("outcomes.json", {"o": "good"}, "rerun Y")
        return sc, x, y

    def test_the_witness_refuses_it(self):
        sc, x, y = self.scratch()
        problems, _, _ = sc.check([(1, x), (2, y)])
        self.assertTrue(problems, "MJ-1: the first-parent reset merge passes the witness")

    def test_read_history_refuses_it(self):
        import takes
        sc, x, y = self.scratch()
        # batch's record-shape check stood in: the git reading is under test, and these records are synthetic
        with mock.patch.object(takes.batch.Batch, "history_problems", staticmethod(lambda history: [])):
            with self.assertRaises(ValueError, msg="MJ-1: read_history reads the re-run as the only outcome"):
                takes.read_history(root=sc.dir, repo=sc.repo)
            # a plain append-only history still reads
            plain = LedgerScratch()
            plain.append("takes.json", {"slot": "s1", "attempt": 1}, "reg")
            plain.append("outcomes.json", {"o": 1}, "outcome")
            self.assertEqual(takes.read_history(root=plain.dir, repo=plain.repo), [{"o": 1}])

    def test_a_linear_rewrite_on_the_run_line_is_refused_by_the_witness(self):
        sc = LedgerScratch()
        x = sc.append("outcomes.json", {"o": "bad"}, "outcome X")
        (sc.dir / "outcomes.json").write_text('[{"o": "good"}]\n')
        git(sc.repo, "commit", "-qam", "rewrite in place")
        problems, _, _ = sc.check([(1, x)])
        self.assertTrue(problems and any("append-only" in p for p in problems), problems)

    def test_a_merge_that_does_not_touch_the_ledger_passes(self):
        sc = LedgerScratch()
        r1 = sc.append("takes.json", {"slot": "s1", "attempt": 1}, "reg")
        git(sc.repo, "checkout", "-q", "-b", "side")
        (sc.dir / "notes.txt").write_text("side\n")
        git(sc.repo, "add", "-A")
        git(sc.repo, "commit", "-qm", "side note")
        git(sc.repo, "checkout", "-q", "main")
        git(sc.repo, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        problems, _, _ = sc.check([(1, git(sc.repo, "rev-parse", "HEAD"))])
        self.assertEqual(problems, [])


class TestOrchMN3Decision(unittest.TestCase):
    def rows(self, *extra):
        import json
        base = [json.loads(ln) for ln in (HERE / ob.OWNER_DECISIONS).read_text().splitlines() if ln.strip()]
        return base + list(extra)

    def test_a_later_supersession_or_answer_or_expiry_refuses(self):
        od160 = self.rows()[0]
        later = dict(od160, id="OD161", outcome="c", principal_match="beacon-r4 c", supersedes_id="OD160",
                     created_at="2026-10-30T09:00:00Z")
        reanswer = dict(od160, id="OD162", outcome="a", principal_match="beacon-r4 a",
                        created_at="2026-10-30T10:00:00Z")
        withdraw = dict(od160, id="OD163", action="ask.supersede", actor_role="chief_of_staff", outcome=None,
                        principal_match=None, created_at="2026-10-30T11:00:00Z")
        for name, rows in (("superseded by a later row", self.rows(later)),
                           ("the ask answered again later", self.rows(reanswer)),
                           ("the ask withdrawn later", self.rows(withdraw))):
            with self.subTest(case=name):
                self.assertIsNotNone(ob.decision_problem(ENTRY_33496978, rows, (ENTRY_33496978,)), f"mn-3: {name}")
        expired = [dict(od160, expires_at="2026-10-30T00:00:00Z")]
        self.assertIsNotNone(ob.decision_problem(ENTRY_33496978, expired, (ENTRY_33496978,),
                                                 now=ob._utc("2026-10-31T00:00:00Z")), "mn-3: expired")
        self.assertIsNone(ob.decision_problem(ENTRY_33496978, self.rows(), (ENTRY_33496978,)))


def registered_beacon(round_no=READING_ROUND):
    return {"round": round_no, "chain_hash": ob.CHAIN["chain_hash"], "genesis_time": ob.CHAIN["genesis_time"],
            "period_s": ob.CHAIN["period_s"]}


class TestOrchMN1MN2Recompute(unittest.TestCase):
    def frozen(self, **edits):
        f = dict(frozen_with(), take_order_beacon=registered_beacon())
        f.update(edits)
        return f

    def test_a_reading_of_another_round_is_refused(self):
        import copy
        import hashlib as h
        import check_results as cr
        sig = "ab" * 48
        other = dict(READING, round=READING_ROUND + 7, round_time=READING["round_time"] + 21, signature=sig,
                     randomness=h.sha256(bytes.fromhex(sig)).hexdigest())
        seed = ob.seed(other)
        rows = self.frozen()["rows"]
        forged = self.frozen(take_order_beacon_reading=other, take_order_seed=seed,
                             take_order=freeze.planned_order({"rows": copy.deepcopy(rows)}, seed))
        self.assertTrue(top(forged), "mn-1: a reading of another round passes")
        for key, value in (("chain_hash", "0" * 64), ("round_time", READING["round_time"] + 1)):
            with self.subTest(field=key):
                bad = self.frozen(take_order_beacon_reading=dict(READING, **{key: value}))
                self.assertTrue(top(bad), f"mn-1: a reading with another {key} passes")
        self.assertEqual(top(self.frozen()), [])

    def test_the_verdict_is_a_standalone_isolated_file(self):
        import ast
        import json
        src = (HERE / "order_reference.py").read_text()
        imports = {a.name for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.Import, ast.ImportFrom))
                   for a in getattr(n, "names", [])}
        self.assertLessEqual(imports, {"hashlib", "json", "sys"}, imports)
        with tempfile.TemporaryDirectory() as tmp:
            for name, frozen, want in (("honest", self.frozen(), 0),
                                       ("reversed", self.frozen(take_order=list(reversed(frozen_with()["take_order"]))),
                                        1)):
                f = Path(tmp) / f"{name}.json"
                f.write_text(json.dumps(frozen))
                d = Path(tmp) / "draft.json"
                d.write_text(json.dumps(DRAFT_STUB))
                got = subprocess.run([sys.executable, "-I", "-S", str(HERE / "order_reference.py"), str(f), str(d)],
                                     capture_output=True, text=True)
                self.assertEqual(got.returncode, want, got.stdout + got.stderr)
                self.assertIn("order_reference:", got.stdout)


class TestOrchMJ2PublicationWitness(unittest.TestCase):
    def setup(self, *, problems=(), stale=False, record=True):
        import json
        sc = LedgerScratch()
        r1 = sc.append("takes.json", {"slot": "s1", "attempt": 1}, "reg")
        if record:
            entry = {"at": "2026-10-30T12:00:00Z", "head": r1, "ledger_head": r1, "ledger_commits": 1,
                     "unwitnessed": [], "problems": list(problems)}
            (sc.dir / "witness-record.json").write_text(json.dumps([entry]) + "\n")
            git(sc.repo, "add", "-A")
            git(sc.repo, "commit", "-qm", "witness record")
        if stale:
            sc.append("outcomes.json", {"slot": "s1"}, "outcome after the record")
        return sc

    def problems(self, sc):
        import check_results as cr
        with mock.patch.object(cr, "REPO", sc.repo), mock.patch.object(cr, "HERE", sc.dir):
            return cr.witness_publication_problems()

    def test_publication_needs_a_current_clean_record(self):
        self.assertEqual(self.problems(self.setup())[0], [])
        for name, kw in (("no record", {"record": False}), ("a record with problems", {"problems": ["x"]}),
                         ("a ledger commit after the record", {"stale": True})):
            with self.subTest(case=name):
                self.assertTrue(self.problems(self.setup(**kw))[0], f"MJ-2: publication passes with {name}")

    def test_witness_record_appends_a_run_and_fails_closed(self):
        import json
        import check_results as cr
        sc = LedgerScratch()
        r1 = sc.append("takes.json", {"slot": "s1", "attempt": 1}, "reg")
        for pushes, code in (([(1, r1)], 0), ([(1, "1" * 40)], 1)):
            out = io.StringIO()
            with mock.patch.object(cr, "REPO", sc.repo), mock.patch.object(cr, "HERE", sc.dir), \
                    mock.patch.object(freeze, "push_records", lambda p=pushes: p), contextlib.redirect_stdout(out):
                self.assertEqual(cr.main(["--witness", "--record"]), code, out.getvalue())
        runs = json.loads((sc.dir / "witness-record.json").read_text())
        self.assertEqual(len(runs), 2)
        self.assertEqual((runs[0]["problems"], runs[0]["ledger_head"]), ([], r1))
        self.assertTrue(runs[1]["problems"])

    def test_result_prints_the_count_and_publication_reads_the_gate(self):
        import inspect
        import result
        text = result.render_witness({"at": "2026-10-30T12:00:00Z", "ledger_commits": 9,
                                      "unwitnessed": ["a" * 40, "b" * 40], "problems": []})
        self.assertIn("9 take-ledger commit(s)", text)
        self.assertIn("2 unwitnessed", text)
        self.assertIn("witness_publication_problems", inspect.getsource(result.main))
        import check_results as cr
        self.assertIn("witness_publication_problems", inspect.getsource(cr.main))
        self.assertIn("witness-record.json", " ".join(str(p) for p in cr.RUNTIME_PATHS))


class TestOrchMN5LocalLint(unittest.TestCase):
    def test_the_publication_check_runs_the_section_lints_without_allow_absent(self):
        import inspect
        import check_results as cr
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "EVALS.md"
            page.write_text("no section\n")
            self.assertTrue(cr.section_lint_problems(page), "mn-5: an absent section passes publication")
            page.write_text(f"{study.SUMMARY_START}\nA plain sentence.\n{study.SUMMARY_END}\n")
            self.assertEqual(cr.section_lint_problems(page), [])
        self.assertIn("section_lint_problems(", inspect.getsource(cr.main))


class TestRecheckR1WitnessRecord(TestOrchMJ2PublicationWitness):
    """probe7: a hand-written clean record with false counts passed, and so did one only in the working tree."""

    def test_false_counts_are_refused(self):
        import json
        sc = LedgerScratch()
        r1 = sc.append("takes.json", {"slot": "s1", "attempt": 1}, "reg")
        x = sc.append("outcomes.json", {"o": 1}, "X")
        for name, edits in (("ledger_commits 0", {"ledger_commits": 0}),
                            ("an unwitnessed sha not on the ledger", {"unwitnessed": ["1" * 40]})):
            with self.subTest(case=name):
                entry = dict({"at": "2026-10-30T12:00:00Z", "head": x, "ledger_head": x, "ledger_commits": 2,
                              "unwitnessed": [], "problems": []}, **edits)
                (sc.dir / "witness-record.json").write_text(json.dumps([entry]) + "\n")
                git(sc.repo, "add", "-A")
                git(sc.repo, "commit", "-qm", f"record: {name}")
                self.assertTrue(self.problems(sc)[0], f"R-1: a record with {name} passes")
        entry = {"at": "2026-10-30T12:00:00Z", "head": x, "ledger_head": x, "ledger_commits": 2,
                 "unwitnessed": [r1], "problems": []}
        (sc.dir / "witness-record.json").write_text(json.dumps([entry]) + "\n")
        git(sc.repo, "add", "-A")
        git(sc.repo, "commit", "-qm", "record: true counts")
        self.assertEqual(self.problems(sc)[0], [])

    def test_a_record_only_in_the_working_tree_is_not_read(self):
        import json
        sc = self.setup(record=False)
        r1 = git(sc.repo, "rev-parse", "HEAD")
        entry = {"at": "2026-10-30T12:00:00Z", "head": r1, "ledger_head": r1, "ledger_commits": 1,
                 "unwitnessed": [], "problems": []}
        (sc.dir / "witness-record.json").write_text(json.dumps([entry]) + "\n")     # never committed
        self.assertTrue(self.problems(sc)[0], "R-1: an uncommitted record passes")


class TestRecheckR2PinnedChain(TestOrchMN1MN2Recompute):
    def run_ref(self, frozen, draft):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            f, d = Path(tmp) / "frozen.json", Path(tmp) / "draft.json"
            f.write_text(json.dumps(frozen))
            d.write_text(json.dumps(draft))
            return subprocess.run([sys.executable, "-I", "-S", str(HERE / "order_reference.py"), str(f), str(d)],
                                  capture_output=True, text=True)

    def consistent(self, beacon_edits, reading_edits):
        import copy
        reading = dict(READING, **reading_edits)
        seed = ob.seed(reading)
        rows = frozen_with()["rows"]
        return dict(frozen_with(), take_order_beacon=dict(registered_beacon(), **beacon_edits),
                    take_order_beacon_reading=reading, take_order_seed=seed,
                    take_order=freeze.planned_order({"rows": copy.deepcopy(rows)}, seed))

    def test_a_self_consistent_frozen_file_off_quicknet_or_the_draft_is_refused(self):
        draft = {"take_order_beacon": {"round": READING_ROUND}}
        self.assertEqual(self.run_ref(self.frozen(), draft).returncode, 0)
        cases = {
            "another chain": self.consistent({"chain_hash": "0" * 64}, {"chain_hash": "0" * 64}),
            "a shifted genesis": self.consistent({"genesis_time": ob.CHAIN["genesis_time"] + 3},
                                                 {"round_time": READING["round_time"] + 3}),
            "round and reading moved together": self.consistent({"round": READING_ROUND + 1},
                                                                {"round": READING_ROUND + 1,
                                                                 "round_time": READING["round_time"] + 3}),
        }
        for name, frozen in cases.items():
            with self.subTest(case=name):
                got = self.run_ref(frozen, draft)
                self.assertEqual(got.returncode, 1, f"R-2: {name} passes: {got.stdout}")

    def test_the_pinned_chain_is_quicknet(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("order_reference_t", HERE / "order_reference.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual((mod.CHAIN_HASH, mod.GENESIS_TIME, mod.PERIOD_S),
                         (ob.CHAIN["chain_hash"], ob.CHAIN["genesis_time"], ob.CHAIN["period_s"]))


class TestRecheckR3FencedRuling(unittest.TestCase):
    WORDINGS = ("Ruling is: DO NOT FREEZE.", "The ruling here is DO NOT FREEZE.", "**Verdict: DO NOT FREEZE.**",
                "**Rule: DO NOT FREEZE.**", "**Ruling: DON'T FREEZE.**", "**Ruling:**\nDO NOT FREEZE.",
                "**Ruling: DO N\u041eT FREEZE.**", "**Ruling: DO NOT\u2028FREEZE.**")

    def test_a_refusal_beside_a_fenced_or_quoted_canonical_line_is_ambiguous(self):
        for wording in self.WORDINGS:
            for carrier in (f"```\n{DO}\n```", f"~~~\n{DO}\n~~~", f"> {DO}", f">{DO}", f"> > {DO}"):
                with self.subTest(wording=wording, carrier=carrier):
                    text = f"x\n{wording}\n\nThe gate reads:\n{carrier}\n"
                    self.assertEqual(freeze.read_ruling(text), freeze.AMBIGUOUS, "R-3")

    def test_a_genuine_line_beside_prose_still_reads(self):
        self.assertEqual(freeze.read_ruling(f"{DO}\nRound 2's ruling was DO NOT FREEZE.\n"), "DO FREEZE")
        self.assertEqual(freeze.read_ruling(f"{DO}\nRound 2 ruled: DO NOT FREEZE.\n"), "DO FREEZE")
        self.assertEqual(freeze.read_ruling(f"x\n{DO}\n"), "DO FREEZE")
        self.assertEqual(freeze.read_ruling(f"x\n{DO_NOT}\n"), "DO NOT FREEZE")


class TestRecheckR4TimelessRow(TestOrchMN3Decision):
    def test_a_same_ask_row_with_no_readable_time_refuses(self):
        od160 = self.rows()[0]
        for created in (None, "", "not a time"):
            with self.subTest(created_at=created):
                other = dict(od160, id="OD170", created_at=created)
                self.assertIsNotNone(ob.decision_problem(ENTRY_33496978, self.rows(other), (ENTRY_33496978,)),
                                     "R-4")


if __name__ == "__main__":
    unittest.main(verbosity=2)
