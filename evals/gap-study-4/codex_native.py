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
  - FileChange (lane vendor-b23, glitch-26's rulings Q1 to Q4, Tue 20 Oct 2026; lane-reports/vendor-b23-DESIGN.md,
    read at the pin 092d3acd): a patch's completed item, written by emit_patch_end with status, stdout and stderr set
    and auto_approved None (core/src/tools/events.rs:599-619; protocol/src/items.rs:411-426, None fields skipped),
    persisted unchanged by paginated history (rollout/src/policy.rs:249, 280; its started item is never persisted,
    :201, 211). Its keys are exactly FILE_CHANGE_KEYS, status one of FILE_CHANGE_STATUSES (protocol.rs:3764-3770), and
    changes a non-empty map from the source path to {type add or delete, content} or {type update, unified_diff,
    move_path} (protocol.rs:4228-4240; core/src/apply_patch.rs:64-90; delete since lane pf1-codex-fcdelete, w-o76).
    It is projected as {kind "file_change", status, changes [{path, kind, move_path}] sorted by path}, the order exec
    prints them in (app-server-protocol/src/protocol/item_builders.rs:342-353). move_path is a rename's target, which
    the exec stream never prints (event_processor_with_jsonl_output.rs:194): check_take's T-8 reader holds such a take.
  - aggregated_output is kept as written; `marker_text` says only that the persistence marker's text occurs in it
    (policy.rs:17-19), which an agent can print too, so it is never read as proof that the writer truncated.
  - a blank or whitespace-only line anywhere but after the last record refuses (the writer frames every line as one
    JSON object, recorder.rs:2079-2086; upstream's reader skips blank lines, recorder.rs:1116; this one is stricter).
  - a Reasoning item whose summary joins to whitespace only refuses: exec drops it from its stream
    (exec/src/event_processor_with_jsonl_output.rs:152-156, 354-356), so no join could ever prove it.
  - one late shape (lane pf1-codex-turnitem, glitch-45's brief of Tue 27 Oct 2026; arm O walk w-o69, its
    native-turn-4.jsonl ordinals 142-143): a CommandExecution of a turn completing AFTER that turn's task_complete.
    The pinned writer (openai/codex 092d3acd) keeps a unified-exec process alive past its turn
    (core/src/unified_exec/process_manager.rs:596-597; core/tests/suite/unified_exec.rs:2835-2928, "expected unified
    exec process to remain alive after turn completion", then Op::Shutdown); its exit watcher is a detached task
    holding the STARTING turn (core/src/unified_exec/async_watcher.rs:158-180, turn_ref at :171) that emits the end
    with source UnifiedExecStartup (:224, :367) and exit -1 when no code was read (:213), and emit_exec_end writes it
    as that turn's item_completed (core/src/tools/events.rs:561-588); exec's shutdown terminates every such process
    after the TurnComplete was sent (core/src/tasks/mod.rs:847-861; core/src/session/handlers.rs:290-312). Admitted
    only: directly after the turn's task_complete (or another admitted late item), naming that turn and this thread, a
    CommandExecution with source "unified_exec_startup" and a non-empty process_id, an id not already completed in the
    turn, started inside the turn (started_at_ms within task_complete's started_at..completed_at seconds) and
    completed no earlier than it started. It is shape-checked like an in-turn command and kept in the turn's
    `after_complete`, never in `output`: the exec stream ends at turn.completed with it started and never completed,
    so join pairs each with an unfinished stream start; check_take's reach reads it like every CommandExecution line.

Known false-refusal risks, for the first recorded pair to confirm (review nit N11; never admitted unseen): a
whitespace-only Reasoning summary (above); a turn_aborted whose turn_id is null (TurnAbortedEvent.turn_id is
Option<String>); a FileChange carrying auto_approved, a non-UTF-8 path (the stream's lossy string then differs from
the key) or two hunks naming one file (lane vendor-b23); and the line types the paginated policy persists but this subset refuses,
retained_context, security_risk_score, compacted, inter_agent_communication, inter_agent_communication_metadata and
realtime_item: if a plain exec session writes any of them, every rollout of it refuses. Lane pf1-codex-turnitem: a
background command completing after a turn_aborted (the writer keeps the process alive past an interrupt too,
unified_exec.rs:3015), or after a later turn has opened, or after any other line has followed the task_complete,
refuses like every other out-of-order item.

Lane vendor-b25 (glitch-26's ruling 1, Wed 21 Oct 2026; the first recorded pair: all 38 committed arm-O walks write
both): two records are admitted on closed shapes and carry NO fact into the projection.
  - world_state, a RolloutItem line (history/src/rollout_payload.rs:57-59, persisted by policy.rs:45): its payload is
    WorldStateItem, exactly {full: bool, state: object} (protocol/src/protocol.rs:3302-3307; state is a
    Map<String, Value>, so its keys are open by the pinned type: the module that fills it,
    core/src/context/world_state/, is named in the audit's tree listing but not retained, and nothing here reads it).
    Admitted only inside an open turn, where every recorded one sits (turn 1, before its turn_context).
  - event_msg thread_settings_applied (protocol.rs:1429, persisted by policy.rs:139): ThreadSettingsAppliedEvent
    {thread_id, thread_settings} (protocol.rs:2228-2236), thread_id required here and equal to session_meta's id
    (it is Option only for older histories); thread_settings is ThreadSettingsSnapshot (protocol.rs:2238-2267), its
    keys exactly TSA_REQUIRED plus any of TSA_OPTIONAL, each value on the type _thread_settings checks (cited there).
    Admitted only between turns, where every recorded one sits (two per resume).

Command output in the join (review finding 3): the writer truncates aggregated_output only when it exceeds
PERSISTED_COMMAND_OUTPUT_MAX_BYTES (64 KiB, policy.rs:16-17, 250-258), through codex_utils_string::
truncate_middle_with_marker (retained since the audit's Addendum A: codex-rs/utils/string/src/truncate.rs:20-33,
156-159, 177-183), reimplemented here in UTF-8 bytes. An exec output over 64 KiB joins only when the rollout holds
exactly that truncation of it; every other output must equal the rollout's exactly, the marker's text compared as
ordinary text.
  - turn_context: the requested model and cwd; approval_policy and sandbox_policy values are placeholders the audit
    did not verify, so they are carried raw and never accepted (permission_mode stays None).
Exec stream: EXEC_EVENTS and EXEC_ITEMS (exec/src/exec_events.rs:9-37, 120-133). The stream holds no user prompt and
no model-facing tool result; its item ids are synthetic (`item_<n>`) and are never matched; command text is a
presentation string and is not compared. A model reroute is an error item "model rerouted: <from> -> <to> (...)"
(exec/src/event_processor_with_jsonl_output.rs:494-507), the only served-model evidence; without it the served model is
unknown. An interrupted turn emits no terminal event and exits 1 (event_processor_with_jsonl_output.rs:559-563; exec/src/lib.rs:1341-1358 per the audit).
A completed file_change (lane vendor-b23) joins the rollout turn's FileChange by order, as commands do: equal counts,
equal paths and kinds, and its status completed for completed, failed for failed or declined (:201-203); its started
item is skipped, as a command's is.
"""
from __future__ import annotations

import json
import re

PINNED_CLI = "0.162.1"
ROLLOUT_TYPES = ("session_meta", "response_item", "inter_agent_communication", "inter_agent_communication_metadata",
                 "compacted", "turn_context", "token_usage_record", "world_state", "retained_context",
                 "security_risk_score", "event_msg", "realtime_item")
SUPPORTED_ROLLOUT_TYPES = ("session_meta", "turn_context", "event_msg", "response_item", "token_usage_record",
                           "world_state")
PAGINATED_EVENTS = ("item_completed", "token_count", "thread_goal_updated", "thread_rolled_back", "turn_aborted",
                    "task_started", "task_complete", "thread_settings_applied")
SUPPORTED_EVENTS = ("item_completed", "token_count", "turn_aborted", "task_started", "task_complete",
                    "thread_settings_applied")
# Lane vendor-b25: ThreadSettingsSnapshot's keys (protocol.rs:2238-2267). Required: the fields with no skip; optional:
# the ones serialized only when Some (skip_serializing_if = "Option::is_none"). disabled_plugin_ids has
# #[serde(default)] and no skip, so it is always written.
TSA_REQUIRED = ("model", "model_provider_id", "approval_policy", "approvals_reviewer", "permission_profile", "cwd",
                "collaboration_mode", "disabled_plugin_ids")
TSA_OPTIONAL = ("service_tier", "active_permission_profile", "runtime_workspace_roots", "reasoning_effort",
                "reasoning_summary", "personality")
APPROVAL_POLICIES = ("untrusted", "on-request", "never")      # AskForApproval, protocol.rs:1000-1025 (kebab-case; Granular refuses)
APPROVALS_REVIEWERS = ("user", "auto_review")                 # config_types.rs:175-190 (the serialized names)
REASONING_SUMMARIES = ("auto", "concise", "detailed", "none")  # config_types.rs:60-72 (lowercase)
PERSONALITIES = ("none", "friendly", "pragmatic")              # config_types.rs:330-336 (lowercase)
MODE_KINDS = ("plan", "default")                               # ModeKind, config_types.rs:673-684 (snake_case)
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
PROJECTED_ITEMS = ("UserMessage", "AgentMessage", "Reasoning", "CommandExecution", "FileChange")
FILE_CHANGE_KEYS = ("type", "id", "changes", "status", "stdout", "stderr")
FILE_CHANGE_STATUSES = ("completed", "failed", "declined")
FILE_CHANGE_KINDS = {"add": ("type", "content"), "delete": ("type", "content"),
                     "update": ("type", "unified_diff", "move_path")}
EXEC_FILE_CHANGE_STATUS = {"completed": "completed", "failed": "failed", "declined": "failed"}
EXEC_EVENTS = ("thread.started", "turn.started", "turn.completed", "turn.failed", "item.started", "item.updated",
               "item.completed", "error")
EXEC_ITEMS = ("agent_message", "reasoning", "command_execution", "file_change", "mcp_tool_call", "collab_tool_call",
              "web_search", "todo_list", "error")
PROJECTED_EXEC_ITEMS = ("agent_message", "reasoning", "command_execution", "file_change", "error")
TRUNCATION_MARKER = "\n... command output truncated for persistence ...\n"
# The one reroute parser, shared with codex_adapter (Codex road review F1, F2): an item.completed error item whose
# message is exactly format!("model rerouted: {} -> {} ({:?})", from, to, reason) (exec/src/event_processor_with_jsonl_
# output.rs:494-507), the reason pinned to ModelRerouteReason's one variant, HighRiskCyberActivity (protocol/src/
# protocol.rs:2132-2134), and `from` the turn's requested model. Residual ambiguity: three other exec roads write the
# same item shape (collect_warning, ConfigWarning as "{summary} ({details})", DeprecationNotice; :409-472), so a warning
# whose text is exactly this sentence about the requested model would read as a reroute; nothing in the item tells
# them apart.
REROUTE = re.compile(r"model rerouted: (\S+) -> (\S+) \(HighRiskCyberActivity\)")


def reroute_of(rec, model):
    """`to` when `rec` is exactly one reroute item away from `model`; None for any other record."""
    if not (isinstance(rec, dict) and set(rec) == {"type", "item"} and rec["type"] == "item.completed"):
        return None
    item = rec["item"]
    if not (isinstance(item, dict) and set(item) == {"id", "type", "message"} and item["type"] == "error"
            and isinstance(item["id"], str) and isinstance(item["message"], str)):
        return None
    m = REROUTE.fullmatch(item["message"])
    return m.group(2) if m and isinstance(model, str) and m.group(1) == model else None
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
    lines = raw.split("\n")
    for n, text in enumerate(lines, 1):
        if not text.strip():
            if n == len(lines) and text == "":
                continue                         # the newline after the last record
            raise error(f"line {n} is blank: every line is one JSON object (upstream skips it; this reader refuses)")

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
        if summary and not "\n".join(summary).strip():
            raise ReaderRefused("a Reasoning item whose summary is whitespace only: exec drops it from its stream "
                                "(event_processor_with_jsonl_output.rs:152-156), so its join cannot be proven; a known "
                                "false-refusal risk, refused until a recorded pair shows it")
        if summary:
            turn["output"].append({"kind": "reasoning", "text": "\n".join(summary)})
    elif kind == "FileChange":
        turn["output"].append(_file_change(item))
    else:
        out = item.get("aggregated_output")
        if not (out is None or isinstance(out, str)) or not isinstance(item.get("status"), str) \
                or not isinstance(item.get("command"), list):
            raise ReaderRefused("a CommandExecution item is off its pinned shape")
        exit_code = item.get("exit_code")
        if not (exit_code is None or (isinstance(exit_code, int) and not isinstance(exit_code, bool))):
            raise ReaderRefused("a CommandExecution exit_code is an int or absent")
        turn["output"].append({"kind": "command", "status": item["status"], "exit_code": exit_code, "output": out,
                               "marker_text": isinstance(out, str) and TRUNCATION_MARKER in out})


def _file_change(item: dict) -> dict:
    """One FileChange item on its pinned shape (module docstring), projected; ReaderRefused otherwise."""
    if set(item) != set(FILE_CHANGE_KEYS):
        raise ReaderRefused(f"a FileChange item's keys are not exactly {list(FILE_CHANGE_KEYS)}")
    if not (isinstance(item["id"], str) and item["id"]):
        raise ReaderRefused("a FileChange item carries no id")
    if item["status"] not in FILE_CHANGE_STATUSES:
        raise ReaderRefused(f"a FileChange status is not one of {list(FILE_CHANGE_STATUSES)}")
    if not (isinstance(item["stdout"], str) and isinstance(item["stderr"], str)):
        raise ReaderRefused("a FileChange item's stdout and stderr are strings")
    changes = item["changes"]
    if not (isinstance(changes, dict) and changes):
        raise ReaderRefused("a FileChange item's changes are a non-empty map")
    out = []
    for path, change in changes.items():
        kind = change.get("type") if isinstance(change, dict) else None
        if not (isinstance(path, str) and path):
            raise ReaderRefused("a FileChange change names no path")
        if kind not in FILE_CHANGE_KINDS or set(change) != set(FILE_CHANGE_KINDS[kind]):
            raise ReaderRefused(f"a FileChange change is off its pinned shape ({kind!r})")
        if kind in ("add", "delete") and not isinstance(change["content"], str):
            raise ReaderRefused(f"a FileChange {kind}'s content is a string")
        if kind == "update" and not (isinstance(change["unified_diff"], str) and (
                change["move_path"] is None or (isinstance(change["move_path"], str) and change["move_path"]))):
            raise ReaderRefused("a FileChange update carries a diff string and a move_path that is a path or null")
        out.append({"path": path, "kind": kind, "move_path": change.get("move_path")})
    return {"kind": "file_change", "status": item["status"], "changes": sorted(out, key=lambda c: c["path"])}


def _world_state(pay: dict, n: int, current) -> None:
    """Lane vendor-b25: a WorldStateItem on its pinned shape inside an open turn (module docstring); nothing carried."""
    if current is None:
        raise ReaderRefused(f"line {n}: a world_state outside an open turn")
    if set(pay) != {"full", "state"} or not isinstance(pay["full"], bool) or not isinstance(pay["state"], dict):
        raise ReaderRefused(f"line {n}: a world_state payload is exactly {{full: bool, state: object}} "
                            f"(protocol.rs:3302-3307)")


def _absolute(value) -> bool:
    return isinstance(value, str) and value.startswith("/")


def _thread_settings(s, n: int) -> None:
    """ThreadSettingsSnapshot (protocol.rs:2238-2267), each value on its pinned type; ReaderRefused otherwise."""
    def bad(what):
        raise ReaderRefused(f"line {n}: thread_settings {what}")
    if not isinstance(s, dict) or not set(TSA_REQUIRED) <= set(s) <= set(TSA_REQUIRED + TSA_OPTIONAL):
        bad(f"keys are not exactly {list(TSA_REQUIRED)} plus any of {list(TSA_OPTIONAL)}")
    if not (isinstance(s["model"], str) and s["model"]) or not (isinstance(s["model_provider_id"], str)
                                                              and s["model_provider_id"]):
        bad("model and model_provider_id are non-empty strings")
    if "service_tier" in s and not isinstance(s["service_tier"], str):
        bad("service_tier is a string")
    if s["approval_policy"] not in APPROVAL_POLICIES:
        bad(f"approval_policy is not one of {list(APPROVAL_POLICIES)} (a Granular policy is unread here)")
    if s["approvals_reviewer"] not in APPROVALS_REVIEWERS:
        bad(f"approvals_reviewer is not one of {list(APPROVALS_REVIEWERS)}")
    # PermissionProfile (models.rs:418-435) is internally tagged by "type"; arm O runs only bypass (codex_adapter
    # MODE_FLAGS), which is Disabled, a unit variant: {"type": "disabled"}. Managed and External carry nested
    # file-system and network policies this lane did not read, so they refuse.
    if s["permission_profile"] != {"type": "disabled"}:
        bad('permission_profile is not {"type": "disabled"} (managed and external are unread here)')
    ap = s.get("active_permission_profile")
    if "active_permission_profile" in s and not (                       # models.rs:444-455
            isinstance(ap, dict) and "id" in ap and set(ap) <= {"id", "extends"}
            and all(isinstance(v, str) for v in ap.values())):
        bad("active_permission_profile is {id: string, extends?: string}")
    if not _absolute(s["cwd"]):
        bad("cwd is an absolute path")                                   # AbsolutePathBuf
    if "runtime_workspace_roots" in s and not (isinstance(s["runtime_workspace_roots"], list)
                                               and all(_absolute(r) for r in s["runtime_workspace_roots"])):
        bad("runtime_workspace_roots is a list of absolute paths")
    # ReasoningEffort serializes as its wire string, any spelling through Custom(String) (openai_models.rs:60-73,
    # 122-128, 144-156; blob 45654aa8, the pin's tree listing, fetched for this lane and hash-checked).
    if "reasoning_effort" in s and not (isinstance(s["reasoning_effort"], str) and s["reasoning_effort"]):
        bad("reasoning_effort is a non-empty string")
    if "reasoning_summary" in s and s["reasoning_summary"] not in REASONING_SUMMARIES:
        bad(f"reasoning_summary is not one of {list(REASONING_SUMMARIES)}")
    if "personality" in s and s["personality"] not in PERSONALITIES:
        bad(f"personality is not one of {list(PERSONALITIES)}")
    cm = s["collaboration_mode"]                                         # config_types.rs:705-711, 778-784
    if not (isinstance(cm, dict) and set(cm) == {"mode", "settings"} and cm["mode"] in MODE_KINDS
            and isinstance(cm["settings"], dict)
            and set(cm["settings"]) == {"model", "reasoning_effort", "developer_instructions"}
            and isinstance(cm["settings"]["model"], str) and cm["settings"]["model"]
            and (cm["settings"]["reasoning_effort"] is None
                 or (isinstance(cm["settings"]["reasoning_effort"], str) and cm["settings"]["reasoning_effort"]))
            and (cm["settings"]["developer_instructions"] is None
                 or isinstance(cm["settings"]["developer_instructions"], str))):
        bad(f"collaboration_mode is not {{mode: one of {list(MODE_KINDS)}, settings: {{model, reasoning_effort, "
            f"developer_instructions}}}}")
    if not (isinstance(s["disabled_plugin_ids"], list) and all(isinstance(i, str) for i in s["disabled_plugin_ids"])):
        bad("disabled_plugin_ids is a list of strings")


def _thread_settings_applied(pay: dict, n: int, current, session_id: str) -> None:
    """Lane vendor-b25: a ThreadSettingsAppliedEvent on its pinned shape between turns, naming this thread
    (module docstring); nothing carried."""
    if current is not None:
        raise ReaderRefused(f"line {n}: a thread_settings_applied inside an open turn")
    if set(pay) != {"type", "thread_id", "thread_settings"}:
        raise ReaderRefused(f"line {n}: a thread_settings_applied payload is exactly {{type, thread_id, "
                            f"thread_settings}} (protocol.rs:2228-2236)")
    if pay["thread_id"] != session_id:
        raise ReaderRefused(f"line {n}: a thread_settings_applied names another thread")
    _thread_settings(pay["thread_settings"], n)


def _ms(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _after_complete(pay: dict, n: int, closed, seen: set, session_id: str) -> None:
    """Lane pf1-codex-turnitem: an item_completed with no turn open is admitted only as the one late shape (module
    docstring): a background CommandExecution of the turn whose task_complete it directly follows; ReaderRefused,
    naming the shape, otherwise. `closed` is (that turn, its task_complete payload), None when any other line came
    between; `seen` the item ids that turn already completed."""
    tid = pay.get("turn_id")
    head = f"line {n}: an item belongs to turn {tid!r}, not the open turn"
    if closed is None:
        raise ReaderRefused(f"{head}: no turn is open and it does not directly follow its turn's task_complete")
    turn, done = closed
    if tid != turn["turn_id"]:
        raise ReaderRefused(f"{head}: after a task_complete only that turn's own command may complete")
    if pay.get("thread_id") != session_id:
        raise ReaderRefused(f"line {n}: an item names another thread")
    item = pay.get("item")
    kind = item.get("type") if isinstance(item, dict) else None
    if kind != "CommandExecution":
        raise ReaderRefused(f"{head}: only a CommandExecution may complete after its turn's task_complete, not "
                            f"{kind!r}")
    if item.get("source") != "unified_exec_startup" or not (isinstance(item.get("process_id"), str)
                                                            and item["process_id"]):
        raise ReaderRefused(f"{head}: a command completing after its turn is a unified-exec process's exit watcher's, "
                            "source unified_exec_startup with a process_id (async_watcher.rs:158-224)")
    if not (isinstance(item.get("id"), str) and item["id"]) or item["id"] in seen:
        raise ReaderRefused(f"{head}: a late command carries an id the turn has not already completed")
    begun, ended = pay.get("started_at_ms"), pay.get("completed_at_ms")
    t0, t1 = done.get("started_at"), done.get("completed_at")
    if not (_ms(begun) and _ms(ended) and _ms(t0) and _ms(t1) and t0 * 1000 <= begun < (t1 + 1) * 1000
            and ended >= begun):
        raise ReaderRefused(f"{head}: a late command must have started inside its turn (started_at_ms within the "
                            "task_complete's started_at..completed_at) and completed no earlier than it started")
    _item(item, turn)
    turn["after_complete"].append(turn["output"].pop())
    seen.add(item["id"])


def read_rollout(raw) -> dict:
    """{session_id, version, turns: [{turn_id, terminal, sent, requested_model, cwd, output, error, after_complete}]},
    or refused. after_complete holds the turn's commands that completed after its task_complete (module docstring)."""
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
    turns, current, closed, seen = [], None, None, set()
    for n, rec in enumerate(records[1:], 2):
        t, pay = rec["type"], rec["payload"]
        if closed is not None and not (t == "event_msg" and isinstance(pay, dict)
                                       and pay.get("type") == "item_completed"):
            closed = None                       # the late window is only the lines directly after task_complete
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
        if t == "world_state":
            _world_state(pay, n, current)
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
        if kind == "thread_settings_applied":
            _thread_settings_applied(pay, n, current, session_id)
            continue
        if kind == "task_started":
            if current is not None:
                raise ReaderRefused(f"line {n}: a turn opens before the previous one closes")
            current = {"turn_id": pay.get("turn_id"), "terminal": "incomplete", "sent": None,
                       "requested_model": None, "cwd": None, "output": [], "error": None, "after_complete": []}
            seen = set()
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
                closed = (current, pay)
            current = None
        elif kind == "item_completed":
            if current is None:
                _after_complete(pay, n, closed, seen, session_id)
                continue
            if pay.get("turn_id") != current["turn_id"]:
                raise ReaderRefused(f"line {n}: an item belongs to turn {pay.get('turn_id')!r}, not the open turn")
            if pay.get("thread_id") != session_id:
                raise ReaderRefused(f"line {n}: an item names another thread")
            _item(pay.get("item"), current)
            if isinstance(pay.get("item"), dict):
                seen.add(pay["item"].get("id"))
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


def read_exec(text, model=None) -> dict:
    """One `codex exec --json` call: thread id, items in order, errors, served-model evidence (reroute_of away from
    `model`; two different reroutes refuse), terminal."""
    records = _json_lines(text, JoinRefused)
    if not records or records[0].get("type") != "thread.started":
        raise JoinRefused("the exec stream must begin with thread.started")
    thread, items, errors, served, terminal, started = None, [], [], None, None, 0
    begun, ended = [], set()         # lane pf1-codex-turnitem: command ids started, and the ones completed
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
            if kind == "command_execution" and t == "item.started":
                begun.append(item.get("id"))
            elif kind == "command_execution" and t == "item.completed":
                ended.add(item.get("id"))
            if t != "item.completed":
                continue
            if kind == "error":
                to = reroute_of(rec, model)
                if to is None:
                    errors.append(item.get("message"))
                elif served is not None and served != to:
                    raise JoinRefused("one exec's stream reroutes to two different models")
                else:
                    served = to
            else:
                items.append(item)
    if started != 1:
        raise JoinRefused(f"an exec call holds {started} turn.started events, not one")
    unfinished = 0                   # a repeated start id makes the count unreadable: none is credited
    if len(set(begun)) == len(begun):
        unfinished = sum(1 for i in begun if isinstance(i, str) and i and i not in ended)
    return {"thread_id": thread, "items": items, "errors": errors, "served_model": served, "terminal": terminal,
            "unfinished_commands": unfinished}


PERSISTED_COMMAND_OUTPUT_MAX_BYTES = 64 * 1024        # rollout/src/policy.rs:17


def _continuation(byte: int) -> bool:
    return byte & 0xC0 == 0x80


def _floor_char_boundary(b: bytes, index: int) -> int:
    """Rust str::floor_char_boundary: the largest char boundary at or below index (len when index >= len)."""
    if index >= len(b):
        return len(b)
    while index > 0 and _continuation(b[index]):
        index -= 1
    return index


def _ceil_char_boundary(b: bytes, index: int) -> int:
    """Rust str::ceil_char_boundary: the smallest char boundary at or above index (len when index > len)."""
    if index > len(b):
        return len(b)
    while index < len(b) and _continuation(b[index]):
        index += 1
    return index


def truncate_middle_with_marker(s: str, max_bytes: int, marker: str) -> str:
    """The writer's truncation, from the retained source (Addendum A of the rollout audit; blob 075d78fd,
    codex-rs/utils/string/src/truncate.rs:20-33, split_budget :156-159, assemble_truncated_output :177-183), in UTF-8
    bytes: unchanged at or under max_bytes; otherwise the head up to floor_char_boundary(budget // 2) and the tail from
    ceil_char_boundary(len - (budget - budget // 2)), budget = max_bytes - len(marker), the tail taking the odd byte,
    joined by the marker. A marker longer than max_bytes keeps the longest prefix that fits (:25-27; never reached here,
    since the caller's marker is 50 bytes)."""
    b = s.encode("utf-8")
    if len(b) <= max_bytes:
        return s
    m = marker.encode("utf-8")
    if len(m) > max_bytes:
        return b[:_floor_char_boundary(b, max_bytes)].decode("utf-8")
    budget = max_bytes - len(m)
    left = budget // 2
    right = budget - left
    prefix_end = _floor_char_boundary(b, left)
    suffix_start = _ceil_char_boundary(b, max(len(b) - right, 0))
    return (b[:prefix_end] + m + b[suffix_start:]).decode("utf-8")


def _output_agrees(native, shown) -> bool:
    """Review finding 3, with the writer's truncation retained: an exec output over 64 KiB agrees only when the
    rollout's output is exactly truncate_middle_with_marker(exec output) (policy.rs:250-258); every other output must
    equal the rollout's exactly, the marker's text compared as ordinary text. MCP results use another, unaudited
    function and are not projected in this subset (McpToolCall refuses)."""
    if native is None:
        return shown == ""
    if not isinstance(shown, str):
        return False
    try:
        size = len(shown.encode("utf-8"))
    except UnicodeError:
        raise JoinRefused("the exec output is not UTF-8 text") from None
    if size > PERSISTED_COMMAND_OUTPUT_MAX_BYTES:
        return native == truncate_middle_with_marker(shown, PERSISTED_COMMAND_OUTPUT_MAX_BYTES, TRUNCATION_MARKER)
    return native == shown


def join(turn: dict, exec_text: str, *, exit_code, session_id: str) -> dict:
    """One rollout turn (read_rollout) joined to its exec call's stream, by order and type, never by exec ids."""
    call = read_exec(exec_text, model=turn["requested_model"])
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
    join_file_changes(turn, call)
    if len(turn["after_complete"]) > call["unfinished_commands"]:
        raise JoinRefused(f"the rollout completes {len(turn['after_complete'])} command(s) after the turn's "
                          f"task_complete and the stream started {call['unfinished_commands']} it never completed")
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
            "marker_text": any(n["marker_text"] for n in native_cmds),
            "command_text": "presentation-derived, not compared"}


def join_file_changes(turn: dict, call: dict) -> int:
    """How many file changes one rollout turn (read_rollout) and its exec call (read_exec) hold, after matching them
    by order (lane vendor-b23): JoinRefused unless the counts, each pair's paths and kinds (the stream's list against
    the rollout's sorted map) and each pair's status agree. A rename's target is the rollout's alone."""
    shown = [i for i in call["items"] if i.get("type") == "file_change"]
    native = [o for o in turn["output"] if o["kind"] == "file_change"]
    if len(shown) != len(native):
        raise JoinRefused("file change count disagrees")
    for s, nat in zip(shown, native):
        got = s.get("changes") if isinstance(s.get("changes"), list) else []
        if not all(isinstance(c, dict) for c in got):
            raise JoinRefused("an exec file_change's changes are not objects")
        if [(c.get("path"), c.get("kind")) for c in got] != [(c["path"], c["kind"]) for c in nat["changes"]]:
            raise JoinRefused("file change paths or kinds disagree")
        if s.get("status") != EXEC_FILE_CHANGE_STATUS[nat["status"]]:
            raise JoinRefused("file change status disagrees")
    return len(native)
