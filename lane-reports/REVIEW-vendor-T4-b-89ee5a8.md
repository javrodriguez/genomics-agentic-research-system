VERDICT: CHANGES

# Review: lane vendor-admission, T4 group (b), range f24ee9c6..89ee5a86

Reviewer: a fresh, independent cloud reviewer, briefed by glitch-b5. Read at branch head 2096c63e (the status commit
on top of 89ee5a86), Sat 17 Oct 2026, about 14:15 EDT. Python 3.11 here; TMPDIR outside the clone. No code, test or
fixture was changed.

Read: the ROUND 8 GROUP (b) SUMMARY and its FOR THE REVIEWER points; plan v4 sections 4, 8 and 9; vendor-T4-TABLE.md;
REVIEW-vendor-T4-a-e7496cf.md; REVIEW-vendor-T4-PLAN-36ce125.md (MINOR 1 folded into P1). Code read: the P1 section of
check_take.py, freeze.registration_problems, vendor_record_binding.bound_items, transcript_codex and transcript_gemini
(decode, check_record, the parsers), codex_native.read_rollout, gemini_projection.project and _tool, C's
study_paths_read, _tool_strings and outside_checkout_reads, the new tests and tests/vendor_check_fixtures.py.

## Test counts (all green at 89ee5a86)

test_vendor_check 21, test_freeze_shapes 9, test_take_checker_dispatch 5, test_pin_for_vendor 2,
test_native_reader_registration 7, test_vendor_admission 10, test_vendor_record_binding 12, test_vendor_take_records 4,
test_check_take 15, test_vendor_script 6, test_checker_body 30, test_drive_loop 27, test_drive_commit 31,
test_walk_wiring 20, test_walk_recheck 17, test_vendor_admission_regrade 3, test_pending_walk 23,
test_pending_codex_walk 11, test_vendor_checker_road 5, test_walk_grade_seam 3, test_codex_adapter 55,
test_gemini_adapter 143: 459 tests, OK. Not run here: test_walk_runner, test_round4, the shards, the athena battery.

Gates clean: freeze --check (470 owned paths), walk_regrade --check, copy_manifest --check (469 files),
build_draft --check, lint_language and lint_pooling over evals/gap-study-4/, every line of
checks.d/vendor-admission.txt (12 lines, each exit 0, the two new ones included). No file changed in the range is in
READER_SOURCES or CODEX_SOURCES (read from native_reader_registration).

## Red first, for real (each red commit's tests run in a worktree at that commit)

- 5e413660 (NIT 1 red): test_freeze_shapes failures=2, FS-check's OSError cases and the witness deleting the new
  refusal; test_vendor_check OK. As stated.
- 9b221cd8 (NIT 2 red): test_vendor_check failures=3, one per foreign callable (CheckRefused, Path, an imported
  function); test_freeze_shapes OK. As stated.
- 38671e5d (P1 red): test_vendor_check failures=12, errors=4: the four P1Readers tests error on the missing readers,
  the twelve witnesses fail on their mutation sites being absent. vendor_check_fixtures.py --check passes there. As
  stated ("check_take has no P1 readers").

## Scope checks

- NIT 1 fold (freeze.py:358-359): any OSError out of production_readers is leg iii's named refusal. Correct; the
  registry raises nothing else outside RegistrationRefused on its git road.
- NIT 2 fold (check_take.py:3834-3835): a reader must be a plain function whose module is check_take. Correct; the
  test-data marks are confined to the patched test readers.
- P1 against sections 4 and 9: each digest-bound stream is re-read line by line through the same decode and
  check_record the binding parser uses (CodexParser.items, GeminiParser via decode); the rollout through
  read_rollout then codex_native._json_lines; the snapshot through project and replay. A ViewError or an empty view
  is transcript-unreadable (vendor_take_view); a raw-reader refusal is transcript-unreadable in vendor_reach, never
  clean; an mcp_tool_call, a REFUSED response_item and an undecodable function_call arguments each refuse; the
  partition equals RESPONSE_ITEMS (tested); keys reach study_paths_read through json.dumps, as C's does; values reach
  outside_checkout_reads through C's own _tool_strings.
