VERDICT: CHANGES
lane-tag: other
purpose: round-1

Fresh round-1 review of lane t104-mutation-baseline, range 3d278db9..fcf3401d (c33e5e05, fcf3401d), on Mon 26 Oct 2026.
The reviewer was assigned by glitch-45, the Lane-orchestrator.
No code was changed.
Tests ran under /usr/local/bin/python3.12 with TMPDIR in the reviewer's scratch folder, after `mac_slot.py light-ok --tests --work gap-study-r4` said `light ok`.

## Findings

1. MAJOR, class: B. `tests/test_rehearsals.py --witnesses` is a subprocess witness runner of the same shape as the fifteen that were wired, and it was missed.
   It is gated by `checks.d/w7d-rehearsals.txt`.
   Its `run_witnesses` starts only `--mutant <name>` children and counts RED when the bound method fails with an AssertionError that carries its clause.
   It never runs the unmutated file.
   Reviewer probe (`subprocess.run` faked so that every child, unmutated or not, fails `TheRegisterFold.test_folders_match_by_exact_name` with `R5.case`): exit 0, `witness case-collision-admitted -> ... R5.case: RED`, `test_rehearsals witnesses: 1/1 red`, one child and that child a mutant.
   `test_mutation_baseline.WITNESS_RUNNERS` leaves it out, so the new test cannot catch the gap.
   Fix: wire it like test_prereg_order (a whole-file `require_green` with tag `test_rehearsals`), and add it to WITNESS_RUNNERS.

2. MAJOR, class: B. The `tests/test_gemini_adapter.py --generated-mutants` sweep was missed.
   It is gated as 16 shard lines in `checks.d/wave10-merge.txt`.
   It is the same in-process shape as the codex_adapter and labelling sweeps, which were wired: `mutation_sweep` counts a mutant killed when `all_checks` prints any line, and it never checks the unmutated modules first.
   The only control is `TestGeneratedMutants.test_generated_mutants_baseline` in the normal suite.
   test_labelling has the same in-suite test and was wired anyway, so this is an inconsistency, not a choice.
   Reviewer probe (`all_checks` patched to return one line on every module, `mutation_sweep(0, 400)`): `ran 4, killed 3`, and no refusal.
   The one EQUIVALENT entry in that shard showed up as stale, but a shard with no EQUIVALENT entry exits 0 with every mutant counted killed.
   Fix: `require_no_lines` over `all_checks(tg, ga)`, mirroring the labelling sweep, plus a T104InProcessSweeps case.

3. MAJOR, class: B. Five in-process `--witnesses` runners still credit a witness over a check that is already red on the unmutated tree.
   They are `test_codex_agents_off`, `test_codex_patch_reads`, `test_codex_started_file_change`, `test_vendor_bookkeeping` and `test_codex_usage_source`.
   Each one marks a witness red when its bound check returns any problem under the mutant, and none of them runs the check on the unmutated code first.
   The lane did take in-process witness runners into scope, since `test_review_kit` was wired.
   Reviewer probe: with `test_codex_agents_off.CHECKS['table']` red and no mutant applied, `witnesses()` returns `key-dropped table True` and `key-set-true table True`, and the CLI would print `witnesses: 3/3 red` and exit 0.
   Other runners were checked and are already controlled.
   `test_gemini_tool_registry` and `test_gemini_undeclared_args` refuse when the unmutated code is red.
   The `TestWitnesses` classes in codex_adapter, gemini_adapter and labelling assert that each bound check is green on the real module first.
   `test_native_snapshot` is only partly guarded: its "red alone" rule catches a baseline where both locators are red, but not one where a single locator is red.
   Fix: before the loop, run each runner's checks with no mutant applied and refuse through `require_no_lines`; for native_snapshot, run both locators on the real module.
   Then add each runner to the test.

4. MINOR. The claims say more than was built.
   The commit message and the `COPIED.d/t104-mutation-baseline.json` reasons say "every Gap4 mutation runner" and give a complete inventory.
   Findings 1 to 3 show that inventory is short.
   Reword the fragment when the fold lands, and list each runner and the reason it is exempt (for example, "already controlled: walk_plan sweep, endstate, gemini_tool_registry, gemini_undeclared_args, the three TestWitnesses classes").

5. MINOR. The fragment says `test_endstate.py --witnesses` "already ran an unmutated control", and that is only half true.
   Its control does run first, but a NOT CLEAN control only sets `ok = False`.
   Every witness then still runs and prints `RED` lines and the `n/n red` count, and the runner exits 1, not 3.
   That is fail-closed by exit code, but it still counts kills over a red baseline, against the spec's "before counting any mutant".
   Either make it return before the witnesses (or exit 3), or record the exemption as a ruling.

