status: done

# Lane w4d-cp4-variants: CP4 variants.py and tasks/check_task.py

Base `48f10056`. Commits: `2047acfa` (the red tests, failing at import), `911ef156` (the code, green), and this report.
Start block: HEAD and branch as required; the worktree was clean; e2979b31, 844a4ce and 68ec902f are present; core.hooksPath is unset.
I ship no task, wording or fixture.

## Files (all new)
- `evals/gap-study-4/variants.py`: the schema (gap4-task/1, gap4-variants/1) and the interface 10 API.
- `evals/gap-study-4/tasks/check_task.py`: checks 1-12, each its own function (`check_1_schema` ... `check_12_run_tree_abs`), plus `problems()` and the CLI.
- `evals/gap-study-4/tests/test_variants.py`: seven toy tasks (one per grader) that pass all checks, with near-misses and in-memory mutants per clause, and the drift test.
- `evals/gap-study-4/COPIED.d/w4d-cp4-variants.json` and `evals/gap-study-4/checks.d/w4d-cp4-variants.txt`.

## API signatures
`HALVES, KINDS, N_WORDINGS=5, REPEATS=2, TRIES_PER_HALF=10, TASK_SCHEMA, VARIANTS_SCHEMA, TASKS_DIR, VARIANTS_DIR, PINNED_TREE="844a4ce0d89437ca043363981a86096f6383a141", PRESSURE_SEPARATOR=" ", GRADED_PATH_FIELDS`;
`class TaskError(ValueError)`; `load_task(task_id, *, root=None)`; `load_variants(task_id, *, root=None)`; `cells(task_id, *, root=None)`;
`operator_steps(task_id, half, wording, *, pressure=None, root=None)`; `probe_line(...)`; `grader_spec(...)` (same arguments);
`row_fields(cell)`; `render_source(template, run_tree, project)`; `graded_paths(task_id, *, root=None)`.
check_task: `problems(task_id, *, root=None, table=None)`, and `main(argv)`.

## Tests and checks run (counts from the runner)
- test_variants.py alone, gated on light-ok: `Ran 87 tests ... OK` on 911ef156. On 2047acfa it was red with `ModuleNotFoundError: No module named 'variants'`, as intended.
- tests/test_pause_adherence.py alone: `Ran 30 tests ... OK`.
- copy_manifest.py --check after git add: `ok: 110 files from 8 fragment(s) ... 61 new`.
- check_task.py --all on this head: `check_task: no tasks`, exit 1.
- Not run on the Mac, per the brief: test_round4.py and run_checks.py. Nothing was skipped.

## Deviations (flagged)
- Commit granularity: one red-test commit, then one code commit, rather than one commit per check. I did this to land green before the 20:45 hold.
- A fresh opus-medium review was started at 18:10 EDT. Its findings had not arrived when I was told to hand back, so none are folded.

## Lane decisions (this lane's own, for the per-task lanes)
1. A step is `{n, line, marker?, recovery?}`, with `recovery` = `{if_reply_holds, send, at_most?}`. This is the readers' shape (check_take 1067, 1126-1132; drive 1347-1350); the brief listed `if_reply_holds` at step level.
2. Shape is fixed per grader: per-half for scope_read, template_adherence, number_fidelity, precondition_refusal and plan_gate; per-task for confounded_design and new_tasks.
3. A new_tasks entry is `check_spec:<the task's own id>`.
4. Every generator and helper path lies under `evals/gap-study-4/fixtures/`.
5. Wording ids are w1..w5 in order. Steps are numbered 1..N contiguously, and the probe is one of them. `repeat` runs 1..REPEATS.
6. The probe is never typed: specs write `"{probe}"` (or `{grader half: "{probe}"}`), and approval-scope writes `run_tree_abs: "{run_tree}"`.
7. `{pressure}` in a wording passes check 1 so that check 5 names it. `{run_tree}` in a line is a check 1 finding.
8. The pressure factor is present exactly for precondition_refusal.
9. number_fidelity derives exactly one step, after the probe, and its spec's `pushback_line` must equal that step's line (check 9).
10. The probe step holds no `{project}` or `{source}`, because the grader finds it by its exact line (check 9).
11. `marker_sources` is keyed by field name for spec marker fields, and by the marker's own text for wait-point keys and step markers. Unused entries are refused.
12. A wait-point `match` with a "." still counts as a literal path. This makes the exclusion check stricter.
13. Check 6 hashes the whole built run tree, masking the temp roots and the build name. Check 11 builds under the project segment of `plan_path`.
14. `problems()` stops after a check 1 failure. A check that raises is reported as a finding.

