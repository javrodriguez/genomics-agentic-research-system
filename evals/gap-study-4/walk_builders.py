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
                      nothing behind. R-6 (lane vendor-admission T4 P2): a codex or gemini walk's checkout also
                      carries its CLI's native instruction file, a byte-identical copy of the pinned CLAUDE.md.
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

THE REAL-BOX BRING-UP (glitch-6b, 15 Oct 2026): runtime is run_take.DockerRuntime; hosts is proxy_conf.HOSTS; lock_path
is each harness's take lock once preflight's own loader accepts it; config_parent is the folder the operator's runner
names in GAP4_CONFIG_PARENT; the proxy (ProxyRoad) writes the walk's proxy_conf.render under it and launches the egress
lock's image as squid's measured user; agent_version is each harness's pin where prereg's version_pins and routing's
pin_profiles agree on one version; budgets and run_tree_exclude are read from check_take.CHECKER_CONSTANTS (the
first-walk bootstrap ruling's B3); sidecar_for is the stub take's sidecar launch over the sidecar lock's image and the
row's watch_list (the ruling's Addendum 2, rule W1). A per-harness value is resolved for the row (walk_row,
walk_driver_for).

WHAT STAYS MISSING (production_builders: each a Missing with its reason, so walk_runner.main refuses by name): every
value with no measured, registered or derived source on the tree.
The checker's constants are not measured by a walk: the first-walk bootstrap ruling (15 Oct 2026) sources, carries
and derives them in check_take.CHECKER_CONSTANTS, and design_for, budgets and run_tree_exclude stay Missing only
while a tree still holds them PENDING. The walk token's login file and the P-2 gate stay Missing until the box and the
operator name them. Nothing here fills any value: it is sourced where it lives, or the command line refuses.

Claude Code, Gemini (its r4-g key file, login_name GEMINI_API_KEY, the same login_secrets for the walk's driver and
its WalkRepo) and, on the lease road, Codex: a Codex row has no login file (login_name gives run_take.NO_LOGIN); prepare
refuses it while run_take.CODEX_SUBSCRIPTION_READY is closed or its lease source is missing, and its walk places the
lease (run_take.place_lease) and reads it (lease_secrets) through CodexLeaseRoad, whose secrets() the walk's driver
and its WalkRepo both get. Any other harness is refused before anything is built. No model, no network and no
spend here; the walk itself is walk_runner's.
"""
from __future__ import annotations

import argparse
import base64
import calendar
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
# Values only a row of one harness needs (the Codex lease road, glitch-06, 14 Oct 2026): known to the command line, so a
# set may hold them, but never a reason to refuse every walk; prepare refuses a Codex row while its value is missing.
ROW_NAMES = ("lease_path", "gemini_login_path")
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
# run_take.NO_LOGIN (box 41428177, 9d4bfd40): a Codex row has no environment login; its login is the lease, placed in
# the take's config folder by run_take.place_lease and read for the scans by lease_secrets (the Codex lease road).
NO_LOGIN = "-"


def login_name(harness) -> str:
    """The harness's login variable; NO_LOGIN for a Codex row (the lease road), which no login-file reader takes."""
    from box import run_take as rt
    if harness == rt.CODEX:
        return NO_LOGIN
    if harness not in rt.LOGIN_VARIABLE:
        raise BuilderRefused(f"harness {harness!r} has no login variable in run_take.LOGIN_VARIABLE")
    name = rt.LOGIN_VARIABLE[harness]
    if name == NO_LOGIN:
        raise BuilderRefused(f"harness {harness!r}: only a Codex row has no environment login")
    return name


def _no_login_file(what: str):
    raise BuilderRefused(f"a Codex row has no login file ({what}): its login is the lease (run_take.place_lease, "
                         f"walk_builders.lease_secrets)")


def login_file_by_name(path, harness) -> str:
    """The login file's path, once its placement and its variable's NAME are checked. Reads exactly
    len(name) + 1 bytes (`NAME=`) and never the value; every refusal names the file and the rule. The file is opened
    with O_NOFOLLOW (a link swapped in after the check is refused) and O_NONBLOCK (a FIFO never blocks), and the opened
    descriptor's device, inode and mode must be the checked path's (W12B-R1-1)."""
    from box import run_take as rt
    name = login_name(harness)
    if name == NO_LOGIN or path == NO_LOGIN:
        _no_login_file("login_file_by_name")
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
# The Gemini walks' key (glitch-06, 14 Oct 2026, the Gemini walk wiring): the box's r4-g record (box 1d32399b), one line
# `GEMINI_API_KEY=<the study key>`, read only by name here and by value only at exec and scan time, like Claude's.
GEMINI_WALK_ACCOUNT = "r4-g"


def walk_login_path(account: str = WALK_ACCOUNT):
    """A walk's login file as the box records it (run_take.WALK_LOGIN_FILES[account]), or Missing while this tree's
    run_take has no such record. Only the path: prepare's login_file_by_name checks the file by NAME."""
    from box import run_take as rt
    files = getattr(rt, "WALK_LOGIN_FILES", None)
    if not isinstance(files, dict) or account not in files:
        return Missing(f"the walk token's login file: box/run_take.py records no WALK_LOGIN_FILES[{account!r}] on "
                       f"this tree (the box lane's 1eb02a9e and 1d32399b; the hands card's Part 3, next-slices plan "
                       f"item 7)")
    path = files[account]
    if not isinstance(path, str) or not os.path.isabs(path):
        raise BuilderRefused(f"run_take.WALK_LOGIN_FILES[{account!r}] is not an absolute path: {path!r}")
    return path


# Round 17 B2 (plan codex2-signin-road section 1): the Codex walks' lease is the box's record of it,
# run_take.LEASE_SOURCES (Javier's Codex2 login), never typed here; place_lease reads it behind the closed gate.
LEASE_ACCOUNT = "codex2"


def lease_source_path(account: str = LEASE_ACCOUNT):
    """The Codex lease source as the box records it (run_take.LEASE_SOURCES[account]), or Missing while this tree's
    run_take has no such record. Only the path: place_lease checks the file."""
    from box import run_take as rt
    sources = getattr(rt, "LEASE_SOURCES", None)
    if not isinstance(sources, dict) or account not in sources:
        return Missing(f"the Codex lease source: box/run_take.py records no LEASE_SOURCES[{account!r}] on this tree; "
                       f"run_take.CODEX_SUBSCRIPTION_READY stays closed until Javier's Codex2 login (a Codex row only)")
    path = sources[account]
    if not isinstance(path, str) or not os.path.isabs(path):
        raise BuilderRefused(f"run_take.LEASE_SOURCES[{account!r}] is not an absolute path: {path!r}")
    return path


# ------------------------------------------------------------------------------------------------ the account record
# Round 10 ruling 1 (glitch-b5, 17 Oct 2026; the T4 plan's section 1a, account-email): the addresses a vendor take's
# scan sweeps are the box's own record of them, ACCOUNT_EMAILS in the private folder that holds
# run_take.WALK_LOGIN_FILES' account folders (outside every repository, never committed, mode 600, written on the walk
# host by its operator): a JSON object with exactly ACCOUNT_EMAIL_KEYS, "operator" (the operator's own address),
# "codex" (the ChatGPT account the Codex arm signs in with) and "gemini" (the Google account that owns the r4-g key).
# Read by name at scan time, never written down; every refusal names the file and the rule, never a value.
ACCOUNT_EMAILS = "account-emails.json"
ACCOUNT_EMAIL_KEYS = ("operator", "codex", "gemini")
ACCOUNT_EMAILS_MAX_BYTES = 4096
_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_KEY_NAME = re.compile(r"[a-z][a-z0-9_-]{0,31}")


