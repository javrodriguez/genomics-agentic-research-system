#!/usr/bin/env python3
"""The live-box forced-timeout claude-code take: one real cut, measured against the cut-tail bound.

Lane gap-live-box (glitch-45, the Lane-orchestrator, Wed 28 Oct 2026, under Javier's standing delegation; design
LIVE-BOX-TAKE-DESIGN-20261028 section 6, B1 item 1; rulings R1-R5 on it). It answers freeze_rehearsal.LIVE_BOX_REQUIRED
(the lead's rulings of Sat 24 Oct 2026 on the second closure check of f0c0eb1d: a forced-timeout claude-code take on
a real box joins the freeze rehearsal's required list, and the rehearsal fails without it).

    athena  python3 -B evals/gap-study-4/live_box_cut.py run --home <new absolute folder> --walk <lbN> --task <t>
                --half <h> --wording <w> --budget-s <B>
            from the shipped line head (Part T's `live-box` verb): a throwaway --no-local clone at <home>/clone, its
            remote removed, then that clone's own `probe` with --record <home>/record.json. The shipped repository is
            only read (git clone); nothing is written into it.
    athena  python3 -B evals/gap-study-4/live_box_cut.py probe --walk <lbN> --task <t> --half <h> --wording <w>
                --budget-s <B> --record <absolute path outside the repository>
            in that clone (run calls it): ONE walk through the walk road unchanged (walk_builders.cli with the production
            builders, so drive, check.json, grade.json and the commit are the walk road's own), the turn budget swapped
            for B in this process only (R1: B about 20 s, refused at or above the registered budget, 900 s). Then the
            committed walk folder's driver-ledger.json, transcript.jsonl (the session file) and every turn-N.jsonl and
            turn-N.jsonl.launch.json are copied byte for byte from HEAD into <record folder>/files/, and the record is
            written: closed fields only, never transcript text.
    any     python3 -B evals/gap-study-4/live_box_cut.py verify --record <absolute path>
            freeze_rehearsal's live-box step, run in its clone: re-reads the record and its files with the clone's code
            and prints one closed line (never a path), exit 0 only when every clause below holds.

The record (KEYS, exactly): schema, line_head (the clone's head the walk ran on), probe_commit (the walk's commit),
walk, harness (claude-code), model (the draft's arm A Haiku pin), cli_version (the ledger's agent version), budget_s
(B), registered_budget_s (check_take.CHECKER_CONSTANTS' turn_timeout_s, read), cut_turns (the turns the driver ledger
records cut: end timed-out or exit 124, claude_code_adapter.host_recorded_cuts), ledger_end and ledger_exit (the first
cut turn's row; the last row's when none is cut), files ({name: sha256}), content_problems ({count, problems}: the
problems of check_take.transcript_content_problems on the copied files, each kept only when it fits a closed sentence
that names kinds and item numbers, else the closed WITHHELD line; the count is the whole count), session_torn (the
session file's last non-blank line is not one JSON object), gap ({stream_units, session_units, shape} of the first cut
turn: gap_shape), check_route and check_reasons (the walk's own committed check.json, its route and its reason ids
only), adapter_sha256 (claude_code_adapter.py), check_take_sha256 (check_take.py), checker_digest
(check_take.checker_constants_sha256(), the claude-code digest), at (UTC, read in this process).

gap_shape is a measurement, never a second bound: the bound is claude_code_adapter.cut_tail_problem, called here, and a
tail it refuses reads "outside". Inside the bound a tail reads "equal", "session-lags-<k>" or "stream-lags-1".

Exit codes. probe and run: 0 the cut was recorded inside the bound with no content problem and no torn line; 3 not cut
(the turn ended before B: the next walk id with B halved, at most twice, R2); 4 a finding (a shape outside the bound, a
content problem, a torn session line, or a checker reason transcript-unreadable or transcript-mismatch on the walk):
the run fails closed and reports to glitch-45 (R5; the checker and the adapter are never edited in this lane); 1 the
walk was not committed or the record could not be made; 2 refused before anything was built. verify: 0 or 1.

Refusals before anything is built (probe): a prereg.json present (a probe is pre-freeze only); B not an integer in
[1, registered budget); a walk id that is not lb<number>; a clone with a remote, with an unclean status, or that is the
records clone (a gap4-walk-records folder) or the shipped child's repository; a record path that is relative, inside
the repository, or already present; a run token's path (run_builders.RUN_LOGIN_FILES) anywhere in the builders, or a
login that is not the claude1 walk login (run_take.WALK_LOGIN_FILES["claude1"]).

Never counted: the walk lives only in the throwaway clone, is never fetched into the records clone, and its ledger
carries budget_s B, which the checker's constant binding refuses for any counted take. No spend: the claude1 walk login
is a subscription with overage disabled. This module is outside check_take.CHECKER_CODE_FILES and the native-reader
source lists, and nothing the checker imports imports it.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import check_take  # noqa: E402
import claude_code_adapter as cca  # noqa: E402
import study  # noqa: E402

SCHEMA = 1
HARNESS = "claude-code"
ARM = "A"
MODEL = "claude-haiku-4-5-20251001"          # the draft's arm A Haiku pin (verify reads the draft's version pin for it)
WALK_ACCOUNT = "claude1"                     # run_take.WALK_LOGIN_FILES' key: the walk login, never the run token
LB_WALK = re.compile(r"lb[1-9][0-9]{0,3}")   # a probe's walk id: never one of the study's w-ids
FILES_DIR = "files"                          # beside the record: the walk's files, copied from the commit
RECORD_NAME = "record.json"
CLONE_NAME = "clone"
REASON = ("live-box probe (freeze_rehearsal.LIVE_BOX_REQUIRED; lane gap-live-box, glitch-45's R1): one claude-code "
          "turn cut by a probe budget below the registered one; never counted")
KEYS = ("schema", "line_head", "probe_commit", "walk", "harness", "model", "cli_version", "budget_s",
        "registered_budget_s", "cut_turns", "ledger_end", "ledger_exit", "files", "content_problems", "session_torn",
        "gap", "check_route", "check_reasons", "adapter_sha256", "check_take_sha256", "checker_digest", "at")
GAP_KEYS = ("stream_units", "session_units", "shape")
CUT_END, CUT_EXIT = "timed-out", 124
NOT_CUT = "not-cut"
OUTSIDE = "outside"
IN_BOUND = re.compile(r"equal|session-lags-[1-9][0-9]{0,5}|stream-lags-1")
SHAPE = re.compile(rf"{IN_BOUND.pattern}|{OUTSIDE}|{NOT_CUT}")
FILE_NAME = re.compile(r"driver-ledger\.json|transcript\.jsonl|turn-[1-9][0-9]{0,3}\.jsonl(\.launch\.json)?")
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,6}")
WORD = re.compile(r"[a-z][a-z0-9_-]{0,39}")
AT = re.compile(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z")
FINDING_REASONS = ("transcript-unreadable", "transcript-mismatch")
# The problem sentences the checker's content reading writes that name kinds and item numbers only (check_take
# transcript_content_problems and transcript_record_problems; claude_code_adapter content_problems and
# cut_tail_problem). A problem that fits none (the uncut turn's sentence quotes up to 60 characters of a unit) is kept
# as WITHHELD; its count is kept.
_TM = r"\[transcript-mismatch\] "
_CUT = _TM + r"turn [0-9]+ \(cut, as the host records\): "
CLOSED_PROBLEMS = tuple(re.compile(p) for p in (
    _TM + r"the session file holds [0-9]+ content item\(s\) before its first operator line, which no turn stream holds",
    _TM + r"the session file holds [0-9]+ operator line\(s\) and the take [0-9]+ turn stream\(s\)",
    _CUT + r"the session file differs from the host-captured stream at item [0-9]+, before the record in flight when "
           r"the turn was cut",
    _CUT + r"the session file holds [0-9]+ item\(s\) after the record in flight that the stream does not, more than "
           r"the one a cut can leave",
    _CUT + r"the session file's record in flight differs from the stream's at its item [0-9]+: a cut drops units, it "
           r"never changes one",
    _CUT + r"the session file's one unit past the stream shares its line with another unit, a shape the CLI never "
           r"writes, so it cannot be left out of grading",
    _TM + r"the session file carries line separator\(s\) (U\+[0-9A-F]{4}(, )?)+ that no turn stream carries: the "
          r"records disagree",
    _TM + r"the session file holds [0-9]+ line\(s\) that are not one JSON record, while every turn stream reads: the "
          r"records disagree",
    _TM + r"the session file holds [0-9]+ sidechain record\(s\), which the main session file never holds: the records "
          r"disagree",
    _TM + r"turn [0-9]+: the session file's operator line is not the prompt the turn's launch journal records: the "
          r"records disagree",
    r"\[transcript-unreadable\] the transcript or a turn stream cannot be read \([A-Za-z]+\)",
))
WITHHELD = "[transcript-mismatch] a problem whose sentence quotes content (withheld here; counted)"


class Refused(RuntimeError):
    """A probe refused before anything was built; the message is closed (no path, no athena-made word)."""


# ------------------------------------------------------------------------------------------------ pure readings
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def gap_shape(stream: list, sess: list) -> str:
    """The cut turn's measured shape: "outside" when claude_code_adapter.cut_tail_problem refuses the tail (the one
    bound, called, never restated), else "equal", "session-lags-<k>" (the session file holds k units fewer) or
    "stream-lags-1" (it holds the one unit more the bound admits)."""
    stream, sess = [tuple(u) for u in stream], [tuple(u) for u in sess]
    if cca.cut_tail_problem(stream, sess) is not None:
        return OUTSIDE
    if len(sess) == len(stream):
        return "equal"
    if len(sess) < len(stream):
        return f"session-lags-{len(stream) - len(sess)}"
    return "stream-lags-1"


def closed_problem(problem: str) -> str:
    """`problem` when it fits a closed sentence, else WITHHELD."""
    return problem if isinstance(problem, str) and any(p.fullmatch(problem) for p in CLOSED_PROBLEMS) else WITHHELD


def session_torn(session_text: str) -> bool:
    """The session file's last non-blank line is not one JSON object (the kill cut it short)."""
    lines = [line for line in session_text.split("\n") if line.strip()]
    if not lines:
        return False
    try:
        return not isinstance(json.loads(lines[-1]), dict)
    except ValueError:
        return True


