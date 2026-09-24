---
date: 2026-09-24
status: standing
kind: decision
touches:
  - evals/bench.py
  - tests/test_registry_columns.py
  - gars/.claude/settings.json
  - gars/00_initialize_project/CONTEXT.md
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
  - gars/_references/artifact_types.md
  - gars/_references/genomes.md
  - gars/_references/manifest_schema.json
  - gars/_system/configure.py
  - gars/_system/executorlib.py
  - gars/_system/guard_hook.py
  - gars/_system/manifest_check.py
  - gars/_system/resolve_artifact.py
  - gars/_system/stage00_register.py
  - gars/_system/tools/registry.json
  - gars/_system/wrapperlib.py
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
  - docs/implementation/row_6_change_report.md
symptoms:
  - prepare manifests omit applicable required provenance groups
  - missing predicate evidence must not shrink the completeness denominator
---
# Row 6 Step A: manifest groups and applicability

## Context

The owner's words, 23 September 2026, verbatim:

> GARS row 6 (manifest completeness + reproduction) on the Mac Codex queue, decisions 0095-0099

Everything below is the lane's specification under the owner's standing delegation
of 23 September 2026, not additional words attributed to the owner. In particular,
the group classification answers gap assessment D-16 **for the lane**, open to the
owner's confirmation in 0099. Step A covers R-084–R-086, R-060, the manifest fields
of R-067/R-068, and the hash half of R-090. Step B is separate.

## Decision

### D-16: the lane's group table

Required means `required` plus `required_if_applicable` whose predicate holds.
Completeness is present divided by applicable required groups; a missing applicable
field invalidates the manifest. No group is optional in this classification.

| # | §8.1 group | class | applicability predicate (only predicate_facts) | source at collect |
|---|---|---|---|---|
| 1 | inputs + sha256 | required | — | existing label_sha256 and inputs; input_data_location per input |
| 2 | workflow name + version | required | — | wrapper and unchanged pipeline_commit from checkout; workflow_name, pinned workflow_version, GARS HEAD at prepare |
| 3 | params + config_sha256 | required | — | existing |
| 4 | container digests per process | required_if_applicable | wrapper_kind = nextflow | Nextflow trace; @sha256 digest or local image hash; mutable tags are missing |
| 5 | software versions | required | — | pipeline_info versions; generated local script's versions.json, interpreter and imported packages |
| 6 | reference build, annotation release, fasta_sha256, gtf_sha256 | required_if_applicable | reference_named = true | genomes.md and preflight comparison |
| 7 | exact command | required | — | commands.sh path and sha256 |
| 8 | output artifacts: sha256 per file + artifact_class | required | — | OUTPUTS.tsv, hashed at collect |
| 9 | execution timestamps | required | — | trace start/complete or executor stage record |
| 10 | resources consumed | required_if_applicable | backend = slurm | sacct -j ID --format=Elapsed,MaxRSS,AllocCPUS -P -n; batch MaxRSS |
| 11 | backend, venue, purpose, data_class, input_data_location, artifact_destination | required | — | executor backend, machine-owned dataset row, input locations, repo-relative output directory |
| 12 | approval record reference | required_if_applicable | approval_gated = true | executor's approval id and sha256 |
| 13 | random seeds + thread counts | required | — | config threads; per-call explicit wrapper seeds; no-RNG sentinel for paths without RNG |
| 14 | design-check output | required_if_applicable | design_record = true | stage-01 record path and sha256 |
| 15 | failure class | required_if_applicable | status = FAILED | collect_failure class |
| 16 | model-step fields | required_if_applicable | model_step = true | provider from closed prefix table, model id/version, contract prompt path and Git object id with algorithm, routing none, sampling sentinel, HISTORY sha256 |
| 17 | idempotency_key | required | — | existing |
| 18 | template_version + agent_model | required | — | existing template version; collect --model |

### Predicate rule and sentinels

Every predicate reads a named fact in the mandatory `predicate_facts` block, never
the group it governs. The checker validates all facts and evaluates predicates
before inspecting group contents. Missing facts and out-of-vocabulary facts are
errors, never inapplicability. Sources are the closed wrapper list (`wrapper_kind`),
config (`reference_named`), executor approval records (`approval_gated`), disk
(`design_record`), the current collect gate (`status`), collect's model argument
(`model_step`), and the executor's own stage record (`backend`). Status is supplied
internally before STATUS is written; it is not read from prior VALIDATING state.

The only named field sentinels are:

- group 13 random seeds: `no-rng-in-code-path`;
- group 16 routing_rule_id: `none` (GARS has no router);
- group 16 sampling_parameters: `not-exposed-by-harness`;
- group 18 agent_model: `none` (no model acted).

