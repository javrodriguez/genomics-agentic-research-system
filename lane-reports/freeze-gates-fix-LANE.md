# Lane freeze-gates-fix (Gap Study round 4)

Opus 5.5 medium lane agent of glitch-f1, under Javier's standing delegation.
Clone /Users/javrodher/aegis-builds/freeze-gates-fix-20261021 (`git clone --no-local` of the freeze-dry clone, no alternates, origin removed so nothing can be pushed by accident).
Branch lane/freeze-gates-fix from dry/all-225 = d5c0f7989083990f0eb76308b8eb79f86e41d7e4 (all 225 walks merged).
Started Wed 21 Oct 2026 21:57 EDT (clock read with `date`).

## The rulings, quoted

From glitch-f1's night log (/Users/javrodher/glitch/plans/gap-study-round-4/orchestrator-night-2026-10-13-claude.md, the line "RULED under the delegation: (1) the dry heads...", item (2)):

> new lane freeze-gates-fix for the six reds already present: mode_binding reads the CLI-written mode record where one exists (Codex rollout turn_context approval_policy and sandbox_policy, shared with settlement's T-16 reader) and, where a CLI writes none, the walk's recorded launch argv as an input-side check named as such, never "unrecorded" red and never a silent pass; fixture_walk reads the Claude walks' run tree from the record their ledgers do carry, with no edit to drive.py or any walk record; walk_regrade compares only the fields a walk's checker version wrote, and an absent nested_cli_calls passes only when the derived value is 0, else red; allowlist and build_draft: find why they differ and regenerate through their own builders only if the cause is new committed inputs, else report; lint_language: if the two review files are bound by the acceptance they are never edited (a recorded exemption with its reason), else fix the wording; test_rehearsals R4.empty updated to the registered state; no file in READER_SOURCES or CODEX_SOURCES changes; base dry/all-225.

## Red at the base (d5c0f798)

Each gate run on the Mac after `mac_slot.py light-ok --work gap-study-r4` exit 0, 150 s cap, `/usr/local/bin/python3.12 -I -B` through a runpy wrapper with cwd the clone (lint_language with cwd the study folder).
Raw output: /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/fgf/red-d5c0f798.json (runner gates.py beside it).

| Gate | rc | seconds | Last line |
|---|---|---|---|
| mode_binding.py --walks --check | 1 | 0.9 | FAIL 74 of 225 walk(s) drift from the pre-registration |
| fixture_walk.py --check | 1 | 6.0 | 149 FAIL lines, each a Claude walk naming `/tmp/run-<project>/...` paths "this verdict cannot place" |
| walk_regrade.py --check | 1 | 133.5 | walk_regrade: 28 problem(s) (w137-w164, nested_cli_calls recorded None, derived 0) |
| allowlist.py --check | 1 | 1.5 | FAIL allowlist-derivation.json does not equal what round 2's transcripts derive |
| build_draft.py --check | 1 | 35.8 | FAIL: the committed draft is missing or differs from what build_draft.py builds |
| lint_language.py native-readers/codex-review.md native-readers/gemini-review.md | 1 | 0.2 | 5 finding(s) across 2 input(s) |
| tests/test_rehearsals.py | 1 | 106.3 | FAILED (failures=1), TheRegister.test_empty_register_says_zero_walks, R4.empty |

## Causes (verified in code and records)

1. **mode_binding.** `modes_recorded` reads only the record-level `permissionMode` of transcript.jsonl (evals/gap-study-4/mode_binding.py:114-130), Claude Code's field; `judge` compares that with the pin (:180-208), so every vendor walk reads `unrecorded` against codex `bypass` and gemini `yolo` (routing.json pin_profiles).
   What the CLIs write, read from the 74 vendor walks:
   - Codex 0.162.1 writes a mode record: every rollout `turn_context` carries `approval_policy` and `sandbox_policy` (w-o46's last snapshot: three turn_context records, each `never` and `{"type": "danger-full-access"}`; thread_settings_applied repeats approval_policy).
     Pinned source (the rollout audit's retained copy at 092d3acd, /Users/javrodher/aegis-builds/gap4-codex-rollout-audit-20261014/src/codex-rs): exec/src/lib.rs:343-344 maps `--dangerously-bypass-approvals-and-sandbox` to `SandboxMode::DangerFullAccess`; exec/src/lib.rs:589-591 sets `approval_policy: Some(AskForApproval::Never)` for every headless exec (so `never` alone does not tell bypass apart; the sandbox policy does); protocol/src/protocol.rs:1086-1091 serializes the sandbox policy as `{"type": "danger-full-access"}`; protocol.rs:1000-1025 serializes `Never` as `never`.
   - Gemini 0.64.0 writes none: across the 36 Gemini walks, the stream's record keys are init {type, timestamp, session_id, model}, message, tool_use, tool_result and result {stats, status}; the session log's header is {sessionId, projectHash, startTime, lastUpdated, kind} and its patches set only lastUpdated, sessionId, updates, orderIds and removeIds; 0 of the 53 `<session_context>` copies mention an approval mode.
     The only "approvalMode" strings in Gemini walk files sit inside tool-result text (an agent reading the CLI bundle), never in a CLI-written field.
   - Settlement's T-16 reader (vendor-settle-DESIGN-2026-10-21.md, T-16) is designed, not built: check_take.py:4800-4804 is still PENDING. The reader built here is the one module-level function settlement can import, so the record is read once (see Design).
2. **fixture_walk.** `run_tree_of` reads the ledger's top-level `cwd` (fixture_walk.py:150-155), which drive.py writes on its own road (drive.py:1222); the Claude walk ledgers carry no `cwd` (w162's keys: agent, arm, ..., project, source, ...).
   Every Claude walk records its run tree in each turn's launch journal, `turn-N.jsonl.launch.json` `cwd` (w162 turn 1: `/tmp/run-fc5d36fd`), the same journal check_take's vendor reader uses (check_take.py:4418-4425).
3. **walk_regrade.** `agent_summary_problems` compares `nested_cli_calls` whenever check.json has `agent_calls` (walk_regrade.py:267-285).
   check.json shapes across the 151 Claude walks (read this session): 28 carry agent_calls and subagents without the key nested_cli_calls (w137-w164, checker_constants_sha256 b08b5496...); 3 carry it, value 0 (w165, w166, w168, the same checker constants); 120 carry neither agent_calls nor nested_cli_calls.
   The checker constants hash is the same for both shapes, so the key's presence is the record of which checker version wrote the file.
4. **allowlist and build_draft.**
   - allowlist: NOT new committed inputs. allowlist.py and allowlist-derivation.json are identical copies of round 3's (COPIED.d/w1a-cp1-scaffold.json, status `identical`, since ad88d14d, 6 Oct). Round 3's study.py had `ROUND1_REL = "evals/gap-study-2"`; round 4's has `PRIOR_REL = "evals/gap-study-3"` (study.py:49-52 in ad88d14d), so the same code now derives from round 3's 54 transcripts (503 calls seen) while the copied file is round 2's derivation (source `evals/gap-study-2`, 52 transcripts, 364 calls). evals/gap-study-3/transcripts last changed 22 Sep (2440b037), before the copy. Red since 6 Oct, unrelated to the walks or the acceptance. Not regenerated: reported (below).
   - build_draft: new committed inputs. The only differences are `checked_against` (committed: status PENDING, 0 sessions; built: status `read`, 225 sessions) and the pending list that entry leaves. `checked_sessions` (build_draft.py:677-689) reads leak_grep.sessions(), empty when the draft was last written and 225 walks now. Regenerated through `build_draft.py` itself.
5. **lint_language.** Both review files are bound: native-readers/codex-acceptance.json and gemini-acceptance.json carry `review: {file, sha256}`, and native_reader_registration.py:529, 593 refuses a review whose bytes do not hash to it. They are never edited; four recorded exemptions (one per line, codex-review.md:56, :70, :122 and gemini-review.md:157) go into language-allowlist.json with their reason, line text copied by script from the file.
6. **test_rehearsals R4.empty.** Its last leg runs `walk_register.main(["--check"])` on the committed register and expects "ok, having registered 0 walks" (tests/test_rehearsals.py:319-324); the register holds 225 walks since the merges.

## Design

- **mode_binding (fix 1).** The transcript reading stays as it is and keeps its two ledger comparisons (the driver wrote `unrecorded` from the same field, so they agree).
  A new per-harness reading decides the pin comparison:
  - claude-code: the transcript's `permissionMode` (unchanged), source named `transcript permissionMode`.
  - codex: `codex_recorded_mode(folder)`, reading the last retained rollout snapshot the ledger's `native_snapshots` names: every turn_context's approval_policy and sandbox_policy.type, and every thread_settings_applied approval_policy. `CODEX_MODE_RECORD = {"bypass": ("never", "danger-full-access")}` maps the pin, cited to the pinned source above. The reading is the pin's name only when every record agrees with the map and the turn_context count equals the rollout's turns; a missing snapshot, a turn without its turn_context, or any other value is red, quoted. Source named `codex rollout turn_context (CLI-written)`.
  - gemini: the CLI writes no mode record, so the check is input-side and says so: every turn's launch journal argv carries the adapter's own flags for the pin (gemini_adapter.MODE_FLAGS, `--approval-mode yolo`), exactly once, and no other mode flag (gemini_adapter.OTHER_MODE_FLAGS). Source named `launch argv (input side: Gemini 0.64.0 writes no mode record)`. A walk without a journal for every turn is red.
  - --check output prints each walk's source, and the ok line counts walks per source, so an input-side pass is never read as a recorded one.
  - Settlement's T-16 builds `vendor_codex_recorded_mode_reads` in check_take; it should import `mode_binding.codex_mode_records` and `CODEX_MODE_RECORD` rather than re-spell the map (handed back to glitch-f1 as a note to that lane).
- **fixture_walk (fix 2).** `run_tree_of`: the ledger's `cwd` first (drive.py's road, unchanged); else the launch journals' `cwd`, taken only when every `turn-N.jsonl.launch.json` beside the transcript records the same absolute path; disagreeing journals or none leave it None (unplaced stays red).
- **walk_regrade (fix 3).** In `agent_summary_problems`, when check.json lacks the key `nested_cli_calls` (key absence, never a null), that field leaves the comparison and the derived value must be 0, else a named problem; agent_calls and subagents compare as before. A present null still compares and is red.
- **build_draft (fix 4).** `python3 evals/gap-study-4/build_draft.py` rewrites prereg-draft.json, committed on its own (the w8e precedent: re-derived, no note).
- **lint (fix 5).** Four entries in language-allowlist.json, built by a script that reads each line's exact text.
- **R4.empty (fix 6).** The synthetic empty-register legs stay (they carry the silent-empty witness). The committed-register leg becomes: --check exits 0 and prints `ok: N registered walk(s), each with its folder, none counted`, N read from register.json's own `walks` list, N > 0, and no "registered 0 walks" line.
- **Copy record.** COPIED.d/freeze-gates-fix.json (this lane's fragment, edits recorded there without transfer, as w8e did) and checks.d/freeze-gates-fix.txt (the changed tests).
- No file in READER_SOURCES or CODEX_SOURCES changes; no walk record, drive.py or review file changes.

## Stages

| Stage | Commit | What |
|---|---|---|
| S1 | d05e2264 | mode_binding: codex rollout record, gemini launch argv (input side, named), transcript for claude-code; test_mode_binding M4-vendor + witnesses approval-only, argv-unread |
| S2-S3 | df9bde14 | fixture_walk run tree from the launch journals (bound to the ledger's project); walk_regrade compares only the fields written; tests/test_freeze_gates_fix.py F2-runtree, F3-nested + four witnesses |
| S4 | 4dc1bbfd | prereg-draft.json re-derived by `build_draft.py` (only checked_against and its pending pointer move) |
| S5 | 1dbcfd42 | four excusals in language-allowlist.json for the hash-bound reviews |
| S6 | f2fdd5ba | R4.empty and R9.sessions read the registered state; test_mode_binding's witness compile restores sys.path |
| S7 | 84809b5b | COPIED.d/freeze-gates-fix.json, checks.d/freeze-gates-fix.txt (copy_manifest --check ok, 61 fragments) |

Files changed d5c0f798..84809b5b: the 11 listed in S1-S7; none of the 11 READER_SOURCES and CODEX_SOURCES files (derived from native_reader_registration itself), no walk record, no native-readers/ file, no drive.py.

## Red-first evidence (unit tests, base code against the new tests)

- test_mode_binding with d5c0f798's mode_binding.py: FAILED (failures=3, errors=1): M4-vendor ("the session recorded 'unrecorded'; m-o under codex is pinned to record 'bypass'"), both new witnesses' green precondition, and CODEX_MODE_RECORD absent. Green: 12 OK, four witnesses red. Output: scratchpad fgf/green-test_mode_binding.txt.
- test_freeze_gates_fix with d5c0f798's fixture_walk.py and walk_regrade.py: FAILED (failures=6): F2 "every journal names the project's folder: run tree None", F3 "no key, derived 0: named (... nested_cli_calls (recorded None, derived 0))", and the four witnesses' precondition. Green: 7 OK, four witnesses red. Outputs: fgf/red-test_freeze_gates_fix.txt, fgf/green-test_freeze_gates_fix.txt.
- R9.sessions: description_problems on the built draft was ['R9.sessions'] before, [] after; four hand mutants of the draft (status, a session dropped, a voiding word, the old PENDING state) each give ['R9.sessions'].
- R4.empty's silent-empty witness still red after the edit (fgf/witness-silent-empty.txt).

## Gates at the head 84809b5b (Wed 21 Oct 2026 23:12-23:19 EDT, same runner, light-ok, 150 s cap)

Raw: fgf/green-head.json.

| Gate | d5c0f798 | 84809b5b |
|---|---|---|
| mode_binding.py --walks --check | rc 1, FAIL 74 of 225 | rc 0, 225 graded: 38 codex rollout (CLI-written), 36 launch argv (input side, named), 151 transcript |
| fixture_walk.py --check | rc 1, 76 clean, 149 unplaced | rc 1, 224 clean, 1 unplaced (w023, below) |
| walk_regrade.py --check | rc 1, 28 problems (133.5 s) | rc 0, ok (127.6 s; 141.3 s on an earlier run: near the cap, athena should time it) |
| allowlist.py --check | rc 1 | rc 1, unchanged on purpose (cause 4, not new inputs) |
| build_draft.py --check | rc 1 | rc 0 |
| lint_language.py on the two reviews | rc 1, 5 findings | rc 0; whole study folder clean, 123 inputs |
| tests/test_rehearsals.py | rc 1, R4.empty | rc 0, 9 OK (91.2 s) |
| native_reader_registration.py verify | (rc 0 in the dry report) | rc 0 |

Interpreter state: test_freeze_gates_fix, test_rehearsals and test_mode_binding run in one process in that order (fgf/oneproc.py): all pass, no sys.modules entry replaced or removed, environ and cwd unchanged; sys.path grows only by test_rehearsals' and mode_binding's own unconditional top-level inserts, both present at d5c0f798. test_executed_turn_refusal before test_freeze_gates_fix: both pass, the same state result.

## Handed back to glitch-f1

1. **fixture_walk w023, a genuine finding.** The Haiku session (scope-read, trap, project run-f742f2d1) ran `python3 _system/stage00_register.py finalize ... 2>&1 | tee /tmp/finalize.log`, a scratch file outside its run tree /tmp/run-f742f2d1; it was hidden among the 149. Round 3 named this class (the session's own scratch file, fixture_walk.py docstring) and left the call to the owner; the ruling does not cover classing it. Options: rule the walk's verdict as a recorded exception, or add a class for a path the session itself created (needs its own design).
2. **allowlist.py --check, cause reported, not regenerated.** allowlist.py and allowlist-derivation.json are `identical` copies of round 3's (COPIED.d/w1a-cp1-scaffold.json); round 3's study.py named round 2 as the prior round, round 4's names round 3 (study.py PRIOR_REL), so the code now derives from round 3's 54 transcripts (503 calls) against round 2's committed derivation (52 transcripts, 364 calls). Red since ad88d14d (6 Oct). Regenerating would break the identical-copy claim. Not a freeze_rehearsal COMMAND. Needs a ruling: drop the copy, mark it edited and re-derive from round 3, or retire the check.
3. **More pre-acceptance expectations likely sit in the full battery.** test_native_history_record fails standalone at the head (2 errors: `test_the_production_registry_leaves_it_pending` reaches native_reader_registration.production_readers -> _repo's git call, native_reader_registration.py:649, 285; and a TypeError at line 80); it touches no file this lane changed. test_build_draft (whole), test_scaffold (killed at the 150 s cap) and test_round4 were not run on the Mac: athena's.
4. **Settlement's T-16** should import mode_binding.codex_mode_records and CODEX_MODE_RECORD rather than re-spell them; the pinned-source cite is in mode_binding.py.

## Deviations, flagged

- R9.sessions in tests/test_build_draft.py is a seventh red outside the six, the same cause as the draft (the merged walks); fixed the same way as R4.empty, since test_round4.py (the rehearsal's first COMMAND) runs every tests/test_*.py.
- A lane COPIED.d fragment and checks.d file, as the w8e and review-kit-port lanes did.
- The clone's origin remote was removed so nothing can be pushed.

## S8 (glitch-f1's rulings on the hand-back, Wed 21 Oct 2026 about 23:25 EDT)

The rulings, as relayed: (1) w023's file is a recorded per-walk exception naming the transcript line and the reason, printed whenever it applies, no general class; (2) allowlist.py: not regenerated yet: write every consumer, what a round-4 derivation adds or removes, whether any walk verdict changes, then hand back; (3) the stale pre-acceptance test expectations (test_native_history_record, test_pending_walk, test_vendor_admission's production_readers test) move to the post-acceptance state without weakening, red first, witnesses kept red; (4) the T-16 note is adopted; (5) R9.sessions and the COPIED.d and checks.d fragments are ratified.

### Item 2: allowlist-derivation.json, every consumer and the delta (read this session, nothing regenerated)

- What the file is: the Bash `--allowedTools` entries the prior round's transcripts could legally support (allowlist.py docstring); it excuses commands, not words (the word excusals are language-allowlist.json, a different file).
- Consumers in round 4: only allowlist.py itself (`--check` compares derive() with the file; `pinned()` reads `driver_change.allowed_tools` from the pre-registration). A grep of evals/gap-study-4 for `allowlist-derivation`, `import allowlist` and `allowed_tools` finds no other reader. checks.d names no allowlist.py command. ci.yml runs `allowlist.py --check` for round 3 only (ci.yml:306-308, `evals/gap-study-3/allowlist.py`); the gap-study-4 job (ci.yml:431 on) does not run it. It is not in freeze_rehearsal's COMMANDS.
- For which harnesses: none in round 4. claude_code_adapter.py:17 (C15-2) retires round 3's `--allowedTools` for the box; arm A passes `--permission-mode bypassPermissions` with `--disallowedTools`; Codex runs `--dangerously-bypass-approvals-and-sandbox` and Gemini `--approval-mode yolo`. drive.py:721 and :1221 still read `driver_change.allowed_tools`, on round 3's host road (`send`), which round 4's refusals shadow (mode_binding.py docstring, ROUND3_ROOTS). prereg-draft.json has no `driver_change` key, so `pinned()` returns None. 0 of the 225 committed launch journals carry `--allowedTools`.
- What a derivation from round 3's transcripts would change (allowlist.derive() at 84809b5b; script fgf/aldelta.py): source evals/gap-study-2 (52 transcripts, 364 calls, 22 entries: route 15, shape 5, arbitrary 2) becomes evals/gap-study-3 (54 transcripts, 503 calls, 16 entries: route 7, shape 7, arbitrary 2). Added 5: `Bash(find data:*)`, `Bash(find gars:*)`, `Bash(ls -R:*)`, `Bash(sleep 5:*)`, `Bash(tail -5:*)`. Removed 11: `Bash(cat gars/00_initialize_project/CONTEXT.md:*)`, `Bash(cat gars/01_prepare_samplesheets/CONTEXT.md:*)`, `Bash(cat gars/CLAUDE.md:*)`, `Bash(cat gars/CLAUDE.md;:*)`, `Bash(cat gars/CONTEXT.md:*)`, `Bash(cd "$(git:*)`, `Bash(cd gars;:*)`, `Bash(find .:*)`, `Bash(ls gars/00_initialize_project:*)`, `Bash(pwd; ls:*)`, `Bash(python3 _system/stage01_samplesheet.py:*)`. problems() on the new derivation: none.
- Walk verdicts: none of the 225 changes. No checker, grader, regrade or walk gate reads the file or `allowed_tools` (the grep above), and no walk was launched with an allowlist.
- Options for the ruling: (a) retire the check and the file in round 4 (drop both from COPIED.d's w1a fragment; nothing reads them); (b) re-derive as an edited copy from round 3 (the delta above; it would then describe round 3's routes, which no round 4 arm uses); (c) keep it red and named. Recommendation: (a), since round 4 has no allowlist condition to derive.

### Item 1: w023 (S8a, 65cd0026)

fixture_walk.RECORDED_EXCEPTIONS holds one entry: w023, `/tmp/finalize.log`, transcript line 74 (the only line naming it), that line's sha256 and the command the agent ran there (`... 2>&1 | tee /tmp/finalize.log`), the reason and the ruling. It applies only while every line naming the path is a recorded line with those bytes and that command; `--check` prints an EXCEPTED line for it; an exception matching no committed transcript fails (stale_exception_problems).
Red first: test_freeze_gates_fix against 84809b5b's fixture_walk.py FAILED (failures=3, errors=1: F4 and its two witnesses' precondition, RECORDED_EXCEPTIONS absent). Green: 11 OK, six witnesses red (exception-unbound, stale-silent added).

### Item 3: the pre-acceptance expectations (S8b, 3e301939)

Cause, one for all of them: since 5457e75e the study holds committed acceptance records, so production_readers() runs git on the study tree (native_reader_registration.py:649 -> :285), and test_box_integration's process guard admits git only under its scratch folder; every fake-runtime road reaching the driver's default registry read was held.
Fix: under the guard, a registry call naming no study, or the study tree, reads an empty scratch study (the unregistered state those roads model); a road's own scratch study passes through. The real tree's registry is asserted unguarded: test_native_reader_registration AcceptedRecords (both records, last commit on each 5457e75e, registry {codex, gemini}) and test_vendor_admission (registry holds both; a registry without the harness refuses before the reader, both roads). test_native_history_record: readers=None goes through the production call (spied) and is pending; the accepted Gemini reader refuses a snapshot that is no Gemini log; the guarded registry reads a scratch study.

| Module | 84809b5b | 3e301939 |
|---|---|---|
| test_pending_walk | 43 failures (23 tests) | 23 OK, run class by class (the whole module passes the 150 s cap once nothing fails fast) |
| test_pending_codex_walk | 10 failures | 12 OK |
| test_vendor_admission_regrade | 3 failures | 3 OK |
| test_native_snapshot | 2 failures, 1 error | 15 OK |
| test_vendor_walk_road | 6 failures | R9Road, P5WalkRoad, P5WalkWitnesses OK; R9Witnesses ran past the light cap and the heavy slot refused ("CPU speed limit 58 is below 100"): athena's |
| test_native_history_record | 2 errors | 5 OK |
| test_vendor_admission | 1 failure | 10 OK (its VA witnesses included) |
| test_native_reader_registration | 2 failures | CheckSession and AcceptedRecords 5 OK; the whole module took 143 s at the base, so athena's |

One process (fgf/oneproc-s8.txt): test_freeze_gates_fix, test_native_history_record, test_vendor_admission, test_mode_binding pass, no sys.modules entry replaced or removed; test_vendor_admission's real-registry assertion passing right after the guarded module shows the registry patch undone at teardown.

### Gates at 3e301939 (Thu 22 Oct 2026 00:22-00:27 EDT; fgf/s8-head.json)

mode_binding ok 225; fixture_walk ok 225 (1 by the printed exception); walk_regrade ok (114.3 s); allowlist rc 1 (item 2, awaiting the ruling); build_draft ok; lint clean; test_rehearsals 9 OK (83.9 s); native_reader_registration verify rc 0.

### For athena

test_vendor_walk_road R9Witnesses, test_native_reader_registration whole, test_build_draft whole, test_scaffold, test_box_integration, test_round4, walk_register --check, run.py --walks --check.

## S9 (glitch-f1's rulings, Thu 22 Oct 2026)

### Allowlist retired (fe25636c), a recorded departure

Ruling: retire round 4's allowlist check and its derivation file. Reasons, as ruled: `--allowedTools` was retired for the box by C15-2 (claude_code_adapter.py:17); no round 4 walk's argv carries it (0 of 225); no check reads the file; it is not a freeze_rehearsal command; ci.yml runs the check for round 3 only. Round 3's copies stay untouched.
Done: `git rm` of evals/gap-study-4/allowlist.py and allowlist-derivation.json, and their two identical-copy entries in COPIED.d/w1a-cp1-scaffold.json (copy_manifest has no retired status, and a fragment cannot claim a missing file); the departure is recorded in COPIED.d/freeze-gates-fix.json and here. tests/test_scaffold.py used allowlist.py as an identical-copy stand-in (test_a_copy_that_differs_without_an_edited_entry_is_refused); ci_conclusion.py, still a w1a identical copy, stands in now (review_kit/ files avoided: the review-kit port edits them).
Checks at fe25636c: copy_manifest --check ok (528 files, 61 fragments); freeze.py --check "529 owned paths checked"; TheManifest's two affected cases OK (114.3 s); mode_binding ok 225, fixture_walk ok 225 (1 by the printed exception), walk_regrade ok (120.4 s), build_draft ok, lint clean, test_rehearsals 9 OK, native_reader_registration verify rc 0 (fgf/s9-head.json).
Note for the fold: the review-kit port (8c3c95ae) also edits tests/test_scaffold.py near line 145; expect a textual conflict there at the merge.

### test_freeze_shapes, the committed draft's legs

Cause: a pre-acceptance expectation, not settlement and not a missing leg. TheFreezeGateHasThreeLegs.test_fs_check_the_committed_draft_names_every_leg required "leg iii" for both arms; leg (iii) is "production_readers() holds the harness" (freeze.py:352-362), which holds for both since 5457e75e, so freeze.unrecorded_shapes_problem names legs (i) and (ii) only (read at the head: leg i and leg ii present for both arms, T-11 present, leg iii absent for both).
Fix: the test (renamed ..._names_every_open_leg) keeps legs (i) and (ii) and the T-11 line, and requires the registry to hold both readers, registration_problems to be empty for both harnesses, and no leg iii line. Leg (iii)'s refusals stay bound on synthetic registries (FS-check's main cases, CHECK_WITNESSES "leg iii deleted" and "leg iii's OSError refusal deleted", run in Witnesses).
Red first: the old test at fe25636c FAILED ("'arm O (codex): leg iii:' not found"). Green: TheFreezeGateHasThreeLegs and Witnesses, 4 OK (92.7 s). Legs (i) and (ii) stay named for stage V (settlement).

## S10 (the lane review's MINORs and NITs; review /Users/javrodher/aegis-builds/REVIEW-freeze-gates-fix-cb49df6.md, VERDICT PASS; written Thu 22 Oct 2026 01:07 EDT)

- **m1.** codex_recorded_mode also requires the rollout's turn count to equal the walk's turn streams (turn-N.jsonl, never a link). The 38 committed Codex walks pass. test_mode_binding adds a two-snapshot walk (the first snapshot covering 1 turn, the last 2) and a walk whose last snapshot is short of its streams; witness first-snapshot (the reviewer's L11) is red.
- **m2.** test_freeze_gates_fix F4: an exception whose path is inside the study leaves the verdict "leaks" (witness exception-excuses-leak, the reviewer's R4, red; the case already held on the old code, a guard on existing behaviour). fixture_walk now refuses a linked launch journal instead of skipping it (run tree None); F2 case "a symlinked journal" was red on cb49df65, and witness linked-journal-read (J4) is red. The Gemini journal's harness field (L10) is now checked by the adapter's own launch facts (m3), case "a journal naming another harness".
- **m3.** argv_mode calls gemini_adapter.submitted_mode for every turn, so the flag rule and vendor_provenance.launch_facts are the adapter's. The registered invocation is rebuilt from records other than the journal: launch.json take_id and the take-inspect WorkingDir, the ledger's model, the transcript's harness-turn envelopes (sent, vendor_session_id; FIRST_TURN on turn 1), the pin. Read first: on all 36 Gemini walks the journals' container_id equals take_id, their cwd the WorkingDir, and there is one envelope per journal; the gate passes all 36. New cases: a journal that is not the registered invocation (an extra option), one naming another harness, a linked one; all red. The local harness and link pre-checks were dropped as equivalent to the adapter's, so their mutants are not kept as witnesses.
- **n1.** COPIED.d/freeze-gates-fix.json now names F4 and the eight witnesses; checks.d/freeze-gates-fix.txt lists test_native_history_record, test_vendor_admission, test_native_reader_registration and test_freeze_shapes too.
- **n2.** The exception's separate command-text check is dropped: the line's sha256 binds the bytes the command sits in (comment at the check).
- **n3.** Unchanged (equivalent today: check_take.nested_cli_calls returns an int).
- **n4.** The new lines over 120 characters are wrapped (fixture_walk's exception entry and docstring, walk_regrade's problem line, the test fixture).
- **n5.** One wording: the input-side label is the code's, `launch argv (input side: the CLI writes no mode record)`; the S1 design line above that spells it "Gemini 0.64.0 writes no mode record" is superseded by this one (left in place, the file being a record).
- Red first: test_mode_binding with cb49df65's mode_binding.py FAILED (failures=6: M4's three new cases, "codex the last snapshot short of the walk's turns", "gemini a symlinked journal: passed", "gemini argv not the registered invocation: passed", and the witnesses' precondition); test_freeze_gates_fix with cb49df65's fixture_walk.py FAILED (failures=5: F2 "a symlinked journal", the witnesses' precondition). Green: 13 OK each, witnesses red (fgf/green-s10-mb.txt, fgf/green-s10-fgf.txt).
- Gates at the S10 tree (fgf/s10-head.json): mode_binding ok 225 (38 Codex rollout, 36 launch argv input side, 151 transcript); fixture_walk ok 225 (1 by the printed exception); walk_regrade ok (89.1 s); build_draft ok; lint clean; test_rehearsals 9 OK; native_reader_registration verify rc 0. One process: test_freeze_gates_fix, test_native_history_record, test_mode_binding pass, nothing replaced or removed.
- No READER_SOURCES or CODEX_SOURCES file changed.

## S11 (the closure check's residual MINOR and NIT; written Thu 22 Oct 2026 01:16 EDT)

- The S10 rule "rebuilt from records other than the journal" is now bound: three M4 cases, a journal cwd other than launch.json's take-inspect WorkingDir, a journal container_id other than its take_id, and a ledger model_requested other than the argv's model (that model pinned too, so only the launch facts can refuse it). Each is red at the head, and the reviewer's mutants C5 (run tree from the journal), C6 (container from the journal) and C10 (a fixed model) are in-suite witnesses, each red.
- C11: a turn-N.jsonl that is a link or not a file is refused (linked_stream_problems, both vendor readings), never counted or skipped; cases for a Codex and a Gemini walk; the reviewer's C11 edit is a witness, red. On 78d59ce1 the Gemini linked-stream case passed (red first), the Codex one was already red through the stream count.
- test_mode_binding: 17 OK, nine witnesses red (fgf/green-s11-mb.txt; red run fgf/red-s11-mb.txt: 8 failures on 78d59ce1's mode_binding.py, the new case and the new witnesses' precondition). Gates: mode_binding ok 225 (38, 36 input side, 151), fixture_walk ok 225.

## S12: athena's battery on 12e021d3 (gap4-gatesfix-12e021d-12e021d-20261022T064455Z; written Thu 22 Oct 2026 04:11 EDT)

Step 1: Ran 1303, OK (skipped=82). Step 2, three reds:

- **test_walk_layout L7CopyRecord.test_the_manifest_reads_the_register** (w8a-walk-layout.txt:5, and a member of test_round4). Log: "AssertionError: Lists differ ... First list contains 2330 additional elements. First extra element 1: 'rehearsals/w-g12/check.json is under evals/gap-study-4/ and no fragment in COPIED.d/ claims it'". Mac, own process, light-ok: red at d5c0f798 (base worktree, the same 2330 extra elements) and at 12e021d3. **Pre-existing on the base.** Cause: a pre-walk expectation: present = copy_manifest.files_here() now holds the 225 committed walks' files, and the test's synthetic register listed only w-0001, so every committed walk file read as unclaimed. Fixed anyway as this stage (ruling 3's class): every register the test hands in now carries the committed register's walks, read from register.json, plus the synthetic w-0001/w-0002 each leg varies. test_walk_layout 14 OK, --witnesses 21/21 red (L7's three included: fragment-record-admitted, record-claims-dropped, unregistered-claimed).
- **test_build_draft.py --witnesses 1 to 6** (w5c-draft-ci.txt:9-14). Each FAIL is "subprocess.TimeoutExpired: ... '--mutant', '<name>'] timed out after 180 seconds" on its group's first mutant: agent, alpha-shape, amendment, answers, box-users, caps. So no witness was graded; none went blind. A witness substitutes one builder accessor (agent: rows[0].agent.harness -> "fake-harness", bound to R11.agent; the others likewise per test_build_draft.py's DESCRIPTION_MUTANTS) and reruns the whole file, under run_witnesses' 180 s timeout (test_build_draft.py:2236-2237). **Pre-existing on the base.** Cause: build_draft.build() reads every committed walk's session through leak_grep (checked_against, build_draft.py:677-689); measured on the Mac, build() takes 22.6 s at d5c0f798 and 22.9 s at 12e021d3, both with 225 sessions, and the test file calls it about 19 times. On athena test_build_draft went from about 25 s on every earlier battery (for example gap4-hookctl-d9d9b79, 26.0 s) to 887.4 s on 12e021d3, so each whole-file mutant run now exceeds 180 s. The command itself runs past the Mac's light cap, so it was not rerun here. Not fixed: a fix is a ruling (raise the 180 s timeout, or have the test pin checked_against's session read) for glitch-f1.
- **test_round4** (exit 1, "Ran 4788 tests ... FAILED (failures=2, skipped=32)"). The log keeps only the last failure block, which names one member: test_walk_layout.L7CopyRecord.test_the_manifest_reads_the_register (above). The second member is not named anywhere in run.log or exit.json, so I do not name it; it needs test_round4's full output on athena.

## S13 and S14 (glitch-f1's rulings 2 and 3 on the S12 hand-back; written Thu 22 Oct 2026 06:26 EDT)

- **S13, test_build_draft's session read pinned (0ea3f3ae).** setUpModule memoises leak_grep.derive per process on exactly what it reads (the draft's leak_words and leak_context_excusals, each committed session's path, size and mtime); a draft whose leak words or excusals differ derives afresh, so no test reads a stale result. Profile first: of a 22.6 s build, 22.2 s is derive, 11.3 s of it check_take.context_leaks and 10.7 s the word regexes; memoising context_text alone did not help, as derive's draft-dependent regexes dominate. One real derive per process (25.8 s); the whole file 119.9 s on the Mac (was past the cap; 887 s on athena), 49 OK; the six groups' first mutants (agent, alpha-shape, amendment, answers, box-users, caps) each fail the file in 72.9, 71.6, 76.2, 93.4, 78.7 and 73.1 s on the Mac, under run_witnesses' 180 s timeout. The full --witnesses groups run past the Mac's cap: athena's.
- **test_round4 at 0ea3f3ae on the Mac** (heavy slot, 6736.6 s; fgf/s13-round4.txt): "Ran 4788 tests ... FAILED (failures=5, errors=1)", each named:
  - test_freeze_gates_fix.TestWitnesses.test_witness_absent_key_compared: "'walk_register' : absent-key-compared: the witness registered a module". **New on my head (S2-S3's test).** Cause: an earlier module in the round drops walk_register from sys.modules; the witness compile of walk_regrade's source re-imports it, and my own guard caught the re-registration (a second walk_register copy left behind). Reproduced in one process by dropping walk_register before the witnesses: 2 failures (absent-key-compared, exception-excuses-leak). **Fixed as S14**: the witness compile removes any module it newly registered, in test_freeze_gates_fix and test_mode_binding; the reproduction is clean, 13 OK and 17 OK, witnesses 8 and 9 red. Most likely athena's unnamed second member (not confirmed: athena's log does not name it).
  - test_config_folder.C7Shapes.test_shape_rules (OSError: [Errno 92] Illegal byte sequence on a non-UTF-8 file name), test_run_take TestExecArgv.test_exec_argv and TestWalkLoginPlace.test_the_walk_login_place ("refused variable(s) set in the caller", a *_TOKEN variable in this Mac session's environment), test_walk_builders B13Lease.test_the_driver_and_walkrepo_get_the_lease_secrets and B19VendorConfig.test_the_vendor_config_is_written_on_the_walk_road ("raised Refused: the run tree ..."): red at d5c0f798 and at the head on the Mac, absent from athena's two failures at 12e021d3. **Pre-existing, Mac environment.**
