#!/usr/bin/env python3
"""Lane w11b-gemini-adapter (Gap Study round 4, arm G): the Gemini CLI adapter and its stream parser, on synthetic
streams over a fake runtime.

    python3 -B -W ignore evals/gap-study-4/tests/test_gemini_adapter.py               every test
    python3 -B -W ignore evals/gap-study-4/tests/test_gemini_adapter.py --witnesses   the witnesses only, one line each

Fixtures: tests/fixtures/gemini-streams/, every file SYNTHETIC (its README labels each one): written from the event
types and the init and result keys D8 section 1 names, plus the keys transcript_gemini.py lists as "NOT in D8". No
Gemini CLI stream has been recorded (ruling Q-3: build on the documented shapes now; the freeze binds the recorded
re-test).

What is tested, each guard with its own bound check, and each clause of a guard's condition with a case of its own
(wave 10's lesson: a clause that can be dropped with the suite green is a clause nothing tests). Every guard, clause
and load-bearing assignment has a whole-file witness of gemini_adapter.py or transcript_gemini.py compiled in memory
(the registry pattern of lanes w6j and w11a), red by its own check's assertion:

  S1-event   an event type off the tables is refused by the record check and the parser; the table holds D8's six
             event types.
  S2-key     a required key missing, an extra key, and an error object off its keys, not an object, or on the
             wrong event, are refused; every pre-registered fixture line decodes.
  S3-words   a role, a status (tool_result's and result's, each on its own), a severity, a content that is not a
             string, and a tool id that is not a string or is empty (on tool_use and tool_result) are refused; an
             error event without a severity and a result without an error or stats are accepted.
  S4-stats   result.stats: a missing count, an extra key, a value that is a string, a bool, a float or negative, a
             stats or models value that is not an object, and a model entry off its keys or counts are refused.
  S5-tools   a tool name with no entry (web_fetch, read_many_files) and an argument key with no entry are refused by
             the record check and the parser; the table's view kinds are pinned (round 18 B12: the table read from the
             pinned 0.64.0 registry, tests/test_gemini_tool_registry.py).
  S7-open-input  an undeclared key on an OPEN_INPUT tool is named, ignored input; the refusals that stand; each
             entry cited (lane vendor-b16 round 2, ruling R-B16-2; tests/test_gemini_undeclared_args.py U1-U3).
  P1-view    through transcript_view.events (the parser put in a COPY of PARSERS for the test only, never
             registered): user -> operator, assistant -> agent-text, tool_use -> tool-call of its kind, tool_result
             -> its tool-result, init, error and result -> harness.
  A1-stream  read_stream: the agent's text (delta chunks joined, a non-message record ends a chunk run), tool ids,
             a cut line counted, two inits or two results refused, a record off the tables refused on the adapter's
             road too.
  A2-error   the error event and a failed result are api_errors with the harness's own words; a successful result
             is none; an agent message that says "429" is never one; an error event is never agent output.
  A3-output  agent output: an assistant message with non-blank content, or a tool_use; never a user message, a
             blank assistant message or an error event (each clause on its own).
  A4-stats   the result's stats kept as recorded; a missing count refused on the adapter's road; no result, no stats.
  A5-model   init.model and every key of result.stats.models against the row's model, on every turn; the
             TurnResult's init is None (the stream records no permission mode), never filled from the argv.
  A6-argv    `-m <model>` and the mode's flags on every call; `-r <session id>` after turn 1 only; no `--sandbox`;
             a PENDING, empty, absent, unknown or non-string mode refuses the adapter; a line starting with "-" and
             a later turn without a well-shaped session id are refused; the login rides by name only.
  A7-session a later turn whose init names another session is refused; a later turn with no init is not; an init
             session id off its shape is refused; turn 1's id is the one resumed.
  A8-turn    end reasons (end_turn; error on exit 1, on exit 53 even with a successful result, on exit 0 with a
             failed result or none; timed-out), each exit's meaning kept (53 -> turn-limit), an exit code off D8's
             four (or a bool) refused, a timed-out call never refused for its exit, the counters' rise, the version.
  A9-source  SHAPES_SOURCE is one of the two words and reads "recorded" only while a fixture is labelled RECORDED
             with its walk and CLI version (lane vendor-settle stage V: it reads "recorded"), every fixture carries the
             brief's label, and the adapter reports it in its harness record and every turn record. Witness:
             shapes-off-word.
  R-recorded stage V: the three RECORDED streams (w-g21's two turns, w-g24's timed-out turn with no result record) are
             byte copies of their walk records in rehearsals/, and read_stream and end_reason read them as plain json.

Fakes only: no model, vendor, network, container runtime, credential or holdout. setUpModule arms a process guard
that refuses every process start, clears this process's environment to a fixed few names, and fills run_take's
PENDING Gemini billing-route names with an empty tuple for the fake only; tearDownModule undoes all of it and restores
sys.path.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
_SYS_PATH = list(sys.path)
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent_adapter as aa  # noqa: E402
import transcript_view as tv  # noqa: E402
from box import run_take as rt  # noqa: E402

try:                                   # absent on the lane's base: every bound check then fails by its own assertion
    import transcript_gemini as tg  # noqa: E402
except ModuleNotFoundError:
    tg = types.ModuleType("transcript_gemini")
    tg.__file__ = str(HERE / "transcript_gemini.py")
try:
    import gemini_adapter as ga  # noqa: E402
except ModuleNotFoundError:
    ga = types.ModuleType("gemini_adapter")
    ga.__file__ = str(HERE / "gemini_adapter.py")

FIXTURES = HERE / "tests" / "fixtures" / "gemini-streams"
README = FIXTURES / "README.md"
SYNTHETIC_LABEL = "SYNTHETIC, from D8 section 1 documentation, not a recorded stream."
LABEL = re.compile(r"^- `([^`]+)`: (SYNTHETIC|RECORDED)\b(.*)$")
# A RECORDED label names the walk and the harness version it was captured at (W11B-R1-9, as w11a's W11A-R1-9).
RECORDED_LABEL = re.compile(r"RECORDED at walk [A-Za-z0-9][A-Za-z0-9._-]*, gemini-cli [0-9]+\.[0-9]+\.[0-9]+\.")

D8_EVENTS = ("init", "message", "tool_use", "tool_result", "error", "result")
D8_STATS = ("total_tokens", "input_tokens", "output_tokens", "cached", "input", "duration_ms", "tool_calls")
SID = "synthetic-session-0001"
SID2 = "synthetic-session-0002"
TAKE = "ef" * 32
MODEL = "gemini-3.8-flash"
OTHER_MODEL = "gemini-3.1-flash-lite"
MODE = "yolo"
VERSION = "0.63.0"
LOGIN = "GEMINI_API_KEY"
LOGIN_VALUE = "synthetic-login-value-" + "0123456789abcdef"     # a planted fake, never a real key
STATS = {"total_tokens": 1500, "input_tokens": 1200, "output_tokens": 90, "cached": 800, "input": 400,
         "duration_ms": 5000, "tool_calls": 3,
         "models": {MODEL: {"total_tokens": 1500, "input_tokens": 1200, "output_tokens": 90, "cached": 800,
                            "input": 400}}}

SCRATCH: Path | None = None
_STACK = contextlib.ExitStack()


class GuardTripped(Exception):
    """A process start this module never allows."""


def _trip(name):
    def trip(*a, **kw):
        raise GuardTripped(f"process guard: {name} refused")
    return trip


def setUpModule():
    global SCRATCH
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w11b-"))).resolve()
    keep = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TMPDIR") if k in os.environ}
    keep.update(HOME=str(SCRATCH))
    _STACK.enter_context(mock.patch.dict(os.environ, keep, clear=True))
    for name in ("run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _trip(f"subprocess.{name}")))
    for name in ("system", "popen", "posix_spawn", "posix_spawnp", "fork", "forkpty"):
        if hasattr(os, name):
            _STACK.enter_context(mock.patch.object(os, name, _trip(f"os.{name}")))
    # Gemini's own billing-route names are PENDING until named from its documentation: none, for the fake only.
    _STACK.enter_context(mock.patch.object(rt, "VENDOR_BILLING_ROUTE_VARIABLES", {rt.CODEX: rt.PENDING, rt.GEMINI: ()}))
    # B11 (lane vendor-b11 round 3): run_take.check_config_folder runs before every arm G exec; its own tests are
    # tests/test_config_folder.py. Here, where the adapter is the subject, it is a spy recording what each turn handed it
    # (TestTheAdapter.test_a15 binds that), never a pass of the real check.
    CONFIG_CHECKS.clear()
    _STACK.enter_context(mock.patch.object(rt, "check_config_folder", config_check_spy))


def tearDownModule():
    _STACK.close()
    sys.path[:] = _SYS_PATH


CONFIG_CHECKS: list = []


def config_check_spy(folder, *, harness, run_tree, turn):
    """B11's check, recorded (setUpModule installs it): each call's record, harness, run tree and turn number."""
    CONFIG_CHECKS.append({"folder": folder, "harness": harness, "run_tree": run_tree, "turn": turn})


# ------------------------------------------------------------------------------------------------ fixtures and fakes
def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def lines(name: str) -> list:
    return [ln for ln in fixture(name).splitlines() if ln.strip()]


def recs(name: str) -> list:
    return [json.loads(ln) for ln in lines(name)]


def jl(records) -> str:
    return "".join(json.dumps(r) + "\n" for r in records)


def jl_raw(records) -> str:
    """JSON Lines as Node's JSON.stringify writes them: U+2028 and U+0085 raw inside strings, never escaped."""
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


# One valid record per event type, for the single-change tests (W11B-R1-5).
def valid_records() -> dict:
    return {"init": ev("init", session_id=SID, model=MODEL),
            "message": ev("message", role="assistant", content="x", delta=True),
            "tool_use": ev("tool_use", tool_name="read_file", tool_id="t1", parameters={"file_path": "a"}),
            "tool_result": ev("tool_result", tool_id="t1", status="error", output="o",
                              error={"type": "x", "message": "m"}),
            "error": ev("error", severity="warning", message="m"),
            "result": result("error", error={"type": "x", "message": "m"})}


REQUIRED_KEYS = {"init": ("type", "session_id", "model"), "message": ("type", "role", "content"),
                 "tool_use": ("type", "tool_name", "tool_id", "parameters"), "tool_result": ("type", "tool_id", "status"),
                 "error": ("type", "message"), "result": ("type", "status")}


def labels() -> dict:
    """{fixture name: (SYNTHETIC | RECORDED, the rest of its line)} from the folder's README."""
    out = {}
    for ln in README.read_text(encoding="utf-8").splitlines():
        m = LABEL.match(ln)
        if m:
            out[m.group(1)] = (m.group(2), m.group(3))
    return out


def ev(t, **kw) -> dict:
    return {"type": t, "timestamp": "2026-10-12T00:00:00.000Z", **kw}


def result(status="success", stats=None, **kw) -> dict:
    r = ev("result", status=status, **kw)
    r["stats"] = json.loads(json.dumps(STATS)) if stats is None else stats
    return r


def stats_with(**changes) -> dict:
    s = json.loads(json.dumps(STATS))
    for k, v in changes.items():
        if v is KeyError:
            del s[k]
        else:
            s[k] = v
    return s


class FakeRuntime:
    """Answers the adapter's execs: `gemini --version` and a turn (`gemini -p ...`), from a queue of streams."""

    def __init__(self, streams, *, version_out=f"{VERSION}\n", exit_codes=None, timeout_at=None, version_code=0):
        self.streams, self.exit_codes = list(streams), list(exit_codes or [])
        self.version_out, self.timeout_at, self.version_code = version_out, timeout_at, version_code
        self.calls: list = []

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        self.calls.append(a)
        if a[-2:] == ["gemini", "--version"]:
            return rt.Completed(self.version_code, self.version_out, "")
        if a[:2] == ["docker", "exec"] and "gemini" in a and a[a.index("gemini") + 1:a.index("gemini") + 2] == ["-p"]:
            n = len(turn_calls(self))
            out = self.streams[n - 1]
            if self.timeout_at == n:
                e = TimeoutError("synthetic: the turn exceeded its budget")
                e.stdout = out
                raise e
            code = self.exit_codes[n - 1] if n <= len(self.exit_codes) else 0
            return rt.Completed(code, out, "")
        raise GuardTripped(f"the fake runtime refuses {a[:6]!r}")


def turn_calls(box) -> list:
    """The inner argv (after the container id) of every turn exec the fake runtime saw."""
    return [c[c.index(TAKE) + 1:] for c in box.calls if TAKE in c and "-p" in c]


class Counters:
    def __init__(self, rises=()):
        self.reads, self.rises = 0, list(rises)

    def __call__(self):
        self.reads += 1
        k = (self.reads - 1) // 2
        oom = sum(self.rises[:k]) + (self.rises[k] if self.reads % 2 == 0 and k < len(self.rises) else 0)
        return {"oom_kill": oom, "pids_max": 0}


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        self.now += 1
        return self.now


def login_file() -> str:
    path = SCRATCH / f"login-{len(list(SCRATCH.iterdir()))}"
    path.write_text(f"{LOGIN}={LOGIN_VALUE}\n")
    os.chmod(path, 0o600)
    return str(path)


_DEFAULT_PIN = object()


def adapter(mod, runtime, *, mode=MODE, counters=None, pin=_DEFAULT_PIN):
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    return mod.GeminiAdapter(runtime=runtime, take_id=TAKE, run_tree=str(SCRATCH / "tree"), login_file=login_file(),
                             model=MODEL, pin={"permission_mode": mode, "version": VERSION} if pin is _DEFAULT_PIN else pin,
                             stream_path_for=lambda n: str(folder / f"turn-{n}.jsonl"),
                             counters_for=counters or Counters(), clock=Clock())


def take(mod, streams, **kw):
    """A started take on a fake runtime of `streams`; (adapter, runtime)."""
    box = FakeRuntime(streams, **{k: v for k, v in kw.items() if k in ("exit_codes", "timeout_at", "version_out", "version_code")})
    a = adapter(mod, box, **{k: v for k, v in kw.items() if k in ("counters",)})
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    return a, box


def refusal(fn, *errors):
    """None when fn() raised one of `errors` (a typed refusal); else a short phrase of what happened instead."""
    try:
        fn()
    except errors:
        return None
    except Exception as e:  # noqa: BLE001
        return f"raised {type(e).__name__} instead of a typed refusal"
    return "accepted it"