Unknown, empty, null, TODO and sentinels in other fields are missing. `--model none`
makes group 16 inapplicable; `unknown` makes it applicable and incomplete. The exact
model id is the version identity reported by this harness; no separate provider
revision or sampling controls are exposed. This does not verify the caller's claim
(decision 0024). Prompt hashes are Git blob object ids, with their algorithm named.

### The lane's R1–R8 rulings

1. Collect supplies group 18 agent_model from its existing --model argument. No
   prepare flag or prepare registry entry changes.
2. Complete and failure lifecycle paths supply their current gate state before
   writing STATUS; tests compare predicate status with the resulting state token.
3. Backend is mandatory and comes from the executor's recorded submission. If it
   differs from the immutable prepare backend, group 11 is incomplete; submit's
   existing acceptance behavior is preserved.
4. The local wrappers pass a per-wrapper seed of 0 to every stochastic call whose
   API accepts one. Group 13 names the calls and values. APIs with no seed control
   are named with determinism unknown. No previous library default is claimed.
5. Directory OUTPUTS paths keep their routing. Their SHA cell is `sha256-tree:`
   plus the hash of the sorted regular-member listing, one relative path, tab,
   SHA-256 and newline per member. Symlinks are named and never traversed. The
   manifest carries the listing; collect, the COMPLETE gate and invariant tests
   recompute file and tree hashes. File rows carry plain file hashes.
6. There is no re-seed verb. Existing project Groovy configs require the manual
   template-copy migration described in 0096, after the owner reviews site scalars.
7. The tests create disposable Git pipeline checkouts with synthetic commits and
   release tags. Spatialvi's production commit-prefix pin cannot name an arbitrary
   fixture commit, so only the test process points that pin at the actual synthetic
   commit. Production workspace.PIPELINES and check_pipeline remain byte-identical;
   a wrong commit still refuses. Synthetic release tags are rnaseq 3.26.0, atacseq
   2.1.2, chipseq 2.1.0, cutandrun 3.2.2, methylseq 4.2.0, and scrnaseq 4.2.0;
   the spatial prefix is derived from its fixture commit and printed evidence is
   never described as a production pipeline run.

8. **R8**, the lane under the owner's standing delegation of 23 September 2026:
   option A of the preserved question in the change report is authorized. Change
   exactly two lines in evals/bench.py: accept widths 3 or 5 with assertIn, then
   unpack row[:3]. Root tests must accept both widths, refuse 4 and 6, and show
   identical scores for the same first three columns even with wrong trailing
   hash/class values. This evaluation-code change is protected and covered by the
   owner's approval record 0099 at merge, never by this producer. It is the first
   commit, containing only that reader, its root tests, and README/DEVELOPMENT
   counts. Step A is the second commit; each passes independently. Benchmark task
   pins remain untouched: row 2 re-pins them at its own run commit.

Finalize requires a data class and purpose and records an agreement reference
(default `none`). The lane reads the four §6.1 purposes together with §6.2's local
“fixtures only” row to permit `fixture` as the fifth purpose. Same-value re-finalize
leaves dataset.tsv untouched; different values refuse. Existing projects without
that row produce missing dataset fields, not inferred classifications.

Reference hashing uses the process-local `_REFERENCE_HASH_CACHE`, keyed by
`(realpath, size, mtime_ns)`. Registry hashes are authoritative, not editable config
hashes. UNKNOWN permits preparation but leaves group 6 incomplete. A known hash
mismatch is `reference_hash_mismatch`; no checksum is invented.

### Threat model

Covered: a producer or agent session that runs the wrapper verbs and the executor CLI, and any code path in this repository. It must not be able to:
  - get a run graded complete while an applicable required group is absent, empty, `unknown` or a placeholder the table does not name;
  - make a group inapplicable by leaving it out (predicates read only other facts);
  - pass a mutable container tag off as a digest;
  - change a prepare-time manifest fact at collect, or get an output file into OUTPUTS.tsv without a sha256 matching the manifest;
  - register a dataset without a data class;
  - write, rewrite, move or delete a project's `dataset.tsv` through its own tools (only `finalize` creates it);
  - run on a reference file whose hash differs from its registry row without a named refusal;
  - make manifest_check skip or silently drop a manifest.
