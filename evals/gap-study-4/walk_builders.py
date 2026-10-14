#!/usr/bin/env python3
"""The walk runner's production builders and its command line (lane w12b-walk-builders; next-slices plan of 12 Oct,
section 1 item 5, the half that fakes can prove; Q-w7b-3).

    python3 evals/gap-study-4/walk_runner.py --walk <id> --task <task> --half <half> --wording <w> --arm <arm>
        --model <model> --reason <why>
        refuses (exit 2) while any builder or real-box value below is missing, naming each one and why

WHAT IS BUILT HERE (glitch-2f's assignment under Javier's standing delegation, Tue 13 Oct 2026):

  walk_identity       ruling D2: session_id = uuid5(takes.namespace(), "walk/" + <walk id>) (check_take's
                      walk_session_id, the one the launch check compares with), row and row_commit None, the source
                      rendered from the task's template, the fixture builder's record and the gars tree; exactly
                      drive.IDENTITY_KEYS, every value checked.
  login_file_by_name  the login file, checked by its NAME only: an absolute path to a regular file of mode 600, owned
                      by the reader, outside every repository, whose first bytes are `<run_take.LOGIN_VARIABLE>=`.
                      It reads exactly that many bytes and never the value: run_take.read_login reads the value at
                      exec time, and scan_record.read_login at scan time (login_secrets).
  counters_reader     the adapter's counters_for(take): run_take.counters over the folder cgroup_dir_for(take) names
                      (the folder itself is a real-box value: run_take.CALLER_PENDING["cgroup_dir"]).
  build_run_tree      the walk's checkout: drive.clean_run_tree of the pinned tree at the walk's own neutral name
                      (one commit, no remote, clean status, nothing above it); a refusal is BuilderRefused and leaves
                      nothing behind.
  build_walk_fixture  the half's fixture built inside the run tree by drive.build_take_fixture (every kind round 3
                      builds), refused by name when nothing was built, when a project fixture records no stage 01
                      exit or not the one its variant is built to reach, or another variant, or when the source the
                      operator will name does not exist afterwards.
  walk_row            the design's own row for the cell (the first in the draft's order), its slot the walk id and
                      its agent version the pinned one.
  cli                 the plumbing: refuse by name while anything is missing; else build the row, the run tree, the
                      fixture and the identity, the walk driver (drive.walk_driver(records="walks")) and its WalkRepo,
                      and run the one walk through walk_runner.run_walks; print what happened as one JSON line.
                      Exit 0 committed, 1 refused or held, 2 refused before anything was built.

WHAT STAYS MISSING (production_builders: each a Missing with its reason, so walk_runner.main refuses by name): the
DockerRuntime and every other value only the real box can tell (next-slices plan item 4), the walk token's login file
(J3, item 7), and the values the walks themselves measure (the agent version pin, routing.json's pin_profiles, the
checker's PENDING constants, the turn budgets, the run tree's exclusions in run_location). Nothing here fills any of
them: a value is either measured and recorded where it lives, or the command line refuses.

Claude walks only: walk_driver admits only the production ClaudeCodeAdapter (drive A1), so a row of another harness
is refused before anything is built. No model, no network and no spend here; the walk itself is walk_runner's.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# Every value the command line needs, in the order it reports them. A builder set holds exactly these names.
NAMES = ("runtime", "config_parent", "take_spec", "sidecar_for", "proxy", "lock_path", "hosts", "uid_map",
         "cgroup_dir_for", "rules_scanner", "login_path", "agent_version", "table", "pin_for", "design_for",
         "budgets", "run_tree_origin", "run_tree_exclude", "clock", "sleep", "ownership", "settings_guard",
         "machine_gate")
CELL = ("task", "half", "wording", "arm", "model")
# TakeSpec.resources: the take container's capacity POLICY, never a measurement (box lane report live-box-2026-10-13.md,
# "TakeSpec.resources: values only, for walk_builders' take_spec", rule R-RES from athena's capacity and three
# concurrent takes; run_take.check_spec requires memory = 3 x memory_reservation). glitch-06's queue item 1, 14 Oct 2026.
TAKE_RESOURCES = {"memory_reservation": 2 * 1024 ** 3, "memory": 6 * 1024 ** 3, "cpus": "8", "pids_limit": 4096}
NETWORK_PLACEHOLDER = "0" * 64       # a 64-hex placeholder: run_take.launch replaces it with the network it creates
TAKE_LOCKS = {"A": "box/image.lock", "O": "box/codex/image.lock", "G": "box/gemini/image.lock"}   # each arm's take image
COMMITTED = "committed"
HEX40 = re.compile(r"[0-9a-f]{40}")


class BuilderRefused(RuntimeError):
    """A builder cannot make what the walk needs. The message names the rule, never a secret's value."""


