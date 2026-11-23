#!/usr/bin/env python3
"""The harness-neutral transcript view: the only way a grader reads an agent's words and tool calls.

Interface 8 (glitch-f3's in-spec ruling, 6 Oct 2026): round 4 will later run agents other than Claude
Code, and their adapters must slot in with no change to graders, tasks or the manifest shape. So a
grader never reads a harness's raw records, record types, tool names or argument keys. It reads
`AgentEvent`s, whose event kinds and tool kinds are this module's own closed vocabulary, and a new
harness adds one parser to `PARSERS` and nothing else. This module is one of the three that hold a
table keyed by `AgentAdapter.name` (with `agent_adapter.py` and `harness_bookkeeping.py`); it is not
under `graders/`.

THE EVENT. One closed record per event:

    AgentEvent(turn, kind, text, tool, args, call)

    kind        one of KINDS:
                  agent-text       the agent's words
                  agent-reasoning  the agent's own reasoning blocks (Claude Code's thinking)
                  tool-call        a call the agent made; `tool` and `args` set, `call` view-assigned
                  tool-result      what came back; the same `call` and the same `tool` as its call
                  operator         a line the operator sent; each one starts the next turn
                  harness          everything else the harness writes: attachments, system and
                                   bookkeeping records, hook output, task notifications
    turn        turn k is the k-th operator line of the take, counting from 1; events before the
                first operator line are turn 0. Never a ledger's `n`, which repeats on a recovery
                turn (16 of round 3's 54 ledgers).
    text        the words, for every kind but tool-call (None there). For harness events it is the
                record's payload strings joined by newlines (None when it holds none).
    tool        one of TOOL_KINDS, never a harness's own tool name, on tool-call and tool-result only
    args        on tool-call only, exactly:
                  shell              {"command": str, "background": bool}
                  read, write, edit  {"path": str}
                  search             {"pattern": str, "path": str | None}
                  other              {}
    call        the view's own call number (1, 2, ...) on tool-call and tool-result only

THE PARSER TABLE. `PARSERS` is keyed by `AgentAdapter.name`. Its only entry is `claude-code`. Each
parser turns one raw line into `RawItem`s through its own pre-registered tables (record types,
block types, tool names and argument keys); the view assembles items into events, numbers turns and
calls, pairs every result with its call, and checks the args' shape. An unknown harness, record
type, block type, tool name or argument key is refused (`ViewError`), never guessed, and no table
here defaults to `claude-code`.

THE `claude-code` PARSER reads Claude Code's SESSION-FILE transcript: round 3's `transcript.jsonl`,
the session JSONL the driver copies from Claude Code's projects folder (record types such as `user`,
`assistant`, `attachment`, `queue-operation`). It does NOT read the `--output-format stream-json`
stdout the host captures per turn; that is another format. If round 4 grades from the host-captured
stream, CP2 adds that parser to this table, and that change touches no grader. Its tables were built
from round 3's 54 committed transcripts at e2979b31 (record types, block types, attachment types and
tool names as they occur there), plus three entries this lane added on the brief's words: `system`
records (the brief names "system ... records" as harness), and the `Grep` and `Glob` tools (the
brief's `search` kind). A tool's allowed argument keys are the ones round 3 used plus Claude Code's
documented inputs for that tool; any other key refuses the take.

    an operator line   a `user` record whose content is a string and which has no `origin`
    harness            a `user` record whose `origin.kind` is `task-notification` (round 3 holds 9,
                       two with `promptSource` `sdk`); a `user` record with any other origin is
                       refused. An `attachment` of type `queued_command` whose `commandMode` is not
                       `task-notification` is refused (round 3's 9 are all notifications). Every
                       other attachment type in CC_ATTACHMENT_TYPES, and every record type in
                       CC_HARNESS_PAYLOAD, is harness.
    a record with `isSidechain` true (a sub-agent's) is refused: the view reads the main thread only.
    a record the harness wrote itself is refused, never read as the agent's or the operator's words
    (review round 1, W2B1-6): one carrying an `isMeta` or `isApiErrorMessage` key, whatever its value
    (round 3's 54 transcripts carry neither on any of their 6,208 records), and an `assistant` record
    whose `message.model` is `<synthetic>` (round 3 has none).
    ONE isMeta record is admitted, as harness (glitch-6b's ruling, 15 Oct 2026, on CP6 walk w006): a
    `scheduled-wakeup`, the agent's own ScheduleWakeup prompt re-delivered by the harness, when
    is_scheduled_wakeup holds: type `user`, isMeta the boolean true, turnOrigin `scheduled`,
    promptSource `system`, no `origin`, no isApiErrorMessage, not a sidechain, string content equal to
    the `prompt` of an EARLIER ScheduleWakeup call in a genuine main-thread agent record that no
    earlier admitted wakeup has consumed (ScheduledWakeups: each call arms its prompt once; a wakeup
    consumes the earliest equal one). Its raw type is `user:scheduled-wakeup`. Every other isMeta
    record is refused as before. check_take.user_text_records imports the same predicate.
    A SECOND isMeta record is admitted, as harness (glitch-b5's ruling 3, 16 Oct 2026, on CP6 walk w053): the
    no-visible-output nudge, when is_no_output_nudge holds: type `user`, isMeta and turnCompanion the boolean true,
    string content equal to CC_NO_OUTPUT_NUDGE_TEXT byte for byte, no origin, no isApiErrorMessage, not a sidechain.
    Its raw type is `user:no-visible-output-nudge`; it never starts a turn.

THE RAW FIELDS THE `claude-code` PARSER READS (interface 6; a closed list):

    every record      type, isSidechain, isMeta, isApiErrorMessage (either key present refuses it, but for
                      a scheduled wakeup)
    user              message.content (a string, or a list of blocks), origin.kind; for a scheduled wakeup
                      also turnOrigin, promptSource and the presence of origin
      tool_result     type, tool_use_id, content (a string, or a list of blocks:
                      text -> text; tool_reference -> tool_name)
    assistant         message.model (`<synthetic>` refuses it), message.content (a list of blocks)
      text            type, text
      thinking        type, thinking
      tool_use        type, id, name, input (its keys checked against CC_TOOLS; the values read are
                      the ones CC_TOOLS maps: command, run_in_background, file_path, pattern, path;
                      and ScheduleWakeup's prompt, which only arms a scheduled wakeup)
    attachment        attachment.type, attachment.commandMode, and attachment's other string leaves (text);
                      for auto_mode (item H), its closed flags and steer, and the record's rendered[0].content (text);
                      for edited_text_file (ruling 1, w041), exactly filename and snippet (the snippet is the text)
    queue-operation   content          last-prompt   lastPrompt        ai-title   aiTitle
    atis-latch        atis             mode          mode              cost-state modelUsage
    system            content

THE FUNCTIONS.

    events(harness, path_or_lines)          the take's events, in order; refuses an unknown harness
    harness_types(harness, path_or_lines)   {raw type: count} of the records mapped to `harness`;
                                            an attachment's raw type is `attachment:<its type>`, a task
                                            notification's is `user:task-notification`. Only the
                                            awareness furniture check calls it; no grader imports it.
    operator_lines(evs)                     the operator lines' text, in order
    require_operator_lines(evs, sent)       refuses a take whose operator lines are not `sent`, in order
                                            (the replay binds a take to its ledger's turns[].sent)

ROUND 3'S HARNESS. Round 3's takes carry no `agent` field (each `driver-ledger.json` has
`claude_version` and no harness name), so ROUND3_HARNESS names it once, here, beside the table. The
replay and the furniture check take the harness from it; no grader types the string.

THE MANIFEST KEYS. Interface 8: wherever a take's `model` is recorded, `agent` is recorded beside it, as
{"harness": AgentAdapter.name, "version": AgentAdapter.version()}. MANIFEST_KEYS names those four words
once. They are the manifest's words, not a harness's, so the source sweep of `graders/*.py` excludes
them even where one is also a raw name (`model` is a Claude Code attachment type) (review round 1,
W2B1-7): a grader that records a take's model and agent never trips it.

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import collections.abc
import contextvars
import json
from dataclasses import dataclass
from pathlib import Path

# ---- the view's closed vocabulary ---------------------------------------------------------------

AGENT_TEXT = "agent-text"
AGENT_REASONING = "agent-reasoning"
TOOL_CALL = "tool-call"
TOOL_RESULT = "tool-result"
OPERATOR = "operator"
HARNESS = "harness"
KINDS = (AGENT_TEXT, AGENT_REASONING, TOOL_CALL, TOOL_RESULT, OPERATOR, HARNESS)

SHELL = "shell"
READ = "read"
WRITE = "write"
EDIT = "edit"
SEARCH = "search"
OTHER = "other"
# glitch-b5's ruling on the d7107255 battery (16 Oct 2026): a call that hands work to a sub-agent (Claude Code's Agent)
# is its own kind, so a grader can tell it apart. Its sub-agent's own tool calls, words and results are not in these
# events (the checker reads them from the turn stream and the copied subagents files): a grader whose label reads the
# agent's tool calls or words refuses a take with one (DELEGATED_REFUSAL), never grading the main thread alone.
DELEGATE = "delegate"
TOOL_KINDS = (SHELL, READ, WRITE, EDIT, SEARCH, OTHER, DELEGATE)

# The view's own argument names per tool kind, and each one's type (None allowed only where listed).
ARG_SHAPES = {
    SHELL: {"command": (str,), "background": (bool,)},
    READ: {"path": (str,)},
    WRITE: {"path": (str,)},
    EDIT: {"path": (str,)},
    SEARCH: {"pattern": (str,), "path": (str, type(None))},
    OTHER: {},
    DELEGATE: {},
}
# Every word above, once: the view's vocabulary (a grader may use these; it never uses a raw name).
VOCABULARY = frozenset(KINDS + TOOL_KINDS + tuple(k for shape in ARG_SHAPES.values() for k in shape))


DELEGATED_REFUSAL = ("delegated-work: the take hands work to a sub-agent (a delegate call), whose own tool calls, words "
                     "and results are not in the view; this grader's label reads them, so the take is refused, never "
                     "graded on the main thread alone")


def delegated_calls(evs) -> list:
    """The events' calls that hand work to a sub-agent (kind DELEGATE), in order."""
    return [e for e in evs if e.kind == TOOL_CALL and e.tool == DELEGATE]


