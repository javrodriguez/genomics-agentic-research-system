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

### Stage 2 mutation check (scratch archive of 23a2795c, each mutant restored from a byte backup), 15:50:50-15:51:36 EDT

Each against tests.test_stub_model_probe (P15 against its ProductionRoadStaysClosed class, P16 against Bindings):
- P1 environment_changes accepts any difference: "FAILED (failures=3, errors=1)";
- P2 HTTPS_PROXY kept in the CLI's environment: "FAILED (failures=5, errors=4)";
- P3 the network made without `--internal`: "FAILED (failures=2)";
- P4 `--pull=never` dropped from the take's create: "FAILED (failures=1)";
- P5 no snapshot retained: "FAILED (failures=2)";
- P6 every process run without `-r` (first=True): "FAILED (failures=2)";
- P7 check_model dropped: "FAILED (failures=1)";
- P8 a held stub does not stop the scenario: "FAILED (failures=1)";
- P9 the probe's hold carries the walk's commit identity: "FAILED (failures=1)";
- P10 fetch-probe skips the manifest: "FAILED (failures=1)";
- P11 fetch-probe skips the scan: "FAILED (failures=1)";
- P12 a link member admitted: "FAILED (errors=1)";
- P13 a member outside the folder admitted: "FAILED (failures=1)";
- P14 the factoring changes run_command (`set -e` dropped): "FAILED (failures=1)";
- P15 run_take stops refusing GOOGLE_GEMINI_BASE_URL (dropped from GEMINI_PACKAGE_SWEEP_REFUSED): "FAILED (failures=1)";
- P16 drive.py imports the probe: "FAILED (failures=1)".

## Stage 3: the b27 cutter and the reader harness

Built:
- tests/fixtures/b27-stub/cut_structure.py (ruling 3): extends lane vendor-b26's cutter, loaded by path and not edited (its JOBS stay hard-coded); this one takes a fetched probe folder and one scenario and cuts every snapshot and stream of it, with PROVENANCE.json (each source's sha256 and the probe manifest's).
  Two rules on top of B26's: formatTruncatedToolOutput's wrapper (:254171-254185, read in stage 1) with its three numbers kept around a synthetic head, tail and path; the `<state_snapshot>` wrapper kept around a synthetic body; and the acknowledgement "Got it. Thanks for the additional context!" (:337261) verbatim.
  Run by hand only; there are no probe records yet, so no fixture is cut in this lane.
