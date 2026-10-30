#!/usr/bin/env python3
"""Lane w11a-codex-adapter (Gap Study round 4, arm O): the Codex CLI adapter and its stream parser, on synthetic
streams over a fake runtime.

    python3 -B -W ignore evals/gap-study-4/tests/test_codex_adapter.py               every test
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_adapter.py --witnesses   the witnesses only, one line each
    python3 -B -W ignore evals/gap-study-4/tests/test_codex_adapter.py --generated-mutants [--shard i/n]
                                                    the generated mutation sweep of both modules (see its section)

Fixtures: tests/fixtures/codex-streams/, every file SYNTHETIC (its README labels each one): written from the event
types, item types and usage keys D8 section 1 names, plus the keys transcript_codex.py lists as "NOT in D8" (and B15's
cache_write_input_tokens, read from the pinned struct: codex_usage_sources.py). No Codex
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
               mcp_tool_call -> other; a delete change -> write (lane pf1-codex-fcdelete, w-o76), any other kind
               refused. Witnesses: reasoning-as-text, delete-hidden, unknown-kind-admitted.
  A1-stream    read_stream: the agent's text, agent output (reasoning alone is not output), usage, tool ids, the
               thread id; a record off the tables refuses the turn on the adapter's road too.
  A2-error     the harness's error event and turn.failed are api_errors with the harness's own words; an agent
               message that says "429" is never one. Witness: agent-text-as-error.
  A3-usage     a usage key that is missing is refused, never 0; a failed turn has no usage (None).
               Witness: usage-zero.
  A4-argv      `-m <model>` on every exec; `resume <thread id>` after turn 1 only, the id read from turn 1's stream;
               a PENDING or unknown mode refuses the adapter; a line starting with "-" is refused; no turn's argv
               carries the planted login value. Witnesses: resume-first, model-first-only.
               Retired 14 Oct 2026 (glitch-06's Codex ruling, option a): the clause "the login rides by name only"
               described the API-key route, which the reviewed subscription transition removed (run_take refuses a
               Codex turn NotReady before any login read; that refusal is bound by its own test outside this module).
               These checks cover the adapter's stream and record road, which does not depend on the login route, so
               every turn here runs through stub_run_turn: an exec that never reads a login and carries no
               credential. Nothing here enables an API-key route.
  A5-model     Codex slice 2 (14 Oct 2026): init is always None, since the rollout's turn_context names the REQUESTED
               model (kept as the turn record's requested_context); identity's model is a reroute item's `to` model,
               else unobserved; version is version-exec. Witnesses: model-defaulted, reroute-unread,
               requested-model-as-served.
  A8-journal   the mode from the turn's own launch journal through launch_facts (exact argv); unobserved without one.
  A6-turn      end reasons (end_turn, error on exit 1, error on exit 0 with turn.failed, timed-out), the counters'
               rise, and a later turn naming another thread refused. Witnesses: failed-as-end-turn,
               other-thread-resumed.
  A7-source    SHAPES_SOURCE is one of the two words and reads "recorded" only while a fixture is labelled RECORDED
               with its walk and CLI version (lane vendor-settle stage V: it reads "recorded"), every fixture carries a
               label, and the adapter reports it in its harness record and every turn record. Witness: shapes-off-word.
  R-recorded   stage V: the seven RECORDED files (w-o46's three streams and rollouts, w-o47's rollout) are byte copies of
               their walk records in rehearsals/, and read_stream, end_reason and read_rollout read them as plain json.

Review round 1 fold (ruling w11a-R1-fold): B1-end, B2-thread, B3-required and B3-stream, B4-rollout, B5-usage,
B6-empty, B7-blank, B8-types, B9-record, B10-cut and B11-version bind each condition and clause one case at a time
(W11A-R1-1 to R1-8, R1-10); A7 requires a RECORDED label's walk id and harness version (R1-9). The generated mutation
sweep binds the class: every mutant killed or listed EQUIVALENT with its reason.

Lane vendor-b23 round 4 (ruling B23-8): B15-fc-pair, B16-fc-second-start and B17-fc-changed bind B22's started
file_change and its pairing: a start and its completion (a call and a result per change under the refs `<id>#<n>`, the
completion's status as the text), a second start refused and each stream's ids new at thread.started, and a completion
off its start's changes refused. Witnesses: started-file-change-unpaired, paired-result-text-dropped,
file-change-second-start-admitted, file-change-changed-admitted.

Fakes only: no model, vendor, network, container runtime, credential or holdout. setUpModule arms a process guard
that refuses every process start, clears this process's environment to a fixed few names, and fills run_take's
PENDING Codex billing-route names with an empty tuple for the fake only; tearDownModule undoes all of it and restores
sys.path.
"""

from __future__ import annotations

import ast
import contextlib
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
# A RECORDED label names the walk and the harness version it was captured at (W11A-R1-9).
RECORDED_LABEL = re.compile(r"RECORDED at walk [A-Za-z0-9][A-Za-z0-9._-]*, codex-cli [0-9]+\.[0-9]+\.[0-9]+\.")

D8_EVENTS = ("thread.started", "turn.started", "item.started", "item.completed", "turn.completed", "turn.failed",
             "error")
D8_ITEMS = ("agent_message", "reasoning", "command_execution", "file_change", "mcp_tool_call")
D8_USAGE = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
# Lane vendor-b14 B15 (practice walk w-o3): the pinned struct Usage, exec_events.rs:59-73 at rust-v0.162.1, in its order.
PINNED_USAGE = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",
                "reasoning_output_tokens")
TID = "synthetic-thread-0001"
TAKE = "cd" * 32
MODEL = "gpt-6.1-sol"
MODE = "bypass"
MODE_FLAG_TEXT = "--dangerously-bypass-approvals-and-sandbox"   # spelled here (D8:110), never read from the module
VERSION = "0.160.1"
LOGIN = "CODEX_API_KEY"
LOGIN_VALUE = "synthetic-login-value-" + "fedcba9876543210"     # a planted fake, never a real key
USAGE = {"input_tokens": 1200, "cached_input_tokens": 800, "cache_write_input_tokens": 0, "output_tokens": 90,
         "reasoning_output_tokens": 40}

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
    # glitch-06's Codex ruling (a), 14 Oct 2026: the turn exec is stubbed, never the login route enabled.
    _STACK.enter_context(mock.patch.object(rt, "run_turn", stub_run_turn))


STUB_CONFIG: list = []


