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
             the record check and the parser; the table's view kinds are pinned.
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
  A9-source  SHAPES_SOURCE is "documented" while no fixture is labelled RECORDED, every fixture carries the brief's
             label, and the adapter reports it in its harness record and every turn record.

Fakes only: no model, vendor, network, container runtime, credential or holdout. setUpModule arms a process guard
that refuses every process start, clears this process's environment to a fixed few names, and fills run_take's
PENDING Gemini billing-route names with an empty tuple for the fake only; tearDownModule undoes all of it and restores
sys.path.
"""

from __future__ import annotations

import contextlib
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


def tearDownModule():
    _STACK.close()
    sys.path[:] = _SYS_PATH


# ------------------------------------------------------------------------------------------------ fixtures and fakes
def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def lines(name: str) -> list:
    return [ln for ln in fixture(name).splitlines() if ln.strip()]


def recs(name: str) -> list:
    return [json.loads(ln) for ln in lines(name)]


def jl(records) -> str:
    return "".join(json.dumps(r) + "\n" for r in records)


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
        self.now += 1.0
        return self.now


def login_file() -> str:
    path = SCRATCH / f"login-{len(list(SCRATCH.iterdir()))}"
    path.write_text(f"{LOGIN}={LOGIN_VALUE}\n")
    os.chmod(path, 0o600)
    return str(path)


def adapter(mod, runtime, *, mode=MODE, counters=None, pin=None):
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    return mod.GeminiAdapter(runtime=runtime, take_id=TAKE, run_tree=str(SCRATCH / "tree"), login_file=login_file(),
                             model=MODEL, pin={"permission_mode": mode, "version": VERSION} if pin is None else pin,
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
    bare = ev("result", status="success")
    out += _both_accept(mod, p, bare, "a result with no stats")
    return out


@guarded("S5-tools", TG_API)
def s5_tools(mod, p):
    out = []
    kinds = {name: entry[0] for name, entry in mod.GEMINI_TOOLS.items()}
    want = {"run_shell_command": tv.SHELL, "read_file": tv.READ, "write_file": tv.WRITE, "replace": tv.EDIT,
            "glob": tv.SEARCH, "search_file_content": tv.SEARCH, "list_directory": tv.OTHER, "write_todos": tv.OTHER}
    if kinds != want:
        out.append(f"{p}: the tool table's kinds are {kinds}")
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
             (ev("error", message=7), None))
    for rec, want in cases:
        got = mod.error_text(rec)
        if got != want:
            out.append(f"{p}: the error text of a {rec['type']} reads {got!r}, not {want!r}")
    return out


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
    got = [e.kind for e in view_events(mod, "error-result.jsonl")]
    if got != [h, tv.OPERATOR, h, h]:
        out.append(f"{p}: error-result reads as {got}")
    if "gemini" in tv.PARSERS:
        out.append(f"{p}: the parser was registered in transcript_view.PARSERS")
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
    bare = jl([ev("result", status="success")])
    got = accepted(lambda: mod.read_stream(bare, model=MODEL))
    if got:
        out.append(f"{p}: a result with no stats {got}")
    else:
        r = mod.read_stream(bare, model=MODEL)
        if (r["stats"], r["served_models"]) != (None, []):
            out.append(f"{p}: a result with no stats reads {r['stats']}, {r['served_models']}")
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
    for bad in ("", 5):
        got = refusal(lambda: mod.read_stream(fixture("no-init.jsonl"), model=bad), mod.StreamError)
        if got:
            out.append(f"{p}: a stream read against model {bad!r} {got}")
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
    for sid in (None, "a b; rm", 5):
        got = refusal(lambda: mod.argv("two", model=MODEL, mode=MODE, session_id=sid, first=False), mod.StreamError)
        if got:
            out.append(f"{p}: a later turn with session id {sid!r} {got}")
    for what, kw in (("an empty line", {"line": ""}), ("an empty model", {"model": ""}), ("a model that is a number", {"model": 5}),
                     ("an unknown mode", {"mode": "default"})):
        args = dict({"line": "one", "model": MODEL, "mode": MODE, "session_id": None, "first": True}, **kw)
        line = args.pop("line")
        got = refusal(lambda: mod.argv(line, **args), mod.StreamError)
        if got:
            out.append(f"{p}: an argv with {what} {got}")
    for what, kw, err in (("an empty model", {"model": ""}, mod.StreamError),
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
    for sid in ("a b", 5, ""):
        bad = jl([ev("init", session_id=sid, model=MODEL)])
        got = refusal(lambda: mod.read_stream(bad, model=MODEL), mod.StreamError)
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
    for printed, code in (("Gemini CLI 0.63.0\n", 0), ("0.63\n", 0), ("v0.63.0\n", 0), (f"{VERSION}\n", 1)):
        a, _ = take(mod, [], version_out=printed, version_code=code)
        got = refusal(a.version, rt.NotReady)
        if got:
            out.append(f"{p}: a version printed {printed!r} with exit {code} {got}")
    return out


@guarded("A9-source", GA_API)
def a9_source(mod, p):
    out = []
    marks = labels()
    files = sorted(f.name for f in FIXTURES.iterdir() if f.name != README.name)
    unlabelled = [f for f in files if f not in marks]
    if unlabelled:
        out.append(f"{p}: fixture(s) with no label: {unlabelled}")
    wrong = [f for f, (kind, rest) in marks.items() if kind == "SYNTHETIC" and kind + rest != SYNTHETIC_LABEL]
    if wrong:
        out.append(f"{p}: fixture(s) whose label is not the brief's words: {wrong}")
    recorded = [f for f, (kind, _) in marks.items() if kind == "RECORDED" and f in files]
    if mod.SHAPES_SOURCE not in mod.SHAPES_SOURCES or tuple(mod.SHAPES_SOURCES) != ("documented", "recorded"):
        out.append(f"{p}: SHAPES_SOURCE {mod.SHAPES_SOURCE!r} is off the two words")
    if mod.SHAPES_SOURCE == "recorded" and not recorded:
        out.append(f"{p}: SHAPES_SOURCE reads 'recorded' while no fixture is labelled RECORDED")
    a, _ = take(mod, [fixture("turn1-tools.jsonl")])
    if a.harness_record() != {"harness": "gemini", "shapes_source": mod.SHAPES_SOURCE}:
        out.append(f"{p}: the harness record is {a.harness_record()}")
    a.turn("one", first=True, budget_s=60)
    if [r["shapes_source"] for r in a.turn_records] != [mod.SHAPES_SOURCE]:
        out.append(f"{p}: the turn records do not carry the shapes' source")
    return out


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

    def test_a9_the_shapes_source_is_documented(self):
        self.assertEqual(a9_source(ga), [])

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
    "error-object-type-unchecked": _w("tg", s2_key, "S2-key", (
        "    if not isinstance(err, dict):\n        raise ShapeError(f\"{what}: its error is not an object\")\n", "")),
    "error-object-unchecked": _w("tg", s2_key, "S2-key", (
        "    if \"error\" in rec:\n        _error_object(t, rec[\"error\"])\n", "")),
    "error-object-presence-dropped": _w("tg", s2_key, "S2-key", ("    if \"error\" in rec:\n", "    if True:\n")),
    "role-unchecked": _w("tg", s3_words, "S3-words", (
        "    if t == MESSAGE and rec[\"role\"] not in ROLES:", "    if False:")),
    "content-unchecked": _w("tg", s3_words, "S3-words", (
        "    if t == MESSAGE and not isinstance(rec[\"content\"], str):", "    if False:")),
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
    "tool-id-type-dropped": _w("tg", s3_words, "S3-words", (
        "(not isinstance(rec[\"tool_id\"], str) or not rec[\"tool_id\"])", "(not rec[\"tool_id\"])")),
    "tool-id-empty-dropped": _w("tg", s3_words, "S3-words", (
        "(not isinstance(rec[\"tool_id\"], str) or not rec[\"tool_id\"])", "(not isinstance(rec[\"tool_id\"], str))")),
    "tool-id-tool-use-only": _w("tg", s3_words, "S3-words", (
        "    if t in (TOOL_USE, TOOL_RESULT) and (not isinstance", "    if t == TOOL_USE and (not isinstance")),
    "stats-unchecked": _w("tg", s4_stats, "S4-stats", (
        "    if \"stats\" in rec:\n        check_stats(rec[\"stats\"])\n", "")),
    "stats-presence-dropped": _w("tg", s4_stats, "S4-stats", (
        "    if \"stats\" in rec:\n        check_stats", "    if rec.get(\"type\") == RESULT:\n        check_stats")),
    "stats-type-unchecked": _w("tg", s4_stats, "S4-stats", (
        "    if not isinstance(stats, dict):\n        raise ShapeError(\"result.stats is not an object\")\n", "")),
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
        "    try:\n        return tv.map_tool(GEMINI_TOOLS, rec.get(\"tool_name\"), rec.get(\"parameters\"))\n"
        "    except tv.ViewError as e:\n        raise ShapeError(f\"tool_use: {e}\") from None\n",
        "    return tv.map_tool(GEMINI_TOOLS, rec.get(\"tool_name\"), rec.get(\"parameters\"))\n")),
    "error-event-words-dropped": _w("tg", s6_error_text, "S6-error-text", (
        "        words = rec.get(\"message\")\n", "        words = None\n")),
    "failed-result-words-dropped": _w("tg", s6_error_text, "S6-error-text", (
        "        words = (rec.get(\"error\") or {}).get(\"message\")\n", "        words = None\n")),
    "error-words-type-unchecked": _w("tg", s6_error_text, "S6-error-text", (
        "    return words if isinstance(words, str) else None\n", "    return words\n")),
    "harness-text-dropped": _w("tg", p1_view, "P1-view", (
        "    return [tv.RawItem(t, tv.HARNESS, text=tv._joined({k: v for k, v in rec.items() if k != \"type\"}))]",
        "    return [tv.RawItem(t, tv.HARNESS, text=None)]")),
    "tool-table-unchecked": _w("tg", s5_tools, "S5-tools", (
        "    if t == TOOL_USE:\n        tool_kind(rec)\n", "")),
    "web-tool-admitted": _w("tg", s5_tools, "S5-tools", (
        "    \"write_todos\": (tv.OTHER, {}, (\"todos\",)),\n}",
        "    \"write_todos\": (tv.OTHER, {}, (\"todos\",)),\n    \"web_fetch\": (tv.OTHER, {}, (\"prompt\",)),\n}")),
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
    "cut-line-uncounted": _w("ga", a1_stream, "A1-stream", ("            bad += 1\n", "            pass\n")),
    "delta-clause-dropped": _w("ga", a1_stream, "A1-stream", (
        "            if rec.get(\"delta\") is True and joining:\n", "            if joining:\n")),
    "joining-clause-dropped": _w("ga", a1_stream, "A1-stream", (
        "            if rec.get(\"delta\") is True and joining:\n", "            if rec.get(\"delta\") is True and pieces:\n")),
    "joining-always": _w("ga", a1_stream, "A1-stream", (
        "            joining = rec.get(\"delta\") is True\n", "            joining = True\n")),
    "failed-result-type-dropped": _w("ga", a2_error, "A2-error", (
        "api.append({\"status\": None, \"type\": err.get(\"type\"),", "api.append({\"status\": None, \"type\": t,")),
    "result-stats-presence-dropped": _w("ga", a4_stats, "A4-stats", (
        "            if \"stats\" in rec:\n", "            if True:\n")),
    "read-model-type-dropped": _w("ga", a5_model, "A5-model", (
        "    if not isinstance(model, str) or not model:\n        raise StreamError(\"the row's model must be a non-empty "
        "string\")\n    init_model",
        "    if not model:\n        raise StreamError(\"the row's model must be a non-empty string\")\n    init_model")),
    "read-model-empty-dropped": _w("ga", a5_model, "A5-model", (
        "    if not isinstance(model, str) or not model:\n        raise StreamError(\"the row's model must be a non-empty "
        "string\")\n    init_model",
        "    if not isinstance(model, str):\n        raise StreamError(\"the row's model must be a non-empty string\")\n"
        "    init_model")),
    "agent-text-as-error": _w("ga", a2_error, "A2-error", (
        "        if t == tg.ERROR:\n            api.append(", "        if t == tg.ERROR or said:\n            api.append(")),
    "success-result-as-error": _w("ga", a2_error, "A2-error", (
        "            if status == tg.FAILED:\n", "            if True:\n")),
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
    "argv-session-type-dropped": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):\n"
        "            raise StreamError(\"a later turn",
        "        if not _SESSION_ID.fullmatch(session_id):\n            raise StreamError(\"a later turn")),
    "argv-session-shape-dropped": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):\n"
        "            raise StreamError(\"a later turn",
        "        if not isinstance(session_id, str):\n            raise StreamError(\"a later turn")),
    "argv-input-type-dropped": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(v, str) or not v:\n            raise StreamError(f\"the turn's",
        "        if not v:\n            raise StreamError(f\"the turn's")),
    "argv-input-empty-dropped": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(v, str) or not v:\n            raise StreamError(f\"the turn's",
        "        if not isinstance(v, str):\n            raise StreamError(f\"the turn's")),
    "argv-mode-unchecked": _w("ga", a6_argv, "A6-argv", (
        "    if mode not in MODE_FLAGS:\n        raise StreamError(f\"no flags pre-registered for mode {mode!r}\")\n"
        "    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, MODEL_FLAG, model, *MODE_FLAGS[mode]]\n",
        "    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, MODEL_FLAG, model, *MODE_FLAGS.get(mode, ())]\n")),
    "adapter-model-unchecked": _w("ga", a6_argv, "A6-argv", (
        "        if not isinstance(model, str) or not model:\n            raise StreamError(\"the row's model must be a "
        "non-empty string\")\n        self.runtime", "        self.runtime")),
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
    "init-session-type-dropped": _w("ga", a7_session, "A7-session", (
        "            if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):\n"
        "                raise StreamError(\"the init carries",
        "            if not _SESSION_ID.fullmatch(session_id):\n                raise StreamError(\"the init carries")),
    "init-session-shape-dropped": _w("ga", a7_session, "A7-session", (
        "            if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):\n"
        "                raise StreamError(\"the init carries",
        "            if not isinstance(session_id, str):\n                raise StreamError(\"the init carries")),
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
    "version-exit-ignored": _w("ga", a8_turn, "A8-turn", ("if c.returncode == 0 else None", "if True else None")),
    "shapes-recorded": _w("ga", a9_source, "A9-source", ("SHAPES_SOURCE = \"documented\"\n",
                                                         "SHAPES_SOURCE = \"recorded\"\n")),
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
        self.assertEqual(len(WITNESSES), 98)
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


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        sys.argv.remove("--witnesses")
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestWitnesses)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        red = sum(1 for x in WITNESS_LOG if ": red by " in x)
        print(f"test_gemini_adapter witnesses: {red}/{len(WITNESSES)} red; registry {len(WITNESSES)}", flush=True)
        raise SystemExit(0 if result.wasSuccessful() and red == len(WITNESSES) else 1)
    unittest.main(verbosity=2)