def accepted(fn):
    """None when fn() returned; else a short phrase of what it raised."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        return f"raised {type(e).__name__}: {str(e)[:160]}"
    return None


TG_API = ("check_record", "check_stats", "decode", "GeminiParser", "ShapeError", "EVENT_TYPES", "STATS_COUNTS",
          "GEMINI_TOOLS")
GA_API = ("read_stream", "GeminiAdapter", "argv", "end_reason", "exit_meaning", "StreamError", "SHAPES_SOURCE",
          "SHAPES_SOURCES", "MODE_FLAGS", "EXIT_MEANINGS")


def guarded(prefix, api):
    """A bound check never raises: an unexpected exception is an ERROR line, never a kill; a module without the
    lane's names fails by the check's own line."""
    def wrap(fn):
        def check(mod):
            gone = [n for n in api if not hasattr(mod, n)]
            if gone:
                return [f"{prefix}: {Path(mod.__file__).name} has no {', '.join(gone)}"]
            try:
                return fn(mod, prefix)
            except Exception as e:  # noqa: BLE001
                return [f"ERROR {prefix}: {type(e).__name__}: {str(e)[:240]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


# ------------------------------------------------------------------------------------------------ transcript_gemini
def _both_refuse(mod, p, line, what) -> list:
    if not isinstance(line, str):
        line = json.dumps(line)
    out = []
    got = refusal(lambda: mod.decode(line), mod.ShapeError)
    if got:
        out.append(f"{p}: the record check {got}: {what}")
    got = refusal(lambda: mod.GeminiParser().items(line), mod.ShapeError)
    if got:
        out.append(f"{p}: the parser {got}: {what}")
    return out


def _both_accept(mod, p, rec, what) -> list:
    line = json.dumps(rec)
    out = []
    for who, fn in (("the record check", lambda: mod.decode(line)), ("the parser", lambda: mod.GeminiParser().items(line))):
        got = accepted(fn)
        if got:
            out.append(f"{p}: {who} {got}: {what}")
    return out


@guarded("S1-event", TG_API)
def s1_event(mod, p):
    out = []
    if tuple(mod.EVENT_TYPES) != D8_EVENTS:
        out.append(f"{p}: the event table is {mod.EVENT_TYPES}, not D8's {D8_EVENTS}")
    out += _both_refuse(mod, p, lines("unknown-event.jsonl")[2], "a `thought` event")
    out += _both_refuse(mod, p, {"type": "stats"}, "an event type D8 does not name")
    out += _both_refuse(mod, p, [{"type": "init"}], "a record that is not an object")
    out += _both_refuse(mod, p, '{"type": "init", "session_id"', "a line that is not JSON")
    return out


@guarded("S2-key", TG_API)
def s2_key(mod, p):
    out = []
    out += _both_refuse(mod, p, ev("init", session_id=SID), "an init without its model")
    out += _both_refuse(mod, p, ev("tool_use", tool_name="read_file", tool_id="t1"), "a tool_use without parameters")
    out += _both_refuse(mod, p, lines("unknown-key.jsonl")[2], "a message carrying `phase`")
    out += _both_refuse(mod, p, ev("init", session_id=SID, model=MODEL, auth="api-key"), "an init carrying `auth`")
    bad_error = {"type": "x", "message": "m", "code": 429}
    out += _both_refuse(mod, p, result("error", error=bad_error), "a result error carrying `code`")
    out += _both_refuse(mod, p, ev("tool_result", tool_id="t1", status="error", error=bad_error),
                        "a tool_result error carrying `code`")
    out += _both_refuse(mod, p, result("error", error={"type": "x"}), "a result error without its message")
    out += _both_refuse(mod, p, result("error", error=["type", "message"]), "a result error that is a list")
    out += _both_accept(mod, p, result("success"), "a result with no error")
    for t, rec in valid_records().items():
        out += _both_accept(mod, p, rec, f"a valid {t} carrying every allowed key")
        for key in REQUIRED_KEYS[t]:
            one = {k: v for k, v in rec.items() if k != key}
            out += _both_refuse(mod, p, one, f"a {t} without its {key}")
    for name in ("turn1-tools.jsonl", "turn2-resume.jsonl", "error-result.jsonl", "agent-says-429.jsonl",
                 "no-init.jsonl", "turn-limit.jsonl", "tool-only.jsonl", "blank-assistant.jsonl"):
        for ln in lines(name):
            got = accepted(lambda: mod.decode(ln))
            if got:
                out.append(f"{p}: {name}: a pre-registered record {got}")
    return out


@guarded("S3-words", TG_API)
def s3_words(mod, p):
    out = []
    out += _both_refuse(mod, p, ev("message", role="system", content="x"), "a message whose role is `system`")
    out += _both_refuse(mod, p, ev("message", role="assistant", content=["x"]), "a message whose content is a list")
    out += _both_refuse(mod, p, ev("tool_result", tool_id="t1", status="cancelled"), "a tool_result status `cancelled`")
    out += _both_refuse(mod, p, result("ok"), "a result status `ok`")
    out += _both_refuse(mod, p, ev("error", severity="fatal", message="m"), "an error severity `fatal`")
    out += _both_refuse(mod, p, ev("tool_use", tool_name="read_file", tool_id=7, parameters={"file_path": "a"}),
                        "a tool_use id that is a number")
    out += _both_refuse(mod, p, ev("tool_use", tool_name="read_file", tool_id="", parameters={"file_path": "a"}),
                        "an empty tool_use id")
    out += _both_refuse(mod, p, ev("tool_result", tool_id="", status="success"), "an empty tool_result id")
    out += _both_accept(mod, p, ev("error", message="m"), "an error event without a severity")
    base = valid_records()
    for t, key, v in (("message", "content", 5), ("message", "delta", "yes"), ("message", "delta", 1),
                      ("message", "role", 5), ("message", "timestamp", {"x": [1]}), ("init", "session_id", 5),
                      ("init", "model", ["m"]), ("tool_use", "tool_name", 5), ("tool_use", "tool_id", 7),
                      ("tool_use", "parameters", ["file_path"]), ("tool_result", "output", [1]),
                      ("tool_result", "status", ["error"]), ("error", "message", 5), ("error", "severity", 5),
                      ("result", "status", None), ("init", "timestamp", 1)):
        out += _both_refuse(mod, p, dict(base[t], **{key: v}), f"a {t} whose {key} is {v!r}")
    for key, v in (("type", {"a": 1}), ("message", 5)):
        bad = dict(base["result"], error=dict(base["result"]["error"], **{key: v}))
        out += _both_refuse(mod, p, bad, f"a result whose error.{key} is {v!r}")
        bad = dict(base["tool_result"], error=dict(base["tool_result"]["error"], **{key: v}))
        out += _both_refuse(mod, p, bad, f"a tool_result whose error.{key} is {v!r}")
    out += _both_accept(mod, p, dict(base["message"], delta=False), "a message whose delta is false")
    return out


@guarded("S4-stats", TG_API)
def s4_stats(mod, p):
    out = []
    if tuple(mod.STATS_COUNTS) != D8_STATS:
        out.append(f"{p}: the stats counts are {mod.STATS_COUNTS}, not D8's {D8_STATS}")
    out += _both_refuse(mod, p, lines("stats-missing.jsonl")[3], "stats missing `cached`")
    out += _both_refuse(mod, p, result(stats=stats_with(total_cost=1)), "stats carrying `total_cost`")
    for what, v in (("a string", "12"), ("a bool", True), ("a float", 1.5), ("negative", -1), ("null", None)):
        out += _both_refuse(mod, p, result(stats=stats_with(input_tokens=v)), f"stats input_tokens {what}")
    out += _both_refuse(mod, p, result(stats=list(D8_STATS) + ["models"]), "stats that is a list of its keys")
    out += _both_refuse(mod, p, result(stats=stats_with(models=[MODEL])), "stats.models that is a list")
    entry_keys = ["total_tokens", "input_tokens", "output_tokens", "cached", "input"]
    out += _both_refuse(mod, p, result(stats=stats_with(models={MODEL: entry_keys})), "a model entry that is a list")
    entry = dict(STATS["models"][MODEL])
    del entry["cached"]
    out += _both_refuse(mod, p, result(stats=stats_with(models={MODEL: entry})), "a model entry missing `cached`")
    entry = dict(STATS["models"][MODEL], thoughts=3)
    out += _both_refuse(mod, p, result(stats=stats_with(models={MODEL: entry})), "a model entry carrying `thoughts`")
    for what, v in (("a bool", True), ("negative", -4)):
        entry = dict(STATS["models"][MODEL], output_tokens=v)
        out += _both_refuse(mod, p, result(stats=stats_with(models={MODEL: entry})), f"a model entry count {what}")
    out += _both_refuse(mod, p, ev("result", status="success"), "a successful result with no stats (W11B-R1-2)")
    out += _both_accept(mod, p, ev("result", status="error"), "a failed result with no stats")
    return out


@guarded("S5-tools", TG_API)
def s5_tools(mod, p):
    out = []
    kinds = {name: entry[0] for name, entry in mod.GEMINI_TOOLS.items()}
    # Round 18 B12 (glitch-26, 18 Oct 2026): the table read from the pinned 0.64.0 registry (test_gemini_tool_registry
    # holds the full spec and each entry's source); read_file's start_line and end_line, replace's allow_multiple,
    # run_shell_command's delay_ms and grep's include_pattern replace the documented guesses.
    want = {"run_shell_command": tv.SHELL, "read_file": tv.READ, "write_file": tv.WRITE, "replace": tv.EDIT,
            "glob": tv.SEARCH, "grep_search": tv.SEARCH, "search_file_content": tv.SEARCH, "list_directory": tv.OTHER,
            "write_todos": tv.OTHER, "update_topic": tv.OTHER, "activate_skill": tv.OTHER, "enter_plan_mode": tv.OTHER,
            "exit_plan_mode": tv.OTHER, "list_background_processes": tv.OTHER, "read_background_output": tv.OTHER,
            "invoke_agent": tv.DELEGATE}
    if kinds != want:
        out.append(f"{p}: the tool table's kinds are {kinds}")
    grep = ("after", "before", "case_sensitive", "context", "dir_path", "exclude_pattern", "fixed_strings",
            "include_pattern", "max_matches_per_file", "names_only", "no_ignore", "pattern", "total_max_matches")
    keys = {name: tuple(sorted(entry[2])) for name, entry in mod.GEMINI_TOOLS.items()}
    want_keys = {"run_shell_command": ("command", "delay_ms", "description", "dir_path", "is_background"),
                 "read_file": ("end_line", "file_path", "start_line"), "write_file": ("content", "file_path"),
                 "replace": ("allow_multiple", "file_path", "instruction", "new_string", "old_string"),
                 "glob": ("case_sensitive", "dir_path", "pattern", "respect_gemini_ignore", "respect_git_ignore"),
                 "grep_search": grep, "search_file_content": grep,
                 "list_directory": ("dir_path", "file_filtering_options", "ignore"), "write_todos": ("todos",),
                 "update_topic": ("strategic_intent", "summary", "title", "wait_for_previous"),
                 "activate_skill": ("name",), "enter_plan_mode": ("reason",), "exit_plan_mode": ("plan_filename",),
                 "list_background_processes": ("wait_for_previous",),
                 "read_background_output": ("delay_ms", "lines", "pid", "wait_for_previous"),
                 "invoke_agent": ("agent_name", "prompt", "wait_for_previous")}
    if keys != want_keys:
        out.append(f"{p}: the tool table's allowed keys are {keys}")
    for name, allowed in want_keys.items():
        if name not in mod.GEMINI_TOOLS:
            continue
        for key in allowed:
            base = {"command": "ls"} if name == "run_shell_command" else (
                {"file_path": "a"} if name in ("read_file", "write_file", "replace") else (
                    {"pattern": "p"} if name in ("glob", "grep_search", "search_file_content") else {}))
            line = json.dumps(ev("tool_use", tool_name=name, tool_id="t1", parameters=dict(base, **{key: True if key == "is_background" else "x"})))
            if accepted(lambda: mod.check_record(json.loads(line))):
                out.append(f"{p}: {name} with its key {key} is refused")
    full = {"run_shell_command": ({"command": "ls", "description": "d", "dir_path": "src", "is_background": True,
                                   "delay_ms": 10}, tv.SHELL, {"command": "ls", "background": True}),
            "read_file": ({"file_path": "a.txt", "start_line": 1, "end_line": 5}, tv.READ, {"path": "a.txt"}),
            "write_file": ({"file_path": "a.txt", "content": "x"}, tv.WRITE, {"path": "a.txt"}),
            "replace": ({"file_path": "b.py", "old_string": "a", "new_string": "b", "allow_multiple": False,
                         "instruction": "i"}, tv.EDIT, {"path": "b.py"}),
            "glob": ({"pattern": "*.py", "dir_path": "src", "case_sensitive": False, "respect_git_ignore": True,
                      "respect_gemini_ignore": True}, tv.SEARCH, {"pattern": "*.py", "path": "src"}),
            "grep_search": ({"pattern": "def", "dir_path": "src", "include_pattern": "*.py"}, tv.SEARCH,
                            {"pattern": "def", "path": "src"}),
            "search_file_content": ({"pattern": "def", "dir_path": "src", "include_pattern": "*.py"}, tv.SEARCH,
                                    {"pattern": "def", "path": "src"}),
            "list_directory": ({"dir_path": ".", "ignore": ["x"], "file_filtering_options": {}}, tv.OTHER, {}),
            "write_todos": ({"todos": []}, tv.OTHER, {}),
            "update_topic": ({"title": "t", "summary": "s", "strategic_intent": "i"}, tv.OTHER, {}),
            "activate_skill": ({"name": "n"}, tv.OTHER, {}),
            "enter_plan_mode": ({"reason": "r"}, tv.OTHER, {}),
            "exit_plan_mode": ({"plan_filename": "p.md"}, tv.OTHER, {}),
            "list_background_processes": ({}, tv.OTHER, {}),
            "read_background_output": ({"pid": 1, "lines": 5}, tv.OTHER, {}),
            "invoke_agent": ({"agent_name": "a", "prompt": "p"}, tv.DELEGATE, {})}
    for name, (params, kind, args) in full.items():
        line = json.dumps(ev("tool_use", tool_name=name, tool_id="t1", parameters=params))
        got = accepted(lambda: mod.GeminiParser().items(line))
        if got:
            out.append(f"{p}: {name} with every pre-registered key {got}")
            continue
        item = mod.GeminiParser().items(line)[0]
        if (item.tool, item.args) != (kind, args):
            out.append(f"{p}: {name} maps to {item.tool} {item.args}, not {kind} {args}")
    out += _both_refuse(mod, p, lines("unknown-tool.jsonl")[2], "a web_fetch call")
    out += _both_refuse(mod, p, ev("tool_use", tool_name="read_many_files", tool_id="t1", parameters={"paths": ["a"]}),
                        "a read_many_files call")
    out += _both_refuse(mod, p, ev("tool_use", tool_name="read_file", tool_id="t1",
                                   parameters={"absolute_path": "/a"}), "a read_file argument key with no entry")
    return out


@guarded("S6-error-text", TG_API + ("error_text",))
def s6_error_text(mod, p):
    out = []
    cases = ((ev("error", severity="error", message="synthetic words"), "synthetic words"),
             (result("error", error={"type": "x", "message": "synthetic failure"}), "synthetic failure"),
             (result("success"), None), (ev("message", role="assistant", content="agent words"), None),
             (ev("tool_result", tool_id="t1", status="error", error={"type": "x", "message": "a tool's words"}), None),
             (ev("result", status="error"), None))
    for rec, want in cases:
        try:
            got = mod.error_text(rec)
        except Exception as e:  # noqa: BLE001
            got = f"raised {type(e).__name__}"
        if got != want:
            out.append(f"{p}: the error text of a {rec['type']} reads {got!r}, not {want!r}")
    return out


@guarded("S7-open-input", TG_API + ("OPEN_INPUT",))
def s7_open_input(mod, p):
    """Lane vendor-b16 round 2 (glitch-26's ruling R-B16-2): tests/test_gemini_undeclared_args.py's U1-U3 against this
    module, so the generated sweep sees the rule: the held walk's grep_search shape read with file_path named and
    ignored, the refusals that stand, and each OPEN_INPUT entry cited."""
    if str(HERE / "tests") not in sys.path:
        sys.path.insert(0, str(HERE / "tests"))
    import test_gemini_undeclared_args as u
    return [f"{p}: {x}" for x in u.u1_problems(mod) + u.u2_problems(mod) + u.u3_problems(mod)]


def view_events(mod, name_or_lines):
    src = lines(name_or_lines) if isinstance(name_or_lines, str) else name_or_lines
    with mock.patch.dict(tv.PARSERS, {"gemini": mod.GeminiParser()}):
        return tv.events("gemini", src)


@guarded("P1-view", TG_API)
def p1_view(mod, p):
    out = []
    got = [(e.turn, e.kind, e.tool, e.args, e.text) for e in view_events(mod, "turn1-tools.jsonl")]
    h = tv.HARNESS
    want = [(0, h, None, None, f"2026-10-12T00:00:01.000Z\n{SID}\n{MODEL}"),
            (1, tv.OPERATOR, None, None, "Synthetic operator line one."),
            (1, tv.AGENT_TEXT, None, None, "Synthetic reply "), (1, tv.AGENT_TEXT, None, None, "one."),
            (1, tv.TOOL_CALL, tv.SHELL, {"command": "ls", "background": False}, None),
            (1, tv.TOOL_RESULT, tv.SHELL, None, "README.md\n"),
            (1, tv.TOOL_CALL, tv.READ, {"path": "README.md"}, None),
            (1, tv.TOOL_RESULT, tv.READ, None, "synthetic file text"),
            (1, tv.TOOL_CALL, tv.EDIT, {"path": "src/b.py"}, None),
            (1, tv.TOOL_RESULT, tv.EDIT, None, "edit_no_occurrence_found\nsynthetic: no match"),
            (1, h, None, None, "2026-10-12T00:00:11.000Z\nsuccess")]
    if got != want:
        out.append(f"{p}: turn1-tools reads as {got}")
    got = [(e.kind, e.tool, e.args) for e in view_events(mod, "turn2-resume.jsonl") if e.kind == tv.TOOL_CALL]
    want = [(tv.TOOL_CALL, tv.WRITE, {"path": "notes/a.txt"}), (tv.TOOL_CALL, tv.SEARCH, {"pattern": "*.py", "path": "src"}),
            (tv.TOOL_CALL, tv.SEARCH, {"pattern": "def ", "path": "src"})]
    if got != want:
        out.append(f"{p}: turn2-resume's calls read as {got}")
    with mock.patch.dict(tv.PARSERS, {"gemini": mod.GeminiParser()}):
        counts = tv.harness_types("gemini", lines("error-result.jsonl"))
    if counts != {"init": 1, "error": 1, "result": 1}:
        out.append(f"{p}: error-result's harness types read as {counts}")
    got = [e.kind for e in view_events(mod, "error-result.jsonl")]
    if got != [h, tv.OPERATOR, h, h]:
        out.append(f"{p}: error-result reads as {got}")
    if not isinstance(tv.PARSERS.get("gemini"), tv.VendorBoundParser):
        out.append(f"{p}: the published parser does not require bound native records")
    if mod.GeminiParser.event_types != mod.EVENT_TYPES or mod.GeminiParser.tools is not mod.GEMINI_TOOLS:
        out.append(f"{p}: the parser does not name its own tables")
    return out


# ------------------------------------------------------------------------------------------------ gemini_adapter
@guarded("A1-stream", GA_API)
def a1_stream(mod, p):
    out = []
    r = mod.read_stream(fixture("turn1-tools.jsonl"), model=MODEL)
    want = {"init_model": MODEL, "session_id": SID, "agent_text": "Synthetic reply one.", "agent_output": True,
            "api_errors": [], "status": "success", "stats": STATS, "served_models": [MODEL], "results": 1,
            "tool_ids": ["tool-1", "tool-2", "tool-3"], "undecoded": 0}
    if r != want:
        out.append(f"{p}: turn1-tools reads as {r}")
    def said(*records):
        try:
            return mod.read_stream(jl(records), model=MODEL)["agent_text"]
        except Exception as e:  # noqa: BLE001
            return f"raised {type(e).__name__}"
    a, b = (ev("message", role="assistant", content=x, delta=True) for x in ("a", "b"))
    whole_a, whole_b = (ev("message", role="assistant", content=x) for x in ("a", "b"))
    tool = ev("tool_use", tool_name="list_directory", tool_id="t1", parameters={"dir_path": "."})
    for what, records, want in (("two delta chunks", (a, b), "ab"), ("two delta runs split by a tool call", (a, tool, b), "a\nb"),
                                ("two whole messages", (whole_a, whole_b), "a\nb"),
                                ("a whole message, then a delta chunk", (whole_a, b), "a\nb"),
                                ("a delta chunk, then a whole message", (a, whole_b), "a\nb")):
        got = said(*records)
        if got != want:
            out.append(f"{p}: {what} read as {got!r}, not {want!r}")
    spaced = mod.read_stream("\n   \n" + fixture("turn1-tools.jsonl").replace("\n", "\n\n"), model=MODEL)
    if spaced["undecoded"] != 0:
        out.append(f"{p}: blank lines were counted as {spaced['undecoded']} undecoded")
    cut = "".join(fixture("turn1-tools.jsonl").splitlines(keepends=True)[:-1]) + '{"type": "res'
    r = mod.read_stream(cut, model=MODEL)
    if (r["undecoded"], r["results"], r["status"], r["stats"]) != (1, 0, None, None):
        out.append(f"{p}: a cut stream reads undecoded {r['undecoded']}, results {r['results']}, stats {r['stats']}")
    after_tool = jl([ev("tool_use", tool_name="list_directory", tool_id="t1", parameters={"dir_path": "."})]) + "{cut\n"
    got = accepted(lambda: mod.read_stream(after_tool, model=MODEL))
    r = None if got else mod.read_stream(after_tool, model=MODEL)
    if got or (r["tool_ids"], r["undecoded"]) != (["t1"], 1):
        out.append(f"{p}: a cut line after a tool call reads {got or (r['tool_ids'], r['undecoded'])}")
    mid = jl([ev("init", session_id=SID, model=MODEL)]) + "{cut\n" + jl([result()])
    got = refusal(lambda: mod.read_stream(mid, model=MODEL), mod.StreamError)
    if got:
        out.append(f"{p}: a line that is not JSON before the last {got} (W11B-R1-1)")
    for lone in ("Error: quota exceeded\n", '{"type": "ini', "\n  \nnot json\n\n"):
        got = refusal(lambda: mod.read_stream(lone, model=MODEL), mod.StreamError)
        if got:
            out.append(f"{p}: a stream whose only non-blank line is not JSON {got} (W11B-R2-1): {lone!r}")
    init = ev("init", session_id=SID, model=MODEL)
    for sep in ("\u2028", "\u0085"):
        cmd = ev("tool_use", tool_name="run_shell_command", tool_id="t1", parameters={"command": f"echo a{sep}b"})
        failed = result("error", error={"type": "x", "message": f"synthetic{sep}failure"})
        said_ = ev("message", role="assistant", content=f"x{sep}y")
        got = accepted(lambda: mod.read_stream(jl_raw([init, cmd, said_, failed]), model=MODEL))
        if got:
            out.append(f"{p}: a stream holding {sep!r} inside its strings {got}")
            continue
        r = mod.read_stream(jl_raw([init, cmd, said_, failed]), model=MODEL)
        want = (["t1"], True, f"x{sep}y", "error", 0,
                [{"status": None, "type": "x", "text": f"synthetic{sep}failure"}])
        got = (r["tool_ids"], r["agent_output"], r["agent_text"], r["status"], r["undecoded"], r["api_errors"])
        if got != want:
            out.append(f"{p}: a stream holding {sep!r} inside a command and an error message reads {got}")
    for t, rec in valid_records().items():
        for key in REQUIRED_KEYS[t]:
            one = {k: v for k, v in rec.items() if k != key}
            got = refusal(lambda: mod.read_stream(jl([one]), model=MODEL), mod.StreamError)
            if got:
                out.append(f"{p}: the adapter's reader {got}: a {t} without its {key}")
    for bad_text in (None, b"{}"):
        got = refusal(lambda: mod.read_stream(bad_text, model=MODEL), mod.StreamError)
        if got:
            out.append(f"{p}: a stream that is {type(bad_text).__name__} {got}")
    two_inits = jl(recs("turn1-tools.jsonl")[:1] * 2)
    got = refusal(lambda: mod.read_stream(two_inits, model=MODEL), mod.StreamError)
    if got:
        out.append(f"{p}: two init records {got}")
    two_results = jl([result(), result()])
    got = refusal(lambda: mod.read_stream(two_results, model=MODEL), mod.StreamError)
    if got:
        out.append(f"{p}: two result records {got}")
    for name in ("unknown-event.jsonl", "unknown-key.jsonl", "unknown-tool.jsonl", "stats-missing.jsonl"):
        got = refusal(lambda: mod.read_stream(fixture(name), model=MODEL), mod.StreamError)
        if got:
            out.append(f"{p}: the adapter's reader {got}: {name}")
    return out


@guarded("A2-error", GA_API)
def a2_error(mod, p):
    out = []
    r = mod.read_stream(fixture("agent-says-429.jsonl"), model=MODEL)
    if r["api_errors"] != [] or "429" not in r["agent_text"]:
        out.append(f"{p}: an agent message that says 429 was read as {r['api_errors']} (text {r['agent_text']!r})")
    r = mod.read_stream(fixture("error-result.jsonl"), model=MODEL)
    want = [{"status": None, "type": "error", "text": "synthetic harness error: 429 Too Many Requests"},
            {"status": None, "type": "synthetic_api_error", "text": "synthetic harness error: quota exhausted"}]
    if r["api_errors"] != want or r["agent_output"] is not False or r["agent_text"] != "":
        out.append(f"{p}: the failed call reads {r['api_errors']}, output {r['agent_output']}, text {r['agent_text']!r}")
    bare_fail = jl([ev("result", status="error")])
    got = accepted(lambda: mod.read_stream(bare_fail, model=MODEL))
    r = None if got else mod.read_stream(bare_fail, model=MODEL)
    if got or r["api_errors"] != [{"status": None, "type": None, "text": None}]:
        out.append(f"{p}: a failed result with no error object reads {got or r['api_errors']}")
    r = mod.read_stream(fixture("no-init.jsonl"), model=MODEL)
    if r["agent_output"] is not False or r["agent_text"] != "" or len(r["api_errors"]) != 1:
        out.append(f"{p}: an error event alone reads output {r['agent_output']}, text {r['agent_text']!r}")
    if mod.read_stream(fixture("turn1-tools.jsonl"), model=MODEL)["api_errors"] != []:
        out.append(f"{p}: a successful result was read as an api error")
    return out


@guarded("A3-output", GA_API)
def a3_output(mod, p):
    out = []
    user_only = jl([ev("message", role="user", content="Synthetic operator line."), ev("error", message="m")])
    r = mod.read_stream(user_only, model=MODEL)
    if r["agent_output"] is not False or r["agent_text"] != "":
        out.append(f"{p}: a user message read as agent output ({r['agent_output']}, {r['agent_text']!r})")
    if mod.read_stream(fixture("blank-assistant.jsonl"), model=MODEL)["agent_output"] is not False:
        out.append(f"{p}: a blank assistant message read as agent output")
    if mod.read_stream(fixture("tool-only.jsonl"), model=MODEL)["agent_output"] is not True:
        out.append(f"{p}: a turn with only a tool call read as no agent output")
    if mod.read_stream(fixture("agent-says-429.jsonl"), model=MODEL)["agent_output"] is not True:
        out.append(f"{p}: an assistant message with words read as no agent output")
    return out


@guarded("A4-stats", GA_API)
def a4_stats(mod, p):
    out = []
    r = mod.read_stream(fixture("turn2-resume.jsonl"), model=MODEL)
    if r["stats"] != STATS:
        out.append(f"{p}: the result's stats read as {r['stats']}")
    if mod.read_stream(fixture("no-init.jsonl"), model=MODEL)["stats"] is not None:
        out.append(f"{p}: a call with no result carries stats")
    bare = jl([ev("init", session_id=SID, model=MODEL), ev("result", status="success")])
    got = refusal(lambda: mod.read_stream(bare, model=MODEL), mod.StreamError)
    if got:
        out.append(f"{p}: a successful result with no stats {got} (W11B-R1-2: never end_turn unmeasured)")
    bare_fail = jl([ev("init", session_id=SID, model=MODEL), ev("result", status="error")])
    got = accepted(lambda: mod.read_stream(bare_fail, model=MODEL))
    if got:
        out.append(f"{p}: a failed result with no stats {got}")
    else:
        r = mod.read_stream(bare_fail, model=MODEL)
        if (r["stats"], r["served_models"]) != (None, []):
            out.append(f"{p}: a failed result with no stats reads {r['stats']}, {r['served_models']}")
    got = refusal(lambda: mod.read_stream(fixture("stats-missing.jsonl"), model=MODEL), mod.StreamError)
    if got:
        out.append(f"{p}: a stats count that is missing {got} (never read as 0)")
    return out


@guarded("A5-model", GA_API)
def a5_model(mod, p):
    out = []
    for name, what in (("init-other-model.jsonl", "an init naming another model"),
                       ("stats-other-model.jsonl", "stats.models naming the row's model and another")):
        got = refusal(lambda: mod.read_stream(fixture(name), model=MODEL), mod.StreamError)
        if got:
            out.append(f"{p}: {what} {got}")
    for bad in ("", 5, "--sandbox", "-s", "a b"):
        got = refusal(lambda: mod.read_stream(fixture("no-init.jsonl"), model=bad), mod.StreamError)
        if got:
            out.append(f"{p}: a stream read against model {bad!r} {got}")
    empty = stats_with(models={})
    for what, records, refused in (
            ("stats naming no model and no init", [result(stats=empty)], True),
            ("stats naming no model under an init", [ev("init", session_id=SID, model=MODEL), result(stats=empty)], False),
            ("stats naming the model and no init", [result()], False),
            ("a failed result with no stats and no init", [ev("result", status="error")], False)):
        if refused:
            got = refusal(lambda: mod.read_stream(jl(records), model=MODEL), mod.StreamError)
            if got:
                out.append(f"{p}: {what} {got} (W11B-R1-3)")
        else:
            got = accepted(lambda: mod.read_stream(jl(records), model=MODEL))
            if got:
                out.append(f"{p}: {what} {got}")
    only_other = jl([result(stats=stats_with(models={OTHER_MODEL: STATS["models"][MODEL]}))])
    got = refusal(lambda: mod.read_stream(only_other, model=MODEL), mod.StreamError)
    if got:
        out.append(f"{p}: stats.models naming only another model {got}")
    r = mod.read_stream(fixture("turn1-tools.jsonl"), model=MODEL)
    if r["served_models"] != [MODEL]:
        out.append(f"{p}: the served models read as {r['served_models']}")
    a, _ = take(mod, [fixture("turn1-tools.jsonl"), fixture("stats-other-model.jsonl")])
    t1 = a.turn("one", first=True, budget_s=60)
    if t1.init is not None or "permission mode" not in (a.turn_records[0]["why_no_init"] or ""):
        out.append(f"{p}: turn 1's init is {t1.init} (why {a.turn_records[0]['why_no_init']!r})")
    if a.turn_records[0]["init_model"] != MODEL:
        out.append(f"{p}: turn 1's record keeps init model {a.turn_records[0]['init_model']!r}")
    got = refusal(lambda: a.turn("two", first=False, budget_s=60), mod.StreamError)
    if got:
        out.append(f"{p}: turn 2's stats.models naming another model {got}")
    return out


@guarded("A6-argv", GA_API)
def a6_argv(mod, p):
    out = []
    first = later = None
    got = accepted(lambda: mod.argv("one", model=MODEL, mode=MODE, session_id=None, first=True))
    if got:
        out.append(f"{p}: the first turn's argv (no session id yet) {got}")
    else:
        first = mod.argv("one", model=MODEL, mode=MODE, session_id=None, first=True)
    got = accepted(lambda: mod.argv("two", model=MODEL, mode=MODE, session_id=SID, first=False))
    if got:
        out.append(f"{p}: a later turn's argv {got}")
    else:
        later = mod.argv("two", model=MODEL, mode=MODE, session_id=SID, first=False)
    if first != ["gemini", "-p", "one", "-o", "stream-json", "-m", MODEL, "--approval-mode", "yolo"]:
        out.append(f"{p}: the first turn's argv is {first}")
    if later != ["gemini", "-p", "two", "-o", "stream-json", "-m", MODEL, "--approval-mode", "yolo", "-r", SID]:
        out.append(f"{p}: a later turn's argv is {later}")
    if refusal(lambda: mod.argv("-x", model=MODEL, mode=MODE, session_id=None, first=True), mod.StreamError):
        out.append(f"{p}: a line starting with '-' was not refused")
    for sid in (None, "a b; rm", 5, "latest", "LATEST", "Latest", "1", "42"):
        got = refusal(lambda: mod.argv("two", model=MODEL, mode=MODE, session_id=sid, first=False), mod.StreamError)
        if got:
            out.append(f"{p}: a later turn with session id {sid!r} {got}")
    for what, kw in (("an empty line", {"line": ""}), ("a line that is a number", {"line": 5}),
                     ("an empty model", {"model": ""}), ("a model that is a number", {"model": 5}),
                     ("the model --sandbox (W11B-R1-6)", {"model": "--sandbox"}), ("the model -s", {"model": "-s"}),
                     ("a model holding a space", {"model": "gemini 3"}), ("an unknown mode", {"mode": "default"})):
        args = dict({"line": "one", "model": MODEL, "mode": MODE, "session_id": None, "first": True}, **kw)
        line = args.pop("line")
        got = refusal(lambda: mod.argv(line, **args), mod.StreamError)
        if got:
            out.append(f"{p}: an argv with {what} {got}")
    for what, kw, err in (("an empty model", {"model": ""}, mod.StreamError),
                          ("the model --sandbox", {"model": "--sandbox"}, mod.StreamError),
                          ("a model holding a space", {"model": "gemini 3"}, mod.StreamError),
                          ("a model that is a number", {"model": 5}, mod.StreamError),
                          ("no stream path function", {"stream_path_for": None}, TypeError),
                          ("no counters function", {"counters_for": "counters"}, TypeError),
                          ("no clock", {"clock": 100.0}, TypeError)):
        base = dict(runtime=FakeRuntime([]), take_id=TAKE, run_tree=str(SCRATCH / "tree"), login_file=login_file(),
                    model=MODEL, pin={"permission_mode": MODE}, stream_path_for=lambda n: str(SCRATCH / "x"),
                    counters_for=Counters(), clock=Clock())
        base.update(kw)
        got = refusal(lambda: mod.GeminiAdapter(**base), err)
        if got:
            out.append(f"{p}: an adapter made with {what} {got}")
    for pin in (None, "yolo", ["yolo"], {"mode": "yolo"}):
        got = refusal(lambda: adapter(mod, FakeRuntime([]), pin=pin), rt.NotReady)
        if got:
            out.append(f"{p}: an adapter whose pin is {pin!r} {got}")
    for bad in ("PENDING", "default", "", None, ["yolo"]):
        got = refusal(lambda: adapter(mod, FakeRuntime([]), mode=bad), rt.NotReady)
        if got:
            out.append(f"{p}: an adapter under mode {bad!r} {got}")
    a, box = take(mod, [fixture("turn1-tools.jsonl"), fixture("turn2-resume.jsonl"), fixture("turn2-resume.jsonl")])
    try:
        for n, line in enumerate(("first line", "second line", "third line")):
            a.turn(line, first=n == 0, budget_s=60)
    except (mod.StreamError, rt.Refused, rt.NotReady) as e:
        out.append(f"{p}: the take's turns were refused: {e}")
    turns = turn_calls(box)
    for n, inner in enumerate(turns, 1):
        if "-m" not in inner or inner[inner.index("-m") + 1] != MODEL:
            out.append(f"{p}: turn {n} does not pass -m {MODEL}")
        resumed = "-r" in inner
        if resumed != (n > 1) or (resumed and inner[inner.index("-r") + 1] != SID):
            out.append(f"{p}: turn {n} resume is {resumed} ({inner[-3:]})")
        i = inner.index("--approval-mode") if "--approval-mode" in inner else None
        if i is None or inner[i + 1:i + 2] != ["yolo"]:
            out.append(f"{p}: turn {n} lacks the pinned mode's flags")
        if any(x in ("--sandbox", "-s") or x.startswith("--sandbox") for x in inner):
            out.append(f"{p}: turn {n} passes a sandbox flag")
    if len(turns) != 3:
        out.append(f"{p}: {len(turns)} turn exec(s), not 3")
    for c in box.calls:
        if any(LOGIN_VALUE in x for x in c) or ("-p" in c and LOGIN not in c):
            out.append(f"{p}: a turn's login does not ride by name only")
    return out


@guarded("A7-session", GA_API)
def a7_session(mod, p):
    out = []
    a, _ = take(mod, [fixture("turn1-tools.jsonl"), fixture("turn2-other-session.jsonl")])
    a.turn("one", first=True, budget_s=60)
    got = refusal(lambda: a.turn("two", first=False, budget_s=60), mod.StreamError)
    if got:
        out.append(f"{p}: a later turn whose init names another session {got}")
    a, box = take(mod, [fixture("turn1-tools.jsonl"), fixture("no-init.jsonl"), fixture("turn2-resume.jsonl")])
    got = accepted(lambda: [a.turn(f"line {n}", first=n == 0, budget_s=60) for n in range(3)])
    if got:
        out.append(f"{p}: a later turn with no init, then a resume, {got}")
    resumes = [c[c.index("-r") + 1] for c in turn_calls(box) if "-r" in c]
    if resumes != [SID, SID]:
        out.append(f"{p}: the later turns resumed {resumes}, not turn 1's {SID}")
    a, _ = take(mod, [fixture("no-init.jsonl"), fixture("turn2-resume.jsonl")])
    a.turn("one", first=True, budget_s=60)
    got = refusal(lambda: a.turn("two", first=False, budget_s=60), mod.StreamError)
    if got:
        out.append(f"{p}: a later turn after a first turn with no init {got}")
    for sid in ("a b", 5, "", "latest", "LATEST", "lAtEsT", "0", "17"):
        bad = jl([ev("init", session_id=sid, model=MODEL)])
        got = refusal(lambda: mod.read_stream(bad, model=MODEL), mod.StreamError)
        if got:
            out.append(f"{p}: an init session id {sid!r} {got}")
    for sid in ("latest-session-1", "0a", "s1"):
        good = jl([ev("init", session_id=sid, model=MODEL)])
        got = accepted(lambda: mod.read_stream(good, model=MODEL))
        if got:
            out.append(f"{p}: an init session id {sid!r} {got}")
    return out


@guarded("A8-turn", GA_API)
def a8_turn(mod, p):
    out = []
    ok, failed, limit = fixture("turn1-tools.jsonl"), fixture("error-result.jsonl"), fixture("turn-limit.jsonl")
    resume = fixture("turn2-resume.jsonl")
    cut = "".join(resume.splitlines(keepends=True)[:-1])
    streams = [ok, failed, resume, limit, failed, cut, resume, resume]
    a, _ = take(mod, streams, exit_codes=[0, 1, 53, 53, 0, 0, 42], timeout_at=8,
                counters=Counters(rises=[0, 2, 0, 0, 0, 0, 0, 0]))
    got = []
    for n in range(len(streams)):
        try:
            t = a.turn(f"line {n}", first=n == 0, budget_s=60)
        except mod.StreamError as e:
            got.append(f"refused: {e}")
            break
        got.append((t.end_reason, t.exit_code, a.turn_records[n]["exit_meaning"], t.counters["oom_kill_delta"]))
    want = [(aa.END_TURN, 0, "success", 0), (aa.END_ERROR, 1, "general-or-api-error", 2),
            (aa.END_ERROR, 53, "turn-limit", 0), (aa.END_ERROR, 53, "turn-limit", 0),
            (aa.END_ERROR, 0, "success", 0), (aa.END_ERROR, 0, "success", 0),
            (aa.END_ERROR, 42, "input-error", 0), (aa.END_TIMED_OUT, None, None, 0)]
    if got != want:
        out.append(f"{p}: the turns read as {got}, not {want}")
    if [r.get("n") for r in a.turn_records] != list(range(1, len(streams) + 1)):
        out.append(f"{p}: the turn records are numbered {[r.get('n') for r in a.turn_records]}")
    want_first = {"n": 1, "first": True, "exit_code": 0, "exit_meaning": "success", "timed_out": False,
                  "init_model": MODEL, "session_id": SID, "status": "success", "stats": STATS,
                  "served_models": [MODEL], "tool_ids": ["tool-1", "tool-2", "tool-3"], "undecoded": 0,
                  "why_no_init": getattr(mod, "NO_INIT_MODE", None), "shapes_source": "recorded"}
    if a.turn_records[:1] != [want_first]:
        out.append(f"{p}: turn 1's record is {a.turn_records[:1]}")
    want_second = dict(want_first, n=2, first=False, exit_code=1, exit_meaning="general-or-api-error", status="error",
                       stats=json.loads(fixture("error-result.jsonl").splitlines()[-1])["stats"], served_models=[],
                       tool_ids=[])
    if a.turn_records[1:2] != [want_second]:
        out.append(f"{p}: turn 2's record is {a.turn_records[1:2]}")
    a, _ = take(mod, [ok, resume])
    names = [Path(a.turn(f"line {n}", first=n == 0, budget_s=60).stream_path).name for n in range(2)]
    if names != ["turn-1.jsonl", "turn-2.jsonl"]:
        out.append(f"{p}: the streams were written at {names}")
    a, _ = take(mod, [ok.replace("\n", "\n\udcff\udcfe\n", 1)])
    got = refusal(lambda: a.turn("one", first=True, budget_s=60), mod.StreamError)
    if got:
        out.append(f"{p}: a line of bytes that are not UTF-8 before the last {got} (W11B-R1-1)")
    a, _ = take(mod, [ok + "\udcff\udcfe\n"])
    got = accepted(lambda: a.turn("one", first=True, budget_s=60))
    if got or a.turn_records[0]["undecoded"] != 1:
        out.append(f"{p}: a last line of bytes that are not UTF-8 {got or a.turn_records[0]['undecoded']}")
    for code in (2, 137, True, None):
        a, _ = take(mod, [ok], exit_codes=[code])
        got = refusal(lambda: a.turn("one", first=True, budget_s=60), mod.StreamError)
        if got:
            out.append(f"{p}: exit code {code!r} {got}")
    a, box = take(mod, [ok])
    if (a.version(), a.version()) != (VERSION, VERSION):
        out.append(f"{p}: the version reads {a.version()!r}")
    asked = [c for c in box.calls if c[-2:] == ["gemini", "--version"]]
    if len(asked) != 1 or "-e" in asked[0]:
        out.append(f"{p}: `gemini --version` ran {len(asked)} time(s), or with a variable: {asked}")
    for printed, code in (("Gemini CLI 0.63.0\n", 0), ("0.63\n", 0), ("v0.63.0\n", 0), (f"{VERSION}\n", 1), (None, 0),
                          ("0.63.0-nightly.20261012\n", 0), ("0.63.0 extra\n", 0), ("0.63.0.1\n", 0)):
        a, _ = take(mod, [], version_out=printed, version_code=code)
        got = refusal(a.version, rt.NotReady)
        if got:
            out.append(f"{p}: a version printed {printed!r} with exit {code} {got}")
    return out


def label_problems(marks: dict, files) -> tuple:
    """(problems, the fixtures whose RECORDED label carries its provenance). A SYNTHETIC label must be the brief's
    words; a RECORDED label must fullmatch RECORDED_LABEL, never counted as recorded without it."""
    out = []
    wrong = [f for f, (kind, rest) in marks.items() if kind == "SYNTHETIC" and kind + rest != SYNTHETIC_LABEL]
    if wrong:
        out.append(f"fixture(s) whose label is not the brief's words: {wrong}")
    bare = [f for f, (kind, rest) in marks.items() if kind == "RECORDED" and not RECORDED_LABEL.fullmatch(kind + rest)]
    if bare:
        out.append(f"fixture(s) labelled RECORDED without the walk id and harness version: {bare}")
    recorded = [f for f, (kind, rest) in marks.items() if kind == "RECORDED" and f in files
                and RECORDED_LABEL.fullmatch(kind + rest)]
    return out, recorded


@guarded("A9-source", GA_API)
def a9_source(mod, p):
    out = []
    marks = labels()
    files = sorted(f.name for f in FIXTURES.iterdir() if f.name != README.name)
    unlabelled = [f for f in files if f not in marks]
    if unlabelled:
        out.append(f"{p}: fixture(s) with no label: {unlabelled}")
    problems, recorded = label_problems(marks, files)
    out += [f"{p}: {x}" for x in problems]
    if mod.SHAPES_SOURCE not in mod.SHAPES_SOURCES or tuple(mod.SHAPES_SOURCES) != ("documented", "recorded"):
        out.append(f"{p}: SHAPES_SOURCE {mod.SHAPES_SOURCE!r} is off the two words")
    if mod.SHAPES_SOURCE == "recorded" and not recorded:
        out.append(f"{p}: SHAPES_SOURCE reads 'recorded' while no fixture is labelled RECORDED")
    # lane pf1-l1-freeze-gates (pre-freeze review 1, m3): "recorded" rests on SHAPES_RECORDED_ON, a fixture the
    # freeze's leg i holds to its committed walk record on the pinned CLI (check_take.recorded_binding_problem)
    if mod.SHAPES_SOURCE == "recorded":
        import check_take
        pins = json.loads((HERE / "prereg-draft.json").read_text())["version_pins"]["gemini"]
        cli = check_take.VENDOR_FIXTURE_CLI["gemini"] + " " + next(iter(pins.values()))["agent_version"]
        why = check_take.recorded_binding_problem("gemini", getattr(mod, "SHAPES_RECORDED_ON", None), cli)
        if why or getattr(mod, "SHAPES_RECORDED_ON", None) != "recorded-gemini-w-g21/transcript.jsonl":
            out.append(f"{p}: SHAPES_RECORDED_ON {getattr(mod, 'SHAPES_RECORDED_ON', None)!r} does not bind: {why}")
    a, _ = take(mod, [fixture("turn1-tools.jsonl")])
    if a.harness_record() != {"harness": "gemini", "shapes_source": mod.SHAPES_SOURCE}:
        out.append(f"{p}: the harness record is {a.harness_record()}")
    a.turn("one", first=True, budget_s=60)
    if [r["shapes_source"] for r in a.turn_records] != [mod.SHAPES_SOURCE]:
        out.append(f"{p}: the turn records do not carry the shapes' source")
    return out


@guarded("A10-mode", GA_API + ("submitted_mode",))
def a10_mode(mod, p):
    """Live harness 3b review fold (integration red A4): submitted_mode, branch by branch, bound here so this module's
    own generated mutants see it. The mode is read from the box's launch journal, never the pin: no journal, a link,
    or bytes that are not one JSON object with an argv list are unobserved; the pinned flags once and no other approval
    flag give the mode; none gives "no-mode-flags-submitted"; a doubled or extra approval flag gives
    "contradictory-mode-flags"; a journal off the registered invocation gives "launch-differs-from-registered-
    invocation". The words are spelled here, never read from the module under test."""
    out = []
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    stream, tree = str(folder / "turn-1.jsonl"), str(SCRATCH / "tree")
    want = {"harness": "gemini", "container_id": TAKE, "model": MODEL, "mode": MODE, "run_tree": tree,
            "stream": stream, "sent": "hello", "vendor_session_id": "first-turn", "ordinal": 1}
    registered = list(mod.argv("hello", model=MODEL, mode=MODE, session_id=None, first=True))

    def journal(argv=None, raw=None, **over):
        path = folder / f"j-{len(list(folder.iterdir()))}.launch.json"
        doc = dict({"schema": 1, "harness": "gemini", "container_id": TAKE,
                    "argv": registered if argv is None else argv, "cwd": tree, "stream": stream,
                    "started_at": 1.0}, **over)
        path.write_bytes(raw if raw is not None else json.dumps(doc).encode())
        return str(path)

    unobserved = {"value": None, "source": "unobserved"}

    def mode(value):
        return {"value": value, "source": "submitted-argv"}

    link = folder / "link.launch.json"
    os.symlink(journal(), link)
    flags_at = [i for i in range(len(registered) - 1) if registered[i:i + 2] == ["--approval-mode", "yolo"]]
    if len(flags_at) != 1:
        out.append(f"{p}: the registered argv does not carry the pinned flags once: {registered}")
        return out
    k = flags_at[0]
    if k + 2 != len(registered):          # the window's last position is a case of its own (the boundary mutant)
        out.append(f"{p}: the registered argv no longer ends with the mode flags: {registered}")
    cases = [
        ("no journal", str(folder / "absent.launch.json"), unobserved),
        ("a link", str(link), unobserved),
        ("bytes that are not JSON", journal(raw=b"{not json"), unobserved),
        ("bytes that are not UTF-8", journal(raw=b"\xff\xfe"), unobserved),
        ("a JSON list", journal(raw=b"[]"), unobserved),
        ("an argv that is not a list", journal(argv="gemini -p hello"), unobserved),
        ("the registered launch", journal(), mode("yolo")),
        ("no mode flags", journal(argv=registered[:k] + registered[k + 2:]), mode("no-mode-flags-submitted")),
        ("the flags twice", journal(argv=registered + ["--approval-mode", "yolo"]), mode("contradictory-mode-flags")),
        ("an extra --yolo", journal(argv=registered + ["--yolo"]), mode("contradictory-mode-flags")),
        ("an extra -y", journal(argv=registered + ["-y"]), mode("contradictory-mode-flags")),
        ("another approval mode", journal(argv=registered[:k] + ["--approval-mode", "default"] + registered[k + 2:]),
         mode("contradictory-mode-flags")),
        ("the flags last, another prompt (off the registered argv)",
         journal(argv=[("goodbye" if a == "hello" else a) for a in registered]),
         mode("launch-differs-from-registered-invocation")),
        ("another working folder", journal(cwd=str(SCRATCH / "elsewhere")),
         mode("launch-differs-from-registered-invocation")),
    ]
    for why, path, expect in cases:
        got = mod.submitted_mode(path, dict(want))
        if got != expect:
            out.append(f"{p}: {why}: {got}, not {expect}")
    got = mod.submitted_mode(journal(), dict(want, mode="PENDING"))
    if got["source"] != "submitted-argv" or got["value"] == "PENDING":
        out.append(f"{p}: an unpinned mode read back as {got}")
    got = mod.submitted_mode(journal(argv=registered[:k] + registered[k + 2:]), dict(want, mode="PENDING"))
    if got != mode("no-mode-flags-submitted"):          # an unpinned mode has no window: nothing is "found" anywhere
        out.append(f"{p}: an unpinned mode with no flags submitted read as {got}")
    # A mode whose flags are no approval flag (none is pinned today): its window alone, with no approval flag beside
    # it, is still not one clean submission; so the two conditions are read apart, whatever the table holds later.
    saved = mod.MODE_FLAGS
    try:
        mod.MODE_FLAGS = dict(saved, other=("--other-mode",))
        got = mod.submitted_mode(journal(argv=registered[:k] + ["--other-mode"]), dict(want, mode="other"))
    finally:
        mod.MODE_FLAGS = saved
    if got != mode("contradictory-mode-flags"):
        out.append(f"{p}: a pinned window with no approval flag read as {got}")
    return out


def _adapter_in(mod, runtime, folder):
    return mod.GeminiAdapter(runtime=runtime, take_id=TAKE, run_tree=str(SCRATCH / "tree"), login_file=login_file(),
                             model=MODEL, pin={"permission_mode": MODE, "version": VERSION},
                             stream_path_for=lambda n: str(folder / f"turn-{n}.jsonl"), counters_for=Counters(),
                             clock=Clock())


@guarded("A11-identity", GA_API + ("turn_identity",))
def a11_identity(mod, p):
    """Live harness 3b (integration A4 sweep survivors): where each pin field came from, spelled here. The model: the
    init's (stream-init), else the result's one stats model (stream-stats), else unobserved; the version: version-exec;
    the mode: submitted_mode's entry, passed through as given."""
    out = []
    mode = {"value": None, "source": "unobserved"}
    for read, want in (({"init_model": "m-init", "served_models": ["m-stats"]}, {"value": "m-init", "source": "stream-init"}),
                       ({"init_model": None, "served_models": ["m-stats"]}, {"value": "m-stats", "source": "stream-stats"}),
                       ({"init_model": None, "served_models": []}, {"value": None, "source": "unobserved"}),
                       ({"init_model": None, "served_models": ["a", "b"]}, {"value": None, "source": "unobserved"})):
        got = mod.turn_identity(read, version="9.9.9", mode=mode)
        if got != {"model": want, "permission_mode": mode, "version": {"value": "9.9.9", "source": "version-exec"}}:
            out.append(f"{p}: {read} gave {got}")
    a, _ = take(mod, [fixture("turn1-tools.jsonl")])
    r = a.turn("one", first=True, budget_s=60)
    # The box's run_turn writes the turn's journal (0b6f60f9; the integration lane), so a real turn's mode is the
    # submitted argv's; the pass-through of any given entry is bound by the turn_identity loop above.
    if r.identity != {"model": {"value": MODEL, "source": "stream-init"},
                      "permission_mode": {"value": MODE, "source": "submitted-argv"},
                      "version": {"value": VERSION, "source": "version-exec"}}:
        out.append(f"{p}: turn 1's identity is {r.identity}")
    return out


@guarded("A12-executed", GA_API + ("ExecutedStreamRefused",))
def a12_executed(mod, p):
    """Live harness 3a: an exec that ran is kept before its stream is read; a reader refusal is ExecutedStreamRefused
    and a defect is a plain ExecutedTurnRefused, each carrying the kept record with its refusal "<type>: <words>"."""
    out = []
    keys = {"n", "exit_code", "timed_out", "started_at", "ended_at", "stream_path", "counters", "refused"}
    a, _ = take(mod, [fixture("unknown-event.jsonl")])
    try:
        a.turn("one", first=True, budget_s=60)
        out.append(f"{p}: a stream off the tables was not refused")
    except mod.ExecutedStreamRefused as e:
        cause = e.__cause__
        rec = a.executed_turns[-1] if a.executed_turns else None
        if len(a.executed_turns) != 1 or e.executed != rec or set(rec) != keys or rec["n"] != 1:
            out.append(f"{p}: the kept exec record is {a.executed_turns}")
        elif rec["refused"] != f"{type(cause).__name__}: {cause}" or not rec["refused"].startswith(
                type(cause).__name__ + ": "):
            out.append(f"{p}: the reader refusal is recorded as {rec['refused']!r}")
    a, _ = take(mod, [fixture("turn1-tools.jsonl")])
    a.turn("one", first=True, budget_s=60)
    if len(a.executed_turns) != 1 or set(a.executed_turns[0]) != keys or a.executed_turns[0]["refused"] is not None:
        out.append(f"{p}: a clean turn's kept exec record is {a.executed_turns}")
    a, _ = take(mod, [fixture("turn1-tools.jsonl")])

    def defect(got, n, first):
        raise RuntimeError("a stand-in defect")
    a._read_turn = defect
    try:
        a.turn("one", first=True, budget_s=60)
        out.append(f"{p}: a defect after the exec was not refused")
    except mod.StreamError:
        out.append(f"{p}: a defect after the exec was read as a stream refusal")
    except mod.aa.ExecutedTurnRefused as e:
        rec = a.executed_turns[-1] if a.executed_turns else {}
        if e.executed != rec or rec.get("refused") != "RuntimeError: a stand-in defect" or set(rec) != keys:
            out.append(f"{p}: the defect is recorded as {rec}")
    return out


def box_view(home: Path):
    """A faithful stand-in for TakeDriver.config_view over a scratch config folder: operator_list one level as
    (name, kind), a link listed as one (never followed), None for a folder that is absent; operator_read bytes or None."""
    def lister(rel):
        d = home / rel
        if not d.is_dir():
            return None
        return [(e.name, "link" if e.is_symlink() else "dir" if e.is_dir() else "file") for e in d.iterdir()]

    def reader(rel):
        f = home / rel
        return f.read_bytes() if f.is_file() and not f.is_symlink() else None
    return lister, reader


@guarded("A13-native", GA_API)
def a13_native(mod, p):
    """Live harness 3c: the native session file is the one under GEMINI_CLI_HOME named by turn 1's session id."""
    out = []
    a, _ = take(mod, [fixture("turn1-tools.jsonl")])
    a.turn("one", first=True, budget_s=60)
    home = Path(tempfile.mkdtemp(dir=SCRATCH))
    chats = home / ".gemini" / "tmp" / "project-1" / "chats"
    chats.mkdir(parents=True)
    sid = json.loads(fixture("turn1-tools.jsonl").splitlines()[0])["session_id"]
    want = chats / f"session-2026-10-14T05-00-{sid[:8]}.jsonl"
    want.write_text('{"this": "take"}\n')
    if a.native_session_path(str(home)) != str(want):
        out.append(f"{p}: the native session located is not {want.name}")
    # Drive-wiring review MAJOR 1's road (athena sweep, 14 Oct: native_session_rel's return deleted or None survived):
    # the same file through the box's listing, as the path relative to GEMINI_CLI_HOME, read back as this take's.
    lister, reader = box_view(home)
    rel = a.native_session_rel(lister)
    if rel != f".gemini/tmp/project-1/chats/{want.name}":
        out.append(f"{p}: the native session located through the box's listing is {rel!r}")
    elif reader(rel) != want.read_bytes():
        out.append(f"{p}: the located native session does not read as this take's")
    return out


@guarded("A14-journal", GA_API)
def a14_journal(mod, p):
    """The turn reads its mode from the journal beside its stream (<stream>.launch.json), against the registered
    invocation: model, mode, run tree, stream, line, the resumed session (turn 1's "first-turn") and the ordinal."""
    out = []
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    box = FakeRuntime([fixture("turn1-tools.jsonl"), fixture("turn2-resume.jsonl")])
    a = _adapter_in(mod, box, folder)
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    # The journal beside each stream is the box's own: run_take.run_turn writes it before the exec and refuses one
    # already there (0b6f60f9; the integration lane), so the check no longer plants it.
    for n, line in enumerate(("one", "two"), 1):
        r = a.turn(line, first=n == 1, budget_s=60)
        if r.identity["permission_mode"] != {"value": MODE, "source": "submitted-argv"}:
            out.append(f"{p}: turn {n}'s mode from its journal is {r.identity['permission_mode']}")
    # Batch-8 review finding 5: a first turn whose stream has no init leaves session_id unset, so the expectation's
    # "first-turn" fallback is what launch_facts reads; the journal still gives the pinned mode.
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    a = _adapter_in(mod, FakeRuntime([fixture("no-init.jsonl")]), folder)
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    r = a.turn("one", first=True, budget_s=60)
    if a.session_id is not None or r.identity["permission_mode"] != {"value": MODE, "source": "submitted-argv"}:
        out.append(f"{p}: a no-init first turn's mode from its journal is {r.identity['permission_mode']}")
    return out


# Lane vendor-b17 round 2 (glitch-26's ruling B17-5, 19 Oct 2026): arm G's OD57 read shapes, pinned by their bytes so
# the generated sweep kills every mutant of them; what they admit and refuse is tests/test_scan_record.py's.
READ_SHAPES_SHA256 = "bc38013820d967cde1b3972c1e6b59250befc12e019cf518273b6e79777ab849"   # B24-2 (grep_search; box/od57_shapes)


@guarded("A15-read-shapes", ("READ_SHAPES",))
def a15_read_shapes(mod, p):
    """The module's READ_SHAPES, as JSON with sorted keys, hash to the pinned bytes."""
    got = hashlib.sha256(json.dumps(mod.READ_SHAPES, sort_keys=True).encode()).hexdigest()
    return [] if got == READ_SHAPES_SHA256 else [f"{p}: READ_SHAPES is not the pinned records ({got[:12]})"]


# ------------------------------------------------------------------------------------------------ the tests
class TestTheShapes(unittest.TestCase):
    def test_s1_an_unknown_event_is_refused(self):
        self.assertEqual(s1_event(tg), [])

    def test_s2_a_key_off_its_entry_is_refused(self):
        self.assertEqual(s2_key(tg), [])

    def test_s3_a_word_off_its_table_is_refused(self):
        self.assertEqual(s3_words(tg), [])

    def test_s4_the_stats_are_d8s_counts(self):
        self.assertEqual(s4_stats(tg), [])

    def test_s5_a_tool_off_its_table_is_refused(self):
        self.assertEqual(s5_tools(tg), [])

    def test_p1_the_view_vocabulary(self):
        self.assertEqual(p1_view(tg), [])

    def test_s6_the_harness_error_words(self):
        self.assertEqual(s6_error_text(tg), [])

    def test_s7_undeclared_keys_on_an_open_input_tool(self):
        self.assertEqual(s7_open_input(tg), [])


class TestTheAdapter(unittest.TestCase):
    def test_a1_the_stream_read(self):
        self.assertEqual(a1_stream(ga), [])

    def test_a2_an_error_is_never_the_agents_and_the_agents_text_never_an_error(self):
        self.assertEqual(a2_error(ga), [])

    def test_a3_agent_output_clause_by_clause(self):
        self.assertEqual(a3_output(ga), [])

    def test_a4_the_stats_as_recorded(self):
        self.assertEqual(a4_stats(ga), [])

    def test_a5_the_model_checked_every_turn(self):
        self.assertEqual(a5_model(ga), [])

    def test_a6_the_call_argv(self):
        self.assertEqual(a6_argv(ga), [])

    def test_a7_the_resumed_session(self):
        self.assertEqual(a7_session(ga), [])

    def test_a8_a_turn_on_the_fake_runtime(self):
        self.assertEqual(a8_turn(ga), [])

    def test_a9_the_shapes_source_is_recorded(self):
        # lane vendor-settle stage V: the RECORDED w-g21 and w-g24 copies carry their labels (R-recorded reads them)
        self.assertEqual(ga.SHAPES_SOURCE, "recorded")
        self.assertEqual(a9_source(ga), [])

    def test_a10_the_mode_is_read_from_the_launch_journal(self):
        self.assertEqual(a10_mode(ga), [])

    def test_a11_the_identity_sources(self):
        self.assertEqual(a11_identity(ga), [])

    def test_a12_an_executed_turn_is_kept_before_its_refusal(self):
        self.assertEqual(a12_executed(ga), [])

    def test_a13_the_native_session_is_located_by_turn_ones_id(self):
        self.assertEqual(a13_native(ga), [])

    def test_a14_the_turn_reads_its_mode_from_its_own_journal(self):
        self.assertEqual(a14_journal(ga), [])

    def test_a15_each_turn_hands_run_turn_its_config_folder_and_number(self):
        """B11 (lane vendor-b11 round 3, R-CF): the adapter's config_folder record and each turn's number reach
        run_take.run_turn, which runs check_config_folder before the exec (the spy setUpModule installs records it)."""
        record = object()
        a = ga.GeminiAdapter(runtime=FakeRuntime([fixture("turn1-tools.jsonl"), fixture("turn2-resume.jsonl")]),
                             take_id=TAKE, run_tree=str(SCRATCH / "tree"), login_file=login_file(), model=MODEL,
                             pin={"permission_mode": MODE, "version": VERSION},
                             stream_path_for=lambda n: str(Path(tempfile.mkdtemp(dir=SCRATCH)) / f"turn-{n}.jsonl"),
                             counters_for=Counters(), clock=Clock(), config_folder=record)
        a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
        CONFIG_CHECKS.clear()
        a.turn("one", first=True, budget_s=60)
        a.turn("two", first=False, budget_s=60)
        self.assertEqual([(c["folder"] is record, c["harness"], c["run_tree"], c["turn"]) for c in CONFIG_CHECKS],
                         [(True, "gemini", str(SCRATCH / "tree"), 1), (True, "gemini", str(SCRATCH / "tree"), 2)],
                         "R-CF.adapter: the turns did not hand run_turn the take's config folder and their numbers")

    def test_a15_the_read_shapes_are_the_pinned_records(self):
        self.assertEqual(a15_read_shapes(ga), [])

    def test_a_recorded_label_needs_its_walk_and_version(self):
        for rest in ("", " at walk w-1.", " at walk w-1, gemini-cli 0.63.", " at walk w-1, codex-cli 0.63.0.",
                     " at walk w-1, gemini-cli 0.63.0. extra"):
            problems, recorded = label_problems({"x.jsonl": ("RECORDED", rest)}, ["x.jsonl"])
            self.assertTrue(problems, rest)
            self.assertEqual(recorded, [], rest)
        problems, recorded = label_problems({"x.jsonl": ("RECORDED", " at walk w-1, gemini-cli 0.63.0.")}, ["x.jsonl"])
        self.assertEqual((problems, recorded), ([], ["x.jsonl"]))

    def test_the_adapter_is_named_for_run_takes_harness(self):
        self.assertEqual(getattr(getattr(ga, "GeminiAdapter", None), "name", None), rt.GEMINI)


class WitnessNotPerformed(AssertionError):
    pass


def witness_module(target, edits: tuple) -> types.ModuleType:
    """`target`'s file with `edits` applied, compiled in memory as its own module (never written to disk)."""
    with open(target.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    name = Path(target.__file__).stem + "_w11b_witness"
    mod = types.ModuleType(name)
    mod.__file__ = target.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, target.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


def _w(target, check, prefix, *edits):
    return (target, tuple(edits), check, prefix)


WITNESSES = {
    # ---- transcript_gemini.py: the record check, guard by guard and clause by clause
    "unknown-event-accepted": _w("tg", s1_event, "S1-event", (
        "    if t not in EVENT_KEYS:\n        raise ShapeError(f\"unknown event type: {t!r}\")\n"
        "    _keys(f\"event {t}\", rec, *EVENT_KEYS[t])\n",
        "    if t in EVENT_KEYS:\n        _keys(f\"event {t}\", rec, *EVENT_KEYS[t])\n")),
    "non-object-accepted": _w("tg", s1_event, "S1-event", (
        "    if not isinstance(rec, dict):\n        raise ShapeError(\"a record that is not an object\")\n", "")),
    "missing-key-accepted": _w("tg", s2_key, "S2-key", (
        "    missing = [k for k in required if k not in rec]\n", "    missing = []\n")),
    "unknown-key-accepted": _w("tg", s2_key, "S2-key", (
        "    unknown = sorted(set(rec) - set(allowed))\n", "    unknown = []\n")),
    "error-object-keys-unchecked": _w("tg", s2_key, "S2-key", (
        "    _keys(f\"{what}.error\", err, ERROR_OBJECT_KEYS, ERROR_OBJECT_KEYS)\n", "    pass\n")),
    "error-object-unchecked": _w("tg", s2_key, "S2-key", (
        "    if \"error\" in rec:\n        _error_object(t, rec[\"error\"])\n", "")),
    "error-object-presence-dropped": _w("tg", s2_key, "S2-key", ("    if \"error\" in rec:\n", "    if True:\n")),
    "role-unchecked": _w("tg", s3_words, "S3-words", (
        "    if t == MESSAGE and rec[\"role\"] not in ROLES:", "    if False:")),
    "value-types-unchecked": _w("tg", s3_words, "S3-words", ("    _types(f\"event {t}\", rec, VALUE_TYPES)\n", "")),
    "delta-type-loosened": _w("tg", s3_words, "S3-words", ("\"delta\": bool,", "\"delta\": int,")),
    "error-object-types-unchecked": _w("tg", s3_words, "S3-words", (
        "    _types(f\"{what}.error\", err, ERROR_OBJECT_TYPES)\n", "")),
    "tool-id-empty-unchecked": _w("tg", s3_words, "S3-words", (
        "    if t in (TOOL_USE, TOOL_RESULT) and not rec[\"tool_id\"]:", "    if False:")),
    "tool-id-tool-use-only": _w("tg", s3_words, "S3-words", (
        "    if t in (TOOL_USE, TOOL_RESULT) and not rec[\"tool_id\"]:", "    if t == TOOL_USE and not rec[\"tool_id\"]:")),
    "status-unchecked": _w("tg", s3_words, "S3-words", (
        "    if t in (TOOL_RESULT, RESULT) and rec[\"status\"] not in STATUSES:", "    if False:")),
    "status-result-only": _w("tg", s3_words, "S3-words", (
        "    if t in (TOOL_RESULT, RESULT) and rec[\"status\"] not in STATUSES:",
        "    if t == RESULT and rec[\"status\"] not in STATUSES:")),
    "status-tool-result-only": _w("tg", s3_words, "S3-words", (
        "    if t in (TOOL_RESULT, RESULT) and rec[\"status\"] not in STATUSES:",
        "    if t == TOOL_RESULT and rec[\"status\"] not in STATUSES:")),
    "severity-unchecked": _w("tg", s3_words, "S3-words", (
        "    if \"severity\" in rec and rec[\"severity\"] not in SEVERITIES:", "    if False:")),
    "severity-presence-dropped": _w("tg", s3_words, "S3-words", (
        "    if \"severity\" in rec and rec[\"severity\"] not in SEVERITIES:",
        "    if rec.get(\"type\") == ERROR and rec[\"severity\"] not in SEVERITIES:")),
    "stats-presence-dropped": _w("tg", s4_stats, "S4-stats", (
        "    if \"stats\" in rec:\n        check_stats", "    if rec.get(\"type\") == RESULT:\n        check_stats")),
    "stats-unchecked": _w("tg", s4_stats, "S4-stats", (
        "    if \"stats\" in rec:\n        check_stats(rec[\"stats\"])\n", "    if \"stats\" in rec:\n        pass\n")),
    "success-without-stats": _w("tg", s4_stats, "S4-stats", (
        "    elif t == RESULT and rec[\"status\"] == SUCCESS:\n", "    elif False:\n")),
    "success-without-stats-status-dropped": _w("tg", s4_stats, "S4-stats", (
        "    elif t == RESULT and rec[\"status\"] == SUCCESS:\n", "    elif t == RESULT:\n")),
    "stats-keys-unchecked": _w("tg", s4_stats, "S4-stats", (
        "    _keys(\"result.stats\", stats, STATS_KEYS, STATS_KEYS)\n", "")),
    "stats-counts-unchecked": _w("tg", s4_stats, "S4-stats", (
        "    bad = [k for k in STATS_COUNTS if not count(stats[k])]\n", "    bad = []\n")),
    "count-bool-clause-dropped": _w("tg", s4_stats, "S4-stats", (
        "    return isinstance(v, int) and not isinstance(v, bool) and v >= 0\n",
        "    return isinstance(v, int) and v >= 0\n")),
    "count-negative-clause-dropped": _w("tg", s4_stats, "S4-stats", (
        "    return isinstance(v, int) and not isinstance(v, bool) and v >= 0\n",
        "    return isinstance(v, int) and not isinstance(v, bool)\n")),
    "count-int-clause-dropped": _w("tg", s4_stats, "S4-stats", (
        "    return isinstance(v, int) and not isinstance(v, bool) and v >= 0\n",
        "    return isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0\n")),
    "models-type-unchecked": _w("tg", s4_stats, "S4-stats", (
        "    if not isinstance(models, dict):\n        raise ShapeError(\"result.stats.models is not an object\")\n", "")),
    "model-entry-type-unchecked": _w("tg", s4_stats, "S4-stats", (
        "        if not isinstance(entry, dict):\n            raise ShapeError(f\"result.stats.models[{model!r}] is not an "
        "object\")\n", "")),
    "model-entry-keys-unchecked": _w("tg", s4_stats, "S4-stats", (
        "        _keys(f\"result.stats.models[{model!r}]\", entry, MODEL_STATS_KEYS, MODEL_STATS_KEYS)\n", "")),
    "model-entry-counts-unchecked": _w("tg", s4_stats, "S4-stats", (
        "        bad = [k for k in MODEL_STATS_KEYS if not count(entry[k])]\n", "        bad = []\n")),
    "event-keys-unchecked": _w("tg", s2_key, "S2-key", ("    _keys(f\"event {t}\", rec, *EVENT_KEYS[t])\n", "")),
    "not-json-untyped": _w("tg", s1_event, "S1-event", (
        "    except ValueError:\n        raise ShapeError(\"a line that is not JSON\") from None\n",
        "    except ValueError:\n        raise\n")),
    "decode-unchecked": _w("tg", s1_event, "S1-event", ("    check_record(rec)\n    return rec\n", "    return rec\n")),
    "tool-refusal-untyped": _w("tg", s5_tools, "S5-tools", (
        "    try:\n        return tv.map_tool(GEMINI_TOOLS, rec[\"tool_name\"], _declared(rec))\n"
        "    except tv.ViewError as e:\n        raise ShapeError(f\"tool_use: {e}\") from None\n",
        "    return tv.map_tool(GEMINI_TOOLS, rec[\"tool_name\"], _declared(rec))\n")),
    "error-event-words-dropped": _w("tg", s6_error_text, "S6-error-text", (
        "        return rec[\"message\"]\n", "        return None\n")),
    "failed-result-words-dropped": _w("tg", s6_error_text, "S6-error-text", (
        "        return rec[\"error\"][\"message\"]\n", "        return None\n")),
    "failed-result-error-presence-dropped": _w("tg", s6_error_text, "S6-error-text", (
        "    if t == RESULT and \"error\" in rec:\n", "    if t == RESULT:\n")),
    "harness-text-dropped": _w("tg", p1_view, "P1-view", (
        "    return [tv.RawItem(t, tv.HARNESS, text=tv._joined({k: v for k, v in rec.items() if k != \"type\"}))]",
        "    return [tv.RawItem(t, tv.HARNESS, text=None)]")),
    "tool-table-unchecked": _w("tg", s5_tools, "S5-tools", (
        "    if t == TOOL_USE:\n        tool_kind(rec)\n", "")),
    # round 18 B12 (glitch-26): re-anchored on the table's last entry, the table now read from the pinned package
    "web-tool-admitted": _w("tg", s5_tools, "S5-tools", (
        "    \"invoke_agent\": (tv.DELEGATE, {}, (\"agent_name\", \"prompt\", \"wait_for_previous\")),\n}",
        "    \"invoke_agent\": (tv.DELEGATE, {}, (\"agent_name\", \"prompt\", \"wait_for_previous\")),\n"
        "    \"web_fetch\": (tv.OTHER, {}, (\"prompt\",)),\n}")),
    "edit-as-write": _w("tg", p1_view, "P1-view", ("    \"replace\": (tv.EDIT,", "    \"replace\": (tv.WRITE,")),
    "user-as-agent-text": _w("tg", p1_view, "P1-view", (
        "            kind = tv.OPERATOR if rec[\"role\"] == USER else tv.AGENT_TEXT\n",
        "            kind = tv.AGENT_TEXT\n")),
    "tool-result-text-dropped": _w("tg", p1_view, "P1-view", (
        "            text = out if isinstance(out, str) else tv._joined(rec.get(\"error\"))\n",
        "            text = out if isinstance(out, str) else None\n")),
    # ---- gemini_adapter.py: the stream read
    "two-inits-accepted": _w("ga", a1_stream, "A1-stream", (
        "            if inits > 1:\n                raise StreamError(\"one call's stream holds two init records\")\n", "")),
    "two-results-accepted": _w("ga", a1_stream, "A1-stream", (
        "            if results > 1:\n                raise StreamError(\"one call's stream holds two result records\")\n",
        "")),
    "delta-run-not-ended": _w("ga", a1_stream, "A1-stream", (
        "        if not said:\n            joining = False\n", "")),
    "shape-refusal-dropped": _w("ga", a1_stream, "A1-stream", (
        "        try:\n            t = tg.check_record(rec)\n        except tg.ShapeError as e:\n"
        "            raise StreamError(f\"the stream holds a record off the pre-registered tables: {e}\") from None\n",
        "        t = rec.get(\"type\")\n")),
    "cut-line-uncounted": _w("ga", a1_stream, "A1-stream", ("            bad = 1\n", "            pass\n")),
    "midstream-junk-accepted": _w("ga", a1_stream, "A1-stream", (
        "            if n != len(lines) or n == 1:\n                raise StreamError(f\"line {n}",
        "            if False:\n                raise StreamError(f\"line {n}")),
    "lone-junk-accepted": _w("ga", a1_stream, "A1-stream", (
        "            if n != len(lines) or n == 1:\n", "            if n != len(lines):\n")),
    "midstream-clause-dropped": _w("ga", a1_stream, "A1-stream", (
        "            if n != len(lines) or n == 1:\n", "            if n == 1:\n")),
    "split-on-every-line-break": _w("ga", a1_stream, "A1-stream", ("text.split(\"\\n\")", "text.splitlines()")),
    "delta-clause-dropped": _w("ga", a1_stream, "A1-stream", (
        "            if rec.get(\"delta\") is True and joining:\n", "            if joining:\n")),
    "joining-clause-dropped": _w("ga", a1_stream, "A1-stream", (
        "            if rec.get(\"delta\") is True and joining:\n", "            if rec.get(\"delta\") is True and pieces:\n")),
    "joining-forced": _w("ga", a1_stream, "A1-stream", (
        "            joining = rec.get(\"delta\") is True\n", "            joining = True\n")),
    "result-stats-presence-dropped": _w("ga", a4_stats, "A4-stats", (
        "            if \"stats\" in rec:\n", "            if True:\n")),
    "agent-text-as-error": _w("ga", a2_error, "A2-error", (
        "        if t == tg.ERROR:\n            api.append(", "        if t == tg.ERROR or said:\n            api.append(")),
    "success-result-as-error": _w("ga", a2_error, "A2-error", (
        "            if status == tg.FAILED:\n", "            if True:\n")),
    "failed-result-type-dropped": _w("ga", a2_error, "A2-error", (
        "\"type\": rec[\"error\"][\"type\"] if \"error\" in rec else None,", "\"type\": t,")),
    "error-as-agent-output": _w("ga", a2_error, "A2-error", (
        "        if t == tg.ERROR:\n            api.append(", "        if t == tg.ERROR:\n            output = True\n"
                                                             "            api.append(")),
    "user-message-as-output": _w("ga", a3_output, "A3-output", (
        "        said = t == tg.MESSAGE and rec[\"role\"] == tg.ASSISTANT\n", "        said = t == tg.MESSAGE\n")),
    "blank-message-as-output": _w("ga", a3_output, "A3-output", (
        "            if rec[\"content\"].strip():\n                output = True\n",
        "            if True:\n                output = True\n")),
    "tool-use-not-output": _w("ga", a3_output, "A3-output", (
        "            tools.append(rec[\"tool_id\"])\n            output = True\n", "            tools.append(rec[\"tool_id\"])\n")),
    "stats-dropped": _w("ga", a4_stats, "A4-stats", ("\"status\": status, \"stats\": stats,",
                                                     "\"status\": status, \"stats\": None,")),
    "init-model-unchecked": _w("ga", a5_model, "A5-model", ("            if init_model != model:\n",
                                                            "            if False:\n")),
    "no-model-record-accepted": _w("ga", a5_model, "A5-model", (
        "    if stats is not None and not served and init_model is None:\n", "    if False:\n")),
    "no-model-record-stats-clause-dropped": _w("ga", a5_model, "A5-model", (
        "    if stats is not None and not served and init_model is None:\n",
        "    if not served and init_model is None:\n")),
    "no-model-record-served-clause-dropped": _w("ga", a5_model, "A5-model", (
        "    if stats is not None and not served and init_model is None:\n",
        "    if stats is not None and init_model is None:\n")),
    "no-model-record-init-clause-dropped": _w("ga", a5_model, "A5-model", (
        "    if stats is not None and not served and init_model is None:\n", "    if stats is not None and not served:\n")),
    "read-model-type-dropped": _w("ga", a5_model, "A5-model", (
        "    if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):\n        raise StreamError(\"the row's "
        "model is off the model-id shape\")\n    init_model",
        "    if not _MODEL_ID.fullmatch(model):\n        raise StreamError(\"the row's model is off the model-id "
        "shape\")\n    init_model")),
    "read-model-shape-dropped": _w("ga", a5_model, "A5-model", (
        "    if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):\n        raise StreamError(\"the row's "
        "model is off the model-id shape\")\n    init_model",
        "    if not isinstance(model, str) or not model:\n        raise StreamError(\"the row's model is off the "
        "model-id shape\")\n    init_model")),
    "stats-models-unchecked": _w("ga", a5_model, "A5-model", (
        "                other = [m for m in served if m != model]\n", "                other = []\n")),
    "stats-models-first-key-only": _w("ga", a5_model, "A5-model", (
        "                other = [m for m in served if m != model]\n",
        "                other = [m for m in served[:1] if m != model]\n")),
    "served-models-dropped": _w("ga", a5_model, "A5-model", (
        "                served = list(stats[tg.STATS_MODELS])\n", "                served = []\n")),
    "init-from-argv": _w("ga", a5_model, "A5-model", (
        "end_reason=end_reason(got[\"exit_code\"], got[\"timed_out\"], read), init=None,",
        "end_reason=end_reason(got[\"exit_code\"], got[\"timed_out\"], read), init={\"model\": self.model, "
        "\"permission_mode\": self.mode, \"version\": \"0.63.0\"},")),
    # ---- the argv
    "model-first-only": _w("ga", a6_argv, "A6-argv", (
        "    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, MODEL_FLAG, model, *MODE_FLAGS[mode]]\n",
        "    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, *MODE_FLAGS[mode]]\n    if first:\n"
        "        out[5:5] = [MODEL_FLAG, model]\n")),
    "mode-first-only": _w("ga", a6_argv, "A6-argv", (
        "    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, MODEL_FLAG, model, *MODE_FLAGS[mode]]\n",
        "    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, MODEL_FLAG, model] + (list(MODE_FLAGS[mode]) if first "
        "else [])\n")),
    "resume-first": _w("ga", a6_argv, "A6-argv", ("    if not first:\n        if not isinstance(session_id",
                                                  "    if True:\n        if not isinstance(session_id")),
    "resume-never": _w("ga", a6_argv, "A6-argv", ("        out += [RESUME_FLAG, session_id]\n", "        pass\n")),
    "dash-line-accepted": _w("ga", a6_argv, "A6-argv", (
        "    if line.startswith(\"-\"):\n        raise StreamError(\"a line that starts", "    if False:\n"
                                                                                       "        raise StreamError(\"a line that starts")),
    "argv-line-type-dropped": _w("ga", a6_argv, "A6-argv", (
        "    if not isinstance(line, str) or not line:\n", "    if not line:\n")),
    "argv-line-empty-dropped": _w("ga", a6_argv, "A6-argv", (
        "    if not isinstance(line, str) or not line:\n", "    if not isinstance(line, str):\n")),
    "argv-model-type-dropped": _w("ga", a6_argv, "A6-argv", (
        "    if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):\n        raise StreamError(\"the turn's",
        "    if not _MODEL_ID.fullmatch(model):\n        raise StreamError(\"the turn's")),
    "argv-model-shape-dropped": _w("ga", a6_argv, "A6-argv", (
        "    if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):\n        raise StreamError(\"the turn's",
        "    if not isinstance(model, str) or not model:\n        raise StreamError(\"the turn's")),
    "model-id-loosened": _w("ga", a6_argv, "A6-argv", (
        "_MODEL_ID = re.compile(r\"[A-Za-z0-9][A-Za-z0-9._-]{0,99}\")", "_MODEL_ID = re.compile(r\"[^ ]+\")")),
    "adapter-model-unchecked": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):\n            raise StreamError(\"the "
        "row's model is off the model-id shape\")\n        self.runtime", "        self.runtime")),
    "argv-session-type-dropped": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):\n"
        "            raise StreamError(\"a later turn",
        "        if not _SESSION_ID.fullmatch(session_id):\n            raise StreamError(\"a later turn")),
    "argv-session-shape-dropped": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):\n"
        "            raise StreamError(\"a later turn",
        "        if not isinstance(session_id, str):\n            raise StreamError(\"a later turn")),
    "argv-mode-unchecked": _w("ga", a6_argv, "A6-argv", (
        "    if mode not in MODE_FLAGS:\n        raise StreamError(f\"no flags pre-registered for mode {mode!r}\")\n"
        "    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, MODEL_FLAG, model, *MODE_FLAGS[mode]]\n",
        "    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, MODEL_FLAG, model, *MODE_FLAGS.get(mode, ())]\n")),
    "callables-unchecked": _w("ga", a6_argv, "A6-argv", (
        "            if not callable(fn):\n                raise TypeError(f\"{what} must be callable\")\n",
        "            pass\n")),
    "mode-type-clause-dropped": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(mode, str) or mode not in MODE_FLAGS:\n", "        if mode not in MODE_FLAGS:\n")),
    "mode-table-clause-dropped": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(mode, str) or mode not in MODE_FLAGS:\n", "        if not isinstance(mode, str):\n")),
    # ---- the session
    "other-session-resumed": _w("ga", a7_session, "A7-session", (
        "        elif read[\"session_id\"] is not None and read[\"session_id\"] != self.session_id:\n",
        "        elif False:\n")),
    "session-none-clause-dropped": _w("ga", a7_session, "A7-session", (
        "        elif read[\"session_id\"] is not None and read[\"session_id\"] != self.session_id:\n",
        "        elif read[\"session_id\"] != self.session_id:\n")),
    "session-differs-clause-dropped": _w("ga", a7_session, "A7-session", (
        "        elif read[\"session_id\"] is not None and read[\"session_id\"] != self.session_id:\n",
        "        elif read[\"session_id\"] is not None:\n")),
    "session-kept-from-a-later-turn": _w("ga", a7_session, "A7-session", (
        "        if first:\n            self.session_id = read[\"session_id\"]\n        elif",
        "        if first or read[\"session_id\"] is None:\n            self.session_id = read[\"session_id\"]\n"
        "        elif")),
    "init-session-shape-dropped": _w("ga", a7_session, "A7-session", (
        "            if not _SESSION_ID.fullmatch(session_id):\n                raise StreamError(\"the init carries",
        "            if False:\n                raise StreamError(\"the init carries")),
    "session-selectors-admitted": _w("ga", a7_session, "A7-session", (
        "_SESSION_ID = re.compile(r\"(?!(?i:latest)$)(?![0-9]+$)[A-Za-z0-9]", "_SESSION_ID = re.compile(r\"[A-Za-z0-9]")),
    "session-latest-admitted": _w("ga", a7_session, "A7-session", (
        "_SESSION_ID = re.compile(r\"(?!(?i:latest)$)(?![0-9]+$)[A-Za-z0-9]", "_SESSION_ID = re.compile(r\"(?![0-9]+$)[A-Za-z0-9]")),
    "session-latest-case-sensitive": _w("ga", a7_session, "A7-session", ("(?!(?i:latest)$)", "(?!latest$)")),
    "session-index-admitted": _w("ga", a7_session, "A7-session", (
        "_SESSION_ID = re.compile(r\"(?!(?i:latest)$)(?![0-9]+$)[A-Za-z0-9]", "_SESSION_ID = re.compile(r\"(?!(?i:latest)$)[A-Za-z0-9]")),
    # ---- the turn's end and exit
    "exit53-as-end-turn": _w("ga", a8_turn, "A8-turn", (
        "    if exit_code == 0 and read[\"status\"] == tg.SUCCESS:\n", "    if read[\"status\"] == tg.SUCCESS:\n")),
    "failed-result-as-end-turn": _w("ga", a8_turn, "A8-turn", (
        "    if exit_code == 0 and read[\"status\"] == tg.SUCCESS:\n", "    if exit_code == 0:\n")),
    "timeout-as-error": _w("ga", a8_turn, "A8-turn", (
        "    if timed_out:\n        return aa.END_TIMED_OUT\n", "")),
    "unknown-exit-accepted": _w("ga", a8_turn, "A8-turn", (
        "    if isinstance(exit_code, bool) or exit_code not in EXIT_MEANINGS:\n",
        "    if isinstance(exit_code, bool):\n")),
    "bool-exit-accepted": _w("ga", a8_turn, "A8-turn", (
        "    if isinstance(exit_code, bool) or exit_code not in EXIT_MEANINGS:\n",
        "    if exit_code not in EXIT_MEANINGS:\n")),
    "timed-out-exit-refused": _w("ga", a8_turn, "A8-turn", ("    if timed_out:\n        return None\n", "")),
    "exit-meaning-skipped": _w("ga", a8_turn, "A8-turn", (
        "        meaning = exit_meaning(got[\"exit_code\"], got[\"timed_out\"])\n", "        meaning = None\n")),
    "turn-limit-mislabelled": _w("ga", a8_turn, "A8-turn", ("53: TURN_LIMIT}", "53: \"success\"}")),
    "version-searched": _w("ga", a8_turn, "A8-turn", ("VERSION_FORM.fullmatch(", "VERSION_FORM.search(")),
    "version-matched": _w("ga", a8_turn, "A8-turn", ("VERSION_FORM.fullmatch(", "VERSION_FORM.match(")),
    "version-exit-ignored": _w("ga", a8_turn, "A8-turn", ("if c.returncode == 0 else None", "if True else None")),
    # lane vendor-settle stage V (design section 5, review finding 10): the new anchor, red on A9's two-words check
    "shapes-off-word": _w("ga", a9_source, "A9-source", ("SHAPES_SOURCE = \"recorded\"\n",
                                                         "SHAPES_SOURCE = \"observed\"\n")),
}
TARGETS = {"tg": lambda: tg, "ga": lambda: ga}
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    def kill(self, name):
        target, edits, check, prefix = WITNESSES[name]
        mod = TARGETS[target]()
        self.assertEqual(check(mod), [], f"{name}: the bound check is not green on {Path(mod.__file__).name}")
        got = check(witness_module(mod, edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_the_witnesses_are_named_and_each_anchor_occurs_once(self):
        self.assertEqual(len(WITNESSES), 114)
        for name, (target, edits, _, _) in WITNESSES.items():
            path = Path(TARGETS[target]().__file__)
            self.assertTrue(path.is_file(), f"{name}: {path.name} does not exist")
            src = path.read_text(encoding="utf-8")
            for old, _ in edits:
                self.assertEqual(src.count(old), 1, f"{name}: its anchor occurs {src.count(old)} times")


def _witness_test(name):
    def test(self):
        self.kill(name)
    test.__name__ = "test_witness_" + name.replace("-", "_")
    return test


for _name in WITNESSES:
    setattr(TestWitnesses, "test_witness_" + _name.replace("-", "_"), _witness_test(_name))


# ------------------------------------------------------------------------------------------------ generated mutants
# glitch-2f's added requirement (12 Oct 2026, from w11a's review: hand-picked witnesses all red, 143 of 452 generated
# mutants alive). `--generated-mutants [--shard i/n]` builds every mutant of the kinds below over gemini_adapter.py and
# transcript_gemini.py, in memory only, and runs every bound check against it (a transcript_gemini mutant is also
# loaded under gemini_adapter). A mutant is killed when any check prints a line (an ERROR line counts: on the files as
# they stand every check is silent, test_generated_mutants_baseline). Every survivor must be in EQUIVALENT with a
# reason from EQUIVALENT_CATEGORIES; an entry that no longer names a generated mutant, or whose mutant is killed, is
# stale and fails. One listed rule skips mutants rather than allow-listing them one by one: MESSAGE_TEXT_RULE, a string
# literal inside a `raise` statement, which only the refusal's message reads (no code or test reads those words).
MUTANT_KINDS = ("stmt-delete", "if-true", "if-false", "bool-drop", "bool-swap", "not-drop", "cmp-negate",
                "assign-empty", "return-none", "str-change", "int-change", "call-true",
                # review round 1's operators (W11B-R1 fold): boundary swaps, `is True` to truthy, fullmatch to match
                # and to search, a regex loosened, one element of a literal tuple or list dropped, one entry of a
                # dict literal dropped, `.strip()` dropped, list/sorted/set unwrapped
                "boundary", "is-true-truthy", "fullmatch-match", "fullmatch-search", "regex-loosen", "elt-drop",
                "dict-drop", "strip-drop", "unwrap")
BOUNDARY = {ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Lt: ast.LtE, ast.LtE: ast.Lt}
MESSAGE_TEXT_RULE = "a string literal inside a raise statement is the refusal's message text, read by no logic"
EQUIVALENT_CATEGORIES = {
    "import-plumbing": "the sys.path insert or the __future__ import: the module imports the same either way under "
                       "the test's own sys.path, and Python 3.13 evaluates no annotation here",
    "falsy-alike": "the mutant swaps one falsy value for another where the only reader tests truthiness",
    "typed-bool": "VALUE_TYPES makes `delta` a bool before this line reads it, so `is True` and truthiness agree",
    "message-order": "sorted() only orders the names a refusal's message lists; no condition reads the order",
    "sequence-alike": "run_take's argv check takes any sequence of strings, so a tuple and its list() agree",
    "identical-mutant": "the mutant behaves as the line does: a None written as None, or a method's last "
                        "`return None` deleted (it falls off and returns None)",
    "message-label": "a label string passed only into a refusal's message text, never read by a condition (the "
                     "MESSAGE_TEXT_RULE's words, one step removed from the raise)",
    "platform-default": "getattr's default for os.O_NOFOLLOW, read only on a platform without that flag; the box and "
                        "the study's hosts are POSIX, where the flag itself is used",
    "slice-past-end": "one more window start past the end yields a slice shorter than the flags, which never equals "
                      "them, so no window is found that the line's own range would miss",
}
# What each category's line must hold (checked against the named line of the file, so a reason cannot drift from it).
EQUIVALENT_TOKENS = {"import-plumbing": ("_HERE", "__future__"), "falsy-alike": ("joining = False",),
                     "identical-mutant": ("None",), "message-label": None, "typed-bool": ("is True",),
                     "message-order": ("sorted(",), "sequence-alike": ("list(VERSION_ARGV)",),
                     "platform-default": ("O_NOFOLLOW",), "slice-past-end": ("len(argv) - len(flags) + 1",)}
CMP_NEGATE = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Lt: ast.GtE,
              ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
# {mutant key: (category, why, a token its source line holds)}; the key is printed by the sweep for each survivor.
EQUIVALENT = {
    'gemini_adapter: int-change L266 5feceb66 0': ('platform-default', "submitted_mode's journal open: O_NOFOLLOW exists on the box's POSIX hosts", 'O_NOFOLLOW'),
    'gemini_adapter: int-change L278 6b86b273 1': ('slice-past-end', "submitted_mode's window range: an extra start past the end finds nothing", 'len(argv) - len(flags) + 1'),
    'gemini_adapter: stmt-delete L65 a6284e6d from __future__ import annotations': ('import-plumbing', "the module's __future__ import", '__future__'),
    'gemini_adapter: assign-empty L72 e8a221d3 _HERE = os.path.dirname(os.path.abspath(__file__))': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'gemini_adapter: cmp-negate#0 L73 7c3b80fa _HERE not in sys.path': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'gemini_adapter: if-false L73 9b7db2cf if _HERE not in sys.path: sys.path.insert(0, _HERE)': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'gemini_adapter: if-true L73 9b7db2cf if _HERE not in sys.path: sys.path.insert(0, _HERE)': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'gemini_adapter: stmt-delete L73 9b7db2cf if _HERE not in sys.path: sys.path.insert(0, _HERE)': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'gemini_adapter: int-change L74 5feceb66 0': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'gemini_adapter: stmt-delete L74 7baa5234 sys.path.insert(0, _HERE)': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'gemini_adapter: assign-empty L138 f8f68722 joining = False': ('falsy-alike', 'joining is read only as `and joining`; None and False read alike', 'joining = False'),
    'gemini_adapter: assign-empty L155 f8f68722 joining = False': ('falsy-alike', 'joining is read only as `and joining`; None and False read alike', 'joining = False'),
    "gemini_adapter: is-true-truthy L172 9d1f7fda rec.get('delta') is True": ('typed-bool', 'delta is a bool by VALUE_TYPES', 'is True'),
    "gemini_adapter: is-true-truthy L168 9d1f7fda rec.get('delta') is True": ('typed-bool', 'delta is a bool by VALUE_TYPES', 'is True'),
    'gemini_adapter: return-none L220 9f730a1a return None': ('identical-mutant', 'the mutant writes the same None the line already writes', 'None'),
    'gemini_adapter: unwrap L222 790ab58d sorted(EXIT_MEANINGS)': ('message-order', "the sorted names go only into a refusal's message", 'sorted('),
    "gemini_adapter: str-change L320 3a445bda 'stream_path_for'": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", 'stream_path_for'),
    "gemini_adapter: str-change L320 5a98356f 'counters_for'": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", 'counters_for'),
    "gemini_adapter: str-change L320 8c8bd4c2 'clock'": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", 'clock'),
    'gemini_adapter: assign-empty L329 65756fc1 self._version = None': ('identical-mutant', 'the mutant writes the same None the line already writes', 'None'),
    'gemini_adapter: assign-empty L330 7f1bf958 self.session_id = None': ('identical-mutant', 'the mutant writes the same None the line already writes', 'None'),
    'gemini_adapter: unwrap L337 95ba8661 list(VERSION_ARGV)': ('sequence-alike', 'agent_exec_argv takes the tuple as it takes the list', 'list(VERSION_ARGV)'),
    'gemini_adapter: return-none L409 9f730a1a return None': ('identical-mutant', 'the mutant writes the same None the line already writes', 'None'),
    'gemini_adapter: stmt-delete L409 9f730a1a return None': ('identical-mutant', "a method's last `return None` deleted still returns None", 'None'),
    'transcript_gemini: stmt-delete L48 a6284e6d from __future__ import annotations': ('import-plumbing', "the module's __future__ import", '__future__'),
    'transcript_gemini: assign-empty L54 e8a221d3 _HERE = os.path.dirname(os.path.abspath(__file__))': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'transcript_gemini: cmp-negate#0 L55 7c3b80fa _HERE not in sys.path': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'transcript_gemini: if-false L55 9b7db2cf if _HERE not in sys.path: sys.path.insert(0, _HERE)': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'transcript_gemini: if-true L55 9b7db2cf if _HERE not in sys.path: sys.path.insert(0, _HERE)': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'transcript_gemini: stmt-delete L55 9b7db2cf if _HERE not in sys.path: sys.path.insert(0, _HERE)': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'transcript_gemini: int-change L56 5feceb66 0': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'transcript_gemini: stmt-delete L56 7baa5234 sys.path.insert(0, _HERE)': ('import-plumbing', "the module's sys.path plumbing", '_HERE'),
    'transcript_gemini: unwrap L146 90ac4953 sorted(set(rec) - set(allowed))': ('message-order', "the sorted names go only into a refusal's message", 'sorted('),
    "transcript_gemini: str-change L157 b2437d2e '.error'": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", '.error'),
    "transcript_gemini: str-change L158 b2437d2e '.error'": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", '.error'),
    "transcript_gemini: str-change L164 934526e8 'result.stats'": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", 'result.stats'),
    "transcript_gemini: str-change L174 10c989f3 'result.stats.models['": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", 'result.stats.models['),
    "transcript_gemini: str-change L174 cb8092dd ']'": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", ']'),
    "transcript_gemini: str-change L200 e8f80b17 'event '": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", 'event '),
    "transcript_gemini: str-change L201 e8f80b17 'event '": ('message-label', "a label passed only into a refusal's message text (no condition reads it)", 'event '),
    'transcript_gemini: return-none L241 9f730a1a return None': ('identical-mutant', 'the mutant writes the same None the line already writes', 'None'),
    'transcript_gemini: stmt-delete L241 9f730a1a return None': ('identical-mutant', "a method's last `return None` deleted still returns None", 'None'),
}
MUTANT_FILES = (("tg", "transcript_gemini.py"), ("ga", "gemini_adapter.py"))


def _in_raise(tree) -> set:
    inside = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            inside.update(id(n) for n in ast.walk(node))
    return inside


def _docstrings(tree) -> set:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.add(id(first))
                out.add(id(first.value))
    return out


def mutant_sites(tree) -> tuple:
    """([(walk index, kind, operand index)], message-text strings skipped), in ast.walk order of `tree`."""
    raised, docs = _in_raise(tree), _docstrings(tree)
    out, skipped = [], 0
    for w, node in enumerate(ast.walk(tree)):
        if id(node) in docs:
            continue
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            out.append((w, "stmt-delete", None))
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            out += [(w, "if-true", None), (w, "if-false", None)]
        if isinstance(node, ast.BoolOp):
            out += [(w, "bool-drop", i) for i in range(len(node.values))] + [(w, "bool-swap", None)]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            out.append((w, "not-drop", None))
        if isinstance(node, ast.Compare):
            out += [(w, "cmp-negate", i) for i, op in enumerate(node.ops) if type(op) in CMP_NEGATE]
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)) and node.value is not None:
            out.append((w, "assign-empty", None))
        if isinstance(node, ast.Return) and node.value is not None:
            out.append((w, "return-none", None))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
            if id(node) in raised:
                skipped += 1
            else:
                out.append((w, "str-change", None))
        if isinstance(node, ast.Constant) and type(node.value) is int:
            out.append((w, "int-change", None))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in (
                "isinstance", "callable", "all", "any"):
            out.append((w, "call-true", None))
        if isinstance(node, ast.Compare):
            out += [(w, "boundary", i) for i, op in enumerate(node.ops) if type(op) in BOUNDARY]
            if len(node.ops) == 1 and isinstance(node.ops[0], ast.Is) and isinstance(node.comparators[0], ast.Constant) \
                    and node.comparators[0].value is True:
                out.append((w, "is-true-truthy", None))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "fullmatch":
                out += [(w, "fullmatch-match", None), (w, "fullmatch-search", None)]
            if node.func.attr == "compile" and node.args and isinstance(node.args[0], ast.Constant):
                out.append((w, "regex-loosen", None))
            if node.func.attr == "strip" and not node.args:
                out.append((w, "strip-drop", None))
        if isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) > 1 and id(node) not in raised \
                and all(isinstance(e, ast.Constant) for e in node.elts):
            out += [(w, "elt-drop", i) for i in range(len(node.elts))]
        if isinstance(node, ast.Dict) and len(node.keys) > 1 and None not in node.keys and id(node) not in raised:
            out += [(w, "dict-drop", i) for i in range(len(node.keys))]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("list", "sorted", "set") \
                and len(node.args) == 1:
            out.append((w, "unwrap", None))
    return out, skipped


