#!/usr/bin/env python3
"""The Gemini CLI adapter for round 4's box, arm G (lane w11b-gemini-adapter; D8 sections 1 and 3, D8:461-472).

`GeminiAdapter` is agent_adapter's interface for `gemini` (run_take.GEMINI): one `docker exec` per turn into the
kept-alive take container (box/run_take.run_turn), the turn's `gemini -p ... -o stream-json` stdout written host-side
at the driver's stream path, and a `TurnResult` read from that stream's harness-side records. It never calls a model
itself: every test drives it on a fake runtime with synthetic streams.

SHAPES_SOURCE. The stream shapes this module reads were first written from the documentation (D8 section 1) and are now
re-tested on streams recorded at walk w-g21 (gemini-cli 0.64.0, both turns) and w-g24 (turn 1, timed out with no result
record), listed in gemini-streams/README.md, against values derived independently with plain json (test R-recorded;
lane vendor-settle stage G's G-legi). The adapter reports the source in its harness record and in every turn record.
Lane vendor-admission T3 (glitch-b5): freeze.py now refuses a design row of this harness (arm G) while SHAPES_SOURCE is
not "recorded" (freeze.unrecorded_shapes_problem); stage V of lane vendor-settle flipped it.

THE ARGV (D8:134-141):

    gemini -p <line> -o stream-json -m <the row's model> <the mode's flags>                   the take's first turn
    gemini -p <line> -o stream-json -m <the row's model> <the mode's flags> -r <session id>   every turn after it

  G-1  `-m <model>` on every call (D8's per-harness table, "Model pin, every turn"; the default `auto` routes between
       models, D8:141).
  G-2  `-r <session id>` after the first turn only. Gemini CLI mints the session id, so it is read from turn 1's
       `init.session_id`. Resuming by id is shown in secondary sources only (D8:138), so a later turn whose init names
       another session is refused: the walk confirms the flag, and this check catches it if it does not hold.
  G-3  The approvals flags are the take's routing pin's permission mode looked up in MODE_FLAGS (D8:139:
       `--approval-mode yolo`); a PENDING, absent or unknown mode refuses the adapter's making. No `--sandbox` flag is
       ever passed: Gemini's own sandbox stays off because the box is the sandbox (D8:139). The pin's word for arm G is
       this lane's ("yolo", the harness's own), Q-w11b-3.
  G-4  A line that starts with "-" is refused (it would be read as a flag); the study's lines never do.

THE RECORDS READ (the tables are transcript_gemini's; see its docstring for which are D8's and which are not):

  stream     every record checked by transcript_gemini.check_record; a record off the tables refuses the turn
             (StreamError), never read on a guess. One init and one result per call at most (a second refuses).
             api_errors   one per `error` event and per result whose status is `error`, in order: {status None, type
                          the event type or the result's error.type, text the harness's own message}. The agent's
                          words (assistant messages) are never an API error.
             agent_output True when an assistant message holds non-blank content or a tool_use exists, read from event
                          types and roles, never from what the words say; an error event is never output.
             stats        result.stats as recorded (transcript_gemini.check_stats: a missing count is refused, never
                          0); a call with no result record has no stats (None, unmeasured).
  model      D8:168: `init.model` and every key of `result.stats.models` are checked against the row's model on every
             turn; one that differs refuses the turn (StreamError). The stream carries no served-model record (D8:166).
  init       the seam's init needs the model, the permission mode and the version (agent_adapter.INIT_FIELDS). The
             Gemini stream records no permission mode, so the TurnResult's init is None on every turn, with its reason
             in the turn record, never filled from the argv the adapter itself passed (Q-w11b-2). The init event's
             model and session id are kept in the turn record.
  exit       0, 1, 42 and 53 (D8:137) are the pre-registered exit codes, each with its meaning in EXIT_MEANINGS; any
             other code from a call that did not time out refuses the turn (StreamError).
  version    `gemini --version`, printed as the bare "X.Y.Z" (this lane's reading, Q-w11b-1); anything else refuses.

end_reason: timed-out when the call timed out; end_turn only on exit 0 with exactly one result whose status is
`success`; error otherwise. Exit 53 (turn limit exceeded) is error, never end_turn, and its meaning
"turn-limit" is kept in the turn record (agent_adapter's END_REASONS hold no turn-limit end).

Not in this lane (named as carried): the PARSERS / harness_bookkeeping / agent_adapter tables, drive.py's admission,
check_take readers, mode_binding expectations, routing markers, per-call cost (price_table is PENDING), the real-box
stub `gemini` (run_take's Gemini billing-route variables are named since 14 Oct, run_take.py:682), and the
freeze's refusal of an arm whose adapter is not re-tested on a recorded stream.

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
import transcript_gemini as tg  # noqa: E402
from box import run_take as rt  # noqa: E402

NAME = rt.GEMINI
CLIENT = "gemini"
PROMPT_FLAG = "-p"
OUTPUT_FLAGS = ("-o", "stream-json")
MODEL_FLAG = "-m"
RESUME_FLAG = "-r"
VERSION_ARGV = (CLIENT, "--version")
VERSION_FORM = re.compile(r"([0-9]+\.[0-9]+\.[0-9]+)")
# The routing pin's permission mode for arm G -> the call's approvals flags (D8:139).
MODE_FLAGS = {"yolo": ("--approval-mode", "yolo")}
# D8:137's exit codes and what each means.
TURN_LIMIT = "turn-limit"
EXIT_MEANINGS = {0: "success", 1: "general-or-api-error", 42: "input-error", 53: TURN_LIMIT}
SHAPES_SOURCE = "recorded"
SHAPES_SOURCES = ("documented", "recorded")
NO_INIT_MODE = "the Gemini stream records no permission mode (Q-w11b-2)"
# A session id: never one of -r's non-id selectors, `latest` in any case or an index (D8:138; W11B-R1-8, w11b-close-1).
_SESSION_ID = re.compile(r"(?!(?i:latest)$)(?![0-9]+$)[A-Za-z0-9][A-Za-z0-9-]{0,127}")
# A model id: box/take_config.py's _MODEL shape, so it can never be read as a flag (W11B-R1-6).
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


class StreamError(ValueError):
    """A stream or exit the reader cannot use as it stands (a typed refusal, never a guess)."""


class ExecutedStreamRefused(aa.ExecutedTurnRefused, StreamError):
    """Live harness 3a: a StreamError raised after the turn's exec ran, carrying what was kept of the exec."""


