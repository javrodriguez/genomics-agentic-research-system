---
name: create-bioinformatics-skill
description: >
  The method for turning a bioinformatics pipeline into a skill an agent can run safely —
  and the tool that scaffolds and verifies one. Derived from six GARS wrappers and four
  recorded upstream defects, not invented.
metadata:
  openclaw:
    source: gars
    requires:
      bins: [python3]
      python: ">=3.6 (stdlib only)"
---

# create-bioinformatics-skill

You have a bioinformatics pipeline. You want an agent to run it for you — reliably, on other
people's data, without you watching. This is how.

The method below is not a style guide. Every rule in it exists because something went wrong
once, in a real run, and is named where it came from. Follow it and you get a skill that fails
loudly instead of quietly, that a stranger can reproduce, and that GARS's router can dispatch.

```
python3 create_bioinformatics_skill.py conform  <wrapper dir | wrappers dir>
python3 create_bioinformatics_skill.py scaffold --spec <spec.json> --out <wrappers dir>
```

---

## Part 1 — Why any of this (first principles)

Strip away the biology and an agent-run pipeline has exactly **four** irreducible problems.
Every requirement in Part 2 traces to one of them. If you are adapting this method to a system
that is not GARS, keep the four and re-derive the rest.

### P1. The agent must not improvise

An agent handed a task will help. That is the danger. GARS's first live test carried both a
workspace-level "do not improvise steps it does not specify" **and** an explicit failure branch
in the contract. Given a path with no FASTQs, the agent searched subdirectories, read a
colleague's sample sheets, and volunteered an analysis of an unrelated experiment. *Both
instructions were present. Both were ignored.*

What works is naming the forbidden action literally — "do not read sample sheets, settings
files, QC reports, or pipeline outputs found there." **Scope is bounded negatively and
specifically, or it is not bounded.**

### P2. A wrong answer must not be able to look like a right one

This is the one that matters. A pipeline that crashes costs an afternoon. A pipeline that
returns a complete, plausible, wrong table costs a paper — or a career.

It is not hypothetical. A dependency GARS relied on published a `log2FoldChange` column that
correlated **0.33** with its own normalized counts; a gene at `padj` ≈ 1e-12 was reported as a
1.04× change. No error, no warning, a perfectly well-formed CSV. It surfaced only because an
unrelated line happened to crash. A separate defect in the same chain silently dropped every
gene identifier, producing a complete DE table in which every row was anonymous.

Therefore: **every gate checks content, never existence.** "The file is there" proves nothing.
"Every sample in the samplesheet appears in the count-matrix header" proves something.

### P3. A run must be reproducible by someone who is not you

Six months later, or on another machine, the same inputs must give the same outputs — and it
must be possible to say *what produced this number*. That means pinning the pipeline, pinning
the environment, and recording the model, because in an agent-run system **the model is part of
the toolchain**. A project that cannot name the model that executed it is not reproducible by
its own standard.

### P4. A failure must be recoverable without a human decoding it

Failures are normal: a node dies, a job is preempted, a reference is missing. The wrapper's job
is to make the failure *legible* — a structured error naming the check, the detail, and the fix
— and to make recovery native rather than bespoke. A guard that cannot resume a crashed run is
a bookkeeping limitation being passed off as a safety feature.

---

## Part 2 — The method

Nine steps. Steps 1–3 are thinking; 4–8 are building; 9 is the gate.

### Step 1 — Name the assay and find its pipeline

Prefer wrapping a maintained community pipeline (nf-core and similar) over porting a bespoke
one. GARS assessed this directly: porting a 13,113-line in-house pipeline was *feasible* — only
~145 lines were site-locked — but the mechanical edits were never the cost. The real costs were
a tool matrix no single environment can satisfy, runtime package installation, a reference
bundle to build, and inheriting a fork of someone else's science.

