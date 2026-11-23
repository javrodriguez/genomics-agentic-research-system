# Design: vendor-b28, the Gemini reader batch before the Gap Study round 4 freeze (21 Oct 2026)

Design only.
Designer: an Opus 5.5 lane agent of glitch-f1 (Lane-orchestrator), under Javier's standing delegation.
Written Wed 21 Oct 2026, 21:42 EDT (`date`).
No code or record was changed, nothing was committed in any study clone, nothing ran on athena.
Every Mac step was light work behind `mac_slot.py light-ok --work gap-study-r4`.
Bare `:<n>` is a line of the pinned bundle/chunk-NR7L3FXV.js (sha256 d566e81b…, from the tarball sha256 891a794e…, extracted with `tar -x` into /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/b28pkg and never executed).
`R:<n>` is a line of evals/gap-study-4/gemini_session_replay.py at 5457e75e (`git show`).
The evidence note is /Users/javrodher/aegis-builds/b27-smoke-20261021/EVIDENCE-NOTE-road-a.md (cited as EN).

## The batch in eight lines

1. Scope, as glitch-f1 ruled at 21:19 (night log, "B27 RULINGS"): road (a) on its exact observed shapes, plus F-B26-9 as ruled at 15:45; no `_walk_commit` change; roads (b) and (c) stay refused by name, with residuals written down.
2. One READER_SOURCES file changes: gemini_session_replay.py. It is not in CODEX_SOURCES, so only the Gemini reader re-accepts.
3. Base: 5457e75e on accept/m2-20261021 (recommended), merged onto the freeze line by exact SHA before the Gemini reader review and the kit.
4. A scratch prototype of the rules below (not in any clone) gives these results. A1, A2 and A3 are admitted with history joined. B1 and B2 are refused under the compression name. C1 keeps its truncation name and C2 is admitted. The 50 native snapshots of the 36 committed Gemini walks replay with no difference from 5457e75e. F-B26-9's witness flips on all three real fixtures.
5. The prototype found one gap the build must close: a second context record inside one resume was silently accepted (mutant M4 below).
6. F-B26-9 also changes the precedence finding. B1 is now refused under the compression name rather than the resume-shape name, so ruling (1)'s precedence residual becomes historical (open call O3).
7. B27's probe code merges onto the freeze line with the batch: yes, if B27 stage 8 passes its closure review before b28's build review (trade-off in section 9).
8. Size: about 6 to 9 builder hours, plus one review round (or two), one athena battery, the Gemini reader review, the kit rebuild and its review, then Javier's sitting. Section 12.

## 1. Base

- Recommended: 5457e75ec115151b6bdcb463242fc63c74033fdb (accept/m2-20261021 in /Users/javrodher/aegis-builds/gap4-walk-records-20261019; read with `git rev-parse` at 21:42). New branch lane/vendor-b28-20261021 in a fresh clone, never in the records clone.
  - Its reader code equals the B26 head 9e91dd34 byte for byte. gemini_session_replay.py, native_reader_registration.py, gemini_projection.py, vendor_record_binding.py and transcript_view.py were hashed and are identical. The only differences are the acceptance files and the walk merges (`git diff --stat 9e91dd34 5457e75e`, outside rehearsals/: native-readers/ only).
  - B27's lane is based on 9e91dd34 (`git merge-base`), so it merges cleanly onto 5457e75e.
- The alternative is the freeze line, freeze/r4-20261021, once the vendor walks merge. It does not exist yet (`git branch --list 'freeze*'`: empty at 21:42).
  - The freeze line's per-merge path guard admits only rehearsals/ paths (freeze-path plan section 2). The batch touches only code, tests, fixtures, checks.d, COPIED.d and lane-reports, so the two never conflict.
- So: build now on 5457e75e and do not wait for the merge. Once the batch passes its review and battery, merge its head onto the freeze line by exact SHA.
  - That merge's diff must touch only the batch's own paths, the inverse of the walk path guard.
  - The Gemini reader review, the acceptance kit and Javier's ACCEPT then run on that freeze-line head. The acceptance binds reader_sources_sha256 at HEAD (native_reader_registration.py:312, :532 at 5457e75e) and the w-g21 register entry. Both are the same on either line, but the record must sit on the line the freeze reads.

## 2. The replay extension for road (a) (gemini_session_replay.py only)

