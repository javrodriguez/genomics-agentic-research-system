#!/usr/bin/env python3
"""Lane w6j (Gap Study round 4, slice S6c): the Claude Code adapter (C15) and its readers, on recorded and synthetic
streams over a fake runtime.

Recorded fixtures (read-only, committed by earlier lanes; harness 2.1.267):
  evals/haiku-prestudy/verification/probes/*.jsonl         real `claude -p --output-format stream-json --verbose` stdout
  evals/gap-study/verification/api-error-stream-probe.txt  the harness's API-error assistant record, as summarised
  evals/gap-study-2/verification/env-smoke/tmpdir/transcript.jsonl   a real session file (one call, two records)

What is tested, each guard with its own bound check and a whole-file witness of claude_code_adapter.py compiled in
memory (the registry pattern of the earlier gap4 lanes):

  A1-recorded  read_stream on the five recorded probes: each init's model, permission mode and version, the credential
               source, the calls counted once per (message.id, request_id), the tool calls, the result record's
               printed total_cost_usd, num_turns and permission_denials (one Bash denial on the haiku auto probe, kept
               as tool name and id only). Witness: init-any-record (a non-init record's model read as the init).
  A2-api-error the harness's own API-error record (is_api_error_message, model <synthetic>, error model_not_found) is
               an api_errors entry typed by its `error`, its words the harness's text; it is never the agent's text
               and never agent output. Witness: api-error-as-agent.
  A3-argv      the turn's argv in the box: the routing pin's permission mode (a PENDING mode refuses the adapter), no
               --allowedTools, --disallowedTools WebFetch WebSearch, round 3's isolation flags, --session-id on the
               first turn and --resume after; the login rides by name only. Witnesses: allowed-tools-back,
               mode-constant.
  A4-turn      a turn on a fake runtime returns a TurnResult read from its stream: init, end reason (end_turn, error,
               timed-out), counters as the cgroup rise, agent_output; turn_records keeps the apiKeySource, the calls
               and the result. Witness: exit-ignored (every exit read as end_turn).

Fakes only: no model, vendor, network, container runtime, credential or holdout. setUpModule arms a process guard
that refuses every process start, and clears this process's environment to a fixed few names (run_take refuses a
take when a login or key name is set in the caller's environment).
"""

from __future__ import annotations

import ast
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent_adapter as aa  # noqa: E402
try:                                   # absent on the stage's base: every bound check then fails by its own assertion
    import claude_code_adapter as cca  # noqa: E402
except ModuleNotFoundError:
    cca = types.ModuleType("claude_code_adapter")
    cca.__file__ = str(HERE / "claude_code_adapter.py")
from box import run_take as rt  # noqa: E402

EVALS = HERE.parent
PROBES = EVALS / "haiku-prestudy" / "verification" / "probes"
SESSION_SMOKE = EVALS / "gap-study-2" / "verification" / "env-smoke" / "tmpdir" / "transcript.jsonl"
API_ERROR_PROBE = EVALS / "gap-study" / "verification" / "api-error-stream-probe.txt"