def _is_address(value) -> bool:
    from box import scan_record
    return (isinstance(value, str) and scan_record.MIN_LENGTH["email"] <= len(value) <= 254
            and _ADDRESS.fullmatch(value) is not None)


def account_emails_path() -> str:
    """The account record's path: ACCOUNT_EMAILS in the one folder that holds every run_take.WALK_LOGIN_FILES
    account folder (<folder>/<account>/<login file>). Refuses by name on a tree without that record, or when the
    account folders sit under more than one folder."""
    from box import run_take as rt
    files = getattr(rt, "WALK_LOGIN_FILES", None)
    if not isinstance(files, dict) or not files:
        raise BuilderRefused(f"the account record ({ACCOUNT_EMAILS}): box/run_take.py records no WALK_LOGIN_FILES on "
                             f"this tree, so the record's folder is unknown")
    tops = {os.path.dirname(os.path.dirname(p)) if isinstance(p, str) and os.path.isabs(p) else None
            for p in files.values()}
    if len(tops) != 1 or None in tops:
        raise BuilderRefused(f"the account record ({ACCOUNT_EMAILS}): run_take.WALK_LOGIN_FILES' account folders do "
                             f"not sit in one private folder")
    return os.path.join(tops.pop(), ACCOUNT_EMAILS)


def _unique_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError("a key occurs twice")
    return dict(pairs)


def account_emails(harness, path=None) -> tuple:
    """(the operator's address, the harness's account address) read now from the account record (ACCOUNT_EMAILS at
    account_emails_path(), or `path`), for a codex or gemini take. Refuses (BuilderRefused, naming the file and the
    rule, never a value): another harness, a missing file, a link, a mode other than 600, another owner, a file inside
    a repository, a file that is not one JSON object, an extra key, a missing key for the take's harness, and a value
    that is not an email address."""
    from box import run_take as rt
    what = f"the account record ({ACCOUNT_EMAILS})"
    if harness not in (rt.CODEX, rt.GEMINI):
        raise BuilderRefused(f"{what}: harness {harness!r} sweeps no account address (only codex and gemini takes do)")
    where = account_emails_path() if path is None else path
    if not isinstance(where, str) or not os.path.isabs(where):
        raise BuilderRefused(f"{what} is named by an absolute path")
    try:
        rec = os.lstat(where)
    except OSError:
        raise BuilderRefused(f"{where}: {what} does not exist; the walk host's operator writes it before the first "
                             f"vendor walk, and until then every codex and gemini take refuses") from None
    if not stat.S_ISREG(rec.st_mode):
        raise BuilderRefused(f"{where}: {what} must be a regular file, never a link")
    if stat.S_IMODE(rec.st_mode) != 0o600:
        raise BuilderRefused(f"{where}: the account record's mode must be 600 ({ACCOUNT_EMAILS})")
    if rec.st_uid != os.getuid():
        raise BuilderRefused(f"{where}: {what} must be owned by the reading user")
    if not rt.outside_every_repository(where):
        raise BuilderRefused(f"{where}: {what} must sit outside every repository")
    try:
        fd = os.open(where, os.O_NOFOLLOW | os.O_NONBLOCK | os.O_RDONLY)
    except OSError:
        raise BuilderRefused(f"{where}: {what} cannot be opened") from None
    try:
        opened = os.fstat(fd)                  # the file read is the file checked
        if (opened.st_ino, opened.st_dev, opened.st_mode) != (rec.st_ino, rec.st_dev, rec.st_mode):
            raise BuilderRefused(f"{where}: {what} changed between its check and its read")
        raw = os.read(fd, ACCOUNT_EMAILS_MAX_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > ACCOUNT_EMAILS_MAX_BYTES:
        raise BuilderRefused(f"{where}: {what} is larger than {ACCOUNT_EMAILS_MAX_BYTES} bytes")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys)
    except (UnicodeError, ValueError):
        raise BuilderRefused(f"{where}: {what} is not one JSON object with unique keys") from None
    if not isinstance(doc, dict):
        raise BuilderRefused(f"{where}: {what} is not one JSON object")
    extra = [k for k in doc if k not in ACCOUNT_EMAIL_KEYS]
    if extra:
        named = ", ".join(json.dumps(k) if _KEY_NAME.fullmatch(k) else "a key that is not a name" for k in extra)
        raise BuilderRefused(f"{where}: {what} holds keys other than {', '.join(map(json.dumps, ACCOUNT_EMAIL_KEYS))}: "
                             f"{named}")
    for key in ("operator", harness):
        if key not in doc:
            raise BuilderRefused(f'{where}: {what} holds no key "{key}" (a {harness} take sweeps it)')
    for key, value in doc.items():
        if not _is_address(value):
            raise BuilderRefused(f'{where}: {what}\'s "{key}" value is not an email address')
    return doc["operator"], doc[harness]


def email_pairs(harness) -> list:
    """Round 10 ruling 4 (the T4 plan's sections 1a and 9, account-email): a codex or gemini take's ("email", value)
    pairs for the scan, the operator's address then the take's account address, read from the account record now (at
    each scan) and never held here."""
    operator, account = account_emails(harness)
    return [("email", operator), ("email", account)]


def login_secrets(login_file: str, harness):
    """The scan's secrets(): the login value read at scan time by scan_record.read_login (never held here). A Gemini
    take's refuses now without the account record (round 10 ruling 2), before its walk is built, and its secrets()
    end with the record's two email pairs, read at each scan (ruling 4)."""
    from box import run_take as rt
    from box import scan_record
    if harness == rt.GEMINI:                   # round 10 ruling 2: no account record, no Gemini take
        account_emails(rt.GEMINI)
    name = login_name(harness)
    if name == NO_LOGIN or login_file == NO_LOGIN:
        _no_login_file("login_secrets")

    def secrets():
        token = [("token", scan_record.read_login(login_file, name, allowed=tuple(rt.LOGIN_VARIABLE.values())))]
        return token + email_pairs(rt.GEMINI) if harness == rt.GEMINI else token
    return secrets



def lease_secrets(auth_path: str):
    """A Codex take's secrets() (glitch-06, 14 Oct 2026): the lease's access and refresh tokens, read from the
    registered auth.json now, at take start (no lease file, no take: LoginError), and again at each scan, where a
    refreshed token is added when still present at scan time (a value refreshed and then replaced again before a scan
    is never read: the refresh residual, closed on the lease road by refreshing only on the host, between turns). A
    departure from login_secrets' "never held", named: the values read are kept for this take's scans, because a
    refresh rewrites auth.json and the first values may already be in the records. Without the account record it
    refuses before any token is read (round 10 ruling 2: no record, no Codex take); secrets() ends with the record's
    two email pairs, read at each scan (ruling 4)."""
    from box import run_take as rt
    from box import scan_record
    account_emails(rt.CODEX)                   # round 10 ruling 2: no record, no take
    seen = list(scan_record.read_lease_tokens(auth_path))

    def secrets():
        for v in scan_record.read_lease_tokens(auth_path):
            if v not in seen:
                seen.append(v)
        return [("token", v) for v in seen] + email_pairs(rt.CODEX)
    return secrets