def stub_run_turn(runtime, take_id, inner, *, harness, run_tree, login_file, stream_path, budget_s, clock,
                  caller_env=None, config_folder=None, turn=None):
    """run_take.run_turn's contract for the adapter, minus every login: the turn is a plain agent exec (no variable,
    no login file opened, `login_file` never read), its stdout written once to the host-side stream path, the times
    from the injected clock. A timeout is a timed-out exec, as in run_take."""
    if harness != rt.CODEX:
        raise GuardTripped(f"the Codex stub runs Codex turns only, not {harness!r}")
    STUB_CONFIG.append({"folder": config_folder, "turn": turn})      # B11's record and turn number, as handed
    if not os.path.isabs(stream_path) or os.path.lexists(stream_path):
        raise rt.Refused("the stream path is absolute and new: a stream is never overwritten")
    if not (isinstance(budget_s, (int, float)) and budget_s > 0):
        raise rt.Refused("budget_s > 0")
    argv = rt.agent_exec_argv(take_id, list(inner), workdir=run_tree)
    started = clock()
    timed_out, code, out, err = False, None, "", ""
    try:
        c = runtime.run(argv, env=rt.runtime_env(caller_env), timeout=budget_s)
        code, out, err = c.returncode, c.stdout, c.stderr
    except TimeoutError as e:
        timed_out, out = True, getattr(e, "stdout", "") or ""
    ended = clock()
    fd = os.open(stream_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(out)
    return {"exit_code": code, "timed_out": timed_out, "started_at": started, "ended_at": ended,
            "stream_path": stream_path, "stderr": err}


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

    def __init__(self, streams, *, version_out=f"codex-cli {VERSION}\n", exit_codes=None, timeout_at=None,
                 version_code=0):
        self.streams, self.exit_codes, self.version_code = list(streams), list(exit_codes or []), version_code
        self.version_out, self.timeout_at = version_out, timeout_at
        self.calls: list = []

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        self.calls.append(a)
        if a[-2:] == ["codex", "--version"]:
            return rt.Completed(self.version_code, self.version_out, "")
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
    out += _both_refuse(mod, p, "not json", "a line that is not JSON")
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
    full = [{"type": "item.completed", "item": {"id": "x1", "type": "mcp_tool_call", "server": "s", "tool": "t",
                                                "arguments": {"q": 1}, "result": None, "error": None,
                                                "status": "completed"}},
            {"type": "item.completed", "item": {"id": "c1", "type": "command_execution", "command": "ls",
                                                "aggregated_output": "", "exit_code": None, "status": "failed"}}]
    for rec in full:
        try:
            mod.decode(json.dumps(rec))
        except mod.ShapeError as e:
            out.append(f"{p}: a record carrying every allowed key was refused: {e}")
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
    # Lane pf1-codex-fcdelete (glitch-45's brief, Tue 27 Oct 2026; w-o76): a delete reads as a write of its path.
    try:
        got = [(e.kind, e.tool, e.args, e.text) for e in view_events(mod, "file-delete.jsonl")][2:4]
    except tv.ViewError as e:
        got = f"refused ({e})"
    if got != [(tv.TOOL_CALL, tv.WRITE, {"path": "old.txt"}, None), (tv.TOOL_RESULT, tv.WRITE, None, "completed")]:
        out.append(f"{p}: a file_change delete reads as {got}")
    renamed = [ln.replace('"kind": "delete"', '"kind": "rename"') for ln in lines("file-delete.jsonl")]
    with mock.patch.dict(tv.PARSERS, {"codex": mod.CodexParser()}):
        got = refusal(lambda: tv.events("codex", renamed), tv.ViewError)
    if got:
        out.append(f"{p}: a file_change of kind rename {got}")
    raws = [it.raw_type for ln in lines("turn1-tools.jsonl") for it in mod.CodexParser().items(ln)]
    if raws != ["thread.started", "turn.started", "item.completed:reasoning", "item.started:command_execution",
                "item.completed:command_execution", "item.completed:file_change", "item.completed:file_change",
                "item.completed:file_change", "item.completed:file_change", "item.completed:agent_message",
                "turn.completed"]:
        out.append(f"{p}: the parser's raw types read {raws}")
    if not isinstance(tv.PARSERS.get("codex"), tv.VendorBoundParser):
        out.append(f"{p}: the published parser does not require bound native records")
    return out


# ------------------------------------------------------------------------------------------------ codex_adapter
@guarded("A1-stream", CA_API)
def a1_stream(mod, p):
    out = []
    r = mod.read_stream(fixture("turn1-tools.jsonl"))
    want = {"thread_ids": [TID], "agent_text": "Synthetic reply one.", "agent_output": True, "api_errors": [],
            "usage": USAGE, "completed": 1, "failed": 0, "tool_ids": ["item_1", "item_2"], "undecoded": 0,
            "served_model": None}
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


# The pinned `codex exec --help` Commands list (box evidence codex-exec-help.json, sha256 a90c28e8...; the box's
# run_take.CODEX_HELP_COMMANDS, box 14670435): a first turn's line that is exactly one of them would run as that
# subcommand (`codex exec [OPTIONS] <COMMAND> [ARGS]`). A later turn's line follows `resume <thread id>` and stays a
# prompt.
EXEC_COMMANDS = ("resume", "fork", "review", "help")


def help_binding_problems(adapter_commands, run_take_mod) -> list:
    """The adapter's subcommand list against run_take.CODEX_HELP_COMMANDS where that module carries one (else nothing
    to bind): any difference, in names or order, is a problem."""
    theirs = getattr(run_take_mod, "CODEX_HELP_COMMANDS", None)
    if theirs is None or tuple(theirs) == tuple(adapter_commands):
        return []
    return [f"A4-help: the adapter's {tuple(adapter_commands)} is not run_take's {tuple(theirs)}"]


def a4_word(mod, word) -> list:
    p, out = "A4-argv", []
    got = refusal(lambda: mod.argv(word, model=MODEL, mode=MODE, session_id=TID, first=True), mod.StreamError)
    if got:
        out.append(f"{p}: a first turn's line {word!r}, a codex exec subcommand name, was {got}")
    try:
        later = mod.argv(word, model=MODEL, mode=MODE, session_id=TID, first=False)
        if later[-3:] != ["resume", TID, word]:
            out.append(f"{p}: a later turn's line {word!r} is not the prompt after resume: {later[-3:]}")
    except Exception as e:  # noqa: BLE001
        out.append(f"{p}: a later turn's line {word!r} was refused ({type(e).__name__})")
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
    for word in EXEC_COMMANDS:          # the box Codex-exec review's MAJOR, on this side: a subcommand-name prompt
        out += a4_word(mod, word)
    for bad in ("PENDING", "default", "", None, ["bypass"]):
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
    for c in box.calls:              # the "rides by name" clause is retired (see A4 above); the value never rides
        if any(LOGIN_VALUE in x for x in c):
            out.append(f"{p}: a turn's argv carries the login value")
    return out


@guarded("A5-model", CA_API + ("turn_identity", "submitted_mode", "reroute_of"))
def a5_model(mod, p):
    """Codex slice 2: init is always None (the rollout's turn_context names the requested model, never the served one;
    it is kept as the turn record's requested_context); identity's model is a reroute item's `to` model, else
    unobserved; version is version-exec; the mode is the turn's journal read through launch_facts."""
    out = []
    box = FakeRuntime([fixture("turn1-tools.jsonl"), fixture("turn2-resume.jsonl")])
    a = adapter(mod, box, rollouts=[fixture("rollout-served-other.jsonl"), fixture("rollout-served-other.jsonl")])
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    t1 = a.turn("one", first=True, budget_s=60)
    if t1.init is not None:
        out.append(f"{p}: turn 1's init is {t1.init}, the requested model read as proof")
    if a.turn_records[0]["requested_context"] != {"model": "gpt-5.6-luna", "permission_mode": "never",
                                                  "version": VERSION}:
        out.append(f"{p}: the requested context is not kept: {a.turn_records[0]['requested_context']}")
    unobserved = {"value": None, "source": "unobserved"}
    if t1.identity != {"model": unobserved, "permission_mode": unobserved,
                       "version": {"value": VERSION, "source": "version-exec"}}:
        out.append(f"{p}: turn 1's identity is {t1.identity}")
    # Codex road review F1, F2: one parser (codex_native.reroute_of), the reason pinned to HighRiskCyberActivity and
    # `from` the turn's own -m model; spelled here from the source, never read from the module.
    good = f"model rerouted: {MODEL} -> gpt-6-sol (HighRiskCyberActivity)"
    rerouted = "\n".join(lines("turn1-tools.jsonl")[:1] + [json.dumps({"type": "item.completed", "item": {
        "id": "item_9", "type": "error", "message": good}})] + lines("turn1-tools.jsonl")[1:]) + "\n"
    try:
        r = mod.read_stream(rerouted, model=MODEL)
    except mod.StreamError as e:
        return out + [f"{p}: a reroute item is refused as off the tables: {e}"]
    if r["served_model"] != "gpt-6-sol" or r["agent_output"] is not True or r["api_errors"]:
        out.append(f"{p}: a reroute item reads as {r['served_model']!r} (output {r['agent_output']}, errors "
                   f"{r['api_errors']})")
    if mod.turn_identity(r, version="9.9.9", mode=unobserved)["model"] != {"value": "gpt-6-sol",
                                                                            "source": "stream-reroute"}:
        out.append(f"{p}: the reroute is not the identity's model")
    if refusal(lambda: mod.read_stream(rerouted), mod.StreamError):
        out.append(f"{p}: with no requested model named, a reroute-shaped item was not refused as off the tables")
    for msg in (f"model rerouted: {MODEL} -> b", f"Model rerouted: {MODEL} -> b (HighRiskCyberActivity)",
                f"model rerouted: {MODEL} -> b (HighRiskCyberActivity) extra",
                f"model rerouted: {MODEL} -> b (HighRiskCyber)", f"model rerouted: {MODEL} -> b (Other)",
                "model rerouted: gpt-other -> b (HighRiskCyberActivity)", "a warning that is not a reroute"):
        rec = {"type": "item.completed", "item": {"id": "i", "type": "error", "message": msg}}
        if mod.reroute_of(rec, MODEL) is not None:
            out.append(f"{p}: {msg!r} read as a reroute")
    shaped = f"model rerouted: {MODEL} -> b (HighRiskCyberActivity)"
    if mod.reroute_of({"type": "item.completed", "item": {"id": "i", "type": "error", "message": shaped}}, MODEL) != "b":
        out.append(f"{p}: the control reroute is not read")
    for rec in ({"type": "item.started", "item": {"id": "i", "type": "error", "message": shaped}},
                {"type": "item.completed", "item": {"id": "i", "type": "error", "message": shaped, "extra": 1}},
                {"type": "item.completed", "item": {"id": 7, "type": "error", "message": shaped}},
                {"type": "item.completed", "item": {"id": "i", "type": "warning", "message": shaped}},
                {"type": "item.completed", "item": {"id": "i", "type": "error", "message": 7}},
                {"type": "item.completed", "item": ["id", "type", "message"]},
                ["type", "item"]):
        try:
            got = mod.reroute_of(rec, MODEL)
        except Exception as e:  # noqa: BLE001 - a crash on a malformed record is a finding, never a kill by error
            got = f"a crash: {type(e).__name__}"
        if got is not None:
            out.append(f"{p}: {rec} read as a reroute ({got})")
    two = rerouted + json.dumps({"type": "item.completed", "item": {
        "id": "item_10", "type": "error", "message": f"model rerouted: {MODEL} -> gpt-6-luna (HighRiskCyberActivity)"}}) + "\n"
    got = refusal(lambda: mod.read_stream(two, model=MODEL), mod.StreamError)
    if got:
        out.append(f"{p}: two reroutes to different models {got}")
    other = "\n".join(lines("turn1-tools.jsonl") + [json.dumps({"type": "item.completed", "item": {
        "id": "item_9", "type": "error", "message": "a warning that is not a reroute"}})]) + "\n"
    got = refusal(lambda: mod.read_stream(other), mod.StreamError)
    if got:
        out.append(f"{p}: any other error item {got}")
    r = mod.read_rollout(fixture("rollout-two-turns.jsonl"), seen=1)
    if r["init"] != {"model": MODEL, "permission_mode": "never", "version": VERSION} or r["turn_contexts"] != 2:
        out.append(f"{p}: the second turn's context reads {r}")
    return out


@guarded("A8-journal", CA_API + ("submitted_mode",))
def a8_journal(mod, p):
    """Codex slice 2: the mode from the turn's own journal, checked by launch_facts against the registered invocation
    (the argv exactly); no journal, a link, bad bytes or no argv list are unobserved; anything off the invocation is
    "launch-differs-from-registered-invocation". Spelled here, never read from the module."""
    out = []
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    stream, tree = str(folder / "turn-1.jsonl"), str(SCRATCH / "tree")
    want = {"harness": "codex", "container_id": TAKE, "model": MODEL, "mode": MODE, "run_tree": tree,
            "stream": stream, "sent": "hello", "vendor_session_id": "first-turn", "ordinal": 1}
    registered = list(mod.argv("hello", model=MODEL, mode=MODE, session_id=None, first=True))

    def journal(argv=None, raw=None, **over):
        path = folder / f"j-{len(list(folder.iterdir()))}.launch.json"
        doc = dict({"schema": 1, "harness": "codex", "container_id": TAKE,
                    "argv": registered if argv is None else argv, "cwd": tree, "stream": stream,
                    "started_at": 1.0}, **over)
        path.write_bytes(raw if raw is not None else json.dumps(doc).encode())
        return str(path)
    unobserved = {"value": None, "source": "unobserved"}
    link = folder / "link.launch.json"
    os.symlink(journal(), link)
    for why, path, expect in (
            ("no journal", str(folder / "absent.launch.json"), unobserved),
            ("a link", str(link), unobserved),
            ("bytes that are not JSON", journal(raw=b"{not json"), unobserved),
            ("bytes that are not UTF-8", journal(raw=b"\xff\xfe"), unobserved),
            ("a JSON list", journal(raw=b"[]"), unobserved),
            ("an argv that is not a list", journal(argv="codex exec"), unobserved),
            ("the registered launch", journal(), {"value": MODE, "source": "submitted-argv"}),
            ("an extra flag", journal(argv=registered[:-1] + ["--full-auto", registered[-1]]),
             {"value": "launch-differs-from-registered-invocation", "source": "submitted-argv"}),
            ("the mode's flag dropped", journal(argv=[a for a in registered if a != MODE_FLAG_TEXT]),
             {"value": "launch-differs-from-registered-invocation", "source": "submitted-argv"}),
            ("another folder", journal(cwd=str(SCRATCH / "elsewhere")),
             {"value": "launch-differs-from-registered-invocation", "source": "submitted-argv"})):
        got = mod.submitted_mode(path, dict(want))
        if got != expect:
            out.append(f"{p}: {why}: {got}, not {expect}")
    box = FakeRuntime([fixture("turn1-tools.jsonl"), fixture("turn2-resume.jsonl")])
    two = fixture("rollout-two-turns.jsonl")
    a = mod.CodexAdapter(runtime=box, take_id=TAKE, run_tree=tree, login_file=login_file(), model=MODEL,
                         pin={"permission_mode": MODE, "version": VERSION},
                         stream_path_for=lambda n: str(folder / f"t-{n}.jsonl"), rollout_for=lambda n: two,
                         counters_for=Counters(), clock=Clock())
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    for n, (line, session) in enumerate((("one", None), ("two", TID)), 1):
        s = str(folder / f"t-{n}.jsonl")
        Path(s + ".launch.json").write_text(json.dumps({
            "schema": 1, "harness": "codex", "container_id": TAKE,
            "argv": list(mod.argv(line, model=MODEL, mode=MODE, session_id=session, first=n == 1)),
            "cwd": tree, "stream": s, "started_at": 1.0}))
    for n, line in enumerate(("one", "two"), 1):
        r = a.turn(line, first=n == 1, budget_s=60)
        if r.identity["permission_mode"] != {"value": MODE, "source": "submitted-argv"}:
            out.append(f"{p}: turn {n}'s mode from its journal is {r.identity['permission_mode']}")
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


def label_problems(marks: dict, files: list) -> tuple:
    """(problems, the fixtures whose RECORDED label carries its provenance) for a README's labels (W11A-R1-9).

    A SYNTHETIC label must be the brief's words; a RECORDED label must name the walk and the harness version it was
    captured at (RECORDED_LABEL); a RECORDED word without both is a problem, never counted as recorded."""
    out = []
    unlabelled = [f for f in files if f not in marks]
    if unlabelled:
        out.append(f"fixture(s) with no label: {unlabelled}")
    wrong = [f for f, (kind, rest) in marks.items() if kind == "SYNTHETIC" and kind + rest != SYNTHETIC_LABEL]
    if wrong:
        out.append(f"fixture(s) whose label is not the brief's words: {wrong}")
    bare = [f for f, (kind, rest) in marks.items() if kind == "RECORDED" and not RECORDED_LABEL.fullmatch(kind + rest)]
    if bare:
        out.append(f"fixture(s) labelled RECORDED without the walk id and harness version: {bare}")
    recorded = [f for f, (kind, rest) in marks.items() if kind == "RECORDED" and f in files
                and RECORDED_LABEL.fullmatch(kind + rest)]
    return out, recorded


@guarded("A7-source", CA_API)
def a7_source(mod, p):
    files = sorted(f.name for f in FIXTURES.iterdir() if f.name != README.name)
    problems, recorded = label_problems(labels(), files)
    out = [f"{p}: {x}" for x in problems]
    if mod.SHAPES_SOURCE not in mod.SHAPES_SOURCES or tuple(mod.SHAPES_SOURCES) != ("documented", "recorded"):
        out.append(f"{p}: SHAPES_SOURCE {mod.SHAPES_SOURCE!r} is off the two words")
    if mod.SHAPES_SOURCE == "recorded" and not recorded:
        out.append(f"{p}: SHAPES_SOURCE reads 'recorded' while no fixture is labelled RECORDED with its provenance")
    # lane pf1-l1-freeze-gates (pre-freeze review 1, m3): "recorded" rests on SHAPES_RECORDED_ON, a fixture the
    # freeze's leg i holds to its committed walk record on the pinned CLI (check_take.recorded_binding_problem)
    if mod.SHAPES_SOURCE == "recorded":
        import check_take
        pins = json.loads((HERE / "prereg-draft.json").read_text())["version_pins"]["codex"]
        cli = check_take.VENDOR_FIXTURE_CLI["codex"] + " " + next(iter(pins.values()))["agent_version"]
        why = check_take.recorded_binding_problem("codex", getattr(mod, "SHAPES_RECORDED_ON", None), cli)
        if why or getattr(mod, "SHAPES_RECORDED_ON", None) != "recorded-codex-w-o46/transcript.jsonl":
            out.append(f"{p}: SHAPES_RECORDED_ON {getattr(mod, 'SHAPES_RECORDED_ON', None)!r} does not bind: {why}")
    box = FakeRuntime([fixture("turn1-tools.jsonl")])
    a = adapter(mod, box, rollouts=[fixture("rollout-two-turns.jsonl")])
    if a.harness_record() != {"harness": "codex", "shapes_source": mod.SHAPES_SOURCE}:
        out.append(f"{p}: the harness record is {a.harness_record()}")
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    a.turn("one", first=True, budget_s=60)
    if [r["shapes_source"] for r in a.turn_records] != [mod.SHAPES_SOURCE]:
        out.append(f"{p}: the turn records do not carry the shapes' source")
    return out


# ------------------------------------------------------------------------------------------------ review round 1 fold
# Each check below changes one thing per case (ruling w11a-R1-fold item 1), so each condition and clause is bound on
# its own; the generated mutation sweep (--generated-mutants) binds the class.
def jl(*recs) -> str:
    return "".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in recs)


