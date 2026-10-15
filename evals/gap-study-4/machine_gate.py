#!/usr/bin/env python3
"""P-2 (glitch-06's ruling, 14 Oct 2026, box lane report "P-2 accepted"): no take starts while an athena suite runs.
The take's memory and CPU caps leave a reserve for the host, PostgreSQL, the sidecars and the proxies only, so a suite
run beside a take could starve it or be starved. Redesigned by the box lane under glitch-6b's ruling of 15 Oct 2026
(item 2), after the G7 finding that the first gate (harness 9425bf62) was closed forever on the Mac and fail-open on
athena (lane-reports/walk-launch-road-2026-10-15.md):

THE ATHENA GATE (the one a take driver checks before each launch; the walk runs ON athena, as javier).
    athena_problems(suite_pids, reservation, own_hold) -> [problem]
        Admits only when NO process runs under the suite account AND the athena reservation
        (/srv/aegis-handoff/machine/reserved.json, athena-reserve's file) is absent or held by THIS walk's own hold,
        matched exactly by its id (`by`). Every unreadable input is a problem, never "nothing running".
    suite_account_pids(account, proc="/proc") -> [pid] | None (None: the account or /proc cannot be read)
    read_reservation(path) -> ("absent", None) | ("held", by) | ("unreadable", why)
    athena_gate(*, account, reservation_path, own_hold, proc="/proc") -> () -> [problem]
    gate_from_env(environ) -> (gate, None) | (None, why)
        From GAP4_SUITE_ACCOUNT, GAP4_RESERVATION and GAP4_OWN_HOLD, which the launch road (box/walk_launch.py) sets
        on athena under `athena-reserve hold --by <GAP4_OWN_HOLD>`. The walk's own hold never blocks itself; anyone
        else's reservation, expired or not, does.
    The suite list is never read on athena: `athena_suite.py list` reads only the Mac's local run records, so on
    athena it is empty whatever runs (the fail-open the first gate had).

THE MAC PRE-CHECK (the launch road reads it before it ships anything; it never admits a take by itself).
    list_problems(list_text, status_of) -> [problem]
        Over `athena_suite.py list`: a line off that command's form is a problem; a run with a verdict has ended;
        `launched=refused` and `launched=busy` never ran (busy is athena's exit 4: a launch it refused); any other
        run without a verdict is read by status_of(name), the `state=` word of `athena_suite.py status <name>`, and
        is in progress unless that state is one of ENDED_STATES. A status that cannot be read is a problem.

Standard library only. The athena gate runs no process; the Mac pre-check runs only athena_suite.py's own verbs.
"""

from __future__ import annotations

import json
import os
import pwd
import re
import stat
import subprocess
import sys

# athena_suite.py cmd_list's line: "%s kind=%s commit=%s launched=%s verdict=%s%s" (its scope words follow).
LIST_LINE = re.compile(r"(?P<name>\S+) kind=(?P<kind>\S+) commit=(?P<commit>\S*) launched=(?P<launched>\S+) "
                       r"verdict=(?P<verdict>\S+)(?P<rest>( .*)?)")
# A launch that never ran: refused on the Mac before shipping, or busy (athena_suite_remote.work wrote `busy` and
# never `started`; athena_suite.py's exit 4, "athena busy").
NEVER_RAN = ("refused", "busy")
# athena_suite_remote.status's states that mean no runner is alive: done/failed (an exit record), busy (refused),
# lost (a recorded pid that is no longer alive), missing (the run folder is gone on athena). `running` and
# `prepared` (no pid yet: about to start) are in progress; any other word is unknown and so a problem.
ENDED_STATES = ("done", "failed", "busy", "lost", "missing")
STATUS_LINE = re.compile(r"run=(?P<name>\S+) state=(?P<state>\S+)( |$)")