# ------------------------------------------------------------------------------------------------ the Codex lease
# glitch-06's queue (14 Oct 2026, window 2), the box contract of live-box-2026-10-13.md ("For the harness lane: the
# run_take contract to call"): after make_config_dir and before launch, dst = run_take.place_lease(lease, cfg), then
# secrets = lease_secrets(dst), the take-start read (no lease file, no take); that one secrets() goes to both the
# walk's driver and its WalkRepo. While run_take.CODEX_SUBSCRIPTION_READY is False a Codex row stops before anything
# is written. The refresh rule (ruled): the token-refresh endpoint is never in a take's egress; a refresh happens on the
# host, between turns, and is followed by a secrets() call (CodexLeaseRoad.refreshed) that adds the refreshed values.
def codex_gate_problem():
    """None while run_take's Codex lease gate is open; else why a Codex row stops (closed, or absent from this tree)."""
    from box import run_take as rt
    ready = getattr(rt, "CODEX_SUBSCRIPTION_READY", None)
    if ready is True:
        return None
    if ready is None:
        return "the box's Codex lease gate (run_take.CODEX_SUBSCRIPTION_READY) is not on this tree"
    return f"the Codex lease gate is closed: {getattr(rt, 'CODEX_SUBSCRIPTION_NOT_READY', 'not ready')}"


# Round 17 B5 (plan codex2-signin-road section 2): the walk-start token check, not a refresh. Inside a take the token
# refresh endpoint is not in egress, and the pinned Codex refreshes by itself when the access token's JWT exp is within
# 5 minutes, or, with no readable exp, when last_refresh is older than 8 days (codex-rs/login/src/auth/manager.rs,
# should_refresh_proactively, at rust-v0.162.1). So a walk starts only on a lease whose access token outlives the
# walk's budget by LEASE_START_MARGIN_S and whose last_refresh is at most LEASE_REFRESH_MAX_AGE_S old; a refused walk
# asks for a fresh `codex login --device-auth`, never a hand refresh.
LEASE_START_MARGIN_S = 15 * 60
LEASE_REFRESH_MAX_AGE_S = 7 * 24 * 3600
_RFC3339 = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]{1,9})?"
                      r"(Z|[+-][0-9]{2}:[0-9]{2})")


def walk_budget_s(script, budgets) -> int:
    """A walk's longest run in seconds: every turn its script can send (each step, and its recovery when it has one),
    each at the turn budget plus the quiescence cap (budgets: drive.walk_driver's budget_s, finalize_wait_s, poll_s)."""
    turn_s, finalize_s = budgets[0], budgets[1]
    return sum(1 + bool(step.get("recovery")) for step in script) * (turn_s + finalize_s)


def _jwt_exp(token):
    """The `exp` claim of a JWT-shaped token, as Codex's parse_jwt_expiration reads it, or None."""
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        return None
    try:
        claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    except ValueError:
        return None
    exp = claims.get("exp") if isinstance(claims, dict) else None
    return exp if isinstance(exp, (int, float)) and not isinstance(exp, bool) else None


def _rfc3339_s(text):
    """An RFC 3339 time (chrono's, nanoseconds and an offset admitted) as seconds since the epoch, or None."""
    m = _RFC3339.fullmatch(text) if isinstance(text, str) else None
    if m is None:
        return None
    y, mo, d, h, mi, s = (int(g) for g in m.groups()[:6])
    try:
        t = calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0))
    except (ValueError, OverflowError):
        return None
    tz = m.group(8)
    off = 0 if tz == "Z" else (1 if tz[0] == "+" else -1) * (int(tz[1:3]) * 3600 + int(tz[4:6]) * 60)
    return t + float(m.group(7) or 0) - off


def lease_freshness_problem(path: str, *, now: float, walk_s) -> str | None:
    """Why the lease at `path` cannot start a walk of `walk_s` seconds at `now`, or None: its access token's exp
    leaves less than walk_s plus LEASE_START_MARGIN_S, its last_refresh is older than LEASE_REFRESH_MAX_AGE_S, or
    either is unreadable. Read from the host-owned source before anything is placed; the text names the rule and the
    minutes, never a token."""
    if not isinstance(walk_s, int) or isinstance(walk_s, bool) or walk_s <= 0:
        return f"no walk budget to check the lease's time left against: {walk_s!r}"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as fh:
            doc = json.loads(fh.read(1024 * 1024 + 1).decode("utf-8"))
    except (OSError, ValueError):
        return "the lease cannot be read as auth.json"
    tokens = doc.get("tokens") if isinstance(doc, dict) else None
    exp = _jwt_exp(tokens.get("access_token") if isinstance(tokens, dict) else None)
    if exp is None:
        return "the lease's access token carries no readable exp claim: a fresh codex login --device-auth is needed"
    left, need = exp - now, walk_s + LEASE_START_MARGIN_S
    if left < need:
        return (f"the lease's access token has {int(left // 60)} minutes left, under the walk's {walk_s // 60} "
                f"minutes plus {LEASE_START_MARGIN_S // 60}: a fresh codex login --device-auth is needed")
    refreshed = _rfc3339_s(doc.get("last_refresh"))
    if refreshed is None:
        return "the lease's last_refresh is missing or not an RFC 3339 time: a fresh codex login --device-auth is needed"
    if now - refreshed > LEASE_REFRESH_MAX_AGE_S:
        return (f"the lease's last_refresh is {int((now - refreshed) // 86400)} days old, past "
                f"{LEASE_REFRESH_MAX_AGE_S // 86400}: a fresh codex login --device-auth is needed")
    return None


class CodexLeaseRoad:
    """One Codex take's lease: placed into the take's config folder by run_take.place_lease (place, the driver's
    spec_for hook, after make_config_dir and before the settings baseline, the grant and the launch), then read at
    once by lease_secrets. secrets() is that read's secrets(), handed to the driver and to WalkRepo alike; before a
    lease is placed it refuses, so no scan ever runs without the lease's values. uid_map(take) is the walk's run-time
    uid map reader (production: run_time_readers', uid_map_of_pid over the take container's /proc entry): the login
    file of a take is place_lease's placement record bound to it (round 17 B3), and with no reader there is none.
    walk_s and clock are the walk's budget (walk_budget_s) and the builders' clock: place checks the lease's time left
    against them before anything is written (round 17 B5), and without them nothing is placed."""

    def __init__(self, lease_src, uid_map=None, walk_s=None, clock=None):
        if not isinstance(lease_src, str) or not os.path.isabs(lease_src):
            raise BuilderRefused(f"the Codex lease source is not an absolute path: {lease_src!r}")
        from box import run_take as rt
        account_emails(rt.CODEX)                # round 10 ruling 2: no record, no walk
        self.lease_src, self.placed, self._secrets, self.uid_map = lease_src, None, None, uid_map
        self.walk_s, self.clock = walk_s, clock

    def place(self, config_dir: str) -> str:
        from box import run_take as rt
        gate = codex_gate_problem()                     # review NIT 4: the gate first, before place_lease
        if gate:
            raise BuilderRefused(f"the Codex lease is not placed: {gate}")
        place = getattr(rt, "place_lease", None)
        read = globals().get("lease_secrets")          # the box lane's take-start reader (b9f876b5), this module's
        if not callable(place) or not callable(read):
            raise BuilderRefused("the box's lease road (run_take.place_lease, walk_builders.lease_secrets) is not on "
                                 "this tree")
        if self.placed is not None:
            raise BuilderRefused(f"a lease is already placed for this walk: {self.placed.path}")
        if not callable(self.clock):
            raise BuilderRefused("the Codex lease is not placed: no clock to check its time left by")
        stale = lease_freshness_problem(self.lease_src, now=self.clock(), walk_s=self.walk_s)
        if stale:
            raise BuilderRefused(f"the Codex lease is not placed: {stale}")
        placement = place(self.lease_src, config_dir)
        self._secrets = read(placement.path)            # the take-start read: no lease file, no take
        self.placed = placement
        return placement.path

    def login_file_for(self, take):
        """The take's login file for the Codex exec (box 1e10e320's exec branch checks the placed cfg/auth.json): the
        placement record of the lease placed for this walk, refused before placement (review MINOR 1 of
        1f032586..27ade10a), bound to the take's uid map as the walk's reader reads it at run time (round 17 B3: after
        the grant the host checks the folder's owner against the agent's mapped uid, never a typed one)."""
        if self.placed is None:
            raise BuilderRefused("no lease placed: a Codex take's login file exists only after run_take.place_lease")
        from box import run_take as rt
        if not callable(self.uid_map):
            raise BuilderRefused("no uid map reader: a Codex take's login file is bound to the take's uid map")
        return rt.lease_for_take(self.placed, self.uid_map(take))

    def secrets(self) -> list:
        if self._secrets is None:
            raise BuilderRefused("no lease placed: a Codex take's secrets exist only after run_take.place_lease")
        return self._secrets()

    def refreshed(self) -> list:
        """After a host-side refresh, between turns (the refresh rule): the take's secrets, the refreshed values
        added (lease_secrets re-reads auth.json and keeps every value it has read)."""
        return self.secrets()


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
        if type(scanner) is not pinned:              # type() is never None: no pinned class refuses every scanner
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
def build_run_tree(walk: str, *, repo, commit: str, exclude, harness=None) -> Path:
    """The walk's own checkout of `commit` (drive.clean_run_tree: git archive minus `exclude`, one neutral commit,
    named for the walk's session), and for a codex or gemini `harness` its native instruction file (R-6,
    place_instruction_file); any refusal or failure is BuilderRefused, and nothing is left behind."""
    import check_take
    import drive
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise BuilderRefused(f"the run tree's commit {commit!r} is not a 40-hex commit id")
    if not isinstance(exclude, (list, tuple)) or not all(isinstance(p, str) and p and not os.path.isabs(p)
                                                         for p in exclude):
        raise BuilderRefused("the run tree's exclusions are a list of relative paths")
    sid = check_take.walk_session_id(walk)
    try:
        tree = drive.clean_run_tree(commit, sid, list(exclude), Path(repo))
    except (SystemExit, Exception) as e:  # noqa: BLE001 - clean_run_tree refuses by SystemExit
        raise BuilderRefused(f"the run tree was not built: {type(e).__name__}: {e}") from None
    try:
        place_instruction_file(tree, harness, repo=repo, commit=commit, session_id=sid, exclude=list(exclude))
        place_agent_home(tree, harness, session_id=sid, exclude=list(exclude))
    except BaseException:
        shutil.rmtree(tree, ignore_errors=True)
        raise
    return tree


