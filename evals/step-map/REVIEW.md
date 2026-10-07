# What GARS leaves the model to decide: the top three per stage

_For Javier's review, about two hours. Written 7 Oct 2026 from the full step map of GARS as of commit `a626cdc2`._

## What this is, and what I am asking of you

GARS's stage contracts tell the agent what to do, step by step, and its scripts do the computing.
I read every numbered step of all 14 contracts (142 steps) and asked, at each one, what the model still decides on its own because no rule, menu or script decides it.
I found 29 such decisions.
Below are the three that matter most in each part of the pipeline, 15 in all, in plain words.

Each was ranked the way the method we agreed on ranks them: first by how bad the outcome would be if the model gets it wrong (harm, 1 to 10), then by how likely the mistake is to slip past everything that comes after it (slip-through, 1 to 10; 10 means nothing later would notice).
How often a model actually gets each one wrong has not been measured for any of them; the Gap Study is how we would measure it, and these are the first candidates.

For each item, I would like your call on two things: is the ranking right (would you move it up or down, and why), and is the proposed fix the right kind of fix.
A short "agree", "move up", "move down" or "different fix" per item is enough; your reasons are what matter most.

## Stage 00: registering a project and its raw data

### 1. The dataset's classification and purpose are never asked

<!-- S00-class -->
**What the model decides on its own.** When it finalises a new project, the registration script needs two facts about the data: its class (public, de-identified under an agreement, or identifiable) and its purpose (fixture, internal, pilot, commercial).
The opening message promises to ask only for the title, the assay types and the data paths, and no step asks for these two, so the model fills them in itself.

**What can go wrong.** Both are written into the project's permanent record and cannot be changed afterwards, and the closing message never shows them to the user.
GARS's safety layer only lets the agent say "public" for a folder a person has declared public, which limits the damage for the class.
Nothing limits the purpose, and the purpose decides how long the data may be kept and whether a job may run on the local machine.

**Why it ranks first here.** Harm 8, slip-through 8: a permanent record of how the data may be used, chosen without asking and never shown back.

**Proposed fix.** Ask both from a fixed list taken from GARS's own data-policy table, show them in the closing message, and give the script's refusals an answer.

### 2. "Your request matches 01": the model matches the user's words to an assay

<!-- S00-match -->
**What the model decides on its own.** If the user's first message names an assay ("RNA-seq of liver"), the contract asks the model to say which menu entry that matches, so the user can confirm with one word.
The same contract forbids the model to match assay names itself, because the script does that matching carefully and refuses anything ambiguous.

**What can go wrong.** "RNA-seq" could mean bulk or single-cell.
A user who sees "Your request matches 01" will usually reply "01", and the project is then built for the wrong assay, which runs the wrong pipeline on the data.

**Why it ranks here.** Harm 8, slip-through 5: the next message names the assay, but only a user who reads it carefully catches the slip.

**Proposed fix.** Let the script match the original words (it already can) and have the model only show its answer.

### 3. Sample names: the model writes the pattern that reads them

<!-- S00-pattern -->
**What the model decides on its own.** When the FASTQ file names do not follow the standard Illumina convention, the contract asks the user how to read the sample name, and then tells the model to pass "their answer as a regular expression".
Users answer in words ("the sample is the part before _R1"), so in practice the model writes the expression, which another line of the same contract forbids.

**What can go wrong.** A wrong expression merges two samples into one or splits one sample into several, and every later step inherits it.
There is a second problem: GARS's safety layer refuses any such expression, because it needs the characters `<` and `>`, so in a guarded session this whole route cannot run and the model has to improvise.

**Why it ranks here.** Harm 8, slip-through 3: the derived sample names are shown for confirmation before anything is linked, and the stage's final human check asks the same question.

**Proposed fix.** The script proposes a few candidate patterns from the actual file names, the user picks one by number, and the safety layer accepts the chosen one.

## Stage 01: checking the design and writing the samplesheets

### 1. The user's words become pipeline settings

<!-- S01-declare -->
**What the model decides on its own.** Before validating, the stage asks the user for missing settings: strandedness, the unit of replication, the reference release, and whether samples are paired.
Users answer in their own words ("dUTP", "TruSeq stranded", "same donors"), and the model translates those words into the allowed values and edits the settings file by hand.
There is no rule for the translation.

**What can go wrong.** A wrong strandedness reaches nf-core silently and miscounts reads; a wrong pairing or replication unit changes the statistics later.
The history file quotes the user's words, but nothing checks the translation against them.

**Why it ranks first here.** Harm 9, slip-through 8: a complete, plausible, wrong result.

