# Review: the Gemini native-session reader, on the acceptance walk w-g21 at 048bfbf2

Reviewer: independent reviewer agent (Claude Opus 5.5), briefed by glitch-f1, the Lane-orchestrator, under Javier's standing delegation.
Clock: Wed 21 Oct 2026, 16:48:02 to 17:01:47 EDT (`date`).
Candidate head: 048bfbf2cc2ee1ae86c971bf9e9fd06d47b565b3, branch accept/m2-20261021 of /Users/javrodher/aegis-builds/gap4-walk-records-20261019.

Verdict for Javier: PASS

The reader reads the native session of the acceptance walk w-g21 and joins it to the live stream on every interaction and every tool round trip.
It does the same on 35 of the 36 committed Gemini walks.
The one walk it refuses, w-g24, it refuses by name, and correctly: that walk timed out in the middle of a tool call.
The four blocking findings of the earlier review (REVIEW-reader-gemini-20261021.md, NOT YET) are closed on the real walks.
All seven mutants I wrote went red.
The reader's sources at 048bfbf2 are byte-identical to the reviewed 9e91dd34.
I would put my name to Javier accepting this reader on this walk.
The findings below are MINOR or NIT: they ask for wording in the acceptance sitrep, not for code changes.

## Scope and method

- This was review only.
  I edited no candidate code, committed nothing to the candidate, pushed nothing, registered nothing and ran nothing on athena.
- The records clone was left as I found it: HEAD 048bfbf2 and `git status --short` empty, both at 17:01.
- Scratch folder: /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/rvg.
  - `tree/` is `git archive 048bfbf2`.
  - `walks/<walk>/` is `git archive <walk branch sha> evals/gap-study-4/rehearsals/<walk>`, one per Gemini walk.
  - `clone/` is a `--no-hardlinks` clone checked out at 048bfbf2, used only for the steps that need git history (`_walk_commit`, `_clean`, the registration tests).
  - `mut/` holds the mutant copies, `probes/` the tampered inputs, `tools/` my scripts, and `survey36.log`, `mutants.log` and `mutant-control.log` the full outputs.
- Every Python process ran as `/usr/local/bin/python3.12 -I -B`, except the unit test files, which ran with `-B`.
  Each batch ran behind `mac_slot.py light-ok --work gap-study-r4` with rc 0.
  The one hold, at 16:48 ("CPU speed limit 45 is below 50"), came before any compute; I waited it out.
- One deviation from the brief, flagged here.
  I tried to run the gate end to end (`acceptance_problems`) in my scratch clone, with a placeholder acceptance record committed only there.
  The permission system denied that step, and rightly: the record would have had to carry `accepted_by: "javier"`.
  Nothing was written (the folder `native-readers/` does not exist in the scratch clone, and its status is empty).
  Instead I ran every step of `acceptance_problems` that does not need a record, in the gate's own order (`tools/gate_parts.py`).
  The steps that need a record (its closed keys, the hash of the committed review, the marker scan of the review and the record) are therefore not exercised here.
  They run when the real record is committed.
- The pinned package: /Users/javrodher/aegis-builds/glitch-26-carry-20261021/b26/pkg-dl/gemini-cli-0.64.0.tgz.
  - Its sha256 is 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6, as pinned.
  - I extracted only `package/bundle/chunk-NR7L3FXV.js` and `package/bundle/gemini.js`, with `tar -x`, into the new empty folder `pkg/`, and executed nothing from it.
  - The chunk's sha256 is d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c, as pinned, and gemini.js:10 imports it.

## 1. The acceptance walk w-g21 (16:50:43 and 16:53:56 to 16:53:59)

The gate's steps that need no record, on the scratch clone at 048bfbf2 (`tools/gate_parts.py`), all returned OK:

- `_clean` over the register, the walk folder and READER_SOURCES.
- `reader_sources_sha256` at HEAD: ec9c80e69cef60a1703ddcb41f98489735ac721703ef54a56c59dd4c1840d5d2, the same value as in M2-REAL-20261021.md.
- The register lists w-g21 once, arm G.
- `drive.walk_files`.
- `_walk_commit`: e2c30e0c1ab3e8bca577485217e16499102009d2, exactly the walk's commit.
- `_ledger_problems`, `_records_problems` (check.json and grade.json re-derived), `_journal_problems` and `_regrade_problems`.

`check_session` (the shared `join_session`) on the last snapshot against both host-captured streams:

- Result: PASS, 2 interactions.
- Shapes: 34 tool round trips, 1 with error status, 8 with an object display, 0 multi-segment interactions.
- Take properties: history_rewrites 0, tool_outputs_masked 0, ignored_prompt_resumes 0, loop_feedback_injected 0.
- Coverage floor ({2 interactions, 1 tool round trip}): met.
- The history join over both snapshots the ledger names (`gemini_snapshot_prefixes`, then `session_history_facts`): PASS.
  Snapshot 1 is a byte prefix of snapshot 2, and interaction 1 reads the same from both.
- Per-snapshot join, a check beyond the road's: snapshot 1 joined against stream 1 alone also reads PASS.
- No marker in the native metadata or the register entry (the gate's regex, run on both).

Interaction by interaction (the projection, then the join):

| Interaction | sent equals the ledger's | model | session id | text segments | tools |
|---|---|---|---|---|---|
| 1 | yes | gemini-3.8-flash | 9d6e08be-586f-4143-b4bb-cfbc60d5b09c | 1 | 34 |
| 2 | yes | gemini-3.8-flash | 9d6e08be-586f-4143-b4bb-cfbc60d5b09c | 1 | 0 |

An independent tally that does not use the reader (`tools/indep.py` and an inline script, 16:51:43):

- Stream 1 has 78 records.
  Its init has session 9d6e08be-..., model gemini-3.8-flash.
  Its one user message equals the ledger's sent.
  It has 34 tool_use, 34 tool_result (1 error), one terminal result `success`, and that result is the last record.
- Stream 2 has 8 records: the same session and model, a user message equal to the ledger's sent, no tools, and a terminal `success`.
- Native snapshot 1: 61 messages, 30 gemini, 34 tool calls (1 error).
- Native snapshot 2: 92 messages, 31 gemini, 29 `_response` resume copies, the same 34 tool calls (1 error).
- In both snapshots, the stream's (id, name) list of 34 equals the native call list in order.
- Native metadata sessionId equals both streams' init session_id.
- The control records:
  - `$set {lastUpdated}` records throughout.
  - One `$set {sessionId}` at line 153, which opens the resume.
  - One `$patch {orderIds, updates}` at line 183.
- The first-written user text messages:
  - line 2, the session context turn;
  - line 4, the turn-1 prompt;
  - line 185, the turn-2 prompt.

The driver ledger's refs, re-hashed on the committed bytes:

- native-turn-1.jsonl: 97e07f76...aab, equal to the ledger.
- native-turn-2.jsonl: 92ca8f1e...edb2, equal to the ledger.
- environment.json: ed40a94d...bd5b, equal to the ledger.
- turn-1.jsonl e11b4c22...60fa and turn-2.jsonl 64ec94e3...c19 equal the sha256 values that transcript.jsonl records for them.
- evidence/ledger.jsonl: aa615d72...cfa, equal to evidence-ledger-copy.json.
- The w-g21 folder tree at 048bfbf2 is 9620c214aa79546c6a9c748cf3095eaf6264650e, the same as at e2c30e0c.
- No masking strings (redacted, `<tool_output_masked`, `[masked`) appear in either snapshot or either stream: the committed bytes are the unmasked originals.

The pinned writer lines behind the two shapes that blocked last time, read in the chunk:

- :286041-286044, deriveStableId.
- :336343-336370, the session context block (opening "<session_context>\nThis is the Gemini CLI. We are setting up the context for our chat.") and its stable id `environment-context`.
- :286180-286188, the `${msg.id}_response` turn.
- :287254-287266, the `$patch` payload with `updates`, `removeIds` and `orderIds`, and the `$rewindTo` branch.
  The reader refuses `$rewindTo` as an unknown destructive operation.

## 2. The same reader over all 36 committed Gemini walks (16:50:50 to 16:51:16)

- One walk per process, light-ok before each, over my archives of the 36 walk branches: w-g12 to w-g48, without w-g22.
- Result: 35 PASS, 1 refused by a named reason.
- Driver-ledger refs re-hash on all 36.
- Native session id equals stream 1's init session_id on all 36.
- No marker in metadata on any walk.

The refusal:

- w-g24 (gemini-3.8-flash, 1 turn, ledger outcome `timed-out`) is refused with "native interaction is incomplete: its last model message ends on tool calls".
- Its stream ends on a tool_result with no terminal result record.
- Both sides agree that the turn was killed mid-tool, which is the refusal NEVER_COUNTED names.

The floor:

- 9 walks meet it, all multi-turn, all PASS with the history join over every snapshot: w-g13, w-g14, w-g21, w-g31, w-g32, w-g39, w-g40, w-g47 and w-g48.
- The other 26 PASS walks are single-turn, below the 2-interaction floor by design.

Take properties and shapes on the walks that exercise the roads the reader added since the earlier review:

| Walk | turns | tools | error statuses | object displays | multi-segment | rewrites | masked parts | ignored-prompt resumes | loop feedback |
|---|---|---|---|---|---|---|---|---|---|
| w-g14 | 4 | 118 | 24 | 30 | 0 | 1 | 20 | 1 | 0 |
| w-g32 | 3 | 97 | 29 | 15 | 1 | 1 | 25 | 0 | 1 |
| w-g47 | 2 | 141 | 21 | 12 | 0 | 1 | 40 | 0 | 0 |
| w-g13 | 3 | 34 | 5 | 1 | 0 | 0 | 0 | 0 | 0 |

- Every other PASS walk has all four properties at 0.
- w-g13's turn 3 (the earlier review's MAJOR 4) now joins:
  - The native side has 0 text segments and 7 tools.
  - The stream side has 0 segments, 7 tools and a terminal `success`.
