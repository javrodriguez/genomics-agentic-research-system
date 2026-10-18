VERDICT: CHANGES

# Review of T4 group (d), lane vendor-admission, range 6302fd38..7c774ad4

Fresh, independent reviewer (cloud), briefed by glitch-b5; written 2026-10-18 00:55 EDT. Head reviewed: 7c774ad4
(lane/vendor-admission, not moved during the review). No code, test or fixture was changed; the two probes below ran
from a scratch folder outside the clone, against the head's own test builders.

Two MINOR findings, both reproduced: a vendor take's account-email count reads 0 when a retained snapshot the ledger
names is missing, and the vendor sweep admits whatever it recorded at the take's own session path, where Claude Code's
sweep also checks the shape and session id. Everything else in scope holds. All six FOR THE REVIEWER points are
acceptable.

## Test counts (python3, TMPDIR outside the clone)

Red first, each red commit's new tests run on its own tree (each red commit is test or fixture only, so its code is its
parent's). Every count and reason matches the lane file:
- a43c0561 test_vendor_body: failures=2. P2Cases fails because the two new session-file cases add no
  transcript-unreadable on codex or gemini, and the witness "an unnamed session file admitted" has its case red on
  check_take.py.
- 71697586 test_walk_builders: failures=1. B18Native fails because AGENTS.md and GEMINI.md above the checkout get
  "placed" for both harnesses. The CLAUDE.md cases pass already through drive.run_tree_problems, as they should.
- e359efbf test_vendor_entries: failures=13 errors=3. The errors are AttributeError on vendor_event_counts; the
  failures are checker_for admitting only claude-code, the entries missing, and the witnesses with their cases red.
  test_take_checker_dispatch: failures=1, CHECKER_ENTRIES is ['claude-code'].
- ca2485e3 test_walk_runner R5 to R13 classes: failures=3. Two are r4c9-comment's sha256 differing; the third is
  R8WalkRoad not finding "check4 reads claude-code only". test_checker_body: failures=2 (R4-guard and its witness).
  test_vendor_script: failures=3 (V0-checker and the two guard witnesses).
- 42293fdb test_vendor_session: failures=3 errors=11, AttributeError on vendor_session_store_problems and
  vendor_session_binding_problems, and the entry cases red.

Green at 7c774ad4:
- Every checks.d/vendor-admission.txt line exits 0 (21 lines). Among them: test_vendor_admission 10,
  test_vendor_admission_regrade 3, test_freeze_shapes 9, test_vendor_script 8, test_vendor_check 26,
  test_take_checker_dispatch 5, test_pin_for_vendor 2, test_vendor_body 10, test_vendor_roads 13,
  test_vendor_entries 8, test_vendor_session 5, vendor_check_fixtures --check, and every check_vendor_sources line
  (PF, P0, P0b, P1, P2 x3, P3, P4).
- Named modules: test_checker_body 30, test_check_take 15, test_pending_walk 23, test_pending_codex_walk 11,
  test_vendor_checker_road 5, test_walk_grade_seam 3, test_drive_loop 27, test_walk_wiring 20, test_walk_recheck 17,
  test_vendor_take_records 4, test_native_reader_registration 7, test_scaffold 49, test_box_integration 61.
- test_walk_builders 88 (--witnesses 42/42 red) and test_walk_runner whole 89 (--witnesses 73/73 red).
- lint_language on evals/gap-study-4/: clean, 115 inputs, 23 excused lines. lint_pooling: clean. copy_manifest
  --check: ok, 477 files from 60 fragments.
- test_nested_agent 35: the two TheSweep failures only (test_review_r15_reads and
  test_the_program_finds_each_session_shape_and_nothing_else). These come from this container running as root. The
  range does not touch test_nested_agent or the sweep code.

Scope item 6: `git diff --stat 6302fd38 7c774ad4` edits no READER_SOURCES or CODEX_SOURCES file, as read from
native_reader_registration. Two code files change: check_take.py (P3, R-1, P4, NIT 2) and walk_builders.py (NIT 7).
Neither file is in either list, and both are as the plan and the rulings name. The other changes are tests, the fixture
writer, the COPIED.d reasons and checks.d.