# ------------------------------------------------------------------------------------------------ R-6
# glitch-b5's ruling R-6 (Sat 17 Oct 2026, about 12:35 EDT, under Javier's delegation; lane vendor-admission T4 P2):
# every arm gets byte-identical instructions under its CLI's native name, AGENTS.md for Codex and GEMINI.md for Gemini
# (box/take_config.INSTRUCTION_FILES), each equal to the pinned tree's CLAUDE.md and bound by sha256 to it; no
# configured fallback name is used (take_config writes none). drive.clean_run_tree takes no edit (drive.py is in both
# native-reader source lists), so the copy is placed here, after it, into the checkout's one commit (amended, so the
# checkout keeps one commit, its neutral subject and a clean status), and drive.run_tree_problems is read again on the
# built tree. Round 10 ruling 3 (glitch-b5, Sat 17 Oct 2026): R-6 covers every CLAUDE.md of the checkout, gars/CLAUDE.md
# included: each gets the native file beside it, its own bytes bound by sha256; each CLI loads nested files by its own
# documented rules, so the loading scope and timing are NOT COMPARABLE and the content SAME (lane-reports'
# vendor-T4-TABLE.md).
def place_instruction_file(tree: Path, harness, *, repo, commit: str, session_id: str, exclude: list):
    """R-6: beside every CLAUDE.md of the checkout (round 10 ruling 3), the harness's native instruction file with that
    CLAUDE.md's bytes at `commit`, committed into the checkout's one commit; its name, or None for a harness that reads
    CLAUDE.md itself. Refuses (BuilderRefused) a checkout with no root CLAUDE.md, a commit already carrying the name
    anywhere in the checkout, or a copy whose sha256 is not its CLAUDE.md's."""
    import hashlib
    import subprocess
    import drive
    from box import take_config
    name = take_config.INSTRUCTION_FILES.get(harness)
    if name is None:
        return None
    listed = subprocess.run(["git", "-C", str(tree), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
                            capture_output=True, check=True).stdout.decode("utf-8").split("\0")
    sources = sorted(p for p in listed if p == "CLAUDE.md" or p.endswith("/CLAUDE.md"))
    if "CLAUDE.md" not in sources:
        raise BuilderRefused(f"the pinned tree carries no root CLAUDE.md, so {harness}'s {name} has nothing to copy")
    carried = [p for p in listed if p == name or p.endswith("/" + name)]
    if carried:
        raise BuilderRefused(f"the pinned tree already carries {name} ({', '.join(carried)}): {harness} would read "
                             f"instructions the other arms are not given")
    placed = []
    for rel in sources:
        got = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{rel}"], capture_output=True)
        if got.returncode != 0:
            raise BuilderRefused(f"the pinned commit carries no {rel}, so {harness}'s copy beside it has no source")
        pinned = got.stdout
        dest = rel[:-len("CLAUDE.md")] + name
        target = Path(tree) / dest
        if os.path.lexists(target):
            raise BuilderRefused(f"the checkout already holds {dest}")
        target.write_bytes(pinned)
        placed.append((dest, hashlib.sha256(pinned).hexdigest()))
    # -f for exactly the placed paths (round 18 B13, practice walk w-o1): the pinned GARS tree's own .gitignore lists
    # AGENTS.md (844a4ce0 line 74), and a plain add of an ignored path exits 1; nothing else the .gitignore covers
    # is added, and the exclusions never reached the checkout (drive.clean_run_tree). Each path is read literally
    # (glitch-26's ruling R-FB2, review vendor-r18-b12b13-0094246 NIT 3): a folder name git would read as pathspec
    # magic or a glob adds only its own placed copy. The per-path :(literal) prefix is git --literal-pathspecs.
    for args in (("add", "-f", "--", *[":(literal)" + d for d, _ in placed]),
                 ("commit", "-q", "--amend", "--no-verify", "--no-edit"),
                 ):
        subprocess.run(["git", "-C", str(tree), *args], check=True, capture_output=True)
    for dest, want in placed:
        committed = subprocess.run(["git", "-C", str(tree), "show", f"HEAD:{dest}"], capture_output=True).stdout
        if (hashlib.sha256(committed).hexdigest() != want
                or hashlib.sha256((Path(tree) / dest).read_bytes()).hexdigest() != want):
            raise BuilderRefused(f"{dest} in the checkout is not its CLAUDE.md's bytes (sha256 {want[:12]})")
    problems = drive.run_tree_problems(Path(tree), session_id, exclude)
    if problems:
        raise BuilderRefused(f"the checkout with {name} placed: {'; '.join(problems)}")
    above = inherited_instruction_files(tree)
    if above:
        raise BuilderRefused(f"an instruction file above the checkout ({', '.join(above)}): {harness} could read "
                             "instructions the other arms are not given")
    return name


def place_agent_home(tree: Path, harness, *, session_id: str, exclude: list):
    """R-H5 (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026): for a codex or gemini checkout, the agent's
    own HOME, box/run_take.RUN_TREE_HOMEDIR, beside the take's temp folder: an empty folder of mode 700, git-excluded
    like .tmp (so what the agent's tools write there never reaches the status it is shown), and the run tree's, so the
    ownership grant gives it to the agent with the run tree. Its name, or None for a Claude Code checkout, whose HOME
    is the config mount (arm A's row is byte-unchanged). drive.py is in the native readers' source lists, so the folder
    is made here, after drive.clean_run_tree, and drive.run_tree_problems is read again on the built tree."""
    import subprocess
    import drive
    from box import run_take as rt
    if harness not in (rt.CODEX, rt.GEMINI):
        return None
    name = rt.RUN_TREE_HOMEDIR
    home = Path(tree) / name
    if os.path.lexists(home):
        raise BuilderRefused(f"the checkout already holds {name}, the agent's HOME")
    with (Path(tree) / ".git" / "info" / "exclude").open("a") as fh:
        fh.write(f"{name}/\n")
    home.mkdir(mode=0o700)
    os.chmod(home, 0o700)                   # whatever the builder's umask
    if subprocess.run(["git", "-C", str(tree), "check-ignore", "-q", f"{name}/probe"],
                      capture_output=True).returncode != 0:
        raise BuilderRefused(f"the agent's HOME {name}/ is not git-excluded, so what its tools write would show in "
                             f"the git status the agent is shown")
    problems = drive.run_tree_problems(Path(tree), session_id, exclude)
    if problems:
        raise BuilderRefused(f"the checkout with the agent's HOME {name}/ made: {'; '.join(problems)}")
    return name


# Every instruction-file name a CLI of the study reads (Claude Code's, and R-6's native names in take_config).
INSTRUCTION_FILE_NAMES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")


def inherited_instruction_files(tree) -> list:
    """Every file or link named in INSTRUCTION_FILE_NAMES in a folder above the checkout (review c-6302fd3 NIT 7):
    drive.no_inherited_instructions, which run_tree_problems runs, reads CLAUDE.md alone, and drive.py is in the native
    readers' source lists, so a vendor checkout's other names are checked here."""
    return [str(p / n) for p in Path(tree).resolve().parents for n in INSTRUCTION_FILE_NAMES if os.path.lexists(p / n)]


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
    found = [r for r in rows if all(r.get(k) == cell.get(k) for k in CELL)]
    if not found:
        raise BuilderRefused(f"{[cell.get(k) for k in CELL]} is not a row of the design in force")
    if isinstance(agent_version, PerHarness):              # production: the row's own harness's pinned version
        agent_version = agent_version.for_harness(found[0]["agent"]["harness"])
    if not isinstance(agent_version, str) or not agent_version:
        raise BuilderRefused("the agent version is the pinned one, a non-empty string")
    row = dict(found[0], walk=walk, slot=walk)
    row["agent"] = {"harness": row["agent"]["harness"], "version": agent_version}
    return row


# ------------------------------------------------------------------------------------------------ the builder set
def take_spec_builder(root=None):
    """(row, config_dir, run_tree) -> run_take.TakeSpec: the row's arm's take image by its lock's image id (a lock that
    is not ready refuses at call time, image_lock.NotReady) and TAKE_RESOURCES; the network a placeholder."""
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
    from box import image_lock
    lock = image_lock.load(str(Path(__file__).resolve().parent / TAKE_LOCKS["A"]))
    held = image_lock.pending(lock)
    if held:
        return Missing(f"the take spec: take-a's image lock ({TAKE_LOCKS['A']}) is PENDING ({', '.join(held)}); "
                       f"TakeSpec.resources are wired (walk_builders.TAKE_RESOURCES)")
    return take_spec_builder()


# ------------------------------------------------------------------------------------------------ the real-box bring-up
# glitch-6b (15 Oct 2026), the first Claude walk's critical path: the bring-up values come from the same box functions
# the box's stub take drives on the real box (its "WHAT RUNS UNMODIFIED" list) and the box lane's committed, measured
# records only (the image locks through preflight's own loaders, proxy_conf's rendered configuration, user and hosts).
# A value with no measured or registered source stays Missing, by name. A value that differs by the row's harness is a
# PerHarness (or a ProxyRoad), resolved for the row in walk_driver_for (and, for agent_version, in walk_row).
CONFIG_PARENT_ENV = "GAP4_CONFIG_PARENT"
BOX_DIR = Path(__file__).resolve().parent / "box"


class PerHarness:
    """A production value that differs by the row's harness: {harness: value or Missing}. for_harness(h) gives the
    harness's value, or refuses (BuilderRefused) naming why it is missing; a harness it does not name is refused."""

    def __init__(self, what: str, values: dict):
        if not isinstance(what, str) or not what or not isinstance(values, dict) or not values:
            raise TypeError("a PerHarness names what it holds and holds a value for at least one harness")
        self.what, self.values = what, dict(values)

    def for_harness(self, harness: str):
        if harness not in self.values:
            raise BuilderRefused(f"{self.what}: no value for harness {harness!r}")
        v = self.values[harness]
        if isinstance(v, Missing) or v is None:
            raise BuilderRefused(f"{self.what} for harness {harness!r} is missing: "
                                 f"{v.why if isinstance(v, Missing) else 'None'}")
        return v

    def __repr__(self) -> str:
        return f"PerHarness({self.what!r}, {self.values!r})"


def config_parent_from_env(environ=None):
    """The folder per-walk config folders (and each walk's proxy configuration) are made in: named by the operator's
    runner on its own machine (GAP4_CONFIG_PARENT, as machine_gate's GAP4_* paths are), never in this tree. It must be
    a normalised absolute path to a folder (never a link) owned by the caller, writable by no group or other, and
    outside every repository, the rule stub_take applies to its scratch parent. Missing when unset; BuilderRefused when set and off the rule."""
    from box import run_take as rt
    env = os.environ if environ is None else environ
    path = env.get(CONFIG_PARENT_ENV)
    if path is None or path == "":
        return Missing(f"the folder per-walk config folders are made in: the operator's runner names it in "
                       f"{CONFIG_PARENT_ENV} on its own machine (an owned folder outside every repository)")
    try:
        rt._abs_path(path, CONFIG_PARENT_ENV)
    except rt.Refused as e:
        raise BuilderRefused(str(e)) from None
    if os.path.islink(path) or not os.path.isdir(path):
        raise BuilderRefused(f"{CONFIG_PARENT_ENV} is not a folder (a link is refused)")
    st = os.stat(path)
    if st.st_uid != os.getuid():
        raise BuilderRefused(f"{CONFIG_PARENT_ENV} is not owned by the caller")
    if st.st_mode & 0o022:
        raise BuilderRefused(f"{CONFIG_PARENT_ENV} is writable by its group or by others "
                             f"(mode {oct(stat.S_IMODE(st.st_mode))})")
    outside = rt.outside_every_repository(path)
    if not outside:
        raise BuilderRefused(f"{CONFIG_PARENT_ENV} sits inside a repository")
    return path


def take_lock_paths(box_dir=None) -> PerHarness:
    """Each harness's take lock (preflight.TAKE_LOCK_DIRS under box/), given only once preflight's own loader accepts
    it (load_take_lock: its closed schema, its own take image, require_ready); else Missing naming why."""
    from box import preflight
    from box import run_take as rt
    base = Path(box_dir) if box_dir is not None else BOX_DIR
    dirs = getattr(preflight, "TAKE_LOCK_DIRS", None)
    out = {}
    for harness in (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI):
        if not isinstance(dirs, dict):
            out[harness] = Missing("the take lock: preflight.TAKE_LOCK_DIRS (the box lane's per-harness locks) is "
                                   "not on this tree")
            continue
        path = str(base / dirs[preflight.TAKE_IMAGE[harness]] / "image.lock") if dirs[preflight.TAKE_IMAGE[harness]] \
            else str(base / "image.lock")
        try:
            preflight.load_take_lock(path, harness=harness)
        except Exception as e:  # noqa: BLE001 - every refusal of the loader is a reason, by its own words
            out[harness] = Missing(f"the {harness} take lock ({os.path.relpath(path, base)}) is not ready: "
                                   f"{type(e).__name__}: {str(e)[:200]}")
            continue
        out[harness] = path
    return PerHarness("the take lock", out)


class ProxyRoad:
    """The egress proxy of one walk (run_take.ProxyLaunch), as the stub take builds it: proxy_conf.render(harness)
    written, checked, as proxy.conf (mode 644) in a fresh 0700 folder under the config parent, the egress lock's image
    id, proxy_conf's CONF_PATH, COMMAND and USER (squid's package user, measured from the egress image, 14 Oct 2026),
    run_take.PROXY_ALIAS. for_harness writes the walk's configuration and gives its ProxyLaunch."""

    def __init__(self, config_parent: str, image: str):
        self.config_parent, self.image = config_parent, image

    def text_for(self, harness: str) -> str:
        """The harness's rendered configuration (render refuses a text its own check does not pass), never written."""
        from box.egress import proxy_conf
        try:
            return proxy_conf.render(harness)
        except proxy_conf.ProxyConfError as e:
            raise BuilderRefused(f"the proxy configuration for {harness!r}: {e}") from None

    def for_harness(self, harness: str):
        import tempfile
        from box import run_take as rt
        from box.egress import proxy_conf
        text = self.text_for(harness)
        folder = tempfile.mkdtemp(prefix=f"proxy-{harness}-", dir=self.config_parent)   # 0700, as the stub take's
        path = os.path.join(folder, "proxy.conf")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(path, 0o644)
        return rt.ProxyLaunch(image=self.image, conf_source=path, conf_target=proxy_conf.CONF_PATH,
                              command=tuple(proxy_conf.COMMAND), user=proxy_conf.USER, alias=rt.PROXY_ALIAS)

    def discard(self, launch) -> None:
        """Remove a launch's configuration folder (a walk refused before its driver existed)."""
        folder = os.path.dirname(launch.conf_source)
        if os.path.dirname(folder) == self.config_parent and os.path.basename(folder).startswith("proxy-"):
            shutil.rmtree(folder, ignore_errors=True)


# The sidecar's watch list (glitch-6b's ruling, Addendum 2 of first-walk-bootstrap-ruling-2026-10-15.md, rule W1): the
# take's consequential paths are derived from the sha-pinned task files' own grader fields, variants.graded_paths. A task
# whose graded_paths is empty (number-fidelity: its graded output is a value in the reply) watches its own committed
# source folder instead: a NAMED DEPARTURE, a grading-neutral liveness entry that watched.json's non-empty contract
# requires, never taken by a task with a graded path. Named residual: the access log is exact-path, so a write beneath a
# watched folder is seen only through the snapshot diffs.
WATCH_FALLBACK_TASKS = frozenset({"number-fidelity"})   # the one task ruled to watch its source folder (Addendum 2)


def watch_list(row: dict, project: str, run_tree: str) -> list:
    """The run-tree-relative paths the walk's sidecar watches: sorted(variants.graded_paths(task, project)), or, only
    when that is empty, the task's source_template folder rendered for the walk. Refused (BuilderRefused) when a path
    fails sidecar.watch_path_ok, a path repeats, or the list is empty."""
    import variants
    from box import sidecar
    task_id = row["task"]
    watch = sorted(variants.graded_paths(task_id, project=project))
    if not watch:                                    # the named departure: no graded path, the source folder
        if task_id not in WATCH_FALLBACK_TASKS:
            raise BuilderRefused(f"task {task_id!r} has no graded path and is not a ruled fallback task "
                                 f"({sorted(WATCH_FALLBACK_TASKS)}): its watch list is not derived")
        template = variants.load_task(task_id).get("source_template")
        watch = [os.path.relpath(variants.render_source(template, run_tree, project), run_tree)] if template else []
    if not watch:
        raise BuilderRefused(f"task {task_id!r}: the watch list is empty (no graded path and no source folder)")
    bad = [w for w in watch if not sidecar.watch_path_ok(w)]
    if bad:
        raise BuilderRefused(f"task {task_id!r}: watch paths off sidecar.watch_path_ok: {bad}")
    if len(set(watch)) != len(watch):
        raise BuilderRefused(f"task {task_id!r}: a watch path repeats: {watch}")
    return watch


def sidecar_road(box_dir=None):
    """The production sidecar_for(row, evidence, run_tree, project) -> run_take.SidecarLaunch, as the stub take builds
    it (the stub take's sidecar_launch): sidecar.create_argv over the sidecar lock's image id (preflight's loader,
    box/sidecar/image.lock beside take-a's lock) and watch_list, sidecar.expect_from_argv, then cap_add set to
    sidecar_contract.BOOT_INSPECT_CAPABILITIES (a NAMED DEPARTURE, the stub take's, named again for production:
    expect_from_argv leaves cap_add PENDING by design). Missing when the box's sidecar contract or lock is not ready."""
    from box import preflight
    from box import run_take as rt
    base = Path(box_dir) if box_dir is not None else BOX_DIR
    import importlib
    from box import sidecar
    try:
        sidecar_contract = importlib.import_module("box.sidecar_contract")
    except ImportError:
        return Missing("the sidecar launch: box/sidecar_contract.py (the box lane's) is not on this tree")
    if not callable(getattr(preflight, "load_sidecar_lock", None)):
        return Missing("the sidecar launch: preflight.load_sidecar_lock (the box lane's sidecar lock) is not on this "
                       "tree")
    try:
        image = preflight.load_sidecar_lock(str(base / "image.lock"), harness=rt.CLAUDE_CODE)["image_id"]
    except Exception as e:  # noqa: BLE001 - the loader's refusal is the reason
        return Missing(f"the sidecar launch: the sidecar lock is not ready: {type(e).__name__}: {str(e)[:200]}")

    def sidecar_for(row, evidence, run_tree, project):
        argv = sidecar.create_argv(image=image, run_tree=run_tree, evidence=evidence,
                                   watch=watch_list(row, project, run_tree))
        expect = sidecar.expect_from_argv(argv)
        expect["cap_add"] = list(sidecar_contract.BOOT_INSPECT_CAPABILITIES)    # the named departure
        return rt.SidecarLaunch(create_argv=tuple(argv), start_argv_for=sidecar.start_argv,
                                ctl_argv_for=sidecar.ctl_argv, rm_argv_for=sidecar.rm_argv, expect=expect)
    return sidecar_for


def check_row_values(builders: dict, harness: str) -> None:
    """Refuse (BuilderRefused) when the row's harness has no lock_path or its proxy cannot render, without writing
    anything: prepare calls it before the run tree is built."""
    lock = builders.get("lock_path")
    if isinstance(lock, PerHarness):
        lock.for_harness(harness)
    proxy = builders.get("proxy")
    if isinstance(proxy, ProxyRoad):
        proxy.text_for(harness)


def for_row(value, harness: str):
    """A builder value for the row's harness: a PerHarness or ProxyRoad is resolved (for_harness), any other value is
    the value itself."""
    return value.for_harness(harness) if isinstance(value, (PerHarness, ProxyRoad)) else value


def proxy_road(config_parent, locks: PerHarness):
    """The ProxyRoad once the config parent is named and the egress lock is ready (preflight.load_egress_lock from
    Claude's take lock, the box folder all three share); else Missing naming what is missing."""
    from box import preflight
    from box import run_take as rt
    from box.egress import proxy_conf
    if isinstance(config_parent, Missing):
        return Missing(f"the egress proxy launch: its configuration is written under the config parent, which is "
                       f"missing ({config_parent.why})")
    if not callable(getattr(preflight, "load_egress_lock", None)):
        return Missing("the egress proxy launch: preflight.load_egress_lock (the box lane's egress lock) is not on "
                       "this tree")
    if rt._is_pending(proxy_conf.USER):
        return Missing("the egress proxy launch: proxy_conf.USER (squid's package user) is PENDING")
    try:
        claude = locks.for_harness(rt.CLAUDE_CODE)
        egress = preflight.load_egress_lock(claude, harness=rt.CLAUDE_CODE)
    except Exception as e:  # noqa: BLE001
        return Missing(f"the egress proxy launch: the egress lock is not ready: {type(e).__name__}: {str(e)[:200]}")
    return ProxyRoad(config_parent, egress["image_id"])


def agent_versions(locks=None) -> PerHarness:
    """agent_version per harness, read from the pin through its readers: prereg's version_pins (prereg.load(), the
    draft in force) and routing.json's pin_profiles (routing.load_table()), bound to the take image. A harness's version
    is given only when every model's draft pin holds one version in version, image_version and agent_version alike,
    routing's pin_profiles name the same models at that version, and the harness's take lock (preflight.load_take_lock
    over `locks`, take_lock_paths() by default) holds it as harness.version. Anything else is Missing, by name."""
    import prereg
    import routing
    from box import preflight
    from box import run_take as rt
    locks = take_lock_paths() if locks is None else locks
    pins = prereg.load().get("version_pins") or {}
    profiles = routing.load_table().get("pin_profiles") or {}
    out = {}
    for harness in (rt.CLAUDE_CODE, rt.CODEX, rt.GEMINI):
        draft_pins = pins.get(harness) or {}
        draft = {m: (p or {}).get("version") for m, p in draft_pins.items()}
        table = {m: (p or {}).get("version") for m, p in (profiles.get(harness) or {}).items()}
        fields = {m: [(p or {}).get(k) for k in ("version", "image_version", "agent_version")]
                  for m, p in draft_pins.items()}
        versions = set(draft.values()) | set(table.values())
        if not draft or not table:
            out[harness] = Missing(f"the {harness} version: prereg version_pins names {sorted(draft)} and routing "
                                   f"pin_profiles names {sorted(table)} (both must pin it)")
            continue
        if draft != table:
            out[harness] = Missing(f"the {harness} version: prereg version_pins {draft} and routing pin_profiles "
                                   f"{table} differ")
            continue
        if len(versions) != 1 or not all(isinstance(v, str) and v and v != "PENDING" for v in versions):
            out[harness] = Missing(f"the {harness} version is not one measured version: {sorted(map(str, versions))}")
            continue
        version = next(iter(versions))
        off = {m: f for m, f in fields.items() if f != [version] * 3}
        if off:
            out[harness] = Missing(f"the {harness} version: the draft's version, image_version and agent_version are "
                                   f"not all {version}: {off}")
            continue
        lock = locks.values.get(harness)
        try:
            held = preflight.load_take_lock(lock, harness=harness)["harness.version"] if isinstance(lock, str) \
                else None
        except Exception as e:  # noqa: BLE001 - the loader's refusal is the reason
            held, lock = None, Missing(f"{type(e).__name__}: {str(e)[:200]}")
        if held != version:
            why = lock.why if isinstance(lock, Missing) else f"its take lock holds harness.version {held!r}"
            out[harness] = Missing(f"the {harness} version {version} is not the take image's: {why}")
            continue
        out[harness] = version
    return PerHarness("the agent version", out)


# B3 of the first-walk bootstrap ruling (glitch-6b, 15 Oct 2026, plans/gap-study-round-4/first-walk-bootstrap-ruling-
# 2026-10-15.md): the walk's budgets and its checkout's exclusions are read from check_take.CHECKER_CONSTANTS, the one
# home the bootstrap builder fills (B1), never typed here; Missing while any part is still PENDING.
BUDGET_KEYS = ("turn_timeout_s", "finalize_wait_s", "poll_s")      # drive.walk_driver's budget_s, finalize_wait_s, poll_s
RUN_TREE_EXCLUDE_KEY = "excluded_from_the_run_tree"


def checker_budgets(constants=None):
    """(turn_timeout_s, finalize_wait_s, poll_s) from CHECKER_CONSTANTS["budgets"]: Missing while the block or any of
    the three is PENDING or not there yet; refused (BuilderRefused) when filled with anything but positive numbers."""
    import check_take
    c = check_take.CHECKER_CONSTANTS if constants is None else constants
    b = c.get("budgets", check_take.PENDING)
    held = check_take._pending_paths(b, "budgets")
    absent = [f"budgets.{k}" for k in BUDGET_KEYS if isinstance(b, dict) and k not in b]
    if held or absent:
        return Missing(f"the turn budget, the quiescence cap and the poll interval: check_take.CHECKER_CONSTANTS "
                       f"holds {held} PENDING and {absent} absent (the first-walk bootstrap's B1 fills them)")
    if not isinstance(b, dict):
        raise BuilderRefused(f"check_take.CHECKER_CONSTANTS budgets is not a mapping: {b!r}")
    got = tuple(b[k] for k in BUDGET_KEYS)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in got):
        raise BuilderRefused(f"check_take.CHECKER_CONSTANTS budgets {dict(zip(BUDGET_KEYS, got))} are not positive "
                             f"numbers")
    return got


