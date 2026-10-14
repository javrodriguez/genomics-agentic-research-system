"""Provisional Gemini 0.64.0 native JSONL replay, never production admission.

Derived from the installed bundle's createJsonlRecordAccumulator retained in
the box lane's gemini-native-session-source.json, not a recorded live session.
This returns raw replayed messages, NOT normalized checker facts. Message payload
fields remain uninterpreted until a separate reviewed semantic reader validates
them. No production registry imports this helper. Per-interaction snapshot
preservation/comparison, visible text/tool projection and recorded-stream proof
remain required before any native session reader can be registered.

Supports complete message upserts and ordinary content/tool-result patches.
Destructive history operations and unknown control records fail closed. Unlike
the vendor's recovery-oriented loader, malformed JSON and unknown patch targets
are never silently ignored.
"""
from copy import deepcopy

import transcript_view as tv
from vendor_record_binding import _json, _jsonl_lines


class ReplayRefused(ValueError):
    """Native recording contains an unsupported or contradictory replay operation."""


METADATA_KEYS = {"sessionId", "projectHash", "startTime", "lastUpdated", "kind", "directories", "summary"}
MESSAGE_KINDS = {"user", "gemini", "info", "error", "warning"}


def _string(value):
    return isinstance(value, str) and bool(value)


def _tools(message):
    tools = message.get("toolCalls", [])
    if not isinstance(tools, list):
        raise ReplayRefused("native toolCalls must be an array")
    ids = set()
    for tool in tools:
        if not isinstance(tool, dict) or not _string(tool.get("id")) or tool["id"] in ids:
            raise ReplayRefused("native tools need unique nonempty ids")
        ids.add(tool["id"])
    return tools


def _patch(messages, patch):
    if (not isinstance(patch, dict) or not set(patch) <= {"id", "content", "toolCalls"}
            or not _string(patch.get("id")) or not ({"content", "toolCalls"} & set(patch))):
        raise ReplayRefused("unknown or empty native message patch")
    target = messages.get(patch["id"])
    if target is None:
        raise ReplayRefused("native message patch target is absent")
    if "content" in patch:
        target["content"] = deepcopy(patch["content"])
    if "toolCalls" in patch:
        if target["type"] != "gemini" or not isinstance(patch["toolCalls"], list):
            raise ReplayRefused("tool-result patch requires a Gemini message and array")
        tools = {tool["id"]: tool for tool in _tools(target)}
        for change in patch["toolCalls"]:
            if (not isinstance(change, dict) or set(change) != {"id", "result"}
                    or not _string(change["id"]) or change["id"] not in tools):
                raise ReplayRefused("native tool-result patch target or shape is unknown")
            tools[change["id"]]["result"] = deepcopy(change["result"])


def replay(raw):
    """Replay one retained native snapshot; no prompt/output/terminal claims."""
    if not isinstance(raw, bytes):
        raise ReplayRefused("native replay requires retained bytes")
    try:
        records = [_json(line) for line in _jsonl_lines(raw.decode("utf-8"))]
    except (UnicodeError, tv.ViewError):
        raise ReplayRefused("native session is not complete UTF-8 JSONL") from None
    if not records:
        raise ReplayRefused("native session is empty")
    metadata = records[0]
    if (not isinstance(metadata, dict) or not set(metadata) <= METADATA_KEYS
            or not all(_string(metadata.get(k)) for k in ("sessionId", "projectHash"))):
        raise ReplayRefused("native session must begin with identity metadata")
    messages = {}
    for record in records[1:]:
        if not isinstance(record, dict):
            raise ReplayRefused("native session record is not an object")
        controls = [key for key in record if key.startswith("$")]
        if controls:
            if len(record) != 1:
                raise ReplayRefused("mixed native control record")
            if "$set" in record:
                update = record["$set"]
                if not isinstance(update, dict) or not update or not set(update) <= {"sessionId", "lastUpdated"}:
                    raise ReplayRefused("unsupported native metadata update")
                if any(not _string(value) for value in update.values()):
                    raise ReplayRefused("native metadata update is not a nonempty string")
                if update.get("sessionId", metadata["sessionId"]) != metadata["sessionId"]:
                    raise ReplayRefused("native session identity changed")
                metadata.update(update)
            elif "$patch" in record:
                patch = record["$patch"]
                if not isinstance(patch, dict) or not patch or not set(patch) <= {"id", "content", "toolCalls", "updates"}:
                    raise ReplayRefused("unsupported native patch operation")
                direct = {key: value for key, value in patch.items() if key != "updates"}
                if direct:
                    _patch(messages, direct)
                if "updates" in patch:
                    if not isinstance(patch["updates"], list) or not patch["updates"]:
                        raise ReplayRefused("native patch updates must be a nonempty array")
                    for update in patch["updates"]:
                        _patch(messages, update)
            else:
                raise ReplayRefused("unsupported destructive or unknown native operation")
        else:
            if (not _string(record.get("id")) or not isinstance(record.get("type"), str)
                    or record["type"] not in MESSAGE_KINDS or "content" not in record):
                raise ReplayRefused("unknown native message record")
            previous = messages.get(record["id"])
            if previous is not None and previous["type"] != record["type"]:
                raise ReplayRefused("native message role changed under the same id")
            _tools(record)
            # Python dict assignment mirrors Map.set: replacing a value retains order.
            messages[record["id"]] = record
    return {"metadata": metadata, "messages": list(messages.values())}
