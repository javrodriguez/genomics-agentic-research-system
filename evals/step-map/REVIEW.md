# What GARS leaves the model to decide: the top three per stage

**What you are reviewing.** Fifteen places where GARS lets the AI agent decide something on its own, because no rule, menu or script decides it for it: the three that matter most in each part of the pipeline.
For each one I say what the agent decides, what can go wrong, why I ranked it where it is, and the fix I would propose.
The fixes would go into the batch of GARS fixes that opens after the freeze on 16 Oct; nothing changes before you answer.

**How to answer.** One line per item, in whatever words you like, for example:
- `agree`, if the risk is real and the ranking and the fix look right;
- `re-rank: higher than X, because ...` or `re-rank: lower, because ...`;
- `not a real risk: ...`, if you think the agent would never get this wrong, or it would not matter;
- `different fix: ...`, if the risk is right but you would fix it another way.

Each item ends with a "Your answer:" line for this. Your reasons are what I most need: they set how the rest of the 34 decisions are ranked.
It should take about two hours; the items are independent, so you can stop and resume anywhere.

_Written 7 Oct 2026 from the full step map of GARS as of commit `a626cdc2`, and corrected the same night after two independent reviews._

## How this was done

I read every numbered step of all 14 GARS stage contracts (142 steps) and asked, at each one, what the agent still decides on its own.
I found 34 such decisions.
Each was scored on two fixed 1-to-10 scales and ranked first by harm, then by slip-through.
Harm is how bad the outcome would be if the agent got it wrong: 9 is a wrong scientific result, 8 the wrong analysis running, 5 a dead end or wasted compute, 3 a misleading message.
Slip-through is how likely the mistake is to get past everything after it: 4 means you are asked to confirm it first, 5 that it is shown to you without asking, 8 that nothing shows it at all.
How often an agent actually gets each one wrong has not been measured for any of them; a paired test of each, run many times, is how we would measure it, and these fifteen are the first candidates.

## Stage 00: registering a project and its raw data

### 1. The dataset's classification and purpose are never asked

<!-- S00-class -->
**What the agent decides on its own.** When it finalises a new project, the registration script needs two facts about the data: its class (public, de-identified under an agreement, or identifiable) and its purpose (fixture, internal, pilot, commercial).
The opening message promises to ask only for the title, the assay types and the data paths, and no step asks for these two, so the agent fills them in itself.

**What can go wrong.** Both are written into the project's permanent record and cannot be changed afterwards, and the closing message never shows them to the user.
GARS's safety layer only lets the agent say "public" for a folder a person has declared public, which limits the damage for the class.
Nothing limits the purpose, and the purpose decides where the project's jobs may run: each class allows only certain machine-and-purpose pairs, and the local machine accepts only test fixtures. (How long the data may be kept follows the class, not the purpose.)

**Why it ranks first here.** Harm 8, slip-through 8: a permanent record of how the data may be used, chosen without asking and never shown back.

**Proposed fix.** Ask both from a fixed list taken from GARS's own data-policy table, show them in the closing message, and give the script's refusals an answer.

Your answer:

### 2. "Your request matches 01": the agent matches the user's words to an assay

<!-- S00-match -->
**What the agent decides on its own.** If the user's first message names an assay ("RNA-seq of liver"), the contract asks the agent to say which menu entry that matches, so the user can confirm with one word.
The same contract forbids the agent to match assay names itself, because the script does that matching carefully and refuses anything ambiguous.

**What can go wrong.** "RNA-seq" could mean bulk or single-cell.
A user who sees "Your request matches 01" will usually reply "01", and the project is then built for the wrong assay, which runs the wrong pipeline on the data.

**Why it ranks here.** Harm 8, slip-through 5: the next message names the assay without asking, so only a user who reads it carefully catches the slip.

**Proposed fix.** Let the script match the original words (it already can) and have the agent only show its answer.

Your answer:

### 3. Sample names: the agent writes the pattern that reads them

