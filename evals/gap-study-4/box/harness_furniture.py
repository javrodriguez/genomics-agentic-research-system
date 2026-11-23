#!/usr/bin/env python3
"""The per-harness furniture tables (lane d8-furniture, 21-22 Oct 2026): data only, no import, no function.

CP2's rule keeps box/scan_record.py and box/sidecar.py harness-agnostic (checks.d/w4c-cp2-sidecar-scan.txt line 11:
neither names a harness), so the tables that do live here; scan_record reads them generically
(scan_record.FURNITURE, furniture_positions, account_positions). Ruled by glitch-f1, 22 Oct 2026, on athena's battery
of 98a1bae7.
"""

# FILLED 21 Oct 2026 (lane d8-furniture, glitch-f1 under Javier's standing delegation; D8 lines 352, 472, 481, 494): what
# each CLI writes itself into its stream (`stream`: the per-turn turn-N.jsonl) or its session file (`session`: Claude
# Code's transcript.jsonl; Codex's rollout and Gemini CLI's chat file, retained as session/native-turn-N.jsonl, each a
# byte prefix of the next), read end to end on w-o46 and w-g21 (D8-READ-w-o46-20261021.md, D8-READ-w-g21-20261021.md)
# and surveyed by record kind and key path over all 225 walks at d5c0f798 (lane-reports/d8-furniture-LANE.md). Never
# the operator's or the model's words: a field that copies them (Codex task_complete's last_agent_message, Gemini's
# $patch contents, Claude's last-prompt and result text) is left out of `fields`.
#   file       "session" or "stream"
#   record     the record kind, by awareness_furniture.record_kind's rule: Codex type[/payload.type][/role], a
#              CLI-injected user message as response_item/message/user:injected; Gemini type, user:session_context,
#              $set:<keys>, $patch, <header>; Claude type[/subtype] and attachment:<type>
#   fields     dotted paths whose string leaves the CLI wrote ("[]" every list item, "[n]" one, "*" the whole record
#              less the record's account positions)
#   account    None; "identifying" (names the account: a scan masks or excludes it, never prints it); "plan" (describes
#              the account's plan or credit: excluded the same way)
#   evidence   walk folder/file:line under rehearsals/ where the record kind stands (read, never edited); for a kind
#              transcript_view admits that no round-4 walk carries, the view's own table line (transcript_view.py:n)
# Codex at 0.162.1: w-o46 predates lane B22's [agents] enabled = false (take_config.py:72-78, 280-284) and carries three
# developer records (skills/permissions/collaboration, multi_agent.role_instructions, multi_agent.mode_instructions);
# the post-B22 walks (w-o39..w-o44, w-o47) carry one, and their session_meta and turn_context multi_agent_version read
# "disabled" (pre-B22: absent and "v2"), with world_state's multi_agent_mode and multi_agent_usage_hint gone. The kinds
# below hold for both; the record counts differ. Gemini at 0.64.0 writes no account field: its header's projectHash is
# sha256 of the run-tree path (36 of 36 walks). Claude Code at 2.1.296 writes plan fields only (apiKeySource,
# rate_limit_info, usage.service_tier).
FURNITURE_KEYS = ("file", "record", "fields", "account", "evidence")
ACCOUNT_CLASSES = (None, "identifying", "plan")
_O46, _O47 = "w-o46/session/native-turn-3.jsonl:", "w-o47/session/native-turn-1.jsonl:"
_O46S, _O47S = "w-o46/turn-1.jsonl:", "w-o47/turn-1.jsonl:"
_G21, _G21S = "w-g21/session/native-turn-2.jsonl:", "w-g21/turn-1.jsonl:"
_C, _CS = "w168/transcript.jsonl:", "w168/turn-1.jsonl:"
_CODEX_META = ("timestamp", "payload.id", "payload.internal_chat_message_metadata_passthrough", "metadata")
_CC_ENVELOPE = ("type", "uuid", "parentUuid", "timestamp", "sessionId", "cwd", "entrypoint", "gitBranch", "userType",
                "version", "promptId", "requestId")