## Findings

1. MINOR, evals/gap-study-4/check_take.py:4499. vendor_email_problems skips a ledger-named published file it cannot
   read (`except OSError: continue`), so the account-email count reads 0 and nothing refuses the take.
   - Reproduced on the test builders' clean codex and gemini takes (three retained snapshots each): deleting
     session/native-turn-1.jsonl, which the ledger's native_snapshots names, and calling check4_vendor returns ok. The
     routed reasons are exactly the clean take's, and the events are account-email 0, study 0, outside 0. vendor_reach
     reads only the last snapshot, the store checks listing counts, and the binding legs read the last snapshot, so no
     reader binds an earlier snapshot's presence.
   - Consequence for the study: round 12's NIT 2 and NIT 6 rule that an unread email count raises CheckRefused and
     never counts 0, and that a file no reader binds never counts 0. This road does both: it counts 0 on bytes it
     never read. The drive's bound (the checker's count not above the scan's masked hits) passes on a 0, so a vendor
     take could reach its verdict with account-email 0 while one of its published records was never opened.
     Claude Code's count stands on a transcript its readers must open.
   - Fix, red first: a named file that cannot be read returns a transcript-unreadable line by name, as the unnamed-file
     branch does, so vendor_event_counts raises CheckRefused. Add an F3 case (a ledger-named snapshot missing; both
     vendors) and a witness that restores the skip.

