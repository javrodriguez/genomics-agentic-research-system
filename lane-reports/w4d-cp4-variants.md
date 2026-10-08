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
