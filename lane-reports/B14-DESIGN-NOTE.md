# B14 design note: which models serve an arm G run under the pinned Gemini CLI 0.64.0

Lane vendor-b14, round 1, glitch-26's ruling B14 (Mon 19 Oct 2026): a design note only, with no code change.
Trigger: practice walk w-g5 was held on "result.stats.models names ['gemini-3-flash-preview', 'gemini-3.1-pro-preview-customtools'], not only the row's 'gemini-3.8-flash'".
The held take's bytes were not seen or asked for; every claim below comes from the package source, read statically.

## Source and method

The package is the npm tarball @google/gemini-cli 0.64.0; its sha256 was verified as 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6.
It was unpacked into a scratch folder outside the clone and read only, with grep and sed; nothing in it was run or imported.
The running chain's sha256 values: bundle/gemini.js ab113d84..., bundle/gemini-Q2GRYIAK.js 7702da31..., bundle/chunk-NR7L3FXV.js d566e81b..., bundle/chunk-FLKY6NH5.js f6a4ddd4... (the last three match take_config.VALUE_SOURCES).
Short names below: G is bundle/gemini-Q2GRYIAK.js (the CLI), C is bundle/chunk-NR7L3FXV.js (core), F is bundle/chunk-FLKY6NH5.js (the settings schema).
Four read-only readers worked in parallel over these files, and I re-read every line this note rests on.
The run studied is the adapter's argv, `gemini -p <line> -o stream-json -m <row model> --approval-mode yolo` (later turns add `-r <session id>`; gemini_adapter.py:209-213).
Its settings are the ones take_config._gemini writes (box/take_config.py:65-91, 239-251): tools.exclude of the two web tools, hooks off, auto-update off, usage statistics off, telemetry off, the ADK noninteractive session off, model.name the row's model, customAliases restating chat-base-3, security.auth.selectedType "gemini-api-key", and folder trust off.

## 1. How the model of each main-conversation request is chosen

The CLI takes the model from `argv.model || process3.env["GEMINI_MODEL"] || settings.model?.name` (G:8457).
Only the literal "auto" is replaced (G:8459), so gemini-3.8-flash passes through unchanged into Config.model.
The init event's model is `config.getModel()` (G:12140), the requested id echoed back, never evidence of what served the call.
With agentSessionNoninteractiveEnabled false, the legacy non-interactive road runs, and that road builds the init and result events (G:12022 onward).
The model router puts its strategies in a fixed order starting at C:362176, and the override strategy returns null only for an auto model (C:362106).
For a concrete model it returns resolveModel of that model (C:362110), so the classifier, numerical classifier and default strategies never run for gemini-3.8-flash.
resolveModel keeps an id it has no case for (C:280109), and the latest-flash promotion yields LATEST_GEMINI_FLASH_MODEL (C:280116), which is "gemini-3.8-flash" itself (C:279985).
The table-driven resolution (modelIdResolutions and classifierIdResolutions, from C:362702) is read only when experimental.dynamicModelConfiguration is true, and that defaults to false (C:380832, F:14534); take_config does not set it.
The availability step then builds the Gemini 3 fallback chain, because gemini-3.8-flash matches `/^gemini-3(\.|-|$)/` (C:280236).
That chain has gemini-3.1-pro-preview-customtools at its head (C:308181, resolved through C:280090) and gemini-3-flash-preview as its last resort (C:308192).
The requested model is not in that chain, so the chain collapses to the requested model alone (C:308338).
So every main-conversation request the client sends names gemini-3.8-flash.

## 2. Every place a model other than the requested one can serve a request

### 2a. A router or classifier

None for a concrete model: the classifier strategies are reached only for auto models (C:362106).
general.plan.modelRouting and experimental.gemmaModelRouter affect auto models only (F:12637, C:362125).

### 2b. A fallback on an error or a quota