**Proposed fix.** Offer each setting as a numbered list with what each value means, the way stage 02 already offers genomes and contrasts; the user picks; the script writes the file and the history line.

### 2. Free-text values for the remaining settings: the contract says both yes and no

<!-- S01-offer -->
**What the model decides on its own.** At the end of stage 01, one line tells the model to offer to write any values the user gives for the settings still open (the reference genome, the contrast).
A note on the same message says never to offer that, because stage 02 offers those as menus.

**What can go wrong.** A model that follows the first line writes a reference path or a contrast by hand.
The settings file then looks complete, so stage 02 skips its menus, which are what keep the genome sequence and its annotation matched and the contrast tied to levels that exist in the design.

**Why it ranks here.** Harm 7, slip-through 5: it bypasses the menus' protection, though stage 02's human check might still catch a bad value.

**Proposed fix.** Delete the offer; the closing message already tells the user stage 02 will offer menus.

### 3. What counts as "yes" before excluding samples or overwriting files

<!-- S01-yes -->
**What the model decides on its own.** Two moments in stage 01 need the user's consent: excluding samples the user left out of the design, and overwriting samplesheets that already exist.
Only "cancel" is a fixed answer; any other reply ("ok", "yes, but keep sample 4") is the model's to interpret, and the model then passes the switches that clear both gates, with nothing tying them to an actual answer.

**What can go wrong.** An exclusion the user did not mean analyses a subset they did not choose; an overwrite also discards any edits the user made to the samplesheets by hand.

**Why it ranks here.** Harm 7, slip-through 4: the counts in the next message and the history file show what happened, afterwards.

**Proposed fix.** A fixed word for each gate ("exclude", "overwrite"), and the script refuses a switch that has no matching recorded answer.

## Stage 02, the router: settings menus and routing

### 1. Single-cell chemistry is never offered as a menu

<!-- R-protocol -->
**What the model decides on its own.** For single-cell RNA-seq, the library chemistry (10x v2, v3, Drop-seq and so on) is the setting the seeded file itself calls its most dangerous.
GARS has a script that offers it as a menu, and the settings script lists it as single-cell's decision, but the router's steps only ever offer the genome, contrast and peak-type menus.
So the model either asks in free text and passes the user's words on, or never asks.

**What can go wrong.** A wrong but valid chemistry runs to completion and reads the cell barcodes at the wrong positions, producing a plausible matrix and no error.
The pre-flight check refuses only a chemistry the chosen aligner cannot run.

**Why it ranks first here.** Harm 9, slip-through 8.

**Proposed fix.** Add the chemistry menu to the router's settings step for single-cell, and show the choice in the confirmation message. The code already exists; only the contract omits it.

### 2. The user's words about the statistical model become a formula

<!-- R-formula -->
**What the model decides on its own.** The differential-expression formula defaults to "~ condition", and the contract allows a different formula "the user gave you".
Users rarely give formula syntax; they say "account for batch" or "the donors are paired", and the model writes the formula.

**What can go wrong.** A wrong covariate or interaction becomes the model that is tested, and every p-value changes.

**Why it ranks here.** Harm 9, slip-through 4: the formula is shown before it is written, which is a real check only for a user who reads formula syntax.

**Proposed fix.** Offer formula choices built from the design table's own columns, the way the contrasts are already offered, and confirm them in the same message.

### 3. Which project and assay the user means

<!-- R-project -->
**What the model decides on its own.** "Run the RNA one on my liver project": the model matches those words to a project folder and an assay by reading the folders and the assay table itself.

**What can go wrong.** The right pipeline runs on the wrong project.

**Why it ranks here.** Harm 6, slip-through 3: the opening message names the project and assay before anything runs, so an attentive user catches it.

**Proposed fix.** A script lists the matching projects and assays, the model shows them, the user picks.

## Stage 02, the sub-stages: running the pipelines

These ten contracts share two shapes (seven nf-core pipelines, three analyses that follow them), so each item below applies to most of them.

### 1. When the job scheduler refuses a submission

<!-- W-submit -->
**What the model decides on its own.** Before a job runs, GARS checks that the data's class and purpose allow it to run where it is going (the venue rules), and refuses a duplicate submission.
The contract's submit step says only "capture the job id", and the next message announces "Submitted as job ..."; no step says what to do if the submission is refused.

**What can go wrong.** The model either reports a submission that never happened, or improvises; the worrying improvisation is changing a setting (for example the declared memory) until the venue rule stops refusing, which defeats a data-policy check.

**Why it ranks first here.** Harm 7, slip-through 6: an improvised way past a policy check is visible only to someone reading the session transcript.

**Proposed fix.** Give the submit step an answer for each refusal: report it word for word and stop, and never change a setting to get past a venue rule.

