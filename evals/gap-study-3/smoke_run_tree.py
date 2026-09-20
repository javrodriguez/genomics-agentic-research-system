#!/usr/bin/env python3
"""Put one neutral line to an agent in a freshly built checkout, and read back what it was given.

    python3 evals/gap-study-2/smoke_run_tree.py --strip none --out evals/gap-study-2/verification/env-smoke/unstripped
    python3 evals/gap-study-2/smoke_run_tree.py --strip draft --out evals/gap-study-2/verification/env-smoke/stripped
    python3 evals/gap-study-2/smoke_run_tree.py --compare evals/gap-study-2/verification/env-smoke/unstripped \\
        evals/gap-study-2/verification/env-smoke/stripped

WHY THIS EXISTS. Review 11 found three defects in the driver's checkout, and all three sat in the
part no test drove: the checkout was verified against nothing, the leak check against a hand-built
string, the inheritance check against a temporary directory. This drives the driver's OWN functions
-- the same clean_run_tree, one_turn and session_file a take calls -- through one real session, then
reads the transcript Claude Code wrote with the same checks a take is held to.

IT IS NOT A WALK AND NOT A TAKE. The line names no task, the checkout holds no fixture, no operator
script is sent, and nothing it records is graded or used to fix a script. It measures the
environment, which is the operator's side of every take. Its transcript is committed so a reader can
see exactly what the agent was given, rather than a summary of it.

ROUND 2, CP3: THE ENVIRONMENT, BOTH WAYS (J4). `--strip` is required and has no default, so every smoke
says which environment it ran. `none` gives the turn an empty stripped list: the record then shows which
Claude Code session names a take driven from this pane inherits. `draft` gives it the draft's
driver_constants.stripped_env: the turn shows whether headless login still works without them. Either way
the turn's environment is built by the driver's own child_env(), the smoke only sets the driver module's
STRIPPED_ENV for this process, and environment.json is written by the driver's own environment_record and
with_turns, before the turn and again after it. `--compare` opens no session: it reads two smoke folders
and exits 0 only when their records differ in the stripped names and those names' presence, and otherwise
only where two sessions must (session id, and each turn's exit and reported source). Names, never values.

Exit 0 only when the session ran, its transcript was found by id, and every check came back empty.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402

LINE = "Reply with the single word: ready."
TREE_SWEEP = re.compile(r"gap-study|gap study|prereg|pre-registration|EVALS\.md|evals/", re.I)
# The record's task and half. The checker compares them with a ledger's and never with the task list, so a
# label naming no task is accepted by the record's own checks; it says what ran rather than borrowing a task.
SMOKE_TASK = "run-tree-smoke"
SMOKE_HALF = "none"
STRIP_CHOICES = ("draft", "none")
REPORT_FILE = "report.json"
# What two sessions' records may differ in besides the stripped names: the session, and per turn what it did.
PER_SESSION_KEYS = ("session_id",)
PER_TURN_OUTCOME_KEYS = ("exit", "apiKeySource")


def scratch_locations(drive, tree: Path, session_id: str) -> dict:
    """Where this session's temp files landed, as counts and never as a path (ruling C, 14 Sep 2026).

    The turn is given TMPDIR, TMP and TEMP naming the checkout's own temp folder (drive.child_env). Whether the
    harness follows them is a fact about one harness version, so it is read here, before the checkout is removed:
    files under the checkout's temp folder, and folders for this session id under a `claude-*` folder there, in
    the machine's temp root, and in /tmp.
    """
    folder = tree / drive.RUN_TREE_TMPDIR
    out = {"run_tree_tmp_files": sum(1 for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else 0,
           "run_tree_tmp_session_dirs": len(list(folder.glob(f"claude-*/*/{session_id}"))) if folder.is_dir() else 0}
    roots = {Path(tempfile.gettempdir()).resolve(), Path("/tmp").resolve()}
    out["os_temp_session_dirs"] = sum(len(list(r.glob(f"claude-*/*/{session_id}"))) for r in roots if r.is_dir())
    return out


def by_path(name: str, file: str):
    """This study's module, loaded by path: the first study has files of the same names."""
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def set_strip(drive, strip: str, pre: dict) -> None:
    """The stripped list child_env() reads, for this process only: the draft's, or none."""
    drive.STRIPPED_ENV = tuple((pre.get("driver_constants") or {}).get("stripped_env") or ()) if strip == "draft" else ()


