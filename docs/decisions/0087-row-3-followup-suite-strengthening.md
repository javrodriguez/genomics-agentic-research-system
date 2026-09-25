---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/tests/test_r164_exact_bytes.py
  - gars/tests/test_r164_failure_recovery.py
  - gars/tests/test_r164_params_mapping.py
  - gars/tests/test_r164_keyed_lookups.py
  - gars/tests/test_r164_boundaries.py
  - docs/implementation/row_3_followup_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - five sealed mutants survived row 3's first sealed run (M03, M05, M07, M08, M10)
  - a checksum that drops trailing whitespace stays green
  - an interrupted atomic write that deletes the previous artifact stays green
  - exchanged index paths, a hard-coded protocol key or a moved count boundary stay green
---
# Row 3 follow-up: a stronger R-164 suite, by class, test-only

Follows [0086](0086-row-3-first-sealed-run.md), the first sealed run under [0085](0085-row-3-first-run-preregistration.md), for [0050](0050-row-3-test-suite-gate-and-mutants.md)'s suite; 0050, 0085 and 0086 stay as written.
Every ruling here is the lane's, under the owner's standing delegation of 23 Sep 2026; none is in the owner's words.

## Context

Row 3 exits on "≥ 8/10 mutants killed; 7/7 wrapper contracts" (§18, spec line 392), and R-164 (§16.3, spec line 354) names the suite, the whole-suite pre-push gate and the ten sealed mutants.
0086 recorded the first sealed run as graded: 5/10 killed at `2a65dbf`, with M03, M05, M07, M08 and M10 surviving.
That result stands; it is never re-graded, re-run or replaced.

**This suite is survivor-informed.** After 0086 the lane gave the producer the first seal's ten intents and the five surviving diffs.
The seal is spent: the interface forbids tuning a seal against producer tests, and none of these tests can be measured against it.
Because a test written only against those five buys nothing against a new seal, the suite is organised by the fault *class* each survivor belongs to, and each class covers functions that no survivor touched.

**The runner changed before this build, not in it.** The coordinator changed the mutation runner under [0110](0110-row-3-mutation-runner-suite-cap-approval.md) at `2a81999`, this branch's base: the tested tree carries the repository, each mutant is committed inside that throwaway tree before the suite runs, and the whole-suite cap rose to 1800 s while probes and `git` keep 300 s.
This producer did not make that change and touches nothing under `evals/`.

**Provenance.** The producer is a headless Claude Code session on Opus 5.5; the reviewer is a separate, fresh Opus 5.5 context.
Producer and reviewer therefore share a model, a named cost as in [0108](0108-pg-delegated-approval-of-protected-changes.md): two contexts of the same model can share blind spots.
A side effect is that the next sealer, a Codex context, is of a different model family from the producer.
This choice is the coordinator's ruling under the owner's standing delegation of 23 Sep 2026: the Mac's Codex account is at its usage limit, and the second account is kept for seals.

## Decision

**Five new modules under `gars/tests/`, one per class**, discovered by `tests/run_tests.py`'s existing `load_tests`:

1. `test_r164_exact_bytes.py`, exact-bytes identity: `wrapperlib.sha256`, `input_key` (both formulas), `output_evidence` (file and tree), `reference_sha256`, the manifest's input digests, `tools.execution.config_holds` and `claims.evidence_check.artifact_problem`, each against `hashlib` over the fixture's own bytes: empty, a trailing newline, trailing whitespace, CRLF, binary bytes, and chunk boundaries at 1 MiB − 1, 1 MiB and 1 MiB + 1.
2. `test_r164_failure_recovery.py`, failure-path recovery: `workspace.atomic_open` with a fault in the body, at `fsync` and at `os.replace`; `write_params_yaml` interrupted mid-write; `write_status` at `fsync` and `os.replace`; `harvest_cache` with a lost rename and a populated cache; and the generated job guard's three states.
   Each asserts the previous complete bytes and no temporary sibling.
