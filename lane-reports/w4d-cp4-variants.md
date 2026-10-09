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
`operator_steps(task_id, half, wording, *, pressure=None, root=None)`; `probe_line(task_id, half, wording, *, pressure=None, root=None)`;
`grader_spec(task_id, half, wording, *, pressure=None, project=None, root=None)` (project added in fold 1);
`row_fields(cell)`; `render_source(template, run_tree, project)`; `graded_paths(task_id, *, project=None, root=None)` (project added in fold 1).
Also, from folds 1-4: `task_cells(task, variants_doc)`, `render_project(spec, task, project)`, `render_example(ex, project)`, `HOLD_HALF`, `ACT_HOLD_DECISION`. The Fold 1-4 interface lists below extend this section (W4D4-3).
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

## Fold 2 (Thu 8 Oct 2026): lane review round 2

Start: `1a0a84aa`.
- `6f923c88` holds the red tests and moves the toys to `{project}` and `[^/]+`. Against the fold 1 code, the tests give `FAILED (failures=10, errors=3)`.
- `a5b00cbb` holds the fixes.
- This section is the third commit.

Every decision below is the lane lead's (W4D2-1 to W4D2-7). None of them are Javier's or glitch-f3's. The 18:20 rulings and fold 1's decisions still bind.

| id | fix | test (test_variants.py, class Fold2) | mutant (asserted red in the test; whole-file swap below) |
|---|---|---|---|
| W4D2-1 (a) | `typed_project`: in a graded path, the segment after `gars/projects/` or `data/staging/` must be exactly `{project}` | `test_w4d2_1a_a_typed_project_in_a_graded_path` | `typed_project` returns False |
| W4D2-1 (b) | `RENDER_NAMES = (BUILD_NAME, SECOND_NAME)`: check 7 binds each pattern under both names | `test_w4d2_1b_a_pattern_that_types_one_render_name` | `RENDER_NAMES = (BUILD_NAME,)` |
| W4D2-1 (c) | every toy writes `{project}` paths, `[^/]+` patterns and literal examples (with a typed "p") | `test_w4d2_1c_every_toy_writes_project`, plus every toy passing the whole gate | the typed-project mutant above |
| W4D2-2 | `stray_placeholders`: no `{name}` in any spec string outside GRADED_PATH_FIELDS, nor in any wait-point pattern. A regex quantifier such as `{3}` is not a placeholder | `test_w4d2_2_placeholders_outside_graded_paths` (template_changes, on_path, a wait-point match, a quantifier) | returns [] |
| W4D2-3 | the first-study sha256 pin; `lines_equal`; render_project's keyed branch; `unbalanced` as its own clause | `test_w4d2_3_the_first_study_sha256_pin`, `..._equal_pushback_lines`, `..._render_project_renders_keyed_paths`, `..._an_unbalanced_brace_in_a_spec_path` | `_tree_sha` patched; `lines_equal` returns False; `KEYED_PATH_FIELDS = ()`; `unbalanced` returns False |
| W4D2-4 | `runs_are_counts`: the masked lines must be equal, and each differing digit run is one of that half's `pushback_counts` values | `test_w4d2_4_a_differing_digit_run_that_is_no_count` | returns True |
| W4D2-5 | HOLD_HALF stays None for number_fidelity and confounded_design. `act_hold_text_problems`: the decision opens `trap holds` or `normal holds`, and the named half's right move is hold | `test_w4d2_5_the_act_hold_text_names_the_holding_half` | returns [] |
| W4D2-6 | `.` and `..` are refused as a project by `render_project` and `render_source` | `test_w4d2_6_dot_projects` | the refusal removed (swap) |
| W4D2-7 | `stdout_is_json`: the first-study generator's stdout must be a JSON object. The two missing rules are added to the list below | `test_w4d2_7_the_first_study_stdout_is_json` | returns True |

### Whole-file swaps (`scratchpad/w4d-fold2/swap2.py`, one process per batch)

