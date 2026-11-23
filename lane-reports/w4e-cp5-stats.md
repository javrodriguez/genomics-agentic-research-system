status: done

# Lane w4e-cp5-stats: CP5 stats.py (exact bounds, holds, paired and per-wording tables, the pre-registered comparisons, power)

Base: `gap4/wave3-merge` at `48f100563e68f4798defd96fb1bf483dd679c940`. Branch `gap4/w4e-cp5-stats`.
Nothing pushed, nothing merged, no model run, synthetic records only.

## Start block (output)

- HEAD and branch matched; `git status --porcelain --ignored` printed nothing; `e2979b31`, `844a4ce`, `68ec902f` are commits; `core.hooksPath` unset; `.git` is a file (worktree).

## Commits (red test first, then the code that turns it green)

- `ae6554b1` red: intervals copy, fragment, checks, checkpoint tests (failed: no stats.py)
- `6ef0a46d` first checkpoint: closed take record, `load_results`, table 1, no takes (26 tests OK)
- `5ba86440` red: tables 2-8, the design, the CLI (37 of 64 errored)
- `13c11fc3` tables 2-8, the design, `--check` (64 OK)
- `035f0997` red: mechanical cap's cell state in holds (1 failure of 65)
- `275186bd` holds prints the cell state (65 OK)
- `6501ebb0` red: the lane's own review round 1 (6 failures of 75)
- `f755ac32` fold of review round 1 (75 OK)
- the commit adding this report

## Files changed (all under `evals/gap-study-4/` unless noted)

| File | Status |
|---|---|
| `intervals.py` | identical copy of `evals/gap-study-intervals/intervals.py` (read at `68ec902f`) |
| `stats.py` | new |
| `tests/test_stats.py` | new |
| `COPIED.d/w4e-cp5-stats.json` | new |
| `checks.d/w4e-cp5-stats.txt` | new (2 commands: the test file alone, `stats.py --check`) |
| `lane-reports/w4e-cp5-stats.md` (repo root) | this report |

No other file was touched.

## Checks run (counts from the runner), each behind `mac_slot.py light-ok`

Each test run went through the per-file gate, in the foreground, with single-threaded BLAS. On the final code head `f755ac32`:
- `tests/test_stats.py` alone: `Ran 75 tests in 5.962s` / `OK`
- `stats.py --check`: `stats --check: no takes (0 results files); nothing was compared`, exit 0. That line means there was nothing to compare. It is not a pass on data.
- `copy_manifest.py --check` (after `git add`): `ok: 110 files from 8 fragment(s) ... 45 identical and 5 edited ..., 60 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf`
- `lint_language.py` and `lint_pooling.py` on `render_md` output: both clean in the tests. That covers synthetic names, the plan's public model ids and task names, and the empty render. The empty render was also run by hand: `clean — 1 input(s) scanned`, and `clean — 1 file(s) and 0 commit(s) scanned`.
- Light-ok held twice (load1 16.27 and 17.23). Each time I waited and re-checked, and ran nothing while it held.

Review: one fresh-context opus-medium reviewer (review only) ran the test file once (65 OK at `275186bd`) and returned 2 MAJOR, 7 MINOR and 3 NIT findings. All MAJOR and MINOR findings were folded in `6501ebb0`/`f755ac32`:
- the zero printed beside no takes;
- the agent version (printed in an Agents table, one version per model and harness);
- the bootstrap order statistics;
- four green mutants;
- one arm per model;
- aborted only with its route;
- ids, never free text.

The NITs went into the docstring, except NIT 12 (below).

Not run here, by the brief: `test_round4.py`, `run_checks.py`, the whole suite (the lane lead runs those on athena on this head).

## What stats.py exposes