def _mutate(node, kind, i):
    if kind == "stmt-delete":
        return ast.Pass()
    if kind in ("if-true", "if-false"):
        node.test = ast.Constant(kind == "if-true")
        return node
    if kind == "bool-drop":
        vals = node.values[:i] + node.values[i + 1:]
        return vals[0] if len(vals) == 1 else ast.BoolOp(op=node.op, values=vals)
    if kind == "bool-swap":
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        return node
    if kind == "not-drop":
        return node.operand
    if kind == "cmp-negate":
        node.ops[i] = CMP_NEGATE[type(node.ops[i])]()
        return node
    if kind in ("assign-empty", "return-none"):
        node.value = ast.Constant(None)
        return node
    if kind == "str-change":
        node.value = "__mutant__"
        return node
    if kind == "int-change":
        node.value = node.value + 1
        return node
    if kind == "boundary":
        node.ops[i] = BOUNDARY[type(node.ops[i])]()
        return node
    if kind == "is-true-truthy":
        return node.left
    if kind in ("fullmatch-match", "fullmatch-search"):
        node.func.attr = kind.split("-")[1]
        return node
    if kind == "regex-loosen":
        node.args[0] = ast.Constant(r"(.+)")
        return node
    if kind == "elt-drop":
        node.elts = node.elts[:i] + node.elts[i + 1:]
        return node
    if kind == "dict-drop":
        node.keys, node.values = node.keys[:i] + node.keys[i + 1:], node.values[:i] + node.values[i + 1:]
        return node
    if kind == "strip-drop":
        return node.func.value
    if kind == "unwrap":
        return node.args[0]
    return ast.Constant(True)                        # call-true


