# Design: vendor-b27, the stub-model observation road for the three refused Gemini history-rewrite roads (Gap Study round 4)

Design only, append-only after this version.
Designer: an Opus 5.5 sub-agent of glitch-f1 (Lane-orchestrator), on the Mac, under Javier's standing delegation.
Written Wed 21 Oct 2026 from 14:40 EDT (`date`).
Nothing was run on athena, nothing was spent, pushed or committed, and no code or record was changed.
The pinned package was never executed; every Mac step was light work, each batch behind `mac_slot.py light-ok --work gap-study-r4` (exit 0 at 14:30 and 14:35 EDT; one check at about 14:35 returned exit 1 and I waited until it passed).

## Verdict in six lines

1. Question 1 is yes: the pinned CLI can be pointed at a local endpoint with no code edit, through the environment variable GOOGLE_GEMINI_BASE_URL, which the CLI reads for the API-key login (:312898-312911) and the bundled SDK reads too (:272775, :257932-257943).
2. The road keeps the study's own settings file and login type and changes only three environment values: the base URL, a dummy API key, and no proxy.
3. No threshold needs lowering for any of the three roads: masking is triggered by the client's own size estimate of real tool output (:344697), and compression and truncation are triggered by the server-reported promptTokenCount (:334025-334027, :337137-337143), which the stub controls.
4. The production take road cannot carry it, because run_take refuses GOOGLE_GEMINI_BASE_URL for every arm (box/run_take.py:519 in the B26 clone); it needs a new box measurement module, built like the CP2 stub take (box/stub_take.py), on athena's walk box with an internal network and the locked take-g image.
5. Nothing needs Javier: no login, key, sudo, spend or deploy; one possible exception is an allow rule for a new launcher path if the auto-mode classifier refuses it.
6. Estimate: about 10 to 14 builder hours of Mac work (light, testable on fakes, can start now) plus under one hour of athena time in one or two gaps after the B26 battery, the M2 fold and Javier's acceptance sitting; then a review and a reader follow-up lane before the freeze.

## Sources and evidence

- The pinned package: /Users/javrodher/aegis-builds/glitch-26-carry-20261021/b26/pkg-dl/gemini-cli-0.64.0.tgz, sha256 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6 (`shasum -a 256`, read 14:31 EDT), extracted with `tar -x` only into a new empty folder of my own, /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/b27pkg.
- bundle/chunk-NR7L3FXV.js: sha256 d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c, 401531 lines; every bare `:<n>` below is a line of it.
- bundle/gemini-Q2GRYIAK.js: sha256 7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da, 17934 lines, the runner bundle/gemini.js:110 imports; cited as Q2G:<n>.
- The study code, read only, never written: /Users/javrodher/aegis-builds/vendor-b26-20261021 at 04c4e774 (box/run_take.py, box/take_config.py, box/stub_take.py, box/walk_launch.py, box/gemini/Dockerfile and image.lock, gemini_adapter.py, native_snapshot.py, tests/fixtures/b26-rewrites/cut_structure.py, lane-reports/vendor-b26-DESIGN.md and vendor-b26-LANE.md).
- The planning note: /Users/javrodher/glitch/plans/gap-study-round-4/rehearsal-walk-resume-after-mask-2026-10-21.md.
- One structure read of a committed walk (scratch copy of w-g14 native-turn-1, keys and tool-call id format only, never model text) for the record shapes the stub must reproduce.

## 1. Can the CLI be pointed at a local endpoint without editing its code? Yes

### The CLI's own base-URL road

- The non-interactive runner validates the login and then calls `config.refreshAuth(authType)` with no base URL (Q2G:16846-16865 validateNonInteractiveAuth; the call at Q2G:17786-17792).
- refreshAuth passes that undefined base URL to createContentGeneratorConfig and createContentGenerator (:381125-381137).
- For the API-key login (USE_GEMINI, "gemini-api-key", :312750) createContentGeneratorConfig takes the key from GEMINI_API_KEY and returns (:312802-312811).
- createContentGenerator then, for USE_GEMINI, USE_VERTEX_AI or GATEWAY (:312866), sets `baseUrl = process.env["GOOGLE_GEMINI_BASE_URL"]` when no base URL was passed and the login is not Vertex, checks it with `new URL(...)` (validateBaseUrl, :312775-312781), and puts it in the SDK's httpOptions (:312896-312911).
- The SDK client is otherwise built exactly as for the walks: the same GoogleGenAI constructor, the same headers, the same ModelMappingContentGenerator and LoggingContentGenerator wrappers (:312912-312941).
- The bundled SDK reads the same variable as its own default when httpOptions carry no base URL (:272775 calling getBaseUrl, :257932-257943), so both layers agree.
- The SDK builds the request URL as `<baseUrl>/<apiVersion>/models/<model>:streamGenerateContent?alt=sse` for the chat and `...:generateContent` for helper calls (getRequestUrlInternal :267524-267534, constructUrl :267554-267564, paths :269099 and :269036).
- A plain `http://127.0.0.1:<port>` passes validateBaseUrl and the SDK; no TLS is needed.

