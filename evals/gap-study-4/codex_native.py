"""Codex CLI 0.162.1 native rollout reader candidate and `codex exec --json` stream join: unregistered, fail closed.

Every name below comes from the pinned source the rollout audit retained, blob-verified against commit
092d3acd6bec3e3a14bdc7e7a2810ab628ab759d (/Users/javrodher/aegis-builds/gap4-codex-rollout-audit-20261014/src/), cited
as codex-rs/<path>:<line>. The audit is research input; each cited line was re-read in the retained copy.

Rollout (native JSONL), the initial supported subset:
  - one JSON object per LF-framed line (rollout/src/recorder.rs:2079-2086: timestamp, ordinal?, then the flattened
    item with its `type` and `payload`); a line that does not decode ABORTS the read. Upstream skips such lines with a
    warning (recorder.rs:1120-1146); this reader never does.
  - the first record is session_meta, with cli_version "0.162.1" (protocol/src/protocol.rs SessionMeta) and
    history_mode "paginated" (exec asks for paginated history, exec/src/lib.rs:1461). Legacy history, fork history (a
    later session_meta) and the line types this subset does not project are refused, never guessed.
  - every line carries an ordinal, contiguous and increasing by one (rollout/src/ordinal.rs:15-50).
  - line types: ROLLOUT_TYPES (history/src/rollout_payload.rs:30-70); event_msg types: the ones the paginated policy
    persists (rollout/src/policy.rs:132-139); legacy-only and never-persisted ones refuse (policy.rs:141-208), which
    would mean another writer; response_item types: the persisted ones (policy.rs:80-98), anything else would be serde
    `Other` and refuses.
  - turns: event_msg task_started opens, task_complete or turn_aborted with the same turn_id closes
    (protocol.rs:1423-1434, 1544); an open turn at the end is incomplete; an item of another turn refuses.
  - item_completed items, TurnItem PascalCase tags (protocol/src/items.rs:46-78): UserMessage (one `text` input,
    protocol/src/user_input.rs:16-26), AgentMessage (its Text parts concatenated, items.rs:125-127), Reasoning (summary
    joined by newline) and CommandExecution (items.rs:244-281) are projected; every other tag refuses in this subset.
  - aggregated_output keeps the persistence truncation marker (policy.rs:17-19) and is flagged `truncated`.
  - turn_context: the requested model and cwd; approval_policy and sandbox_policy values are placeholders the audit
    did not verify, so they are carried raw and never accepted (permission_mode stays None).
Exec stream: EXEC_EVENTS and EXEC_ITEMS (exec/src/exec_events.rs:9-37, 120-133). The stream holds no user prompt and
no model-facing tool result; its item ids are synthetic (`item_<n>`) and are never matched; command text is a
presentation string and is not compared. A model reroute is an error item "model rerouted: <from> -> <to> (...)"
(exec/src/event_processor_with_jsonl_output.rs:494-507), the only served-model evidence; without it the served model is
unknown. An interrupted turn emits no terminal event and exits 1 (event_processor_with_jsonl_output.rs:559-563; exec/src/lib.rs:1341-1358 per the audit).
"""
from __future__ import annotations

import json
import re

PINNED_CLI = "0.162.1"
ROLLOUT_TYPES = ("session_meta", "response_item", "inter_agent_communication", "inter_agent_communication_metadata",
                 "compacted", "turn_context", "token_usage_record", "world_state", "retained_context",
                 "security_risk_score", "event_msg", "realtime_item")
SUPPORTED_ROLLOUT_TYPES = ("session_meta", "turn_context", "event_msg", "response_item", "token_usage_record")
PAGINATED_EVENTS = ("item_completed", "token_count", "thread_goal_updated", "thread_rolled_back", "turn_aborted",
                    "task_started", "task_complete", "thread_settings_applied")
SUPPORTED_EVENTS = ("item_completed", "token_count", "turn_aborted", "task_started", "task_complete")
LEGACY_ONLY_EVENTS = ("user_message", "agent_message", "agent_reasoning", "agent_reasoning_raw_content",
                      "entered_review_mode", "exited_review_mode", "patch_apply_end", "context_compacted",
                      "mcp_tool_call_end", "web_search_end", "image_generation_end", "sub_agent_activity")
NEVER_PERSISTED_EVENTS = ("error", "warning", "stream_error", "model_reroute", "model_verification",
                          "session_configured", "exec_command_begin", "exec_command_end", "raw_response_item")
RESPONSE_ITEMS = ("additional_tools", "message", "agent_message", "reasoning", "local_shell_call", "function_call",
                  "tool_search_call", "function_call_output", "tool_search_output", "custom_tool_call",
                  "custom_tool_call_output", "web_search_call", "image_generation_call", "configuration_update",
                  "compaction", "compaction_summary", "context_compaction")