def read_stream(text: str, *, model: str) -> dict:
    """One call's `-o stream-json` stdout, read for its harness-side records and the agent's words, kept apart.

    init_model    the init event's model, or None when the call has no init
    session_id    the init event's session id, or None when the call has no init
    agent_text    the assistant messages' content: delta chunks joined as they came, messages joined by newlines
                  (graders read it; routing never does)
    agent_output  True when an assistant message holds non-blank content or a tool_use exists
    api_errors    [{status, type, text}] per error event and per failed result, in order
    status        the result's status, or None when the call has no result
    stats         the result's stats as recorded, or None when the call has none
    served_models the keys of result.stats.models, in order ([] when none)
    results       how many result records (0 or 1)
    tool_ids      the tool_use ids, in order
    undecoded     1 when the stream's last non-blank line is not JSON (a cut stream), else 0; a line that is not JSON
                  anywhere before it refuses, so does a stream whose only non-blank line is not JSON (W11B-R2-1: a
                  harness-side stop, Q-w11b-5), and so does a decoded record off the tables

    The stream is split on "\n" only, never str.splitlines: Node writes U+2028 and U+0085 raw inside JSON strings,
    and splitting on them would drop the record that holds them (W11B-R1-1). A stream whose stats name no model and
    whose init is missing refuses: no record would name the model (W11B-R1-3).
    """
    if not isinstance(text, str):
        raise StreamError("the stream must be text")
    if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):
        raise StreamError("the row's model is off the model-id shape")
    init_model, session_id, inits, pieces, output, api = None, None, 0, [], False, []
    status, stats, served, results, tools, bad = None, None, [], 0, [], 0
    joining = False
    lines = [raw for raw in text.split("\n") if raw.strip()]
    for n, raw in enumerate(lines, 1):
        try:
            rec = json.loads(raw)
        except ValueError:
            if n != len(lines) or n == 1:
                raise StreamError(f"line {n} of {len(lines)} is not JSON: only a cut stream's last line may be, and "
                                  f"never its only line (W11B-R2-1)") from None
            bad = 1
            continue
        try:
            t = tg.check_record(rec)
        except tg.ShapeError as e:
            raise StreamError(f"the stream holds a record off the pre-registered tables: {e}") from None
        said = t == tg.MESSAGE and rec["role"] == tg.ASSISTANT
        if not said:
            joining = False
        if t == tg.ERROR:
            api.append({"status": None, "type": t, "text": tg.error_text(rec)})
        elif t == tg.INIT:
            inits += 1
            if inits > 1:
                raise StreamError("one call's stream holds two init records")
            init_model, session_id = rec["model"], rec["session_id"]
            if init_model != model:
                raise StreamError(f"the init names model {init_model!r}, not the row's {model!r}")
            if not _SESSION_ID.fullmatch(session_id):
                raise StreamError("the init carries a session id off its shape")
        elif said:
            if rec.get("delta") is True and joining:
                pieces[-1] += rec["content"]
            else:
                pieces.append(rec["content"])
            joining = rec.get("delta") is True
            if rec["content"].strip():
                output = True
        elif t == tg.TOOL_USE:
            tools.append(rec["tool_id"])
            output = True
        elif t == tg.RESULT:
            results += 1
            if results > 1:
                raise StreamError("one call's stream holds two result records")
            status = rec["status"]
            if status == tg.FAILED:
                api.append({"status": None, "type": rec["error"]["type"] if "error" in rec else None,
                            "text": tg.error_text(rec)})
            if "stats" in rec:
                stats = rec["stats"]
                served = list(stats[tg.STATS_MODELS])
                other = [m for m in served if m != model]
                if other:
                    raise StreamError(f"result.stats.models names {other}, not only the row's {model!r}")
    if stats is not None and not served and init_model is None:
        raise StreamError("the result's stats name no model and the call has no init: no record names the model")
    return {"init_model": init_model, "session_id": session_id, "agent_text": "\n".join(pieces),
            "agent_output": output, "api_errors": api, "status": status, "stats": stats, "served_models": served,
            "results": results, "tool_ids": tools, "undecoded": bad}