class Missing:
    """A builder or value that does not exist yet, and why (where it will come from)."""

    def __init__(self, why: str):
        if not isinstance(why, str) or not why.strip():
            raise TypeError("a missing value says why it is missing")
        self.why = why

    def __repr__(self) -> str:
        return f"Missing({self.why!r})"


# ------------------------------------------------------------------------------------------------ D2, the identity
def walk_identity(walk: str, *, source: str, fixture: dict, gars_tree_sha: str) -> dict:
    """Ruling D2: the walk's identity, exactly drive.IDENTITY_KEYS. The session id is check_take.walk_session_id's
    (uuid5 of 'walk/<id>' in takes.namespace()), the one walk_identity_problems compares at launch."""
    import check_take
    sid = check_take.walk_session_id(walk)
    if not isinstance(source, str) or not os.path.isabs(source) or os.path.normpath(source) != source:
        raise BuilderRefused(f"the walk's source {source!r} is not an absolute, normalised path")
    if not isinstance(fixture, dict) or not fixture:
        raise BuilderRefused("the walk's identity needs the fixture builder's record, and there is none")
    if not isinstance(gars_tree_sha, str) or not HEX40.fullmatch(gars_tree_sha):
        raise BuilderRefused(f"the gars tree {gars_tree_sha!r} is not a 40-hex tree id")
    return {"session_id": sid, "row": None, "row_commit": None, "source": source, "fixture": dict(fixture),
            "gars_tree_sha": gars_tree_sha}


def identity_for(prepared: dict):
    """The driver's identity_for(row): the identity prepared for the row's own walk id, a copy each call. A row whose
    walk was not prepared is refused (the launch check reads that as an identity that cannot be read)."""
    def ident(row):
        walk = row.get("walk") if isinstance(row, dict) else None
        if walk not in prepared:
            raise BuilderRefused(f"no identity was prepared for walk {walk!r}")
        return dict(prepared[walk])
    return ident


# ------------------------------------------------------------------------------------------------ the login file
def login_name(harness) -> str:
    from box import run_take as rt
    if harness not in rt.LOGIN_VARIABLE:
        raise BuilderRefused(f"harness {harness!r} has no login variable in run_take.LOGIN_VARIABLE")
    return rt.LOGIN_VARIABLE[harness]


def login_file_by_name(path, harness) -> str:
    """The login file's path, once its placement and its variable's NAME are checked. Reads exactly
    len(name) + 1 bytes (`NAME=`) and never the value; every refusal names the file and the rule. The file is opened
    with O_NOFOLLOW (a link swapped in after the check is refused) and O_NONBLOCK (a FIFO never blocks), and the opened
    descriptor's device, inode and mode must be the checked path's (W12B-R1-1)."""
    from box import run_take as rt
    name = login_name(harness)
    if not isinstance(path, str) or not os.path.isabs(path):
        raise BuilderRefused("the login file is named by an absolute path")
    try:
        st = os.lstat(path)
    except OSError:
        raise BuilderRefused(f"{path}: the login file does not exist") from None
    if not stat.S_ISREG(st.st_mode):
        raise BuilderRefused(f"{path}: the login file must be a regular file, never a link")
    if stat.S_IMODE(st.st_mode) != 0o600:
        raise BuilderRefused(f"{path}: the login file's mode must be 600")
    if st.st_uid != os.getuid():
        raise BuilderRefused(f"{path}: the login file must be owned by the reading user")
    if not rt.outside_every_repository(path):
        raise BuilderRefused(f"{path}: the login file must sit outside every repository")
    want = (name + "=").encode("ascii")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise BuilderRefused(f"{path}: the login file cannot be opened") from None
    try:
        opened = os.fstat(fd)                  # W12B-R1-1: the file read is the file checked
        if (opened.st_dev, opened.st_ino, opened.st_mode) != (st.st_dev, st.st_ino, st.st_mode):
            raise BuilderRefused(f"{path}: the login file changed between its check and its read")
        head = os.read(fd, len(want))
    finally:
        os.close(fd)
    if head != want:
        raise BuilderRefused(f"{path}: the login file does not start with {name}=")
    return path


