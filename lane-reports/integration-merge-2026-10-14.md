# Integration merge, Gap Study round 4 live box and live harness, 14 Oct 2026

Writer: the integration lane (sole writer), under orchestrator glitch-06.
Clone: `/Users/javrodher/aegis-builds/gap4-live-merge-20261014`, branch `gap4/live-merge-20261014`, cloned with `--no-hardlinks` from the box checkout.
Common base: `a12569a` (W12, reviewed, Athena 246/246).
Nothing was pushed.

## Merges

| Merge commit | What came in | Conflict hunks |
|---|---|---|
| `96b31d32` | harness head `d56cebf0` into box head `db252b9e` | none |
| `5ae385a8` | harness head `beecc274` (glitch-06 moved the harness head after the first merge) | none |
| `01e12172` | box head `c6a6637e` (the box lane's fix of the preflight audit defect, `3a3716a0`, and its sidecar-contract follow-ups) | none |
| `0d2085ee` | box head `0f7cdbfd` (audit and importlib fixes, the r2 rulings incl. `b2a470f8`'s strict `ignored_newline_paths`) | none |
| `7b5a9dd4` | harness head `86ca78e6` (the Codex stub exec on glitch-06's option a, and the harness-owned fixes queued after run `gap4-merge-01e1217`) | none |
| `2189a8e5` | box head `0dbe18ed` (the reviewed lock writer and the build records; the real locks had not landed by 05:03) | none |
| `71b1cc7f` | harness head `9649aa0a` (batch 8 and the three harness reds of run `gap4-merge-a1f7405`) | none: see the R3DeadWalk line below |

How "no conflict" was checked: `comm -12` of `git diff --name-only a12569a <box head>` and `git diff --name-only a12569a <harness head>` printed no path for the first merge, so no file was changed on both sides.
For `0d2085ee` and `7b5a9dd4`, `comm -12` of the two heads' changed paths since `fa98717e` (`git diff --name-only HEAD...<head>`) printed no path, so again no file was changed on both sides.
`b2a470f8`'s three edits outside the box lane (`probes4.py`, `tests/test_new_tasks.py`, `tests/test_plan_gate.py`) were changed by neither the harness branch nor this branch.
On the merged tree (`7b5a9dd4`), a search for literal watcher-stop records without `ignored_newline_paths` finds only `tests/test_box_integration.py:1643`.
That record feeds the lenient `drive.sidecar_health`, not endstate, and the box lane owns the file; `box/sidecar.py:789` passes the field on its next line.
Each later merge reported "Automatic merge went well" and left no unmerged path in `git status`.

## Conflict resolutions, one line per hunk

- `71b1cc7f`, `evals/gap-study-4/tests/test_walk_runner.py`, `R3DeadWalk.test_a_ledgerless_walk_with_only_a_launch_journal_is_refused` strip loop: the harness lane mirrored `492af633` byte for byte, so git merged it with no conflict marker. `git diff harness/<head> -- tests/test_walk_runner.py` is empty, so the merged file is the harness lane's text, as glitch-06 ruled.

There were no conflict hunks in any of the three merges, so there are no resolution lines.

## Cross-lane edits after the merge (not conflict hunks)

These are expectation and fixture updates to harness-owned tests that the box lane could not touch.
No production file was changed.

- `tests/test_walk_wiring.py` `sidecar_for`: the fake sidecar expectation now names the accepted launch (boot user, the four boot inspect capabilities, image, setpriv cmd, empty entrypoint). Justified by `0b6f60f9`'s contract, the matching fake inspect in `test_box_integration` (`5f1b33ee`), and `gap4-review-box-witness-20261014/review-box-witness-locks.md` (PASS).
- `tests/test_walk_builders.py` B9 `sidecar_for`: the same change, for the same reason.
- `tests/test_walk_builders.py` B2: a Codex API-key login file is now expected to be refused with the subscription words, before any open, and the refusal must not carry the value. Justified by `0b6f60f9` (owner amendment 13 Oct; `walk_builders.login_name`) and `test_live_box.SubscriptionTransitionRegression`.
- `tests/test_env_allowlist.py` E2: the exec-shape checks now run over the two arms that still exec (`EXEC_ARMS`), and a new check binds that a Codex turn refuses `NotReady` before its login is read. No witness changed; the witnesses report 17 of 17 red. Justified by `0b6f60f9` (`run_take.exec_argv`).

These edits are in commit `daf4311b`.

A second pair came from the first athena battery on the merged head (`gap4-merge-01e1217-20261014T052729Z`).
The harness lane's tests had simulated the box's launch journal, because its branch had no box that wrote one; on the merged head the box's `run_turn` writes it (`0b6f60f9`).

- `tests/test_identity_mode_evidence.py` `Journal`: wraps the box's real `run_turn`, then removes its journal (`write=False`) or rewrites its argv (`edit`). It no longer writes a journal of its own, which the box now refuses.
- `tests/test_identity_evidence.py`: a plain Gemini turn now reads its mode from the submitted argv, as `91eb1754`'s own comment anticipated ("the box writes it"). A turn with no journal is still bound as unobserved by `test_identity_mode_evidence`.

These edits are in commit `fa98717e`; athena subset `gap4-merge-fa98717-20261014T060727Z` read PASS-SUBSET (2 of 2).

A third came from the battery on `a1f74059` (`gap4-merge-a1f7405-20261014T065439Z`).

- `tests/test_walk_runner.py` `R3DeadWalk.test_a_ledgerless_walk_with_only_a_launch_journal_is_refused` (harness `97fb09fe`): its control strips every turn sign from a committed walk. It did not strip the `turn-N.jsonl.launch.json` files that the box's `run_turn` now writes (`0b6f60f9`), so the control was refused. The strip now removes them too; the refusal assertion is unchanged.

This edit is in commit `492af633`; athena subset `gap4-merge-492af63-20261014T073256Z` read PASS-SUBSET (1 of 1).

The Codex adapter tests were moved to a login-free stub exec by the harness lane itself (`86ca78e6`, glitch-06's option a). This lane did not edit them.

A fourth came on the merged head after `71b1cc7f`.

- `tests/test_gemini_adapter.py` A11 and A14 (harness `eace8897`, `da021cde`): A11 expected an end-to-end turn's mode unobserved, and A14 planted each turn's journal before the turn. The box's `run_turn` now writes the journal and refuses one already there (`0b6f60f9`). A11 now expects the submitted argv's mode, and A14 no longer plants the journal; every mode assertion is unchanged. This is in commit `ce852b01`.
  Mac: 143 tests OK, 114/114 witnesses red, generated-mutant shards 1-16 each with 0 survivors and 0 stale.

Harness `a36a5743` (newer than `9649aa0a`, not in the harness's green subset) was left for the next re-merge. It touches `tests/test_identity_mode_evidence.py`, which `fa98717e` also changed, so that merge may carry a hunk.

## Not changed, and why (as of the 01:28 merge; superseded where the lanes since fixed them)

- `tests/test_codex_adapter.py`: every Codex turn check (A4, A5, A6, A7's turn clause, B1, B2, B9 and six witnesses) drives a turn through `run_take.run_turn`, which the transition refuses.
  Moving it to the transition would mean either bypassing the refusal in a fake (re-enabling the API-key route in the test) or retiring checks and witnesses (loosening the instrument).
  Both are outside a fixture update, so they are held for a ruling.
- `tests/test_run_take.py` audit (5 failures): this is the box lane's second real finding, that preflight reads `run_take.GEMINI_MODE_ROUTE_VARIABLES`, which `MODULE_ATTRS` does not list.
  The box lane holds it for a ruling (`3a3716a0`), and it is not this lane's to change.
- COPIED.d and checks.d: no declaration was needed. On the merged head `copy_manifest.py --check` and `freeze.py --check` both report ok (390 files from 57 fragments).
