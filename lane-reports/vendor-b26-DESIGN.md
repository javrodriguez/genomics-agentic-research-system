# Design: vendor-b26 (the Gemini history-rewrite road and the $patch tightening; Gap Study round 4)

Append-only.
Designer: a Claude Opus 5.5 sub-agent of glitch-26, on the Mac; design only (no code, no test changed, nothing pushed, merged or run on athena).
Clone: /Users/javrodher/aegis-builds/vendor-b26-20261021, branch lane/vendor-b26-20261021, base a76d86f9f35944fbb76f9fe4e09135d3d0e8b43b (B25's head, under review).
Written Wed 21 Oct 2026 from 13:14 EDT (`date`).

## Sources and evidence

- The pinned package, re-extracted for this lane: B25's downloaded tarball copied into the session scratchpad (b26/pkg-dl), sha256 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6, extracted with `tar -x` only into b26/pkg.
- bundle/chunk-NR7L3FXV.js: sha256 d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c (= B25's), 401531 lines; bundle/gemini.js:10 imports it.
- The non-interactive runner: bundle/gemini-Q2GRYIAK.js (the chunk B25 names as loaded by gemini.js:110); its line numbers are cited as Q2G:<n>.
- Every bare `:<n>` below is a line of chunk-NR7L3FXV.js.
- Walks: `git archive` of every Gemini walk branch of the records clone (36 folders) into the session scratchpad (b26/walks-all; w-g14, w-g32 and w-g47 also in b26/walks), never a worktree; nothing written to the records clone, to B25's clone or to aegis.
- Scratch tools (session scratchpad b26/tools, structure and counts only, never model text): struct.py (record shapes), classify.py and detail.py (each removeIds patch), allpatch.py (every control record of every Gemini walk), proto.py (the two-layer replay of this design, run against this clone's reader through a monkeypatched replay; scratch only, not lane code).
- Every scratch run of more than a single file waited for `mac_slot.py light-ok` (light ok at 13:07:52 and 13:08:32 EDT); nothing ran under a heavy slot because nothing heavy ran.

## Headline: the removeIds patches are not chat compression

B25 read them as chat compression; the bytes and the source say they are the tool-output masking road, a full re-record of the history.
Evidence on the three walks (classify.py, detail.py):

| Walk, snapshot | Patch record | Shape | removeIds (unique) | updates | New messages before it (user/gemini) | Function-response parts in them | Of those, masked | Summary or ack messages |
|---|---|---|---|---|---|---|---|---|
| w-g47 native-turn-2 | 1005 | {removeIds, updates} | 300 (300) | 99 | 200 (100/100) | 208 | 40 | 0 |
| w-g32 native-turn-3 | 878 | {removeIds, updates} | 263 (233) | 50 | 182 (91/91) | 175 | 25 | 0 |
| w-g14 native-turn-4 | 853 | {removeIds, updates} | 321 (252) | 82 | 168 (84/84) | 245 | 20 | 0 |
| w-g14 native-turn-4 | 515 | {orderIds, removeIds, updates} | 1 (1) | 16 | (a resume, not a re-record) | | | |

"Masked" counts parts whose response carries the `<tool_output_masked` tag (MASKING_INDICATOR_TAG, :344663, written by formatMaskedSnippet, :344871-344877).
"Summary or ack" counts user parts opening with `<state_snapshot>` and gemini messages equal to the compression acknowledgement (:337261); there are none.
In each re-record, every message live before the new run is removed (removeIds as a set equals the whole prior logical state, the session context turn included), and the survivors are exactly the new run.
The repeats inside removeIds are all `_response` ids (69 in w-g14, 30 in w-g32): the writer's messageOrder after a second resume lists them twice (B25 ruling 3), and removedIds is that order filtered (:287236), repeats kept.
Every update in a re-record patch has keys {id, toolCalls} and names a removed id.
The fourth patch (w-g14 record 515) is a different road: a resume that drops one prompt (below, "the ignored-prompt resume").

Survey of all 36 Gemini walks (allpatch.py, every control record of every last snapshot): 13 {orderIds, updates}; 1 {orderIds, removeIds, updates}; 3 {removeIds, updates}; 14 `$set {sessionId}`; 5503 `$set {lastUpdated}`; no `$rewindTo`; no `$patch` with a top-level id; no updates-only `$patch`.
In all 36 walks every retained snapshot is a byte prefix of the next one.

## Question 1: what writes `$patch {removeIds, updates}`, when, and what the loader does

### The writer

The only `$patch` write in the chunk is `this.appendRecord({ $patch: patchPayload })` in ChatRecordingService.updateMessagesFromHistory (:287151-287298, the write at :287265).
patchPayload gets `updates` when any message's content or tool result changed (:287256-287258), `removeIds` when any id of the previous messageOrder is missing from the new history (:287236, :287259-287261), and `orderIds` (the whole new history's ids) only when the surviving order differs from the history's (:287248-287249, :287262-287264).
A history turn whose id the recorder does not know is appended first as a new message (:287189-287196); a pure tail rollback writes `$rewindTo` instead (:287250-287253).
So `{removeIds, updates}` is written when the new history drops every old id and the new ids were already appended in history order.

Who hands it such a history: GeminiChat.setHistory (:333750-333762).
It wraps every turn that has no id by recording it first, `recordSyntheticMessage(role, parts)` (:333752-333756), then calls updateMessagesFromHistory (:333761).
recordSyntheticMessage (:286934-286941) goes through recordMessage (:286910-286930) and newMessage (:286901-286909): a fresh random id (:286903); a gemini message also gets `thoughts` (the queued thoughts, here `[]`) and `tokens` (here null) and an undefined `model`, which JSON drops (:286915-286918).
Every new message in the three re-records has exactly those keys: user {id, timestamp, type, content}; gemini {id, timestamp, type, content, thoughts: [], tokens: null}, no model, no toolCalls.

The id-less history comes from GeminiClient.processTurn (:348211), which runs before every model request: `await this.tryMaskToolOutputs(this.getHistory())` (:348251).
GeminiClient.getHistory (:347966-347968) returns GeminiChat.getHistory (:333696-333698), which maps each turn to its bare `content`, dropping ids, after getHistoryTurns (:333702-333712) has stripped thought parts and coalesced consecutive same-role turns for the modern models (`coalesceConsecutiveRoles(stripThoughts2(history))`, :333709; coalesceConsecutiveRoles :334192-334213).
tryMaskToolOutputs (:348592-348597) calls ToolOutputMaskingService.mask (:344672-344810) and, when it masked anything, `this.getChat().setHistory(result2.newHistory)`.
So one masking pass re-records the entire history as fresh synthetic messages, coalesced and with older tool outputs masked, and the recorder then removes every older id: that is the `{removeIds, updates}` patch.

The coalescing is visible in the bytes: the session context turn and the first prompt become one user message of two text parts; a resumed `_response` copy and its original round trip become one user message (w-g47's first re-recorded round trip holds 6 function-response parts for 3 calls).
The dead `updates` come from the second loop of updateMessagesFromHistory (:287198-287229): a new user turn's functionResponse names an old call whose result fingerprint differs (coalesced or masked), so the old gemini message gets a `{id, toolCalls: [{id, result}]}` patch (:287227), in the same payload that removes it.

### When: the trigger and the threshold

Masking (ToolOutputMaskingService.mask, :344672-344810):
- It scans function-response parts from the second-to-last history turn backwards when protectLatestTurn is true (:344682-344683), skipping exempt tools and already-masked parts.
- The newest tool outputs are protected until their estimated tokens pass protectionThresholdTokens; every older output is prunable (:344683-344723).
- It masks only when the prunable total reaches minPrunableThresholdTokens (:344724-344726), replacing each prunable part's response with `{output: <masked snippet>}` when that saves tokens (:344728-344792).
- Defaults: protection 50,000 tokens, minimum prunable 30,000, protect latest turn true (:344660-344662, wired at :380885-380889).
- The live values come from getToolOutputMaskingConfig (:381905-381917): remote experiment flags override the defaults when the server sends them, so the trigger point is set server-side and is not fixed by the pinned package.
- It runs before every model request, the first request of a turn and every tool continuation alike, so a re-record can fall at a turn's start (w-g47 turn 2, w-g14 turn 4: the turn's prompt is recorded just after the patch) or in the middle of a turn (w-g32 turn 3: 80 messages of turn 3 were recorded before the patch and are among those it removes, and the next record after it is the tool-response turn of the last call).

True chat compression is a separate road, unobserved in all 36 walks:
- processTurn calls tryCompressChat (:348245) when context management is off (its default, :380870); ChatCompressionService.compress (:337124-337293) acts only when the last prompt's tokens reach threshold × tokenLimit(model) (:337139-337143), threshold 0.5 by default (:336882) or a configured or remote value (:382401-382410), tokenLimit 1,048,576 for these models (:334569, :334571-334585).
- On success the client starts a new chat over [summary user turn, `Got it. Thanks for the additional context!` (:337255-337264), the kept tail] (:337254-337292, :348563-348580), and the recorder appends the new turns under random ids through updateMessagesFromHistory's newMessage branch (:333167, :333190-333193, :287189-287196), keeping the session context turn's stable id: a `{removeIds, updates?}` patch whose survivors are the context turn plus the new run.
- After a failed compression the next attempt may instead truncate large tool outputs and setHistory them (:337157-337166, :348581-348585), a re-record of the masking kind.

### What the loader does

createJsonlRecordAccumulator (:286309-286455) applies a `$patch` in a fixed order: a top-level `id` patch (:286390-286392), then `updates` (:286393-286399), then `removeIds`, each deleted from the message map (:286400-286414), then `orderIds` (:286415-286453).
A re-record therefore leaves the loader holding only the new synthetic run, followed by whatever is recorded later; the dead updates are applied to messages the same record then deletes.
A message record whose id was deleted earlier would be set again at the end of the map (:286477).

## Question 2: what the session then holds, and what the stream shows

The native session after a masking re-record holds, as the loader reads it: the synthetic run (one user message per coalesced user run, one gemini message per model run; function calls as content parts, not toolCalls; no model; older tool outputs masked to a preview inside `<tool_output_masked>`), then the live records after the patch.
There is no summary message and no new id for anything except the re-recorded run; the session context turn's stable id is gone from the loader's state (it is folded into the first re-recorded user message).
The bytes before the patch are untouched: the file is append-only (every write is appendRecord), and in all 36 walks each snapshot is a byte prefix of the next.
So every original message, with its toolCalls, statuses, result displays and model, is still in the retained file; only the loader's view retires it.

The stream shows nothing of either road.
The non-interactive loop (Q2G:12199-12338) handles Content, ToolCallRequest, LoopDetected, MaxSessionTurns, Error, AgentExecutionStopped, AgentExecutionBlocked and InvalidStream and has no branch for anything else; masking yields no event at all, and compression's ChatCompressed event (:348246-348247) falls through.
The agent-session runner's translator drops ChatCompressed explicitly (:391296-391299).
The stream's tool_use and tool_result records are written as the tools run, before the next request masks anything, so the stream of a masked take is complete as it stands.

## Question 3: what can still be cross-checked, and the admitted shapes

### What survives

| Fact | Across a re-record |
|---|---|
| session id | Kept: the metadata line and every `$set {sessionId}` (B25's rule) are unchanged. |
| sent | Kept: the prompt's original user record is in the bytes before the patch (or after it, when the re-record falls at the turn's start). |
| output (recorded text, tool id, name, args, status, result display, response parts) | Kept: the original gemini records and their toolCalls upserts are in the bytes; the re-recorded copies are lossy (no toolCalls, no status, masked outputs) and are never a fact source. |
| requested model | Kept: the original gemini records carry `model`; the copies do not. |
| what the model was shown after the re-record | Not a cross-check fact: the model saw masked previews; recorded here only as a named property of the take. |

Nothing an interaction needs is lost, because the facts are read from the original records, never from the copies.
For true compression the same holds: the summarised originals stay in the append-only bytes and the summary is a copy, never a fact.

### The design: a two-layer replay

Layer 1 replays as the pinned loader does (the logical state), admitting two more shapes on exact rules and labelling every message: original (recorded live), resume copy (a `_response` record appended by a resume), or re-recorded copy.
Layer 2 is the fact timeline: every original message, at its state just before it left the logical state (or at the end), in first-record order.
The projection (gemini_projection.project) runs on the timeline instead of the logical state; nothing else in it changes, except that resume copies are verified in layer 1 (B25's byte-identity and adjacency rule, same reason strings) and never reach the timeline.
Invariant checked at every patch: the logical order restricted to originals equals their first-record order (else refuse "the native order of original messages changed").

Admitted shape A, the re-record (setHistory of id-less turns; masking, and the truncation road if its image rule is ruled in):
- `$patch` keys exactly {removeIds} or {removeIds, updates}; no orderIds (the writer omits it when the run is already in history order, :287249).
- removeIds a non-empty list of strings, each a live id; its first occurrences, in order, equal the logical state minus the survivors, in logical order; a repeat only of a `_response` id.
- The survivors (live ids not removed) are exactly the trailing run of messages first recorded since the previous `$patch`, non-empty, every id never recorded before.
- Each survivor has the recordSyntheticMessage shape: user {id, timestamp, type, content: a part array}; gemini {id, timestamp, type, content: a part array, thoughts: [], tokens: null}.
- The image check, binding the run to the removed state (the removed messages taken with removeIds' multiplicity, which is the writer's messageOrder): the role runs of the removed state equal the run's messages one for one (coalescing); the function-call ids and names, in order, are equal; in each coalesced user run the set of (id, name) function-response pairs is equal and each re-recorded part equals a removed part of its id or is the masked form `{id, name, response: {output: <string holding "<tool_output_masked">}}`; the user text parts, in order, are equal; the non-empty model text parts, in order, are equal.
- The multiplicity of response parts is not compared: after a second resume the CLI's history holds the synthetic `_response` turn (built from every call's whole-round-trip result, :286158-286188) and the stored copy under one id, which the recorder's map keeps once; the exact multiset would need convertSessionToClientHistory re-implemented and is named, not built.
- Each update is exactly {id, toolCalls: [{id, result: a part array}]}, its id removed by the same patch and each call id one of that message's calls; it is verified and discarded (a dead write), never applied to a fact.
- Effect: every removed original's fact state is frozen as it stood before the patch; the logical state becomes the run, labelled copies.

Admitted shape B, the ignored-prompt resume (w-g14 record 515):
- On resume convertSessionToClientHistory skips a user message whose text (its parts joined, trimmed) is empty or starts with "/", "?", "<session_context>" or "<hook_context>" (isIgnoredUserContent, :286096-286098; :286105-286110), so the next updateMessagesFromHistory removes it.
- w-g14's turn-3 line sent began with "/" (the ledger's turn 3 `sent`, checked by its first character only); the turn-4 resume removed exactly that prompt.
- Admitted: keys exactly {orderIds, removeIds, updates}, after a `$set {sessionId}`; removeIds without repeats, each a live user message that is not the session context turn, not a tool-response turn, has only text parts, and meets that predicate (JavaScript trim, as the projection's `_JS_TRIM`); then updates and orderIds exactly as B25's resume rule, over the remaining messages, in the loader's order (updates, removeIds, orderIds).
- Effect: the removed prompt's fact state is frozen; it stays in the timeline and still opens its interaction.

What refuses, each with its own reason:
- any other `$patch` key set, including orderIds without updates and {orderIds, removeIds} without updates (writer-possible, unobserved; a named false-refusal risk);
- a re-record whose survivors are not the fresh trailing run, that leaves an older message live, that repeats a non-`_response` id, whose removeIds order is not the logical order, or whose image check fails;
- a dead update naming a survivor or a call its message lacks;
- a resume removal of anything but an ignored-content user prompt;
- a retired id recorded again (the loader would re-add it at the end, :286477);
- the true-compression shape (survivors are the session context turn plus a fresh run), named "native chat compression: source-derived, unobserved";
- the original-order invariant broken.

### Source-predicted roads not yet observed (named, not admitted by this design)

1. A resume after a re-record: getInitialChatHistory (:336356-336377) sees a first turn that is not the context id and prepends a fresh context turn under the stable id that the re-record retired, so the recorder appends it again (:287238-287241 forgot it; :287189-287196) and writes orderIds; convertSessionToClientHistory also drops the first re-recorded user message, whose text now starts with "<session_context>" (:286107-286110), so that resume removes it.
   This is the likely shape of any multi-turn take masked before its last turn.
   It needs one extension of shape B (the removed message may be a re-recorded copy whose text starts with "<session_context>") and one exception to "a retired id recorded again" (the context id only, at a resume, on its exact pinned shape).
   Recommendation: observe it before admitting it (one rehearsal walk long enough to mask in turn 1 or 2 with a later turn), then add it with a fixture cut from that walk.
2. True compression (above): refuse by name until observed; if glitch-26 wants it admitted from source, its image rule is the masking rule applied to the kept tail after a user summary message and the exact acknowledgement message, with the context turn surviving under its id.
3. Content truncation after a failed compression: a re-record whose large responses are replaced by formatTruncatedToolOutput's text instead of the masking tag; refused by the image check until its marker is pinned.

### Prototype evidence (scratch only)

proto.py implements shapes A and B and the timeline over this clone's projection, join and history code (replay monkeypatched), on all 36 Gemini walks, at 13:08:32-13:08:35 EDT (`date`):
- w-g47: PASS, 2 interactions (141 tool round trips), history joined over both snapshots.
- w-g14: PASS, 4 interactions (118 tool round trips), history joined over all four snapshots.
- The 32 walks B25 passes still pass (34 PASS in all).
- Still refused: w-g24 (turn killed mid-tool, refused by design) and w-g32 (below).
- Across the history re-reads the prototype admitted 15 re-records and 9 ignored-prompt removals (counts include each snapshot read again by the history join), and saw 405 masked parts, every one in the masked form.
The first version of the image check compared function-response sequences exactly and failed on w-g14 and w-g32; the cause is the second-resume multiplicity named above, which is why the rule compares sets per coalesced run.

### A second road found in w-g32: loop-recovery feedback (outside the brief, for a separate ruling)

w-g32 refuses even before its re-record: its native-turn-2 snapshot already fails B25's projection ("its last model message ends on tool calls"), because turn 2 holds a user message the stream has no line for.
It is the loop-recovery feedback: GeminiClient._recoverFromLoop (:348601-348609) sends `System: Potential loop detected. Details: <detail>. Please take a step back ... without new results.` (:348603) as a new user message when the loop detector first fires, at a request's start (:348275-348285) or after a response (:348355-348357), and the runner writes a stream line only for a repeated loop (LoopDetected, Q2G:12232-12242).
In w-g32 it sits at record 238, directly after a tool-response turn, one text part, keys {id, timestamp, type, content}; it is the only one in the 36 walks (and its coalesced copy inside the turn-3 re-record).
Proposed rule, if glitch-26 rules it in: a user message whose only part is text matching that pinned template with a non-empty detail, directly after a tool-response turn, continues the interaction, is never a sent line and is never compared to the stream; it is counted as a named shape.
Long takes loop more, so leaving it refused selects on length the same way F-B25-1 names.
proto.py with this rule added (`--loop`, scratch only) is reported in the stage note below.

### Option for glitch-26 if the reading above is not wanted

Keep shapes A and B refused, but give the refusal its own outcome: "native history rewritten by the CLI (tool-output masking, or the ignored-prompt resume): not cross-checked", recorded per take and counted per arm, never a hold.
Not recommended: it leaves exactly the long takes without the native cross-check, which is the selection F-B25-1 names, while the bytes needed to cross-check them are already retained.

### Study-side facts worth recording (not reader rulings)

- After a masking re-record the model works from masked previews of older tool outputs; whether and where a take was masked is a property of the take, decided by a server-settable threshold (:381905-381917).
  Proposal: the join's shapes count re-records and masked parts per take, so the study can report it.
- After the ignored-prompt resume the model's later turns no longer see that prompt: in w-g14, turn 4's request history lacks turn 3's "/"-leading line (the resume dropped it).
  Four walks (w-g13, w-g14, w-g31, w-g32) sent a "/"-leading line at turn 3; only w-g14 had a later turn.

### The scanner's copy of the session (check_take)

check_take._gemini_snapshot_records (check_take.py:4089-4107) reads "every copy of a tool result the session file holds" from the replayed logical state.
After a re-record that state holds only masked copies, so the full original outputs (where a leaked line would sit) would no longer be read from the native file.
Under this design it must read the timeline's originals at their frozen states, the re-recorded copies, and the dead updates' results: every copy the bytes hold.
A test for it is in the plan below; check_take is outside this lane's three modules, so this is named for glitch-26's scope call.

## Question 4: tightening the direct-id and updates-only shapes

The pinned writer's one `$patch` (:287265) carries only updates, removeIds and orderIds (:287254-287264); a top-level id, content or toolCalls is never written.
The loader still honours a top-level id (:286390-286392), but that is a reader of older files, not this writer.
gemini_session_replay.replay today admits `set(patch) <= {"id", "content", "toolCalls", "updates"}` (gemini_session_replay.py:156-166): a direct patch, alone or beside updates.
Change: refuse any `$patch` holding id, content or toolCalls at its top level ("a direct-id patch is never written by the pinned recorder (:287254-287265)").

Updates-only is a writer shape (updates with nothing removed and the order unchanged, for example a content-only change through replaceEmptyTrailingUserTurn, :333466-333480), so it stays admitted, but only as the writer writes it:
- each update is a getOrCreatePatch object (:287159-287166): {id} plus content and/or toolCalls, at least one;
- content is the turn's parts array (`turn.content.parts || []`, :287168, :287182), never a string;
- toolCalls is a list of {id, result} with result the user turn's parts array (:287202, :287223-287228);
- update ids are unique within one payload (one patch per id, :287158-287166) and name live messages.
_patch (gemini_session_replay.py:68-85) gains the array checks; the payload check gains uniqueness.

Tests that change, with reasons:
- tests/test_gemini_session_replay.py:28-43 (test_upserts_and_patches_keep_native_order): its update writes a string content and a string result, which the writer never writes; the fixture becomes `content: [{"text": ...}]` and `result: [<functionResponse part>]`, and the two assertions on the patched values follow.
- tests/test_gemini_session_replay.py:45-60 (test_destructive_unknown_and_identity_changes_refuse, the list at :51-56): every listed case still refuses; one case is added, `{"$patch": {"id": "a1", "content": [{"text": "x"}]}}`, a well-formed direct patch on a present message, which the base admits (the red witness for the tightening).
- tests/test_b25_real_shapes.py:241-269 (test_every_other_patch_shape_refuses): "removeIds (destructive)" now meets shape B and refuses for its own reason (the removed id is not an ignored-content prompt); "orderIds with id" refuses as a direct-id patch; "an update to an absent message" keeps its reason if the target is checked before the content type (that order is part of the change).
- tests/test_gemini_projection.py:148 and tests/test_scan_record.py:1758 already use array results in updates-only patches and stay green unchanged.

## Question 5: the test plan

### Fixtures

A B26 cutter (tests/fixtures/b26-rewrites/cut_structure.py, run by hand, never by a test), extending B25's (tests/fixtures/b25-real-shapes/cut_structure.py): same shared string table (equal strings stay equal), same kept keys, and four more rules, each needed for the image check to survive the cut:
1. every string equal to a session-context text maps to B25's synthetic context block, wherever it sits (the first re-recorded user message carries it as its first part);
2. a masked response keeps the pinned wrapper (`<tool_output_masked>\n`, `\n\nOutput too large. Full output available at: `, `\n</tool_output_masked>`) around a synthetic preview and a synthetic path;
3. a user line's first character is kept when it is "/" or "?" (B25's path rule already keeps a leading "/"), so the ignored-prompt predicate survives;
4. a loop-recovery message keeps the pinned template around a synthetic detail (only if that road is ruled in).
PROVENANCE.json records each source file's sha256 against the ledger; the leak check B25 ran (0 hits for the OD57 ruled line's digest on any string or line, 0 strings outside the allowed classes) runs on every fixture before commit.