2. MINOR, evals/gap-study-4/check_take.py:4951-4956. vendor_session_store_problems drops every sweep record at the
   take's own session path before sweep_violations runs, whatever shape and session id the sweep recorded there.
   - Claude Code's session_store_problems admits the own path only when the record's shape is claude and its session
     id is the take's own (sweep_violations: `path in admitted and shape == "claude" and sid == own_id`).
   - Reproduced: rewriting every sweep record in a clean take's session-store.json to [own path, "claude",
     "00000000-0000-0000-0000-000000000000"] leaves vendor_session_store_problems empty for codex and for gemini.
   - Consequence for the study: the nested-agent sweep is silently weaker for arms O and G than for arm C. A sweep
     showing another harness's session, or another session id, in the take's own file at turn k is admitted. Leg 2
     reads the session id of the last retained snapshot only, so an earlier turn's sweep is the only record of that
     file at that turn. This is against the principle; nothing in the table marks the leg NOT COMPARABLE.
   - Fix, red first: drop only the record equal to [own path, harness, the CLI's session id] and let any other record
     at that path reach sweep_violations. Add a store case (the own path recorded with another shape, and with
     another session id; both vendors) and a witness that restores the path-only filter.

## The FOR THE REVIEWER points

1. Acceptable. walk_builders.build_run_tree is the one road to a walk's checkout: walk_runner's road goes through it
   with the row's harness, at walk_builders.py:1207. build_run_tree always calls place_instruction_file, and
   place_instruction_file runs inherited_instruction_files for codex and gemini. drive.main's take road launches the
   Claude CLI only, through one_turn, and no code outside check_take.py reaches check4_vendor, check4_walk_vendor or
   CHECKER_ENTRIES. inherited_instruction_files uses os.path.lexists over every parent of the resolved tree. Probed:
   a dangling GEMINI.md link two folders up and a CLAUDE.md link one folder up are both listed. The check runs once,
   at build, which is when drive.no_inherited_instructions runs too (clean_run_tree), so the timing is the same as
   Claude Code's. lexists is stricter than drive's is_file, which misses a dangling link. Keeping the check outside
   drive.py, which is a READER_SOURCES and CODEX_SOURCES file, is the right call.
2. Acceptable. CheckRefused propagates out of take_checker and the drive holds the take, the same outcome as check4's
   own "check() and its reader disagree". A gemini take whose operator records disagree is therefore held, never routed
   as readers-disagree. That is stricter than routing, not weaker, though it routes differently from a codex take with
   the same cause. Worth one line in the table's readers-disagree row when it is next touched.
3. Acceptable. drive.take_checker calls checker_for, then side, then entry (drive.py:3602-3606), so _vendor_side's
   refusal comes before any vendor reading. V0-dispatch and its witness vendor-on-claude-entry pin it.
4. Acceptable. No check, fixture --check or witness reads the committed F1 or F2 store. Every take a test builds goes
   through vendor_check_fixtures.write with store=True, and the committed folders are only byte-compared (P1-fixtures)
   and read by the P1 view. vendor_check_fixtures --check compares against files(store=False), so a store added to F1
   or F2 would turn it red. An excusal scoped to those exact lines would be safe: language-allowlist.json matches only
   when the file, the pattern and the exact line text all agree, so it cannot switch ratio-slash off anywhere else, and
   a regenerated line brings the finding back. It stays a person's ruling.
5. Acceptable. The P3 refusal words differ from check4's (for example "vendor take" and "the account-email count could
   not be read"); no other anchor moved.
6. Acceptable. This review ran test_walk_runner --witnesses and test_walk_builders --witnesses here, both green. The
   whole battery and the generated walk_builders sweep remain glitch-b5's to run on the home server.

## Scope items, ruled

- P3: an unread reach (records None) and an unread email reading (any line not account-email) raise CheckRefused.
  Codex image_generation_call, a gemini snapshot the projection refuses and an unnamed session file are covered by
  P3-unread and its witnesses. The one road to a 0 on unread bytes is finding 1.
  - The event lines are lifted with the invariant `(counts > 0) != lifted`, as check4 lifts them. The arm binding,
    ledger_budget_problems and the CheckRefused preamble match check4's.
  - CHECKER_ENTRIES admits codex and gemini only as (_vendor_entry, _vendor_side), and checker_for still refuses any
    other harness.
- P4: the closed store shape is stricter than Claude Code's (a listing per retained snapshot plus publish, one sweep
  per post, the drive's two counts re-derived). native_rel is derived with native_snapshot's own locators for the CLI's
  id.
  - Legs 1 to 3 read the launch journals, the envelopes and the last snapshot, as plan section 2 says. Leg 4 is the
    derived session in every listing. Leg 5 is vendor_project_problems plus the row-commit session id.
  - The plan's four witnesses (an extra listing entry, a turn-2 argv resuming another id, an extra native interaction,
    a project name from another commit) each go red in P4Witnesses, with seven more beside them. The one gap found is
    finding 2.
- Moved assertions: test_take_checker_dispatch's CHECKER_ENTRIES test moved by plan section 9's P3 line. R4-guard,
  V0-checker and R8WalkRoad's refusal words moved by R-1. r4c9-comment was re-pinned, and harness-guard-message added
  under BOOTSTRAP_SPANS, by R-1. Each carries its ruling in a comment. No witness was weakened and nothing is skipped.
  B18.place and P2's witness table only gained entries.

## NITs

1. evals/gap-study-4/check_take.py:4496: vendor_email_problems reads with Path.read_bytes, which follows a link and
   resolves a ledger name such as "../x". The other vendor readers use _binding._regular_bytes. Use the same reader
   here when finding 1 is fixed.
2. tests/test_vendor_session.py:263: the leg-5 witness drops the whole vendor_take_binding_problems call. A narrower
   witness on the `sid != want` comparison would pin the leg itself.
3. evals/gap-study-4/walk_builders.py:677: like drive.no_inherited_instructions, inherited_instruction_files walks the
   resolved tree's parents, so a tree reached through a link has its logical parents unchecked. It is the same as
   Claude Code's check, so no arm is weaker. Mention it only if the drive's check is ever revisited.
4. evals/gap-study-4/tests/vendor_check_fixtures.py, module docstring: the line ending "...lane vendor-admission round
   12). Every file is SYNTHETIC, written by this module from the documented shapes, and its" runs past the file's line
   width.
