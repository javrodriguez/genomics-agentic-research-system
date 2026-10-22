# Lane file: hook-control (the D8 hook positive control for arms O and G; Gap Study round 4, a D8 walk-phase duty)

Append-only.
Builder: a Claude Opus 5.5 (medium) sub-agent of glitch-f1 (the Lane-orchestrator), on the Mac, under Javier's standing delegation.
Clone: /Users/javrodher/aegis-builds/hook-control-20261021, a clone of /Users/javrodher/aegis-builds/vendor-b27-20261021, branch lane/hook-control from B27's head 49c350a9b008e3ea15f83f3873fe62b3766722fe; its push URL is set to `DISABLED-no-push` and nothing is pushed.
Design: lane-reports/hook-control-DESIGN.md, a byte copy of /Users/javrodher/glitch/plans/gap-study-round-4/hook-control-DESIGN-2026-10-21.md (sha256 da686566ef4a50e610524af289b12cb393a0de96b76a1873473be2601ac4ee45 on both, `shasum -a 256` at 22:45:29 EDT).
Build and test on fakes only on the Mac; the athena run is a later operator's step. Nothing here runs a container, a CLI, a model or a login.

## glitch-f1's rulings on the design's open calls (as received in the brief, Wed 21 Oct 2026)

1. Base: B27's head 49c350a9 (it carries no walk records, so its ships pass athena's door), in this new clone; the lane later merges into lane/vendor-b28 after B27 does (small conflicts expected in B27's probe and tests; changes kept additive).
2. Gemini: the G-on/G-off pair on B27's stub road as designed.
3. Codex: the four configurations as designed (O-on-bypass must fire, O-off-bypass silent, O-off-study with the exact walk argv silent, O-on-study informational); the trust-bypassed pair is accepted as the proof that the switch gates hooks.
4. Codex roads: C0 (no model, no login, internal network) and C1 (a dead local provider) in one athena trip; C2 only if both on twins stay silent, and then it is a new ruling.
5. Verdicts: PASS only when every on twin fires and every off twin stays silent; INCONCLUSIVE when an on twin stays silent (never a pass); FAIL when any off twin fires, which holds that arm's counted runs.
6. The fail-safe pre-run marker check and the twin diff rule stay as designed.
7. The record: the fetched folder /Users/javrodher/aegis-builds/hookctl-<date>/ plus a labelled note in lane-reports/, read by the pre-freeze reviewers.
8. Arm A (Claude) is out of this lane's scope: a separate read-only investigation answers whether GARS's hooks run there.
9. Tests on fakes as the design lists them, red first; mutants for the verdict rule, the diff rule and the marker pre-check; the one-process hazard check.

## Stage 1: the base, the design copy, this file

- Clone and branch: `git clone` of vendor-b27-20261021, `git checkout -b lane/hook-control 49c350a9b008e3ea15f83f3873fe62b3766722fe`; `git log --oneline -1` read "49c350a9 vendor-b27 stage 8: the A1-fake cross-check gets one fake file per process (glitch-f1's B27 ruling 4)".
- Mac discipline: every batch runs behind `/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok --work gap-study-r4` (exit 0 = go); first read 22:38:13 EDT, "light ok: load1 11.62 < 16.00, memory pressure normal, CPU speed limit 52 >= 50".

## Stage 2: the hook control module, its walk_launch entry, its tests

Built:
- evals/gap-study-4/box/hook_control_probe.py, a new module beside B27's probe (not an edit of it: the brief asks for additive changes, and the lane later merges onto lane/vendor-b28 after B27, so B27's file stays byte-unchanged; a deviation from the design's "box/stub_model_probe.py: ..." code list, reported).
  It reuses B27's pieces by import (stub_model_probe.process_argv, environment_changes, cli_inner, stub_start_argv, build_run_tree, take_spec, client_env, Recorder, check_output) and writes records with B27's RECORD_KIND, so walk_launch's fetch-probe and its manifest check read them unchanged; its own not-a-study-record text names this lane.
  The runs: HG (G-on, G-off) and HO-C0, HO-C1 (O-on-bypass, O-off-bypass, O-off-study, O-on-study), each run its own config folder, run tree, `--internal` network, take container, teardown by id and restore.
  The twins: hook_twins builds both from take_config.files_for bytes; check_twins (the diff rule) refuses unless the base is the road's derivation of the study bytes (C1: exactly the dead provider's top-level line and table), the off twin is the base plus the planted hook only with the switch off, and the on twin differs from the off twin in exactly one value, the switch (Gemini `hooksConfig.enabled`, compared over the flattened JSON; Codex the one line `hooks = false` -> `hooks = true` under `[features]`, every other byte and file equal).
  The marker: `/usr/bin/python3 -I -S -c "<append program>" <run tree>/.hookctl/fired.log <Event>`; Gemini all eleven HookEventName events (chunk-NR7L3FXV.js:336623-336636, read in the pinned bundle at /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/hookctl/pkg/package/bundle/chunk-NR7L3FXV.js, sha256 d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c read with `shasum -a 256`); Codex SessionStart and PreToolUse in GARS's shape.
  The self-test: the exact marker command through `/bin/bash -c` as the agent (run_take.agent_exec_argv) with event `selftest`; marker_precheck then requires fired.log to read exactly `selftest\n`, or the run raises before any CLI process (recorded as `precheck`, never a run problem).
  Codex: process argv from codex_adapter.argv, run_take.check_codex_turn on it, then (bypass runs only) `--dangerously-bypass-hook-trust`, before the prompt in process 1 and right after `resume` in process 2 (both placements are listed by the pinned help captures, lane-reports/live-box-evidence-2026-10-13/codex-exec-help.json lines 64-66 and codex-resume-help.json lines 47-49 of their stdout); the resume runs only when process 1's stream names a `thread.started` thread id; per-process cap 120 s.
  Codex run tree: `git init` and one empty commit on the host before the grant (identity `dana <dana@localhost>`, a fixed date, no global or system git config), plus .tmp, .home and .hookctl.
  The verdict: hook_verdict per arm and overall, glitch-f1's rule read literally: every on twin run (G-on; O-on-bypass on every road run) must log SessionStart in process 1 after a good self-test, so C0 silent with C1 firing is INCONCLUSIVE, not PASS (the design's "at least one road" is the looser reading; glitch-f1's ruling 5 is followed); any event in an off twin is FAIL and outranks everything; a failed self-test, no process, a lost log or a missing run is INCONCLUSIVE; O-on-study never moves it. The probe exits 0 only on PASS with no run problem (a failure other than the pre-run check, a leak, a failed restore, a kept scratch; never the CLI's exit, which C0 and C1 expect to be non-zero).
  Descriptive (the design's open call 7, no runtime cost): census_names records that run_take.CONFIG_FOLDER_NAMED refuses the planted `hooks.json` by name ("hook config (hooks/src/engine/discovery.rs 339-343)").
- evals/gap-study-4/box/walk_launch.py, additive only: HOOK_PROBE_MODULE, hook_probe_command (the probe's hold id rule, fresh_child_guard, _held_command and output folder; `--gemini-image`/`--codex-image` each exactly when one of its scenarios is named), probe_hooks, and the `probe-hooks` verb; the docstring gains its usage. probe_command, fetch_probe and run_command are byte-unchanged.
- evals/gap-study-4/tests/test_hook_control_probe.py: 52 tests on fakes (the marker's text, a real `/bin/bash -c` run of it, the hooks documents, the diff rule and its refused mutant twins, the set hash equal to take_config.config_sha256, the Codex argv and flag placement, the Codex environment equal to the row and the exec equal to run_take._codex_exec_argv byte for byte with only the lease check stubbed, Gemini equal to B27's exec, the ast bindings, the verdict truth table, the pre-run check, the dry run, full runs on a fake box, walk_launch's entry and its witnesses).
- evals/gap-study-4/tests/test_stub_model_probe.py: one additive exemption in B27's no-production-import test for box/hook_control_probe.py (itself bound unimported by the new tests).

Deviations, each with its why:
1. A new module instead of edits to stub_model_probe.py, and the HG script as a constant in it instead of box/stub_model_scenarios/HG.json: B27's scenario folder is bound byte for byte to its generator (tests/test_stub_model_server.py:354-364), so a file there would edit B27's generator; both keep the merge onto lane/vendor-b28 additive.
2. The Codex environment is the Codex row exactly, HTTPS_PROXY included (the design said the row less HTTPS_PROXY): run_take.launcher_argv admits the no-login name only over exactly the Codex row's names (run_take.py:1021-1029), so dropping it would need a production launcher change; on the `--internal` network the named proxy does not exist, so there is still no route out, and the exec now equals the walk's exec byte for byte (bound by a test).
3. A `probe-hooks` verb beside `probe` instead of an optional `--codex-image` on `probe`: probe_command's text holds test_walk_launch witness texts and B27's own pins; a separate entry leaves them byte-unchanged.

Inference to watch on athena (not verified here): the study's config.toml carries `forced_login_method = "chatgpt"` (take_config.py:61) in every run, so Codex may refuse before session start with no login on both C0 and C1; then both on twins stay silent, the verdict is INCONCLUSIVE, and C2 is glitch-f1's new ruling.

### Runs (`date` at each step, every batch behind the light-ok gate, a retrying gate script in the session scratchpad)

- Red, 22:49:43 EDT: `python3.12 -B -W ignore evals/gap-study-4/tests/test_hook_control_probe.py` with the tests written and no module: "ImportError: cannot import name 'hook_control_probe' from 'box'".
- First green attempt, 22:56:00-22:56:09: "Ran 52 tests", "FAILED (failures=6, errors=1)", all test-side: a helper that wrote `selftest` where the unit key is `selftest_read`, the study-word check reading the never-planted `selftest` event, and the Gemini environment check reading the launcher pairs without the by-name key; then 22:57:24-22:57:31 "FAILED (failures=2, errors=1)": the real bash run read this Mac's own ~/.bashrc (the test now gives bash a scratch HOME) and the module built the network argv through B27's helper instead of run_take.network_name (fixed in the module).
- Green, 22:57:55-22:58:02: "Ran 52 tests", "OK".
- B27's own tests on this tree, 23:00:15: test_stub_model_probe "Ran 47 tests", "OK".
- Dry run, 23:00:15-23:00:23: `hook_control_probe.py ... --codex-image sha256:21b21415... --scenarios HO-C1 --dry-run` exit 0; O-on-bypass's twins row reads diff {"line": 10, "switch": "features.hooks", "off": false, "on": true, "planted": "hooks.json"} and walk_census_refuses [["hooks.json", "hook config (hooks/src/engine/discovery.rs 339-343)"]]; process 2's argv ends `resume --dangerously-bypass-hook-trust <thread id> Thanks.`.
- Correction to stage 2's deviation 2: the no-login check in run_take.launcher_argv sits at run_take.py:1018-1027 (`if login == NO_LOGIN:` at 1018, "the no-login launcher's values must be exactly the Codex row's names" at 1027, read with `grep -n`), not 1021-1029.

## Stage 3: mutants, the hazard check, checks.d and COPIED.d

### Mutation check (scratch archive of 6cb1e827, each mutant restored from a byte backup), 23:12:33-23:15:39 EDT

`hcmut.py` (session scratchpad) applied each mutant to box/hook_control_probe.py in a `git archive` copy, ran tests/test_hook_control_probe.py, and restored the file's bytes (sha256 bfd0ab2913430bf19c98cfa703d22d141dbcd386923e8880c87e6d8374246241 asserted equal after each):
- the verdict rule: V1 an off twin's events ignored "FAILED (failures=4)"; V2 the self-test line accepted as the pass event "FAILED (failures=2)"; V3 the on twin's self-test not required "FAILED (failures=4)"; V4 a silent on twin not counted (the looser reading) "FAILED (failures=7)"; V5 FAIL no longer outranks INCONCLUSIVE "FAILED (failures=2)"; V6 a missing run not counted "FAILED (failures=3)"; V7 the informational run counted as an on twin "FAILED (failures=6)"; V8 the overall verdict the best arm "FAILED (failures=7)"; V9 a rewritten log trusted as silent "FAILED (failures=1)"; V10 an off twin's failed self-test not counted "FAILED (failures=4)".
- the diff rule: D1 the Gemini change set loosened "FAILED (failures=1)"; D5 the Codex one-line count loosened "FAILED (failures=3)"; D6 the [features] section check dropped "FAILED (failures=1)"; D7 the road's base derivation unchecked "FAILED (failures=3)"; D8 the Codex hooks file unchecked "FAILED (failures=1)"; D9 the on twin's switch value unchecked "FAILED (failures=3)".
  Survivors on that run: D2 (the Gemini off twin no longer held to the study's settings), D3 (the Gemini off twin's hook not required), D4 (the Codex off config no longer the base's bytes).
- the marker pre-check: P1 any non-empty log accepted "FAILED (failures=6)"; P2 no log accepted "FAILED (failures=2)"; P3 the run ignores the pre-check "FAILED (failures=1)"; P4 a log that starts with the self-test accepted "FAILED (failures=2)".
- the Codex argv: T1 the trust flag on every run "FAILED (failures=4, errors=1)".
- D6 and D9 were already killed by two tests added before this run (commit 6cb1e827: the flipped line must sit under [features]; the on twin's switch must be exactly true), found missing while writing the mutant list.
- D2 and D4 survived because every refused mutant twin had changed one twin only, so the change-set check caught it first; a new test mirrors one change into both twins (Gemini telemetry.enabled, Codex web_search), so only the study-bytes check can refuse it. Rerun 23:16:08-23:16:38 with that test: "Ran 55 tests", "OK" on the tree; D2 "FAILED (failures=1)", D4 "FAILED (failures=1)", D3 "OK".
- D3, named equivalent, no test: an off twin whose `hooks` is not the planted document is already refused either by the on-twin hook check (when the on twin lacks it too) or by the change-set check (when the on twin has it, the flattened diff holds the hooks paths); the clause stays as the rule written down.

### The one-process hazard check, 23:16:54-23:17:12 EDT

The two changed test modules with a neighbour before and after each, in one process from evals/gap-study-4 (`unittest.defaultTestLoader.loadTestsFromNames`): tests.test_holdout_digests, tests.test_hook_control_probe, tests.test_identity_evidence, tests.test_stub_agents, tests.test_stub_model_probe, tests.test_stub_take: "Ran 160 tests", "OK"; `sys.platform` read "darwin" afterwards (the fake runs patch it to linux inside a mock context only).

### checks.d, COPIED.d, the battery's rules

- evals/gap-study-4/checks.d/hook-control.txt: one command, `python3 -B -W ignore evals/gap-study-4/tests/test_hook_control_probe.py`; run_checks.file_problems over checks.d read `[]` and its commands list holds `hook-control.txt:5` (23:17:45).
- evals/gap-study-4/COPIED.d/hook-control.json: the two new files, the lane's own checks file and fragment, and the edits without transfer named in the fragment's entry (box/walk_launch.py, lane live-box-2026-10-14's; tests/test_stub_model_probe.py, lane vendor-admission's). `copy_manifest.py --check`, 23:18:53-23:19:15: rc 0, "ok: 546 files from 61 fragment(s) ...".
- test_round4 fails any skip whose reason is not in SKIP_ALLOWED (test_round4.py:14-16, :104-106), so the real-bash marker test no longer carries a skip (athena's Debian has /usr/bin/python3 and /bin/bash); green 23:19:36-23:19:44 "Ran 55 tests", "OK", and loaded the battery's way (discover with top_level_dir tests/) 23:21:02-23:21:09: "Ran 55 tests", "OK", skipped [].
- Not run on the Mac: the whole battery (about 13 GB free; never a whole suite here) and test_walk_launch's heavy TestWitnesses (its light precondition, every witness text occurring once, is a test in both B27's and this lane's module and is green). Athena's battery on the head is the verdict.

## The operator's athena plan (a later operator's step; nothing here has run on athena)

Preconditions: a fresh review of this lane's head (opus-medium, adversarial first lens per the design's section 2) and athena's battery green on that head, both as glitch-f1 schedules them; then `athena_suite.py active` reads `athena free lower_may_start=true`, and `mac_slot.py light-ok --work gap-study-r4` exits 0.
Values: python `/usr/local/bin/python3.13`, `--suite`, `--reserve`, `--gitleaks` as B27's smoke run used them (/Users/javrodher/aegis-builds/b27-smoke-20261021/RUNLOG.md, from lane-reports/first-walk-runbook-2026-10-15.md section 3); images from the committed locks, Gemini sha256:d10aa00b5958b00d1c719be1f0572967c04f30bfe381a427107c9e9a3f16b013 (box/gemini/image.lock) and Codex sha256:21b214159e4eb02d5e73f78ccdf5ee047da2fc6944808f9a454a6b0f427dd381 (box/codex/image.lock), each re-read from the lock at the run; `<date>` from `date +%Y%m%d` at the run.
1. Mac, optional and light: `python3 -B .../evals/gap-study-4/box/hook_control_probe.py --box .../evals/gap-study-4/box --scratch-parent /nonexistent --output /nonexistent/stub-probe-hookctl1 --gemini-image <G> --codex-image <O> --scenarios HG,HO-C0,HO-C1 --dry-run` (prints every argv per run, runs nothing).
2. ship: `walk_launch.py ship --repo /Users/javrodher/aegis-builds/hook-control-20261021 --ref lane/hook-control --suite ... --reserve ... --gitleaks ... --work /Users/javrodher/aegis-builds/hookctl-<date>/ship-work`; the printed head must equal the reviewed head.
3. athena gate: `athena_suite.py active` reads free.
4. start: `walk_launch.py probe-hooks --child <child from ship> --probe hookctl1 --scenarios HG,HO-C0,HO-C1 --gemini-image <G> --codex-image <O> --reason "D8 hook positive control, arms O and G"` (one athena trip: HG, then C0 and C1, glitch-f1's ruling 4).
5. `walk_launch.py status --child <child>` until it reads `exit=<n>`; worst case about 16-20 minutes of probe time (eight Codex runs at up to 120 s per process).
6. fetch: `walk_launch.py fetch-probe --child <child> --probe hookctl1 --out /Users/javrodher/aegis-builds/hookctl-<date>/stub-probe-hookctl1 --gitleaks ... --work /Users/javrodher/aegis-builds/hookctl-<date>/fetch-work`, then the athena gate again.
7. Read: summary.json's `verdict` (PASS, INCONCLUSIVE or FAIL, with each arm's reasons and each run's events); `exit=0` only on PASS with no run problem. Write RUNLOG.md beside the fetched folder in B27's form, and the labelled note lane-reports/hook-control-<date>.md (verdict, the manifest's sha256, each twin's twin_sha256 and study_sha256) for the pre-freeze reviewers.
8. If both C0 and C1 on twins are silent, the verdict is INCONCLUSIVE and C2 is glitch-f1's new ruling; if any off twin fired, FAIL holds that arm's counted runs until a fix and a rerun.

## Close of the build (head 51506c662f68c6d95aa294ba15cc1734034f450b, `git rev-parse HEAD`)

- One process on that head, 23:26:43-23:27:05 EDT: tests.test_holdout_digests, test_hook_control_probe, test_identity_evidence, test_stub_agents, test_stub_model_probe, test_stub_model_server, test_stub_take: "Ran 189 tests", "OK".
- Not pushed (push URL `DISABLED-no-push`). Next, not this lane agent's: the fresh review, athena's battery on the head, then the operator's plan above; the merge onto lane/vendor-b28 after B27's.
- Open for glitch-f1 (not ruled in the brief, left as they were): the design's open calls 8 (the records scan of the committed walks) and 13 (the stale settings_guard.py:221 text); open call 7 is recorded descriptively (census_names), never a gate.

## Stage 4: the review fold (REVIEW-hook-control-d9d9b79, VERDICT CHANGES; glitch-f1's rulings as received)

Review: /Users/javrodher/aegis-builds/REVIEW-hook-control-d9d9b79.md (its fakes and mutants in the session scratchpad's review-hookctl/).
glitch-f1's rulings: M1 an off twin counts as silent only with its on twin's liveness (Gemini: the stub's state.json shows requests served; Codex: the same first stream records or the same exit class), and cli_version must exit 0, with the reviewer's exit-126 fake as a red test; m1 the verdict reads every unit's failure, so a failed unit never leaves PASS; m2 fired.log read on the host once more after teardown, the off twins judged on that read; m3 (glitch-f1's revision of "every on twin must fire", now that liveness is bound) the per-road reading: a road passes when its on twin fires and its live off twins stay silent, the Codex arm PASS when at least one road passes and no off twin on any road fires, FAIL when any off twin fires, INCONCLUSIVE when no road's on twin fires, Gemini as before; m4 noted (below); NITs 1-3.

Built (box/hook_control_probe.py, tests/test_hook_control_probe.py):
- Liveness, per process, recorded in each probe.json `liveness`: Gemini `served` (this process's requests from the stub's state.json `requests` counter, stub_model_server.py:293-295); Codex `exit_class` (ok, error, timeout, or exec-failed for no code or 125/126/127) and `first_type` (the first JSON record's `type`). liveness_problem: the same process count as the on twin; Gemini at least one request served in every process (a model request comes after SessionStart); Codex never exec-failed, and the same exit class and first record type as the road's on twin (O-on-bypass). Only the first record is compared, not the whole stream, because an on twin may print hook items the off twin does not (inference; no Codex hook engine source here).
- unit_blockers, read for every run including the informational one: any failure (the pre-run check's included), a `--version` exit other than 0, a Gemini resume not run (the design's open call 9). Any blocker makes the arm INCONCLUSIVE at best; an off twin's event still makes it FAIL.
- The host's final read: after a successful restore the probe reads <run tree>/.hookctl/fired.log itself (every writer is dead), keeps it as fired-after-teardown.log and `final_read`; off twins are judged on the per-process reads plus that read, and an off twin without it cannot pass its road.
- The verdict per road (`roads` in each arm's record), as ruled in m3; a missing run anywhere still blocks a PASS.
- NIT 1: a DEPARTURES entry names the per-run tree path inside the twins (the trust table's key, the marker's fired.log path), so twin_sha256 differs across runs.
- NIT 2: a test refuses a Gemini twin holding the same document in other bytes (compact, or with a leading duplicate `hooks` key).
- New fake-box tests: the reviewer's OffDies (every off CLI exits 126 with no stream) and Off2Raises (G-off's resume raises), and LateWriter (an off Codex process times out in the client and writes SessionStart before teardown).

Runs (`date` at each):
- Red, 23:47:03-23:47:12 EDT, the new tests on the stage-3 module: "Ran 62 tests", "FAILED (failures=24)", every failure on a new rule (OffDies, Off2Raises, LateWriter, liveness, cli_version and failures, the host read, per-road). The serialisation test passed there, as a mutant-killing test should (the rule existed; no test held it).
- Green, 23:48:14-23:48:23: "Ran 62 tests", "OK"; committed as c7d81bbe.
- Mutation check over a `git archive` of c7d81bbe, 23:49:40-23:56:59, the file restored after each (sha256 e617d943ba1604e94bb9f133cc620b66bc80069217adc48b0ebae68aaff5ddd9): 38 mutants; failed as they should: V1, V1b (the host read ignored), V2-V5, V7-V10, L1 (the liveness clause dropped, failures=10), L2, L4, L5, U1-U4, M3 (every Codex road required again), F1, F2, R6 (the reviewer's survivor, now failures=1), D1, D2, D4-D9, P1-P4, T1. Survivors: V6 (a missing run not counted), L3 (a docker exec failure admitted), D3 (equivalent, as in stage 3).
  Two tests added for them: a missing O-off-study on C0 while C1 passes is INCONCLUSIVE; a docker exec failure in the on and both off twins alike is never live. Rerun 23:58:28-00:01:10: "Ran 64 tests", "OK"; V6 "FAILED (failures=1)", L3 "FAILED (failures=1)", D3 "OK" (named equivalent).
- One process (the gate held until 00:12:02): test_holdout_digests, test_hook_control_probe, test_identity_evidence, test_stub_agents, test_stub_model_probe, test_stub_model_server, test_stub_take: "Ran 198 tests", "OK"; `sys.platform` read "darwin" afterwards. `copy_manifest.py --check` rc 0 (00:12:49).

m4, the named risk restated: the reviewer read the pinned Codex source subset and found `enforce_login_restrictions` returns Ok with no auth loaded (login/src/auth/manager.rs:1331-1349 at 092d3acd, as the review cites it; not re-read here), so `forced_login_method = "chatgpt"` alone does not stop `codex exec` before the thread starts. The open question is narrower: whether SessionStart fires before the first model request or the provider's auth check. INCONCLUSIVE stays the honest outcome if both Codex on twins are silent; C2 is ruled only after glitch-f1 reads C0's and C1's turn-1.stderr.txt.

The operator's plan, step 7 replaced (NIT 3): read summary.json's `verdict` (each arm's verdict, `roads` and reasons) AND its `problems` (each run's leak, network, restore and scratch record); `exit=0` only on PASS with no problem. Before step 2, stop if step 1's dry-run twins rows or image ids differ from the committed locks. Then RUNLOG.md and the labelled note as before; for an INCONCLUSIVE Codex arm, copy C0's and C1's O-on-bypass turn-1.stderr.txt paths into the note for glitch-f1's C2 ruling.

## Stage 5: the Gemini session entries' matcher (glitch-f1's ruling after the HG trip of 22 Oct)

Finding (the trip's G-on, /Users/javrodher/aegis-builds/hookctl-20261022/stub-probe-hookctl1/HG): G-on logged ten per-turn events in process 1 and five in process 2 but never SessionStart or SessionEnd, both processes exiting 0 (the awaited path). Every planted Gemini entry carried `"matcher": ".*"` (hook_control_probe.py:200 at 2d4fec8f), and 0.64.0 matches a SessionStart or SessionEnd entry against its trigger by exact string equality, so `.*` matched no trigger: my design error (GARS's Codex shape carried over to Gemini).
Source, re-read in the verified pin /Users/javrodher/aegis-builds/gemini-cli-pin-20261022/unpacked/package/bundle/chunk-NR7L3FXV.js (sha256 d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c, `shasum -a 256` at 04:43:35 EDT): matchesContext returns true for an empty or absent matcher (365636-365639); an entry whose context has a trigger goes to matchesTrigger (365647-365648), which is `matcher === trigger` (365666-365668); the tool-name road reads the matcher as a regex (365655-365662).
Fix: Gemini SessionStart and SessionEnd entries carry `"matcher": ""` (GEMINI_TRIGGER_EVENTS); the nine per-turn events keep `.*`; Codex is untouched.
- Red, 04:43:49-04:43:58: a new test reading the generated settings of both twins (SessionStart and SessionEnd matcher `""`, the rest `.*`) plus the updated hooks-document test: "Ran 65 tests", "FAILED (failures=5)".
- Green, 04:44:11-04:44:23: "Ran 65 tests", "OK"; B27's test_stub_model_probe "OK".
Next: the reviewer's short closure, then the HG-only trip (`--scenarios HG`, Gemini image only) after the furniture battery, shipped from the B26 clone as before.

## Stage 5, the closure's NIT (the closure of d07561f6 PASSED with one NIT)

PreCompress also matches its trigger by exact string (firePreCompressEvent passes `{ trigger }` as the context, chunk-NR7L3FXV.js:365807 in the verified pin, sha256 prefix d566e81b1df8d4d4 re-read at the fold), so its `.*` could never fire; it now carries `"matcher": ""` with SessionStart and SessionEnd (GEMINI_TRIGGER_EVENTS).
The HG stub script never compresses, so PreCompress is armed but not exercised by this control.
Red, 04:47:04 EDT (the extended tests with the module fold stashed): "Ran 65 tests", "FAILED (failures=3)"; green, 04:47:19: "Ran 65 tests", "OK".

## Correction to stage 5's closure-NIT section (after the HG2 trip on 41796301)

"The HG stub script never compresses, so PreCompress is armed but not exercised by this control" is wrong: in HG2's G-on, PreCompress fired 3 times, each line directly before a BeforeModel line (/Users/javrodher/aegis-builds/hookctl-20261022/stub-probe-hookctl2/HG/G-on/fired-after-teardown.log lines 4, 10 and 18, read with `grep -n`). The CLI fires the event without a real compression, so PreCompress is armed and exercised; the empty matcher is what let it fire. HG2 PASSED (glitch-f1's relay; /Users/javrodher/aegis-builds/hookctl-20261022/RUNLOG.md, HG2).
