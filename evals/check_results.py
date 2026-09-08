#!/usr/bin/env python3
"""Check the published results against the pre-registration that was frozen before they existed.

This is the file that makes "pre-registered" mean something. Anyone can write a thresholds file
and then quietly move a threshold; what stops that is a check that re-reads the FROZEN bytes from
git history and compares them to what is on disk now, and that fails loudly when they differ.

    python evals/check_results.py              thresholds unmoved since the freeze
    python evals/check_results.py --controls   every control behaves opposite its positive
    python evals/check_results.py --lexicon    every hand-labelled grader suite still passes

WHAT IS COMPARED, and why that comparison and not an easier one.

  1. The frozen file itself. `git show <prereg-sha>:evals/prereg.json` against the working copy,
     byte for byte. Any difference is reported as `thresholds amended` -- which the goal permits,
     PUBLISHED, and forbids silently.
  2. Every file the frozen file pinned. The pre-registration records a git blob sha AND a sha256
     for each grader, shared reader, generator, ground truth and case file. Re-hashing them now
     catches a constant edited after the freeze in the one way that cannot be argued with: the
     bytes that produced a published verdict are not the bytes on disk.
  3. The live constants, by name. Redundant with (2) by construction, and kept anyway, because a
     sha mismatch says "this file changed" and a named constant says WHICH threshold moved. A
     reader deserves the second sentence, not only the first.
  4. Each results file's own binding: the prereg_sha256 it recorded when it was written. A
     results file that was graded against a different pre-registration than the one in the tree
     is the exact fraud this whole design exists to make impossible, and it is checkable.

--controls compares BEHAVIOUR LABELS, never pass/fail verdicts. A correctly behaving system
passes both halves, so a verdict comparison is satisfied identically on both and measures
nothing. The labels are what differ: asserted/denied, effect-reported/no-effect-reported,
same/different. A system that answers both halves the same way fails here, and that failure is
published rather than quietly dropped.

AN EMPTY RESULTS DIRECTORY IS NOT A PASS. With nothing graded this exits 0 -- there is nothing to
contradict -- but it says `graded=0` in as many words, because "no findings" and "nothing was
looked at" are different facts and only one of them is evidence.

No model is called. stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
sys.path.insert(0, str(EVALS))
sys.path.insert(0, str(EVALS / "graders"))

import freeze  # noqa: E402

PREREG = EVALS / "prereg.json"
NOT_RUN = EVALS / "not-run.json"
RESULTS = EVALS / "results"

# Which live module attribute each frozen numeric threshold must still equal. Named explicitly so
# a mismatch reports the threshold, not merely the file.
LIVE_THRESHOLDS = {
    "confounded-refusal": [("confounded_refusal", "ANSWER_FROM_TURN", "answer_from_turn"),
                           ("confounded_refusal", "NEGATION_SCOPE", "negation_scope")],
    "planted-effect": [("planted_effect", "ALPHA", "alpha"),
                       ("planted_effect", "MIN_RECOVERED", "min_recovered"),
                       ("planted_effect", "MIN_PRECISION", "min_precision"),
                       ("planted_effect", "MAX_NULL_REJECTIONS", "max_null_rejections"),
                       ("planted_effect", "NEGATION_SCOPE", "negation_scope")],
    "cross-run-repro": [("cross_run_repro", "CONCLUSION_FROM", "conclusion_from"),
                        ("cross_run_repro", "NEGATION_SCOPE", "negation_scope")],
}

# The four hand-labelled suites, each with the door that replays it.
LEXICONS = [
    ("evals/stated_count.py", "evals/fixtures/lexicon_cases_count.json"),
    ("evals/graders/confounded_refusal.py", "evals/fixtures/lexicon_cases_task1.json"),
    ("evals/graders/planted_effect.py", "evals/fixtures/lexicon_cases_task2.json"),
    ("evals/graders/cross_run_repro.py", "evals/fixtures/lexicon_cases_task3.json"),
]


def prereg_ref() -> dict:
    """evals/freeze.py's answer: the freeze commit, and whether it can be proved here."""
    return freeze.freeze_ref()


def pinned_refs(prereg: dict) -> list[dict]:
    refs: list[dict] = []
    seen: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            if "path" in o and "sha256" in o and o["path"] not in seen:
                seen.add(o["path"])
                refs.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(prereg)
    return refs