T_START = {"type": "thread.started", "thread_id": TID}
TURN_START = {"type": "turn.started"}
DONE = {"type": "turn.completed", "usage": USAGE}
FAILED = {"type": "turn.failed", "error": {"message": "synthetic failure"}}


def say(text, i="m1"):
    return {"type": "item.completed", "item": {"id": i, "type": "agent_message", "text": text}}


def take_with(mod, streams, rollouts=None, exit_codes=None):
    box = FakeRuntime(streams, exit_codes=exit_codes)
    two = fixture("rollout-two-turns.jsonl")
    a = adapter(mod, box, rollouts=rollouts or [two] * len(streams))
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    return a, box


@guarded("B1-end", CA_API)
def b1_end(mod, p):
    """W11A-R1-1: each of end_reason's three conditions, and the turn.failed count, on its own."""
    out = []
    cases = [((1, False, {"completed": 1, "failed": 0}), aa.END_ERROR, "a non-zero exit with a clean stream"),
             ((0, False, {"completed": 0, "failed": 0}), aa.END_ERROR, "exit 0 with no turn.completed"),
             ((0, False, {"completed": 1, "failed": 1}), aa.END_ERROR, "exit 0 with a turn.failed"),
             ((None, False, {"completed": 1, "failed": 0}), aa.END_ERROR, "no exit code"),
             ((0, False, {"completed": 1, "failed": 0}), aa.END_TURN, "exit 0, one turn.completed, no turn.failed"),
             ((0, True, {"completed": 1, "failed": 0}), aa.END_TIMED_OUT, "a timed-out exec")]
    for args, want, what in cases:
        got = mod.end_reason(*args)
        if got != want:
            out.append(f"{p}: {what} ends {got!r}, not {want!r}")
    r = mod.read_stream(jl(T_START, TURN_START, say("x"), FAILED, DONE))
    if (r["failed"], r["completed"]) != (1, 1):
        out.append(f"{p}: a stream with one turn.failed and one turn.completed counts {r['failed']}, {r['completed']}")
    a, _ = take_with(mod, [jl(T_START, TURN_START, say("x"), FAILED, DONE)])
    t = a.turn("one", first=True, budget_s=60)
    if t.end_reason != aa.END_ERROR:
        out.append(f"{p}: a turn with turn.failed and turn.completed under exit 0 ends {t.end_reason!r}")
    return out


@guarded("B2-thread", CA_API)
def b2_thread(mod, p):
    """W11A-R1-2: the thread id at all three seats: read_stream's shape, argv's later-turn id, turn 1's one thread."""
    out = []
    for bad in ("--last", "", "a b", 5):
        got = refusal(lambda: mod.read_stream(jl({"type": "thread.started", "thread_id": bad}, TURN_START)),
                      mod.StreamError)
        if got:
            out.append(f"{p}: read_stream with thread id {bad!r} {got}")
    for bad in (None, "--last", "", 5):
        got = refusal(lambda: mod.argv("two", model=MODEL, mode=MODE, session_id=bad, first=False), mod.StreamError)
        if got:
            out.append(f"{p}: argv for a later turn with session id {bad!r} {got}")
    second = jl(T_START, TURN_START, say("two"), DONE)
    a, box = take_with(mod, [jl(T_START, T_START, TURN_START, say("one"), DONE), second])
    a.turn("one", first=True, budget_s=60)
    if a.turn_records[0]["thread_ids"] != [TID]:
        out.append(f"{p}: one thread named twice reads {a.turn_records[0]['thread_ids']}")
    if refusal(lambda: a.turn("two", first=False, budget_s=60), mod.StreamError) is None or len(turn_calls(box)) != 2:
        out.append(f"{p}: turn 1 naming its one thread twice did not let turn 2 resume it")
    for what, first in (("no thread.started", jl(TURN_START, say("one"), DONE)),
                        ("two thread ids", jl(T_START, {"type": "thread.started", "thread_id": "synthetic-thread-0009"},
                                              TURN_START, say("one"), DONE))):
        a, box = take_with(mod, [first, second])
        a.turn("one", first=True, budget_s=60)
        got = refusal(lambda: a.turn("two", first=False, budget_s=60), mod.StreamError)
        if got or len(turn_calls(box)) != 1:
            out.append(f"{p}: turn 1 with {what}: turn 2 {got or 'refused'} after {len(turn_calls(box))} exec(s)")
    a, box = take_with(mod, [jl(T_START, TURN_START, say("one"), DONE), jl(TURN_START, say("two"), DONE)])
    a.turn("one", first=True, budget_s=60)
    try:
        a.turn("two", first=False, budget_s=60)
        refused = False
    except mod.StreamError:
        refused = True
    if refused or len(turn_calls(box)) != 2:
        out.append(f"{p}: a later turn whose stream names no thread was refused (Q-w11a-5: it is accepted)")
    a, box = take_with(mod, [jl({"type": "thread.started", "thread_id": "--last"}, TURN_START, say("one"), DONE),
                             second])
    got = refusal(lambda: a.turn("one", first=True, budget_s=60), mod.StreamError)
    if got or any("resume" in c for c in turn_calls(box)):
        out.append(f"{p}: a turn 1 naming thread '--last' {got or 'refused'}; execs {turn_calls(box)}")
    return out


REQUIRED_DROPS = (
    ("thread.started without thread_id", {"type": "thread.started"}),
    ("turn.completed without usage", {"type": "turn.completed"}),
    ("turn.failed without error", {"type": "turn.failed"}),
    ("turn.failed error without message", {"type": "turn.failed", "error": {}}),
    ("error without message", {"type": "error"}),
    ("item.completed without item", {"type": "item.completed"}),
    ("item without id", {"type": "item.completed", "item": {"type": "agent_message", "text": "x"}}),
    ("agent_message without text", {"type": "item.completed", "item": {"id": "i1", "type": "agent_message"}}),
    ("reasoning without text", {"type": "item.completed", "item": {"id": "i1", "type": "reasoning"}}),
    ("command_execution without command", {"type": "item.completed", "item": {"id": "i1", "type": "command_execution"}}),
    ("file_change without changes", {"type": "item.completed", "item": {"id": "i1", "type": "file_change"}}),
    ("a change without kind", {"type": "item.completed", "item": {"id": "i1", "type": "file_change",
                                                                   "changes": [{"path": "a"}]}}),
    ("mcp_tool_call without tool", {"type": "item.started", "item": {"id": "i1", "type": "mcp_tool_call",
                                                                      "server": "s"}}),
    ("mcp_tool_call without server", {"type": "item.started", "item": {"id": "i1", "type": "mcp_tool_call",
                                                                        "tool": "t"}}),
)
TYPE_BREAKS = (
    ("agent_message text 5", say(5)),
    ("reasoning text 5", {"type": "item.completed", "item": {"id": "i1", "type": "reasoning", "text": 5}}),
    ("item id ''", {"type": "item.completed", "item": {"id": "", "type": "agent_message", "text": "x"}}),
    ("item id 5", {"type": "item.completed", "item": {"id": 5, "type": "agent_message", "text": "x"}}),
    ("item not an object", {"type": "item.completed", "item": "agent_message"}),
    ("command 5", {"type": "item.started", "item": {"id": "i1", "type": "command_execution", "command": 5}}),
    ("exit_code '0'", {"type": "item.completed", "item": {"id": "i1", "type": "command_execution", "command": "ls",
                                                           "exit_code": "0"}}),
    ("exit_code true", {"type": "item.completed", "item": {"id": "i1", "type": "command_execution", "command": "ls",
                                                            "exit_code": True}}),
    ("changes []", {"type": "item.completed", "item": {"id": "i1", "type": "file_change", "changes": []}}),
    ("changes not a list", {"type": "item.completed", "item": {"id": "i1", "type": "file_change", "changes": "a"}}),
    ("a change not an object", {"type": "item.completed", "item": {"id": "i1", "type": "file_change",
                                                                    "changes": ["a"]}}),
    ("a change path 5", {"type": "item.completed", "item": {"id": "i1", "type": "file_change",
                                                             "changes": [{"path": 5, "kind": "add"}]}}),
    ("error message 5", {"type": "error", "message": 5}),
    ("turn.failed error not an object", {"type": "turn.failed", "error": "x"}),
    ("turn.failed error 5", {"type": "turn.failed", "error": 5}),
    ("turn.failed message 5", {"type": "turn.failed", "error": {"message": 5}}),
    ("usage not an object", {"type": "turn.completed", "usage": [1, 2]}),
    ("status 5", {"type": "item.completed", "item": {"id": "i1", "type": "file_change", "status": 5,
                                                      "changes": [{"path": "a", "kind": "add"}]}}),
    ("server 5", {"type": "item.started", "item": {"id": "i1", "type": "mcp_tool_call", "server": 5, "tool": "t"}}),
    ("a record not an object", [1]),
    ("aggregated_output 5", {"type": "item.completed", "item": {"id": "i1", "type": "command_execution",
                                                                 "command": "ls", "aggregated_output": 5}}),
    ("tool 5", {"type": "item.started", "item": {"id": "i1", "type": "mcp_tool_call", "server": "s", "tool": 5}}),
    ("changes 5", {"type": "item.completed", "item": {"id": "i1", "type": "file_change", "changes": 5}}),
    ("a change 5", {"type": "item.completed", "item": {"id": "i1", "type": "file_change", "changes": [5]}}),
    ("a change kind [1]", {"type": "item.completed", "item": {"id": "i1", "type": "file_change",
                                                               "changes": [{"path": "a", "kind": [1]}]}}),
    ("an event type [1]", {"type": [1]}),
    ("an item type [1]", {"type": "item.completed", "item": {"id": "i1", "type": [1]}}),
)


@guarded("B3-required", TC_API)
def b3_required(mod, p):
    """W11A-R1-3: each required key, dropped one at a time, refused by the record check."""
    out = []
    for what, rec in REQUIRED_DROPS:
        got = refusal(lambda: mod.check_record(rec), mod.ShapeError)
        if got:
            out.append(f"{p}: {what}: the record check {got}")
    return out


@guarded("B3-stream", CA_API)
def b3_stream(mod, p):
    """W11A-R1-3 and R1-8 on the adapter's road: each dropped key and each value off its type is a StreamError."""
    out = []
    for what, rec in REQUIRED_DROPS + TYPE_BREAKS:
        got = refusal(lambda: mod.read_stream(jl(T_START, TURN_START, rec)), mod.StreamError)
        if got:
            out.append(f"{p}: {what}: read_stream {got}")
    return out


@guarded("B8-types", TC_API)
def b8_types(mod, p):
    """W11A-R1-8: each value off its type, one at a time, refused (typed) by the record check or the parser."""
    out = []
    for what, rec in TYPE_BREAKS:
        got = refusal(lambda: mod.CodexParser().items(json.dumps(rec)), mod.ShapeError)
        if got:
            out.append(f"{p}: {what}: the parser {got}")
        got = refusal(lambda: mod.check_record(rec), mod.ShapeError)
        if got:
            out.append(f"{p}: {what}: the record check {got}")
    return out


ROLLOUT_META_OK = {"type": "session_meta", "payload": {"id": TID, "cli_version": VERSION}}


def ctx(**payload):
    return {"type": "turn_context", "payload": payload}