3. `test_r164_params_mapping.py`, parameter mapping: `build_params` of all seven nf-core wrappers and `cmd_prepare` of the three downstream wrappers (manifest params and the generated script's constants), plus the Slurm directives, with pairwise-distinct fixture values so any exchanged field is visible.
4. `test_r164_keyed_lookups.py`, data-keyed lookups: protocols by aligner (directly and through `run_checks`), index parameters by aligner, design columns and input kinds by assay, pipeline checkouts by assay, the legacy-parser export by assay, reference evidence by genome row, and descriptors by backend, each with at least two keys whose content differs.
5. `test_r164_boundaries.py`, boundaries: the spatial count gate at 0, 1, −1, a non-integer, a missing and an extra sample; per-sample byte gates of the spatialvi, scrnaseq and spatial-cluster-count wrappers at zero and one byte; the DE contrast level at one and two samples; the BH tolerance, `p <= q` and `q <= 1` on both sides; the commit-pin length at 6/7 and 40/41; the login-node threshold; and the run-directory refusal.

Class 6, the gate and the guard, gets no new module: `test_pre_push.py` already refuses a planted failure and each empty tree, and `test_guard_hook.py` with `test_protected_paths.py` already refuse each protected shape.

**Anti-gaming rules, which bind these modules.** A test observes behaviour only through imports, CLIs and written artifacts.
No test reads the bytes, text, AST or hash of any file under `gars/_system/` or `gars/02_bioinformatics/`; the only text parsed is a script a wrapper generated into a temporary project.
No `inspect.getsource`, no source AST, no golden source hash, and no branch on the working directory's name, `TMPDIR`'s name, `gars-mutants-`, `GARS_SEALED_MUTANTS_DIR`, tree hashes or Git state.
Lifecycle writers are stubbed only where their own suites cover them (collect's `collect_failure`, `complete_manifest`, `write_status`, `require_collect_config`), so a gate's decision is observed without the executor.

**Budget.** The five modules add 54 tests and about 2.4 s of wall time on this machine (each module 0.3 to 0.7 s), below the 15 s allowance; no sleep, no network, no Docker and no new skip; stdlib only, Python 3.6 grammar, Linux and macOS.

## Known-survivor regression check (development evidence, not a sealed-run score)

Each of the five survivors was planted in a disposable copy of the working tree under `<scratch>`, and only the module meant to kill it was run; M07 no longer applies at `2a81999` and was re-planted by hand with the same behaviour (the two index values exchanged); the other four were applied with `git apply` as the brief gives them.
Each named module failed on a new test, and the unplanted copy was green on all five modules.
Fifteen further plants in functions no survivor touches (per class 1 to 5: 3, 2, 3, 3 and 4) were each watched red the same way.
The table, every command and its summary line are in the [change report](../implementation/row_3_followup_change_report.md).
This is producer-authored evidence; it is not a mutation score and cannot stand in for one.

## What this does not close

- **The exit.** "≥ 8/10 mutants killed" needs the second sealed run, pre-registered in 0088 and recorded in 0089; neither exists at this commit, and no score is claimed.
- **Public claims** need `external_human_seal` evidence.
- **The first seal can never measure again**: 0086 stays 5/10 at `2a65dbf`.
- **The whole suite was not run by the producer.** The lane runs it on a separate node (modes B and C, timed); the added-time figure above is the new modules' own.
- **Classes not covered completely.** Class 2 does not inject faults into `complete_manifest`'s own temporary write or the executor's record writes, and class 4 does not cover the Slurm state map, which needs a scheduler; both are named in the change report.
- **Shared model** between producer and reviewer (see Context).

## Test

`python3 gars/tests/test_r164_exact_bytes.py`, `test_r164_failure_recovery.py`, `test_r164_params_mapping.py`, `test_r164_keyed_lookups.py` and `test_r164_boundaries.py` each print `OK` at this commit.
Each fails on its planted survivor (M03, M05, M07, M08, M10 respectively) and on its own class's plants (P1a–P1c, P2a–P2b, P3a–P3c, P4a–P4c, P5a–P5d in the change report).
`python3 tests/check_counts.py` is clean at 757 tests; `python3 tests/check_contracts.py`, `python3 evals/check_results.py --controls --lexicon` and `python3 tests/test_decision_links_resolve.py` pass after `bash docs/decisions/build_index.sh`.

## Status

standing; test-only change awaiting independent review; Row 3 exit NOT met and not claimed.

## Date

2026-09-25

## Addendum, 2026-09-25: review round 1

The bytes above are unchanged; this addendum records the round-2 fixes for the independent review of `01eed13` ([change report](../implementation/row_3_followup_change_report.md), "Review round 2 fixes").
The review found the suite killed its named functions but did not reach one call further: of its 13 own-class faults outside the coverage map, none went red on the new modules, and classes 2 and 5 had no kill at all (F1, F2, F3).

- **Class 2** now injects faults into the collect-side writers: `wrapperlib.complete_manifest` (at `json.dump`, `fsync`, `os.replace`), the executor's submission record (`executorlib._save_record`: unserialisable value, `fsync`, `os.replace`) and `claims/render_report.py` `main` (at the write and at `os.replace`); each keeps the previous bytes and leaves no temporary sibling.
- **Class 5** adds `gars/tests/test_r164_collect_gates.py`, a module this record's `touches` list does not name because the frontmatter is not edited: it drives `cmd_collect` of the rnaseq, atacseq, chipseq, cutandrun, methylseq, rnaseq-de and scrna-qc-cluster wrappers over a complete layout, with each byte-gated artifact at zero and one byte, each required artifact absent, and each per-sample content check missing a sample. `test_r164_boundaries.py` adds `integrity.check_one` at zero and one byte in every mode, the Slurm `FAILED` exit-code split at `0:0`, `1:0` and `2:0`, and `configure.py contrasts` at zero, one and two levels. The login-node threshold is now pinned to the stages' stated ~10 GB (F5).
- **Class 1** adds `executorlib._sha256` over the shared payload set and the legacy branch of `executorlib.prepared_key`; **class 3** adds `configure.py apply` for the scrnaseq protocol/aligner and the peaks type/gsize/mito keys; **class 4** adds the stage-01 samplesheet format by assay and the scheduler `status_map` lookup, which closes the gap this record named above for the Slurm state map (observed through a stub status command, not a scheduler).

Every one of the reviewer's faults that was in scope (G1a, G1c, G2a, G2b, G3b, G4a, G4b, G5a–G5d) and eight further plants went red in a disposable copy on a new test, and the five survivors still go red on the extended modules; the unplanted copy was green.
The suite rises to 806 tests; the six R-164 modules take about 3.2 s together on the producer's machine and add no skip.
This is producer-authored development evidence, not a mutation score; the exit still needs the second seal (0088, 0089), and nothing in this addendum claims it.

## Addendum, 2026-09-25: review round 2

The bytes above, including the round-1 addendum, are unchanged; this addendum records the round-3 fixes for the independent review of `51b0e47` ([change report](../implementation/row_3_followup_change_report.md), "Review round 3 fixes").

- **Correction.** The round-1 addendum's "eight further plants went red" should read **seven**: the round-2 plant table holds Q3a and Q5a–Q5f, and its count line (18 = 11 reviewer plants + 7 own) was right.
- **Class 2 now reaches the writers' callers.** `gars/tests/test_r164_failure_recovery.py` adds `CallSiteRecoveryTests`: `executorlib.submit` on a definite refusal (a first submission leaves no record; a retry restores the failed record's exact bytes and its lineage), `claims/emit_report.py` `main` with `--from-db` (no exported `.claims-*` snapshot outlives a preflight refusal, a preflight exception, a renderer failure or a failed export), stage 01's `main` with `os.replace` refused at each of the samplesheet, the design table and the design-check record, and stage 00's `finalize` with it refused at `samples.csv` (first run), `files.csv`, `CONTEXT.md` and `HISTORY.md`; each keeps the previous bytes and leaves no sibling.
- **Class 3 reaches stage 01's control columns.** `gars/tests/test_r164_keyed_lookups.py` adds chipseq and cutandrun sheets with crossed controls, so a row's own group and replicate and its control's group and replicate are all distinct.
- **`touches` is not extended.** `gars/tests/test_r164_collect_gates.py` is still missing from this record's frontmatter and so from the index: the frontmatter is not edited, and no other record number is this lane's; the change report asks for a ruling.

The reviewer's four fresh faults in scope (N2a, N2b, N2c, N3a) and seven further plants (R2a–R2e, R3a, R3b) went red in disposable copies on the new tests; the five survivors still go red; the unplanted copy was green.
The suite rises to 813 tests; the six R-164 modules take about 4.1 s together on the producer's machine and add no skip.
This is producer-authored development evidence, not a mutation score; the exit still needs the second seal (0088, 0089), and nothing in this addendum claims it.

## Addendum, 2026-09-25: the lane's extra round (round 4)

The bytes above, including both earlier addenda, are unchanged; this addendum records the fixes for the lane's extra round (`docs/reviews/row3fu_lane_extra_round.md`, E1 and E2; [change report](../implementation/row_3_followup_change_report.md), "Review round 4 fixes").
Every ruling in it is the lane's, under the owner's standing delegation of 23 Sep 2026.

- **Class 2 by principle (E2).** `gars/tests/test_r164_writer_recovery.py` holds one table row per public entry point that writes a recorded state or artifact file, 46 rows over `wrapperlib`, `executorlib`, each wrapper's `check`, `prepare` and `collect`, stages 00, 01 and 03, `configure.py`, `adapt_counts.py` and the hook installer. Each row is driven through its public interface, once cleanly and then with one fault per destination file: the open-for-write refused, a write that lands half its data and fails, the fsync refused, the rename into place refused, the same write fault on a first write, and named helper or copy faults. Every run must surface the fault, keep the destination's prior bytes exactly and leave no file anywhere in the fixture tree. Faults are matched by destination, so a writer that bypasses the atomic helper is caught at its own file. The writers left out, each with its reason, are listed in the change report.
- **The index (E1).** The two modules added after this record's first round are made findable by path in [0111](0111-row-3-followup-suite-index-addendum.md), the plan's reserved spare number, on the lane's ruling; this record's frontmatter is not edited.
- **Owner rulings.** Probes in a scratch folder show that two writers outside the table, the local backend's job record and stage 03's launcher, leave a partial file behind when a write fails. Whether that is a defect is the owner's to rule; the change report states both behaviours, and no test for them is committed.

Twelve class-2 plants in writers that no earlier test named (W1–W12) went red in disposable copies on the new module. So did three earlier call-site plants (N2b, R2b, R2d) and M05. The five survivors still go red on their modules, and the unplanted copy was green on all seven.
The suite rises to 860 tests; the seven R-164 modules take about 8.2 s together on the producer's machine and add no skip.
This is producer-authored development evidence, not a mutation score. The exit still needs the second seal (0088, 0089), and nothing in this addendum claims it.

## Addendum, 2026-09-25: the ruling on the non-atomic writers (round 5)

The bytes above, including the three earlier addenda, are unchanged; this addendum records the ruling on round 4's owner question (`docs/reviews/row3fu_ruling_round5.md`, R1; [change report](../implementation/row_3_followup_change_report.md), "Review round 5 fixes").
The ruling is the coordinator's, under the owner's standing delegation of 23 Sep 2026; it is not the owner's own words.

- **Ruling: option (a).** The four non-atomic writers of recorded state that round 4 found are real R-164 failure-path defects: a torn job record or launcher after a write fault is exactly class 2's shape.
- **Class-2 residuals, untestable as built.** A test would fail on current code, which the test-only rule forbids, so none is fixed here and none is tested around:
  - `executorlib._local_submit`'s `jobs/<pid>.json`, **observed** by a scratch probe: left torn after a write fault once the job has started;
  - `executorlib._analysis_launcher`'s `run/launch-*.sh`, **observed** by a scratch probe: left truncated after a write fault;
  - `_submit_analysis`'s append to `ANALYSIS_SUBMISSIONS`, **code-derived, not probed**: could leave a torn final line;
  - stage 00's project creation, **code-derived, not probed**: could leave a partial project.
- **Where the fix lands.** A later, non-test-only item with its own approval record fixes these writers under `gars/_system/` and then adds their rows to `gars/tests/test_r164_writer_recovery.py`.
- **Reading the second seal.** The second seal's class-2 result is read with these four residuals in mind.

No code or test changed in this round. This is not a mutation score; the exit still needs the second seal (0088, 0089), and nothing in this addendum claims it.

## Addendum, 2026-09-25: review 4, the last round before the seal (round 6)

The bytes above, including the four earlier addenda, are unchanged. This addendum records the round-6 fixes for review 4 (`docs/reviews/row3fu_review4.md`), within the lane's round-6 scope (`docs/reviews/row3fu_round6_scope.md`); see the [change report](../implementation/row_3_followup_change_report.md), "Review round 6 fixes".
Round 6 is the coordinator's ruling, under the owner's standing delegation of 23 Sep 2026; it is not the owner's own words.

- **Class 4 by principle (F1).** `gars/tests/test_r164_keyed_lookups.py` adds `KeyedTablePrincipleTests`. The lookups come from the code: every dict or `get` lookup in scope keyed on a backend, a recorded executor, an assay or an input kind. Each one not already driven is now driven through its public interface, with a non-default key beside a default one whose content differs, and the test asserts the chosen key's content. On the backend side that means `validate`, `submit_argv`, `resources_argv`, stage 03's resubmission poll, its execution evidence, and `status` of an analysis job. On the assay side it means each nf-core wrapper's recorded pipeline, the genome menu's cache folder, `configure apply`'s decisions, the assay menu, and stage 00's `inspect`, `link` and `finalize` and stage 01's path column by input kind. The change report lists the lookups left out, each with its reason.
- **Stage 03's approve and verify writers (F2).** `gars/tests/test_r164_writer_recovery.py` gains rows for `stage03_analysis approve` (`PLAN.md`) and `verify` (`OUTPUTS.tsv`). Each builds its workspace under the row's own folder, as `test_stage03_execution` does. Round 4's "Left out" entry is corrected in the change report: only the `O_EXCL` approval records stay out.
- **Directories (F3) and the half copy (F4).** The tree check now lists every path, directories included, so a leaked temporary directory fails the row. The hook installer's half-copy fault now writes fixed bytes and no longer reads the shipped hook.
- **Owner question.** With directories visible, a failed `stage03_analysis create` leaves its allocated analysis folders behind. The row stops judging those folders, and the change report asks for a ruling.
- **Named residuals, with no new tests (review 4's MINOR and NOTE).** Four one-step-out faults survive the modules the reviewer ran: C1b (the retry approval digest), G1 (the dataset-record migration), G3b (R1 and R2 exchanged in `files.csv`) and G5b (replicate `0` accepted). The round-4 plant driver and probes remain uncommitted scratch material.

Ten plants went red in disposable copies on the new tests: the reviewer's G4, C4a, C4b, X1, X2 and X4, and four of the producer's own (K1–K4).
The suite rises to 874 tests. The seven R-164 modules take about 9.7 s together on the producer's machine and add no skip.
This is producer-authored development evidence, not a mutation score. The exit still needs the second seal (0088, 0089), and nothing in this addendum claims it.

## Addendum, 2026-09-25: the ruling on stage 03's allocated folders (round 7)

The bytes above, including the five earlier addenda, are unchanged; this addendum records the ruling on round 6's owner question (`docs/reviews/row3fu_ruling_round7.md`, R2; [change report](../implementation/row_3_followup_change_report.md), "Review round 7 fixes").
The ruling is the coordinator's, under the owner's standing delegation of 23 Sep 2026, by the precedent of round 5's ruling; it is not the owner's own words.

- **Ruling: option (a).** A failed `stage03_analysis create` that leaves its allocated `03_custom_analysis/01_<slug>/`, `results/` and `scripts/` behind is a real R-164 failure-path defect, the same shape as round 5's stage 00 project creation.
- **A fifth class-2 residual, observed, untestable as built.** Round 6's directory check saw the folders stay on unmodified code when the `PLAN.md` write fails. A test would fail on current code, which the test-only rule forbids, so it is not fixed here and not tested around; the `test_stage03_analysis_create` row of `gars/tests/test_r164_writer_recovery.py` keeps its `creates` list for those four folders, and every other path in its tree is still judged.
- **Where the fix lands.** The same later, non-test-only item that fixes round 5's four writers under `gars/_system/` fixes this one, and then removes the row's `creates` list.
- **Reading the second seal.** The second seal's class-2 result is read with these five residuals in mind.

No code or test changed in this round. This is not a mutation score; the exit still needs the second seal (0088, 0089), and nothing in this addendum claims it.