<!-- S00-pattern -->
**What the agent decides on its own.** When the FASTQ file names do not follow the standard Illumina convention, the contract asks the user how to read the sample name, and then tells the agent to pass "their answer as a regular expression".
Users answer in words ("the sample is the part before _R1"), so in practice the agent writes the expression, which another line of the same contract forbids.

**What can go wrong.** A wrong expression merges two samples into one or splits one sample into several, and every later step inherits it.
Two more problems sit on the same road: GARS's safety layer refuses any such expression, because it needs the characters `<` and `>`, and a malformed expression crashes the script with no readable answer. In a guarded session the agent therefore has to improvise.

**Why it ranks here.** Harm 8, slip-through 4: the derived sample names are shown and you are asked to confirm them before anything is linked.

**Proposed fix.** The script proposes a few candidate patterns from the actual file names, the user picks one by number, and the safety layer accepts the chosen one.

Your answer:

## Stage 01: checking the design and writing the samplesheets

### 1. The user's words become pipeline settings

<!-- S01-declare -->
**What the agent decides on its own.** Before validating, the stage asks the user for missing settings: strandedness, the unit of replication, the reference release, and whether samples are paired.
The question lists the allowed values, the contract says to write exactly what the user supplied, and the check rejects anything outside the list.
What no rule covers is an answer in other words ("dUTP", "TruSeq stranded", "same donors"): the agent may translate it into an allowed value instead of asking again, and a pairing the user mentions in passing is only ever flagged with a warning.

**What can go wrong.** A wrong but allowed strandedness passes every check and miscounts reads, which gives a complete, plausible, wrong result.
nf-core reports a strandedness mismatch only as a warning in the quality report's strandedness section.

**Why it ranks first here.** Harm 9, slip-through 6: the warning sits in a report you are pointed to, but only someone who looks at that section sees it.

**Proposed fix.** Offer each setting as a numbered list with what each value means, the way stage 02 already offers genomes and contrasts; ask again on any other answer; the script writes the file and the history line.

Your answer:

### 2. What counts as "yes" before excluding samples or overwriting files

<!-- S01-yes -->
**What the agent decides on its own.** Two moments in stage 01 need the user's consent: excluding samples the user left out of the design, and overwriting samplesheets that already exist.
Only "cancel" is a fixed answer; any other reply ("ok", "yes, but keep sample 4") is the agent's to interpret.
The contract says the two switches that clear these gates need the user's confirmation, but nothing in the code checks that an answer was given.

**What can go wrong.** An exclusion the user did not mean runs the analysis on samples they did not choose; an overwrite also discards any edits the user made to the samplesheets by hand.

**Why it ranks here.** Harm 8, slip-through 5: the counts in the next message and the history file show what happened, but only afterwards and without asking.

**Proposed fix.** A fixed word for each gate ("exclude", "overwrite"), and the script refuses a switch that has no matching recorded answer.

Your answer:

### 3. Free-text values for the remaining settings: the contract says both yes and no

<!-- S01-offer -->
**What the agent decides on its own.** At the end of stage 01, one line tells the agent to offer to write any values the user gives for the settings still open (the reference genome, the contrast).
A note on the same message says never to offer that, because stage 02 offers those as menus.

**What can go wrong.** An agent that follows the first line writes a reference path or a contrast by hand.
If stage 02 then judges the settings complete, it skips its menus, which are what keep the genome sequence and its annotation matched and the contrast tied to levels that exist in the design.

**Why it ranks here.** Harm 8, slip-through 5: stage 02's human check asks you to confirm the reference and contrast before the first pipeline runs.

**Proposed fix.** Delete the offer; the closing message already tells the user stage 02 will offer menus.

Your answer:

## Stage 02, the router: settings menus and routing

### 1. Single-cell chemistry is never offered as a menu

<!-- R-protocol -->
**What the agent decides on its own.** For single-cell RNA-seq, the library chemistry (10x v2, v3, Drop-seq and so on) is the setting the seeded settings file itself calls its most dangerous.
GARS has a script that offers it as a menu, and the settings script lists it as single-cell's decision, but the router's steps only ever offer the genome, contrast and peak-type menus.
So the agent either asks in free text and passes the user's words on, or never asks.

