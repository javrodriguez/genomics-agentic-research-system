# Lane file: vendor-b25 (the native readers on the real walks; Gap Study round 4)

Append-only.
Builder: a Claude Opus 5.5 sub-agent of glitch-26, on the Mac.
Clone: /Users/javrodher/aegis-builds/vendor-b25-20261021, branch lane/vendor-b25-20261021, base 06cb26981b33125a278c22d45d33d8b63441f87f (B24).
Reviews fixed: /Users/javrodher/aegis-builds/REVIEW-reader-codex-20261021.md and REVIEW-reader-gemini-20261021.md, read in full first.
Evidence: the records clone gap4-walk-records-20261019, read by `git archive` of each walk branch (74 branches, one walk folder each: 38 w-o, 36 w-g) into the session scratchpad (b25/walks); never a worktree of it, nothing written to it.

## Stage 0, design: Wed 21 Oct 2026 11:06 EDT (`date`)

### Sources read (what each citation below rests on)

- Codex: the retained pinned source, /Users/javrodher/aegis-builds/gap4-codex-rollout-audit-20261014/src (openai/codex 092d3acd), as the module already cites it.
  One more file was needed and is not retained: codex-rs/protocol/src/openai_models.rs (ReasoningEffort's spellings).
  It was fetched with `gh api repos/openai/codex/contents/codex-rs/protocol/src/openai_models.rs?ref=092d3acd6bec3e3a14bdc7e7a2810ab628ab759d` into the scratchpad, and `git hash-object` gave 45654aa8c552bf851c1f54b42b4709fd8370c856, the blob the retained tree listing (git-tree-recursive.json) names for that path at the pin, size 76856 = the listing's.
- Gemini: the pinned package itself, read on the Mac, not on athena.
  `npm view @google/gemini-cli@0.64.0 dist.tarball` named https://registry.npmjs.org/@google/gemini-cli/-/gemini-cli-0.64.0.tgz; `curl` saved it in its own empty scratch folder; its sha256 is 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6, the tarball pin in gemini_tool_sources._PKG and box/take_config.py.
  Extracted with `tar -x` only (no install, no script run): bundle/chunk-NR7L3FXV.js sha256 d566e81b…cbb8c (= gemini_tool_sources._C_SHA256) and bundle/chunk-J7SXW2FI.js e2aca152…f206e (= the projection's pin).
  bundle/gemini.js:10 imports chunk-NR7L3FXV.js (and :110 loads gemini-Q2GRYIAK.js, which imports it), so the citations are to that chunk, the one the CLI runs.
- Deviation, reported: the fix code was drafted before the tests in this stage.
  The red evidence is therefore taken by running the new and changed tests against a `git archive` of the base 06cb2698 (stage 1 below), not by writing the tests first in time.

### Ruling 1, Codex BLOCKER (codex_native.read_rollout)

What the 38 committed rollouts hold (types only, scratch survey): world_state 89 records across the snapshots (once per walk, always inside turn 1, after the opening response items and before turn_context, always full: true); thread_settings_applied 202 records (two per resume, always between task_complete and the next task_started, thread_id = session_meta.id every time, approval_policy never, approvals_reviewer user, permission_profile {type: disabled}, model and cwd equal to the turns' turn_context).
Design, closed shapes, no fact carried into the projection:
- world_state: payload exactly {full: bool, state: object}: WorldStateItem, protocol.rs:3302-3307 (state is Map<String, Value>, so its keys are open by the pinned type; the module that fills it, core/src/context/world_state/, is in the tree listing but not retained, and the reader reads nothing from it). Admitted only inside an open turn.
- thread_settings_applied: payload exactly {type, thread_id, thread_settings} (ThreadSettingsAppliedEvent, protocol.rs:2228-2236), thread_id required and equal to the session's id (Option only for older histories), admitted only between turns; thread_settings is ThreadSettingsSnapshot (protocol.rs:2238-2267): the eight always-written keys required, the six skip-if-None keys optional, nothing else; values: model and model_provider_id non-empty strings; service_tier a string; approval_policy one of untrusted, on-request, never (AskForApproval, protocol.rs:1000-1025; Granular refuses); approvals_reviewer user or auto_review (config_types.rs:175-190); permission_profile exactly {type: disabled} (models.rs:418-435; arm O runs only bypass, codex_adapter MODE_FLAGS; managed and external carry nested policies not read here, so they refuse); active_permission_profile {id, extends?} strings (models.rs:444-455); cwd and runtime_workspace_roots absolute paths; reasoning_effort a non-empty string (openai_models.rs:60-73, 122-128, 144-156: the wire string, any spelling through Custom); reasoning_summary auto, concise, detailed, none (config_types.rs:60-72); personality none, friendly, pragmatic (config_types.rs:330-336); collaboration_mode {mode: plan or default (config_types.rs:673-684), settings: exactly {model, reasoning_effort, developer_instructions} (config_types.rs:778-784)}; disabled_plugin_ids a list of strings.

### Ruling 2, Codex M1 (the shared join)

native_reader_registration.codex_join_session gains required keyword arguments sent (one per stream) and model.
Each rollout turn's UserMessage must equal the line sent that turn, and its turn_context model must equal the take's requested model, else DISAGREE naming which.
codex_check passes the ledger's turns[].sent and model_requested; drive.codex_cross_check (production) passes take.ledger_rows' sent and row["model"] (the value drive writes as model_requested, drive.py:2697); walk_regrade passes the ledger's.
cwd is not compared: vendor_provenance.cross_check, the contract, binds session_id, sent, output and requested_model only; turn_context.cwd stays a read, unbound fact, as the review's nit n2 asks to say plainly.

### Ruling 3, Gemini BLOCKER 1 (the resume $patch)

The pinned writer and loader (chunk-NR7L3FXV.js):
- updateMessagesFromHistory (:287151-287298), run by GeminiChat.initialize on every chat start, writes the only $patch there is (:287265), whose payload holds updates (:287256-287258), removeIds (:287259-287261) and orderIds = the whole history's ids in order (:287262-287264); a history turn whose id is unknown is appended as a new message first (:287190-287196).
- convertSessionToClientHistory (:286099-286194) builds the resumed history: after each tool-calling model turn it emits a synthetic user turn `${msg.id}_response` holding its calls' results (:286156-286188), and the stored round-trip message comes back as a user turn of its own (:286105-286117). So the copy is appended, and in the new order it sits between the gemini message and the original. On a second resume both the synthetic turn and the stored copy carry the `_response` id, so orderIds lists it twice.
- The loader (createJsonlRecordAccumulator, :286309-286455) applies a $patch's direct id patch, then updates (:286390-286399), then removeIds (:286400-286414), then orderIds (:286415-286453): listed ids move behind unlisted ones in that order, and an id listed twice keeps its first place (Map.set on a present key, :286450-286452).
Design: admit exactly {orderIds, updates}: updates as before, then orderIds a non-empty list of strings, each naming a known message, covering every known message (a permutation, so no prefix stays), and a repeat allowed only for a `<gemini id>_response` user message whose base is a gemini message; first occurrence keeps its place.
removeIds, orderIds without updates, orderIds with a direct id, any other repeat, an unknown id or a missing id refuse.
test_gemini_session_replay.py:48's `{"$patch": {"orderIds": ["a1", "u1"]}}` still refuses under this rule (orderIds without updates, and notice1 left out), so that case stays, with this reason and the source lines now cited beside it; the new admission and each off-shape variant are pinned in tests/test_b25_real_shapes.py.
The projection (ruling 3, second half): the copy is recognised only as the user message whose id is the preceding gemini message's id + "_response", directly after it, directly followed by the original, the two with the same keys and content equal as serialized JSON; then the copy counts as nothing and the original is that gemini message's round trip; every other repeat still refuses.
Real data, scratch survey (all 50 Gemini snapshot files): 618 `_response` records, each base a gemini message; every copy whose original I could match uniquely by its call ids (389) is byte-identical to it.
Two real shapes stay refused under this ruling, by design: `$patch {removeIds, updates}` and `{orderIds, removeIds, updates}` (4 patches, in w-g14 turn 4, w-g32 turn 3, w-g47 turn 2: hundreds of messages removed at once, which reads like chat compression); they are named in the survey below.

### Ruling 4, Gemini BLOCKER 2 (the session context turn)

GeminiClient.startChat (:348055-348079) builds the history with getInitialChatHistory (:336356-336377), whose first turn is a user turn with id deriveStableId(["environment-context"]) (:336357, :336369; deriveStableId = sha256 of the sorted ids joined by "|", first 32 hex digits, :286041-286044, so the id is the constant d04923d38bb0f6017037e74183378ef4), holding one text part: getEnvironmentContext's block (:336332-336355), beginning "<session_context>\nThis is the Gemini CLI. We are setting up the context for our chat.\n" and ending "</session_context>" (:336343-336352, trimmed).
The recorder writes it through newMessage (:286901-286909): keys id, timestamp, type, content (displayContent undefined is dropped).
On resume, convertSessionToClientHistory skips the stored one (isIgnoredUserContent, :286096-286098, :286105-286110) and getInitialChatHistory puts a fresh one first under the same id.
Design: the first replayed message is set aside only when it is type user, that id, exactly those four keys, and content one {text} part with that opening and closing; anything else stays an interaction.
Real data: all 50 Gemini snapshot files open with exactly that shape.

### Ruling 5, Gemini MAJOR (session identity)

gemini_stream_join.join: the stream's init session_id must equal the fact's session_id (the native sessionId); a stream with no init, or another id, refuses. read_call now returns init_session.
The existing test that kept an init-less stream "unknown" changes with that reason (tests/test_gemini_stream_join.py).

### Ruling 6, Gemini MAJOR (empty final answer)

gemini_projection._interaction no longer refuses an interaction with no recorded text segment.
The join already compares the native segments with the stream's normalized non-empty responses, in order, so both empty agrees and one side empty disagrees (a missing segment on either side).
The existing test that pinned the refusal changes with that reason (tests/test_gemini_projection.py).

### Ruling 7, Codex M2: design only (no fold, no merge, nothing run)

Facts (read-only git on the records clone):
- w-o46 is walk/w-kbm1P3ZO, commit ae6bec92, one commit on 45239b01; w-g21 is walk/w-vNjKNXbo, commit e2c30e0c, one commit on d8ceb181. Both parents are ancestors of 06cb2698 (`merge-base --is-ancestor`); each walk commit changes only its folder and rehearsals/register.json.
- register.json is `{"schema": 1, "walks": []}` at 45239b01, at d8ceb181 and at 06cb2698 (0 diff lines from each parent to 06cb2698).
Recommendation: append-only merges, never a rewrite or a cherry-pick (a cherry-pick makes a second walk commit that is not the one the walk branch, its mirror and the ledger's history name).
1. On the reviewed fixed-reader head F (this lane's head after review, rebased on nothing), `git merge --no-ff walk/w-kbm1P3ZO` (w-o46): a clean merge, since only the walk side changes register.json from its base.
2. Then `git merge --no-ff walk/w-vNjKNXbo` (w-g21): register.json conflicts (both sides append to `[]`); the merge commit resolves it to `[<w-o46 entry>, <w-g21 entry>]`, each entry byte-for-byte its walk commit's, and changes nothing else.
3. Why _walk_commit still holds: `git log HEAD -- <walk folder>/` simplifies the merge away (it is TREESAME to its walk-side parent for that folder), so the oldest commit touching the folder is the walk commit itself, whose subject is WALK_SUBJECT and whose register is its parent's plus exactly its entry; the merge touches the register, not the folder. acceptance_problems then finds the entry once in HEAD's register, arm O or G.
4. Before glitch-26 rules the fold, rehearse it in a throwaway clone (not the records clone, not a lane branch): run acceptance_problems' parts that need no record (`_walk_commit`, `drive.walk_files`, `_ledger_problems`, `_records_problems`, `_journal_problems`, codex_check or check_session, session_history_facts) at the merge head. The risk named: `_records_problems` re-derives check.json and grade.json with HEAD's pending_walk and run code, so a format change since the walk's base would refuse; the survey below runs that re-derivation on w-o46 and w-g21 against this lane's code as a first check.
5. Then a fresh independent review of that exact HEAD, then Javier's acceptance commit in his own window.
Which walks: w-o46 for Codex (3 turns, 9 commands; the reviewer's pick). For Gemini, w-g21 (2 turns, 34 tool round trips in turn 1), as glitch-26 suggests; the survey below says whether it and the other multi-turn Gemini walks pass, and the floor.
Alternative, not recommended: one merge per vendor on separate lines; production_readers needs both records on one HEAD to register both, so the two folds meet anyway.

## Stage 1 to 4, commits and runs: Wed 21 Oct 2026 11:15 to 12:49 EDT (`date` at each step)

Commits: a6165962 (design, fixtures, tests), 53737107 (Codex rulings 1 and 2), eee5f440 (Gemini rulings 3 to 6), e2d78eee (what the green runs found).
Mac slot: `mac_slot.py acquire --kind heavy --owner vendor-b25 ...` waited from 10:45; the first two 30-minute waits ended `rc=3` (CPU speed limit 25 to 64, below 80; `light-ok` also held at 41); the third acquired at 12:04:57 ("heavy slot held until 13:04"); released at 12:49:27 (`released: .machine-slots/vendor-b25`). No test or survey ran before 12:04:57; only git and file edits did.

### Red (the new and changed tests on a `git archive` of base 06cb2698, the tests laid over it), 12:05:02-12:05:03

`python3.12 -B -m unittest tests.test_b25_real_shapes tests.test_gemini_projection tests.test_gemini_stream_join tests.test_gemini_session_replay` (via a `-c` launcher that chdirs to the study folder): "Ran 38 tests", "FAILED (failures=38, errors=11)" (subtests counted); every Codex shape, every resume-patch, context-turn, copy, identity and empty-answer case among them.

### Green, on the lane head

- 12:05:07: the same four modules plus tests.test_codex_native: "Ran 53 tests", "FAILED (failures=3, errors=1)": two test bugs (the order compared past the patch, where the next turn's messages follow; a thread_id mutant overwritten by its own helper) and one real find: the w-g31 fixture's context turn lost its wrapper in a resume patch's update (below). Fixed in e2d78eee.
- 12:06:07-12:06:08: "Ran 53 tests", "OK".
- Module battery 12:06:21-12:42:47, one module at a time (`Ran`, verdict): test_pending_codex_walk 11 OK; test_pending_walk 23 OK; test_native_reader_registration 7 OK; test_native_history_record 3 OK; test_vendor_take_records 4 OK; test_codex_patch_reads 13 OK; test_codex_started_file_change 5 OK; test_vendor_provenance 6 OK; test_codex_adapter 64 OK; test_vendor_admission 10 OK; test_vendor_admission_regrade 3 OK; test_walk_grade_seam 4 OK; test_walk_recheck 17 OK; test_vendor_walk_road 6 OK; test_vendor_check 26 OK; test_vendor_body 11 OK; test_take_checker_dispatch 5 OK; test_recheck_coverage 5 OK; test_vendor_constants 10 OK; test_pipeline 85 OK; test_agent_tool 17 OK; test_egress 25 OK; test_nested_agent 35 OK; test_no_output_nudge 9 OK; test_vendor_envelopes 7 "FAILED (failures=2)"; test_freeze_shapes 9 "FAILED (failures=1)".
  (The four test_native_reader_registration ManifestClaim failures both reviews saw on archive copies do not occur in this git checkout.)
- The two reds were gates working: check_vendor_sources pins drive.py whole (POST_EDIT_D_DRIVE_SHA256), and ruling 2's drive.py change was unrecorded; freeze --check refused the nine new files no COPIED.d fragment claimed.
  Fixed the way earlier lanes did it: edit E recorded in tests/check_vendor_sources.py as edit D is (EDIT_E hunks, EDIT_E_RULING "B25-2", POST_EDIT_E_DRIVE_SHA256 = 4a1835d7…25120, computed and written by one script, never typed; edit E taken out first, and edit D's pin then holds unchanged), tests/test_vendor_envelopes.py's EditD reading it and a new EditE class (pinned and named; each hunk taken out, and a moved line, go red); nine "new" entries appended to COPIED.d/vendor-admission.json (45 insertions, no other line moved).
- 12:46:09-12:49:10: test_vendor_envelopes "Ran 9 tests" "OK"; test_freeze_shapes "Ran 9 tests" "OK"; test_b25_real_shapes "Ran 18 tests" "OK"; `check_vendor_sources.py EB drive.py` rc 0.
- Not run: the whole suite (athena's battery comes after review); test_walk_launch, test_walk_builders and other modules that do not import a changed module.
- Deviation, reported: the three 12:46 logs were first written to /tmp/claude-501/ (the parent of the session scratchpad) instead of the scratchpad; I removed exactly those three files at 12:49.

### The fixture find (real data, so it is recorded)

Every resume rewrites the context turn through a `$patch` `updates` entry for its id (13 such updates across w-g13, w-g14 and w-g31; each keeps the pinned opening and closing, one text part).
The replay applies it like any content update, and the projection reads the replayed content, so the context turn is still recognised; only my cutter had replaced that update's text. The cutter now keeps the wrapper in updates too, and the w-g31 fixture was re-cut (the other fixtures held no such update).
Leak check on every fixture after the re-cut: 0 hits for the OD57 ruled-line sha256 on any string or any line of one, 0 strings that are not synthetic text, a synthetic path, the context wrapper, or a kept-key value (ids, timestamps, tool and display names, statuses, model names, pinned enum values).

## Stage 5, the survey: 12:06:29 (fixed) and 12:07:16 (base), `date`

`python3.12 -I -B survey.py <code> <walks>`: every committed walk, no filtering: codex_check (Codex, with the ledger's sent and model_requested) or check_session (Gemini) on the last snapshot and the ledger's streams, then session_history_facts over every snapshot the ledger names, then the acceptance floor.

| | Base 06cb2698 | Lane head |
|---|---|---|
| Codex (38) | 38 DISAGREE: line N, `world_state` unsupported | 38 PASS; history 38 joined; 25 meet the floor (every multi-turn walk), 13 single-turn do not |
| Gemini (36) | 27 DISAGREE: lacks an assistant message (the context turn); 9 DISAGREE: unsupported native patch operation | 32 PASS; history 32 joined; 6 meet the floor (w-g13, w-g21, w-g31, w-g39, w-g40, w-g48) |

The base column reproduces both reviews exactly.
The four Gemini walks still refused, each named:
- w-g14 (4 turns), w-g32 (3 turns), w-g47 (2 turns): `native replay refused: unsupported native patch operation`: their later resumes write `$patch {removeIds, updates}` (and w-g14 also `{orderIds, removeIds, updates}`), removing hundreds of messages at once (w-g14 turn 4: 151 copies, 85 user, 85 gemini; w-g32 turn 3: 263; w-g47 turn 2: 300), which reads like chat compression. Ruling 3 keeps every shape but {orderIds, updates} refused; a reader for this road needs its own source reading and ruling.
- w-g24 (1 turn): `native interaction is incomplete: its last model message ends on tool calls`: the ledger says outcome timed-out, exit 124, and the stream ends on a tool_result with no result record; a turn killed mid-tool is refused by design (NEVER_COUNTED), never an agreement.
Counted against the review: the Codex review says 24 walks meet the floor and 14 are single-turn; this survey counts 13 single-turn walks (the ledger's streams, and the join's interactions, equal for every PASS) and 25 multi-turn, each with at least one command. I did not find the review's 14th; named, not resolved.

### Real-byte probes (scratch, in memory; nothing written to a walk)

w-o46 through codex_check: unchanged PASS; UserMessage text replaced DISAGREE ("the rollout's sent prompt is not the line sent"); every turn_context model replaced DISAGREE ("requested model is not the take's"); world_state without full, thread_settings_applied naming another thread, permission_profile managed, an unknown thread_settings key: each DISAGREE naming its line and shape. The review's two PASS-with-replacement probes now go red.
w-g21 through check_session: unchanged PASS; a non-identical `_response` copy, a `$patch` with removeIds added, orderIds repeating a non-`_response` id, the context turn under another id, and the stream's init session_id changed: each DISAGREE for its own reason.

### Ruling 7 pre-check (no fold, no merge)

Under this lane's code, on the archive copies, w-o46 and w-g21 each pass `drive.walk_files`, and their committed check.json and grade.json re-derive byte for byte (pending_walk.check_doc, run.grade_walk), with the register entry read from each walk commit's register.json. So the risk named in the design (step 4) does not bite these two walks at this code; the throwaway-clone rehearsal of the merges is still the step before the fold.
w-g21 meets the Gemini floor (2 interactions, 34 tool round trips) and w-o46 the Codex floor (3 turns, 9 commands).

## Stop for review: Wed 21 Oct 2026 12:49 EDT

Open for glitch-26:
1. The compression road (removeIds) refuses on 3 of 36 Gemini walks; rule whether it is read (a source reading of the compression writer) or stays refused.
2. The Gemini replay still admits the direct `$patch {id, ...}` and updates-only shapes from the earlier source reading, though the pinned writer's one `$patch` site (:287265) never writes a direct id; tightening is out of this lane's scope.
3. world_state with full: false (a patch, source-attested) is admitted by type but unseen in the 38 walks; thread_settings_applied's Managed or External permission profile and a Granular approval policy refuse (arm O runs only bypass).
4. Codex floor count 25 against the review's 24 (above).
5. The M2 fold (design above): merge, never cherry-pick; the second merge resolves register.json by appending both entries.

## Correction, Wed 21 Oct 2026 12:51 EDT (`date`)

Stage 4's "13 such updates across w-g13, w-g14 and w-g31" was read from a listing cut at ten lines. Counted in full over every Gemini snapshot file: 14 `$patch` updates of the context turn's id (w-g13 3, w-g14 5, w-g31 3, w-g32 2, w-g47 1), all 14 one text part with the pinned opening and closing.
