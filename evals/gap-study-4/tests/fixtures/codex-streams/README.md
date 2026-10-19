# Codex stream fixtures (lane w11a-codex-adapter)

Every file in this folder is SYNTHETIC: written by hand by lane w11a from the documented shapes, never captured from a Codex CLI run.
No Codex stream or rollout has been recorded; none can be before J3's keys (D8:113-115).
The stream fixtures use only the event types, item types and usage keys D8 section 1 names, plus the keys transcript_codex.py lists as "NOT in D8" (Q-w11a-1) and the usage key cache_write_input_tokens read from the pinned struct (lane vendor-b14 B15, codex_usage_sources.py).
The rollout fixtures use the record shape codex_adapter.py lists as "NOT in D8" (Q-w11a-1).
tests/test_codex_adapter.py reads the label of each file from the list below: a file with no label fails, and codex_adapter.SHAPES_SOURCE may read "recorded" only once a file here is labelled RECORDED, with the walk and harness version it was captured at.

- `turn1-tools.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `turn2-resume.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `turn2-other-thread.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `turn-failed.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `agent-says-429.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `reasoning-only.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `unknown-event.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `unknown-item.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `unknown-key.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `usage-missing.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `mcp-call.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `file-delete.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `rollout-two-turns.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `rollout-served-other.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `rollout-no-context.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