**What can go wrong.** A wrong but valid chemistry runs to completion and reads the cell barcodes at the wrong positions, producing a plausible, scrambled or empty-looking matrix and no error.
The pre-flight check refuses only a chemistry the chosen aligner cannot run.

**Why it ranks first here.** Harm 9, slip-through 7: only an expert reading the cell counts closely would notice.

**Proposed fix.** Add the chemistry menu to the router's settings step for single-cell, and show the choice in the confirmation message. The code already exists; only the contract omits it.

Your answer:

### 2. The user's words about the statistical model become a formula

<!-- R-formula -->
**What the agent decides on its own.** The differential-expression formula defaults to "~ condition", and the contract allows a different formula "the user gave you".
Users rarely give formula syntax; they say "account for batch" or "the donors are paired", and the agent writes the formula.
The settings script checks only that each term names a column of the design table.

**What can go wrong.** A wrong covariate or interaction becomes the model that is tested, and every p-value changes.

**Why it ranks here.** Harm 9, slip-through 4: you are asked to confirm the formula before it is written, which is a real check only for someone who reads formula syntax.

**Proposed fix.** Offer formula choices built from the design table's own columns, the way the contrasts are already offered, and confirm them in the same message.

Your answer:

### 3. Which project and assay the user means

<!-- G-project -->
**What the agent decides on its own.** "Run the RNA one on my liver project": the agent matches those words to a project folder and an assay by reading the folders and the assay table itself. Stage 01 makes the same match from the project title.

**What can go wrong.** The right step runs on the wrong project.

**Why it ranks here.** Harm 6, slip-through 5: the opening message names the project and assay before anything runs, though it does not ask.

**Proposed fix.** A script lists the matching projects and assays, the agent shows them, the user picks.

Your answer:

## Stage 02, the sub-stages: running the pipelines

These ten contracts share two shapes (seven nf-core pipelines, three analyses that follow them), so each item below applies to several of them.

### 1. Carrying the input file into the analysis, and naming where it came from

<!-- D-handoff -->
**What the agent decides on its own.** The three analyses that follow a pipeline (differential expression, single-cell clustering, spatial cluster counts) need an input file and, when their results are collected, the name of the step that produced it.
For clustering and spatial counts the router finds the input and the analysis contract then starts afresh; differential expression finds its own input, but collection happens on a later visit.
Either way the path and the producer's name travel only in the conversation, so the agent carries or re-derives them, sometimes in a later session.

**What can go wrong.** A wrong path analyses the wrong object; a wrong producer name records false provenance in the project's history.

**Why it ranks first here.** Harm 6, slip-through 6: the scripts' own checks catch most wrong inputs, but nothing checks the provenance line, which only a careful reader of the history would catch.

**Proposed fix.** Each analysis finds its own input with GARS's resolver, and the final check takes the producer's name from the resolver, not from the agent.

Your answer:

### 2. Where to pick up again after a job has finished

<!-- W-reentry -->
**What the agent decides on its own.** A sub-stage is visited twice: once to submit the job, and again later to collect the results.
On the second visit, the first steps say to stop only if the job is still queued, running or already complete; for every other state (finished and waiting to be checked, failed, stale) the steps read in order lead back into check, prepare and submit.
Only a later step's phrase "on a later invocation" hints that the agent should jump ahead to collecting.

**What can go wrong.** Read literally, a finished run is prepared again (rewriting its generated files and its reproducibility record) and submitted again; the duplicate is refused, and the collection waits until the agent works out the jump.

**Why it ranks here.** Harm 5, slip-through 3: wasted work and a rewritten provenance file rather than a wrong result, and the duplicate refusal stops it.

**Proposed fix.** The first steps route each job state to its own step, as the router already does; better, the script says which step comes next.

Your answer:

### 3. When GARS's own pre-submission check refuses a job

