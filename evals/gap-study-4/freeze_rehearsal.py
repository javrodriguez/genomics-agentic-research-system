#!/usr/bin/env python3
"""Rehearse the freeze and its gate in a disposable, full-depth local clone.

The default review is the latest committed pre-freeze review; --review-commit
can name it explicitly. It must already satisfy freeze.py's review rule and
be claimed by its writing lane. No synthetic review is added to the build.
The frozen-state COMMANDS include every Level 3 gate, even files not yet built.
Only after those checks does rehearsal register the first full planned row and
exercise the publication readers. The copy gate never runs on runtime outputs
(w5b-4). No take is driven, and no graded observation is manufactured.

All outputs, including the rehearsal report, stay under a temporary directory,
outside the source tree. --keep retains the clone too. Pass the report to the
real freeze with --rehearsal-record; the frozen file retains its content and
hash. Its tree line names the committed source tree that was cloned. This program runs on the
remote runner, never as a Mac gate. No vendor executable, model or container.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import freeze  # noqa: E402
import run_checks  # noqa: E402
import scratch_git  # noqa: E402
import study  # noqa: E402

DRAFT = HERE / "prereg-draft.json"

# THE LIVE-BOX CHECKLIST: records this program cannot make (it drives no take), required on a real box before the
# freeze and read beside its report. Lane pf1-l3 (the lead's ruling on the second closure check of f0c0eb1d, 24 Oct
# 2026): no committed claude-code walk holds a cut turn, so the cut-tail bound (claude_code_adapter.cut_tail_problem)
# has met only synthetic records.
LIVE_BOX_REQUIRED = (
    "one forced-timeout claude-code take on a real box: a turn the registered budget cuts (driver ledger row end "
    "timed-out, exit 124), its turn stream and session file committed, check_take.transcript_content_problems read on "
    "it, so a real cut's gap between the two records is measured against the cut-tail bound",
)
# Lane gap-live-box (glitch-45's rulings R1-R5 on LIVE-BOX-TAKE-DESIGN-20261028, Wed 28 Oct 2026, under Javier's standing
# delegation; NIGHT:2085, the lead's ruling of Sat 24 Oct 2026: LIVE_BOX_REQUIRED becomes a failing rehearsal step). The
# step "live-box" follows the take-order beacon step and is never one of COMMANDS (the review brief and
# review_kit/athena_outputs.py pin COMMANDS). Without --live-box-record it fails NOT REHEARSED, so the rehearsal is
# never all green; with it, the clone's own live_box_cut.py verify re-reads the record and its files with the clone's
# code (before the clone is frozen) and the step passes only on its closed line carrying the record's sha256. The
# step's tail is that closed line or a closed refusal: never the record's path, since the report is frozen into
# prereg.json and masks only the repository's and the scratch folder's paths.
LIVE_BOX_STEP = "live-box: forced-timeout claude-code take"
LIVE_BOX_NOT_REHEARSED = ("NOT REHEARSED: LIVE_BOX_REQUIRED (one forced-timeout claude-code take on a real box); "
                          "this rehearsal was given no --live-box-record, so it is not all green")
LIVE_BOX_TOOL = "live_box_cut.py"
# glitch-45's multi-cut ruling (review CHANGES of 9fb0deda, F2): the rehearsal takes the record Part T's live-box-close
# named, by its sha256 (--live-box-sha256); a record with another sha256 fails the step before it is verified.
LIVE_BOX_NOT_CLOSED = "live-box record {sha}: REFUSED: it is not the record live-box-close named"
LIVE_BOX_SHA = re.compile(r"[0-9a-f]{64}")
LIVE_BOX_OK = re.compile(r"live-box record ([0-9a-f]{64}): walk lb[0-9]+, budget [0-9]+ s of [0-9]+ s, turn [0-9]+ "
                         r"cut \(end timed-out, exit 124\), stream [0-9]+ unit\(s\), session [0-9]+ unit\(s\), shape "
                         r"(equal|session-lags-[0-9]+|stream-lags-1), content problems 0, session torn no; files "
                         r"[0-9]+ re-read equal; adapter, check_take and checker digests this tree's; within the bound")
LIVE_BOX_REFUSED = re.compile(r"live-box record ([0-9a-f]{64}|-{64}): REFUSED: [A-Za-z0-9 ,;:()'._-]{1,600}")


def live_box_record_problem(record):
    """Why `record` may not be read as the live-box record (a closed reason, never the path), or None: an absolute
    path to an existing regular file outside this repository (R3: the record stays where the probe wrote it)."""
    path = Path(record)
    if not path.is_absolute():
        return "--live-box-record is not an absolute path"
    if path.is_symlink() or not path.is_file():
        return "--live-box-record is not an existing regular file"
    if Path(REPO).resolve() in (path.resolve(), *path.resolve().parents):
        return "--live-box-record is inside this repository; the probe's record stays outside it (R3)"
    return None


def live_box_command(record):
    """The clone's own verifier on the record (run through python_command, in the clone)."""
    return (LIVE_BOX_TOOL, "verify", "--record", str(record))


