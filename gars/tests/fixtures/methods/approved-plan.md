# Analysis plan: fixture-followup

Status: APPROVED 2026-09-29

An analysis runs only after a person has read this file and approved it. Edit anything;
approval is what freezes it. After approval the plan is the record of intent -- change of
mind means a new analysis, not a quiet edit.

## Goal
Synthetic fixture: tabulate the fixture differential expression table by adjusted p-value.

## Inputs
Artifact types resolve through each sub-stage's OUTPUTS.tsv at execution time; the paths
below are what they resolve to today.

| Artifact type | Resolved from | Path |
|---|---|---|
| de_results | 02_bioinformatics/rnaseq_bulk/02_rnaseq-de | run/tables/de_results.csv |

## Method
1. Read the fixture table with the Python standard library (gars-bio).
2. Write one row per gene with its adjusted p-value; no input is modified in place.

## Outputs
Types come from the closed vocabulary in _references/artifact_types.md.

| File | Type | Description |
|---|---|---|
| results/table.tsv | table | synthetic fixture table |

## Execution
Runs: batch
Expected wall time under a minute; output under one kilobyte.