def argv(line: str, *, model: str, mode: str, session_id, first: bool) -> list:
    """The call's argv inside the box (G-1..G-4)."""
    if not isinstance(line, str) or not line:
        raise StreamError("the turn's line must be a non-empty string")
    if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):
        raise StreamError("the turn's model is off the model-id shape: it could be read as a flag")
    if line.startswith("-"):
        raise StreamError("a line that starts with '-' would be read as a flag")
    if mode not in MODE_FLAGS:
        raise StreamError(f"no flags pre-registered for mode {mode!r}")
    out = [CLIENT, PROMPT_FLAG, line, *OUTPUT_FLAGS, MODEL_FLAG, model, *MODE_FLAGS[mode]]
    if not first:
        if not isinstance(session_id, str) or not _SESSION_ID.fullmatch(session_id):
            raise StreamError("a later turn needs the session id turn 1's init named")
        out += [RESUME_FLAG, session_id]
    return out


def exit_meaning(exit_code, timed_out: bool):
    """D8:137's meaning of the exit code (None for a timed-out call); any other code refuses."""
    if timed_out:
        return None
    if isinstance(exit_code, bool) or exit_code not in EXIT_MEANINGS:
        raise StreamError(f"exit code {exit_code!r} is not one of the pre-registered {sorted(EXIT_MEANINGS)}")
    return EXIT_MEANINGS[exit_code]