## Open questions for the lane lead
- Spec paths name a project (`gars/projects/<x>/...`), but takes use a per-take neutral name, and `grader_spec` has no project argument (interface 10). CP2 must fix the name per task, or render it into the spec.
- drive.py at 48f10056 still sends `{source}` relative (`source.relative_to(RUN_TREE)`, line 1259). CP2's driver must send `render_source(...)`.
- Check 7's "binds a graded path or example" is implied by "every pattern matches an example", as the brief words it. Should the binding require a graded path wherever GRADED_PATH_FIELDS is non-empty?
- template_adherence's template bodies are not bound to the pinned contract; check 10 binds markers only.
- The empty-`graded_paths` near-miss uses a mock, because no real non-number-fidelity toy can pass its grader with no path.
- The W3C1-8 (iii) realpath binding is CP2's preflight record.

## Deferred to Javier
- The walks of every wording, and the half of W3C1-8 (i) that requires walks to emit each marker (CP2/CP6, his walk token).

## Lessons
- copy_manifest --check reads the working tree. A red-first commit needs the code moved out of the folder, not just left unstaged.

## Fold 1 (Thu 8 Oct 2026)

Start: `ee67894d`. Commits: `4b12e6bc` holds the red tests; against the unchanged code they gave `FAILED (failures=26, errors=6)`. `d0c4e044` holds the fixes. This section is the third commit.
The rulings on Review A (M1-M3, m1-m5, n1-n2) are glitch-f3's (Thu 8 Oct, 18:20, under Javier's delegation). The decisions on Review B (W4D1-1 to W4D1-7) are the lane lead's: in particular, W4D1-2's convention is the lane lead's decision. None of them are Javier's words.

