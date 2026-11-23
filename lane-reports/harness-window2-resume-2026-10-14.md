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

## RESUME HERE (window 3, 14 Oct 23:5x EDT; supersedes the block above)

Written 14 Oct 2026 23:53 EDT (clock read first), restarted by glitch-6b. HEAD: the commit that adds this block (parent 9442333a). Nothing pushed. No Mac process of this lane is running.

Commits (each red first, then green, through the gitleaks staged gate):
- 1b0fce97: R1 and R2. The real lease_secrets is held to the lease contract, both ways on every tree. The pending rules-scanner branch is driven through the pending() seam. test_walk_builders: 62 OK here, 62 OK on the merged scratch.
- fdf3297b: review NIT 1. The Codex subcommand binding is proven to read run_take's list on every tree. test_codex_adapter: 54 OK here and on the merged scratch.
- 9442333a: the lease postflight stand-in test is checked against the lease-less postflight. It was red on the merged tree. test_pending_codex_walk: 11 OK on both trees.

Merged scratch: /Users/javrodher/aegis-builds/gap4-harness-scratch-merge-20261014b at ad9ee13f, which is the integration lane's 5110eae5 (13031aca plus box 3f3beb21) with these three test diffs. It differs from this branch's three test files only by the integration lane's 8-line resolution in test_walk_builders.
Correction: scratch 151b0e91 copied this branch's test_walk_builders over the merged one and lost that resolution (3 B9 and B12 reds came from that copy, not from the code). Its athena run was cancelled. 8b83a3bb restored the resolution.

athena:
- gap4-harness-alone-83b83ea-83b83ea-20261015T025335Z (kind gars): PASS, GARS step 1 only, Ran 1303. It is not the battery.
- gap4-harness-alone-27ade10-…005635Z (gars-gap4): FAIL 270/271. Its one red was prepare:drop-0, already closed in 0095f47a.
- gap4-harness-r123-merged-ad9ee13-20261015T034740Z (gars-gap4, jobs 12): launched 23:47. It is the R1-R3 proof and the item 3 re-proof. Fetch it with `athena_suite.py fetch <id> --wait`.

Mac, item 1 (light-ok gate), this branch: test_build_draft 47 OK, test_drive_loop 27 OK, test_walk_wiring 20 OK, test_drive_ownership 43 OK. Merged scratch: test_build_draft 48 OK, with TakeALock 2 OK (review NIT 2).

Next: read every red line of ad9ee13's run. R3 means the prepare L16 mutants are killed there; also check walk_driver_for:delete:L38. Fix any red that is this lane's. Then send the final report to glitch-6b. Next gars-gap4 launches use --jobs 24.

### Addendum, 15 Oct 00:3x EDT: the merged battery

gap4-harness-r123-merged-ad9ee13-20261015T034740Z (gars-gap4, jobs 12, head ad9ee13f): **PASS**. Step 1 ran 1303, OK (82 skipped). `run_checks: 272 of 272 commands passed`. Log sha256 c9ca543e5a1ac83beb9f202f8f59f6b50011cd4e9d6699155fcc4715098b058b.
test_walk_builders: the module, the witnesses and all 16 generated shards (634 mutants) exit 0. run_generated exits 0 only when no mutant survives unlisted, none listed is killed and none is inconclusive. So the 12 lease_secrets mutants (R1), the 6 production_builders L34-35 mutants (R2), the 5 prepare L16 mutants (R3) and walk_driver_for:delete:L38 (item 2) are all settled on the merged tree. A PASS shard does not log per-mutant lines, so this is read from the exit rule.
test_round4 (box test_live_box at 3f3beb21), test_pending_codex_walk and test_codex_adapter (its generated sweep included) all pass there.
Note: the block above says 23:53 and the clock read 23:52 (a one-minute slip, kept).
Next: this lane's queue is empty, pending glitch-6b's merge of 9442333a..HEAD.

### Addendum, 15 Oct 00:41 EDT: review NIT 1 folded

The review of 83b83ea1..d78c8791 passed (0 MAJOR, 0 MINOR). Its NIT 1 is folded in bdb77d7a: wherever the box's lease road is on the tree, the real lease reader must be there too.
- Red: on the merged scratch with both readers hidden, the old test passes and the new one fails.
- Green: test_walk_builders runs 62 OK on the merged scratch and 62 OK on this branch.
bdb77d7a goes into the next battery, before production admission; it is not in the battery running now. Queue empty.

## RESUME HERE (15 Oct 01:24 EDT): G1, G2 and B3 for the first Claude walk