class ViewError(ValueError):
    """The view refuses a transcript: an unknown harness, record, block, tool or key, or a broken pairing."""


@dataclass(frozen=True)
class AgentEvent:
    turn: int
    kind: str
    text: str | None
    tool: str | None
    args: dict | None
    call: int | None


@dataclass(frozen=True)
class RawItem:
    """What a parser hands the view for one event: `raw_type` is the harness's own type name (read only by
    harness_types), `ref` the harness's own call id (read only to pair a result with its call)."""
    raw_type: str
    kind: str
    text: str | None = None
    tool: str | None = None
    args: dict | None = None
    ref: str | None = None


def map_tool(table: dict, name, raw_args) -> tuple[str, dict]:
    """Map a harness's tool name and arguments onto a view tool kind and the view's args, by `table`:
    {tool name: (kind, {raw key: view arg}, allowed raw keys)}. Refuses a name with no entry and a raw key
    the entry does not allow. A view arg the map does not fill takes its default (background False, path None)."""
    if not isinstance(name, str) or name not in table:
        raise ViewError(f"tool name with no entry in the parser's table: {name!r}")
    if not isinstance(raw_args, dict):
        raise ViewError(f"tool {name!r}: arguments are not an object")
    kind, keymap, allowed = table[name]
    unknown = sorted(set(raw_args) - set(allowed))
    if unknown:
        raise ViewError(f"tool {name!r}: argument keys with no entry: {unknown}")
    args = {}
    for raw_key, view_key in keymap.items():
        if raw_key in raw_args:
            args[view_key] = raw_args[raw_key]
    shape = ARG_SHAPES[kind]
    if kind == SHELL:
        args.setdefault("background", False)
    if kind == SEARCH:
        args.setdefault("path", None)
    for key, types in shape.items():
        if key not in args:
            raise ViewError(f"tool {name!r}: required argument for {kind} missing")
        if not isinstance(args[key], types) or (bool not in types and isinstance(args[key], bool)):
            raise ViewError(f"tool {name!r}: argument {key} of the wrong type")
    return kind, args


