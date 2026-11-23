# Codex 0.162.1 native reader candidate and exec join (live harness slice)

Parent: `38b70ae8`. Writer: Claude Code harness lane, 14 Oct 2026, under glitch-06's Codex order (slice 1).
The module is unregistered. All fixtures are synthetic and labelled. Every name comes from the audit's retained, blob-verified source (`/Users/javrodher/aegis-builds/gap4-codex-rollout-audit-20261014/src/`, commit `092d3acd…`), cited by path and line in `codex_native.py`. I re-read each cited line myself; the audit is research input, not reviewed truth. One audit-derived citation was corrected: `AgentMessageContent` is at `items.rs:125-127`.

## What it reads (fail closed)

**Rollout, the paginated subset (the mode `codex exec` uses)**
- The first line must be `session_meta`, with `cli_version` `0.162.1` and `history_mode` `paginated`.
- Every line must decode. One that does not aborts the read; upstream skips such lines, and this reader never does.
- Line keys come from a closed set. Ordinals must be contiguous.
- Line types come from the 12 pinned ones. Event types come from what the pinned paginated policy persists. A legacy-only event refuses, and so does a never-persisted one (for example `error` or `model_reroute`), because either would mean a different writer.
- `response_item` tags come from the persisted list. Anything else would be serde `Other`, so it refuses.
- Turns open with `task_started` and close with `task_complete` (marked failed when it carries an error) or `turn_aborted` (aborted). A turn still open at the end is incomplete.
- Projected items: one text `UserMessage` per turn, `AgentMessage` (its Text parts concatenated), `Reasoning` (summary text) and `CommandExecution`. Every other `TurnItem` refuses in this subset.
- A truncation marker in `aggregated_output` is kept and flagged.
- `approval_policy` and `sandbox_policy` values are placeholders the audit did not verify. They are never accepted, so `permission_mode` stays None.
- Legacy history, fork history, compaction, rollback and the other line types refuse in this subset.

**Exec stream**
- It must start with exactly one `thread.started`, and hold exactly one `turn.started` per call.
- Event and item tags come from the pinned enums.
- Projected items: `agent_message`, `reasoning`, `command_execution` and `error`. Everything else refuses in this subset.
- An error item reading `model rerouted: A -> B (…)` is the only evidence of the served model, so the served model is B. Without one, the served model is unknown.
- Item ids and the presentation-only command text are never compared.

**The join, matched by order and type**
- The thread id must match.
- Agent texts must match exactly.
- Reasoning summaries must match.
- Commands must match in count, status and exit code. Their output must match exactly. When the native output carries the truncation marker, the comparison is by prefix and suffix. A native None must pair with an exec empty string.
- Terminals pair as follows: complete with `turn.completed`; failed with `turn.failed`; aborted with no terminal plus exit 1; incomplete with no terminal. No terminal with exit 0 refuses.

## Verification (each run behind a fresh light gate)

- **Red:** 10 tests, 9 errors (the module was absent).
- **Green:** 10/10.
- **Mutants:** ten in-memory mutants, each failing at least one assertion. Four of them also raised errors in other tests: any CLI version, ordinals unchecked, aborted read as complete, and agent text unchecked.

## What can never be observed (from the audit, re-checked)

- The served model when no reroute happened.
- Encrypted reasoning, and `encrypted_function_args`.
- `FunctionCallOutputPayload.success`.
- `ErrorEvent.misalignment`.
- Output above 64 KiB beyond the truncation marker. Only exec holds it live, and only when exec did not backfill it from the rollout.
- Exec items dropped under backpressure.
- The user prompt and model-facing tool results on the exec side.

## Not run, owed

- A real recorded stream and rollout pair.
- Registration, on the corrected acceptance pattern.
- Independent review.