def live_box_outcome(code, output, record_sha):
    """(step code, tail) from the verifier's last line: 0 only on exit 0 and the closed pass line naming the sha256 of
    the record this rehearsal read; a closed refusal line is kept as the tail, anything else is never echoed."""
    lines = output.strip().splitlines()
    last = lines[-1] if lines else ""
    ok = LIVE_BOX_OK.fullmatch(last)
    if code == 0 and ok and ok.group(1) == record_sha:
        return 0, last
    if LIVE_BOX_REFUSED.fullmatch(last):
        return 1, last
    return 1, (f"live-box record {record_sha}: the verifier's output is off its closed form or names another record "
               f"(exit {code if isinstance(code, int) else 'none'}); its words are not echoed")

# Frozen-state gates only. Missing files are interpreter failures, never dropped.
# W8A (ruling W8-layout-1; this file moved from lane w5b to lane w8a under ruling W8A-gap4-1): the four walk checks,
# so the rehearsal proves the walks the freeze rests on are registered, held to their pins, clean of the checkout and
# graded as committed (README Q5).
WALK_COMMANDS = (
    ("walk_register.py", "--check"), ("mode_binding.py", "--walks", "--check"),
    ("fixture_walk.py", "--check"), ("run.py", "--walks", "--check"),
    # glitch-6b's recheck-coverage ruling (15 Oct 2026): a counted recheck has been re-derived at freeze
    ("walk_regrade.py", "--check"),
)
# Pre-freeze review 1 (lane L1), two freeze gates over the walks, kept apart from WALK_COMMANDS because the review
# brief names WALK_COMMANDS one by one and is pinned byte-identical across rounds (review_kit/rounds.py); the brief's
# "each command of COMMANDS" covers these. MAJOR 4 part 3: every required walk of an arm the freeze runs is covered by
# a graded walk (a deferred arm's coverage recorded); m6: every walk held to the draft's version pins, the image locks'
# ids and the pinned gars tree.
WALK_PIN_COMMANDS = (("walk_plan.py", "--coverage", "--require-run-arms"), ("walk_pins.py", "--check"))
COMMANDS = (
    ("test_round4.py",), ("copy_manifest.py", "--check"),
    ("tests/test_box_integration.py",), ("tests/test_pipeline.py",),
    ("probes4.py", "--check"), ("build_draft.py", "--check"),
    ("leak_grep.py", "--check"), ("holdout.py", "--check"),
    ("review_kit/rounds.py", "--check"),
) + WALK_COMMANDS + WALK_PIN_COMMANDS


