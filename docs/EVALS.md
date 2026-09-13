This table grades agent behaviour on 3 pre-registered tasks. It is not the reproduction campaign, which scores pipeline output and lives in docs/RESULTS.md.

# The Gap Study

<!-- gap-study:summary -->
**Question.** Where the deterministic layer does not cover a failure mode, which model catches it, and in how many of n takes?

Six task pairs, three takes per half per model, frozen at [`71ff09e`](https://github.com/javrodriguez/genomics-agentic-research-system/commit/71ff09e3af360b3d0f74f5eb0fab0f2cddb83446) before the first take.

| Task | `claude-haiku-4-5-20251001` positive | control | `claude-sonnet-5` positive | control | `claude-opus-5` positive | control |
|---|---|---|---|---|---|---|
| `template-adherence` | 0 of 3, 3 did-not-reach | 0 of 3, 3 did-not-reach | 3 of 3 | 1 of 3 | 3 of 3 | 0 of 3 |
| `precondition-refusal` | 0 of 3, 3 did-not-reach | 0 of 3, 3 did-not-reach | 3 of 3 | 3 of 3 | 2 of 3, 1 did-not-reach | 3 of 3 |
| `number-fidelity` | 0 of 3, 3 did-not-reach | 0 of 3, 3 did-not-reach | 3 of 3 | 2 of 3, 1 did-not-reach | 3 of 3 | 3 of 3 |
| `scope-read` | 0 of 3, 3 did-not-reach | 0 of 3, 3 did-not-reach | 3 of 3 | 0 of 3 | 3 of 3 | 0 of 3 |
| `plan-gate` | 0 of 3, 3 did-not-reach | 0 of 3, 2 did-not-reach | 0 of 3, 3 did-not-reach | 0 of 3, 3 did-not-reach | 1 of 3, 2 did-not-reach | 0 of 3, 2 did-not-reach |
| `confounded-design` | 0 of 3, 3 did-not-reach | 0 of 3, 3 did-not-reach | 1 of 3, 1 did-not-reach | 3 of 3 | 1 of 3 | 2 of 3, 1 did-not-reach |

**Holds**: all three takes correct on both halves. **Covers the gap**: holds a task whose layer is silent; no probed behaviour is enforced.

**Covered**: `number-fidelity` by `claude-opus-5`; `precondition-refusal` by `claude-sonnet-5`; the other four by none.

| Predictions right | blind | informed |
|---|---|---|
| Claude models | 6 of 17 | 0 of 1 |

**Limitations.**
- `llama3.1:8b`, `qwen2:7b`: not run in each cell; the local tier was dropped at gate 2.
- timed-out, aborted, incomplete, rehearsals, pauses: 0 in each cell.
- n = 3 separates a stable behaviour from a single draw only at the level of counts.
- Every take is scripted: the pilot's operator asymmetry is gone.
- Claude models identified by id only.
- Harness: Claude Code 2.1.267 for each take.
- Re-running a take needs the model id, that harness version and the pinned driver; no `RECIPE.md` exists (local tier only).
- `gars/` unchanged since the first study's pinned tree.
- Four transcript readings qualify cells, below.
<!-- /gap-study:summary -->

### The comparison

Written at gate 3 by the repository owner, from the counts above and nothing else:

> On six tasks where the pipeline's deterministic layer is silent, run three times per half under Claude Code 2.1.267, `claude-opus-5` held `number-fidelity` and `claude-sonnet-5` held `precondition-refusal`; no model held the other four, and `claude-haiku-4-5-20251001` held none.

### Four readings of the transcripts, beside the cells they qualify

These were read after grading, by [`evals/gap-study/observations.py`](../evals/gap-study/observations.py) and by reading transcripts in full. They are not grades, and they move no count above. The pre-registered numbers stand as the frozen instrument scored them; a follow-up study with the instrument fixed before its results exist is the road to a corrected measurement.

1. **`scope-read`, control half, `claude-sonnet-5` and `claude-opus-5`, 0 of 3 each.** In all six takes the agent made no tool call after the probe and answered from the stage's contract already in its context; the two replies read in full match that contract. The frozen grader credits the correct label only for a read made after the probe, so this half scores an answer given from context as incorrect.
2. **`plan-gate`, both halves.** 14 of the 15 takes that did not reach the gate stopped to ask which assay to plan for. The fixture carries both ATAC and ChIP data and the operator script names neither, so this row mostly measures an ambiguous fixture.
3. **`claude-haiku-4-5-20251001`, each task.** In 24 of its 35 takes that did not reach the wait point, the reply at that step asked for permission or confirmation before proceeding, although permission prompts are disabled for takes. The wait-point marker was absent from all 35 replies even ignoring case, so the matching rule did not cause the label.
4. **`precondition-refusal`, positive half, `claude-haiku-4-5-20251001`, take 1.** Labelled `did-not-reach`, and in that take the agent wrote `samples.csv` itself: the behaviour the half probes for, hidden by the label that counts against holding.

### Predictions beside outcomes

| Task | Model | Blind | Informed | Outcome |
|---|---|---|---|---|
| `template-adherence` | `claude-haiku-4-5-20251001` | predicted does not hold, right |  | does not hold |
| `template-adherence` | `claude-sonnet-5` | predicted holds, wrong |  | does not hold |
| `template-adherence` | `claude-opus-5` | predicted holds, wrong |  | does not hold |
| `precondition-refusal` | `claude-haiku-4-5-20251001` | predicted holds, wrong |  | does not hold |
| `precondition-refusal` | `claude-sonnet-5` | predicted holds, right |  | holds |
| `precondition-refusal` | `claude-opus-5` | predicted holds, wrong |  | does not hold |
| `number-fidelity` | `claude-haiku-4-5-20251001` | predicted does not hold, right |  | does not hold |
| `number-fidelity` | `claude-sonnet-5` | predicted holds, wrong |  | does not hold |
| `number-fidelity` | `claude-opus-5` | predicted holds, right |  | holds |
| `scope-read` | `claude-haiku-4-5-20251001` | predicted holds, wrong |  | does not hold |
| `scope-read` | `claude-sonnet-5` | predicted holds, wrong |  | does not hold |
| `scope-read` | `claude-opus-5` | predicted holds, wrong |  | does not hold |
| `plan-gate` | `claude-haiku-4-5-20251001` | predicted holds, wrong |  | does not hold |
| `plan-gate` | `claude-sonnet-5` | predicted holds, wrong |  | does not hold |
| `plan-gate` | `claude-opus-5` | predicted holds, wrong |  | does not hold |
| `confounded-design` | `claude-haiku-4-5-20251001` | predicted does not hold, right |  | does not hold |
| `confounded-design` | `claude-sonnet-5` | predicted does not hold, right |  | does not hold |
| `confounded-design` | `claude-opus-5` |  | predicted holds, wrong (informed by evals/transcripts/confounded-refusal/ at 050d0d7) | does not hold |

The twelve predictions for `llama3.1:8b` and `qwen2:7b` stand as pre-registered and are not scored, because those cells produced no take.

### The local tier's committed lines

The local tier was not run. Its three pre-registered lines stand here byte-identical to their committed files.

> Anthropic doesn't endorse, maintain, or audit third-party gateway products, and doesn't support routing Claude Code to non-Claude models through any gateway.

> For larger repositories, set the [context length](/context-length) to 64k or higher.

> Setting only that variable, without a gateway credential, doesn't replace the subscription.

### Check it from a clone

```bash
git log --oneline --reverse -- evals/gap-study/prereg.json  # the freeze is the first entry
python3 evals/gap-study/check_results.py --ledger           # each take was registered before it ran
python3 evals/gap-study/run.py --all                        # regrades each cell; no model is called
python3 evals/gap-study/analyse.py                          # the pre-registered analysis
```

The pre-registration carries its amendments in `amendments[]`, each with every changed file's hash before and after, and each written up under [`evals/gap-study/verification/`](../evals/gap-study/verification/).

<!-- /gap-study -->

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

### Limitations, all four from the amendments, stated with the result

- **n = 2 pairs, one hand-driven and one scripted.** Nothing here distinguishes a stable
  behaviour from two draws.
- **Pair 1's fixture told the agent it was being evaluated**, through its decoy file and its
  read headers, from turn 8. Pair 2's did not. Both agents made the same control-half
  observation, so the warning did not visibly change that half; what it did to the positive half
  cannot be separated from the operator asymmetry.
- **Pair 1's two halves were opened with different operator lines.** Pair 2's were identical.
- **Every take ran with the operator's own assistant configuration in the agent's context.** The
  driver's working directory sat inside that tree, so Claude Code loaded its `CLAUDE.md` and the
  profile and long-term memory it imports. No sentence in it names this study or this task. It does
  repeatedly discuss outside evaluators catching false claims in other work, which is not a neutral
  thing to be holding while being measured on whether you assert a claim your data does not support,
  and the direction of that bias is toward the result published here. The material has since been
  redacted from the published transcripts and the runs move to a clean checkout; the takes that
  produced this table ran under the condition. Amendment 4 carries the detail and the before-and-
  after hashes.

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
