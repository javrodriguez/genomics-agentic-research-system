#!/usr/bin/env python3
"""P-2 (glitch-06's ruling, 14 Oct 2026, box lane report "P-2 accepted"): no take starts while an athena suite runs or
the machine is booked. The take's memory and CPU caps leave a reserve for the host, PostgreSQL, the sidecars and the
proxies only, so a suite run beside a take could starve it or be starved.

    problems(list_text, booking_exists) -> [problem]
        Every run `athena_suite.py list` shows still in progress (its verdict "-" and not refused), every line that is
        not that command's own form (fail closed: an unreadable list is never "nothing running"), and a booking.

    gate(*, run_list, booking_path) -> () -> [problem]
        The gate a take driver checks before each launch: run_list() -> (exit code, the list's text), the booking a
        path (`.machine-reserved`: a file that exists is booked, an emptied one too).

    gate_from_env(environ) -> gate, or a reason it cannot be built
        The operator's runner names both on its own machine, never in this tree: GAP4_ATHENA_SUITE (the
        athena_suite.py the aegis checkout holds) and GAP4_MACHINE_BOOKING (that machine's `.machine-reserved`).

Standard library only. It runs one process: the list command, with the interpreter running this module.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

# athena_suite.py cmd_list's line: "%s kind=%s commit=%s launched=%s verdict=%s%s" (its scope words follow).
LIST_LINE = re.compile(r"(?P<name>\S+) kind=(?P<kind>\S+) commit=(?P<commit>\S*) launched=(?P<launched>\S+) "
                       r"verdict=(?P<verdict>\S+)(?P<rest>( .*)?)")
NOT_RUNNING_LAUNCH = ("refused",)         # a run refused before it left the Mac never ran
ENV_SUITE, ENV_BOOKING = "GAP4_ATHENA_SUITE", "GAP4_MACHINE_BOOKING"
LIST_TIMEOUT_S = 120


def problems(list_text: str, booking_exists: bool) -> list:
    out = []
    for line in (list_text or "").splitlines():
        if not line.strip():
            continue
        m = LIST_LINE.fullmatch(line.rstrip())
        if m is None:
            out.append(f"an athena_suite list line is not that command's form: {line[:120]!r}")
        elif m["verdict"] == "-" and m["launched"] not in NOT_RUNNING_LAUNCH:
            out.append(f"athena suite run {m['name']} ({m['kind']}) is still in progress (no verdict)")
    if booking_exists:
        out.append("the machine is booked (.machine-reserved exists)")
    return out


def gate(*, run_list, booking_path: str):
    if not callable(run_list):
        raise TypeError("run_list must be callable () -> (exit code, text)")
    if not isinstance(booking_path, str) or not os.path.isabs(booking_path):
        raise ValueError("booking_path must be an absolute path")

    def check() -> list:
        try:
            code, text = run_list()
        except Exception as e:  # noqa: BLE001 - an unreadable list is a problem, never "nothing running"
            return [f"athena_suite list could not run ({type(e).__name__})"]
        if code != 0:
            return [f"athena_suite list exited {code}: what runs is unknown"]
        return problems(text, os.path.lexists(booking_path))
    return check


def gate_from_env(environ=None):
    """(gate, None), or (None, why): both paths must be named, absolute and present (the booking's folder)."""
    environ = os.environ if environ is None else environ
    suite, booking = environ.get(ENV_SUITE), environ.get(ENV_BOOKING)
    if not suite or not os.path.isabs(suite) or not os.path.isfile(suite):
        return None, f"{ENV_SUITE} does not name the athena_suite.py of the operator's aegis checkout"
    if not booking or not os.path.isabs(booking) or not os.path.isdir(os.path.dirname(booking)):
        return None, f"{ENV_BOOKING} does not name the operator machine's .machine-reserved path"

    def run_list():
        c = subprocess.run([sys.executable, suite, "list"], capture_output=True, text=True, timeout=LIST_TIMEOUT_S)
        return c.returncode, c.stdout
    return gate(run_list=run_list, booking_path=booking), None
