# Lane file: vendor-b26 (the Gemini history-rewrite roads; Gap Study round 4)

Append-only.
Builder: a Claude Opus 5.5 sub-agent of glitch-26, on the Mac.
Clone: /Users/javrodher/aegis-builds/vendor-b26-20261021, branch lane/vendor-b26-20261021, base a76d86f9 (B25's head, under review); design commit 312c9aad (lane-reports/vendor-b26-DESIGN.md).
Evidence: the records clone gap4-walk-records-20261019, read by `git archive` of all 74 walk branches (38 w-o, 36 w-g) into the session scratchpad (b26/walks-all); never a worktree of it, nothing written to it.
Pinned source: @google/gemini-cli 0.64.0, tarball sha256 891a794e…, bundle/chunk-NR7L3FXV.js sha256 d566e81b… (re-extracted and hashed in the design stage); bare `:<n>` is a line of that chunk.

## glitch-26's rulings on the design (as received, 21 Oct 2026, before 13:34 EDT)

1. Shapes A (the masking re-record) and B (the ignored-prompt resume) in, as designed: the two-layer replay, every fact read from the originals; "tool outputs masked" a named take property, never a fact.
2. The loop-recovery road in: the injected "System: Potential loop detected..." user message a continuation, never a sent line, on its exact cited shape (:348601-348609); anything else on that shape refuses; "loop feedback injected" a take property.
3. The resume after a re-record, true compression and content truncation stay refused by name; glitch-26 plans the rehearsal walk; not run here.
4. check_take's scanner in scope, with a red witness.
5. The image check: set per run plus equal counts per run (multisets of call ids and function-response ids per run); no re-implementation of convertSessionToClientHistory.
6. The byte-prefix invariant between consecutive snapshots inside the Gemini history join, vendor_provenance's core contract unchanged.
7. The "/"-leading operator line finding written here as study note F-B26-7, with a count; no study change.
8. The tightening in as designed.

### Ruled deviation on ruling 5 (glitch-26's message, quoted)

Raised before building (13:41 EDT): equal counts as written fail on 16 of 3786 coalesced runs (w-g14 and w-g32, every one a run holding a `_response` id the second resume listed twice; the CLI's image holds the synthetic `_response` turn built from every call's whole-round-trip result, n x n parts, :286158-286188, plus the stored copy and the original, so n+2 per id).
glitch-26's reply: "your variant of ruling 5 is accepted. It is equal multisets per run, and the first occurrence of a repeated `_response` id counts the concatenated toolCalls results of its base gemini message. Cite :286158-286188 beside it and record it in the lane file as a ruled deviation, quoting this message. Add mutant witnesses on a repeated-`_response` run, and each must turn DISAGREE: one part too many, one too few, a result from a different call, and a repeat on a non-`_response` id."
Measured before building (scratch prototype, light-ok, 13:37-13:41 EDT): call multisets equal on 3786 of 3786 runs; response multisets with removeIds' multiplicity 3770 of 3786; with the ruled variant 3786 of 3786.
Built: gemini_session_replay._Replay._image, the expected multiset of each run, with :286158-286188 cited in the module docstring; the four mutants are tests/test_b26_rewrites.py RepeatedResponseRun, each asserting check_session DISAGREE with its reason.

## What was built (commits 82d36c5e stage 1, f9e9dde4 stage 2)

- gemini_session_replay.py: the two-layer replay. Layer 1 labels every message original, resume copy or re-recorded copy and admits only the writer's payloads (:287254-287265): {updates} on the writer's patch-object shape (arrays only, one patch per id), {orderIds, updates} (B25's resume, the copy check moved here with its reason unchanged, plus the originals' first-record order kept), {orderIds, removeIds, updates} only inside a resume and only for ignored user prompts (shape B), {removeIds} or {removeIds, updates} as the re-record (shape A: survivors the fresh trailing run on the recordSyntheticMessage shape, removeIds in the loader's order with repeats only of `_response` ids, dead updates verified and never applied, the image check). Layer 2, `timeline`, is the originals frozen at their state before removal, in first-record order. Also returned: `copies` and `dead_results` (for the scanner) and `properties` (history_rewrites, tool_outputs_masked, ignored_prompt_resumes).
- Refused by name (ruling 3): a retired id recorded again (the resume after a re-record), a resume dropping a re-recorded context copy, the context turn surviving a re-record (true compression), a re-recorded response neither original nor masked (content truncation); a top-level id, content or toolCalls in a $patch (ruling 8).
- gemini_projection.py: facts from `timeline`; the loop-recovery message on its exact shape after a tool-response turn continues its interaction, anything else opening with the template refuses; project_with_properties adds loop_feedback_injected.
- native_reader_registration.py: join_session's PASS carries `properties` (take_properties, never facts); gemini_snapshot_prefixes and gemini_history (the byte-prefix invariant, then session_history_facts); acceptance_problems runs the prefix check for Gemini.
- drive.py edit F (ruling 6, production): native_history_record runs gemini_snapshot_prefixes after the history join for a Gemini take; recorded in tests/check_vendor_sources.py as edits D and E are (EDIT_F, EDIT_F_RULING "B26-6", POST_EDIT_F_DRIVE_SHA256 4f869701…5777f computed and written by one script, never typed; F taken out first, edit E's pin unchanged under it); tests/test_vendor_envelopes.py's EditD and EditE read it and a new EditF class pins and names it (each hunk taken out, and a moved line, go red).
- check_take.py (ruling 4): _gemini_snapshot_records reads the timeline's originals, every copy and every dead update's results.
- Tests changed, with reasons: test_gemini_session_replay.py (an update's string content and result become the writer's arrays; a well-formed direct patch added to the refusals); test_b25_real_shapes.py (two reason strings: the destructive removeIds variant now meets shape B's own refusal, the orderIds-with-id variant the direct-id refusal).
- COPIED.d/vendor-admission.json: 18 "new" entries appended (90 insertions, no line moved).

## Stage notes

### B25's review folded in (glitch-26's word; REVIEW-vendor-b25-a76d86f.md, CHANGES, three minors), stage 3 commit 7fd8cf19

- MINOR 1 (drive.py:2617-2619 and :3219 at a76d86f, edit E's forwarding): tests/test_pending_codex_walk.py CodexCrossCheckRefusesInTheDriver; CodexBox gains `skew` ("sent" or "model") and rollout() a `model` argument; a rollout whose UserMessage or turn_context model is not what was launched leaves cross_check_status refused, the reason naming sent or model.
- MINOR 2 (gemini_projection.py:346 at a76d86f, the copy's key set): the copy check now lives in the replay's resume reorder (`set(following) == set(copy)`); tests/test_b26_rewrites.py B25ReviewGaps adds an original carrying displayContent its copy lacks, refused "not the resumed copy".
- MINOR 3 (gemini_session_replay.py:109 at a76d86f, the base clause): B25ReviewGaps adds a `u1_response` repeat whose base is a user message, refused; and a `_response` id is now capped at two listings, in orderIds and in a re-record's removeIds, because a resumed history holds it once as the synthetic turn (:286180-286188) and once as the stored copy read back as a user turn (:286105-286117), and the recorder's map keeps one message per id; the real second resume (w-g31, two listings) still reads, a third listing refuses.
- NIT 4 (native_reader_registration.py:185 with drive.py:2618 at a76d86f), recorded only: on the executed-refusal road the ledger rows outnumber the turns, so the production refusal reads "not one exit code and one sent line per stream" rather than a turn-count reason; it still refuses.
- NIT 5 (gemini_stream_join.py:148), recorded only: the model comparison still skips when no native gemini message carries `model`; it never skips on the committed walks (the reviewer's probe: 0 of 40 streams), and the acceptance write-up should say so plainly.

Mutation check of the new witnesses (scratch archive of 7fd8cf19, each mutant restored from a byte backup; the drive mutant in a scratch git clone because test_pending_codex_walk needs a checkout), 13:52-13:53 EDT:
- copy key-set clause dropped: B25ReviewGaps "FAILED (failures=1)";
- base-is-gemini clause dropped: "FAILED (failures=1)";
- the two-listing cap dropped: "FAILED (failures=1)";
- the ruled count variant dropped (removeIds multiplicity only): test_b26_rewrites "FAILED (failures=3, errors=4)";
- image counts weakened to sets: RepeatedResponseRun "FAILED (failures=2)";
- the dead updates applied before freezing: Rerecord "FAILED (failures=4, errors=2)";
- drive.codex_cross_check handing the join the rollout's own sent and model (the reviewer's self-compare mutant): CodexCrossCheckRefusesInTheDriver "FAILED (failures=2)" while the positive CodexCrossCheckInTheDriver stays green, so this mutant is no longer caught only by the byte pin.

## F-B26-7, study note: "/"-leading operator lines (ruling 7; no study change in this lane)

On resume the Gemini CLI drops from the model's history any user prompt whose text, trimmed, is empty or starts with "/", "?", "<session_context>" or "<hook_context>" (isIgnoredUserContent, :286096-286098; convertSessionToClientHistory skips it, :286105-286110), and the next updateMessagesFromHistory removes it from the session (w-g14 record 515).
So on the Gemini arm a "/"-leading operator line is seen by the model in its own turn but is gone from the history of every later turn; Codex and Claude are not affected by this code.
Count over every sent line of all 74 committed walks (the ledgers' turns[].sent): 10 of 139 start with "/", none with "?"; Gemini w-g13, w-g14, w-g31, w-g32 (each turn 3, conditional-yes); Codex w-o13, w-o14, w-o29, w-o30 (turn 3, conditional-yes), w-o32 (turn 2, confounded-design), w-o41 (turn 2, scope-read).
Only w-g14 had a later turn, so it is the one Gemini walk where the effect occurred.
In the task and variant JSON files, the only "/"-leading string literals are grader templates and run_tree paths; the "/"-leading sent lines are operator answers built at run time (for example conditional-yes's turn 3 answering a raw-data-path question with a path); I did not trace the builder that writes them.

## Runs (`date` at each step)

Mac slot: heavy slot acquired 13:44:41 (`mac_slot.py acquire --kind heavy --owner vendor-b26 --minutes 60 --wait 1200 --needs-mac "reader fixes read the local records clone's committed walks"`, after waiting on the thermal gate from 13:41); this acquire did not carry `--work gap-study-r4`, which glitch-f1's tick then flagged; any later heavy acquire will carry it.
Released 14:01:54 (`released: .machine-slots/vendor-b26`) on glitch-26's word that it blocked the qwen GPU booking: the first battery pass was stopped by pid mid test_vendor_walk_road (started 13:58:40), and everything after ran as light work, one module at a time, each behind `light-ok`.
Before the slot, only light-ok-gated scratch runs ran (the ruling-5 measurement, 13:37-13:41).

### Red (the new and changed tests over a `git archive` of a76d86f9), 13:48:16-13:48:19

test_b26_rewrites, test_gemini_session_replay, test_b25_real_shapes: "Ran 52 tests", "FAILED (failures=37, errors=10)"; every re-record, resume-removal, loop, scanner, prefix and tightening witness among them.
Deviation, reported: the code was drafted before the tests (as in lane vendor-b25); the red is that base-archive run.
The stage-3 review witnesses pin clauses the base already had (MINORs 1, 2 and the base clause of 3), so their evidence is the mutation check above; the two-listing cap is new and red on the base.

### Green, on the lane head

- Heavy slot, 13:47-13:58 (stage 2, then stage 3 for the replay cap only): test_b26_rewrites 31 OK (13:49:07), test_b25_real_shapes 18 OK, test_gemini_projection 8 OK, test_gemini_stream_join 9 OK, test_gemini_session_replay 3 OK, test_codex_native 15 OK, test_vendor_envelopes 11 OK, test_freeze_shapes 9 OK, test_native_reader_registration 7 OK (13:49:56-13:51:16, stage-2 code), test_native_history_record 3 OK, test_vendor_take_records 4 OK, test_vendor_provenance 6 OK, test_pending_walk 23 OK (13:51:26-13:54:48), test_pending_codex_walk 12 OK (13:51:06-13:52:09 and 13:54:48-13:55:57, stage 3), test_vendor_admission 10 OK, test_vendor_admission_regrade 3 OK, test_walk_grade_seam 4 OK, test_walk_recheck 17 OK (13:56:32-13:58:40).
- Light, behind light-ok, on the stage-3 head 7fd8cf19, 14:02:05-14:04:42: test_vendor_check 26 OK; test_take_checker_dispatch 5 OK; test_recheck_coverage 5 OK; test_vendor_constants 10 OK; test_codex_patch_reads 13 OK; test_codex_started_file_change 5 OK; test_freeze_shapes 9 OK; test_vendor_envelopes 11 OK; test_b26_rewrites 34 OK; test_b25_real_shapes 18 OK; test_gemini_projection 8 OK; test_gemini_stream_join 9 OK; test_gemini_session_replay 3 OK; test_codex_native 15 OK; test_native_history_record 3 OK; test_vendor_provenance 6 OK; test_vendor_take_records 4 OK; test_scan_record's 34 Gemini tests (selected by id) OK.
- Waiting for a heavy slot (each longer than light work allows): test_vendor_body (stopped by its 40-second cap at 14:02:51, no verdict), test_vendor_walk_road (stopped with the slot), the whole of test_scan_record, test_native_reader_registration on the stage-3 head (it passed on stage 2; stage 3 changed only the replay's repeat cap and tests), and the modules lane vendor-b25 also ran (test_pipeline, test_agent_tool, test_egress, test_nested_agent, test_no_output_nudge, test_codex_adapter); athena's battery after review covers the whole suite.
- `git status --short` after every run: only this lane file untracked.

### The survey, every committed walk, no filtering

`python3.12 -I -B survey26.py <code> <walks>` (scratch b26/survey26.py, sha256 0fd65dae8f555f45…: lane vendor-b25's survey.py with the Gemini history join through native_reader_registration.gemini_history when the code has it, and the take properties printed), over `git archive` copies of all 74 walk folders, under the heavy slot.

| | Base a76d86f9 (13:45:21) | Lane head 7fd8cf19 (13:53:20) |
|---|---|---|
| Codex (38) | 38 PASS; history 38 joined; 25 meet the floor | 38 PASS; history 38 joined; 25 meet the floor |
| Gemini (36) | 32 PASS; 3 DISAGREE "unsupported native patch operation" (w-g14, w-g32, w-g47); 1 DISAGREE incomplete (w-g24) | 35 PASS; history 35 joined; 9 meet the floor; 1 DISAGREE (w-g24) |

The base column reproduces lane vendor-b25's survey and its review's.
The one refusal left is w-g24, by name: "native interaction is incomplete: its last model message ends on tool calls" (outcome timed-out, exit 124; a turn killed mid-tool, NEVER_COUNTED).
Take properties on the head: w-g14 {history_rewrites 1, tool_outputs_masked 20, ignored_prompt_resumes 1, loop_feedback_injected 0}; w-g32 {1, 25, 0, 1}; w-g47 {1, 40, 0, 0}; every other walk all zero.
The floor now also counts w-g14, w-g32 and w-g47 (9 Gemini walks: w-g13, w-g14, w-g21, w-g31, w-g32, w-g39, w-g40, w-g47, w-g48).

## Stop for review: Wed 21 Oct 2026

Open for glitch-26 and glitch-f1:
1. The properties live in join_session's PASS dict (`properties`), which the acceptance check and the survey read; drive.gemini_cross_check still records only {status, why} in the driver ledger, so carrying the properties into the ledger needs a further drive.py edit (another pinned edit), not made here.
2. The rehearsal walk for the resume after a re-record (ruling 3) is glitch-26's; the replay refuses that road by name today.
3. The modules listed as waiting for a heavy slot.
4. The reader still refuses orderIds-only and {orderIds, removeIds} without updates, which the writer could write but no walk shows (a named false-refusal risk, as in the design).

## The fold of REVIEW-vendor-b26-04c4e77 (VERDICT: CHANGES), stage 5 commit 75b7655d

Fold builder: a Claude Opus 5.5 sub-agent of glitch-f1 (the Lane-orchestrator), under Javier's standing delegation; the lane's first builder released, this builder the only writer of the clone from 14:26 EDT Wed 21 Oct 2026.
Rulings folded: glitch-f1's six on that review (21 Oct 2026), as briefed.
Scratch: /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/fold (base/ and red/ are `git archive` copies of 04c4e774's evals/, head/ a copy of the working tree, walks/ `git archive` copies of the eight walk commits the review names).
Nothing was written into the reviewer's clone, nothing run on athena, nothing pushed or merged.
Every run below sat behind `mac_slot.py light-ok --work gap-study-r4` (rc 0), one module or class per process, each capped at 45 s.

### What changed, ruling by ruling

1. MAJOR 1 (the scanner witness): tests/test_b26_scanner.py, ScannerReadsEveryCopy, the reviewer's scratch witness folded in and tightened: every tool of every frozen original that carries toolCalls, every part of every dead re-record update, and every part of every copy tool-response turn must be read, each by the record's own `where`.
   Claimed in COPIED.d/vendor-admission.json (one "new" entry appended after the last b26 entry; no line moved).
   The stage-1 Scanner class stays as it was.
2. MINOR 2 (calls in full): gemini_session_replay._calls returns (id, name, canonical arguments) for an original's toolCalls and a copy's functionCall parts, so the image's call multiset binds the arguments; module docstring updated.
   Witness: test_b26_rewrites.FullCalls (a w-g47 re-recorded copy whose one call gains a synthetic argument: refused "function calls differ"; the three real fixtures still replay with one re-record each).
3. MINOR 3 (shape B): the shape-B branch now checks the removed ids first, then refuses any update naming one: "a resume updates the prompt it removes (the recorder writes content patches only for history turns, chunk-NR7L3FXV.js:287167-287183, and a removed prompt is not one)"; then applies the updates and retires the removed prompts.
   The ignored-prompt predicate therefore reads the removed prompt before the updates; with no update allowed on a removed id the two readings are the same message, and an update that would have turned a plain prompt into a "/"-leading one before its removal now refuses.
   Witness: ShapeBUpdateOnRemoved (the reviewer's P5 on w-g14: refused, the reason carrying :287167-287183).
4. MINOR 4 (the unobserved resume shapes): UNOBSERVED_RESUME_SHAPES, three named reasons, checked while the resume window is open: {orderIds} ("a resume with no update"), {orderIds, removeIds} ("an ignored prompt dropped, no update"), {removeIds, updates} inside a resume ("an ignored prompt dropped, the order unchanged"); each says "writer-possible ..., unobserved in any walk: refused by name (glitch-f1's ruling 4)".
   Witnesses: UnobservedResumeShapes, one per shape, each cut from w-g14's shape-B patch.
   Implementation choice, flagged: the resume window (`self.resume`) now closes at the resume's $patch whatever its shape; before, only a reordering patch closed it, so an updates-only resume patch would have left it open and this check would have refused a later masking re-record by the resume-shape name.
   The module's own comment already defines the window as "after $set {sessionId}, before its $patch".
   Over every Gemini walk's last snapshot (36, read from git blobs of the records clone, 14:29:03-14:29:07): 13 resume patches {orderIds, updates}, 1 {orderIds, removeIds, updates}, 0 updates-only, and all 3 re-records outside a resume, so the change moves no walk.
   Witness: UnobservedResumeShapes.test_the_window_closes_at_the_resume_patch (an updates-only resume patch, then {orderIds}: refused "unsupported native patch operation", not the resume-shape name).
5. MINOR 5 (the loop closing check): LoopFeedback's "another closing" case is now LOOP_OPEN, then len(LOOP_CLOSE) + 10 characters, then ". Other.", asserted longer than LOOP_OPEN + LOOP_CLOSE, so only the closing check refuses it.
6. NIT 6 (the re-record listing cap): RerecordListingCap (a third listing of a twice-listed `_response` id appended to w-g14's re-record removeIds: refused "native re-record lists a <gemini id>_response turn more than twice").

Changed test, with its reason: tests/test_b25_real_shapes.py test_every_other_patch_shape_refuses, case "orderIds without updates", now expects "writer-possible resume shape {orderIds} (a resume with no update)": that case sits inside w-g21's resume, so ruling 4 names it (the review's "orderIds-only admitted" mutant counted on this very case).

### Recorded only (rulings NIT 7 and NIT 8, with the reviewer's reasoning)

- NIT 7, shape B's ORIGINAL clause (gemini_session_replay.py, `self.kind[i] == ORIGINAL` in _ignored_prompts) is untested but outcome-neutral: dropping it leaves every test green, yet the only road to a removable re-recorded copy is the resume after a re-record, and that road records the retired context id first, which refuses ("a retired native message id is recorded again") before its $patch is read.
- NIT 8, a dead update's toolCalls ids are not checked for uniqueness (the dead-update loop in _rerecord): the writer writes one entry per call id (:287219-287224), and it is outcome-neutral because dead results are never applied to a fact and the scanner reads every one of them.
- NIT 9 (take properties per take via take_properties at the freeze) is the orchestrator's freeze checklist, not this fold.

### The false-refusal residual (glitch-f1's ruling 4; the orchestrator's 14:08 ruling)

Three resume $patch shapes the pinned writer can write (:287254-287265 writes each key only when it has entries) are seen in no committed walk and stay refused, now each by its own name so a survey counts them apart from corrupt files: {orderIds}, {orderIds, removeIds}, and {removeIds, updates} inside a resume.
By :286764-286783 and :286120-286150 a resume writes a content update for every gemini message that carries thoughts or tool calls, so the update-less shapes need a take with neither, which no agent take in the study has shown (the review's finding 4).
Noticed while folding, outside the rulings, for glitch-f1: {removeIds} alone inside a resume is writer-possible by the same reasoning (an ignored prompt dropped, no update, the order unchanged) and is also unseen in the 36 Gemini walks; it still refuses, but under the shape-A reason "native re-record leaves an older message live, ..." (probe on w-g14's shape-B patch cut to {removeIds}, 15:12:06), not by name.
Not folded: naming it would be a fourth reason the rulings did not list; it is one line in UNOBSERVED_RESUME_SHAPES if glitch-f1 wants it.

### Red before green (`date` at each step)

- Red on 04c4e774 (the new tests laid over a `git archive` of 04c4e774's evals/), 14:32:25: test_b26_rewrites "Ran 42 tests", "FAILED (failures=5)": FullCalls.test_an_argument_changed_in_a_copy_only, ShapeBUpdateOnRemoved.test_an_update_on_the_removed_prompt, and the three UnobservedResumeShapes shape tests; every other test green there (the code they pin was already right).
  test_b26_scanner on 04c4e774, 14:32:29: "Ran 3 tests", "OK" (the scanner code was right; its red is by mutant, as ruled).
  The changed test_b25_real_shapes case expects a reason 04c4e774 does not give ("unsupported native patch operation" there), so it is red on the base by construction.
- Red by mutant on this head (scratch head/ copy, identical to the working tree by `diff -rq` before and after; each mutant one edit, the named test in its own process, the file restored from its byte backup and its sha256 checked equal), 14:32:47-14:32:50:
  - R1a the scanner reads `replayed["messages"]` instead of the timeline: test_b26_scanner "FAILED (failures=1)"; restored sha256 832c9a6f247c30ba... == before;
  - R1b the scanner skips the dead-update results: "FAILED (failures=1)"; restored == before;
  - R1c the scanner skips the copies: "FAILED (failures=1)"; restored == before;
  - R2 calls compared by (id, name) only: FullCalls "FAILED (failures=1)"; restored sha256 f556600399f1dde1... == before;
  - R3 the shape-B update check off: ShapeBUpdateOnRemoved "FAILED (failures=1)"; restored == before;
  - R4a the named resume-shape check off: UnobservedResumeShapes "FAILED (failures=3)"; restored == before;
  - R4b the resume window left open after a patch: UnobservedResumeShapes "FAILED (failures=1)"; restored == before;
  - R5 `endswith(LOOP_CLOSE)` dropped: LoopFeedback "FAILED (failures=1)" (it survived at 04c4e774, the review's finding 5); restored sha256 b80cdfaebf360943... == before;
  - R6 the re-record two-listing cap dropped: RerecordListingCap "FAILED (failures=1)"; restored == before.
- Ruling 2 on the real walks (scratch tools/argscount.py, the image check wrapped to count, over the head code and `git archive` copies of the walks, 14:33:09): w-g14 84 image calls, w-g32 92, w-g47 104, 280 in all; 0 differ in full (id, name, arguments), 0 differ in (id, name); each replay admitted with the same properties as before (w-g14 {1, 20, 1}, w-g32 {1, 25, 0}, w-g47 {1, 40, 0}).

### Green on this head (the working tree that became 75b7655d; only COPIED.d and test_b25_real_shapes changed after 14:33, and the modules they touch were re-run after)

- 14:34:19-14:47:39: test_b26_scanner 3 OK; test_b26_rewrites 42 OK; test_gemini_projection 8 OK; test_gemini_stream_join 9 OK; test_gemini_session_replay 3 OK; test_codex_native 15 OK; test_native_history_record 3 OK; test_vendor_provenance 6 OK; test_vendor_take_records 4 OK; test_scan_record's 34 Gemini tests (`-k gemini -k Gemini`) OK; test_vendor_check 26 OK; test_take_checker_dispatch 5 OK; test_recheck_coverage 5 OK; test_vendor_constants 10 OK; test_codex_patch_reads 13 OK; test_codex_started_file_change 5 OK; test_vendor_envelopes 11 OK (30.9 s); test_vendor_admission 10 OK; test_vendor_admission_regrade 3 OK (35.4 s); test_walk_grade_seam 4 OK.
  In that pass test_b25_real_shapes was "FAILED (failures=1)" (the ruling-4 reason change above) and test_freeze_shapes "FAILED (failures=1)" ("tests/test_b26_scanner.py is under evals/gap-study-4/ and no fragment in COPIED.d/ claims it"); both fixed before the commit.
- 14:49:52-15:11:26, after those two fixes: test_b25_real_shapes 18 OK; test_freeze_shapes 9 OK (31.4 s); test_native_reader_registration CheckSession 4 OK and NoRecord 1 OK.
  test_native_reader_registration ManifestClaim was stopped by its 45-second cap at 15:05:23 with no verdict (the Mac was thermally held at CPU speed limit 37 to 45 from about 14:44; it ran under the heavy slot at stage 2).
- `git status --short` before the commit: only the five files committed.

### The survey, eight walks, one walk per process, on this head

`python3.12 -I -B survey26.py` (copied from /Users/javrodher/aegis-builds/glitch-26-carry-20261021/b26/survey26.py, sha256 0fd65dae8f555f452d440e486e81bdce82e0602d41bf63aedd08e7d6bac499ea as the lane records) over this head's evals/gap-study-4 and my own `git archive` copies of the eight walk commits the review names, 14:33:19-14:33:23:
- w-g14 PASS, 4 interactions, history joined, floor met, {history_rewrites 1, tool_outputs_masked 20, ignored_prompt_resumes 1, loop_feedback_injected 0};
- w-g32 PASS, 3, joined, floor, {1, 25, 0, 1};
- w-g47 PASS, 2, joined, floor, {1, 40, 0, 0};
- w-g24 DISAGREE, refused by name: "native interaction is incomplete: its last model message ends on tool calls" (history refused for the same reason);
- w-g31 PASS 3, w-g13 PASS 3, w-g40 PASS 2, each joined and floor met, no properties printed (all zero);
- w-o29 (Codex) PASS 5, joined, floor met.
The same verdicts and properties as the reviewer's head run: Gemini 6 PASS, only w-g24 refused by name; Codex 1 PASS.
The full 74-walk survey was not run: `mac_slot.py run --kind heavy --work gap-study-r4 --owner vendor-b26-fold --minutes 15 -- <archive all walks, then survey26>` at 14:33:37 returned rc 3, "busy: the machine is booked (.machine-reserved)" (the timed run booked until about midnight), as expected; the script is scratch tools/full74.sh.

### Left for athena (heavier than light work allows; not run here)

test_native_reader_registration ManifestClaim (and so that module whole), test_pending_walk, test_pending_codex_walk, test_walk_recheck, test_vendor_body, test_vendor_walk_road, the whole of test_scan_record, and lane vendor-b25's list (test_pipeline, test_agent_tool, test_egress, test_nested_agent, test_no_output_nudge, test_codex_adapter); athena's battery of the whole suite at this head covers them.
The orchestrator's queued athena battery pins 04c4e774 and is untouched by these commits.

## Stop for review of the fold: Wed 21 Oct 2026

Head: stage 5 75b7655d, then this lane file as stage 6.
Open for glitch-f1: the {removeIds}-alone resume shape (above), refused but not by name; the 74-walk survey and the heavy modules under a heavy slot or on athena.

## Stage 7 commit dfdce120: the fourth unobserved resume shape named (glitch-f1's ruling on the fold's question, 21 Oct 2026)

glitch-f1's ruling, as received: "yes, name it. A resume patch carrying only {removeIds} is writer-possible for the same reason as the three ruled shapes and unseen in every walk, so it gets its own named refusal reason in UNOBSERVED_RESUME_SHAPES, so a survey counts it."
The same message accepted the flagged choice (the resume window closes at the resume's $patch, whatever its shape) as recorded, for the closure reviewer to check.

The false-refusal residual is now four shapes, each refused by its own name while the resume window is open: {orderIds}, {orderIds, removeIds}, {removeIds, updates} inside a resume, and {removeIds} alone inside a resume ("writer-possible resume shape {removeIds} alone inside a resume (an ignored prompt dropped, no update, the order unchanged), unobserved in any walk: refused by name (glitch-f1's ruling 4)").
Outside a resume, {removeIds} and {removeIds, updates} remain the masking re-record (shape A), unchanged.

Evidence (`date`, each behind light-ok, one process each, 45-second cap):
- Red on f7f868cf (the new test laid over a `git archive` of f7f868cf's evals/), 15:17:18: UnobservedResumeShapes "Ran 5 tests", "FAILED (failures=1)", test_remove_ids_alone_inside_a_resume, refused there as "native re-record leaves an older message live, or its survivors are not the messages recorded just before it".
- Mutant on this head (the entry's key changed so it never matches; byte-backed scratch copy, restored, sha256 c6e2d85e9eb42098... == before; the copy identical to the working tree after by `diff -rq`), 15:17:19: UnobservedResumeShapes "FAILED (failures=1)".
- Green on this head, 15:17:22-15:17:31: test_b26_rewrites 43 OK; test_b25_real_shapes 18 OK; test_gemini_session_replay 3 OK; test_b26_scanner 3 OK; test_gemini_projection 8 OK.
- Eight-walk survey on this head, one walk per process, 15:17:38-15:20:49: unchanged; w-g14, w-g32, w-g47, w-g31, w-g13 and w-g40 PASS with the same properties; w-g24 refused by name; w-o29 PASS.
- The 74-walk survey and the athena list are as in the stop above.

## Stop: Wed 21 Oct 2026, head after this lane file (stage 8)