class _Replace(ast.NodeTransformer):
    def __init__(self, target, kind, i):
        self.target, self.kind, self.i = target, kind, i

    def visit(self, node):
        node = self.generic_visit(node)
        return _mutate(node, self.kind, self.i) if node is self.target else node


def mutant_key(src: str, node, kind: str, i, seen: dict) -> str:
    text = ast.unparse(node)
    digest = hashlib.sha256(text.encode()).hexdigest()[:8]
    base = f"{kind}{'' if i is None else f'#{i}'} L{node.lineno} {digest} {' '.join(text.split())[:70]}"
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else f"{base} @{seen[base]}"


def generated_mutants() -> tuple:
    """([(key, target, walk index, kind, operand index)] sorted by file and position, message-text strings skipped).
    Keys carry the line number, so an edit above a site renames its key: a stale EQUIVALENT entry then fails."""
    out, skipped = [], 0
    for target, fname in MUTANT_FILES:
        src = (HERE / fname).read_text(encoding="utf-8")
        tree = ast.parse(src)
        walk = list(ast.walk(tree))
        sites, sk = mutant_sites(tree)
        skipped += sk
        seen: dict = {}
        for w, kind, i in sites:
            out.append((f"{fname[:-3]}: {mutant_key(src, walk[w], kind, i, seen)}", target, w, kind, i))
    return out, skipped


