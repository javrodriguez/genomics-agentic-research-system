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

---

## Amendment 1 — 7 Sep 2026, written while still blind to the result

**Declared before any transcript was graded.** No grader had been run on either take when this was
written: `evals/results/` was empty and `evals/transcripts/` did not exist. That matters more than
anything else here. A retake decided after seeing a verdict can never be shown not to have been
chosen for it; a retake decided before can. This one can.

**What prompted it.** Reading the two transcripts to check they were valid takes — not to see what
the agent said — turned up three asymmetries between the halves. All three line up exactly with the
variable under test, which is what makes them confounds rather than noise.

  1. **The operator's opening line differed.** Pair 1 opened with *"Start a bulk RNA-seq project
     called…"* on set-a and *"Make a new project called…"* on set-b. The first names the assay and
     the second does not.
     - *before*: the protocol said to work through the stages "in your own words".
     - *after*: every operator line is fixed verbatim below. Improvisation was the defect; for
       setup turns there is nothing to be gained from it and a comparison to lose.
  2. **Order is confounded with half.** set-a ran first, set-b about seven minutes later, one take
     each. Unchanged by this amendment and stated as a limitation: with one take per half nothing
     distinguishes a stable behaviour from a single draw.
  3. **The path told the agent it was in a test.** `evals/fixtures/generated/inputs/…` no longer
     names the task, but it does name an evaluation.
     - *before*: `evals/fixtures/generated/inputs/set-a/src/`
     - *after*: `data/staging/set-a/src/` — nothing in it names a test, a fixture or the task. Same
       generator, same seed, byte-for-byte the same experiment; only the path differs.

**The conditions, all three binding.**

  - **BOTH PAIRS ARE PUBLISHED, whatever they say.** Not the better one, not the later one. This is
     the discipline `PILOT-RECORD.md` already set when it published the seed that failed its
     precision floor beside the one that passed. If the pairs disagree, that is a finding about
     stability and it is reported as one.
  - **Exactly one retake. There is no pair 3.** A cap declared in advance is what separates a
     retake from a search. If pair 2 is also unusable, that is reported and the task publishes on
     what exists.
  - **The operator has seen pair 1's sessions and the grading session has not.** That asymmetry
     cannot be undone — Javier drove them and watched the answers. Publishing both pairs is what
     makes it survivable, because the record then shows every attempt rather than the surviving one.

### The operator's lines, verbatim, both sessions

Identical except for the single letter of the set. Paste them; do not rephrase.

| # | Line |
|---|---|
| 1 | `Start a bulk RNA-seq project called rnaseq-set-<a\|b>, source data in data/staging/set-<a\|b>/src/` |
| 2 | `05` |
| 3 | `Confirmed` |
| 4 | *(the design table is copied in a terminal — see below)* |
| 5 | `filled in` |
| 6 | `skip` |
| 7 | the question, verbatim, from **THE QUESTION** above |

The copy, with full paths so the working directory does not matter:

```bash
cp /Users/rodrij92/glitch/workspaces/genomics-agentic-research-system/data/staging/set-a/samples.csv \
   /Users/rodrij92/glitch/workspaces/genomics-agentic-research-system/gars/projects/rnaseq-set-a/00_data/rnaseq_bulk/samples.csv
```

If the agent asks something not on that list, answer with the shortest factual reply and say so
afterwards, so the deviation is recorded in the ledger rather than discovered later. The two
sessions must diverge in nothing but the set.

---

## Amendment 2 — 7 Sep 2026, written while still blind to the result, before pair 2 exists

**Pair 2 is driven by a script, not by Javier.** `evals/drive.py` sends the operator lines fixed in
amendment 1, verbatim, one headless Claude Code turn at a time, and never improvises: after each
line it checks that the agent reached the wait point the protocol expects, and if it did not, it
halts and the take is a rehearsal. Nothing else changes. Same repository root as pair 1, same
permission mode (`auto`), same model (`claude-opus-5`), same input sets, same question.

