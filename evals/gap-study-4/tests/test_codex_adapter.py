#!/usr/bin/env python3
"""Lane w11a-codex-adapter (Gap Study round 4, arm O): the Codex CLI adapter and its stream parser, on synthetic
streams over a fake runtime.

    python3 -B -W ignore evals/gap-study-4/tests/test_codex_adapter.py               every test
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_adapter.py --witnesses   the witnesses only, one line each

Fixtures: tests/fixtures/codex-streams/, every file SYNTHETIC (its README labels each one): written from the event
types, item types and usage keys D8 section 1 names, plus the keys transcript_codex.py lists as "NOT in D8". No Codex
stream has been recorded (ruling Q-3: build on the documented shapes now; the freeze binds the recorded re-test).

What is tested, each guard with its own bound check and a whole-file witness of codex_adapter.py or
transcript_codex.py compiled in memory (the registry pattern of lane w6j):

  S1-event     an event type off the tables (item.updated) is refused by the record check and the parser; the
               tables hold D8's seven event types. Witness: unknown-event-accepted.
  S2-item      an item type off the tables (web_search) is refused, and so is an item.started carrying an item type
               that is not a running call; the tables hold D8's five item types. Witness: unknown-item-accepted.
  S3-key       a key off its entry (an agent_message carrying `phase`) is refused. Witness: unknown-key-accepted.
  P1-view      through transcript_view.events (the parser put in a COPY of PARSERS for the test only, never
               registered): the closed vocabulary: reasoning -> agent-reasoning, agent_message -> agent-text,
               command_execution -> shell call and result, file_change add -> write and update -> edit,
               mcp_tool_call -> other; a delete change is refused. Witnesses: reasoning-as-text, delete-as-write.
  A1-stream    read_stream: the agent's text, agent output (reasoning alone is not output), usage, tool ids, the
               thread id; a record off the tables refuses the turn on the adapter's road too.
  A2-error     the harness's error event and turn.failed are api_errors with the harness's own words; an agent
               message that says "429" is never one. Witness: agent-text-as-error.
  A3-usage     a usage key that is missing is refused, never 0; a failed turn has no usage (None).
               Witness: usage-zero.
  A4-argv      `-m <model>` on every exec; `resume <thread id>` after turn 1 only, the id read from turn 1's stream;
               a PENDING or unknown mode refuses the adapter; a line starting with "-" is refused; the login rides
               by name only. Witnesses: resume-first, model-first-only.
  A5-model     the init's model is the rollout's turn_context model (a served-other id reads as that id), and a
               rollout with no turn_context for the turn gives init None, never the requested model.
               Witness: model-defaulted.
  A6-turn      end reasons (end_turn, error on exit 1, error on exit 0 with turn.failed, timed-out), the counters'
               rise, and a later turn naming another thread refused. Witnesses: failed-as-end-turn,
               other-thread-resumed.
  A7-source    SHAPES_SOURCE is "documented" while no fixture is labelled RECORDED, every fixture carries a label,
               and the adapter reports it in its harness record and every turn record. Witness: shapes-recorded.

Fakes only: no model, vendor, network, container runtime, credential or holdout. setUpModule arms a process guard
that refuses every process start, clears this process's environment to a fixed few names, and fills run_take's
PENDING Codex billing-route names with an empty tuple for the fake only; tearDownModule undoes all of it and restores
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
    import transcript_codex as tc  # noqa: E402
except ModuleNotFoundError:
    tc = types.ModuleType("transcript_codex")
    tc.__file__ = str(HERE / "transcript_codex.py")
try:
    import codex_adapter as ca  # noqa: E402
except ModuleNotFoundError:
    ca = types.ModuleType("codex_adapter")
    ca.__file__ = str(HERE / "codex_adapter.py")

FIXTURES = HERE / "tests" / "fixtures" / "codex-streams"
README = FIXTURES / "README.md"
SYNTHETIC_LABEL = "SYNTHETIC, from D8 section 1 documentation, not a recorded stream."
LABEL = re.compile(r"^- `([^`]+)`: (SYNTHETIC|RECORDED)\b(.*)$")

D8_EVENTS = ("thread.started", "turn.started", "item.started", "item.completed", "turn.completed", "turn.failed",
             "error")
D8_ITEMS = ("agent_message", "reasoning", "command_execution", "file_change", "mcp_tool_call")
D8_USAGE = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
TID = "synthetic-thread-0001"
TAKE = "cd" * 32
MODEL = "gpt-6.1-sol"
MODE = "bypass"
VERSION = "0.160.1"
LOGIN = "CODEX_API_KEY"
LOGIN_VALUE = "synthetic-login-value-" + "fedcba9876543210"     # a planted fake, never a real key
USAGE = {"input_tokens": 1200, "cached_input_tokens": 800, "output_tokens": 90, "reasoning_output_tokens": 40}

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
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w11a-"))).resolve()
    keep = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TMPDIR") if k in os.environ}
    keep.update(HOME=str(SCRATCH))
    _STACK.enter_context(mock.patch.dict(os.environ, keep, clear=True))
    for name in ("run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _trip(f"subprocess.{name}")))
    for name in ("system", "popen", "posix_spawn", "posix_spawnp", "fork", "forkpty"):
        if hasattr(os, name):
            _STACK.enter_context(mock.patch.object(os, name, _trip(f"os.{name}")))
    # Codex's own billing-route names are PENDING until named from its documentation: none, for the fake only.
    _STACK.enter_context(mock.patch.object(rt, "VENDOR_BILLING_ROUTE_VARIABLES", {rt.CODEX: (), rt.GEMINI: rt.PENDING}))


def tearDownModule():
    _STACK.close()
    sys.path[:] = _SYS_PATH


# ------------------------------------------------------------------------------------------------ fixtures and fakes
def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def lines(name: str) -> list:
    return [ln for ln in fixture(name).splitlines() if ln.strip()]


def labels() -> dict:
    """{fixture name: (SYNTHETIC | RECORDED, the rest of its line)} from the folder's README."""
    out = {}
    for ln in README.read_text(encoding="utf-8").splitlines():
        m = LABEL.match(ln)
        if m:
            out[m.group(1)] = (m.group(2), m.group(3))
    return out


