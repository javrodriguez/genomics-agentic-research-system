# Validity of the Gap Study

> **DRAFTS for the owner's review.**
> Every page in this folder was written by the E2 build lane from the repository at `37a8d94`.
> None of it is the owner's argument or assessment until he has read it and says so in a later commit; until then, read each page as a draft that a reviewer checked, not as a position anyone holds.

The Gap Study asks, per task, where the deterministic layer does not cover a failure mode, whether the agent catches it, in how many of three takes, on a positive half and a matched control (`evals/gap-study-2/PROTOCOL.md:3`).
Its counts, and since `37a8d94` its intervals, say how often.
This folder asks the question that comes before any count: does each task measure what it says it measures, and would its graders survive the field's checklist?

## What is here

| Page | What it holds |
|---|---|
| `template-adherence.md` | the validity argument for that task |
| `precondition-refusal.md` | the same, for that task |
| `number-fidelity.md` | the same |
| `scope-read.md` | the same |
| `plan-gate.md` | the same |
| `confounded-design.md` | the same |
| `abc-checklist.md` | the Agentic Benchmark Checklist (Zhu et al. 2025, arXiv:2507.02825 version 5) run read-only over the graders, as a findings table |
| `follow-ups.md` | every finding, each as a follow-up to be pre-registered before it runs |
| `probes.py` | the constructed replies behind every probe the pages cite, and `--check`, which fails unless each returns the label the pages state |

Each argument has the same parts: the claim the task makes; construct validity (is the property the right one, and is the probe a fair way to put it); task validity (can a capable agent reach the probe and do the right thing, and is the ground truth verified); outcome validity (does the label mean the behaviour); known threats; what the grader can and cannot read; follow-ups.

## How to read a citation

`path:N` or `path:N-M` names lines of a file at commit `37a8d94`.
Every file cited under `evals/gap-study/`, `evals/gap-study-2/` and `evals/gap-study-3/` is frozen by its round, so the lines do not move.
A probe (P1 to P11) is a constructed reply run through a grader by `probes.py`; it shows that a reply of that shape gets that label, and says nothing about how many published takes, if any, had that shape.

    python3 docs/validity/probes.py --check

The script reads the graders from their committed paths, writes nothing (bytecode writing is switched off, so nothing lands in a study folder), and uses the standard library only.

## What this folder does not do

It regrades nothing: every round publishes exactly as graded.
It compares no models: the pages name no model, and every comparative sentence about a model is the owner's.
It publishes no rate and no count as a percentage.
It edits no grader, label, fixture or results file; a finding becomes a follow-up in `follow-ups.md`, pre-registered before it runs.

## For the owner's review

The owner defends these arguments, so each needs his reading before it is his.
For each of the six arguments: sign it as his, amend it, or reject it.
For the checklist table: accept the statuses, or change any.
For `follow-ups.md`: choose which follow-ups run, in what order, and which is pre-registered first.
Also his: whether and where this folder is linked from `docs/EVALS.md`.