@guarded("B4-rollout", CA_API)
def b4_rollout(mod, p):
    """W11A-R1-4: the rollout init's guards, one at a time."""
    out = []
    good = {"model": MODEL, "permission_mode": "never", "version": VERSION}
    r = mod.read_rollout(jl(ROLLOUT_META_OK, ctx(model=MODEL, approval_policy="never")), seen=0)
    if r != {"turn_contexts": 1, "init": good, "why_no_init": None}:
        out.append(f"{p}: a clean rollout reads {r}")
    r = mod.read_rollout(jl(ROLLOUT_META_OK, ctx(model=MODEL, approval_policy="never"),
                            ctx(model=MODEL, approval_policy="never")), seen=0)
    if r["init"] != good or r["turn_contexts"] != 2:
        out.append(f"{p}: two agreeing turn_contexts in one turn read {r}")
    got = refusal(lambda: mod.read_rollout(jl(ROLLOUT_META_OK, ctx(model="a", approval_policy="never"),
                                              ctx(model="b", approval_policy="never")), seen=0), mod.StreamError)
    if got:
        out.append(f"{p}: one turn's turn_contexts naming two models {got}")
    nones = (("no approval_policy", jl(ROLLOUT_META_OK, ctx(model=MODEL))),
             ("approval_policy 5", jl(ROLLOUT_META_OK, ctx(model=MODEL, approval_policy=5))),
             ("approval_policy ''", jl(ROLLOUT_META_OK, ctx(model=MODEL, approval_policy=""))),
             ("no model", jl(ROLLOUT_META_OK, ctx(approval_policy="never"))),
             ("model ''", jl(ROLLOUT_META_OK, ctx(model="", approval_policy="never"))),
             ("no session_meta", jl(ctx(model=MODEL, approval_policy="never"))),
             ("two session_metas", jl(ROLLOUT_META_OK, {"type": "session_meta", "payload": {"cli_version": "9.9.9"}},
                                      ctx(model=MODEL, approval_policy="never"))),
             ("a session_meta with no cli_version", jl({"type": "session_meta", "payload": {"id": TID}},
                                                       ctx(model=MODEL, approval_policy="never"))),
             ("a session_meta payload not an object", jl({"type": "session_meta", "payload": "x"},
                                                         ctx(model=MODEL, approval_policy="never"))))
    for what, text in nones:
        r = mod.read_rollout(text, seen=0)
        if r["init"] is not None or not isinstance(r["why_no_init"], str) or not r["why_no_init"]:
            out.append(f"{p}: {what}: init {r['init']}, reason {r['why_no_init']!r}")
    for what, text in (("a payload not an object", jl(ROLLOUT_META_OK, {"type": "turn_context", "payload": "x"})),
                       ("a line that is not JSON", jl(ROLLOUT_META_OK, "not json")),
                       ("a record that is not an object", jl(ROLLOUT_META_OK, [1]))):
        got = refusal(lambda: mod.read_rollout(text, seen=0), mod.StreamError)
        if got:
            out.append(f"{p}: a rollout with {what} {got}")
    r = mod.read_rollout(jl(ROLLOUT_META_OK, ctx(model="a", approval_policy="never"),
                            ctx(model=MODEL, approval_policy="never")), seen=1)
    if r["init"] != good:
        out.append(f"{p}: the turn_contexts before `seen` were read: {r}")
    r = mod.read_rollout(jl(ROLLOUT_META_OK, ctx(model=MODEL, approval_policy="on-request"),
                            ctx(model=MODEL, approval_policy="never")), seen=0)
    if r["init"] != good:
        out.append(f"{p}: of one turn's two turn_contexts, the last is not the one read: {r['init']}")
    r = mod.read_rollout(jl(ROLLOUT_META_OK, "", "   ", ctx(model=MODEL, approval_policy="never")), seen=0)
    if r["init"] != good:
        out.append(f"{p}: a rollout with blank lines reads {r}")
    r = mod.read_rollout(jl(ROLLOUT_META_OK), seen=0)
    if r["init"] is not None or r["turn_contexts"] != 0:
        out.append(f"{p}: a rollout with no turn_context reads {r}")
    return out


@guarded("B5-usage", CA_API)
def b5_usage(mod, p):
    """W11A-R1-5: usage values true, negative or not an int, and two turn.completed records, each refused."""
    out = []
    for what, v in (("true", True), ("-5", -5), ("1.0", 1.0), ("'3'", "3"), ("None", None)):
        got = refusal(lambda: mod.read_stream(jl(T_START, {"type": "turn.completed",
                                                           "usage": dict(USAGE, output_tokens=v)})), mod.StreamError)
        if got:
            out.append(f"{p}: output_tokens {what} {got}")
    r = mod.read_stream(jl(T_START, {"type": "turn.completed", "usage": dict(USAGE, output_tokens=0)}))
    if r["usage"] != dict(USAGE, output_tokens=0):
        out.append(f"{p}: a usage of 0 output tokens reads {r['usage']}")
    got = refusal(lambda: mod.read_stream(jl(T_START, DONE, DONE)), mod.StreamError)
    if got:
        out.append(f"{p}: two turn.completed records {got}")
    return out


@guarded("B6-empty", CA_API)
def b6_empty(mod, p):
    """W11A-R1-6: an empty or absent model and an empty line, at argv and at the adapter's making."""
    out = []
    for what, kw in (("model ''", {"line": "x", "model": ""}), ("model None", {"line": "x", "model": None}),
                     ("model 5", {"line": "x", "model": 5}), ("line 5", {"line": 5, "model": MODEL}),
                     ("line ''", {"line": "", "model": MODEL}), ("line None", {"line": None, "model": MODEL})):
        got = refusal(lambda: mod.argv(kw["line"], model=kw["model"], mode=MODE, session_id=TID, first=True),
                      mod.StreamError)
        if got:
            out.append(f"{p}: argv with {what} {got}")
    got = refusal(lambda: mod.argv("x", model=MODEL, mode="default", session_id=TID, first=True), mod.StreamError)
    if got:
        out.append(f"{p}: argv with an unknown mode {got}")
    for bad in ("", None, 5):
        got = refusal(lambda: mod.CodexAdapter(runtime=FakeRuntime([]), take_id=TAKE, run_tree=str(SCRATCH),
                                               login_file="x", model=bad, pin={"permission_mode": MODE},
                                               stream_path_for=str, rollout_for=str, counters_for=dict, clock=float),
                      mod.StreamError)
        if got:
            out.append(f"{p}: an adapter for model {bad!r} {got}")
    for what, kw in (("stream_path_for", "stream_path_for"), ("rollout_for", "rollout_for"),
                     ("counters_for", "counters_for"), ("clock", "clock")):
        args = dict(stream_path_for=str, rollout_for=str, counters_for=dict, clock=float)
        args[kw] = "not callable"
        got = refusal(lambda: mod.CodexAdapter(runtime=FakeRuntime([]), take_id=TAKE, run_tree=str(SCRATCH),
                                               login_file="x", model=MODEL, pin={"permission_mode": MODE}, **args),
                      TypeError)
        if got:
            out.append(f"{p}: an adapter whose {what} is not callable {got}")
    got = refusal(lambda: mod.CodexAdapter(runtime=FakeRuntime([]), take_id=TAKE, run_tree=str(SCRATCH),
                                           login_file="x", model=MODEL, pin="bypass", stream_path_for=str,
                                           rollout_for=str, counters_for=dict, clock=float), rt.NotReady)
    if got:
        out.append(f"{p}: a pin that is not an object {got}")
    return out


@guarded("B7-blank", CA_API)
def b7_blank(mod, p):
    """W11A-R1-7: a blank agent_message is not output; each output item type alone is."""
    out = []
    for text in ("", "   ", "\n\t"):
        r = mod.read_stream(jl(T_START, say(text), DONE))
        if r["agent_output"] is not False:
            out.append(f"{p}: an agent_message of {text!r} was read as output")
    singles = (("command_execution", {"type": "item.completed", "item": {"id": "c1", "type": "command_execution",
                                                                         "command": "ls"}}),
               ("file_change", {"type": "item.completed", "item": {"id": "f1", "type": "file_change",
                                                                   "changes": [{"path": "a", "kind": "add"}]}}),
               ("mcp_tool_call", {"type": "item.completed", "item": {"id": "x1", "type": "mcp_tool_call",
                                                                     "server": "s", "tool": "t"}}),
               ("agent_message", say("words")))
    for what, rec in singles:
        r = mod.read_stream(jl(T_START, rec, DONE))
        if r["agent_output"] is not True:
            out.append(f"{p}: a completed {what} alone was not read as output")
        want = [] if what == "agent_message" else [rec["item"]["id"]]
        if r["tool_ids"] != want:
            out.append(f"{p}: a completed {what} gives tool ids {r['tool_ids']}")
    # Pre-freeze review 2, m7 (lane fold2/la2): a call the agent started is its output, though it never completed;
    # it is still no completed tool id.
    started = {"type": "item.started", "item": {"id": "c1", "type": "command_execution", "command": "ls"}}
    r = mod.read_stream(jl(T_START, started, DONE))
    if r["agent_output"] is not True or r["tool_ids"]:
        out.append(f"{p}: a call started and never completed reads output {r['agent_output']}, ids {r['tool_ids']}")
    r = mod.read_stream(jl(T_START, say("a"), say("", "m2"), say("b", "m3"), DONE))
    if r["agent_text"] != "a\nb":
        out.append(f"{p}: the agent's texts join as {r['agent_text']!r}")
    return out


@guarded("B10-cut", CA_API)
def b10_cut(mod, p):
    """W11A-R1-10: a line that is not JSON is accepted only as a cut stream's last line, and counted."""
    out = []
    r = mod.read_stream(jl(T_START, TURN_START, say("x"), '{"type": "turn.compl'))
    if r["undecoded"] != 1 or r["agent_text"] != "x":
        out.append(f"{p}: a cut last line reads undecoded {r['undecoded']}")
    r = mod.read_stream(jl(T_START, TURN_START, say("x"), '{"type": "turn.compl', ""))
    if r["undecoded"] != 1:
        out.append(f"{p}: a cut last line before a blank line reads undecoded {r['undecoded']}")
    for what, text in (("a first line", jl("garbage", T_START, TURN_START)),
                       ("a middle line", jl(T_START, "garbage", TURN_START)),
                       ("two last lines", jl(T_START, TURN_START, "garbage", "more garbage"))):
        got = refusal(lambda: mod.read_stream(text), mod.StreamError)
        if got:
            out.append(f"{p}: a line that is not JSON as {what} {got}")
    r = mod.read_stream("")
    if r["undecoded"] != 0 or r["usage"] is not None or r["agent_output"]:
        out.append(f"{p}: an empty stream reads {r}")
    return out


@guarded("B9-record", CA_API)
def b9_record(mod, p):
    """The turn record and the TurnResult, field by field, for one clean turn and one failed turn."""
    out = []
    a, box = take_with(mod, [fixture("turn1-tools.jsonl"), fixture("turn-failed.jsonl")], exit_codes=[0, 1])
    t1 = a.turn("one", first=True, budget_s=60)
    t2 = a.turn("two", first=False, budget_s=60)
    want = [{"n": 1, "first": True, "exit_code": 0, "timed_out": False, "thread_ids": [TID], "usage": USAGE,
             "tool_ids": ["item_1", "item_2"], "completed": 1, "failed": 0, "undecoded": 0, "why_no_init": None,
             "shapes_source": mod.SHAPES_SOURCE,
             "requested_context": {"model": MODEL, "permission_mode": "never", "version": VERSION},
             "served_model": None},
            {"n": 2, "first": False, "exit_code": 1, "timed_out": False, "thread_ids": [TID], "usage": None,
             "tool_ids": [], "completed": 0, "failed": 1, "undecoded": 0,
             "why_no_init": a.turn_records[1]["why_no_init"], "shapes_source": mod.SHAPES_SOURCE,
             "requested_context": None, "served_model": None}]
    if a.turn_records != want or not a.turn_records[1]["why_no_init"]:
        out.append(f"{p}: the turn records read {a.turn_records}")
    if (t1.text, t1.exit_code, t1.started_at, t1.ended_at) != ("Synthetic reply one.", 0, 101.0, 102.0):
        out.append(f"{p}: turn 1's result reads {(t1.text, t1.exit_code, t1.started_at, t1.ended_at)}")
    if not (t1.stream_path.endswith("turn-1.jsonl") and t2.stream_path.endswith("turn-2.jsonl")):
        out.append(f"{p}: the stream paths are {t1.stream_path}, {t2.stream_path}")
    if Path(t1.stream_path).read_text(encoding="utf-8") != fixture("turn1-tools.jsonl"):
        out.append(f"{p}: turn 1's stream file is not the exec's stdout")
    if (t2.text, t2.agent_output, len(t2.api_errors), t2.init) != ("", False, 2, None):
        out.append(f"{p}: turn 2's result reads {(t2.text, t2.agent_output, t2.api_errors, t2.init)}")
    cut = jl(T_START, TURN_START, say("x")) + '{"type": "turn.compl\udcff'
    a2, _ = take_with(mod, [cut])
    t = a2.turn("one", first=True, budget_s=60)
    if a2.turn_records[0]["undecoded"] != 1 or "\udcff" not in Path(t.stream_path).read_text(
            encoding="utf-8", errors="surrogateescape"):
        out.append(f"{p}: a cut last line holding an undecodable byte reads {a2.turn_records[0]['undecoded']}")
    if a._start({"row_id": 1}) != {"container_id": TAKE} or a.end_take() is not None:
        out.append(f"{p}: the take's start or end is off")
    return out


