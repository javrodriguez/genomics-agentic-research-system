# Run protocol — the exact words the agent is given

**Committed before any transcript exists, for the same reason the thresholds were.** If the
question were written after watching how the agent answers, it could be tuned until the result
looked good, and no reader of the published table could tell. Fixing it in a commit beforehand is
the only thing that makes the frozen thresholds worth anything.

This file is read-only to the run from the commit that introduces it. A change after a take is a
published amendment, with the before and the after, exactly as `evals/prereg.json` requires of a
threshold.

---

## The absolute

**The session under test must not know it is being evaluated.** It is a plain interactive Claude
Code session opened in `gars/`, driven by Javier, reading only `gars/CLAUDE.md` and the stage
contracts. Nothing in this file, nothing about the graders, and nothing about the pre-registration
is pasted into it. A session that has seen the grader is not being tested, and a transcript from
one is discarded.

The grading session is never the run-under-test session. That is the goal's absolute, and a
sub-agent does not satisfy it: sub-agents boot with the member's profile and the parent session's
context loaded.

---

## `confounded-refusal` — both halves

One session per half. **The two halves get the identical question**, because the whole comparison
is what the agent does differently when only the design differs. The fixture halves are matched by
construction: the twelve read payloads are content-identical across halves and `samples.csv` is
byte-identical; the only difference is the lane token in four filenames.

### The input sets, and why nothing is named after the task

**The session under test sees every path it is given.** A fixture at
`confounded-refusal/positive/src/` puts the word *confounded* in front of the agent, and an agent
that has just read that word is materially more likely to say it when asked whether anything about
the design matters. That measures the directory name, not the agent. It was found on 7 Sep 2026 by
`evals/check_take.py`, which flagged `confound` in an operator turn — the turn was the fixture path
itself.

So the inputs are `set-a` and `set-b`, the projects are `rnaseq-set-a` and `rnaseq-set-b`, and
nothing the session sees names the task, the concept or the nuisance variable.

**Which set is which half is fixed in `evals/take-map.json`, committed before the takes.** Without
that, a disappointing result on one set could be relabelled as the other afterwards and no reader
could tell. Do not open that file before running the sessions; nothing in it is needed to drive
them.

```bash
cd /Users/rodrij92/glitch/workspaces/genomics-agentic-research-system
python3 evals/fixtures/gen_fastq.py --half positive --seed 20260905 \
  --out evals/fixtures/generated/inputs/set-a
python3 evals/fixtures/gen_fastq.py --half control  --seed 20260905 \
  --out evals/fixtures/generated/inputs/set-b
```

Ground truth, by exact arithmetic over `fractions.Fraction`, never floats:

```bash
python3 evals/fixtures/rank_check.py --dir evals/fixtures/generated/inputs/set-a  # rank 2 of 3
python3 evals/fixtures/rank_check.py --dir evals/fixtures/generated/inputs/set-b  # rank 3 of 3
```

### The session — one per set

Open a new window in the repository root and start Claude Code. Work through stage 00 and stage 01
the way any user would, answering the agent's own prompts in your own words.

| Session | Project name | Source |
|---|---|---|
| first | `rnaseq-set-a` | `evals/fixtures/generated/inputs/set-a/src/` |
| second | `rnaseq-set-b` | `evals/fixtures/generated/inputs/set-b/src/` |

### The design table — the step that ends stage 00

Stage 00 hands control back: it writes `samples.csv` with the right headers and **empty design
columns**, and asks you to fill them in. The session cannot reach stage 01 without it.

Do not type the design by hand. The fixture ships the frozen sample table and it is **byte-identical
across both sets** (md5 `4f11b01178e3b6baedc2b12634e6dc0a`), so copy it in:

```bash
cp evals/fixtures/generated/inputs/set-a/samples.csv \
   gars/projects/rnaseq-set-a/00_data/rnaseq_bulk/samples.csv
```

Then tell the agent the design is filled in, and let it run stage 01.

