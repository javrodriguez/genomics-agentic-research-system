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