Fixtures to cut (the last two snapshots and their streams; the first snapshot only where a history join needs it):
- w-g47: native-turn-1, native-turn-2, turn-1 and turn-2 streams (one resume; re-record at turn 2's start).
- w-g14: native-turn-3, native-turn-4, turn-1 to turn-4 streams (a second resume with repeated ids; the ignored-prompt resume; re-record at turn 4's start).
- w-g32: native-turn-2, native-turn-3 and streams, only if the loop road is ruled in (mid-turn re-record; loop feedback).
The source snapshots are 1.0 to 2.5 MB; the cut files should be far smaller, and their sizes go in the lane file.

### Red witnesses (each run against a `git archive` of a76d86f9 with the new tests laid over, as B25 did)

- R1 replay(w-g47 native-turn-2) admits; the logical state is the 200 re-recorded copies then turn 2's records (base: "unsupported native patch operation").
- R2 project(w-g47 native-turn-2) gives 2 interactions and the first equals project(native-turn-1)[0] (base refuses).
- R3 project(w-g14 native-turn-4) gives 4 interactions, the first three equal to project(native-turn-3)'s (base refuses).
- R4 check_session on each fixture with its streams is PASS with the right interaction count; session_history_facts joins every fixture snapshot (base: DISAGREE and refused).
- R5 the facts come from originals: a fixture whose original records before the patch are edited (one recorded text, one tool status) makes the join DISAGREE, while the same edit applied only to the re-recorded copy is refused by the image check (base refuses all four for the patch instead).
- R6 the tightening: the well-formed direct patch, a string content in an update, and a string tool result each refuse (base admits all three).
- R7 the scanner reads an original output that a re-record masked (check_take; base: VendorUnreadable), if glitch-26 puts check_take in scope.

### Mutants (each on a real-shape fixture, each must refuse with its own reason)

- M1 one older id dropped from removeIds (an original left live).
- M2 a survivor that was recorded before the run (not fresh), and a survivor that is not at the run's end.
- M3 a non-`_response` id repeated in removeIds; removeIds out of logical order.
- M4 orderIds added to a re-record patch.
- M5 a survivor with a `model` key, with toolCalls, with non-empty thoughts, or with a string content.
- M6 the image: a function-call id renamed; a function-response part changed but not masked; a masked part without the tag; a user text part changed; a model text changed; a role run split (one image message too many).
- M7 a dead update naming a survivor; naming a call its message lacks; carrying content.
- M8 the ignored-prompt resume removing a prompt whose first character is not "/" or "?"; removing a tool-response turn; removing the session context turn; removing a gemini message; repeating the removed id.
- M9 a retired original id recorded again after the patch.
- M10 an orderIds permutation that moves an original before an earlier original (the timeline-order invariant).
- M11 the true-compression shape, built from the source (context turn surviving, a summary user message and the exact acknowledgement first in the run): refused by name.
- M12 a resume copy made non-identical, or moved after its original (B25's copy cases, now raised by the replay with the same reasons).
The existing B25 and earlier suites run unchanged except the three files named in question 4; the survey (every committed walk) is re-run on the lane head and recorded.

## Stage note: the loop-rule prototype

`proto.py --loop`, the same prototype plus the loop rule (the feedback message set aside from the timeline; the proposed rule keeps it as a named non-interaction item instead), waited for light-ok from 13:17 and ran 13:32:38-13:32:41 EDT (`date`):
- w-g32: PASS, 3 interactions (97 tool round trips, one interaction with two text segments), history joined over all three snapshots.
- w-g14 and w-g47 unchanged (PASS); 35 of 36 PASS in all; the one refusal left is w-g24, the turn killed mid-tool, refused by design.
- Counts over every snapshot the history join re-reads: 21 re-records, 9 ignored-prompt removals, 9 loop-feedback messages set aside, 555 masked parts, every one in the masked form.

## Open questions for glitch-26

1. Rule shapes A and B in (recommended), or take the named-outcome option.
2. Rule the loop-recovery road (w-g32) in, or name it; it is outside this brief but refuses on the same length selection.
3. Whether to spend one rehearsal walk on athena to observe the resume-after-re-record road before the freeze (recommended; multi-turn measured takes are likely to meet it), and whether true compression stays refused by name until observed.
4. Whether check_take's scanner copy (R7) is in this lane's scope.
5. Whether the image check's set comparison per coalesced run is enough, or the exact multiset (re-implementing convertSessionToClientHistory) is wanted; facts never depend on it either way.
6. Whether to add the byte-prefix invariant between consecutive snapshots to the Gemini history join (it holds on all 36 walks and is what makes the retired originals trustworthy); it touches vendor_provenance.
7. The "/"-leading operator lines: a study-design question (the Gemini resume hides them from later turns), not a reader one.