def _strings(o) -> list[str]:
    """Every string value under `o`, depth first, in order (keys are not values)."""
    if isinstance(o, str):
        return [o]
    if isinstance(o, dict):
        return [s for v in o.values() for s in _strings(v)]
    if isinstance(o, list):
        return [s for v in o for s in _strings(v)]
    return []


def _joined(o) -> str | None:
    parts = _strings(o)
    return "\n".join(parts) if parts else None


# ---- the claude-code parser (Claude Code's session-file transcript) -----------------------------

CC_TOOLS = {
    # name: (view kind, {raw key: view arg}, allowed raw keys)
    "Bash": (SHELL, {"command": "command", "run_in_background": "background"},
             ("command", "run_in_background", "description", "timeout", "dangerouslyDisableSandbox")),
    "Read": (READ, {"file_path": "path"}, ("file_path", "limit", "offset", "pages")),
    "Write": (WRITE, {"file_path": "path"}, ("file_path", "content")),
    "Edit": (EDIT, {"file_path": "path"}, ("file_path", "old_string", "new_string", "replace_all")),
    "Grep": (SEARCH, {"pattern": "pattern", "path": "path"},
             ("pattern", "path", "glob", "type", "output_mode", "-i", "-n", "-A", "-B", "-C", "context",
              "head_limit", "offset", "multiline")),
    "Glob": (SEARCH, {"pattern": "pattern", "path": "path"}, ("pattern", "path")),
    "ScheduleWakeup": (OTHER, {}, ("delaySeconds", "reason", "prompt", "noop", "stop")),
    "ToolSearch": (OTHER, {}, ("query", "max_results")),
    "Monitor": (OTHER, {}, ("process_id",)),
    # glitch-b5's ruling (16 Oct 2026, option 1, parity; CP6 walk w083): round 3 offered Agent in 64 of 64 transcripts
    # and never called it. Its input keys are the 2.1.296 schema's, closed (the Agent tool's zod object and its
    # extensions; cwd is omitted from the schema the model sees, so it refuses). Its sub-agent's own records are read
    # from the turn stream and the copied subagents files by the checker, never by this view.
    "Agent": (DELEGATE, {}, ("description", "prompt", "subagent_type", "model", "effort", "run_in_background", "name",
                          "team_name", "mode", "isolation")),
}
CC_ASSISTANT_BLOCKS = ("text", "thinking", "tool_use")
CC_USER_BLOCKS = ("tool_result",)
CC_RESULT_BLOCKS = ("text", "tool_reference")
CC_ATTACHMENT_TYPES = (
    "agent_listing_delta", "date", "deferred_tools_delta", "deferred_tools_record", "environment",
    "instructions", "model", "nested_memory", "prompt_snapshot", "queued_command", "remote_session_change",
    "session_context", "skill_listing", "task_reminder", "total_tokens_reminder", "auto_mode", "edited_text_file")
