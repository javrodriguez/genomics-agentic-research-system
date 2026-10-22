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