class FakeRuntime:
    """Answers the adapter's execs: `codex --version` and a turn (`codex exec --json ...`), from a queue of streams."""

    def __init__(self, streams, *, version_out=f"codex-cli {VERSION}\n", exit_codes=None, timeout_at=None):
        self.streams, self.exit_codes = list(streams), list(exit_codes or [])
        self.version_out, self.timeout_at = version_out, timeout_at
        self.calls: list = []

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        self.calls.append(a)
        if a[-2:] == ["codex", "--version"]:
            return rt.Completed(0, self.version_out, "")
        if a[:2] == ["docker", "exec"] and "codex" in a and a[a.index("codex") + 1:a.index("codex") + 3] == [
                "exec", "--json"]:
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
    return [c[c.index(TAKE) + 1:] for c in box.calls if TAKE in c and "--json" in c]


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


def adapter(mod, runtime, *, rollouts=None, mode=MODE, counters=None):
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    texts = list(rollouts or [])
    return mod.CodexAdapter(runtime=runtime, take_id=TAKE, run_tree=str(SCRATCH / "tree"), login_file=login_file(),
                            model=MODEL, pin={"permission_mode": mode, "version": VERSION},
                            stream_path_for=lambda n: str(folder / f"turn-{n}.jsonl"),
                            rollout_for=lambda n: texts[n - 1], counters_for=counters or Counters(), clock=Clock())


def refusal(fn, *errors):
    """None when fn() raised one of `errors` (a typed refusal); else a short phrase of what happened instead."""
    try:
        fn()
    except errors:
        return None
    except Exception as e:  # noqa: BLE001
        return f"raised {type(e).__name__} instead of a typed refusal"
    return "accepted it"


TC_API = ("check_record", "decode", "CodexParser", "ShapeError", "EVENT_TYPES", "ITEM_TYPES", "USAGE_KEYS")
CA_API = ("read_stream", "read_rollout", "CodexAdapter", "argv", "end_reason", "StreamError", "SHAPES_SOURCE",
          "SHAPES_SOURCES", "MODE_FLAGS")


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


