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
| `0afb6825` | box head `6221c297` (the five reviewed image locks, schema 2, with the post-write guard) | none |
| `9588a563` | harness head `840048ab` (carries `a36a5743`, `19ec4c41` and the lint fix) | none: see the test_identity_mode_evidence line below |
| `fe2f5bdf` | harness head `8a598b49` (carries `75a8074d`, D-INT-2: `served_model_rule.codex`) | none: see the draft-file lines below |
| `c3a0cb77` | box head `ba2995ee` (the test_egress fix; its parent `2dd00dc7`, the egress pin at preflight, is under review) | none |
| `9a92e4ce` | box head `1bbc2e77` (`e05805c1`, `1bbc2e77`: tests and evidence only) | none |
| `34c5098f` | box head `6c775f67` (`ba1fcf42` CP5 STUDY_PATHS and LEAK_WORDS; `f5c17498` TOP_FORMAT, INSPECT_STATUS, VERSION_PATTERNS; `6c775f67` FALLBACK_ENV) | none |
| `47632770` | harness head `3740f8f6` (CP5 arm A pin_profiles and status) | prereg-draft.json: see below |
| `e3309476` | box head `d65d81b8` (the ownership, settings, caps and scanner set, `6a29d6e2..32246b0c`; the STUDY_RECORD_DIRS fix `20237a3d`) | none |
| `bfed7c44` | harness head `e3f5010b` (ownership wiring `4c2d805f`, operator-step routing, the three CP5 checks.d lines) | one hunk: see below |
| `10408dc4` | box head `d73c43ed` (`22b15f56..d73c43ed`, reviewed PASS, incl. the E2 fix `544c6ddb`) | test_env_allowlist.py: see below |
| `daf5d94c` | harness head `9425bf62` (wiring `4c2d805f..9425bf62`, merged for signal: **review MAJOR open on `4c2d805f`**, the driver ledger written into the watcher-owned evidence folder, fix in progress; carries `0768f478`, which must come in with box ≥ `22b15f56`'s settings_guard `model=`, and does) | none |
| `7225f22d` | box head `03180228` (`1eb02a9e` walk-token road, `8ad2978a` scanner binding moved, `03180228` operator-list folds) | none; see the walk_builders lines below |
| `9783d584` | harness head `573b5a61` (`fcb0fb80`, `573b5a61`) | none |
| `de6616a3` | harness head `1e8d0cd3` (the scanner-class fix) | one hunk, `walk_builders.py` `production_builders`: see that commit |
| `9991f26a`, `40acb6de` | box heads `60093f55`, `5c73dab4` | none |
| `1ff9ade2` | box head `72239cd4` (`2fd8215a..72239cd4`: the Codex lease postflight, `lease_secrets`, the lease gate, the no-login launcher, the Codex row with no API-key route) | none |
| `4e30d774` | harness head `1f032586` (`cd824501..1f032586`) | one hunk, `tests/test_walk_builders.py`: see below |
| `2d6983e9` | box head `39fc4f0a` (`41fccf4c` review folds, `39fc4f0a` athena redeploy and postflight case probe) | none |

How "no conflict" was checked: `comm -12` of `git diff --name-only a12569a <box head>` and `git diff --name-only a12569a <harness head>` printed no path for the first merge, so no file was changed on both sides.
For `0d2085ee` and `7b5a9dd4`, `comm -12` of the two heads' changed paths since `fa98717e` (`git diff --name-only HEAD...<head>`) printed no path, so again no file was changed on both sides.
`b2a470f8`'s three edits outside the box lane (`probes4.py`, `tests/test_new_tasks.py`, `tests/test_plan_gate.py`) were changed by neither the harness branch nor this branch.
On the merged tree (`7b5a9dd4`), a search for literal watcher-stop records without `ignored_newline_paths` finds only `tests/test_box_integration.py:1643`.
That record feeds the lenient `drive.sidecar_health`, not endstate, and the box lane owns the file; `box/sidecar.py:789` passes the field on its next line.
Each later merge reported "Automatic merge went well" and left no unmerged path in `git status`.

## Conflict resolutions, one line per hunk

- `71b1cc7f`, `evals/gap-study-4/tests/test_walk_runner.py`, `R3DeadWalk.test_a_ledgerless_walk_with_only_a_launch_journal_is_refused` strip loop: the harness lane mirrored `492af633` byte for byte, so git merged it with no conflict marker. `git diff harness/<head> -- tests/test_walk_runner.py` is empty, so the merged file is the harness lane's text, as glitch-06 ruled.
- `9588a563`, `evals/gap-study-4/tests/test_identity_mode_evidence.py`: harness `a36a5743` changed `AcceptancePerHarness` (Codex now has an identity source table), and this lane's `fa98717e` changed the `Journal` fake. The lines do not overlap, so git merged them with no conflict marker and both are kept. The merged-head `Journal` that wraps the box's real `run_turn` stays, as glitch-06 ruled.
- `9588a563`, `evals/gap-study-4/tests/test_gemini_adapter.py`: the harness branch did not change this file after `ce852b01`, so this lane's A11/A14 change carries through unchanged.
- `fe2f5bdf`, `evals/gap-study-4/build_draft.py`, `prereg-draft.json` and `tests/test_build_draft.py`: the harness hunks (`served_model_rule.codex` from routing) and the box hunks (the new-folder residual) are on separate lines. Git merged them with no conflict marker, and both are kept.
- `34c5098f`, `evals/gap-study-4/tests/test_env_allowlist.py`: the box hunks and this lane's `daf4311b` `EXEC_ARMS` hunks merged with no conflict marker; both are kept.
- `47632770`, `evals/gap-study-4/tests/test_walk_builders.py` and `tests/test_walk_wiring.py`: the harness CP5 hunks (`EXPECTED_MISSING` without `pin_for`, `CP5_PROFILES`) and this lane's sidecar-fake hunks touch separate lines, so there was no conflict marker and both are kept.
- `47632770`, `evals/gap-study-4/prereg-draft.json`: a real conflict between the two lanes' generated drafts. In the merge commit it is resolved with the harness lane's text as a placeholder only. `d1b018e5` then regenerates it with `build_draft.py`, as glitch-06 ruled.
- `e3309476`, `evals/gap-study-4/tests/test_stub_take.py`: the box hunks and this lane's `e0a4f957` repin (`ADAPTER_CHECK_SHA256 = 47cdad38…2717`, ruled by glitch-06 and citing `c35fc915`) do not overlap, so there was no conflict marker and the repin is kept.
- `bfed7c44`, `evals/gap-study-4/tests/test_build_draft.py`, `R6.unpinned` (a conflict): this lane's `32e688ae` form met the harness lane's mirror of the same ruled rule. I took the harness lane's text: it is the owner's, it uses the same rule, and it also binds `version_pins`' `agent_version`.
  Direct reads of `core_problems` on the merged draft: the clean draft gives `[]`. The `0.0.0-fake` mutant, an O row given a version and an A row set to null each give `['R6.unpinned']`.
  Correction (the follow-up commit "restore the box hunks"): `bfed7c44` took the harness lane's whole file, not only that hunk, and that dropped the box lane's `NEW_FOLDER_RESIDUAL` lines (`b2a470f8`). The Mac showed `R8.residuals` and `R8.mode-residual` red.
  The follow-up commit reruns the three-way merge (`git merge-file --diff3`), keeps every non-conflicting hunk from both sides, and takes the harness lane's text only in the `R6.unpinned` hunk. test_build_draft: Ran 47, OK.
- `bfed7c44`, `prereg-draft.json`, `tests/test_box_integration.py`, `tests/test_walk_builders.py`, `tests/test_walk_wiring.py` and `walk_builders.py`: no conflict marker.
  `build_draft.py --check` printed ok on `bfed7c44`, so the draft was not regenerated.
- `claude_code_adapter.py`: glitch-06 expected the box's `--settings` argv edit to meet the harness lane's version. The harness branch did not change this file after the last merge, so the box's argv change came in without a conflict.
- `10408dc4`, `evals/gap-study-4/tests/test_env_allowlist.py`, four hunks (E2's three arm loops and the launcher-credential check): a conflict between this lane's `daf4311b` `EXEC_ARMS` form and the box lane's reviewed `544c6ddb` rewrite.
  The box rewrite runs every arm, Codex through `launch_for`, and binds the Codex refusal itself with the login read forbidden.
  I took the box lane's file whole, because it supersedes `daf4311b`.
  The unused `EXEC_ARMS` and this lane's duplicate Codex refusal test go with it.
  Mac: 28 tests OK; witnesses 17/17 red.
- `10408dc4`, `tests/test_box_integration.py`, `tests/test_build_draft.py` and `walk_builders.py`: no conflict marker.
- `daf5d94c`, `claude_code_adapter.py`: no conflict marker. The box's `--settings` argv stays in `argv()`; the harness hunks are in `read_stream` (`served_models`, `model_usage`).
- `daf5d94c`, `tests/test_box_integration.py`, `tests/test_claude_code_adapter.py`, `tests/test_walk_builders.py`, `tests/test_walk_wiring.py` and `walk_builders.py`: no conflict marker.
- `7225f22d`, `evals/gap-study-4/walk_builders.py` `production_builders`: box `8ad2978a`'s hunk, which binds the scanner through `rules_scanner.real_rules_scanner()`, merged without a marker beside harness `786be12c`'s per-walk build.
  **Not reconciled (a finding):** `walk_rules_scanner` (`786be12c`) still requires `type(scanner) is scan_record.RealRulesScanner`, and `8ad2978a` moved that class to `rules_scanner.RealRulesScanner`.
  Reproduced on `9783d584`: `walk_rules_scanner(rules_scanner.RealRulesScanner instance, ..., real=True)` raises `BuilderRefused: a real walk scans only with the pinned scanner (scan_record.RealRulesScanner), never RealRulesScanner`.
  `test_walk_builders` does not catch it, because it patches `scan_record.RealRulesScanner` with `create=True`.
  The fix is a production change in the harness lane's file plus its test, so this lane did not make it.
- `9783d584`, `tests/test_box_integration.py`, `tests/test_walk_builders.py` and `tests/test_walk_wiring.py`: no conflict marker.
- `4e30d774`, `evals/gap-study-4/tests/test_walk_builders.py`, after `EXPECTED_MISSING`: this branch's `TAKE_A_LOCK_READY` block (`6e965d12`) met the harness `8b3adf14` text.
  The harness text carries that block byte for byte (the two 14-line spans compared with `cmp`: identical) and appends the `WALK_LOGIN_ON_TREE` block.
  Resolved with the harness text in that hunk; every other hunk of both sides kept.
- `1ff9ade2`, `walk_builders.py`: the box hunk (`lease_secrets`, after `login_secrets`) and the harness hunks touch separate lines; no conflict marker.

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

## The draft regenerated on the merged head (`75ba79ef`)

glitch-06 ruled that `prereg-draft.json` be regenerated where both lanes' inputs meet: box `6221c297` (the image locks) and harness `75a8074d` (`served_model_rule.codex`).
It was run on `fe2f5bdf` by the writer's own path, `python3 -B -W ignore evals/gap-study-4/build_draft.py` with no arguments.
That run wrote 1260 planned tries and 126 half-cells, with 51 pending inputs.
The diff below compares JSON paths in the regenerated draft against the merged head's committed draft (`git show fe2f5bdf:evals/gap-study-4/prereg-draft.json`); long values are cut at 160 characters.
- `served_model_rule.codex` does not appear in it, because the harness merge already carried that rule into the committed draft.
- Every entry is derived from the image locks: the five `image_locks` entries, the seven `version_pins/*/image_version` values, and the 25 lock keys leaving the pending map and the pending-key list `/stats_design/PENDING` (76 entries before).
- For each of the five locks, the `sha256` and `lock` in the draft equal the committed lock file's bytes.
- Nothing else moved.
- After the commit, `build_draft.py --check` printed ok.
- After the box re-merge `c3a0cb77`, it is still ok, so no second regeneration was needed.

```
changed /image_locks/0/lock/base | "PENDING" -> "docker.io/library/node@sha256:efd0ab5780c2d9ab1f0f869571a00d5edb17793bff4cce4a2792e3eb0ffc7562"
added /image_locks/0/lock/config_digest | null -> "sha256:4647fdaace69f1e9083d0c1424192f81ac3ad43c4382ce5f7d1ec8cfda52c175"
changed /image_locks/0/lock/harness/version | "PENDING" -> "0.162.1"
changed /image_locks/0/lock/image_id | "PENDING" -> "sha256:21b214159e4eb02d5e73f78ccdf5ee047da2fc6944808f9a454a6b0f427dd381"
added /image_locks/0/lock/manifest_digest | null -> "sha256:46deefc20439372cbdfabbaa023fe71aed4d4dbee518c729d3b23b52c8d03aa3"
removed /image_locks/0/lock/pending/base | "the shared base digest is read and pinned when CP2 builds on the real box; that base must also supply node and npm, confirmed at the same pin" -> null
removed /image_locks/0/lock/pending/harness.version | "the latest stable on the day CP2 builds the image (D8 B2 item 2), never bumped after the first counted walk; D8's 6 Oct reading is history, never the pin" -> null
removed /image_locks/0/lock/pending/image_id | "only a built image has an id; recorded when CP2 builds the image on the real box" -> null
removed /image_locks/0/lock/pending/python | "the image's own python3 version, read from the pinned base when CP2 builds the image (F-16)" -> null
changed /image_locks/0/lock/python | "PENDING" -> "3.11.2"
changed /image_locks/0/lock/schema | 1 -> 2
added /image_locks/0/lock/source_commit | null -> "ad766f016693b60e94a2819368a206fa580176d2"
changed /image_locks/0/sha256 | "0970bf678e251cd9b67c73f6b659fe170261e2c169c8d10ada2b55691c4871f8" -> "b668a1263536730385cc0894b696473c51d1c2aa3e0452aadb45d78cb8748467"
changed /image_locks/1/lock/base | "PENDING" -> "docker.io/library/debian@sha256:a4672c0cb26fbdde88e38fa2dfb6c681942306680e41e4378b28770b6e79ee91"
added /image_locks/1/lock/config_digest | null -> "sha256:388fbbc4d0cc6ea5ad8a942a779643d7842e2da4eeb96f5fd2930a888ec8161f"
changed /image_locks/1/lock/image_id | "PENDING" -> "sha256:5055a840860667f02f7425f855f27ac3ef3c6b16da19afb794863a66f8147674"
added /image_locks/1/lock/manifest_digest | null -> "sha256:24c9fbdf938114d2ff412a70f5b2f2d08f2c4f7735ab7c229c8ad254dc02a89d"
removed /image_locks/1/lock/pending/base | "the egress image's own base digest, read and pinned when CP2 builds on the real box" -> null
removed /image_locks/1/lock/pending/image_id | "only a built image has an id; recorded when CP2 builds the image on the real box" -> null
removed /image_locks/1/lock/pending/squid | "the squid package version the pinned base's archive offers, read and pinned when CP2 builds the egress image; squid -k parse on that build is a real-box check" -> null
changed /image_locks/1/lock/schema | 1 -> 2
added /image_locks/1/lock/source_commit | null -> "ad766f016693b60e94a2819368a206fa580176d2"
changed /image_locks/1/lock/squid | "PENDING" -> "5.7-2+deb12u6"
changed /image_locks/1/sha256 | "0d840c02f881f96121a9cb68f5f176183447c44437d9a7d970f084cc6b448f50" -> "3480fe6c72730e4a8159e3e867b08e43ffeb23050a6d6ef43bfb28d8221d9a20"
changed /image_locks/2/lock/base | "PENDING" -> "docker.io/library/node@sha256:efd0ab5780c2d9ab1f0f869571a00d5edb17793bff4cce4a2792e3eb0ffc7562"
added /image_locks/2/lock/config_digest | null -> "sha256:6bba97e7c55af01c1831ab214fb8eb343772859ee152c7702e00f108ecd7c1f6"
changed /image_locks/2/lock/harness/version | "PENDING" -> "0.64.0"
changed /image_locks/2/lock/image_id | "PENDING" -> "sha256:d10aa00b5958b00d1c719be1f0572967c04f30bfe381a427107c9e9a3f16b013"
added /image_locks/2/lock/manifest_digest | null -> "sha256:7eb4c799f29fe5330d9cf76deae8988ea04f8183ee451a5dad4f12bcb00eee9f"
removed /image_locks/2/lock/pending/base | "the shared base digest is read and pinned when CP2 builds on the real box; that base must also supply node and npm, confirmed at the same pin" -> null
removed /image_locks/2/lock/pending/harness.version | "the latest stable on the day CP2 builds the image (D8 B2 item 2), never bumped after the first counted walk; D8's 6 Oct reading is history, never the pin" -> null
removed /image_locks/2/lock/pending/image_id | "only a built image has an id; recorded when CP2 builds the image on the real box" -> null
removed /image_locks/2/lock/pending/python | "the image's own python3 version, read from the pinned base when CP2 builds the image (F-16)" -> null
changed /image_locks/2/lock/python | "PENDING" -> "3.11.2"
changed /image_locks/2/lock/schema | 1 -> 2
added /image_locks/2/lock/source_commit | null -> "ad766f016693b60e94a2819368a206fa580176d2"
changed /image_locks/2/sha256 | "f2157dca8e8bd9db98d4ae96343951ee56b061a72eeba4f34bb2757bafdfeead" -> "e9e5dab642c93530a7995c1237962459ee9dc468ea53549e41f81025dcd6e4f5"
changed /image_locks/3/lock/base | "PENDING" -> "docker.io/library/node@sha256:efd0ab5780c2d9ab1f0f869571a00d5edb17793bff4cce4a2792e3eb0ffc7562"
added /image_locks/3/lock/config_digest | null -> "sha256:da2067d3ee9f1eeea61afc39cdeddadfed2bd9d339382f8b1ccd8cbd1b9d33a6"
changed /image_locks/3/lock/harness/version | "PENDING" -> "2.1.296"
changed /image_locks/3/lock/image_id | "PENDING" -> "sha256:336aa8cd024f0781c3ae3223e70bb0df15d9ad052fb1ec935deb2294b17c8b49"
added /image_locks/3/lock/manifest_digest | null -> "sha256:c8d50caa6de74e8c1761aaf572e2ef8f6d2d573a69bb851af02395f6106366e8"
removed /image_locks/3/lock/pending/base | "the shared base digest is read and pinned when CP2 builds on the real box; that base must also supply node and npm, confirmed at the same pin" -> null
removed /image_locks/3/lock/pending/harness.version | "walked before it is pinned (the checker reads record shapes specific to each version); the latest stable on the day CP2 builds the image, never bumped after th -> null
removed /image_locks/3/lock/pending/image_id | "only a built image has an id; recorded when CP2 builds the image on the real box" -> null
removed /image_locks/3/lock/pending/python | "the image's own python3 version, read from the pinned base when CP2 builds the image (F-16)" -> null
changed /image_locks/3/lock/python | "PENDING" -> "3.11.2"
changed /image_locks/3/lock/schema | 1 -> 2
added /image_locks/3/lock/source_commit | null -> "ad766f016693b60e94a2819368a206fa580176d2"
changed /image_locks/3/sha256 | "82db89a8825781db0a9c1f0cee78fc2f4c739295d32a2ff0bdb05f8fbd6e0d57" -> "f181a29f204fb37b2621d81654b908049ad97e83860ba8e3dba36920da3ab513"
changed /image_locks/4/lock/base | "PENDING" -> "docker.io/library/node@sha256:efd0ab5780c2d9ab1f0f869571a00d5edb17793bff4cce4a2792e3eb0ffc7562"
added /image_locks/4/lock/config_digest | null -> "sha256:80951705c2ce29d10782ca4b664c4ee14b680c6ed6fdc8197f45caabad828dfe"
changed /image_locks/4/lock/image_id | "PENDING" -> "sha256:13d0597e231ca7f9176f77e8bc4b9f263bcdafd24e375f27145a7dc79e91069d"
added /image_locks/4/lock/manifest_digest | null -> "sha256:c1409b3323bc991d9c86ed99411455ffba3aabbe6159384d0786216aba092a82"
removed /image_locks/4/lock/pending/base | "the shared base digest (the take images' base), read and pinned when CP2 builds on the real box" -> null
removed /image_locks/4/lock/pending/image_id | "only a built image has an id; recorded when CP2 builds the image on the real box" -> null
removed /image_locks/4/lock/pending/python | "the image's own python3 version, read from the pinned base when CP2 builds the image (F-16); the sidecar program's floor is 3.11" -> null
changed /image_locks/4/lock/python | "PENDING" -> "3.11.2"
changed /image_locks/4/lock/schema | 1 -> 2
added /image_locks/4/lock/source_commit | null -> "ad766f016693b60e94a2819368a206fa580176d2"
changed /image_locks/4/sha256 | "4c139b3c4fe40e6e375eb123384d5ddff6b48ac2dd251ec32cb22d84382881c1" -> "90aacb863532a9e7472127f70d7257c44ca87d02440cbdfa8b5f7bb5933fb7a4"
removed /pending//image_locks/0/lock/base | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/0/lock/harness/version | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/0/lock/image_id | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/0/lock/python | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/1/lock/base | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/1/lock/image_id | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/1/lock/squid | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/2/lock/base | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/2/lock/harness/version | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/2/lock/image_id | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/2/lock/python | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/3/lock/base | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/3/lock/harness/version | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/3/lock/image_id | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/3/lock/python | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/4/lock/base | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/4/lock/image_id | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//image_locks/4/lock/python | "R6 plan 828: CP2 supplies built image and version pins." -> null
removed /pending//version_pins/claude-code/claude-haiku-4-5-20251001/image_version | "R6/R14 plan 828, CP5-req 49: routing and image pins require the same measured version." -> null
removed /pending//version_pins/claude-code/claude-opus-5-5/image_version | "R6/R14 plan 828, CP5-req 49: routing and image pins require the same measured version." -> null
removed /pending//version_pins/claude-code/claude-sonnet-5-5/image_version | "R6/R14 plan 828, CP5-req 49: routing and image pins require the same measured version." -> null
removed /pending//version_pins/codex/gpt-6-luna/image_version | "R6/R14 plan 828, CP5-req 49: routing and image pins require the same measured version." -> null
removed /pending//version_pins/codex/gpt-6.1-sol/image_version | "R6/R14 plan 828, CP5-req 49: routing and image pins require the same measured version." -> null
removed /pending//version_pins/gemini/gemini-3.5-flash-lite/image_version | "R6/R14 plan 828, CP5-req 49: routing and image pins require the same measured version." -> null
removed /pending//version_pins/gemini/gemini-3.8-flash/image_version | "R6/R14 plan 828, CP5-req 49: routing and image pins require the same measured version." -> null
list-removed /stats_design/PENDING | "/image_locks/0/lock/base" -> null
list-removed /stats_design/PENDING | "/image_locks/0/lock/harness/version" -> null
list-removed /stats_design/PENDING | "/image_locks/0/lock/image_id" -> null
list-removed /stats_design/PENDING | "/image_locks/0/lock/python" -> null
list-removed /stats_design/PENDING | "/image_locks/1/lock/base" -> null
list-removed /stats_design/PENDING | "/image_locks/1/lock/image_id" -> null
list-removed /stats_design/PENDING | "/image_locks/1/lock/squid" -> null
list-removed /stats_design/PENDING | "/image_locks/2/lock/base" -> null
list-removed /stats_design/PENDING | "/image_locks/2/lock/harness/version" -> null
list-removed /stats_design/PENDING | "/image_locks/2/lock/image_id" -> null
list-removed /stats_design/PENDING | "/image_locks/2/lock/python" -> null
list-removed /stats_design/PENDING | "/image_locks/3/lock/base" -> null
list-removed /stats_design/PENDING | "/image_locks/3/lock/harness/version" -> null
list-removed /stats_design/PENDING | "/image_locks/3/lock/image_id" -> null
list-removed /stats_design/PENDING | "/image_locks/3/lock/python" -> null
list-removed /stats_design/PENDING | "/image_locks/4/lock/base" -> null
list-removed /stats_design/PENDING | "/image_locks/4/lock/image_id" -> null
list-removed /stats_design/PENDING | "/image_locks/4/lock/python" -> null
list-removed /stats_design/PENDING | "/version_pins/claude-code/claude-haiku-4-5-20251001/image_version" -> null
list-removed /stats_design/PENDING | "/version_pins/claude-code/claude-opus-5-5/image_version" -> null
list-removed /stats_design/PENDING | "/version_pins/claude-code/claude-sonnet-5-5/image_version" -> null
list-removed /stats_design/PENDING | "/version_pins/codex/gpt-6-luna/image_version" -> null
list-removed /stats_design/PENDING | "/version_pins/codex/gpt-6.1-sol/image_version" -> null
list-removed /stats_design/PENDING | "/version_pins/gemini/gemini-3.5-flash-lite/image_version" -> null
list-removed /stats_design/PENDING | "/version_pins/gemini/gemini-3.8-flash/image_version" -> null
changed /version_pins/claude-code/claude-haiku-4-5-20251001/image_version | "PENDING" -> "2.1.296"
changed /version_pins/claude-code/claude-opus-5-5/image_version | "PENDING" -> "2.1.296"
changed /version_pins/claude-code/claude-sonnet-5-5/image_version | "PENDING" -> "2.1.296"
changed /version_pins/codex/gpt-6-luna/image_version | "PENDING" -> "0.162.1"
changed /version_pins/codex/gpt-6.1-sol/image_version | "PENDING" -> "0.162.1"
changed /version_pins/gemini/gemini-3.5-flash-lite/image_version | "PENDING" -> "0.64.0"
changed /version_pins/gemini/gemini-3.8-flash/image_version | "PENDING" -> "0.64.0"
TOTAL 118
```

## The draft regenerated again for CP5 (`d1b018e5`)

It was written on `47632770` by `build_draft.py` with no arguments: 1260 planned tries, 126 half-cells and 45 pending inputs.
A second write from a different starting file gave byte-identical output.
`build_draft.py --check` printed ok, and `batch.py --check` printed `batch: routing.json ready` (exit 0).

Against the previous merged draft (the one from the `c3a0cb77` merge), there are 616 JSON-path entries, all arm A pins, what derives from them, and the status.
- `routing/sha256` equals the hash of the committed `routing.json`, which carries the profiles and the status line "RULED by Javier 14 Oct: arm A profiles registered; O and G follow when their rate-limit and spend-cap rules are set".
- `agent/version` is filled only for the 540 arm A rows, 54 predictions and 3 `version_pins` entries. The value is 2.1.296, the pin's version, which equals the take-a lock's harness version.
- No box CP5 value moved the draft.

```
   1 changed /routing/sha256
   1 changed /version_pins/claude-code/claude-haiku-4-5-20251001/permission_mode
   1 changed /version_pins/claude-code/claude-haiku-4-5-20251001/version
   1 changed /version_pins/claude-code/claude-opus-5-5/permission_mode
   1 changed /version_pins/claude-code/claude-opus-5-5/version
   1 changed /version_pins/claude-code/claude-sonnet-5-5/permission_mode
   1 changed /version_pins/claude-code/claude-sonnet-5-5/version
   6 list-removed /stats_design/PENDING
   1 removed /pending//version_pins/claude-code/claude-haiku-4-5-20251001/permission_mode
   1 removed /pending//version_pins/claude-code/claude-haiku-4-5-20251001/version
   1 removed /pending//version_pins/claude-code/claude-opus-5-5/permission_mode
   1 removed /pending//version_pins/claude-code/claude-opus-5-5/version
   1 removed /pending//version_pins/claude-code/claude-sonnet-5-5/permission_mode
   1 removed /pending//version_pins/claude-code/claude-sonnet-5-5/version
  54 type /predictions/N/agent/version
 540 type /rows/N/agent/version
   1 type /version_pins/claude-code/claude-haiku-4-5-20251001/agent_version
   1 type /version_pins/claude-code/claude-opus-5-5/agent_version
   1 type /version_pins/claude-code/claude-sonnet-5-5/agent_version
```

Against the harness placeholder in `47632770`, the families are these.
The lock fields and the new-folder residual (`box_residuals` going from 3 to 4) were already in the merged draft before this round; the agent versions are the same ones as above.

```
   5 added /image_locks/N/lock/config_digest
   5 added /image_locks/N/lock/manifest_digest
   5 added /image_locks/N/lock/source_commit
   5 changed /image_locks/N/lock/base
   3 changed /image_locks/N/lock/harness/version
   5 changed /image_locks/N/lock/image_id
   4 changed /image_locks/N/lock/python
   5 changed /image_locks/N/lock/schema
   1 changed /image_locks/N/lock/squid
   5 changed /image_locks/N/sha256
   1 changed /version_pins/claude-code/claude-haiku-4-5-20251001/image_version
   1 changed /version_pins/claude-code/claude-opus-5-5/image_version
   1 changed /version_pins/claude-code/claude-sonnet-5-5/image_version
   1 changed /version_pins/codex/gpt-6-luna/image_version
   1 changed /version_pins/codex/gpt-6.1-sol/image_version
   1 changed /version_pins/gemini/gemini-3.5-flash-lite/image_version
   1 changed /version_pins/gemini/gemini-3.8-flash/image_version
   1 len /box_residuals
  25 list-removed /stats_design/PENDING
   5 removed /image_locks/N/lock/pending/base
   3 removed /image_locks/N/lock/pending/harness.version
   5 removed /image_locks/N/lock/pending/image_id
   4 removed /image_locks/N/lock/pending/python
   1 removed /image_locks/N/lock/pending/squid
   5 removed /pending//image_locks/N/lock/base
   3 removed /pending//image_locks/N/lock/harness/version
   5 removed /pending//image_locks/N/lock/image_id
   4 removed /pending//image_locks/N/lock/python
   1 removed /pending//image_locks/N/lock/squid
   1 removed /pending//version_pins/claude-code/claude-haiku-4-5-20251001/image_version
   1 removed /pending//version_pins/claude-code/claude-opus-5-5/image_version
   1 removed /pending//version_pins/claude-code/claude-sonnet-5-5/image_version
   1 removed /pending//version_pins/codex/gpt-6-luna/image_version
   1 removed /pending//version_pins/codex/gpt-6.1-sol/image_version
   1 removed /pending//version_pins/gemini/gemini-3.5-flash-lite/image_version
   1 removed /pending//version_pins/gemini/gemini-3.8-flash/image_version
  54 type /predictions/N/agent/version
 540 type /rows/N/agent/version
   1 type /version_pins/claude-code/claude-haiku-4-5-20251001/agent_version
   1 type /version_pins/claude-code/claude-opus-5-5/agent_version
   1 type /version_pins/claude-code/claude-sonnet-5-5/agent_version
```

Each `image_locks` entry still equals its lock file's bytes.

## The draft regenerated for arm A's config templates (`3e7b1046`)

`build_draft.py --check` failed after `daf5d94c`.
Box `d3fd5305` restored `take_config`, so `take_config.files_for` now renders arm A's settings, and neither lane's committed draft carries the rendered templates.
On the Mac, the box head `d73c43ed`'s own `--check` fails the same way.
I regenerated the draft with the writer's own path.
The JSON-path diff against `daf5d94c`'s draft has 9 entries, all arm A config templates; Codex and Gemini stay PENDING.

```
type /config_templates/claude-code/claude-haiku-4-5-20251001 | "PENDING" -> {"files": [{"path": "settings.json", "sha256": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356"}], "sha256": "a2993c9b40b365cd48edd9986e4dc260
type /config_templates/claude-code/claude-opus-5-5 | "PENDING" -> {"files": [{"path": "settings.json", "sha256": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356"}], "sha256": "a2993c9b40b365cd48edd9986e4dc260
type /config_templates/claude-code/claude-sonnet-5-5 | "PENDING" -> {"files": [{"path": "settings.json", "sha256": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356"}], "sha256": "a2993c9b40b365cd48edd9986e4dc260
removed /pending//config_templates/claude-code/claude-haiku-4-5-20251001 | "R15 CP5-req 50: CP2 fills take_config's measured settings before templates can render." -> null
removed /pending//config_templates/claude-code/claude-opus-5-5 | "R15 CP5-req 50: CP2 fills take_config's measured settings before templates can render." -> null
removed /pending//config_templates/claude-code/claude-sonnet-5-5 | "R15 CP5-req 50: CP2 fills take_config's measured settings before templates can render." -> null
list-removed /stats_design/PENDING | "/config_templates/claude-code/claude-haiku-4-5-20251001" -> null
list-removed /stats_design/PENDING | "/config_templates/claude-code/claude-opus-5-5" -> null
list-removed /stats_design/PENDING | "/config_templates/claude-code/claude-sonnet-5-5" -> null
TOTAL 9
```

## RESUME HERE (Mac shutdown 14 Oct)

Written at 16:13 EDT, when Javier was turning the Mac off.

- **Merge clone:** `/Users/javrodher/aegis-builds/gap4-live-merge-20261014`, branch `gap4/live-merge-20261014`. HEAD is the commit that carries this block; its parent is `40acb6de`.
- **Heads carried:**
  - box `5c73dab4` (merged in `40acb6de`, on top of `60093f55` in `9991f26a`);
  - harness `1e8d0cd3` (merged in `de6616a3`; one conflict hunk in `walk_builders.py` `production_builders` `rules_scanner`, resolved with the harness `1e8d0cd3` hunk, as logged in that commit).
- **Checks on `40acb6de`:** `build_draft.py --check` ok, `copy_manifest.py --check` ok (414 files), `freeze.py --check` ok (415 paths). On `de6616a3`, `batch.py --check` printed `batch: routing.json ready`.
- **Athena runs:**
  - Running: `gap4-merge-40acb6d-20261014T194627Z` (head `40acb6de`, solo, full). The launch completed, so it runs without the Mac. Do not cancel it.
  - Finished, already read: `gap4-harness-alone-c2d0308-20261014T190412Z` (harness `c2d03086` alone) has a verdict derived on the Mac of FAIL, with `run_checks: 249 of 271 commands passed` and log SHA-256 `1677cd10…d59ed`.
    - Its reds: test_walk_builders generated mutants (16 shards; survivors in `cgroup_dir_of_pid`, `container_pid`, `walk_rules_scanner`, `uid_map_of_pid`, `run_time_readers`, `take_spec_builder`, `take_a_spec`, `production_builders`, `cli`).
    - Also: test_gemini_adapter generated mutants, shards 1, 2 and 16 (`native_snapshot.gemini_session_rel`, L418-419), and test_codex_adapter generated mutants (2 survivors in `CodexAdapter.native_session_rel`).
    - Also: test_vendor_record_binding (1 error, `adapter.rollout_for(1)`), and test_round4 (`test_drive_ownership.TestOwnershipMutants.test_post_unchecked` fails, plus the vendor_record_binding error).
- **Next step:**
  1. `/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py fetch gap4-merge-40acb6d-20261014T194627Z --wait`.
  2. Derive its verdict on the Mac and group every red by owner, checking each against the lane heads alone (worktrees of this clone) where needed.
  3. Write a dated checkpoint and report to glitch-06.
  4. Re-merge only on glitch-06's go.

## Re-merge after the Mac restart (14 Oct, 18:57-19:12 EDT)

Written by a fresh integration window, under glitch-06.

- **athena:** athena rebooted at about 18:55. `gap4-merge-40acb6d-20261014T194627Z` (head `40acb6de`) died with it and is recorded as lost to the reboot. Its verdict is none, and nothing from it is cited.
- **Heads taken:** box `72239cd4` (the newest committed box head at 18:57), then `39fc4f0a` on glitch-06's word (it moved at about 19:05). Harness `1f032586`. Each lane clone had uncommitted edits, which were left alone. Only committed heads were fetched.
- **Merged head `2d6983e9`:**
  - `build_draft.py --check` ok, so the draft was not regenerated.
  - `copy_manifest.py --check` ok, 414 files.
  - `freeze.py --check` ok, 415 paths.
  - `batch.py --check`: `batch: routing.json ready`.
- **Mac, light-ok before each module:**
  - On `4e30d774`: test_claude_code_adapter 27, test_vendor_record_binding 9, test_drive_ownership 43 and test_walk_wiring 20, all OK.
  - On `2d6983e9`: test_run_take 54, test_env_allowlist 28, test_scan_record 80, test_preflight 58, test_ownership 38 and test_rules_scanner 9, all OK.
  - test_walk_builders: Ran 52, FAILED (failures=5). The same five failures are on `35bfd98b` (Ran 49, checked in a scratch worktree), so this merge did not cause them. They came in with harness `1e8d0cd3` (`de6616a3`), and no battery has read that head.
    - B7Production, 4 failures: `EXPECTED_MISSING` lists `rules_scanner`, but on the merged tree the box's scan_record no longer holds it pending, so `production_builders` builds `rules_scanner.real_rules_scanner()`. The harness test has no on-tree switch for it, as it does for `WALK_LOGIN_ON_TREE`.
    - B10Resources, 1 failure: the fixture sets `image_id` to PENDING on the real schema-2 take-a lock without a `pending` reason. `image_lock` raises `LockError` ("schema 2 holds no PENDING value and no pending reason") before `require_ready` can raise `NotReady`, so review nit 7's assertion fails. Reproduced directly.
    - Both are harness-owned test expectations. Neither is fixed here.
- **athena name scan:** `athena_suite.name_hits` on `2d6983e9` finds five NEW token-name paths from the box lane's lease work (`b9f876b5` range): `mutants/lease_tokens_mutants.py`, plus `runs/100-…`, `101-…`, `105-…` and `106-…lease-tokens…` under `lane-reports/stub-take-20261014/`. The seven earlier ones are covered by aegis `6cb2063`. Under the T52 method, this lane does not read them and does not pass `--allow-path`. The version hashes were sent to glitch-06 for a reviewed exemption.

## Battery on the merged head (14 Oct, 19:35-20:13 EDT)

- **Exemptions:** aegis `136190c` lists the five lease-token files; `name_hits` on `66bacade` then had no unexempted path.
- **Harness alone, `gap4-harness-alone-1f03258-1f03258-20261014T225556Z`** (fetched, verdict on the Mac):
  - FAIL; step 1 `Ran 1303`, OK (skipped=82); `run_checks: 265 of 271 commands passed`; log sha256 `fa1e3dfc…b24b60b`.
  - Reds: test_round4 (its two skips, `test_build_draft.py:559` and `test_routing.py:2891`, "take-a lock PENDING on this branch", are not in `SKIP_ALLOWED`, an artifact of a harness-alone tree); test_codex_adapter generated mutants (2 survivors, `CodexAdapter.native_session_rel`); test_walk_builders `--witnesses` (the `scanner-class-by-name` anchor occurs 0 times since `0f1aa5ea` removed `pinned is None or`); test_gemini_adapter generated mutants shards 1, 2 and 16 (`gemini_session_rel`, L418-419).
- **Merged, solo, `gap4-merge-66bacad-20261014T233549Z`** (head `66bacade`):
  - FAIL; step 1 `Ran 1303`, OK (skipped=82); `run_checks: 254 of 272 commands passed`; log sha256 `ffa7c69c6682e6e2271786f4875a44e959100273d61fefd8e747cc87e5f31b4f`; account processes 0 at start and end.
  - **Cross-lane, new (5 lines):** test_vendor_take_records, test_vendor_checker_road, test_codex_identity and test_pending_codex_walk. A driven Codex stub take now meets box `34b1a3d2`'s postflight, which refuses with "auth.json: absent; the lease home must hold exactly one registered credential file", so no driver ledger is written and walks go `held`. All four passed at harness `1f032586` alone. The fifth line is test_round4, whose 15 failures and 4 errors are exactly these plus test_walk_builders' 5.
  - **Box-owned (6 lines):** test_env_allowlist generated mutants, shards 1, 3, 4, 5, 7 and 8: 12 unlisted survivors in `run_take.launcher_argv`, added by the no-login launcher variant `41428177` and folded in `41fccf4c`.
  - **Harness-owned, known (3 lines):** test_walk_builders (the 5 reds above, routed by glitch-06); `--witnesses` (the stale `scanner-class-by-name` anchor); generated shard 14/16, "LISTED BUT KILLED: walk_builders.remove_run_tree:delete:L6:C4:e3e767f5", which passes at `1f032586` alone, so the merged tree kills a mutant listed as equivalent.
  - **Harness-owned, open since `c2d03086` (4 lines):** test_codex_adapter generated mutants (`native_session_rel`, 2 survivors), and test_gemini_adapter generated mutants shards 1, 2 and 16 (`gemini_session_rel`).
- `gap4-merge-40acb6d-20261014T194627Z` was lost to the athena reboot; it has no verdict.

## Re-merge onto box 14670435 and harness 27ade10a (14 Oct, 21:40-21:52 EDT, coordinator glitch-5a)

- `f1f9b6eb`: box `14670435` (`06775d56..14670435`, the Codex exec branch behind the closed gate and its folds, reviewed). No conflict hunk.
- `5e722095`: harness `27ade10a` (`86c60dba..27ade10a`, reviewed PASS). The harness branch tip had moved to `be4bbdca`, but `27ade10a` is the head glitch-5a named. Three conflict hunks, resolved as the harness lane rehearsed and glitch-5a ruled:
  - `walk_builders.py` `login_name`: the ruling's `NO_LOGIN` for a Codex row (harness), not box's `CODEX_SUBSCRIPTION_NOT_READY` refusal.
  - `walk_builders.py`, after `login_secrets`: both kept, box `lease_secrets` and then harness `CodexLeaseRoad`, which calls it.
  - `tests/test_walk_builders.py`, the B2.login Codex case: the harness expectation ("its login is the lease"), which follows from `NO_LOGIN`.
  - Check: the merged `walk_builders.py` differs from `27ade10a` only by box `lease_secrets`. The box side's other change since the base (`rules_scanner`) was already resolved in `de6616a3`.
- On `5e722095`:
  - `build_draft --check` ok; `copy_manifest --check` ok, 414 files; `freeze --check` ok, 415 paths; `batch --check` ready.
  - T52: 12 secret-shaped paths, all exempt at aegis `136190c`, none new.
- Mac (light-ok before each), all OK: test_walk_builders 56, test_vendor_take_records 4, test_vendor_checker_road 5, test_codex_identity 5, test_pending_codex_walk 10, test_codex_adapter 48, test_gemini_adapter 143, test_claude_code_adapter 27, test_env_allowlist 29, test_run_take 58, test_preflight 59, test_scan_record 80, test_build_draft 48, test_routing 282.
- Harness integration contract, proved with the real box symbols against the harness's B13 boundary fakes. A scratch probe drove the fakes' contract with their synthetic lease values; 14 checks, all PASS:
  - The gate: `CODEX_SUBSCRIPTION_READY` is `False`. `run_take.NO_LOGIN == walk_builders.NO_LOGIN == "-"`, and `LOGIN_VARIABLE[CODEX]` is `NO_LOGIN`. `login_name(CODEX)` is `NO_LOGIN`. `preflight.LEASE_CREDENTIAL[CODEX]` is `auth.json`.
  - The real `place_lease`: it refuses `NotReady` while the gate is closed. With the gate open it returns `<cfg>/auth.json` as a regular file, mode 600, with the same bytes, and it never writes over an existing lease (`LoginRefused`).
  - The real `lease_secrets`: it reads access and refresh at take start, keeps them and adds a refreshed value, and refuses a missing file (`LoginError`).
  - `CodexLeaseRoad` works over the real pair, and `codex_gate_problem` reads the real closed gate.
- Known and not fought, on glitch-5a's word: the harness passes `login_file` `"-"` where the box exec needs the placed lease path. It fails closed, and the harness fold is queued.
- Battery: `gap4-merge-5e72209-20261015T015202Z`, solo.
- **Result:** FAIL; step 1 `Ran 1303`, OK (skipped=82); `run_checks: 256 of 272 commands passed`; log sha256 `2c0633a9b9de4de98fcfe2cea288302988cd596d523f4e9c80ceccda82a07b18`; account processes 0 at start and end. Every earlier Codex-road, env_allowlist, adapter-mutant and witness red is green. The 16 reds:
  - **test_walk_builders generated mutants, 15 of 16 shards (shard 6 passes); harness's sweep:**
    - 12 unlisted survivors in `walk_builders.lease_secrets` (box `b9f876b5`'s function, now in the harness module). The sweep's B13 swaps it for `fake_lease_secrets` at the boundary, so no test drives the real one.
    - 3 in `production_builders` L34-35, the `rules_scanner` pending branch. On the merged tree `scan_record.pending()` has no `rules_scanner`, so the Missing branch never runs.
    - 1 in `prepare` L16 (`builders.get("lease_path")`, drop-0), past the closed Codex gate.
  - **test_round4, failures=2; box's test_live_box:** `SubscriptionTransitionRegression.test_walk_login_and_scanner_refuse_before_open` still expects "subscription binding not ready" from `walk_builders.login_secrets`, and per the test's source also from `login_file_by_name`. Under the ruled `NO_LOGIN`, the harness refuses with "a Codex row has no login file (…): its login is the lease". The log shows the `login_secrets` subtest; the second failure is cut by the log's tail, so it is inferred from the source. No Mac rerun: light-ok held at load1 165.

## RESUME HERE (handover, 14 Oct 22:3x EDT)

- **Merge clone:** `/Users/javrodher/aegis-builds/gap4-live-merge-20261014`, branch `gap4/live-merge-20261014`. The merged code head is `5e722095` (box `14670435` + harness `27ade10a`); log commits follow it. Nothing was pushed.
- **Battery:** `gap4-merge-5e72209-20261015T015202Z` (solo, head `5e722095`) was fetched; its verdict, derived on the Mac, is FAIL with 256 of 272 commands passing; log sha256 `2c0633a9…2a07b18`.
- **Reds by owner (16):**
  - **Harness, 15 lines:** test_walk_builders generated mutants, shards 1-5 and 7-16. There are 16 unlisted survivors: 12 in `lease_secrets` (the real function is never driven because B13 fakes it), 3 in `production_builders`' `rules_scanner` pending branch (dead on the merged tree), and 1 in `prepare` L16 (`lease_path`, behind the closed gate).
  - **Box, 1 line:** test_round4, from test_live_box `SubscriptionTransitionRegression.test_walk_login_and_scanner_refuse_before_open`. It expects "subscription binding not ready" where the ruled `NO_LOGIN` now refuses with "its login is the lease"; 2 subtests.
- **Known, not a red here:** the harness passes `login_file` `"-"` where the box exec needs the placed lease path. It fails closed, and the harness fold is queued.
- **Next:** the two owner fixes, then a re-merge of the newer heads (the harness tip was already `be4bbdca`) and a solo battery, with light-ok exiting 0 first (the Mac was at load1 165 at handover).

## Interim re-merge onto harness 83b83ea1 and box 3f3beb21 (14 Oct, 22:57-23:47 EDT, coordinator glitch-6b)

- `13031aca`: harness `83b83ea1` (`27ade10a..83b83ea1`: `0095f47a` Gemini walk wiring, `be4bbdca` subcommand words, review folds `77418a8e`, `0ba98258`, `2c8b0d26`, and the RESUME commit). No conflict hunk.
  - The three rulings hold on the merged tree: `login_name` gives `NO_LOGIN` for a Codex row; box `lease_secrets` sits beside harness `CodexLeaseRoad`; the Codex exec's `login_file` is the take's placed `cfg/auth.json` through `CodexLeaseRoad.login_file_for` and `drive.login_file_of` (`77418a8e`).
  - The merged `walk_builders.py` differs from `83b83ea1` only by box `lease_secrets` (18 added lines).
  - Boundary symbol present on the tree: `run_take.CODEX_HELP_COMMANDS` (box `14670435`), which `codex_adapter` binds to.
- `5110eae5`: box `3f3beb21` (`22f80269`, test_live_box follows the ruled `NO_LOGIN`; `3f3beb21`, its report), merged on glitch-6b's word. No conflict hunk.
- Checks, on `13031aca` and again on `5110eae5`: `build_draft --check` ok; `copy_manifest --check` ok, 414 files; `freeze --check` ok, 415 paths; `batch --check` ready. T52 `name_hits` with the committed allowlist (aegis HEAD, list sha256 `b878a17a…7b9202`): 12 secret-shaped paths, 12 exempt, 0 new.
- Mac, on `5110eae5`, light-ok exiting 0 before each module (glitch-6b's gate, aegis `19c4e39`): test_walk_builders 60, test_codex_adapter 54, test_gemini_adapter 143, test_run_take 58, all OK.
- athena:
  - `gap4-merge-interim-13031ac-13031ac-20261015T030108Z`: refused, busy `other-suite`.
  - `gap4-merge-interim-13031ac-13031ac-20261015T030250Z`: launched with the default `--kind gars`, so it ran **step 1 only** (the 1303 GARS unit tests), not the Gap Study battery. Step 1 PASS: ran 1303, failures 0, errors 0, skipped 82; log sha256 `423c63680bd65637e18af7398518b2e53c8cbd100bf09ea4dcca7995e7c1259d`. It is not a battery verdict and is not cited as one.
  - `gap4-merge-interim-5110eae-5110eae-20261015T031358Z` (`--kind gars-gap4 --jobs 12`, not solo): refused, busy `other-suite`.
  - `gap4-merge-interim-5110eae-5110eae-20261015T034151Z` (`--kind gars-gap4 --jobs 12`, not solo): launched automatically by this lane's wait loop 7 seconds after the harness run `gap4-harness-r123-merged-151b0e9-20261015T031158Z` ended (state failed, reason cancelled, 03:41:44Z). **Cancelled by glitch-6b; no verdict.** Fetched record: rc 143, log sha256 `dbcf4f04aac22e47bb04b50ea7158a611489e0ab97dec712cc6b3b36c270cddb`.
- The busy rule (read in `ops/athena_suite_remote.py`): `run_is_solo(solo, suite_user)` returns true for every run as the suite account, and the Mac's `cmd_run` always passes `SUITE_USER`. So every run is solo on athena, without `--solo`, and `acquire_slots` raises `Busy("other-suite")` while any other suite-shaped process runs. Two suite batteries cannot share athena; "at most 2 runs share it" cannot happen through this tool.
- No red is classified in this window: no Gap Study battery finished on a merged head.

## RESUME HERE (handover 14 Oct 23:47 EDT)

- **Merge clone:** `/Users/javrodher/aegis-builds/gap4-live-merge-20261014`, branch `gap4/live-merge-20261014`. The merged code head is `5110eae5` (box `3f3beb21` + harness `83b83ea1`, via `13031aca`); log commits follow it. Nothing was pushed.
- **Checks on `5110eae5`:** all four ok; T52 12/12 exempt, none new.
- **Battery:** none with a verdict on this head. The last Gap Study verdict on a merged head is still `gap4-merge-5e72209-20261015T015202Z` (FAIL, 256 of 272).
- **Expected at the final:** the box red (test_live_box `NO_LOGIN`) should be gone with `22f80269`; the harness's 16 test_walk_builders mutant survivors depend on the harness head glitch-6b sends.
- **Next:** on glitch-6b's go, merge the harness's new head (and any newer box head), rerun the four checks and T52, then one `--kind gars-gap4` battery on athena, which runs alone there by construction, then fetch, the verdict on the Mac, and every red by owner.

## Final re-merge onto harness d78c8791 (15 Oct, 00:2x-00:31 EDT, coordinator glitch-6b)

- `383e5c2f`: harness `d78c8791` (`83b83ea1..d78c8791`: test-only `1b0fce97` R1 and R2, `fdf3297b` NIT 1, `9442333a` the postflight stand-in, and two RESUME commits) onto `5110eae5`. Box stays at `3f3beb21`. No conflict hunk.
- Tree proof: `git diff ad9ee13f 383e5c2f -- evals/` is empty (0 lines). `ad9ee13f` is the harness lane's merged candidate (fetched from `/Users/javrodher/aegis-builds/gap4-harness-scratch-merge-20261014b`), whose battery glitch-6b reports as PASS 272 of 272. The whole-tree difference is only `lane-reports/` (this file and the harness resume file).
- Checks on `383e5c2f`: `build_draft --check` ok; `copy_manifest --check` ok, 414 files; `freeze --check` ok, 415 paths; `batch --check` ready. T52: 12 secret-shaped paths, 12 exempt, 0 new.
- No `gfb-` gap-filler was listed on athena at launch, so nothing was cancelled.
- Final battery launched 00:30:59 EDT: `gap4-merge-final-383e5c2-383e5c2-20261015T043059Z`, `--kind gars-gap4 --jobs 24 --solo`, head `383e5c2f`.

## RESUME HERE (15 Oct, after the final launch)

- **Merge clone:** branch `gap4/live-merge-20261014`. Merged code head `383e5c2f` (box `3f3beb21` + harness `d78c8791`); log commits follow it. Nothing pushed.
- **Running:** `gap4-merge-final-383e5c2-383e5c2-20261015T043059Z` (solo, the citable final). Do not cancel it.
- **Next:** `athena_suite.py fetch gap4-merge-final-383e5c2-383e5c2-20261015T043059Z --wait`, derive the verdict on the Mac, list every red by owner, record it here, report to glitch-6b.

## Final battery on 383e5c2f (15 Oct, read 01:10 EDT)

- `gap4-merge-final-383e5c2-383e5c2-20261015T043059Z`, `--kind gars-gap4 --jobs 24 --solo`, slots 1-4, solo 1, commit `383e5c2f987ae13a95f43cefc1ea692bd110709a`.
- Verdict, derived on the Mac: **PASS** ("every check holds"). Step 1 `Ran 1303`, OK (skipped=82), exit 0. `run_checks: 272 of 272 commands passed`. Account processes 0 at start and at end.
- Log sha256 `63114034aafd8a3a9f1b4d187858e33733e3e61ba9da128727c6dc100734c095` (the Mac's hash of the fetched log equals the summary's).
- Reds: none. The 16 reds on `5e722095` are gone: the box test_live_box `NO_LOGIN` red (box `22f80269`) and the 16 test_walk_builders mutant survivors (harness `1b0fce97`, R1 and R2).

## RESUME HERE (15 Oct, after the final battery)

- **Merge clone:** branch `gap4/live-merge-20261014`. Merged code head `383e5c2f` (box `3f3beb21` + harness `d78c8791`), whose battery `gap4-merge-final-383e5c2-383e5c2-20261015T043059Z` is PASS, 272 of 272, solo. Log commits follow it. Nothing pushed.
- **Next:** nothing owed by this lane until glitch-6b names a next step (a push or the hand-off of `383e5c2f` is not this lane's).

## Interim 2: harness 89525f03 and box 58013b43 onto 383e5c2f (15 Oct, 01:2x-01:30 EDT, coordinator glitch-6b)

- `f5496d2d`: harness `89525f03` (`bdb77d7a`, review NIT 1, a test-only lease-reader presence guard in `tests/test_walk_builders.py`; RESUME addendum). No conflict hunk.
- `0cd9b1be`: box `58013b43` (`98d45802` G14 stub take runs 7 and 8 and the G7 walk launch road write-up; `ba6d7f14` the Claude Code 2.1.296 static-read evidence; RESUME block). 18 files, all under `lane-reports/`. No conflict hunk.
- The lane tips had moved past the named heads (harness `2e84ca1f`, box `988f24ee`); only the named heads were merged.
- Checks on `0cd9b1be`: `build_draft --check` ok; `copy_manifest --check` ok, 414 files; `freeze --check` ok, 415 paths; `batch --check` ready. T52 with the committed allowlist (list sha256 `b878a17a…7b9202`): 12 secret-shaped paths, 12 exempt, 0 new. The new `lane-reports/stub-take-20261015/` files add no secret-shaped name.
- Battery launched 01:30:24 EDT: `gap4-merge-interim2-0cd9b1b-0cd9b1b-20261015T053025Z`, `--kind gars-gap4 --jobs 24 --solo`, head `0cd9b1be`.

## RESUME HERE (15 Oct, after the interim-2 launch)

- **Merge clone:** merged code head `0cd9b1be` (box `58013b43` + harness `89525f03`); log commits follow it. Nothing pushed.
- **Running:** `gap4-merge-interim2-0cd9b1b-0cd9b1b-20261015T053025Z`. Do not cancel it.
- **Next:** fetch it with `--wait`, derive the verdict on the Mac, classify any red by owner, record it, report to glitch-6b.

## Interim-2 battery on 0cd9b1be (15 Oct, read 02:09 EDT)

- `gap4-merge-interim2-0cd9b1b-0cd9b1b-20261015T053025Z`, `--kind gars-gap4 --jobs 24 --solo`, slots 1-4, solo 1, commit `0cd9b1beaa4a434115b9e1ddc82dec2fe575f5c9`.
- Verdict, derived on the Mac: **PASS** ("every check holds"). Step 1 `Ran 1303`, OK (skipped=82). `run_checks: 272 of 272 commands passed`. Account processes 0 at start; the account sweep at end stopped 0 processes.
- Log sha256 `b8c0a17cfb12e85d4824e18adcab6df9279528faefa5f8d9c2099ff38867d7c4` (the Mac's hash of the fetched log equals the summary's).
- Reds: none.

## RESUME HERE (15 Oct, after the interim-2 battery)

- **Merge clone:** merged code head `0cd9b1be` (box `58013b43` + harness `89525f03`), battery PASS 272 of 272, solo. Log commits follow it. Nothing pushed.
- **Next:** wait for glitch-6b's heads for the admission battery (harness G1, G2, B3 walk builders; the checker constants on the bootstrap branch; the box's gate and launch road).

## Admission merge: box edd65756, harness d6ad30c2, bootstrap 6f2a6390 onto 0cd9b1be (15 Oct, 04:14-04:4x EDT, coordinator glitch-6b)

- `be0c2be6`: box `edd65756` (machine_gate athena-side `fa0838ec`; walk_launch.py `0db7d615`, `a112030a`; the Claude refusals `116d83e8`, `7d515916`; review folds `6a8aff48`, `7dbcdad8`, `0a318f4a`, `edd65756`; the box merge of `383e5c2f`, `988f24ee`). No conflict hunk. The merged `evals/` equals `edd65756` except harness `bdb77d7a` in `tests/test_walk_builders.py`.
- `1c87b7c7`: harness `d6ad30c2` (`da73335f` G1/G2/B3, `32c6085a`, `96d1a60a`, `5bae9e01`, `6fe573d5`, `3943d61c`, `d6ad30c2`, RESUME commits). No conflict hunk. Against `d6ad30c2`, the merged walk_builders.py and its tests differ only by the box side already carried (`lease_secrets`, B7's `take_spec` clause, the accepted sidecar launch).
- `bd9d05a7`: bootstrap `6f2a6390` (fetched from `/Users/javrodher/aegis-builds/gap4-bootstrap-20261015`, branch `gap4/bootstrap-constants-20261015`). No conflict marker. The expected overlap merged hunk by hunk, both sides kept:
  - `tests/test_walk_builders.py`: the harness EXPECTED_MISSING removals (runtime, hosts, lock_path, agent_version, budgets, run_tree_exclude), `B7Production(Drafted)` with its setUp, B15, B8 and B11; and the bootstrap's `_constants_held()` and `expected_missing()` with both B7 asserts reading it. No duplicate class or function name.
  - `drive.py`: the bootstrap's `finalize_wait_s`/`poll_s` record fields, `TakeDriver.checker_constants_sha256`, `take_checker`'s digest line, and the appended `RECORD_` 2.1.296 block; the harness's lines kept.
  - `prereg-draft.json`: git's merge is byte-identical to `build_draft.py`'s output on the merged tree (written twice, `cmp` equal both times), so it is not hand-edited and no regeneration changed it.
- Checks on `bd9d05a7`: `build_draft --check` ok; `copy_manifest --check` ok, 420 files from 58 fragments (adds `bootstrap-constants`); `freeze --check` ok, 421 paths; `batch --check` ready. T52 (allowlist sha256 `b878a17a…7b9202`): 12 secret-shaped paths, 12 exempt, 0 new; the new box evidence adds no secret-shaped name.
- Mac, light-ok exiting 0 before each, `env -u CLAUDE_CODE_MESSAGING_TOKEN` throughout: test_walk_builders 76, test_checker_constants 25, test_walk_runner 83, test_machine_gate 9, test_walk_launch 15, test_run_take 60, test_drive_commit 31, all OK. The w6e byte check (round 3's driver unchanged above the round-4 banner) exits 0, run with absolute paths and `git -C` in place of the line's repo-root relative paths.
- `walk_runner.py` dry, every `GAP4_*` unset (none was set), `--walk w-0001 --task scope-read --half trap --wording w3 --arm A --model claude-opus-5-5`: exit 2, four refusals:
  - `config_parent`: GAP4_CONFIG_PARENT (walk-time env).
  - `proxy`: its configuration goes under the config parent, which is missing (follows from config_parent).
  - `machine_gate`: GAP4_SUITE_ACCOUNT does not name the athena suite account (the gate).
  - **`sidecar_for`: not env.** "sidecar.create_argv needs the take's pre-registered consequential paths (its watch list), and no registered per-task list is on the tree; variants.graded_paths names none for number-fidelity." The harness test carries it as intended Missing ("sidecar_for stays Missing (no registered watch list)"), but it is a builder refusal, so the dry run does not yet refuse only on the gate and the env.
- No battery launched (glitch-6b: wait for the go).

## RESUME HERE (15 Oct, after the admission merge)

- **Merge clone:** merged code head `bd9d05a7` (box `edd65756` + harness `d6ad30c2` + bootstrap `6f2a6390`); log commits follow it. Nothing pushed.
- **Waiting on:** the bootstrap's NIT A/NIT B commit on top of `6f2a6390` (merge it as the same branch's newer head), then glitch-6b's go for the battery (`--kind gars-gap4 --jobs 24 --solo`).
- **Open:** `sidecar_for` is the one builder walk_runner still refuses on (no registered per-task watch list).

## Admission battery on bd9d05a7 (15 Oct, launched 04:25:54, read 05:12 EDT)

- Correction to the admission block above: its heading's "04:14-04:4x" should read 04:14-04:22 (the log commit was made at 04:22).
- `gap4-merge-admit-bd9d05a-bd9d05a-20261015T082555Z`, `--kind gars-gap4 --jobs 24 --solo`, commit `bd9d05a7`.
- Verdict, derived on the Mac: **FAIL**. Step 1 `Ran 1303`, OK (skipped=82), exit 0. `run_checks: 273 of 274 commands passed`. Account processes 0 at start and at end. Log sha256 `2aca8f84e702edf7420c808f48c8bf7c9ae4b0aeccb2f341d00945c30237c783` (the Mac's hash equals the summary's).
- **The one red, bootstrap-owned, not merge-level:** `FAIL [w10-walk-runner.txt:6] python3 -B -W ignore evals/gap-study-4/tests/test_walk_runner.py --witnesses`: `setUpModule` errors with "AssertionError: the anchor occurs 0 times in the module".
  - Reproduced on the Mac with a text-only scan of every `test_walk_runner` mutant (72): only `walk-check-unwritten` (target `walk_runner`) has a missing anchor, `    write_check(folder, check_record(walk, records, table, route_fn, checked=checked))\n`.
  - Cause: bootstrap `93a98927..9229d10b` (B4) changed that call in `walk_runner.py` to pass one more argument (`checked=checked,` then a continuation line), and the witness anchor in `tests/test_walk_runner.py` was not moved.
  - The red is on the bootstrap head alone: at `6f2a6390` the anchor is absent from `walk_runner.py`, while `0cd9b1be` and harness `d6ad30c2` still carry it. The bootstrap's newer head `d4f066f4` does not move it either (its test still holds the old anchor).
  - The fix is the bootstrap lane's: re-anchor `walk-check-unwritten` to the new call. This lane did not change it.
- Per glitch-6b, the final pre-walk merge waits for word after this red.

## RESUME HERE (15 Oct, after the admission battery)

- **Merge clone:** merged code head `bd9d05a7`; log commits follow it. Nothing pushed.
- **Admission battery:** FAIL 273 of 274; the one red is the bootstrap's stale `walk-check-unwritten` witness anchor.
- **Next, on glitch-6b's word:** the final pre-walk merge (bootstrap `d4f066f4` or a newer head carrying the anchor fix; the harness's newest committed head, `664a24e7` at 05:1x), regenerate the draft through build_draft, the four checks and T52, the five Mac modules, the dry walk_runner, then `gap4-merge-prewalk-<sha7>` solo.

## Final pre-walk merge: bootstrap 253fb094, harness 664a24e7 onto bd9d05a7 (15 Oct, 05:17-05:27 EDT)

- `44d9cb4e`: bootstrap `253fb094` (`82eacb72` closure NITs A and B; `d4f066f4` the sidecar watch ruling in the draft; `253fb094` walk-check-unwritten re-anchored). No conflict hunk.
- `26dd61be`: harness `664a24e7`, the branch's newest committed head when the merge started (`git log -1` at 05:17: `664a24e7 Bind the watch-list fallback to number-fidelity in code; correct the RESUME line`). Brings `184f05b3` (S1-S3) and `664a24e7`. No conflict hunk: the harness `_sidecar_on_tree` block, `EXPECTED_MISSING.remove("sidecar_for")`, `B16Watch` and its `GENERATED_ORDER` entry sit beside the bootstrap's `expected_missing()` and its two B7 asserts; both kept; no duplicate names.
- Draft: `build_draft.py` run on `26dd61be` left `prereg-draft.json` byte-identical (cmp), so the merged draft is build_draft's output; it carries `sidecar_watch_ruling`.
- Checks on `26dd61be`: `build_draft --check` ok; `copy_manifest --check` ok, 420 files; `freeze --check` ok, 421 paths; `batch --check` ready. T52: 12 secret-shaped paths, 12 exempt, 0 new.
- Mac (light-ok before each; CLAUDE_CODE_MESSAGING_TOKEN unset): test_walk_builders 83, test_checker_constants 27, test_walk_runner 83, test_pending_walk 23, test_build_draft 48, all OK; `test_walk_runner.py --witnesses` rc 0, 72/72 red.
- `walk_runner.py` dry (no GAP4_* set; `--walk w-0001 --task scope-read --half trap --wording w3 --arm A --model claude-opus-5-5`): exit 2, refusing only on `config_parent`, `proxy` (follows it) and `machine_gate`. `sidecar_for` is no longer refused.
- Battery launched 05:27:24 EDT: `gap4-merge-prewalk-26dd61b-26dd61b-20261015T092724Z`, `--kind gars-gap4 --jobs 24 --solo`, head `26dd61be`.

## RESUME HERE (15 Oct, after the pre-walk launch)

- **Merge clone:** merged code head `26dd61be` (box `edd65756` + harness `664a24e7` + bootstrap `253fb094`); log commits follow it. Nothing pushed.
- **Running:** `gap4-merge-prewalk-26dd61b-26dd61b-20261015T092724Z`. Do not cancel it.
- **Next:** fetch with `--wait`, derive the verdict on the Mac, classify every red by owner, record it, report to glitch-6b.