FURNITURE = {
    "codex": (
        {"file": "session", "record": "session_meta", "fields": ("*",), "account": None,
         "evidence": (_O46 + "1", _O47 + "1")},
        {"file": "session", "record": "session_meta", "fields": ("payload.creator_user_id", "payload.creator_account_id"),
         "account": "identifying", "evidence": (_O46 + "1", _O47 + "1")},
        {"file": "session", "record": "response_item/message/developer", "fields": ("*",), "account": None,
         "evidence": (_O46 + "3", _O46 + "4", _O46 + "5", _O47 + "3")},
        {"file": "session", "record": "response_item/message/user:injected", "fields": ("*",), "account": None,
         "evidence": (_O46 + "6", _O47 + "4")},
        {"file": "session", "record": "world_state", "fields": ("*",), "account": None,
         "evidence": (_O46 + "7", _O47 + "5")},
        {"file": "session", "record": "turn_context", "fields": ("*",), "account": None,
         "evidence": (_O46 + "8", _O47 + "6")},
        {"file": "session", "record": "event_msg/task_started", "fields": ("*",), "account": None,
         "evidence": (_O46 + "2", _O47 + "2")},
        {"file": "session", "record": "event_msg/thread_settings_applied", "fields": ("*",), "account": None,
         "evidence": (_O46 + "40", _O46 + "41")},
        {"file": "session", "record": "event_msg/task_complete",
         "fields": ("timestamp", "type", "payload.type", "payload.turn_id", "payload.root_turn_id"), "account": None,
         "evidence": (_O46 + "39", _O47 + "62")},
        {"file": "session", "record": "token_usage_record", "fields": ("*",), "account": None,
         "evidence": (_O46 + "14", _O47 + "12")},
        {"file": "session", "record": "event_msg/token_count", "fields": ("*",), "account": None,
         "evidence": (_O46 + "17", _O47 + "15")},
        {"file": "session", "record": "event_msg/token_count",
         "fields": ("payload.rate_limits.plan_type", "payload.rate_limits.credits.has_credits",
                    "payload.rate_limits.credits.unlimited", "payload.rate_limits.credits.balance"),
         "account": "plan", "evidence": (_O46 + "17", _O47 + "15")},
        {"file": "session", "record": "event_msg/item_completed",
         "fields": ("timestamp", "type", "payload.type", "payload.thread_id", "payload.turn_id", "payload.item.id",
                    "payload.item.type", "payload.item.cwd", "payload.item.source", "payload.item.status",
                    "payload.item.process_id", "payload.item.phase"), "account": None,
         "evidence": (_O46 + "10", _O47 + "8")},
        {"file": "session", "record": "response_item/message/assistant", "fields": _CODEX_META + ("payload.phase",),
         "account": None, "evidence": (_O46 + "12", _O47 + "10")},
        {"file": "session", "record": "response_item/message/user", "fields": _CODEX_META, "account": None,
         "evidence": (_O46 + "9", _O47 + "7")},
        {"file": "session", "record": "response_item/reasoning", "fields": _CODEX_META, "account": None,
         "evidence": (_O46 + "54", _O47 + "17")},
        {"file": "session", "record": "response_item/custom_tool_call",
         "fields": _CODEX_META + ("payload.call_id", "payload.name", "payload.status"), "account": None,
         "evidence": (_O46 + "13", _O47 + "11")},
        {"file": "session", "record": "response_item/custom_tool_call_output",
         "fields": _CODEX_META + ("payload.call_id", "payload.output[0].text"), "account": None,
         "evidence": (_O46 + "16", _O47 + "14")},
        {"file": "stream", "record": "thread.started", "fields": ("*",), "account": None,
         "evidence": (_O46S + "1", _O47S + "1")},
        {"file": "stream", "record": "turn.started", "fields": ("*",), "account": None,
         "evidence": (_O46S + "2", _O47S + "2")},
        {"file": "stream", "record": "turn.completed", "fields": ("*",), "account": None,
         "evidence": (_O46S + "14", _O47S + "20")},
        {"file": "stream", "record": "item.started/command_execution", "fields": ("item.id", "item.type", "item.status"),
         "account": None, "evidence": (_O46S + "4", _O47S + "4")},
        {"file": "stream", "record": "item.completed/command_execution",
         "fields": ("item.id", "item.type", "item.status"), "account": None, "evidence": (_O46S + "5", _O47S + "5")},
        {"file": "stream", "record": "item.completed/agent_message", "fields": ("item.id", "item.type"),
         "account": None, "evidence": (_O46S + "3", _O47S + "3")},
    ),
    "gemini": (
        {"file": "session", "record": "<header>", "fields": ("*",), "account": None, "evidence": (_G21 + "1",)},
        {"file": "session", "record": "$set:lastUpdated", "fields": ("*",), "account": None,
         "evidence": (_G21 + "3",)},
        {"file": "session", "record": "$set:sessionId", "fields": ("*",), "account": None,
         "evidence": (_G21 + "153",)},
        {"file": "session", "record": "$patch", "fields": ("$patch.orderIds", "$patch.removeIds", "$patch.updates[].id"),
         "account": None, "evidence": (_G21 + "183", "w-g14/session/native-turn-4.jsonl:515")},
        {"file": "session", "record": "user:session_context", "fields": ("type", "id", "timestamp", "content[0].text"),
         "account": None, "evidence": (_G21 + "2", "w-g14/session/native-turn-4.jsonl:517")},
        {"file": "session", "record": "user",
         "fields": ("type", "id", "timestamp", "content[].functionResponse.id", "content[].functionResponse.name"),
         "account": None, "evidence": (_G21 + "4", _G21 + "9")},
        {"file": "session", "record": "gemini",
         # review fold M1: toolCalls[].description renders the model's arguments and resultDisplay holds the file
         # text the model wrote (newContent, fileDiff, originalContent) and matched file lines: neither is furniture
         "fields": ("type", "id", "timestamp", "model", "tokens", "thoughts[].timestamp", "toolCalls[].id",
                    "toolCalls[].status", "toolCalls[].timestamp", "toolCalls[].displayName",
                    "toolCalls[].renderOutputAsMarkdown", "toolCalls[].result[].functionResponse.id",
                    "toolCalls[].result[].functionResponse.name"),
         "account": None, "evidence": (_G21 + "6", _G21 + "8")},
        {"file": "stream", "record": "init", "fields": ("*",), "account": None, "evidence": (_G21S + "1",)},
        {"file": "stream", "record": "result", "fields": ("*",), "account": None, "evidence": (_G21S + "78",)},
        {"file": "stream", "record": "message", "fields": ("type", "timestamp", "role", "delta"), "account": None,
         "evidence": (_G21S + "2",)},
        {"file": "stream", "record": "tool_use", "fields": ("type", "timestamp", "tool_id"), "account": None,
         "evidence": (_G21S + "3",)},
        # review fold n1: error.message echoes the model's paths and arguments; only its type is the CLI's
        {"file": "stream", "record": "tool_result", "fields": ("type", "timestamp", "tool_id", "status", "error.type"),
         "account": None, "evidence": (_G21S + "7",)},
    ),
    "claude-code": (
        {"file": "session", "record": "attachment:agent_listing_delta", "fields": ("*",), "account": None,
         "evidence": (_C + "7",)},
        {"file": "session", "record": "attachment:date", "fields": ("*",), "account": None, "evidence": (_C + "13",)},
        {"file": "session", "record": "attachment:deferred_tools_delta", "fields": ("*",), "account": None,
         "evidence": (_C + "6",)},
        {"file": "session", "record": "attachment:edited_text_file", "fields": ("*",), "account": None,
         "evidence": ("w142/transcript.jsonl:82",)},
        {"file": "session", "record": "attachment:environment", "fields": ("*",), "account": None,
         "evidence": (_C + "4",)},
        {"file": "session", "record": "attachment:instructions", "fields": ("*",), "account": None,
         "evidence": (_C + "11",)},
        {"file": "session", "record": "attachment:model", "fields": ("*",), "account": None, "evidence": (_C + "5",)},
        {"file": "session", "record": "attachment:nested_memory", "fields": ("*",), "account": None,
         "evidence": ("w002/transcript.jsonl:47",)},
        {"file": "session", "record": "attachment:prompt_snapshot", "fields": ("*",), "account": None,
         "evidence": (_C + "15",)},
        # review fold M1: the prompt and its renderings carry the task notification wrapping the model's command (or an
        # operator's mid-turn prompt); only the CLI's own keys are furniture
        {"file": "session", "record": "attachment:queued_command",
         "fields": _CC_ENVELOPE + ("isSidechain", "attachment.type", "attachment.commandMode", "attachment.origin",
                                   "attachment.delivery_id", "attachment.runId", "attachment.source_uuid",
                                   "attachment.timestamp"), "account": None,
         "evidence": ("w003/transcript.jsonl:69",)},
        # review fold m1: the kinds transcript_view admits as harness that no round-4 walk carries, cited to the view's
        # own tables (transcript_view.py), and the scheduled wakeup, which walks carry (its content is the model's own
        # ScheduleWakeup prompt, so only the envelope is furniture)
        {"file": "session", "record": "attachment:auto_mode", "fields": ("*",), "account": None,
         "evidence": ("transcript_view.py:280",)},
        {"file": "session", "record": "attachment:deferred_tools_record", "fields": ("*",), "account": None,
         "evidence": ("transcript_view.py:278",)},
        {"file": "session", "record": "ai-title", "fields": ("type", "sessionId"), "account": None,
         "evidence": ("transcript_view.py:304",)},
        # closure NIT: no walk carries a session system record, which can carry an operator's slash command; its
        # content is left out until one is seen
        {"file": "session", "record": "system", "fields": ("type", "subtype", "level", "timestamp", "uuid", "sessionId"),
         "account": None, "evidence": ("transcript_view.py:305",)},
        {"file": "session", "record": "user:no-visible-output-nudge", "fields": ("*",), "account": None,
         "evidence": ("transcript_view.py:331",)},
        {"file": "session", "record": "user:scheduled-wakeup", "fields": _CC_ENVELOPE + ("isSidechain", "isMeta",
                                                                                         "turnOrigin", "promptSource"),
         "account": None, "evidence": ("w033/transcript.jsonl:96", "w116/transcript.jsonl:86")},
        {"file": "session", "record": "attachment:remote_session_change", "fields": ("*",), "account": None,
         "evidence": (_C + "14",)},
        {"file": "session", "record": "attachment:session_context", "fields": ("*",), "account": None,
         "evidence": (_C + "12",)},
        {"file": "session", "record": "attachment:skill_listing", "fields": ("*",), "account": None,
         "evidence": (_C + "8",)},
        {"file": "session", "record": "attachment:task_reminder", "fields": ("*",), "account": None,
         "evidence": ("w001/transcript.jsonl:54",)},
        {"file": "session", "record": "attachment:total_tokens_reminder", "fields": ("*",), "account": None,
         "evidence": (_C + "9",)},
        {"file": "session", "record": "queue-operation", "fields": ("type", "operation", "timestamp", "sessionId"),
         "account": None, "evidence": (_C + "1",)},
        {"file": "session", "record": "last-prompt", "fields": ("type", "sessionId"), "account": None,
         "evidence": (_C + "16",)},
        {"file": "session", "record": "atis-latch", "fields": ("*",), "account": None, "evidence": (_C + "10",)},
        {"file": "session", "record": "cost-state", "fields": ("*",), "account": None, "evidence": (_C + "72",)},
        {"file": "session", "record": "mode", "fields": ("*",), "account": None,
         "evidence": ("w001/transcript.jsonl:80",)},
        {"file": "session", "record": "user", "fields": _CC_ENVELOPE + ("isSidechain",), "account": None,
         "evidence": (_C + "3",)},
        {"file": "session", "record": "assistant",
         "fields": _CC_ENVELOPE + ("message.id", "message.model", "message.type", "message.role",
                                   "message.stop_reason", "message.usage"), "account": None,
         "evidence": (_C + "18",)},
        # review fold m3: the usage's service tier is an account-plan field
        {"file": "session", "record": "assistant", "fields": ("message.usage.service_tier",), "account": "plan",
         "evidence": (_C + "18",)},
        {"file": "stream", "record": "system/init", "fields": ("*",), "account": None, "evidence": (_CS + "1",)},
        {"file": "stream", "record": "system/init", "fields": ("apiKeySource",), "account": "plan",
         "evidence": (_CS + "1",)},
        {"file": "stream", "record": "rate_limit_event", "fields": ("*",), "account": None, "evidence": (_CS + "4",)},
        {"file": "stream", "record": "rate_limit_event", "fields": ("rate_limit_info",), "account": "plan",
         "evidence": (_CS + "4",)},
        {"file": "stream", "record": "system/thinking_tokens", "fields": ("*",), "account": None,
         "evidence": (_CS + "15",)},
        # review fold M1: a task's description and summary carry the model's Bash command; the CLI's keys only
        {"file": "stream", "record": "system/task_started",
         "fields": ("type", "subtype", "uuid", "session_id", "task_id", "task_type", "tool_use_id", "run_id",
                    "is_backgrounded"), "account": None, "evidence": ("w003/turn-1.jsonl:38",)},
        {"file": "stream", "record": "system/task_updated", "fields": ("*",), "account": None,
         "evidence": ("w003/turn-1.jsonl:40",)},
        {"file": "stream", "record": "system/task_notification",
         "fields": ("type", "subtype", "uuid", "session_id", "task_id", "tool_use_id", "run_id", "status",
                    "output_file"), "account": None, "evidence": ("w003/turn-1.jsonl:41",)},
        {"file": "stream", "record": "system/background_tasks_changed",
         "fields": ("type", "subtype", "uuid", "session_id", "tasks[].task_id", "tasks[].task_type", "tasks[].run_id"),
         "account": None, "evidence": ("w003/turn-1.jsonl:37",)},
        {"file": "stream", "record": "command_lifecycle", "fields": ("*",), "account": None,
         "evidence": ("w033/turn-1.jsonl:86",)},
        # lane gap-rewalk-fix (glitch-45's ruling, 27 Oct 2026, under Javier's standing delegation): two kinds the CLI
        # writes while an Agent sub-agent runs, first seen in the rewalk's w255 and w260 (Haiku walks that called the
        # Agent tool) and in no other of the 387 walks. As for system/task_started, only the CLI's keys are listed:
        # task_progress's description renders the sub-agent's own command ("Running find /tmp/run-...") and its
        # subagent_type is the model's Agent argument, so neither is furniture. Listing a kind here only makes the
        # completeness check know it; no scan of the walks' text reads this table (awareness_furniture scans listed
        # positions in codex and gemini native sessions only, and never skips text because it is listed).
        {"file": "stream", "record": "system/task_progress",
         "fields": ("type", "subtype", "uuid", "session_id", "task_id", "tool_use_id", "run_id", "last_tool_name",
                    "usage"), "account": None, "evidence": ("w255/turn-1.jsonl:55", "w260/turn-1.jsonl:20")},
        {"file": "stream", "record": "tool_progress",
         "fields": ("type", "uuid", "session_id", "tool_use_id", "parent_tool_use_id", "tool_name",
                    "elapsed_time_seconds", "heartbeat"), "account": None, "evidence": ("w260/turn-1.jsonl:68",)},
        {"file": "stream", "record": "result/success",
         "fields": ("type", "subtype", "uuid", "session_id", "stop_reason", "terminal_reason", "fast_mode_state",
                    "fast_mode_disabled_reason", "usage", "origin", "permission_denials"), "account": None,
         "evidence": (_CS + "41",)},
        {"file": "stream", "record": "result/success", "fields": ("usage.service_tier",), "account": "plan",
         "evidence": (_CS + "41",)},
        {"file": "stream", "record": "assistant",
         "fields": ("type", "uuid", "session_id", "parent_tool_use_id", "message.id", "message.model",
                    "message.usage"), "account": None, "evidence": (_CS + "2",)},
        {"file": "stream", "record": "assistant", "fields": ("message.usage.service_tier",), "account": "plan",
         "evidence": (_CS + "2",)},
        {"file": "stream", "record": "user", "fields": ("type", "uuid", "session_id", "parent_tool_use_id", "timestamp"),
         "account": None, "evidence": (_CS + "5",)},
    ),
}
