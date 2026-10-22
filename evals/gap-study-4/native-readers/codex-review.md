# Review: Codex native-session reader on the real walk w-o46, Gap Study round 4, arm O (GPT)

Reviewer: independent reviewer sub-agent (Claude Opus 5.5), briefed by glitch-f1, the Lane-orchestrator, under Javier's standing delegation; review only.
Written Wed 21 Oct 2026 17:03 EDT (clock read with `date`); the work ran 16:48:01 to 17:03:42 EDT.
Candidate head: 048bfbf2cc2ee1ae86c971bf9e9fd06d47b565b3, branch accept/m2-20261021, records clone /Users/javrodher/aegis-builds/gap4-walk-records-20261019.

Verdict for Javier: PASS

The reader reads every committed GPT walk, 38 of 38, with no filtering, and agrees with the host-captured streams on every turn.
The three blocking findings of the earlier NOT YET review (REVIEW-reader-codex-20261021.md: B1, M1, M2) are closed, each with evidence below.
The full acceptance road, run end to end on a scratch clone of this exact head with a stand-in record and review, loads the Codex reader, and refuses every bad variant I tried.
What stays open is minor: patch edits (file_change) and non-empty reasoning summaries are still unexercised by any real walk, one wrong-field mutant survives the test suites (my real-bytes probe catches it), and there is still no command-line road for the Codex check.
None of these changes what Javier would be accepting on w-o46; the record should name the unexercised paths.

## What I did, and where

- Nothing in the records clone was changed: before and after, `git status --short` is empty, HEAD is 048bfbf2, branch accept/m2-20261021 (checked 16:58:08).
- Scratch: /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/rev-codex/
  - head/ and f/: `git archive` of 048bfbf2 and 9e91dd34.
  - walks/w-o*/: each of the 38 committed GPT walks, `git archive` of its own walk branch's commit (w-o46's equals the head's folder byte for byte, `diff -r` clean).
  - mut/: a further `git archive` of 048bfbf2's evals/gap-study-4, for mutants.
  - clone/ and clone2/: `git clone --no-local` of accept/m2-20261021 into scratch, needed because the acceptance road reads git history (`_walk_commit`) and the registration tests need a repository. clone/ holds one scratch-only commit (a stand-in acceptance record and review, committed as "reviewer scratch <scratch@invalid>", never pushed anywhere); clone2/ is unchanged at 048bfbf2 (`git status --short` empty after the mutants).
  - scripts/: survey.py, detail.py, trunc.py, probes.py, mutate.py, mutate2.py, road.py, road_neg.py, mkrecord.py; logs survey-head.txt, mutate2.log.
- Every batch ran behind `mac_slot.py light-ok --work gap-study-r4` with rc 0 (load1 4.88 to 7.82, CPU speed limit 54 to 60). Nothing ran on athena.
- Python 3.13.2, with `-I -B` for every script that reads walk bytes.

## 1. w-o46 at the head, turn by turn (16:50 to 16:52)

The driver ledger: arm O, codex 0.162.1, model_requested gpt-6.1-sol, task explain-not-act, 3 turns, exits 0, 0, 0; served_model unobserved on all three.
Its refs re-hash on the committed bytes: native-turn-1 749f216a..., native-turn-2 f42b44c1..., native-turn-3 568705600a46...; environment.json 7d9ab09c... equals the ledger's.
Each earlier snapshot is a byte prefix of the next (1 of 2, 2 of 3).
session_meta: id 01a15a88-1ded-7760-b734-ee1706b7ecca (equal to its session_id field in all 38 walks), cli_version 0.162.1, history_mode paginated, source exec.

My own reading (detail.py, written for this review, not through codex_native) against the reader's codex_check:

| Turn | Thread (rollout = stream) | Sent: rollout = ledger = launch argv | Model: turn_context = ledger = argv `-m` | Agent messages | Commands (status/exit/bytes, output sha256 equal) | Terminal |
|---|---|---|---|---|---|---|
| 1 | yes | yes (84 chars) | gpt-6.1-sol | 3 = 3, text equal | 4 = 4: 83 B, 56,290 B, 25,439 B, 918 B, all completed/0 | task_complete, turn.completed, exit 0 |
| 2 (resume) | yes | yes ("skip") | gpt-6.1-sol | 3 = 3 | 3 = 3: 1,531 B, 824 B, 0 B | same |
| 3 (resume) | yes | yes (48 chars) | gpt-6.1-sol | 1 = 1 | 2 = 2: 174 B, 174 B | same |