def strip_problems(drive, strip: str, pre: dict) -> list[str]:
    """What is wrong with the child environment for the strip asked for, before any session. Names only."""
    child = drive.child_env()
    if strip == "none":
        if drive.STRIPPED_ENV:
            return [f"--strip none and the driver strips {sorted(drive.STRIPPED_ENV)}"]
        if child != (dict(os.environ) | drive.ISOLATION_ENV):
            # compared as a yes or no; only the names that differ are shown
            names = sorted(set(child) ^ set(dict(os.environ) | drive.ISOLATION_ENV)) or ["(a value differs)"]
            return [f"--strip none and child_env() is not this environment plus isolation: {names}"]
        return []
    listed = list((pre.get("driver_constants") or {}).get("stripped_env") or ())
    out = []
    if not listed:
        out.append("--strip draft and the draft's driver_constants.stripped_env is empty")
    if sorted(drive.STRIPPED_ENV) != sorted(listed):
        out.append("--strip draft and the driver's stripped list is not the draft's")
    left = sorted(n for n in listed if n in child)
    if left:
        out.append(f"--strip draft and child_env() still carries {left}")
    return out + drive.never_stripped_problems(drive.STRIPPED_ENV)


def compare_records(a: dict, b: dict) -> tuple[list[str], list[str]]:
    """(problems, the names that differ) between two smoke records.

    They may differ in stripped_names, in names_present for exactly those names (the record that stripped a name
    does not list it), in session_id, and in each turn's exit and apiKeySource (and so in `reported`, which is
    derived from them). Anything else is a problem, named by key and by variable name, never by value.
    """
    problems: list[str] = []
    sa, sb = set(a.get("stripped_names") or []), set(b.get("stripped_names") or [])
    stripped = sa ^ sb
    differ = set(stripped)
    if not stripped:
        problems.append("the two records strip the same names, so there is no stripped difference to show")

    pa = {e.get("name"): e.get("matched_by") for e in a.get("names_present") or []}
    pb = {e.get("name"): e.get("matched_by") for e in b.get("names_present") or []}
    for n in sorted((sa & set(pa)) | (sb & set(pb)), key=str):
        problems.append(f"names_present lists {n} in a record that strips it")
    for n in sorted({n for n in set(pa) | set(pb) if pa.get(n) != pb.get(n)}, key=str):
        differ.add(n)
        if n not in stripped:
            problems.append(f"names_present differs on {n}, which is not a name one record strips and the other not")

    skip = set(PER_SESSION_KEYS) | {"stripped_names", "names_present", "credential_source"}
    for key in sorted((set(a) | set(b)) - skip):
        va, vb = a.get(key), b.get(key)
        if va == vb:
            continue
        if isinstance(va, dict) and isinstance(vb, dict):
            names = sorted(n for n in set(va) | set(vb) if va.get(n) != vb.get(n))
            differ.update(names)
            problems.append(f"{key} differs on {names}")
        else:
            problems.append(f"{key} differs")

    ca, cb = a.get("credential_source") or {}, b.get("credential_source") or {}
    if set(ca) != set(cb) or ca.get("key") != cb.get("key"):
        problems.append("credential_source differs in its keys or the key it reads")
    ta, tb = ca.get("per_turn") or [], cb.get("per_turn") or []
    if len(ta) != len(tb):
        problems.append(f"credential_source.per_turn records {len(ta)} and {len(tb)} turn(s)")
    else:
        for i, (x, y) in enumerate(zip(ta, tb)):
            if set(x) != set(y) or any(x[k] != y[k] for k in x if k not in PER_TURN_OUTCOME_KEYS):
                problems.append(f"credential_source.per_turn entry {i} differs in more than its exit and source")
    sources_differ = [t.get("apiKeySource") for t in ta] != [t.get("apiKeySource") for t in tb]
    if ca.get("reported") != cb.get("reported") and not sources_differ:
        problems.append("credential_source.reported differs while every turn reported the same source")
    return problems, sorted(differ, key=str)


