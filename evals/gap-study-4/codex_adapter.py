#!/usr/bin/env python3
"""The Codex CLI adapter for round 4's box, arm O (lane w11a-codex-adapter; D8 sections 1 and 3, D8:461-472).

`CodexAdapter` is agent_adapter's interface for `codex` (run_take.CODEX): one `docker exec` per turn into the
kept-alive take container (box/run_take.run_turn), the turn's `codex exec --json` stdout written host-side at the
driver's stream path, and a `TurnResult` read from that stream's harness-side records and the rollout file's per-turn
context. It never calls a model itself: every test drives it on a fake runtime with synthetic streams.

SHAPES_SOURCE. The stream and rollout shapes this module reads were re-tested on the streams and rollouts recorded at
walk w-o46 (codex-cli 0.162.1, three resumed turns) and the rollout of walk w-o47 (gpt-6-luna), listed in
tests/fixtures/codex-streams/README.md, against values derived independently with plain json
(tests/vendor_settle_codex.py CLegI); the adapter reports the word in its harness record and in every turn record, and
freeze leg i reads it. Lane vendor-admission T3 (glitch-b5): freeze.py now refuses a design row of this harness (arm O)
while SHAPES_SOURCE is not "recorded" (freeze.unrecorded_shapes_problem); stage V of lane vendor-settle flipped it.

THE ARGV (D8:107-112):

    codex exec --json -m <the row's model> <the mode's flags> <line>                       the take's first turn
    codex exec --json -m <the row's model> <the mode's flags> resume <SESSION_ID> <line>   every turn after it

  O-1  `-m <model>` on every exec (D8's per-harness table, "Model pin, every turn").
  O-2  `resume <SESSION_ID>` after the first turn only. Codex mints the session id, so it is read from turn 1's
       `thread.started.thread_id` (never imposed, unlike Claude Code's); a later turn whose stream names another
       thread is refused.
  O-3  The approvals and sandbox flags are the take's routing pin's permission mode looked up in MODE_FLAGS (D8:110:
       `--dangerously-bypass-approvals-and-sandbox`, for a box that is the sandbox); a PENDING, absent or unknown mode
       refuses the adapter's making. The pin's word for arm O is this lane's ("bypass"), Q-w11a-4.
  O-4  A line that starts with "-" is refused (it would be read as a flag); the study's lines never do.
  Whether exec's options are read before `resume` at the pinned version is the walk's to confirm (Q-w11a-5).

THE RECORDS READ (the tables are transcript_codex's; see its docstring for which are D8's and which are not):

  stream     the event and item types and keys of transcript_codex, each record checked by check_record; a record
             off the tables refuses the turn (StreamError), never read on a guess.
             api_errors  one per `error` event and per `turn.failed`, in order: {status None, type the event type,
                         text the harness's own message}. The agent's words (agent_message) are never an API error.
             agent_output True when an item.completed of an OUTPUT_ITEM_TYPES type exists (text or a tool call;
                         reasoning alone is not output), or an item.started of a STARTED_ITEM_TYPES tool item (the
                         agent issued the call; pre-freeze review 2, m7: a turn cut by a timeout while its command
                         ran is past the first turn, as a Claude Code tool_use block is), read from event and item
                         types, never from content.
             usage       turn.completed.usage's five USAGE_KEYS as recorded; a key that is missing or not a count
                         refuses (StreamError), never 0; a turn with no turn.completed has no usage (None, unmeasured).
  rollout    `$CODEX_HOME/sessions/.../rollout-*.jsonl`, copied out host-side by the driver and handed over by
             `rollout_for(n)`: exec JSON carries no model (D8:168, issue #14736), so the turn's init is read here.
             NOT in D8 (this lane's reading, Q-w11a-1): records {type, payload}; `session_meta.payload.cli_version`;
             `turn_context.payload.model` and `.approval_policy`. The init is {model, permission_mode (the
             approval_policy), version (the cli_version)} from the turn_context records the rollout gained during this
             turn; none gained, or one of the three not a string, is init None. Never the requested model.
  version    `codex --version`, printed as "codex-cli X.Y.Z" (this lane's reading, Q-w11a-1); anything else refuses.

end_reason: timed-out when the exec timed out; end_turn only on exit 0 with one turn.completed and no turn.failed;
error otherwise.

Not in this lane (named as carried): the PARSERS / harness_bookkeeping / agent_adapter tables, drive.py's admission,
check_take readers, mode_binding expectations, routing markers, per-call cost (price_table is PENDING), the real-box
stub `codex`. (run_take's Codex billing-route variables are named since 14 Oct, run_take.py:663-681.)

Standard library only. No model, vendor, network or credential is touched by anything in this module.
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import agent_adapter as aa  # noqa: E402
import codex_native as cn  # noqa: E402
import transcript_codex as tc  # noqa: E402
from box import run_take as rt  # noqa: E402

NAME = rt.CODEX
CLIENT = "codex"
SUBCOMMAND = "exec"
JSON_FLAG = "--json"
MODEL_FLAG = "-m"
RESUME = "resume"
# The pinned `codex exec --help` Commands list (box evidence codex-exec-help.json, sha256 a90c28e8...): the usage is
# `codex exec [OPTIONS] <COMMAND> [ARGS]`, so a first turn's prompt that is exactly one of these runs as that subcommand
# (the box Codex-exec review's MAJOR, the same hole here). The box's run_take.CODEX_HELP_COMMANDS (box 14670435) holds
# the same names; a test binds the two wherever both are on the tree.
CODEX_EXEC_COMMANDS = ("resume", "fork", "review", "help")
VERSION_ARGV = (CLIENT, "--version")
VERSION_FORM = re.compile(r"codex-cli ([0-9]+\.[0-9]+\.[0-9]+)")
# The routing pin's permission mode for arm O -> the exec's approvals and sandbox flags (D8:110-112).
MODE_FLAGS = {"bypass": ("--dangerously-bypass-approvals-and-sandbox",)}
SHAPES_SOURCE = "recorded"
SHAPES_SOURCES = ("documented", "recorded")
# Pre-freeze review 1, m3 (lane L1): the RECORDED fixture SHAPES_SOURCE "recorded" rests on. freeze.py's leg i holds
# it to the committed walk record it was copied from (check_take.recorded_binding_problem), so the word alone
# never opens the leg.
SHAPES_RECORDED_ON = "recorded-codex-w-o46/transcript.jsonl"

# The rollout file's records (NOT in D8; Q-w11a-1).
ROLLOUT_META, ROLLOUT_TURN = "session_meta", "turn_context"
ROLLOUT_VERSION_KEY = "cli_version"
ROLLOUT_INIT_KEYS = {"model": "model", "permission_mode": "approval_policy"}
_THREAD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}")
# Codex slice 2: the one served-model evidence exec writes, an item.completed error item (exec/src/exec_events.rs:132,
# 310-312) whose message is format!("model rerouted: {} -> {} ({:?})", from, to, reason)
# (exec/src/event_processor_with_jsonl_output.rs:494-507). Only that exact shape is read; any other error item stays
# off the tables and refuses the turn.
LAUNCH_DISAGREES = "launch-differs-from-registered-invocation"

# ---- OD57's read shapes for arm O (lane vendor-b17 round 2, glitch-26's rulings B17-5 to B17-7, 19 Oct 2026) ---------
# They live in box/od57_shapes.py since lane vendor-b24 (B24-2 item 1: one rule set, shared with the aegis door); the
# drive still reads them here (drive.scan_read_shapes reads module.READ_SHAPES).
from box import od57_shapes as _od57_shapes  # noqa: E402
READ_SHAPES = _od57_shapes.CODEX


class StreamError(ValueError):
    """A stream or rollout the reader cannot use as it stands (a typed refusal, never a guess)."""


class ExecutedStreamRefused(aa.ExecutedTurnRefused, StreamError):
    """Live harness slice 6: a StreamError raised after the turn's exec ran, carrying what was kept of the exec."""