# Item H (glitch-6b, 15 Oct 2026; CP6 walk w032, claude-opus-5-5, held): 2.1.296's auto_mode attachment, a NAMED
# DEPARTURE from round 3 (whose 54 graded transcripts never carry it; one round-3 walk, not a take, does:
# walks/template-adherence/1 at e2979b31, claude-sonnet-5 at 2.1.267 in permission mode auto, every flag false, its
# rendered text auto mode's own notice, not the bash-first steer). Under bypassPermissions the binary emits it only when
# its bash-first gate holds (a model cohort, or CLAUDE_CODE_THRIFTY_SONIC), and renders it into the model's context as
# "While bypass permissions mode is active:" and a bash-first steer; so it is harness furniture the agent SEES, read
# with its rendered text (the record's `rendered`, one {content}) as the event's text. Its shape is closed: exactly
# these keys, booleans, and a steer from CC_AUTO_MODE_STEERS present exactly when bashFirst is true.
CC_AUTO_MODE = "auto_mode"
CC_AUTO_MODE_FLAGS = ("autoModeConsentFlow", "bashFirst", "steerOnly", "bypass")
CC_AUTO_MODE_STEERS = ("strict", "relaxed")
# glitch-6b's ruling 1 (15 Oct 2026; CP6 walk w041, held): 2.1.296's edited_text_file attachment, a NAMED DEPARTURE from
# round 3 (whose 64 transcripts at e2979b31 never carry it). Each query's changed_files pass runs over the files the
# agent has read whole; a file whose mtime is later than the read and whose content differs yields exactly {type,
# filename, snippet}, whoever wrote it (in w041 the agent's own background job), rendered to the model as a steer to
# take the change as the current state. No targeted switch exists (CLAUDE_CODE_DISABLE_ATTACHMENTS would drop round-3
# kinds); lane-reports/attachment-vocabulary-20261016/edited-text-file-trigger-20261015.json. Read as harness furniture:
# the snippet is the event's text, never the agent's or the operator's words. Closed shape: exactly these keys, the
# filename a non-empty string, the snippet a string (empty past the binary's snippet budget).
CC_EDITED_TEXT_FILE = "edited_text_file"
CC_EDITED_TEXT_FILE_KEYS = ("type", "filename", "snippet")
# Harness-only record types and the payload field whose strings are the event's text.
CC_HARNESS_PAYLOAD = {
    "queue-operation": "content", "last-prompt": "lastPrompt", "ai-title": "aiTitle", "atis-latch": "atis",
    "mode": "mode", "cost-state": "modelUsage", "system": "content"}
CC_RECORD_TYPES = ("user", "assistant", "attachment") + tuple(CC_HARNESS_PAYLOAD)
CC_TASK_NOTIFICATION = "task-notification"
CC_QUEUED_COMMAND = "queued_command"
# Records the harness wrote itself (W2B1-6): either key present, whatever its value, refuses the record; so does an
# assistant record whose model is CC_SYNTHETIC_MODEL. Round 3's 54 transcripts hold none of them.
CC_REFUSED_FLAGS = ("isMeta", "isApiErrorMessage")
CC_SYNTHETIC_MODEL = "<synthetic>"
# glitch-6b's ruling, 15 Oct 2026 (CP6 walk w006): the one harness-written isMeta record admitted, as harness. At
# 2.1.296 `claude -p` stays alive after the agent's ScheduleWakeup and the harness re-delivers the agent's own prompt
# as a user record (w006 transcript line 111: isMeta true, turnOrigin "scheduled", promptSource "system", no origin,
# content byte-equal to the call's prompt, sha256 c50d1115aaef...). Round 3 never carried one.
CC_SCHEDULED_WAKEUP = "scheduled-wakeup"
CC_WAKEUP_TOOL = "ScheduleWakeup"
CC_WAKEUP_TURN_ORIGIN = "scheduled"
CC_WAKEUP_PROMPT_SOURCE = "system"
CC_WAKEUP_ABSENT_KEYS = ("isApiErrorMessage",)
# glitch-b5's ruling 3 (16 Oct 2026; CP6 walk w053, Haiku, held on transcript line 107): the second isMeta record
# admitted, as harness, a NAMED DEPARTURE from round 3 (whose 64 transcripts carry no isMeta record). When a model
# response ends with end_turn or stop_sequence, is not an API error and carries no text block with visible text, the
# 2.1.296 query loop (offset 224269128; the string at 207900138) writes a user record {isMeta: true, turnCompanion:
# true} whose content is exactly CC_NO_OUTPUT_NUDGE_TEXT and asks the model again; at most once per model round, the
# guard reset after each tool round; no env or setting gates it. 2.1.267 and 2.1.280 carry the same path. Admitted
# by is_no_output_nudge alone: type user, isMeta the boolean true, turnCompanion the boolean true, string content
# equal to the text byte for byte, no origin, no isApiErrorMessage, not a sidechain. Its raw type is
# `user:no-visible-output-nudge`. Every other isMeta record is refused as before.
CC_NO_OUTPUT_NUDGE = "no-visible-output-nudge"
CC_NO_OUTPUT_NUDGE_TEXT = ("[Your previous response had no visible output. Please continue and produce a user-visible "
                           "response.]")


def _genuine_agent_record(rec) -> bool:
    """A main-thread agent record: an assistant record no refusal applies to (no isMeta, no isApiErrorMessage, not a
    sidechain, not <synthetic>). Only such a record's ScheduleWakeup call arms a wakeup."""
    if not isinstance(rec, dict) or rec.get("type") != "assistant" or rec.get("isSidechain") is True:
        return False
    if any(flag in rec for flag in ("isMeta", "isApiErrorMessage")):
        return False
    msg = rec.get("message")
    return isinstance(msg, dict) and msg.get("model") != CC_SYNTHETIC_MODEL