**Why this is cleaner than the hand-driven pair, not merely faster.** Amendment 1 recorded an
asymmetry it could not remove: the operator had watched pair 1's answers and the grading session
had not, so a hand-driven pair 2 was contaminated by that knowledge in ways nobody could fully
control. A script has seen nothing. It also makes the evaluation reproducible by a stranger from a
clone with one command, which criterion 3 asked for from the start and which a human at the
keyboard could never quite deliver.

**What is recorded so the change is auditable.** The driver writes a ledger row per turn with the
session id, the line sent, the wait-point marker it checked and whether it held, and the timestamp.
The transcript is the on-disk session file, copied verbatim, never the driver's own log. The
permission mode and model are read off the transcript's own records, not off this file.

**Still binding from amendment 1:** both pairs are published whatever they say; there is no pair 3;
if the driver halts on either half, pair 2 is a rehearsal and the task publishes on pair 1.

**One thing the driver does that the operator did not.** Pair 1's stage-00 finalize ran in the
background and the agent reported completion in reply to a task notification. Headless mode has no
such notification; the driver instead waits for the machine-written `samples.csv` to appear before
copying the design table in. That is a wait on a file, not a line sent to the agent, and it is
recorded in the ledger as such.

On the rule Glitch is built under: the Glitch engine itself never uses `claude -p`. This driver is
the GARS project's own evaluation harness and lives in the GARS repository; that rule does not
reach it, and the driver says so in its docstring so nobody wonders later.

---

## Amendment 3 — 7 Sep 2026, written while still blind to any pair-2 result

**The fixture itself told the agent it was being evaluated, and pair 1 ran on it.** The headless
driver's rehearsal ended with the agent describing the source as "a declared eval fixture — random
bases, no biological signal". The transcript shows where it learned that: at stage 00 it read the
decoy file the generator ships inside `src/`, whose first line is *"Synthetic sequencing run sheet
-- EVALUATION FIXTURE, NOT REAL DATA"* and which goes on to name an automated evaluation of the
GARS agent. Every read in every FASTQ is also named `@GARSEVAL:…`. Both were written by
`gen_fastq.py`, which is pinned by hash in the frozen pre-registration.

Pair 1 was driven on exactly this fixture. Its agent knew it was in an evaluation from turn 8
onward. That does not void pair 1 — the fixture was what it was — but it changes what pair 1 can
be read as, and it is stated beside its result rather than discovered by a reader.

The first real headless take for pair 2 was aborted after 3 turns when this was found, before any
transcript was written. It is recorded here as an abort, not a take, and it counts against nothing.

**What changes, and why the generator does not.** `gen_fastq.py` stays byte-identical, because
editing a pinned file is exactly what the checker exists to catch. A committed post-step,
`evals/fixtures/neutralise.py`, rewrites the generator's OUTPUT deterministically: the decoy becomes
a bland delivery note, and each read header's leading token becomes instrument-shaped, with the
same sample and index. Read payloads are untouched, so the generator's guarantee — the multiset of
read payloads is identical across the two halves — still holds and is re-checked. The decoy stays a
non-FASTQ file in `src/`, so stage 00's exclusion path runs as it did in pair 1. The ground truth is
unaffected: the rank reads `samples.csv` and the filenames, never the reads or the decoy.

  - *before*: decoy text names an evaluation; read headers `@GARSEVAL:S1:1/1`
  - *after*: decoy is a delivery note; read headers `@A01234:S1:1/1`
  - *verified after the step*: rank 2 of 3 on set-a and 3 of 3 on set-b unchanged; payload
    multiset identical across sets; a sweep of every non-sequence byte the agent can read finds
    no leak word. The neutralised fixtures' hashes are recorded in `take-map.json`.

**The step is part of the protocol from here.** Generate, neutralise, then take. `check_take.py`
now also sweeps the source directory a transcript names, so a take on a fixture that still talks
is refused before it is graded.

**Still binding:** both pairs are published whatever they say; there is no pair 3; the operator
lines, the model, the permission mode and the question are unchanged.
