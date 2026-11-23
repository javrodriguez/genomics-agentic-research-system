#!/usr/bin/env python3
"""Lane gap-live-box (Gap Study round 4; glitch-45, the Lane-orchestrator, Wed 28 Oct 2026, under Javier's standing
delegation; design LIVE-BOX-TAKE-DESIGN-20261028 section 6 B1 and section 7, rulings R1-R5): the live-box probe
(live_box_cut.py), freeze_rehearsal's live-box step, and the battery step's time limit.

  T1.not-rehearsed  freeze_rehearsal with no --live-box-record: the step "live-box: forced-timeout claude-code take"
                    follows the take-order beacon step, reads [1] NOT REHEARSED: LIVE_BOX_REQUIRED, and the rehearsal
                    is NOT all green while every other step is green. Witnesses: live-box-not-appended,
                    live-box-default-green.
  T2.record         one red per clause, each named by its own reason: end not timed-out; exit not 124; harness not
                    claude-code; a file changed by one byte; a file planted beside the named ones; the adapter digest
                    and the checker digest not this tree's; content problems non-empty (a rewrite before the record in
                    flight); a torn session line; a shape outside the bound (two units past the stream, and a forged
                    shape); an extra key; a relative path and a record inside the repository (freeze_rehearsal refuses
                    both before anything runs, exit 2, and so does the verifier); a pass line naming another record's
                    sha256. Witnesses: end-unchecked, exit-unchecked, harness-unchecked, file-sha-unchecked,
                    files-extra-admitted, adapter-unchecked, checker-digest-unchecked, content-unchecked,
                    torn-unchecked, shape-unchecked, extra-key-admitted, relative-admitted, in-repo-admitted,
                    rehearsal-in-repo-admitted, live-box-sha-unbound.
  T3.good           records built over synthetic cut folders (copies of the committed arm A Haiku walks w001, two turns, and w285, one, the last turn
                    marked cut, in the pf1-l3 shapes: equal, the session lagging, the stream lagging by one unit) verify
                    clean with their shape, and freeze_rehearsal given one reads the step [0] and "all green" when every
                    other step is green.
  T4.no-path        the written report and stdout hold no absolute path of the record or its folder, on a pass and on
                    a verifier whose output names the path. Witness: live-box-path-echoed.
  T5.commands       freeze_rehearsal.COMMANDS is byte-equal to its value at e3aa853c (sha256 of its lines pinned), and
                    the live-box step is not one of them.
  T6.probe          live_box_cut's refusals before anything is built (exit 2, the walk runner never called): a
                    prereg.json present; B at and above the registered budget, and B 0; a run token's path in the
                    builders; a login other than the claude1 walk login; the records clone; a clone with a remote;
                    a walk id that is not lb<number>; and gap_shape over equal, session-lags-k, stream-lags-1 and
                    outside. The probe end to end on a scratch repository with a fake walk runner that commits a cut
                    folder: exit 0 with the record and its files written (closed keys, no transcript text), exit 3 when
                    no turn is cut, exit 4 on a finding. Witnesses: prereg-admitted, budget-at-registered-admitted,
                    token-unchecked, login-unchecked, records-clone-admitted, remote-admitted, gap-outside-unread.
  T7.timeout        the test_round4.py step's limit is run_checks.timeout_for("test_round4") (18000 s), one source
                    (a changed run_checks limit reaches it), every other step 3600 s; run_step hands sh that limit; a
                    step that times out names its limit in its tail. Witnesses: step-timeout-flat,
                    run-step-default-timeout.

Synthetic and copied records only: no walk, model, container, network, login or spend. The scratch repositories and
copies live in temporary folders outside the study and are removed.

--mutant NAME compiles one altered module in memory before the bound test runs; --witnesses runs every registered
mutant in its own process, only its bound test, and requires that test to fail by an AssertionError carrying its
clause token, with no error.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SELECTED = None
MODS: dict = {}
WALKS = HERE / "rehearsals"
WALK = WALKS / "w001"           # a committed two-turn claude-code walk (arm A Haiku), read only
FIXTURE_NAMES = ("driver-ledger.json", "transcript.jsonl", "turn-1.jsonl", "turn-1.jsonl.launch.json",
                 "turn-2.jsonl", "turn-2.jsonl.launch.json")
COMMANDS_SHA256_E3AA853C = "d35a9676d51340c3c05a3a99981274c7c31589d72bf9d0cc0cd4652a782df206"
SHA = "d" * 40
BUDGET = 20


def mutants():
    """name -> (clause, target module, old text, new text). Each weakens one guard; old must occur exactly once."""
    fr, lb = "freeze_rehearsal", "live_box_cut"
    return {
        "live-box-not-appended": ("T1.not-rehearsed", fr, "        steps.append((LIVE_BOX_STEP, *live_box))\n", ""),
        "live-box-default-green": ("T1.not-rehearsed", fr, "    live_box = (1, LIVE_BOX_NOT_REHEARSED)\n",
                                   "    live_box = (0, LIVE_BOX_NOT_REHEARSED)\n"),
        "end-unchecked": ("T2.record", lb, '    if rec["ledger_end"] != CUT_END:', "    if False:"),
        "exit-unchecked": ("T2.record", lb, '    if rec["ledger_exit"] != CUT_EXIT:', "    if False:"),
        "harness-unchecked": ("T2.record", lb, '    if rec["harness"] != HARNESS:', "    if False:"),
        "file-sha-unchecked": ("T2.record", lb, "or sha256_bytes(f.read_bytes()) != want:", "or False:"),
        "files-extra-admitted": ("T2.record", lb, "    if on_disk != sorted(files):", "    if False:"),
        "adapter-unchecked": ("T2.record", lb,
                              '    if rec["adapter_sha256"] != sha256_bytes((HERE / "claude_code_adapter.py")',
                              '    if False and rec["adapter_sha256"] != sha256_bytes((HERE / "claude_code_adapter.py")'),
        "checker-digest-unchecked": ("T2.record", lb,
                                     '    if rec["checker_digest"] != check_take.checker_constants_sha256():',
                                     "    if False:"),
        "content-unchecked": ("T2.record", lb, '    if got["content_problems"]["count"]:', "    if False:"),
        "torn-unchecked": ("T2.record", lb, '    if got["session_torn"]:', "    if False:"),
        "shape-unchecked": ("T2.record", lb, '            and IN_BOUND.fullmatch(gap["shape"])):',
                            "            and True):"),
        "extra-key-admitted": ("T2.record", lb, "    if not isinstance(rec, dict) or set(rec) != set(KEYS):",
                               "    if not isinstance(rec, dict) or not set(KEYS) <= set(rec):"),
        "relative-admitted": ("T2.record", lb, '        return None, ["the record path is not absolute"]',
                              "        pass"),
        "in-repo-admitted": ("T2.record", lb, '        return None, ["the record is inside the repository"]',
                             "        pass"),
        "rehearsal-in-repo-admitted": ("T2.record", fr,
                                       '        return "--live-box-record is inside this repository; the probe\'s',
                                       '        return None and "--live-box-record is inside this repository; the probe\'s'),
        "live-box-sha-unbound": ("T2.record", fr, "    if code == 0 and ok and ok.group(1) == record_sha:",
                                 "    if code == 0 and ok:"),
        "live-box-path-echoed": ("T4.no-path", fr, "    return 1, (f\"live-box record {record_sha}: the verifier's",
                                 "    return 1, last + (f\"live-box record {record_sha}: the verifier's"),
        "prereg-admitted": ("T6.probe", lb, '        if (repo / study.rel("prereg.json")).exists():\n            raise',
                            '        if False:\n            raise'),
        "budget-at-registered-admitted": ("T6.probe", lb, "    if budget >= registered:", "    if budget > registered:"),
        "token-unchecked": ("T6.probe", lb, "    if any(s in tokens or any(t in s for t in tokens)",
                            "    if False and any(s in tokens or any(t in s for t in tokens)"),
        "login-unchecked": ("T6.probe", lb, '    if builders.get("login_path") != want:', "    if False:"),
        "records-clone-admitted": ("T6.probe", lb, '    if any("gap4-walk-records" in part for part in where.parts):',
                                   "    if False:"),
        "remote-admitted": ("T6.probe", lb, '    if git(where, "remote"):', "    if False:"),
        "gap-outside-unread": ("T6.probe", lb, "    if cca.cut_tail_problem(stream, sess) is not None:\n        return OUTSIDE",
                               "    if False:\n        return OUTSIDE"),
        "cli-version-unchecked": ("T2.record", lb, '    elif rec["cli_version"] != pins:', "    elif False:"),
        "pin-unread-admitted": ("T2.record", lb, "    if pins is None:\n", "    if False:\n"),
        "ledger-binding-unchecked": ("T2.record", lb,
                                     "        out.append(\"the ledger's budget, arm, model or harness is not the record's\")",
                                     "        pass"),
        "dirty-admitted": ("T6.probe", lb, '    if git(where, "status", "--porcelain", "--untracked-files=all"):',
                           "    if False:"),
        "child-repo-admitted": ("T6.probe", lb,
                                '    if where.name == "repo" and re.fullmatch(r"w-[A-Za-z0-9]{8}", where.parent.name):',
                                "    if False:"),
        "finding-after-cut": ("T6.probe", lb, "    why = finding(record)\n",
                              '    why = finding(record) if record["cut_turns"] else []\n'),
        "close-sha-unchecked": ("T2.record", fr, "            if live_box_sha != args.live_box_sha256:",
                                "            if False:"),
        "sha-prefix-only": ("T2.record", fr, "            if live_box_sha != args.live_box_sha256:",
                            "            if live_box_sha[:1] != args.live_box_sha256[:1]:"),
        "close-sha-optional": ("T2.record", fr, "        if not (isinstance(args.live_box_sha256, str)",
                               "        if False and not (isinstance(args.live_box_sha256, str)"),
        "step-timeout-flat": ("T7.timeout", fr,
                              '    return run_checks.timeout_for("test_round4") if script == "test_round4.py" else '
                              'STEP_TIMEOUT_S', "    return STEP_TIMEOUT_S"),
        "run-step-default-timeout": ("T7.timeout", fr,
                                     "    return sh(command, clone, env=step_environment(), timeout=step_timeout(command))",
                                     "    return sh(command, clone, env=step_environment())"),
    }


def compile_module(name: str, source: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


def setUpModule():
    for name in ("live_box_cut", "freeze_rehearsal", "run_checks"):
        MODS[name] = __import__(name)
    if SELECTED is None:
        return
    _, target, old, new = mutants()[SELECTED]
    text = (HERE / f"{target}.py").read_text()
    assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
    MODS[target] = compile_module(target, text.replace(old, new))


def tearDownModule():
    if SELECTED is not None:
        for name in ("live_box_cut", "freeze_rehearsal"):
            sys.modules.pop(name, None)


# ------------------------------------------------------------------------------------------------ fixtures
STOP = {"type": "assistant", "message": {"id": "m-synthetic-stop", "model": "claude-haiku-4-5-20251001",
                                         "content": [{"type": "text", "text": "Synthetic stop record."}]},
        "requestId": "r-synthetic-stop"}


def session_id(text: str):
    first = next(line for line in text.split("\n") if line.strip())
    return json.loads(first).get("sessionId")


def cut_folder(files: Path, shape: str, budget: int = BUDGET, cut=True, walk=WALK) -> None:
    """w001's records (or `walk`'s) copied into `files`, its last turn marked cut (end timed-out, exit 124), the ledger's budget the
    probe's, and the session file shaped: equal (as committed), session-lags (its last assistant line dropped),
    stream-lags (one stop record past the stream), outside (two), rewrite (an earlier record's text changed), torn
    (its last assistant line cut short, the lines after it gone)."""
    files.mkdir(parents=True)
    for p in sorted(Path(walk).iterdir()):
        if p.name in ("driver-ledger.json", "transcript.jsonl") or p.name.startswith("turn-"):
            shutil.copyfile(p, files / p.name)
    led = json.loads((files / "driver-ledger.json").read_text())
    if cut:
        led["turns"][-1].update(end="timed-out", exit=124)
    led["budget_s"] = budget
    (files / "driver-ledger.json").write_text(json.dumps(led))
    path = files / "transcript.jsonl"
    text = path.read_text()
    lines = [line for line in text.split("\n") if line.strip()]
    last = max(k for k, line in enumerate(lines) if json.loads(line).get("type") == "assistant")
    stop = json.dumps(dict(STOP, sessionId=session_id(text)))
    if shape == "session-lags":
        lines = lines[:last] + lines[last + 1:]
    elif shape == "stream-lags":
        lines = lines + [stop]
    elif shape == "outside":
        lines = lines + [stop, stop.replace("m-synthetic-stop", "m-synthetic-stop-2")]
    elif shape == "rewrite":
        first = next(k for k, line in enumerate(lines) if json.loads(line).get("type") == "assistant"
                     and any(b.get("type") == "text" for b in json.loads(line)["message"]["content"]))
        rec = json.loads(lines[first])
        for b in rec["message"]["content"]:
            if b.get("type") == "text":
                b["text"] = "A synthetic rewrite."
        lines[first] = json.dumps(rec)
    elif shape == "torn":
        lines = lines[:last] + [lines[last][:30]]
    elif shape != "equal":
        raise ValueError(shape)
    path.write_text("\n".join(lines) + "\n")


def honest_record(tmp: Path, shape: str, *, cut=True, walk=WALK, ledger_budget=BUDGET, **override) -> Path:
    """A record built by live_box_cut over a cut folder in `tmp`, written to tmp/record.json; `override` replaces
    record fields after the build (a forged record)."""
    lb = MODS["live_box_cut"]
    files = tmp / lb.FILES_DIR
    cut_folder(files, shape, cut=cut, walk=walk, budget=ledger_budget)
    data = {p.name: p.read_bytes() for p in files.iterdir()}
    rec = lb.build_record(folder=files, walk="lb1", budget=BUDGET, registered=lb.registered_budget_s(),
                          line_head="a" * 40, probe_commit="b" * 40, files=data, route="graded", reasons=[],
                          at="2026-10-28T15:00:00Z")
    rec.update(override)
    path = tmp / lb.RECORD_NAME
    path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    return path


class Case(unittest.TestCase):
    def tmpdir(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="live-box-test-")).resolve()
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def verify(self, path):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = MODS["live_box_cut"].main(["verify", "--record", str(path)])
        return code, out.getvalue()

    def problems(self, path, repo=None):
        return MODS["live_box_cut"].verify_problems(Path(path), repo=repo)[1]


# ------------------------------------------------------------------------------------------------ the rehearsal rig
class Rehearsal:
    """freeze_rehearsal.main with the clone, git, the review and every step replaced by fakes (test_cp6_wiring's rig);
    the live-box verifier runs in process, through live_box_cut.main, unless `verifier` stands in for it."""

    def __init__(self, tmp: Path, verifier=None):
        self.tmp, self.commands, self.verifier = tmp, [], verifier
        self.draft = tmp / "prereg-draft.json"
        self.draft.write_text((HERE / "prereg-draft.json").read_text())
        self.scratch = tmp / "scratch"
        self.tool = tmp / "tool" / "holdout.py"
        self.tool.parent.mkdir()
        self.tool.write_text("# synthetic stand-in for aegis holdout/tools/holdout.py; never run here\n")

    def sh(self, argv, cwd, env=None, timeout=3600):
        if argv[:2] == ["git", "clone"]:
            target = Path(argv[-1])
            (target / "evals" / "gap-study-4").mkdir(parents=True)
            (target / "evals" / "gap-study-4" / "prereg-draft.json").write_bytes(self.draft.read_bytes())
        return 0, ""

    def git(self, clone, *args):
        return (0, SHA + "\n") if args[:2] == ("rev-parse", "HEAD") else (0, "")

    def run_step(self, command, clone):
        command = [str(c) for c in command]
        self.commands.append(command)
        if command[4].endswith("freeze.py"):
            frozen = {"status": "FROZEN", "take_order": [{}], "take_order_beacon_reading": {"signature": "ab"}}
            if "--holdout-digests" in command:
                source = json.loads(Path(command[command.index("--holdout-digests") + 1]).read_text())
                frozen.update(holdout_salted_digests=source["salted_sha256"],
                              holdout_wordings_per_task_version=len(next(iter(source["salted_sha256"].values()))))
            (Path(clone) / "evals" / "gap-study-4" / "prereg.json").write_text(json.dumps(frozen))
            return 0, "freeze: wrote prereg.json"
        if command[4].endswith("live_box_cut.py"):
            if self.verifier is not None:
                return self.verifier(command[5:])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = MODS["live_box_cut"].main(command[5:])
            return code, out.getvalue()
        return 0, "ok"

    def run(self, argv):
        r = MODS["freeze_rehearsal"]
        self.scratch.mkdir()
        patches = ((r, "DRAFT", self.draft), (r, "git", self.git), (r, "sh", self.sh), (r, "run_step", self.run_step),
                   (r, "rehearsal_plan", lambda pre, row: ({}, ())),
                   (r.tempfile, "mkdtemp", lambda *a, **k: str(self.scratch)),
                   (r.freeze, "outputs_exist", lambda *a: False),
                   (r.freeze, "review_file_problems", lambda commit: ([], "review/prefreeze-1.md")),
                   (r.freeze, "study_tree_sha", lambda *a, **k: "c" * 64))
        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            for module, name, value in patches:
                stack.enter_context(mock.patch.object(module, name, value))
            stack.enter_context(contextlib.redirect_stdout(out))
            code = r.main(["--review-commit", "a" * 40, "--holdout-tool", str(self.tool), *argv])
        report = self.scratch / "freeze-rehearsal-1.txt"
        return code, (report.read_text() if report.is_file() else ""), out.getvalue()


def lb_args(path, sha=None) -> list:
    """--live-box-record and the sha256 live-box-close names (the record's own unless `sha` is given)."""
    sha = sha if sha is not None else hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return ["--live-box-record", str(path), "--live-box-sha256", sha]


def step_lines(report: str) -> list:
    return [line for line in report.splitlines() if re.match(r"\[[0-9]+\] ", line)]


# ------------------------------------------------------------------------------------------------ T1
class T1NotRehearsed(Case):
    def test_no_record_fails_the_live_box_step(self):
        r = MODS["freeze_rehearsal"]
        code, report, out = Rehearsal(self.tmpdir()).run([])
        steps = step_lines(report)
        names = [s.split("] ", 1)[1] for s in steps]
        self.assertIn(r.LIVE_BOX_STEP, names, f"T1.not-rehearsed: no live-box step: {report}")
        self.assertEqual(names.index(r.LIVE_BOX_STEP), names.index("take-order beacon") + 1,
                         "T1.not-rehearsed: the step follows the take-order beacon step")
        self.assertIn(f"[1] {r.LIVE_BOX_STEP}\n    NOT REHEARSED: LIVE_BOX_REQUIRED (one forced-timeout claude-code "
                      f"take on a real box)", report, f"T1.not-rehearsed: {report}")
        others = [s for s in steps if not s.endswith(r.LIVE_BOX_STEP)]
        self.assertTrue(others and all(s.startswith("[0] ") for s in others), f"T1.not-rehearsed: {others}")
        self.assertEqual((code, report.rstrip().splitlines()[-1]), (1, "NOT all green"), "T1.not-rehearsed")
        self.assertIn(f"[1] {r.LIVE_BOX_STEP}: NOT REHEARSED", out, "T1.not-rehearsed: stdout")


# ------------------------------------------------------------------------------------------------ T2
class T2Record(Case):
    def assertReason(self, path, reason, repo=None):
        got = self.problems(path, repo=repo)
        self.assertTrue(any(reason in p for p in got), f"T2.record: {reason!r} not among {got}")
        with mock.patch.object(MODS["live_box_cut"], "REPO", repo) if repo else contextlib.nullcontext():
            code, out = self.verify(path)
        self.assertEqual(code, 1, f"T2.record: {reason!r}: verify passed: {out}")
        self.assertIn("REFUSED", out, "T2.record")

    def test_each_clause_refuses_by_name(self):
        lb = MODS["live_box_cut"]
        for field, value, reason in (("ledger_end", "end_turn", "ledger end is not timed-out"),
                                     ("ledger_exit", 0, "ledger exit is not 124"),
                                     ("harness", "codex", "harness is not claude-code"),
                                     ("adapter_sha256", "e" * 64, "adapter digest is not this tree's"),
                                     ("checker_digest", "e" * 64, "checker digest is not this tree's"),
                                     ("gap", {"stream_units": 4, "session_units": 7, "shape": "outside"},
                                      "the cut turn's shape is not inside the bound")):
            with self.subTest(field=field):
                self.assertReason(honest_record(self.tmpdir(), "equal", **{field: value}), reason)
        # a file changed by one byte, and one planted beside the named ones
        path = honest_record(self.tmpdir(), "equal")
        f = path.parent / lb.FILES_DIR / "turn-2.jsonl"
        f.write_bytes(f.read_bytes()[:-1] + b" ")
        self.assertReason(path, "turn-2.jsonl is not the file the record names")
        path = honest_record(self.tmpdir(), "equal")
        (path.parent / lb.FILES_DIR / "turn-3.jsonl").write_text("{}\n")
        self.assertReason(path, "the files folder holds other files than the record names")
        # honest records of a finding: a rewrite before the record in flight, a torn line, two units past the stream
        self.assertReason(honest_record(self.tmpdir(), "rewrite"), "content problems re-read are not empty")
        self.assertReason(honest_record(self.tmpdir(), "torn"), "the session file's last line is torn")
        self.assertReason(honest_record(self.tmpdir(), "outside"), "the cut turn's shape is not inside the bound")
        # review F4: the cli version against the draft's pin, a pin that cannot be read (never None == None), and the
        # ledger's own budget, arm, model and harness against the record's
        self.assertReason(honest_record(self.tmpdir(), "equal", cli_version="9.9.9"),
                          "cli version is not the draft's pin")
        with mock.patch.object(lb, "_draft_version", lambda: None):
            self.assertReason(honest_record(self.tmpdir(), "equal", cli_version=None),
                              "the draft's version pin cannot be read")
        self.assertReason(honest_record(self.tmpdir(), "equal", ledger_budget=BUDGET + 10),
                          "the ledger's budget, arm, model or harness is not the record's")
        # an extra key
        path = honest_record(self.tmpdir(), "equal")
        rec = json.loads(path.read_text())
        rec["transcript_excerpt"] = "x"
        path.write_text(json.dumps(rec))
        self.assertReason(path, "the record's keys are not exactly the closed set")
        # a relative path and a record inside the repository: the verifier and the rehearsal refuse both
        self.assertReason(Path("record.json"), "the record path is not absolute")
        inside = honest_record(self.tmpdir(), "equal")
        self.assertReason(inside, "the record is inside the repository", repo=inside.parent)
        r = MODS["freeze_rehearsal"]
        for argv, patch in ((["--live-box-record", "record.json", "--live-box-sha256", "0" * 64], None),
                            (lb_args(inside), inside.parent)):
            h = Rehearsal(self.tmpdir())
            with mock.patch.object(r, "REPO", patch) if patch else contextlib.nullcontext():
                code, _, out = h.run(argv)
            self.assertEqual((code, h.commands), (2, []), f"T2.record: {argv}: {out}")
            self.assertIn("refusing: --live-box-record", out, "T2.record")

    def test_the_record_must_be_the_one_close_named(self):
        """glitch-45's multi-cut ruling: the rehearsal takes the record live-box-close named, by its sha256."""
        r = MODS["freeze_rehearsal"]
        path = honest_record(self.tmpdir(), "equal")
        h = Rehearsal(self.tmpdir())
        code, report, _ = h.run(lb_args(path, sha="f" * 64))
        self.assertIn(f"[1] {r.LIVE_BOX_STEP}\n    live-box record {hashlib.sha256(path.read_bytes()).hexdigest()}: "
                      f"REFUSED: it is not the record live-box-close named", report, f"T2.record: {report}")
        self.assertFalse(any(c[4].endswith("live_box_cut.py") for c in h.commands), "T2.record: verified anyway")
        self.assertEqual(code, 1, "T2.record")
        # closure review N1: a sha256 that differs only in its last character is another record
        real = hashlib.sha256(path.read_bytes()).hexdigest()
        near = real[:-1] + ("0" if real[-1] != "0" else "1")
        code, report, _ = Rehearsal(self.tmpdir()).run(lb_args(path, sha=near))
        self.assertIn("REFUSED: it is not the record live-box-close named", report, f"T2.record: {report}")
        self.assertEqual(code, 1, "T2.record: a sha256 equal but for its last character passed")
        for argv in (["--live-box-record", str(path)], ["--live-box-record", str(path), "--live-box-sha256", "x"],
                     ["--live-box-sha256", "0" * 64]):
            h = Rehearsal(self.tmpdir())
            code, _, out = h.run(argv)
            self.assertEqual((code, h.commands), (2, []), f"T2.record: {argv}: {out}")
            self.assertIn("refusing: --live-box-", out, "T2.record")

    def test_a_pass_line_for_another_record_fails_the_step(self):
        r = MODS["freeze_rehearsal"]
        path = honest_record(self.tmpdir(), "equal")
        _, good = self.verify(path)
        other = good.strip().replace(hashlib.sha256(path.read_bytes()).hexdigest(), "f" * 64)
        self.assertNotEqual(other, good.strip(), "T2.record: the pass line names the record's sha256")
        code, report, _ = Rehearsal(self.tmpdir(), verifier=lambda argv: (0, other + "\n")).run(lb_args(path))
        self.assertIn(f"[1] {r.LIVE_BOX_STEP}", report, f"T2.record: another record's pass line passed: {report}")
        self.assertEqual(code, 1, "T2.record")


# ------------------------------------------------------------------------------------------------ T3
class T3Good(Case):
    def test_good_records_verify_and_the_rehearsal_is_all_green(self):
        r = MODS["freeze_rehearsal"]
        for walk, shape, want, turn in (("w001", "equal", "equal", 2), ("w001", "session-lags", "session-lags-", 2),
                                        ("w001", "stream-lags", "stream-lags-1", 2), ("w285", "equal", "equal", 1),
                                        ("w285", "session-lags", "session-lags-", 1)):
            with self.subTest(walk=walk, shape=shape):
                path = honest_record(self.tmpdir(), shape, walk=WALKS / walk)
                rec = json.loads(path.read_text())
                self.assertTrue(rec["gap"]["shape"].startswith(want), f"T3.good {shape}: {rec['gap']}")
                self.assertEqual((rec["cut_turns"], rec["ledger_end"], rec["ledger_exit"]), ([turn], "timed-out", 124),
                                 "T3.good")
                self.assertEqual(rec["content_problems"], {"count": 0, "problems": []}, f"T3.good {shape}")
                self.assertEqual(self.problems(path), [], f"T3.good {shape}")
                code, out = self.verify(path)
                self.assertEqual(code, 0, f"T3.good {shape}: {out}")
                self.assertTrue(r.LIVE_BOX_OK.fullmatch(out.strip()), f"T3.good {shape}: off the closed line: {out}")
        path = honest_record(self.tmpdir(), "stream-lags")
        code, report, out = Rehearsal(self.tmpdir()).run(lb_args(path))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertIn(f"[0] {r.LIVE_BOX_STEP}\n    live-box record {sha}: walk lb1", report, f"T3.good: {report}")
        self.assertEqual((code, report.rstrip().splitlines()[-1]), (0, "all green"), f"T3.good: {report}")


# ------------------------------------------------------------------------------------------------ T4
class T4NoPath(Case):
    def test_the_report_never_holds_the_record_path(self):
        path = honest_record(self.tmpdir(), "equal")
        for verifier in (None, lambda argv: (1, f"Traceback: {path} {path.parent}\n"),
                         lambda argv: (1, f"live-box record {'-' * 64}: REFUSED: {path}\n")):
            code, report, out = Rehearsal(self.tmpdir(), verifier=verifier).run(lb_args(path))
            for text, where in ((report, "report"), (out.replace(f"report: ", ""), "stdout")):
                for p in (str(path), str(path.parent), str(path.parent.resolve())):
                    self.assertNotIn(p, text, f"T4.no-path: the {where} holds the record's path")


# ------------------------------------------------------------------------------------------------ T5
class T5Commands(unittest.TestCase):
    def test_commands_are_unchanged(self):
        r = MODS["freeze_rehearsal"]
        text = "\n".join(" ".join(c) for c in r.COMMANDS)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), COMMANDS_SHA256_E3AA853C,
                         "T5.commands: COMMANDS moved from e3aa853c")
        self.assertFalse(any(r.LIVE_BOX_TOOL in " ".join(c) for c in r.COMMANDS), "T5.commands")


# ------------------------------------------------------------------------------------------------ T6
def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


def scratch_repo(parent: Path, name="repo") -> Path:
    repo = parent / name
    (repo / "evals" / "gap-study-4" / "rehearsals").mkdir(parents=True)
    (repo / "evals" / "gap-study-4" / "rehearsals" / "README.md").write_text("synthetic\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "synthetic base")
    return repo


class FakeWalk:
    """Stands in for the walk road: commits rehearsals/<walk>/ (a cut folder of `shape`, a check.json) and exits 0."""

    def __init__(self, repo: Path, shape="equal", cut=True):
        self.repo, self.shape, self.cut, self.calls = repo, shape, cut, []

    def __call__(self, builders, argv):
        self.calls.append((builders, argv))
        walk = argv[argv.index("--walk") + 1]
        folder = self.repo / "evals" / "gap-study-4" / "rehearsals" / walk
        cut_folder(folder, self.shape, budget=builders["budgets"][0], cut=self.cut)
        (folder / "check.json").write_text(json.dumps({"route": "graded", "checker_reasons": []}))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "synthetic walk")
        return 0


def builders_ok(**extra):
    from box import run_take as rt
    b = {"login_path": rt.WALK_LOGIN_FILES["claude1"], "budgets": (900, 180, 3)}
    b.update(extra)
    return b


class T6Probe(Case):
    def args(self, tmp: Path, **kw):
        out = tmp / "out"
        out.mkdir(exist_ok=True)
        base = dict(walk="lb1", task="approval-scope", half="trap", wording="w1", budget_s=BUDGET,
                    record=str(out / "record.json"))
        base.update(kw)
        return types.SimpleNamespace(**base)

    def probe(self, args, repo, builders=None, walk=None):
        out = io.StringIO()
        walk = walk or FakeWalk(repo)
        with contextlib.redirect_stdout(out):
            code = MODS["live_box_cut"].probe(args, builders_factory=lambda: builders or builders_ok(),
                                             walk_runner=walk, repo=repo)
        return code, out.getvalue(), walk

    def refused(self, why, tmp, repo, builders=None, **kw):
        code, out, walk = self.probe(self.args(tmp, **kw), repo, builders)
        self.assertEqual((code, walk.calls), (2, []), f"T6.probe: {why}: {out}")
        self.assertIn(why, out, f"T6.probe: {out}")

    def test_refusals_before_anything_is_built(self):
        lb = MODS["live_box_cut"]
        import run_builders
        tmp = self.tmpdir()
        repo = scratch_repo(tmp)
        token = next(iter(run_builders.RUN_LOGIN_FILES.values()))
        self.refused("--budget-s 900 is not below", tmp, repo, budget_s=900)
        self.refused("--budget-s 901 is not below", tmp, repo, budget_s=901)
        self.refused("--budget-s is a positive integer", tmp, repo, budget_s=0)
        self.refused("a run token's path is in the builders", tmp, repo, builders=builders_ok(extra=(token,)))
        self.refused("a run token's path is in the builders", tmp, repo,
                     builders=builders_ok(login_path=token))
        self.refused("the builders' login is not the claude1 walk login", tmp, repo,
                     builders=builders_ok(login_path="/home/javier/gap4-secrets/other/token"))
        self.refused("the walk id is not lb<number>", tmp, repo, walk="w001")
        self.refused("--record is inside the repository", tmp, repo, record=str(repo / "record.json"))
        self.refused("--record is not an absolute path", tmp, repo, record="record.json")
        records = scratch_repo(tmp, "gap4-walk-records-20261019")
        self.refused("this is the records clone", tmp, records)
        remote = scratch_repo(tmp, "with-remote")
        git(remote, "remote", "add", "origin", str(repo))
        self.refused("this clone has a remote", tmp, remote)
        frozen = scratch_repo(tmp, "frozen")
        (frozen / "evals" / "gap-study-4" / "prereg.json").write_text("{}\n")
        git(frozen, "add", "-A")
        git(frozen, "commit", "-q", "-m", "synthetic freeze")
        self.refused("prereg.json is present", tmp, frozen)
        dirty = scratch_repo(tmp, "dirty")
        (dirty / "loose.txt").write_text("x\n")
        self.refused("this clone's status is not clean", tmp, dirty)
        (tmp / "w-AbCd1234").mkdir()
        child = scratch_repo(tmp / "w-AbCd1234", "repo")
        self.refused("this is the shipped child's repository", tmp, child)
        self.assertEqual(lb.registered_budget_s(), 900, "T6.probe: the registered budget is check_take's")

    def test_a_finding_exits_4_cut_or_not(self):
        """Review F1: a content problem, a torn line or a transcript-* reason exits 4 whether or not a turn was cut; a
        clean uncut walk exits 3."""
        for shape, cut, want in (("torn", False, 4), ("rewrite", False, 4), ("equal", False, 3), ("torn", True, 4)):
            with self.subTest(shape=shape, cut=cut):
                tmp = self.tmpdir()
                repo = scratch_repo(tmp)
                code, out, _ = self.probe(self.args(tmp), repo, walk=FakeWalk(repo, shape, cut))
                self.assertEqual(code, want, f"T6.probe uncut {shape}: {out}")

    def test_gap_shape(self):
        lb = MODS["live_box_cut"]
        t = lambda mid, x: ("text", x, mid)  # noqa: E731
        stream = [t("m1", "a"), ("tool_use", "t1", "Read", {}, "m1"), ("tool_result", "t1", "A", False),
                  t("m2", "b")]
        for sess, want in ((stream, "equal"), (stream[:3], "session-lags-1"), (stream + [t("m3", "c")], "stream-lags-1"),
                           (stream + [t("m3", "c"), t("m4", "d")], "outside"),
                           (stream[:3] + [t("m2", "X")], "outside"), ([t("m1", "Z")] + stream[1:], "outside")):
            self.assertEqual(lb.gap_shape(stream, sess), want, f"T6.probe: gap_shape {len(sess)} {want}")

    def test_the_probe_end_to_end_on_fakes(self):
        lb = MODS["live_box_cut"]
        for shape, cut, want in (("stream-lags", True, 0), ("equal", False, 3), ("outside", True, 4),
                                 ("torn", True, 4)):
            with self.subTest(shape=shape, cut=cut):
                tmp = self.tmpdir()
                repo = scratch_repo(tmp)
                args = self.args(tmp)
                code, out, walk = self.probe(args, repo, walk=FakeWalk(repo, shape, cut))
                self.assertEqual(code, want, f"T6.probe {shape}: {out}")
                [(builders, argv)] = walk.calls
                self.assertEqual(builders["budgets"], (BUDGET, 180, 3), "T6.probe: only the turn budget swapped")
                self.assertEqual([argv[argv.index(k) + 1] for k in ("--arm", "--model")], ["A", lb.MODEL], "T6.probe")
                rec = json.loads(Path(args.record).read_text())
                self.assertEqual(list(rec), sorted(lb.KEYS), "T6.probe: the record's keys")
                self.assertEqual(rec["budget_s"], BUDGET, "T6.probe")
                self.assertNotIn("Synthetic stop record", Path(args.record).read_text(), "T6.probe: transcript text")
                self.assertEqual(sorted(p.name for p in (Path(args.record).parent / lb.FILES_DIR).iterdir()),
                                 sorted(FIXTURE_NAMES), "T6.probe: the files copied from the commit")
                self.assertNotIn(str(tmp), out, "T6.probe: a path on stdout")
                if want == 0:
                    self.assertEqual(self.problems(args.record, repo=repo), [], f"T6.probe {shape}")


# ------------------------------------------------------------------------------------------------ T7
class T7Timeout(unittest.TestCase):
    def test_the_battery_step_takes_run_checks_limit(self):
        r, rc = MODS["freeze_rehearsal"], MODS["run_checks"]
        battery = ("python", "-B", "-W", "ignore", "evals/gap-study-4/test_round4.py")
        self.assertEqual((r.step_timeout(battery), rc.timeout_for("test_round4")), (18000, 18000), "T7.timeout")
        for command in r.COMMANDS[1:]:
            self.assertEqual(r.step_timeout(("python", "-B", "-W", "ignore", "evals/gap-study-4/" + command[0],
                                             *command[1:])), 3600, f"T7.timeout {command}")
        with mock.patch.object(r.run_checks, "timeout_for", lambda where: 9999 if where == "test_round4" else 1):
            self.assertEqual(r.step_timeout(battery), 9999, "T7.timeout: one source, run_checks")
        seen = []
        with mock.patch.object(r, "sh", lambda argv, cwd, env=None, timeout=3600: seen.append(timeout) or (0, "")):
            r.run_step(list(battery), "/nowhere")
            r.run_step(["python", "-B", "-W", "ignore", "evals/gap-study-4/copy_manifest.py", "--check"], "/nowhere")
        self.assertEqual(seen, [18000, 3600], "T7.timeout: run_step hands sh the step's limit")

        def expire(argv, **kw):
            raise subprocess.TimeoutExpired(argv, kw["timeout"])
        with mock.patch.object(r.subprocess, "run", expire):
            code, tail = r.run_step(list(battery), "/nowhere")
        self.assertEqual(code, 1, "T7.timeout")
        self.assertIn("timed out after 18000 seconds", tail, "T7.timeout")
        self.assertIn("the step's limit is 18000 s", tail, "T7.timeout")


BOUND = {"T1.not-rehearsed": "T1NotRehearsed.test_no_record_fails_the_live_box_step",
         "T2.record": "T2Record.test_each_clause_refuses_by_name",
         "T4.no-path": "T4NoPath.test_the_report_never_holds_the_record_path",
         "T6.probe": "T6Probe.test_refusals_before_anything_is_built",
         "T7.timeout": "T7Timeout.test_the_battery_step_takes_run_checks_limit"}
SPECIAL = {"live-box-sha-unbound": "T2Record.test_a_pass_line_for_another_record_fails_the_step",
           "gap-outside-unread": "T6Probe.test_gap_shape",
           "finding-after-cut": "T6Probe.test_a_finding_exits_4_cut_or_not",
           "close-sha-unchecked": "T2Record.test_the_record_must_be_the_one_close_named",
           "close-sha-optional": "T2Record.test_the_record_must_be_the_one_close_named",
           "sha-prefix-only": "T2Record.test_the_record_must_be_the_one_close_named"}
WITNESSES = {name: (SPECIAL.get(name, BOUND[clause]), clause) for name, (clause, _, _, _) in mutants().items()}


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    import mutation_baseline
    mutation_baseline.require_green("test_live_box_cut witnesses", [sys.executable, "-B", "-W", "ignore",
                                    str(Path(__file__).resolve()), *sorted({WITNESSES[x][0] for x in chosen})],
                                    timeout=1800, tag="test_live_box_cut")
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=600)
        record = re.findall(r"^test_live_box_cut outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and set(outcome["failures"]) == {method} and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_live_box_cut witnesses: {red} red of {len(chosen)}; registry {len(WITNESSES)}", flush=True)
    return 0


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_live_box_cut: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_live_box_cut outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                   "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