### The login type stays the walks' login type

- With GOOGLE_GEMINI_BASE_URL set, getAuthTypeFromEnv would pick GATEWAY (:312763-312765), but validateNonInteractiveAuth uses the configured type first (`configuredAuthType || getAuthTypeFromEnv()`, Q2G:16848).
- The study's settings set `security.auth.selectedType` = "gemini-api-key" (box/take_config.py, GEMINI_AUTH_SETTING), so the probe runs as USE_GEMINI exactly as every walk did; the base URL is the only change in the generator.
- The model-resolution branch keys on the login type (:312834), so it is unchanged too.

### No remote flags, as in the walks

- Under the API-key login there is no Code Assist server (getCodeAssistServer :312485-312499), so getExperiments returns no flags (:366237-366262), as the planning note found.
- So the masking thresholds come from settings or the defaults (getToolOutputMaskingConfig :381905-381917) and the compression threshold from settings, else the default 0.5 (getCompressionThreshold :382401-382410, default :336882 applied at :337138).

### A second road, named for the cross-check only

- The pinned CLI has hidden testing flags `--fake-responses <file>`, `--fake-responses-non-strict <file>` and `--record-responses <file>` (Q2G:8205-8216, wired at Q2G:8642-8644 and :380953-380955).
- With `--fake-responses`, createContentGenerator returns a FakeContentGenerator over the file, wrapped only in LoggingContentGenerator (:312825-312832; the class :312557-312623).
- That bypasses the SDK's HTTP and SSE parsing and the ModelMappingContentGenerator, so it is a weaker copy of the walks' path than the base-URL road; I use it only as an independent cross-check of one scenario (section 7, risk R9).

## 2. The smallest stub server the CLI accepts

### Endpoints