TURN_ITEMS = ("UserMessage", "FunctionCallOutput", "HookPrompt", "AgentMessage", "Plan", "Reasoning",
              "CommandExecution", "DynamicToolCall", "CollabAgentToolCall", "SubAgentActivity", "WebSearch", "ImageView",
              "Extension", "ImageGeneration", "EnteredReviewMode", "ExitedReviewMode", "FileChange", "McpToolCall",
              "ContextCompaction")
PROJECTED_ITEMS = ("UserMessage", "AgentMessage", "Reasoning", "CommandExecution")
EXEC_EVENTS = ("thread.started", "turn.started", "turn.completed", "turn.failed", "item.started", "item.updated",
               "item.completed", "error")
EXEC_ITEMS = ("agent_message", "reasoning", "command_execution", "file_change", "mcp_tool_call", "collab_tool_call",
              "web_search", "todo_list", "error")
PROJECTED_EXEC_ITEMS = ("agent_message", "reasoning", "command_execution", "error")
TRUNCATION_MARKER = "\n... command output truncated for persistence ...\n"
_REROUTE = re.compile(r"model rerouted: (.+?) -> (.+?) \(")
LINE_KEYS = {"timestamp", "ordinal", "type", "payload", "metadata"}


class ReaderRefused(ValueError):
    """The rollout is outside the reviewed subset, or not the pinned writer's."""


class JoinRefused(ValueError):
    """The exec stream and the rollout turn disagree, or the stream is outside the reviewed subset."""


def _json_lines(raw, error):
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeError:
            raise error("not UTF-8") from None
    out = []
    for n, text in enumerate(raw.split("\n"), 1):
        if not text.strip():
            continue

        def pairs(items):
            d = {}
            for k, v in items:
                if k in d:
                    raise error(f"line {n}: duplicate key {k!r}")
                d[k] = v
            return d
        try:
            rec = json.loads(text, object_pairs_hook=pairs)
        except ValueError:
            raise error(f"line {n} does not decode (upstream would skip it; this reader aborts)") from None
        if not isinstance(rec, dict):
            raise error(f"line {n} is not a JSON object")
        out.append(rec)
    return out


def _text_input(content):
    if (not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict)
            or content[0].get("type") != "text" or not isinstance(content[0].get("text"), str)):
        raise ReaderRefused("a UserMessage must hold one text input in this subset")
    return content[0]["text"]


def _item(item, turn):
    kind = item.get("type") if isinstance(item, dict) else None
    if kind not in TURN_ITEMS:
        raise ReaderRefused(f"TurnItem tag {kind!r} is not in the pinned TurnItem enum")
    if kind not in PROJECTED_ITEMS:
        raise ReaderRefused(f"TurnItem {kind!r} is unsupported in this subset")
    if kind == "UserMessage":
        if turn["sent"] is not None:
            raise ReaderRefused("a turn holds two UserMessage items")
        turn["sent"] = _text_input(item.get("content"))
    elif kind == "AgentMessage":
        parts = item.get("content")
        if not isinstance(parts, list) or not all(isinstance(p, dict) and set(p) == {"type", "text"}
                                                  and p["type"] == "Text" and isinstance(p["text"], str) for p in parts):
            raise ReaderRefused("an AgentMessage holds only Text parts")
        turn["output"].append({"kind": "agent-text", "text": "".join(p["text"] for p in parts)})
    elif kind == "Reasoning":
        summary = item.get("summary_text")
        if not isinstance(summary, list) or not all(isinstance(s, str) for s in summary):
            raise ReaderRefused("a Reasoning item's summary_text is a list of strings")
        if summary:
            turn["output"].append({"kind": "reasoning", "text": "\n".join(summary)})
    else:
        out = item.get("aggregated_output")
        if not (out is None or isinstance(out, str)) or not isinstance(item.get("status"), str) \
                or not isinstance(item.get("command"), list):
            raise ReaderRefused("a CommandExecution item is off its pinned shape")
        exit_code = item.get("exit_code")
        if not (exit_code is None or (isinstance(exit_code, int) and not isinstance(exit_code, bool))):
            raise ReaderRefused("a CommandExecution exit_code is an int or absent")
        turn["output"].append({"kind": "command", "status": item["status"], "exit_code": exit_code, "output": out,
                               "truncated": isinstance(out, str) and TRUNCATION_MARKER in out})


