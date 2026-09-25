---
date: 2026-09-25
status: standing
kind: decision
touches:
  - evals/bench.py
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/_system/stage00_register.py
  - gars/_system/tools/registry.json
  - gars/00_initialize_project/CONTEXT.md
  - gars/_references/manifest_schema.json
  - gars/_system/manifest_check.py
  - gars/_system/wrapperlib.py
  - gars/_system/executorlib.py
  - gars/_system/resolve_artifact.py
  - gars/_references/artifact_types.md
  - gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py
  - gars/_system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py
  - gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py
  - gars/_system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py
  - gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py
  - gars/_system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py
  - gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py
  - gars/_system/wrappers/spatial-cluster-count/spatial_cluster_count.py
  - gars/_templates/config/nextflow.slurm.config
  - gars/_references/genomes.md
  - gars/_system/configure.py
  - gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md
  - gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md
  - gars/_references/tolerances.yaml
symptoms:
  - row 6's evaluation-code, guard, settings, registry, reference, template, system, wrapper and stage-contract changes are protected paths with no owner approval record
  - 0095, 0096 and 0097 reserve 0099 for the owner's approval of the protected changes and the confirmation of the lane's D-16 answer at merge; the owner delegated it on 23 September 2026
---
# 0099 — Row 6: delegated approval of protected changes

Addendum to [0095](0095-row-6-manifest-groups-and-applicability.md), [0096](0096-row-6-collect-time-manifest-r042.md) and [0097](0097-row-6-reproduction-and-tolerances.md), which stay byte-identical, including their dated addenda.
Every file this record touches is a protected path (R-094, spec §9.3), or evaluation code that 0095's R8 routes to this record, so it needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by the lane under that delegation and labelled as such; it is not in the owner's words.
Its shape follows row 7's [0079](0079-row-7-delegated-approval-of-protected-additions.md), which follows row 12's [0066](0066-row-12-owner-approval-of-protected-changes.md).
The changes themselves arrive with row 6's merge; this commit adds only this record and the regenerated decision index.

## Context

Row 6 (manifest completeness and reproduction) was built on branch `build/gars-row-6-manifest` from public main `2f891d8` in ten producer commits, `bcc50b5` to `9e55220`: the R8 reader change, Step A (the manifest), the Step B blocker report, the Step B build with R9, the R10 and R11 ruling rounds, a review-fix round, the R12 and R13 ruling round, a round-3 review-fix round, and the R14 verification round.
The merge candidate is `6efec97`.
The owner's words for the row, quoted in 0095 and 0097, were: "GARS row 6 (manifest completeness + reproduction) on the Mac Codex queue, decisions 0095-0099".
The owner's D-9 answer, quoted in 0097, was: "D-9: yes, the n = 2 is my two Slurm re-runs; the fixture 2/2 is the instrument's self-test".
D-9 is the owner's own word and needs no confirmation here.

The owner's delegation, typed in the row 6 working session on 23 September 2026, in the owner's words, verbatim:

> I follow your recommendations. I  delegate every decision to you for the work happening in this session, use your best judgement. I don't want to intervene, we already have plans, specs, etc, just get things done, use your best judgment, you know all the context, i dont, you are capable of taking the paths that best fit our goals. Coordinate with the other sessions if you have to, you can agree the best route together.

Every other sentence in this record is the lane's, under that delegation.
0095, 0096 and 0097 each keep the protected-path approval out of the producer's hands and reserve it, with the confirmation of the lane's D-16 answer, for record 0099 at merge.
The row was reviewed in fresh contexts: review round 2's findings F1 to F11 were answered in the fix round and in rulings R12 and R13, and round-2 NOTEs N1 to N4 were answered in the round-3 fix round, as the dated addenda and [the change report](../implementation/row_6_change_report.md) record.
The round-3 review (Claude Code, fresh context, on `ce67841`) was APPROVE, with one new NOTE, N5; its SHA-256 is `fe4caf39d32ca763006ed3d1ef76baa6f0e3389479144cc29d0140dc24baeebc`.
After round 3 the lane's own independent verification found two defects, D1 (a relative-path prepare made every replay a false non-match) and D2 (failure-path manifest completion was tested for one wrapper of ten); the lane ruled R14 on them, and the producer fixed both in `9e55220`, recorded in the dated R14 addenda of 0096 and 0097.
The final review (round 4, on `9e55220`) was APPROVE, with 0 BLOCKER, 0 MAJOR and 0 MINOR findings and two NOTEs: N5 carried from round 3, and the new N6.
Its SHA-256 is `d1482a0a021cf733cab0907a4427d01173bca23ac9862e4fa27f6b2512fb13f4`; both reviews are kept outside the repository.