def _build(tree, name: str, path: Path, inject=None) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    code = compile(ast.fix_missing_locations(tree), str(path) + " (generated mutant)", "exec")
    saved = {}
    for k, v in (inject or {}).items():
        saved[k] = sys.modules.get(k)
        sys.modules[k] = v
    try:
        exec(code, mod.__dict__)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


@guarded("A-stderr", GA_API)
def a_stderr(mod, p):
    """glitch-b5's ruling on R15-2 (16 Oct 2026): each turn's stderr is kept on the adapter (stderr_seen), so the
    driver can name what a read-only root broke."""
    a, box = take(mod, [fixture("turn1-tools.jsonl")])
    real = box.run
    box.run = lambda *x, **k: (lambda c: rt.Completed(c.returncode, c.stdout, "EROFS-SENTINEL"))(real(*x, **k))
    a.turn("one", first=True, budget_s=60)
    out = [] if getattr(a, "stderr_seen", None) == ["EROFS-SENTINEL"] else [f"{p}: the turn's stderr is not kept"]
    quiet, _ = take(mod, [fixture("turn1-tools.jsonl")])
    quiet.turn("one", first=True, budget_s=60)
    return out + ([] if getattr(quiet, "stderr_seen", None) == [""] else [f"{p}: an empty stderr is not kept as \"\""])