def wakeup_calls(rec) -> list:
    """(tool_use id, prompt) of the ScheduleWakeup calls in one genuine agent record, in order (string ids and
    prompts only)."""
    out = []
    if not _genuine_agent_record(rec):
        return out
    content = rec["message"].get("content")
    for b in content if isinstance(content, list) else []:
        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == CC_WAKEUP_TOOL:
            prompt = b.get("input").get("prompt") if isinstance(b.get("input"), dict) else None
            if isinstance(prompt, str) and isinstance(b.get("id"), str):
                out.append((b["id"], prompt))
    return out


def _genuine_result_record(rec) -> bool:
    """A main-thread user record no refusal applies to (no isMeta, no isApiErrorMessage, not a sidechain)."""
    return (isinstance(rec, dict) and rec.get("type") == "user" and rec.get("isSidechain") is not True
            and not any(flag in rec for flag in ("isMeta", "isApiErrorMessage")))


def tool_results(rec) -> list:
    """(tool_use_id, is_error) of the tool_result blocks of one genuine user record, in order (review F's NIT: only
    such a record's result arms a wakeup)."""
    if not _genuine_result_record(rec):
        return []
    msg = rec.get("message") if isinstance(rec, dict) and rec.get("type") == "user" else None
    content = msg.get("content") if isinstance(msg, dict) else None
    return [(b.get("tool_use_id"), b.get("is_error") is True) for b in content if isinstance(b, dict)
            and b.get("type") == "tool_result"] if isinstance(content, list) else []


def is_no_output_nudge(rec) -> bool:
    """glitch-b5's ruling 3: the 2.1.296 no-visible-output nudge, exactly; shared by check_take's record reader."""
    if not (isinstance(rec, dict) and rec.get("type") == "user" and rec.get("isMeta") is True
            and rec.get("turnCompanion") is True):
        return False
    if rec.get("isSidechain") is True or any(k in rec for k in ("isApiErrorMessage", "origin")):
        return False
    msg = rec.get("message")
    return isinstance(msg, dict) and msg.get("content") == CC_NO_OUTPUT_NUDGE_TEXT      # only a str equals it (JSON)


def is_scheduled_wakeup(rec, armed) -> bool:
    """The ruling's predicate, every clause required: a user record, isMeta the boolean True, turnOrigin "scheduled",
    promptSource "system", no origin key, no isApiErrorMessage key, not a sidechain, string content, and that content
    equal to a prompt in `armed` (the unconsumed prompts of earlier ScheduleWakeup calls, ScheduledWakeups.armed)."""
    if not isinstance(rec, dict) or rec.get("type") != "user":
        return False
    if rec.get("isMeta") is not True:
        return False
    if rec.get("turnOrigin") != CC_WAKEUP_TURN_ORIGIN:
        return False
    if rec.get("promptSource") != CC_WAKEUP_PROMPT_SOURCE:
        return False
    if "origin" in rec:
        return False
    if any(k in rec for k in CC_WAKEUP_ABSENT_KEYS):
        return False
    if rec.get("isSidechain") is True:
        return False
    msg = rec.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, str):
        return False
    return content in armed


# The current reading pass's ScheduledWakeups (view._items sets it; None outside a pass).
_PASS_WAKEUPS = contextvars.ContextVar("_PASS_WAKEUPS", default=None)


class ScheduledWakeups:
    """One reading pass's armed prompts. note(rec) reads every record that is not an admitted wakeup: a genuine agent
    record's ScheduleWakeup call waits for its result; a non-error tool_result for that call's id arms its prompt
    (review F, 15 Oct 2026: an errored call scheduled nothing). Each tool_use id arms at most once, so a record a
    --resume transcript repeats with the same id arms nothing more. admit(rec) is is_scheduled_wakeup, and when it
    holds the record consumes the earliest armed equal prompt, so one call admits at most one wakeup (two calls with
    one prompt admit two). Both readers make one per pass."""

    def __init__(self):
        self.armed: list = []
        self.waiting: dict = {}             # tool_use id -> prompt, the call's result not yet read
        self.done: set = set()              # ids whose result was read (armed, or errored)

    def note(self, rec) -> None:
        for ref, prompt in wakeup_calls(rec):
            if ref not in self.done and ref not in self.waiting:
                self.waiting[ref] = prompt
        for ref, errored in tool_results(rec):
            if ref in self.waiting:
                prompt = self.waiting.pop(ref)
                self.done.add(ref)
                if not errored:
                    self.armed.append(prompt)

    def admit(self, rec) -> bool:
        if not is_scheduled_wakeup(rec, self.armed):
            return False
        self.armed.remove(rec["message"]["content"])
        return True