Record the **pinned version**, and verify it exists. If the pipeline has no release, say so in
the SKILL.md and pin a commit SHA — never imply a stability that does not exist.

### Step 2 — Decide what is a *user decision* and what is a *derived fact*

This is the highest-leverage step, and the easiest to get wrong.

A **user decision** is anything where a wrong value produces *confident, wrong biology rather
than an error*: the reference genome, a DE formula, a contrast, a peak type. These are never
defaulted. They come from closed menus, not free text, so a typo cannot become a silent
mis-analysis.

A **derived fact** is anything computable from a decision already made: an index path, a mito
contig name, a genome size. These are never hand-typed — choosing a genome should set every
fact that follows from it, so they cannot be mismatched.

### Step 3 — Declare the artifacts, from a closed vocabulary

List what the sub-stage produces, using the shared vocabulary (`_references/artifact_types.md`).
**Closed means closed:** if you need a type that does not exist, extend the vocabulary through
its own sanctioned route and say why. Inventing one privately defeats the point — the value is
that a consumer can rely on a name meaning one thing.

Then pick the one artifact whose **content** proves the run was complete. Usually a matrix whose
header must contain every sample. That is your content gate (P2), and the scaffold refuses a
spec without one.

### Step 4 — Scaffold

```bash
python3 create_bioinformatics_skill.py scaffold --spec myassay.json --out ../wrappers
```

The spec is small JSON: `assay_id`, `wrapper_name`, `substage`, `pipeline`, `pipeline_version`,
`samplesheet_header`, `required_config_keys`, and `artifacts` (each with a `type`, a `path`, and
exactly one carrying `content_gate: true`).

It writes the wrapper module and its `SKILL.md`, and **prints the registry rows for you to paste
by hand.** It does not edit shared registries itself: those files are reviewed, and a generator
that rewrites them turns a review into a merge conflict.

### Step 5 — Fill the three verbs

A wrapper is **one stdlib Python file** exposing exactly three verbs. Not twelve modules — the
module count was somebody else's shape, not the contract's requirement. (A reference
implementation of the same contract elsewhere runs ~12 modules and 2 MB; the GARS equivalent is
324 lines, because everything an assay does *not* get to vary lives in `wrapperlib.py`.)

| Verb | Does | Writes | Must never |
|---|---|---|---|
| `check` | preflight: config, samplesheet, pinned checkout, executor config, output dir | `preflight/check_result.json` | fix anything it finds |
| `prepare` | re-validates, then generates `params.yaml`, `submit.sh`, reproducibility bundle | deterministic bytes | be composed by the agent |
| `collect` | the exit gate, after the job finishes | `OUTPUTS.tsv`, `STATUS` | infer state from output files |

Three rules inside them, each from a scar:

- **`submit.sh` is generated by code, not written by the agent.** It is a deterministic
  artifact, so it is code's job; the requeue guard ships inside it and cannot be
  mis-transcribed.
- **`prepare` lists every parameter the pipeline receives.** The agent never composes one. A
  missing parameter is a config or wrapper change to report — never a flag to add.
- **Crash recovery is the workflow engine's native `-resume`.** Do not invent manifest-gated
  replay; a wrapper that refuses to resume a crashed run has turned its own bookkeeping into a
  dead end.

### Step 6 — Write the exit gate as a content check

The gate is the whole point of the skill. Existence checks are theatre.

Concretely: read the count matrix header and assert **every sample token** from the samplesheet
appears in it. Check the group *and* replicate, not the bare group — otherwise a lost replicate
hides behind its surviving sibling. Fail naming exactly which are missing.

### Step 7 — Write the sub-stage contract

The wrapper computes; the contract governs what the agent *says and does around it*. Eight
sections, in order (`_references/contract_standard.md`): Purpose · Inputs · **Scope Boundaries**
· Definitions · Process · **Response Format** · OUTPUT · Human check.

Three of them are load-bearing and must not be simplified away:

- **Scope Boundaries**, stated negatively and specifically (P1).
- **Response Format** as fixed templates `T1…Tn` — free-form replies vary every run and bury
  decisions in prose. A template that ends by asking is a **wait point**: the agent sends it and
  stops. So two templates must never ask the same thing, and two consecutive steps must never
  both send one — a real contract shipped exactly that bug, and the menu the user needed was
  never rendered.
- **Human check** — exactly one thing a person *does*, concrete enough to act on ("read the
  FRiP and confirm per-sample peak counts are the same order across replicates"), never "review
  the output". A vague human check is no gate at all.

### Step 8 — Test offline, then for real

Offline first: the wrapper's whole `check`/`prepare` path runs with no cluster and no pipeline
present, in a throwaway workspace. Assert **determinism** — same inputs, byte-identical outputs
— because that property is the entire justification for generating artifacts in code.

Then the real thing. **Honest miniaturization is real pipeline + small public inputs**
(`-profile test`). A mocked pipeline is not a test, it is a lie with a green tick.

### Step 9 — Conform, then benchmark

```bash
python3 create_bioinformatics_skill.py conform ../wrappers/my-new-wrapper
```

`conform` mechanically enforces what Part 2 can only ask for: one module, stdlib-only, py3.6
syntax, `wrapperlib` used, the four exit codes, `ASSAY`/`SUBSTAGE` declared, the pin **derived**
rather than restated, all three verbs present, `--model` accepted, `OUTPUTS.tsv` and `STATUS`
written, writes atomic, `SKILL.md` frontmatter complete.

The rules are trustworthy because they are run against wrappers already known good — **every
existing GARS wrapper passes** — and because each rule is mutation-tested: break it deliberately
and the linter must go red. (One rule originally tested a substring, and a mutation renaming the
flag slipped past it. That is why the check now matches a complete quoted flag.)

**Then the step no linter can do for you.** `conform` proves the skill is well-formed. It cannot
prove the answer is right. Validate at least one number against something external — a published
result, an independent reimplementation, a naive calculation from the same inputs.

This is not optional ceremony. The dependency that published a 0.33-correlated fold-change
column carried its library's *highest* maturity tier and passed its own CI. Its unit tests
confirmed the code did what its author coded; they could not notice that the estimator was the
wrong estimator. **A tier that can be earned without ever checking an answer against truth is a
tier that misleads.** Write down what you validated against, and where it disagreed.

---

## Part 3 — The checklist

A skill is done when every line is true.

- [ ] Pipeline pinned to a version that exists; a SHA pin says it is a SHA pin
- [ ] Every user decision comes from a closed menu; nothing biologically load-bearing defaults
- [ ] Every derived fact follows from a decision, hand-typed nowhere
- [ ] Artifacts declared from the closed vocabulary; extensions went through the sanctioned route
- [ ] `check` validates and fixes nothing
- [ ] `prepare` generates `submit.sh` and `params.yaml`; the agent composes neither
- [ ] Exit gate checks **content** — every sample provably present
- [ ] `OUTPUTS.tsv` and `STATUS` written; state is never inferred from output files
- [ ] Structured failures: check, detail, fix
- [ ] `--model` recorded in the history entry
- [ ] Offline test passes, and proves determinism
- [ ] A real run on real (possibly small, public) data completed
- [ ] `conform` passes
- [ ] **At least one number validated against something external, and the comparison written down**

## Provenance

The behavioural contract is decision 0028. Wrapper homes are 0012. The silent-defect lessons are
0010, 0021 and `docs/upstream/clawbio-rnaseq-de-defects.md`. Contract sections and their scars
are `_references/contract_standard.md`. The artifact registry is 0007; the model-as-provenance
rule is 0024; menus-not-free-text is 0020. Nothing here was invented for this document; the
first-principles frame in Part 1 is the *ordering*, and the content is what six wrappers and
four defects already taught.