# glitch-06's queue item 2 of 14 Oct 2026 (window 2): the walk token's file is the box's own record of it,
# run_take.WALK_LOGIN_FILES (box lane 1eb02a9e: one file per account, prepared and verified on athena), never typed here.
# The CP6 walks run on the Claude1 account's token. A tree without that record leaves login_path Missing, by name.
WALK_ACCOUNT = "claude1"


def walk_login_path():
    """The walk token's login file as the box records it (run_take.WALK_LOGIN_FILES[WALK_ACCOUNT]), or Missing while
    this tree's run_take has no such record. Only the path: prepare's login_file_by_name checks the file by NAME."""
    from box import run_take as rt
    files = getattr(rt, "WALK_LOGIN_FILES", None)
    if not isinstance(files, dict) or WALK_ACCOUNT not in files:
        return Missing(f"the walk token's login file: box/run_take.py records no WALK_LOGIN_FILES[{WALK_ACCOUNT!r}] on "
                       f"this tree (the box lane's 1eb02a9e; the hands card's Part 3, next-slices plan item 7)")
    path = files[WALK_ACCOUNT]
    if not isinstance(path, str) or not os.path.isabs(path):
        raise BuilderRefused(f"run_take.WALK_LOGIN_FILES[{WALK_ACCOUNT!r}] is not an absolute path: {path!r}")
    return path


def login_secrets(login_file: str, harness):
    """The scan's secrets(): the login value read at scan time by scan_record.read_login (never held here)."""
    from box import run_take as rt
    from box import scan_record
    name = login_name(harness)

    def secrets():
        return [("token", scan_record.read_login(login_file, name, allowed=tuple(rt.LOGIN_VARIABLE.values())))]
    return secrets


# ------------------------------------------------------------------------------------------------ the counters
# glitch-06's queue item 2 (14 Oct 2026): the take container's cgroup folder and the runtime's uid map are read at run
# time from the container's id and /proc, never typed in (measured on athena by the box lane:
# /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/user.slice/docker-<id>.scope and
# ((0,1000,1),(1,100000,65536))). Every reader refuses (BuilderRefused) anything it cannot read exactly.
_UID_MAP_LINE = re.compile(r"\s*([0-9]+)\s+([0-9]+)\s+([1-9][0-9]*)\s*")
_CID = re.compile(r"[0-9a-f]{64}")


def container_pid(runtime, take_id: str, caller_env=None) -> int:
    """The take container's init process id on the host, by `docker inspect`; a stopped container (pid 0) refuses."""
    from box import run_take as rt
    if not isinstance(take_id, str) or not _CID.fullmatch(take_id):
        raise BuilderRefused("the take container's id is not a full 64-hex id")
    c = runtime.run([rt.RUNTIME_CLIENT, "inspect", "--format", "{{.State.Pid}}", take_id],
                    env=rt.runtime_env(caller_env), timeout=rt.STEP_TIMEOUT_S)
    text = (c.stdout or "").strip()
    if c.returncode != 0 or not text.isdigit() or int(text) <= 0:
        raise BuilderRefused(f"the take container's pid cannot be read (exit {c.returncode}): the run-time readers "
                             f"refuse")
    return int(text)


def uid_map_of_pid(pid: int, *, proc: str = "/proc") -> tuple:
    """The process's user-namespace map, ((container start, host start, length), ...), from /proc/<pid>/uid_map."""
    try:
        with open(os.path.join(proc, str(int(pid)), "uid_map"), encoding="ascii") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    except (OSError, ValueError, UnicodeError) as e:
        raise BuilderRefused(f"the uid map of pid {pid} cannot be read ({type(e).__name__})") from None
    rows = [_UID_MAP_LINE.fullmatch(ln) for ln in lines]
    if not rows or not all(rows):
        raise BuilderRefused(f"the uid map of pid {pid} is empty or not (start, host start, length) lines")
    return tuple(tuple(int(x) for x in m.groups()) for m in rows)