- Both resume launch journals name the rollout's own thread id after `resume`.
- Reasoning: 2 Reasoning items (turns 2 and 3), both with an empty summary; the stream shows none; projected 0 = 0.
- No file_change, no error item, no reroute in any of the three streams.
- `codex_check(native-turn-3, streams, ledger)`: PASS, 3 interactions, shapes {interactions 3, command_round_trips 9, reroutes 0, marker_texts 0}; CODEX_FLOOR {interactions 2, command_round_trips 1} met.
- `vp.session_history_facts` over all three snapshots with codex_reader: joins, 3 snapshots, each later one reproducing every earlier interaction.
- `_codex_metadata` (the session_meta payload): the marker gate does not fire. The register entry carries no marker either (0 hits).
- reader_sources_sha256 over CODEX_SOURCES at the head: c0121f0c09de98c1e2c2587881137299ce6e8e4bfe7454e522acbc69d1be2d48, the value the M2 report printed.

### The acceptance road end to end (16:51:40)

On clone/ I committed a stand-in `native-readers/codex-acceptance.json` (walk w-o46, native session/native-turn-3.jsonl, the three stream hashes, join PASS 3, reviewer "scratch-reviewer", accepted_by javier) and a placeholder `native-readers/codex-review.md`, then ran `production_readers(study)`:
- `production_readers: ['codex'] {'codex': 'codex_reader'}` in 2.5 s. Every gate of acceptance_problems ran: the clean check, the source hash, the register, drive.walk_files, `_walk_commit` (found ae6bec92 through the merge), the ledger, check.json and grade.json re-derived, the launch journals, the regrade check, the record's refs, codex_check, the floor, the history join, at least 2 snapshots, the marker gate.
- Refused, each with the road's own reason: walk w-g21 (not arm O); walk w-o7 (not in this head's register); native named as the turn-2 snapshot (not the ledger's last); join interactions 2 ("does not re-derive"); reviewer "Javier" (same principal as the acceptor); streams 1..2 only; drive.py edited and uncommitted ("a bound path differs from the committed tree"); the review carrying the marker word, committed with its hash updated (the marker gate refused).
- After resetting the marker probe commit, the road loads again (3.0 s).
So the road Javier's acceptance commit will travel works on this head; the real record must carry the real review's bytes and hash.

## 2. Every committed GPT walk (survey-head.txt, 16:50:48)

The 38 walk branches each add exactly one w-o folder, every commit subject "Commit one walk; never counted": w-o7 to w-o47, with w-o17, w-o38 and w-o45 absent from every branch.
For each, the head's reader with no filtering, plus my independent comparison (thread, sent against ledger and argv, model against ledger and argv, agent text, command status/exit/output, reasoning, file changes, terminal, turn count):

- codex_check PASS: 38 of 38. Refusals: 0.
- My independent comparison agrees on all 38.
- History join over every retained snapshot: 38 of 38.
- Every ledger snapshot ref re-hashes: 38 of 38.
- Marker gate on session_meta: fires on none.
- Floor met: 25 walks. Not met (single-turn, 1 interaction; these would refuse only as acceptance walks, by the named floor, never as reads): w-o15, w-o16, w-o20, w-o25, w-o26, w-o27, w-o28, w-o35, w-o36, w-o39, w-o42, w-o43, w-o47 (13).
- Over 64 KiB: one command each in w-o22, w-o30, w-o43, w-o47 (marker_texts 1). trunc.py, my own check: the rollout output is 65,536 B, one marker at byte 32,743, head 32,743 B a prefix of the stream's output and tail 32,743 B a suffix, head plus tail 65,486 B (64 KiB minus the 50-byte marker), in all four.
- Record types across the 38 last snapshots: world_state 38 (all `full: true`, all inside turn 1), thread_settings_applied 102 (all between turns, every one with the extra keys reasoning_effort and runtime_workspace_roots, every model equal to the ledger's), task_started 89 = task_complete 89, item kinds UserMessage 89, AgentMessage 169, CommandExecution 226, Reasoning 125 (0 with a non-empty summary), FileChange 0; no turn_aborted, no error, no reroute.

## 3. The earlier review's findings

- B1 (BLOCKER, world_state and thread_settings_applied refused): CLOSED. codex_native.py at the head admits world_state only inside an open turn on exactly {full: bool, state: object} (:269-275, :393-395) and thread_settings_applied only between turns, naming the session's thread, its thread_settings checked key by key (:282-345, :412-414). Evidence: 38 of 38 read unfiltered (section 2); probes on w-o46 bytes refuse a world_state with an extra key, a world_state moved before turn 1, a thread_settings_applied moved inside turn 2 and one naming another thread (probes.py, all DISAGREE on the head).
- M1 (MAJOR, sent and requested_model never compared): CLOSED. codex_join_session compares each turn's UserMessage to the ledger's sent line and turn_context.model to model_requested (native_reader_registration.py:229-232), and drive.codex_cross_check passes the same two from the ledger rows (drive.py:2617-2618, 3204-3222), so production and acceptance share it. Evidence: on w-o46 bytes, turn 2's prompt replaced gives "interaction 2: the rollout's sent prompt is not the line sent"; turn 2's turn_context model replaced gives "the rollout's requested model is not the take's". The earlier review's probes passed both.
- M2 (MAJOR, walk and fixed reader not on one HEAD): CLOSED. 048bfbf2 holds the reviewed reader 9e91dd34 and w-o46's walk commit ae6bec92 as a merge parent; the register at the head lists w-o46 once, arm O; `_walk_commit` accepts it and the full road loads (section 1).
- m1 (MINOR, no command-line road for the Codex check): OPEN, unchanged (main's `check` still calls the Gemini check_session only, :725). Finding 3 below.
- m2 (MINOR, the patch path has no real walk): OPEN, unchanged: 0 file_change in every stream and 0 FileChange in every rollout of the 38; CODEX_SHAPES still has no file-change count. Finding 1 below.
- m3 (MINOR, non-empty reasoning unexercised): OPEN, unchanged: 125 Reasoning items, 0 non-empty. Folded into finding 1.
- n1, n2 (NITs): unchanged; cwd is read and never bound, permission_mode is None for Codex by design (codex_native.py:67-68, :447-448).

## 4. Default-deny: mutants on my copy (16:55:56, and 16:58 to 17:03:42)

Each mutant was applied to a byte-backed file, its probe run through codex_check on w-o46-derived bytes (the head refuses every probe, section 3), then test_b25_real_shapes (18) and test_codex_native (15); the file was restored and its sha256 re-checked.

| Mutant | Probe on the mutant | Tests |
|---|---|---|
| M1 widen the world_state shape (any payload keys) | extra key admitted: PASS | red: test_world_state_off_its_shape_or_place_refuses (1 failure, 1 error) |
| M2 drop world_state's place check | world_state before turn 1: PASS | red: same test |
| M3 drop the sent check in the shared join | replaced prompt: PASS | red: 3 failures (test_a_replaced_prompt_or_model_disagrees x2, test_codex_check_reads_both_from_the_ledger) |
| M4 take requested_model from the wrong field (turn_context.collaboration_mode.settings.model) | replaced turn_context.model: PASS | green in every suite tried (also test_pending_codex_walk, test_vendor_admission, test_vendor_envelopes, test_walk_grade_seam, test_codex_patch_reads, test_codex_started_file_change, test_native_reader_registration) |
| M5 admit thread_settings_applied inside a turn | moved into turn 2: PASS | red: test_thread_settings_applied_off_its_shape_or_place_refuses |
| M6 drop thread_settings_applied's thread check | other thread: PASS | red: same test |
| M7 drop the turn-count check | 3 native turns for 2 streams: PASS | green in the two fast suites; red in test_pending_codex_walk (test_the_coverage_floor_and_the_shared_join) |

Six of seven go red in the tests; all seven are refused by the unmutated head on real-walk bytes. M4 is finding 2.

Baseline on clone2 at 16:52:10, unmutated, all green: test_b25_real_shapes 18, test_codex_native 15, test_codex_started_file_change 5, test_codex_patch_reads 13, test_vendor_provenance 6, test_native_reader_registration 7, test_native_history_record 3, test_pending_codex_walk 12.

## 5. CODEX_SOURCES between 9e91dd34 and 048bfbf2

Nothing differs.
Blob ids are identical at both commits: codex_native.py 83dd8821, native_reader_registration.py ecdb8ea1, drive.py 6aa45e7b, vendor_provenance.py 0dad979b, native_snapshot.py f378ca50; `git diff --stat` over the five is empty.
`git diff --name-only 9e91dd34 048bfbf2`: 40 paths under rehearsals/w-o46/, 32 under rehearsals/w-g21/, and rehearsals/register.json; nothing else.
`git log 9e91dd34..048bfbf2`: the two merges (baa4f814, 048bfbf2) and the two walk commits (ae6bec92, e2c30e0c).

## Findings

1. MINOR (carried from m2 and m3): the patch path (FileChange and the stream's file_change, lane vendor-b23) and the non-empty reasoning join have no real walk behind them: 0 of 38 walks contain either. Accepting the reader on w-o46 accepts those paths on constructed test input only. The acceptance record or its review copy should say so in words ("file_change: 0 seen; reasoning summaries: 0 non-empty seen"), and CODEX_SHAPES could count file changes the way the Gemini coverage line names unseen shapes. Not blocking.
2. MINOR (new): mutant M4, which reads the requested model from turn_context.collaboration_mode.settings.model instead of turn_context.model, survives every suite I ran, because the tests' constructed turn_context carries no collaboration_mode. The code is right (it reads `pay["model"]`, codex_native.py:401) and in all 38 real walks the two fields agree, so this is a test gap, not a defect. A test with the two fields different would pin it. Fixing it touches tests only, not CODEX_SOURCES, so it need not wait on or disturb an acceptance.
3. MINOR (carried from m1): no command-line road runs the Codex acceptance check on retained files (main's `check` is Gemini-only, native_reader_registration.py:700-733); Javier or a reviewer must call codex_check from Python. `verify` does cover the committed record.
4. NIT (new): CODEX_SOURCES hashes the reader, the join, drive.py, vendor_provenance.py and native_snapshot.py, but not the acceptance road's other modules (walk_register.py, pending_walk.py, mode_binding.py, walk_regrade.py, run.py, walk_runner.py). production_readers re-runs acceptance_problems with whatever those files say at load time, so a later edit that weakened one of them would not unregister the reader. Today's acceptance is unaffected (they are at 048bfbf2's bytes, which this review ran). Worth a follow-up, for the Gemini READER_SOURCES too.
5. NIT (new, for whoever touches the marker gate): the marker word occurs in w-o46's own real content (GARS repository text quoted in world_state and command outputs: native-turn-3.jsonl lines 6, 7, 19 and 21, and turn-1.jsonl). The gate scans only the session_meta payload, the register entry, the review and the record, so it correctly does not fire; widening it to whole snapshots would refuse this real walk.
6. NIT (new): the earlier review counted 24 floor-meeting and 14 single-turn walks; at the head I count 25 and 13 (listed in section 2). It does not change any conclusion; this list is the one to quote.
7. NIT (carried from n1, n2): the gate function is session_facts, not native_session; cwd is not a bound native fact and permission_mode is None for Codex. The acceptance write-up should say both plainly.

## What Javier would be accepting

That Codex 0.162.1's rollout for w-o46, read by this reader, shows the same thread, the same prompt that was launched each turn, the same requested model, the same agent messages, the same nine commands with the same statuses, exit codes and outputs, and the same completion as the streams the driver captured, turn by turn over three turns and two resumes, and that no later snapshot rewrites an earlier turn.
The same holds for all 38 committed GPT walks.
He would not be accepting patch edits or non-empty reasoning summaries on real evidence (finding 1), nor cwd or the permission mode as native facts.
The gates are consistency checks over producer-written bytes; the guarantee against a consistent fabrication is his acceptance commit in his own window, as the module's docstring says.
