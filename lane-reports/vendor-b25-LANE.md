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