def read_rollout(raw) -> dict:
    """{session_id, version, turns: [{turn_id, terminal, sent, requested_model, cwd, output, error}]}, or refused."""
    records = _json_lines(raw, ReaderRefused)
    if not records:
        raise ReaderRefused("the rollout is empty")
    expected = None
    for n, rec in enumerate(records, 1):
        unknown = set(rec) - LINE_KEYS
        if unknown:
            raise ReaderRefused(f"line {n}: unknown key(s) {sorted(unknown)}")
        if not isinstance(rec.get("timestamp"), str) or "payload" not in rec:
            raise ReaderRefused(f"line {n}: a rollout line carries a timestamp and a payload")
        if rec.get("type") not in ROLLOUT_TYPES:
            raise ReaderRefused(f"line {n}: rollout line type {rec.get('type')!r} is not a pinned RolloutItem")
        if "metadata" in rec and rec["type"] != "response_item":
            raise ReaderRefused(f"line {n}: only a response_item carries metadata")
        ordinal = rec.get("ordinal")
        if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0 or (
                expected is not None and ordinal != expected):
            raise ReaderRefused(f"line {n}: the ordinal is missing or not contiguous")
        expected = ordinal + 1
    meta = records[0]
    if meta["type"] != "session_meta":
        raise ReaderRefused("the first record must be session_meta")
    pay = meta["payload"]
    if not isinstance(pay, dict) or pay.get("cli_version") != PINNED_CLI:
        raise ReaderRefused(f"session_meta cli_version is not the pinned {PINNED_CLI}")
    if pay.get("history_mode") != "paginated":
        raise ReaderRefused("history_mode is not paginated: legacy history is refused in this subset")
    session_id = pay.get("id")
    if not isinstance(session_id, str) or not session_id:
        raise ReaderRefused("session_meta carries no thread id")
    turns, current = [], None
    for n, rec in enumerate(records[1:], 2):
        t, pay = rec["type"], rec["payload"]
        if t not in SUPPORTED_ROLLOUT_TYPES or t == "session_meta":
            raise ReaderRefused(f"line {n}: rollout line type {t!r} is unsupported in this subset")
        if not isinstance(pay, dict):
            raise ReaderRefused(f"line {n}: the payload is not an object")
        if t == "response_item":
            if pay.get("type") not in RESPONSE_ITEMS:
                raise ReaderRefused(f"line {n}: response_item {pay.get('type')!r} would be serde Other")
            continue
        if t == "token_usage_record":
            continue
        if t == "turn_context":
            if current is None or pay.get("turn_id", current["turn_id"]) != current["turn_id"]:
                raise ReaderRefused(f"line {n}: a turn_context outside its open turn")
            if not isinstance(pay.get("model"), str) or not pay["model"] or not isinstance(pay.get("cwd"), str):
                raise ReaderRefused(f"line {n}: a turn_context carries a model and a cwd")
            current["requested_model"], current["cwd"] = pay["model"], pay["cwd"]
            continue
        kind = pay.get("type")
        if kind in NEVER_PERSISTED_EVENTS:
            raise ReaderRefused(f"line {n}: event {kind!r} is never persisted by the pinned writer")
        if kind in LEGACY_ONLY_EVENTS:
            raise ReaderRefused(f"line {n}: event {kind!r} is persisted only in legacy history")
        if kind not in PAGINATED_EVENTS:
            raise ReaderRefused(f"line {n}: event {kind!r} is not one the pinned paginated policy persists")
        if kind not in SUPPORTED_EVENTS:
            raise ReaderRefused(f"line {n}: event {kind!r} is unsupported in this subset")
        if kind == "task_started":
            if current is not None:
                raise ReaderRefused(f"line {n}: a turn opens before the previous one closes")
            current = {"turn_id": pay.get("turn_id"), "terminal": "incomplete", "sent": None,
                       "requested_model": None, "cwd": None, "output": [], "error": None}
            if not isinstance(current["turn_id"], str) or not current["turn_id"]:
                raise ReaderRefused(f"line {n}: task_started carries no turn_id")
            turns.append(current)
        elif kind in ("task_complete", "turn_aborted"):
            if current is None or pay.get("turn_id") != current["turn_id"]:
                raise ReaderRefused(f"line {n}: {kind} closes no open turn")
            if kind == "turn_aborted":
                current["terminal"], current["error"] = "aborted", pay.get("reason")
            else:
                current["terminal"] = "failed" if pay.get("error") is not None else "complete"
                current["error"] = pay.get("error")
            current = None
        elif kind == "item_completed":
            if current is None or pay.get("turn_id") != current["turn_id"]:
                raise ReaderRefused(f"line {n}: an item belongs to turn {pay.get('turn_id')!r}, not the open turn")
            if pay.get("thread_id") != session_id:
                raise ReaderRefused(f"line {n}: an item names another thread")
            _item(pay.get("item"), current)
    for turn in turns:
        if turn["sent"] is None:
            raise ReaderRefused(f"turn {turn['turn_id']} holds no UserMessage")
    return {"session_id": session_id, "version": PINNED_CLI, "turns": turns}


