# Next harness integration: addendum, 14 Oct 2026 00:24 EDT

This adds to `live-harness-next-integration-2026-10-13.md` (left as written). Sources: glitch-06's rulings on the step-2 reviews r1 and r2 (`/Users/javrodher/aegis-builds/gap4-review-harness-step2-20261014/`).

## Owed by the stream-side slice

1. **Recorder normalization before any text comparison.** The native fact is `recorded-text`, one segment per gemini message, in the recorder's normal form (`gemini_projection.recorder_normalize`, cited in `gemini-0.64.0-source-retained-2026-10-14.md`). The stream side must group its assistant deltas per model message, apply `recorder_normalize` to each, and compare segment by segment. A recorded segment is never called displayed text.
2. **Completeness comes from the stream, never from the native record alone.** A kill while a tool is still running leaves an ordinary-looking text message with no `toolCalls`, because `recordToolCalls` runs only once tools complete. An interaction counts as complete only when it is joined to that turn's stream terminal `result` record (status, stats) and to the turn's exit/timeout. A native interaction without that join stays unverified.

## Named departure D-3a-1: a human ruling replaces automatic classification for an executed turn whose own record is refused

Design item 3 above says the integration "must still complete … scientific classification".
Step 3a (`0d417a1d`) instead stops such a take: `DriveRefused` after cleanup, ledger and scan; batch `failed` with `drive_started=True`, which needs a ruling and is never re-run. glitch-06 kept this stricter behaviour (r2 ruling 2) and asked whether a registered class exists for it.

What the pre-registration says (`/Users/javrodher/glitch/plans/gap-study-round-4.md`):
- The routing table (lines 192-199) is phase-split. Before the agent's first turn, harness faults are a `rehearsal`, re-run in the slot (capped at 3 per half-cell). After it, the listed records (API error, container exit, watcher gap, init mismatch, a non-zero exec exit with no API error and no counter rise, operator-side reasons, unreadable consequential paths) are `harness-error`, with one re-run (capped at 2 per half-cell).
- "Three in one night stop the run for a ruling" (line 560, and line 904 for `batch.py`).

Why no registered class applies:
- The phase is decided by completed agent output read from the turn's stream (the gap4 lane lead's W1B-5 ruling, in `routing.py`). On this road the stream is exactly what the harness refused to read, so whether the agent's first turn started is unknown for that turn. Routing it would mean choosing a phase, and choosing "before" would make it a rehearsal: a free replacement take.
- No registered row names "the harness could not read its own record of an executed turn". Mapping it onto "non-zero exec exit" or "readers-disagree" would invent a meaning for a registered class. That is forbidden.
- Even where earlier turns show agent output (phase known: after the first turn), the refused turn's own records (end, API errors, init) are unread, so the routing record for that turn cannot be built truthfully.

So on this road a human ruling replaces classification. The take is never graded, rehearsed or re-run automatically; its exit, timeout, times, stream, launch journal, ledger row, quiescence kill and scan are all retained for that ruling.

Finding for the orchestrator, not fixed here: the nightly stop rule ("three `harness-error`s in one night") has no implementation at this head. A search of `batch.py`, `routing.json`, `takes.py` and `prereg-draft.json` for night/stop-rule terms finds only review prose. So there is no counter the executed-refusal road could feed. Every executed refusal already stops the loop for a ruling (`failed` after drive start), which is at least as strict as the per-night rule for this road.