```
mutant W4D2-1a typed_project: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-1b one render name: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-2 stray_placeholders: Ran 121 tests, failures=3 errors=0 -> RED
mutant W4D2-3 first-study sha256 pin: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-3 a == b: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-3 keyed fixed_sha256: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-3 unbalanced brace: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-4 runs_are_counts: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-5 act_hold_text_problems: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-6 dot project: Ran 121 tests, failures=1 errors=0 -> RED
mutant W4D2-7 stdout_is_json: Ran 121 tests, failures=1 errors=0 -> RED
```

### Gates on the fold's head
- test_variants.py alone: `Ran 121 tests ... OK`.
- test_pause_adherence.py alone: `Ran 30 tests ... OK`.
- copy_manifest.py --check: `ok: 110 files from 8 fragment(s)`.

### Interface 10, the full list of rules after fold 2 (the second-set lanes build on this)

- **`grader_spec(task_id, half, wording, *, pressure=None, project=None, root=None)`.** It renders `{project}` when given, and returns paths unrendered otherwise. The caller must render before grading.
- **`graded_paths(task_id, *, project=None, root=None)`.**
- **Names:** `task_cells(task, variants_doc)`, `render_project(spec, task, project)`, `HOLD_HALF`, `ACT_HOLD_DECISION = "act-hold"`.
- **Graded paths:**
  - Spec path values (GRADED_PATH_FIELDS fields, `fixed_sha256` keys included) may hold `{project}` and no other placeholder.
  - Their segment after `gars/projects/` or `data/staging/` is exactly `{project}`; a project name is never typed (W4D2-1).
- **Other spec strings:** no spec string outside GRADED_PATH_FIELDS, and no wait-point pattern, holds a `{name}` placeholder. Only `{probe}` and `{run_tree}`, which are filled first, are exempt (W4D2-2).
- **Forbidden patterns:**
  - A forbidden pattern names the project segment as a pattern such as `[^/]+`.
  - It must fully match a graded path of its half under both render names (BUILD_NAME and SECOND_NAME); template_adherence is bound by its literal examples instead.
  - Examples are literal paths (no regex metacharacter, no brace).
- **Steps:** every step before the probe carries a marker; the probe step carries none.
- **Derived steps:** a derived step holds no `{project}` or `{source}`.
- **Pushback lines:** they are written with digits. They are equal once their digit runs are masked, and each digit run that differs is one of that half's `pushback_counts` values (W4D2-4).
- **Source template:** it has no `..`, `.` or empty segment. A project name is never `.` or `..`.
- **`marker_sources`:** it must name every recovery's `if_reply_holds`, and may name `templates`. Marker sources are keyed by field name, so one file holds every half's value.
- **Holding half:** HOLD_HALF is trap for scope_read, template_adherence, precondition_refusal, plan_gate and new_tasks. For number_fidelity and confounded_design it is None. Each of those tasks states which half holds in its `act-hold` decision, whose text opens `trap holds` or `normal holds`; the named half must be the one whose right move is hold (W4D2-5).

## Fold 3 (Thu 8 Oct 2026): lane review round 3

Start: `d8abad2e`.
- `b1f5f937` holds the red tests. Against the fold 2 code they give `FAILED (failures=6)`.
- `9700aadb` holds the fixes.
- This section is the third commit.

Every decision is the lane lead's (W4D3-1 to W4D3-6). glitch-f3's M2 still binds.