def ledger_rows(ledger: dict) -> list:
    rows = ledger.get("turns") if isinstance(ledger, dict) else None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def measure(folder: Path) -> dict:
    """The closed reading of a walk folder holding the copied files: cut_turns, ledger_end, ledger_exit,
    content_problems, session_torn, gap. Reads with this tree's checker and adapter."""
    folder = Path(folder)
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    cut = sorted(cca.host_recorded_cuts(folder))
    rows = ledger_rows(ledger)
    row = next((r for r in rows if r.get("n") == cut[0]), {}) if cut else (rows[-1] if rows else {})
    end, code = row.get("end"), row.get("exit")
    session = (folder / "transcript.jsonl").read_bytes().decode("utf-8", errors="replace")
    try:
        problems = check_take.transcript_content_problems(folder / "transcript.jsonl")
    except check_take.CheckRefused as e:
        problems = [f"[transcript-unreadable] {e}"]
    gap = {"stream_units": None, "session_units": None, "shape": NOT_CUT}
    if cut:
        n = cut[0]
        stream_path = folder / f"turn-{n}.jsonl"
        stream = (cca.stream_content_units(stream_path.read_bytes().decode("utf-8", errors="replace"))
                  if stream_path.is_file() else [])
        turns = cca.session_content_turns(session)
        sess = turns[n] if n < len(turns) else []
        gap = {"stream_units": len(stream), "session_units": len(sess), "shape": gap_shape(stream, sess)}
    return {"cut_turns": cut,
            "ledger_end": end if isinstance(end, str) and WORD.fullmatch(end) else None,
            "ledger_exit": code if type(code) is int else None,
            "content_problems": {"count": len(problems), "problems": [closed_problem(p) for p in problems]},
            "session_torn": session_torn(session), "gap": gap}