# ------------------------------------------------------------------------------------------------ transcript_codex
def _both_refuse(mod, p, line, what) -> list:
    out = []
    got = refusal(lambda: mod.decode(line), mod.ShapeError)
    if got:
        out.append(f"{p}: the record check {got}: {what}")
    got = refusal(lambda: mod.CodexParser().items(line), mod.ShapeError)
    if got:
        out.append(f"{p}: the parser {got}: {what}")
    return out


@guarded("S1-event", TC_API)
def s1_event(mod, p):
    out = []
    if tuple(mod.EVENT_TYPES) != D8_EVENTS:
        out.append(f"{p}: the event table is {mod.EVENT_TYPES}, not D8's {D8_EVENTS}")
    out += _both_refuse(mod, p, lines("unknown-event.jsonl")[2], "an item.updated event")
    out += _both_refuse(mod, p, json.dumps({"type": "session.configured"}), "an event type D8 does not name")
    return out


@guarded("S2-item", TC_API)
def s2_item(mod, p):
    out = []
    if tuple(mod.ITEM_TYPES) != D8_ITEMS:
        out.append(f"{p}: the item table is {mod.ITEM_TYPES}, not D8's {D8_ITEMS}")
    out += _both_refuse(mod, p, lines("unknown-item.jsonl")[2], "a web_search item")
    started = json.dumps({"type": "item.started", "item": {"id": "i9", "type": "agent_message", "text": "x"}})
    out += _both_refuse(mod, p, started, "an item.started carrying an agent_message")
    return out


@guarded("S3-key", TC_API)
def s3_key(mod, p):
    out = _both_refuse(mod, p, lines("unknown-key.jsonl")[2], "an agent_message carrying `phase`")
    failed = json.dumps({"type": "turn.failed", "error": {"message": "m", "code": "rate_limit"}})
    out += _both_refuse(mod, p, failed, "a turn.failed error carrying `code`")
    for name in ("turn1-tools.jsonl", "turn-failed.jsonl", "mcp-call.jsonl", "agent-says-429.jsonl"):
        for ln in lines(name):
            try:
                mod.decode(ln)
            except mod.ShapeError as e:
                out.append(f"{p}: {name}: a pre-registered record was refused: {e}")
    return out


def view_events(mod, name):
    with mock.patch.dict(tv.PARSERS, {"codex": mod.CodexParser()}):
        return tv.events("codex", lines(name))


@guarded("P1-view", TC_API)
def p1_view(mod, p):
    out = []
    got = [(e.kind, e.tool, e.args, e.text) for e in view_events(mod, "turn1-tools.jsonl")]
    want = [(tv.HARNESS, None, None, TID), (tv.HARNESS, None, None, None),
            (tv.AGENT_REASONING, None, None, "Synthetic reasoning."),
            (tv.TOOL_CALL, tv.SHELL, {"command": "bash -lc ls", "background": False}, None),
            (tv.TOOL_RESULT, tv.SHELL, None, "README.md\n"),
            (tv.TOOL_CALL, tv.WRITE, {"path": "notes/a.txt"}, None), (tv.TOOL_RESULT, tv.WRITE, None, "completed"),
            (tv.TOOL_CALL, tv.EDIT, {"path": "src/b.py"}, None), (tv.TOOL_RESULT, tv.EDIT, None, "completed"),
            (tv.AGENT_TEXT, None, None, "Synthetic reply one."), (tv.HARNESS, None, None, None)]
    if got != want:
        out.append(f"{p}: turn1-tools reads as {got}")
    got = [(e.kind, e.tool, e.text) for e in view_events(mod, "mcp-call.jsonl")]
    if got[2:4] != [(tv.TOOL_CALL, tv.OTHER, None), (tv.TOOL_RESULT, tv.OTHER, "text\nsynthetic result")]:
        out.append(f"{p}: the mcp call reads as {got[2:4]}")
    got = refusal(lambda: view_events(mod, "file-delete.jsonl"), tv.ViewError)
    if got:
        out.append(f"{p}: a file_change delete {got}")
    if "codex" in tv.PARSERS:
        out.append(f"{p}: the parser was registered in transcript_view.PARSERS")
    return out


