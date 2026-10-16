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
