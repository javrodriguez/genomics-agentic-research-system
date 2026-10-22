# Codex stream fixtures (lane w11a-codex-adapter)

The first fifteen files below are SYNTHETIC: written by hand by lane w11a from the documented shapes, never captured from a Codex CLI run (none could be before J3's keys, D8:113-115).
Lane vendor-settle stage V (Thu 22 Oct 2026, glitch-f1's settle rulings) added seven RECORDED files, byte copies of committed walk records in this tree (rehearsals/<walk>/, read, never edited): walk w-o46's three resumed turn streams (`turn-<k>.jsonl`) and the rollout retained after each turn (`session/native-turn-<k>.jsonl`), and walk w-o47's one-turn rollout (gpt-6-luna); tests/test_codex_adapter.py binds each copy to its walk file and reads them through the adapter against plain-json values (R-recorded).
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
- `w-o46-turn-1.jsonl`: RECORDED at walk w-o46, codex-cli 0.162.1.
- `w-o46-turn-2.jsonl`: RECORDED at walk w-o46, codex-cli 0.162.1.
- `w-o46-turn-3.jsonl`: RECORDED at walk w-o46, codex-cli 0.162.1.
- `w-o46-rollout-1.jsonl`: RECORDED at walk w-o46, codex-cli 0.162.1.
- `w-o46-rollout-2.jsonl`: RECORDED at walk w-o46, codex-cli 0.162.1.
- `w-o46-rollout-3.jsonl`: RECORDED at walk w-o46, codex-cli 0.162.1.
- `w-o47-rollout-1.jsonl`: RECORDED at walk w-o47, codex-cli 0.162.1.