class ClaudeCodeSessionParser:
    """Claude Code's session-file transcript (never the stream-json stdout), one JSON record per line."""

    record_types = CC_RECORD_TYPES
    block_types = tuple(dict.fromkeys(CC_ASSISTANT_BLOCKS + CC_USER_BLOCKS + CC_RESULT_BLOCKS))
    attachment_types = CC_ATTACHMENT_TYPES
    tools = CC_TOOLS

    def items(self, line: str) -> list[RawItem]:
        """One line's items. The pass's ScheduledWakeups is _PASS_WAKEUPS (view._items sets one per pass); a line read
        outside a pass has none, so no wakeup can be admitted and every isMeta record is refused."""
        wakeups = _PASS_WAKEUPS.get()
        try:
            r = json.loads(line)
        except ValueError:
            raise ViewError("a line that is not JSON") from None
        if not isinstance(r, dict):
            raise ViewError("a record that is not an object")
        t = r.get("type")
        if t not in CC_RECORD_TYPES:
            raise ViewError(f"unknown record type: {t!r}")
        if r.get("isSidechain") is True:
            raise ViewError("a sidechain record (a sub-agent's): the view reads the main thread only")
        flagged = [flag for flag in CC_REFUSED_FLAGS if flag in r]
        if flagged and wakeups is not None and wakeups.admit(r):
            return [RawItem("user:" + CC_SCHEDULED_WAKEUP, HARNESS, text=r["message"]["content"])]
        if flagged and is_no_output_nudge(r):
            return [RawItem("user:" + CC_NO_OUTPUT_NUDGE, HARNESS, text=r["message"]["content"])]
        for flag in flagged:
            raise ViewError(f"a record carrying {flag}: the harness wrote it itself, refused")
        if t == "user":
            got = self._user(r)
            if wakeups is not None:
                wakeups.note(r)
            return got
        if t == "assistant":
            got = self._assistant(r)
            if wakeups is not None:
                wakeups.note(r)
            return got
        if t == "attachment":
            return self._attachment(r)
        return [RawItem(t, HARNESS, text=_joined(r.get(CC_HARNESS_PAYLOAD[t])))]

    def _user(self, r) -> list[RawItem]:
        msg = r.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, str):
            if "origin" not in r:
                return [RawItem("user", OPERATOR, text=content)]
            origin = r["origin"]
            if isinstance(origin, dict) and origin.get("kind") == CC_TASK_NOTIFICATION:
                return [RawItem("user:" + CC_TASK_NOTIFICATION, HARNESS, text=content)]
            raise ViewError(f"a user record with an unknown origin: {origin!r}")
        if not isinstance(content, list) or not content:
            raise ViewError("a user record whose content is neither a string nor a list of blocks")
        out = []
        for b in content:
            bt = b.get("type") if isinstance(b, dict) else None
            if bt not in CC_USER_BLOCKS:
                raise ViewError(f"unknown block type in a user record: {bt!r}")
            ref = b.get("tool_use_id")
            if not isinstance(ref, str):
                raise ViewError("a tool result without a tool_use_id")
            out.append(RawItem("user", TOOL_RESULT, text=self._result_text(b.get("content")), ref=ref))
        return out

    @staticmethod
    def _result_text(c) -> str:
        if isinstance(c, str):
            return c
        if not isinstance(c, list):
            raise ViewError("a tool result whose content is neither a string nor a list of blocks")
        parts = []
        for x in c:
            xt = x.get("type") if isinstance(x, dict) else None
            if xt not in CC_RESULT_BLOCKS:
                raise ViewError(f"unknown block type in a tool result: {xt!r}")
            v = x.get("text") if xt == "text" else x.get("tool_name")
            if not isinstance(v, str):
                raise ViewError(f"a {xt} block without its string")
            parts.append(v)
        return "\n".join(parts)

    def _assistant(self, r) -> list[RawItem]:
        msg = r.get("message")
        if isinstance(msg, dict) and msg.get("model") == CC_SYNTHETIC_MODEL:
            raise ViewError("an assistant record whose model is <synthetic>: the harness wrote it itself, refused")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            raise ViewError("an assistant record whose content is not a list of blocks")
        out = []
        for b in content:
            bt = b.get("type") if isinstance(b, dict) else None
            if bt not in CC_ASSISTANT_BLOCKS:
                raise ViewError(f"unknown block type in an assistant record: {bt!r}")
            if bt == "text":
                if not isinstance(b.get("text"), str):
                    raise ViewError("a text block without its string")
                out.append(RawItem("assistant", AGENT_TEXT, text=b["text"]))
            elif bt == "thinking":
                if not isinstance(b.get("thinking"), str):
                    raise ViewError("a thinking block without its string")
                out.append(RawItem("assistant", AGENT_REASONING, text=b["thinking"]))
            else:
                if not isinstance(b.get("id"), str):
                    raise ViewError("a tool call without an id")
                kind, args = map_tool(CC_TOOLS, b.get("name"), b.get("input"))
                out.append(RawItem("assistant", TOOL_CALL, tool=kind, args=args, ref=b["id"]))
        return out

    @staticmethod
    def _auto_mode(r, a) -> list[RawItem]:
        return _auto_mode_item(r, a)

    def _attachment(self, r) -> list[RawItem]:
        a = r.get("attachment")
        at = a.get("type") if isinstance(a, dict) else None
        if at not in CC_ATTACHMENT_TYPES:
            raise ViewError(f"unknown attachment type: {at!r}")
        if at == CC_QUEUED_COMMAND and a.get("commandMode") != CC_TASK_NOTIFICATION:
            raise ViewError(f"a queued command that is not a task notification: {a.get('commandMode')!r}")
        if at == CC_AUTO_MODE:
            return self._auto_mode(r, a)
        if at == CC_EDITED_TEXT_FILE:
            return _edited_text_file_item(a)
        return [RawItem("attachment:" + at, HARNESS, text=_joined({k: v for k, v in a.items() if k != "type"}))]