def finding(record: dict) -> list:
    """Why a record, cut or not, is a finding for glitch-45 (R5): a shape outside the bound, a content problem, a torn
    session line, or a transcript-unreadable or transcript-mismatch check reason; [] when it is none of them."""
    out = []
    if record["gap"]["shape"] == OUTSIDE:
        out.append("the cut turn's tail is outside the cut-tail bound")
    if record["content_problems"]["count"]:
        out.append(f"{record['content_problems']['count']} content problem(s)")
    if record["session_torn"]:
        out.append("the session file's last line is torn")
    bad = [r for r in FINDING_REASONS if r in record["check_reasons"]]
    if bad:
        out.append("the walk's check reads " + ", ".join(bad))
    return out


def summary_line(record: dict, sha: str) -> str:
    """One closed line: integers, closed words and the record's sha256; never a path."""
    g = record["gap"]
    cut = record["cut_turns"]
    return (f"live-box record {sha}: walk {record['walk']}, budget {record['budget_s']} s of "
            f"{record['registered_budget_s']} s, " +
            (f"turn {cut[0]} cut (end {record['ledger_end']}, exit {record['ledger_exit']}), stream "
             f"{g['stream_units']} unit(s), session {g['session_units']} unit(s), shape {g['shape']}" if cut else
             f"no turn cut (end {record['ledger_end']}, exit {record['ledger_exit']})") +
            f", content problems {record['content_problems']['count']}, session torn "
            f"{'yes' if record['session_torn'] else 'no'}")


