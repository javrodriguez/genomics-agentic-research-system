#!/usr/bin/env python3
"""The round's local stand-in for CI until publication: the battery, then every lane's listed commands.

    python3 evals/gap-study-4/run_checks.py

Runs `python3 -W ignore evals/gap-study-4/test_round4.py`, then every line of every checks.d/*.txt (one file
per lane, so no two lanes edit one list): one shell command per line, run from the repository root; blank lines
and lines starting with `#` are skipped. Each command's result is printed as it finishes. The very last line is
exactly

    run_checks: <k> of <n> commands passed

(k passed of n run, the battery counted as one), and the exit is 0 only when k equals n and n is at least 1.
athena's `gars-gap4` suite kind reads that line, so its wording is fixed.

S4 (run_checks.py transferred from w1a to the w6c-w5c-nits lane, ruling S4-gap4-1): a PASSING command also
echoes its witness summary lines (ECHO_ON_PASS: test_build_draft's and test_ci_job's group lines, "red without
collateral" and "collateral totals"), as it echoes the battery's own count, so the athena log itself holds every
witness group's collateral.

Review round 3: every command runs under `bash -o pipefail`, so a pipeline fails when any stage fails (W1A3-4),
and the battery passes only with its own closing count as its last line (W1A3-3).

Home fold of review round 1: a file in checks.d that is not `<lane>.txt` in lower case, or a lane file that lists
no command, counts as one failed command (W1A-4), so a lane's checks cannot be recorded and never run. Each command
has a time limit (TIMEOUT_S), output is decoded with replacement, and anything a command raises counts as a
failure, so the closing line is always printed and always last (N1).

No model, no network, stdlib only.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CHECKS = HERE / "checks.d"
BATTERY = "python3 -W ignore evals/gap-study-4/test_round4.py"
TIMEOUT_S = 3600
# Lane pf1-checker-digest (the lane orchestrator's ruling of Mon 26 Oct 2026 on review c99f114's note): the battery
# ran in 3547.5-3595.8 s against TIMEOUT_S, so the battery command alone gets BATTERY_TIMEOUT_S. Operational headroom
# only: what is checked does not change, and every other command keeps TIMEOUT_S.
BATTERY_TIMEOUT_S = 18000
# v3-timeouts (the V3 gate, gap4-verify1-c91974a-20261114T183802Z, glitch-34's ruling under OD197): the lines that
# read the graded records (stats, result, check_results, completeness and test_stats) ran in seconds before the
# run and past TIMEOUT_S on its records, and the battery past 7200 s; the eight draft-witness groups rebuild the
# draft, whose leak sweep now reads every recorded take, for each mutant; their code did not change between the
# green battery (c2a2ef6) and H, so the time is the data's. Measured alone at H on athena (14-15 Nov 2026): stats.py --check exits 0 in 5393 s, tests/test_stats.py in 5431 s; draft-witness group 1 in 5917 s on the fixed line. The battery runs first in step 2, so its limit fires before the suite run's own cap (athena_suite_remote MAX_MINUTES_CAP, 360 minutes, step 1 included) and a slow battery fails by name; the post-run lines start about 75-90 minutes into step 2, so a hung post-run line can still reach the 360-minute run cap (the fold then is raising MAX_MINUTES_CAP in aegis ops). The battery is estimated, not measured, at about 224 minutes.
# Operational headroom only, as on 26 Oct: what is checked does not change, and every other line keeps TIMEOUT_S.
POST_RUN_TIMEOUT_S = 14400
POST_RUN_LINES = frozenset(('pf1-l2b-labelling-stats.txt:5', 'w4e-cp5-stats.txt:3', 'w4e-cp5-stats.txt:4', 'w5b-cp5-pipeline.txt:8', 'w5b-cp5-pipeline.txt:10', 'w5b-cp5-pipeline.txt:12', 'w5c-draft-ci.txt:9', 'w5c-draft-ci.txt:10', 'w5c-draft-ci.txt:11', 'w5c-draft-ci.txt:12', 'w5c-draft-ci.txt:13', 'w5c-draft-ci.txt:14', 'w5c-draft-ci.txt:15', 'w5c-draft-ci.txt:16'))


def timeout_for(where: str) -> int:
    """The time limit of the command listed at `where`: BATTERY_TIMEOUT_S for the battery, POST_RUN_TIMEOUT_S for
    the post-run lines, TIMEOUT_S for the rest."""
    if where == "test_round4":
        return BATTERY_TIMEOUT_S
    return POST_RUN_TIMEOUT_S if where in POST_RUN_LINES else TIMEOUT_S
# Lines a PASSING command's output keeps in the log, matched at the line start: the battery's run and skip count
# (review round 2) and every witness group's summary and collateral lines (S4).
ECHO_ON_PASS = ("test_round4: ", "test_build_draft witnesses", "test_ci_job witnesses", "red without collateral",
                "collateral totals")
LANE_FILE = re.compile(r"^[a-z0-9][a-z0-9-]*\.txt$")
# The battery's own closing line (review round 3 W1A3-3): the battery passes only with exit 0 AND this as its last
# line of output, at least one test run and no expected failure. A battery that exits 0 without it (a test that
# calls os._exit(0)) counts as a failed command.
BATTERY_CLOSING = re.compile(r"^test_round4: ([1-9]\d*) run, (\d+) skipped, 0 expected failures$")


def commands(folder: Path | None = None) -> list[tuple[str, str]]:
    """(where it was listed, command) for the battery and every listed line, in file order."""
    folder = CHECKS if folder is None else folder
    out = [("test_round4", BATTERY)]
    if folder.is_dir():
        for f in sorted(folder.glob("*.txt")):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                line = line.strip()
                if line and not line.startswith("#"):
                    out.append((f"{f.name}:{n}", line))
    return out


def file_problems(folder: Path | None = None) -> list[tuple[str, str]]:
    """(file, why) for every checks.d entry that would be silently skipped: a name that is not `<lane>.txt`, a
    non-file, or a lane file listing no command. Each counts as one failed command (W1A-4)."""
    folder = CHECKS if folder is None else folder
    out = []
    if folder.is_dir():
        for f in sorted(folder.iterdir()):
            if not f.is_file() or not LANE_FILE.match(f.name):
                out.append((f.name, "not a lane checks file (`<lane>.txt`, lower case); its lines would never run"))
            elif not any(l.strip() and not l.strip().startswith("#") for l in f.read_text().splitlines()):
                out.append((f.name, "lists no command"))
    return out


def summary(k: int, n: int) -> str:
    return f"run_checks: {k} of {n} commands passed"


def verdict(k: int, n: int) -> int:
    return 0 if n >= 1 and k == n else 1


def run_all(cmds: list[tuple[str, str]], cwd: Path = REPO, tally: dict | None = None) -> tuple[int, int]:
    """Run every command, counting into `tally` as each one ends, so an interrupt still leaves a true count
    (review round 2 W1A2-7): an interrupted command counts as one failed command, then the interrupt goes on."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    tally = {"k": 0, "n": 0} if tally is None else tally
    k = 0
    for where, cmd in cmds:
        tally["n"] += 1
        t0 = time.monotonic()
        try:
            p = subprocess.run(["bash", "-o", "pipefail", "-c", cmd], cwd=str(cwd), env=env, capture_output=True,
                               text=True, errors="replace", timeout=timeout_for(where))
            code, output = p.returncode, (p.stdout or "") + (p.stderr or "")
            if code == 0 and where == "test_round4":
                last = [l for l in (p.stdout or "").splitlines() if l.strip()][-1:]
                if not last or not BATTERY_CLOSING.match(last[0]):
                    code, output = "no-closing-count", output + "\nthe battery's last line is not its closing count"
        except subprocess.TimeoutExpired:
            code, output = "timeout", f"no result within {timeout_for(where)} s"
        except Exception as e:  # anything the command raises is a failure, never a lost closing line
            code, output = "error", f"{type(e).__name__}: {e}"
        except BaseException:
            print(f"FAIL [{where}] interrupted: {cmd}", flush=True)
            raise
        took = time.monotonic() - t0
        ok = code == 0
        k += ok
        tally["k"] += ok
        print(f"{'PASS' if ok else 'FAIL'} [{where}] exit {code} in {took:.1f}s: {cmd}", flush=True)
        for line in output.splitlines():
            if ok and line.startswith(ECHO_ON_PASS):
                print(f"    {line}")   # summary lines, on a pass too (review round 2; S4)
        if not ok:
            for line in output.strip().splitlines()[-20:]:
                print(f"    {line}")
    return k, len(cmds)


def main() -> int:
    tally = {"k": 0, "n": 0}
    try:
        for name, why in file_problems():
            tally["n"] += 1
            print(f"FAIL [checks.d/{name}] {why}", flush=True)
        run_all(commands(), tally=tally)
    except Exception as e:  # the closing line is printed whatever happened
        tally["n"] += 1
        print(f"FAIL [run_checks] {type(e).__name__}: {e}", flush=True)
    finally:
        # also on an interrupt: the count of what really ended, the interrupted command counted as failed
        print(summary(tally["k"], tally["n"]), flush=True)
    return verdict(tally["k"], tally["n"])


if __name__ == "__main__":
    sys.exit(main())