What the records show (EN, "The writers" and "The mapping"). After a masking re-record, the next `-r` resume writes four things:
- `$set {sessionId}` (:286695).
- The context turn re-appended under its stable id, which the re-record retired (:336356-336375 → :287190-287196).
- Zero or more `<gemini id>_response` copies (:286180-286188).
- `$patch {orderIds, removeIds, updates}` (:287254-287265). Here removeIds are the re-recorded user copies whose text is ignored content (:286096-286110): always the context copy, which coalesced the context turn with prompt 1, plus in A2 the "/" prompt's copy. orderIds puts the context id first. updates are content patches on the live original gemini responses.

Masking at the resume's first request (A3; w-g47 in real data) is already shape A and already admitted (R:55-71; A3 snapshot 2 PASS at 5457e75e).
The new part is the resume after it.

### State added to _Replay

- `ctx_retired`: set when a shape-A re-record removes CONTEXT_ID, at `_rerecord` just before `_retire`.
- `ctx_pending`: set when the context turn re-enters, cleared by its resume's patch.
- A new label, `CONTEXT_COPY = "resumed context turn"`, beside ORIGINAL, RESUME_COPY and RERECORDED (R:101).

### Rule 1, the re-entry (in `message`, before the retired-id refusal at R:460-462)

A record whose id is CONTEXT_ID and which is in `retired` is admitted only when all of these hold:
- the resume window is open (after `$set {sessionId}`);
- `ctx_retired` is true;
- `ctx_pending` is false;
- the record has exactly the keys {id, timestamp, type, content} (SYNTHETIC_USER_KEYS, R:94; newMessage :286901-286908);
- type is "user";
- content is a one-element list holding one {text} part, whose text, trimmed with JS_TRIM, starts with "<session_context>" (:336366-336373).

When admitted:
- CONTEXT_ID leaves `retired`;
- its kind becomes CONTEXT_COPY;
- it goes into `live`;
- it is never added to `since`, and its `first` and `frozen` entries are left untouched;
- `ctx_retired` becomes false and `ctx_pending` becomes true.

Any other retired id, and CONTEXT_ID outside these conditions, keeps today's refusal and its name.

New refusal: a CONTEXT_ID record while `ctx_pending` is true is refused as "the context turn recorded twice in one resume". This is the gap the prototype missed (mutant M4).

Why the frozen original stays the fact: `_retire` sends a non-ORIGINAL kind to `others` (R:330-333). So when the next re-record removes the re-entered turn, it lands in `copies` (the scanner reads them, R:481) and never overwrites `frozen[CONTEXT_ID]`. The projection then drops the original context turn from the timeline as before (gemini_projection.py `_session_context`).

### Rule 2, the resume's patch (in `patch`)

Precedence in `patch`, in this order:
1. the direct-id refusal (R:271-273, unchanged);
2. UNOBSERVED_RESUME_SHAPES while the window is open (R:274-275, unchanged);
3. new: while `ctx_pending`, any patch other than {orderIds, removeIds, updates} inside the open window refuses. If it is {removeIds} or {removeIds, updates}, `_rerecord` runs first so that true compression keeps its own name (R:371-374). Otherwise the refusal is "a context turn re-entered after a re-record is not consumed by its resume's {orderIds, removeIds, updates} patch";
4. the existing shape branches.

In the {orderIds, removeIds, updates} branch (R:281-295), when `ctx_pending` is true:
- `_ignored_prompts` keeps checking each removed ORIGINAL exactly as today, and skips RERECORDED ids, which a new `_context_copies(remove)` checks instead.
  - Each removed RERECORDED id must be a user copy whose content is text parts only, and whose joined, trimmed text is empty or starts with an IGNORED_PREFIX (R:97).
  - Exactly one of them starts with "<session_context>".
  - No live RERECORDED user copy with ignored text may stay.
  - This completeness check holds because convertSessionToClientHistory drops every such message (:286105-286110) and the writer removes everything absent from the history (:287236).
- The no-update-on-a-removed-id check (R:287-291), `_updates`, `_retire` and `_resume_order` run unchanged.
- After the reorder, the first live id must be CONTEXT_ID (:336366-336375). New refusal: "the resumed context turn is not first after the resume's reorder".
- Then `ctx_pending` becomes false and the new property `resumes_after_rerecord` increments. `ignored_prompt_resumes` stays for resumes that drop only original prompts.
- `_ignored_prompts`' named refusal for a removed re-recorded context copy (R:345-347) stays for every case where no re-entry happened.

### Rule 3, the end of a snapshot (in `result`)