SUITE_ACCOUNT = "athena-suite"
RESERVATION = "/srv/aegis-handoff/machine/reserved.json"
# athena-reserve's BY_RE (a byte copy of agents/runner/scheduler.py's): the hold id the reservation carries in `by`.
HOLD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,63}$")
RESERVATION_MAX_BYTES = 4 * 1024          # athena-reserve's MACHINE_FILE_MAX
ENV_ACCOUNT, ENV_RESERVATION, ENV_HOLD = "GAP4_SUITE_ACCOUNT", "GAP4_RESERVATION", "GAP4_OWN_HOLD"
STATUS_TIMEOUT_S = 120


# ------------------------------------------------------------------------------------------------ the athena gate
def suite_account_pids(account: str, proc: str = "/proc"):
    """The pids of every process the account owns, read from /proc's per-process folders; None when the account is
    unknown or /proc cannot be listed (never an empty list on doubt)."""
    try:
        uid = pwd.getpwnam(account).pw_uid
    except (KeyError, TypeError):
        return None
    try:
        names = os.listdir(proc)
    except OSError:
        return None
    pids = []
    for name in names:
        if not name.isdigit():
            continue
        try:
            st = os.stat(os.path.join(proc, name))
        except FileNotFoundError:
            continue                       # the process ended between the listing and the stat
        except OSError:
            return None
        if st.st_uid == uid:
            pids.append(int(name))
    return sorted(pids)


def read_reservation(path: str):
    """("absent", None), ("held", by) or ("unreadable", why): a regular file of at most 4 KiB holding one JSON
    object whose `by` is a hold id; anything else is unreadable."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return ("absent", None)
    except OSError as e:
        return ("unreadable", f"lstat failed ({type(e).__name__})")
    if not stat.S_ISREG(st.st_mode):
        return ("unreadable", "not a regular file")
    if st.st_size > RESERVATION_MAX_BYTES:
        return ("unreadable", "larger than 4 KiB")
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read(RESERVATION_MAX_BYTES + 1).decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as e:
        return ("unreadable", f"not one JSON object ({type(e).__name__})")
    if not isinstance(doc, dict):
        return ("unreadable", "not one JSON object")
    by = doc.get("by")
    if not isinstance(by, str) or not HOLD_ID.match(by):
        return ("unreadable", "its `by` is not a hold id")
    return ("held", by)


def athena_problems(suite_pids, reservation, own_hold) -> list:
    out = []
    if suite_pids is None:
        out.append(f"the {SUITE_ACCOUNT} account's processes cannot be read: what runs is unknown")
    elif suite_pids:
        out.append(f"{len(suite_pids)} process(es) run under the {SUITE_ACCOUNT} account: an athena suite is running")
    if not isinstance(reservation, tuple) or len(reservation) != 2:
        out.append("the athena reservation's reading is off its shape")
        return out
    kind, value = reservation
    if kind == "absent":
        pass
    elif kind == "held":
        if not (isinstance(own_hold, str) and HOLD_ID.match(own_hold) and value == own_hold):
            out.append(f"athena is reserved by another hold ({value!r}), not this walk's own")
    elif kind == "unreadable":
        out.append(f"the athena reservation cannot be read: {value}")
    else:
        out.append(f"the athena reservation's reading is unknown: {kind!r}")
    return out


def athena_gate(*, account: str, reservation_path: str, own_hold: str, proc: str = "/proc"):
    if not isinstance(account, str) or not account:
        raise ValueError("account must name the suite account")
    if not isinstance(reservation_path, str) or not os.path.isabs(reservation_path):
        raise ValueError("reservation_path must be an absolute path")
    if not isinstance(own_hold, str) or not HOLD_ID.match(own_hold):
        raise ValueError("own_hold must be a hold id (athena-reserve's BY_RE)")

    def check() -> list:
        try:
            pids = suite_account_pids(account, proc)
            reservation = read_reservation(reservation_path)
        except Exception as e:  # noqa: BLE001 - an unreadable machine is a problem, never "nothing running"
            return [f"the athena gate could not read the machine ({type(e).__name__})"]
        return athena_problems(pids, reservation, own_hold)
    return check


def gate_from_env(environ=None):
    """(gate, None), or (None, why): the suite account, the reservation's absolute path (its folder present) and this
    walk's own hold id, each named by the launch road on athena."""
    environ = os.environ if environ is None else environ
    account, path, hold = environ.get(ENV_ACCOUNT), environ.get(ENV_RESERVATION), environ.get(ENV_HOLD)
    if not account:
        return None, f"{ENV_ACCOUNT} does not name the athena suite account"
    try:
        pwd.getpwnam(account)
    except KeyError:
        return None, f"{ENV_ACCOUNT}={account!r} is no account on this machine"
    if not path or not os.path.isabs(path) or not os.path.isdir(os.path.dirname(path)):
        return None, f"{ENV_RESERVATION} does not name the athena reservation file's absolute path"
    if not hold or not HOLD_ID.match(hold):
        return None, f"{ENV_HOLD} does not carry this walk's own athena-reserve hold id"
    return athena_gate(account=account, reservation_path=path, own_hold=hold), None