## Decision

The lane, under the owner's 23 September 2026 delegation, approves the following protected changes as they stand at `9e55220`, merged as `6efec97`, on 2026-09-25.
Only the quoted sentences in this record are the owner's words.
Each file's approved scope was checked against `git diff 2f891d8 9e55220`, and no file's diff exceeds the scope its ruling allowed.

1. **The evaluation reader (R8).** The two-line reader change routed here by 0095's R8.
   - `evals/bench.py`: exactly two lines in `assert_registry`: `assertIn(len(row), (3, 5))` replaces the three-column equality, and the row unpacks `row[:3]`; no pin, threshold or other evaluation code changes.
2. **The guard and its settings mirror (R-060 and R12).** The machine-owned dataset row and the whole stage-02 pipeline output tree become read-only to session tools.
   - `gars/_system/guard_hook.py`: exactly three added `READ_ONLY` lines: `projects/*/00_data/dataset.tsv` (R-060, Step A), `projects/*/02_bioinformatics/*/run/*` and `projects/*/02_bioinformatics/*/run/**/*` (R12); no other guard byte changes, and the refusal message is unchanged (F8 declined).
   - `gars/.claude/settings.json`: exactly six added lines: the `Edit` and `Write` deny pair for `dataset.tsv` and the two deny pairs for the two run-tree patterns.
3. **Finalize classifies the dataset (R-060).** Finalize requires a data class and a purpose, records an agreement reference, and writes the machine-owned `00_data/dataset.tsv` once.
   - `gars/_system/stage00_register.py`: `finalize` only: `--data-class`, `--purpose` and `--agreement-ref` (default `none`), the named refusals `data_class_required`, `purpose_required`, `agreement_ref_required` and `dataset_classification_locked`, and a single atomic mode-0444 write of `dataset.tsv`; same-value re-finalize leaves it untouched.
   - `gars/_system/tools/registry.json`: the `finalize` entry only: the three new CLI flags and their input-schema properties, with the three data classes and five purposes as enums; no other entry changes.
   - `gars/00_initialize_project/CONTEXT.md`: one Definitions paragraph naming the new flags and four refusals, and the finalize command line gaining the three flags.
4. **The manifest schema and checker (R-084 to R-086, D-16, R9, R13).** The eighteen §8.1 groups, their classes, predicates and sentinels as in 0095's table.
   - `gars/_references/manifest_schema.json` (new): the eighteen groups of 0095's D-16 table, predicates reading only `predicate_facts`, the four named sentinels, the model-provider prefix table and the wrapper list; group 3 carries `execution_config` (R9) and group 11 carries `agreement_ref` (R13), and nothing else departs from the table.
   - `gars/_system/manifest_check.py` (new): the fail-closed grader: facts validated and predicates evaluated before group contents, applicable-required completeness, group 3's execution-config entries (R9) and group 11's agreement-reference check mirroring finalize's value rules (R13).
