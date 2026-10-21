# Lane file: vendor-b27 (the stub-model probe for the three refused Gemini history-rewrite roads; Gap Study round 4)

Append-only.
Builder: a Claude Opus 5.5 sub-agent of glitch-f1 (the Lane-orchestrator), on the Mac, under Javier's standing delegation.
Clone: /Users/javrodher/aegis-builds/vendor-b27-20261021, branch lane/vendor-b27-20261021, base 04c4e774 (B26's head); its push URL is disabled and nothing is pushed.
Design: lane-reports/vendor-b27-DESIGN.md, a byte copy of /Users/javrodher/glitch/plans/gap-study-round-4/vendor-b27-stub-DESIGN-2026-10-21.md, committed in stage 1.
Pinned source: @google/gemini-cli 0.64.0, tarball /Users/javrodher/aegis-builds/glitch-26-carry-20261021/b26/pkg-dl/gemini-cli-0.64.0.tgz sha256 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6 (`shasum -a 256`, the 14:51 batch), extracted with `tar -x` only into a new empty folder of my own (session scratchpad b27b-pkg); bundle/chunk-NR7L3FXV.js sha256 d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c, the design's; bare `:<n>` is a line of it.
Nothing from the package was executed; the CLI was never run on the Mac; nothing ran on athena.

## glitch-f1's rulings (as received in the brief, 21 Oct 2026)

1. The road and the venue approved: a new box measurement module (box/stub_model_probe.py, built like stub_take.py, reusing run_take's create_argv and teardown, take_config.write, gemini_adapter.argv and native_snapshot's retain), in athena's walk box from the locked take-g image with `--pull=never`, an `--internal` network with no proxy, a stdlib stub on 127.0.0.1 inside the container, exactly three environment changes (GOOGLE_GEMINI_BASE_URL to the stub, a dummy key, no HTTPS_PROXY); launched through walk_launch's road as `probe` and `fetch-probe` entries with its reservation hold; run_take.py keeps refusing the base URL; the probe never touches a counted walk, a record or the register.
2. Admission later only when the record is written by the walks' own client code path (cited lines), the stub's influence is limited to model content and reported token counts, and a fresh reviewer agrees; road (b) only if B2 shows B1's shape. This lane builds the probe and gathers records; the readers are not changed here.
3. Fixtures in the cut form through a new b27 structure-only cutter; the raw probe records (synthetic only) kept as the lane's evidence once produced (the orchestrator fetches them).
4. Keep the `--fake-responses` cross-check of A1.

## Stage 1: the stub server and the scenario scripts

Built:
- box/stub_model_server.py: standard library only, one file, importing nothing of the study (it is copied alone into the run tree and run as `python3 -I -S`).
  The `Stub` class is the whole rule set with no socket (handle(method, path, body) -> status, type, body): the two endpoints of the design (streamGenerateContent with alt=sse, generateContent), match kinds user_text (one part of the last user content is the exact text), user_text_prefix (the last user text starts with the prefix; the compression summary's anchor "Generate a new <state_snapshot> based on the provided history." :337193, its request text `${anchorInstruction}\n\nFirst, reason in your scratchpad...` read at :337200-337215, and the verification "Critically evaluate the <state_snapshot> you just generated." :337228) and function_response (the last content is functionResponse parts only, answering exactly the stub's previous stream calls, bare `call_<n>` or the CLI's `read_file__call_<n>`, :333878-333880).
  Any other request gets 400 with the Google error body and holds the scenario; every later request is refused; requests.jsonl, bodies/req-<n>.json and state.json record each request.
  `make_server` binds 127.0.0.1 only, HTTP/1.1, Connection: close; `--daemon` binds first, then forks, and the parent prints {"ready", "port", "pid"}.
  `fake_records` writes the same script as the pinned FakeContentGenerator's JSONL (:312557-312623, read in this stage: one {"method", "response"} record per call, strict order), from the stub's own response code; an unnamed usage count there is a fixed 1000 (named difference: the fake road sees no request first).
- box/stub_model_scenarios/make_scenarios.py and A1.json ... C2.json: the seven scenarios of the design's section 3 as data; read_file arguments name `${RUN_TREE}/<file>`, which the probe fills (read_file's parameter is `file_path`, :280599, :280621); `expect` carries the design's per-snapshot predictions of the B26 reader, never an input to the stub.
- tests/test_stub_model_server.py: 25 tests (framing under an independent responseLineRE, the 400 and the hold, out-of-order refusals, the inflated count only on the design's entries, call ids, finish reasons, generated text, the fake records, the files bound to the generator, every scenario reachable in order by a local fake client, a loopback server).

One source reading that makes the design's road (c) explicit (section 3): with the failed-compression flag set, compress() calls truncateHistoryToBudget (:337154) and returns CONTENT_TRUNCATED (:337155-337163) before any summary request, so C1's and C2's second compression makes no helper call; the scripts carry none.
Another: compress()'s originalTokenCount is lastPromptTokenCount when positive (:337138-337139), so a truncation re-records whenever the truncated estimate is under the reported 600,000, as the design says for C2.
The summary request's last user text is the anchor followed by "\n\nFirst, reason in your scratchpad. Then, generate the updated <state_snapshot>." (:337200-337204), which is why the summary match is a prefix match.

### Runs (`date` at each step)

Machine discipline, reported: my first batch (14:47-14:51, the tarball's sha256 and the `tar -x` of it, a few seconds) ran in the same command line as a `light-ok` that returned 1 ("CPU speed limit 29 is below 50"); the commands were chained with `;`, not `&&`.
From 14:51 every batch runs behind a gate script that calls `mac_slot.py light-ok --work gap-study-r4` and retries every 60 s, and the batch starts only on exit 0 (`b27gate.py N && ...`).
The gate held for most of 14:51-15:25 (CPU speed limit 20-47 below 50, load1 up to 27.75); code was written in that time and nothing ran.

- Red, 15:25:19: `python3.12 -B -m unittest tests.test_stub_model_server` over a `git archive` of 04c4e774 with only the new test file laid over: "Ran 1 test", "FAILED (errors=1)" (the module does not exist on the base).
  Deviation, reported (as lanes vendor-b25 and vendor-b26): the stub was drafted before its tests; the red is that base-archive run, and the mutation check below is the evidence each test binds its rule.
- Green, 15:25:19-15:25:21, lane working tree: "Ran 25 tests", "OK".

### Stage 1 mutation check (scratch archive of 94bf7966, each mutant restored from a byte backup), 15:30:25-15:30:33 EDT

`b27mut.py` (session scratchpad) applied each mutant to the archive copy, ran tests.test_stub_model_server, and restored the file's bytes (asserted):
- M1 the hold dropped (a refusal no longer holds the scenario): "FAILED (failures=1, errors=3)";
- M2 the call-id check dropped: "FAILED (failures=1)";
- M3 the named promptTokenCount ignored: "FAILED (failures=3)";
- M4 the SSE separator cut to one newline: "FAILED (failures=12, errors=2)";
- M5 a helper's answer resets the calls the chat must answer: "FAILED (failures=5)";
- M6 finishReason dropped from the final chunk: "FAILED (errors=2)";
- M7 a scenario JSON edited by hand (A1's last prompt): "FAILED (failures=2)".

## Stage 2: the probe module and its walk_launch entries

Built:
- box/stub_model_probe.py, per ruling 1 (module docstring lists what runs unmodified and each departure, also written into every scenario's probe.json `departures`).
  The environment is computed, not typed: `probe_environment` takes run_take.take_environment(GEMINI) and makes the three changes; `environment_changes` refuses any other difference (an extra variable such as a key-file path, HTTPS_PROXY present, a key other than the fixed dummy, a base URL off 127.0.0.1).
  The exec is exec_argv's form with run_take.launcher_argv, so the CLI starts from an empty environment plus exactly that row, as every walk turn does; the dummy key rides by name in the client environment only.
  The container: run_take.create_argv on a TakeSpec with the locked take-g image id (preflight.load_take_lock of box/gemini/image.lock) and walk_builders.TAKE_RESOURCES, on a network made by `docker network create --internal`; no proxy, no sidecar, no network connect.
  Per scenario: take_config.write (its sha256 recorded), the run tree (.tmp, .home, the synthetic files, `.stub-probe/` with the stub's read-only copy, the materialised script and, for A1-fake, the fake-responses file), ownership.grant, network, take, the stub started as the agent (`--daemon`, ready line with the port), `gemini --version`, then each process: gemini_adapter.argv (check_model on the study argv), stdout and stderr kept as turn-<n>.jsonl and turn-<n>.stderr.txt, the session id from process 1's init, the session file located by native_snapshot.gemini_session_rel over ownership.operator_list and read by operator_read, retained by native_snapshot.retain_bytes, the stub's state read; a non-zero exit, no session id, a held stub or an unretained snapshot stops the scenario.
  Teardown: run_take._teardown_partial (take container, then network, by recorded id), run_take.leaked, a network listing, ownership.restore; then the stub's log, bodies and state, the materialised script, ledger.json (turns[].sent) and probe.json are written; manifest.json and calls.json at the top.
  `--dry-run` prints every argv (grants, network, take, stub, version, each process, teardown) and the process environment, and runs nothing; it is the one mode allowed off Linux.
- box/walk_launch.py (an existing file; its claim's reason in COPIED.d/live-box-2026-10-14.json gains one sentence, the way lane vendor-b24 recorded its edit there): run_command's tail factored into `_gate_env` and `_held_command` with its string byte-unchanged (sha256 7eb86a1e…881b8 computed at the base 04c4e774 at 15:31 and pinned in the test); `probe` (the claim, gate and hold under gap4-probe-<id>, the probe's argv with --scratch-parent CONFIG_PARENT and --output <child>/stub-probe-<id>, no commit identity; walk.pid, walk.log and walk.exit as a walk's, so `status` reads it) and `fetch-probe` (tar on athena, copy, sha256 on both sides, unpacked by this code with only regular files and folders under the one folder, the manifest checked, every file canary-scanned with no allowance through the existing canary_scan, then moved to --out).
- tests/test_stub_model_probe.py: 30 tests.

Deviation from ruling 1's wording, flagged (not a block): the ruling says the probe reuses run_take's teardown.
run_take.teardown refuses a launch record without a proxy and a sidecar and would remove and log both, and ruling 1 itself fixes a road with neither, so the probe uses run_take's own by-recorded-id remover for that case, `_teardown_partial`, which removes exactly the take container and then the network; leaked() and a network listing confirm nothing is left.
For the same reason run_take.launch is not used (it creates the proxy and the sidecar); the steps run through run_take's own _step, _new_id and _inspect.
glitch-f1 may rule otherwise; nothing else depends on it.

### Runs (`date` at each step)

- Red 1, 15:43:16: tests.test_stub_model_probe over a `git archive` of 94bf7966 (stage 1) with only the new test laid over: "Ran 1 test", "FAILED (errors=1)" (no probe module).
- Red 2, 15:43:28-15:43:31: the same archive with the probe module laid over too (walk_launch at the base): "Ran 30 tests", "FAILED (failures=1, errors=13)": every walk_launch probe test errors (no probe_command, fetch_probe, _extract_probe) and the no-production-import test fails on the base walk_launch's absent PROBE_MODULE line; run_command's sha256 test passes on the base, as it must.
- Green, lane tree, one module at a time: test_stub_model_probe 30 OK (15:42:42-15:42:47, again 15:43:43-15:43:48); test_stub_take 19 OK (15:43:39-15:43:42; its no-production-import rule still holds with the new box modules); test_stub_model_server 25 OK (15:43:42-15:43:43); test_freeze_shapes 9 OK (15:43:48-15:44:18, the new claims read).
- test_walk_launch as a whole passed its 45-second cap (15:46:26-15:47:11, killed by the cap, no verdict); a heavy slot was refused at 15:47:22 (`mac_slot.py run --kind heavy ... --minutes 10`: "busy: first slot: CPU speed limit 77 is below 80", rc 3), so it is skipped and recorded.
  Run one test at a time instead (15:47:37-15:49:16): TestTheRoad test_l1_ship, test_l2_run, test_l3_fetch, test_l4_bounds, test_l5_guards, test_l6_start, test_l7_env, test_l9_echo_and_env, test_pinned_tree_is_variants, test_reserve_pin_is_the_runbooks, and TestSkipRule (2), each "OK"; test_l8_blobs and TestWitnesses each passed the 30-second cap with no verdict; TestOD57ReturnRoad and TestRealReturnScan were not run. They wait for a heavy slot or athena's battery.
- Outside the gate, reported: two single-file reads by grep ran at about 15:41 without a `light-ok` first (test_walk_launch's FAKE_GITLEAKS and an `ls`); everything else in this stage ran behind the gate.