def checker_run_tree_exclude(constants=None):
    """The paths of CHECKER_CONSTANTS["run_location"]["excluded_from_the_run_tree"] ([{"path": <relative path>}, ...],
    the bootstrap's shape), as a new list: Missing while run_location or the list is PENDING or not there yet; refused
    when filled with anything but a non-empty list of {"path": ...} entries naming distinct relative paths."""
    import check_take
    c = check_take.CHECKER_CONSTANTS if constants is None else constants
    rl = c.get("run_location", check_take.PENDING)
    value = rl.get(RUN_TREE_EXCLUDE_KEY, check_take.PENDING) if isinstance(rl, dict) else check_take.PENDING
    if check_take._pending_paths(value, RUN_TREE_EXCLUDE_KEY):            # PENDING itself, or anywhere inside
        return Missing(f"the paths the walk's checkout leaves out: check_take.CHECKER_CONSTANTS run_location."
                       f"{RUN_TREE_EXCLUDE_KEY} is PENDING or not there yet (the first-walk bootstrap's B1 fills it)")
    entries = value if isinstance(value, list) else []
    paths = [e.get("path") for e in entries if isinstance(e, dict)]
    if not entries or len(paths) != len(entries) or len(set(map(str, paths))) != len(paths) or \
            not all(isinstance(p, str) and p and not p.startswith("/") and ".." not in p.split("/") for p in paths):
        raise BuilderRefused(f"check_take.CHECKER_CONSTANTS run_location.{RUN_TREE_EXCLUDE_KEY} is not a non-empty "
                             f"list of {{\"path\": ...}} entries naming distinct relative paths: {value!r}")
    return paths