def cgroup_dir_of_pid(pid: int, take_id: str, *, proc: str = "/proc", root: str = "/sys/fs/cgroup") -> str:
    """The process's cgroup v2 folder, from /proc/<pid>/cgroup's one `0::` line; it must be the take container's own
    scope (docker-<id>.scope) and an existing folder under `root`."""
    try:
        with open(os.path.join(proc, str(int(pid)), "cgroup"), encoding="ascii") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    except (OSError, ValueError, UnicodeError) as e:
        raise BuilderRefused(f"the cgroup of pid {pid} cannot be read ({type(e).__name__})") from None
    if len(lines) != 1 or not lines[0].startswith("0::/"):
        raise BuilderRefused(f"pid {pid} is not in exactly one cgroup v2 hierarchy")
    rel = lines[0][len("0::"):]
    if os.path.basename(rel) != f"docker-{take_id}.scope" or ".." in rel.split("/"):
        raise BuilderRefused(f"pid {pid}'s cgroup is not the take container's own scope")
    folder = os.path.join(root, rel.lstrip("/"))
    if os.path.islink(folder) or not os.path.isdir(folder):
        raise BuilderRefused(f"the take container's cgroup folder {folder} is not an existing folder")
    return folder


def run_time_readers(runtime_of, caller_env=None) -> tuple:
    """(uid_map(take), cgroup_dir_for(take)) over the runtime `runtime_of()` gives at call time; a runtime that does not
    exist yet (a Missing) refuses by name."""
    def runtime():
        r = runtime_of()
        if not callable(getattr(r, "run", None)):
            raise BuilderRefused(f"no container runtime to read the take container with: {r!r}")
        return r

    def uid_map(take):
        return uid_map_of_pid(container_pid(runtime(), take.launched.take_id, caller_env))

    def cgroup_dir_for(take):
        cid = take.launched.take_id
        return cgroup_dir_of_pid(container_pid(runtime(), cid, caller_env), cid)
    return uid_map, cgroup_dir_for


# glitch-06's queue item 3 and review NOTE S-2 (14 Oct 2026): the box's pinned rules scanner
# (rules_scanner.real_rules_scanner(), box 8ad2978a) is NOT callable; each walk builds its scan once with
# build(runtime, report_dir) over a fresh, empty report folder, and a real walk (the production builders) scans only with
# that build's product, held in a BuiltRulesScan that only walk_rules_scanner makes.
_BUILD_KEY = object()


class BuiltRulesScan:
    """The per-walk scan(paths) the pinned scanner's build(runtime, report_dir) returned (review NOTE S-2)."""

    __slots__ = ("scan", "report_dir", "source")

    def __init__(self, scan, report_dir, source, key):
        if key is not _BUILD_KEY:
            raise BuilderRefused("a BuiltRulesScan is made only by walk_rules_scanner, from a pinned scanner's build")
        self.scan, self.report_dir, self.source = scan, report_dir, source

    def __call__(self, paths):
        return self.scan(paths)


def pinned_scanner_class():
    """The box's pinned scanner class, rules_scanner.RealRulesScanner (box 8ad2978a moved it there from scan_record),
    or None while box/rules_scanner.py is not on this tree (a real walk is then refused)."""
    import importlib.util
    if importlib.util.find_spec("box.rules_scanner") is None:
        return None
    from box import rules_scanner
    return getattr(rules_scanner, "RealRulesScanner", None)


