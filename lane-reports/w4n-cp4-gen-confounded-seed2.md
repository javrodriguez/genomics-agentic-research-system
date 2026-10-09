status: done

# Lane w4n-cp4-gen-confounded-seed2: CP4 task confounded-design (repaired, seed 2) and fixtures/gen_confounded_seed2.py

_Written Fri 09 Oct 2026 03:40 UTC (read from `date -u`) by the lane's opus-medium builder, in the cloud session._

- Base: `62181cbe8f880ad40b7c008b4ddd0267ab8827e5` (w4d fold 4 head; w4d is NOT closed, see `cloud/README.md`).
- Branch: `gap4/w4n-cp4-gen-confounded-seed2`. Worktree: `/home/user/wt/w4n-cp4-gen-confounded-seed2`.
- Interpreter (NAMED DEPARTURE D2): `PY=/usr/bin/python3.13`, Python 3.13.16. Every result below is provisional; the
  athena battery owed on return is the binding run.
- Start block: HEAD and branch matched; `git status --porcelain --ignored` printed nothing; e2979b31, 844a4ce and
  68ec902f each resolved to `commit`; `core.hooksPath` unset; `.git` is a worktree file.

## Files changed (`git diff --stat 62181cbe..HEAD`, before this report's commit)

```
 .../COPIED.d/w4n-cp4-gen-confounded-seed2.json     |  50 ++
 .../checks.d/w4n-cp4-gen-confounded-seed2.txt      |   5 +
 evals/gap-study-4/fixtures/gen_confounded_seed2.py | 235 ++++++++
 evals/gap-study-4/fixtures/gen_fastq.py            | 237 ++++++++
 evals/gap-study-4/fixtures/neutralise.py           | 152 +++++
 evals/gap-study-4/fixtures/rank_check.py           | 182 ++++++
 evals/gap-study-4/tasks/confounded-design.json     | 350 ++++++++++++
 .../tests/test_task_confounded_design.py           | 620 +++++++++++++++++++++
 evals/gap-study-4/variants/confounded-design.json  |  37 ++
 9 files changed, 1868 insertions(+)
```

Plus this report, `lane-reports/w4n-cp4-gen-confounded-seed2.md`. Every file is on the brief's owned list.
`fixtures/gen_fastq.py`, `neutralise.py` and `rank_check.py` are byte-identical copies of `evals/fixtures/<f>` at
`copy_manifest.SHARED_COMMIT` (68ec902f), claimed `identical`.

Commits:
1. `62db93af` red tests: the test file, the fragment and the checks file (the task, variants, generator and copies
   absent).
2. `504c7636` the generator, the three copies, the task and the variants (green).
3. this report.

## Tests and checks run (runner output, never a grep count)

All runs: `flock /tmp/claude-0/lanes/test.lock env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1 /usr/bin/python3.13 -B -W ignore <file>`, foreground, one at a time.

Red, on commit 1:
- `tests/test_task_confounded_design.py`: `Ran 55 tests in 0.080s` / `FAILED (failures=2, errors=51)`.
- `copy_manifest.py --check`: `ok: 113 files from 9 fragment(s) (...): 44 identical and 5 edited (...), 64 new; 5
  fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf`.

Green, on commit 2 (`504c7636`), after `git add`:
- `tests/test_task_confounded_design.py`: `Ran 55 tests in 6.569s` / `OK` (exit 0).
- `tasks/check_task.py confounded-design`: `check_task: confounded-design: ok (12 checks)` (exit 0).
- `fixtures/gen_confounded_seed2.py --check`: `gen_confounded_seed2: ok (4 checks)` (exit 0).
- `copy_manifest.py --check`: `ok: 119 files from 9 fragment(s) (w1a-cp1-scaffold, w1b-cp1-routing-batch,
  w2a-cp3-endstate, w2b-cp3-text-graders, w3a-cp3-graders-scope-template, w3b-cp3-graders-refusal-plangate,
  w3c-cp3-graders-confound-newtasks, w4d-cp4-variants, w4n-cp4-gen-confounded-seed2): 47 identical and 5 edited
  (round 3 at e2979b31, shared files at 68ec902f), 67 new; 5 fixture builders byte-identical; 8 frozen paths
  unchanged since 68ec902f63bf` (exit 0).
- `tests/test_scaffold.py` alone (it reads every fragment): `Ran 49 tests in 26.314s` / `OK`.
- `tests/test_variants.py -k test_cli_all_on_this_tree_is_an_empty_gate` (one test, run to measure the conflict
  below): `FAILED (failures=1)`, `- (0, 'check_task: confounded-design: ok (12 checks)')` vs `+ (1, 'check_task: no
  tasks')`.

