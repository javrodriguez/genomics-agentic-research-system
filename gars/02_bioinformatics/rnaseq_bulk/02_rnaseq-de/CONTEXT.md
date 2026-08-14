# Sub-stage 02.02: Bulk RNA-seq Differential Expression

## Purpose
Run differential expression on the count matrix produced by sub-stage 02.01, using the
experimental design the user completed in stage 00 and validated in stage 01. Produces DE
tables, QC and PCA figures, and a report.

## Inputs
1. **Count matrix** — the `preferred_counts_tsv` named in sub-stage 02.01's `run/result.json`
2. **`01_samplesheets/rnaseq_bulk_design.csv`** — `sample_id,condition,group,replicate`
3. **`_config/rnaseq_bulk.yaml`** — `de.formula` and `de.contrast`
4. **The `rnaseq-de` skill** — shipped by the installed `clawbio` package, read-only

## Scope Boundaries
This sub-stage performs the steps in Process and nothing else.

- Never edit, patch, or work around the skill's code. If it errors, report the error verbatim
  and stop.
- **Never substitute a hand-written analysis.** If the skill cannot run, do not compute DE with
  another library, do not write your own DESeq2/PyDESeq2 call, and do not approximate results.
  Report and stop.
- **Never invent a formula or contrast.** Both come from `_config/rnaseq_bulk.yaml`. If either
  is missing, ask the user. A wrong contrast produces confident, wrong biology.
- Never modify the design table, the count matrix, `00_data/`, or `01_samplesheets/`.
- Never re-run sub-stage 02.01, and never regenerate counts.
- **Never interpret the results.** Report file paths and row counts. Do not name significant
  genes, describe pathways, speculate about mechanism, or characterise the biology. That is
  03_custom_analysis, and the user's judgment.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

**Skill invocation.** Source `tools/gars-env.sh`, then run from inside `$GARS_SKILLS/rnaseq-de/`
using `$GARS_PY`. Do not re-declare environment paths in `submit.sh`:
```
PY=~/install/miniconda_clean/envs/gars-bio/bin/python
$PY rnaseq_de.py --counts <tsv> --metadata <csv> --formula <f> --contrast <c> --output <dir>
```
Use the interpreter path, not `conda run` — the latter buffers and can swallow the skill's
output. This sub-stage needs no `module load` at all; Nextflow and Singularity belong to 02.01.

**DE backend.** The skill exposes `--backend {auto,pydeseq2,simple}` and defaults to `auto`.
`pydeseq2==0.5.4` is installed in `gars-bio`, so leave the default. Never force `simple` to work
around a pydeseq2 error — report the error instead.

**Declared requirements.** `_references/assay_stage_skill_map.md` lists what this skill needs (binaries and Python packages). Report a missing requirement by name — "scikit-learn missing, required by rnaseq-de" — not as a raw traceback.

**Skill importability.** Confirm the skill imports before doing anything else:
`$PY rnaseq_de.py --help`. This was verified working on 2026-08-11 with `clawbio==0.6.1`,
`scikit-learn==1.9.0`, and `pydeseq2==0.5.4`. If it fails, that is a preconditions failure (T4):
report it and stop. Never pip-install on the fly, never vendor or stub a missing module, and
never swap in a different PCA or DE implementation.

**Adapted count matrix.** nf-core emits `gene_id`, `gene_name`, then one column per sample.
`rnaseq-de` documents "first column is gene identifier" and coerces every later column to
numeric, so `gene_name` raises `Count matrix contains non-numeric entries`. The two skills
declare each other as chaining partners, but their formats do not actually meet.

This sub-stage therefore writes an adapted copy into **its own** directory — `adapted/counts_gene.tsv`,
with `gene_name` dropped and counts rounded to integers — and preserves the mapping in
`adapted/gene_id_to_name.tsv` so results can be annotated afterwards. **The source matrix is
never modified**; sub-stage 02.01 owns it.

**Scheduled execution.** Submit this sub-stage to Slurm; do not run it in the foreground.
PyDESeq2 dispersion fitting over ~79k genes was SIGKILLed (exit 137) on a login node. An
analysis sub-stage needs a scheduled allocation just as much as the pipeline does.

**Non-empty output.** The skill refuses a populated `--output` with `FileExistsError`. A rerun
must move the previous `run/` aside rather than writing into it.

**Metadata table.** The skill requires a `sample_id` column. `01_samplesheets/rnaseq_bulk_design.csv`
already has exactly that header, so it is passed unchanged as `--metadata`. Never edit it to
suit the skill.

**Formula.** `de.formula` in config, e.g. `~ condition` or `~ batch + condition`. Every term in
it must be a column of the design table.

**Contrast.** `de.contrast` in config, `factor,numerator,denominator`, e.g.
`condition,treated,control`. The factor must be a design column, and both levels must appear in
that column.

**Valid comparison.** The numerator and denominator levels each have at least 2 samples in the
design table. Fewer makes dispersion estimation unreliable, and the result is not interpretable.

## Process
1. Reply T1.
2. Confirm sub-stage 02.01's STATUS is `COMPLETE`. If not, reply T4 and stop.
3. Read `run/result.json` from sub-stage 02.01 and resolve `preferred_counts_tsv`. If it is
   absent or the file does not exist, reply T4 and stop.