<!-- W-submit -->
**What the agent decides on its own.** Before a job is queued, GARS checks that the data's class and purpose allow it to run where it is going, and refuses a duplicate.
The router's text says to report every refusal and stop, but the sub-stage's own steps say only "capture the job id", and the next message announces "Submitted as job ..." with no answer for a refusal.

**What can go wrong.** The agent announces a submission that never happened, or changes the executor or memory setting itself to get past the refusal, without asking you.

**Why it ranks here.** Harm 5, slip-through 3: a setting changed without you, or a false "submitted"; the next status read shows nothing was queued.

**Proposed fix.** Give the submit step an answer for each refusal: report it word for word and stop; settings change only on your word.

Your answer:

## Stage 03: custom analysis

### 1. The approved plan becomes code that nobody reviews

<!-- S03-scripts -->
**What the agent decides on its own.** In stage 03 the user approves a written plan, in their own terminal, before anything runs.
After approval, the agent writes the analysis scripts that carry the plan out.
The approval locks the plan text, not the scripts, and the final check confirms only that the promised output files exist, are not empty, and came from recorded runs of unchanged scripts.

**What can go wrong.** A script that departs from the approved method, reads data the plan does not list, or computes the statistic differently passes every check.

**Why it ranks first here.** Harm 9, slip-through 8: this is the one place the agent writes the computation itself, and its output is a scientific result.

**Proposed fix.** Show the scripts for approval too, and lock their fingerprints into the approval record the way the plan's already is.

Your answer:

### 2. Which project and assay the analysis draws on

<!-- S03-assay -->
**What the agent decides on its own.** Stage 03 starts by listing the available results for "the relevant assay"; in a project with several assays, the agent picks one, and the plan's inputs inherit that choice.

**What can go wrong.** The plan is built on the wrong assay's results.

**Why it ranks here.** Harm 6, slip-through 4: the plan you approve lists its inputs, so a careful read catches it.

**Proposed fix.** List every assay's results and let the plan name the assay of each input.

Your answer:

### 3. The order in which several analysis scripts run

<!-- S03-order -->
**What the agent decides on its own.** An analysis may need several scripts, one feeding the next. The contract says to submit every script, but gives no order and no way to make one wait for another; all of them share a single "done" marker, and the final check looks at each script's own run, not their order.

**What can go wrong.** A script that reads another's output can run before that output exists, which usually crashes it, or, more rarely, read a stale copy left by an earlier attempt.

**Why it ranks here.** Harm 6, slip-through 3: most bad orderings fail loudly and the final check reports them; the stale copy is the rare, quieter case.

**Proposed fix.** The plan lists its scripts in order, and GARS runs them as one job, or with declared dependencies.

Your answer:

## What else the map found

- **22 defects that need no model run to fix**, in `evals/step-map/DEFECTS.md`, each with the exact file and line, for the post-freeze fix batch that opens on 16 Oct. One more was withdrawn when a reviewer showed that a stage-wide table in the contract already covers it. The ones worth knowing about:
  - In a workspace that holds any non-public project, the safety layer refuses the job-submission, job-status and resolver commands exactly as the contracts spell them (38 places in 12 contracts), and accepts only a different spelling no contract mentions.
  - Once a job has been handed back to the user, no step the agent reaches refreshes its status, so a finished job can look "still running" until someone runs the status command by hand.
  - No contract says what happens on a non-public project, where the safety layer refuses most steps.
  - The date in every history entry is whatever the agent believes today's date is.
- **The first trial map of stages 00 and 01 mostly holds up.** Two of its findings did not survive the corrected check: it said the registration script's "create" and "link" steps had unhandled failure codes, but a table in the stage's own definitions routes them (one of them to a message whose wording is then wrong). Its three top decisions (the classification, settings from free text, what counts as a yes) all remain in the top ranks. One decision it did not rank, "Your request matches 01", now sits second in stage 00.
- **The full map** is `evals/step-map/MAP.md`: every step, who acts, how much is already code, and every silent decision with its scores. Its facts were pulled out by code from GARS itself and can be re-derived; the judgments are mine and are marked as such.
