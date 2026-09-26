---
date: 2026-09-26
status: standing
kind: decision
touches:
  - docs/decisions/0089-row-3-second-sealed-run.md
symptoms:
  - 0089 states the second seal's class spread only as inferred from the killing tests, because the sealer's notes were unread until it was committed
---
# Row 3's second seal: the sealer's own class draw (addendum to 0089)

[0089](0089-row-3-second-sealed-run.md) recorded the second sealed run (10/10 killed at `8744978`) and inferred the class spread of the draw from the killing tests alone, because 0088's blindness rule kept the sealer's notes closed until 0089 was committed.
0089 is committed and its bytes are not edited; this addendum records what the sealer's own notes say, and it confirms the inference.
The number is from the row 3 follow-up's reserved block, written on the coordinator's ruling under the owner's standing delegation of 23 Sep 2026.

## Context

The sealer's notes are `SEAL-NOTES.md` in the second seal's kit, SHA-256 `cba6e58b662ebcdb2a200cb24b85defe09f2c76360b86653e81ad9861e33be72`, the hash anchored in the private repository before the census (0088, anchor A).
They were first read after 0089's commit, as 0088's blindness rule required.

## Decision

**The sealer's own draw, from its mutant table.**
All ten mutants attack R-164.
M01-M07 are one parameter-builder fault in each of the seven nf-core wrappers (ATAC-seq peak type, ChIP-seq reference publication, CUT&RUN controls, methylseq aligner, RNA-seq index swap, single-cell chemistry, spatial QC threshold).
M08 breaks prepare idempotence: repeated identical prepare calls accumulate parameters instead of rewriting `params.yaml` with identical bytes.
M09 breaks resume after interruption: the generated script omits `-resume` and repeats a completed side effect.
M10 removes the pre-push hook's veto on positive suite failure codes.
No mutant in the draw is a keyed-lookup or a boundary fault.

**What this changes.**
Nothing in 0089's score, binding or exit statement.
It turns 0089's inferred reading into the sealer's stated one: the concentration is in the draw itself, not only in which tests caught it, so this run says nothing about keyed lookups or boundaries and little about failure-path recovery beyond M08 and M09.

## What this does not close

- Everything 0089 lists stays open: public credibility needs an `external_human_seal`, the README's evidence cells stay `unmeasured`, and ten mutants remain one small draw.
- A draw that samples keyed lookups and boundaries would need a separately sealed, pre-registered run; none is planned by this record.

## Test

This record changes no code.
`shasum -a 256 <kit>/SEAL-NOTES.md` prints `cba6e58b662ebcdb2a200cb24b85defe09f2c76360b86653e81ad9861e33be72`, the hash anchored before the census, and its `## Mutant table` lists M01-M10, each naming R-164, with the files and intents summarised above.
With this record placed and `bash docs/decisions/build_index.sh` re-run, `python3 tests/test_decision_links_resolve.py` passes.

## Status

standing

## Date

2026-09-26