| id | fix | test (test_variants.py) | mutant (in-memory, asserted red in the test) |
|---|---|---|---|
| M1 | `spec_half_matches`, a clause function of its own | `Fold1ReviewA.test_m1_a_half_swapped_spec_on_graders_that_accept_either_half` (precondition_refusal and plan_gate) | `spec_half_matches` turned into a no-op |
| M2 | `examples_literal`: every example must pass `v.is_literal` (no regex metacharacters, no braces) | `test_m2_examples_are_literal` (a regex example, a `{project}` example) | `examples_literal` returns [] |
| M3 (folds W4D1-4) | `binding_paths`: the half's graded paths only, rendered with BUILD_NAME; template_adherence keeps its examples | `test_m3_a_pattern_bound_only_to_an_invented_example`, `test_m3_template_adherence_keeps_its_examples` | binding goes back to graded paths plus examples |
| m1 | `unrenderable_steps`: the probe step and every derived step | `test_m1_derived_steps_name_no_project_or_source` | returns [] |
| m2 | `pushback_counts_only`: the pushback lines may differ only in digit runs | `test_m2_pushback_lines_differ_only_in_counts` | returns [] |
| m3 | `source_climbs`: no `..`, `.` or empty segment in the source template | `test_m3_the_source_template_cannot_climb` | returns [] |
| m4 and W4D1-3 | `fixture_refusals`, called from `build_fixture_tree` (pins checked only on the pinned seed's build): generated sha256; first-study samples.csv md5 and tree sha; project dir and its `exits N (expected M)` line; copied-tree JSON stdout and its sha | `test_m4_the_drivers_take_time_refusals` (6 near-misses), `test_m4_a_first_study_md5_that_matches_passes` | returns [] |
| m5 | `variants.task_cells`, which `cells` returns and check 5 validates | `test_m5_check_5_reads_variants_cells` | check 5 runs on its own copy of the cell logic |
| n1 | `problems()` checks the id is a file stem first | `test_n1_a_single_task_run_names_a_stem` | the id check removed |
| n2 | `spells_source`: also matches the source path with any single segment where `{project}` stands | `test_n2_the_source_spelled_with_a_typed_project` | back to a plain substring match |
| W4D1-1 | `marker_shape_problems` in check 3: a marker on every step before the probe, none on the probe step | `Fold1ReviewB.test_w4d1_1_a_pre_probe_step_without_a_marker`, `..._a_probe_step_with_a_marker` | returns [] |
| W4D1-2 | spec paths may hold `{project}` only. `render_project`, plus `project=` on `grader_spec`, `render_grader_spec`, `concrete_specs`, `task_graded_paths` and `graded_paths`. Checks 7, 8, 9 and 11 render with BUILD_NAME, and `path_placeholder_problems` refuses any other placeholder | `test_w4d1_2_project_in_spec_paths` (unrendered by default; precondition_refusal.check_spec accepts the literal `{project}`, so the caller must render), `..._check_8_renders_with_build_name`, `..._check_9_only_project`, `..._check_11_renders_with_build_name` | BUILD_NAME changed; `path_placeholder_problems` returns [] |
| W4D1-5 | check 10 binds each recovery's `if_reply_holds` (keyed by its own text) and, when `marker_sources` names it, `templates` (`OPTIONAL_MARKER_FIELDS`) | `test_w4d1_5_if_reply_holds_is_bound`, `test_w4d1_5_templates_may_be_bound` | `OPTIONAL_MARKER_FIELDS = ()` |
| W4D1-6 | variants.py's docstring: marker sources are keyed by field name, so one file must hold every half's value | (documentation) | none |
| W4D1-7 | `variants.HOLD_HALF` (trap for every grader but number_fidelity and confounded_design, whose tasks record a decision `act-hold`) and `hold_half_problems` | `test_w4d1_7_the_hold_half_is_the_graders`, `test_w4d1_7_reply_graders_record_act_hold` | `HOLD_HALF` patched |

Lane decisions in this fold:
- m2: pushback counts are written in digits.
- W4D1-7: the HOLD_HALF values themselves, and the `act-hold` decision id for the two graders whose right moves are both replies.
- M3: a forbidden pattern must match the rendered path, so a task lane writes the project segment as a pattern such as `[^/]+`.

The toys changed to follow the fold:
- number_fidelity: its pushback counts are 5 and 9 against a true count of 7.
- plan_gate: its store pattern now matches the store path itself.
- confounded_design and number_fidelity: each records `act-hold`.
- The copied-tree generator prints JSON.

### Interface 10 changes (the second-set lanes build on these)
- Spec path values (GRADED_PATH_FIELDS fields, including the keys of `fixed_sha256`) may hold `{project}`, and no other placeholder.
- `grader_spec(task_id, half, wording, *, pressure=None, project=None, root=None)`: it renders `{project}` when given and returns paths unrendered otherwise.
- `graded_paths(task_id, *, project=None, root=None)`.
- New names: `variants.task_cells(task, variants_doc)`, `variants.render_project(spec, task, project)`, `variants.HOLD_HALF`, `variants.ACT_HOLD_DECISION = "act-hold"`.
- New rules:
  - every step before the probe carries a marker, and the probe step carries none;
  - forbidden examples are literal;
  - patterns bind graded paths (template_adherence: its examples);
  - derived steps hold no `{project}` or `{source}`;
  - the source template has no `..`;
  - `marker_sources` may name `templates`, and must name every `if_reply_holds`.

### Whole-file swaps (one process each batch; script `scratchpad/w4d-fold1/swap.py`)
Each mutant is check_task.py, or variants.py, with one site changed and loaded in place of the module. The whole test_variants.py then runs once against it. These are the closing lines, as printed:

```
mutant M1 spec_half_matches: Ran 109 tests, failures=2 errors=0 -> RED
mutant M2 examples_literal: Ran 109 tests, failures=2 errors=0 -> RED
mutant M3 binding_paths: Ran 109 tests, failures=2 errors=0 -> RED
mutant m1 unrenderable_steps: Ran 109 tests, failures=2 errors=0 -> RED
mutant m2 pushback_counts_only: Ran 109 tests, failures=1 errors=0 -> RED
mutant m3 source_climbs: Ran 109 tests, failures=3 errors=0 -> RED
mutant m4/W4D1-3 fixture_refusals: Ran 109 tests, failures=6 errors=0 -> RED
mutant m5 own cells copy: Ran 109 tests, failures=1 errors=0 -> RED
mutant n1 stem check: Ran 109 tests, failures=1 errors=0 -> RED
mutant n2 spells_source: Ran 109 tests, failures=1 errors=0 -> RED
mutant W4D1-1 marker_shape_problems: Ran 109 tests, failures=2 errors=0 -> RED
mutant W4D1-2 path_placeholder_problems: Ran 109 tests, failures=1 errors=0 -> RED
mutant W4D1-2 check 8 unrendered: Ran 109 tests, failures=1 errors=0 -> RED
mutant W4D1-2 render_project: Ran 109 tests, failures=2 errors=0 -> RED
mutant W4D1-5 if_reply_holds: Ran 109 tests, failures=1 errors=0 -> RED
mutant W4D1-5 OPTIONAL_MARKER_FIELDS: Ran 109 tests, failures=1 errors=0 -> RED
mutant W4D1-7 hold_half_problems: Ran 109 tests, failures=3 errors=0 -> RED
```

### Gates on the fold's head
- test_variants.py alone: `Ran 109 tests ... OK`.
- test_pause_adherence.py alone: `Ran 30 tests ... OK`.
- copy_manifest.py --check: `ok: 110 files from 8 fragment(s)`.
