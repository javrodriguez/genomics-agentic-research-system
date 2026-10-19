#!/usr/bin/env python3
"""Where each key of transcript_codex.USAGE_KEYS was read in the pinned Codex CLI (lane vendor-b14 round 1 B15;
glitch-26's ruling, Mon 19 Oct 2026; practice walk w-o3).

The pinned source is openai/codex at tag rust-v0.162.1, which peels to commit 092d3acd (git ls-remote), read from the
public repository at that commit, never run. turn.completed is ThreadEvent::TurnCompleted (exec_events.rs:19-21,
serde tag "type" at :10), whose one field is `usage: Usage` (:50-52). struct Usage (:59-73) has five i64 fields. No
field carries skip_serializing_if (the same file uses it where a field is left out when unset, :272 and :303), and the
serde(default) on cache_write_input_tokens (:67) is a deserialize attribute only: an object without the key still
deserializes, but serializing always writes it. codex exec prints each event with serde_json::to_string
(event_processor_with_jsonl_output.rs:105-116) and builds turn.completed's usage from usage_from_last_total (:118-129,
which sets all five, or Usage::default(), all zeros, before any token count arrives) at :533-535. So every field is
always present, and WHEN_SET, the fields present only when set, is empty.

Read statically, never imported by a reader: kept apart from transcript_codex.py so its generated sweep mutates the
table, not its documentation. Bound by tests/test_codex_usage_source.py (U2; --sources re-reads every cited line).
"""

PIN = {"repo": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"}
STRUCT_FILE = "codex-rs/exec/src/exec_events.rs"
EMIT_FILE = "codex-rs/exec/src/event_processor_with_jsonl_output.rs"
FILE_SHA256 = {STRUCT_FILE: "dafa872d7e86a099e56e28a329dcb9c03db90ed768c3b88cca8c91d46dc1d0e5",
               EMIT_FILE: "bc296541b385f9b4ca2c28cc638e25a8d6b1332b2cd67f5a03eaa97a3d612b19"}

# Each usage key, in the struct's order: the line that declares it and that line's text.
USAGE_SOURCES = {
    "input_tokens": {"file": STRUCT_FILE, "line": 63, "text": "    pub input_tokens: i64,"},
    "cached_input_tokens": {"file": STRUCT_FILE, "line": 65, "text": "    pub cached_input_tokens: i64,"},
    "cache_write_input_tokens": {"file": STRUCT_FILE, "line": 68,
                                 "text": "    pub cache_write_input_tokens: i64,"},
    "output_tokens": {"file": STRUCT_FILE, "line": 70, "text": "    pub output_tokens: i64,"},
    "reasoning_output_tokens": {"file": STRUCT_FILE, "line": 72, "text": "    pub reasoning_output_tokens: i64,"},
}

# The fields serialized only when set: none (no skip_serializing_if in struct Usage, :59-73).
WHEN_SET = ()

# The other lines read: the struct heads, the deserialize-only default, and the serializer road.
LINES = (
    (STRUCT_FILE, 50, "pub struct TurnCompletedEvent {"),
    (STRUCT_FILE, 51, "    pub usage: Usage,"),
    (STRUCT_FILE, 60, "#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, TS, Default)]"),
    (STRUCT_FILE, 61, "pub struct Usage {"),
    (STRUCT_FILE, 67, "    #[serde(default)]"),
    (EMIT_FILE, 108, "            serde_json::to_string(&event).unwrap_or_else(|err| {"),
    (EMIT_FILE, 125, "            cache_write_input_tokens: usage.total.cache_write_input_tokens,"),
    (EMIT_FILE, 533, "                        events.push(ThreadEvent::TurnCompleted(TurnCompletedEvent {"),
    (EMIT_FILE, 534, "                            usage: self.usage_from_last_total(),"),
)