- `POST /v1beta/models/<model>:streamGenerateContent?alt=sse`: the main chat, every request of every turn (the SDK's stream road; processStreamResponse :267676-267735).
- `POST /v1beta/models/<model>:generateContent`: the helper calls (BaseLlmClient), here the compression summary and its verification (:337194-337238); also any JSON helper the smoke run shows.
- Anything else: HTTP 400 with a Google error body (`{"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "stub: unscripted request"}}`), which the SDK raises as an ApiError (:267693-267707), so an unscripted call fails the process loudly instead of being guessed; 400 rather than 5xx so the CLI's retry loop does not spin.
- The stub listens on 127.0.0.1 only, inside the take container, and is Python 3 standard library only (http.server), because the take-g image already carries python3 3.11.2 (box/gemini/Dockerfile, image.lock `python`).

### The SSE framing the SDK accepts

- Each chunk is written as `data: <one-line JSON>\r\n\r\n`; the SDK matches `/^\s*data: (.*)(?:\n\n|\r\r|\r\n\r\n)/` (:267445) and parses each match as one GenerateContentResponse.
- The body must end with no partial segment, or the SDK throws "Incomplete JSON segment at the end" (:267688-267691).
- Content-Type `text/event-stream`, HTTP/1.1 with `Connection: close` (one response per connection keeps the server single-threaded and simple).

### The response fields the CLI reads (GeminiChat.processStreamResponse, :333847-334041)

- `candidates[0].content.parts`: text parts, thought parts (`thought: true`), and `functionCall` parts; `candidates[].finishReason` ("STOP").
- A response with no tool call must carry a finishReason and non-empty text, or the CLI raises InvalidStreamError (:333990-334020).
- functionCall `{id, name, args}`: the real API gives ids of the form `call_<digits>` (the committed w-g14 snapshot holds `read_file__call_1039466`, the CLI adding `<name>__` at :333872-333876), so the stub issues `call_<n>` ids from its own counter.
- Thought parts with a `**Subject**` line and a short body, so the recorder writes `thoughts` entries {subject, description, timestamp} as in the walks (recordThought, :334021-334023).
- `usageMetadata` on the last chunk: promptTokenCount, candidatesTokenCount, cachedContentTokenCount, thoughtsTokenCount, toolUsePromptTokenCount, totalTokenCount, the six the walks' `tokens` records carry as {input, output, cached, thoughts, tool, total} (recordMessageTokens, :334024).
- promptTokenCount is load-bearing: the CLI sets `lastPromptTokenCount = usageMetadata.promptTokenCount` (:334025-334027), which the compression trigger (:337135-337143), the overflow check (:348250-348258) and the shell truncation threshold (:382685-382690) read.
- The `model` the recorder writes is the CLI's own requested model, never a response field (recordMessage with `model`, :334030-334036), so the stub cannot alter it.

### The non-streaming helper responses

- Compression summary and verification: `{"candidates": [{"content": {"role": "model", "parts": [{"text": "<state_snapshot>...</state_snapshot>"}]}, "finishReason": "STOP"}], "usageMetadata": {...}}`.
- The stub recognises them by the fixed last user text of each request: "Generate a new <state_snapshot> based on the provided history." or the "A previous <state_snapshot> exists" variant (:337192-337193), and "Critically evaluate the <state_snapshot> you just generated." (:337228).
- The next-speaker check is off by default (`skipNextSpeakerCheck ?? true`, :380928; the call site :348370-348381), and the LLM loop check starts only after 30 requests in one prompt (:343862), so neither is scripted; if the smoke run shows either, the stub fails it (above) and the script is extended with a recorded reason.

### Scripting

- One scenario file per scenario: an ordered list of expected requests, each with a match rule (endpoint; the last content's role and kind: a user prompt with an exact text, or a functionResponse turn naming the expected call ids; or a compression request by its fixed text) and the response to send (parts, finishReason, the usage numbers).
- One stub process per scenario, alive across all of the scenario's CLI processes, keeps a global request counter; a request that does not match the next expected entry gets the 400 above and the scenario ends held, with the mismatch logged.
- Tool calls whose real execution yields large outputs: `read_file` on synthetic files the probe writes into the run tree before the first process (2,000 lines of about 30 characters, about 62,000 characters each).
- read_file is chosen over the shell tool because only the shell tool (and MCP tools) are cut at execution time to the 40,000-character threshold (truncateOutputIfNeeded, :348856-348880, keyed on SHELL_TOOL_NAME), while read_file stops at 2,000 lines of at most 2,000 characters (:253707-253708); read_file was also the most frequent tool in the committed masking walks.
- Every call names a distinct file and every text answer is distinct, so the client-side loop detector, which keys on repeated identical calls and text, stays quiet (processTurn's loop check, :348275-348285).
- The usage numbers the stub reports are computed from the request it received (its JSON length divided by four, the CLI's own estimate rule, :312103 and :312059), except where a scenario names an inflated promptTokenCount.
- The stub writes a request log: per request, the endpoint, the model in the URL, the matched script entry, the sha256 of the body, and the body itself (synthetic: the CLI's system prompt, the synthetic run tree's context, synthetic file text and the stub's own words).
- The request bodies are evidence on their own: they show what the model was shown after each re-record and each resume (for example whether a "/"-leading prompt or the first operator line is gone, F-B26-7).

## 3. The three roads: scripted sequences, thresholds, expected records

All scenarios use the study's own settings file, written by take_config.write for gemini-3.8-flash (its config_sha256 recorded), the study's own argv from gemini_adapter.argv (`gemini -p <line> -o stream-json -m <model> --approval-mode yolo`, then `-r <session id>` from turn 1's init on every later process), and the CLI's default thresholds.
Each "process" below is one `gemini` exec, the unit the driver makes per operator step; after each, the probe retains the native session file with native_snapshot's own locate and retain rules (session/native-turn-<n>.jsonl) and the stdout as turn-<n>.jsonl.

### Threshold arithmetic at the defaults (why nothing is lowered)

- Masking: protection 50,000 and minimum prunable 30,000 estimated tokens, protect latest turn on (:344660-344662, wired :380885-380889), the scan starting at the second-to-last history turn (:344682), each part estimated as JSON length / 4 (:344697 via :312095-312121).
- A 62,000-character read_file result is about 15,500 estimated tokens, so masking fires at the first request whose history, minus its latest turn, holds about six such results (four to pass protection, two more to reach 30,000 prunable).
- Compression: fires when `lastPromptTokenCount >= 0.5 × tokenLimit(model)` (:337135-337143), tokenLimit 1,048,576 for every model name here (:334569-334585), so a reported promptTokenCount of 600,000 (over 524,288) fires it; nothing about the history needs to be that large.
- The overflow check stays clear at 600,000: it compares only the new request's own parts with 1,048,576 minus 600,000 (:348250-348258).
- The shell-truncation threshold stays 40,000 at that count: min(4 × (1,048,576 − 600,000), 40,000) (:382685-382690; default :380446).
- Lowering is a named fallback only, if a smoke run shows the arithmetic off: `contextManagement.tools.outputMasking.protectionThresholdTokens`, `.minPrunableThresholdTokens` (:380885-380889) or `model.compressionThreshold` (:382402-382403).
  The record-writing path is the same at any value: mask() reads the numbers from getToolOutputMaskingConfig and then always ends in the same `setHistory(result.newHistory)` (:344724-344726, :348592-348597), and compress() uses the threshold only in its trigger comparison (:337138-337139).
  The study's runs set no `contextManagement` key (the planning note; take_config's GEMINI_SETTINGS), so a lowered value would be a named departure in the probe's record, never silent.

### Road (a): a resume after a masking re-record

Scenario A1 (the plain case):
1. Process 1, prompt "Read the files r01.txt to r08.txt one by one." : the stub answers seven read_file calls in turn (r01 to r07), each with usage computed from the request.
   Masking falls before about the seventh request: tryMaskToolOutputs (:348251, :348592-348597) re-records the whole history as synthetic messages (setHistory :333750-333762; recordSyntheticMessage :286934-286941) and the recorder writes `$patch {removeIds, updates}` (:287151-287298, write at :287265), B26's shape A.
   The stub's log confirms it independently: the first request whose body carries `<tool_output_masked>` (:344663, :344871-344877).
   The stub then answers a final text; the process exits 0.
2. Process 2, `-r <session id>`, prompt "Summarise what you read.": one text answer.
   Expected records, from source (B26 design, "Named, not admitted" item 1): `$set {sessionId}`; a user message whose id is deriveStableId(["environment-context"]) recorded again, because getInitialChatHistory finds a first turn that is not the context id and prepends a fresh one (:336356-336377) and the recorder appends an unknown id (:287189-287196); a `$patch {orderIds, removeIds, updates}` whose removeIds holds the first re-recorded user message (context and prompt coalesced, its text starting "<session_context>", dropped by convertSessionToClientHistory, :286096-286110); then the new prompt and answer.
   The B26 reader's expected verdict: refused, "a retired native message id is recorded again (the resume after a history re-record ...)" (gemini_session_replay.py:425-427 at 04c4e774).
3. Process 3, `-r` again, prompt "Thanks.": one text answer, to see whether a second resume after the road is stable (the context id is now first, so getInitialChatHistory should return the history unchanged, :336359-336363).

Scenario A2 (the conditional-yes variant, F-B26-7): process 1 small (one read of a short file, a text answer); process 2's prompt starts with "/" and carries the seven heavy reads, so masking falls inside process 2 and the "/" prompt is inside the re-recorded run; process 3 resumes.
Expected: the process-3 resume removes two re-recorded user messages, the context copy and the "/" copy (:286096-286110), the case the planning note named.

Scenario A3 (the w-g47 pattern, now with a boundary after it): process 1 runs five heavy reads (under the masking line), process 2 resumes, and the resume's re-added `_response` turns (:286158-286188) push the history over, so masking falls at process 2's first request; process 3 resumes after it.

### Road (b): true chat compression

Scenario B1:
1. Process 1: prompt, two small read_file calls, a final text, usage computed (far under 524,288).
2. Process 2, `-r`: response 1 is one small read_file call whose usage names promptTokenCount 600,000.
   At request 2, processTurn calls tryCompressChat before masking (:348245-348251), context management being off by default (:380870, the branch :348224-348243).
   compress() finds the split at process 2's prompt, the last plain user turn (findCompressSplitPoint :337012-337035, fraction 0.7 from COMPRESSION_PRESERVE_THRESHOLD :337010), sends the summary and verification requests (:337194-337238), which the stub answers with a short `<state_snapshot>` text, estimates the new history far under 600,000 (calculateRequestTokenCount, estimate only when no media, :312124-312144) and returns COMPRESSED (:337283-337292).
   tryCompressChat starts a new chat over [summary, "Got it. Thanks for the additional context!", kept tail] with the session's recording data (:348568-348580; startChat :348055-348077 runs getInitialChatHistory, so the context turn keeps its stable id, :336358-336363).
   The stub's later responses report computed usage again; the process ends on a text.
   Expected record, from source: a `$patch` whose survivors are the context turn under its stable id plus the fresh run (summary user message, the acknowledgement, the kept tail), B26's named "native chat compression: source-derived, unobserved".
   A process 2 with a single prompt and no earlier plain user turn would not compress: the split point would be 0 and compress() returns NOOP (:337176-337187, :337024-337034), which is why the compression scenarios run in a resumed process, as every driver turn after the first is.
3. Process 3, `-r`: a resume after compression (also unobserved), one text answer.

Scenario B2 (the realistic interleave): A1's process 1 (a masking re-record), then process 2 as in B1, so a compression follows a masking re-record and a resume, the order a long real take would meet.

### Road (c): content truncation after a failed compression

Scenario C1:
1. Process 1: prompt, one small read, a final text.
2. Process 2, `-r`: responses 1 to 4 are read_file calls on four 62,000-character files; response 4's usage names promptTokenCount 600,000.
   Request 5: compress() fires; the stub answers the summary and the verification with a single `<state_snapshot>` text of about 2.6 million characters, so the new history's estimate (over 650,000) exceeds 600,000 and compress() returns COMPRESSION_FAILED_INFLATED_TOKEN_COUNT (:337271-337282); tryCompressChat sets hasFailedCompressionAttempt (:348566-348567).
   That is the only status that sets the flag: an empty summary returns COMPRESSION_FAILED_EMPTY_SUMMARY without it (:337243-337255), which is why the stub inflates the summary rather than emptying it.
   The flag lives in the GeminiClient object and is reset by startChat (:348057), so the failure and the truncation must fall inside one process.
   Masking at request 5 sees three heavy results under its 50,000 protection, so it does nothing.
   Response 5 is a small read_file call, again with promptTokenCount 600,000.
   Request 6: compress() fires with the flag set, truncateHistoryToBudget (:337063-337120) keeps the newest 50,000 estimated tokens of tool output (COMPRESSION_FUNCTION_RESPONSE_TOKEN_BUDGET, :337011) and replaces the oldest heavy result with formatTruncatedToolOutput's text (:254171-254185: "Output too large. Showing first 8,000 and last 32,000 characters. For full output see: <path>" then the head, the omitted count and the tail), because it is longer than the 40,000-character threshold; the estimate is under 600,000, so the status is CONTENT_TRUNCATED (:337155-337166), and tryCompressChat calls setHistory (:348581-348585).
   Expected record: a re-record of shape A's kind (`$patch {removeIds, updates}`, survivors a fresh synthetic run) whose image differs from the originals in that one response, neither original nor masked.
   The B26 reader's expected verdict: refused, "a re-recorded response neither original nor masked (content truncation)".
3. Process 3, `-r`: a resume after the truncation re-record (road (a)'s shape, reached another way).

Scenario C2 (a truncation that truncates nothing): as C1 but with results that all fit the 50,000 budget.
Source says CONTENT_TRUNCATED is still returned whenever the estimate is under the reported count (:337155-337164), so the CLI re-records an image-identical history.
Expected: B26's reader admits it as shape A with zero masked parts, labelled a masking re-record; the probe records whether that is so, and the follow-up lane decides whether a truncation re-record needs its own label.

### Scenario list and their CLI processes

| Scenario | Processes | Road reached (predicted) | Inflated usage |
|---|---|---|---|
| A1 | 3 | masking re-record, then a resume after it | none |
| A2 | 3 | the same with a "/"-leading prompt inside the re-record | none |
| A3 | 3 | masking at a resume's first request, then a resume | none |
| B1 | 3 | true compression, then a resume after it | one response at 600,000 |
| B2 | 3 | masking, resume, compression, resume | one response at 600,000 |
| C1 | 3 | failed compression, truncation re-record, resume | two responses at 600,000 |
| C2 | 2 | truncation re-record with nothing truncated | two responses at 600,000 |
| A1-fake | 3 | A1 again through `--fake-responses` (cross-check) | none |

Every process runs in seconds against the stub; the whole set is about 22 processes.

## 4. Where it runs

### athena's walk box, as a new measurement road (preferred)

- Not the production take road: run_take's Gemini package sweep refuses GOOGLE_GEMINI_BASE_URL (and GOOGLE_VERTEX_BASE_URL, GEMINI_API_KEY_AUTH_MECHANISM, NO_PROXY) for every arm (box/run_take.py:466-530, the name at :519), the take's environment row hands HTTPS_PROXY and the real key file (run_take.py:172-174), and the driver refuses any adapter but its own (stub_take.py docstring); editing any of that would touch frozen, pinned production code for a probe.
- So: a new box module, for example evals/gap-study-4/box/stub_model_probe.py, built on stub_take.py's pattern ("a MEASUREMENT road ... never a study take", stub_take.py:1-40): it imports run_take's DockerRuntime, TakeSpec, check_spec, create_argv, make_config_dir and teardown, take_config.write for the settings file, gemini_adapter.argv for the exact argv, and native_snapshot's locate and retain; it never calls run_take.exec_argv, run_turn or read_login (bound by an ast test, as tests/test_stub_take.py does); no production module imports it.
- The container: the locked take-g image by id (box/gemini/image.lock image_id, `--pull=never` in create_argv, so nothing is fetched), on a fresh `docker network create --internal` network that no proxy joins, so the container has no route out at all; loopback inside it still works, and that is all the stub needs.
- The execs: the stub server started as the agent user from a read-only copy placed in the run tree (one background exec), then each CLI process as a docker exec built from gemini_adapter.argv, with an environment of exactly PATH, HOME, LANG, TMPDIR/TMP/TEMP and GEMINI_CLI_HOME as the take row sets them (run_take.py:172-173), plus GEMINI_API_KEY=<a fixed dummy string, recorded in the manifest> and GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:<port>, and no HTTPS_PROXY.
- Output: one folder per scenario named so it can never be mistaken for study records (stub_take's FOLDER_PREFIX rule, outside mode_binding.RECORD_ROOTS): session/native-turn-<n>.jsonl, turn-<n>.jsonl, the stub's request log, the scenario file, the settings file's sha256, the container and image ids, and a manifest of every file's sha256, every record carrying a RECORD_KIND such as "stub-model-probe" and "never a study take, walk or rehearsal".
- Launch: walk_launch.py's road already ships a bundle to a new mode-700 child on athena, claims the reservation under a hold and runs one Python entry under it, and copies back with sha256 read on both sides (walk_launch.py:1-60); the smallest change is a `probe` entry beside `run` and a `fetch-probe` that copies the output folder back with copy_from instead of fetching a git ref, with the same hold, gate and machine checks.
  The alternative is a one-off script driving walk_launch's Runner; I recommend the entry, because it inherits the hold, the gate and the tests.
- Machine order: one thing at a time on athena under its reservation (machine-order rule), never beside a battery; athena time about 15 minutes per full run including container start and teardown, so one gap covers the smoke run and one the full set.

### What it needs, and whether Javier is needed

- No login, key, credential, sudo, spend, deploy or public push: the dummy key is not a key, the stub sees only loopback, and the take-g image is already on athena.
- athena's use: the walk box already runs Gemini CLI walks there, and the CP2 stub take ran there as a box measurement (night log, 14 Oct 08:23 and 09:00); this probe is the same class, so it is glitch-f1's call under the delegation, not Javier's.
- One possible exception, as in the planning note: if the auto-mode classifier refuses the new launcher path, only Javier can add an allow rule for it in /Users/javrodher/glitch/.claude/settings.local.json; the operator stops and asks, never rewords or re-routes.

### The Mac, only if athena cannot

- Docker is installed on the Mac (/usr/local/bin/docker), but the take-g image is not, and building it would pull the node base and npm package over the network onto a disk already under the suite's 20 GB floor; so the Mac fallback is a plain Node run, which I do not recommend unless athena is unavailable for days.
- Isolation it would have: the pinned tarball, hash-checked, installed into a new scratch prefix; every process under `env -i` with only the variables above and a scratch HOME and GEMINI_CLI_HOME; the run tree in the scratch folder; the stub on 127.0.0.1; and a macOS sandbox profile denying network except loopback and writes outside the scratch folder.
  That is weaker than the container (the CLI's tools would run as Javier's user on the host), the settings and folder paths would differ from the box's, and it would wait for the Mac booking to end (about midnight) and for a heavy slot.

## 5. How the records are read, and what lets glitch-f1 rule

### Reading

1. Mac only, light work, on the fetched folder: sha256 of every file against the manifest.
2. B26's readers over each scenario's snapshots, from a `git archive` of the reviewed B26 head (04c4e774 or its successor), never the fold clone: gemini_session_replay.replay on each native-turn-<n>.jsonl, native_reader_registration.gemini_snapshot_prefixes and gemini_history over each scenario's snapshot sequence, and check_session with its streams where the survey's inputs exist.
   The probe writes each scenario in the walk folder's layout (session/, turn-<n>.jsonl, and a minimal ledger with each turn's sent line) so B26's survey script (glitch-26-carry-20261021/b26/survey26.py) can read it unchanged; if the survey needs fields a probe cannot honestly fill (a register entry, a grade), the reading calls replay and gemini_history directly and says so.
3. B26's structure tools (allpatch.py, classify.py, detail.py in glitch-26-carry-20261021/b26/tools) over every control record and every removeIds patch, and the stub's request log beside them (which request carried the masked tag, the truncation text or the summary, and what each post-resume request's history held).
4. The fixture: the probe's records hold no model text, no study prompt, no tool output from the study and no credential (every string is the CLI's own or the probe's synthetic text), so they are admissible raw after the B25/B26 leak checks (0 hits for the OD57 ruled digest, no string outside the allowed classes).
   If glitch-f1 prefers the cut form for uniformity, a new cutter tests/fixtures/b27-stub/cut_structure.py extends B26's (which hard-codes its JOBS and must not be edited) with two rules: the truncation wrapper (:254177-254184) kept around a synthetic head and tail, and the summary's `<state_snapshot>` wrapper and the exact acknowledgement (:337261) kept verbatim.

### What lets glitch-f1 rule each road

Admit a road (in a follow-up reader lane, design first, base the reviewed B26 head) only when all of these hold:
- the road's records were written by the pinned CLI's own recorder in the locked take-g image, with the probe's manifest showing only the three named environment changes and the study's settings file byte for byte (its config_sha256);
- every record in the road's span is mapped to a cited line (the recorder write at :287265 or the append at :287189-287196, and the trigger: :348592-348597 masking, :348568-348580 compression, :348581-348585 truncation, :336356-336377 and :286096-286110 for the resume), and nothing in the span is unexplained;
- the stub's request log agrees with the records (the request that first carried the masked or truncated text, or the two summary requests, sits exactly where the records say the re-record fell);
- the B26 reader on the reviewed head refuses the span for the reason that names that road, and refuses nothing else in the scenario;
- for A1, the `--fake-responses` cross-check gives the same record structure (record kinds, `$patch` key sets, the removeIds and survivor structure, the re-recorded context id), ids and timestamps aside.
Then the follow-up lane extends the replay on the exact observed shape, with mutants that each refuse on their own reason, re-runs the survey over every committed walk plus the probe folders with no filtering, gets a fresh review and an athena battery, all before the freeze.
Keep a road refused, with the probe's evidence written into the reader's docstring and the lane file, when any of these fails, when the shape needs a departure beyond the three environment values (for example a lowered threshold), or when the reviewer judges that the stub's inflated usage makes the shape unrepresentative (risk R4).
In both cases the residual recorded for the study is plain: whether a road was observed on the real API (none of the three was, in 36 practice walks) or only on the pinned client against a stub.

## 6. Size, stages, tests, estimate and place in the order

### Stages

1. The stub server and scenario format (Mac, light): about 250 lines of standard-library Python plus tests against a local fake client that speaks the SDK's framing (a test client, never the CLI); about 2 to 3 builder hours.
2. The probe module (Mac, light): container, network, settings, run tree, stub start, process loop, retain, manifest and teardown, all on a fake runtime as tests/test_stub_take.py does (the ast bindings: no exec_argv, run_turn, read_login; no production import of the module; the environment exactly the named set; the output folder outside the record roots); about 4 to 5 hours.
3. The launch entry (`probe` and `fetch-probe` on walk_launch's road, tests on its fakes): about 1.5 hours.
4. A fresh independent review of stages 1 to 3 before anything runs on athena (opus-medium per the engine policy): about 1 hour, plus folding its findings.
5. athena smoke run (A1 only), in the first gap: it shows every request the CLI really makes (the stub fails anything unscripted), the real request that masks, and whether the arithmetic of section 3 holds; script corrections, if any, are recorded with their reason.
6. athena full run (every scenario plus A1-fake), in the next gap.
7. Reading and the evidence note (Mac, light): about 2 hours; then glitch-f1's ruling per road.
8. If any road is admitted, the reader follow-up lane (design, build, survey, review, battery), sized on its own; it is about the size of B26's stage 2 for one road.

### Test plan (before athena)

- The stub: SSE framing parsed by an independent framing check that mirrors responseLineRE (:267445); an unscripted request gets 400 and ends the scenario; an out-of-order request is refused; the inflated usage is sent only where the scenario names it; call ids follow `call_<n>`; finishReason on every final chunk.
- The probe: create_argv called with the internal network's id and the locked image id; the environment of each CLI exec exactly the named set (a test refuses HTTPS_PROXY, a real-looking key file path, or any extra variable); settings from take_config.write and its sha256 recorded; argv from gemini_adapter.argv with `-r` only after process 1; snapshots retained after each process before the next exec; teardown leaves nothing (run_take.leaked).
- Red witnesses: each of those bindings broken in a scratch copy turns its test red (the mutation habit of B25 and B26).
- The ast bindings named in stage 2.

### Honest time

- Builder work: about 10 to 14 hours of agent time across stages 1 to 4 and 7, Mac-side light work that can start now, beside the queue, because it touches no athena time and no frozen file.
- athena: under one hour in all (two short gaps).
- Wall clock to a ruling: likely Fri 23 Oct to Mon 26 Oct, set by athena's order and the review round trips, not by the build; this is my estimate, not an ETA-engine date.
- Order: the B26 fold, its battery, the M2 fold and Javier's acceptance sitting keep athena first; the probe takes the first athena gap after them in which no battery is queued, one run per gap, never beside a battery; the reader follow-up lane (if any) and its battery then sit before the freeze.
- If the freeze date comes first, the roads stay refused by name with the probe's design and any partial evidence recorded as the residual; the probe never delays the freeze.

## 7. Risks: where the stub's records could differ from the real API's, and how each is handled

- R1, transport: the only code path change is httpOptions.baseUrl (:312896-312911); the SDK, the wrappers, the recorder and the tools are the walks' code; the walks' proxy is absent, which only carries bytes.
  Ruled out by source; named in the manifest.
- R2, response chunking: the real API streams many chunks per response, the stub few; the CLI consolidates every chunk into one model turn and one recorded message before recording (:333950-333985, then :334021-334041), and the after-model hooks that would see chunks are off (hooksConfig.enabled false, take_config GEMINI_SETTINGS).
  Ruled out by source for the records; the stream-json output may differ in delta count, which no road depends on.
- R3, ids, thoughts and usage shape: the stub uses the real call-id form, real thought parts and all six usage fields; the records' key sets are compared with a committed walk's (rec, toolCall, tokens and thought key sets as read from w-g14 native-turn-1) in the reading step.
  Checked at reading; a key-set difference is a finding, not ignored.
- R4, inflated usage: for (b) and (c) the stub reports a promptTokenCount the history does not have.
  The CLI cannot tell: the trigger compares the number only (:337135-337143), and the summary, truncation and re-record paths read the history, not the number.
  But on the real API a context of 524,288 tokens would almost surely have masked first, so a real take would reach compression after masking, not alone; B2 covers that order, and the reviewer judges whether B1's isolated shape is representative.
  Named, partly covered by B2.
- R5, server-side behaviours absent: thought-signature checks, implicit caching, safety blocks and rate limits do not occur; none of them writes a session record on these roads (the cache only changes cachedContentTokenCount; a blocked response raises before recording, :333990-334020).
  Named; out of the roads' span.
- R6, remote flags: none under the API key, as in the walks (:312485-312499, :366237-366262).
  Ruled out by source.
- R7, helper calls the real run makes and the stub does not script: the stub fails every unscripted request, so a missing helper shows up as a held smoke run, never as a silently different record.
  Ruled out by construction.
- R8, synthetic text: content strings differ from a real take's; the B26 rules are on structure, ids and the ignored-content predicate, and the scenarios set the predicate deliberately (A2's "/" prompt).
  Named; the A2 scenario exercises the one content rule that matters.
- R9, a stub-specific artefact in the SDK path: the A1-fake cross-check runs the same script through the CLI's own FakeContentGenerator (:312825-312832), which bypasses the SDK; equal record structure from both says the transport does not shape the records.
  Covered by the cross-check.
- R10, the box image: the probe uses the locked take-g image by id, so the CLI version and the settings are the walks'; a system-wide settings file in the image is the one place neither the planning note nor I read; the probe records `gemini --version` and the effective settings sources the CLI reports, and the smoke run would show a difference in thresholds through where masking falls.
  Named; checked at the smoke run.
- R11, isolation: an internal network with no proxy, no credential in the container or the environment, the dummy key recorded as such, and the CLI's own tools limited to the synthetic run tree by the box's read-only root and two bind mounts (create_argv).
  As safe as a walk, with strictly less reachable.

## Open calls for glitch-f1 (none needs Javier)

1. Approve the road: a box measurement module plus a `probe` entry on walk_launch's road, run on athena in two gaps after the queue named above.
2. Whether the follow-up reader lane may admit a road observed only against the stub (my recommendation: yes for road (a) and (c), whose triggers are client-side or count-only; for (b), admit only if B2 shows the same shape as B1).
3. Raw probe records as fixtures, or the cut form through a new b27 cutter.
4. Whether to keep the A1-fake cross-check (recommended; it costs one more scenario and no athena time worth counting).