In a headless run, nothing switches the main conversation to another model.
The only call to setFallbackModelHandler is in the interactive UI chunk, which a `-p` run never loads (G:17727), so handleFallback finds no handler and returns null (C:308463).
Utility calls made through BaseLlmClient get no fallback callback at all when the run is not interactive (C:309053).
retryWithBackoff retries the same model (up to 10 attempts by default) and then throws.
Invalid or empty stream responses are also retried on the same model.
One edge exists: a request on a model other than the active one (for example a flash-lite helper) can be switched silently to the active model when its own chain's action is silent (C:308447).
That edge moves a helper onto the row's model, never away from it.
No setting turns fallback off; none is needed for the main conversation, because its chain is the requested model alone (C:308338).

### 2c. The customtools variant

gemini-3.1-pro-preview-customtools is chosen whenever a request resolves gemini-3-pro-preview or gemini-3.1-pro-preview while useCustomToolModel is true (C:280090).
useCustomToolModel is "Gemini 3.1 launched and API-key auth" (C:382496), and 3.1 counts as launched for API-key auth with no experiment flag (C:382499).
It does not depend on which tools are present.
The main conversation never resolves a pro model in this run (section 1), so customtools can only serve helper calls whose alias names a pro model (2d).

### 2d. Internal helper calls

Each helper names a built-in alias; the alias table starts near C:362380, and helpers pass through the same availability step (C:309019).
gemini-3-flash-base pins gemini-3-flash-preview (C:362386-362389).
loop-detection extends gemini-3-flash-base (C:362486), so its calls are gemini-3-flash-preview.
loop-detection-double-check pins gemini-3-pro-preview (C:362493), which becomes gemini-3.1-pro-preview-customtools here (C:280090).
The loop detector's LLM check starts after 30 turns within one prompt (C:343862), and the double check runs only when the first check's confidence reaches 0.9 (C:343866).
model.disableLoopDetection defaults to false (F:13371-13376) and, when true, removes both calls (C:344011).
Chat compression of a gemini-3.8-flash chat uses the alias chat-compression-3-flash (C:337044), which pins gemini-3-flash-preview (C:362524).
An unrecognised model string gets chat-compression-default, which pins gemini-3-pro-preview (C:362549) and so becomes customtools.
Compression runs only above model.compressionThreshold, which defaults to 0.5 of the context window (F:13366).
llm-edit-fixer (C:362496) and next-speaker-checker extend gemini-3-flash-base, but neither runs here.
The edit fixer is off because disableLLMCorrection defaults to true (C:380822, F:13976-13980).
The next-speaker check is off because skipNextSpeakerCheck defaults to true (C:380928, F:13385).
Subagents: invoke_agent is in arm G's tool table (round 18 B12), and agents are enabled by default (experimental.enableAgents, F:14421-14426).
The built-in codebase_investigator runs on PREVIEW_GEMINI_FLASH_MODEL, gemini-3-flash-preview, whenever the main model is a modern one (C:336021).
The built-in generalist inherits the main model (C:340912), but its own compression, if reached, uses chat-compression-default, so customtools.
Several helpers do not run under these settings: the shell output summarizer needs model.summarizeToolOutput (default undefined, F:13348); the context-management summarizers need experimental.generalistProfile or contextManagement (both off); the session summary runs only from listSessions; and the update_topic tool makes no model call.

### 2e. The server

The stats key for each response is the server-reported `modelVersion`, falling back to the request's model only when the response carries none (C:312324 for non-streaming calls, C:312388 for streaming calls).
So even a request that names gemini-3.8-flash is counted under whatever version string the API returns.
The package cannot say what the API reports for a gemini-3.8-flash request.

## 3. What result.stats.models then reports

result.stats is built from uiTelemetryService.getMetrics() (G:12426) by convertToStreamStats, which copies every key of metrics.models as is (C:383042-383051).
Each API response is added to the bucket of event.model (C:287523), where event.model is `responses[0]?.modelVersion || req.model` (C:312388); API errors are keyed by req.model (C:312337).
Helper calls go through the same content generator and are counted in the same per-model totals; the role that would tell them apart is dropped from stream stats.
Loop-detection calls even reuse the main turn's prompt id (C:344284).
telemetry.enabled false and privacy.usageStatisticsEnabled false do not stop this accounting (uiTelemetryService.addEvent runs unconditionally, C:289316).
So stats.models is the set of server-reported versions over the main turns and every helper call in the invocation, never the set of requested ids.
~~The w-g5 stats name no gemini-3.8-flash key at all.~~ Corrected in round 2 (below).