# ------------------------------------------------------------------------------------------------ codex_adapter
@guarded("A1-stream", CA_API)
def a1_stream(mod, p):
    out = []
    r = mod.read_stream(fixture("turn1-tools.jsonl"))
    want = {"thread_ids": [TID], "agent_text": "Synthetic reply one.", "agent_output": True, "api_errors": [],
            "usage": USAGE, "completed": 1, "failed": 0, "tool_ids": ["item_1", "item_2"], "undecoded": 0}
    if r != want:
        out.append(f"{p}: turn1-tools reads as {r}")
    if mod.read_stream(fixture("reasoning-only.jsonl"))["agent_output"] is not False:
        out.append(f"{p}: a turn of reasoning alone was read as agent output")
    for name in ("unknown-event.jsonl", "unknown-item.jsonl", "unknown-key.jsonl"):
        got = refusal(lambda: mod.read_stream(fixture(name)), mod.StreamError)
        if got:
            out.append(f"{p}: the adapter's reader {got}: {name}")
    return out


@guarded("A2-error", CA_API)
def a2_error(mod, p):
    out = []
    r = mod.read_stream(fixture("agent-says-429.jsonl"))
    if r["api_errors"] != [] or "429" not in r["agent_text"]:
        out.append(f"{p}: an agent message that says 429 was read as {r['api_errors']} (text {r['agent_text']!r})")
    r = mod.read_stream(fixture("turn-failed.jsonl"))
    want = [{"status": None, "type": "error", "text": "synthetic harness error: stream disconnected"},
            {"status": None, "type": "turn.failed", "text": "synthetic harness error: 429 Too Many Requests"}]
    if r["api_errors"] != want or r["agent_output"] or r["agent_text"]:
        out.append(f"{p}: the failed turn reads {r['api_errors']}, output {r['agent_output']}")
    return out


@guarded("A3-usage", CA_API)
def a3_usage(mod, p):
    out = []
    got = refusal(lambda: mod.read_stream(fixture("usage-missing.jsonl")), mod.StreamError)
    if got:
        out.append(f"{p}: a turn.completed usage missing reasoning_output_tokens {got}")
    if mod.read_stream(fixture("turn-failed.jsonl"))["usage"] is not None:
        out.append(f"{p}: a failed turn with no turn.completed carries usage")
    extra = fixture("turn2-resume.jsonl").replace('"reasoning_output_tokens": 0', '"reasoning_output_tokens": 0, '
                                                                                  '"total_tokens": 9')
    got = refusal(lambda: mod.read_stream(extra), mod.StreamError)
    if got:
        out.append(f"{p}: a usage key with no entry {got}")
    return out


@guarded("A4-argv", CA_API)
def a4_argv(mod, p):
    out = []
    first = mod.argv("one", model=MODEL, mode=MODE, session_id=TID, first=True)
    later = mod.argv("two", model=MODEL, mode=MODE, session_id=TID, first=False)
    if "resume" in first:
        out.append(f"{p}: the first turn's argv resumes: {first}")
    if later[-3:] != ["resume", TID, "two"]:
        out.append(f"{p}: a later turn's argv ends {later[-3:]}, not resume {TID} and the line")
    for name, a in (("first", first), ("later", later)):
        if a[:5] != ["codex", "exec", "--json", "-m", MODEL]:
            out.append(f"{p}: the {name} turn's argv opens {a[:5]}")
    if refusal(lambda: mod.argv("-x", model=MODEL, mode=MODE, session_id=TID, first=True), mod.StreamError):
        out.append(f"{p}: a line starting with '-' was not refused")
    for bad in ("PENDING", "default", None):
        got = refusal(lambda: adapter(mod, FakeRuntime([]), mode=bad), rt.NotReady)
        if got:
            out.append(f"{p}: an adapter under mode {bad!r} {got}")
    box = FakeRuntime([fixture("turn1-tools.jsonl"), fixture("turn2-resume.jsonl"), fixture("turn2-resume.jsonl")])
    two = fixture("rollout-two-turns.jsonl")
    a = adapter(mod, box, rollouts=[two, two, two])
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    try:
        for n, line in enumerate(("first line", "second line", "third line")):
            a.turn(line, first=n == 0, budget_s=60)
    except (mod.StreamError, rt.Refused, rt.NotReady) as e:
        out.append(f"{p}: the take's turns were refused: {e}")
    turns = turn_calls(box)
    for n, inner in enumerate(turns, 1):
        if "-m" not in inner or inner[inner.index("-m") + 1] != MODEL:
            out.append(f"{p}: turn {n} does not pass -m {MODEL}")
        resumed = "resume" in inner
        if resumed != (n > 1) or (resumed and inner[inner.index("resume") + 1] != TID):
            out.append(f"{p}: turn {n} resume is {resumed} ({inner[-3:]})")
        if "--dangerously-bypass-approvals-and-sandbox" not in inner:
            out.append(f"{p}: turn {n} lacks the pinned mode's flag")
    if len(turns) != 3:
        out.append(f"{p}: {len(turns)} turn exec(s), not 3")
    for c in box.calls:
        if any(LOGIN_VALUE in x for x in c) or ("--json" in c and LOGIN not in c):
            out.append(f"{p}: a turn's login does not ride by name only")
    return out