4. Read `de.formula` and `de.contrast` from `_config/rnaseq_bulk.yaml`. If either is missing,
   reply T5 asking for it, and stop. Do not proceed with a default.
5. Read `01_samplesheets/rnaseq_bulk_design.csv`. Check that every formula term is a column, that
   the contrast factor is a column, and that both contrast levels appear in it. Check the
   comparison is a **valid comparison**. Collect every failure.
6. Check that the sample IDs in the count matrix header and the design table match. Report each
   direction separately — samples in the matrix but not the design, and the reverse.
7. If any check in steps 5-6 failed, reply T3 listing all of them, and stop. Write nothing.
8. Create the output directory. If it exists and is non-empty, reply T4 and stop.
9. Reply T2, then write `submit.sh` carrying its own environment and the adapted-matrix step,
   and submit it with `sbatch`. Write `STATUS` as `SUBMITTED <job_id> <iso8601>` and return; do
   not run the skill in the foreground and do not poll. Collect results on a later invocation,
   as sub-stage 02.01 does.
10. If the skill exits non-zero, write `STATUS` as `FAILED <iso8601>`, reply T4 with its verbatim
    error, and stop.
11. Run the exit gate. Existence is not sufficient — **check content**:
    - `report.md`, `tables/de_results.csv` and the three `figures/` PNGs exist and are non-empty
    - `de_results.csv` has at least one data row
    - `de_results.csv` **has a gene identifier column**, and its values are non-empty

    The identifier check is not hypothetical: a version of this skill silently dropped the gene
    column, producing a complete and plausible table in which every gene was anonymous. A
    file-exists gate passes that happily. If any check fails, write `FAILED`, reply T4, stop.
12. Write `OUTPUTS.tsv`: `de_results` as `native`, plus the two artifacts this sub-stage created
    while adapting its input — `counts_gene` as **`adapted`** and `gene_id_map` as `native`.
    Marking the reshaped matrix `adapted` is what stops a later consumer mistaking it for the
    authoritative one from 02.01.
13. Write `STATUS` as `COMPLETE <iso8601>`, append a dated entry to the project's `HISTORY.md`
    naming which sub-stage supplied the count matrix, and reply T6.

## Response Format
Every message you send in this sub-stage is one of the templates below, with placeholders
filled. Add nothing else — in particular, no interpretation of the DE results.

**T1 — Start**
```
Sub-stage 02.02: bulk RNA-seq differential expression.
Counts:   <preferred_counts_tsv>
Design:   01_samplesheets/rnaseq_bulk_design.csv (<n> samples)
Formula:  <formula>
Contrast: <contrast>
```

**T2 — Validation passed**
```
| Check | Result |
|---|---|
| Formula terms present in design | Pass |
| Contrast levels present | <numerator>: <n> samples, <denominator>: <n> samples |
| Count matrix / design sample match | <n> samples |

Running differential expression.
```

**T3 — Validation failed**
```
Validation failed. Nothing was run; no input was modified.

| Check | Detail |
|---|---|
| <check> | <what is wrong, and which samples or levels are responsible> |

Correct _config/rnaseq_bulk.yaml or the design, then run stage 02 again.
```

**T4 — Failed or preconditions not met**
```
Sub-stage 02.02 could not complete.

| Requirement | Status |
|---|---|
| 02.01 STATUS is COMPLETE | Yes / No |
| Count matrix resolves | Yes / No |
| Output directory empty | Yes / No |

<verbatim skill error if one was produced>

Nothing was retried, nothing was deleted.
```

**T5 — Design decision required**
```
_config/rnaseq_bulk.yaml does not declare <de.formula|de.contrast>.

Design columns available: condition, group, replicate
Levels in <column>: <observed levels, with sample counts>

Provide the formula and contrast to use. I will not choose them.
```

**T6 — Complete**
```
Sub-stage 02.02 complete.

| Artifact | Path |
|---|---|
| DE results | <output>/tables/de_results.csv |
| Report | <output>/report.md |
| Figures | <output>/figures/ (pca.png, volcano.png, ma_plot.png) |

Genes tested: <n>
Next: 03_custom_analysis.
```

# OUTPUT
Written to `projects/<project_title>/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/`:

| Artifact | Contents |
|---|---|
| `STATUS` | Sub-stage state. |
| `OUTPUTS.tsv` | Artifacts produced, by type and role. |
| `adapted/` | Input reshaped for this skill: `counts_gene.tsv` (role `adapted`) and `gene_id_to_name.tsv`. The source matrix is never modified. |
| `logs/rnaseq_de.log` | Skill stdout/stderr. |
| `run/report.md` | Skill report, including its required disclaimer. |
| `run/tables/` | `de_results.csv`, `normalized_counts.csv`, `qc_summary.csv`. |
| `run/figures/` | `pca.png`, `volcano.png`, `ma_plot.png`. |
| `run/reproducibility/` | `commands.sh`, `environment.yml`, `checksums.sha256`. |

`00_data/`, `01_samplesheets/`, and sub-stage 02.01's output are never modified.