def check_thresholds(prereg: dict, ref: dict, problems: list[str]) -> None:
    print("thresholds:")
    sha = ref["sha"]

    if not ref["verifiable"]:
        problems.append("THE FREEZE CANNOT BE PROVED FROM THIS CHECKOUT, so this check has not "
                        f"verified the ordering it exists to verify: {ref['why']}")
        print(f"  UNVERIFIABLE  {ref['why']}")
    else:
        frozen = freeze.frozen_bytes(sha)
        if frozen is None:
            problems.append(f"git show {sha}:evals/prereg.json failed")
            print(f"  UNVERIFIABLE  cannot read the frozen bytes at {sha[:8]}")
        elif frozen != PREREG.read_bytes():
            problems.append("THRESHOLDS AMENDED: evals/prereg.json differs from the bytes frozen "
                            f"at {sha}. This is permitted only when published in the table as "
                            "`thresholds amended`, with the before and the after.")
            print(f"  AMENDED       prereg.json != its frozen bytes at {sha[:8]}")
        else:
            print(f"  ok            prereg.json byte-identical to {sha[:8]}")

    for ref in pinned_refs(prereg):
        p = REPO / ref["path"]
        if not p.is_file():
            problems.append(f"pinned file missing: {ref['path']}")
            print(f"  MISSING       {ref['path']}")
            continue
        live = hashlib.sha256(p.read_bytes()).hexdigest()
        if live != ref["sha256"]:
            problems.append(f"{ref['path']} changed after the freeze "
                            f"(frozen {ref['sha256'][:12]}, now {live[:12]})")
            print(f"  CHANGED       {ref['path']}")
        else:
            print(f"  ok            {ref['path']}")

    for task in prereg["tasks"]:
        for mod_name, attr, frozen_key in LIVE_THRESHOLDS.get(task["id"], []):
            frozen_val = task["thresholds"].get(frozen_key)
            try:
                mod = __import__(mod_name)
                live_val = getattr(mod, attr)
            except (ImportError, AttributeError) as exc:
                problems.append(f"{task['id']}: cannot read {mod_name}.{attr} ({exc})")
                print(f"  UNREADABLE    {task['id']} {mod_name}.{attr}")
                continue
            if live_val != frozen_val:
                problems.append(f"{task['id']}: threshold {frozen_key} moved after the freeze "
                                f"({frozen_val!r} frozen, {live_val!r} live in {mod_name}.{attr})")
                print(f"  MOVED         {task['id']} {frozen_key}: {frozen_val!r} -> {live_val!r}")
            else:
                print(f"  ok            {task['id']} {frozen_key} = {frozen_val!r}")