6. NIT. Each witness baseline runs the union of the bound methods in one process, while each mutant child runs one method alone.
   A test that is green in the union but red alone (order or shared-state dependent) would still be credited.
   A baseline that runs once also cannot catch a flaky test.
   Both are recorded as residuals; the conservative direction (a refusal) is what a union red gives, so nothing is over-counted the other way.

7. NIT. In the in-process sweeps (codex_adapter `baseline_lines`, labelling), a check that raises on the unmutated files, instead of returning lines, crashes the runner with a traceback and exit 1, not the one `BASELINE RED` line and exit 3.
   This is still fail-closed.

## What was checked and holds

- Q1, inventory: every file under `evals/gap-study-4/tests` that carries `--witnesses`, `--generated-mutants`, `--mutant`, `--gen-mutant` or `--witness-child` was read.
  The 15 subprocess witness runners and 4 subprocess generated sweeps that the lane names are wired before the first mutant, and so are the codex_adapter and labelling sweeps and the review_kit witnesses.
  `test_walk_plan --generated-mutants` returns 1 before any mutant when its unmutated re-emit fails.
  `test_pipeline.py --mutant` has no runner of its own, and `walk_mutation.py` is the generator, not a runner.
  The gaps are findings 1 to 3 and 5.
- Q2, same selection: for each wired subprocess runner, the baseline argv, cwd and env were compared with its mutant child's.
  The argv is the same file and either the whole file or the union of the bound methods.
  The `--gen-mutant` children get GENERATED_ORDER exactly as the baseline does.
  run_builders uses a scratch cwd for both.
  stub_agents uses the same restricted env for both.
  Real child processes, run unmutated through each runner's own `require_green` call and stopped before any mutant, were all green.
  The results were walk_layout 11 tests, walk_plan 17, prereg_order 10, prereg_status 10, stub_agents 18, holdout_digests 12 and cp8_prep 4, so the argv shapes are valid.
  codex_adapter's `baseline_lines` builds the modules exactly as `mutant_killed` does, both ways.
  labelling's `triple("sm", unmutated)` rebuilds all three modules unmutated.
  review_kit runs the same `TestCase(meth).run` with `MUTATED` empty.
- Q3, the red rule: red means a non-zero exit, no `Ran N` line or N = 0, any FAIL or ERROR block, or a red outcomes line.
  A timeout refuses.
  A skip is green: a skipped bound test also skips under the mutant, and every runner already refuses to credit a skipped method, so this does not lead to over-counting.
  Flakiness is a residual (finding 6).
- Q4, nothing weakened: the diff deletes only three lines.
  One is the HELPERS tuple's closing line, which gains `mutation_baseline.py`.
  The other two are the `mock.patch("subprocess.run", return_value=fake)` lines in ci_job and build_draft `WitnessEvidence.outcome`, now a `side_effect` that answers the unmutated run green and each mutant run with the case's own fake.
  Every expected verdict is unchanged.
  One process ran test_mutation_baseline, test_ci_job, test_build_draft, test_prereg_order, test_prereg_status and test_stub_agents: 148 run, 0 failures, 0 errors, 0 skipped.
  `test_round4.module_problems()` returns `[]`.
- Q5, red first: on a `git archive` of 3d278db9 (`evals/` whole), with the head's `test_mutation_baseline.py` and `mutation_baseline.py` copied in, the result was `Ran 13 tests ... FAILED (failures=42)`.
  The six T104Helper tests pass there, and every runner case fails.
  This matches the builder's "42 failures at 3d278db9".
  With the test file alone, the module fails at import (`No module named 'mutation_baseline'`).
  At the head: 13 run, OK.
- Q6, the COPIED.d claim: `lanes/REVIEW-pf1-gateway-838cfde.md` appears in no COPIED.d fragment at 3d278db9 (`git grep` exit 1).
  Its blob is `8d1c24f020de346147202603cd4b6447ce2025ee` at both 3d278db9 and fcf3401d, so it is byte-identical; its working-tree sha256 is `1b6fc3ec9bdfb58e1f411f83ab876cf2c2965f7da371f9c85b4695e39c174685`.
  Status `new` matches the other REVIEW-pf1-* claims.
  fcf3401d changes only the fragment (+5 lines).
  `copy_manifest.py --check` at the head prints `ok: 793 files from 85 fragment(s)`, exit 0.

## Not run

- No full `test_round4.py` battery, and no real `--witnesses` or `--generated-mutants` run of any runner on the Mac; those runs are athena's.
  Nothing on athena, freeze/r4-20261021 or the rehearsal-records clone was touched.