def walk_rules_scanner(scanner, runtime, report_parent, *, real: bool):
    """The walk's rules scan. real (the production builders): `scanner` must be exactly rules_scanner.RealRulesScanner
    (by class identity, never by name), built here; otherwise an injected scan(paths) is used as given, and anything with a build() is built the same way.
    Each build gets its own fresh, empty folder under report_parent (outside every repository)."""
    import tempfile
    if real:
        pinned = pinned_scanner_class()
        if pinned is None or type(scanner) is not pinned:
            raise BuilderRefused(f"a real walk scans only with the pinned scanner (rules_scanner.RealRulesScanner), "
                                 f"never {type(scanner).__module__}.{type(scanner).__name__}")
    elif callable(scanner):
        return scanner
    build = getattr(scanner, "build", None)
    if not callable(build):
        raise BuilderRefused("the rules scanner is neither a scan(paths) nor a pinned scanner to build")
    report_dir = tempfile.mkdtemp(prefix="walk-scan-", dir=report_parent)
    scan = build(runtime, report_dir)
    if not callable(scan):
        raise BuilderRefused("the pinned scanner's build did not give a scan(paths)")
    return BuiltRulesScan(scan, report_dir, scanner, _BUILD_KEY)


def counters_reader(cgroup_dir_for):
    """The adapter's counters_for(take): run_take.counters over the absolute folder cgroup_dir_for(take) names."""
    if not callable(cgroup_dir_for):
        raise BuilderRefused("cgroup_dir_for must be callable (take) -> the take container's cgroup folder")

    def counters_for(take):
        from box import run_take as rt
        folder = cgroup_dir_for(take)
        if not isinstance(folder, str) or not os.path.isabs(folder) or not os.path.isdir(folder):
            raise BuilderRefused(f"the take's cgroup folder {folder!r} is not an absolute, existing folder")
        return rt.counters(folder)
    return counters_for


# ------------------------------------------------------------------------------------------------ the run tree
def build_run_tree(walk: str, *, repo, commit: str, exclude) -> Path:
    """The walk's own checkout of `commit` (drive.clean_run_tree: git archive minus `exclude`, one neutral commit,
    named for the walk's session); any refusal or failure is BuilderRefused, and clean_run_tree leaves nothing."""
    import check_take
    import drive
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise BuilderRefused(f"the run tree's commit {commit!r} is not a 40-hex commit id")
    if not isinstance(exclude, (list, tuple)) or not all(isinstance(p, str) and p and not os.path.isabs(p)
                                                         for p in exclude):
        raise BuilderRefused("the run tree's exclusions are a list of relative paths")
    sid = check_take.walk_session_id(walk)
    try:
        return drive.clean_run_tree(commit, sid, list(exclude), Path(repo))
    except (SystemExit, Exception) as e:  # noqa: BLE001 - clean_run_tree refuses by SystemExit
        raise BuilderRefused(f"the run tree was not built: {type(e).__name__}: {e}") from None


def remove_run_tree(tree) -> str | None:
    """Remove a walk's checkout; why it could not be removed, or None."""
    try:
        shutil.rmtree(tree)
    except OSError as e:
        return f"the run tree {tree} could not be removed: {type(e).__name__}: {e}"
    return None


# ------------------------------------------------------------------------------------------------ the fixture
def build_walk_fixture(row: dict, run_tree, project: str) -> tuple[dict, str]:
    """(the fixture record, the source the operator names): the half's fixture built inside the run tree by
    drive.build_take_fixture, then checked; the source is the task's template rendered for this walk."""
    import drive
    import variants
    task = variants.load_task(row["task"])
    fx = task["halves"][row["half"]]["fixture"]
    source = variants.render_source(task["source_template"], str(run_tree), project)
    try:
        record, _ = drive.build_take_fixture(fx, Path(run_tree), project)
    except (SystemExit, Exception) as e:  # noqa: BLE001 - the round-3 builders refuse by SystemExit
        raise BuilderRefused(f"the {fx.get('kind')!r} fixture was not built: {type(e).__name__}: {e}") from None
    if not isinstance(record, dict):
        raise BuilderRefused(f"the {fx.get('kind')!r} fixture was not built (the builder said why above)")
    if fx.get("kind") == "project":
        if record.get("variant") != fx.get("variant"):
            raise BuilderRefused(f"the builder made the {record.get('variant')!r} project, not this half's "
                                 f"{fx.get('variant')!r}")
        got, want = record.get("stage01_check_exit"), record.get("stage01_expected_exit")
        if not isinstance(got, int) or not isinstance(want, int) or got != want:
            raise BuilderRefused(f"the project fixture's stage 01 exit is {got!r}, not the {want!r} its variant "
                                 f"is built to reach")
    if not os.path.exists(source):
        raise BuilderRefused(f"the fixture did not make the source the operator will name ({source})")
    return record, source