# W8B fold (lane w8b-holdout-digests; glitch-1b's rulings Q7 and Q8 at the w8b hand-back, Mon 12 Oct 2026 09:08 EDT,
# under ruling W8B-gap4-1). Q7: the rehearsal's freeze exercises the digest path. A synthetic digest file (the sha256 of
# obviously fake strings, one list per task of the cloned draft, never a holdout) is written in the rehearsal's temporary
# folder, beside the clone so the clone stays committed, and handed to freeze.py --holdout-digests; the step "holdout
# digests" then checks that the frozen file carries both fields exactly. Only --no-holdout-digests leaves it out, and that
# rehearsal records NOT REHEARSED as a failing step, so it is never all green. Q8: holdout.py --check lives in private
# aegis (ruling C4) and is wired with S9's landing; until then its step names itself as owed and fails, never passes.
HOLDOUT_FILE = "synthetic-holdout-digests.json"
OWED = {"holdout.py": "OWED: holdout.py --check lives in private aegis (ruling C4); this rehearsal was given no "
                      "--holdout-tool (aegis holdout/tools/holdout.py), so it did not run and this rehearsal is not "
                      "all green"}
NO_FILE_LINE = ("NOT REHEARSED: the holdout digests (--no-holdout-digests: the freeze ran without a digest file, so "
                "this rehearsal is not all green)")


def synthetic_holdout_source(draft_file, out_file) -> dict:
    """freeze.synthetic_holdout_source (W8B-R1-1: the generator lives in freeze.py, so a real freeze refuses its
    digests); the file is deleted in main's finally unless --keep."""
    return freeze.synthetic_holdout_source(draft_file, out_file)


def holdout_written_problems(frozen: dict, source: dict) -> list[str]:
    """What the rehearsal's frozen file got wrong about the two freeze-written holdout fields; empty when both match."""
    problems = []
    if frozen.get("holdout_salted_digests") != source["salted_sha256"]:
        problems.append("holdout_salted_digests is not the digest file's")
    counts = {len(digests) for digests in source["salted_sha256"].values()}
    if [frozen.get("holdout_wordings_per_task_version")] != sorted(counts):
        problems.append("holdout_wordings_per_task_version is not the digest file's count")
    return problems


def freeze_command(review, holdout_file, beacon_reading=None):
    return ("freeze.py", "--review-commit", review, "--rehearsal", "--write") + (
        () if holdout_file is None else ("--holdout-digests", str(holdout_file))) + (
        () if beacon_reading is None else ("--beacon-reading", str(Path(beacon_reading).resolve())))


# Pre-freeze review 1, MAJOR 9 (lane L1): the rehearsal's freeze seeds its order from a reading of the draft's drand
# round, handed in as --beacon-reading (read once on the Mac with order_beacon.py --read <round>); without one the
# freeze uses a synthetic reading, and the step "take-order beacon" fails, so the rehearsal is never all green.
def beacon_written_problems(frozen: dict) -> list[str]:
    """What the rehearsal's frozen file says about its beacon reading: [] for a real-shaped reading, else why not."""
    reading = frozen.get(freeze.BEACON_READING_KEY)
    if not isinstance(reading, dict):
        return ["the frozen file carries no take_order_beacon_reading"]
    if reading.get("signature") == freeze.SYNTHETIC_SIGNATURE:
        return [freeze.BEACON_NOT_REHEARSED]
    return []


def owed_step(command):
    """(1, why) for a gate that is owed elsewhere, or None for a gate this clone runs. `command` is the interpreter
    argv a step is handed; the script is the first argument that names a study-relative .py file (W9: the aegis
    tool's absolute path, outside this repository, is never one: holdout_check_command runs it)."""
    script = next((Path(part).name for part in command
                   if str(part).endswith(".py") and not Path(part).is_absolute()), None)
    return (1, OWED[script]) if script in OWED else None