def _auto_mode_item(r, a) -> list:
    """Item H: an auto_mode attachment of the closed shape, read with its rendered text; anything else refuses."""
    want = {"type", *CC_AUTO_MODE_FLAGS} | ({"bashFirstSteer"} if a.get("bashFirst") is True else set())
    if set(a) != want:
        raise ViewError(f"an auto_mode attachment whose keys are not exactly {sorted(want)}")
    if not all(type(a[k]) is bool for k in CC_AUTO_MODE_FLAGS):
        raise ViewError("an auto_mode attachment with a flag that is not a boolean")
    if a["bashFirst"] is True and a.get("bashFirstSteer") not in CC_AUTO_MODE_STEERS:
        raise ViewError(f"an auto_mode steer outside {list(CC_AUTO_MODE_STEERS)}")
    rendered = r.get("rendered")
    if not (isinstance(rendered, list) and len(rendered) == 1 and isinstance(rendered[0], dict)
            and set(rendered[0]) == {"content"} and isinstance(rendered[0]["content"], str)):
        raise ViewError("an auto_mode attachment whose rendered text is not one {content: str}")
    return [RawItem("attachment:" + CC_AUTO_MODE, HARNESS, text=rendered[0]["content"])]


def _edited_text_file_item(a) -> list:
    """glitch-6b's ruling 1: an edited_text_file attachment of the closed shape, its snippet the harness event's text;
    anything else refuses."""
    if set(a) != set(CC_EDITED_TEXT_FILE_KEYS):
        raise ViewError(f"an edited_text_file attachment whose keys are not exactly {sorted(CC_EDITED_TEXT_FILE_KEYS)}")
    if type(a["filename"]) is not str or not a["filename"]:
        raise ViewError("an edited_text_file attachment whose filename is not a non-empty string")
    if type(a["snippet"]) is not str:
        raise ViewError("an edited_text_file attachment whose snippet is not a string")
    return [RawItem("attachment:" + CC_EDITED_TEXT_FILE, HARNESS, text=a["snippet"])]


def is_edited_text_file(a) -> bool:
    """glitch-b5's ruling 2 (16 Oct 2026): whether an attachment is an edited_text_file of exactly the admitted closed
    shape (the reader's own clauses), so check_take leaves only such a record's snippet out of its leak sweep."""
    if not (isinstance(a, dict) and a.get("type") == CC_EDITED_TEXT_FILE):
        return False
    try:
        _edited_text_file_item(a)
    except ViewError:
        return False
    return True


class VendorBoundParser:
    """The published vendor road requires a ledger-bound file, not loose lines."""
    def __init__(self, harness):
        self.harness = harness

    def bound_items(self, path):
        from vendor_record_binding import bound_items
        return bound_items(self.harness, path)


PARSERS = {"claude-code": ClaudeCodeSessionParser(),
           "codex": VendorBoundParser("codex"), "gemini": VendorBoundParser("gemini")}

# Round 3's takes carry no harness name; this is the one place it is written.
ROUND3_HARNESS = "claude-code"

# Interface 8's manifest keys: `model`, and `agent` = {"harness": ..., "version": ...} beside it (W2B1-7).
MANIFEST_KEYS = ("model", "agent", "harness", "version")


# ---- the bound transcript (the review of item E, MAJOR; glitch-6b's ruling, 15 Oct 2026) ----------------

class BoundLine(str):
    """One line of a BoundTranscript: the line's own text (a str, equal to it in every way a grader reads), which also
    names the transcript it was read from. A grader that copies the lines (plan_gate's take_events hands the view
    list(transcript); its code is pinned to its base) still hands the view lines that say where they came from."""

    def __new__(cls, text, owner):
        line = super().__new__(cls, text)
        line.__dict__["owner"] = owner
        return line

    def __setattr__(self, name, value):
        raise AttributeError("a BoundLine is immutable")


class BoundTranscript(collections.abc.Sequence):
    """One take's transcript as BOTH contracts take it: an immutable sequence of the file's lines (read_text(utf-8)
    split by jsonl_lines, on newline only, the bytes the graders were always handed) that also carries its `.path`, which the vendor binding
    (vendor_record_binding.bound_items) needs to read the envelope's ledger and native streams beside it. It is not a
    str, bytes or os.PathLike, so a grader's guard against a bare path still refuses one; bound_items re-reads `.path`
    and refuses when its lines are not the carried ones, so one value never carries two transcripts. Each line is a
    BoundLine naming this transcript, so a copy of the whole sequence, in order, binds the same way (of())."""

    __slots__ = ("_path", "_lines")

    def __init__(self, path):
        p = Path(path)
        object.__setattr__(self, "_path", p)
        object.__setattr__(self, "_lines", tuple(BoundLine(x, self)
                                                 for x in jsonl_lines(p.read_text(encoding="utf-8"))))

    @classmethod
    def of(cls, value):
        """The BoundTranscript `value` is, or whose every line, all of them, in order and by identity, `value` holds
        (a grader's copy); None for anything else (a plain list of strings is never bound)."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, (list, tuple)) or not value or not isinstance(value[0], BoundLine):
            return None
        owner = value[0].owner
        if len(value) != len(owner._lines) or any(a is not b for a, b in zip(value, owner._lines)):
            return None
        return owner

    def __setattr__(self, name, value):
        raise AttributeError("a BoundTranscript is immutable")

    @property
    def path(self) -> Path:
        return self._path

    @property
    def lines(self) -> tuple:
        return self._lines

    def __getitem__(self, i):
        return self._lines[i]

    def __len__(self) -> int:
        return len(self._lines)

    def __repr__(self) -> str:
        return f"BoundTranscript({len(self._lines)} lines)"


# ---- the view ------------------------------------------------------------------------------------

def _parser(harness):
    if not isinstance(harness, str) or harness not in PARSERS:
        raise ViewError(f"unknown harness: {harness!r} (the parser table holds {sorted(PARSERS)})")
    return PARSERS[harness]


def jsonl_lines(text: str) -> list[str]:
    """A JSONL file's records: split on "\\n" alone (review r7: str.splitlines also splits on U+2028, U+2029, \\x85 and
    others, which JSON strings carry raw), the empty piece after the final newline dropped."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _lines(path_or_lines) -> list[str]:
    if isinstance(path_or_lines, (str, Path)):
        lines = jsonl_lines(Path(path_or_lines).read_text(encoding="utf-8"))
    else:
        lines = list(path_or_lines)
    for i, ln in enumerate(lines, 1):
        if not isinstance(ln, str):
            raise ViewError(f"line {i} is not a string")
        if not ln.strip():
            raise ViewError(f"line {i} is blank")
    return lines