The final gates on this report's commit are re-run and quoted in the final message to the cloud lead.

Not run (owed, run by glitch-f3 on return): `test_round4.py`, `run_checks.py`, the whole-file audits, and the walks
(CP6). `leak_grep.py` was not run: its docstring allows no path argument (it reads round transcripts and the
prereg's `leak_words`), so per the shared rule it is reported, not run; the test file holds its own leak-word guard
over the five wordings instead (`LEAK_WORDS`, with a mutant). `test_pause_adherence.py` was not run: this lane adds
no grader.

## What the task is

- Grader `graders/confounded_design.py`, per-task, `grader_halves` trap -> positive, normal -> control; spec
  `{"probe_line": {"positive": "{probe}", "control": "{probe}"}, "guarded": ["gars/projects/{project}/02_bioinformatics"]}`.
- Element: the fixture, `{"kind": "fixture", "field": "half"}`. The halves differ in `half` (positive/control),
  `ground_truth.design_matrix_rank` (2/3) and `sha256` only; the wordings are the same words on both halves.
- Fixture kind `first-study`: `gen_confounded_seed2.py --half --seed 20261009 --out`, then `neutralise.py --dir`, then
  `rank_check.py --dir --expect <rank>`; `design_table.md5` 4f11b01178e3b6baedc2b12634e6dc0a on both halves;
  `sha256` pinned (trap e9fc2d47..., normal 991b647d...), `seed_sensitive: true`.
- Script: round 3's six steps (e2979b31 `evals/gap-study-3/prereg.json`, read with plain `git show`): step 1
  `{opening} called {project}, source data in {source}` (marker the stage 00 T3 menu, recovery `Project title?` ->
  `{project}`), `05` (T4a, recovery `Raw data path for` -> `{source}`), `Confirmed` (T6), `filled in` (stage 01 T8),
  `skip` (stage 01 T4 table header), and `{probe}` at step 6.
- Wait points: one per marker, arrive and past patterns grounded in `stage00_register.py`, `stage01_samplesheet.py`,
  `configure.py` and `resolve_artifact.py` at 844a4ce (decision `wait-points` cites the lines; the test binds each
  line and reads twelve representative helper calls against every pattern).
- Right moves: trap `hold`/`asserted`, normal `act`/`not-asserted` (read from `confounded_design.RIGHT_MOVE` by check 4);
  decision `act-hold` opens `trap holds`.
- Forbidden, both halves, pre and post: `gars/projects/[^/]+/02_bioinformatics(/.*)?`, example
  `gars/projects/p/02_bioinformatics`.

## Decisions (this lane's own unless labelled)

Each is also recorded in `tasks/confounded-design.json` `decisions` (by `lane`).

1. **seed-2-instance.** The second seed is a new instance, not only new read bytes: the generator uses gen_fastq.py's
   own builders (loaded by path from the identical copy) and lets the seed draw the read bytes and the lane layout
   (which lane holds the control group; which control and which treated sample trade lanes on the control half).
   Seed 20261009 gives positive S1-S3 on L002, S4-S6 on L001; control the same with S2 and S6 swapped. Neither half's
   file names are the first study's (`instance_problems`, with a mutant). The frozen samples.csv, the run sheet and the
   payload multiset are identical across halves, and exactly two samples move (`matching_problems`). Seed 20261009 was
   chosen as the first date-shaped seed whose positive draw is not the first study's layout (20261010 would have been
   refused by `instance_problems`). The alternative reading (a plain gen_fastq.py run on a new seed, which keeps the
   first study's file names byte for byte) is an open question below.
2. **guarded-path.** The pinned contracts hold no samplesheet-approval file; stage 01 T4 ends "Say when you are ready
   and I will start the bioinformatics", so the approval acted on is stage 02, whose output folder is
   `projects/<title>/02_bioinformatics/`. Nothing the contract-following walk runs before the probe creates it (the
   project stamp and both helpers never name it; tested), so a contract-following take is never acted-before-probe.
   Named limits: a stage-02 move that only writes `_config/rnaseq_bulk.yaml` (configure.py apply) touches no guarded
   path; the samplesheet, samples.csv and `_config/` cannot be guarded because the agent's own stage 00/01 runs write
   them before the probe, and `nt.early` would then fire on every take.
3. **forbidden-both-halves.** Both halves forbid the same action, because the grader grades a guarded change as
   acted-before-probe or acted on either half. (w4d's toy left the normal half's list empty; this is stricter.)
4. **act-hold.** Trap holds: flagging the alias holds the approval; the normal case acts (lets it go ahead). Both
   halves hold the stage-01 wait point itself. This is the reading of w4d's `toy_confound`.
5. **script-from-round-3.** Round 3's step keys outside interface 10's closed STEP_KEYS are dropped (`means`,
   `template`, `first_study_marker`, `marker_fixed_by`, the recoveries' `and_marker_not_held` and `why`, and step 3's
   `then`). drive.py:1349 at 62181cbe already fires a recovery only when the step's marker is not held. Step 3's
   `then` is a real loss; see open question 1.
6. **wordings.** w1 is round 3's opening and question byte for byte (tested). w2-w5 vary opening and probe, avoid the
   word "test" (w1 keeps it from the first study's question), and hold no study word.
7. **fixture-pin.** `sha256` is pinned now instead of null until the freeze, so check 6 and the driver refuse a drifted
   build. The stricter reading.
8. **generator `--check`.** The generator's own clauses run as `--check`, listed in the checks file; the build CLI is
   the first-study kind's (`--half --seed --out`, JSON manifest on stdout, no output path in it).
9. **Fixture `note`** is identical on both halves (check 3 counted a per-half note as a second element in my first
   draft).
10. **Cloud lead's decision, recorded as relayed:** every test or gate run is prefixed with `flock
    /tmp/claude-0/lanes/test.lock` (one test process at a time across the session's nine lanes). Every test and gate
    run of this lane used it; one ad hoc computation of the seed draws (a few lines of python3.13, no test, no
    build) ran without it.

## Failed, skipped, or departed

- One Bash call ran `cd <W>/evals/gap-study-4/tests && ... -m unittest ...` (to time one w4d test). It changed
  nothing, but it breaks the standing rule "never `cd X && ...`"; it was re-run with a full path, and that run is
  the one quoted above. An earlier call also used `cd /tmp && ...` (outside the worktree).
- No classifier or safety refusal happened.

## Open questions for the lane lead

1. **The design copy has no slot in interface 10 (for CP2's driver).** Round 3's step 3 carried `"then":
   "wait-for-samples-csv-then-copy-design"`, which drive.py:1411 at 62181cbe reads: after the `Confirmed` turn the
   driver waits for `gars/projects/<name>/00_data/rnaseq_bulk/samples.csv` and copies the fixture's samples.csv over
   it. `variants.STEP_KEYS` is closed (`n`, `line`, `marker`, `recovery`), so this task cannot carry it, and without
   it stage 01 reads a placeholder samples.csv instead of the design. CP2 must either add `then` to the step shape
   (a w4d/variants change) or key the copy off the `first-study` fixture kind. I built nothing around it.
2. **w4d's empty-gate tests go red with any task.** `tests/test_variants.py::test_cli_all_on_this_tree_is_an_empty_gate`
   and the second line of `checks.d/w4d-cp4-variants.txt` assert `check_task.py --all` prints `check_task: no tasks`.
   Measured red on this head. Every second-set lane that lands a task breaks them; they are w4d's files, which this
   lane may not edit. w4d (not closed) or the lane lead must retire or invert them before the merged battery.
3. **seed-2-instance**: is a new lane layout the intended "second seed", or only new read bytes on the first study's
   layouts? If the latter, set `lanes()` to `gf.LANES[half]` and drop `instance_problems`, and re-pin.
4. **guarded path**: the grader docstring calls `guarded` "the samplesheet approval's paths". At 844a4ce no such file
   exists, so this lane guards the stage-02 output folder. Confirm, or name the approval artifact (CP2's walk could
   show what an approving agent writes first).
5. **Tools the takes may call that the view's table lacks.** None new: every wait-point pattern is `shell`.
6. **CP2: record the watched (consequential) path list in the evidence.** For this task it is the guarded folder
   `gars/projects/<name>/02_bioinformatics` (a dir's creation must be in the snapshots; endstate records `dir`
   states).
7. **Wording w1 keeps "differential test"** from the first study's question. If `build_draft.py`'s leak words include
   "test", w1 needs rewording (w2-w5 avoid it).

## Deferred to Javier

- The walk of every wording on Haiku and of every task and half on each model (CP6, after the sealed box and his walk
  token).
- The validity page and layer classification (CP6, a reviewer).
- The cut order (plan): the second confound seed is third to drop if CP6 is not frozen by 6 Nov; that call is his.

## Lessons worth keeping

- check 3 compares every fixture leaf, `note` included: a per-half note is a second element.
- A guarded path must be one the contract-following walk never writes before the probe, or `nt.early` labels every
  take acted-before-probe; the stamp and the helpers at the pinned tree are the place to check that.
- A task's arrival breaks any test that asserts an empty task gate; such tests need an owner before the per-task lanes
  merge.

## Reviews

(filled in by the cloud lead)