# W9 (lane w9-cp6, glitch-2f's wave 9 ruling under Javier's standing delegation, Mon 12 Oct 2026; this file's edit is
# recorded in lane w8b-holdout-digests' entry, without transfer, because tests/test_pipeline.py binds its owner). Q8's
# step retargeted: S9b landed holdout/tools/holdout.py on aegis master (76ec9f5). Given --holdout-tool, the rehearsal
# runs that tool's --check on HOLDOUT_FIXTURE, a SYNTHETIC holdout committed in this study (obviously fake wordings,
# one file per task, never a held-out wording), against the clone at its own HEAD. The holdout folder is not an
# option: the rehearsal never reads any folder but the clone's fixture, and the real folder is checked by the tool at
# the real freeze, by the orchestrator alone. Salt and digests are made only at the freeze (W8B-gap4-1 A), so the
# rehearsal never runs --make-salt or --digests. Without --holdout-tool the step stays OWED and fails.
HOLDOUT_GATE = ("holdout.py", "--check")
HOLDOUT_FIXTURE = "fixtures/holdout-rehearsal"
HOLDOUT_TOOL_NAME = "holdout.py"
# Fold w9-close-1 (glitch-2f): the step's name wherever it is written (stdout and the report a freeze records), so the
# fixture's counts are never read as the real holdout's.
HOLDOUT_STEP_LABEL = (" ".join(HOLDOUT_GATE) + " on the synthetic fixture " + study.rel(HOLDOUT_FIXTURE)
                      + ", not the real holdout")


def holdout_tool_problem(tool):
    """Why `tool` may not be run as the aegis holdout check (a reason), or None: it must be an existing file named
    holdout.py outside this repository (the check lives in private aegis, ruling C4)."""
    path = Path(tool)
    if not path.is_absolute():
        return f"--holdout-tool {tool} is not an absolute path"
    if path.name != HOLDOUT_TOOL_NAME or not path.is_file():
        return f"--holdout-tool {tool} is not an existing {HOLDOUT_TOOL_NAME}"
    if path.resolve().is_relative_to(REPO.resolve()):
        return f"--holdout-tool {tool} is inside this repository; the holdout check lives in private aegis (C4)"
    return None


def holdout_check_command(tool, clone, sha):
    """The aegis tool's --check on the clone's synthetic fixture, against the clone at `sha`; never --digests."""
    return (sys.executable, "-B", "-W", "ignore", str(Path(tool).resolve()), "--check",
            "--holdout", str(Path(clone) / study.rel(HOLDOUT_FIXTURE)), "--gars", str(clone), "--sha", sha)


def runtime_commands(row_file):
    """The runtime steps a green frozen state runs, in order (pre-freeze review 2, m2: freeze.rehearsal_step_problems
    requires each by name, with the row file as the report masks it, <scratch>/row.json)."""
    return (
        ("takes.py", "--add", "--row", str(row_file), "--attempt", "1"),
        ("takes.py", "--session-id", "0"),
        ("run.py", "--all"), ("result.py", "--write"),
        ("check_results.py", "--ledger", "--rehearsal-plan"), ("completeness.py", "--check"),
    )


def rehearsal_plan(pre, row_file):
    """A full frozen row and the runtime commands; never another copy gate."""
    first = copy.deepcopy(pre["take_order"][0])
    import takes
    takes.require_planned_row(first, pre)
    return first, runtime_commands(row_file)


# Lane gap-live-box (design section 7): the battery step's limit is run_checks' own for the battery, one source for
# both (test_round4 ran 3644.2 s in battery4 on 26 Oct, past 3600 s); every other step keeps STEP_TIMEOUT_S.
STEP_TIMEOUT_S = 3600


def step_timeout(command):
    """run_checks.timeout_for("test_round4") for the test_round4.py step, STEP_TIMEOUT_S for every other step."""
    script = next((Path(part).name for part in command if str(part).endswith(".py")), None)
    return run_checks.timeout_for("test_round4") if script == "test_round4.py" else STEP_TIMEOUT_S


def sh(argv, cwd, env=None, timeout=STEP_TIMEOUT_S):
    try:
        got = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                             env=env, timeout=timeout)
        return got.returncode, got.stdout + got.stderr
    except subprocess.TimeoutExpired as exc:
        return 1, f"{exc} (the step's limit is {timeout} s)"
    except OSError as exc:
        return 1, str(exc)


