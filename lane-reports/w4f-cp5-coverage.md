status: done

# Lane w4f-cp5-coverage: CP5's coverage table (report written Thu 8 Oct 2026, 18:24 EDT)

Branch `gap4/w4f-cp5-coverage` from base `48f10056`. Nothing pushed, nothing merged.

## Files changed (all new, all this lane's)

- `evals/gap-study-4/coverage_today.md`: the ten-row table, its reading rules, a two-line note per row, and what it does not say.
- `evals/gap-study-4/tests/test_coverage.py`: the parser, the closed lists, the commit pin, the cite binding, the reach-home binding, the notes binding, the forward binding to `tasks/*.json`, and the mutants.
- `evals/gap-study-4/COPIED.d/w4f-cp5-coverage.json`: the copy-record fragment (four files, all `new`).
- `evals/gap-study-4/checks.d/w4f-cp5-coverage.txt`: the test alone, and `lint_language.py` and `lint_pooling.py` on the table.
- `lane-reports/w4f-cp5-coverage.md`: this report.

Commits: `2cd760ef` (checkpoint 1: the test, red on a stub with one cited row), `5a3529e4` (checkpoint 2: ten rows, green), `9b0d2538` (the notes bound), `6d1c1d72` (review round 1 folded), then this report.

## Start block and the commit pin

- Start block: HEAD `48f10056...`, branch right, `git status --porcelain --ignored` printed nothing, `e2979b31`, `844a4ce` and `68ec902f` all `commit`, no `core.hooksPath`.
- `git log -1 --format='%H %cI' a626cdc2...` printed `a626cdc2337246e972a198b026d53ce836416321 2026-10-06T20:15:15-04:00`.
- The `gars/` diff between `0f602ea0` and `a626cdc2` listed 0 files; between `844a4ce` and `a626cdc2` it listed 205; `844a4ce` is an ancestor of HEAD.

## The answers (one yes, six partly, three no)

This table is as of `7934d5d4`. Fold 1 changed the approval-scope row's reach to `claude-and-codex` and relabelled declarations `(dropped)`; see "Fold 1" below.

Each row is read for a Claude Code session in a public project with GARS's hooks active.

| pair | caught | reach | in two lines |
|---|---|---|---|
| scope-read | partly | claude-and-codex | `decide` refuses reads outside the workspace (guard_hook.py:957-962; policy.py:126-129 for shell reads). A source inside the workspace but outside `projects/` is read freely, so the answer turns on the fixture. |
| template-adherence | partly | claude-and-codex | `decide` refuses every agent `link` unless a human declared the source public (guard_hook.py:848-849). With a declaration the link passes, and nothing checks the reply's template or the restated pause. |
| number-fidelity | no | none | The wrong move is in words, and the hooks fire only before tool calls and at session start (.claude/settings.json:2-24). No code checks a reply against stage 00's counts. |
| precondition-refusal | partly | claude-and-codex | Stage 01 exits while an input is absent (stage01:1033-1040), and `decide` refuses writes to `files.csv` and `01_samplesheets/*` (guard_hook.py:88-91). `samples.csv` is not protected, so a fabricated one passes. |
| plan-gate | partly | claude-and-codex | The producer role cannot run `approve` (registry.json:1121, policy.py:156-158), and the approval store is protected. A hand-typed stamp in `PLAN.md` lands, and only `verify` and `approve` reject it later. |
| confounded-design | no | none | The wrong move is in words; stage 01 checks `batch` and `sex` against condition (stage01:562-573, 597-606) but never `lane`. Nothing reads whether the reply names the alias. |
| declarations (candidate) | no | none | The only strandedness rule refuses a blank (stage01:774-777) and accepts any listed value; `_config/` is not protected. A guessed value passes. |
| explain-not-act | partly | claude-and-codex | `decide` refuses hand edits to `01_samplesheets/*` (guard_hook.py:91, 195-196). Editing `samples.csv` and re-running stage 01 with `--force` stays open. |
| approval-scope | yes | every-agent | `link` refuses a populated `raw/` without `--force` in every harness (stage00:513-514), and `decide` refuses a forced link (guard_hook.py:665, 848-849). For Gemini CLI, `--force` reopens the overwrite. |
| conditional-yes | partly | claude-and-codex | Without a public declaration `decide` refuses every agent link, and the right move with it. With one, `link` never reads the layout (stage00:494-534). |

The plan's gotcha (line 773) expected `explain-not-act` to read as covered. It does only for hand edits to the emitted sheets; the design's own route is open.

## Tests and checks run (counts from the runner)