def _items(harness, path_or_lines) -> list[RawItem]:
    parser = _parser(harness)
    if isinstance(parser, VendorBoundParser):
        return parser.bound_items(path_or_lines)
    out = []
    token = _PASS_WAKEUPS.set(ScheduledWakeups())     # one pass, one set of armed prompts (the scheduled-wakeup kind)
    try:
        for i, ln in enumerate(_lines(path_or_lines), 1):
            try:
                got = parser.items(ln)
            except ViewError as e:
                raise ViewError(f"line {i}: {e}") from None
            for it in got:
                if not isinstance(it, RawItem) or it.kind not in KINDS:
                    raise ViewError(f"line {i}: the parser produced an item outside the view's kinds")
            out.extend(got)
    finally:
        _PASS_WAKEUPS.reset(token)
    return out


def _check_args(tool, args):
    if tool not in TOOL_KINDS:
        raise ViewError(f"a tool kind outside the view's: {tool!r}")
    shape = ARG_SHAPES[tool]
    if not isinstance(args, dict) or set(args) != set(shape):
        raise ViewError(f"{tool} args are not exactly {sorted(shape)}")
    for k, types in shape.items():
        if not isinstance(args[k], types) or (bool not in types and isinstance(args[k], bool)):
            raise ViewError(f"{tool} arg {k} of the wrong type")


def events(harness, path_or_lines) -> list[AgentEvent]:
    """Every event of one take, in order. Refuses an unknown harness and anything its parser refuses."""
    turn = 0
    calls: dict[str, tuple[int, str]] = {}
    answered: set[str] = set()
    out = []
    for it in _items(harness, path_or_lines):
        if it.kind == OPERATOR:
            if not isinstance(it.text, str):
                raise ViewError("an operator line without its text")
            turn += 1
            out.append(AgentEvent(turn, OPERATOR, it.text, None, None, None))
        elif it.kind == TOOL_CALL:
            _check_args(it.tool, it.args)
            if not isinstance(it.ref, str) or it.ref in calls:
                raise ViewError(f"a tool call whose id is missing or repeated: {it.ref!r}")
            n = len(calls) + 1
            calls[it.ref] = (n, it.tool)
            out.append(AgentEvent(turn, TOOL_CALL, None, it.tool, dict(it.args), n))
        elif it.kind == TOOL_RESULT:
            if it.ref not in calls:
                raise ViewError(f"a tool result for no call: {it.ref!r}")
            if it.ref in answered:
                raise ViewError(f"a second tool result for one call: {it.ref!r}")
            answered.add(it.ref)
            n, tool = calls[it.ref]
            out.append(AgentEvent(turn, TOOL_RESULT, it.text, tool, None, n))
        else:
            if it.text is not None and not isinstance(it.text, str):
                raise ViewError(f"a {it.kind} event whose text is not a string")
            if it.kind in (AGENT_TEXT, AGENT_REASONING) and it.text is None:
                raise ViewError(f"a {it.kind} event without its text")
            out.append(AgentEvent(turn, it.kind, it.text, None, None, None))
    return out


def raw_items(harness, path_or_lines) -> list[RawItem]:
    """Every RawItem of one take in one reading pass (item G, glitch-6b 15 Oct 2026: a scheduled wakeup resolves only
    against the ScheduleWakeup call and result before it, so a reader that needs each item's raw type reads the whole
    file here, never a line alone). Refuses whatever the parser refuses."""
    return _items(harness, path_or_lines)


def harness_types(harness, path_or_lines) -> dict[str, int]:
    """{raw type: count} of the records this harness's parser mapped to `harness` events."""
    counts: dict[str, int] = {}
    for it in _items(harness, path_or_lines):
        if it.kind == HARNESS:
            counts[it.raw_type] = counts.get(it.raw_type, 0) + 1
    return counts


def operator_lines(evs) -> list[str]:
    return [e.text for e in evs if e.kind == OPERATOR]


def require_operator_lines(evs, sent) -> None:
    """Refuse a take whose operator lines are not exactly `sent`, in order (a ledger's turns[].sent)."""
    got = operator_lines(evs)
    if got != list(sent):
        raise ViewError(f"the take's {len(got)} operator line(s) are not the ledger's {len(list(sent))} sent "
                        "line(s), in order")