- No refusal under any of the ruled residual names on any walk:
  - the resume after a masking re-record;
  - compression;
  - truncation;
  - the four unobserved resume shapes;
  - F-B26-9.

## 3. The earlier review's findings

| Earlier finding | Closed | Evidence |
|---|---|---|
| BLOCKER 1, the resume `$patch {orderIds, updates}` and the duplicated round trips | yes | The replay admits exactly that shape inside a resume: a permutation, a repeat only of a `_response` id, each copy directly after its gemini message and byte-identical to the original that follows, originals in first-record order (gemini_session_replay.py:276-322). All 9 multi-turn walks PASS. test_gemini_session_replay.py:48 now pins only the off-shape `{orderIds}` alone as a refusal (its comment names the ruling). Mutants M1 and M2 go red. |
| BLOCKER 2, the session context turn read as an interaction | yes | It is recognised only as the first message, with id deriveStableId(["environment-context"]), keys {id, timestamp, type, content} and one text part with the pinned opening and closing (gemini_projection.py `_session_context`). On w-g21, interaction 1's sent is the turn-1 prompt and equals the ledger's sent. Mutant M7 goes red. |
| MAJOR 3, the Gemini join never compared session identity | yes | gemini_stream_join.join refuses unless the stream's init session_id equals the native sessionId; a stream with no init refuses. Probe P-sid refuses at the head. Mutant M6 goes red. |
| MAJOR 4, an empty final answer refused | yes (by ruling 6) | Both sides empty now agree, and one side empty disagrees. w-g13 turn 3 joins (section 2). |
| MINOR 5, sent and model compared only when the stream carries them | mostly | The model is now always compared: init is required for the session check, and transcript_gemini requires `model` in an init. sent is still compared only when the stream has a user message. On w-g21 both streams carry it, and the gate binds the ledger's sent to each launch journal through `launch_facts`. See NIT 4. |
| MINOR 6, fixtures cut from real walks | yes | tests/fixtures/b25-real-shapes (from w-g21, w-g31, w-o46) and tests/fixtures/b26-rewrites (from w-g14, w-g32, w-g47), each with PROVENANCE.json and cut_structure.py. test_b25_real_shapes (18) and test_b26_rewrites (43) are green on the archive copy. |
| NIT 7, the ledger's session_id is the take's id | unchanged, as designed | transcript.jsonl now records `vendor_session_id` beside it. |
| Not attributed, the 4 ManifestClaim failures | attributed | They fail on archive copies and pass in a git checkout. test_native_reader_registration in the scratch clone: "Ran 7 tests ... OK" (16:58:28). In my non-git copies the same 4 fail, with or without a mutant. |