def git(clone, *args):
    return sh(["git", "-C", str(clone), "-c", "user.name=rehearsal",
               "-c", "user.email=rehearsal@example.invalid", "-c",
               f"{scratch_git.MAINTENANCE_KEY}={scratch_git.MAINTENANCE_VALUE}", *args], clone)


def step_environment():
    """A fixed fake identity for subprocesses committing disposable records."""
    return dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
                OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                GIT_AUTHOR_NAME="rehearsal", GIT_AUTHOR_EMAIL="rehearsal@example.invalid",
                GIT_COMMITTER_NAME="rehearsal", GIT_COMMITTER_EMAIL="rehearsal@example.invalid")


def run_step(command, clone):
    return sh(command, clone, env=step_environment(), timeout=step_timeout(command))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)   # W9: no prefix reaches an option
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--review-commit")
    ap.add_argument("--no-holdout-digests", action="store_true")
    ap.add_argument("--holdout-tool", help="aegis holdout/tools/holdout.py (W9): its --check runs on the synthetic "
                                           "fixture; without it the holdout step is OWED and fails")
    ap.add_argument("--beacon-reading", help="order_beacon.py --read's output for the draft's round (MAJOR 9); "
                                             "without it the take-order beacon step fails")
    ap.add_argument("--live-box-record", help="the live-box probe's record (live_box_cut.py); without it the live-box "
                                              "step fails NOT REHEARSED")
    ap.add_argument("--live-box-sha256", help="the record's sha256 as Part T's live-box-close named it; required "
                                              "with --live-box-record")
    args = ap.parse_args(argv)
    if args.holdout_tool is not None:
        why = holdout_tool_problem(args.holdout_tool)
        if why:
            print("refusing: " + why)
            return 2
    live_box_sha = None
    if args.live_box_record is not None:
        why = live_box_record_problem(args.live_box_record)
        if why:
            print("refusing: " + why)
            return 2
        if not (isinstance(args.live_box_sha256, str) and LIVE_BOX_SHA.fullmatch(args.live_box_sha256)):
            print("refusing: --live-box-record needs --live-box-sha256, the sha256 live-box-close named")
            return 2
        live_box_sha = hashlib.sha256(Path(args.live_box_record).read_bytes()).hexdigest()
    elif args.live_box_sha256 is not None:
        print("refusing: --live-box-sha256 names a record, and no --live-box-record was given")
        return 2
    if freeze.outputs_exist(HERE):
        print("refusing: a freeze output already exists here")
        return 2
    code, dirty = git(REPO, "status", "--porcelain")
    if code or dirty.strip():
        print("refusing: commit the complete source repository before rehearsal")
        return 2
    review = args.review_commit
    if not review:
        code, review = git(REPO, "log", "-1", "--format=%H", "--",
                           study.rel(study.REVIEW_DIR, "prefreeze-*.md"))
        review = review.strip()
    problems, _ = freeze.review_file_problems(review or "")
    if problems:
        print("refusing: " + "; ".join(problems))
        return 2
    digest = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
    tree = freeze.study_tree_sha()
    scratch = Path(tempfile.mkdtemp(prefix="rehearsal-"))
    clone = scratch / "repo"
    report = scratch / "freeze-rehearsal-1.txt"
    env = step_environment()
    steps = []
    holdout_file = None
    live_box = (1, LIVE_BOX_NOT_REHEARSED)

    def step(name, command):
        owed = owed_step(command)
        code, output = owed if owed else run_step(command, clone)
        tail = " | ".join(output.strip().splitlines()[-3:])
        steps.append((name, code, tail))
        print(f"[{code}] {name}: {tail}", flush=True)
        return code

    def python_command(command):
        return [sys.executable, "-B", "-W", "ignore", study.rel(command[0]), *command[1:]]

    try:
        code, output = sh(["git", "clone", "-q", "--no-local", str(REPO), str(clone)], REPO, env)
        if code:
            raise ValueError("local clone failed: " + output)
        code, output = git(clone, "remote", "remove", "origin")
        if code:
            raise ValueError("cannot remove clone remote: " + output)
        if args.live_box_record is not None:      # read with the clone's code before the clone is frozen
            if live_box_sha != args.live_box_sha256:
                live_box = (1, LIVE_BOX_NOT_CLOSED.format(sha=live_box_sha))
            else:
                code, output = run_step(python_command(live_box_command(args.live_box_record)), clone)
                live_box = live_box_outcome(code, output, live_box_sha)
        holdout_file = None if args.no_holdout_digests else scratch / HOLDOUT_FILE
        source = (None if holdout_file is None else
                  synthetic_holdout_source(clone / study.rel("prereg-draft.json"), holdout_file))
        fz = step("freeze", python_command(freeze_command(review, holdout_file, args.beacon_reading)))
        if fz == 0:
            code, output = git(clone, "add", "--", *(study.rel(p) for p in
                                   ("prereg.json", "COPIED.json", "COPIED.d/freeze.json")))
            if code:
                raise ValueError("freeze staging failed: " + output)
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as message:
                message.write("Rehearse the frozen state\n\nCo-Authored-By: Codex (gpt-6-astra) <noreply@openai.com>\n")
                message.flush()
                code, output = git(clone, "commit", "-F", message.name)
            if code:
                raise ValueError("freeze commit failed: " + output)
            if source is None:
                steps.append(("holdout digests", 1, NO_FILE_LINE))
            else:
                wrong = holdout_written_problems(json.loads((clone / study.rel("prereg.json")).read_text()), source)
                steps.append(("holdout digests", 1 if wrong else 0,
                              "; ".join(wrong) or "both fields written from the synthetic digest file"))
            wrong = beacon_written_problems(json.loads((clone / study.rel("prereg.json")).read_text()))
            steps.append(("take-order beacon", 1 if wrong else 0,
                          "; ".join(wrong) or "the order seeded from the --beacon-reading file's round"))
        steps.append((LIVE_BOX_STEP, *live_box))
        print(f"[{live_box[0]}] {LIVE_BOX_STEP}: {live_box[1]}", flush=True)
        for command in COMMANDS:
            if command == HOLDOUT_GATE and args.holdout_tool is not None:      # W9: the aegis tool, synthetic fixture
                code, head = git(clone, "rev-parse", "HEAD")
                if code:
                    raise ValueError("the clone's HEAD cannot be read: " + head)
                step(HOLDOUT_STEP_LABEL, holdout_check_command(args.holdout_tool, clone, head.strip()))
            else:
                step(" ".join(command), python_command(command))
        if fz == 0 and all(code == 0 for _, code, _ in steps):
            pre = json.loads((clone / study.rel("prereg.json")).read_text())
            row_file = scratch / "row.json"
            first, commands = rehearsal_plan(pre, row_file)
            row_file.write_text(json.dumps(first))
            for command in commands:
                if step(" ".join(command), python_command(command)):
                    break
    except (ValueError, KeyError, OSError) as exc:
        steps.append(("rehearsal", 1, str(exc)))
    finally:
        if not args.keep and clone.exists():
            shutil.rmtree(clone)
        # W8B-R1-1: the synthetic digest file never outlives the rehearsal unless --keep keeps its clone too
        if holdout_file is not None and not args.keep:
            holdout_file.unlink(missing_ok=True)
    green = bool(steps) and all(code == 0 for _, code, _ in steps)
    lines = [digest, "Disposable rehearsal; no takes driven.", freeze.REHEARSAL_TREE_PREFIX + tree]
    for name, code, tail in steps:
        lines.extend((f"[{code}] {name}", "    " + tail))
    lines.append("all green" if green else "NOT all green")
    text = "\n".join(lines).replace(str(REPO), "<repo>").replace(str(scratch), "<scratch>") + "\n"
    report.write_text(text)
    print(f"report: {report}")
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