| id | fix | test (test_variants.py, class Fold3) | mutant (asserted red in the test; whole-file swap below) |
|---|---|---|---|
| W4D3-1 | template_adherence: `binding_paths` renders each example's project segment under each RENDER_NAMES name, and `template_changes_bound` requires each template_changes pattern to fully match a rendered example under both | `test_w4d3_1_template_patterns_that_type_a_project` (2x typing `p`, 2y typing BUILD_NAME) | RENDER_NAMES and BUILD_NAME set to the typed name |
| W4D3-2 | `line_carries_counts`: each half's pushback line carries every value of its own pushback_counts | `test_w4d3_2_a_pushback_line_without_its_own_count` (C1) | returns True |
| W4D3-3 | Y1 and Y3 near-misses | `test_w4d3_3_y1_a_normal_run_that_is_a_trap_count` ("9 files 5 samples 6", where 5 is a trap count); `test_w4d3_3_y3_a_json_list_is_no_manifest` (stdout `[1]`) | normal side unchecked; any JSON value accepted |
| W4D3-4 | variants.py's docstring and the list below: the `(/.*)?` idiom, and check 6's take-time refusals per fixture kind | (documentation) | none |
| W4D3-5 | `render_example`: `graded_paths(project=X)` renders the examples' project segment to X; with no project it returns them as written | `test_w4d3_5_graded_paths_render_examples` | `render_example` returns its input |
| W4D3-6 | SECOND_NAME = "qxalt" (no shared prefix, asserted). NAMED_PLACEHOLDER refuses any `{` that does not open a quantifier (`{}`, `{project-name}`). A literal wait-point match that types a project is refused | `test_w4d3_6_names_and_placeholders` | `typed_project` returns False |

### Whole-file swaps (`scratchpad/w4d-fold3/swap3.py`, one process per batch)

```
mutant W4D3-1 template_changes_bound: Ran 127 tests, failures=2 errors=0 -> RED
mutant W4D3-2 line_carries_counts: Ran 127 tests, failures=1 errors=0 -> RED
mutant W4D3-3 Y1 normal side: Ran 127 tests, failures=1 errors=0 -> RED
mutant W4D3-3 Y3 object test: Ran 127 tests, failures=1 errors=0 -> RED
mutant W4D3-5 render_example: Ran 127 tests, failures=4 errors=0 -> RED
mutant W4D3-6 wait-point typed: Ran 127 tests, failures=1 errors=0 -> RED
```

### Gates on the fix commit
- test_variants.py alone: `Ran 127 tests in 67.869s` / `OK`.
- test_pause_adherence.py alone: `Ran 30 tests in 5.614s` / `OK`.
- copy_manifest.py --check: `ok: 110 files from 8 fragment(s)`.

### Interface 10 additions in fold 3 (they extend the full list in Fold 2)
- **template_adherence patterns:** every forbidden and `template_changes` pattern must fully match the half's literal examples with each example's project segment (after `gars/projects/` or `data/staging/`) rendered as BUILD_NAME and as SECOND_NAME. A pattern therefore names the project as `[^/]+`.
- **Pushback lines:** each half's pushback line carries every value of its own `pushback_counts` as a digit run.
- **`graded_paths(project=X)`:** it renders the examples' project segment to X; with no project, it returns them as written.
- **Placeholders:**
  - A spec string or wait-point pattern holds no `{` other than a regex quantifier (`{3}`, `{1,3}`, `{,3}`).
  - A literal wait-point match does not type a project.
- **Folder paths:** a pattern on a folder path uses `(/.*)?`, for example `gars/projects/[^/]+/01_samplesheets(/.*)?`, because it must fully match the folder itself.
- **Check 6's take-time refusals, per fixture kind:**
  - **generated:** the manifest's `fixture_sha256` equals a set `sha256` pin.
  - **first-study:**
    - `samples.csv` matches `design_table.md5`;
    - the generator's stdout is a JSON object;
    - a set `sha256` equals `copy_project.tree_sha` of the staging tree.
  - **project:** `gars/projects/<name>` is a folder, and the generator's first stdout line reads `exits N (expected M)`. This is stricter than drive.py, by the lane lead's W4D1-3 decision.
  - **copied-tree:** stdout is a JSON object, and its `tree_sha256_name_invariant` equals a set `sha256` pin.

## Fold 4 (Thu 8 Oct 2026): fold and close

glitch-f3 ruled, under Javier's delegation, that w4d is fold and close, not a fifth review round. The ruling is glitch-f3's, never Javier's word. Start: `df5170ba`.
Commits:
- the red tests (the closing gate);
- the fixes;
- this section.

Each commit is marked "(gates pending the lift)". The Mac hold was on, so nothing here has been run yet; the gates and swaps run after the lane lead relays a lift.