@guarded("B11-version", CA_API)
def b11_version(mod, p):
    """The version exec: its exit code and its form are read, and it runs once per adapter."""
    out = []
    box = FakeRuntime([])
    a = adapter(mod, box)
    if (a.version(), a.version()) != (VERSION, VERSION) or len(box.calls) != 1:
        out.append(f"{p}: two version reads made {len(box.calls)} exec(s)")
    if box.calls and box.calls[0][-2:] != ["codex", "--version"]:
        out.append(f"{p}: the version exec is {box.calls[0]}")
    if mod.CodexAdapter.name != rt.CODEX or mod.NAME != "codex":
        out.append(f"{p}: the adapter is named {mod.CodexAdapter.name!r}")
    for what, kw in (("exit 1", {"version_code": 1}), ("a trailing word", {"version_out": f"codex-cli {VERSION} x"}),
                     ("another client", {"version_out": f"claude {VERSION}"}), ("no stdout", {"version_out": None})):
        got = refusal(lambda: adapter(mod, FakeRuntime([], **kw)).version(), rt.NotReady)
        if got:
            out.append(f"{p}: a version exec with {what} {got}")
    return out


@guarded("B12-executed", CA_API + ("ExecutedStreamRefused",))
def b12_executed(mod, p):
    """Live harness slice 6 (integration sweep survivors): an exec that ran is kept before its stream is read; a clean
    turn's record says refused None; a reader refusal is ExecutedStreamRefused and a defect a plain
    ExecutedTurnRefused, each carrying the kept record with its refusal "<type>: <words>"."""
    out = []
    keys = {"n", "exit_code", "timed_out", "started_at", "ended_at", "stream_path", "counters", "refused"}
    a, _ = take_with(mod, [fixture("turn1-tools.jsonl")])
    a.turn("first line", first=True, budget_s=60)
    if len(a.executed_turns) != 1 or set(a.executed_turns[0]) != keys or a.executed_turns[0]["refused"] is not None:
        out.append(f"{p}: a clean turn's kept exec record is {a.executed_turns}")
    a, _ = take_with(mod, [fixture("unknown-event.jsonl")])
    try:
        a.turn("first line", first=True, budget_s=60)
        out.append(f"{p}: a stream off the tables was not refused")
    except mod.ExecutedStreamRefused as e:
        cause = e.__cause__
        rec = a.executed_turns[-1] if a.executed_turns else {}
        if len(a.executed_turns) != 1 or e.executed != rec or set(rec) != keys or \
                rec.get("refused") != f"{type(cause).__name__}: {cause}":
            out.append(f"{p}: the reader refusal is kept as {a.executed_turns}")
    a, _ = take_with(mod, [fixture("turn1-tools.jsonl")])

    def defect(got, n, first):
        raise RuntimeError("a stand-in defect")
    a._read_turn = defect
    try:
        a.turn("first line", first=True, budget_s=60)
        out.append(f"{p}: a defect after the exec was not refused")
    except mod.StreamError:
        out.append(f"{p}: a defect after the exec was read as a stream refusal")
    except mod.aa.ExecutedTurnRefused as e:
        rec = a.executed_turns[-1] if a.executed_turns else {}
        if e.executed != rec or rec.get("refused") != "RuntimeError: a stand-in defect" or set(rec) != keys:
            out.append(f"{p}: the defect is kept as {rec}")
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


@guarded("B13-native", CA_API + ("ExecutedStreamRefused",))
def b13_native(mod, p):
    """Codex slice 3: the rollout this take resumes is the one under CODEX_HOME named by turn 1's thread id."""
    out = []
    a, _ = take_with(mod, [fixture("turn1-tools.jsonl")])
    a.turn("first line", first=True, budget_s=60)
    home = Path(tempfile.mkdtemp(dir=SCRATCH))
    folder = home / "sessions" / "2026" / "10" / "14"
    folder.mkdir(parents=True)
    want = folder / f"rollout-2026-10-14T05-00-00-{TID}.jsonl"
    want.write_text('{"this": "take"}\n')
    (folder / "rollout-2026-10-14T05-00-00-another-thread.jsonl").write_text("{}\n")
    if a.native_session_path(str(home)) != str(want):
        out.append(f"{p}: the rollout located is not {want.name}")
    # Drive-wiring review MAJOR 1's road (athena sweep, 14 Oct: native_session_rel's import and return deleted
    # survived): the same rollout through the box's listing, as the path relative to CODEX_HOME, and that path read
    # through the box gives this take's rollout.
    lister, reader = box_view(home)
    rel = a.native_session_rel(lister)
    if rel != f"sessions/2026/10/14/{want.name}":
        out.append(f"{p}: the rollout located through the box's listing is {rel!r}")
    elif reader(rel) != want.read_bytes():
        out.append(f"{p}: the located rollout does not read as this take's")
    return out


# Lane vendor-b23 round 4 (glitch-26's ruling B23-8; athena battery gap4-t5-b23-a67b2b7, w11a-codex-adapter.txt:9):
# B22's started file_change (check_record's started status, the items branch, CodexParser._file_change_started) and
# B23's pairing in CodexParser._file_change, bound here so the generated sweep kills their mutants by these checks' own
# lines. Every record is synthetic, in the keys transcript_codex.py's table admits for a file_change.
FC_ID = "item_7"
FC_CHANGES = ({"path": "notes/a.txt", "kind": "add"}, {"path": "src/b.py", "kind": "update"})


def fc(event, status, changes=FC_CHANGES, i=FC_ID) -> str:
    return json.dumps({"type": event, "item": {"id": i, "type": "file_change", "changes": [dict(c) for c in changes],
                                                "status": status}})


def fc_items(mod, recs) -> list:
    """Each record's items through one parser, a list per record; a refusal reads as ("refused", its type name)."""
    parser, out = mod.CodexParser(), []
    for rec in recs:
        try:
            out.append(parser.items(rec if isinstance(rec, str) else json.dumps(rec)))
        except Exception as e:  # noqa: BLE001 - read by the check as what the parser did instead
            out.append(("refused", type(e).__name__))
            break
    return out


def fc_want(event, kind, text=None, i=FC_ID, changes=FC_CHANGES) -> list:
    tools = {"add": tv.WRITE, "update": tv.EDIT}
    if kind == tv.TOOL_CALL:
        return [tv.RawItem(f"{event}:file_change", tv.TOOL_CALL, tool=tools[c["kind"]], args={"path": c["path"]},
                           ref=f"{i}#{n}") for n, c in enumerate(changes)]
    return [tv.RawItem(f"{event}:file_change", tv.TOOL_RESULT, text=text, ref=f"{i}#{n}") for n in range(len(changes))]