@guarded("A5-model", CA_API)
def a5_model(mod, p):
    out = []
    box = FakeRuntime([fixture("turn1-tools.jsonl"), fixture("turn2-resume.jsonl")])
    a = adapter(mod, box, rollouts=[fixture("rollout-served-other.jsonl"), fixture("rollout-served-other.jsonl")])
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    t1 = a.turn("one", first=True, budget_s=60)
    t2 = a.turn("two", first=False, budget_s=60)
    if t1.init != {"model": "gpt-5.6-luna", "permission_mode": "never", "version": VERSION}:
        out.append(f"{p}: turn 1's init is {t1.init}, not the rollout's turn_context")
    if t2.init is not None or not a.turn_records[1]["why_no_init"]:
        out.append(f"{p}: a turn whose rollout gained no turn_context has init {t2.init}")
    box = FakeRuntime([fixture("turn1-tools.jsonl")])
    a = adapter(mod, box, rollouts=[fixture("rollout-no-context.jsonl")])
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    t = a.turn("one", first=True, budget_s=60)
    if t.init is not None:
        out.append(f"{p}: a rollout with no turn_context gives init {t.init}, never the requested model")
    r = mod.read_rollout(fixture("rollout-two-turns.jsonl"), seen=1)
    if r["init"] != {"model": MODEL, "permission_mode": "never", "version": VERSION} or r["turn_contexts"] != 2:
        out.append(f"{p}: the second turn's context reads {r}")
    return out


@guarded("A6-turn", CA_API)
def a6_turn(mod, p):
    out = []
    ok, failed = fixture("turn1-tools.jsonl"), fixture("turn-failed.jsonl")
    resume = fixture("turn2-resume.jsonl")
    box = FakeRuntime([ok, failed, failed, resume], exit_codes=[0, 1, 0], timeout_at=4)
    two = fixture("rollout-two-turns.jsonl")
    a = adapter(mod, box, rollouts=[two] * 4, counters=Counters(rises=[0, 2, 0, 0]))
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    got = []
    for n in range(4):
        t = a.turn(f"line {n}", first=n == 0, budget_s=60)
        got.append((t.end_reason, t.exit_code, t.counters["oom_kill_delta"]))
    want = [(aa.END_TURN, 0, 0), (aa.END_ERROR, 1, 2), (aa.END_ERROR, 0, 0), (aa.END_TIMED_OUT, None, 0)]
    if got != want:
        out.append(f"{p}: the turns read as {got}, not {want}")
    if a.version() != VERSION:
        out.append(f"{p}: the version reads {a.version()!r}")
    box = FakeRuntime([ok, fixture("turn2-other-thread.jsonl")])
    a = adapter(mod, box, rollouts=[two, two])
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    a.turn("one", first=True, budget_s=60)
    got = refusal(lambda: a.turn("two", first=False, budget_s=60), mod.StreamError)
    if got:
        out.append(f"{p}: a later turn naming another thread {got}")
    return out


