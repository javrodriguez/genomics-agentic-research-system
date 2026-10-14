# Codex slice 3: the arm O registration road

Writer: Claude Code harness lane, 14 Oct 2026, under glitch-06's order (arm O, on the corrected pattern of the Gemini road).
Parent: `19ec4c41`. Fakes only; no CLI ran, and no acceptance record was written into the study.

## What was built

**Where the rollout is.**
`native_snapshot.codex_rollout_file(home, thread)` locates `<home>/sessions/<Y>/<MM>/<DD>/rollout-<YYYY-MM-DDTHH-MM-SS>-<thread>.jsonl` exactly, per audit Addendum B:
- `recorder.rs:1740-1762`, `rollout_file_name.rs:62-74` (blob `61ad43cd`, re-hashed here), and `SESSIONS_SUBDIR` at `lib.rs:86`;
- the year folder is unpadded and the month and day are two digits;
- the name's date must equal its folder's (one local instant);
- no time is read from the name, and it is never compared with `session_meta`'s UTC timestamp;
- a reverted `_<rollout id>` name or a `.jsonl.zst` refuses, as do none or two matches and a link.

`CODEX_HOME` is the take's config mount: `box/run_take.py` `TAKE_ENV[CODEX]` holds `"CODEX_HOME": CONFIG_MOUNT` (read only), so the host reads the rollout in the take's config folder.

**The adapter and the driver.**
- `CodexAdapter.native_session_path` names that rollout by turn 1's thread id, so the driver retains it after each turn, as it does Gemini's session.
- Without a `rollout_for`, `harness_adapter_for` reads the rollout live from the same place; a rollout that cannot be located refuses the turn.
- `drive.codex_cross_check` runs the one shared join, `native_reader_registration.codex_join_session` (`codex_native.read_rollout` and `join` per turn: one turn per exec stream, each complete).
- A Codex take's cross-check now comes from its retained rollouts exactly as a Gemini take's does: pending without a registered Codex reader, refused when nothing was retained, agreed only when every turn joins.
- The old always-pending Codex branch is gone.

**The registration.**
`native_reader_registration` now holds one profile per harness (`PROFILES`): pinned CLI, arm, acceptance and review names, reader, sources, floor, join, session id source, ledger keys and metadata.
Codex:
- CLI `0.162.1`, arm O;
- `native-readers/codex-acceptance.json` and `codex-review.md`, both already claimed by the `native-readers/**` pattern;
- the reader is `codex_reader` (codex_native's projection, the requested model only);
- the sources are `codex_native.py`, `native_reader_registration.py`, `drive.py`, `vendor_provenance.py` and `native_snapshot.py`;
- the floor is 2 interactions and 1 command round trip;
- the ledger keys add `served_model` (D-INT-2), and the session comes from turn 1's `thread.started`.

Every gate of the Gemini road applies unchanged: the committed tree, the walk commit, writer-equal records, the full ledger, launch journals, regrade re-derivation, the principals and the synthetic marker last.
`production_readers` returns each harness whose record holds.
`walk_regrade` regrades Codex walks through `drive.codex_cross_check`.

## Verification (behind a light gate)

The real road in scratch repositories: `WalkDriver` with `harness_adapter_for`, the production `CodexAdapter` on a fake box (`codex exec --json` streams and a growing rollout), the login-free stub exec of ruling (a) with the box-schema journal, `walk_runner`, and `WalkRepo`.

`test_pending_codex_walk` (new) covers:
- a pending Codex walk committed with its two retained rollouts and `served_model` recorded unobserved;
- a positive registration;
- seven single mutations, each refused for its own reason;
- a marked rollout refused last;
- the shared join's refusals and the Codex floor;
- with a reader registered, the driver's history joining and its cross-check agreeing, so the checker reads the take;
- a regrade from the committed bytes.

Also changed and covered:
- `test_native_snapshot` adds `CodexRollout` (the exact name, and eight refusals);
- `test_codex_adapter` adds B13, the rollout located by the thread;
- `test_vendor_take_records`, `test_vendor_checker_road` and `test_vendor_record_binding` are updated: a Codex take is now native, and the factory reads the live rollout.

Lint: `lint_language` and `lint_pooling` over the whole tree are clean on this head.
Three phrases of mine are reworded within the lint's rules (none excused): two uses of a banned word in `COPIED.d/live-harness-foundation.json:127`, plus `always` and a `15/15` ratio in `COPIED.d/w11a-codex-adapter.json`.

Results, mutants and the red-first runs are in the commit message.