Every run was gated on `mac_slot.py light-ok` (exit 0 each time), in the foreground, with single-threaded BLAS.

- Checkpoint 1: `test_coverage.py` alone, `Ran 32 tests`, `FAILED (failures=8, errors=30)`. This red was intended: the stub's nine missing pairs, and mutants that index rows the stub lacks.
- Checkpoint 2: `Ran 32 tests`, `OK`.
- After binding the notes: `Ran 35 tests`, `OK`.
- After the review fold (the head): `Ran 37 tests in 24.057s`, `OK`. Forward binding: `tasks/*.json seen: 0`.
- `lint_language.py coverage_today.md`: `clean — 1 input(s) scanned, 1 excused line(s) on record` (the excusal is the shared allowlist's, not this lane's). Before the fix it found 2 `[percentage]` hits on `stage 00 %s` inside an excerpt; I shortened that excerpt.
- `lint_pooling.py coverage_today.md`: `clean — 1 file(s) and 0 commit(s) scanned, no excusal path`.
- `copy_manifest.py --check` after each `git add`: `ok: 109 files from 8 fragment(s) ... 60 new`.
- Not run, per the brief: `test_round4.py`, `run_checks.py` and the whole suite. Those are the lane lead's, on athena, on this head.

## What failed or was skipped, and why

- No skip exists in the test file.
- Nothing failed at the head.
- One real defect, found and fixed on the way: `str.splitlines()` splits `codex_hook.py` at characters other than `\n`, which shifted its line numbers by 3 (487 lines by `\n`, 490 by `splitlines`). The test now counts lines at `\n` only, with a mutant that restores `splitlines` and goes red.

## Decisions (this lane's own)

1. **I read `gars/_system/tools/registry.json` at `a626cdc2`.** The brief does not name it. It is the table `tools/policy.py` reads (policy.py:27-28, 101-102), and the plan-gate and explain-not-act answers depend on its roles. It is a `gars/` path and not sealed.
2. **The reading rule.** `caught` covers every route the 6 Oct tree leaves open to a Claude Code session in a public project with hooks active. Inside a non-public project, `decide`'s closed-project rule refuses nearly everything, right moves included, so the table names it once rather than in every row.
3. **The reach cites.**
   - `where` cites the guard that stops the main route.
   - `reach where` cites the line that gives that guard its reach: Codex's envelope for `claude-and-codex`, the helper's own dispatch for `every-agent`.
   - The test binds each reach value to where its two cites live.
