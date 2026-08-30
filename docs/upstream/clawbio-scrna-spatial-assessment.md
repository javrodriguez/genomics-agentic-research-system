# Assessment — ClawBio's single-cell skills, and the absence of spatial

**Date:** 2026-08-29 · **Subject:** `clawbio==0.6.1` · **Question:** should GARS adopt ClawBio's
scRNA skills for its single-cell and spatial assays, or build its own?

**Answer in one line:** build our own wrappers, and mine ClawBio's for parameter-surface
knowledge — its single-cell code is **well engineered but scientifically unvalidated**, and that
is the axis GARS's own history says matters.

This is a fair assessment, not a case for a conclusion already reached. Where ClawBio is good it
is said so plainly; two of the four findings below cut in its favour.

---

## 1. Method

The rubric is the one GARS proved on this same dependency in
[`clawbio-rnaseq-de-defects.md`](clawbio-rnaseq-de-defects.md): read the source, test the declared
handoff, and hunt specifically for results that are **wrong but silent**. A skill that crashes is
cheap; a skill that returns a complete, plausible, wrong answer is the one that costs a career.

Evidence gathered: `clawbio-0.6.1-py3-none-any.whl` pulled from PyPI and unpacked; all 95
`catalog.json` entries read; the single-cell skills' source and test suites read directly.

## 2. What exists

| Skill | Status | Tier | `ci_tested` | `benchmark_validated` | What it is |
|---|---|---|---|---|---|
| `nfcore-scrnaseq-wrapper` | mvp | cli-registered | ❌ | ❌ | wraps nf-core/scrnaseq **4.1.0** |
| `scrna-orchestrator` | mvp | cli-registered | ❌ | ❌ | Scanpy QC → clustering → markers (61 KB) |
| `scrna-embedding` | mvp | cli-registered | ❌ | ❌ | scVI/scANVI batch integration (40 KB) |
| `cell-detection` | planned | tested | ❌ | ❌ | Cellpose segmentation on microscopy images |
| `skill-builder` | planned | ci-validated | ✅ | ❌ | scaffolds a ClawBio skill from a spec |

**Spatial transcriptomics: nothing.** `grep -i spatial` across all 95 catalog entries returns zero
matches. Spatial is a build from scratch regardless of what is decided about single-cell.

## 3. Findings

### Finding 1 — the engineering quality is genuinely good *(in ClawBio's favour)*

`nfcore-scrnaseq-wrapper` ships **25 test files, ~8,000 lines**, including five successive rounds
of audit tests, plus dedicated suites for path remapping, bundle portability, resume policy and
provenance. That is more test code than GARS's entire deterministic-core suite (1,408 lines).

Its exception discipline is clean: the only three swallowing `except: pass` blocks are in process
termination (`killpg`, and a `taskkill` branch for Windows), where swallowing `ProcessLookupError`
on an already-dead process is the correct behaviour rather than a lapse.

`scrna-orchestrator`'s suite (36 tests) covers end-to-end runs, 10x Matrix Market and `.h5ad`
inputs, a tiny-dataset PCA edge case, actionable rejection messages, and it exercises real
**PBMC3K** data with a synthetic fallback. This is not slapdash work.

### Finding 2 — the known silent-defect pattern is absent here, but systemic elsewhere

The `rnaseq-de` defect #2 — `reset_index().rename(columns={"index": ...})`, a silent no-op when
the index is named, which anonymised every gene in a published DE table — **does not appear in any
single-cell skill.** They are clean of it.

It does appear in two others: `proteomics-clock` (`"organ"`) and `methylation-clock`
(`"sample_id"`, `"clock"`). The defect class GARS reported upstream is therefore **systemic rather
than isolated**, and is worth adding to that report. It is not, however, a mark against the
single-cell code.

### Finding 3 — the tests verify shape, never scientific correctness *(the decisive finding)*