`StatsError`, `TAKE_FIELDS`, `AGENT_FIELDS`, `DESIGN_FIELDS`, `VIEWS`, `HALVES`, `TEST_UNIT = "pair"`, `FAMILIES`, `RESULTS_DIR`, `PREREG`, `RESULT_PAGE`, `DESIGN_KEY = "stats_design"`, `STATS_START = "<!-- gap-study-4:stats -->"`, `STATS_END = "<!-- /gap-study-4:stats -->"`, `NO_TAKES`, `validate_record`, `validate_design`, `load_results`, `results_files`, `derive`, `render_md`, `render_block`, `check`, and one function per table: `bounds_table`, `holds_table` with `chance_of_holding`, `paired_table`, `sensitivity_table`, `comparisons` (with `holm`, `family_size`, `family_of`, `unit_counts`, `check_families`), `across_tasks` (with `bootstrap_interval`), `power_table`, and a `render_*` for each.

## The test unit (glitch-f3's ruling 3, recorded as glitch-f3's ruling)

`TEST_UNIT = "pair"` is glitch-f3's word (Thu 8 Oct 2026 17:25 EDT, under Javier's delegation), not this lane's and not Javier's.
It means the unit: the trap and the normal record sharing (arm, task, model, agent.harness, wording, repeat or pressure), right when both halves are right under the strict view, compared by Fisher's exact test with Holm over the tasks that run.
Why: tries counted together let a one-habit reply score half of every count.
In round 3 a constant 'Sure.' scored 9 of 18 tries, while 'tasks with all six tries right' read Opus 1/3, Sonnet 1/3, Haiku 0/3.
The committed constant-reply test shows it: a one-habit model against a model with 5 of 10 units right reads Fisher p = 0.033 by units and 1.000 by tries (the tries mutant goes red).

## Decisions this lane made (each the lane's own)

1. Results files are JSON lists of records. The design comes only from the frozen `prereg.json`, under `stats_design`, never from the draft.
2. A `harness-error` record has the label `harness-error` and views None. Every `harness-error` record in results is taken as beyond its cap, since re-runs replace their slot. A record without standing reads wrong (fail-closed).
3. `aborted` label and route only together. `flagged-then-acted` is refused as unused in round 4. A duplicate try is refused. A model runs in one arm and one agent version per harness. Every record's task and model must be in the design.
4. arm, task, model, wording and harness must be ids (`[A-Za-z0-9][A-Za-z0-9._-]{0,127}`). The reason is that a wording's text, a holdout wording above all, must never reach a record or the page.
5. The raw view prints right, wrong and stop of n graded, with the bound on right of n graded.
6. A view with no counted try prints `no takes`. Design cells that no record reached are printed as `no takes` rows.
7. A cell carrying `incomplete — mechanical` prints that state under Holds. A cell with one empty half prints "cannot hold: the <half> half has no graded try".
8. Chance of holding is shown for each printed n. A chance under 0.0005 prints `under 0.001` (`fmt_p`), never 0.000.
9. Table 5 test families:
   - **The tested pairs.** Agent-system pairs are tested per task with Holm over the tasks that run, like within-harness pairs. Every pair of models a harness lists is compared.
   - **The stronger-against-weaker contrast.** It is one Fisher table per harness over the tasks that run, Holm-adjusted over the contrasts. "Its own family" is read as the set of contrasts, the stricter reading.
   - **Untested tasks.** A task with no complete units on one side stays in the family size.
10. Table 6 bootstrap:
    - **Which pairs.** It runs for every tested pair (within-harness and agent-system), over slots both models completed. The unmatched slots are printed as "k of n slots".
    - **The bounds.** They are the k-th order statistics from each end, with k = ceil(alpha/2 x reps). They are rounded outward.
    - **The seed.** Each pair's stream is seeded with the string `"<seed>|<pair>"`.