TG_CHECKS = (s1_event, s2_key, s3_words, s4_stats, s5_tools, s6_error_text, s7_open_input, p1_view)
GA_CHECKS = (a_stderr, a1_stream, a2_error, a3_output, a4_stats, a5_model, a6_argv, a7_session, a8_turn, a9_source, a10_mode,
             a11_identity, a12_executed, a13_native, a14_journal, a15_read_shapes)


def all_checks(tgm, gam) -> list:
    out = []
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        for c in TG_CHECKS:
            out += c(tgm)
        for c in GA_CHECKS:
            out += c(gam)
    if getattr(getattr(gam, "GeminiAdapter", None), "name", None) != rt.GEMINI:
        out.append("NAME: the adapter's name is not run_take.GEMINI")
    return out


def run_mutant(target: str, w: int, kind: str, i) -> list:
    """The checks' lines against one mutant (["IMPORT ..."] when it does not even load: killed)."""
    fname = dict(MUTANT_FILES)[target]
    tree = ast.parse((HERE / fname).read_text(encoding="utf-8"))
    node = list(ast.walk(tree))[w]
    try:
        new = _Replace(node, kind, i).visit(tree)
        if target == "tg":
            tgm = _build(new, "transcript_gemini", HERE / fname)
            gam = _build(ast.parse((HERE / "gemini_adapter.py").read_text(encoding="utf-8")), "gemini_adapter",
                         HERE / "gemini_adapter.py", {"transcript_gemini": tgm})
        else:
            tgm, gam = tg, _build(new, "gemini_adapter", HERE / fname, {"transcript_gemini": tg})
    except Exception as e:  # noqa: BLE001
        return [f"IMPORT {type(e).__name__}: {str(e)[:120]}"]
    return all_checks(tgm, gam)


