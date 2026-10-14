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

## Named departure D-INT-1, 14 Oct 2026 01:37 EDT: a vendor take with a pending native cross-check stops for a ruling

Ruled by glitch-06, 14 Oct 2026, under the standing delegation. Implemented in `5ec06353`; the reasoning is in `vendor-checker-road-2026-10-14.md`.

**What happens to such a take:** a vendor take whose native cross-check cannot run is stopped with the typed `NativeCrossCheckPending`. A cross-check cannot run when no native reader is registered through a committed acceptance record. The stop comes after cleanup, ledger and scan. Batch records the take as failed after its drive started, so it needs a ruling. It is never graded, never readers-disagree, never re-run, and never counted as a harness-error.

**What the registered text does and does not say:** it names the graded record, the stream cross-checked with the native record. It does not decide what happens while that cross-check cannot run. This departure decides it.

**Effect:** the vendor arms cannot run unattended until each vendor has a registered reader.

## glitch-06's rulings on the three drive-wiring departures, recorded 14 Oct 2026 17:04 EDT (harness lane, window 2)

Ruled by glitch-06 under the standing delegation, in the window 2 resume brief of 14 Oct 2026.

### D-INT-2a (ACCEPTED): a failed grant or a refused settings baseline is BLOCKED before launch, never a rehearsal

Implemented in `cd824501`.
The box contract called both a rehearsal.
Nothing ran, so neither can be routed as a take: both raise `LaunchNeedsRuling`, and batch records the launch failure BLOCKED ("failed before launch, a ruling needed"), `drive_started` false.
The loop stops; the slot goes on only by a ruling, and a restart never re-drives it.

### D-INT-2b (ACCEPTED as a departure): a settings change found after turn 1 stops the take for a ruling

Implemented in `0768f478`, with the executed-refusal road in `e0acd771`.
The box contract routes a post-k problem (and a pre-k problem for k > 1) as harness-error.
`routing.json` has no registered row that reads a settings snapshot, so routing it as harness-error would invent a meaning for a registered class.
Instead no further turn is sent, and the drive raises `DriveRefused` after cleanup, restore, postflight and scan: failed after the drive started, never re-run, for a ruling.
A pre-1 problem stays preflight's pre-turn refusal (a rehearsal), as the contract says.
Routing it as harness-error would need a registered row, which is a pre-registration change.

### D-INT-2c (ACCEPTED for now): SIDE_MODELS holds only the observed haiku key; any other side model stops the take and is reported

The closed list is `c2d03086`; the stop lands in the same commit as this section (`claude_code_adapter.unlisted_side_model` and `SideModelOffList`; test A7-served and its witness side-model-not-stopped).
`claude_code_adapter.SIDE_MODELS` is `("claude-haiku-4-5-20251001",)`, the one side model observed (the recorded sonnet probe: 915 tokens in, 11 out).
A modelUsage key beside the pin's that is off that list, on a turn whose served models are all the pin's, stops the take: the turn is an executed turn's refusal whose recorded reason names the side model and its tokens, so the driver takes the executed-refusal road (ledger, post-n settings check, scan) and the take waits for a ruling.
A real switch (an assistant record on another model, or a modelUsage without the pin's model) stays the registered init-mismatch route.
`FIRST_WALK_ACCEPTANCE` records the subagent-stream check the first walk must show.