If `ctx_pending` is still true, refuse: "a context turn re-entered after a re-record without its resume's patch".
The writer writes the re-entry and the patch in one synchronous initialize call (:333190-333192), so a retained snapshot never ends between them.

### F-B26-9, as ruled at 15:45

In `message`, before anything else: if the window is open and the id is neither CONTEXT_ID nor ends with RESPONSE_SUFFIX, close the window.
Keep the existing close at the window's patch (R:301).
Inside a resume the writer appends only those two kinds (:287190-287196 with :286099-286194; B26 closure review, NIT 1).

### The property

`resumes_after_rerecord` joins the `properties` dict (R:484-485).
gemini_projection passes the dict through (`dict(replayed["properties"], loop_feedback_injected=loops)`, gemini_projection.py:456), and native_reader_registration.take_properties passes it on. So neither file changes.
Existing tests assert only per-key values (test_b26_rewrites.py:113-114, :133, :317, :440), so they are unaffected.
The acceptance record's join is {status, interactions} only (native-readers/gemini-acceptance.json at 5457e75e).

### The docstring

The module docstring (R:1-75) gains three things:
- road (a) with these cited lines;
- the F-B26-9 window rule;
- the new refusal names.

The "Refused by name" paragraph (R:72-75) is rewritten to list what stays refused (section 3).

### Predicted verdicts

Measured on the prototype (scratch/tools/proto-b28-replay.diff, sha256 fd9dead9…; run through stub_model_reading.py with `--code` set to the scratch copy, 21:35 EDT):

