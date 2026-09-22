# Sub-stage 02.02: Differential Expression

## Purpose
Test for differential gene expression between the two conditions the user chose, through the
GARS-authored `rnaseq-de` wrapper (decision 0029; the retired ClawBio-skill procedure — the
source of four recorded defects, two silent, reported upstream as ClawBio/ClawBio#365 — was
deleted 2026-08-27 after all three switchover criteria were met on a live run). The
analysis runs under the workspace's executor; this sub-stage submits and returns, then
collects on a later
invocation.

**The computation is not yours.** The wrapper's `check` validates the design against the
config, `prepare` generates the analysis script (`scripts/run_de.py`, PyDESeq2) and
`submit.sh`, and `collect` runs the content-checking exit gate and writes `OUTPUTS.tsv` and
`STATUS`. Your job is the dialogue between those calls; the adaptation of the count matrix
happens inside the generated job via `_system/adapt_counts.py` (decision 0021) — never by
hand.

## Inputs
1. **`counts_gene` and `design`** — resolved by artifact type through
   `_system/resolve_artifact.py`, never by path (decision 0007). The counts are 02.01's
   *native* matrix; this sub-stage adapts it itself.
2. **`_config/rnaseq_bulk.yaml`** — `de.formula` and `de.contrast`, completed from the stage
   02 menus
3. **The wrapper** — `$GARS_WRAPPERS/rnaseq-de/rnaseq_de.py`, versioned in this workspace
4. Reference (every run): `_references/artifact_types.md`, `_system/gars-env.sh`

## Scope Boundaries
This sub-stage performs the steps in Process and nothing else.

- Never resolve the count matrix or design yourself — step 2's resolver call is the only
  source, and reading `OUTPUTS.tsv` by eye is how a consumer silently picks a matrix reshaped
  for someone else's parser.
- Never edit the wrapper's code or the generated `run_de.py`. A change of method is a config
  or template change to report, not an edit to make.
- Never run the analysis in the foreground: a pure-Python DE step was SIGKILLed on a login
  node once (decision 0005). Submit, write STATUS, and return.
- Never modify the native count matrix, anything under 02.01's directory, `00_data/`, or
  `01_samplesheets/`.
- Never resubmit a job whose STATUS is `SUBMITTED` or `RUNNING`.
- Do not interpret the results. Report counts of genes tested and significant, paths, and
  the top-genes table location — the science of what they mean is the user's.
- If you believe a step should deviate, stop and ask. Do not act first and report afterwards.

## Definitions

**Wrapper invocation.** From the workspace root, on stock python:

```bash
python3 _system/wrappers/rnaseq-de/rnaseq_de.py <subcommand> --project projects/<title> \
    [--counts <resolved path> --design <resolved path>]
```

