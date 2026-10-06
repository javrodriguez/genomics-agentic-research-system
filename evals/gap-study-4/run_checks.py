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

No model, no network, stdlib only.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CHECKS = HERE / "checks.d"
BATTERY = "python3 -W ignore evals/gap-study-4/test_round4.py"


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


def summary(k: int, n: int) -> str:
    return f"run_checks: {k} of {n} commands passed"


def verdict(k: int, n: int) -> int:
    return 0 if n >= 1 and k == n else 1


def run_all(cmds: list[tuple[str, str]], cwd: Path = REPO) -> tuple[int, int]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    k = 0
    for where, cmd in cmds:
        t0 = time.monotonic()
        p = subprocess.run(cmd, shell=True, cwd=str(cwd), env=env, capture_output=True, text=True)
        took = time.monotonic() - t0
        ok = p.returncode == 0
        k += ok
        print(f"{'PASS' if ok else 'FAIL'} [{where}] exit {p.returncode} in {took:.1f}s: {cmd}", flush=True)
        if not ok:
            tail = (p.stdout + p.stderr).strip().splitlines()[-20:]
            for line in tail:
                print(f"    {line}")
    return k, len(cmds)


def main() -> int:
    k, n = run_all(commands())
    print(summary(k, n))
    return verdict(k, n)


if __name__ == "__main__":
    sys.exit(main())