**Round 2 correction (glitch-26's ROUND 2 rulings, Mon 19 Oct 2026).**
The inference made here in round 1, that w-g5's result.stats.models named no gemini-3.8-flash key and so no response reported gemini-3.8-flash as its modelVersion, was wrong.
It rested on the refusal line, which listed only the keys beyond the row's id, not the whole stats object.
glitch-26 read the per-model numbers of the held w-g5 take's result.stats.models on athena: gemini-3.8-flash carries 5,577,337 tokens (the main turns), gemini-3-flash-preview 25,347 and gemini-3.1-pro-preview-customtools 2,430, and the result counts 113 tool calls against 91 tool_use events in the stream.
So the server reports the row's id as modelVersion for the main turns, and the two extra keys are helper calls, as section 2d reads them.
This settles option C's open question in favour of option A: the strict identity check stands with no named server-alias difference (ruling R-B14-3).
Round 2 builds option A as ruled: R-B14-1 repoints every helper alias at the row's model with loop detection left on (not model.disableLoopDetection, as section 6's option A first proposed), and R-B14-2 excludes invoke_agent (box/take_config.py GEMINI_HELPER_ALIASES, GEMINI_ROW_ALIASES, GEMINI_AGENT_EXCLUSION, each with its lines in VALUE_SOURCES).
Round 2 re-read every other built-in alias for whether a run under these settings reaches it, and found none beyond the ruled ones: loop-detection, llm-edit-fixer and next-speaker-checker extend gemini-3-flash-base (C:362486, 362496, 362500) and follow its repointed entry; chat-compression-3-pro and the 2.5 compression aliases are picked only for other chat models (C:337037-337061); classifier and prompt-completion serve the router for auto models and completion in the interactive UI; fast-ack-helper serves only generateSteeringAckMessage (C:349827), which no bundle file calls (it is defined and re-exported only, C:400661); edit-corrector needs disableLLMCorrection false (C:310738, default true, C:380822); summarizer-shell needs model.summarizeToolOutput; summarizer-default serves the session summary of listSessions (C:390466); web-search, web-fetch and web-fetch-fallback belong to the two excluded web tools; context-snapshotter and the node distillation's own gemini-3-flash-base call (C:345269, repointed anyway) run only with contextManagement.enabled (default false, C:380870), which also gates agent-history-provider-summarizer's two callers (C:348224, C:348857); that alias is pinned as ruled all the same.
The customtools key needs a pro-model helper call: the loop detector's double check, chat-compression-default, or a customtools fallback of a failed gemini-3-flash-preview helper (the helper chains wrap; C:308266, C:308336).

