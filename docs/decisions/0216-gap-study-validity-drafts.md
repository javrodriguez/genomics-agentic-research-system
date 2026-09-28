---
date: 2026-09-28
status: standing
kind: decision
touches:
  - docs/validity/
symptoms:
  - the Gap Study publishes counts per task with no argument that each task measures what it says it measures
  - no grader of the Gap Study had been read against a published checklist for agentic benchmarks
---
# Gap Study validity: a draft argument per task, and the agentic benchmark checklist run over its graders

Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and within the owner's 28 September 2026 direction that makes the AI-evaluation track a build priority (approved 15:21 EDT); no sentence in this record, and no page it adds, is the owner's.
That direction makes the owner the author of record for each validity argument, because he defends them; so everything added here is a labelled draft for his review, and nothing is presented as his view before he has read it.

## Context

The Gap Study's three rounds publish, per task and half, how many of three takes carried the correct label, and, since [0210](0210-gap-study-intervals.md), an exact interval beside each count.
No page argued, per task, that the probe measures the property the task names, that a capable agent can reach it and do the right thing, and that the label means the behaviour.
No grader had been read against a published checklist for agentic benchmarks.
The rounds are pinned instruments: their folders are copied byte for byte into later rounds' manifests, their results publish exactly as graded, and a flaw is fixed only in a pre-registered follow-up ([0068](0068-evals-round-2-incomplete-cell-correction.md)).

## Decision

1. **A new folder, `docs/validity/`, outside every study folder.**
   Six one-page arguments, one per task (`template-adherence`, `precondition-refusal`, `number-fidelity`, `scope-read`, `plan-gate`, `confounded-design`), each in the same parts: the claim, construct validity, task validity, outcome validity, known threats, what the grader can and cannot read, follow-ups.
   Every page opens with a DRAFT banner naming the lane as its writer.
2. **The checklist, from its primary source.**
   The Agentic Benchmark Checklist of Zhu et al., arXiv:2507.02825, version 5 (7 August 2025), read from its TeX source; the item ids and texts are quoted from its three checklist figures, and the page records where the paper's own tables and the authors' repository number the items differently.
   Scope: the six tasks' graders at the round 2 bytes (round 3 pins them byte-identical), the shared label reader, the driver, and the first study's classifier that `confounded-design` imports.
   Result: of 43 items, 13 met, 14 met in part, 5 not met, 11 not applicable; those 19 findings, and the threats the six pages name, map to 18 proposed follow-ups.
3. **Every claim about a grader cites `path:line` at `37a8d94`.**
   The cited study files are frozen by their rounds, so the lines do not move.
4. **Mechanisms are shown, never asserted.**
   `docs/validity/probes.py` (standard library only) builds one synthetic take per probe from the pre-registered operator lines and runs it through the committed grader, with bytecode writing switched off so nothing lands in a study folder; `--check` fails unless every probe returns the label the pages state.
   A probe shows that a reply of a given shape gets a given label; it reads no transcript and no results file, and says nothing about how many published takes had that shape.
5. **Findings go to follow-ups only.**
   `docs/validity/follow-ups.md` lists each, with the direction the error moves a label, and proposes a follow-up to be pre-registered before it runs; none edits a grader, label, fixture, results file or table.
6. **No between-model sentence, no rate.**
   The pages name no model and restate no count as a percentage.

## Rejected alternatives

- **Correcting the graders the probes show to be weak.** They are frozen; a fix belongs to a later, pre-registered instrument.
- **Counting how many published takes each weakness touched.** That reading is itself a study with a design to freeze first; it is proposed (F-01 to F-08), not done here.
- **Reconstructing the checklist from a secondary summary.** The items are quoted from the paper's own source, with its version.
- **Publishing the arguments as the owner's.** He defends them; they are his only after he has read them.
- **A CI job for `probes.py --check`.** It would touch a protected path for a draft; wiring it is the owner's call at sign-off.

## What this does not close

- **The owner's reading.** Until he signs each argument in a later commit, the pages are drafts, and the checklist's R.5 and R.11 rows read "in part".
- **A leak for later rounds.** These pages name every probe; a later round must add `docs/validity/` and this record to the paths its checkout excludes (F-11).
- **The graders not assessed**: the five-task benchmark, the planted-fault harnesses, the smoke gate, Layer B and the permission pre-study (`evals/haiku-prestudy/`) (F-15).
- **Whether an argument is right.** The checks below bind the citations, the checklist's text and the probes' labels; they cannot bind the reasoning, which is the reviewer's and, finally, the owner's.

## Test

`python3 docs/validity/probes.py --check` runs 28 probes and exits 0 only when each returns the label the pages state; a changed expectation, or a grader that returned another label, makes it exit 1.
The lane's citation check resolved every `path:line` in `docs/validity/` against a clean archive of the branch head and matched each against the text it was cited for; its checklist check matched every item id and text against the version 5 source.
The fault that must make the probe check fail is any edit to a cited grader that changes one of the labels the pages report.

## Status

Standing, as a record of drafts.
The pages are the lane's until the owner signs them; the public push waits on the owner's word.

## Date

2026-09-28