# The recorded probes and what each records (read from the files by hand, 11 Oct 2026; harness 2.1.267).
RECORDED = {
    "claude-haiku-4-5-20251001.driver-argv.jsonl": ("claude-haiku-4-5-20251001", "default", 2, 1,
                                                    0.014705200000000003, 2, []),
    "claude-sonnet-5.auto.jsonl": ("claude-sonnet-5", "auto", 2, 1, 0.03317559999999999, 2, []),
    "claude-haiku-4-5-20251001.auto.jsonl": ("claude-haiku-4-5-20251001", "default", 2, 1, 0.014775100000000001, 2,
                                             [{"tool_name": "Bash", "tool_use_id": "toolu_01H8kMC3peRVpMqfyM1QWW6w"}]),
    "claude-haiku-4-5-20251001.auto.allow.jsonl": ("claude-haiku-4-5-20251001", "default", 2, 1,
                                                   0.005676800000000001, 2, []),
    "claude-haiku-4-5-20251001.auto.allow-three-forms.jsonl": ("claude-haiku-4-5-20251001", "default", 2, 3,
                                                               0.019206599999999997, 4, []),
}
VERSION = "2.1.267"
TAKE = "ab" * 32
SID = "5f0c8e2a-1b3d-5c7e-9a1f-2b4d6f8a0c11"
BYPASS = "bypassPermissions"
MODEL = "claude-haiku-4-5-20251001"
LOGIN = "CLAUDE_CODE_OAUTH_TOKEN"
LOGIN_VALUE = "synthetic-login-value-" + "0123456789abcdef"     # a planted fake, never a real login

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
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w6j-"))).resolve()
    keep = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TMPDIR") if k in os.environ}
    keep.update(HOME=str(SCRATCH))
    _STACK.enter_context(mock.patch.dict(os.environ, keep, clear=True))
    for name in ("run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _trip(f"subprocess.{name}")))
    for name in ("system", "popen", "posix_spawn", "posix_spawnp", "fork", "forkpty"):
        if hasattr(os, name):
            _STACK.enter_context(mock.patch.object(os, name, _trip(f"os.{name}")))
    # Claude Code's fallback variables are PENDING until confirmed at the pinned version: none, for the fake only.
    _STACK.enter_context(mock.patch.object(rt, "FALLBACK_ENV", {}))


def tearDownModule():
    _STACK.close()


# ------------------------------------------------------------------------------------------------ fixtures
def recorded(name: str) -> str:
    return (PROBES / name).read_text(encoding="utf-8")


def api_error_stream() -> str:
    """A turn's stream holding the harness's API-error record, built from the fields the probe recorded (model
    <synthetic>, flags error=model_not_found and is_api_error_message=true, the words "There's an issue with the
    selected model"), then the init and an error result."""
    probe = API_ERROR_PROBE.read_text(encoding="utf-8")
    assert "'error': 'model_not_found', 'is_api_error_message': True" in probe and "<synthetic>" in probe
    recs = [{"type": "system", "subtype": "init", "session_id": SID, "apiKeySource": "none", "model": "no-such-model",
             "permissionMode": BYPASS, "claude_code_version": VERSION, "tools": ["Bash"]},
            {"type": "assistant", "session_id": SID, "error": "model_not_found", "is_api_error_message": True,
             "message": {"id": "msg_synthetic_err", "model": "<synthetic>", "role": "assistant",
                         "content": [{"type": "text", "text": "There's an issue with the selected model"}]}},
            {"type": "result", "subtype": "success", "is_error": True, "session_id": SID,
             "result": "There's an issue with the selected model", "total_cost_usd": 0, "num_turns": 1,
             "permission_denials": [], "api_error_status": None}]
    return "".join(json.dumps(r) + "\n" for r in recs)


def synthetic_turn(*, text="Synthetic reply.", tool=False, model=MODEL, sid=SID, mode=BYPASS, msg="msg_s1",
                   req="req_s1", cost=0.01, result=True) -> str:
    """A synthetic stream of one call, in the recorded probes' shape."""
    content = [{"type": "text", "text": text}] if text is not None else []
    if tool:
        content.append({"type": "tool_use", "id": f"toolu_{msg}", "name": "Bash", "input": {"command": "ls"}})
    recs = [{"type": "system", "subtype": "init", "session_id": sid, "apiKeySource": "none", "model": model,
             "permissionMode": mode, "claude_code_version": VERSION, "tools": ["Bash", "Read"]},
            {"type": "assistant", "session_id": sid, "request_id": req,
             "message": {"id": msg, "model": model, "role": "assistant", "content": content,
                         "usage": {"input_tokens": 3, "output_tokens": 1}}}]
    if result:
        recs.append({"type": "result", "subtype": "success", "is_error": False, "session_id": sid,
                     "total_cost_usd": cost, "num_turns": 1, "permission_denials": [],
                     "usage": {"input_tokens": 3, "output_tokens": 9}, "modelUsage": {model: {"costUSD": cost}}})
    return "".join(json.dumps(r) + "\n" for r in recs)


class FakeRuntime:
    """Answers the adapter's two execs: `claude --version` and a turn (`claude -p ...`), from a queue of streams."""

    def __init__(self, streams, *, version_out=f"{VERSION} (Claude Code)\n", exit_codes=None, timeout_at=None):
        self.streams, self.exit_codes = list(streams), list(exit_codes or [])
        self.version_out, self.timeout_at = version_out, timeout_at
        self.calls: list = []
        self.envs: list = []

    def run(self, argv, env=None, timeout=None):
        a = list(argv)
        self.calls.append(a)
        self.envs.append(dict(env or {}))
        if a[-2:] == list(cca.VERSION_ARGV):
            return rt.Completed(0, self.version_out, "")
        if a[:2] == ["docker", "exec"] and cca.CLIENT in a and "-p" in a:
            n = sum(1 for c in self.calls if "-p" in c)
            out = self.streams[n - 1]
            if self.timeout_at == n:
                e = TimeoutError("synthetic: the turn exceeded its budget")
                e.stdout = out
                raise e
            code = self.exit_codes[n - 1] if n <= len(self.exit_codes) else 0
            return rt.Completed(code, out, "")
        raise GuardTripped(f"the fake runtime refuses {a[:6]!r}")


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


def adapter(mod, runtime, *, mode=BYPASS, counters=None):
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    return mod.ClaudeCodeAdapter(runtime=runtime, take_id=TAKE, run_tree=str(SCRATCH / "tree"),
                                 login_file=login_file(), session_id=SID, model=MODEL,
                                 pin={"permission_mode": mode, "version": VERSION},
                                 stream_path_for=lambda n: str(folder / f"turn-{n}.jsonl"),
                                 counters_for=counters or Counters(), clock=Clock())


API = ("read_stream", "ClaudeCodeAdapter", "argv", "end_reason", "session_calls", "ISOLATION_FLAGS", "VERSION_ARGV",
       "CLIENT")


def guarded(prefix):
    """A bound check never raises: an unexpected exception is an ERROR line, never a kill; a module without the
    adapter's names fails by the check's own line."""
    def wrap(fn):
        def check(mod):
            gone = [n for n in API if not hasattr(mod, n)]
            if gone:
                return [f"{prefix}: claude_code_adapter.py has no {', '.join(gone)}"]
            try:
                return fn(mod, prefix)
            except Exception as e:  # noqa: BLE001
                return [f"ERROR {prefix}: {type(e).__name__}: {str(e)[:240]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("A1-recorded")
def a1_recorded(mod, p):
    out = []
    for name, (model, mode, calls, tools, cost, turns, denials) in RECORDED.items():
        r = mod.read_stream(recorded(name))
        if r["init"] != {"model": model, "permission_mode": mode, "version": VERSION}:
            out.append(f"{p}: {name}: init read as {r['init']}")
        if r["init_extra"]["api_key_source"] != "none" or r["inits"] != 1:
            out.append(f"{p}: {name}: credential source {r['init_extra']['api_key_source']!r}, {r['inits']} init(s)")
        if len(r["calls"]) != calls or len(r["tool_use_ids"]) != tools or not r["agent_output"]:
            out.append(f"{p}: {name}: {len(r['calls'])} call(s), {len(r['tool_use_ids'])} tool call(s), "
                       f"output {r['agent_output']}")
        res = r["result"] or {}
        if (res.get("total_cost_usd"), res.get("num_turns"), res.get("permission_denials")) != (cost, turns, denials):
            out.append(f"{p}: {name}: the result reads {res.get('total_cost_usd')}, {res.get('num_turns')}, "
                       f"{res.get('permission_denials')}")
        if r["api_errors"] or r["undecoded"]:
            out.append(f"{p}: {name}: {r['api_errors']} API errors, {r['undecoded']} undecoded line(s)")
    return out


@guarded("A2-api-error")
def a2_api_error(mod, p):
    out = []
    r = mod.read_stream(api_error_stream())
    types_ = [e["type"] for e in r["api_errors"]]
    if "model_not_found" not in types_:
        out.append(f"{p}: the API-error record's type is not read: {r['api_errors']}")
    if any("issue with the selected model" in (e["text"] or "") for e in r["api_errors"]) is False:
        out.append(f"{p}: the API-error words are not the harness's text: {r['api_errors']}")
    if r["agent_output"] or "issue" in r["agent_text"] or r["calls"]:
        out.append(f"{p}: the harness's API-error record was read as the agent's (output {r['agent_output']}, "
                   f"text {r['agent_text']!r}, calls {r['calls']})")
    return out


@guarded("A3-argv")
def a3_argv(mod, p):
    out = []
    try:
        adapter(mod, FakeRuntime([]), mode="PENDING")
        out.append(f"{p}: an adapter was made under a PENDING permission mode")
    except rt.NotReady:
        pass
    box = FakeRuntime([synthetic_turn(msg="m1", req="r1"), synthetic_turn(msg="m2", req="r2")])
    a = adapter(mod, box)
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    a.turn("first line", first=True, budget_s=60)
    a.turn("second line", first=False, budget_s=60)
    turns = [c for c in box.calls if "-p" in c]
    for n, c in enumerate(turns, 1):
        inner = c[c.index(TAKE) + 1:]
        if "--allowedTools" in inner:
            out.append(f"{p}: turn {n} passes --allowedTools")
        if inner[inner.index("--permission-mode") + 1] != BYPASS:
            out.append(f"{p}: turn {n} passes mode {inner[inner.index('--permission-mode') + 1]!r}, not the pin's")
        i = inner.index("--disallowedTools")
        if inner[i + 1:i + 3] != ["WebFetch", "WebSearch"]:
            out.append(f"{p}: turn {n} disallows {inner[i + 1:i + 3]}")
        if not all(f in inner for f in mod.ISOLATION_FLAGS) or inner[inner.index("--model") + 1] != MODEL:
            out.append(f"{p}: turn {n} lacks round 3's isolation flags or the row's model")
        want = ["--session-id", SID] if n == 1 else ["--resume", SID]
        if inner[-2:] != want:
            out.append(f"{p}: turn {n} ends {inner[-2:]}, not {want}")
        if any(LOGIN_VALUE in x for x in c) or LOGIN not in c:
            out.append(f"{p}: turn {n}'s login does not ride by name only")
    return out


@guarded("A4-turn")
def a4_turn(mod, p):
    out = []
    box = FakeRuntime([synthetic_turn(msg="m1", req="r1", tool=True), synthetic_turn(msg="m2", req="r2"),
                       synthetic_turn(msg="m3", req="r3", result=False)], exit_codes=[0, 1], timeout_at=3)
    a = adapter(mod, box, counters=Counters(rises=[0, 2, 0]))
    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
    t1 = a.turn("one", first=True, budget_s=60)
    t2 = a.turn("two", first=False, budget_s=60)
    t3 = a.turn("three", first=False, budget_s=60)
    got = [(t.end_reason, t.exit_code, t.counters["oom_kill_delta"]) for t in (t1, t2, t3)]
    want = [(aa.END_TURN, 0, 0), (aa.END_ERROR, 1, 2), (aa.END_TIMED_OUT, None, 0)]
    if got != want:
        out.append(f"{p}: the turns read as {got}, not {want}")
    if t1.init != {"model": MODEL, "permission_mode": BYPASS, "version": VERSION} or not t1.agent_output:
        out.append(f"{p}: turn 1's init {t1.init}, output {t1.agent_output}")
    if t1.text != "Synthetic reply." or not os.path.isfile(t1.stream_path):
        out.append(f"{p}: turn 1's text {t1.text!r} or stream {t1.stream_path} is off")
    recs = a.turn_records
    if [r["api_key_source"] for r in recs] != ["none"] * 3 or recs[0]["calls"][0]["message_id"] != "m1":
        out.append(f"{p}: the turn records hold {[(r['api_key_source'], r['calls']) for r in recs]}")
    if recs[0]["result"]["total_cost_usd"] != 0.01 or recs[2]["result"] is not None or not recs[2]["timed_out"]:
        out.append(f"{p}: the result records are {[r['result'] for r in recs]}")
    if a.version() != VERSION:
        out.append(f"{p}: the version reads {a.version()!r}")
    return out


# ------------------------------------------------------------------------------------------------ the tests
class TestTheReaders(unittest.TestCase):
    def test_a1_the_recorded_streams_read_as_recorded(self):
        self.assertEqual(a1_recorded(cca), [])

    def test_a2_the_harness_api_error_is_never_the_agents(self):
        self.assertEqual(a2_api_error(cca), [])

    def test_a3_the_turn_argv(self):
        self.assertEqual(a3_argv(cca), [])

    def test_a4_a_turn_on_the_fake_runtime(self):
        self.assertEqual(a4_turn(cca), [])

    def test_the_isolation_flags_are_round_3s(self):
        tree = ast.parse((HERE / "drive.py").read_text(encoding="utf-8"))
        got = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "ISOLATION_FLAGS" for t in n.targets)]
        self.assertEqual(got, [getattr(cca, "ISOLATION_FLAGS", None)])

    def test_a_version_that_does_not_parse_refuses(self):
        self.assertTrue(hasattr(cca, "ClaudeCodeAdapter"), "claude_code_adapter.py has no ClaudeCodeAdapter")
        a = adapter(cca, FakeRuntime([], version_out="claude 2.1\n"))
        with self.assertRaises(rt.NotReady):
            a.version()

    def test_the_session_file_calls_count_once_each(self):
        self.assertTrue(hasattr(cca, "session_calls"), "claude_code_adapter.py has no session_calls")
        calls = cca.session_calls(SESSION_SMOKE.read_text(encoding="utf-8"))
        self.assertEqual(len(calls), 1)          # two records of one call (thinking, text): one call
        self.assertEqual(calls[0]["usage"], {"input_tokens": 10, "output_tokens": 195,
                                             "cache_read_input_tokens": 13607, "cache_creation_input_tokens": 6458})