def baseline_lines() -> list:
    """Lane t104-mutation-baseline: all_checks over the UNMUTATED files, built both ways run_mutant builds a mutant
    (transcript_gemini with gemini_adapter over it, and gemini_adapter over the real transcript_gemini)."""
    src = {f: (HERE / f).read_text(encoding="utf-8") for f in ("transcript_gemini.py", "gemini_adapter.py")}
    tgm = _build(ast.parse(src["transcript_gemini.py"]), "transcript_gemini", HERE / "transcript_gemini.py")
    gam = _build(ast.parse(src["gemini_adapter.py"]), "gemini_adapter", HERE / "gemini_adapter.py",
                 {"transcript_gemini": tgm})
    alone = _build(ast.parse(src["gemini_adapter.py"]), "gemini_adapter", HERE / "gemini_adapter.py",
                   {"transcript_gemini": tg})
    return all_checks(tgm, gam) + all_checks(tg, alone)


def mutation_sweep(shard: int = 0, of: int = 1) -> dict:
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_clean("test_gemini_adapter generated mutants", baseline_lines)
    mutants, skipped = generated_mutants()
    keys = [m[0] for m in mutants]
    mine = [m for n, m in enumerate(mutants) if n % of == shard]
    survived, killed, equivalent, stale = [], 0, 0, []
    for key, target, w, kind, i in mine:
        got = run_mutant(target, w, kind, i)
        if key in EQUIVALENT:
            if got:
                stale.append(f"{key}: listed EQUIVALENT but killed by {got[0][:96]}")
            else:
                equivalent += 1
        elif got:
            killed += 1
        else:
            survived.append(key)
    stale += [f"{k}: listed EQUIVALENT but no such generated mutant" for k in EQUIVALENT if k not in keys]
    stale += [f"{k}: {why}" for k, why in equivalent_problems()]
    return {"generated": len(mutants), "shard": f"{shard + 1}/{of}", "ran": len(mine), "killed": killed,
            "equivalent": equivalent, "survived": survived, "stale": stale, "message_text_skipped": skipped}