`check` and `prepare` take the resolved `--counts` and `--design`; `collect` takes `--model`
and `--counts-from` (the supplying sub-stage, from the resolver's answer). Exit codes are the
stage-helper standard: 0 ok, 1 failure, 2 refused, 3 usage.

**Failure vocabulary.** `preconditions`, `config`, `config_unfilled`, `design` (contrast
level missing or under-sampled), `counts` (a design sample absent from the matrix header);
`collect` adds `de_results`, `figures`, `report`, `adaptation`.

**Execution venue.** Always the workspace's configured executor — `_config/executor.yaml`
names it (decision 0039); on this cluster that is Slurm (decision 0027, no opt-out). The generated `submit.sh`
first runs `adapt_counts.py` (stdlib), then `run_de.py` under `$GARS_PY` — pandas, pydeseq2,
scikit-learn and matplotlib live in `gars-bio`.

**The adaptation** (decisions 0010, 0021). nf-core emits `gene_id, gene_name, <samples>`;
the DE parser requires the identifier column named `gene` and every later column numeric.
`adapt_counts.py` performs the reshape, writes `adapted/counts_gene.tsv` and
`adapted/gene_id_to_name.tsv`, and verifies its own output header. The exit gate re-checks
the result end to end: a complete, plausible DE table in which every gene is anonymous is
exactly the silent failure that motivated all of this.

**Output schema.** Byte-compatible with the retired skill:
`run/tables/de_results.csv` (`gene,baseMean,log2FoldChange,pvalue,padj`),
`run/tables/normalized_counts.csv`, `run/figures/{pca,volcano,ma_plot}.png`, `run/report.md`.
Projects produced by either path read the same downstream.

## Process
1. Reply T1.
2. Read the STATUS file. If `SUBMITTED`, `RUNNING`, or `COMPLETE`, stop — the router handles
   those states.
3. Resolve the inputs:

   ```bash
   python3 _system/resolve_artifact.py --project projects/<title> --assay rnaseq_bulk \
       --consumes counts_gene design
   ```

   Exit non-zero → reply T5 naming its `missing` entries and stop. Never dispatch without
   resolved inputs, and never regenerate a missing artifact.
4. Run the wrapper's `check` with the resolved `--counts` and `--design`. Exit 1 → reply T5
   with its `failures` verbatim and stop: `design` failures mean the design or contrast needs
   the user, `config_unfilled` means the stage 02 menus have not run.
5. Run `prepare` with the same paths. Exit 1 → reply T5. Exit 0 → it wrote
   `scripts/run_de.py`, `submit.sh` and the reproducibility bundle.
6. Submit with `python3 <workspace>/_system/executorlib.py submit --workspace <project dir>
   <sub-stage dir>/submit.sh`; capture `job_id` from the JSON. Write `STATUS` as
   `SUBMITTED <job_id> <iso8601>`. Reply T2 and stop.
7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: ask `python3 <workspace>/_system/executorlib.py
   status --workspace <project dir> <job_id>` — it answers `PENDING`, `RUNNING`,
   `COMPLETED` or `FAILED`. Not yet terminal → update STATUS to `RUNNING <job_id>
   <iso8601>`, reply T3, stop.
8. If the job has finished, run `collect` with `--model "<the exact model id you are running
   as>"` (decision 0024) and `--counts-from <the sub-stage the resolver named>`. Exit 2 → the
   run did not complete: write `STATUS` as `FAILED <iso8601>`, reply T4 with the scheduler log
   path, stop. Exit 1 → the exit gate failed: write `FAILED`, reply T4 with its `failures`
   verbatim, stop.
9. Exit 0 → `collect` has written `OUTPUTS.tsv` (`de_results` native, `counts_gene`
   **adapted**, `gene_id_map` native — the role marking is what stops a later consumer
   mistaking the reshaped matrix for 02.01's authoritative one) and `STATUS COMPLETE`.
   Append its `history_entry` to the project's `HISTORY.md` **verbatim**, replacing
   `<ISO-8601 date>` with today's date, and reply T6.

## Response Format
Every message you send in this sub-stage is one of the templates below, with placeholders
filled. Add nothing else — in particular, no interpretation of the DE results.

One standing exception, from `_references/contract_standard.md` ("the bounded voice"): if the
user asks a direct question, answer it from this workspace's own files — the contracts,
`_references/`, and the current project's directory — read-only, in a short paragraph, then
restate the pending wait point. Never let the answer become an action, a recommendation to
deviate, or a reason to skip a step.

**T1 — Start**
```
Sub-stage 02.02: differential expression.
Assay: rnaseq_bulk
Formula: <de.formula> | Contrast: <de.contrast>
Counts: <resolved counts_gene path> (from <sub-stage>)
Design: <resolved design path> (<n> samples)
```

**T2 — Submitted**
```
Checks passed. Submitted as job <job_id>.

Output: 02_bioinformatics/rnaseq_bulk/02_rnaseq-de/run/
Status: 02_bioinformatics/rnaseq_bulk/02_rnaseq-de/STATUS

Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
Run stage 02 again when it finishes to collect results.
```

**T3 — Still running**
```
Job <job_id> is <state>, submitted <timestamp>. Nothing was resubmitted.

Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
```

**T4 — Failed**
```
Sub-stage 02.02 failed at <stage: run|exit gate>.

<verbatim wrapper failures or scheduler error>

STATUS set to FAILED. Nothing was retried, nothing was deleted.
Log: 02_bioinformatics/rnaseq_bulk/02_rnaseq-de/logs/<log file>
```

**T5 — Preconditions not met**
```
Cannot start sub-stage 02.02.

<the resolver's missing entries, or the wrapper's failures, verbatim>

<what the user must do: complete 02.01 / fix the design / complete the config menus>
```

**T6 — Complete**
```
Sub-stage 02.02 complete.

| Output | Path |
|---|---|
| DE results | run/tables/de_results.csv |
| Normalized counts | run/tables/normalized_counts.csv |
| Figures | run/figures/ (pca.png, volcano.png, ma_plot.png) |
| Report | run/report.md |

Genes tested: <n> | Significant at padj < 0.05: <n>

This is the last automated sub-stage for rnaseq_bulk. For anything further — a signature
score, a custom figure, an integration — ask for a custom analysis: stage 03 drafts a plan
for your approval and runs it against these artifacts by type.
```

## OUTPUT
Written to `projects/<project_title>/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/`:

| Artifact | Contents |
|---|---|
| `STATUS` | Sub-stage state. The authority on completion. |
| `scripts/run_de.py` | The generated analysis, inputs frozen in. Re-runnable by hand. |
| `submit.sh` | The generated batch script: adaptation, then analysis. |
| `adapted/` | `counts_gene.tsv` (identifier renamed to `gene`), `gene_id_to_name.tsv`. |
| `reproducibility/` | `manifest.json` (input checksums, template commit), `commands.sh`. |
| `logs/` | The scheduler's stdout/stderr. |
| `OUTPUTS.tsv` | `de_results` native, `counts_gene` adapted, `gene_id_map` native. |
| `run/` | `tables/`, `figures/`, `report.md`, the completion marker. |

## Human check
Open `run/report.md` and confirm the contrast reads the direction you intended —
`condition,MT,WT` means positive log2FC is higher in MT, and nothing downstream can detect a
reversed contrast. Then open `run/figures/pca.png`: if samples do not separate by the tested
condition, the DE table is answering a question your data may not be asking.
