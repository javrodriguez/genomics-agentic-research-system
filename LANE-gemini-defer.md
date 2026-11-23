# Lane gemini-defer (Gap Study round 4)

Built Thu 22 Oct 2026, from about 09:45 to 11:00 EDT, by an Opus 5.5 medium builder for glitch-f1, on branch `lane/gemini-defer` from `5292df49` (the freeze line with Javier's Gemini reader acceptance).
Why: Javier's decision OD105 on ask gemini-defer ("gemini-defer yes", Thu 22 Oct 2026 09:19:59 EDT): arm G stays registered unchanged at the freeze, its counted run is deferred, it starts only on his later go after the Claude and Codex results, and if he says go it runs exactly as registered, published as a follow-up he chose after seeing those results.
Map: `/Users/javrodher/aegis-builds/GEMINI-DEFER-MAP-20261022.md`.
No push, no mirror, no athena dispatch; no committed record, walk record, holdout file, credential or `.env` was opened or edited.

## Commits

| Commit | Ruling | What |
|---|---|---|
| `ec4cd9f8` | R7 | `check_results.frozen_content_problems` reads the draft's `amendments` dict |
| `6a108ede` | R1, R2 | `build_draft.assemble` emits `deferred_arms.G`; `prereg.py` prints arm G deferred |
| `0d7e20f6` | R5 | `batch.Batch.row_problems` refuses a deferred arm's row unless a committed go record exists |
| `2b540d6a` | R3 | `completeness.py` reads G's unmeasured half-cells as "deferred (Javier, 22 Oct 2026)" |
| `7e79861e` | R4 | `labelling/sample.py`: the original draw withholds G at its full-design share; a follow-up draws G only after a go |
| `81c84b4d` | (lint) | three wordings so every added line passes `lint_language.py` |
| `9118a6eb` | | this file |
| `987c8030` | OD107 stage | `costs.CAPS` openai 180, google 220, total 400; `deferred_arms.G.registered_cap` |

## The rulings, quoted, and what changed per file

**R1.** "The mark: a new top-level key `deferred_arms` in build_draft.assemble beside `optional_arms` ... Every G row, models.G, arms, counts, stats_design_inputs and every analysis text stay byte-identical. Not optional_arms, not amendments. Regenerate prereg-draft.json with build_draft.py (never hand-edit it); `build_draft.py --check` must pass. Pin the key in tests/test_build_draft.py the way R13.amendment pins amendments."

- `evals/gap-study-4/build_draft.py`: a `DEFERRED_ARMS` constant and the `deferred_arms` key placed right after `optional_arms`, holding for G: status "deferred", by "Javier", his words and time, records {decision OD105, ask gemini-defer}, starts_only_on, if_go, design_changed false, the map's section 6 caveat sentence verbatim, `blind_sample` (R4's split), `analysis` (R6), and rows 360 and models computed from the rows and `MODELS["G"]`.
- Byte-identity check: `build()` on 5292df49 and on the lane, each dumped sorted with `deferred_arms` removed: `diff` printed nothing.
- `evals/gap-study-4/tests/test_build_draft.py`: clause `R13.deferred` in `core_problems` (the entry typed independently of the builder, placed after `optional_arms`, G not in `optional_arms`, `amendments` still the two letters, rows equal to `counts.by_arm.G` and 360, models equal to `models.G`) and four mutants (`deferred-by`, `deferred-design`, `deferred-gone`, `deferred-rows`).
- **Deviation, not built: prereg-draft.json is not regenerated, and `build_draft.py --check` does not pass.** It is already red on 5292df49 itself: `build()` now reads the 225 committed walks into `checked_against` (`sessions_read` 225 against the committed draft's 0 and PENDING), and `test_build_draft` clause R9.sessions is red on 5292df49 for the same reason (run below). Regenerating here would write that `checked_against` with the reader that predates vendor-settle (the hollow vendor read glitch-f1's 22 Oct 02:02 ruling names) and against that ruling's "prereg-draft.json regenerated once on the freeze line after d8-furniture, freeze-gates-fix and vendor-settle merge, by build_draft only". So the key lives in build_draft.py and its test, and enters the draft at that single regeneration. Every R2 to R5 behaviour reads the key from the design in force, so it takes effect then; until then the committed draft defers nothing and every existing test runs unchanged.

