# Gemini CLI stream fixtures (lane w11b-gemini-adapter)

Every file in this folder is SYNTHETIC: written by hand by lane w11b from the documented shapes, never captured from a Gemini CLI run.
No Gemini CLI stream has been recorded; none can be before J3's keys (D8:131-133).
The fixtures use only the event types D8 section 1 names (init, message, tool_use, tool_result, error, result), the init and result keys it names, and the keys transcript_gemini.py lists as "NOT in D8" (Q-w11b-1).
tests/test_gemini_adapter.py reads the label of each file from the list below: a file with no label fails, and gemini_adapter.SHAPES_SOURCE may read "recorded" only once a file here is labelled exactly "RECORDED at walk <id>, gemini-cli <X.Y.Z>."

- `turn1-tools.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `turn2-resume.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `turn2-other-session.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `error-result.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `agent-says-429.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `no-init.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `turn-limit.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `unknown-event.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `unknown-key.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `unknown-tool.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `stats-missing.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `stats-other-model.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `init-other-model.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `tool-only.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
- `blank-assistant.jsonl`: SYNTHETIC, from D8 section 1 documentation, not a recorded stream.
