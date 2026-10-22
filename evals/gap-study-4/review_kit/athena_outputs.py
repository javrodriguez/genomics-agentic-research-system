#!/usr/bin/env python3
"""Write the heavy gates' outputs a pre-freeze reviewer reads from athena/, one file per gate, on the remote runner.

    python3 evals/gap-study-4/review_kit/athena_outputs.py <out folder> [--holdout-tool <aegis holdout.py>] [--timeout-s N]

Run by the pre-check operator on the remote runner, in a throwaway child of the head under review, never on the Mac.
It runs, from the repository root and at its committed HEAD (it refuses a study with uncommitted changes, so the
commit line says what ran):

  - run_checks.py (the battery and every lane's listed checks);
  - each command of freeze_rehearsal.COMMANDS, run directly the way the rehearsal runs it (the walk gates
    included); holdout.py --check runs the aegis tool on the synthetic fixture when --holdout-tool is given, and is
    written as OWED otherwise, through the rehearsal's own owed_step, so it can never read as a pass;
  - ("freeze.py", "--check");
  - the three legs each vendor arm must hold, through freeze.unrecorded_shapes_problem on the draft.

Each file is `NN-<gate>.txt` and opens with `command: <gate>`, `commit: <full HEAD sha>`, `exit: <code>` and
`masked: <rule counts>`, then the tail of the gate's output. The tail is masked by named rules before it is written,
because the reviewer reads and quotes it and build_kit.py --athena refuses what the report may not carry: the
repository's path becomes <repo>, the home folder <home>, any other absolute path's root <abs>, an account or
person name <account>, and an operator marker <marker> (blindness.py's MARKERS, less the study folder names the clone
carries anyway; build_kit.athena_markers). The gate's exit code is never masked. Lane review-kit-port, from the
review of the port (MINOR 3: nothing produced the files the kit requires).

No model, no network, no container. stdlib only.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_DIR = HERE.parent
REPO = STUDY_DIR.parent.parent
TAIL_LINES = 200
LEGS_CODE = ("import json, freeze; p = freeze.unrecorded_shapes_problem(json.load(open('prereg-draft.json'))); "
             "print('every leg holds' if p is None else p); raise SystemExit(0 if p is None else 1)")
LEGS_NAME = "freeze.unrecorded_shapes_problem(prereg-draft.json): legs i-iii"


def _load_build_kit():
    saved = list(sys.path)
    try:
        spec = importlib.util.spec_from_file_location("review_kit_build_kit_for_outputs", HERE / "build_kit.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path[:] = saved


_bk = _load_build_kit()


def mask(text: str, repo: Path, home: Path) -> tuple[str, dict]:
    """The text with each named rule applied in order, and how many times each fired."""
    counts = {}
    rules = [("repository path", re.escape(str(repo)), "<repo>"),
             ("home folder", re.escape(str(home)), "<home>"),
             ("absolute path root", _bk.ABS_PATH.pattern, "<abs>/"),
             ("account or person", _bk.PERSON.pattern, "<account>")]
    # every marker counts under one label: the header must not carry the word it masked
    rules += [("operator marker", re.escape(m), "<marker>") for m in _bk.athena_markers()]
    for name, pattern, repl in rules:
        flags = re.I if name in ("account or person", "operator marker") else 0
        text, n = re.subn(pattern, repl, text, flags=flags)
        if n:
            counts[name] = counts.get(name, 0) + n
    return text, counts


def write_output(out: Path, n: int, name: str, head: str, code: int, text: str, repo: Path, home: Path) -> str:
    """Write one gate's file; return its name."""
    tail = "\n".join(text.rstrip("\n").splitlines()[-TAIL_LINES:])
    body, counts = mask(tail, repo, home)
    label, _ = mask(name, repo, home)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-")[:60] or "gate"
    fname = f"{n:02d}-{slug}.txt"
    masked = ", ".join(f"{k} {v}" for k, v in counts.items()) or "none"
    (out / fname).write_text(f"command: {label}\n" + f"commit: {head}\n" + f"exit: {code}\nmasked: {masked}\n"
                             f"--- the last {TAIL_LINES} lines of its output, at most ---\n{body}\n")
    return fname


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--holdout-tool", default=None)
    ap.add_argument("--timeout-s", type=int, default=6 * 3600)
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists():
        print(f"refusing: {out.name} already exists; the outputs of one head go in one new folder")
        return 2
    if out.is_relative_to(REPO.resolve()):
        print("refusing: the out folder is inside this repository, which would make the tree dirty")
        return 2
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True)
    if dirty.returncode or dirty.stdout.strip():
        print("refusing: the repository has uncommitted changes, so no commit line could say what ran")
        return 2
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    sys.path.insert(0, str(STUDY_DIR))
    import freeze_rehearsal  # noqa: E402  (imported here: it imports the freeze and the checker)
    fr = freeze_rehearsal
    if args.holdout_tool is not None:
        why = fr.holdout_tool_problem(args.holdout_tool)
        if why:
            print("refusing: " + why)
            return 2
    py = [sys.executable, "-B", "-W", "ignore"]
    gates = [("run_checks.py", py + [fr.study.rel("run_checks.py")], REPO)]
    for command in freeze_rehearsal.COMMANDS:
        if command == fr.HOLDOUT_GATE and args.holdout_tool is not None:
            gates.append((fr.HOLDOUT_STEP_LABEL, list(fr.holdout_check_command(args.holdout_tool, REPO, head)), REPO))
        else:
            gates.append((" ".join(command), py + [fr.study.rel(command[0]), *command[1:]], REPO))
    gates.append((" ".join(("freeze.py", "--check")), py + [fr.study.rel("freeze.py"), "--check"], REPO))
    gates.append((LEGS_NAME, py + ["-c", LEGS_CODE], STUDY_DIR))
    out.mkdir(parents=True)
    env = fr.step_environment()
    passed = 0
    for n, (name, argv, cwd) in enumerate(gates, 1):
        owed = fr.owed_step(argv)
        code, text = owed if owed else fr.sh(argv, cwd, env, timeout=args.timeout_s)
        fname = write_output(out, n, name, head, code, text, REPO, Path.home())
        passed += code == 0
        print(f"[{code}] {fname}", flush=True)
    print(f"athena_outputs: {len(gates)} file(s) written at {head[:12]}, {passed} gate(s) exited 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
