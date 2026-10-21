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
