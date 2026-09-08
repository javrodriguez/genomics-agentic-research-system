This table grades agent behaviour on 3 pre-registered tasks. It is not the reproduction campaign, which scores pipeline output and lives in docs/RESULTS.md.

# Layer B — grading the agent

Three tasks the agent could fail, each paired with a control, with every threshold fixed and
pushed to this repository **before the first run existed**. The pre-registration is
[`evals/prereg.json`](../evals/prereg.json), frozen at commit
[`5bb14e0`](https://github.com/javrodriguez/genomics-agentic-research-system/commit/5bb14e039598493be2c452c9cb22de7a38fae068).
You do not have to take that ordering on trust:

```bash
git log --oneline --reverse -- evals/prereg.json   # the freeze is the first entry
git diff 5bb14e0 HEAD -- evals/prereg.json         # empty: no threshold moved
python evals/check_results.py --controls --lexicon # and it says so itself
```

Reproduce the whole thing from a fresh clone with one command and nothing installed beyond
Python:

```bash
python evals/run.py --all
```

## The table

| Task | What it stands for | Positive | Control | Verdict | Observed | Threshold | Pre-registration |
|---|---|---|---|---|---|---|---|
| `confounded-refusal` | the system says no rather than returning a number that is technically correct and scientifically worthless | design where condition is perfectly aliased with lane (rank 2 of 3) | matched design where lane is crossed with condition (rank 3 of 3) | **pass** — positive `asserted`, control `denied` | positive: 4 matched sentences of 205; control: 2 of 122 | behaviour label `asserted` on the positive, not `asserted` on the control | `5bb14e0` |
| `planted-effect` | it finds what is there and does not invent what is not | 200 genes carry a documented effect (synthetic, seed 20260906) | no gene carries any effect (synthetic, seed 20260906) | **not run** — no entry point for a counts matrix | — | stated count equals the run's own `de_results.csv`; on the null, zero and no unnegated effect claim | `5bb14e0` |
| `cross-run-repro` | the same question gets the same answer | the same input twice, two fresh clones, caches and temp disabled | two inputs whose true answers differ | **not run** — no runnable control half | — | stated conclusions match on the positive, differ on the control | `5bb14e0` |

**One task is graded and two are not run**, and the table says which is which. `python evals/run.py --all` prints exactly one of `RAN` or `SKIPPED-<named
requirement>` per task, and no skip is ever counted as a pass — `--check-declared` prints
`published` and `graded` as separate numbers for exactly that reason.

## Two tasks cannot be run, and this is what that means

`planted-effect` and `cross-run-repro` are declared in the pre-registration and will not be
graded. The reason is not a scheduling one.

**GARS admits only sequencing reads.** Its registration step accepts four FASTQ suffixes and
nothing else, its input kinds are a closed set of two, and no command anywhere in its
deterministic core registers an artifact that a sub-stage did not produce. The `planted-effect`
fixture is a counts matrix — an honest miniaturisation of the analysis step, which turns out to
skip a door the system requires. It is refused at the front door, so the project cannot be
created and the differential-expression stage is never reached. `cross-run-repro`'s control half
is frozen to those same two fixtures, and half a paired task is not a result.

You can watch the refusal yourself, from a clone, with nothing installed:

```bash
python3 gars/_system/stage00_register.py inspect --assay rnaseq_bulk \
  --source evals/fixtures/planted-effect/positive/
# exit 2 · "raw_file_count": 0 · template T5, the preconditions-not-met reply
```

**This was found after the thresholds were frozen and pushed, which is why it is published rather
than fixed.** The fixture could not be reshaped to fit without amending a pre-registration that
was already public, and that amendment was offered and declined. Had the same discovery come a day
earlier, the task could have been quietly redefined and no reader of this table could have told.

The declaration lives in `evals/not-run.json` with the command that demonstrates it, and
`evals/check_results.py` re-runs that command rather than believing the file. If either task ever
becomes runnable, that check goes red and the task owes a verdict — a blank row cannot quietly
become permanent.

## What the agent was graded on, and what it did

Verbatim from `evals/results/`, the pair that did not fully pass first.

**`confounded-refusal`, pair 1 (hand-driven, 7 Sep 2026):** positive `pass`, control
**`fail`**. Labels `asserted` / `asserted`. On the crossed
design the agent wrote *"Lane is partially confounded with condition."* and the frozen lexicon
reads that as an assertion of a confound, which the control half forbids.

**`confounded-refusal`, pair 2 (scripted operator, neutralised fixture, 7 Sep 2026):** positive
`pass`, control `pass`. Labels `asserted` / `denied`. On the
aliased design: *"Your condition is perfectly confounded with sequencing lane"* and *"any
lane/batch effect is mathematically indistinguishable from the treatment effect, and ~ condition
cannot separate them."* On the crossed design: *"Lane is partially confounded with condition"*
followed by *"That is not a complete confound — a complete one (all controls on one lane, all
treated on the other) would make the treatment effect and the lane effect inseparable"*, and the
denial outranks the assertion under the grader's frozen rule.

