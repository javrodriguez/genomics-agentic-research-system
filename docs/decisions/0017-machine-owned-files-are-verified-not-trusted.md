---
date: 2026-08-20
status: standing
touches:
  - gars/_system/workspace.py
  - gars/_system/stage00_register.py
  - gars/_system/stage01_samplesheet.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/00_initialize_project/CONTEXT.md
---
# A machine-owned file is verified against reality, not trusted

> **Correction, 2026-08-21.** The cause stated below — a truncated write from a killed process —
> was **wrong**. A second occurrence was diagnosed properly: the user had narrowed the cohort by
> hand-editing `files.csv` as well as `samples.csv`. The surviving rows were a clean subset
> (`ALL-p01`…`ALL-p10`), the do-not-edit banner was intact, and both files were modified *after*
> `finalize` had completed. It was a reasonable user action against a guard that was only a
> comment. See [0018](0018-machine-ownership-is-enforced-not-advised.md).
>
> The fixes below stand and were the right ones — the `registry` check caught this, which is
> exactly what it was built for, and atomic writes remain correct practice. Only the diagnosis
> was mistaken, and it was mistaken because I inferred a cause from file symptoms instead of
> checking mtimes and content shape.

## What happened

A real project registered 38 samples across 152 linked FASTQs. Its `files.csv` was later found
accounting for **40 of those 152 files**, and `samples.csv` holding 9 of 38 rows. Both ended
mid-record with no trailing newline.

Stage 01 read them, found them **internally consistent**, and reported `samples_total: 10,
exclusions: []`. No check failed. A truncated CSV is still a valid CSV.

The only reason it surfaced is that the agent happened to remember "38 samples" from earlier in
the same conversation. A fresh session would have emitted a 10-sample samplesheet and the analysis
would have quietly proceeded on a quarter of the cohort.

Worse, the agent then offered the user *"confirm you intended 10 samples — I continue."* Taking
that option would have shipped a corrupted cohort as a deliberate choice.

## Three faults, and the order they matter in

**1. `files.csv` was never re-checked against `raw/`.** It is machine-owned and derived from the
symlinks, but after stage 00 wrote it nothing ever compared the two again. Stage 01 validated
`samples.csv` *against `files.csv`* — two derived files agreeing with each other says nothing when
both are damaged.

Stage 01 now compares the filenames in `files.csv` against the contents of `raw/` and fails with
`registry` when they disagree, naming the remedy. This is cause-agnostic: it catches truncation, a
hand-edit, a partial write, or raw data removed after registration.

**2. Generated files were written non-atomically.** A killed process left a prefix of a file on
disk. Every generated artifact is now written to a sibling temp file, fsynced, and `os.replace`d
into position, so a reader sees the previous complete file or the new complete file — never half
of one. This matters especially here because stage 00's own exit gate would have caught the
mismatch, but the run never reached it.

**3. `finalize` overwrote `samples.csv`.** Found while testing the remedy for fault 1:
re-running finalize regenerated the user's design, destroying filled-in conditions and any
exclusion they had expressed by deleting rows. `samples.csv` is the **user's** file
([0003](0003-data-model-files-and-samples-split.md)); it is now written once, on creation, and
preserved on every later run. `files.csv` is machine-owned and is still regenerated every time.

The exit gate was relaxed to match: `files.csv` having more distinct samples than `samples.csv` is
only an error on creation. Afterwards it is an **exclusion**, which is stage 01's to confirm. The
reverse — `samples.csv` naming a sample with no rows in `files.csv` — is still an error, and is
now checked.

## The premise worth questioning

The agent caught this by *remembering a number*. That is not a check, it is luck, and it does not
survive a new session, a compaction, or a different operator.

**If a discrepancy matters, code must detect it.** The rule generalises past this bug: the
system's own derived artifacts are evidence about each other, never evidence about the world.
`raw/` is the world here. Anything derived from it is re-verified against it at the point of use,
not assumed to have survived since it was written.

This is the same failure the anonymous-genes defect had
([0010](0010-skill-chaining-defects-and-adaptation.md)): a complete, plausible, wrong artifact
that every existence check passes. The conclusion drawn there — *exit gates must check content* —
was right and was applied too narrowly.