# ------------------------------------------------------------------------------------------------ git
def git(repo, *args, binary=False):
    p = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args], capture_output=True)
    if p.returncode != 0:
        raise Refused(f"git {args[0]} failed (exit {p.returncode})")
    return p.stdout if binary else p.stdout.decode("utf-8", "surrogateescape").strip()


# ------------------------------------------------------------------------------------------------ refusals
def registered_budget_s(constants=None) -> int:
    c = check_take.CHECKER_CONSTANTS if constants is None else constants
    b = c.get("budgets") if isinstance(c, dict) else None
    v = b.get("turn_timeout_s") if isinstance(b, dict) else None
    if type(v) is not int or v < 2:
        raise Refused("check_take.CHECKER_CONSTANTS holds no integer turn_timeout_s")
    return v


def budget_problem(budget, registered: int):
    if type(budget) is not int or budget < 1:
        return "--budget-s is a positive integer"
    if budget >= registered:
        return (f"--budget-s {budget} is not below the registered turn budget ({registered} s): a probe never runs at "
                f"or above it, so it can never read as a registered take")
    return None


def clone_problems(repo: Path) -> list:
    """Why `repo` may not hold a probe walk: a records clone, the shipped child's repository, a remote, a dirty tree."""
    out = []
    where = Path(repo).resolve()
    if any("gap4-walk-records" in part for part in where.parts):
        out.append("this is the records clone; a probe runs only in a throwaway clone")
    if where.name == "repo" and re.fullmatch(r"w-[A-Za-z0-9]{8}", where.parent.name):
        out.append("this is the shipped child's repository; `run` clones it first")
    if git(where, "remote"):
        out.append("this clone has a remote; a probe's clone has none")
    if git(where, "status", "--porcelain", "--untracked-files=all"):
        out.append("this clone's status is not clean")
    return out


def record_path_problem(record: str, repo: Path):
    path = Path(record)
    if not path.is_absolute():
        return "--record is not an absolute path"
    if path.resolve().is_relative_to(Path(repo).resolve()):
        return "--record is inside the repository; the record stays outside it (R3)"
    if os.path.lexists(path) or os.path.lexists(path.parent / FILES_DIR):
        return "--record (or its files folder) already exists; a record is never overwritten"
    if not path.parent.is_dir():
        return "--record's folder does not exist"
    return None


