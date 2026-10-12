status: stopped

# Lane w7a-draft-text: Gap Study round 4 wave 7 piece P1 (draft text, prereg status)

Written Sun 11 Oct 2026, 23:47 EDT (`date`), by the lane's sole writer (Claude Opus 5.5), assigned by glitch-1b under Javier's standing delegation.
Branch `gap4/w7a-draft-text`, base `d051bece` (the wave 6 merge head).
Code commit `7eef1417`.
Nothing was pushed, merged or dispatched, and no model, network, Docker, credential or holdout was used.

RESUME HERE: hand-back at 7eef1417; athena owns the exact-head run_checks (test_round4, every checks.d line including test_build_draft's six witness groups and `checks.d/w7a-draft-text.txt`).

## What closed

- W6D-R1-2: `order_carry` now reads "prereg.py --order <review sha> prints freeze.planned_order: one permutation of the design's whole planned rows, seeded by the full 40-character sha of the pre-freeze review commit; it refuses until every agent version is pinned."
  The R3.order substring is kept; the new clause R3.carry binds the exact sentence and ties it to `prereg.ORDER_FUNCTION`, `prereg.SEED_SHAPE` and `take_order_function`.
- OPEN-4: `box_residuals[2]` pre-registers S7-D2 (C): mode bits are not graded, with the closed check `tests/test_endstate.py ModeBits.test_no_task_move_is_chmod_only`.
  R8.residuals binds the entry; R8.mode-residual checks the named test exists and asserts `mode_problems() == []`, and that box/sidecar.py still states the residual.
- W6D-R1-1: `prereg.py --status` prints `arms     : 3 planned (A, O, G); optional: C`, one line per arm (harness, models, rows) and `rows     : 1260 planned rows (n = 10 tries per half), 126 half-cells`, counted from the rows.
  `models()` returns the seven models of the arm-keyed table (it returned the arm letters); round 3's `cells()` count is removed (nothing else read it).
- W6-claims-1: `test_scaffold.copied_modules()` now reads every fragment through `copy_manifest.load_fragments` and keeps .py entries copied from `study.PRIOR_REL`; Claims derives its expected list from every COPIED.d fragment by that rule (floor >30 kept; 39 modules now, 31 before).
  Finding: the old hand list never held w5b's eight pipeline copies (freeze.py, takes.py, check_results.py, run.py, result.py, completeness.py, costs.py, freeze_rehearsal.py), so TheImports was not probing them; it now does and passes (3 tests OK).
- W6C-R1-2: `folded()` applies NFKC, casefolds, and reads every dash (Pd) and invisible format character (Cf) as a space; `floors_missing` also refuses any floor text holding a Cf character (`invisible()`), which covers a zero-width character inside a word.

## Ownership (ruling W7A-gap4-1)

- New fragment `COPIED.d/w7a-draft-text.json`: build_draft.py (transferred from w5c-draft-ci), prereg.py (from w1a-cp1-scaffold), tests/test_prereg_status.py, checks.d/w7a-draft-text.txt, the fragment itself.
- Transfers named in the old owners' self-entries (w5c, w1a).
- Edits without transfer, recorded in the owners' entries: tests/test_build_draft.py and prereg-draft.json (w5c), tests/test_scaffold.py (w1a; departure: a w1a file edited, as w6e/w6h/w6j did for the same function).

## Evidence (Mac, `mac_slot.py light-ok` and `timeout -s INT 120` in each command, Python 3.13.2, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`)

- Red first, by assertion only: test_prereg_status 3 run, 5 failures, 0 errors, exit 1. test_build_draft (Assembly, Description, the two floor tests, Claims) 13 run, 14 failures, 0 errors, exit 1 (R3.carry, R8.residuals, R8.mode-residual, R3.floors:dash/invisible/width, R13.claims).
- Green: test_prereg_status 3 OK; test_prereg_order 10 OK; test_wave6_bindings 2 OK; test_scaffold TheImports 3 OK; whole test_build_draft 43 run, 0 failures, exit 0 (after the commit; before it, only Readiness.test_committed_writer failed, as it compares against HEAD).
- Draft regenerated through `build_draft.py` (writer); `build_draft.py --check` exit 0, `freeze.py --check` exit 0, `copy_manifest.py --check` exit 0 (35 identical, 18 edited, 205 new, 38 fragments), `prereg.py --status` exit 0.
- Witnesses (rule B, each RED by its bound method's AssertionError with its clause, 0 errors): test_prereg_status `--witnesses` 4/4 (models-label, counts-field, round3-count, arm-keys).
  test_build_draft's new mutants run through the module's own `run_witnesses` restricted to those names: order-carry-stale, mode-residual, folded-case, folded-dash, floors-invisible, folded-width, claims-dropped-fragment, plus claims-old-only, 8/8 RED.
  Collateral listed, not credited: Readiness.test_committed_writer (order-carry-stale, mode-residual), Description.test_mode_residual_is_bound (mode-residual), Readiness.test_floor_fallback_keeps_closed (folded-case).
  The registry is now 249; athena's six groups are the run of record.
- lint_language and lint_pooling exit 1 with 25 and 8 findings, none in a file this lane touched (same counts as w6d recorded).
- Not run on the Mac: whole test_scaffold (TheManifest took 579 s in w6d), test_pipeline, run_checks, the six full witness groups.

## Open questions for glitch-1b

- Q-w7a-1: cp6-readiness section 2 also names S7-D4's dwell line for the draft; this brief scoped OPEN-4 to the mode-bits line only, so the dwell line is not added.
- Q-w7a-2: prereg-draft.json stays claimed by w5c-draft-ci while its writer moved to w7a; say if it should follow the writer.
- Q-w7a-3: `prereg.running_models()` and `not_run_reason()` read a `model_status` key the round 4 draft does not have; left as is.

## Appendix: fold W7A-close-1 (review round 1 PASSED, no MAJOR)

Written Mon 12 Oct 2026, 00:10 EDT (`date`), by the same writer, on glitch-1b's ruling W7A-close-1 (table in the Brain at `plans/gap-study-round-4/w7a-review-r1-2026-10-12.md`).
Base `31c918db`; fold code commit `632ae20e`.
This appendix controls where it differs from the body above; the body's three open questions are answered by the ruling (Q-w7a-1 folded, Q-w7a-2 ruled and folded, Q-w7a-3 folded as W7A-R1-2).
The test_scaffold edit is ratified as departure w7a-1.

Folded:
- W7A-R1-1: `folded()` also reads connectors (Pc) and U+2212 as spaces (`SPACE_LIKE`, `SPACE_LIKE_CHARS`); floors refuse every default-ignorable code point (`ignorable()`: Cf, plus `IGNORABLE_RANGES` covering U+034F, U+115F-1160, U+17B4-17B5, U+180B-180F, U+2065, U+3164, U+FE00-FE0F, U+FFA0, U+FFF0-FFF8, U+E0000-E0FFF). New clauses R3.floors:connector (3 spellings) and R3.floors:ignorable (11 spellings, one per class); witnesses folded-connector and floors-format-only.
- W7A-R1-2: `models()` lists the planned arms' models and then the optional arms' (8 on the draft); `running_models()` and `not_run_reason()` come from the planned rows (fable and any row-less model not running, with "no planned rows in ..."); the dead NOT RUN loop in --status is removed. Clause S4.running, witness runs-default.
- W7A-R1-3: `Assembly.test_order_carry_is_true` (R3.carry): test_prereg_order's BOUND holds O1.planned_order, O3.cli, O5.pending, O4.seed, O6.length and O6.hex, each to a real method; SEED_SHAPE takes no extra flag; `prereg.py --order <fake sha>` on the committed draft exits 1 with "refuses the design in force".
- W7A-R1-4: order_carry now reads "prereg.py --order <review sha> names freeze.planned_order and shows the head of its permutation of the design's whole planned rows, seeded by the full 40-character sha of the pre-freeze review commit; it refuses until every agent version is pinned." Witness order-carry-prints (the first w7a sentence).
- Q-w7a-1: the draft's new `final_stop` entry pre-registers S7-D4 (A) (strictly after post-N's snapshot, else harness-error via the existing watcher rows; the tail lasts the drive step's dwell, no minimum checked), bound by R8.final-stop to FinalStop.test_the_final_stop_is_strictly_after_post_n and endstate.py's docstring; witness final-stop.
- Q-w7a-2: prereg-draft.json moved from w5c-draft-ci to w7a-draft-text; the transfer is named in w5c's self-entry; Readiness.test_committed_writer now reads w7a's fragment.
- W7A-R1-5: copied_modules() and Claims keep every non-new .py copy: 44 modules, TheImports 3 OK.
- W7A-R1-6: pending() gives floors refused for an invisible character the reason `floor_invisible`; --status prints "0 rows; optional (D2 B)".
- Draft regenerated through the writer only (order_carry and final_stop changed; 79 pending inputs, unchanged).

Evidence (Mac, light-ok and `timeout -s INT 120` in each command, Python 3.13.2):
- Red first, assertion only: test_prereg_status 4 run, 5 failures, 0 errors, exit 1; test_build_draft 45 run, 25 failures, 0 errors, exit 1 (a first run had 5 AttributeErrors from the not-yet-existing `ignorable`; the test was changed to fail by assertion and re-run red before any code).
- Green after commit: test_build_draft 45 run, 0 failures, exit 0; test_prereg_status 4 OK; test_prereg_order 10 OK; test_wave6_bindings OK; test_scaffold TheImports OK; build_draft --check, freeze --check, copy_manifest --check (35 identical, 18 edited, 205 new) exit 0; lints unchanged (no finding in touched files).
- Witnesses (rule B, 0 errors): test_prereg_status --witnesses 5/5 RED. test_build_draft through its own run_witnesses on the named mutants: folded-connector, floors-format-only, order-carry-prints, final-stop, folded-dash, floors-invisible, folded-width, claims-dropped-fragment 8/8 RED; collateral listed, not credited (test_order_carry_is_true, test_final_stop_is_bound, test_committed_writer). Registry 253; athena's six groups are the run of record.
- Not run on the Mac: whole test_scaffold, test_pipeline, run_checks, the six full witness groups.

RESUME HERE: hand-back at 632ae20e
