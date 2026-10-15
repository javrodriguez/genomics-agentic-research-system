# Harness lane, window 2: RESUME HERE (Mac shutdown 14 Oct)

Written Wed 14 Oct 2026 15:58 EDT (clock read first). Writer: the harness lane, window 2, under glitch-06.
Branch codex/gap4-live-harness-20261013. Nothing pushed. Nothing of this lane runs on athena; no mac_slot booking is held (only light-ok reads were used).

## Head

The commit that adds this file (see `git log -1`); its parent is 1e8d0cd3.

## Done today (each commit red-first, gitleaks gate clean, path-limited)

- 3740f8f6 CP5 arm A pin profiles; 4c2d805f ownership road wiring (+ CP5 status quote, R6 mirror).
- e3f5010b operator steps through the box, three checks.d lines converted.
- 0768f478 settings guard; 03f1851c served-model backstop; 5b03311b B-3 one-road guard.
- ce2bdef4 take resources; 37272ef5 run-time cgroup and uid map; 786be12c scanner per walk (S-2); 9425bf62 P-2 machine gate.
- Drive-wiring review fixes: fcb0fb80 (MAJOR 1, ledger host-side and faithful evidence fake), 573b5a61 (MAJOR 1, config reads through operator_list/operator_read, faithful config fake), e0acd771 (2), 6bc58390 (3), 4aa3c829 (4), c2d03086 (5), cd824501 (6), 1e8d0cd3 (scanner bound to rules_scanner.RealRulesScanner by identity; review nit 7).
- This commit: test_walk_builders puts B10Resources, B11Derived and B12Scanner in GENERATED_ORDER (they were never run by the generated sweep, so every mutant of the functions they bind survived), binds that with G1's order test, turns a raising check into an assertion line (problems_by_assertion), and adds two bad-take-id refusals to B11. The module runs 50 tests OK.

## Not done: the generated-mutant item (glitch-06's queue)