- box/stub_model_reading.py (ruling 2's evidence, readers unchanged): loads gemini_session_replay and native_reader_registration from `--code` (a study folder; the design says a `git archive` of the reviewed B26 head), and per scenario prints one line: each snapshot's replay verdict (PASS with its properties, or the refusal reason) marked "as predicted" or "DIFFERS" against scenario.json's `expect`, the history join (gemini_history: the byte-prefix invariant and session_history_facts), the outcome (admitted only when the last snapshot passes and the history joins), and where the stub log puts the first masked, truncated and snapshot-carrying requests, the helper requests and any refused request, each placed in its CLI process by probe.json's process times; `--json` prints the whole record.
- tests/test_b27_reading.py: 12 tests on synthetic probe folders built from lane vendor-b26's committed w-g47 structure fixtures (the masking re-record the reader admits) plus a third snapshot recording a retired id again (the shape the reader refuses by name), and on a synthetic C1 folder for the cutter.

### Runs (`date` at each step)

- Green, 15:54:05-15:54:07: "Ran 11 tests", "OK"; with the wrong-reason witness added, 15:54:33-15:54:35: "Ran 12 tests", "OK".
- Red, 15:54:35-15:54:36: over a `git archive` of 23a2795c with the new test laid over: "Ran 1 test", "FAILED (errors=1)"; with the cutter laid over too: the same (the harness module is absent).
- Gate before the commit: test_freeze_shapes 9 OK (15:55:09-15:55:30), with the three new files claimed in COPIED.d/vendor-admission.json.

### Stage 3 mutation check (scratch archive of 795fd7f5, each mutant restored from a byte backup), 15:55:47-15:56:07 EDT

Each against tests.test_b27_reading:
- R1 a refusal for any reason counts as predicted: "FAILED (failures=1)";
- R2 "admitted" whatever the last snapshot says: "FAILED (failures=1)";
- R3 the history join skipped: "FAILED (failures=1)";
- R4 the stub log not placed in its processes: "FAILED (failures=2)";
- R5 a PASS prediction marked met whatever the verdict: "FAILED (failures=1)";
- C1 the cutter's truncation rule dropped: "FAILED (failures=1)";
- C2 the acknowledgement made synthetic: "FAILED (failures=1)";
- C3 the state-snapshot wrapper dropped: "FAILED (failures=1)";
- C4 the truncation head kept raw: "FAILED (failures=2)".

## Stage 4: the whole lane, the smoke-run plan for athena, and the open questions

### What the lane holds (commits on lane/vendor-b27-20261021, base 04c4e774)

- 94bf7966 stage 1: lane-reports/vendor-b27-DESIGN.md (byte copy, sha256 28b9d627…a39360 both sides), this lane file, box/stub_model_server.py, box/stub_model_scenarios/ (make_scenarios.py and A1 to C2 .json), tests/test_stub_model_server.py (25).
- 23a2795c stage 2: box/stub_model_probe.py, box/walk_launch.py (probe, fetch-probe, the factoring), tests/test_stub_model_probe.py (30).
- 795fd7f5 stage 3: tests/fixtures/b27-stub/cut_structure.py, box/stub_model_reading.py, tests/test_b27_reading.py (12).
- This commit: this section.
- COPIED.d: 15 "new" entries appended to vendor-admission.json (no line moved), and one sentence added to walk_launch.py's reason in live-box-2026-10-14.json.
- No reader, record, register, lock, pinned constant or production take path changed; run_take.py and drive.py are untouched (`git diff 04c4e774 --stat` names only the files above).
- B26's fold: glitch-f1 has not sent its final head in this session, so nothing is merged; the lane depends on no fold change.

Red and green: every stage's tests were red on the archive of the stage before (stage 1 and 3: module absent; stage 2: also with the probe laid over the base walk_launch, every walk_launch probe test red) and green on the lane tree; 32 mutants across the three stages each turned their module red.
The Mac dry run of the real script (15:56:19, `python3.12 -I -B box/stub_model_probe.py ... --scenarios all --dry-run`, rc 0, 119 lines, session scratchpad b27-dryrun.jsonl): every scenario's argv, A1's network `docker network create --internal n…`, the take `docker create --pull=never --network <id> --user 10003:10003 --cap-drop ALL ...` with the take-g lock's image id, process 2 ending `-r dry-run-session-0000`, and the process environment exactly PATH, HOME (<run tree>/.home), LANG, TMPDIR/TMP/TEMP, GEMINI_CLI_HOME (/opt/cfg), GEMINI_API_KEY (the dummy) and GOOGLE_GEMINI_BASE_URL, no HTTPS_PROXY.

### The smoke-run plan for athena (what glitch-f1 runs, in order)

Preconditions: this lane reviewed by a fresh reviewer (opus-medium) and its findings folded; B26's fold merged in (`git merge`, never a rebase) if its head is final by then; athena free of any battery (the design's order: the B26 battery, the M2 fold and Javier's acceptance sitting first); one run per gap, never beside a battery.
If the auto-mode classifier refuses a new launcher command, only Javier can add an allow rule (design section 4); the operator stops and asks, never rewords or re-routes.

1. Mac: `python3 evals/gap-study-4/box/walk_launch.py ship --repo /Users/javrodher/aegis-builds/vendor-b27-20261021 --ref lane/vendor-b27-20261021 --suite <athena_suite.py> --reserve <athena-reserve> --gitleaks <binary> --work <new Mac folder>`; it prints the child and the head.
2. Mac: `python3 evals/gap-study-4/box/walk_launch.py probe --child <child> --probe smoke1 --scenarios A1 --image sha256:d10aa00b5958b00d1c719be1f0572967c04f30bfe381a427107c9e9a3f16b013 --reason "B27 smoke run, A1 only"` (the image is box/gemini/image.lock's image_id); it prints the pid.
3. Mac: `walk_launch.py status --child <child>` until `exit=0` (about 15 minutes at most by the design; A1 is three short processes).
4. Mac: `walk_launch.py fetch-probe --child <child> --probe smoke1 --out <Mac folder>/stub-probe-smoke1 --gitleaks <binary> --work <new Mac folder>`.
5. Mac, light: `python3 -I -B evals/gap-study-4/box/stub_model_reading.py <Mac folder>/stub-probe-smoke1 --code <git archive of the reviewed B26 head>/evals/gap-study-4`.

Expected from the smoke run (the design's section 3, A1):
- summary.json: no failure; A1's probe.json: cli_version 0.64.0, environment changes exactly {added GOOGLE_GEMINI_BASE_URL, removed HTTPS_PROXY, replaced GEMINI_API_KEY}, three processes with exit 0, three snapshots retained, leaked_after_teardown [], network_left "", scratch_removed true.
- The reading line: `A1: refused: a retired native message id is recorded again ... | snapshots: 1 PASS {history_rewrites 1, tool_outputs_masked > 0, ...} [as predicted]; 2 refused: a retired native message id is recorded again ... [as predicted]; 3 refused: (the same) [as predicted] | history: refused | stub: masked request <n> (process 1)`, with the first masked request about request 8 (the request after the seventh read; section 3's arithmetic), no helper request, no refused request.
- What the smoke run decides: whether every request the CLI makes is scripted (a held stub names the request and why: then the script is corrected with the reason recorded here and the smoke run repeated under a new probe id), where masking really falls, and whether the stub's assumptions hold (below).

Then, in the next gap: `probe --probe full1 --scenarios all`, then fetch-probe and the reading as above.
Expected lines (scenario.json `expect`, the design's predictions): A1 [PASS, retired id, retired id]; A2 [PASS, PASS, the resume after a history re-record]; A3 [PASS, PASS, the same]; B1 [PASS, native chat compression (the context turn survives a re-record), the same]; B2 [PASS, the resume after a history re-record, the same]; C1 [PASS, neither one of its originals nor masked (content truncation), the same]; C2 [PASS, PASS (shape A with zero masked parts)]; A1-fake as A1, with zero stub requests (the fake road bypasses HTTP).
After that, the reading step of the design's section 5: the manifest check (fetch-probe already did it), B26's structure tools (allpatch.py, classify.py, detail.py) over every $patch, the stub's request log beside them, the cutter for any fixture, then glitch-f1's ruling per road under ruling 2.

### Open questions (the design's "not checked" items, and what this lane added)

1. Ruling 1's "teardown": the probe uses run_take._teardown_partial, because run_take.teardown needs the proxy and the sidecar ruling 1 excludes (stage 2); glitch-f1 to confirm.
2. walk_launch's probe reuses the walk's process files in the child (walk.pid, walk.log, walk.exit), so `status` reads it unchanged; one probe or walk per child.
3. The stub's files sit in the run tree's `.stub-probe/` (the design's placement), so the CLI's workspace context will list that folder and the synthetic files; content only, no structure, but it is a difference from a walk's run tree.
4. Unverified until the smoke run (the stub fails loudly on each): that the real API's call-id form is what the CLI records (the stub sends `call_<n>`, the CLI prefixes `read_file__`, :333878-333880); that a `-p` line arrives as one text part equal to the line (the user_text match); that read_file accepts the absolute paths the scripts name; that no unscripted helper call happens (next-speaker check off by default, the LLM loop check after 30 requests, no countTokens under the API key); that masking falls where section 3's arithmetic puts it (A1 about request 8; A3 at process 2's first request; C1 not at all before the truncation).
5. The design's R10: a system-wide settings file in the take-g image was never read; the probe records `gemini --version` and the smoke run shows the thresholds through where masking falls.
6. The `--daemon` start inside `docker exec` (fork, setsid, the three standard streams on /dev/null) is expected to return at once, as stub_take.py's background-writer did on 14 Oct; seen only at the smoke run.
7. Ruling 2's B1-versus-B2 comparison: in B2 the B26 reader refuses snapshot 2 at the resume after the masking re-record, before the compression re-record is reached, so "B2 shows the same shape as B1" must be read from the records with the structure tools and the stub log (where the two helper requests fall, the survivors' structure), not from the reader's verdict line.
8. The A1-fake records use a fixed promptTokenCount of 1000 where the stub would compute one, and the fake road bypasses the SDK and ModelMappingContentGenerator (the design's R9); the comparison is of record structure, ids and timestamps aside.
9. The predictions for A2's and A3's second snapshots (PASS) and B2's refusal reason are my reading of B26's replay order, not run.
10. Not run on the Mac (each past the light cap, a heavy slot refused at 15:47:22): test_walk_launch's test_l8_blobs, TestWitnesses, TestOD57ReturnRoad and TestRealReturnScan, and the whole suite; athena's battery after review covers them.
11. Machine discipline, reported in stage 1: one 14:47-14:51 batch ran beside a `light-ok` that returned 1; two single-file greps at about 15:41 ran without a gate.

## Stop for review: Wed 21 Oct 2026

## glitch-f1's rulings on the stage-4 questions (as received, 21 Oct 2026, word for word)

(1) Teardown: accepted. run_take._teardown_partial (the take container, then the network, by recorded id), confirmed by leaked() and a network listing, is the right teardown for a probe with no proxy or sidecar.
(2) One probe or walk per child: accepted. Name it in the smoke-run plan.
(3) The stub in the run tree's .stub-probe/: accepted as a content-only difference. The reading must name it as a difference from a walk's workspace.
(4) B1 against B2 is read from the structure tools and the stub log, not the verdict line: accepted.
(5)-(8): as you recorded. The heavy test_walk_launch parts go to the athena battery on your head.

Carried into the plan above, by this append (the plan's text is not rewritten):
- Ruling 2: the smoke run and the full run each use a new athena child from their own `ship`; one probe or walk per child, never a second `probe` or `run` in a child that already ran one.
- Ruling 3: the reading of every scenario names, beside its verdict line, that the probe's workspace holds `.stub-probe/` (the stub's copy, its script, its log) and the scenario's synthetic files, a content-only difference from a walk's workspace; stub_model_reading.py does not print this itself, so the evidence note states it once per reading.
- Ruling 4: B1 against B2 is read from B26's structure tools and the stub log (where the two helper requests fall, the survivors of the compression re-record), not from the verdict line.

## The merge of B26's reviewed head (glitch-f1's word, 21 Oct 2026)

- B26's head 9e91dd34417b18dbaffa4069f45a4e1f5e298bb6 (lane/vendor-b26-20261021, closure review PASS, REVIEW-vendor-b26-9e91dd3.md), an extension of 04c4e774 (`merge-base --is-ancestor` true), fetched into this clone and merged with `git merge --no-ff` (no rebase): merge commit 76ed1c6e2df44b97646abe84b841cc1481b896e5, parents bb833b66 and 9e91dd34.
- B26's changes since 04c4e774: COPIED.d/vendor-admission.json (+5), gemini_session_replay.py, tests/test_b25_real_shapes.py, tests/test_b26_rewrites.py, tests/test_b26_scanner.py (new), lane-reports/vendor-b26-LANE.md.
- One conflict, COPIED.d/vendor-admission.json (both sides appended after the base's last entry). Resolved by taking B26's file and appending this lane's 15 entries, each taken byte for byte from this lane's head (the same claim script): 98 entries = B26's 83 + this lane's 15, B26's entries an unchanged prefix, 0 lines removed against B26's side and only additions against this lane's (B26's 5 lines before this lane's entries); no conflict marker left.
- Runs on the merge tree, one module at a time behind `light-ok` (15:59:06-15:59:43 EDT): test_stub_model_server 25 OK; test_stub_model_probe 30 OK; test_b27_reading 12 OK (the harness loads the study folder's readers, so these ran against the merged gemini_session_replay: the w-g47 masking re-record still PASS, the retired-id snapshot still refused by name); test_stub_take 19 OK; test_b26_scanner 3 OK; test_b26_rewrites 43 OK; test_b25_real_shapes 18 OK; test_gemini_session_replay 3 OK; test_gemini_projection 8 OK; test_freeze_shapes 9 OK.
- test_walk_launch as a whole under a heavy slot: refused at 15:59:57 (`mac_slot.py run --kind heavy --work gap-study-r4 --owner vendor-b27 --minutes 15`: "busy: second slot: CPU speed limit 47 is below 100", rc 3); left for athena's battery on this head, per ruling (5)-(8).
- New for the reading, from the merged replay: B26's fold names further unobserved resume shapes, each refused by its own words (UNOBSERVED_RESUME_SHAPES, the orderIds-only and no-update forms, and a resume that updates the prompt it removes). A probe resume that writes one of them will show that reason and be marked DIFFERS against the scenario's prediction; that is evidence, not a fault of the probe, and the predictions are left as the design wrote them.

## Stop: Wed 21 Oct 2026, after the merge

## Stage 5: REVIEW-vendor-b27-25ffff5 folded (PASS, six MINORs; glitch-f1's word, 21 Oct 2026)

Review: /Users/javrodher/aegis-builds/REVIEW-vendor-b27-25ffff5.md. Every code change below had its test written first and red on the unchanged code (15:13:38-15:13:47 EDT, the lane tree at 25ffff56 with only the three test files changed: test_stub_model_server "Ran 29", "FAILED (failures=3)"; test_stub_model_probe "Ran 35", "FAILED (failures=2, errors=3)"; test_b27_reading "Ran 14", "FAILED (failures=2, errors=1)").
Correction to that time: the red ran at 16:13:38-16:13:47 EDT (`date`).

1. MINOR 1 (box/stub_model_probe.py, the teardown's `finally`): leaked() and the network listing each sit in their own try, recording `{"error": ...}`, and any non-OwnershipError from the restore is recorded too, so the restore is always attempted and probe.json and ledger.json are always written. Red test: ReviewFold.test_a_failed_listing_after_teardown_still_restores_and_records, the reviewer's reproduction (a FakeBox whose `docker ps --all` exits 1 once process 3 has run): red as an error (Refused raised out of run_scenario), green after (restore called once, probe.json and ledger.json written, leaked_after_teardown an error record, scenario_problems non-empty). When the listing fails, ownership.restore itself refuses (it reads leaked() first), so the scratch is kept for a human and named; that is recorded, not hidden.
2. MINOR 2 (tests/test_stub_model_server.py): test_an_unscripted_endpoint_is_refused_even_with_the_next_entry_s_body (countTokens with entry 1's exact body) and test_a_request_matching_a_later_entry_is_refused (entry 2's request first). Both pass on the code as it was (the rules exist); their red evidence is the reviewer's surviving mutants M3b and M3c, run again in stage 6.
3. MINOR 3 (box/stub_model_probe.py main): `scenario_problems(rec)` (a failure, a stop, fewer processes than scripted, a non-zero exit, an unretained snapshot, a held stub, anything left after teardown, a failed restore, a kept scratch) is written into each probe.json and summary.json, and main returns 1 when any scenario has a problem, so `status` exit=0 means every scenario ran as scripted. Red tests: test_the_probe_exits_non_zero_when_a_scenario_fails_its_checks (failed: returned 0), test_a_clean_scenario_has_no_problem_and_a_stopped_one_has (error: no scenario_problems).
4. MINOR 4 (box/walk_launch.py): `fresh_child_guard(child)` prefixes probe_command only: `if test -e <child>/walk.pid || test -e <child>/walk.log || test -e <child>/walk.exit; then echo 'the child already ran a walk or a probe' >&2; exit 1; fi; `. Red test: test_a_child_that_already_ran_a_walk_or_a_probe_is_refused (error: no fresh_child_guard), which runs the guard in /bin/sh over a stand-in child with each file present (refused) and none (started), and checks run_command does not carry it; run_command's sha256 pin stays green.
5. MINOR 5: carried into the plan in stage 6 (no code).
6. MINOR 6: DEPARTURES gains the workspace differences (.stub-probe/ and the synthetic files; not a git checkout; no GEMINI.md), and the reading names them: stub_model_reading.py prints `workspace differences from a walk: ...` as its first line and carries `workspace_differences` in every record. Red tests: test_the_departures_name_every_workspace_difference (failed), test_every_reading_names_the_workspace_differences (error); test_one_line_per_scenario now skips that first line.
7. NIT 7 (box/stub_model_server.py): HEAD, OPTIONS and PATCH map to the stub's handler, so they are logged and hold the scenario. Red test: Server.test_every_verb_is_logged_and_holds_the_scenario (3 subtests failed: http.server's own 501), green after.
8. NIT 8 (box/stub_model_reading.py compare): a refused prediction without reason_contains is marked "DIFFERS (the prediction names no reason)". Red test: test_a_refused_prediction_without_its_reason_is_never_met (failed: "as predicted"); and test_every_refused_prediction_names_its_reason binds the committed scenarios.
9. NIT 9, recorded only: the take inspect is recorded, not compared with preflight.expected_take_inspect (run_take.launch compares it, run_take.py:1927-1930); with `--pull=never` and the image id it adds little.
10. NIT 10: carried into the plan in stage 6.
11. NIT 11, recorded only (the reviewer's inference, not tested): the `--internal` network is the production take's form with nothing else on it, so the probe's exposure is a subset of a walk's; whether a rootless internal bridge reaches the rootlesskit namespace's gateway was not checked, and it is the same for walks.

Green on the lane tree, one module at a time behind `light-ok`: test_stub_model_server 29 OK, test_stub_model_probe 35 OK, test_b27_reading 14 OK, test_stub_take 19 OK (16:15:06-16:15:16); test_b26_scanner 3 OK, test_b26_rewrites 43 OK, test_b25_real_shapes 18 OK, test_gemini_session_replay 3 OK, test_gemini_projection 8 OK, test_freeze_shapes 9 OK, test_walk_launch's test_l2_run, test_l4_bounds, test_l6_start and test_l7_env each OK (16:15:26-16:15:59).
No new file; every changed file is already claimed in COPIED.d.

### Stage 5 mutation check (scratch archive of 5e6fc97e, each mutant restored from a byte backup), 16:16:46-16:16:58 EDT

- M3b, the reviewer's surviving mutant (an unscripted endpoint no longer refused), against MINOR 2's first test: "FAILED (failures=1)" (it survived the review's suite, 25 OK).
- M3c, the reviewer's surviving mutant (skip ahead to a later matching entry), against MINOR 2's second test: "FAILED (failures=1)".
- F1 leaked() back outside its own try: ReviewFold "FAILED (errors=1)".
- F3 the probe exits 0 whatever happened: "FAILED (failures=1)".
- F3b the stop not counted in scenario_problems: survived ("OK"). Named equivalent: every stop also leaves fewer processes than scripted (and a held stub, when that is the cause), each its own problem, so the exit and the summary do not change; the clause is kept for the record's words.
- F4 the fresh-child guard admitting walk.exit: "FAILED (failures=1)"; F4b the guard dropped from probe_command: "FAILED (failures=1)".
- F6 the git-checkout difference dropped from DEPARTURES: "FAILED (failures=1)"; F6b the GEMINI.md difference dropped from the reading: "FAILED (failures=1)".
- N7 PATCH back to http.server's 501: "FAILED (failures=1)"; N8 an empty reason_contains matching any refusal: "FAILED (errors=1)".

## Stage 6: what the review fold found further, the checks.d lines, and the plan's additions

### A regression of stage 2, found by the heavy slot: three test_walk_launch witnesses could no longer be performed

- The Mac's heavy slot was granted twice.
  First at 16:17:07, for the whole tests.test_walk_launch on 5e6fc97e under an 840-second cap: 48 tests passed, then two "F", then the cap killed it at 16:31:09 (no verdict line).
  Second at 16:34:21, verbose, on 29d432ea, with a 1,700-second cap: every test outside TestWitnesses passed, 48 "ok" (TestOD57ReturnRoad, TestRealReturnScan, TestSkipRule and TestTheRoad's eleven, test_l8_blobs included). TestWitnesses (62 witnesses, each running its whole check, the L8 ones heavy) was still running when the cap killed it at 17:02:43, so it has no verdict on the Mac.
- The two "F" were TestWitnesses subtests: test_walk_launch's witness() requires each edit's text to occur exactly once in walk_launch.py, and stage 2 broke three: hold-dropped's text occurred 0 times (_held_command named its variable held_env), back-sha-unchecked's and pid-isdigit's twice each (fetch_probe and probe repeated fetch's and run's lines).
  Lane review REVIEW-vendor-b27-25ffff5 did not run test_walk_launch whole, and neither did I before stage 5; this is the cost of skipping the heavy module, recorded plainly.
- Fix, commit 29d432ea: _held_command keeps the local name walk_env, so the hold line's text is the original; fetch_probe's sha256 comparison and probe's pid check are spelled apart from fetch's and run's. No behaviour changed.
- Red: b27witness.py (session scratchpad) on 5e6fc97e: "['hold-dropped: occurs 0 times', 'back-sha-unchecked: occurs 2 times', 'pid-isdigit: occurs 2 times']"; on the base 04c4e774 archive: none. The new light test WalkLaunchProbe.test_every_walk_launch_witness_edit_still_applies_once on a 5e6fc97e archive (16:34:00): "FAILED (failures=1)" with those three.
- Green on 29d432ea (16:33:21-16:33:50): all 62 witness edits performable once; the ten L2-run, L6-start and L7-env witnesses each red on their own clause with the tree green; test_stub_model_probe 36 OK; test_walk_launch test_l2_run, test_l5_guards, test_l9_echo_and_env OK.
- TestWitnesses as a whole waits for athena's battery on this head (ruling (5)-(8)).

### checks.d (glitch-f1's word, 21 Oct 2026)

- Athena's gars-gap4 battery runs only checks.d's lines; B26's final athena battery (371/371) covered checks.d, which named none of test_b25_real_shapes, test_b26_rewrites, test_b26_scanner or this lane's modules, so those reader tests have run on the Mac and in the reviews only.
- checks.d/vendor-admission.txt gains six lines in its existing form (`python3 -B -W ignore evals/gap-study-4/tests/<module>.py`), under two comment lines naming the lanes: test_b25_real_shapes, test_b26_rewrites, test_b26_scanner; test_stub_model_server, test_stub_model_probe, test_b27_reading.
- run_checks.py's own parser (`run_checks.commands()`, through b27checks.py in the session scratchpad; the whole battery was not run), 16:44:53: 377 commands with the battery (371 + 6), the six read at vendor-admission.txt:168-170 and :173-175, in order.
- Those six lines only, exactly as written, from the repository root under `bash -o pipefail` with python3 3.13.2, 16:44:53-16:45:09: test_b25_real_shapes 18 OK; test_b26_rewrites 43 OK; test_b26_scanner 3 OK; test_stub_model_server 29 OK; test_stub_model_probe 36 OK; test_b27_reading 14 OK.
- Athena's battery on this head will run them all.

### The smoke-run plan's additions (REVIEW-vendor-b27-25ffff5 MINOR 5 and NIT 10; appended, the plan's text above is not rewritten)

- A precondition before `ship`: athena's battery on this lane's head is green, including the whole test_walk_launch (its TestWitnesses has no Mac verdict) and the six checks.d lines above.
- At step 1: the head `ship` prints must equal the reviewed head (this lane's final head after the stage-5 review, or its reviewed successor); otherwise stop before `probe`.
- At step 2: `probe` now refuses by itself in a child that already holds walk.pid, walk.log or walk.exit (MINOR 4), so a second probe or walk needs a new `ship` and child.
- At step 3: `status` exit=0 now means every scenario ran as scripted (MINOR 3); exit=1 means at least one scenario has problems, listed in summary.json and its probe.json. On a non-zero exit or `lost`, do not repeat: read walk.log's tail, then on athena `docker ps -a --no-trunc`, `docker network ls`, and /home/javier/gap4-walk-config for an `sp-*` scratch left (the restore records why).
- At step 5: the reading's `--code` is a `git archive` of B26's reviewed head 9e91dd34417b18dbaffa4069f45a4e1f5e298bb6 (its gemini_session_replay.py is byte-identical to this lane's), evals/gap-study-4.
- The evidence note of every reading names the workspace differences (ruling 3, MINOR 6): `.stub-probe/` and the synthetic files, the run tree not a git checkout, no GEMINI.md; stub_model_reading.py's first line prints them.

## Stop for review: Wed 21 Oct 2026, after stage 6

## Stage 7: athena's battery on 931f946a failed test_round4 (failures=5, errors=7 of 4843); root cause and fix (glitch-f1's word, 21 Oct 2026)

Log: /Users/javrodher/aegis-builds/athena-suites/gap4-t5-b27-931f946-931f946-20261021T211045Z/run.log (the last traceback: test_vendor_envelopes.py:355, "the masked take is held: NativeCrossCheckPending: native cross-check pending (no reviewed native-session reader for gemini)").

Root cause: box/stub_model_reading.load_readers (stage 3) deleted gemini_session_replay, native_reader_registration, vendor_provenance and gemini_projection from sys.modules and imported fresh copies.
test_round4 runs every module in one process.
drive.py binds `import native_reader_registration as _registration` when it is first imported (at discovery, by an earlier module), while test_vendor_envelopes, test_pending_walk, test_pending_codex_walk, test_vendor_admission and others import native_reader_registration lazily inside their tests and patch `production_readers` on it.
Once test_b27_reading had run (alphabetically before them), those lazy imports got the new copy, the patch missed drive's old one, and drive found no reviewed reader, so each take was held as cross-check pending.
Each module alone was green because no stale copy existed there.

- Reproduced on the Mac, light (19:30:39-19:31:12... `date` read 18:30:39-18:31:12 EDT): `unittest tests.test_stub_take tests.test_b27_reading tests.test_vendor_envelopes` (test_stub_take imports drive at load, as the battery's earlier modules do): 2 errors and 2 failures in test_vendor_envelopes, each "native cross-check pending (no reviewed native-session reader for codex|gemini)". Control without test_b27_reading (18:31:26-18:31:56): "Ran 30 tests", "OK".
- Red first (18:32:14): two new tests, tests/test_b27_reading.py Isolation: reading this study must return the already-loaded readers and leave sys.path as it was; reading another study folder (a copy of this one) must return that folder's readers and leave every sys.modules entry and sys.path exactly as before. "Ran 2 tests", "FAILED (failures=2)" (the copy's module left in sys.modules, which also broke the other test).
- Fix: load_readers returns the loaded modules when they are `--code`'s own; otherwise it sets aside every module loaded from this study or `--code`, imports the readers with `--code` first on sys.path, and then restores sys.modules and sys.path exactly (the returned modules keep their own imports). Nothing else changed.
- Green (18:32:41-18:33:15): test_b27_reading "Ran 16 tests", "OK"; the reproduction trio "Ran 46 tests", "OK".
- The whole test_round4 on the Mac under a heavy slot (granted 18:33:24, `mac_slot.py run --kind heavy --work gap-study-r4 --owner vendor-b27 --minutes 60`, 3,500-second cap): 4,094 tests "ok" before the cap killed it at 19:31:47 (no closing line). Every affected module passed in that one process: test_b27_reading 16, test_pending_codex_walk 10, test_pending_walk 23, test_vendor_admission 10, test_vendor_envelopes 11, test_vendor_walk_road 5 ok. It did not reach test_walk_launch.
  Three tests failed there, and each fails the same way alone on this Mac (19:32:42), so they are this Mac's environment, not this lane: test_run_take TestExecArgv.test_exec_argv and TestWalkLoginPlace.test_the_walk_login_place refuse because this agent session's environment holds a refused variable name (CLAUDE_CODE_MESSAGING_TOKEN, by name only; run_take reads the process's own environment), and test_config_folder C7Shapes.test_shape_rules errors because APFS refuses a non-UTF-8 file name ("[Errno 92] Illegal byte sequence"). Athena's battery does not have either condition.
- Athena's battery on the new head is the verdict.
- Correction to the reproduction line above: it ran at 18:30:39-18:31:12 EDT (`date`); the "19:30:39-19:31:12" there is a typing slip.

## Stage 8: the A1-fake cross-check gets one fake file per process (glitch-f1's B27 ruling 4, 21 Oct 2026)

The ruling's words (night log /Users/javrodher/glitch/plans/gap-study-round-4/orchestrator-night-2026-10-13-claude.md, "B27 RULINGS", item 4): "the A1-fake defect is fixed as B27 stage 8: one fake file per process, split at each process's user_text match and refused unless the split gives exactly the scenario's processes in order; red first; closure review; then A1 and A1-fake rerun together on athena."
glitch-f1's brief adds: each group non-empty.

Defect (the full run, /Users/javrodher/aegis-builds/b27-smoke-20261021/RUNLOG.md "# Full run"): A1-fake matched A1 only through process 1, because the pinned gemini-cli 0.64.0's FakeContentGenerator replays its whole --fake-responses file from response 1 in every process, and the probe passed one file to all three processes (stub_model_probe.py:264, :353, :411 at 82da1830).

- fake_groups (box/stub_model_probe.py): a boundary is a script entry whose match is `user_text`; the boundaries' texts must equal the scenario's process prompts exactly, in order, and the first entry must be a boundary; each group runs from its boundary to the next.
  Refusals, each by name: a process prompt out of order; a missing boundary (a `user_text_prefix` entry is not a boundary); an extra boundary; boundaries that are not the scenario's prompts; a record before process 1's prompt.
  check_fake_groups then refuses a group count other than the process count, an empty group, and groups that do not cover every record exactly once in order.
  Through fake_groups those three cannot fire on a split that passed the text and leading-record rules (each group holds at least its boundary; inferred from the construction); they stay as the ruling's rule written down and are tested directly.
- A1.json splits at its requests 1, 9 and 10 into groups of 8, 1 and 1; A1.json and every other scenario file are unchanged, and stub_model_server.fake_records is unchanged (the probe slices its one-per-entry output).
- Each process k gets `.stub-probe/fake-responses-<k>.jsonl`; process k's argv (dry run and run) ends `--fake-responses <run tree>/.stub-probe/fake-responses-<k>.jsonl`; the output folder <out>/A1-fake carries every per-process file (so the manifest and fetch-probe carry them); the single fake-responses.jsonl is gone.
- check_fake runs in main before the dry run or the run, and at the head of dry_run, so a bad split refuses before any runtime call.

Red first, on 82da1830 with only the test file changed (21:25:07-21:25:10 EDT, `date`): test_stub_model_probe "Ran 47 tests", "FAILED (failures=3, errors=10)": 8 errors "has no attribute 'fake_groups'", 2 "has no attribute 'check_fake_groups'", the dry run's process-1 argv "fake-responses.jsonl != fake-responses-1.jsonl", the run path's argv likewise, and "ProbeRefused not raised" for a bad split.
Green (21:25:52-21:25:55): "Ran 47 tests", "OK".
Mutants, each against the new tests, the file restored from a byte backup after each (cmp clean): the leading-record check dropped, the empty-group check dropped, the coverage check dropped, the text check loosened to a count, the run path naming process 1's file for every process, the dry run's up-front check dropped: each "FAILED".
Mac, light-ok (21:26:41-21:26:56): test_stub_model_server 29 OK; test_stub_model_probe 47 OK; test_b27_reading 16 OK; the single-process hazard check, `unittest tests.test_stub_agents tests.test_stub_model_probe tests.test_stub_take` in one process from evals/gap-study-4: "Ran 84 tests", "OK".
Next, not this lane agent's: a closure review, then A1 and A1-fake rerun together on athena.

## Closure-review fold (REVIEW-vendor-b27-49c350a MINOR 1, NITs 1-3), made in lane vendor-b28 after the merge of 49c350a9 (glitch-f1's ruling O2, 21 Oct 2026)

Ruling O2's words (night log, "B27 DECISION", Wed 21 Oct 21:48 EDT): "B27's code merges with the batch (stage 8 passed its closure), its MINOR 1 and NITs 1-3 folded on the b28 branch right after the merge, recorded in B27's lane file".
Where: /Users/javrodher/aegis-builds/vendor-b28-20261021, branch lane/vendor-b28, merge commit ae63e925 (B27's 49c350a9b008e3ea15f83f3873fe62b3766722fe onto 5457e75e by exact SHA; `git diff --stat` of the merge against 5457e75e equals 9e91dd34..49c350a9's, compared with diff).

- MINOR 1 (main's check_fake bound by no test): tests/test_stub_model_probe.py B27ClosureFold.test_main_refuses_a_bad_split_before_the_run and ...before_the_dry_run call smp.main with load_scenario patched to an out-of-order script, run_probe, check_output or dry_run patched to fail if reached, and assert ProbeRefused with nothing written under the scratch folder.
- NIT 1 (a refused split in run_scenario left <out>/A1-fake and an sp-* folder): run_scenario takes the fake split (fake_groups of A1's unmaterialised script; materialise only fills ${RUN_TREE}, so the indices are the same) before os.mkdir(out); B27ClosureFold.test_a_refused_split_in_run_scenario_leaves_nothing_behind.
- NIT 2 (the prefix-boundary test red under m2 only by a KeyError): B27ClosureFold.test_a_prefix_match_with_a_decoy_text_is_still_not_a_boundary gives the prefix entry a decoy `text` equal to the missing prompt, so a rule that counts prefix matches as boundaries fails by assertion; the original test stays.
- NIT 3: the defect's line numbers in stage 8 above (":264, :353, :411") are lines of box/stub_model_probe.py at 82da1830, not at 49c350a9 or later.

Red, a `git archive` of ae63e925 with only the new test file laid over (21:52:46-21:52:50 EDT, `date`): "Ran 51 tests", "FAILED (failures=1)": the NIT 1 test, "Tuples differ: (['sp-9un90gld'], ['A1-fake']) != ([], [])". (Two earlier tries at 21:52:21 and 21:52:34 went red by an incidental KeyError 'road' and a ScriptError from fake_records; the test's script gained "road" and "expect" and fake_records is patched, so the red is the assertion.)
The MINOR 1 tests pass on ae63e925, as they must (main's check is there); their witness is mutant m9.
Green, lane tree (21:53:02-21:53:07): "Ran 51 tests", "OK".
Mutants on a scratch copy, restored from a byte backup and checked with cmp after each: m9 (main's check_fake removed) "FAILED (failures=2)", the two MINOR 1 tests; m2 (prefix matches counted as boundaries) "FAILED (failures=1, errors=1)", the decoy test by "ProbeRefused not raised" and the original by KeyError 'text'; the NIT 1 change reverted (split after mkdir) "FAILED (failures=1)".
Single-process hazard check (21:53:27-21:53:37): `unittest tests.test_stub_agents tests.test_stub_model_probe tests.test_stub_take` in one process: "Ran 88 tests", "OK".