def end_reason(exit_code, timed_out: bool, read: dict) -> str:
    """timed-out; end_turn on exit 0 with a result whose status is success (read_stream refuses a second result);
    else error (exit 53 included)."""
    if timed_out:
        return aa.END_TIMED_OUT
    if exit_code == 0 and read["status"] == tg.SUCCESS:
        return aa.END_TURN
    return aa.END_ERROR


def turn_identity(read: dict, *, version: str, mode: dict) -> dict:
    """Live harness 3b: where each pin field of this turn came from (agent_adapter.IDENTITY_SOURCES), never fabricated
    into init. model: the init event's (stream-init), else the result's single stats.models key (stream-stats; the
    reader already refused any other key), else unobserved. version: `gemini --version` in the take container
    (version-exec). permission_mode: no Gemini record names it; `mode` is submitted_mode's reading of the turn's
    actual-submission journal (submitted-argv), or unobserved when there is none: never the pin echoed back."""
    if read["init_model"] is not None:
        model = {"value": read["init_model"], "source": "stream-init"}
    elif len(read["served_models"]) == 1:
        model = {"value": read["served_models"][0], "source": "stream-stats"}
    else:
        model = {"value": None, "source": aa.UNOBSERVED}
    return {"model": model, "permission_mode": dict(mode),
            "version": {"value": version, "source": "version-exec"}}


# Live harness 3b review fold (finding 1): the mode a turn's actual-submission journal shows. Values that are never a
# pinned mode name an observation that differs, so routing reads a mismatch.
MODE_ABSENT, MODE_CONTRADICTED, LAUNCH_DISAGREES = ("no-mode-flags-submitted", "contradictory-mode-flags",
                                                    "launch-differs-from-registered-invocation")
OTHER_MODE_FLAGS = ("--yolo", "-y", "--approval-mode")


def submitted_mode(journal_path: str, want: dict) -> dict:
    """The turn's permission_mode identity entry, read from the box's journal at <stream>.launch.json (written before
    the exec: schema 1, harness, container_id, argv, cwd, stream, started_at), never from the pin.
    No journal, a link, or bytes that are not one JSON object: unobserved. Otherwise the journal is checked against
    the registered invocation (vendor_provenance.launch_facts with `want`) and its argv read on its own: the mode is the
    pinned mode only when its exact flags occur once and no other approval flag occurs; else a value that is no mode."""
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
    argv = launch["argv"]
    flags = MODE_FLAGS.get(want.get("mode"), ())
    windows = [i for i in range(len(argv) - len(flags) + 1) if flags and tuple(argv[i:i + len(flags)]) == flags]
    approvals = [a for a in argv if a in OTHER_MODE_FLAGS]
    if not windows and not approvals:
        return {"value": MODE_ABSENT, "source": "submitted-argv"}
    if len(windows) != 1 or len(approvals) != 1:
        return {"value": MODE_CONTRADICTED, "source": "submitted-argv"}
    import vendor_provenance as vp       # imported here: vendor_provenance imports this module
    try:
        vp.launch_facts(launch, want)
    except vp.ProvenanceRefused:
        return {"value": LAUNCH_DISAGREES, "source": "submitted-argv"}
    return {"value": want["mode"], "source": "submitted-argv"}