Not covered, named as residual in 0095: a session that edits `_system/`, `_references/` or `_templates/` (the guard and the owner's approval are that line); a process outside the guarded session that chmods or rewrites `dataset.tsv` (the guard sees only the session's tool calls); the truth of a value the harness reports (e.g. a lying `--model`, which is only as honest as the caller, per decision 0024); real-cluster trace and sacct content; a forged manifest written outside the wrapper verbs (the guard's READ_ONLY on manifest.json is that line).

## What this does not close

- NOT met: real-cluster trace and sacct. This step measures synthetic fixtures;
  row 13 measures real execution.
- NOT met: GRCh38 hashes, UNKNOWN until the owner hashes the files where they live.
- NOT met: R-062 venue refusal and the remainder of §6.1's record, including
  permitted_backends, provider exposure, retention and expiry: row 8, D-3.
- NOT met: R-087/R-088 registry validation.
- NOT met: §8.3 test_reference_pairing.py; it compares claims from row 7's table.
- NOT met: R-069 artifact liveness.
- NOT met: report methods and reproduction sections; row 7's renderer reads these
  fields in later wiring.
- NOT met: stage03_analysis.py and create_bioinformatics_skill.py still write
  three-column OUTPUTS.tsv without complete_manifest. Their manifests grade
  incomplete and count against §17's “every completed run”.
- NOT met: protection from processes outside the guarded session. A human shell or
  unseen script can chmod and rewrite dataset.tsv. Source protection, reported-value
  truth and externally forged manifests have the threat-model limits stated above.
- NOT met: the pilot-1 measurement, and §17's real-run completeness measurement.
- NOT met: Step B reproduction, n = 2, tolerances and artifact comparison modes.
- NOT met: benchmark task source-pin validation after the authorized changes.
  Row 2 owns re-pinning at its run commit; benchmarks/ remains untouched.

## Test

`python3 gars/tests/test_manifest_groups.py` exercises all ten real prepare/collect
paths on local and synthetic SLURM, immutable prepare facts, idempotent re-collect,
all groups, predicates, model sentinels, container forms, output hashes and reference
mismatch. `python3 gars/tests/test_data_class_required.py` drives real finalize and
the guard. Twenty whole-run fixture exit lines are reproduced in the change report;
fixture completeness ranges from 13/13 to 16/16 applicable required groups.
These are fixture measurements, not a §17 real-run exit claim. The report records
fault plants and parent-red evidence separately.

Whole-run synthetic fixture measurements (local and stub SLURM), verbatim:

```text
EXIT manifest completeness nfcore-atacseq-wrapper local: 15/15
EXIT manifest completeness nfcore-atacseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-chipseq-wrapper local: 15/15
EXIT manifest completeness nfcore-chipseq-wrapper slurm: 16/16
EXIT manifest completeness nfcore-cutandrun-wrapper local: 15/15
EXIT manifest completeness nfcore-cutandrun-wrapper slurm: 16/16
EXIT manifest completeness nfcore-methylseq-wrapper local: 15/15
EXIT manifest completeness nfcore-methylseq-wrapper slurm: 16/16
EXIT manifest completeness rnaseq-de local: 14/14
EXIT manifest completeness rnaseq-de slurm: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-rnaseq-wrapper slurm: 16/16
EXIT manifest completeness scrna-qc-cluster local: 14/14
EXIT manifest completeness scrna-qc-cluster slurm: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper local: 15/15
EXIT manifest completeness nfcore-scrnaseq-wrapper slurm: 16/16
EXIT manifest completeness spatial-cluster-count local: 13/13
EXIT manifest completeness spatial-cluster-count slurm: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper local: 14/14
EXIT manifest completeness nfcore-spatialvi-wrapper slurm: 15/15
```

## Status

Standing lane specification; implementation verification is recorded in the change
report. Record 0099 is the owner's approval of this row's protected changes,
committed by the owner at merge. This producer neither writes nor claims it. 0097
is reserved for Step B and 0098 for the owner's n = 2 result.

Protected files touched by Step A are listed below, one per line; all require the
owner's 0099 approval at merge.

- `evals/bench.py` (R8 evaluation-code reader change)
- `gars/.claude/settings.json`
- `gars/00_initialize_project/CONTEXT.md`
- `gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md`
- `gars/02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md`
- `gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md`
- `gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md`
- `gars/_references/artifact_types.md`
- `gars/_references/genomes.md`
- `gars/_references/manifest_schema.json`
- `gars/_system/configure.py`
- `gars/_system/executorlib.py`
- `gars/_system/guard_hook.py`
- `gars/_system/manifest_check.py`
- `gars/_system/resolve_artifact.py`
- `gars/_system/stage00_register.py`
- `gars/_system/tools/registry.json`
- `gars/_system/wrapperlib.py`
- `gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py`
- `gars/_system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py`
- `gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py`
- `gars/_system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py`
- `gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py`
- `gars/_system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py`
- `gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py`
- `gars/_system/wrappers/rnaseq-de/rnaseq_de.py`
- `gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py`
- `gars/_system/wrappers/spatial-cluster-count/spatial_cluster_count.py`
- `gars/_templates/config/nextflow.slurm.config`

## Date

2026-09-24