HEAD: the commit that adds this block (parent da73335f).
- da73335f builds runtime, hosts, lock_path, config_parent (GAP4_CONFIG_PARENT), the proxy (ProxyRoad), agent_version, budgets and run_tree_exclude. Red: 16 run, 15 failures. Green: test_walk_builders 73 OK on both trees.
- sidecar_for stays Missing: there is no registered per-task watch list. It needs a ruling.
- Merged scratch: /Users/javrodher/aegis-builds/gap4-harness-scratch-383e5c2f (383e5c2f, with bdb77d7a and da73335f applied as patches, uncommitted; its walk_builders lacks only da73335f's docstring edit).
- Running: the single-function generated mutants of the eight new or changed functions (223 ids) on that scratch. Log: the session's scratchpad batch6.log. walk_driver_for and production_builders go to the next athena battery.
Next: read the mutant result and bind any survivor. Then report to glitch-6b.

### Addendum, 15 Oct 03:13 EDT

Commits since 2e84ca1f:
- 32c6085a: evidence folder 0755.
- 96d1a60a: COPIED.d machine-gate reason text.
- 5bae9e01: the 8 reds of battery gap4-harness-g123-merged-109b4ee-20261015T061404Z (FAIL 264/272, all harness), and B3 reads the bootstrap's [{"path": p}] shape.

Mac (light-ok): test_walk_builders 73 OK on both trees; --witnesses 41/41 on both trees; test_drive_ownership 44 OK; test_stub_take 19 OK on the merged scratch.
Single-function mutants on the Mac: config_parent_from_env 33/33, take_lock_paths 25/25, for_row 1/1, proxy_road 22/22 killed. agent_versions was 51/55 there; its 4 survivors are now killed.
Stopped on glitch-6b's word: the athena battery's sweep covers every function.

Next: launch the next battery on scratch f05ad45f (/Users/javrodher/aegis-builds/gap4-harness-scratch-0cd9b1be; gars-gap4, jobs 24, --solo) once athena is free after the bootstrap battery (glitch-6b's word). Then report.
sidecar_for stays Missing and needs a ruling: there is no registered watch list.

### Addendum, 15 Oct 04:26 EDT

Battery gap4-harness-g123b-merged-56a1780-20261015T074328Z (head 56a17802 = 0cd9b1be + 89525f03..6fe573d5): **PASS**, 272/272, step 1 1303 OK. Log sha256 c41636a9e3df126bd4d64bd1d5dbde0986896db4c56ad0d075d609c048b81dda. All 18 w12b lines pass (module, witnesses, 16 generated shards).

Since then (Mac proof only, light-ok, not yet in a battery):
- 3943d61c: design_for's pending list test (the bootstrap battery's survivor; red on a b1f4df1c scratch).
- d6ad30c2: the review fold (MINOR 1-3, NIT 1-2, the evidence-folder comment). test_walk_builders 76 OK on both trees; witnesses 41/41.

Owed: a battery on scratch 355d615c (0cd9b1be + 89525f03..d6ad30c2), or the admission merge's own battery. sidecar_for stays Missing pending a ruling on the watch list.

### Addendum, 15 Oct 04:41 EDT: S1-S3, the sidecar watch list

184f05b3 builds watch_list and sidecar_road under Addendum 2 of the bootstrap ruling (rule W1).
- Red on a merged scratch of bd9d05a7: 12 run, 11 failures, 3 errors.
- Green: 83 OK on both trees; witnesses 41/41; test_stub_take 19 OK.
- Merged scratch: /Users/javrodher/aegis-builds/gap4-harness-scratch-bd9d05a7 (committed there as a scratch commit).

S4's draft text went to glitch-6b, since build_draft is not this lane's file. On the merged tree every production builder is now built except config_parent and proxy (until GAP4_CONFIG_PARENT is set) and machine_gate.
Correction (15 Oct 04:55, review NIT 1): with GAP4_CONFIG_PARENT unset, production also lacks lease_path (the Codex lease) and agent_version for codex and gemini (per-harness Missing inside the PerHarness); neither matters for a Claude walk.
- 184f05b3's review MINOR 2 is folded in the next commit: WATCH_FALLBACK_TASKS binds the fallback in code.
Owed: a battery that includes 184f05b3.

## RESUME HERE (15 Oct 14:38 EDT; supersedes the blocks above): w006 ruling A and B, items D, E and F

Writer: the harness lane, for glitch-6b (Lane-orchestrator). Nothing pushed. No athena access was used.
Commits since 664a24e7, each red-first and through the gitleaks staged gate (0 findings):
- d7ec1db0 merge of the bootstrap head 253fb094 (check_take CHECKER_CONSTANTS and test_checker_constants were not on 664a24e7).
- 1b51f5ce A: the scheduled-wakeup kind (transcript_view.is_scheduled_wakeup and ScheduledWakeups, shared by check_take.user_text_records; meta_kinds in CHECKER_CONSTANTS; the departure in build_draft; BOOTSTRAP_SPANS updated). Constants digest 8fd8c39b2baf... to d836285fdfda4bad8f7baaca8aac94e79ddfacc6e9f63f32ac9468cf3b81c842.
- d9c54f50 B: walk_regrade recheck-<n>.json from committed records (append-only, tamper refuses, machine named); pending_walk.checker_standing reads a verified recheck.
- 2adfebad merge of the ship head ce818d85 (box modules for D); no conflict hunk.
- 4545622e D: drive.py calls box operator_read and operator_list with the O-3 signature; FakeOwnership updated; tests/test_drive_box_seams.py adopted from the box lane.
- 8a79b261 E: run.transcript_lines; both production grading callers hand the graders lines; tests/test_walk_grade_seam.py over all nine tasks.
- b7aca72a F: the review notes (arm on a non-error result once per id; --check re-derives only the latest recheck; no checker events in a recheck).

## Exact next step
1. glitch-6b merges this head into the ship head and runs the athena battery (test_build_draft, a heavy module, did not get a Mac slot here: thermal holds).
2. RULED (glitch-6b, 15 Oct): rechecks run ON ATHENA, the walks' own machine, with --home, --temp-root and --checkout named from that machine's records; glitch-6b reads any reason change before a recheck is accepted. After review, glitch-6b runs `walk_regrade.py --recheck <walk> --home H --temp-root T --checkout C` there.
3. Done as item G (be74a97f, ruled by glitch-6b): awareness_furniture reads each transcript in one pass, so a wakeup line resolves against its earlier call; red before, witness red, round 3's output byte-identical.
4. The athena gars-gap4 battery runs on b7aca72a (glitch-6b's); an independent review of D, E and F runs from a scratch copy; G sits on top.

## RESUME HERE (15 Oct ~17:00 EDT; supersedes the blocks above for what follows 2cab338a)

Writer: the harness lane, for glitch-6b. Nothing pushed. Commits since 2cab338a, each red-first through the gitleaks staged gate:
- 38d45af9 E (review MAJOR): run.transcript_lines hands a transcript_view.BoundTranscript (lines that carry their path, each a BoundLine naming it); vendor_record_binding binds it by path or by a grader's whole ordered copy.
- 7d7d0264 D (review MINOR): RootedFake binds each drive-to-box read to its root.
- b6da219d review NITs: wakeups arm only on a genuine result record; G's test names what binds it.
- 28c353d4 the b7aca72a battery reds this lane caused (walk_plan/test_round4, walk_runner generated survivors, w6j line 10).
- 2c3784e6, a5bb4c3e H: the auto_mode attachment read as harness furniture for audit; RULED (glitch-6b, 15 Oct): disabled for all claude-code takes via CLAUDE_CODE_THRIFTY_SONIC (box lane: allowlist value, parser proof, harness-condition-violated refusal).
- 4e0d64ac recheck coverage: register schema 2 `rechecks`, coverage from the latest register entry with no git (ruled by glitch-6b).

## Standing facts for whoever resumes
- VENDOR BOOKKEEPING IS NOT PRODUCTION: harness_bookkeeping.TABLE holds claude-code only, so production Evidence.load refuses every Codex and Gemini take before any grader. This is the known "native-session readers pending" gate; production vendor admission stays closed until they are registered. The codex and gemini bookkeeping entries in tests/test_walk_grade_seam.py are TEST DATA only.
- Rechecks run ON ATHENA with --home, --temp-root and --checkout from that machine's records; glitch-6b reads any reason change before a recheck is accepted.
- Open (not built): commit_regrade's regrade.json commit is a second commit touching a walk folder, which walk_register's history check does not admit (it admits walk and recheck commits only). No regrade has been committed yet.

## Exact next step
glitch-6b launches the athena battery on this head plus the box lane's env commit.

## RESUME HERE (15 Oct 20:02 EDT; supersedes the blocks above)

Writer: the harness lane, restarted by glitch-6b after the Mac restart. Nothing pushed. No athena access. No mac_slot booking held; no process of this lane running.
HEAD: the commit that adds this block (parent fee76182).

Commits since 1491e946, each red first and through the gitleaks staged gate (0 findings):
- 7979489a the four athena battery reds on 1491e946 (277/281):
  - test_pipeline: the pinned rehearsal COMMANDS carry walk_regrade.py --check (1491e946 added it to freeze_rehearsal.WALK_COMMANDS).
  - test_rehearsals --witnesses: duplicate-keys-admitted and schema-by-value re-anchored on 4e0d64ac's lines; 20/20 red.
  - test_cp8_prep --witnesses: three anchors re-anchored; walk-commits-uncounted then survived, so H1 now drives a later ordinary commit and its revert; 15/15 red.
  - test_round4's P14Cli: test_recheck_coverage cached walk_plan, test_walk_layout's tearDown dropped walk_register, so P14's patch missed; test_walk_plan now loads walk_plan afresh and asserts the binding.
- d55b712b the steer-off condition (box patch b0c6f86c, reviewed): check_take.steer_condition_problems; harness-condition-violated in routing.json's operator_reasons with operator_reasons_round4 (its ruling), bound by routing.check_table and TestRound4Additions; TestRound3Sources still re-derives round 3's 24; the draft names "false", the parser proof and the departure.
- fee76182 the isolation denials (box patches fd9b2209 and 816e4769, reviewed): the adapter denies RemoteTrigger, SendMessage and ListAgents (spelled in the adapter, bound to run_take's where present); check_take.denied_tool_problems; the draft carries the box report's departures (1)-(4) and walk_scope.

Departures from the box patches (named in the commits): the check_take definitions are appended, not mid-file (R5's round-3 prefix), with check4's added lines a new ruled span check4-study-conditions; the adapter spells the three names (this tree's run_take predates db7c0d14).

RULED (glitch-6b, 15 Oct): the 25 pre-ruling walks are NOT rechecked under the steer or isolation guards. They are rehearsal records of the earlier conditions and never cover CP6 (all 25 refuse on replay, as expected). Every line reruns under the new ship head.

Mac proof (all green unless named): test_round4 full, 4027 run, 2 failures, both test_run_take, because this Claude Code session exports CLAUDE_CODE_MESSAGING_TOKEN and run_take rightly refuses it; test_run_take with it unset is 60 OK. Then the touched modules and neighbours after the three commits: test_walk_runner 84 OK and witnesses 72/72; box_integration 61, walk_builders 83, drive_loop 27, walk_wiring 20, stub_take 19, wave4_bindings 13, live_box 38, routing 287, claude_code_adapter 28, env_allowlist 29, steer 6, isolation 6, auto_mode 6, cp8_prep 4, rehearsals 9; copy_manifest, build_draft, routing and batch checks ok. The generated-mutant shards were not run on the Mac.

## Exact next step
glitch-6b merges this head with box db7c0d14 into the ship candidate and runs the athena battery (run test_round4 with CLAUDE_CODE_MESSAGING_TOKEN unset on any Claude-hosted runner).

## RESUME HERE (15 Oct, evening; supersedes the block above)

Writer: the harness lane, for glitch-6b. Nothing pushed. No athena access. HEAD: the commit that adds this block (parent dd499432). One commit, red first, through the gitleaks staged gate.

Ruled (glitch-6b, 15 Oct): departures 1 (check_take functions appended; the check4-study-conditions span) and 2 (the adapter spells the three names, bound by test) ACCEPTED. The open ruling: require the switch, fail closed, and the same for the isolation conditions.

This commit (the fail-closed fold, with the review of 1491e946..dd499432, CHANGES):
- MAJOR: every claude-code turn needs its launch journal; each journal's one inline --settings sets CLAUDE_CODE_THRIFTY_SONIC to a STRING whose stripped, lowercased value is in STEER_OFF_VALUES ("0", "false", "no", "off"), and carries the three-tool deny by --disallowedTools and permissions.deny with crossSessionInbound "refuse". A missing journal, a missing switch, a JSON boolean or any other value, two settings, and any auto_mode record (whatever the journals say) refuse [harness-condition-violated]. The prompt after -p is never read as a flag.
- NIT folded: a turn stream with no init record, and a transcript deferred_tools_delta whose addedNames includes one of the three, refuse.
- MINOR: test_walk_runner R2 drives check4_walk on a committed walk missing a launch journal (refuses), with a witness (the claude-code branch turned off, it passes unnamed).
- walk_register: a recheck commit whose register cannot be read (absent, not JSON, duplicate key) is named, fail closed (it read as empty before). Witnesses for its no_duplicate_keys read and its --full-history log (test_walk_recheck TheRechecksHistory).
- tests/test_checker_body's clean take now carries each turn's study launch journal (it had none; drive_loop D8 uses it).
- The draft: harness_furniture_ruling.fail_closed, one line.
- From the a6a01b1c preview's reds, folded here: the draft's "out of the box" (lint_language's out-of pattern, w8e and test_build_draft) now reads "as the product ships"; R2 also drives a walk missing only the switch and one with crossSessionInbound "hold", and holds another harness clear of the conditions, killing the six check4_walk survivors of shards 3, 4, 5, 6, 8 and 10 (6 run, 6 killed on the scratch merge).

On this tree alone (no box db7c0d14), test_walk_runner R1/R2/R8 and test_walk_wiring E1 refuse harness-condition-violated: this tree's run_take writes no steer or isolation settings. They pass on the scratch merge with db7c0d14 (/Users/javrodher/aegis-builds/gap4-harness-scratch-ship-20261015). The ship head must be the merge.

Running tests on the Mac: prefix every run with `env -u CLAUDE_CODE_MESSAGING_TOKEN` (a Claude Code session exports it and run_take rightly refuses it; athena's runner does not carry it), and run the witness runners under python3.12 (they expect 3.11+ unittest output).

## Exact next step
glitch-6b merges this head with box db7c0d14 into the ship candidate and runs the athena battery.

## RESUME HERE (15 Oct 22:2x EDT; supersedes the blocks above)

Writer: the harness lane, for glitch-6b. Nothing pushed. No athena access. HEAD: the commit that adds this block.
This branch IS the ship candidate (glitch-6b's ruling): 1f63acaa (the fail-closed fold, with the a6a01b1c preview's lint and survivor reds folded in), then 8e4a274a (merge of box db7c0d14, no conflict hunk, gitleaks 0), then this commit.

This commit: tests/test_scan_record.py's test_mutant_relative_path_goes_red (box-owned, named in the fragment) computes its relative path before patching isabs. Under python3.12, relpath reads isabs through abspath, so the patched isabs bent the path ("the login file cannot be found"); 3.13 passed. It is green under both now.

The a6a01b1c reds (athena 274/283):
- w8e lint and test_build_draft (and test_round4's one failure): the draft's "out of the box" matched lint_language's out-of pattern. It now reads "as the product ships" (in 1f63acaa).
- test_walk_runner generated shards 3, 4, 5, 6, 8 and 10: one survivor each, all on check4_walk's claude-code branch (L33 to L35). R2 now drives a walk missing only the switch, one with crossSessionInbound "hold", and a harness the guard admits that is held to no condition. On the scratch merge, `--only` those six ids gave 6 run, 6 killed. The full shards were NOT rerun on the Mac (about 15 minutes each on athena, about 5x on the Mac).

Mac proof on this branch (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, heavy mac_slot), all OK:
- build_draft 48, scan_record 80, auto_mode 6, steer 7, isolation 9, walk_runner 84, walk_recheck 13, checker_body 30, drive_loop 27, walk_wiring 20, run_take 64, env_allowlist 29, claude_code_adapter 28, stub_take 19, live_box 38, wave4_bindings 13, routing 287, check_take 15, rehearsals 9 (witnesses 20/20), cp8_prep 4 (witnesses 15/15);
- copy_manifest, build_draft and routing checks; the w8e lint line clean.
- test_round4 on the scratch merge of 1f63acaa's content: 4080 run, 2 reds, both fixed since (the lint wording, and the scan_record 3.12 path).

Running tests on the Mac: prefix every run with `env -u CLAUDE_CODE_MESSAGING_TOKEN`, and run under python3.12 (the witness runners expect 3.11+ unittest output).

## Exact next step
glitch-6b runs the solo athena battery on this head, including the full generated shards 3, 4, 5, 6, 8 and 10.

## RESUME HERE (15 Oct 23:3x EDT, handoff; supersedes the blocks above)

HEAD: the commit that adds this block (parent 9200d150). Branch codex/gap4-live-harness-20261013, the ship candidate. Nothing pushed. Tree clean except the provenance report (not this lane's). No background process of this lane running; no mac_slot held.

Since e471902f:
- 870148e3: finding 1 (w033-w040 did-not-reach) is not a code regression. Each turn 1 ended end_turn, exit 0, marker not held: Haiku ran stage 00's finalize itself without the "Confirm to create symlinks under" line. Pre-ruling w002, w003 and w005 did the same. R1 now asserts turn 2 is sent through the production adapter (witness red). Also lane-reports/attachment-vocabulary-20261016/: the binary's 113 attachment names with offsets. glitch-6b ACCEPTED the default: 16 admitted, 96 refused until a held walk asks for a ruling.
- 9200d150: edited_text_file (a) and (b), and the round-3 auto_mode correction.
  - (a) `ear`, the changed_files attachment, runs each query over files read whole. A later mtime plus a content change emits {type, filename, snippet}, whoever wrote the file. The only switch, CLAUDE_CODE_DISABLE_ATTACHMENTS, skips the whole attachment list, so it breaks round-3 parity; no targeted switch exists. Record: attachment-vocabulary-20261016/edited-text-file-trigger-20261015.json (offsets and excerpt sha256s).
  - (b) w041: HISTORY.md, read by the agent via Bash, then rewritten by the agent's own background `stage00_register.py finalize` within turn 1. Neither the operator script nor the sidecar changed it.
  - Round 3: the 54 graded transcripts carry no auto_mode. The one record is the walk walks/template-adherence/1 (claude-sonnet-5, 2.1.267, permission mode auto): every flag false, auto mode's own notice, not the steer. transcript_view's comment, the draft and test_auto_mode now say so. DONE.

Open for glitch-6b: ruling 1 on edited_text_file. The facts point to "admit as a named departure with a closed shape, snippet counted as furniture", since no switch keeps parity. Nothing is built for it yet.

## RESUME HERE (16 Oct 00:18 EDT; supersedes the blocks above)

Writer: the harness lane, briefed by glitch-b5. HEAD: the commit that adds this block (parent 3ee511df). Branch codex/gap4-live-harness-20261013. Nothing pushed. No athena access. No mac_slot booking held; no process of this lane running. Tree clean except the provenance report and untracked lane notes (not this lane's).

Commits since 4ce3318f, each red first and through the gitleaks staged gate (0 findings):
- bd012b34: glitch-6b's ruling 1. edited_text_file is admitted as a named departure. Its shape is closed: exactly type, filename and snippet, as strings, the filename non-empty. The snippet is the harness event's text. The draft's harness_furniture_ruling names it. tests/test_edited_text_file.py: the near misses and ten spelling variants refuse; the allow-list is the vocabulary record's 16 plus this one, and the other 96 refuse.
- 7c2010ce: r5 NITs (a)-(c). The journal prompt is read by position. Each journal is bound to its turn and harness (harness, stream turn-N.jsonl, client claude). A journal with no stream refuses. tests/test_journal_binding.py is new. The fixtures in test_steer_condition, test_isolation_denials_checker and test_checker_body carry run_take's stream.
- 3ee511df: r5 NIT (d). rechecks_append_only_problems reads its log's exit status (RA-rc).

Mac proof (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, light-ok before each), all OK: edited_text_file 6, auto_mode 6, transcript_view 20, awareness_furniture 7, pause_adherence 30, build_draft 48 (38 s), journal_binding 4, steer_condition 7, isolation_denials_checker 9, checker_body 30, checker_constants 27, walk_runner R5Bootstrap 2, drive_loop 27, walk_wiring 20, stub_take 19, identity_mode_evidence 8, walk_recheck 14 (74 s). copy_manifest, build_draft --check and the lint_language line are clean.
Not run on the Mac: test_pending_walk (it timed out at 90 s, so it is left to the battery), the full test_walk_runner, test_round4 and the generated shards.

Open for glitch-b5 (finding): check_take.context_text reads every attachment line. So with edited_text_file now admitted, a leak word in a snippet (the agent's own file content) is named by context_leaks. On a synthetic record, a snippet carrying "evaluation" gave {'evaluation'}. Nothing was changed for this.

w053 (no-visible-output nudge): static facts only, nothing built. They are in the report to glitch-b5. The 2.1.296 linux-x64 npm tarball matches the registry integrity, and its binary's sha256 is the pinned 24972e3b.... The trigger is in the query loop (reason thinking_only_retry). round 3's 64 transcripts carry 0 isMeta records. 2.1.267 and 2.1.280 carry the same code path.

## Exact next step
glitch-b5 runs the battery on this head. Then the held walks (w041, and any edited_text_file hold) re-run as new ids.

## RESUME HERE (16 Oct 00:38 EDT; supersedes the blocks above)

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 88c3e19e). Nothing pushed. No athena access. No mac_slot booking held; no process of this lane running.

Commits since b9392024, each red first and through the gitleaks staged gate (0 findings):
- 23500a87: ruling 2. context_text sweeps an admitted edited_text_file without its snippet. It changes one line in place (0-based 142), which is pinned by the new context-text span and admitted by the w6j byte check. The type and the filename stay in the sweep. No check reads repository content for leak words, so the snippet is routed to none.
- 93205aa2: the draft's new sentence tripped lint_language (out-of), and 23500a87 was committed with that red. This commit rewords it. The lint is clean.
- 88c3e19e: ruling 3. The no-visible-output nudge is admitted as a named departure (is_no_output_nudge, an exact shape) and is gated in check_take by meta_kinds. It is counted in check.json's no_output_nudges. The draft names the facts. The CHECKER_CONSTANTS digest is now b08b5496fe28..., which was d836285fdfda... before.

Mac proof (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, light-ok before each), all OK: no_output_nudge 8, edited_text_file 9, scheduled_wakeup 11, checker_constants 27, auto_mode 6, transcript_view 20, awareness_furniture 7, walk_runner R5Bootstrap 2 and R8WalkRoad 38, checker_body 30, recheck_coverage 5, walk_grade_seam 3, stub_take 19, steer_condition 7, isolation_denials_checker 9, journal_binding 4, rehearsals 9, cp8_prep 4, walk_plan 18, walk_recheck 14, drive_loop 27, walk_wiring 20, pending_walk 23 (170 s). build_draft --check, copy_manifest, lint_language and the w6j byte check are clean.
Not run on the Mac: the full test_walk_runner and its generated shards, test_round4 and test_box_integration. check_record and _run_one are generated-sweep targets and both gained lines.

Every walk checked under d836285f... now reads stale against the new constants until it is rechecked or rerun.

## Exact next step
glitch-b5 runs the battery on this head and schedules a fresh reviewer.

## RESUME HERE (16 Oct 01:02 EDT; supersedes the blocks above)

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent bf730fb7). Nothing pushed. No athena access. No mac_slot booking held; no process of this lane running.

bf730fb7 folds review r6 of e471902f..5824c344 (two MINORs and a note). Each was reproduced first with the reviewer's dup.py and mut2.py. The commit went through the gitleaks staged gate, gated on its exit status.
- MINOR 1: the leak sweep reads the raw line with only the admitted snippet's value cut. The value is located by its one unescaped key; if the key is not found exactly once, the line is swept whole.
- MINOR 2: a checked walk is never written without its nudge count; walk_runner holds such a walk. pending_walk reads a check.json under the constants in force without a count as unreadable. walk_regrade re-derives the count from the committed transcript, in --check and in a recheck.
- The note: the sidechain-clause witness now reads check_take's count, and that mutant is red.

Mac proof (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, light-ok first), all OK:
- no_output_nudge 9, edited_text_file 10, checker_constants 27, scheduled_wakeup 11, checker_body 30, recheck_coverage 5, rehearsals 9, cp8_prep 4, walk_plan 18, walk_grade_seam 3, walk_recheck 14, pending_walk 23 (170 s), build_draft 48.
- test_walk_runner, class by class, 84 tests in all: R5 2, R8 38, R1 1, R2 6, R3 4, R4 7, R12 3, R13 1, R6 1, R7 1, R10 3, R11 15, G1 1, R9 1, R5Round3 1, TestSysPath 1.
- walk_regrade --check, copy_manifest, build_draft --check and lint_language are clean.
Not run on the Mac: the generated shards, test_round4 and test_box_integration.

## Exact next step
glitch-b5: the battery and a fresh review on this head. Every walk is rechecked on the final head before the freeze.

## RESUME HERE (16 Oct 01:28 EDT; supersedes the blocks above)

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 25076228). Nothing pushed. No athena access (walks run there on 0c830443). No mac_slot booking held; no process of this lane running.

25076228 folds review r7 (three MINORs and the observation). Each was reproduced first with the reviewer's scratchpad/r7 scripts.
- R7-1: a cut is kept only when the cut line parses, with no duplicate key, to the record with exactly its snippet emptied. fix.py's other two guards are implied by this one and were equivalent mutants when written, so they are not written.
- R7-2: a recheck carries the transcript's count, and standing reads the effective reading.
- R7-3: TheNudgeRederivation runs over committed fixture walks. It kills the reviewer's three mutants and a fourth.
- R7-obs: every transcript read in check_take, transcript_view and vendor_record_binding splits on "\n" alone (R5 BOOTSTRAP_SUBSTITUTIONS, the w6j byte check).
Open for a ruling: evals/transcript.py (round 3's tx) still splits with splitlines(). A user record carrying U+2028 refuses readers-disagree (fail closed).

Mac proof (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, light-ok first), all OK:
- edited_text_file 10, no_output_nudge 9, jsonl_split 5, transcript_view 20, awareness_furniture 7, vendor_record_binding 12, vendor_provenance 6, vendor_take_records 4, scheduled_wakeup 11, auto_mode 6, steer_condition 7, isolation_denials_checker 9, journal_binding 4, checker_body 30, checker_constants 27, recheck_coverage 5, walk_plan 18, walk_grade_seam 3, rehearsals 9, cp8_prep 4, pause_adherence 30, stub_take 19, drive_loop 27, walk_wiring 20, walk_recheck 17, pending_walk 23, build_draft 48.
- test_walk_runner, class by class: 85.
- lint_language, copy_manifest, build_draft --check, walk_regrade --check and the w6j byte check are clean.
Not run on the Mac: the generated shards, test_round4 and test_box_integration.

## Exact next step
glitch-b5: r8 and the battery on this head.

## RESUME HERE (16 Oct 01:54 EDT; supersedes the blocks above)

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 42b48b60). Nothing pushed. No athena access. No mac_slot booking held; no process of this lane running.

Correction to the block above (review r8 NIT): "every transcript read in check_take, transcript_view and vendor_record_binding splits on newline alone" is right only for those three modules. These still call splitlines() and were left as they are:
- evals/transcript.py (round 3's tx, kept for round 3's reproduction);
- round2.py:104 and :165 (round 2's reproduction);
- native_reader_registration.py:414 (the vendor road's first stream line).
The fail-closed ends below make them moot for a claude-code take. mode_binding.modes_recorded is now newline only (round 4's copy).

42b48b60 is glitch-b5's ruling on review r8's finding 1, reproduced first with scratchpad/r8/u2028.py:
- the driver (claude_code_adapter) refuses a stream or session text carrying a line separator other than newline (an executed turn's refusal);
- drive's three round-3 stream readers split on newline only (w6e admits lines 473, 517 and 540);
- check_take refuses [transcript-unreadable] on a separator or a non-blank line that is not JSON. It is routed like harness-condition-violated (routing.json, test_routing).
The w6j comment names R5 as the real pin.

Mac proof (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, light-ok first), all OK:
- line_separators 5, jsonl_split 5, edited_text_file 10, no_output_nudge 9, claude_code_adapter 28, routing 288, mode_binding 8, drive_commit 31, checker_body 30, checker_constants 27, steer_condition 7, isolation_denials_checker 9, journal_binding 4, scheduled_wakeup 11, auto_mode 6, transcript_view 20, stub_take 19, live_box 38, wave4_bindings 13, pending_codex_walk 11, drive_loop 27, walk_wiring 20, rehearsals 9, cp8_prep 4, walk_plan 18, recheck_coverage 5, walk_recheck 17, pending_walk 23, build_draft 48.
- test_walk_runner, class by class: 85.
- The w6e and w6j byte checks, walk_regrade --check, mode_binding --check and --walks --check, lint_language, copy_manifest and build_draft --check are clean.
Not run on the Mac: the generated shards, test_round4 and test_box_integration.

## Exact next step
glitch-b5: r9 and the battery on this head.

## RESUME HERE (16 Oct 02:06 EDT; supersedes the blocks above): the final head

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 0e9a57c0). It is the final head for the battery at the Haiku/Opus break. Nothing pushed. No athena access. No mac_slot booking held; no process of this lane running.

0e9a57c0 is review r9's wording fold (glitch-b5's ruling, option b; no logic change).
Correction to the block above: the driver end (claude_code_adapter) refuses U+2028, U+2029 and U+0085. It refuses the other separators only when they reach it untranslated. box/run_take captures the turn's stdout with universal newlines, so a \r becomes \n before the stream file is written, and the session file is read the same way. \r is therefore the checker's to refuse: check_take.transcript_line_problems reads the transcript's bytes. The adapter's \r entry stays as harmless defence in depth. box/run_take.py's capture and drive.py's session read are unchanged.
Claude Code's writer (JSON.stringify) leaves exactly U+2028, U+2029 and U+0085 raw inside strings. routing.json's ruling text says so (the draft is rebuilt for its sha256), and so do the adapter and check_take comments.
Before any system-under-test pin bump, scan the new tree for raw U+2028/U+2029/U+0085 (HEAD gars/_system/codex_hook.py:89,92 carries them; glitch-b5's r9 NIT 4, not read here).

Mac proof (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, light-ok first), all OK: line_separators 5, claude_code_adapter 28, routing 288, checker_body 30, jsonl_split 5, walk_runner R5Bootstrap 2, build_draft 48. lint_language, copy_manifest, the w6e and w6j byte checks and build_draft --check are clean. The proof of 9c989213's block stands for the code, which is unchanged.

## Exact next step
glitch-b5: the battery on this head at the Haiku/Opus break; every walk is rechecked on it before the freeze.

## RESUME HERE (16 Oct 03:02 EDT; supersedes the blocks above): Agent parity built

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent d247a0e3). Nothing pushed. No athena access. No mac_slot booking held; no process of this lane running.

glitch-b5's Agent parity ruling (option 1; R-A to R-D; CP6 walk w083). Each part was red first, and each commit passed the gates on their exit status (lint_language, copy_manifest, the w6e and w6j byte checks, build_draft --check, gitleaks):
- f34c8a3d part 1: the view reads Agent (kind other). Its input keys are the 2.1.296 schema's closed set (description, prompt, subagent_type, model, effort, run_in_background, name, team_name, mode, isolation); cwd refuses.
- 170b6727 parts 4 and 5, R-C: read_stream keeps assistant and user records with parent_tool_use_id set apart as a sub-agent's (never the agent's words, output or main calls). A late record refuses (R-B).
  - SUBAGENT_EXPLICIT_MODELS = claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5 (2.1.296's first-party alias ids; fable is not admitted). A model off the pin's and that list stops the take (SubagentModelOffList).
  - TAKE_ENV and the inline settings set neither CLAUDE_CODE_SUBAGENT_MODEL nor CLAUDE_CODE_SUBAGENT_MODEL_FORCE.
- 31513e1b part 2, R-A: _take_records copies <session>/subagents/**/agent-<id>.jsonl byte for byte before the config folder goes. The ledger names each copy, and they are scanned as transcripts. The reader is CLOSED (derived from the binary): a file of any other shape HOLDS the walk.
- 91ae369e part 3: check_take binds the sub-agent records. Failures refuse [subagent-records], a new round-4 operator reason routed like harness-condition-violated (routing.json, test_routing). A denied tool refuses [harness-condition-violated], and a file separator [transcript-unreadable].
  - The reach readers read the stream sub-agent records as the agent's own, and the files' attachments are swept for leaks. This sits inside check4's ruled span (re-pinned) and in check4_walk.
- bbacb27a part 6: check.json's agent_calls (int) and subagents ({calls, models}), with the same strictness as no_output_nudges. Rechecks carry them re-derived, and walk_regrade names a forged pair.
- d247a0e3 part 7: the draft's parity note.

Static reads of the pinned 2.1.296 (sha256 24972e3b..., never run): the subagents path (lg); the sidechain writer (insertMessageChain); the Agent schema (Lo/$o/jn); the agent types' models (Explore and Plan "inherit", with an opus-family cap that does not bind haiku or opus; general-purpose and claude have no model field; statusline-setup "sonnet"); the alias catalog (aliases.*.default).

Mac proof (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, light-ok first), all OK:
- agent_tool 12 (17 witnesses), claude_code_adapter 28, routing 289, checker_body 30, checker_constants 27, steer 7, isolation 9, journal_binding 4, line_separators 5, no_output_nudge 9, edited_text_file 10, auto_mode 6, scheduled_wakeup 11, transcript_view 20, pause_adherence 30, awareness_furniture 7.
- drive_commit 31, drive_loop 27, executed_turn_refusal 10, vendor_take_records 4, native_reader_registration 7, walk_wiring 20, cp8_prep 4, stub_take 19, wave4_bindings 13, live_box 38, identity_mode_evidence 8, drive_box_seams 6, walk_grade_seam 3, rehearsals 9, walk_plan 18, recheck_coverage 5, walk_recheck 17, pending_walk 23, build_draft 48.
- test_walk_runner, class by class: 85.
- walk_regrade --check ok.
Not run on the Mac: the generated shards (check_record and _run_one gained lines again), test_round4 and test_box_integration.

What a live Agent walk will show, and what holds it:
- the subagents file's real shape: a mismatch holds the walk for a ruling;
- whether 2.1.296 writes the file under -p: a missing file refuses [subagent-records].
Every walk checked on an earlier head reads "check unreadable" until rechecked on this head, which carries the Agent pair.

## Exact next step
glitch-b5: r10 and the battery on this head.

## RESUME HERE (16 Oct 03:43 EDT; supersedes the blocks above): r10 folded, silent-turn reminder off

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 692dcf12). Nothing pushed. athena was used only for one keys-and-enumerated-values-only read of held w083's turn-1.jsonl (glitch-b5's permission), with nothing written there but a temporary reader, which was removed. No mac_slot booking held; no process of this lane running.

- 25dd1eaa: review r10's fold (F1, F2, R-B revised, F3, NITs).
  - F1: the sub-agent file's tool calls feed every reach reader, and the stream and the file must agree both ways.
  - F2: the meta file (closed shape, bound by toolUseId), attachments under the view's own allow-list, U+2028/U+2029/U+0085 inside strings admitted, the jsonl scrubbed as the transcript is, and the account email counted.
  - R-B: async_launched is read only with its task_notification in its own turn, before the final result. remote_launched refuses; errored calls are recorded.
  - F3: a sub-agent's API errors are routed as the agent's.
  - The w083 structure-only model reads clean.
- 692dcf12: glitch-b5's parity switch. CLAUDE_CODE_SILENT_TURN_REMINDER "0" is set in TAKE_ENV and the inline settings, and proved per turn by steer_condition_problems. The view still refuses silent_turn_reminder, and the draft has its parity note.

Mac proof: listed in both commits (python3.12, env -u CLAUDE_CODE_MESSAGING_TOKEN, light-ok first). Every module listed there is green; build_draft is 48 OK on the committed draft.
Not run on the Mac: the generated shards, test_round4 and test_box_integration.

Open, for the first live walks on this head:
- the 2.1.296 subagents pair's real shape (any mismatch holds);
- a meta with a "model" key (an explicit-model sub-agent) holds under the closed shape;
- the first Opus normal half must show 0 silent_turn_reminder records.

## Exact next step
glitch-b5: r11 and the battery on this head. The held Opus lines 4, 6 and 8 rerun on it.

## RESUME HERE (16 Oct 04:15 EDT; supersedes the blocks above): r11 folded

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 29f2bb91). Nothing pushed. athena not used. No mac_slot booking held; no process of this lane running.

- 29f2bb91: review r11's fold under glitch-b5's rulings.
  - R11-1: the reach reads every file record and every stream sub-agent record. A stream record is dropped only when canonical-JSON-equal to a file record of the same sub-agent; the ones that differ are counted into check.json's subagents.stream_file_differences, an int pending_walk requires. The call-level two-way agreement still refuses.
  - R11-2: tests kill the three surviving mutants (stream-only result, file-only off-list model, meta bound to another agent's call); the dead "n is None or" is gone.
  - R11-3: nothing of an async call after its task_notification; no task event naming it in another turn; completion from its own turn only; the notification's task_id must match its single task_started.
  - R11-4: the meta may carry model (a schema alias), effort (a schema value) and name (a string), each bound to the call's input; R-C still binds the resolvedModel.
  - NITs: each switch compared to exactly the string the study sets (steer "false", reminder "0"; no strip, no case-folding); a stream sub-agent record with no agent_id refuses.

Interpretation flagged to glitch-b5: the NIT said exact "0" for both switches; the steer stays at its set value "false" (compared exactly), since "0" would change run_take and the draft. One-line change if ruled otherwise.

Mac proof: listed in the commit (light-ok first). Not run on the Mac: the generated shards, test_round4 and test_box_integration.

Open, for the first live walks on this head:
- the 2.1.296 subagents pair's real shape (any mismatch holds), and the take's stream_file_differences count;
- the first Opus normal half must show 0 silent_turn_reminder records.

## Exact next step
glitch-b5: r12 (reproduced MINOR+ only) and the battery on this head. The held Opus lines 4, 6 and 8 rerun on it.

## RESUME HERE (16 Oct 05:05 EDT; supersedes the blocks above): r12 and the d7107255 battery folded

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent f12275f1). Nothing pushed. athena not used. No mac_slot booking held; no process of this lane running.

- 0a278e90: review r12.
  - R12-1: one helper, materialize_walk, so regrade_problems reads the whole committed walk folder (subagents/ included) as recheck_doc does. A forged stream_file_differences is named field by field.
  - R12-2: the surviving mutants killed.
  - NITs: the drop is keyed on (type, content); the stored effort follows the writer (absent for lower/higher); end and completion use the last notification.
- f12275f1: the d7107255 battery.
  - The Agent call is the view's own kind, delegate.
  - Graders on a delegated take:
    - scope_read grades it and sends it to the human sample (the access log holds the sub-agent's reads).
    - template_adherence, number_fidelity and confounded_design grade it as before.
    - pause_adherence, new_tasks (where it reads a call) and awareness refuse with DELEGATED_REFUSAL.
    - plan_gate and precondition_refusal are refused at both grading seams, since their code is gate-closed.
  - The 14 generated survivors are killed (rerun with --only), and the walk-check-unwritten witness is re-anchored.

Open:
- The pre-registration draft does not yet say how delegated takes are graded.
- The Mac did not run test_round4, the full generated shards or test_box_integration.

## Exact next step
glitch-b5: r13 on 0a278e90 and f12275f1, and the battery on this head.

## RESUME HERE (16 Oct 05:32 EDT; supersedes the blocks above): delegated takes presented to the graders

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent d6506219). Nothing pushed. athena not used. No mac_slot booking held; no process of this lane running. r13 of 3d0597f9..611f46dd passed; its NITs are folded here.

- d6506219: glitch-b5's pre-freeze ruling.
  - delegated_take.present splices each Agent call's sub-agent session file into the main thread as the agent's own. Its text is presented as reasoning for the reply readers and as text for awareness.
  - graders/delegation.seam presents to plan_gate, precondition_refusal and new_tasks on both roads; the graders are unchanged and their gates hold.
  - A named refusal is kept only for what cannot be presented.
  - Parity: plan_gate 46, precondition_refusal 140 and new_tasks 44 moved cases grade identically, and pause_adherence too.
  - The dated draft note "Agent grading" is in the draft. The r13 NITs: every field named; one harness field.

Open:
- The stream copy of a sub-agent's records is not presented; differences are counted in check.json.
- Nested agents through Bash: claude is on the take's PATH and the walk token reaches Bash children (no subprocess env scrub). This is reported to glitch-b5 as an isolation question, not built.

## Exact next step
glitch-b5: review d6506219, and the battery on this head.

## RESUME HERE (16 Oct 06:24 EDT; supersedes the blocks above): W-3b nested agents bounded

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 9e57ce79). Nothing pushed. athena not used. No mac_slot booking held; no process of this lane running.

- 26ea8729: the same one-line import fix as glitch-b5's 72c9e520, so the two lines do not diverge.
- 9e57ce79: W-3b.
  - Session store: the driver lists the store into session-store.json after every turn (through the box) and at publish (on the host). The checker refuses [nested-agent] for claude-code; the driver judges Codex and Gemini.
  - Count: nested_cli_calls is the third Agent key in check.json; a nonzero count sends the take to the human sample.
  - --no-session-persistence in a Bash command line refuses.
  - Draft: box residual W-3b.

Open:
- Gemini's tmp folder may hold other entries a live walk shows, and they would hold it.
- A nested CLI with another config folder AND a spelling the count misses is not bounded (stated in W-3b).

## Exact next step
glitch-b5: r14 on 26ea8729..9e57ce79, and the battery on this head.

## RESUME HERE (16 Oct 07:29 EDT; supersedes the blocks above): r14 folded

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 953d358c). Nothing pushed. athena not used. No mac_slot booking held; no process of this lane running.

- 953d358c: review r14.
  - The counter is token-level; the persistence switch is refused by its prefix; moving an agent CLI's store (HOME and kin) refuses.
  - The in-box session sweep runs after every turn (box/run_take.sweep_sessions; on the stub walk about 1.5 ms per sweep).
  - Store files are admitted by their producer.
  - Multi-call presentation fixtures and r14's witnesses.
  - The draft's W-3b names what remains.

Open:
- test_box_integration (its fake box gains the sweep) is not run on the Mac.
- The first live walks show whether the sweep or the producer allow-list holds a clean walk.

## Exact next step
glitch-b5: r15 on 953d358c, and the battery on this head.

## RESUME HERE (16 Oct 08:15 EDT; supersedes the blocks above): r15 folded but for the read-only root

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 03711e05). Nothing pushed. athena not used. No mac_slot booking held; no process of this lane running.

- 03711e05: review r15.
  - R15-1: the workflow writers. R15-3: lstat failures and links that leave the roots are reported.
  - R15-4: every line is read, up to 64 MB per file. R15-5: the vendor road runs the readers.
  - R15-6: assignments are refused only in assignment position. R15-7: r15's mutants are killed.
  - R15-2's count is now a regex over the raw command text.

HELD: R15-2's read-only root filesystem and roots from the mount table. The ruling says to check the box read-only first; the Mac has no running Docker daemon, and building and running the take image is not light work.

Static inventory of where the box writes:
- Claude Code 2.1.296:
  - CLAUDE_CONFIG_DIR and HOME, both /opt/cfg: projects/, shell snapshots and the rest of its config.
  - os.tmpdir(), which is TMPDIR, the run tree's .tmp: its claude-<uid> temp folder. The binary falls back to /tmp only when TMPDIR is unset.
  - /dev/shm: the binary opens it read-write for a file-descriptor handoff. Docker mounts a tmpfs there even under --read-only.
- GARS stages: python3 standard library in the run tree, with PYTHONDONTWRITEBYTECODE=1; git writes inside the run tree. The image has no pip, conda or uv.
- Codex and Gemini: CODEX_HOME and GEMINI_CLI_HOME, both /opt/cfg.
- Other processes: the keep-alive is "sleep infinity"; the kill and sweep execs run "python3 -I -S" and write nothing.

Proposed mount set: docker create --read-only, --tmpfs /tmp, --tmpfs /var/tmp, the default /dev/shm, plus the two binds as today. /run, /run/lock and /home/dana stay read-only.

Unknown until a live run: whether any GARS stage, the agent's own commands, or Claude Code writes elsewhere. The box lane's create-argv pins ("exactly two mounts") and the preflight's inspect checks change with this.

## Exact next step
glitch-b5: rule how the read-only check is run (a box-lane rehearsal on athena with the mount set above, or Docker on the Mac). Then r16 on 03711e05, and the battery.

## RESUME HERE (16 Oct 08:45 EDT; supersedes the blocks above): the read-only root built

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent fe0aef73). Nothing pushed. athena not used. No Docker on the Mac. No mac_slot booking held; no process of this lane running.

- fe0aef73: the read-only root.
  - Take containers are created --read-only, with --tmpfs /tmp and /var/tmp (rw,exec,nosuid,nodev,mode=1777) beside the two binds; the preflight pins the inspect (HostConfig.ReadonlyRootfs and Tmpfs).
  - The sweep's roots come from /proc/self/mountinfo: every read-write mount, with /proc, /sys and /dev never read and /dev/shm kept. A read-write mount outside run_take.sweep_roots() refuses [nested-agent].
  - Every turn's EROFS and "Read-only file system" lines (stream and stderr) are recorded in read-only-errors.json.
  - The draft records the read-only root as a box condition, and how round 3's box differed.

Open, on athena (glitch-b5):
- The solo battery, then the owed walks, Haiku line 89 first.
- Any EROFS line names a path to add.
- The first inspect confirms the HostConfig.ReadonlyRootfs and HostConfig.Tmpfs spellings, and the first sweep the mount table's.

## Exact next step
glitch-b5: the battery on this head, then the walks; r16 on 03711e05..fe0aef73.

## RESUME HERE (16 Oct 09:32 EDT; supersedes the blocks above): r16 folded

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 2e11a52d). Nothing pushed. athena not used. No Docker on the Mac. No mac_slot booking held; no process of this lane running.

- 2e11a52d: review r16.
  - Links are reported only into a barred tree or dangling outside the roots, so a venv reads clean.
  - Assignments are read through wrappers, for, read and printf -v; what still escapes is named in W-3b.
  - A captured read-only mount table parses exactly, and a missing table is refused.
  - The expected set is recomputed from the launch journal's run tree, an admitted file over the cap is left to its own readers, and each root is walked once.

## Exact next step
glitch-b5: r17 (stop at nits), and the battery on this head.

## RESUME HERE (16 Oct 12:32 EDT; supersedes the blocks above): the final fold

Writer: the harness lane, for glitch-b5. HEAD: the commit that adds this block (parent 1077f568). Nothing pushed. No Docker on the Mac. No mac_slot booking held.

- 3a263ffe: review r17's NITs.
- 1a06fba6: db9ffe1f's battery reds (2f0b76ab carries the same).
  - The vendor shell-command reader counts a stream line it cannot read (unread_stream_lines in session-store.json) and never refuses on it; the adapter's read_stream still validates every line.
  - The adapters read stderr by its key, so the generated stderr mutants are killed (Codex and Gemini).
- 1077f568: OD57, Javier's ruling on ask T83.
  - box/scan_record.py admits generic-api-key on gars/_references/environment.md line 175 by the sha256 of its exact text, only inside a Read or a Bash cat/grep result (main thread or sub-agent), only in agent text, and only when a probe rescan without that text no longer reports the rule on that line.
  - The scan result lists each admitted finding under "ruled", naming OD57. Every other finding still refuses.
  - The draft has no scanner-rulings place, so it is unchanged.
- Mac pre-check on the working tree: 116 of 120 modules run, 115 green. test_walk_launch timed out at 1200 s (it also stops on an export of 3a263ffe). Four modules were not run on the Mac (test_walk_wiring, test_wave4_bindings, test_wave6_bindings, test_write_image_lock): the Mac battery was stopped on glitch-b5's word, under load.

Open (glitch-b5):
- The record battery on athena on this head.
- The walk return scan (walk_launch fetch, athena_suite.scan_unpublished) carries no allowance by glitch-6b's ruling, so a walk whose committed transcript holds the line may still be refused at fetch. OD57 there needs its own wiring and ruling.
- Held walks w088 and w133 stay as records; lines 94 and 13 re-run as new ids.

## Exact next step
glitch-b5: the athena battery on this head, then the walks.