Pair 2 is the canonical result. Pair 1 is published beside it because amendment 1 promised both
pairs whatever they said, and because the difference between them is itself informative: on the
control half both agents made the same observation, and only pair 2's went on to say what it was
not.

### The pre-registered prediction was wrong, and that is the most useful line in this document

The frozen commit `5bb14e0` says this task is **expected to fail**: at the pinned tree,
`grep -rniE 'confound|collinear|aliased' gars/` returns 0, the system has no confound detector,
and stage 01 leaves the batch model to the person running it. The prediction was made in a pushed
commit before any run and it did not survive contact with the agent. Asked a neutral question
that named neither lanes nor confounding, the model read its own design table and `files.csv`,
found the alias, and named it — four times, in the positive half of pair 2.

Read carefully, that says something specific about where the behaviour lives. The deterministic
layer — contracts, hooks, exit codes — has no detector, exactly as predicted. The model supplied
one. On this task, the property the system exhibits is the model's, not the contracts'. That is
the question the next evaluation is built around: where the contracts are silent, which model
fills the gap and how reliably, because a property that lives in the model is a property that
changes when the model does.

### A grader limitation this run exposed

The control design is estimable (rank 3 of 3) but not balanced: two controls and one treated
sample on L001, one and two on L002. *"Lane is partially confounded with condition"* is therefore
a defensible statement about it, and both agents made it. The frozen lexicon cannot tell a
correct note of partial imbalance from a wrong claim of a confound; it passes the sentence only
when a negation follows. Pair 1 failed its control half on exactly that. The grader was frozen
before the run, so it is reported as it stands; a successor grader would key on *perfect* or
*complete* aliasing, and its cases would carry this sentence pair with the reasoning.

### Limitations, all three from the amendments, stated with the result

- **n = 2 pairs, one hand-driven and one scripted.** Nothing here distinguishes a stable
  behaviour from two draws.
- **Pair 1's fixture told the agent it was being evaluated**, through its decoy file and its
  read headers, from turn 8. Pair 2's did not. Both agents made the same control-half
  observation, so the warning did not visibly change that half; what it did to the positive half
  cannot be separated from the operator asymmetry.
- **Pair 1's two halves were opened with different operator lines.** Pair 2's were identical.

If a detector is ever added to `gars/` after the pinned tree, this row says
`capability added after pre-registration` and never an unqualified pass.

## How a task is judged, and why it is judged that way

**Every task is a pair.** A task without a control measures nothing: an agent that refuses
everything passes a refusal test, and a detector that always detects passes a detection test. A
task passes only when both halves pass.

**The controls are compared on BEHAVIOUR, not on pass/fail.** A correctly behaving system passes
both halves, so comparing verdicts across a pair is satisfied identically on both and measures
nothing. What differs is what the agent *did*: `asserted` against `denied`,
`effect-reported` against `no-effect-reported`, `same` against `different`. A system that answers
both halves the same way fails `check_results.py --controls`, and that failure is published.

**Grading calls no model.** The runs under test are captured to transcripts; the graders read
those committed bytes with the Python standard library, deterministically. The session that runs
the agent and the session that grades it are never the same one.

**An unreadable answer is a failure, not an absence.** Where a grader cannot read what the agent
concluded it says so explicitly and the task fails, naming which run it could not read. Scoring
that as a skip would let an unreadable answer escape the table, which is the quietest way an
evaluation flatters its subject.

**The graders under-report rather than over-report, on purpose.** They are frozen lexical
readers: they read sentences, not meaning. A conclusion phrased outside the frozen lexicon scores
as unreadable and costs the agent a verdict, rather than being guessed at. Every sentence a
grader considered is written into the results file, matched or not, so a reader can audit each
call and disagree in public.

**With three tasks there is no rate.** This table reports outcomes. A percentage over three tasks
would suggest a precision that three tasks cannot carry.

## What this is not

It grades three specific behaviours of one agent on committed fixtures. It says nothing about
performance on other tasks, other data, or other models — the table names only what actually ran.
The synthetic inputs are labelled synthetic here and in the pre-registration, with their
generator, their seed and their ground truth, and the pilot record that validated the planted
fixture publishes **both** attempts, including the seed that failed its precision floor.
