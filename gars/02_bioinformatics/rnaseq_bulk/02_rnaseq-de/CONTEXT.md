# Sub-stage 02.02: Bulk RNA-seq Differential Expression

## Purpose
Run differential expression on the count matrix produced by sub-stage 02.01, using the
experimental design the user completed in stage 00 and validated in stage 01. Produces DE
tables, QC and PCA figures, and a report.

## Inputs
- Working (this run), **resolved by type, never by path**:
  1. **`counts_gene`** — resolved from the `OUTPUTS.tsv` of completed sub-stages
  2. **`design`** — resolved the same way; stage 01 supplies it
- Reference (every run):
  3. **`_config/rnaseq_bulk.yaml`** — `de.formula` and `de.contrast`
  4. **`_system/resolve_artifact.py`** — the resolver
  5. **The `rnaseq-de` skill** — shipped by the installed `clawbio` package, read-only

## Scope Boundaries
This sub-stage performs the steps in Process and nothing else.

- Never edit, patch, or work around the skill's code. If it errors, report the error verbatim
  and stop.
- **`AttributeError: 'Pandas' object has no attribute 'gene'` is not an upstream defect to escalate.**
  It is the known symptom of an adapted matrix whose identifier column is not named `gene`. Check
  `adapted/counts_gene.tsv`'s first column before concluding anything about the skill; if it reads
  `gene_id`, the adaptation was wrong and re-running with `_system/adapt_counts.py` fixes it.
- **Never substitute a hand-written analysis.** If the skill cannot run, do not compute DE with
  another library, do not write your own DESeq2/PyDESeq2 call, and do not approximate results.
  Report and stop.
- **Never invent a formula or contrast.** Both come from `_config/rnaseq_bulk.yaml`. If either
  is missing, ask the user. A wrong contrast produces confident, wrong biology.
- Never modify the design table, the count matrix, `00_data/`, or `01_samplesheets/`.
- Never re-run sub-stage 02.01, and never regenerate counts.
- **Never locate the count matrix yourself.** Do not read 02.01's `result.json`, do not glob its
  `run/` tree, and do not open its `OUTPUTS.tsv` by eye. Resolution is
  `_system/resolve_artifact.py`'s job: it applies the reverse-order scan, the `native` preference
  and the STATUS gate that keep a consumer from silently picking a matrix reshaped for someone
  else's parser.
- **Never interpret the results.** Report file paths and row counts. Do not name significant
  genes, describe pathways, speculate about mechanism, or characterise the biology. That is
  03_custom_analysis, and the user's judgment.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

**Skill invocation.** Source `_system/gars-env.sh`, then run from inside `$GARS_SKILLS/rnaseq-de/`
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

**Input resolution.** This sub-stage finds its inputs **by artifact type, not by path**, so a
change in where 02.01 writes does not break it. The rule and its rationale are in
`_references/artifact_types.md`; the implementation is `_system/resolve_artifact.py`. Resolution
prefers `native` artifacts — the `adapted` matrix this sub-stage writes at step 8 is deliberately
*not* what a later consumer would pick up.

**Adapted count matrix.** nf-core emits `gene_id`, `gene_name`, then one column per sample.
`rnaseq-de` documents "first column is gene identifier" and coerces every later column to
numeric, so `gene_name` raises `Count matrix contains non-numeric entries`. The two skills
declare each other as chaining partners, but their formats do not actually meet.

This sub-stage therefore writes an adapted copy into **its own** directory — `adapted/counts_gene.tsv`
— and preserves the mapping in `adapted/gene_id_to_name.tsv` so results can be annotated
afterwards. **The source matrix is never modified**; sub-stage 02.01 owns it.

`_system/adapt_counts.py` performs the reshape. It is three changes, and the third is the one that
bites:

1. `gene_name` dropped — the skill coerces every column after the first to numeric.
2. Counts rounded to integers — nf-core emits length-scaled floats, DESeq2 wants counts.
3. **The identifier column renamed `gene_id` → `gene`.** Not cosmetic. The skill does
   `results_df.reset_index().rename(columns={"index": "gene"})`, which assumes an *unnamed*
   index. Given `gene_id` the rename matches nothing, and the identifier is then dropped from the
   output column selection **with no error** — verified directly: with the index named `gene_id`,
   `"gene" in res.columns` is `False` and no identifier column survives; named `gene`, it is
   `True`.

**Never hand-write this reshape into `submit.sh`.** A heredoc version omitted the rename and
produced a real 22,783-gene differential-expression table in which every gene was anonymous. It
surfaced only because report-writing later crashed on `row.gene`; without that crash it would
have looked publishable.

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
2. Resolve this sub-stage's declared inputs by type, from the workspace root:

   ```bash
   python3 _system/resolve_artifact.py --project projects/<title> --assay rnaseq_bulk \
       --consumes counts_gene design
   ```

   It reports only artifacts of sub-stages whose `STATUS` is `COMPLETE`, so this subsumes the
   old "check 02.01 completed" step. Exit 1 → reply T4 with its `missing` and
   `declared_but_absent` entries and stop. Never fall back to searching for the file.
3. Take the `counts_gene` path from its `resolved` map. Record the supplying sub-stage — it goes
   in `HISTORY.md` at step 13, so every result can name where its inputs came from.
4. Read `de.formula` and `de.contrast` from `_config/rnaseq_bulk.yaml`. If either is missing,
   reply T5 asking for it, and stop. Do not proceed with a default.
5. Read `01_samplesheets/rnaseq_bulk_design.csv`. Check that every formula term is a column, that
   the contrast factor is a column, and that both contrast levels appear in it. Check the
   comparison is a **valid comparison**. Collect every failure.
6. Check that the sample IDs in the count matrix header and the design table match. Report each
   direction separately — samples in the matrix but not the design, and the reverse.
7. If any check in steps 5-6 failed, reply T3 listing all of them, and stop. Write nothing.
8. Create the output directory. If it exists and is non-empty, reply T4 and stop.
9. Reply T2, then write `submit.sh` carrying its own environment and, for the adapted matrix, a
   call to the shared helper — never an inline reshape:

   ```bash
   "$GARS_PY" "$WS/_system/adapt_counts.py" --counts "$COUNTS" --out "$SUB/adapted"
   ```

   It exits non-zero if the matrix is not the expected shape, and verifies its own output header
   before returning. Then
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
    The entry must name the **template version** this sub-stage ran under, read from
    `_references/VERSION`. A workspace can be upgraded between stages, so the version that
    created the project is not necessarily the version that produced this result.

## Response Format
Every message you send in this sub-stage is one of the templates below, with placeholders
filled. Add nothing else — in particular, no interpretation of the DE results.

**T1 — Start**
```
Sub-stage 02.02: bulk RNA-seq differential expression.
Counts:   <resolved counts_gene path>  (type counts_gene, native, from <supplying sub-stage>)
Design:   <resolved design path> (<n> samples)
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

This is the last implemented sub-stage for rnaseq_bulk. 03_custom_analysis is not implemented in
this template version, so these artifacts are yours to analyse directly.
```

## OUTPUT
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

## Human check
Open `run/tables/de_results.csv` and confirm the first column holds real gene identifiers, not
blanks or row numbers. This check exists because a defect in the skill once produced a complete,
plausible DE table in which every gene was anonymous, with no error and no warning — a
file-exists check passes happily on it.

Then confirm the contrast in `run/report.md` is the one you asked for, in the direction you
asked for: `condition,treated,control` means treated relative to control, and reversing it
reverses the sign of every fold change.