class GeminiAdapter(aa.AgentAdapter):
    """One take's Gemini CLI turns in the box.

    runtime          run_take's runtime protocol
    take_id          the take container's recorded id
    run_tree         the take's run tree (the call's working folder)
    login_file       the login file run_take.read_login reads at exec time (its value never reaches argv)
    model            the row's model
    pin              the take's routing pin: its permission_mode is looked up in MODE_FLAGS (G-3)
    stream_path_for  (n) -> the host-side path turn n's stream is written at
    counters_for     () -> run_take.counters(cgroup_dir), read host-side
    clock            the injected host clock
    config_folder    run_take.ConfigFolder: B11's record, handed to run_turn with each turn's number (vendor-b11)

    `turn_records` holds, per turn, what the TurnResult has no field for: the exit, its meaning and the timeout, the
    init's model and session id, the result's status, stats and served models, the tool ids, the undecoded line
    count, why the init is None, and SHAPES_SOURCE.
    """

    name = NAME

    def __init__(self, *, runtime, take_id: str, run_tree: str, login_file: str, model: str, pin: dict,
                 stream_path_for, counters_for, clock, caller_env=None, config_folder=None):
        super().__init__()
        mode = pin.get("permission_mode") if isinstance(pin, dict) else None
        if not isinstance(mode, str) or mode not in MODE_FLAGS:
            raise rt.NotReady(f"the take's routing pin holds no pre-registered Gemini mode ({mode!r}): no take runs "
                              f"under a mode nobody pinned")
        for what, fn in (("stream_path_for", stream_path_for), ("counters_for", counters_for), ("clock", clock)):
            if not callable(fn):
                raise TypeError(f"{what} must be callable")
        if not isinstance(model, str) or not _MODEL_ID.fullmatch(model):
            raise StreamError("the row's model is off the model-id shape")
        self.runtime, self.take_id, self.run_tree, self.login_file = runtime, take_id, run_tree, login_file
        self.model, self.mode = model, mode
        self.stream_path_for, self.counters_for = stream_path_for, counters_for
        self.clock, self.caller_env, self.config_folder = clock, caller_env, config_folder
        self._version = None
        self.session_id = None
        self.turn_records: list = []
        self.executed_turns: list = []     # live harness 3a: each exec as kept before its stream was read

    def version(self) -> str:
        """`gemini --version` in the take container, as the agent (a plain exec: no login), parsed; cached."""
        if self._version is None:
            c = self.runtime.run(rt.agent_exec_argv(self.take_id, list(VERSION_ARGV)),
                                 env=rt.runtime_env(self.caller_env), timeout=rt.STEP_TIMEOUT_S)
            m = VERSION_FORM.fullmatch((c.stdout or "").strip()) if c.returncode == 0 else None
            if m is None:
                raise rt.NotReady(f"`gemini --version` exited {c.returncode} with no version in its documented form")
            self._version = m.group(1)
        return self._version

    def harness_record(self) -> dict:
        """What this adapter says about itself beside every take: the harness name and where its shapes came from."""
        return {"harness": NAME, "shapes_source": SHAPES_SOURCE}

    def _start(self, take: dict) -> dict:
        return {"container_id": self.take_id}

    def _turn(self, line: str, *, first: bool, budget_s: float) -> aa.TurnResult:
        n = self._turns + 1
        inner = argv(line, model=self.model, mode=self.mode, session_id=self.session_id, first=first)
        version = self.version()     # live harness 3b: observed before the exec (cached; a failure here is pre-exec)
        before = self.counters_for()
        got = rt.run_turn(self.runtime, self.take_id, inner, harness=NAME, run_tree=self.run_tree,
                          login_file=self.login_file, stream_path=self.stream_path_for(n), budget_s=budget_s,
                          clock=self.clock, caller_env=self.caller_env, config_folder=self.config_folder, turn=n)
        self.__dict__.setdefault("stderr_seen", []).append(got["stderr"])   # R15-2: EROFS evidence (run_turn: a str)
        after = self.counters_for()
        counters = rt.counter_delta(before, after)
        # Live harness 3a: the exec ran, so what the runtime returned is kept before anything of the turn is read; a
        # refusal from here on is an executed turn's (ExecutedStreamRefused), never a turn that did not happen.
        executed = {"n": n, "exit_code": got["exit_code"], "timed_out": got["timed_out"],
                    "started_at": got["started_at"], "ended_at": got["ended_at"], "stream_path": got["stream_path"],
                    "counters": counters, "refused": None}
        self.executed_turns.append(executed)
        try:
            meaning, read = self._read_turn(got, n, first)
        except (StreamError, OSError) as e:
            executed["refused"] = f"{type(e).__name__}: {e}"
            raise ExecutedStreamRefused(str(e), executed=executed) from e
        except Exception as e:  # noqa: BLE001 - review nit: any other failure after the exec is still the exec's
            executed["refused"] = f"{type(e).__name__}: {e}"           # a defect: typed, never a StreamError
            raise aa.ExecutedTurnRefused(executed["refused"], executed=executed) from e
        self.turn_records.append({
            "n": n, "first": first, "exit_code": got["exit_code"], "exit_meaning": meaning,
            "timed_out": got["timed_out"], "init_model": read["init_model"], "session_id": read["session_id"],
            "status": read["status"], "stats": read["stats"], "served_models": read["served_models"],
            "tool_ids": read["tool_ids"], "undecoded": read["undecoded"], "why_no_init": NO_INIT_MODE,
            "shapes_source": SHAPES_SOURCE})
        return aa.TurnResult(exit_code=got["exit_code"], text=read["agent_text"], stream_path=got["stream_path"],
                             end_reason=end_reason(got["exit_code"], got["timed_out"], read), init=None,
                             api_errors=read["api_errors"], counters=counters,
                             started_at=got["started_at"], ended_at=got["ended_at"],
                             agent_output=read["agent_output"],
                             identity=turn_identity(read, version=version, mode=submitted_mode(
                                 got["stream_path"] + ".launch.json",
                                 {"harness": NAME, "container_id": self.take_id, "model": self.model,
                                  "mode": self.mode, "run_tree": self.run_tree, "stream": got["stream_path"],
                                  "sent": line, "vendor_session_id": "first-turn" if first else self.session_id,
                                  "ordinal": n})))

    def _read_turn(self, got: dict, n: int, first: bool) -> tuple:
        """The exec's exit meaning and its stream read, and the resumed session checked (G-2); raised from here, a
        refusal is an executed turn's (live harness 3a: _turn keeps the exec first)."""
        meaning = exit_meaning(got["exit_code"], got["timed_out"])
        with open(got["stream_path"], encoding="utf-8", errors="surrogateescape") as fh:
            read = read_stream(fh.read(), model=self.model)
        if first:
            self.session_id = read["session_id"]
        elif read["session_id"] is not None and read["session_id"] != self.session_id:
            raise StreamError(f"turn {n} resumed another session than turn 1's")
        return meaning, read

    def _end(self) -> None:
        """Nothing of the adapter's own to tear down: the driver removes the container by its recorded id."""
        return None

    def native_session_path(self, home: str) -> str:
        """Live harness 3c: the native session file this take resumes, under GEMINI_CLI_HOME `home`, located by the
        session id turn 1's init named (native_snapshot.gemini_session_file; directory names only)."""
        import native_snapshot
        return native_snapshot.gemini_session_file(home, self.session_id)

    def native_session_rel(self, lister) -> str:
        """The same session file, relative to the config folder, found through the box's one-level listing
        (drive-wiring review MAJOR 1: the driver never opens the agent's config folder during the take)."""
        import native_snapshot
        return native_snapshot.gemini_session_rel(lister, self.session_id)


# ---- OD57's read shapes for arm G (lane vendor-b17 round 2, glitch-26's rulings B17-5 to B17-7, 19 Oct 2026) ---------
# They live in box/od57_shapes.py since lane vendor-b24 (B24-2 item 1: one rule set, shared with the aegis door); the
# drive still reads them here (drive.scan_read_shapes reads module.READ_SHAPES).
from box import od57_shapes as _od57_shapes  # noqa: E402
READ_SHAPES = _od57_shapes.GEMINI


# Pre-freeze review 1, m3 (lane L1; placed last so no mutated line moves): the RECORDED fixture SHAPES_SOURCE
# "recorded" rests on. freeze.py's leg i holds it to the committed walk record it was copied from
# (check_take.recorded_binding_problem), so the word alone never opens the leg.
SHAPES_RECORDED_ON = "recorded-gemini-w-g21/transcript.jsonl"