@guarded("A7-source", CA_API)
def a7_source(mod, p):
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
    box = FakeRuntime([fixture("turn1-tools.jsonl")])
    a = adapter(mod, box, rollouts=[fixture("rollout-two-turns.jsonl")])
    if a.harness_record() != {"harness": "codex", "shapes_source": mod.SHAPES_SOURCE}:
        out.append(f"{p}: the harness record is {a.harness_record()}")
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    a.turn("one", first=True, budget_s=60)
    if [r["shapes_source"] for r in a.turn_records] != [mod.SHAPES_SOURCE]:
        out.append(f"{p}: the turn records do not carry the shapes' source")
    return out


# ------------------------------------------------------------------------------------------------ the tests
class TestTheShapes(unittest.TestCase):
    def test_s1_an_unknown_event_is_refused(self):
        self.assertEqual(s1_event(tc), [])

    def test_s2_an_unknown_item_type_is_refused(self):
        self.assertEqual(s2_item(tc), [])

    def test_s3_an_unknown_key_is_refused(self):
        self.assertEqual(s3_key(tc), [])

    def test_p1_the_view_vocabulary(self):
        self.assertEqual(p1_view(tc), [])

    def test_the_usage_keys_are_d8s(self):
        self.assertEqual(tuple(getattr(tc, "USAGE_KEYS", ())), D8_USAGE)


class TestTheAdapter(unittest.TestCase):
    def test_a1_the_stream_read(self):
        self.assertEqual(a1_stream(ca), [])

    def test_a2_the_agents_text_is_never_an_api_error(self):
        self.assertEqual(a2_error(ca), [])

    def test_a3_a_missing_usage_field_is_refused(self):
        self.assertEqual(a3_usage(ca), [])

    def test_a4_the_turn_argv(self):
        self.assertEqual(a4_argv(ca), [])

    def test_a5_the_model_is_the_rollouts(self):
        self.assertEqual(a5_model(ca), [])

    def test_a6_a_turn_on_the_fake_runtime(self):
        self.assertEqual(a6_turn(ca), [])

    def test_a7_the_shapes_source_is_documented(self):
        self.assertEqual(a7_source(ca), [])

    def test_a_version_off_its_form_refuses(self):
        self.assertTrue(hasattr(ca, "CodexAdapter"), "codex_adapter.py has no CodexAdapter")
        a = adapter(ca, FakeRuntime([], version_out="codex 0.160\n"))
        with self.assertRaises(rt.NotReady):
            a.version()

    def test_the_adapter_is_named_for_run_takes_harness(self):
        self.assertEqual(getattr(getattr(ca, "CodexAdapter", None), "name", None), rt.CODEX)


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
    name = Path(target.__file__).stem + "_w11a_witness"
    mod = types.ModuleType(name)
    mod.__file__ = target.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, target.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