def _strings(value, depth=0):
    """Every string a builder value carries: containers walked, an object's own attributes one level down."""
    if depth > 6:
        return
    if isinstance(value, (str, os.PathLike)):
        yield os.fspath(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(k, depth + 1)
            yield from _strings(v, depth + 1)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for v in value:
            yield from _strings(v, depth + 1)
    elif depth < 2:
        attrs = getattr(value, "__dict__", None)
        if isinstance(attrs, dict):
            yield from _strings(attrs, depth + 1)
        for name in getattr(type(value), "__slots__", ()) or ():
            if isinstance(name, str):
                yield from _strings(getattr(value, name, None), depth + 1)


def token_problem(builders: dict):
    """Refused when a run token's path appears anywhere in the builders, or the login is not the claude1 walk
    login."""
    import run_builders
    from box import run_take as rt
    tokens = {p for p in run_builders.RUN_LOGIN_FILES.values() if isinstance(p, str)}
    if any(s in tokens or any(t in s for t in tokens) for s in _strings(builders)):
        return "a run token's path is in the builders; a probe uses the walk login only"
    want = rt.WALK_LOGIN_FILES.get(WALK_ACCOUNT)
    if builders.get("login_path") != want:
        return "the builders' login is not the claude1 walk login"
    return None


def with_budget(builders: dict, budget: int) -> dict:
    """The production builders with the turn budget swapped for `budget`, in this process only; the quiescence cap
    and the poll interval stay the registered ones."""
    b = builders.get("budgets")
    if not (isinstance(b, tuple) and len(b) == 3):
        raise Refused("the production builders hold no (turn, quiescence, poll) budgets")
    return dict(builders, budgets=(budget, b[1], b[2]))


# ------------------------------------------------------------------------------------------------ probe
def walk_argv(args) -> list:
    return ["--walk", args.walk, "--task", args.task, "--half", args.half, "--wording", args.wording,
            "--arm", ARM, "--model", MODEL, "--reason", REASON]


def run_walk(builders: dict, argv: list) -> int:
    """walk_builders.cli with production_builders answering `builders`, so cli keeps its real-walk rules (the pinned
    rules scanner among them) and only the turn budget differs."""
    import walk_builders
    original = walk_builders.production_builders
    walk_builders.production_builders = lambda: builders
    try:
        return walk_builders.cli(argv, None, refusal="the live-box probe refused before anything was built")
    finally:
        walk_builders.production_builders = original


def committed_files(repo: Path, commit: str, walk: str) -> dict:
    """{name: bytes} of the walk folder's files FILE_NAME admits, as committed (git show), at `commit`."""
    folder = study.rel("rehearsals", walk)
    names = git(repo, "ls-tree", "--name-only", commit, folder + "/").splitlines()
    out = {}
    for path in names:
        name = path.rsplit("/", 1)[-1]
        if FILE_NAME.fullmatch(name):
            out[name] = git(repo, "show", f"{commit}:{path}", binary=True)
    return out


def check_reading(repo: Path, commit: str, walk: str) -> tuple:
    """(route, reason ids) of the walk's committed check.json; closed words only."""
    try:
        doc = json.loads(git(repo, "show", f"{commit}:{study.rel('rehearsals', walk, 'check.json')}", binary=True))
    except (Refused, ValueError):
        return None, ["check-unread"]
    route = doc.get("route") if isinstance(doc, dict) else None
    reasons = doc.get("checker_reasons") if isinstance(doc, dict) else None
    ids = []
    for r in reasons if isinstance(reasons, list) else []:
        m = re.match(r"\[([a-z][a-z0-9-]{0,39})\]", r) if isinstance(r, str) else None
        ids.append(m.group(1) if m else "unnamed")
    return (route if isinstance(route, str) and WORD.fullmatch(route) else None), sorted(set(ids))


def write_new(path: Path, data: bytes) -> None:
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_record(*, folder: Path, walk: str, budget: int, registered: int, line_head: str, probe_commit: str,
                 files: dict, route, reasons: list, at: str) -> dict:
    """The record over the copied files in `folder` (the files folder), read with this tree's code."""
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    agent = ledger.get("agent") if isinstance(ledger.get("agent"), dict) else {}
    version = agent.get("version")
    record = {"schema": SCHEMA, "line_head": line_head, "probe_commit": probe_commit, "walk": walk,
              "harness": HARNESS, "model": MODEL,
              "cli_version": version if isinstance(version, str) and VERSION.fullmatch(version) else None,
              "budget_s": budget, "registered_budget_s": registered,
              "files": {name: sha256_bytes(data) for name, data in sorted(files.items())},
              "check_route": route, "check_reasons": reasons,
              "adapter_sha256": sha256_bytes((HERE / "claude_code_adapter.py").read_bytes()),
              "check_take_sha256": sha256_bytes((HERE / "check_take.py").read_bytes()),
              "checker_digest": check_take.checker_constants_sha256(), "at": at}
    record.update(measure(folder))
    return {k: record[k] for k in KEYS}


def probe(args, *, builders_factory=None, walk_runner=None, clock=utc_now, repo=None) -> int:
    repo = Path(repo if repo is not None else REPO)
    try:
        if not LB_WALK.fullmatch(args.walk or ""):
            raise Refused("the walk id is not lb<number>: a probe never takes one of the study's walk ids")
        if (repo / study.rel("prereg.json")).exists():
            raise Refused("prereg.json is present: a probe runs before the freeze only")
        registered = registered_budget_s()
        why = budget_problem(args.budget_s, registered) or record_path_problem(args.record, repo)
        if why:
            raise Refused(why)
        bad = clone_problems(repo)
        if bad:
            raise Refused("; ".join(bad))
        if builders_factory is None:
            import walk_builders
            builders_factory = walk_builders.production_builders
        builders = builders_factory()
        why = token_problem(builders)
        if why:
            raise Refused(why)
        builders = with_budget(builders, args.budget_s)
        line_head = git(repo, "rev-parse", "HEAD")
    except Refused as e:
        print(f"live-box: refused: {e}", flush=True)
        return 2
    except Exception as e:  # noqa: BLE001 - a builder set that cannot be read is a refusal, its words unechoed
        print(f"live-box: refused: the builders cannot be read ({type(e).__name__})", flush=True)
        return 2
    code = (walk_runner or run_walk)(builders, walk_argv(args))
    if code != 0:
        print(f"live-box: the walk was not committed (walk_runner exit {code}); no record", flush=True)
        return 1
    record_path = Path(args.record)
    try:
        commit = git(repo, "rev-parse", "HEAD")
        if commit == line_head:
            raise Refused("the walk made no commit")
        files = committed_files(repo, commit, args.walk)
        missing = [n for n in ("driver-ledger.json", "transcript.jsonl") if n not in files]
        if missing:
            raise Refused(f"the walk's commit holds no {', '.join(missing)}")
        folder = record_path.parent / FILES_DIR
        folder.mkdir(mode=0o700)
        for name, data in files.items():
            write_new(folder / name, data)
        route, reasons = check_reading(repo, commit, args.walk)
        record = build_record(folder=folder, walk=args.walk, budget=args.budget_s, registered=registered,
                              line_head=line_head, probe_commit=commit, files=files, route=route, reasons=reasons,
                              at=clock())
        data = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
        write_new(record_path, data)
    except (Refused, OSError, ValueError) as e:
        print(f"live-box: the record could not be made ({type(e).__name__})", flush=True)
        return 1
    print(summary_line(record, sha256_bytes(data)), flush=True)
    # review F1: a finding is read first, so a torn line or a content problem on a walk no turn of which was cut
    # exits 4, never "not cut"
    why = finding(record)
    if why:
        print("live-box: FINDING for glitch-45 (R5, fail closed): " + "; ".join(why), flush=True)
        return 4
    if not record["cut_turns"]:
        print("live-box: not cut: the turn ended inside the probe budget (R2: the next walk id with B halved)",
              flush=True)
        return 3
    return 0


# ------------------------------------------------------------------------------------------------ run (from the ship)
def run(args, *, runner=None, repo=None) -> int:
    """Clone the shipped repository into <home>/clone (--no-local, remote removed, HEAD equal), then that clone's own
    probe, record at <home>/record.json. The shipped repository is only read."""
    repo = Path(repo if repo is not None else REPO).resolve()
    home = Path(args.home)
    runner = runner or (lambda argv, cwd: subprocess.run(argv, cwd=str(cwd)).returncode)
    if not home.is_absolute() or ".." in home.parts:
        print("live-box: refused: --home is not a plain absolute path", flush=True)
        return 2
    if home.resolve().is_relative_to(repo):
        print("live-box: refused: --home is inside the shipped repository", flush=True)
        return 2
    if (repo / study.rel("prereg.json")).exists():
        print("live-box: refused: prereg.json is present: a probe runs before the freeze only", flush=True)
        return 2
    if not LB_WALK.fullmatch(args.walk or ""):
        print("live-box: refused: the walk id is not lb<number>", flush=True)
        return 2
    try:
        home.parent.mkdir(parents=True, exist_ok=True)
        home.mkdir(mode=0o700)
    except FileExistsError:
        print("live-box: refused: --home already exists; each probe walk has its own new folder", flush=True)
        return 2
    clone = home / CLONE_NAME
    try:
        head = git(repo, "rev-parse", "HEAD")
        for argv in (["git", "clone", "-q", "--no-local", str(repo), str(clone)],
                     ["git", "-C", str(clone), "remote", "remove", "origin"]):
            if runner(argv, home):
                raise Refused("git clone or git remote remove failed")
        if git(clone, "rev-parse", "HEAD") != head:
            raise Refused("the clone's HEAD is not the shipped head")
    except Refused as e:
        print(f"live-box: refused: the throwaway clone could not be made ({e})", flush=True)
        return 2
    argv = [sys.executable, "-B", "-W", "ignore", str(clone / study.rel("live_box_cut.py")), "probe",
            "--walk", args.walk, "--task", args.task, "--half", args.half, "--wording", args.wording,
            "--budget-s", str(args.budget_s), "--record", str(home / RECORD_NAME)]
    return runner(argv, clone)


# ------------------------------------------------------------------------------------------------ verify
REFUSED_LINE = "live-box record {sha}: REFUSED: {why}"


def verify_problems(record_path: Path, *, repo=None) -> tuple:
    """(sha256 of the record's bytes or None, [closed reasons]). Every clause of the live-box step, re-read here."""
    repo = Path(repo if repo is not None else REPO).resolve()
    path = Path(record_path)
    if not path.is_absolute():
        return None, ["the record path is not absolute"]
    if path.is_symlink() or not path.is_file():
        return None, ["the record is not a regular file"]
    if path.resolve().is_relative_to(repo):
        return None, ["the record is inside the repository"]
    data = path.read_bytes()
    sha = sha256_bytes(data)
    try:
        rec = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return sha, ["the record is not JSON"]
    if not isinstance(rec, dict) or set(rec) != set(KEYS):
        return sha, ["the record's keys are not exactly the closed set"]
    out = []
    registered = registered_budget_s()
    if rec["schema"] != SCHEMA:
        out.append("schema")
    if rec["harness"] != HARNESS:
        out.append("harness is not claude-code")
    if rec["model"] != MODEL:
        out.append("model is not the arm A Haiku pin")
    if not (isinstance(rec["walk"], str) and LB_WALK.fullmatch(rec["walk"])):
        out.append("walk id")
    if not all(isinstance(rec[k], str) and HEX40.fullmatch(rec[k]) for k in ("line_head", "probe_commit")):
        out.append("commit ids")
    if not (isinstance(rec["at"], str) and AT.fullmatch(rec["at"])):
        out.append("time")
    if rec["registered_budget_s"] != registered:
        out.append("registered budget is not this tree's")
    if budget_problem(rec["budget_s"], registered):
        out.append("budget is not below the registered one")
    pins = _draft_version()
    if pins is None:
        out.append("the draft's version pin cannot be read")
    elif rec["cli_version"] != pins:
        out.append("cli version is not the draft's pin")
    cut = rec["cut_turns"]
    if not (isinstance(cut, list) and cut and all(type(n) is int and n >= 1 for n in cut)):
        out.append("no cut turn")
    if rec["ledger_end"] != CUT_END:
        out.append("ledger end is not timed-out")
    if rec["ledger_exit"] != CUT_EXIT:
        out.append("ledger exit is not 124")
    for k in ("adapter_sha256", "check_take_sha256", "checker_digest"):
        if not (isinstance(rec[k], str) and HEX64.fullmatch(rec[k])):
            out.append(f"{k} is off its form")
    if rec["adapter_sha256"] != sha256_bytes((HERE / "claude_code_adapter.py").read_bytes()):
        out.append("adapter digest is not this tree's")
    if rec["check_take_sha256"] != sha256_bytes((HERE / "check_take.py").read_bytes()):
        out.append("check_take digest is not this tree's")
    if rec["checker_digest"] != check_take.checker_constants_sha256():
        out.append("checker digest is not this tree's")
    route, reasons = rec["check_route"], rec["check_reasons"]
    if not (route is None or (isinstance(route, str) and WORD.fullmatch(route))):
        out.append("check route is off its form")
    if not (isinstance(reasons, list) and all(isinstance(r, str) and WORD.fullmatch(r) for r in reasons)):
        out.append("check reasons are off their form")
    elif any(r in reasons for r in FINDING_REASONS):
        out.append("the walk's check reads transcript-unreadable or transcript-mismatch")
    files = rec["files"]
    folder = path.parent / FILES_DIR
    if not (isinstance(files, dict) and files and all(isinstance(n, str) and FILE_NAME.fullmatch(n) and
                                                      isinstance(s, str) and HEX64.fullmatch(s)
                                                      for n, s in files.items())):
        return sha, out + ["files are off their form"]
    need = {"driver-ledger.json", "transcript.jsonl"}
    if isinstance(cut, list):
        need |= {f"turn-{n}.jsonl" for n in cut if type(n) is int}
    if not need <= set(files):
        out.append("files lack the ledger, the session file or a cut turn's stream")
    try:
        on_disk = sorted(p.name for p in folder.iterdir())
    except OSError:
        return sha, out + ["the files folder cannot be read"]
    if on_disk != sorted(files):
        out.append("the files folder holds other files than the record names")
    for name, want in sorted(files.items()):
        f = folder / name
        if f.is_symlink() or not f.is_file() or sha256_bytes(f.read_bytes()) != want:
            out.append(f"{name} is not the file the record names")
    if out:
        return sha, out
    got = measure(folder)
    for k in ("cut_turns", "ledger_end", "ledger_exit", "content_problems", "session_torn", "gap"):
        if got[k] != rec[k]:
            out.append(f"{k} re-read differs from the record")
    if got["content_problems"]["count"]:
        out.append("content problems re-read are not empty")
    if got["session_torn"]:
        out.append("the session file's last line is torn")
    gap = rec["gap"]
    if not (isinstance(gap, dict) and set(gap) == set(GAP_KEYS) and isinstance(gap["shape"], str)
            and IN_BOUND.fullmatch(gap["shape"])):
        out.append("the cut turn's shape is not inside the bound")
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    if ledger.get("budget_s") != rec["budget_s"] or ledger.get("arm") != ARM or \
            ledger.get("model_requested") != MODEL or (ledger.get("agent") or {}).get("harness") != HARNESS:
        out.append("the ledger's budget, arm, model or harness is not the record's")
    return sha, out


def _draft_version():
    """The draft's claude-code version pin for MODEL, or None when it cannot be read (verify then refuses: review F4,
    never None == None)."""
    try:
        pins = json.loads((HERE / "prereg-draft.json").read_text())["version_pins"][HARNESS][MODEL]
        return pins["version"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def verify(args, *, repo=None) -> int:
    try:
        sha, problems = verify_problems(Path(args.record), repo=repo)
    except Exception as e:  # noqa: BLE001 - its words could carry a path: the type only
        sha, problems = None, [f"the record could not be read ({type(e).__name__})"]
    shown = sha or "-" * 64
    if problems:
        print(REFUSED_LINE.format(sha=shown, why="; ".join(problems)), flush=True)
        return 1
    rec = json.loads(Path(args.record).read_bytes())
    print(summary_line(rec, sha) + f"; files {len(rec['files'])} re-read equal; adapter, check_take and checker "
          f"digests this tree's; within the bound", flush=True)
    return 0


# ------------------------------------------------------------------------------------------------ cli
def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 allow_abbrev=False)
    sub = ap.add_subparsers(dest="verb", required=True)
    for name in ("run", "probe"):
        p = sub.add_parser(name, allow_abbrev=False)
        p.add_argument("--walk", required=True)
        p.add_argument("--task", required=True)
        p.add_argument("--half", required=True)
        p.add_argument("--wording", required=True)
        p.add_argument("--budget-s", required=True, type=int)
        if name == "run":
            p.add_argument("--home", required=True)
        else:
            p.add_argument("--record", required=True)
    p = sub.add_parser("verify", allow_abbrev=False)
    p.add_argument("--record", required=True)
    return ap


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    return {"run": run, "probe": probe, "verify": verify}[args.verb](args)


if __name__ == "__main__":
    raise SystemExit(main())