class WitnessNotPerformed(AssertionError):
    pass


def witness_module(edits: tuple) -> types.ModuleType:
    """claude_code_adapter.py with `edits` applied, compiled in memory as its own module (never written to disk)."""
    with open(cca.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    name = "claude_code_adapter_w6j_witness"
    mod = types.ModuleType(name)
    mod.__file__ = cca.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, cca.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


WITNESSES = {
    "init-any-record": ((("        if kind == INIT_TYPE and rec.get(\"subtype\") == INIT_SUBTYPE:",
                          "        if kind == INIT_TYPE or kind == \"assistant\":"),), a1_recorded, "A1-recorded"),
    "api-error-as-agent": ((("    return rec.get(API_ERROR_FLAG) is True or msg.get(\"model\") == SYNTHETIC_MODEL",
                             "    return False"),), a2_api_error, "A2-api-error"),
    "allowed-tools-back": ((("\"--model\", model, *ISOLATION_FLAGS, \"--disallowedTools\", *DISALLOWED_TOOLS]",
                             "\"--model\", model, *ISOLATION_FLAGS, \"--allowedTools\", \"Bash\", "
                             "\"--disallowedTools\", *DISALLOWED_TOOLS]"),), a3_argv, "A3-argv"),
    "mode-constant": ((("        self.session_id, self.model, self.permission_mode = session_id, model, mode",
                        "        self.session_id, self.model, self.permission_mode = session_id, model, \"default\""),),
                      a3_argv, "A3-argv"),
    "exit-ignored": ((("    return aa.END_TURN if exit_code == 0 else aa.END_ERROR",
                       "    return aa.END_TURN"),), a4_turn, "A4-turn"),
}
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(cca), [], f"{name}: the bound check is not green on claude_code_adapter.py")
        got = check(witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_init_any_record(self):
        self.kill("init-any-record")

    def test_witness_api_error_as_agent(self):
        self.kill("api-error-as-agent")

    def test_witness_allowed_tools_back(self):
        self.kill("allowed-tools-back")

    def test_witness_mode_constant(self):
        self.kill("mode-constant")

    def test_witness_exit_ignored(self):
        self.kill("exit-ignored")

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted(["init-any-record", "api-error-as-agent", "allowed-tools-back",
                                                    "mode-constant", "exit-ignored"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