- Local partial sweep after this commit's fix, over container_pid, uid_map_of_pid, cgroup_dir_of_pid and run_time_readers only: 76 of 83 run, 59 killed, 17 survived (list: scratch file gen3_survivors.txt; rerun to regenerate).
- Not yet swept: walk_rules_scanner, take_spec_builder, take_a_spec, production_builders, cli, pinned_scanner_class (163 mutants), on both the pending-lock and the ready-lock branch (the integration lane's 6e965d12 shows the ready pattern).

## Exact next step

1. `python3 evals/gap-study-4/tests/test_walk_builders.py --generated-mutants --only <ids of the ten functions> --timeout 300` (ids from `generate()`), after mac_slot light-ok; bind each survivor with a real test or list it in EQUIVALENT with its reason only where honestly equivalent.
2. Add the ready-lock branch to B10 (take_a_spec builds the builder when take-a's lock is ready).
3. Then the athena sweep (`athena_suite.py list` first), and report.

## Open items for glitch-06 (named departures)

- A failed grant or refused baseline is BLOCKED before launch (cd824501), not a rehearsal.
- A post-k or later pre-k settings problem stops the take for a ruling (no registered harness-error row reads it).
- SIDE_MODELS is the one observed haiku key; FIRST_WALK_ACCEPTANCE records the subagent-stream check.
- The merged head needs box >= 22b15f56 (settings guard model=) and box operator_list for the vendor arms; until then their launches refuse (fail closed).

## Window 2, after the restart: the generated-mutant item done locally (14 Oct 2026, 18:46 EDT)

Local Mac sweep, python3.13, one function at a time under a heavy mac_slot (acquired and released each time), light-ok before every test batch. athena offline: no athena sweep run.

- Sweep 1 (17:02-17:57, on 8b3adf14's tree): 265 run, 237 killed, 28 survived. Per function, killed/survived: take_a_spec 10/1, take_spec_builder 11/1, walk_login_path 19/0, pinned_scanner_class 5/3, walk_rules_scanner 32/1, production_builders 46/2, cli 51/0, container_pid 22/1, uid_map_of_pid 13/1, cgroup_dir_of_pid 19/12, run_time_readers 9/6.
- Correction: the message of 0f1aa5ea says "255 run, 225 killed, 30 survived"; the logs give 265, 237 and 28 (a tally slip, kept in history, corrected here).
- 0f1aa5ea binds every survivor (four by removing redundant code, the rest by real tests); nothing is listed in EQUIVALENT.
- Sweep 2 (18:16-18:45, on 802e720f's tree), every changed function again: take_a_spec 10/0, take_spec_builder 11/0, pinned_scanner_class 8/0, walk_rules_scanner 30/0, production_builders 47/0, container_pid 23/0, uid_map_of_pid 14/0, cgroup_dir_of_pid 31/0, run_time_readers 15/0: 189 run, 189 killed. cli (51/51) and walk_login_path (19/19) are unchanged since sweep 1.
- Not swept in this window: the functions swept before it (walk_identity through walk_row, missing, parse, prepare, walk_driver_for, walk_runner.main); the full 531-mutant sweep is the athena run, deferred.

Owed to athena when it is back: the full generated sweep of test_walk_builders (`athena_suite.py list` first), and the full suite on this head.

## Window 2, evening: lease road, review folds and the athena and merged-battery items (14 Oct 2026, 20:55 EDT)

Head 201f20d6. Nothing pushed. No mac_slot held. athena untouched by this lane.

Commits, in order:
- 86c60dba: the Codex lease road. login_name gives NO_LOGIN; prepare stops a Codex row while the gate is closed or absent, or its lease source is missing; CodexLeaseRoad places the lease in the driver's spec_for and hands one secrets() to both the driver and WalkRepo (NIT 4); drive's environment record sets no Codex login variable; NIT 5 runs through drive's own scan.
- 3724b84c: the review folds (MINOR 1, MINOR 2, NIT 3).
- 85ceeec1: B7 and B10 follow the tree (the integration lane's five test_walk_builders reds on 2d6983e9).
- ee27d109 and 0ae70b66: the Codex stub fixtures model the real road where the box's lease postflight is on the tree (a real lease through CodexLeaseRoad in the walk Road; a synthetic registered auth.json in drive_vendor's takes).
- 08f65e38: three witness anchors re-anchored (39/39 red); both adapters' native_session_rel bound (all five athena survivors killed).
- 201f20d6: test_round4's two forbidden skips turned into tests run both ways on every tree.

Shard 14's "LISTED BUT KILLED" remove_run_tree mutant was killed only by the B10 red that fails on that tree under every mutant; with the B10 fix it survives as listed on both trees. It stays in EQUIVALENT (glitch-06 accepted, 20:4x).

Boundary fakes the integration merge must prove against the real box symbols: run_take.CODEX_SUBSCRIPTION_READY, NO_LOGIN and place_lease; walk_builders.lease_secrets (scan_record.read_lease_tokens); preflight.LEASE_CREDENTIAL. Conflicts the merge must resolve, rehearsed in a scratch clone of 2d6983e9: in walk_builders, login_name takes the ruling's NO_LOGIN (not the merged side's CODEX_SUBSCRIPTION_NOT_READY refusal), and box's lease_secrets sits beside CodexLeaseRoad (keep both). In test_walk_builders, B2's Codex case is already carried on this branch since ee27d109.

Owed to athena: the full battery (test_round4 included) and the full generated sweeps on this head. test_round4 was last run in full locally on 1f032586 (Ran 3605, OK, 2 skips), before 201f20d6.

## RESUME HERE (handover 14 Oct 22:4x)

Written 14 Oct 2026 22:41 EDT (clock read first), at glitch-5a's handover call. Branch codex/gap4-live-harness-20261013.
HEAD: the commit that adds this block (its parent is 2c8b0d26). Nothing pushed. No mac_slot held. No process of this lane running.
Uncommitted: nothing of this lane's (lane-reports/live-harness-provenance-2026-10-13.md is modified in the tree and is not this lane's; leave it).

Done since 27ade10a (each through the gitleaks staged gate):
- 0095f47a: the Gemini walk wiring (r4-g key file by name; the same login_secrets to driver and WalkRepo; the exact-value mask proven on the real Gemini road: stream and session masked, ledger refused). Generated: walk_login_path 19/19, production_builders 47/47, prepare 57/57.
- be4bbdca: codex_adapter.argv refuses a first line that is a codex exec subcommand (resume, fork, review, help); bound to run_take.CODEX_HELP_COMMANDS where on the tree. argv mutants 44/46 killed, 2 listed equivalents; witnesses 16/16.
- 77418a8e: review MINOR 1 (the Codex adapter gets the take's placed cfg/auth.json via drive.login_file_of and CodexLeaseRoad.login_file_for) and NIT 4 (the lease gate checked before place_lease). Witnesses 41/41.
- 0ba98258: review MINOR 2 (the take-a lock fake builds locks image_lock accepts).
- 2c8b0d26: review NIT 3 (the lease postflight stand-in keeps every other problem).
- athena's prepare survivor (prepare:drop-0, the lease Missing clause) was closed in 0095f47a: the clause was redundant and is removed; prepare 57/57 killed.

Owed, in order (the light gate held at load ~159 at the handover, so nothing more ran):
1. Rerun on the Mac when light-ok passes: test_walk_builders (full; last full run 60 OK before NIT 4), test_pending_codex_walk, test_drive_loop, test_walk_wiring, test_pending_walk, test_build_draft, test_drive_ownership.
2. Rerun one inconclusive generated mutant (a timeout under load ~30): `python3 evals/gap-study-4/tests/test_walk_builders.py --generated-mutants --only walk_builders.walk_driver_for:delete:L38:C4:a20d0dfd --timeout 600`, under a heavy slot.
3. Re-prove 0095f47a's last edit (the unknown-harness case, the redundant term) and 77418a8e..2c8b0d26 on a scratch `git clone --shared` of the merge clone with the box head (1e10e320 or later) applied; the scratch proof so far covered 0095f47a's earlier draft.
4. The integration merge's list: the boundary fakes (CODEX_SUBSCRIPTION_READY, NO_LOGIN, place_lease, lease_secrets / read_lease_tokens, LEASE_CREDENTIAL, CODEX_HELP_COMMANDS); walk_builders' two conflicts (login_name takes NO_LOGIN; keep box's lease_secrets beside CodexLeaseRoad); the Codex exec reads login_file = the take's placed cfg/auth.json (77418a8e).
5. athena: the full battery and generated sweeps on this head.
