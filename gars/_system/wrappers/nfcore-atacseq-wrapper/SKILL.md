---
name: nfcore-atacseq-wrapper
description: >
  GARS-authored wrapper around nf-core/atacseq 2.1.2: preflight, audited params translation,
  Slurm submission script with requeue guard, content-checking exit gate, artifact registry
  rows and derived-index cache harvesting. Wrapper #1 of the assay expansion (decision 0028).
metadata:
  openclaw:
    source: gars                    # versioned in this repo, ours to maintain (decision 0012)
    pipeline: nf-core/atacseq
    pipeline_version: "2.1.2"
    requires:
      bins: [python3, nextflow, java, git]
      python: ">=3.6 (stdlib only)"
    install: >
      Nothing to install for the wrapper itself. Runtime needs the gars-nxf conda environment
      (nextflow, openjdk 17) on PATH at submit time -- provided by _system/gars-env.sh -- and a
      pinned local checkout of nf-core/atacseq 2.1.2 at $GARS_PIPELINES/atacseq-2.1.2, cloned
      over the git protocol (the GitHub REST API is rate-capped on this cluster).
---

# nfcore-atacseq-wrapper

The same behavioral contract as the ClawBio nf-core wrappers, in the `_system/` idiom: one
stdlib Python file, JSON on stdout, exit codes `0 ok / 1 failure / 2 refused / 3 usage`.
The sub-stage contract at `02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md`
orchestrates it; nothing here is invoked directly by a user.

```
python3 nfcore_atacseq_wrapper.py check   --project projects/<title>
python3 nfcore_atacseq_wrapper.py prepare --project projects/<title>
sbatch <substage>/submit.sh                       # written by prepare
python3 nfcore_atacseq_wrapper.py collect --project projects/<title> --model "<model id>"
```

- `check` — preflight: config complete and sane, samplesheet header and FASTQ paths, pinned
  checkout tag verified with `git describe`, executor config carries no `params` block, `run/`
  safe to use. Writes `preflight/check_result.json`.
- `prepare` — re-validates, then writes `params.yaml` (the audited parameter surface),
  `submit.sh` (Slurm directives from `compute.*`, requeue guard, native `-resume` crash
  recovery) and `reproducibility/{manifest.json,commands.sh}`. Deterministic bytes.
- `collect` — the exit gate after the job finishes: every sample present in the consensus
  count-matrix header, peaks/consensus/bigwig/BAM/MultiQC all real; writes `OUTPUTS.tsv` and
  `STATUS`, harvests the aligner index into the derived cache when configured, returns the
  `history_entry` (template version + model) to append verbatim.