Reading `scrna-orchestrator`'s 36 test names end to end: they assert output files exist, schemas
match between CSV and TSV, flags are whitelisted, bad inputs are rejected with actionable
messages, `commands.sh` quotes its paths. Every one is a test of **software behaviour**.

Not one asserts a **biological result is correct**. There is no test that clustering recovers
known PBMC cell types, that markers match a published reference, that the scVI embedding preserves
known structure, or that any number matches an external ground truth.

This is exactly the gap `rnaseq-de` fell through. That skill is `ci_tested: true` and carries
ClawBio's **highest** maturity tier, `ci-validated` — and it still published a `log2FoldChange`
column correlating **0.33** with its own normalized counts, with a gene at `padj` ≈ 1e-12 reported
as a 1.04× change. Its unit tests passed throughout, because unit tests confirm the code does what
the author coded; they cannot notice that the estimator is the wrong estimator.

`benchmark_validated: false` on **all 95 skills** is ClawBio's own label for this, not our
inference. Nothing in the library has been checked against a known-correct answer.

**Consequence for us:** test volume is not evidence of scientific reliability, and the tier field
is actively misleading — the highest-rated skill in the library is the one demonstrated to be
wrong. Adoption cannot be justified by either signal.

### Finding 4 — the architecture is ~40× heavier for the same contract

| | ClawBio `nfcore-scrnaseq-wrapper` | GARS `nfcore-atacseq-wrapper` |
|---|---|---|
| Modules | ~12 | 1 |
| Main script | 50 KB | 324 lines |
| Preflight | 66 KB separate module | inside the file, shared via `wrapperlib.py` |
| `SKILL.md` | 54 KB | 1 KB |

Both meet the same behavioural contract. Decision [0028](../decisions/0028-wrappers-are-thin-system-helpers.md)
already ruled on precisely this: clone the *behaviour*, not the *architecture*. The module count
was ClawBio's shape, not the contract's requirement.

## 4. Verdict

**Do not take ClawBio's single-cell skills as dependencies. Do read them as reference material.**

Reasoning, in order of weight:

1. **Adoption would import an unvalidated scientific artefact** into a system whose entire claim
   is that its results are checked (finding 3). GARS's credibility rests on being able to say how
   each number was verified; a dependency that has never been benchmarked cannot support that
   sentence.
2. **Two standing decisions would have to be reversed** — [0012](../decisions/0012-gars-authored-wrappers-live-in-system.md)
   routes every new assay through GARS-authored wrappers, and [0029](../decisions/0029-the-clawbio-path-is-deprecated.md)
   retired the ClawBio path for rnaseq after live numerical validation. Nothing found here is
   evidence to reopen either.
3. **The cost of building is low** — `wrapperlib.py` means a new wrapper is a ~300-line diff of an
   existing one, not a 2 MB project (finding 4).
4. **Spatial is a build regardless**, so adopting for single-cell only would leave the two new
   assays on different idioms — the exact inconsistency 0029 closed.

**What is worth taking, with credit:** the parameter-surface knowledge encoded in ClawBio's
preflight and `nfcore_4_1_0_contract.py` — protocol/aligner combinations, barcode whitelist
handling, the expected shape of nf-core/scrnaseq's outputs. That is real, hard-won, and reading it
will save mistakes. Reading is not depending.

**One thing to send upstream:** finding 2 — the `reset_index` defect class appears in two further
skills. The existing draft report is already written and unfiled; this belongs with it. Filing is
a person's decision, not an agent's.

## 5. What this implies for the build

- Target **nf-core/scrnaseq 4.2.0** (released 2026-07-04), not ClawBio's 4.1.0. No reason to
  inherit a lag.
- **nf-core/spatialvi has no published releases at all** — verified against the GitHub releases
  API, which returns an empty list. Any spatial support pins a commit SHA and must say so; the
  alternative is implying a stability that does not exist.
- The methodology skill this work produces must make **benchmark validation a required gate**,
  not an optional field. Finding 3 is the whole argument for it: a maturity tier that can be
  earned without ever checking an answer against truth is a tier that misleads.