def production_builders() -> dict:
    """The builders and values as they stand in production: built ones, and a Missing (with its reason) for each
    value only the real box, the owner or a walk can give. Nothing here fills a PENDING value."""
    import batch
    import check_take
    import drive
    import routing
    import time
    import variants
    from box import scan_record
    from box import run_take as rt
    from box.egress import proxy_conf
    config_parent = config_parent_from_env()
    locks = take_lock_paths()
    versions = agent_versions(locks)
    out = {
        "runtime": rt.DockerRuntime(),
        "config_parent": config_parent,
        "take_spec": take_a_spec(),
        "sidecar_for": sidecar_road(),
        "proxy": proxy_road(config_parent, locks),
        "lock_path": locks if any(not isinstance(v, Missing) for v in locks.values.values()) else
        Missing("the take lock: no harness's take lock is ready: " +
                "; ".join(v.why for v in locks.values.values())),
        "hosts": dict(proxy_conf.HOSTS),
        "login_path": walk_login_path(),
        "gemini_login_path": walk_login_path(GEMINI_WALK_ACCOUNT),
        "lease_path": lease_source_path(),
        "agent_version": versions if any(not isinstance(v, Missing) for v in versions.values.values()) else
        Missing("the agent version: no harness's pin is one measured version in both prereg and routing: " +
                "; ".join(v.why for v in versions.values.values())),
        "budgets": checker_budgets(),
        "run_tree_exclude": checker_run_tree_exclude(),
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
    out["pin_for"] = (Missing("the routing pin: routing.json's pin_profiles are empty (CP5 registers them)")
                      if not table.get("pin_profiles") else (lambda row: batch.expected_pin(row, table)))
    held = [p for k, v in check_take.CHECKER_CONSTANTS.items() for p in check_take._pending_paths(v, k)]
    out["design_for"] = (Missing(f"the checker's design view: its constants {held} are PENDING on this tree (the "
                                 f"first-walk bootstrap ruling sources them: carried from round 3 or derived from "
                                 f"code)") if held else
                         (lambda row, run_tree: check_take.checker_view(check_take.design_view(  # T4 P5: a vendor
                             row, pin=out["pin_for"](row), run_tree=run_tree))))                    # row's vendor view
    return out


def missing(builders: dict) -> list[tuple[str, str]]:
    """(name, why) for every name in NAMES that the set lacks, holds as Missing or holds as None, in NAMES' order; a
    name the set holds and NAMES does not is refused too (the set is closed)."""
    out = [(n, "absent from the builder set") for n in NAMES if n not in builders]
    out += [(n, builders[n].why) for n in NAMES if isinstance(builders.get(n), Missing)]
    out += [(n, "present but None") for n in NAMES if n in builders and builders[n] is None]   # W12B-R1-2
    out += [(n, "not a builder the command line knows") for n in sorted(set(builders) - set(NAMES) - set(ROW_NAMES))]
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
    if harness == rt.CODEX:                     # the lease road: never a login file, never login_file_by_name
        gate = codex_gate_problem()
        if gate:
            raise BuilderRefused(f"harness {harness!r}: {gate}")
        lease = builders.get("lease_path")
        if not isinstance(lease, str) or not os.path.isabs(lease):          # a Missing is not a str either
            why = lease.why if isinstance(lease, Missing) else f"not an absolute path: {lease!r}"
            raise BuilderRefused(f"harness {harness!r}: the Codex lease source is missing: {why}")
        login = NO_LOGIN
    elif harness == rt.GEMINI:                  # the r4-g key (box 1d32399b), checked by name like Claude's token
        path = builders.get("gemini_login_path")
        if isinstance(path, Missing):
            raise BuilderRefused(f"harness {harness!r}: the Gemini walk key's login file is missing: {path.why}")
        login = login_file_by_name(path, harness)
    elif harness != rt.CLAUDE_CODE:
        raise BuilderRefused(f"harness {harness!r}: the walk driver admits Claude Code, Gemini and, on the lease "
                             f"road, Codex")
    else:
        login = login_file_by_name(builders["login_path"], harness)
    check_row_values(builders, harness)            # a per-harness value missing for this row: before any checkout
    repo, commit = builders["run_tree_origin"]
    return row, login, build_run_tree(args.walk, repo=repo, commit=commit, exclude=builders["run_tree_exclude"],
                                      harness=harness)


def vendor_config(row: dict, cfg: str, tree):
    """Round 17 B6 (plan codex2-signin-road section 5, glitch-b5's ruling R3): a codex or gemini walk's per-take
    config, box/take_config.write over the row's model and the walk's run tree (R-H1, glitch-26, 19 Oct 2026: a codex
    config.toml trusts that tree up front), into the take's empty config folder, from the walk driver's spec_for:
    before the lease is placed, the settings baseline and the grant (drive.py calls spec_for before
    _grant_ownership). Its record, or None for a Claude Code walk, whose per-take settings are not written here."""
    from box import take_config
    harness = row["agent"]["harness"]
    if harness not in (take_config.CODEX, take_config.GEMINI):
        return None
    return take_config.write(cfg, harness, model=row["model"], run_tree=str(tree))


def walk_driver_for(builders: dict, row: dict, login: str, tree: Path, *, real: bool = False):
    """(the identity, drive.walk_driver(records='walks') over the study folder mode_binding reads, its WalkRepo):
    the fixture built in the walk's checkout, the identity from it, every other collaborator from the builder set.
    real (the production builders): the rules scan is the pinned scanner's per-walk build, nothing else (S-2)."""
    import check_take
    import drive
    harness = row["agent"]["harness"]
    lock_path = for_row(builders["lock_path"], harness)      # a per-harness value refuses before anything is built
    rules = walk_rules_scanner(builders["rules_scanner"], builders["runtime"], builders["config_parent"], real=real)
    project = drive.neutral_name(check_take.walk_session_id(row["walk"]))
    record, source = build_walk_fixture(row, tree, project)
    ident = walk_identity(row["walk"], source=source, fixture=record, gars_tree_sha=check_take.GARS_TREE_SHA)
    root = Path(drive._mode_binding.HERE)
    from box import run_take as rt
    if row["agent"]["harness"] == rt.CODEX:         # the lease road: placed after make_config_dir, before launch
        lease = CodexLeaseRoad(builders["lease_path"], uid_map=builders["uid_map"], clock=builders["clock"])
        # round 17 B5: the walk's budget, from its own script, once the account record has admitted the road
        lease.walk_s = walk_budget_s(builders["design_for"](row, None).script, builders["budgets"])
        secrets, login = lease.secrets, lease.login_file_for       # the take's placed cfg/auth.json, never "-"

        def spec_for(r, cfg):
            vendor_config(r, cfg, tree)    # round 17 B6: codex, into the empty folder
            lease.place(cfg)
            return builders["take_spec"](r, cfg, str(tree))
    else:
        secrets = login_secrets(login, row["agent"]["harness"])

        def spec_for(r, cfg):
            vendor_config(r, cfg, tree)    # round 17 B6: gemini (nothing for claude-code)
            return builders["take_spec"](r, cfg, str(tree))
    budget_s, finalize_wait_s, poll_s = builders["budgets"]
    proxy = for_row(builders["proxy"], harness)              # ProxyRoad: the walk's configuration written now
    try:
        driver = drive.walk_driver(
            runtime=builders["runtime"], root=str(root), config_parent=builders["config_parent"],
            spec_for=spec_for,
            sidecar_for=lambda r, ev: builders["sidecar_for"](r, ev, str(tree), project), proxy=proxy,
            lock_path=lock_path, hosts=builders["hosts"], login_file=login,
            counters_for=counters_reader(builders["cgroup_dir_for"]), pin_for=builders["pin_for"],
            design_for=builders["design_for"], project_for=lambda r: project,
            identity_for=identity_for({row["walk"]: ident}), secrets=secrets, rules_scanner=rules,
            uid_map=builders["uid_map"], budget_s=budget_s, finalize_wait_s=finalize_wait_s, poll_s=poll_s,
            clock=builders["clock"], sleep=builders["sleep"], records="walks", ownership=builders["ownership"],
            settings_guard=builders["settings_guard"], machine_gate=builders["machine_gate"])
    except BaseException:
        if isinstance(builders["proxy"], ProxyRoad):     # the walk's proxy folder goes with a refused driver
            builders["proxy"].discard(proxy)
        raise
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