Tests on the archive copy at 16:52:25 to 16:52:41, all green:

| Test file | Tests | Result |
|---|---|---|
| test_gemini_stream_join | 9 | OK |
| test_gemini_projection | 8 | OK |
| test_gemini_session_replay | 3 | OK |
| test_b25_real_shapes | 18 | OK |
| test_b26_rewrites | 43 | OK |
| test_b26_scanner | 3 | OK |
| test_native_history_record | 3 | OK |

## 4. Default-deny: seven mutants (16:55:37 to 16:58:28)

Method:

- Each mutant is one exact-string edit, asserted to apply once, on a copy of the candidate's evals/gap-study-4 (`tools/mutants.py`).
- Each copy then ran:
  - five tampered inputs cut from w-g21 (`tools/make_probes.py`);
  - the reader on w-g21, w-g14, w-g32 and w-g47;
  - the six reader test files.
- A control copy with no edit (M0) was run in the same layout.
  In that layout, test_b26_scanner and one Scanner test in test_b26_rewrites error with `No module named 'transcript'`, a module outside the copied folder.
  Those two errors are layout artifacts, present in the control, and are subtracted below.
- In the control, all five probes refuse and all four walks PASS.

The five probes:

- P-perm: the resume's orderIds with one id left out.
- P-copy: one resume copy's response altered, so it is no longer byte-identical to its original.
- P-extra: snapshot 2 joined to stream 1 only.
- P-args: one tool_use argument value changed in stream 1.
- P-sid: both streams' init session_id changed.

| Mutant | Kind | What goes red (beyond the control) |
|---|---|---|
| M1: drop the orderIds permutation check (`_reorder`) | widen a shape | test_b25_real_shapes: failures 1, errors 1. P-perm still refuses, through a second check ("no resume reorder placed it"). |
| M2: drop the byte-identity of a resume copy and its original (`_resume_order`) | widen a shape | P-copy is admitted (PASS). test_b25_real_shapes: failures 1. |
| M3: drop the extra-native-interaction refusal (`join_session`) | drop a check | P-extra is admitted (PASS, 1 interaction). test_native_reader_registration CheckSession fails ("native interactions for 1 streams"). |
| M4: drop the tool-arguments comparison (`join`) | drop a check | P-args is admitted. test_gemini_stream_join: failures 4. |
| M5: read facts from the loader's state (copies and re-recorded messages) instead of the original timeline | a fact from a copy | w-g14, w-g32 and w-g47 refuse ("a tool-response turn must answer exactly the calls of the gemini message just before it"). test_b26_rewrites: failures 5, errors 5. |
| M6: compare the stream's session id with itself instead of the native sessionId | a fact from a copy | P-sid is admitted. test_gemini_stream_join: failures 1. test_b25_real_shapes: failures 1. |
| M7: recognise a context turn under any id | widen a shape | test_b25_real_shapes: failures 1, errors 1. |