- The plan's P1 mutants: all seven of section 9's line, plus five more, are in P1_WITNESSES and the witness test is
  green, so each goes red. Extra mutants run here: gemini tool_result skipped, mcp_tool_call admitted, returned
  fields dropped: each RED. Two survive, neither a finding (see NITs 2 and 3).
- F1 and F2: every file labelled SYNTHETIC in its folder's README (P1-fixtures asserts it file by file); --check bound
  by a checks.d line; ids are zero-padded placeholders, model names synthetic, cwd /work/tree; nothing reads as
  recorded from a real vendor take.

## The four named departures

1. vendor_take_view in place of vendor_view: ACCEPTABLE (section 6's vendor_view(design) keeps its name for P5).
2. vendor_reach carries the checkout leg only; home and temp legs with P2's cwd readers: ACCEPTABLE, because nothing
   calls vendor_reach yet and the freeze gate holds arms O and G; P2's review must find both legs.
3. Launch journals, session-store.json and environment.json in F1/F2 deferred to P4 and P5: ACCEPTABLE, P1 reads none.
4. The gemini F3 case uses "evals/gap-study-4" in place of "<checkout>/evals": ACCEPTABLE, it is exactly what C's
   pattern needs, so not weaker.

## Findings

1. MINOR (reproduced). check_take.py:4063, _gemini_snapshot_records reads toolCalls only, so the snapshot's
   tool-response user turns (the functionResponse parts gemini_projection accepts at gemini_projection.py:297-306)
   are never read. These turns are CLI-written tool-result records: the model-facing tool output. The projection
   checks only that their (id, name) pairs answer the calls before them, never that their response bodies equal
   toolCalls[].result. So the snapshot carries two copies of each tool result, they may differ, and P1 reads only
   one. Repro on F2's parts (vendor_check_fixtures.gemini_parts, written by vcf.write): set message rt2's
   content[0].functionResponse.response to {"output": "evals/gap-study-4/prereg-draft.json says ..."}. project
   accepts the file, and vendor_reach returns problems [] with records 6. The same edit on a2's
   toolCalls[0].result raises study-materials-reached (control). The same happens with "<checkout>/README.md" in place
   of read-outside-the-checkout. C reads every tool_result its session file holds
   (check_take.py:209-214, 302-322), so on this road a gemini take is checked less strictly than a Claude Code take,
   with no NOT COMPARABLE row saying so. That breaks the principle. The gap starts in plan section 4's source-2
   wording (toolCalls only), not in a departure by the build. Consequence for the study: a G take could pass
   study-materials-reached or the checkout leg while its CLI-written session file names the study, once T4 is wired
   (P2). Fix: read each tool-response user turn's functionResponse parts as returned records in
   _gemini_snapshot_records, with an F3 case firing on that source alone and a mutant skipping it. Alternatively,
   refuse transcript-unreadable when a turn's parts differ from the toolCalls[].result parts that answer the same
   ids. Either way, red first.

## NITs

1. tests/test_vendor_check.py:383-384: the comment says "`e` for one letter", but the arguments string carries no
   e escape. Plan section 4 asks for both `\/` and `e`. The case still needs decoding to reach evals/, so
   the reading holds, but the \u leg of the plan's case is not exercised.
2. check_take.py:4091: the snapshot's sha256 check against the ledger has no case. A mutant disabling it stays green.
   It is stricter than the plan asks, but untested.
3. check_take.py:4035: the "outside the readers' partition" refusal cannot be reached behind read_rollout's
   RESPONSE_ITEMS check and the partition-equality test, so its mutant survives. Equivalent mutant, so no case is
   needed.
4. Plan section 9 says departures go in w10-walk-runner (check_take.py) and w8b-holdout-digests (freeze.py). Neither
   report changed in group (a) or (b). The COPIED.d reasons carry the record, so name that change of place, or add
   the two lines.