| Scenario | 5457e75e | After the batch (prototype) |
|---|---|---|
| A1 | PASS, then refused twice: retired id | admitted; snapshots PASS {1,2,0,0}, {2,5,0,1}, {2,5,0,2}; history joined |
| A2 | PASS, PASS, retired id | admitted; snapshot 3 {2,5,0,1}; history joined |
| A3 | PASS, PASS, retired id | admitted; snapshot 3 {2,9,0,1}; history joined |
| B1 | snapshots 2-3 refused as "writer-possible resume shape {removeIds, updates} inside a resume" | refused as "native chat compression (the context turn survives a re-record)" (F-B26-9 closes compression's window at its first new turn) |
| B2 | snapshots 2-3 refused, retired id | refused under the compression name at record 119 (the re-entry at 114 is consumed by Rule 2 step 3 through `_rerecord`) |
| C1 | refused for truncation | unchanged |
| C2 | admitted | unchanged |
| A1-fake (the defective folder) | retired id | replay PASS per snapshot; history refused "native tool call id reused" (projection). This is the probe defect: one fake file replayed in every process |
| smoke A1 (stub-probe-smoke1) | retired id | admitted |

Properties are shown as {history_rewrites, tool_outputs_masked, ignored_prompt_resumes, resumes_after_rerecord}.

## 3. What stays refused

- Road (b), a resume or chat start after true compression: refused under the compression name (R:371-374), whichever key set appears. Both observed sets stay refused: B1's {removeIds, updates} and B2's {removeIds}, the latter with the context turn re-appended first.
- Road (c), content truncation: refused as "neither one of its originals nor masked" (R:447-448), unchanged.
- The four unobserved resume shapes (R:107-121), unchanged, still checked before the new rule (mutant M8).
- Every other unknown shape:
  - a retired id other than CONTEXT_ID;
  - a re-entry outside a window, off its shape, twice, or never consumed;
  - a road (a) patch that keeps an ignored copy, drops a non-ignored copy, drops no context copy or two, or leaves the context turn off the front;
  - any patch key set outside the writer's;
  - each of these by its own name.

## 4. Mutants (each on a probe fixture, each refusing on its own reason)

The prototype's results are in brackets (scratch/tools/mutants.py, sha256 7767fa15…, 21:39 EDT).
A1 means snapshot 2 (re-entry at index 69, patch at 71); A2 means snapshot 3.

- M1, no `$set {sessionId}` before the re-entry → "a retired native message id is recorded again …" [as stated].
- M2, the re-entry with an extra key → re-entry off shape [as stated].
- M3, the re-entry with two parts → re-entry off shape [as stated].
- M4, the context record twice in one resume → "the context turn recorded twice in one resume" [the prototype PASSED it: the build must add this guard].
- M5, the patch without removeIds ({orderIds, updates}) → "not consumed by its resume's … patch" [as stated].
- M6, the context id moved last in orderIds → "not first after the resume's reorder" [as stated].
- M7, the snapshot cut right after the re-entry → "re-entered … without its resume's patch" [as stated].
- M8, the patch without updates ({orderIds, removeIds}) → UNOBSERVED_RESUME_SHAPES' own name [as stated].
- M9, A2 with the "/" copy kept → "keeps a re-recorded copy the CLI drops" [as stated].
- M10, A2 with only the "/" copy removed → "must drop exactly one re-recorded context copy" [as stated].
- M11, A2 also removing a function-response copy → "removes a re-recorded copy that is not ignored content" [as stated].
- M12, F-B26-9: the closure reviewer's construction, `$set {sessionId}` inserted after the last $patch before the re-record.
  - It is refused at 5457e75e under the resume-shape name and admitted after the fix: w-g47 {1,40,0,0}, w-g14 {1,20,1,0}, w-g32 {1,25,0,0} [all three as stated, scratch/tools/nopatch.py].
- M13, a retired copy id (not the context) re-appended inside a window → the retired-id name.
- M14, B2 real → the compression name, and B1 real → the compression name (real-shape tests, not mutants).
- Positive tests:
  - the timeline's first message is the original context record (record 2), never the re-entered one;
  - the re-entered turn appears in `copies`;
  - B26's scanner test pattern (test_b26_scanner.py) is red when check_take stops reading copies.
- Code mutants, byte-backed as B25 and B26 did, restored and hash-checked afterwards: each new guard disabled alone must turn its test red. The guards are the re-entry conditions, the twice guard, the completeness check, the exactly-one check, the first-position check, the end-of-snapshot check and the F-B26-9 close.

Red witnesses: the new tests laid over a `git archive` of 5457e75e must fail.
- A1, A2 and A3 fail with the retired-id refusal.
- B1's compression-name test fails with the resume-shape name.
- M12 fails with the resume-shape name.
- M4, M6, M7 and M9-M11 fail with the retired-id name.

## 5. The survey (every committed walk plus the probe folders, no filtering; expected counts stated in advance)

Inputs:
- all 74 walk refs (38 w-o, 36 w-g), each read with `git archive` of its walk folder into scratch, never a worktree;
- stub-probe-full1 (8 scenarios);
- stub-probe-smoke1 (A1);
- the corrected A1 and A1-fake rerun folder once B27 stage 8 runs.

The tool is B26's survey26.py (sha256 0fd65dae8f555f45…), unedited, under a heavy slot or on athena. For the probe folders, stub_model_reading.py with `--code` on the batch head.

Expected on the batch head:

| Set | Expected | Basis |
|---|---|---|
| Codex 38 | 38 PASS, history 38 joined, 25 meet the floor | no Codex source changes; B26 survey on 9e91dd34 (night log 17:04) |
| Gemini 36 | 35 PASS, history 35 joined, 9 meet the floor; w-g24 DISAGREE by name "native interaction is incomplete: its last model message ends on tool calls" | same; the prototype's replay of all 50 Gemini native snapshots shows 0 differences (scratch/tools/walkreplay.py, 21:37) |
| Gemini properties | w-g14 {1,20,1}, loop 0; w-g32 {1,25,0}, loop 1; w-g47 {1,40,0}, loop 0; every other walk all zero; resumes_after_rerecord 0 on all 36 | prototype; B26 lane file |
| stub-probe-full1 | as the table in section 2 | prototype |
| smoke A1 | admitted, as full1 A1 | prototype |
| corrected A1-fake | the same verdicts and record structure as A1 over all three processes (test 5) | B27 ruling 4 |

Any difference from this table is a finding to read, never a filter.

## 6. Tests and fixtures

- A new module, tests/test_b28_resume_after_rerecord.py, holds the classes for road (a) real shapes, the mutants M1-M13, F-B26-9, the compression precedence and the scanner.
  - Its line goes in checks.d/vendor-admission.txt, so athena's battery runs it (the F-B26-10 lesson).
  - If B27 does not merge, the batch also adds B27's three lines for test_b25_real_shapes, test_b26_rewrites and test_b26_scanner.
- Fixtures go in tests/fixtures/b28-road-a/: A1, A2, A3, B1 and B2.
  - Each scenario's snapshots and streams, cut by B27's cutter (tests/fixtures/b27-stub/cut_structure.py), which extends B26's. That cutter maps every context version to one synthetic `<session_context>` block and keeps a leading "/", so the road (a) predicates survive the cut.
  - Raw is the fallback: about 1.5 to 1.9 MB per last snapshot (ls), stored once, with earlier snapshots as recorded byte-prefix lengths.
- A one-time check, recorded in the lane file: replay and properties on cut equal those on raw for every fixture.
- PROVENANCE.json records:
  - the records are synthetic CLI output from the B27 stub-model probe, never a study take;
  - B27 head 82da1830fa7dab843287ee0bd1efd91fd7946497 (the shipped head, RUNLOG "full 1. ship");
  - child /home/javier/w-ZJvHzvGU;
  - fetch tar sha256 e9face6e…8966;
  - manifest.json sha256 4628db56…, and each source file's sha256;
  - the corrected rerun's head and tar when it lands.
- B25/B26 leak checks stay on the fixtures (0 hits for the OD57 ruled digest; only allowed string classes).
- Changed tests: none expected. Every existing assertion on properties is per-key. A reason string changes only where a test pinned B1's old resume-shape name; if one does, it is changed with its reason recorded.

## 7. Which files change

- READER_SOURCES (native_reader_registration.py:85-87): only gemini_session_replay.py.
- CODEX_SOURCES (:191-192) is codex_native.py, native_reader_registration.py, drive.py, vendor_provenance.py and native_snapshot.py. gemini_session_replay.py is not among them, so the Codex acceptance stays valid.
- Not touched: native_reader_registration.py (in both lists; this is why `_walk_commit` stays out), drive.py, vendor_provenance.py, gemini_projection.py.
- Outside the hashed sources: the new test module and fixtures, checks.d/vendor-admission.txt, COPIED.d/vendor-admission.json (new entries appended, no line moved), and lane-reports/vendor-b28-DESIGN.md plus LANE.md.

## 8. Residual text

- Road (b), true compression: "Refused by name. The pinned client against a stub writes two compression shapes: B1, a resume with the context turn live, writes $patch {removeIds, updates} with the context turn as an update. B2, compression after a masking re-record, re-appends the context turn and writes $patch {removeIds}. Same survivors, different key sets. No study take approaches the trigger: the highest per-request promptTokenCount in the 36 committed Gemini walks is 160,229 (w-g47) against 524,288 (0.5 × 1,048,576, :337138-337143). Observed only on the pinned client against a stub (B27), never on the real API."
- Road (c), truncation: "Refused by name although C1 met its prediction exactly (wrapper head 8,000 + omitted 22,328 + tail 32,000 = the original 62,328). It needs a reported prompt of at least 524,288 tokens, which no study take approaches (160,229 at most). Stub-only."
- The precedence finding: "At 5457e75e, B1 was refused by the resume-shape rule before the compression rule. After vendor-b28's F-B26-9 window close, both B1 and B2 are refused under the compression name; the earlier precedence is recorded as history." If glitch-f1 keeps ruling (1)'s wording instead, add "fixed by F-B26-9 in vendor-b28" (open call O3).
- Road (a), admitted: "Admitted on its observed shapes from the pinned client against a stub (B27 A1, A2, A3, B2), with an evidence note mapping every record to its cited line. Masking at a resume's first request is seen in real data (w-g47); the resume after it was never seen on the real API. After such a resume the CLI no longer sends the first prompt (and any '/'-leading prompt) to the model (stub requests A1 9, A2 11, A3 9); the reader's facts come from the frozen originals."
- The false-refusal residual is narrowed: a resume writes a content update for every live original gemini response stored as a string (A1 record 72 updates record 67, a plain string). So the four update-less shapes need a resume in which every live gemini message is a re-recorded copy.

## 9. B27's probe code on the freeze line

- For merging (glitch-f1 leans yes):
  - the fixtures' provenance names code the frozen tree then holds: the stub, the probe, the reading harness and the cutter, so a reviewer can re-derive every road (a) verdict from the tree;
  - one battery covers both lanes (ruling 6);
  - B27's checks.d lines for the B25 and B26 tests (F-B26-10) come along;
  - none of B27's 21 files is in READER_SOURCES or CODEX_SOURCES (git diff --stat 9e91dd34..49c350a9), so no extra re-acceptance.
- Against:
  - 5,363 added lines in the frozen tree, more battery and review surface;
  - an edit to walk_launch.py, the walk launch road. Its run command is pinned byte-unchanged by test_stub_model_probe (COPIED.d entry), but whether freeze.py hashes walk_launch.py was not checked;
  - b28 then waits on B27 stage 8's closure review.
- Recommendation: merge B27's reviewed head into lane/vendor-b28 first, then build b28 on top, if stage 8's closure review passes before b28's build review.
  - Otherwise b28 lands alone. It copies only the cutter into its fixture folder (or uses raw fixtures), and the provenance names B27's head and tar.

## 10. Steps

1. Build on lane/vendor-b28-20261021, base 5457e75e (plus B27 if section 9 holds). Red first on a `git archive` of 5457e75e, then green. Mutants. Stages committed one by one, with an append-only lane file.
2. Mac light: the new module plus test_b26_rewrites, test_b25_real_shapes, test_gemini_session_replay, test_b26_scanner and test_gemini_projection. The heavy modules go to athena.
3. The survey (section 5), under a heavy slot or on athena, with expected counts compared line by line.
4. A fresh review (opus-medium) on the batch head: the rules against the cited lines, every mutant red without its guard, and the survey re-run by the reviewer's own parser. Fold, then a closure review if there are findings.
5. The athena battery on the exact head (checks.d, including the new line). B26's took 510.9 s.
6. Merge onto freeze/r4-20261021 by exact SHA. The path guard admits only the batch's paths.
7. The Gemini reader review on that head, as ruled at F4: diff-focused, plus a full re-read of the 36 walks and the mutants. It is written as native-readers/gemini-review.md's replacement candidate, kept outside the clone.
8. The kit: a Gemini-only rebuild of accept-readers-20261021.sh and accept_readers_build.py.
   - It builds only the Gemini record: walk w-g21, reader_sources_sha256 at the new head, the new review's sha256.
   - It replaces native-readers/gemini-acceptance.json and gemini-review.md in one commit (the file name is fixed by ACCEPTANCE_FILE, native_reader_registration.py:82). The codex files are untouched.
   - It has the same dry run, `verify` with both readers registering, and a removal-on-failure path.
   - It is reviewed fresh before Javier sees it.
9. Javier's second ACCEPT, for Gemini only, in his own Terminal.
10. Cut-off, as ruled: if the batch is not accepted by the time settlement's battery passes, nothing lands, and road (a) plus F-B26-9 are published as residuals by name.

## 11. Risks

- R1: a real walk could show a road (a) variant the stub did not, for example a re-record whose copy run does not start with the context copy. The completeness and exactly-one rules then refuse it by name, a false refusal and never a false admission.
- R2: the stub's inflated usage. Masking depends on character estimates (:344698), not reported usage, so road (a)'s trigger is the client's own (B27 R4). Inference.
- R3: re-acceptance overwrites a fixed-name record. Git history keeps the first acceptance; the lane file and the kit say so.

## 12. Honest size

- Builder: about 6 to 9 agent hours. The replay change is about 80-120 lines with its docstring; the tests and mutants about 350-450; cutting fixtures, the provenance and the raw-versus-cut check about 1 hour; the survey about 1 hour.
- Review: 1 to 2 hours a round, one or two rounds. Battery: one athena slot, about 10 minutes plus ship and fetch. Gemini reader review: 1 to 2 hours. Kit rebuild and its review: 2 to 3 hours.
- Wall clock: set by athena's order and Javier's sitting, not by the build. This is my estimate, not an ETA-engine date.

## 13. Open calls for glitch-f1

- O1: the base, 5457e75e then a merge onto the freeze line (recommended), or wait for the freeze line.
- O2: B27 merging with the batch on the condition in section 9 (recommended), or b28 alone.
- O3: the precedence residual's wording now that F-B26-9 fixes it (section 8), and whether road (b)'s status needs any re-ruling (I recommend none: still refused, because the key sets differ and no take nears 524,288).
- O4: the property name `resumes_after_rerecord` (new key, recommended) versus folding it into an existing count.
- O5: cut fixtures through B27's cutter (recommended) versus raw.
- O6: the completeness rule (every ignored re-recorded copy must be removed), stricter than B26's per-id check (recommended).
- O7: whether the kit replaces gemini-acceptance.json in place (the only road without touching native_reader_registration.py) is acceptable under the record-integrity rules.
- O8: whether test 5 (the corrected A1-fake) must pass before the build review or only before the battery (I recommend before the review, since the fixtures cite it).

## What I could not check

- Test 5. The current A1-fake is defective, so the cross-check holds for process 1 only.
- That a walk-side config sha256 equals the probe's (EN, test 1).
- The full check_session survey on the prototype. Only replay-level verdicts were compared over the walks; the probe folders went through stub_model_reading, history included.
- Whether freeze.py hashes walk_launch.py.
- The CLI's estimated token count at a walk's resume.