def fc_unpaired(items):
    """A completion read with no start, without its refs' spelling (the joiner there is EQUIVALENT below, W11A's entry:
    no logic reads it): (its items with no ref, whether each result's ref is its call's and each call's is its own)."""
    if not isinstance(items, list) or not all(isinstance(it, tv.RawItem) for it in items):
        return items
    refs = [it.ref for it in items]
    own = (len(refs) % 2 == 0 and all(isinstance(r, str) for r in refs) and refs[0::2] == refs[1::2]
           and len(set(refs[0::2])) == len(refs) // 2)
    return [tv.RawItem(it.raw_type, it.kind, it.text, it.tool, it.args, None) for it in items], own


@guarded("B15-fc-pair", TC_API)
def b15_fc_pair(mod, p):
    """A started file_change is one call per change (its tool by kind, its path, the ref `<id>#<n>`), and its
    completion is one result per change, under the same refs, with the completion's own status as the text; through
    transcript_view.events each result answers its call. A started status other than in_progress is refused."""
    out = []
    started = fc("item.started", "in_progress")
    try:
        mod.decode(started)
    except Exception as e:  # noqa: BLE001
        out.append(f"{p}: the record check refused a started file_change ({type(e).__name__})")
    for status in ("completed", "failed"):
        got = fc_items(mod, [T_START, started, fc("item.completed", status)])
        want = [fc_want("item.started", tv.TOOL_CALL), fc_want("item.completed", tv.TOOL_RESULT, status)]
        if got[1:] != want:
            out.append(f"{p}: a start paired with its {status} completion reads {got}")
    try:
        with mock.patch.dict(tv.PARSERS, {"codex": mod.CodexParser()}):
            evs = tv.events("codex", [json.dumps(T_START), started, fc("item.completed", "completed"),
                                      json.dumps(DONE)])
        got = [(e.kind, e.tool, e.args, e.text, e.call) for e in evs]
    except Exception as e:  # noqa: BLE001
        got = f"refused ({type(e).__name__}: {str(e)[:120]})"
    want = [(tv.TOOL_CALL, tv.WRITE, {"path": "notes/a.txt"}, None, 1),
            (tv.TOOL_CALL, tv.EDIT, {"path": "src/b.py"}, None, 2),
            (tv.TOOL_RESULT, tv.WRITE, None, "completed", 1), (tv.TOOL_RESULT, tv.EDIT, None, "completed", 2)]
    if not isinstance(got, list) or got[1:5] != want:
        out.append(f"{p}: the view reads the pair as {got}")
    for status in ("completed", "failed", None):
        rec = json.loads(started)
        if status is None:
            del rec["item"]["status"]
        else:
            rec["item"]["status"] = status
        got = refusal(lambda: mod.check_record(rec), mod.ShapeError)
        if got:
            out.append(f"{p}: a started file_change with status {status!r}: the record check {got}")
        if fc_items(mod, [rec]) != [("refused", "ShapeError")]:
            out.append(f"{p}: a started file_change with status {status!r}: the parser reads {fc_items(mod, [rec])}")
    return out


@guarded("B16-fc-second-start", TC_API)
def b16_fc_second_start(mod, p):
    """A second item.started for one file_change id in one stream is refused; a thread.started begins a new stream,
    whose ids are new (one parser reads a take's streams one after another)."""
    out = []
    started = fc("item.started", "in_progress")
    got = fc_items(mod, [T_START, started, started])
    if got[-1:] != [("refused", "ShapeError")] or len(got) != 3:
        out.append(f"{p}: a second start of {FC_ID} in one stream reads {got}")
    other = fc("item.started", "in_progress", i="item_8")
    got = fc_items(mod, [T_START, started, other, fc("item.completed", "completed", i="item_8")])
    if got[1:] != [fc_want("item.started", tv.TOOL_CALL), fc_want("item.started", tv.TOOL_CALL, i="item_8"),
                   fc_want("item.completed", tv.TOOL_RESULT, "completed", i="item_8")]:
        out.append(f"{p}: two ids started in one stream read {got[1:]}")
    done = fc("item.completed", "completed")
    got = fc_items(mod, [T_START, started, T_START, started, done])
    if got[3:] != [fc_want("item.started", tv.TOOL_CALL), fc_want("item.completed", tv.TOOL_RESULT, "completed")]:
        out.append(f"{p}: a start of {FC_ID} again after thread.started reads {got[3:]}")
    got = fc_items(mod, [T_START, started, T_START, done])
    call, res = fc_want("item.completed", tv.TOOL_CALL), fc_want("item.completed", tv.TOOL_RESULT, "completed")
    if len(got) != 4 or fc_unpaired(got[3]) != fc_unpaired([call[0], res[0], call[1], res[1]]):
        out.append(f"{p}: a completion in the next stream, its start in the last, reads {got[3:]}")
    return out


@guarded("B17-fc-changed", TC_API)
def b17_fc_changed(mod, p):
    """A completion whose changes are not its start's (another path, another kind, one more, one fewer, another
    order) is refused; with no start, a completion is its own calls and results."""
    out = []
    a, b = FC_CHANGES
    for what, changes in (("another path", ({"path": "notes/c.txt", "kind": "add"}, b)),
                          ("another kind", ({"path": a["path"], "kind": "update"}, b)),
                          ("one more", (a, b, {"path": "src/c.py", "kind": "add"})), ("one fewer", (a,)),
                          ("another order", (b, a))):
        got = fc_items(mod, [T_START, fc("item.started", "in_progress"), fc("item.completed", "completed", changes)])
        if got[2:] != [("refused", "ShapeError")]:
            out.append(f"{p}: a completion with {what} than its start reads {got[2:]}")
    got = fc_items(mod, [T_START, fc("item.completed", "failed")])
    call, res = fc_want("item.completed", tv.TOOL_CALL), fc_want("item.completed", tv.TOOL_RESULT, "failed")
    if len(got) != 2 or fc_unpaired(got[1]) != fc_unpaired([call[0], res[0], call[1], res[1]]):
        out.append(f"{p}: a completion with no start reads {got[1:]}")
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

    def test_b3_a_dropped_required_key_is_refused(self):
        self.assertEqual(b3_required(tc), [])

    def test_b8_a_value_off_its_type_is_refused(self):
        self.assertEqual(b8_types(tc), [])

    def test_b15_a_started_file_change_pairs_with_its_completion(self):
        self.assertEqual(b15_fc_pair(tc), [])

    def test_b16_a_second_start_is_refused_and_each_stream_starts_again(self):
        self.assertEqual(b16_fc_second_start(tc), [])

    def test_b17_a_completion_off_its_start_is_refused(self):
        self.assertEqual(b17_fc_changed(tc), [])

    def test_the_usage_keys_are_d8s_and_the_pinned_structs(self):
        self.assertEqual(tuple(getattr(tc, "USAGE_KEYS", ())), PINNED_USAGE)
        self.assertEqual(tuple(k for k in PINNED_USAGE if k in D8_USAGE), D8_USAGE)


class TestTheAdapter(unittest.TestCase):
    def test_every_turn_here_runs_through_the_login_free_stub(self):
        """glitch-06's Codex ruling (a): the stub is in place, and a turn through it never opens the login file."""
        self.assertIs(rt.run_turn, stub_run_turn)
        box = FakeRuntime([fixture("turn1-tools.jsonl")])
        a = adapter(ca, box, rollouts=[fixture("rollout-two-turns.jsonl")])
        a.login_file = str(SCRATCH / "no-such-login-file")      # a read would raise; the stub never reads it
        a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
        a.turn("first line", first=True, budget_s=60)
        self.assertFalse(any(LOGIN in x or LOGIN_VALUE in x for c in box.calls for x in c))

    def test_a1_the_stream_read(self):
        self.assertEqual(a1_stream(ca), [])

    def test_the_turns_stderr_is_kept(self):
        """glitch-b5's ruling on R15-2 (16 Oct 2026): the driver reads each turn's stderr for EROFS lines."""
        self.assertEqual(a_stderr(ca), [])

    def test_a2_the_agents_text_is_never_an_api_error(self):
        self.assertEqual(a2_error(ca), [])

    def test_a3_a_missing_usage_field_is_refused(self):
        self.assertEqual(a3_usage(ca), [])

    def test_a4_the_turn_argv(self):
        self.assertEqual(a4_argv(ca), [])

    def test_a4_a_first_line_resume_is_refused(self):
        self.assertEqual(a4_word(ca, "resume"), [])

    def test_a4_a_first_line_fork_is_refused(self):
        self.assertEqual(a4_word(ca, "fork"), [])

    def test_a4_a_first_line_review_is_refused(self):
        self.assertEqual(a4_word(ca, "review"), [])

    def test_a4_a_first_line_help_is_refused(self):
        self.assertEqual(a4_word(ca, "help"), [])

    def test_a4_the_commands_are_the_pinned_helps(self):
        """The adapter's list is the pinned help's, and run_take's wherever the box has landed it: they cannot drift.
        Both ways on every tree (review of 83b83ea1, NIT 1): the binding reads run_take's list whenever one is there, so
        a run_take holding another list is caught here even on a tree without the box's (box 14670435)."""
        self.assertEqual(getattr(ca, "CODEX_EXEC_COMMANDS", None), EXEC_COMMANDS)
        self.assertEqual(help_binding_problems(ca.CODEX_EXEC_COMMANDS, rt), [])
        with mock.patch.object(rt, "CODEX_HELP_COMMANDS", ("resume", "fork", "review"), create=True):
            self.assertTrue(help_binding_problems(ca.CODEX_EXEC_COMMANDS, rt),
                            "A4-help: a run_take list that drifted from the adapter's was not caught")
        if hasattr(rt, "CODEX_HELP_COMMANDS"):         # the box's own list, compared directly where it is on the tree
            self.assertEqual(tuple(rt.CODEX_HELP_COMMANDS), ca.CODEX_EXEC_COMMANDS)

    def test_a5_the_served_model_is_only_a_reroutes(self):
        self.assertEqual(a5_model(ca), [])

    def test_a8_the_mode_is_read_from_the_turns_journal(self):
        self.assertEqual(a8_journal(ca), [])

    def test_a6_a_turn_on_the_fake_runtime(self):
        self.assertEqual(a6_turn(ca), [])

    def test_a7_the_shapes_source_is_recorded(self):
        # lane vendor-settle stage V: the RECORDED w-o46 and w-o47 copies are labelled with their walk and CLI version,
        # so the source reads "recorded" (R-recorded below binds the copies and reads them)
        self.assertEqual(ca.SHAPES_SOURCE, "recorded")
        self.assertEqual(a7_source(ca), [])

    def test_b1_each_end_reason_condition(self):
        self.assertEqual(b1_end(ca), [])

    def test_b2_the_thread_id_at_every_seat(self):
        self.assertEqual(b2_thread(ca), [])

    def test_b3_a_dropped_required_key_is_refused_on_the_adapters_road(self):
        self.assertEqual(b3_stream(ca), [])

    def test_b4_the_rollout_init_guards(self):
        self.assertEqual(b4_rollout(ca), [])

    def test_b5_usage_values_and_two_completions(self):
        self.assertEqual(b5_usage(ca), [])

    def test_b6_an_empty_model_or_line(self):
        self.assertEqual(b6_empty(ca), [])

    def test_b7_a_blank_message_is_not_output(self):
        self.assertEqual(b7_blank(ca), [])

    def test_b9_the_turn_record_field_by_field(self):
        self.assertEqual(b9_record(ca), [])

    def test_b11_the_version_exec(self):
        self.assertEqual(b11_version(ca), [])

    def test_b12_an_executed_turn_is_kept_before_its_refusal(self):
        self.assertEqual(b12_executed(ca), [])

    def test_b13_the_rollout_is_located_by_turn_ones_thread(self):
        self.assertEqual(b13_native(ca), [])

    def test_b14_each_turn_hands_run_turn_its_config_folder_and_number(self):
        """B11 (lane vendor-b11 round 3, R-CF): the adapter's config_folder record and each turn's number reach
        run_take.run_turn (the stub records what it was handed; run_turn's own check is tests/test_config_folder.py)."""
        record, folder, two = object(), Path(tempfile.mkdtemp(dir=SCRATCH)), fixture("rollout-two-turns.jsonl")
        a = ca.CodexAdapter(runtime=FakeRuntime([fixture("turn1-tools.jsonl"), fixture("turn1-tools.jsonl")]),
                            take_id=TAKE, run_tree=str(SCRATCH / "tree"), login_file=login_file(), model=MODEL,
                            pin={"permission_mode": MODE, "version": VERSION},
                            stream_path_for=lambda n: str(folder / f"turn-{n}.jsonl"), rollout_for=lambda n: two,
                            counters_for=Counters(), clock=Clock(), config_folder=record)
        a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
        STUB_CONFIG.clear()
        a.turn("one", first=True, budget_s=60)
        try:
            a.turn("two", first=False, budget_s=60)
        except Exception:  # noqa: BLE001 - only what reached run_turn is read here
            pass
        self.assertEqual([(c["folder"] is record, c["turn"]) for c in STUB_CONFIG], [(True, 1), (True, 2)],
                         "R-CF.adapter: the turns did not hand run_turn the take's config folder and their numbers")

    def test_b14_the_read_shapes_are_the_pinned_records(self):
        self.assertEqual(b14_read_shapes(ca), [])

    def test_b10_a_cut_line_only_last(self):
        self.assertEqual(b10_cut(ca), [])

    def test_a7_a_recorded_label_needs_its_provenance(self):
        files = ["x.jsonl", "y.jsonl"]
        bare = {"x.jsonl": ("RECORDED", ""), "y.jsonl": ("RECORDED", " at walk w-1.")}
        problems, recorded = label_problems(bare, files)
        self.assertEqual(recorded, [])
        self.assertTrue(any("without the walk id and harness version" in x for x in problems), problems)
        full = {"x.jsonl": ("RECORDED", " at walk w-1, codex-cli 0.160.1."), "y.jsonl": ("SYNTHETIC",
                                                                                         SYNTHETIC_LABEL[9:])}
        self.assertEqual(label_problems(full, files), ([], ["x.jsonl"]))

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
    "unknown-event-accepted": ("tc", (("    if not isinstance(t, str) or t not in EVENT_KEYS:\n        raise ShapeError("
                                       "f\"unknown event type: {t!r}\")\n    _keys(f\"event {t}\", rec, *EVENT_KEYS[t])\n",
                                       "    if t in EVENT_KEYS:\n        _keys(f\"event {t}\", rec, *EVENT_KEYS[t])\n"),),
                               s1_event, "S1-event"),
    "unknown-item-accepted": ("tc", (("    if not isinstance(it, str) or it not in ITEM_KEYS:\n        raise ShapeError("
                                      "f\"unknown item type: {it!r}\")\n    _keys(f\"item {it}\", item, *ITEM_KEYS[it])\n",
                                      "    if it in ITEM_KEYS:\n        _keys(f\"item {it}\", item, *ITEM_KEYS[it])\n"),),
                              s2_item, "S2-item"),
    "unknown-key-accepted": ("tc", (("    unknown = sorted(set(rec) - set(allowed))\n", "    unknown = []\n"),),
                             s3_key, "S3-key"),
    "reasoning-as-text": ("tc", (("return [tv.RawItem(raw, tv.AGENT_REASONING,", "return [tv.RawItem(raw, tv.AGENT_TEXT,"),),
                          p1_view, "P1-view"),
    # Lane pf1-codex-fcdelete: delete is a write of its path; any other kind still refuses.
    "delete-hidden": ("tc", (("CHANGE_KINDS = {\"add\": tv.WRITE, \"update\": tv.EDIT, \"delete\": tv.WRITE}",
                              "CHANGE_KINDS = {\"add\": tv.WRITE, \"update\": tv.EDIT, \"delete\": tv.READ}"),),
                      p1_view, "P1-view"),
    "unknown-kind-admitted": ("tc", (("CHANGE_KINDS = {\"add\": tv.WRITE, \"update\": tv.EDIT, \"delete\": tv.WRITE}",
                                      "CHANGE_KINDS = {\"add\": tv.WRITE, \"update\": tv.EDIT, \"delete\": tv.WRITE, "
                                      "\"rename\": tv.WRITE}"),),
                              p1_view, "P1-view"),
    # Lane vendor-b23 round 4 (ruling B23-8): the started file_change and its pairing, one witness per check.
    "started-file-change-unpaired": ("tc", (("                return self._file_change_started(item, raw)\n",
                                             "                return []\n"),), b15_fc_pair, "B15-fc-pair"),
    "paired-result-text-dropped": ("tc", (("TOOL_RESULT, text=item.get(\"status\"), ref=f\"{item['id']}#{i}\")\n"
                                           "                    for i in range(len(changes))]",
                                           "TOOL_RESULT, text=None, ref=f\"{item['id']}#{i}\")\n"
                                           "                    for i in range(len(changes))]"),), b15_fc_pair,
                                   "B15-fc-pair"),
    "file-change-second-start-admitted": ("tc", (("        if item[\"id\"] in self._started:\n",
                                                  "        if False:\n"),), b16_fc_second_start,
                                          "B16-fc-second-start"),
    "file-change-changed-admitted": ("tc", (("            if started != changes:\n", "            if False:\n"),),
                                     b17_fc_changed, "B17-fc-changed"),
    # codex_adapter.py
    "agent-text-as-error": ("ca", (("        if t == tc.ERROR:\n            api.append({\"status\": None, \"type\": t, "
                                    "\"text\": rec[\"message\"]})\n",
                                    "        if t == tc.ERROR or it == tc.AGENT_MESSAGE:\n            api.append({"
                                    "\"status\": None, \"type\": t, \"text\": rec.get(\"message\")})\n"),), a2_error,
                            "A2-error"),
    "usage-zero": ("ca", (("vals = {k: rec[\"usage\"].get(k) for k in tc.USAGE_KEYS}",
                           "vals = {k: rec[\"usage\"].get(k, 0) for k in tc.USAGE_KEYS}"),), a3_usage, "A3-usage"),
    "resume-first": ("ca", (("    if not first:\n        if not isinstance(session_id",
                             "    if True:\n        if not isinstance(session_id"),), a4_argv, "A4-argv"),
    "subcommand-word-admitted": ("ca", (("    if first and line in CODEX_EXEC_COMMANDS:", "    if False:"),),
                                 a4_argv, "A4-argv"),
    "model-first-only": ("ca", (("    out = [CLIENT, SUBCOMMAND, JSON_FLAG, MODEL_FLAG, model, *MODE_FLAGS[mode]]",
                                 "    out = [CLIENT, SUBCOMMAND, JSON_FLAG, *MODE_FLAGS[mode]] + "
                                 "([MODEL_FLAG, model] if first else [])"),), a4_argv, "A4-argv"),
    # Codex slice 2: the requested model standing as init (the rollout's turn_context read as proof)
    "model-defaulted": ("ca", (("end_reason(got[\"exit_code\"], got[\"timed_out\"], read), init=None,",
                                "end_reason(got[\"exit_code\"], got[\"timed_out\"], read), init=init,"),),
                        a5_model, "A5-model"),
    "reroute-unread": ("ca", (("        if to_model is not None:", "        if False:"),), a5_model, "A5-model"),
    "requested-model-as-served": ("ca", (("    model = ({\"value\": read[\"served_model\"], \"source\": \"stream-reroute\"}"
                                          " if read[\"served_model\"] is not None",
                                          "    model = ({\"value\": read[\"served_model\"] or \"gpt-6-luna\", "
                                          "\"source\": \"stream-reroute\"} if True"),), a5_model, "A5-model"),
    "failed-as-end-turn": ("ca", (("    if exit_code == 0 and read[\"completed\"] == 1 and read[\"failed\"] == 0:",
                                   "    if exit_code == 0:"),), a6_turn, "A6-turn"),
    "other-thread-resumed": ("ca", (("        elif read[\"thread_ids\"] and read[\"thread_ids\"] != [self.thread_id]:",
                                     "        elif False:"),), a6_turn, "A6-turn"),
    # lane vendor-settle stage V (design section 5, review finding 10): the source reads "recorded", so the witness
    # moves to the new anchor as "shapes-off-word", red on A7's two-words check
    "shapes-off-word": ("ca", (("SHAPES_SOURCE = \"recorded\"\n", "SHAPES_SOURCE = \"observed\"\n"),), a7_source,
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

    def test_witness_delete_hidden(self):
        self.kill("delete-hidden")

    def test_witness_unknown_kind_admitted(self):
        self.kill("unknown-kind-admitted")

    def test_witness_started_file_change_unpaired(self):
        self.kill("started-file-change-unpaired")

    def test_witness_paired_result_text_dropped(self):
        self.kill("paired-result-text-dropped")

    def test_witness_file_change_second_start_admitted(self):
        self.kill("file-change-second-start-admitted")

    def test_witness_file_change_changed_admitted(self):
        self.kill("file-change-changed-admitted")

    def test_witness_agent_text_as_error(self):
        self.kill("agent-text-as-error")

    def test_witness_usage_zero(self):
        self.kill("usage-zero")

    def test_witness_resume_first(self):
        self.kill("resume-first")

    def test_witness_model_first_only(self):
        self.kill("model-first-only")

    def test_witness_subcommand_word_admitted(self):
        self.kill("subcommand-word-admitted")

    def test_witness_model_defaulted(self):
        self.kill("model-defaulted")

    def test_witness_reroute_unread(self):
        self.kill("reroute-unread")

    def test_witness_requested_model_as_served(self):
        self.kill("requested-model-as-served")

    def test_witness_failed_as_end_turn(self):
        self.kill("failed-as-end-turn")

    def test_witness_other_thread_resumed(self):
        self.kill("other-thread-resumed")

    def test_witness_shapes_recorded(self):
        self.kill("shapes-off-word")

    def test_the_witnesses_are_named_and_each_anchor_occurs_once(self):
        # 16: + subcommand-word-admitted (the box Codex-exec review's MAJOR); 20: + B23-8's four file_change witnesses;
        # 21: pf1-codex-fcdelete replaces delete-as-write with delete-hidden and unknown-kind-admitted
        self.assertEqual(len(WITNESSES), 21)
        for name, (target, edits, _, _) in WITNESSES.items():
            path = Path(TARGETS[target]().__file__)
            self.assertTrue(path.is_file(), f"{name}: {path.name} does not exist")
            src = path.read_text(encoding="utf-8")
            for old, _ in edits:
                self.assertEqual(src.count(old), 1, f"{name}: its anchor occurs {src.count(old)} times")


# ------------------------------------------------------------------------------------------------ generated mutants
# Ruling w11a-R1-fold item 2: the class of guard, bound by a generated sweep (built from review round 1's harness).
# Every mutant of codex_adapter.py and transcript_codex.py below is compiled in memory (never written to disk) and run
# against every bound check of its file (a transcript_codex mutant also rebuilds codex_adapter on it, so the adapter's
# checks see it). Each must be killed (a check returns a line, or the module does not build), or be listed in
# EQUIVALENT with a reason a reader can check against the source; an EQUIVALENT entry that names no generated mutant,
# or whose mutant is killed, is stale and fails.
#
# The mutation kinds: `del` a statement replaced by `pass`; `true` and `false` an if/elif/while/conditional test
# forced; `drop<i>` one operand of an and/or dropped; `not` a `not` dropped; `neg<i>` one comparison negated
# (== and !=, in and not in, is and is not, < and >=, > and <=); `none` an assignment's value emptied to None;
# `str` a string literal changed.
#
# ONE RULE instead of entries: string literals inside a `raise` statement are not mutated. They are message strings,
# not asserted verbatim, and no logic reads them: every refusal is told apart by its exception type, never its words.
NEGATE = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot,
          ast.IsNot: ast.Is, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt}
@guarded("A-stderr", CA_API)
def a_stderr(mod, p):
    """glitch-b5's ruling on R15-2 (16 Oct 2026): each turn's stderr is kept on the adapter (stderr_seen), so the
    driver can name what a read-only root broke."""
    box = FakeRuntime([fixture("turn1-tools.jsonl")])
    a = adapter(mod, box, rollouts=[fixture("rollout-served-other.jsonl")])
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    real = box.run
    box.run = lambda *x, **k: (lambda c: rt.Completed(c.returncode, c.stdout, "EROFS-SENTINEL"))(real(*x, **k))
    a.turn("one", first=True, budget_s=60)
    out = [] if getattr(a, "stderr_seen", None) == ["EROFS-SENTINEL"] else [f"{p}: the turn's stderr is not kept"]
    quiet = adapter(mod, FakeRuntime([fixture("turn1-tools.jsonl")]), rollouts=[fixture("rollout-served-other.jsonl")])
    quiet.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    quiet.turn("one", first=True, budget_s=60)
    return out + ([] if getattr(quiet, "stderr_seen", None) == [""] else [f"{p}: an empty stderr is not kept as \"\""])


# Lane vendor-b17 round 2 (glitch-26's ruling B17-5, 19 Oct 2026): arm O's OD57 read shapes, pinned by their bytes so
# the generated sweep kills every mutant of them; what they admit and refuse is tests/test_scan_record.py's.
READ_SHAPES_SHA256 = "4dc0a95edf555f6454693dd5c7827407fd241dd64d2d013b5ce6cc3d59063759"   # B24 (-lc only; box/od57_shapes)


@guarded("B14-read-shapes", ("READ_SHAPES",))
def b14_read_shapes(mod, p):
    """The module's READ_SHAPES, as JSON with sorted keys, hash to the pinned bytes."""
    import hashlib
    got = hashlib.sha256(json.dumps(mod.READ_SHAPES, sort_keys=True).encode()).hexdigest()
    return [] if got == READ_SHAPES_SHA256 else [f"{p}: READ_SHAPES is not the pinned records ({got[:12]})"]


TC_CHECKS = (s1_event, s2_item, s3_key, p1_view, b3_required, b8_types, b15_fc_pair, b16_fc_second_start,
             b17_fc_changed)
CA_CHECKS = (a_stderr, a1_stream, a2_error, a3_usage, a4_argv, a5_model, a8_journal, a6_turn, a7_source, b1_end, b2_thread, b3_stream,
             b4_rollout, b5_usage, b6_empty, b7_blank, b9_record, b10_cut, b11_version, b12_executed, b13_native,
             b14_read_shapes)

_PREAMBLE = "the import preamble: this test puts the module folder on sys.path before it imports either module"
_LABEL = "a what-label passed to _keys or _types, which use it only in their refusal's words"
_REASON = ("why_no_init's words: a reason the turn record carries for a reader; no logic reads it, and B4 and B9 "
           "assert only that it is a non-empty string when init is None")
_SAME_NONE = "the attribute's starting value is None already: emptying it to None changes nothing"
# fold2/fix (battery gap4-fold2merge-889d6dd, w11a-codex-adapter.txt:9): fold2/la2's m7 branch in read_stream. Every
# record reaching it passed tc.check_record, which returns it None for an event that is not an item event and refuses
# an item.started whose item type is not in STARTED_ITEM_TYPES; the branch is reached only by turn.started and
# item.started (every other event type of EVENT_KEYS has its own branch above). So each operand alone decides as both do.
_M7_STARTED = ("check_record refuses an item.started of any other item type, and the only other event that reaches "
               "this elif, turn.started, carries it None; so `t == tc.ITEM_STARTED` alone and `it in "
               "tc.STARTED_ITEM_TYPES` alone are each true exactly when both are")
EQUIVALENT = {
    "ca drop0 read_stream: t == tc.ITEM_STARTED and it in tc.STARTED_ITEM_TYPES #1": _M7_STARTED,
    "ca drop1 read_stream: t == tc.ITEM_STARTED and it in tc.STARTED_ITEM_TYPES #1": _M7_STARTED,
    "tc del <module>: _HERE not in sys.path #1": _PREAMBLE,
    "tc del <module>: from __future__ import annotations #1": _PREAMBLE,
    "tc del <module>: sys.path.insert(0, _HERE) #1": _PREAMBLE,
    "tc false <module>: _HERE not in sys.path #1": _PREAMBLE,
    "tc neg0 <module>: _HERE not in sys.path #1": _PREAMBLE,
    "tc none <module>: _HERE = os.path.dirname(os.path.abspath(__file__)) #1": _PREAMBLE,
    "tc true <module>: _HERE not in sys.path #1": _PREAMBLE,
    "ca del <module>: _HERE not in sys.path #1": _PREAMBLE,
    "ca del <module>: from __future__ import annotations #1": _PREAMBLE,
    "ca del <module>: sys.path.insert(0, _HERE) #1": _PREAMBLE,
    "ca false <module>: _HERE not in sys.path #1": _PREAMBLE,
    "ca neg0 <module>: _HERE not in sys.path #1": _PREAMBLE,
    "ca none <module>: _HERE = os.path.dirname(os.path.abspath(__file__)) #1": _PREAMBLE,
    "ca true <module>: _HERE not in sys.path #1": _PREAMBLE,
    "tc str check_record: ' change' in check_record #1": _LABEL,
    "tc str check_record: ' change' in check_record #2": _LABEL,
    "tc str check_record: 'event ' in check_record #1": _LABEL,
    "tc str check_record: 'event ' in check_record #2": _LABEL,
    "tc str check_record: 'item ' in check_record #1": _LABEL,
    "tc str check_record: 'item ' in check_record #2": _LABEL,
    "tc str check_record: 'item ' in check_record #3": _LABEL,
    "tc str check_record: 'item ' in check_record #4": _LABEL,
    "tc str check_record: 'turn.failed.error' in check_record #1": _LABEL,
    "tc str check_record: 'turn.failed.error' in check_record #2": _LABEL,
    "tc str CodexParser._file_change: '#' in CodexParser._file_change #1": "the ref joiner: a ref is read only to pair a result with its call (transcript_view.events), and any spelling keeps each change's ref unique",
    "ca str CodexAdapter.__init__: 'clock' in CodexAdapter.__init__ #1": "a what-label used only in the TypeError's words for a callable that is not one",
    "ca str CodexAdapter.__init__: 'counters_for' in CodexAdapter.__init__ #1": "a what-label used only in the TypeError's words for a callable that is not one",
    "ca str CodexAdapter.__init__: 'rollout_for' in CodexAdapter.__init__ #1": "a what-label used only in the TypeError's words for a callable that is not one",
    "ca str CodexAdapter.__init__: 'stream_path_for' in CodexAdapter.__init__ #1": "a what-label used only in the TypeError's words for a callable that is not one",
    "ca str argv: 'line' in argv #1": "a what-label used only in the StreamError's words",
    "ca str argv: 'model' in argv #1": "a what-label used only in the StreamError's words",
    "ca str read_rollout: 'the rollout gained no turn_context during this turn' in read_rollout #1": _REASON,
    "ca str read_rollout: 'the turn_context or the one session_meta lacks a model, appr' in read_rollout #1": _REASON,
    "ca none CodexAdapter.__init__: self._version = None #1": _SAME_NONE,
    "ca none CodexAdapter.__init__: self.thread_id = None #1": _SAME_NONE,
    "ca none CodexAdapter.__init__: self._contexts = 0 #1": "read only as read_rollout's `seen`, a slice start: ctxs[None:] is ctxs[0:]",
}


def _parents(tree) -> dict:
    return {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}


def _docstring(node, parents) -> bool:
    par = parents.get(node)
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
            and isinstance(par, (ast.Module, ast.FunctionDef, ast.ClassDef)) and par.body[0] is node)