**Round 3 (glitch-26's ruling R-B14-5, Mon 19 Oct 2026):** with loop-detection-double-check on the row's model, a row model whose availability snapshot reads unavailable confirms a loop on the flash check alone, where the shipped CLI asked a separate model (gemini-3-pro-preview, C:362493): the double check's model is resolved from that alias (C:344238-344240), and when `availability.snapshot(doubleCheckModelName).available` is false (C:344246-344247) the detector returns isLoop true with the loop-detection model as confirmedByModel (C:344248-344255) without the second query (C:344257); this arises only once the main model is already unavailable.

## 4. Whether gemini-3.8-flash is accepted as given

It is a model id the pinned CLI knows and keeps as given: LATEST_GEMINI_FLASH_MODEL = "gemini-3.8-flash" (C:279985), listed in the model sets and in its own alias entry (C:362361-362364).
No client-side step maps, aliases or replaces it for the main conversation; the API-key model mapping rewrites only gemini-3.5-flash and gemini-3-flash (C:280032-280033, wired in at C:312940).
hasLatestFlashGAAccess sets PREVIEW_GEMINI_FLASH_MODEL to "gemini-3-flash-preview" under API-key auth (C:382514), which governs helpers and the codebase investigator, not the main model.
What the server reports as the version of a gemini-3.8-flash response is outside the package and is not settled by this reading.

## 5. Settings or flags that pin every request to the one requested model

No single setting or flag does it: -m, GEMINI_MODEL and model.name pin the main conversation only (G:8457).
The helper models can be pinned one by one through settings.json.
modelConfigs.customAliases (default {}, F:13409) is layered over the built-in aliases at lookup time (C:342156), and an alias's model wins (C:342290-342297).
Pointing gemini-3-flash-base, loop-detection-double-check, chat-compression-3-flash, chat-compression-default and agent-history-provider-summarizer at the row's model repoints every helper that runs here.
A row model outside the preview chain is then kept as given by the availability step (C:308338).
model.disableLoopDetection true removes both loop-detection calls outright (C:344011).
tools.exclude with invoke_agent removes the subagent tool from the offered tools (the registry filters excluded names, C:313463-313473).
That also fits the plan's vendor side, where agent_summary counts zero Agent calls by construction and any delegation refuses (vendor-T4-PLAN.md section 6).
experimental.enableAgents false (F:14421-14426) would remove the agent registry altogether.
None of these settings governs the server's modelVersion, so none can guarantee that stats.models names only the row's id.

## 6. The honest options for the study

### Option A: pin by settings, and keep the strict check

take_config adds model.disableLoopDetection true, tools.exclude gains invoke_agent, and customAliases repoints the four flash and pro helper aliases at the row's model; each value goes into VALUE_SOURCES with its file and line, as R3 requires.
gemini_adapter's check and routing.ACCEPTED_IDENTITY_SOURCES stay as they are, and the plan does not change.
This removes every helper model the source shows for these settings.
But if the API reports a version string other than the row's id for main turns, every arm G take still stops at the stream check, and no setting can fix that.

### Option B: admit named helper models under a closed list, as a named difference

gemini_adapter.read_stream would accept stats.models keys within {the row's model} plus a closed per-row list (for gemini-3.8-flash: gemini-3-flash-preview and gemini-3.1-pro-preview-customtools), each entry citing its source line above.
routing.ACCEPTED_IDENTITY_SOURCES would keep stream-init for the model, and stream-stats would become evidence that the served set lies within the list, not proof of the row's model.
The plan's section 6 and vendor-T4-TABLE.md would gain a named difference from arm C: arm G's served model is the requested id echoed by init, plus helper and server-reported versions from a closed list, parallel to arm O's D-INT-2 (routing.UNOBSERVED_ACCEPTED, SERVED_MODEL_LIMIT).
That weakens the identity check: a main turn actually served by gemini-3-flash-preview would pass unseen, which is the very swap the check exists to catch.

### Option C: pin by settings first, then settle the server question from the held record

Build option A, and before any measured arm G walk, glitch-26 reads one held w-g5 record on athena that names a per-message model: the native session file, if it keeps one per message.
The question is whether the main turns' modelVersion was gemini-3.8-flash.
If it was, option A is enough, and the strict check stands with no named difference.
If it was not, the API reports another version for the requested id, and the only honest admission is a named, closed server-alias entry (gemini-3.8-flash reported as that exact string), added under option B's plan text and limited to that one alias, with helpers still pinned by option A.

### Recommendation

Recommend option C.
It removes every helper model the source shows by settings, keeps the identity check strict, and narrows any admission to a server-reported alias that is named, closed and cited.
The one open question (what version the API reports for a gemini-3.8-flash main turn) is a fact in the held w-g5 record, not in the package; that is glitch-26's read on athena, since this executor neither sees nor asks for those bytes.
The same reading applies to the other arm G row, gemini-3.5-flash-lite: its compression alias is chat-compression-3.1-flash-lite (C:337050-337052), so option A must repoint that alias too.