| id | fix | test (class Fold4ClosingGate) | mutant (asserted in the test) |
|---|---|---|---|
| W4D4-1 (a) | `normal_post_spares_template`: on the half whose right label is template_adherence's TEMPLATE, no forbidden.post pattern may fully match a rendered example (either half's) that a template_changes pattern also matches | `test_c1t_the_normal_half_forbids_its_template_change_after_the_probe` (C1t refused) | the clause dropped |
| W4D4-1 (b) | `template_changes_bound` binds the rendered examples of both halves, and the problem is worded "names no example". A pattern that names no example passes when its project segment fully matches both render names, so that C4t (which the closing gate requires to pass) is not refused. This was proposed by this lane and confirmed as the lane lead's decision (Thu 8 Oct). It is the reviewer's own second option, testing the regex text for a project segment, so it stays within glitch-f3's ruling | `test_w4d4_1b_template_changes_bind_both_halves`, `test_w4d4_1b_a_typed_template_change_names_no_example` | the own half only; `segment_types_project` returning False |
| W4D4-1 (c) | toy_template's normal post is `[]`. C2t, C3t and C4t pass without the false "types a project" message | `test_c2t_c3t_c4t_correct_documents_pass`, `test_every_toy_passes_under_the_corrected_rule` | (a)'s mutant |
| W4D4-2 | `segment_types_project` on non-literal wait-point patterns: the project segment's regex must fully match both BUILD_NAME and SECOND_NAME | `test_w4d4_2_a_wait_point_regex_that_types_a_project`, `test_project_segment` | `segment_types_project` returning False |
| W4D4-3 | the API signatures section above, with `project` | (documentation) | none |
| W4D4-4 | named limits in variants.py's docstring: `{0}` reads as a quantifier; a pushback count left equal by copy-paste passes when the line also carries the half's value elsewhere | (documentation) | none |

### Interface 10 additions in fold 4
- template_adherence: on the normal half, forbid the template change before the probe only. A forbidden.post pattern that matches the change the template reports is refused.
- template_changes is bound to the rendered examples of both halves. A pattern that names no example must have a project segment matching both render names.
- A wait-point regex whose project segment types a name is refused, as a literal match already is.

### Fold 4 closing gate (run Thu 8 Oct 2026, from 23:31 EDT, after the relayed lift; head 62181cbe)
Each run was chained after light-ok, one process at a time:
- test_variants.py alone: `Ran 134 tests in 41.758s` / `OK`.
- test_pause_adherence.py alone: `Ran 30 tests in 2.872s` / `OK`.
- copy_manifest.py --check: `ok: 110 files from 8 fragment(s) ... 8 frozen paths unchanged since 68ec902f63bf`.
- The reviewer's swap_r4.py, copied and retargeted to an archive of 62181cbe (`scratchpad/w4d-fold4/swap_r4_copy.py`). The archive has no .git, so 39 git-reading tests fail in the baseline. Every mutant was RED beyond that baseline: Y1 +1, Y3 +1, Z1 +3, Z2 +3, Z3 +1, Z4 +4, Z5 +1, Z6 +1, Z7 +2.
- The new fold 4 mutants (`scratchpad/w4d-fold4/swap4.py`, a whole-file swap in the worktree, 134 tests):
  - W4D4-1a, normal_post_spares_template dropped: failures=1, RED.
  - W4D4-1b, the segment test dropped: failures=4, RED.
  - W4D4-2, the wait-point regex clause dropped: failures=3, RED.
  - W4D4-1b "own half only": failures=0, which makes it the named equivalent mutant described next.

**A named equivalent mutant (glitch-f3's ruling, under Javier's delegation: option 2).** W4D4-1b's "own half only" swap binds template_changes to the normal half's examples alone, and it changes no pass/refuse outcome. A template_changes pattern that names no example passes only when its project segment fully matches both render names. A pattern that types a project fails both render names whichever half's examples are searched, so binding against one half's examples or both refuses the same documents. Only the number of messages differs. The binding stays, as the reviewer's fix (b), and this swap is recorded as equivalent, not as a missing test.