def project(raw) -> list:
    """vendor_provenance's fact schema, one per turn. permission_mode stays None (unverified enum spellings)."""
    got = read_rollout(raw)
    return [{"session_id": got["session_id"], "requested_model": t["requested_model"], "version": got["version"],
             "cwd": t["cwd"], "permission_mode": None, "sent": t["sent"], "output": [dict(o) for o in t["output"]]}
            for t in got["turns"]]


def read_exec(text) -> dict:
    """One `codex exec --json` call: thread id, items in order, errors, served-model evidence, terminal."""
    records = _json_lines(text, JoinRefused)
    if not records or records[0].get("type") != "thread.started":
        raise JoinRefused("the exec stream must begin with thread.started")
    thread, items, errors, served, terminal, started = None, [], [], None, None, 0
    for n, rec in enumerate(records, 1):
        t = rec.get("type")
        if t not in EXEC_EVENTS:
            raise JoinRefused(f"exec line {n}: event {t!r} is not a pinned ThreadEvent")
        if terminal is not None:
            raise JoinRefused(f"exec line {n} comes after the terminal event")
        if t == "thread.started":
            if thread is not None:
                raise JoinRefused("two thread.started events")
            thread = rec.get("thread_id")
        elif t == "turn.started":
            started += 1
        elif t in ("turn.completed", "turn.failed"):
            terminal = "complete" if t == "turn.completed" else "failed"
        elif t == "error":
            errors.append(rec.get("message"))
        else:
            item = rec.get("item")
            kind = item.get("type") if isinstance(item, dict) else None
            if kind not in EXEC_ITEMS:
                raise JoinRefused(f"exec line {n}: item {kind!r} is not a pinned ThreadItem")
            if kind not in PROJECTED_EXEC_ITEMS:
                raise JoinRefused(f"exec line {n}: item {kind!r} is unsupported in this subset")
            if t != "item.completed":
                continue
            if kind == "error":
                m = _REROUTE.match(item.get("message") or "")
                if m:
                    served = m.group(2)
                else:
                    errors.append(item.get("message"))
            else:
                items.append(item)
    if started != 1:
        raise JoinRefused(f"an exec call holds {started} turn.started events, not one")
    return {"thread_id": thread, "items": items, "errors": errors, "served_model": served, "terminal": terminal}


def _output_agrees(native, shown) -> bool:
    if native is None:
        return shown == ""
    if TRUNCATION_MARKER in native:
        head, _, tail = native.partition(TRUNCATION_MARKER)
        return shown.startswith(head) and shown.endswith(tail) and len(shown) >= len(head) + len(tail)
    return native == shown


def join(turn: dict, exec_text: str, *, exit_code, session_id: str) -> dict:
    """One rollout turn (read_rollout) joined to its exec call's stream, by order and type, never by exec ids."""
    call = read_exec(exec_text)
    if call["thread_id"] != session_id:
        raise JoinRefused("the exec thread is not the rollout's thread")
    native = [o for o in turn["output"]]
    shown_text = [i["text"] for i in call["items"] if i["type"] == "agent_message"]
    if shown_text != [o["text"] for o in native if o["kind"] == "agent-text"]:
        raise JoinRefused("agent text disagrees")
    if [i["text"] for i in call["items"] if i["type"] == "reasoning"] != [o["text"] for o in native
                                                                          if o["kind"] == "reasoning"]:
        raise JoinRefused("reasoning summary disagrees")
    shown_cmds = [i for i in call["items"] if i["type"] == "command_execution"]
    native_cmds = [o for o in native if o["kind"] == "command"]
    if len(shown_cmds) != len(native_cmds):
        raise JoinRefused("command count disagrees")
    for s, nat in zip(shown_cmds, native_cmds):
        if s.get("status") != nat["status"] or s.get("exit_code") != nat["exit_code"]:
            raise JoinRefused("command status or exit code disagrees")
        if not _output_agrees(nat["output"], s.get("aggregated_output")):
            raise JoinRefused("command output disagrees")
    shown = call["terminal"]
    if shown is None and exit_code == 0:
        raise JoinRefused("no terminal event with exit 0: the call is incomplete")
    native_end = turn["terminal"]
    agrees = ((native_end == "complete" and shown == "complete") or (native_end == "failed" and shown == "failed")
              or (native_end == "aborted" and shown is None and exit_code == 1)
              or (native_end == "incomplete" and shown is None))
    if not agrees:
        raise JoinRefused(f"terminal disagrees: rollout {native_end}, exec {shown}, exit {exit_code}")
    return {"complete": native_end == "complete" and shown == "complete", "terminal": native_end,
            "served_model": call["served_model"], "agent_texts": shown_text, "commands": len(shown_cmds),
            "truncated": any(n["truncated"] for n in native_cmds),
            "command_text": "presentation-derived, not compared"}