def load_smoke(folder: Path, drive) -> tuple[dict | None, dict | None, list[str]]:
    """(record, report, problems) for one smoke folder: the record bound to the report by its bytes."""
    rec_path, rep_path = folder / drive.ENVIRONMENT_RECORD_FILE, folder / REPORT_FILE
    if not rec_path.is_file() or not rep_path.is_file():
        return None, None, [f"{folder.name}: no {rec_path.name} and {rep_path.name} side by side"]
    raw = rec_path.read_bytes()
    try:
        rec, rep = json.loads(raw.decode("utf-8")), json.loads(rep_path.read_text())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, None, [f"{folder.name}: unreadable ({type(exc).__name__})"]
    got = (rep.get("environment") or {}).get("sha256")
    if got != hashlib.sha256(raw).hexdigest():
        return rec, rep, [f"{folder.name}: {rep_path.name} does not record the sha256 of {rec_path.name}'s bytes"]
    return rec, rep, []


def compare(dir_a: str, dir_b: str) -> int:
    drive = by_path("gap_drive", "drive.py")
    loaded = [(Path(d), *load_smoke(Path(d), drive)) for d in (dir_a, dir_b)]
    problems = [p for _f, _r, _p, ps in loaded for p in ps]
    for folder, rec, rep, _ps in loaded:
        if rec is not None:
            print(f"{folder.name}: strip {(rep or {}).get('strip')!r}, "
                  f"credential_source.reported {(rec.get('credential_source') or {}).get('reported')!r}, "
                  f"stripped_names {rec.get('stripped_names')}")
    if all(rec is not None for _f, rec, _r, _ps in loaded):
        more, names = compare_records(loaded[0][1], loaded[1][1])
        problems += more
        print(f"names that differ: {names}")
    for p in problems:
        print(f"  - {p}")
    print("the records differ only in the stripped names and what two sessions must" if not problems
          else f"{len(problems)} difference(s) beyond the stripped names")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One neutral turn in a built checkout, read back.")
    ap.add_argument("--model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--out", help="where the transcript, environment.json and report are written")
    ap.add_argument("--strip", choices=STRIP_CHOICES,
                    help="required for a run, no default: draft strips the draft's stripped_env, none strips nothing")
    ap.add_argument("--compare", nargs=2, metavar=("DIR_A", "DIR_B"),
                    help="open no session: compare two smoke folders' environment records")
    args = ap.parse_args(argv)
    if args.compare:
        return compare(*args.compare)
    if args.strip is None:
        ap.error("--strip {draft,none} is required: every smoke says which environment it ran")
    if not args.out:
        ap.error("--out is required for a run")

    drive = by_path("gap_drive", "drive.py")
    ct = by_path("gap_check_take", "check_take.py")
    pre = prereg.load()

    # ---- the environment, before anything is built: the strip asked for, and the money line ----
    set_strip(drive, args.strip, pre)
    bad = strip_problems(drive, args.strip, pre)
    if bad:
        print("refusing: " + "; ".join(bad) + ". Nothing was sent.")
        return 2

    sid = str(uuid.uuid4())
    claude_version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    env_rec = drive.environment_record(drive.child_env(), os.environ, session_id=sid, row=None, row_commit=None,
                                       task=SMOKE_TASK, half=SMOKE_HALF, model=args.model,
                                       claude_version=claude_version)
    money = drive.money_line_names(env_rec)
    if money:
        print(f"refusing: {', '.join(money)} set in the environment the session would be given. Nothing was sent.")
        return 2

    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    exclude = drive.excluded_from_run_tree(pre)
    tree = drive.clean_run_tree(head, sid, exclude)
    drive.RUN_TREE = tree

    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(tree), *a], capture_output=True,
                              text=True).stdout.strip()

    report: dict = {
        "what": "a smoke of the driver's checkout: one neutral line, no task, no fixture, not graded",
        "line": LINE, "model_requested": args.model, "session_id": sid,
        "strip": args.strip,
        "built_from": head, "excluded": exclude,
        "claude_version": claude_version,
        "argv_flags": list(getattr(drive, "ISOLATION_FLAGS", ())),
        "isolation_env": dict(getattr(drive, "ISOLATION_ENV", {})),
        "checkout": {
            "name": tree.name, "commits": git("rev-list", "--all", "--count"),
            "subject": git("log", "-1", "--format=%s"), "remote": git("remote"),
            "status": git("status", "--porcelain"), "git_user": git("config", "user.name"),
            "problems_before_the_turn": drive.run_tree_problems(tree, sid, exclude),
        },
    }

    # what a reader of the checkout could still find that mentions an evaluation; reported, not
    # judged -- the pre-registration names the residual it expects
    hits = []
    for f in sorted(tree.rglob("*")):
        if ".git" in f.relative_to(tree).parts or not f.is_file():
            continue
        try:
            text = f.read_text(errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for i, ln in enumerate(text.splitlines(), start=1):
            if TREE_SWEEP.search(ln):
                hits.append(f"{f.relative_to(tree)}:{i}")
    report["checkout"]["sweep_hits"] = hits

    # the record beside the transcript before the turn, as the driver writes a walk's
    out = Path(args.out)
    env_path = out / drive.ENVIRONMENT_RECORD_FILE
    try:
        out.mkdir(parents=True, exist_ok=True)
        drive.write_record_atomically(env_path, env_rec)
    except OSError as exc:
        shutil.rmtree(tree, ignore_errors=True)
        print(f"refusing: the environment record could not be written ({type(exc).__name__}). Nothing was sent.")
        return 2

    budget = int(pre["budgets"]["turn_timeout_s"])
    said, code, err, harness_said, source = drive.one_turn(LINE, sid, args.model, True, budget)
    # ROUND 2, CP3: one_turn's fifth value is the credential source the harness reported for the turn (its init
    # record's apiKeySource; None when it reported none), kept under the key the environment record reads it by.
    report["turn"] = {"exit": code, "reply": said[:200], "stderr_tail": err.strip()[-400:],
                      "credential_source": {"key": drive.CREDENTIAL_SOURCE_KEY, "apiKeySource": source}}
    row = {"n": 1, "exit": code}
    drive.write_record_atomically(env_path, drive.with_turns(env_rec, [row], {id(row): source}))
    report["environment"] = {"file": env_path.name, "sha256": hashlib.sha256(env_path.read_bytes()).hexdigest()}

    src = drive.session_file(sid)
    failures = []
    if code != 0:
        failures.append(f"the turn exited {code}")
    if src is None:
        failures.append("no session file was found for the session id")
        report["transcript"] = None
    else:
        dest = out / "transcript.jsonl"
        shutil.copy2(src, dest)
        # never an absolute path from outside the repository: it names the operator's machine
        report["transcript"] = str(dest.relative_to(REPO)) if dest.is_relative_to(REPO) else dest.name
        ctx = ct.context_text(dest)
        report["context_leaks"] = sorted(ct.context_leaks(ctx, pre))
        report["inherited_context"] = ct.inherited_context(dest)
        report["study_paths_read"] = ct.study_paths_read(dest)
        kinds: dict[str, int] = {}
        for ln in dest.read_text(errors="replace").splitlines():
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and rec.get("type") == "attachment":
                k = (rec.get("attachment") or {}).get("type", "?")
                kinds[k] = kinds.get(k, 0) + 1
        report["attachment_kinds"] = kinds
        for key in ("context_leaks", "inherited_context", "study_paths_read"):
            if report[key]:
                failures.append(f"{key}: {report[key]}")
    failures += [f"checkout: {p}" for p in report["checkout"]["problems_before_the_turn"]]
    report["scratch"] = scratch_locations(drive, tree, sid)

    shutil.rmtree(tree, ignore_errors=True)
    report["failures"] = failures
    (out / REPORT_FILE).write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({k: report[k] for k in ("strip", "environment", "checkout", "turn", "failures")}, indent=2))
    for key in ("context_leaks", "inherited_context", "attachment_kinds", "scratch"):
        print(f"{key}: {report.get(key)}")
    final = json.loads(env_path.read_text())
    print(f"stripped_names: {final['stripped_names']}")
    print(f"names_present: {[e['name'] for e in final['names_present']]}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