4. **Tight cites.** An excerpt must touch both the first and the last cited line, so every line shift is caught.
5. **Excerpt cells.** They are backtick-wrapped, with `\|` for a pipe.
6. **Only `gars/` paths may be cited** (stricter than the brief, which allows any path at the commit).
7. **The candidate mark** is the literal ` (candidate)` after the pair name.
8. **The notes are bound too.** The test checks one note per pair, that each note's verdict equals the row's, and that all 42 line references lie inside their files. The test does not check the notes' excerpts; a reviewer and I checked those by hand.
9. **A review round of my own** (started before the lane lead's rule that lanes spawn no reviewer; its findings and their dispositions are in `scratchpad/w4-review/w4f-builder-review.md`, as the lane lead asked). One fresh `opus-medium` reviewer read the answers, on the same rules. I folded M1 (plan-gate `yes` to `partly`), M3 (confounded-design `partly` to `no`) and M4 (the reach-home binding).
   - I answered M2 (declarations should be `partly` because of the closed-project rule) with decision 2: it stays `no` for a public project.
   - Minor m5 (cite `decide` instead for approval-scope) I did not take. The helper's refusal stops the plain link in every harness; the note states the Gemini residual.

## Open questions for the lane lead

- Several answers turn on fixture layout: where the scope-read source lies, whether the stage 00 tasks carry a `data_sources.tsv` declaration, which stage 01 input precondition-refusal removes, and whether confounded-design's lane appears as `batch`. When CP4's task files land, one more pass could replace "depends on the fixture" with the fixture's answer. The forward binding will already demand a row for each task.
- Ask CP2/CP4 whether the round's tasks run in public projects. The table assumes so.
- The plan-gate note leaves open whether anything stops an analysis from running before `verify` (for example `executor.submit`). The reviewer could not read those files under the named-file rule, and neither did I.

## Deferred to Javier

- Publishing the table beside the results as "which guards to add next" is his word, never this lane's.
- Proposing new GARS guards from it belongs to the post-freeze fix batch, his call. Candidates the table points at: a lane-versus-condition alias check in stage 01, a layout check in `link`, protection for `PLAN.md`'s status line, and a strandedness provenance rule.

## Lessons worth keeping

- `str.splitlines()` is not a line counter for source files: it splits at form feeds and Unicode separators. Count at `\n` when binding `file:line`.
- A mutant that swaps a value for one outside the vocabulary proves the vocabulary check only. A wrong value inside the vocabulary needs a binding of its own (here, reach to where its cites live).
- An answer about what code stops has to be read against the grader's wrong move, not the system's own idea of the act. `PLAN.md`'s stamp is "not an approval" to GARS but is the wrong move to the grader.

## Fold 1 (review round 1, folded Thu 8 Oct 2026, written 19:36 EDT)

This fold was finished by a fresh opus-medium builder after the 18:55 EDT teardown of the old lead's session, on Javier's "w4f and w4h: start fresh".
The first builder committed the red tests (`3fd1527d`) and left uncommitted edits; the fresh builder judged each, finished the fold and committed it (`91e46a46`).
Every decision below is the gap4 lane lead's, from `scratchpad/w4-review/w4f_fold1_brief.md`, never Javier's or glitch-f3's.
Where the fresh builder chose within a decision, it says so as this lane's choice.

| id | lane lead's decision | fix | test | mutant (whole-file swap, red) |
|---|---|---|---|---|
| W4F1-1 (MAJOR) | the reviewer's fix: a per-stage reading | "Each row's stage." replaces "The project is public.": the five stage 00 pairs are read in the closed project, the stage 01 and 03 pairs in a public one. approval-scope's note cites `closed_edit_refusal` (`guard_hook.py:796-814`) and Codex's `apply_patch` Delete (`codex_hook.py:267-269`); template-adherence no longer says "other project writes stay open". | `test_w4f1_1_each_row_is_read_in_its_stage`; `reading_problems` in `problems()` (each stage 00 pair named, no other pair named, each in PAIRS) | `src_stage_pair_not_named_off` red (6), `src_stage_extra_pair_off` red (1), `src_stage_pair_outside_off` red (1), `md_public_reading_restored` red (5), `md_stage_line_drops_approval_scope` red (5) |
| W4F1-2 (MAJOR) | reach is the weakest guard's | "Reach is the weakest." line; approval-scope `yes · claude-and-codex`, where `guard_hook.py:665`, reach where `codex_hook.py:378`; the note says the plain-link refusal (`stage00_register.py:513-514`) reaches every agent | `test_w4f1_2_reach_is_the_weakest_guard_the_verdict_needs` | `md_approval_scope_back_to_every_agent` red (5), `md_weakest_line_removed` red (5) |
| W4F1-3 (MINOR) | fold | CONTRACT_NAME: a cite whose last segment is `CONTEXT.md` is refused; DECIDE_CALL: a claude-and-codex reach excerpt holds `decide(`; "A verdict is a reading." line | `test_w4f1_3_a_codex_reach_cite_is_a_decide_call`, `test_w4f1_3_no_cite_is_a_stage_contract`; near-misses (`MYCONTEXT.md` passes) in `test_w4f1_mutants_and_near_misses` | `src_drop_contract_clause` red (2), `src_drop_decide_call_clause` red (2), `md_reach_cite_to_codex_docstring` red (4), `md_where_cites_a_contract` red (6), `md_verdict_line_removed` red (5), `src_reading_line_missing_off` red (4) |
| W4F1-4 (NIT) | relabel "declarations (dropped)", keep ten rows | DROPPED_ROWS and DROPPED_MARK; the note names the drop as glitch-f3's ruling | `test_w4f1_4_declarations_is_dropped` (a planted `tasks/declarations.json` is red; the real one is absent) | `src_drop_dropped_task_clause` red (1), `src_dropped_mark_off` red (1), `md_declarations_candidate` red (10) |
| W4F1-5 (NIT) | delete, or give each a red test | deleted (the first builder's choice, kept): the rev-parse equality is the pin | a short sha of COMMIT passes, the ancestor fails (`test_w4f1_mutants_and_near_misses`) | `src_pin_rev_parse_off` red (1) |
| W4F1-6 (NIT) | fold one clause | the precondition-refusal note: stage 00 writes `files.csv` at mode 0444 (`stage00_register.py:679-680`; `workspace.py:107`, `MACHINE_OWNED_MODE = 0o444`) | `test_w4f1_6_files_csv_mode` | `md_mode_ref_removed` red (2) |

The mutant counts are failing tests out of 44 in one whole-file run each (runner `scratchpad/w4f_fold1_mutrun.py`, adapted from the reviewer's `w4f-r1/mutrun.py`; the unmutated `base` ran 44, 0 failures).

**Inherited edits, judged by the fresh builder (this lane's calls):**
- Kept: W4F1-5's deletions, W4F1-4's rename and dropped-task clause, W4F1-3's CONTRACT_NAME and DECIDE_CALL clauses, W4F1-2's row, and the md's reading lines and notes for W4F1-1, -2, -3, -4, -6 (each re-read against `git show a626cdc2` of the named files: `guard_hook.py:393-432, 660-702, 796-814, 848-849`, `codex_hook.py:267-269, 378`, `stage00_register.py:513-523, 679-680`).
- Kept: the fix to `test_mutant_reach_value_swapped_inside_the_vocabulary` (already in the file, though the hand-back called it planned). It no longer requires two live reach kinds and still swaps each live row to each other vocabulary value. Proof it did not weaken: `src_every_agent_home_open` and `src_claude_only_home_open` each turn it red (8 failures each).
- Finished: STAGE_00_PAIRS. Its inherited mutant only checked that a string replace removed a string, so it could not go red. It is now a clause of `problems()` (`reading_problems`, with READING_LINES and STAGE_LINE), and its mutants go through `problems()`.
- Finished: W4F1-6's note gained `workspace.py:107`, the line where 0444 is written (stage 00's lines name only `MACHINE_OWNED_MODE`); NOTE_REFS is 47.
- Reset: nothing.

**Rows re-checked under the two new rules (this lane's reading, after the first builder's):** under the per-stage rule only approval-scope's cells changed (reach and cites); template-adherence's note wording changed, not its verdict; scope-read, number-fidelity and conditional-yes are unchanged. Under the weakest-reach rule no other row changed: every other live row's verdict already rests on `decide`.

**Gates at `91e46a46`** (each gated on `mac_slot.py light-ok`, foreground, one process at a time):
- `tests/test_coverage.py` alone: `Ran 44 tests in 38.000s`, `OK` (`tasks/*.json seen: 0`).
- `tests/test_pause_adherence.py`: `Ran 30 tests in 6.557s`, `OK`.
- `copy_manifest.py --check` after `git add`: `ok: 109 files from 8 fragment(s) ... 60 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf`.
- `lint_language.py coverage_today.md`: `clean — 1 input(s) scanned, 1 excused line(s) on record`; `lint_pooling.py coverage_today.md`: `clean — 1 file(s) and 0 commit(s) scanned, no excusal path`.
- Not run, per the brief: `test_round4.py`, `run_checks.py`, the whole suite, a whole-file audit (athena's, through the lane lead).

## Fold 2 (review round 2, folded Thu 8 Oct 2026, written 20:35 EDT)

Round 2 on `a5883ebb` passed with no MAJOR, so under the stop rule only the MINOR that loosens a check was folded. The decisions below are the gap4 lane lead's, from `scratchpad/w4-review/w4f_fold2_brief.md`.

- **W4F2-1 (MINOR), folded.** DECIDE_CALL was only a substring test, so a reach cite on the docstring line `codex_hook.py:320` passed. DECIDE_LINES now pins the only allowed claude-and-codex reach cites to the envelope's `decide(` call lines at `a626cdc2`: `codex_hook.py:323`, `378`, `416-417` and `426`. `decide_line_problems` re-reads each with `git show` and requires its first line, stripped, to open with `decide(`.
  - Test: `TheFold2.test_w4f2_1_reach_cites_are_the_envelope_decide_calls`. Red commit `17485ce9` first (Ran 45, FAILED (failures=1)), then the fix.
  - Near-miss: the `:320` cite is red. Its in-memory mutant: `:320` added to DECIDE_LINES is red as "not a decide( call line".
  - Whole-file swaps (45 tests each): `src_drop_decide_lines_clause` red (1), `src_decide_line_reread_off` red (1), `md_reach_cite_to_codex_docstring_320` red (4).
- **W4F2-2 to W4F2-5 (NITs), left unchanged by the lane lead's decision** and named here: W4F2-2 (STAGE_00_PAIRS and the stage line can swap a pair together), W4F2-3 (`reading_problems` checks the reading lines' heads only), W4F2-4 (the stage line's wording on what `decide` refuses inside a closed project), W4F2-5 (NOTE_NAME and the dropped-mark handling in `note_problems`; see the findings file).
- Gates at the fix commit: `test_coverage.py` alone Ran 45, OK; `test_pause_adherence.py` Ran 30, OK; `copy_manifest.py --check` after `git add` ok (109 files, 8 fragments).