# ------------------------------------------------------------------------------------------------ the row
def walk_row(walk: str, cell: dict, agent_version: str, rows: list) -> dict:
    """The design's own row for the cell (the first in the draft's order: its pressure and repeat), as a walk row:
    its `walk` and `slot` the walk id, its agent version the pinned one."""
    if not isinstance(agent_version, str) or not agent_version:
        raise BuilderRefused("the agent version is the pinned one, a non-empty string")
    found = [r for r in rows if all(r.get(k) == cell.get(k) for k in CELL)]
    if not found:
        raise BuilderRefused(f"{[cell.get(k) for k in CELL]} is not a row of the design in force")
    row = dict(found[0], walk=walk, slot=walk)
    row["agent"] = {"harness": row["agent"]["harness"], "version": agent_version}
    return row


# ------------------------------------------------------------------------------------------------ the builder set
def take_spec_builder(root=None):
    """(row, config_dir, run_tree) -> run_take.TakeSpec: the row's arm's take image by its lock's image id (a lock that
    is not ready refuses at call time, image_lock.NotReady) and TAKE_RESOURCES; the network a placeholder."""
    from pathlib import Path

    from box import image_lock
    from box import run_take as rt
    base = Path(root) if root is not None else Path(__file__).resolve().parent

    def take_spec(row, config_dir, run_tree):
        lock = image_lock.load(str(base / TAKE_LOCKS[row["arm"]]))
        image_lock.require_ready(lock)
        return rt.TakeSpec(image=lock["image_id"], run_tree=run_tree, config_dir=config_dir,
                           network=NETWORK_PLACEHOLDER, **TAKE_RESOURCES)
    return take_spec


def take_a_spec():
    """The production take spec: built once take-a's lock is ready (an arm A walk's image), else Missing naming what
    the lock still holds PENDING. TakeSpec.resources are wired (TAKE_RESOURCES)."""
    from pathlib import Path

    from box import image_lock
    lock = image_lock.load(str(Path(__file__).resolve().parent / TAKE_LOCKS["A"]))
    held = image_lock.pending(lock)
    if held:
        return Missing(f"the take spec: take-a's image lock ({TAKE_LOCKS['A']}) is PENDING ({', '.join(held)}); "
                       f"TakeSpec.resources are wired (walk_builders.TAKE_RESOURCES)")
    return take_spec_builder()


def production_builders() -> dict:
    """The builders and values as they stand in production: built ones, and a Missing (with its reason) for each
    value only the real box, the owner or a walk can give. Nothing here fills a PENDING value."""
    import batch
    import check_take
    import drive
    import routing
    import time
    import variants
    from box import run_take as rt
    from box import scan_record
    box = "next-slices plan item 4, the real-box bring-up (Q-w7b-3)"
    out = {
        "runtime": Missing(f"the DockerRuntime, built at {box}"),
        "config_parent": Missing(f"the folder per-walk config folders are made in, outside every repository: {box}"),
        "take_spec": take_a_spec(),
        "sidecar_for": Missing(f"the sidecar launch, its image pinned and sidecar.expect bound to launched.sidecar_id "
                               f"(cp6-readiness:62): {box}"),
        "proxy": Missing(f"the egress proxy launch (box/egress, squid -k parse): {box}"),
        "lock_path": Missing(f"the take lock (box/image.lock, pinned at the bring-up): {box}"),
        "hosts": Missing(f"preflight's hosts mapping: {box}"),
        "login_path": walk_login_path(),
        "agent_version": Missing("the Claude Code version the walk runs: prereg-draft.json's version_pins are "
                                 "PENDING until a walk measures them"),
        "budgets": Missing("the turn budget (check_take.CHECKER_CONSTANTS budgets.turn_timeout_s), the quiescence cap "
                           "and the poll interval: pre-registered values not yet in the draft"),
        "run_tree_exclude": Missing("the paths the walk's checkout leaves out: check_take.CHECKER_CONSTANTS "
                                    "run_location is PENDING"),
        "clock": time.time,
        "sleep": time.sleep,
        "run_tree_origin": (drive.REPO, variants.PINNED_TREE),
    }
    pending = scan_record.pending()
    if "rules_scanner" in pending:
        out["rules_scanner"] = Missing(f"the rules scanner: {pending['rules_scanner']}")
    else:                         # box 8ad2978a: the binding is rules_scanner.real_rules_scanner(), built per walk
        from box import rules_scanner
        out["rules_scanner"] = rules_scanner.real_rules_scanner()
    table = routing.load_table()
    out["table"] = table
    import machine_gate
    check, why = machine_gate.gate_from_env()                       # P-2: the operator's machine names its paths
    out["machine_gate"] = check if check is not None else Missing(f"the P-2 machine gate: {why}")
    out["uid_map"], out["cgroup_dir_for"] = run_time_readers(lambda: out["runtime"])   # queue item 2: never typed in
    out["ownership"] = (Missing("the ownership road: box/ownership.py (the box lane's 81ede46d) is not on this tree")
                        if drive._ownership is None else drive._ownership)
    out["settings_guard"] = (Missing("the settings guard: box/settings_guard.py (the box lane's d3fd5305) is not on "
                                     "this tree") if drive._settings_guard is None else drive._settings_guard)
    out["pin_for"] = (Missing("the routing pin: routing.json's pin_profiles are empty until the walks measure them")
                      if not table.get("pin_profiles") else (lambda row: batch.expected_pin(row, table)))
    held = [p for k, v in check_take.CHECKER_CONSTANTS.items() for p in check_take._pending_paths(v, k)]
    out["design_for"] = (Missing(f"the checker's design view: its constants {held} are PENDING until a walk "
                                 f"measures them") if held else
                         (lambda row, run_tree: check_take.design_view(row, pin=out["pin_for"](row),
                                                                       run_tree=run_tree)))
    return out