Every mutant refuses or goes red.
No mutant changes the w-g21 result, which is expected: w-g21 is a well-formed walk, and each mutant only widens what is admitted.

## 5. READER_SOURCES between 9e91dd34 and 048bfbf2

- `git diff --stat 9e91dd34 048bfbf2 --` over the nine READER_SOURCES is empty.
- Every blob id is equal, for example:
  - gemini_projection.py 0d24b9d9;
  - gemini_session_replay.py 8fd04408;
  - gemini_stream_join.py 1f0e3b2e;
  - native_reader_registration.py ecdb8ea1;
  - drive.py 6aa45e7b;
  - vendor_provenance.py 0dad979b.
- The whole diff is 73 paths: 40 under w-o46/, 32 under w-g21/, and evals/gap-study-4/rehearsals/register.json.
- Nothing differs.

Not verified by me: the athena battery PASS on 9e91dd34.
I take it from the brief.

## Findings

1. MINOR: the bound walk exercises only the plain resume.
   - w-g21's take properties are all 0, and it has no multi-segment interaction.
   - The roads the reader gained since the earlier review are shown on real walks only by this survey (w-g14, w-g32, w-g47 PASS with history) and by the fixtures, not by the acceptance record. Those roads are the masking re-record, the ignored-prompt resume and the loop feedback.
   - Nothing is wrong with the reader here.
   - The acceptance sitrep should say plainly that the record certifies w-g21, and that the rewrite roads rest on the 36-walk survey.
   - Alternatively, bind w-g47 or w-g14 instead.
2. MINOR: the end-to-end gate was not exercised by this review.
   - The record-dependent steps of `acceptance_problems` were not run: the closed keys, the hash of the committed review, the marker scan of the review and the record, and the `join` equality.
   - Writing a placeholder record was refused by the permission system (section "Scope and method").
   - Every other step passed.
   - `native_reader_registration.py verify` should run in Javier's window after the acceptance commit, and its output should be kept with the record.
3. NIT: the marker gate is narrow by design.
   - The marker word occurs once in the body of each w-g21 native snapshot, inside a tool's read of the GARS repository's own folder listing (real content, not a label).
   - The gate scans only the metadata, the register entry, the review and the record, so this neither refuses nor should.
   - I record it so that a later widening of the gate does not turn it into a false refusal.
4. NIT: residual from MINOR 5.
   - `join` compares sent only when the stream carries a user message.
   - The acceptance road covers this: on w-g21 both streams carry it, and `_journal_problems` binds the ledger's sent to each launch journal.
   - A production take whose stream lacks the user message would rest on vendor_record_binding alone.
5. NIT: one check is shadowed.
   - The projection's own byte-identity check of a resume copy (`_resumed_copy`) never sees resume-time copies, because facts are read from the timeline of originals.
   - The replay's check (gemini_session_replay.py:313-318) is the only gate for them, as M2 shows.
   - No fact is at risk, because copies never feed a fact.
   - The projection check still covers a `_response`-suffixed id first written outside a resume.

Ruled residuals: none was observed on any of the 36 walks, and none is reopened here.
They are the resume after a masking re-record, compression, truncation, the four unobserved resume shapes, and F-B26-9 (a false refusal under a wrong name).

## Reproduction

- The scripts are in /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/rvg/tools: survey.py, indep.py, gate_parts.py, make_probes.py, probe_run.py and mutants.py.
- The logs are survey36.log, mutants.log and mutant-control.log in the folder above.
- Survey: `python3.12 -I -B tools/survey.py tree/evals/gap-study-4 walks/<w>/evals/gap-study-4/rehearsals/<w>`.
- Gate steps: `python3.12 -I -B tools/gate_parts.py clone/evals/gap-study-4 w-g21`.
