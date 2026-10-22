# Gemini CLI stream fixtures (lane w11b-gemini-adapter)

The first fifteen files below are SYNTHETIC: written by hand by lane w11b from the documented shapes, never captured from a Gemini CLI run (none could be before J3's keys, D8:131-133).
Lane vendor-settle stage V (Thu 22 Oct 2026, glitch-f1's settle rulings) added three RECORDED files, byte copies of committed walk records in this tree (rehearsals/<walk>/turn-<k>.jsonl, read, never edited): walk w-g21's two turn streams, and walk w-g24's one turn stream, a turn that timed out (driver outcome timed-out) with no result record, so no stats; tests/test_gemini_adapter.py binds each copy to its walk file and reads them through the adapter against plain-json values (R-recorded).
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
- `w-g21-turn-1.jsonl`: RECORDED at walk w-g21, gemini-cli 0.64.0.
- `w-g21-turn-2.jsonl`: RECORDED at walk w-g21, gemini-cli 0.64.0.
- `w-g24-turn-1.jsonl`: RECORDED at walk w-g24, gemini-cli 0.64.0.