def missing(builders: dict) -> list[tuple[str, str]]:
    """(name, why) for every name in NAMES that the set lacks, holds as Missing or holds as None, in NAMES' order; a
    name the set holds and NAMES does not is refused too (the set is closed)."""
    out = [(n, "absent from the builder set") for n in NAMES if n not in builders]
    out += [(n, builders[n].why) for n in NAMES if isinstance(builders.get(n), Missing)]
    out += [(n, "present but None") for n in NAMES if n in builders and builders[n] is None]   # W12B-R1-2
    out += [(n, "not a builder the command line knows") for n in sorted(set(builders) - set(NAMES))]
    order = {n: i for i, n in enumerate(NAMES)}
    return sorted(out, key=lambda nw: order.get(nw[0], len(NAMES)))


# ------------------------------------------------------------------------------------------------ the command line
def parse(argv) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="walk_runner.py", description="Run one CP6 walk end to end.")
    ap.add_argument("--walk", required=True, help="the walk id (one path segment; a retry is a new id)")
    for k in CELL:
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--reason", required=True, help="why the walk is run; committed with it")
    return ap.parse_args(argv)


def prepare(builders: dict, args) -> tuple[dict, str, Path]:
    """(the walk row, its login file, its run tree): the row from the design, the login checked by name, then the
    walk's checkout built. Nothing is built for a row of another harness or a login the name check refuses."""
    import prereg
    import walk_register
    from box import run_take as rt
    if not walk_register.WALK_ID.fullmatch(args.walk):        # W12B-R1-3: before anything is built
        raise BuilderRefused(f"the walk id {args.walk!r} is not one path segment (walk_register.WALK_ID)")
    cell = {k: getattr(args, k) for k in CELL}
    row = walk_row(args.walk, cell, builders["agent_version"], prereg.load()["rows"])
    harness = row["agent"]["harness"]
    if harness != rt.CLAUDE_CODE:
        raise BuilderRefused(f"harness {harness!r}: the walk driver admits only Claude Code (drive A1); arms O and "
                             f"G wait for their adapters' admission")
    login = login_file_by_name(builders["login_path"], harness)
    repo, commit = builders["run_tree_origin"]
    return row, login, build_run_tree(args.walk, repo=repo, commit=commit, exclude=builders["run_tree_exclude"])