# ------------------------------------------------------------------------------------------------ the Mac pre-check
def list_problems(list_text: str, status_of) -> list:
    if not callable(status_of):
        raise TypeError("status_of must be callable (run name) -> state word")
    out = []
    for line in (list_text or "").splitlines():
        if not line.strip():
            continue
        m = LIST_LINE.fullmatch(line.rstrip())
        if m is None:
            out.append(f"an athena_suite list line is not that command's form: {line[:120]!r}")
            continue
        if m["verdict"] != "-" or m["launched"] in NEVER_RAN:
            continue
        try:
            state = status_of(m["name"])
        except Exception as e:  # noqa: BLE001 - an unread status is a problem, never "ended"
            out.append(f"athena suite run {m['name']}: its status cannot be read ({type(e).__name__})")
            continue
        if state not in ENDED_STATES:
            out.append(f"athena suite run {m['name']} ({m['kind']}) is in progress or unknown (state {state!r})")
    return out


def suite_status_reader(suite: str):
    """status_of for list_problems: the `state=` word of `athena_suite.py status <name>`, run with this interpreter;
    a non-zero exit or a line off its form raises."""
    def status_of(name: str) -> str:
        c = subprocess.run([sys.executable, suite, "status", name], capture_output=True, text=True,
                           timeout=STATUS_TIMEOUT_S)
        lines = [x for x in c.stdout.splitlines() if x.strip()]
        m = STATUS_LINE.match(lines[-1]) if c.returncode == 0 and lines else None
        if m is None or m["name"] != name:
            raise RuntimeError(f"athena_suite.py status {name} exited {c.returncode} or printed no status line")
        return m["state"]
    return status_of


def mac_precheck(suite: str) -> list:
    if not isinstance(suite, str) or not os.path.isabs(suite) or not os.path.isfile(suite):
        return ["the athena_suite.py path is not an existing absolute file"]
    try:
        c = subprocess.run([sys.executable, suite, "list"], capture_output=True, text=True, timeout=STATUS_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        return [f"athena_suite list could not run ({type(e).__name__})"]
    if c.returncode != 0:
        return [f"athena_suite list exited {c.returncode}: what runs is unknown"]
    return list_problems(c.stdout, suite_status_reader(suite))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "mac-precheck":
        problems = mac_precheck(argv[1])
    elif len(argv) == 1 and argv[0] == "athena-check":
        check, why = gate_from_env()
        problems = [why] if check is None else check()
    else:
        print("usage: machine_gate.py mac-precheck <athena_suite.py> | athena-check", file=sys.stderr)
        return 2
    for p in problems:
        print(f"gate: {p}")
    print("gate: OPEN" if not problems else "gate: CLOSED")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
