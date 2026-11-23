# Gemini projection and launch record kinds

Parent checkpoint: `ba207710` (native snapshot history join).
Writer: Claude Code harness lane, resumed from the Codex builder's migration checkpoint, 14 Oct 2026 00:02 EDT.
This is an unregistered source-derived projection plus an exact record-kind allowance, not a production session reader or checker.

## What changed

`gemini_projection.project(raw)` replays one retained snapshot through `gemini_session_replay` and returns one fact dict per user-delimited interaction, in `vendor_provenance.SESSION_KEYS`.
Version, cwd and permission mode are `None`.
`requested_model` is the `model` the native gemini messages of that interaction report, `None` when none reports one; two different models in one interaction refuse.
`output` is a comparison summary, not an event sequence: one exact visible-text aggregate (non-thought text in replay order) followed by ordered tool facts.
A tool fact carries id, name, structured args, the emitted raw status, and whether a string display result exists.
Model-facing `toolCalls[].result` parts are validated (each a `functionResponse` with matching id and name) but never become displayed output; an object display result is absent output, never an empty string.

Source grounding: the box lane's retained `gemini-native-session-source.json` (`chunk-J7SXW2FI.js`, `newMessage`, `recordMessage`, `recordToolCalls`) and `gemini-tool-result-source.json` (`recordCompletedToolCalls`: id, name, args, result as responseParts or null, status, timestamp, agentId, resultDisplay, description; plus displayName, description and renderOutputAsMarkdown enrichment).
The stream path strips ANSI unless raw output is configured (`gemini-legacy-content-source.json`), so native text containing ESC refuses as an unproven transformation.

Refused in this initial subset: unknown message, part or tool keys; mixed parts; statuses other than success/error; a sub-agent call (`agentId`); nonfinite numbers anywhere; missing, empty or mismatched response parts; reused call ids within or across interactions; content function calls that disagree with the recorded tool calls; `displayContent`; multi-part user content; info/error/warning messages; a gemini message before any user message; an interaction without an assistant message or without visible answer text.
A refusal is a reader result only and never erases an executed record or authorizes a replacement take.
No production registry entry was added.

`drive.record_kind` gains exactly two top-level launch-kind names: `public-config.json` (the box's `take_config.public_record` bytes, per the box report's boundary line) and `turn-N.jsonl.launch.json` for positive N without leading zeros (the box's `run_take` actual-submission journal).
`launch` is outside `scan_record.MASKABLE`, so a finding in either refuses the commit rather than being masked.
Nearby and nested spellings still refuse.

## Verification (Mac, each run behind a fresh `mac_slot.py light-ok` exit 0)

- Red first, the checkpoint's exact commands: `test_gemini_projection.py` failed 4/4 by assertion ("Gemini legacy projection is not built"), no errors; `test_vendor_record_kinds.py` failed 3 subtests of the positive test by assertion ("no scan classification"), the refusal test already passed, no errors.
- Green: projection 4/4, record kinds 2/2; neighbours vendor provenance 6/6 and Gemini replay 3/3.
- Every refusal mutant in the projection test was checked to refuse for its intended reason (reason strings retained in the scratch witness output).
- Seven in-memory mutations, each killed by assertion with no errors: model-facing response text used as display; any status accepted; reused-id check removed; reuse checked only within an interaction (initially survived, so the test gained a cross-interaction reuse witness, then killed); ANSI accepted; launch name matched by search or nested; `public-config.json` accepted nested. Candidate bytes unchanged.
- `copy_manifest.py --check`: ok, 372 files from 56 fragments. `git diff --check` clean.

## Not run, and owed

- `test_walk_runner.py`, `test_box_integration.py` and the full battery: broad, for athena by the supported road.
- Language and pooling lints over the new files.
- Independent review of this slice.
- Projection against a recorded Gemini 0.64.0 session; the stream-side counterpart comparison; registration.
- `walk_files` counts a stream or transcript as "a turn ran"; a launch journal alone does not yet make the driver ledger mandatory. Whether a submitted-but-streamless turn should is a boundary question for the next integration slice.

## Addendum, 14 Oct 2026 00:20 EDT: review CHANGES and the fix

The independent review of `f0546df8` (`/Users/javrodher/aegis-builds/gap4-review-harness-step2-20261014/review-harness-step2.md`) returned CHANGES. This addendum corrects the report above; the text above stays as written.

Corrections to claims above:
- "exact visible text" was wrong. Native gemini `content` is the recorder's normalized text (zero-width removal, repeated HTML-comment removal, trim), not what the stream showed, and the `""` join dropped separators between model messages. The fact is now `recorded-text`, one segment per gemini message, with the normalization defined in `gemini_projection.recorder_normalize` and cited in `lane-reports/gemini-0.64.0-source-retained-2026-10-14.md`; the stream side must apply it per model message before comparing.
- "Every refusal mutant ... refuses for its intended reason" was wrong for the tool-name mutant: it refused at the response-part name check, so the name and id parts of the content-versus-recorded comparison were unwitnessed. Every refusal case now asserts its own reason, and name-only and id-only content functionCall mutants exist.
- An interaction ending on tool calls with no later model message was projected as complete; it now refuses as incomplete (the fact schema has no incomplete marker).
- The launch-journal walk boundary named under "Not run, and owed" was opened by this slice's admission; it is closed in `0d417a1d` (3a) with its test.

Kept refusing, named as known false-refusal risks because their pinned source lines are not retained: user `displayContent`, multi-part user content, history-patched parallel tool results. Admitted: `thoughtSignature` on a functionCall part (retained `stripThoughts2`), never output.