def walk_driver_for(builders: dict, row: dict, login: str, tree: Path, *, real: bool = False):
    """(the identity, drive.walk_driver(records='walks') over the study folder mode_binding reads, its WalkRepo):
    the fixture built in the walk's checkout, the identity from it, every other collaborator from the builder set.
    real (the production builders): the rules scan is the pinned scanner's per-walk build, nothing else (S-2)."""
    import check_take
    import drive
    rules = walk_rules_scanner(builders["rules_scanner"], builders["runtime"], builders["config_parent"], real=real)
    project = drive.neutral_name(check_take.walk_session_id(row["walk"]))
    record, source = build_walk_fixture(row, tree, project)
    ident = walk_identity(row["walk"], source=source, fixture=record, gars_tree_sha=check_take.GARS_TREE_SHA)
    root = Path(drive._mode_binding.HERE)
    secrets = login_secrets(login, row["agent"]["harness"])
    budget_s, finalize_wait_s, poll_s = builders["budgets"]
    driver = drive.walk_driver(
        runtime=builders["runtime"], root=str(root), config_parent=builders["config_parent"],
        spec_for=lambda r, cfg: builders["take_spec"](r, cfg, str(tree)),
        sidecar_for=lambda r, ev: builders["sidecar_for"](r, ev, str(tree)), proxy=builders["proxy"],
        lock_path=builders["lock_path"], hosts=builders["hosts"], login_file=login,
        counters_for=counters_reader(builders["cgroup_dir_for"]), pin_for=builders["pin_for"],
        design_for=builders["design_for"], project_for=lambda r: project,
        identity_for=identity_for({row["walk"]: ident}), secrets=secrets, rules_scanner=rules,
        uid_map=builders["uid_map"], budget_s=budget_s, finalize_wait_s=finalize_wait_s, poll_s=poll_s,
        clock=builders["clock"], sleep=builders["sleep"], records="walks", ownership=builders["ownership"],
        settings_guard=builders["settings_guard"], machine_gate=builders["machine_gate"])
    repo = drive.WalkRepo(runtime=builders["runtime"], secrets=secrets, rules_scanner=rules,
                          root=root, repo=drive.records_repo(root))
    return ident, driver, repo


def cli(argv, builders=None, *, refusal: str) -> int:
    """walk_runner.main's body. Refuses (exit 2), naming every missing builder or value, before anything is built;
    a builder set that cannot be read (production_builders raising, a TableError say) exits 2 the same way; a walk
    id that is not one path segment and a builder that refuses also exit 2, its run tree (if any) removed; else one
    walk, end to end, through walk_runner.run_walks, exit 0 only when it was committed (1 when refused at launch or
    held). A held walk keeps its run tree for a human, as it keeps its folder; so does a walk whose run_walks raised,
    and its path is printed on its own `kept run tree:` line before the exception goes on (W12B-R1-3)."""
    real = builders is None                                    # S-2: a real walk takes the pinned scanner's build
    try:                                                       # W12B-R1-3: an unreadable value is a refusal too
        builders = production_builders() if builders is None else builders
    except Exception as e:  # noqa: BLE001
        print(f"refused: the production builders cannot be read: {type(e).__name__}: {e}", file=sys.stderr)
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    gaps = missing(builders)
    if gaps:
        for name, why in gaps:
            print(f"refused: missing {name}: {why}", file=sys.stderr)
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    args = parse(argv)
    try:
        row, login, tree = prepare(builders, args)
    except BuilderRefused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    try:
        _, driver, repo = walk_driver_for(builders, row, login, tree, real=real)
    except BaseException as e:
        left = remove_run_tree(tree)
        if not isinstance(e, BuilderRefused):
            raise
        print(f"refused: {e}" + (f"; and {left}" if left else ""), file=sys.stderr)
        return 2
    import walk_runner
    try:
        got = walk_runner.run_walks(driver, repo, [{"row": row, "reason": args.reason}], table=builders["table"])
    except BaseException:
        print(f"kept run tree: {tree} (run_walks raised; left for a human)", file=sys.stderr)   # W12B-R1-3
        raise
    state = got[0]["state"]
    kept = None if state == walk_runner.HELD else remove_run_tree(tree)
    print(json.dumps({"walk": args.walk, "results": got, "run_tree": str(tree), "run_tree_kept": kept},
                     sort_keys=True, default=str))
    return 0 if state == COMMITTED else 1