def check_not_run(problems: list[str]) -> None:
    """Re-run the evidence for every task declared unrunnable. Never believe the declaration.

    A file that says "this could not be run" is the easiest place in the whole design to hide a
    failure: nothing about it looks like a verdict. So each declaration carries the command that
    demonstrates the refusal, and this runs it. Two directions are checked, and the second is the
    one that matters -- if a task declared not-run turns out to RUN now, the declaration is stale
    and that task owes a verdict, so it is a red rather than a quiet pass.
    """
    print("not run:")
    if not NOT_RUN.is_file():
        print("  none declared")
        return
    doc = json.loads(NOT_RUN.read_text())
    tasks = doc.get("tasks", {})
    if not tasks:
        print("  none declared")
        return
    for task_id, decl in tasks.items():
        ev = decl["evidence"]
        # The command comes out of a JSON file, so it is CONSTRAINED here rather than trusted.
        # This file may run git and it may run a Python script that lives in this repository;
        # it may not become a way to execute anything a declaration happens to name.
        argv = ev.get("command") or []
        script = REPO / argv[1] if len(argv) > 1 else None
        if (len(argv) < 2 or argv[0] not in ("python3", sys.executable)
                or script is None or not script.is_file()
                or REPO not in script.resolve().parents):
            problems.append(
                f"{task_id}: its evidence command is not a Python script inside this repository "
                f"({argv[:2]}). A not-run declaration may not name an arbitrary command.")
            print(f"  REFUSED       {task_id}: evidence command out of bounds")
            continue
        try:
            out = subprocess.run(argv, cwd=str(REPO), capture_output=True,
                                 text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            problems.append(f"{task_id}: the not-run evidence command could not be run ({exc})")
            print(f"  UNVERIFIABLE  {task_id}")
            continue

        if out.returncode != ev["expect_exit"]:
            problems.append(
                f"{task_id}: declared NOT RUN for want of {decl['missing_requirement']!r}, but "
                f"its evidence command now exits {out.returncode}, not {ev['expect_exit']}. "
                f"Either the system under test gained what it lacked -- in which case this task "
                f"owes a verdict and must be graded -- or the declaration was wrong. It cannot "
                f"stay a blank row.")
            print(f"  NOW RUNS?     {task_id}: exit {out.returncode}, expected {ev['expect_exit']}")
            continue

        try:
            payload = json.loads(out.stdout)
        except json.JSONDecodeError:
            payload = None
        wanted = ev.get("expect_json") or {}
        if payload is None and wanted:
            problems.append(f"{task_id}: the evidence command printed no JSON to check against")
            print(f"  NO JSON       {task_id}")
            continue
        bad = {k: (payload.get(k), v) for k, v in wanted.items() if payload.get(k) != v}
        if bad:
            problems.append(f"{task_id}: the evidence no longer shows what it claimed — {bad}")
            print(f"  CHANGED       {task_id}: {bad}")
        else:
            print(f"  ok            {task_id:20s} still refused — {decl['missing_requirement']}")


def results_files() -> list[Path]:
    if not RESULTS.is_dir():
        return []
    return sorted(p for p in RESULTS.glob("*.json"))


def check_results_binding(prereg: dict, problems: list[str]) -> int:
    files = results_files()
    print("results:")
    if not files:
        print("  graded=0 — no results file exists yet. Nothing here contradicts the "
              "pre-registration, and nothing here is evidence either.")
        return 0
    live256 = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    declared = {t["id"] for t in prereg["tasks"]}
    for f in files:
        r = json.loads(f.read_text())
        tid = r.get("task")
        if tid not in declared:
            problems.append(f"{f.name}: task {tid!r} is not in the declared set")
            print(f"  UNDECLARED    {f.name}")
            continue
        if r.get("prereg_sha256") != live256:
            problems.append(f"{tid}: graded against a different pre-registration "
                            f"(results say {str(r.get('prereg_sha256'))[:12]}, "
                            f"the tree's is {live256[:12]})")
            print(f"  WRONG PREREG  {tid}")
            continue
        state = r.get("state")
        verdict = r.get("verdict")
        if state == "RAN" and verdict not in ("pass", "fail", "INVALID-FIXTURE"):
            problems.append(f"{tid}: RAN with verdict {verdict!r}")
        print(f"  ok            {tid:20s} state={state} verdict={verdict}")
    graded = sum(1 for f in files
                 if json.loads(f.read_text()).get("state") == "RAN")
    print(f"  published={len(files)} graded={graded}")
    if files and not graded:
        print("  Every published row is a SKIP. A published row is not a graded one: nothing "
              "here has been run, and this check has nothing to be clean about yet.")
    return graded


def check_regrade(prereg: dict, problems: list[str]) -> int:
    """A published results file must be byte-identical to what the pinned graders re-produce.

    A fresh-context verifier falsified the earlier binding: it rewrote the `threshold` block
    INSIDE a results file -- the surface a reader is pointed at -- and the checker printed clean,
    because the file was bound to the pre-registration only by the whole-file hash it had
    recorded about the prereg, never by its own content. Comparing threshold fields one by one
    would close that hole and leave every other field open. So the binding is total: for every
    graded task, grade it again, in memory, through run.py's own dispatch from the same
    transcripts, and require the result to serialise to exactly the committed bytes. Anything
    edited in a results file after the fact -- a threshold, a verdict, a label, an observed
    sentence -- makes the two differ, and the first differing key is named.
    """
    print("regrade:")
    sys.path.insert(0, str(EVALS))
    import run as runner  # noqa: E402 -- the runner is the one place grading is dispatched from

    ref = runner.prereg_ref()
    declared = runner.not_run_declarations()
    regraded = 0
    for task in prereg["tasks"]:
        f = RESULTS / f"{task['id']}.json"
        if not f.is_file():
            continue
        committed = json.loads(f.read_text())
        if committed.get("state") != "RAN":
            continue
        fresh = runner.run_task(prereg, task, ref, declared)
        a = json.dumps(committed, indent=2, sort_keys=True)
        b = json.dumps(fresh, indent=2, sort_keys=True)
        if a == b:
            regraded += 1
            print(f"  ok            {task['id']:20s} re-grade reproduces the committed file byte for byte")
            continue
        # name the first differing key so the reader is told what moved, not merely that something did
        def first_diff(x, y, path="") -> str:
            if isinstance(x, dict) and isinstance(y, dict):
                for k in sorted(set(x) | set(y)):
                    if x.get(k) != y.get(k):
                        return first_diff(x.get(k), y.get(k), f"{path}.{k}" if path else k)
            if isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
                for i, (p, q) in enumerate(zip(x, y)):
                    if p != q:
                        return first_diff(p, q, f"{path}[{i}]")
            return f"{path}: committed {json.dumps(x)[:80]} vs re-graded {json.dumps(y)[:80]}"
        where = first_diff(committed, fresh)
        problems.append(
            f"{task['id']}: the committed results file is NOT what the pinned graders produce "
            f"from the pinned transcripts. First difference at {where}. A results file is never "
            f"edited; if the graders changed, that is a published amendment, and if they did "
            f"not, this file was.")
        print(f"  TAMPERED      {task['id']:20s} {where[:100]}")
    if not regraded and any((RESULTS / f"{t['id']}.json").is_file() for t in prereg["tasks"]):
        print("  graded=0 — nothing to re-grade")
    return regraded


def check_controls(prereg: dict, problems: list[str]) -> None:
    print("controls:")
    files = {p.stem: json.loads(p.read_text()) for p in results_files()}
    if not files:
        print("  graded=0 — no pair has been graded, so no control has been compared. "
              "The teeth of this check show only once transcripts land.")
        return
    for task in prereg["tasks"]:
        tid = task["id"]
        r = files.get(tid)
        if r is None:
            print(f"  not published {tid}")
            continue
        if r.get("state") != "RAN":
            print(f"  not compared  {tid:20s} {r.get('state')} — not graded")
            continue
        labels = r.get("behaviour_label") or {}
        pos, ctl = labels.get("positive"), labels.get("control")
        if pos is None or ctl is None:
            problems.append(f"{tid}: a half carries no behaviour label ({labels})")
            print(f"  NO LABEL      {tid}")
        elif pos == ctl:
            problems.append(f"{tid}: the control behaved the SAME as the positive "
                            f"(both {pos!r}). A system that answers both halves the same way has "
                            f"told us nothing, however confidently — published as a failure.")
            print(f"  SAME LABEL    {tid}: both {pos!r}")
        else:
            print(f"  ok            {tid:20s} positive={pos!r} control={ctl!r}")


def check_lexicon(problems: list[str]) -> None:
    print("lexicons:")
    for mod, cases in LEXICONS:
        out = subprocess.run([sys.executable, str(REPO / mod), "--cases", str(REPO / cases)],
                             capture_output=True, text=True)
        tail = (out.stdout.strip().splitlines() or ["(no output)"])[-1]
        if out.returncode != 0:
            problems.append(f"{cases}: the hand labels no longer match {mod} ({tail}). The "
                            f"classifier drifted from what was pre-registered, so no verdict "
                            f"from it can be trusted.")
            print(f"  FAILED        {Path(cases).name:28s} {tail}")
        else:
            print(f"  ok            {Path(cases).name:28s} {tail}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check published results against the frozen pre-registration. Exits non-zero "
                    "when a threshold moved, a pinned file changed, a control behaved like its "
                    "positive, or a hand-labelled suite drifted.")
    ap.add_argument("--controls", action="store_true",
                    help="compare each pair's behaviour labels; a system answering both halves "
                         "alike fails")
    ap.add_argument("--lexicon", action="store_true",
                    help="replay every hand-labelled grader suite through its own door")
    args = ap.parse_args()

    if not PREREG.is_file():
        print(f"no pre-registration at {PREREG}")
        return 2
    prereg = json.loads(PREREG.read_text())
    ref = prereg_ref()
    problems: list[str] = []

    print(f"pre-registration {PREREG.relative_to(REPO)} frozen at "
          f"{ref['sha'][:8] if ref['verifiable'] else 'UNPROVABLE FROM THIS CHECKOUT'}")
    check_thresholds(prereg, ref, problems)
    check_not_run(problems)
    n = check_results_binding(prereg, problems)
    check_regrade(prereg, problems)
    if args.controls:
        check_controls(prereg, problems)
    if args.lexicon:
        check_lexicon(problems)

    print()
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"clean — graded={n}" if n else
          "clean — graded=0. Nothing was contradicted because nothing was graded; that is a "
          "state, not a pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
