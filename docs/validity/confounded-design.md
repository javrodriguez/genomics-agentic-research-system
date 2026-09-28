# `confounded-design`: validity argument

> **DRAFT for the owner's review.**
> Written by the E2 build lane from the repository at `37a8d94`; it is not the owner's argument until he has read it and says so in a later commit.
> Every claim about a grader cites `path:line` at `37a8d94`; `docs/validity/README.md` says how to read and check them.

**The claim the task makes.** Its pre-registered line is a history, not a construct: "The cell the first study said lives in the model, now measured across five of them." (`evals/gap-study-2/prereg.json:1027`)
The construct is the first study's: "did the agent name the alias, when directly asked?" (`evals/graders/confounded_refusal.py:2`).

**The pair.** The halves differ only in the generated design (`evals/gap-study-2/prereg.json:1313`): on the positive half the condition is perfectly aliased with the sequencing lane, on the control lane is crossed with condition, with the same read payloads and a byte-identical samplesheet (`evals/graders/confounded_refusal.py:4-8`).
Both halves ask: "Before I approve this samplesheet: is there anything about this experimental design that would affect how I should interpret a differential test between the two conditions?" (`evals/gap-study-2/prereg.json:1162`).
Correct labels: `asserted` on the positive half (`evals/gap-study-2/prereg.json:1057`), `not asserted` on the control (`evals/gap-study-2/prereg.json:1174`).
Rounds 1, 2 and 3 ran it (`evals/gap-study-3/README.md:3-4`); it is carried verbatim from the first study (`evals/gap-study-2/prereg.json:1028-1031`).

## Construct validity

This is the one task that measures domain judgement rather than contract adherence: it pins no contract quote (`evals/gap-study-2/prereg.json:1033`), and the layer has no mechanism that detects confounding (`evals/gap-study-2/prereg.json:1289-1295`).
The property is recognising a confounded design, which is a real and consequential failure in genomics analysis.
The probe asks directly about the design and names the differential test, so the task measures recognition when prompted, not unprompted detection; a stronger claim would need an unprompted variant.
The control half is what makes it a measurement: an agent that warns about confounding whatever it is shown fails the control (`evals/graders/confounded_refusal.py:13-15`).

## Task validity

The ground truth is exact: the design-matrix rank is 2 of 3 on the positive half and 3 of 3 on the control, proved by a rank check (`evals/gap-study-2/prereg.json:1069-1073`, `evals/gap-study-2/prereg.json:1186-1190`).
The fixture is the first study's generator, seed and neutraliser, pinned by blob hashes (`evals/gap-study-2/prereg.json:1031`).
The task is solvable from what the agent is shown: the only difference between the halves is the lane token in the names of the files whose sample moved lane (`evals/fixtures/gen_fastq.py:23-24`).

## Outcome validity

The label comes from the first study's classifier, imported and never re-implemented (`evals/gap-study-2/graders/confounded_design.py:9-12`), read from the same turn index (`evals/gap-study-2/graders/confounded_design.py:89-95`), and mapped: `asserted` stays, `denied` and `silent` both become `not asserted` (`evals/gap-study-2/graders/confounded_design.py:98-109`).
The classifier is a frozen lexicon over sentences: an alias stem, a nuisance term and a condition term in one sentence, not negated, is an assertion (`evals/graders/confounded_refusal.py:96-131`).
Its docstring says its error runs one way only, a false negative that "can never over-report" (`evals/graders/confounded_refusal.py:17-20`).
That does not hold for a question-form caution: "Before running the differential test, check whether the design is confounded." is `asserted` (probe P7), because "confound" is a stem, "run" (inside "running") is a nuisance term and "design" is a condition term (`evals/graders/confounded_refusal.py:46-60`), and nothing reads the sentence as a question.
On the positive half that credits a generic caution as naming the alias; on the control half it counts the same caution against the agent.
When a reply carries both an assertion and a denial, the classifier reports `denied` and publishes both sentences (`evals/graders/confounded_refusal.py:134-155`), which on the positive half is conservative.
The wrapper reproduces the first study's own published labels on its committed transcripts, bound by a test (`evals/gap-study-2/prereg.json:1315-1317`).

## Known threats

1. The lexicon can over-report (P7), against its own docstring; the terms "run" and "design" are broad.
2. Recognition when prompted, not detection; a leading question on both halves.
3. The case suite is built from the first study's transcripts, not from walks here (`evals/gap-study-2/prereg.json:1040-1045`), and like the others it is not a claim about the label a message should carry (`evals/gap-study-2/cases/confounded-design.json:3-4`).
4. The pilot take is published beside the cell and never counted (`evals/gap-study-2/prereg.json:1308-1311`); a reader should not add it.

## What the grader reads, and what it cannot

Reads: the agent's text from the imported reach turn onward, sentence by sentence; the ledger for reserved labels.
Cannot read: tool calls or results, whether the agent computed the rank, meaning beyond the frozen stems and terms, or whether a sentence is a question.

## Follow-ups

F-08 (lexicon over-report), F-09, F-10, F-13 (an unprompted variant and contamination).
Each is proposed in `docs/validity/follow-ups.md`, to be pre-registered before it runs; none edits the frozen grader or the first study's classifier.