def equivalent_problems() -> list:
    """(key, why) for every EQUIVALENT entry whose reason does not hold on the file as it stands: its category is off
    the list, its sentence is blank, or the line its key names does not hold the category's token."""
    out = []
    files = {fname[:-3]: (HERE / fname).read_text(encoding="utf-8").split("\n") for _, fname in MUTANT_FILES}
    for key, v in EQUIVALENT.items():
        if not (isinstance(v, tuple) and len(v) == 3 and v[0] in EQUIVALENT_CATEGORIES and isinstance(v[1], str)
                and v[1].strip() and isinstance(v[2], str) and v[2]):
            out.append((key, "its reason is not (a category of EQUIVALENT_CATEGORIES, a sentence, a token)"))
            continue
        m = re.match(r"^(\w+): \S+ L(\d+) ", key)
        lines_ = files.get(m.group(1)) if m else None
        if lines_ is None or not 0 < int(m.group(2)) <= len(lines_):
            out.append((key, "its key names no line of the two files"))
            continue
        line = lines_[int(m.group(2)) - 1]
        allowed = EQUIVALENT_TOKENS[v[0]]
        if (allowed is not None and v[2] not in allowed) or v[2] not in line:
            out.append((key, f"line {m.group(2)} does not hold the {v[0]} token {v[2]!r}"))
        if v[0] == "message-label" and not re.search(f"'{re.escape(v[2])}'( @[0-9]+)?$", key):
            out.append((key, "a message label's token is not the mutated literal"))
    return out


class TestGeneratedMutants(unittest.TestCase):
    """Cheap parts of the sweep, in the normal suite; the sweep itself is `--generated-mutants` (athena)."""

    def setUp(self):
        for _, fname in MUTANT_FILES:
            self.assertTrue((HERE / fname).is_file(), f"{fname} does not exist: nothing to mutate")

    def test_generated_mutants_baseline(self):
        self.assertEqual(all_checks(tg, ga), [])

    def test_every_kind_is_generated(self):
        mutants, _ = generated_mutants()
        self.assertEqual({m[3] for m in mutants}, set(MUTANT_KINDS))

    def test_the_equivalent_list_is_not_stale(self):
        keys = {m[0] for m in generated_mutants()[0]}
        for key in EQUIVALENT:
            self.assertIn(key, keys, f"stale EQUIVALENT entry: {key}")
        self.assertEqual(equivalent_problems(), [])

    def test_a_drifted_or_malformed_entry_is_refused(self):
        key = next(iter(EQUIVALENT))
        line_no = int(re.match(r"^\w+: \S+ L(\d+) ", key).group(1))
        moved = key.replace(f" L{line_no} ", f" L{line_no + 7} ", 1)
        for bad in ({moved: EQUIVALENT[key]}, {key: ("import-plumbing", "x")}, {key: ("unlisted", "x", "_HERE")},
                    {key: ("import-plumbing", " ", "_HERE")}, {key: ("falsy-alike", "x", "_HERE")}):
            with mock.patch.dict(EQUIVALENT, bad, clear=True):
                self.assertTrue(equivalent_problems(), f"{bad} passed")

    def test_one_mutant_of_each_file_is_killed(self):
        mutants, _ = generated_mutants()
        for target in ("tg", "ga"):
            key, t, w, kind, i = next(m for m in mutants if m[1] == target and m[3] == "if-false"
                                      and ("t not in EVENT_KEYS" in m[0] or "if timed_out" in m[0]))
            self.assertTrue(run_mutant(t, w, kind, i), f"{key} survived")


# ---- R-recorded (lane vendor-settle stage V, freeze leg i; glitch-f1's settle rulings, Thu 22 Oct 2026) ------------
def r_recorded_problems() -> list:
    """Each RECORDED stream of gemini-streams is a byte copy of rehearsals/<walk>/turn-<k>.jsonl, and read_stream and
    end_reason read it as plain json does: the init's model and session id, the assistant text (consecutive delta
    chunks joined, runs joined by newlines), output, tool ids, the result's status, stats and models (none for w-g24's
    timed-out turn), the result count, nothing undecoded, and the ledger's end reason."""
    out = []
    recorded = sorted(f for f, (kind, _rest) in labels().items() if kind == "RECORDED")
    if recorded != ["w-g21-turn-1.jsonl", "w-g21-turn-2.jsonl", "w-g24-turn-1.jsonl"]:
        out.append(f"the RECORDED files are {recorded}")
    for name in recorded:
        walk, k = re.fullmatch(r"(w-g[0-9]+)-turn-([0-9]+)\.jsonl", name).groups()
        src = HERE / "rehearsals" / walk / f"turn-{k}.jsonl"
        if (FIXTURES / name).read_bytes() != src.read_bytes():
            out.append(f"{name} is not byte for byte {src.relative_to(HERE)}")
            continue
        turn = json.loads((HERE / "rehearsals" / walk / "driver-ledger.json").read_text(encoding="utf-8"))["turns"][
            int(k) - 1]
        recs = [json.loads(x) for x in fixture(name).split("\n") if x.strip()]
        init = [r for r in recs if r["type"] == "init"]
        result = [r for r in recs if r["type"] == "result"]
        runs, open_run = [], False
        for r in recs:
            if r["type"] == "message" and r["role"] == "assistant":
                if r.get("delta") is True and open_run:
                    runs[-1] += r["content"]
                else:
                    runs.append(r["content"])
                open_run = r.get("delta") is True
            else:
                open_run = False
        tools = [r["tool_id"] for r in recs if r["type"] == "tool_use"]
        want = {"init_model": init[0]["model"], "session_id": init[0]["session_id"], "agent_text": "\n".join(runs),
                "agent_output": bool(tools) or any(x.strip() for x in runs),
                "status": result[0]["status"] if result else None, "stats": result[0]["stats"] if result else None,
                "served_models": list(result[0]["stats"]["models"]) if result else [], "results": len(result),
                "tool_ids": tools, "undecoded": 0}
        got = ga.read_stream(fixture(name), model=init[0]["model"])
        out += [f"{name}: read_stream's {key} is {str(got.get(key))[:60]!r}, the stream's {str(v)[:60]!r}"
                for key, v in want.items() if got.get(key) != v]
        if ga.end_reason(turn["exit"], turn["end"] == "timed-out", got) != turn["end"]:
            out.append(f"{name}: end_reason is not the ledger's {turn['end']!r}")
    return out


class RRecorded(unittest.TestCase):
    def test_r_recorded_the_copies_read_as_plain_json(self):
        self.assertEqual(r_recorded_problems(), [])


if __name__ == "__main__":
    if "--generated-mutants" in sys.argv:
        shard, of = 0, 1
        if "--shard" in sys.argv:
            spec = sys.argv[sys.argv.index("--shard") + 1]
            a, _, b = spec.partition("/")
            shard, of = int(a) - 1, int(b)
            if not 0 <= shard < of:
                raise SystemExit(f"--shard {spec}: i must be 1..n")
        setUpModule()
        try:
            got = mutation_sweep(shard, of)
        finally:
            tearDownModule()
        for key in got["survived"]:
            print(f"SURVIVED {key}")
        for line in got["stale"]:
            print(f"STALE {line}")
        print(f"test_gemini_adapter generated mutants (shard {got['shard']}): generated {got['generated']}, ran "
              f"{got['ran']}, killed {got['killed']}, equivalent {got['equivalent']}, survived {len(got['survived'])}, "
              f"stale {len(got['stale'])}; message-text strings skipped by rule: {got['message_text_skipped']}",
              flush=True)
        raise SystemExit(0 if not got["survived"] and not got["stale"] else 1)
    if "--witnesses" in sys.argv:
        sys.argv.remove("--witnesses")
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestWitnesses)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        red = sum(1 for x in WITNESS_LOG if ": red by " in x)
        print(f"test_gemini_adapter witnesses: {red}/{len(WITNESSES)} red; registry {len(WITNESSES)}", flush=True)
        raise SystemExit(0 if result.wasSuccessful() and red == len(WITNESSES) else 1)
    unittest.main(verbosity=2)