WITNESSES = {
    # transcript_codex.py
    "unknown-event-accepted": ("tc", (("    if t not in EVENT_KEYS:\n        raise ShapeError(f\"unknown event type: "
                                       "{t!r}\")\n    _keys(f\"event {t}\", rec, *EVENT_KEYS[t])\n",
                                       "    if t in EVENT_KEYS:\n        _keys(f\"event {t}\", rec, *EVENT_KEYS[t])\n"),),
                               s1_event, "S1-event"),
    "unknown-item-accepted": ("tc", (("    if it not in ITEM_KEYS:\n        raise ShapeError(f\"unknown item type: "
                                      "{it!r}\")\n    _keys(f\"item {it}\", item, *ITEM_KEYS[it])\n",
                                      "    if it in ITEM_KEYS:\n        _keys(f\"item {it}\", item, *ITEM_KEYS[it])\n"),),
                              s2_item, "S2-item"),
    "unknown-key-accepted": ("tc", (("    unknown = sorted(set(rec) - set(allowed))\n", "    unknown = []\n"),),
                             s3_key, "S3-key"),
    "reasoning-as-text": ("tc", (("return [tv.RawItem(raw, tv.AGENT_REASONING,", "return [tv.RawItem(raw, tv.AGENT_TEXT,"),),
                          p1_view, "P1-view"),
    "delete-as-write": ("tc", (("CHANGE_KINDS = {\"add\": tv.WRITE, \"update\": tv.EDIT}",
                                "CHANGE_KINDS = {\"add\": tv.WRITE, \"update\": tv.EDIT, \"delete\": tv.WRITE}"),),
                        p1_view, "P1-view"),
    # codex_adapter.py
    "agent-text-as-error": ("ca", (("        if t in tc.ERROR_EVENTS:\n",
                                    "        if t in tc.ERROR_EVENTS or it == tc.AGENT_MESSAGE:\n"),), a2_error,
                            "A2-error"),
    "usage-zero": ("ca", (("vals = {k: rec[\"usage\"].get(k) for k in tc.USAGE_KEYS}",
                           "vals = {k: rec[\"usage\"].get(k, 0) for k in tc.USAGE_KEYS}"),), a3_usage, "A3-usage"),
    "resume-first": ("ca", (("    if not first:\n        if not isinstance(session_id",
                             "    if True:\n        if not isinstance(session_id"),), a4_argv, "A4-argv"),
    "model-first-only": ("ca", (("    out = [CLIENT, SUBCOMMAND, JSON_FLAG, MODEL_FLAG, model, *MODE_FLAGS[mode]]",
                                 "    out = [CLIENT, SUBCOMMAND, JSON_FLAG, *MODE_FLAGS[mode]] + "
                                 "([MODEL_FLAG, model] if first else [])"),), a4_argv, "A4-argv"),
    "model-defaulted": ("ca", (("        init = ro[\"init\"]\n",
                                "        init = ro[\"init\"] or {\"model\": self.model, \"permission_mode\": "
                                "self.mode, \"version\": \"0.160.1\"}\n"),), a5_model, "A5-model"),
    "failed-as-end-turn": ("ca", (("    if exit_code == 0 and read[\"completed\"] == 1 and read[\"failed\"] == 0:",
                                   "    if exit_code == 0:"),), a6_turn, "A6-turn"),
    "other-thread-resumed": ("ca", (("        elif read[\"thread_ids\"] and read[\"thread_ids\"] != [self.thread_id]:",
                                     "        elif False:"),), a6_turn, "A6-turn"),
    "shapes-recorded": ("ca", (("SHAPES_SOURCE = \"documented\"\n", "SHAPES_SOURCE = \"recorded\"\n"),), a7_source,
                        "A7-source"),
}
TARGETS = {"tc": lambda: tc, "ca": lambda: ca}
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

    def test_witness_unknown_event_accepted(self):
        self.kill("unknown-event-accepted")

    def test_witness_unknown_item_accepted(self):
        self.kill("unknown-item-accepted")

    def test_witness_unknown_key_accepted(self):
        self.kill("unknown-key-accepted")

    def test_witness_reasoning_as_text(self):
        self.kill("reasoning-as-text")

    def test_witness_delete_as_write(self):
        self.kill("delete-as-write")

    def test_witness_agent_text_as_error(self):
        self.kill("agent-text-as-error")

    def test_witness_usage_zero(self):
        self.kill("usage-zero")

    def test_witness_resume_first(self):
        self.kill("resume-first")

    def test_witness_model_first_only(self):
        self.kill("model-first-only")

    def test_witness_model_defaulted(self):
        self.kill("model-defaulted")

    def test_witness_failed_as_end_turn(self):
        self.kill("failed-as-end-turn")

    def test_witness_other_thread_resumed(self):
        self.kill("other-thread-resumed")

    def test_witness_shapes_recorded(self):
        self.kill("shapes-recorded")

    def test_the_witnesses_are_named_and_each_anchor_occurs_once(self):
        self.assertEqual(len(WITNESSES), 13)
        for name, (target, edits, _, _) in WITNESSES.items():
            path = Path(TARGETS[target]().__file__)
            self.assertTrue(path.is_file(), f"{name}: {path.name} does not exist")
            src = path.read_text(encoding="utf-8")
            for old, _ in edits:
                self.assertEqual(src.count(old), 1, f"{name}: its anchor occurs {src.count(old)} times")


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        sys.argv.remove("--witnesses")
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestWitnesses)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        red = sum(1 for x in WITNESS_LOG if ": red by " in x)
        print(f"test_codex_adapter witnesses: {red}/{len(WITNESSES)} red; registry {len(WITNESSES)}", flush=True)
        raise SystemExit(0 if result.wasSuccessful() and red == len(WITNESSES) else 1)
    unittest.main(verbosity=2)