def _in(node, parents, kinds) -> bool:
    while node in parents:
        node = parents[node]
        if isinstance(node, kinds):
            return True
    return False


def _qual(node, parents) -> str:
    names = []
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.append(node.name)
    return ".".join(reversed(names)) or "<module>"


def mutant_sites(src: str) -> list:
    """[(key, kind, walk index, operand index)] in ast.walk order; the key is stable across line moves."""
    tree = ast.parse(src)
    parents = _parents(tree)
    raw = []
    for idx, node in enumerate(ast.walk(tree)):
        if _in(node, parents, ast.Raise) and isinstance(node, ast.Constant):
            continue
        seg = " ".join((ast.get_source_segment(src, node) or "").split())[:110]
        here = []
        if isinstance(node, ast.stmt) and not isinstance(node, ast.Pass) and not _docstring(node, parents) \
                and not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            here.append(("del", None))
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            here += [("true", None), ("false", None)]
            seg = " ".join((ast.get_source_segment(src, node.test) or "").split())[:110]
        if isinstance(node, ast.BoolOp):
            here += [(f"drop{i}", i) for i in range(len(node.values))]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            here.append(("not", None))
        if isinstance(node, ast.Compare):
            here += [(f"neg{i}", i) for i, op in enumerate(node.ops) if type(op) in NEGATE]
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            here.append(("none", None))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and not _docstring(parents.get(node),
                                                                                           parents):
            here.append(("str", None))
            seg = f"{node.value[:60]!r} in {_qual(node, parents)}"
        for kind, i in here:
            raw.append((f"{kind} {_qual(node, parents)}: {seg}", kind, idx, i))
    seen, out = {}, []
    for key, kind, idx, i in raw:
        seen[key] = seen.get(key, 0) + 1
        out.append((f"{key} #{seen[key]}", kind, idx, i))
    return out