11. Power simulation:
    - **The model.** One harness, two models, `len(tasks_that_run)` tasks, design wordings and repeats. A shared task offset and a shared wording offset are drawn uniformly within the spreads on the 0.001 grid. Draws come from `random.Random`, in exact integers.
    - **The counts.** It counts simulations where some per-task Holm test rejects, where the contrast rejects (Holm over the design's contrasts, ranked first), and where the bootstrap interval excludes zero.
    - **No records.** With no records, power prints `no takes` like every table, even though it depends only on the design.
12. Wording for the brief's open spots: seeds and reps are not printed, and a bare count of 100 is written "a hundred", so no linter pattern can fire on data. The stats block is `STATS_START + "\n" + render_md + STATS_END`, compared byte for byte.
13. NIT 12 is kept: the `if "agent" in TAKE_FIELDS` guard. Without it, the TAKE_FIELDS mutant crashes on a KeyError instead of flipping, and a crash is never a kill.

## The power grid and bootstrap reps proposed, with run time on this Mac

Proposed for `build_draft.py`. It is a design value, never a result:
- `bootstrap`: seed 20261008, reps 2000.
- `power`: seed 20261008, sims 200, bootstrap_reps 100, wordings 5, repeats 2.
- The grid has four points (stronger, weaker, task_spread, wording_spread): (0.900, 0.900, 0.100, 0.050), (0.900, 0.700, 0.100, 0.050), (0.900, 0.500, 0.100, 0.050) and (0.800, 0.400, 0.200, 0.100).

On this Mac (Intel, under the light-ok gate), with nine tasks, `power_table` took 8.31 s alone. `derive` plus `render_md` on 1,260 synthetic records (seven models, nine tasks, ten tries per half) took 10.97 s, so `--check` (two derivations) takes about 22 s.

Synthetic, as a design check only: some per-task test after Holm rejected in 0, 8, 107 and 101 of 200 simulations. The contrast rejected in 1, 155, 200 and 200, and the bootstrap excluded zero in 1, 141, 200 and 200. That agrees with E1's sizing: per-task tests at ten units resolve little.

With bootstrap_reps 200 the power run took about 17 s, so 100 was chosen to keep it to seconds.

## Open questions for the lane lead

1. **The design's home.** `build_draft.py` must write the design under `stats_design` in the pre-registration, in the closed shape of stats' docstring. Confirm the key name, or rename it in one place (`DESIGN_KEY`).
2. **The results-file shape.** The pipeline lane must write `results/*.json` as JSON lists of interface 11 records, and must map each grader's output onto the three view words.
3. **result.py.** It must place `render_block(derive(...))` into RESULT.md once.
4. **Optional arm C.** If arm C (`claude-fable-5-1`) runs, the pre-registration must say whether it is listed in Claude Code's `harness_models`. If it is listed, it gets within-harness tests the plan does not name. If it is not, its records are refused.
5. **Agent versions in the rendered output.** A version is printed as code. A bare version such as `1.0` would trip `lint_language` (one-point-zero). Ask CP2 what the version strings look like.
6. **Mixed levels in one cell.** A cell that mixes repeat and pressure levels is not refused.

## Deferred to Javier

- Any sentence comparing models (plan line 215): stats prints numbers and family labels only.
- Real numbers: none exist until the run (CP7); the one-habit floor values come from `probes4.py`.

## Lessons worth keeping

- A grep watcher on a sub-agent's transcript matched the brief's own text (the word SubagentHandback in the prompt) and fired at once. Wait for the completion notification instead.
- Working out the expected figures for a typed Holm case at the wrong family size (four, not five) gave a red test that was wrong, not one that showed the code was missing. Derive the expected numbers from the stated m.
- A mutant that only swaps the stop view can still agree with the strict view (raw and failures both read a stop as not right). Choose the mutant whose output differs.

## Fold 1 (the round 1 lane review, folded under the lane lead's fold brief, Thu 8 Oct 2026)

Start: c724881e, clean tree.
Commits:
- c86ba42e: red tests (91 run: 9 failures, 1 error);
- a0318fa7: the fixes;
- this section.

No reviewer of my own was spawned in this fold.

| Finding | Severity | Fold |
|---|---|---|
| W4E1-1 `--check` blind to records outside top-level `*.json` | MAJOR | `_strays`, called from `results_files`: the results folder holds only top-level `*.json` files. `--check` exits 1 with `FAIL results folder` for a subfolder, `.jsonl` or `.txt`. Mutant: `_strays` returns [], and the check falls back to the no-takes line. |
| W4E1-2 bootstrap outward rounding unbound | MAJOR | A test stubs the order statistics at 2/3 and 5/6 and asserts lower 0.666 (floor3) and upper 0.834 (ceil3); all three rounding mutants are red. |
| W4E1-3 contrast Holm size unbound | MAJOR | The test asserts the contrast's exact Holm value, 3 x p over the three contrasts. |
| W4E1-4 power clustering unbound | MAJOR | Seeded counts are bound on three grid points: (0.7, 0.5) with no spread, with task spread 0.4, and with wording spread 0.4. Zeroing either offset changes them. |
| W4E1-5 markers once and in order unbound | MAJOR | The two-blocks page and the reversed-markers page are added to `test_each_named_problem`. |
| W4E1-6 `0 of n` slots beside no takes | MINOR | Table 6 prints no takes when no slot matched. The zero test now also catches any cell starting `0 of` and runs on a fixture with an unmatched pair. |
| W4E1-7 free-text agent.version | MINOR | `VERSION_ID` (id-like: no spaces, pipes or slashes), with a mutant. CP2 should confirm the shape. |
| W4E1-8 multi-model harness without a contrast | MINOR | `validate_design` refuses it. |
| W4E1-9 PASS on files with no records | MINOR | The check prints `stats --check: no takes (k results files, 0 records); nothing was compared`, exit 0, never PASS. |
| W4E1-10 mixed levels | MINOR | `check_records` refuses a task that carries both kinds of level (read through `level()`, so the untagged-level mutant goes red). |
| W4E1-11 descriptive-with-test clause unbound | MINOR | A mutant adds a p to the descriptive rows, and `derive` refuses. |
| W4E1-12 `<=` against `<` at alpha | NIT | A Holm case lands exactly on 1/20 and reads at alpha. |
| W4E1-13 NITs | NIT | All five are folded: a negative repeat is refused; alpha must use its shortest spelling ("0.05"); the comparisons heading names both Holm families; an all-stop half's excluded view reads "k stops excluded, none counted"; the agent check is its own function `_check_agent`, called unconditionally. |
| The review's equivalent and error-only mutants | n/a | New tests make each one red: `family_of` is read alone; harness-error with label `wrong-move` and views None is refused; a harness name with a space is refused; `_complete` on a missing half is asserted directly. |

Checks on a0318fa7 (each behind light-ok, foreground, single-threaded BLAS):
- `tests/test_stats.py` alone: `Ran 91 tests` / `OK`.
- `stats.py --check`: `stats --check: no takes (0 results files); nothing was compared`, exit 0.
- `copy_manifest.py --check` after `git add`: `ok: 110 files from 8 fragment(s) ...`.

Mutant re-run: copies of the review's `swap.py` and `mutants.json`, run one at a time, each behind light-ok. `mutants.json` holds 49 entries; the review's prose says 50. All 49 are RED with 91 tests in the whole file (`grep -c ' -> RED'` gives 49; none GREEN or ERROR-ONLY). The first background pass died at 18:55 with the previous lead's session, after 35 mutants, all red. The full pass then ran again in the foreground, 19:07 to 19:15 EDT.

`git diff c724881e --stat` touches only `evals/gap-study-4/stats.py`, `evals/gap-study-4/tests/test_stats.py` and this report.

## Fold 2 (the round 2 lane review, folded under the lane lead's fold brief, Thu 8 Oct 2026)

Start: 2f5ba871, clean tree.
Commits:
- 1fd9e6da: red tests (96 run, 2 failures);
- 3912c6d9: the fixes;
- this section.

No reviewer was spawned. Every gate and mutant pass ran in the foreground, behind light-ok.

| Finding | Fold (decision: the lane lead's) | Whole-file mutant |
|---|---|---|
| W4E2-1 MAJOR heading's contrast count unbound | The heading is asserted on a NINE-task design with three contrasts: "over the 9 tasks that run" and "over the 3 stronger-against-weaker contrasts". The code was already right. | f_heading_contrasts_wrong RED |
| W4E2-2 MINOR VERSION_ID space and pipe unbound | `1.0\|x` and `1.0 x` are added to the refused versions. | f_version_allows_space RED, f_version_allows_pipe RED |
| W4E2-3 NIT dotfiles | `_ignored`: a dot-named entry that is not .json (.DS_Store, .gitkeep) is ignored, and a dot-named .json is read as records. Both halves are bound. | f_dotfiles_are_strays RED, f_dot_json_skipped RED |
| W4E2-4 NIT per-task level scope | A fixture with m1 on repeats and m2 on pressure in one task is refused. | f_mixed_level_per_model RED |
| W4E2-5 NIT docstring | THE CHECK now names the strays refusal (and the ignored dotfiles) and the "k results files, 0 records" line, with a test. The fold 1 first mutant pass ran as a background job, against the brief; this fold ran every gate and mutant in the foreground. | n/a |

Gates on 3912c6d9:
- `tests/test_stats.py` alone: `Ran 96 tests` / `OK`.
- `stats.py --check`: `stats --check: no takes (0 results files); nothing was compared`, exit 0.
- `copy_manifest.py --check` after `git add`: `ok: 110 files from 8 fragment(s) ...`.

The review's own strays mutants (`f_strays_*`) no longer apply as written, because the line they replace now carries `_ignored`. The fold's six mutants, run against the whole file, cover the new rule.

Open items the lane lead carries to glitch-f3 (no change in this lane):
- RESULTS_DIR is shared with base run.py's per-task dict files.
- VERSION_ID needs the adapters to return a bare version (CP2).
- Alpha's shortest form binds build_draft.py's writer.
- The excluded view has three shapes (a dict, `no takes`, "k stops excluded, none counted"), which matters for result.py.

## Fold 3 (the round 3 lane review: VERDICT PASS, no MAJOR; the loop stops here under the stop rule)

Start: 114cdc69, clean tree.
Commits:
- bdfb7d9f: red test (97 run: 1 failure, 1 error);
- 82bd268f: the fix;
- this section.

| Finding | Fold (decision: the lane lead's) | Whole-file mutants |
|---|---|---|
| W4E3-1 MINOR: `_ignored` skipped dot-named folders, and its .json test was case-sensitive | `_ignored(p)` now ignores only dot-named regular files that are not .json in any case. A test asserts that `.d/x.json` (a dot-named folder) and `.t.JSON` each make `--check` exit 1, with a mutant. | f3_dot_folders_skipped RED; f3_json_case_sensitive RED; f3_all_dot_skipped RED |
| W4E3-2 NIT | Left, by the lane lead's decision. | n/a |

Gates on 82bd268f, finished at 20:40 EDT, before the hold:
- `tests/test_stats.py` alone: `Ran 97 tests` / `OK`.
- `stats.py --check`: the no-takes line, exit 0.
- `copy_manifest.py --check`: `ok: 110 files from 8 fragment(s) ...`.

## Fold 4 (athena's test_scaffold collision; glitch-f3's named exception)

athena run `gap4-w4e-f3-d851079-20261009T022328Z` on d851079b failed `test_round4.py` in one test: wave 1's `tests/test_scaffold.py` `test_a_source_outside_the_allowed_ones_is_refused`. Its hypothetical lane `zz-later` targeted `intervals.py`, which this lane really claims.

Named exception, glitch-f3's ruling under Javier's delegation (glitch-f3's, not Javier's words):
- The hypothetical lane's target path at test_scaffold.py:217-219 changes from `intervals.py` to `zz_intervals_probe.py`. The source and `allowed == []` are unchanged.
- This is the only wave 1 edit.

Guard: `NoFixtureTargetIsARealClaim` in `tests/test_stats.py`.
- It derives the fixture's later-lane target paths from test_scaffold.py's own source (ast), and the claims from every COPIED.d fragment.
- It asserts that the two sets do not overlap.
- Mutant: `intervals.py` put back as the target makes the overlap `["intervals.py"]`.

Commits:
- 06ed8098: the guard (red by construction before the fix);
- the next commit: the test_scaffold exception and this section.

Both are written under the Mac hold, and every gate is pending the lift.