**R2.** "prereg.py --status and not_run_reason print arm G as "deferred (Javier, 22 Oct 2026)", never as running and never absent."

- `evals/gap-study-4/prereg.py`: `deferred_arms`, `deferral_label` (who and the date read from the entry's words), `deferred_models`; `--status` adds "; deferred: G" to the arms line and "; deferred (Javier, 22 Oct 2026)" to arm G's line (its 2 models and 360 rows still printed); `running_models` leaves a deferred arm's models out and `not_run_reason` returns the label; `models()` still lists all eight.
- The go record reader for R4 and R5 also lives here (the one door to the design): `GO_KEYS` (kind, arm, by, decision, ask, at), `go_record_problems` (kind "deferred arm go", by "Javier", decision and ask non-empty, `at` an ISO time with offset), `committed_go_records` (`git show HEAD:./deferred-arm-go.json`, never the working copy; none when not committed or no git), `deferred_arm_go`.
- `evals/gap-study-4/tests/test_prereg_status.py`: class `DeferredArm` (status lines, reasons, a deferral without who or date refused, the closed go record, a go read only once committed) on the committed draft plus build_draft's own key; S1 and S4 now also hold once the draft carries the key.

**R3.** "completeness.py: G's half-cells read "deferred (Javier, 22 Oct 2026)" from the frozen key instead of "no takes"."

- `evals/gap-study-4/completeness.py`: a deferred arm's half-cell with no graded take and no committed mechanical state reads the label, reason "arm G's counted run is deferred in the frozen deferred_arms"; committed mechanical states keep precedence.
- `evals/gap-study-4/tests/test_pipeline.py`: `Reporting.test_a_deferred_arms_half_cells_read_deferred`.

**R4.** "labelling/sample.py: the original report's blind draw covers the five run models (arm A's three, arm O's two) with the registered per-cell share; a follow-up draws the two G cells under the same design. sample.py excludes a deferred arm's models unless a go record exists (R5's record)."

- `evals/gap-study-4/labelling/sample.py`: `deferred_cells` reads the frozen key; `draw(frame, design, deferred, part)` computes the quota over every cell of the full design (the frame's and the withheld ones, the same seeded remainder), so each run cell keeps its full seven-model share; part "original" draws the run cells, part "followup" only the withheld cells. `derive` refuses the follow-up until every deferred arm has a committed go record; `--check` checks `sample-followup.json` beside `sample.json` once a go exists; `--write-followup` writes it. With nothing deferred the draw and its bytes are unchanged and no go record is read.
- Reading taken for "registered per-cell share": the share of about_n each cell has in the full design (80 over seven cells), not 80 over five; the `blind_sample` text in the key says so.
- `evals/gap-study-4/tests/test_labelling.py`: check `r4_deferred` in SAMPLE_CHECKS; two witness anchors follow the edited lines (the same clause removed); EQUIVALENT key `return-none L268` moves to L329; `n1_names` pins `SAMPLE_FOLLOWUP`; `_patched` points `SAMPLE_FOLLOWUP` at the temporary tree (before that, one mutant wrote the real `labelling/sample-followup.json`; it was removed and never committed).

**R5.** "batch.Batch.row_problems refuses, by name, a row whose arm is in the frozen deferred_arms unless a committed go record exists ... Not in takes.commit_registration."

- `evals/gap-study-4/batch.py`: `_read_deferral` at construction (a pure read of the design in force); `deferral_problem` before the pins, the money gate and the cells, by arm or by a registered model of the arm: "row N: arm G is deferred (Javier, 22 Oct 2026) in the frozen deferred_arms, and no committed 'deferred arm go' record for arm G exists (deferred-arm-go.json, Javier's go): never driven while deferred". The go records are read only when such a row is handed, from `repo.deferred_go_records()` when the repo offers one, else `prereg.committed_go_records`. A first version read git at every construction; the process guards in `test_walk_wiring` refused that under the simulated key, so the read is lazy. `takes.py` is untouched.
- `evals/gap-study-4/tests/test_batch.py`: class `TestDeferredArm` (four go-record variants refused, a model-only row refused, a valid go runs, arm A runs, nothing read when nothing is deferred, the repo's own records read once and only for a deferred row).

**R6.** "Multiplicity, pre-registered in deferred_arms.G.analysis ... stats.py is not changed." Built as the `analysis` text; `stats.py` untouched.

**R7.** "check_results.frozen_content_problems treats the dict `amendments` as a list and raises KeyError slice(None, 2, None) on the draft's own shape. Fix it red first ... keep every existing refusal."

- `evals/gap-study-4/check_results.py`: a dict keeps every key present at the freeze with its value, new keys after the freeze are the later amendments (their `files` chain moved pins as before); a list keeps its head rule; a change of shape is refused as an edit.
- `evals/gap-study-4/tests/test_pipeline.py`: `FreezeCoverage.test_frozen_content_reads_the_drafts_amendment_dict` on the real `prereg-draft.json` (no change on itself; an edited, removed or list-shaped amendment refused; a moved pin refused bare, accepted when a new dict entry chains it, refused when the chain ends wrong; the list shape unchanged).
- `check_results.py --ledger` end to end was not run: it needs a frozen `prereg.json`, which does not exist on this line.

**The OD107 stage** (glitch-f1, relayed mid-lane: Javier's "gcap-220 yes", decision OD107, ask gcap-220, his turn Thu 22 Oct 2026 14:43:19Z): "costs.CAPS becomes {"openai": 180, "google": 220} with TOTAL_CAP 400 unchanged ... with a test pinning the new caps and the total, the draft regenerated so its caps mirror costs.py, and deferred_arms.G noting the registered Google cap (220 dollars, OD107) so a later go runs exactly as registered. Nothing else in costs.py changes."

- `evals/gap-study-4/costs.py`: the one `CAPS` line (and its comment); nothing else.
- `evals/gap-study-4/build_draft.py`: `deferred_arms.G.registered_cap` {vendor google, usd 220, decision OD107, ask gcap-220, his words, why}; the `caps` key already derives from `costs.CAPS` (`build()` now gives openai 180, google 220, total 400).
- Tests: `test_pipeline` CostAccounting pins the caps and total (spends moved so each vendor stays one step under its cap and the projection passes the total by one, as before); `test_build_draft` R16.caps pins 180, 220, 400 and R13.deferred binds `registered_cap.usd` to `costs.CAPS["google"]`; `test_spend_wiring`'s synthetic "caps trimmed" figures move from openai 200 to 150 (a trim above the cap is refused by design).
- Red: `{'openai': Decimal('260'), 'google': Decimal('140')} != {'openai': Decimal('180'), 'google': Decimal('220')}`; Assembly `['R13.deferred']`; test_commitments `['R9.sessions', 'R16.caps']`. Green: CostAccounting 11, test_spend_wiring 25, test_batch 122, test_prereg_status 9, test_claude_code_adapter 28 OK; Assembly 5 OK; test_commitments red on R9.sessions only.
- Not done: the draft regeneration (the same reason as R1). Left as it stands: the requirements quote `caps` in build_draft's QUOTES (req line 57, "The cap is $400 (OpenAI $260, Google $140).", with its structured 260 and 140), because it is a quoted source sentence; whether it needs an amendment note beside it is glitch-f1's call, with the D8 addendum.

**R8.** freeze.py is not changed. Untouched, as are `stats.py`, `takes.py`, D8 and the launcher.

## Red, then green

Red runs are the new tests against 5292df49's code (a detached scratch worktree, `/private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/gd-base-5292`), except R7 and R3, red on the lane before the fix.

| Ruling | Red | Green |
|---|---|---|
| R7 | `KeyError: slice(None, 2, None)` at check_results.py line 300; 1 run, 1 error | FreezeCoverage 11 run OK |
| R1 | test_build_draft.Assembly: 1 failure (`['R13.deferred']`), 3 errors (mutants with no key) | Assembly 5 run OK |
| R2 | test_prereg_status: 2 failures, 8 errors (no `deferred_arms`; the status line missing) | 9 run OK |
| R5 | test_batch.TestDeferredArm: 4 run, 7 failures ("BatchConfigError not raised") | test_batch 122 run OK |
| R3 | `AssertionError: 'no takes' != 'deferred (Javier, 22 Oct 2026)'` | test_pipeline Reporting and FreezeCoverage 22 run OK |
| R4 | `R4: raised TypeError: draw() got an unexpected keyword argument 'deferred'` | test_labelling 110 run OK; witnesses 64 of 64 red |

Generated mutants over sample.py's changed lines (a scratch driver over the module's own `generated_mutants` and `run_mutant`): 219 mutants, 0 survivors, after four equivalent sites were simplified away and the survivors' clauses were given checks.
The full 16-shard sweep is athena's.

Module runs on the Mac (light gate read before each batch; `run_named.py` is a scratch unittest runner by test name):

- test_batch 122, test_batch_rolling 36, test_spend_wiring 25, test_nightly_stop 13, test_night_ruling_history 4, test_walk_wiring 20, test_prereg_status 9, test_prereg_order 10, test_cp6_wiring 5, test_ci_job 23, test_ownership 44, test_labelling 110, test_labels4 9: all OK.
- With `prereg.load()` carrying build_draft's `deferred_arms` (the regenerated draft simulated): test_batch 122, test_spend_wiring 25, test_nightly_stop 13, test_night_ruling_history 4, test_prereg_status 9, test_walk_wiring 20: all OK.
- test_freeze_shapes: 9 run, 1 failure, `test_fs_check_the_committed_draft_names_every_leg` ("'arm O (codex): leg iii:' not found"): the same failure on 5292df49 (run there), since both readers are accepted on this line; not this lane's.
- test_vendor_checker_road: 2 failures, 3 errors (the process guard refuses `git rev-parse --show-toplevel`): the same on 5292df49; not this lane's.
- test_build_draft `Description.test_commitments`: red on R9.sessions only, as on 5292df49 (see R1's deviation).
- test_pipeline and test_build_draft, whole: NOT run on the Mac. test_build_draft alone ran past 14 minutes in a light attempt (stopped by pid); two `mac_slot.py run --kind heavy` tries (the second with --wait 1500) never got a slot: "busy: first slot: CPU speed limit 50 is below 80", exit 3. Their touched classes ran (above); the whole modules, the labelling 16-shard sweep and the witness runs go to athena's battery.

## For glitch-f1

1. The draft regeneration is the open step for R1: at the ruled single regeneration after vendor-settle merges, `deferred_arms` enters the draft from build_draft.py; then `build_draft.py --check` and R9.sessions are the regeneration's to turn green.
2. When it lands, `prereg.py --status` prints G deferred, `running_models` drops to five, completeness and the blind draw withhold G, and batch refuses G rows; the counted-run launcher's repo can offer `deferred_go_records()` (read at HEAD, as `history()` is), else batch reads `prereg.committed_go_records`.
3. A go record is `evals/gap-study-4/deferred-arm-go.json`, a JSON list of `{kind: "deferred arm go", arm: "G", by: "Javier", decision, ask, at}`, committed after his go.
4. Not built here, as briefed: the launcher's A+O queue and the ledger's no-G rule, and the D8 addendum.

## Review fold (REVIEW-gemini-defer-dd7126a.md, PASS WITH FIXES)

Folded Thu 22 Oct 2026, about 12:50 to 13:40 EDT, by an Opus 5.5 medium builder for glitch-f1, on top of `dd7126a0`.
glitch-f1's rulings, under Javier's standing delegation: MAJOR-1 adopted (it reverses the earlier "D8 addendum only", because D8 sits outside the frozen file), MINOR-1 adopted, the four NITs adopted.
Red runs: the new tests against `dd7126a0`'s code, in a scratch export (focused classes) and a detached scratch worktree (the in-memory `describe()`, which reads git).

| Commit | Finding | What |
|---|---|---|
| `9a3169ad` | MAJOR-1 | `build_draft.CAPS_DECISION` and `d["caps_decision"]` beside `caps` |
| `3aac3fc3` | MINOR-1 | `check_results.RUNTIME_PATHS` holds `deferred-arm-go.json` |
| `2bf97548` | NIT-1 to NIT-4 | the staged go record test, completeness after a go, the status line, one deferral call per row |

**MAJOR-1.** `caps_decision` = decision OD107, ask gcap-220, by Javier, his words ("gcap-220 yes", Thu 22 Oct 2026 10:43:19 EDT), at 2026-10-22T14:43:19+00:00, vendors openai 180 and google 220, total 400, and `supersedes` {commitment `commitments.caps`, source CP5-requirements line 57, vendors openai 260 and google 140, total 400, why}.
The quote `commitments.caps` stays byte for byte.
`tests/test_build_draft.py` R16.caps pins the typed dict, binds its vendors and total to `caps` and its superseded figures to `QUOTES["caps"]` and the commitment's source; description mutants `caps-decision` (openai 260) and `caps-superseded` (google 220).
- Red, `description_problems(describe())` on `dd7126a0`: `['R9.sessions', 'R16.caps']`, no `caps_decision`.
- Green on the lane: `['R9.sessions']` only (red before this lane, the ruled regeneration's), the three caps mutants red, `core_problems(assemble()) == []`.
- prereg-draft.json is NOT regenerated here: the key enters it at the single regeneration in the freeze merge.

**MINOR-1.** `RuntimeTiming.test_a_go_record_before_or_with_the_freeze_is_refused`: a go record in the freeze commit gives exactly one "run output committed before or with the freeze"; one committed before the freeze is refused; one after it passes.
Red: `'deferred-arm-go.json' not found in (...)`. Green: RuntimeTiming 4 OK.
Not built: the review's optional future-`at` refusal in `go_record_problems` (not in the ruling).

**NIT-1.** `DeferredArm.test_go_record_is_read_committed` asserts no go while the record is only staged; it passes on correct code by design, and the review's M07 (read the index) now dies.
**NIT-2.** `completeness.summarize(..., go_records=None)`: after a valid committed go, a G half-cell with no take reads "no takes" with reason "no committed graded take"; no record, arm O's or one not by Javier keeps "deferred (Javier, 22 Oct 2026)". The records are read (`prereg.committed_go_records`) only when the design defers an arm. Red: TypeError (no `go_records`).
**NIT-3.** `prereg.status_lines` appends "; deferred: ..." only when a planned arm is deferred. Red: `'... optional: C; deferred: '`.
**NIT-4.** `row_problems` binds `deferral := self.deferral_problem(r)`. Red: calls `[1, 1, 2, 2, 3]` against `[1, 2, 3]`.

Green on the Mac (light gate read before each batch): test_batch.TestDeferredArm 5, test_prereg_status.DeferredArm 6 and StatusIsRound4 4, test_pipeline RuntimeTiming 4, Reporting 11, CostAccounting 11, FreezeCoverage 11: all OK.
Added lines: `lint_language.scan_text` finds nothing.
Whole modules on the Mac, at `2bf97548` in a scratch worktree: test_batch 123 OK, test_prereg_status 10 OK.
Mutants: the review's driver extended in a scratch copy (`/private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/fold/mutants-fold.py`, output `mutants-fold.out` beside it), run on a detached scratch worktree at `2bf97548`: the review's 30 plus M31 to M37 (caps_decision openai 260, caps_decision not emitted, supersedes google 220, the go record out of RUNTIME_PATHS, completeness ignoring a go, the empty "deferred:" back, deferral_problem asked twice): 37 killed, 0 survivors (M07 now killed by DeferredArm). The `DESC` runner ignores R9.sessions, which was red before this lane.
Left to athena's battery, as before: whole test_build_draft and test_pipeline, the labelling 16-shard sweep and the witnesses.

**Final-merge stage A finding (Thu 22 Oct 2026, 16:42 EDT).** R16.caps read `d["commitments"]["caps"]["source"]` with no guard, so mutant `quote-caps` raised `KeyError` in `test_each_clause_red`; it now reads every nested field through `reached()` and a damaged caps gives R16.caps. Fixed in the one commit that adds this line, on top of `fc8e2ac0`; no expectation, mutant or clause changed.