def _mutate(src: str, kind: str, idx: int, i):
    tree = ast.parse(src)
    nodes = list(ast.walk(tree))
    node = nodes[idx]
    parents = _parents(tree)
    if kind == "del":
        par = parents[node]
        for field, value in ast.iter_fields(par):
            if isinstance(value, list) and any(v is node for v in value):
                value[[j for j, v in enumerate(value) if v is node][0]] = ast.Pass()
    elif kind in ("true", "false"):
        node.test = ast.Constant(kind == "true")
    elif kind.startswith("drop"):
        rest = node.values[:i] + node.values[i + 1:]
        if len(rest) == 1:
            _replace(parents, node, rest[0])
        else:
            node.values = rest
    elif kind == "not":
        _replace(parents, node, node.operand)
    elif kind.startswith("neg"):
        node.ops[i] = NEGATE[type(node.ops[i])]()
    elif kind == "none":
        node.value = ast.Constant(None)
    elif kind == "str":
        node.value = node.value + "X"
    return ast.fix_missing_locations(tree)


def _replace(parents, old, new):
    par = parents[old]
    for field, value in ast.iter_fields(par):
        if value is old:
            setattr(par, field, new)
            return
        if isinstance(value, list):
            for j, v in enumerate(value):
                if v is old:
                    value[j] = new
                    return
    raise WitnessNotPerformed(f"no parent slot for {type(old).__name__}")


def _build(tree, name: str, path: str, swap=None) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = path
    saved = {k: sys.modules.get(k) for k in (swap or {})}
    sys.modules.update(swap or {})
    try:
        exec(compile(tree, path + " (generated mutant)", "exec"), mod.__dict__)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


def mutant_killed(target: str, kind: str, idx: int, i):
    """How the mutant was killed: "build" (it does not compile or import), "line" (a bound check returned its own
    line), "error" (only ERROR lines: a check crashed on it); None when it survived."""
    src_tc, src_ca = (Path(m.__file__).read_text(encoding="utf-8") for m in (tc, ca))
    try:
        if target == "tc":
            tcm = _build(_mutate(src_tc, kind, idx, i), "transcript_codex", tc.__file__)
            cam = _build(ast.parse(src_ca), "codex_adapter", ca.__file__, {"transcript_codex": tcm})
            checks = [(f, tcm) for f in TC_CHECKS] + [(f, cam) for f in CA_CHECKS]
        else:
            cam = _build(_mutate(src_ca, kind, idx, i), "codex_adapter", ca.__file__)
            checks = [(f, cam) for f in CA_CHECKS]
    except Exception:  # noqa: BLE001 - a mutant that does not build is killed
        return "build"
    sink, crashed = io.StringIO(), False
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        for f, m in checks:
            got = f(m)
            if any(not x.startswith("ERROR") for x in got):
                return "line"
            crashed = crashed or bool(got)
    return "error" if crashed else None


def all_mutants() -> list:
    out = []
    for target, mod in (("tc", tc), ("ca", ca)):
        for key, kind, idx, i in mutant_sites(Path(mod.__file__).read_text(encoding="utf-8")):
            out.append((f"{target} {key}", target, kind, idx, i))
    return out


def baseline_lines() -> list:
    """Lane t104-mutation-baseline: every line mutant_killed's checks print over the UNMUTATED files, built the
    same two ways (transcript_codex with codex_adapter over it, and codex_adapter alone). A mutant counts as
    killed on any line, ERROR lines included, so any line here means the sweep would count nothing real."""
    src_tc, src_ca = (Path(m.__file__).read_text(encoding="utf-8") for m in (tc, ca))
    try:
        tcm = _build(ast.parse(src_tc), "transcript_codex", tc.__file__)
        cam = _build(ast.parse(src_ca), "codex_adapter", ca.__file__, {"transcript_codex": tcm})
        alone = _build(ast.parse(src_ca), "codex_adapter", ca.__file__)
    except Exception as e:  # noqa: BLE001 - the unmutated files do not build: red
        return [f"BUILD the unmutated files do not build: {type(e).__name__}: {e}"]
    out, sink = [], io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        for f, m in [(f, tcm) for f in TC_CHECKS] + [(f, cam) for f in CA_CHECKS] + [(f, alone) for f in CA_CHECKS]:
            out += [f"{f.__name__}: {x}" for x in f(m)]
    return out


def run_generated(shard: int, of: int) -> int:
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_clean("test_codex_adapter generated mutants", baseline_lines)
    muts = all_mutants()
    keys = {m[0] for m in muts}
    stale = sorted(k for k in EQUIVALENT if k not in keys)
    mine = [m for n, m in enumerate(muts) if n % of == shard - 1]
    killed, equivalent, survivors, wrongly_listed, how = 0, 0, [], [], {"build": 0, "line": 0, "error": 0}
    for key, target, kind, idx, i in mine:
        dead = mutant_killed(target, kind, idx, i)
        if dead:
            how[dead] += 1
        if key in EQUIVALENT:
            equivalent += 1
            if dead:
                wrongly_listed.append(key)
        elif dead:
            killed += 1
        else:
            survivors.append(key)
    for k in survivors:
        print(f"SURVIVOR {k}", flush=True)
    for k in stale:
        print(f"STALE (names no generated mutant) {k}", flush=True)
    for k in wrongly_listed:
        print(f"STALE (listed EQUIVALENT but killed) {k}", flush=True)
    print(f"test_codex_adapter generated mutants: shard {shard} of {of}: {len(mine)} mutants of {len(muts)}, "
          f"{killed} killed ({how['line']} by a check's own line, {how['error']} by a crash, {how['build']} at "
          f"build), {equivalent} equivalent, {len(survivors)} survivors, "
          f"{len(stale) + len(wrongly_listed)} stale", flush=True)
    return 0 if not survivors and not stale and not wrongly_listed else 1


class TestGeneratedMutantRegistry(unittest.TestCase):
    """The cheap half of the sweep, run with every suite: the generator finds sites in both files, and every
    EQUIVALENT entry names a generated mutant (the killing half runs under --generated-mutants)."""

    def test_the_equivalent_list_names_generated_mutants(self):
        for mod in (tc, ca):
            self.assertTrue(Path(mod.__file__).is_file(), f"{Path(mod.__file__).name} does not exist")
        muts = all_mutants()
        self.assertGreater(len([m for m in muts if m[1] == "tc"]), 100)
        self.assertGreater(len([m for m in muts if m[1] == "ca"]), 100)
        self.assertEqual(sorted(k for k in EQUIVALENT if k not in {m[0] for m in muts}), [])
        self.assertTrue(all(isinstance(r, str) and len(r) > 20 for r in EQUIVALENT.values()))


# ---- R-recorded (lane vendor-settle stage V, freeze leg i; glitch-f1's settle rulings, Thu 22 Oct 2026) ------------
# Each RECORDED file of codex-streams is a byte copy of a committed walk record in this tree, and read_stream,
# end_reason and read_rollout read the copies as plain json does.
def recorded_source(name: str) -> Path:
    walk, kind, k = re.fullmatch(r"(w-o[0-9]+)-(turn|rollout)-([0-9]+)\.jsonl", name).groups()
    return HERE / "rehearsals" / walk / (f"turn-{k}.jsonl" if kind == "turn" else f"session/native-turn-{k}.jsonl")


def r_recorded_problems() -> list:
    out = []
    recorded = sorted(f for f, (kind, _rest) in labels().items() if kind == "RECORDED")
    if recorded != sorted([f"w-o46-turn-{k}.jsonl" for k in (1, 2, 3)] + [f"w-o46-rollout-{k}.jsonl" for k in (1, 2, 3)]
                          + ["w-o47-rollout-1.jsonl"]):
        out.append(f"the RECORDED files are {recorded}")
    for name in recorded:
        if (FIXTURES / name).read_bytes() != recorded_source(name).read_bytes():
            out.append(f"{name} is not byte for byte {recorded_source(name).relative_to(HERE)}")
    turns = json.loads((HERE / "rehearsals" / "w-o46" / "driver-ledger.json").read_text(encoding="utf-8"))["turns"]
    for k in (1, 2, 3):
        st = [json.loads(x) for x in fixture(f"w-o46-turn-{k}.jsonl").split("\n") if x.strip()]
        want = {"thread_ids": list(dict.fromkeys(x["thread_id"] for x in st if x["type"] == "thread.started")),
                "agent_text": "\n".join(x["item"]["text"] for x in st if x["type"] == "item.completed"
                                        and x["item"]["type"] == "agent_message"),
                "usage": [x for x in st if x["type"] == "turn.completed"][0]["usage"],
                "completed": sum(x["type"] == "turn.completed" for x in st), "failed": 0, "undecoded": 0}
        got = ca.read_stream(fixture(f"w-o46-turn-{k}.jsonl"))
        out += [f"w-o46 turn {k}: read_stream's {key} is {str(got.get(key))[:60]!r}, the stream's {str(v)[:60]!r}"
                for key, v in want.items() if got.get(key) != v]
        if ca.end_reason(turns[k - 1]["exit"], False, got) != turns[k - 1]["end"]:
            out.append(f"w-o46 turn {k}: end_reason is not the ledger's {turns[k - 1]['end']!r}")
    for name, seen in [(f"w-o46-rollout-{k}.jsonl", k - 1) for k in (1, 2, 3)] + [("w-o47-rollout-1.jsonl", 0)]:
        recs = [json.loads(x) for x in fixture(name).split("\n") if x.strip()]
        tc = [r["payload"] for r in recs if r["type"] == "turn_context"]
        want = {"model": tc[-1]["model"], "permission_mode": tc[-1]["approval_policy"],
                "version": recs[0]["payload"]["cli_version"]}
        got = ca.read_rollout(fixture(name), seen=seen)
        if (got["init"], got["turn_contexts"]) != (want, len(tc)):
            out.append(f"{name}: read_rollout gives {got}, plain json {want} over {len(tc)} turn_context(s)")
    return out


class RRecorded(unittest.TestCase):
    def test_r_recorded_the_copies_read_as_plain_json(self):
        self.assertEqual(r_recorded_problems(), [])


if __name__ == "__main__":
    if "--generated-mutants" in sys.argv:
        shard, of = 1, 1
        if "--shard" in sys.argv:
            shard, of = (int(x) for x in sys.argv[sys.argv.index("--shard") + 1].split("/"))
        setUpModule()
        try:
            code = run_generated(shard, of)
        finally:
            tearDownModule()
        raise SystemExit(code)
    if "--witnesses" in sys.argv:
        sys.argv.remove("--witnesses")
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestWitnesses)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        red = sum(1 for x in WITNESS_LOG if ": red by " in x)
        print(f"test_codex_adapter witnesses: {red}/{len(WITNESSES)} red; registry {len(WITNESSES)}", flush=True)
        raise SystemExit(0 if result.wasSuccessful() and red == len(WITNESSES) else 1)
    unittest.main(verbosity=2)
