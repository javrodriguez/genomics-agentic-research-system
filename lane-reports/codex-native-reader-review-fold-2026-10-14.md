# Codex 0.162.1 reader: the review fold of bcdc4bca (addendum)

Parent: the harness lane's head after the integration items. Writer: Claude Code harness lane, 14 Oct 2026 03:05 EDT, under glitch-06's order after the review `review-harness-registration-fix-codex1.md` (CHANGES).
The original report, `codex-native-reader-2026-10-14.md`, stays as written.
All fixtures are synthetic and written by hand from the retained pinned source; no CLI ran.

## Finding 3 (MINOR, check-weakening): an agent-printed marker relaxed the output comparison

The writer truncates `aggregated_output` only when it exceeds `PERSISTED_COMMAND_OUTPUT_MAX_BYTES`, 64 KiB (`codex-rs/rollout/src/policy.rs:16-17, 253-258`), through `codex_utils_string::truncate_middle_with_marker`.
That function's source is not in the retained copy (`src/codex-rs/` holds no `utils/` folder), so its exact output cannot be reproduced here.
So the join now compares command output by exact equality only, the marker's text compared as ordinary text.
An exec output over 64 KiB (counted in UTF-8 bytes, as Rust's `len()` counts) refuses the join, naming the missing source.
The projection's flag is renamed `marker_text`: it says only that the marker's text occurs, never that the writer truncated.

Known consequence, fail closed: a real command whose output exceeds 64 KiB refuses its turn's join until the truncation function is retained and reproduced exactly.
Follow-up: retain `codex-rs/utils/string` at commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`, then replace the refusal with an exact reproduction.

## Nits

N10: a blank or whitespace-only line anywhere but after the last record refuses, in the rollout and in the exec stream (stricter than upstream's skip, as ruled).

N11: a Reasoning item whose summary joins to whitespace only refuses by name, since exec drops it (`exec/src/event_processor_with_jsonl_output.rs:152-156, 354-356`), so its join can never be proven.
An empty summary still projects nothing, as exec skips it too.
The other known false-refusal risks are listed in the module docstring for the first recorded pair to confirm, never admitted unseen: a `turn_aborted` with a null `turn_id`, and the line types the paginated policy persists but this subset refuses (`world_state`, `retained_context`, `security_risk_score`, `compacted`, `inter_agent_communication`, `inter_agent_communication_metadata`, `realtime_item`).

## Verification (behind a light gate)

- Red: the new `tests/test_codex_native.py` against HEAD's `codex_native.py`, in a scratch copy: 13 tests, 9 failures and 2 errors.
- Green: 13/13.
- Mutants, in memory, all killed (7): the reviewer's witness (prefix and suffix around an agent-printed marker), no 64 KiB limit, characters instead of bytes, the limit itself refused, blank lines skipped again, the final newline refused, a whitespace-only summary admitted.
- The reviewer's `witness_codex1.py` against the fold: the baseline passes; the three observations no longer hold.
  The blank-line and reasoning ones now raise the reader's refusals.
  The marker one raises a KeyError on the renamed flag before reaching the join, so it proves nothing by itself; the same attack is the test `test_an_agent_printed_marker_is_ordinary_text` and the first mutant above.