5. **The collect-time manifest writer and the Nextflow wrappers (R-067, R-068, R-042; R2, R3, R5, R9, R13, R14a).** Collect extends the prepare manifest atomically before STATUS, and OUTPUTS carries per-file hashes and classes.
   - `gars/_system/wrapperlib.py`: prepare facts including `agreement_ref` from the dataset row (R13) and the hash-bound `execution_config` evidence (R9); `complete_manifest` for success and failure; the collect failure token `FAILED` (R2); output file and `sha256-tree:` hashing and the five-column OUTPUTS rewrite (R5); the COMPLETE gate's hash recheck; the registry-authoritative reference hash comparison and `reference_hash_mismatch` (R-090); no change to the key formula, `check_pipeline` or existing prepare keys.
   - `gars/_system/executorlib.py`: the fixed Slurm `resources_argv` (`sacct` Elapsed, MaxRSS, AllocCPUS, with the batch step's MaxRSS), an empty local one, both fixed by the backend enum; the approval id and hash on a destructive retry; `completed_at` recorded once.
   - `gars/_system/resolve_artifact.py`: `read_outputs` accepts exactly three or five columns, routes on the first three, and returns the hash and class of a five-column row.
   - `gars/_references/artifact_types.md`: the OUTPUTS.tsv description becomes five columns with the file and tree hash forms and `durable`/`intermediate`; legacy three-column indexes stay readable.
   - The seven Nextflow wrappers (`nfcore_atacseq_wrapper.py`, `nfcore_chipseq_wrapper.py`, `nfcore_cutandrun_wrapper.py`, `nfcore_methylseq_wrapper.py`, `nfcore_rnaseq_wrapper.py`, `nfcore_scrnaseq_wrapper.py`, `nfcore_spatialvi_wrapper.py`): each two collect lines: `collect_failure` receives `args.model` (R1), and `complete_manifest(substage, args.model, "COMPLETE")` runs before STATUS.
   - In six of them, R14a's params expressions only, in `build_params`: every path-valued parameter wrapped in `str(Path(...).resolve())`, or `.resolve()` on an existing `Path`. That covers `fasta` in all six, plus `gtf` (atacseq, chipseq, cutandrun, rnaseq, scrnaseq), `blacklist` (atacseq, chipseq, cutandrun), `spikein_fasta` and `spikein_bowtie2` (cutandrun), and the derived index paths (atacseq, chipseq, rnaseq, scrnaseq). The same list feeds `params.yaml`, as N6 notes. `nfcore_spatialvi_wrapper.py` is unchanged by R14, because its only path parameters, `input` and `outdir`, were already resolved.
6. **The Nextflow template records execution evidence (R6).**
   - `gars/_templates/config/nextflow.slurm.config`: appended `trace`, `report` and `timeline` blocks with fixed relative `pipeline_info/` filenames and one fixed trace field list; existing projects migrate manually as 0096 describes, with no new verb.
7. **Reference hashes (R-090, hash half).**
   - `gars/_references/genomes.md`: one appended ID-keyed hash table with a single GRCh38 row, Ensembl release 116, both hashes `UNKNOWN`; the identity table and its GRCh38 row stay byte-identical.
   - `gars/_system/configure.py`: `read_genomes` also parses the hash table, and `apply` writes `fasta_sha256` and `gtf_sha256` into the assay YAML, `UNKNOWN` when the registry has none.
   - The ten stage-02 sub-stage contracts (atacseq, chipseq, cutandrun, methylseq, rnaseq wrapper, rnaseq-de, scrnaseq wrapper, scrna-qc-cluster, spatialvi wrapper, spatial-cluster-count `CONTEXT.md`): each one Definitions entry for `reference_hash_mismatch`.
8. **The local wrappers: seeds, versions, consumed inputs and path identity (R4, R10, R11, R14a).**
   - `gars/_system/wrappers/rnaseq-de/rnaseq_de.py`: `RANDOM_SEED = 0` passed to PCA (R4), a generated `versions.json`, the canonical-design refusal `design_not_canonical` before any write (R11), the `counts` and `design` params recorded as resolved absolute paths (R14a), and the two collect lines of item 5.
   - `gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py`: `RANDOM_SEED = 0` passed to PCA, neighbors, UMAP and Leiden (R4), a generated `versions.json`, the samplesheet recorded as a prepare input (R10), the `h5ad` param recorded resolved (R14a), and the two collect lines of item 5.
   - `gars/_system/wrappers/spatial-cluster-count/spatial_cluster_count.py`: a generated `versions.json` (Python and anndata), the `h5ad` param recorded resolved (R14a), and the two collect lines of item 5; no seed, as its code path has no RNG.
   - `gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md`: beyond item 7's entry, one failure-vocabulary entry for `design_not_canonical` (R11).
9. **The pre-committed tolerances (0097).**
   - `gars/_references/tolerances.yaml` (new): one entry, `rerun-fixture` / `fixture_numeric`, `numeric_tolerance` by `max_absolute_error` at 0.000001, with its cause and second-re-run evidence; no real wrapper receives an entry.

### Confirmations under the delegation

Each line below is confirmed by the lane under the owner's delegation; none is the owner's word.

- **D-16**, 0095's group table: the eighteen groups, their classes and applicability predicates, completeness as present over applicable required groups, and no optional group: confirmed by the lane under the owner's delegation.
- **The lane's defaults** recorded with D-16 in 0095: the predicate rule (predicates read only `predicate_facts`; missing or out-of-vocabulary facts are errors), the four named sentinels, `fixture` as the fifth purpose, `none` as the default agreement reference, the registry-authoritative reference hash with `UNKNOWN` as incomplete, and F3's correction of the `design_record` source in 0095's round-2 addendum: confirmed by the lane under the owner's delegation.
- **R1** (collect supplies group 18's `agent_model` from `--model`; no prepare change): recorded in 0095, "The lane's R1–R8 rulings" item 1; accepted as given in the change report's Step A: confirmed by the lane under the owner's delegation.
- **R2** (the collect gate's current state is supplied before STATUS): 0095 item 2; change report Step A expectation table: confirmed by the lane under the owner's delegation.
- **R3** (backend from the executor's recorded submission; a mismatch leaves group 11 incomplete): 0095 item 3; accepted as given in the change report's Step A: confirmed by the lane under the owner's delegation.
- **R4** (seed 0 to every seed-capable local stochastic call; no-seed APIs named with determinism unknown): 0095 item 4; 0096's R-042 table: confirmed by the lane under the owner's delegation.
- **R5** (directory outputs hashed as `sha256-tree:` over the sorted regular-member listing; symlinks named, never traversed): 0095 item 5; 0096's R-042 table: confirmed by the lane under the owner's delegation.
- **R6** (no re-seed verb; manual template-copy migration): 0095 item 6; 0096 "Template grammar and manual migration"; change report Step A expectation table: confirmed by the lane under the owner's delegation.
- **R7** (disposable synthetic pipeline checkouts; only the test process repoints spatialvi's pin): 0095 item 7; accepted as given in the change report's Step A: confirmed by the lane under the owner's delegation.
- **R8** (option A: the two-line `evals/bench.py` reader change as its own first commit): 0095 item 8; 0096; change report "Answer to item 1: R8": confirmed by the lane under the owner's delegation.
- **R9** (execution configuration becomes immutable, hash-bound prepare evidence; group 3 gains `execution_config`): 0097 addendum "step B"; change report "B-1 answered (R9)": confirmed by the lane under the owner's delegation.
- **R10** (scrna-qc-cluster records its consumed samplesheet): 0097 addendum "step B's ruling round b"; change report "B-2 answered (R10)": confirmed by the lane under the owner's delegation.
- **R11** (rnaseq-de prepare requires the canonical project design): 0097 addendum "step B's ruling round b2"; change report "B-3 answered (R11)": confirmed by the lane under the owner's delegation.
- **R12** (the two run-tree `READ_ONLY` patterns and their four settings denies): 0095 addendum "ruling answered on fix round 2"; 0096 addendum of the same name; change report "F1 answered (R12)": confirmed by the lane under the owner's delegation.
- **R13** (group 11 requires `agreement_ref` captured at prepare; replay registers through real finalize): 0095 and 0097 addenda "ruling answered on fix round 2"; 0096 addendum of the same name; change report "F9 answered (R13)": confirmed by the lane under the owner's delegation.
- **R14** (R14a: every path-valued wrapper parameter recorded as its resolved absolute path at the source, with rerun_check's equality test unchanged, which changes the key of a new relative-path or symlink prepare and supersedes R11's claim of unchanged keys for every accepted spelling; R14b: the FAILED collect path driven for all ten wrappers on both backends, with group 15 present and prepare keys unchanged): recorded in the 0096 and 0097 addenda "verification fixes (R14)" and in the change report's "Verification fixes (R14)": confirmed by the lane under the owner's delegation.
- **F8 declined** (no dataset-specific guard refusal message; the generic refusal still names the protected path): 0095 addendum "ruling answered on fix round 2"; change report "F8 disposition": confirmed by the lane under the owner's delegation.

## What this does not close

Copied from 0095 at HEAD:

- NOT met: real-cluster trace and sacct. This step measures synthetic fixtures; row 13 measures real execution.
- NOT met: GRCh38 hashes, UNKNOWN until the owner hashes the files where they live.
- NOT met: R-062 venue refusal and the remainder of §6.1's record, including permitted_backends, provider exposure, retention and expiry: row 8, D-3.
- NOT met: R-087/R-088 registry validation.
- NOT met: §8.3 test_reference_pairing.py; it compares claims from row 7's table.
- NOT met: R-069 artifact liveness.
- NOT met: report methods and reproduction sections; row 7's renderer reads these fields in later wiring.
- NOT met: stage03_analysis.py and create_bioinformatics_skill.py still write three-column OUTPUTS.tsv without complete_manifest. Their manifests grade incomplete and count against §17's "every completed run".
- NOT met: protection from processes outside the guarded session. A human shell or unseen script can chmod and rewrite dataset.tsv. Source protection, reported-value truth and externally forged manifests have the threat-model limits stated above.
- NOT met: the pilot-1 measurement, and §17's real-run completeness measurement.
- NOT met: Step B reproduction, n = 2, tolerances and artifact comparison modes.
- NOT met: benchmark task source-pin validation after the authorized changes. Row 2 owns re-pinning at its run commit; benchmarks/ remains untouched.

Copied from 0097 at HEAD:

- The owner's two real Slurm re-runs and the whole row's exit remain unmeasured.
- §8.4's second backend, §17's ≥ 4/5 on test data and the external pilot-1 re-run are NOT met.
- Real-wrapper re-execution is NOT met: the suite has no bio environment. Its real-wrapper checks exercise prepare and synthetic collect on both fixture backends, with separate real local execution for the instrument self-test.
- Model-mediated steps compared as typed claim-set equality need row 7's claims.
- README's manifest/re-run evidence row stays unmeasured. Step A's other residuals remain; no real-run manifest completeness or benchmark-pin result is promoted.

Added by this record:

- **Review round 3, NOTE N5, carried open by round 4.** The GRCh38 hash rows in `genomes.md` stay `UNKNOWN`. The owner commits the site's `fasta_sha256` and `gtf_sha256` rows, hashed where the files live, and any other `_references` edit, before preparing the original run that 0098 will replay. An uncommitted edit makes replay refuse, and committing it after the original's prepare moves HEAD away from that original's `gars_commit`, so it can no longer be replayed.
- **R14's owner obligation (review round 4).** A completed original prepared under the old code with relative or symlinked paths cannot be replayed. The 0098 original must be prepared and completed after this merge, as the R14 addenda of 0096 and 0097 state.
- **Review round 4, NOTE N6 (a documentation follow-up).** 0096's R14 addendum describes R14a only as how path parameters are recorded, and discloses only the key change. In the six changed nf-core wrappers the same list feeds `params.yaml`, so the pipeline's own invocation changes too: a relative reference path now reaches Nextflow as the file preflight checked and hashed, which fixes a latent mismatch, and a symlinked reference or index is passed by its target path. The next append to 0096 adds that sentence. No code change is needed.
- **Merge interaction with row 8 step A (named).** Row 6 merged onto public main `ef5c8af`, which carries row 8 step A's Benjamini-Hochberg gate in rnaseq-de's collect (`check_table`, "padj differs from BH"). Row 6's tests predate that gate, and their one-gene DE fixture wrote `pvalue` 0.1 with `padj` 0.2, so at the first merge candidate `5f393e9` 15 row 6 tests failed on that refusal: 11 in `test_manifest_groups.py` and 4 in `test_rerun_check.py`.
  The lane resolved it under the owner's delegation as a test-fixture-only merge commit, `049c0c3`: the fixture's `padj` is 0.1, which is BH(`pvalue`) for one tested gene. No production file changed, and the BH gate is byte-identical to `ef5c8af`'s. Restoring `padj` 0.2 brought back the same 15 failures. A fresh-context review of that commit alone was APPROVE, with 0 BLOCKER and 0 MAJOR findings.
  Its one MINOR finding predates the fix and stays open as a follow-up: `test_failure_collect_preserves_prepare_facts` asserts only the failure class, and since row 8 step A two checks refuse its malformed table. The change report's section "Merge interaction with row 8 step A (at merge)" records the details.
- **Regenerating a gap study on current GARS.** `evals/gap-study-2/controls/run_controls.py` and `fixtures/gen_project.py` call `finalize` without row 6's required `--data-class` and `--purpose`, so regenerating those study projects on post-row-6 GARS is refused (R-060). CI is unaffected, because the gap-study jobs check out their own pinned refs. Published study instruments are never amended.
- **Row 2's stale task pins.** The benchmark task pins are stale against the contracts this row changes, and `python3 evals/bench.py validate` refuses with an input sha256 mismatch; row 2 re-pins after this merge, at its own run commit.
- The dated addenda's named residuals stand: F8's declined dataset-specific message; a process outside the guarded session can still write the run tree (no OS-user isolation); replay refuses the uncommitted CUT&RUN patch (N2), so 0098 uses a non-CUT&RUN original; the active-scheduler wait is unbounded; custom registration aliases and patterns are not recorded; F10's frontmatter omissions and F11's free-text placeholder issue remain.
- A review in a fresh context on the same machine and OS user is `independent_context`, not `external_human_seal`.

## Test

The full checks ran on the merge candidate `6efec97`, which is row 6's head `9e55220` merged onto public main `ef5c8af` with the merge-resolution commits named above, with every protected change this record approves in place.
They ran on macOS with Python 3.13, with no other GARS suite on the machine.

- The suite, in its three modes: `Ran 579 tests … OK (skipped=13)` as CI sets it (Docker answering), `OK (skipped=75)` on a macOS cold clone, and `OK (skipped=106)` with `TMPDIR` also unset; the canary was 0/9 in both modes that plant it.
- `tests/check_contracts.py` clean (14 contracts); `tests/check_counts.py` `579 … clean`; `evals/test_harness.py` `Ran 44 … OK`; the prereg check `graded=1`; no new file in the system temp folders; no row 5 container or volume left.
- `gars/tests/test_manifest_groups.py` `Ran 18 … OK` and `gars/tests/test_rerun_check.py` `Ran 21 … OK`, run directly.
- Twenty `EXIT manifest completeness` lines, every one n/n: each of the six other nf-core wrappers 15/15 local and 16/16 Slurm; rnaseq-de and scrna-qc-cluster 14/14 and 15/15; spatial-cluster-count 13/13 and 14/14; spatialvi 14/14 and 15/15.
- `EXIT instrument self-test (fixture, local): reproduction 2/2`.
- The fresh-clone job, emulated on a fresh clone of the candidate: the suite as the README prints it `OK (skipped=75)`, with the README's scratch folder `OK (skipped=13)`, contracts clean, and the skip-count gate `75 skips, at most 106 documented`. The gap-study jobs check out their own pinned study commits, and row 6 changes no workflow and nothing under `evals/haiku-prestudy/`, so they read the same bytes with or without this row. Emulated on this machine, they show the same home-folder and checkout-name reds on `ef5c8af` as on the candidate, test by test, while GitHub CI on `ef5c8af` is green.

At the parent: with row 6's four test modules and their fixtures placed on `2f891d8`, all four were red, each naming a row 6 piece. That is an ImportError on `manifest_check.py`, 6 `data_class_required` failures, an ImportError on `rerun_check.py`, and 7 five-column registry failures. At step A (`94249c5`), `test_rerun_check.py` was red on its ImportError.
An independent mutation proof, at `ce67841`, one planted fault at a time in a disposable copy with byte-for-byte restores: 14 plants, 13 red, and every restore green.
The one survivor, a failure path left untested for nine of the ten wrappers, was ruled R14b and fixed in `9e55220`. The round-4 reviewer re-planted it in two wrappers, and both went red.
The round-4 reviewer also re-planted D1 (R14a), which went red at the parent.
The merge-resolution fixture commit `049c0c3` was proved both ways: restoring the non-BH `padj` brings back the same 15 failures, and neutering the BH gate turns main's own `test_collect_diagnostic_drift` red.

The secret sweep: over `ef5c8af..6efec97`, gitleaks found 0 findings under the push door's ruleset and 0 under `gars/.gitleaks.toml`, over 14 commits. No canary shape appears in the added lines or the head tree. No home path, operator name, LAN, CGNAT, system-temp or aegis-named address appears in the added lines. The address check had 3 patterns, so it was not vacuous. The only e-mail hits are `fixture@example.invalid` in test code.
The fixture reproduction 2/2 in the suite is the instrument's self-test, as the owner's D-9 answer states; it is not reproduction evidence and not the owner's n = 2.
This record changes no code; with it placed and `bash docs/decisions/build_index.sh` re-run, the record checks and the contracts and counts checks stay clean.

## Status

standing

This record is the lane's approval of row 6's protected changes and its confirmation of D-16, the lane's defaults, R1 to R14 and F8's disposition, under the owner's 23 September 2026 delegation; implementation evidence stays in 0095 to 0097 and the change report.
Record 0098 is reserved for the owner's n = 2 Slurm re-run result, made as 0097 describes, and is not written here.
The fixture 2/2 is the instrument's self-test.

## Date

2026-09-25
