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