### 2. Carrying the input file from the router into the sub-stage

<!-- D-handoff -->
**What the model decides on its own.** For the three analyses that follow a pipeline (differential expression, single-cell clustering, spatial cluster counts), the router finds the input file, and the sub-stage then needs that path and the name of the step that produced it.
Nothing passes them on except the conversation, so the model carries or re-derives them, sometimes in a later session.

**What can go wrong.** A wrong path analyses the wrong object; a wrong "produced by" name records false provenance in the history.

**Why it ranks here.** Harm 6, slip-through 4: the scripts' own checks catch most wrong inputs, but nothing checks the provenance line.

**Proposed fix.** Each analysis finds its own input with GARS's resolver (the differential-expression step already does), and the final check takes the producer's name from the resolver, not from the model.

### 3. Where to pick up again after a job has finished

<!-- W-reentry -->
**What the model decides on its own.** A sub-stage is visited twice: once to submit the job, and again later to collect the results.
On the second visit, the first steps say to stop only if the job is still queued, running or already complete; for every other state (finished and waiting to be checked, failed, stale) the steps read in order lead back into check, prepare and submit.
Only a later step's phrase "on a later invocation" hints that the model should jump ahead to collecting.

**What can go wrong.** Read literally, a finished run is prepared again (rewriting its recorded parameters and reproducibility file) and resubmitted; the duplicate is refused and the collection never happens until the model works out the jump.

**Why it ranks here.** Harm 5, slip-through 4: wasted work and a rewritten provenance file rather than a wrong result.

**Proposed fix.** The first steps route each job state to its own step, as the router already does; better, the script says which step comes next.

## Stage 03: custom analysis

### 1. The approved plan becomes code that nobody reviews

<!-- S03-scripts -->
**What the model decides on its own.** In stage 03 the user approves a written plan, in their own terminal, before anything runs.
After approval, the model writes the analysis scripts that carry the plan out.
The approval locks the plan text, not the scripts, and the final check confirms only that the promised output files exist, are not empty, and came from recorded runs of unchanged scripts.

**What can go wrong.** A script that departs from the approved method, reads data the plan does not list, or computes the statistic differently passes every check.

**Why it ranks first here.** Harm 9, slip-through 8: this is the one place the model writes the computation itself, and its output is a scientific result.

**Proposed fix.** Show the scripts for approval too, and lock their fingerprints into the approval record the way the plan's already is.

### 2. Which project and assay the analysis draws on

<!-- S03-assay -->
**What the model decides on its own.** Stage 03 starts by listing the available results for "the relevant assay"; in a project with several assays, the model picks one, and the plan's inputs inherit that choice.

**What can go wrong.** The plan is built on the wrong assay's results.

**Why it ranks here.** Harm 5, slip-through 3: the plan you approve lists its inputs, so a careful read catches it.

**Proposed fix.** List every assay's results and let the plan name the assay of each input.

### 3. How to "monitor" a running analysis

<!-- S03-monitor -->
**What the model decides on its own.** After submitting, stage 03 says "monitor the job", while every other contract forbids checking in a loop and no step says when to look.

**What can go wrong.** The model checks repeatedly, sleeps, or simply waits for the user; a wasted or stalled session, visibly.

**Why it ranks here.** Harm 3, slip-through 2: minor, and listed only because stage 03 has few silent decisions.

**Proposed fix.** Return after submitting; the next visit checks once.

## What else the map found

- **21 defects that need no model run to fix**, in `evals/step-map/DEFECTS.md`, each with the exact file and line, for the post-freeze fix batch that opens on 16 Oct. The ones worth knowing about:
  - In a workspace that holds any non-public project, the safety layer refuses the job-submission, job-status and resolver commands exactly as the contracts spell them (38 places in 12 contracts), and accepts only a different spelling no contract mentions.
  - Once a job has been handed back to the user, no step the agent follows refreshes its status, so a finished job can look "still running" until someone runs the status command by hand.
  - No contract says what happens on a non-public project, where the safety layer refuses most steps.
  - The date in every history entry is whatever the model believes today's date is.
- **The pilot's findings hold up.** The extractor re-found, from the code, every defect the pilot reported for stages 00 and 01, and the full map keeps the pilot's three top decisions (the classification, the settings from free text, what counts as a yes). The one ranking that moved: the "Your request matches 01" decision, which the pilot did not rank, now sits second in stage 00.
- **The full map** is `evals/step-map/MAP.md`: every step, who acts, how much is already code, and every silent decision with its scores. The facts in it were pulled out by code and can be re-derived; the judgments are mine and are marked as such.