def _count(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def read_stream(text: str, model=None) -> dict:
    """One turn's `codex exec --json` stdout, read for its harness-side records and the agent's words, kept apart.

    thread_ids    the distinct thread.started thread ids, in order
    agent_text    the agent_message texts, joined by newlines (graders read it; routing never does)
    agent_output  True when an item.completed of an OUTPUT_ITEM_TYPES type exists, or an item.started of a
                  STARTED_ITEM_TYPES tool item (pre-freeze review 2, m7)
    api_errors    [{status, type, text}] per error event and turn.failed, in order
    usage         turn.completed.usage's USAGE_KEYS, or None when the turn has no turn.completed
    completed     how many turn.completed records; failed: how many turn.failed records
    tool_ids      the ids of the completed tool items, in order
    undecoded     1 when the stream's last non-blank line is not JSON (a cut stream), else 0; a line that is not
                  JSON anywhere before it refuses (W11A-R1-10), and so does a decoded record off the tables
    """
    thread_ids, said, output, api, usage, completed, failed, tools, bad = [], [], False, [], None, 0, 0, [], 0
    served = []
    # lane pf1-l3 (the second closure check of f0c0eb1d, 24 Oct 2026): split on "\n" alone, as gemini_adapter does;
    # str.splitlines also splits on U+2028, U+2029 and U+0085, which a JSON string carries raw, so a command's output
    # printing one would split a record and refuse the turn
    lines = [raw.strip() for raw in text.split("\n") if raw.strip()]
    for n, raw in enumerate(lines, 1):
        try:
            rec = json.loads(raw)
        except ValueError:
            if n != len(lines):
                raise StreamError(f"line {n} of {len(lines)} is not JSON: only a cut stream's last line may be") from None
            bad = 1
            continue
        to_model = reroute_of(rec, model)
        if to_model is not None:              # Codex slice 2: served-model evidence, never agent output or an error
            served.append(to_model)
            continue
        try:
            t, it = tc.check_record(rec)
        except tc.ShapeError as e:
            raise StreamError(f"the stream holds a record off the pre-registered tables: {e}") from None
        if t == tc.ERROR:
            api.append({"status": None, "type": t, "text": rec["message"]})
        elif t == tc.TURN_FAILED:
            api.append({"status": None, "type": t, "text": rec["error"]["message"]})
            failed += 1
        elif t == tc.THREAD_STARTED:
            tid = rec["thread_id"]
            if not _THREAD_ID.fullmatch(tid):
                raise StreamError("thread.started carries a thread id off its shape")
            if tid not in thread_ids:
                thread_ids.append(tid)
        elif t == tc.TURN_COMPLETED:
            completed += 1
            if completed > 1:
                raise StreamError("one exec's stream holds two turn.completed records")
            vals = {k: rec["usage"].get(k) for k in tc.USAGE_KEYS}
            if not all(_count(v) for v in vals.values()):
                raise StreamError(f"turn.completed.usage lacks a count for one of {tc.USAGE_KEYS}: unmeasured is "
                                  f"refused, never read as 0")
            extra = sorted(set(rec["usage"]) - set(tc.USAGE_KEYS))
            if extra:
                raise StreamError(f"turn.completed.usage carries key(s) with no entry: {extra}")
            usage = vals
        elif t == tc.ITEM_COMPLETED:
            item = rec["item"]
            if it == tc.AGENT_MESSAGE and item["text"]:
                said.append(item["text"])
            if it in tc.OUTPUT_ITEM_TYPES and (it != tc.AGENT_MESSAGE or item["text"].strip()):
                output = True
            if it in tc.TOOL_ITEM_TYPES:
                tools.append(item["id"])
        elif t == tc.ITEM_STARTED and it in tc.STARTED_ITEM_TYPES:
            output = True                     # pre-freeze review 2, m7: a tool call the agent issued is its output
    if len(set(served)) > 1:
        raise StreamError("one exec's stream reroutes to two different models: the served model is not one")
    return {"thread_ids": thread_ids, "agent_text": "\n".join(said), "agent_output": output, "api_errors": api,
            "usage": usage, "completed": completed, "failed": failed, "tool_ids": tools, "undecoded": bad,
            "served_model": served[0] if served else None}


reroute_of = cn.reroute_of    # (rec, model): `to` for exactly one reroute away from the turn's -m model, else None


def turn_identity(read: dict, *, version: str, mode: dict) -> dict:
    """Codex slice 2: where each pin field of this turn came from. model: the reroute's `to` model (stream-reroute),
    else unobserved; the requested model (the argv's -m, the rollout's turn_context) is never proof of the served one.
    version: `codex --version` in the take container (version-exec). permission_mode: submitted_mode's reading."""
    model = ({"value": read["served_model"], "source": "stream-reroute"} if read["served_model"] is not None
             else {"value": None, "source": aa.UNOBSERVED})
    return {"model": model, "permission_mode": dict(mode), "version": {"value": version, "source": "version-exec"}}


def submitted_mode(journal_path: str, want: dict) -> dict:
    """Codex slice 2: the turn's permission_mode entry, read from the box's launch journal (<stream>.launch.json),
    never from the pin. No journal, a link, or bytes that are not one JSON object holding an argv list: unobserved.
    Otherwise vendor_provenance.launch_facts checks the whole journal against the registered invocation (the argv
    exactly, so no flag can be added or dropped): the pinned mode when it holds, else LAUNCH_DISAGREES, a value that is
    never a mode. Unlike Gemini's reading, no other approval flag is enumerated: exec's shared option list is not in
    the retained source, so exact argv equality is the only admission."""
    try:
        fd = os.open(journal_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return {"value": None, "source": aa.UNOBSERVED}
    try:
        with os.fdopen(fd, "rb") as fh:
            launch = json.loads(fh.read().decode("utf-8"))
    except (ValueError, OSError):
        return {"value": None, "source": aa.UNOBSERVED}
    if not isinstance(launch, dict) or not isinstance(launch.get("argv"), list):
        return {"value": None, "source": aa.UNOBSERVED}
    import vendor_provenance as vp       # imported here: vendor_provenance imports this module
    try:
        vp.launch_facts(launch, want)
    except vp.ProvenanceRefused:
        return {"value": LAUNCH_DISAGREES, "source": "submitted-argv"}
    return {"value": want["mode"], "source": "submitted-argv"}


def _rollout_records(text: str) -> list:
    out = []
    for raw in text.split("\n"):              # lane pf1-l3: "\n" alone (U+2028 and kin sit inside JSON strings)
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            raise StreamError("the rollout holds a line that is not JSON") from None
        if not isinstance(rec, dict):
            raise StreamError("the rollout holds a record that is not an object")
        out.append(rec)
    return out


def read_rollout(text: str, *, seen: int) -> dict:
    """The rollout's per-turn context for the turn that just ran: the turn_context records past the first `seen`.

    turn_contexts  how many turn_context records the rollout holds now (the next turn's `seen`)
    init           {model, permission_mode, version} from this turn's turn_context and the session_meta's
                   cli_version, or None when the turn gained no turn_context or one of the three is not a string.
                   Two turn_contexts in one turn naming different models refuse (StreamError): never one picked.
    why_no_init    the reason init is None (None when it is not)
    """
    recs = _rollout_records(text)
    metas = [r.get("payload") for r in recs if r.get("type") == ROLLOUT_META]
    ctxs = [r.get("payload") for r in recs if r.get("type") == ROLLOUT_TURN]
    new = ctxs[seen:]
    out = {"turn_contexts": len(ctxs), "init": None, "why_no_init": None}
    if not new:
        out["why_no_init"] = "the rollout gained no turn_context during this turn"
        return out
    if not all(isinstance(c, dict) for c in new):
        raise StreamError("a turn_context whose payload is not an object")
    models = {c.get(ROLLOUT_INIT_KEYS["model"]) for c in new}
    if len(models) != 1:
        raise StreamError("one turn's turn_context records name different models")
    ctx = new[-1]
    version = metas[0].get(ROLLOUT_VERSION_KEY) if len(metas) == 1 and isinstance(metas[0], dict) else None
    init = {f: ctx.get(k) for f, k in ROLLOUT_INIT_KEYS.items()}
    init["version"] = version
    if all(isinstance(v, str) and v for v in init.values()):
        out["init"] = init
    else:
        out["why_no_init"] = "the turn_context or the one session_meta lacks a model, approval policy or cli version"
    return out


def argv(line: str, *, model: str, mode: str, session_id, first: bool) -> list:
    """The turn's argv inside the box (O-1..O-4)."""
    for what, v in (("line", line), ("model", model)):
        if not isinstance(v, str) or not v:
            raise StreamError(f"the turn's {what} must be a non-empty string")
    if line.startswith("-"):
        raise StreamError("a line that starts with '-' would be read as a flag")
    if first and line in CODEX_EXEC_COMMANDS:
        raise StreamError("a one-word line that is a `codex exec` subcommand name would run as that subcommand")
    if mode not in MODE_FLAGS:
        raise StreamError(f"no flags pre-registered for mode {mode!r}")
    out = [CLIENT, SUBCOMMAND, JSON_FLAG, MODEL_FLAG, model, *MODE_FLAGS[mode]]
    if not first:
        if not isinstance(session_id, str) or not _THREAD_ID.fullmatch(session_id):
            raise StreamError("a later turn needs the thread id turn 1's stream named")
        out += [RESUME, session_id]
    return out + [line]


def end_reason(exit_code, timed_out: bool, read: dict) -> str:
    """timed-out; end_turn on exit 0 with one turn.completed and no turn.failed; else error."""
    if timed_out:
        return aa.END_TIMED_OUT
    if exit_code == 0 and read["completed"] == 1 and read["failed"] == 0:
        return aa.END_TURN
    return aa.END_ERROR


class CodexAdapter(aa.AgentAdapter):
    """One take's Codex CLI turns in the box.

    runtime          run_take's runtime protocol
    take_id          the take container's recorded id
    run_tree         the take's run tree (the exec's working folder)
    login_file       the login file run_take.read_login reads at exec time (its value never reaches argv)
    model            the row's model
    pin              the take's routing pin: its permission_mode is looked up in MODE_FLAGS (O-3)
    stream_path_for  (n) -> the host-side path turn n's stream is written at
    rollout_for      (n) -> the rollout file's text as copied out host-side after turn n
    counters_for     () -> run_take.counters(cgroup_dir), read host-side
    clock            the injected host clock
    config_folder    run_take.ConfigFolder: B11's record, handed to run_turn with each turn's number (vendor-b11)

    `turn_records` holds, per turn, what the TurnResult has no field for: the exit and timeout, the thread ids, the
    usage, the tool ids, the undecoded line count, why the init is None, and SHAPES_SOURCE.
    """

    name = NAME

    def __init__(self, *, runtime, take_id: str, run_tree: str, login_file: str, model: str, pin: dict,
                 stream_path_for, rollout_for, counters_for, clock, caller_env=None, config_folder=None):
        super().__init__()
        mode = pin.get("permission_mode") if isinstance(pin, dict) else None
        if not isinstance(mode, str) or mode not in MODE_FLAGS:      # PENDING and the empty word are not keys
            raise rt.NotReady(f"the take's routing pin holds no pre-registered Codex mode ({mode!r}): no take runs "
                              f"under a mode nobody pinned")
        for what, fn in (("stream_path_for", stream_path_for), ("rollout_for", rollout_for),
                         ("counters_for", counters_for), ("clock", clock)):
            if not callable(fn):
                raise TypeError(f"{what} must be callable")
        if not isinstance(model, str) or not model:
            raise StreamError("the row's model must be a non-empty string")
        self.runtime, self.take_id, self.run_tree, self.login_file = runtime, take_id, run_tree, login_file
        self.model, self.mode, self.config_folder = model, mode, config_folder
        self.stream_path_for, self.rollout_for = stream_path_for, rollout_for
        self.counters_for, self.clock, self.caller_env = counters_for, clock, caller_env
        self._version = None
        self.thread_id = None
        self._contexts = 0
        self.turn_records: list = []
        self.executed_turns: list = []     # live harness slice 6: each exec as kept before its stream was read

    def version(self) -> str:
        """`codex --version` in the take container, as the agent (a plain exec: no login), parsed; cached."""
        if self._version is None:
            c = self.runtime.run(rt.agent_exec_argv(self.take_id, list(VERSION_ARGV)),
                                 env=rt.runtime_env(self.caller_env), timeout=rt.STEP_TIMEOUT_S)
            m = VERSION_FORM.fullmatch(c.stdout.strip()) if c.returncode == 0 and isinstance(c.stdout, str) else None
            if m is None:
                raise rt.NotReady(f"`codex --version` exited {c.returncode} with no version in its documented form")
            self._version = m.group(1)
        return self._version

    def harness_record(self) -> dict:
        """What this adapter says about itself beside every take: the harness name and where its shapes came from."""
        return {"harness": NAME, "shapes_source": SHAPES_SOURCE}

    def _start(self, take: dict) -> dict:
        return {"container_id": self.take_id}

    def _turn(self, line: str, *, first: bool, budget_s: float) -> aa.TurnResult:
        n = self._turns + 1
        inner = argv(line, model=self.model, mode=self.mode, session_id=self.thread_id, first=first)
        version = self.version()     # Codex slice 2: observed before the exec (cached; a failure here is pre-exec)
        before = self.counters_for()
        got = rt.run_turn(self.runtime, self.take_id, inner, harness=NAME, run_tree=self.run_tree,
                          login_file=self.login_file, stream_path=self.stream_path_for(n), budget_s=budget_s,
                          clock=self.clock, caller_env=self.caller_env, config_folder=self.config_folder, turn=n)
        self.__dict__.setdefault("stderr_seen", []).append(got["stderr"])   # R15-2: EROFS evidence (run_turn: a str)
        after = self.counters_for()
        counters = rt.counter_delta(before, after)
        # Live harness slice 6 (3a's rule): the exec ran, so what the runtime returned is kept before anything of the
        # turn is read; a refusal from here on is an executed turn's (ExecutedStreamRefused), never a turn that did not
        # happen.
        executed = {"n": n, "exit_code": got["exit_code"], "timed_out": got["timed_out"],
                    "started_at": got["started_at"], "ended_at": got["ended_at"], "stream_path": got["stream_path"],
                    "counters": counters, "refused": None}
        self.executed_turns.append(executed)
        try:
            read, ro, init = self._read_turn(got, n, first)
        except (StreamError, OSError, ValueError) as e:
            executed["refused"] = f"{type(e).__name__}: {e}"
            raise ExecutedStreamRefused(str(e), executed=executed) from e
        except Exception as e:  # noqa: BLE001 - review nit: any other failure after the exec is still the exec's
            executed["refused"] = f"{type(e).__name__}: {e}"           # a defect: typed, never a StreamError
            raise aa.ExecutedTurnRefused(executed["refused"], executed=executed) from e
        self.turn_records.append({
            "n": n, "first": first, "exit_code": got["exit_code"], "timed_out": got["timed_out"],
            "thread_ids": read["thread_ids"], "usage": read["usage"], "tool_ids": read["tool_ids"],
            "completed": read["completed"], "failed": read["failed"], "undecoded": read["undecoded"],
            "why_no_init": ro["why_no_init"], "shapes_source": SHAPES_SOURCE,
            "requested_context": init, "served_model": read["served_model"]})
        # Codex slice 2: the rollout's turn_context names the REQUESTED model, never the served one, so it is kept in
        # the turn record (requested_context) and never stands as init; identity carries what was observed.
        return aa.TurnResult(exit_code=got["exit_code"], text=read["agent_text"], stream_path=got["stream_path"],
                             end_reason=end_reason(got["exit_code"], got["timed_out"], read), init=None,
                             api_errors=read["api_errors"], counters=counters,
                             started_at=got["started_at"], ended_at=got["ended_at"],
                             agent_output=read["agent_output"],
                             identity=turn_identity(read, version=version, mode=submitted_mode(
                                 got["stream_path"] + ".launch.json",
                                 {"harness": NAME, "container_id": self.take_id, "model": self.model,
                                  "mode": self.mode, "run_tree": self.run_tree, "stream": got["stream_path"],
                                  "sent": line, "vendor_session_id": "first-turn" if first else self.thread_id,
                                  "ordinal": n})))

    def native_session_path(self, home: str) -> str:
        """Codex slice 3: the rollout this take resumes, under CODEX_HOME `home` (the take's config folder, box
        run_take TAKE_ENV[CODEX]), located by the thread id turn 1's stream named (native_snapshot.codex_rollout_file;
        directory names only)."""
        import native_snapshot
        return native_snapshot.codex_rollout_file(home, self.thread_id)

    def native_session_rel(self, lister) -> str:
        """The same rollout, relative to the config folder, found through the box's one-level listing (drive-wiring
        review MAJOR 1: the driver never opens the agent's config folder during the take)."""
        import native_snapshot
        return native_snapshot.codex_rollout_rel(lister, self.thread_id)

    def _read_turn(self, got: dict, n: int, first: bool) -> tuple:
        """The turn's stream read, its resumed thread checked and its rollout read; raised from here, a refusal is an
        executed turn's (live harness slice 6: _turn keeps the exec first)."""
        with open(got["stream_path"], encoding="utf-8", errors="surrogateescape") as fh:
            read = read_stream(fh.read(), model=self.model)
        if first:
            if len(read["thread_ids"]) == 1:
                self.thread_id = read["thread_ids"][0]
        elif read["thread_ids"] and read["thread_ids"] != [self.thread_id]:
            raise StreamError(f"turn {n} resumed another thread than turn 1's")
        ro = read_rollout(self.rollout_for(n), seen=self._contexts)
        self._contexts = ro["turn_contexts"]
        init = ro["init"]
        return read, ro, init

    def _end(self) -> None:
        """Nothing of the adapter's own to tear down: the driver removes the container by its recorded id."""