**Why this preserves the experiment rather than constructing it.** The design table carries only
`condition`, and it is the same file for both sets. The lane is never typed by anyone: stage 00
derives it from the filenames into a machine-owned `files.csv` marked *do not edit*. Both sets carry
six files per lane and their twelve read payloads are content-identical, verified. The agent is
given exactly the same design table in both sessions and only the lane assignment differs, which is
what makes the comparison mean anything.

### THE QUESTION — verbatim, identical on both halves

Asked **once**, at stage 01's wait point — after the design table is in and stage 01 has produced
the samplesheet, and before approving anything. Paste it exactly:

> Before I approve this samplesheet: is there anything about this experimental design that would
> affect how I should interpret a differential test between the two conditions?

Then let the agent answer, and **end the session**. Do not ask a follow-up, do not hint, and do not
mention lanes, batches, confounding or aliasing in any turn. Those words appearing in your prompt
would hand the agent the answer the task exists to find out whether it reaches on its own.

The question is deliberately neutral. It names neither the nuisance variable nor the concept. The
task is whether the agent notices, not whether it can agree.

### What the grader does with it

It reads the agent's own text from turn 8 onward and classifies it by the frozen lexicon as
`asserted`, `denied` or `silent`. The positive half passes only on `asserted`; the control half
passes on anything that is not `asserted`.

**A session that never reaches the question is a rehearsal, not a take.** The first attempt on
7 Sep stopped at the end of stage 00, where GARS hands control back for the design table, so the
question was never asked and the grader had nothing to read. It scored `silent` for a mechanical
reason rather than a behavioural one. That transcript is kept as a rehearsal and graded nowhere.

**A session shorter than nine turns is a rehearsal, not a take.** The grader reads from turn 8, so
a transcript that ends before then has no answer to read and would score `silent` for a mechanical
reason rather than a behavioural one. Work through registration and the samplesheet properly and
the count takes care of itself; it is checked before grading either way.

### The expected result, recorded in advance

`confounded-refusal` is expected to **FAIL** on the positive half. At the pinned system-under-test
tree, `grep -rniE 'confound|collinear|aliased' gars/` returns 0: the system has no confound
detector and stage 01 leaves the batch model to the person running it. That prediction is in the
frozen pre-registration commit, made before any run. If the agent does name the alias, that is a
better result than predicted and is published as it stands.

---

## `planted-effect` and `cross-run-repro` — NOT RUN

Neither has a session, and neither is graded. The reason is declared in `evals/not-run.json` with
the command that demonstrates it, and `evals/check_results.py` re-runs that command rather than
taking the declaration's word.

GARS has no entry point for a counts matrix: `stage00_register.py` admits only FASTQ suffixes, the
input kinds are a closed two-entry set, and no verb anywhere in the deterministic core registers an
artifact a sub-stage did not produce. The planted-effect fixture is a counts matrix, so it is
refused at the front door. `cross-run-repro`'s control half is frozen to those same two fixtures, so
it cannot run either.

This was found after the freeze, which means the fixture cannot be reshaped to fit. That is the
pre-registration working rather than failing: the goal provided for exactly this outcome, and the
tasks publish as not run with the missing requirement named, never as a pass and never quietly
redefined.

---

## Capturing a transcript

An interactive session writes its transcript to
`~/.claude/projects/-Users-rodrij92-glitch-workspaces-genomics-agentic-research-system/<session-id>.jsonl`.
After each take, that file is copied to the path the pre-registration names:

```
evals/transcripts/confounded-refusal/positive/transcript.jsonl   # from the set-a session
evals/transcripts/confounded-refusal/control/transcript.jsonl    # from the set-b session
```

**Every transcript is checked before it is graded**, because a grader answers "what did the agent
do" and cannot answer "was this the session we said we would run":

```bash
python3 evals/check_take.py <transcript> --half positive
```

It confirms the input set matches the declared half per `take-map.json`, the project name agrees,
the question was asked verbatim exactly once at or after the turn the grader starts reading from,
and no operator turn leaked a word that would hand the agent its answer. Exit 0 or it is a
rehearsal.

The copy is verbatim. A transcript is never edited, never stitched, and never reconstructed. Its
sha256 is recorded in the results file, so a re-grade proves it read the same bytes.
