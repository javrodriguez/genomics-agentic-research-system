VERDICT: PASS

# Closure check of lane pf1-l2b-labelling-stats at b1dcf926 (the m16 rework, on bef2a568)

Fresh reviewer, Sun 25 Oct 2026, 08:07-08:12 EDT (times from `date`).
I read: `git diff bef2a568..b1dcf926` (run.py, probes4.py, tests/test_pf1_l2b.py, the COPIED reason) and the battery log.
I ran on the Mac, behind `mac_slot.py light-ok --tests --work gap-study-r4` ("light ok", CPU speed limit 100), with python3.12, read-only:
- one comparison script, `/private/tmp/claude-501/-Users-javrodher-glitch/5da39513-9adc-4587-8d29-3722641cf776/scratchpad/l2b/cmp.py`;
- one `run.walk_problems()` call.

## The coordinator's checks

- **No pinned walk grade's bytes move.** Verified by running both versions.
  - The script loads bef2a568's `run.py` and `probes4.py` from `git show` into the same tree as b1dcf926, then computes `walk_grade_bytes(grade_walk(...))` for every registered walk under both.
    Result: `walks 225 same 225 (graded 151) differ 0`.
  - `run.walk_problems()` at b1dcf926 also returns `225 0`: every committed `grade.json` equals its regrade byte for byte.
  - Every walk road goes through `grade_walk_folder`, which pops `grader_flag`: `grade_walk`, `walk_regrade.py:168`, `native_reader_registration.py:444` and `probes4.vendor_rows`. `regrade` adds no other key, and the key order is unchanged.
- **m16's purpose holds.**
  - Both roads call the grader through the one table, `run.call_grader`. The seven names in `GRADER_CALLS` are bound to `variants.GRADERS`.
  - precondition_refusal's row fields cannot differ between the roads: `variants.row_fields` itself refuses any cell that is not exactly `{half, wording, repeat, pressure}` (`variants.py:772`). So probes4's whole-cell call and regrade's four-field call give the same value or both refuse. This replaces the guard that the removed `dispatch_row` used to give.
  - The seam and sample wrappers are now written twice, and I read them as identical: the original transcript is kept, then `seam`, `GradeError` on a refusal, the call, and `sampled(got, original)`.
  - Probes4's output is unchanged by running it: old and new `render(build())` are identical, 169 rows each, sha256 prefix 187d98d488e038c7 for both.
- **The five shared modules are met by code, not by test edits.**
  `git diff 96c1d959..b1dcf926` is empty for test_vendor_admission, test_walk_grade_seam, test_delegated_grading, test_nested_agent and test_walk_layout.
  All five pass in battery pf1-l2b-battery-b1dcf92-20261025T101906Z, and so do walk_regrade --check, test_probes4, probes4 --check, test_pipeline and test_pf1_l2b.
- **The 12 battery reds come from the base.**
  Each one reads either "review_kit/rounds.json … no fragment in COPIED.d/ claims it" or "prefreeze round 1 is OPEN".
  The checks behind them are copy_manifest, freeze --check, test_freeze_shapes, test_round4 and rounds.py.
  rounds.json was added by base commit 96c1d959, and no COPIED fragment there claims it. The lane never touches `review_kit/`.
- **The D1 and nit-8 rewrites still bind.**
  - D1 spies on `call_grader` from both roads and checks the grader name, `task_id`, and that `row_fields()` equals `variants.row_fields(cell)`. It uses a pressure cell, so the factor field is actually exercised.
  - D1's new walk test asserts that `grade_walk_folder`'s output on w-o46 holds no `grader_flag`.
  - Nit-8 checks through `regrade` that `grader_flag` is the grader's own False while the sample raised `human_sample` to True.
  - `grade_committed` pops the flag and re-adds it as a strict bool.

## Findings

1. **NIT: the test that each road keeps its own seam and sample checks only that the calls are present.**
   It looks for `delegation.seam` and `delegation.sampled` by name in an AST, not at their order or arguments.
   For example, `sampled` called on the presented transcript instead of the original would pass.
   Each wrapper is five lines, so a test comparing the two wrappers' structure, or one behavioural case with a delegated take on each road, would bind them fully.
2. **NIT: stale "dispatch" wording remains.**
   - The original paragraph of the COPIED reason still says "probes4.py …, run_grader through run.dispatch".
   - The import comment at `probes4.py:104` says "the one grading dispatch".
   - `probes4.py:889` says "the walk road through the same dispatch".
   The appended rework sentence in the COPIED reason is accurate.

Stopped at nits.
