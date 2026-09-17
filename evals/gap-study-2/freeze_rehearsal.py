#!/usr/bin/env python3
"""Rehearse the freeze into a throwaway clone, and run the entire gate against the frozen state, before the real one.

    python3 evals/gap-study-2/freeze_rehearsal.py            rehearse, and write verification/freeze-rehearsal-<n>.txt
    python3 evals/gap-study-2/freeze_rehearsal.py --keep     also keep the clone for reading

WHY (goal item 4, first bullet; structural lesson: rehearse the irreversible transition). Round 1 froze a task the
system under test refused at its front door, and every take on it published as a failure the model did not earn. A
one-way change switches on code paths nothing has run: the take ledger opens, the pinned files are compared with
their freeze commit, the take order exists. So the freeze is run into a throwaway copy first, and the whole gate is
run against the after-state there. freeze.py refuses `--write` in the real repository until a rehearsal record for the
current draft bytes ends `all green`.

WHAT IT DOES, in order:
  1. clones this repository at full depth into a folder under the home folder (never the OS temp folder, which round
     2's own leak controls treat as reachable), removes the clone's remote, and turns off background git maintenance
     in it (scratch_git);
  2. commits a synthetic pre-freeze review report there, `verification/prefreeze-1.md`, whose first line is the draft's
     sha256 and whose ruling is DO FREEZE: freeze.py requires a committed review that lands exactly one report, and
     the rehearsal must exercise that rule, not skip it. The report is synthetic and says so on its second line;
  3. runs `freeze.py --review-commit <that commit> --rehearsal --write` in the clone and commits the frozen file;
  4. runs the entire gate on the frozen state: the suite, `check_results.py` (default, --ledger, --controls,
     --regrade), the language guard, `costs.py --check`, `contracts.py --check`, `fixtures/check_fixture.py --all`,
     `copy_manifest.py --check`, `prereg.py --status`, the mutation battery, and `clean_clone_battery.sh --source`
     over the clone;
  5. registers the first ledger row with `takes.py --add` and commits it, so the ledger is shown to open against the
     frozen file and its session id to derive from the row's commit; then `check_results.py --ledger` once more.
  6. writes verification/freeze-rehearsal-<n>.txt: line 1 the draft's sha256, then every step with its exit code and
     the tail of its output, and the last line `all green` only when every step exited 0.

NOT DONE HERE, said plainly: the plan named a second pass over a synthetic full ledger of 108 takes. No generator
of synthetic graded takes exists in this harness, and a take the checker accepts needs the driver's own fixture
binding, markers, session id and environment record; building one would be a harness of its own. The pass is
recorded as not done in the rehearsal record rather than faked, and the ledger is exercised with one real row.

No model, no network beyond git's local clone. stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import freeze  # noqa: E402
import scratch_git  # noqa: E402
import study  # noqa: E402

DRAFT = HERE / "prereg-draft.json"
VERIFICATION = HERE / "verification"
CLONES = Path.home() / ".gap-study-2-rehearsal"
NOT_DONE = ("the synthetic full ledger of 108 takes: not done, no synthetic graded-take generator exists; the ledger "
            "was exercised with one real registered row instead")


def sh(argv: list[str], cwd: Path, env: dict | None = None, timeout: int = 3600) -> tuple[int, str]:
    r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, env=env, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


def git(clone: Path, *args: str) -> tuple[int, str]:
    return sh(["git", "-C", str(clone), "-c", "user.name=rehearsal", "-c", "user.email=rehearsal@localhost",
               "-c", "commit.gpgsign=false", *args], clone)


def next_n() -> int:
    VERIFICATION.mkdir(exist_ok=True)
    existing = sorted(VERIFICATION.glob("freeze-rehearsal-*.txt"))
    return len(existing) + 1


def make_clone(n: int) -> Path:
    CLONES.mkdir(exist_ok=True)
    clone = CLONES / f"rehearsal-{n}-{int(time.time())}"
    code, out = sh(["git", "clone", "-q", "--no-local", str(REPO), str(clone)], REPO)
    if code != 0:
        raise SystemExit(f"could not clone: {out[-500:]}")
    git(clone, "remote", "remove", "origin")
    subprocess.run(["git", "-C", str(clone), "config", scratch_git.MAINTENANCE_KEY, scratch_git.MAINTENANCE_VALUE],
                   check=True, capture_output=True)
    return clone


def main() -> int:
    ap = argparse.ArgumentParser(description="Rehearse the freeze in a throwaway clone.")
    ap.add_argument("--keep", action="store_true", help="keep the clone for reading")
    args = ap.parse_args()

    if (HERE / "prereg.json").is_file():
        print("refusing: prereg.json already exists here; there is nothing left to rehearse.")
        return 2
    code, dirty = sh(["git", "-C", str(REPO), "status", "--porcelain", "--", str(HERE)], REPO)
    if dirty.strip():
        print("refusing: the study has uncommitted changes, so the clone would not rehearse what is committed:\n" + dirty)
        return 2

    draft_sha = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
    n = next_n()
    record = VERIFICATION / f"freeze-rehearsal-{n}.txt"
    clone = make_clone(n)
    study_dir = clone / study.STUDY_REL
    env = {k: v for k, v in os.environ.items() if k != "GAP_STUDY_2_POISON_LIVE_STATE"}
    lines = [draft_sha, f"freeze rehearsal {n}, {time.strftime('%Y-%m-%d %H:%M %Z')}, draft sha256 above, "
                        f"clone of HEAD {subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()[:12]}",
             # the study tree rehearsed, as data: freeze.py requires HEAD's to be the same when it writes
             f"{freeze.REHEARSAL_TREE_PREFIX}{freeze.study_tree_sha('HEAD')}"]
    steps: list[tuple[str, int, str]] = []

    def step(name: str, argv: list[str], cwd: Path = clone, timeout: int = 3600) -> int:
        t0 = time.time()
        code, out = sh(argv, cwd, env=env, timeout=timeout)
        tail = " | ".join(out.strip().splitlines()[-3:])[:400]
        steps.append((name, code, tail))
        print(f"  [{code}] {name} ({(time.time() - t0) / 60:.1f} min): {tail[:160]}")
        return code

    try:
        # 2. the synthetic review, committed once
        # a number no earlier commit used: the review rule refuses a report path committed more than once, and the
        # seed must be the latest review
        taken = [int(m.group(1)) for p in (study_dir / "verification").glob("prefreeze-*.md")
                 for m in [__import__("re").match(r"prefreeze-(\d+)\.md$", p.name)] if m]
        report = study_dir / "verification" / f"prefreeze-{max(taken, default=0) + 1}.md"
        report.write_text(f"prereg.json sha256: {draft_sha}\n\nSYNTHETIC: a stand-in report written by freeze_rehearsal.py "
                          f"so the freeze's review-commit rule is exercised; no reviewer wrote it.\n\n"
                          f"**Ruling: DO FREEZE.**\n")
        git(clone, "add", "--", str(report.relative_to(clone)))
        git(clone, "commit", "-q", "-m", "verification: a synthetic pre-freeze review, for the rehearsal only")
        _, review_sha = git(clone, "rev-parse", "HEAD")
        # 3. the freeze, in the clone
        fz = step("freeze.py --rehearsal --write", [sys.executable, str(study_dir / "freeze.py"), "--review-commit",
                                                    review_sha.strip(), "--rehearsal", "--write"])
        if fz == 0:
            # the round-1 regrade record names the pre-registration in force by its sha, so the freeze commit
            # carries it rewritten against the frozen file (found by rehearsal 1, where the gate read a stale one)
            step("regrade_environment.py --write (the record names the frozen file)",
                 [sys.executable, f"{study.STUDY_REL}/verification/round1-regrade/regrade_environment.py", "--write"])
            git(clone, "add", "--", str((study_dir / "prereg.json").relative_to(clone)),
                f"{study.STUDY_REL}/verification/round1-regrade/environment.json")
            git(clone, "commit", "-q", "-m", "freeze: the pre-registration, rehearsed")
        # 4. the gate on the frozen state
        S = study.STUDY_REL
        for name, argv in [
            ("prereg.py --status", [sys.executable, f"{S}/prereg.py", "--status"]),
            ("copy_manifest.py --check", [sys.executable, f"{S}/copy_manifest.py", "--check"]),
            ("test_harness.py", [sys.executable, f"{S}/test_harness.py"]),
            ("contracts.py --check", [sys.executable, f"{S}/contracts.py", "--check"]),
            ("fixtures/check_fixture.py --all", [sys.executable, f"{S}/fixtures/check_fixture.py", "--all"]),
            ("lint_language.py", [sys.executable, f"{S}/lint_language.py", f"{S}/"]),
            ("check_results.py", [sys.executable, f"{S}/check_results.py"]),
            ("check_results.py --ledger", [sys.executable, f"{S}/check_results.py", "--ledger"]),
            ("check_results.py --controls", [sys.executable, f"{S}/check_results.py", "--controls"]),
            ("check_results.py --regrade", [sys.executable, f"{S}/check_results.py", "--regrade"]),
            ("costs.py --check", [sys.executable, f"{S}/costs.py", "--check"]),
            ("test_harness.py --mutations", [sys.executable, f"{S}/test_harness.py", "--mutations"]),
            ("clean_clone_battery.sh --source <clone>", ["bash", f"{S}/clean_clone_battery.sh", "--source", str(clone)]),
        ]:
            step(name, argv)
        # 5. the first ledger row, registered and committed against the frozen file
        first = json.loads((study_dir / "prereg.json").read_text())["take_order"]
        axis, cells = next(iter(first.items()))
        task, half, model, take = cells[0]
        add = step("takes.py --add (first row of the take order)",
                   [sys.executable, f"{S}/takes.py", "--add", "--task", task, "--half", half, "--model", model,
                    "--take", str(take)])
        if add == 0:
            git(clone, "add", "--", f"{S}/takes.json")
            git(clone, "commit", "-q", "-m", "take: row 0 registered, rehearsal")
            step("check_results.py --ledger (one row)", [sys.executable, f"{S}/check_results.py", "--ledger"])
    finally:
        if not args.keep:
            shutil.rmtree(clone, ignore_errors=True)

    lines.append("")
    for name, code, tail in steps:
        lines.append(f"[{code}] {name}")
        lines.append(f"     {tail}")
    lines.append("")
    lines.append("not done: " + NOT_DONE)
    lines.append("")
    all_green = all(code == 0 for _, code, _ in steps) and bool(steps)
    lines.append("all green" if all_green else "NOT all green: " + ", ".join(n for n, c, _ in steps if c != 0))
    text = "\n".join(lines) + "\n"
    home = str(Path.home())
    if home in text or str(REPO) in text:
        text = text.replace(str(REPO), "<repo>").replace(home, "<home>")
    record.write_text(text)
    print(f"\nwrote {record.relative_to(REPO)}: {'all green' if all_green else 'NOT all green'}")
    return 0 if all_green else 1


if __name__ == "__main__":
    raise SystemExit(main())
