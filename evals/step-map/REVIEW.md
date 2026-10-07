# What GARS leaves the model to decide: the top three per stage

**What you are reviewing.** Fifteen places where GARS lets the AI agent decide something on its own, because no rule, menu or script decides it for it: the three that matter most in each part of the pipeline.
For each one I say what the agent decides, what can go wrong, why I ranked it where it is, and the fix I would propose.
The fixes would go into the batch of GARS fixes that opens after the freeze on 16 Oct; nothing changes before you answer.

**How to answer.** One line per item, in whatever words you like, for example:
- `agree`, if the risk is real and the ranking and the fix look right;
- `re-rank: higher than X, because ...` or `re-rank: lower, because ...`;
- `not a real risk: ...`, if you think the agent would never get this wrong, or it would not matter;
- `different fix: ...`, if the risk is right but you would fix it another way.

Each item ends with a "Your answer:" line for this. Your reasons are what I most need: they set how the rest of the 43 decisions are ranked.
It should take about two hours; the items are independent, so you can stop and resume anywhere.

_Written 7 Oct 2026 from the full step map of GARS as of commit `a626cdc2`, and corrected the same night after independent reviews._

## How this was done

I read every numbered step of all 14 GARS stage contracts (142 steps) and asked, at each one, what the agent still decides on its own.
I found 43 such decisions. Most have no rule at all; a few are covered by a written rule that nothing checks, and those are marked.
Each was scored on two fixed 1-to-10 scales and ranked first by harm, then by slip-through.
Harm is how bad the outcome would be if the agent got it wrong: 10 is a wrong scientific result that no check flags, 9 a wrong scientific result, 8 the wrong analysis running, 6 false provenance in the project's record, 5 a dead end or wasted compute, 3 a misleading message.
Slip-through is how likely the mistake is to get past everything after it: 4 means you are asked to confirm it first, 5 that it is shown to you without asking, 8 that nothing shows it at all.
How often an agent actually gets each one wrong has not been measured for any of them; a paired test of each, run many times, is how we would measure it, and these fifteen are the first candidates.

## Stage 00: registering a project and its raw data

### 1. The dataset's classification and purpose are never asked

<!-- S00-class -->
**What the agent decides on its own.** When it finalises a new project, the registration script needs two facts about the data: its class (public, de-identified under an agreement, or identifiable) and its purpose (fixture, internal, pilot, commercial).
The opening message promises to ask only for the title, the assay types and the data paths, and no step asks for these two, so the agent fills them in itself.

**What can go wrong.** Both are written into the project's permanent record and cannot be changed afterwards, and the closing message never shows them to the user.
GARS's safety layer refuses any class but "public" from the agent, and "public" only for a folder a person has declared public, which limits the damage for the class.
Nothing limits the purpose, and the purpose decides where the project's jobs may run: each class allows only certain machine-and-purpose pairs, and the local machine accepts only test fixtures. (How long the data may be kept follows the class, not the purpose.)

**Why it ranks first here.** Harm 8, slip-through 8: a permanent record of how the data may be used, chosen without asking and never shown back.

**Proposed fix.** Ask both from a fixed list taken from GARS's own data-policy table (a non-public answer goes to the person's own terminal, since the safety layer refuses it from the agent), show them in the closing message, and give the script's refusals an answer.

Your answer:

### 2. What counts as "yes" before the raw files are linked

<!-- S00-yes -->
**What the agent decides on its own.** After checking a data folder, the agent shows what it found (file counts, sample names) and asks the user to "Confirm ... or provide a different path".
There is no fixed answer, so a reply like "looks fine, but what about the undetermined files?" is the agent's to read as a yes or a no.

**What can go wrong.** On a misread yes, the wrong files are linked into the project and enter the analysis; the stage forbids re-linking, so undoing it means deleting the project and starting again.

**Why it ranks here.** Harm 8, slip-through 5: the next message and the stage's final check show what was linked, but without asking.

**Proposed fix.** A fixed word (for example "link"), asked again on any other reply.

Your answer:

### 3. One sample-name pattern for several assays

<!-- S00-onepattern -->
**What the agent decides on its own.** When a data folder's file names do not follow the standard convention, the user explains how to read them and the agent passes that pattern on. The step that finishes the project then takes only one pattern and applies it to every assay.
In a project with two or more assays whose files were read in different ways, the agent picks one pattern for all of them.

**What can go wrong.** The other assays then either fail the final check or, worse, get wrong sample names, which every later step inherits.

**Why it ranks here.** Harm 8, slip-through 5: the closing message's sample counts and the stage's final check (confirm the sample names) show it, without asking. (In a session where GARS's safety layer is active, the pattern road is refused anyway; see the defects list.)

**Proposed fix.** The finishing step takes a pattern per assay, recorded when each folder was checked.

Your answer:

## Stage 01: checking the design and writing the samplesheets

### 1. The user's words become pipeline settings (a rule covers answers to its question; nothing checks it)

<!-- S01-declare -->
**What the agent decides on its own.** Before validating, the stage asks only for the settings still missing from the project's settings file, usually the unit of replication and the reference release.
Strandedness is asked only if someone removed the `auto` that every new RNA-seq settings file starts with; whether samples are paired is recorded only if the user says so.
For answers to its question, the contract says to write exactly what the user supplied and never invent values, and nothing checks that the value written is what the user said.
A strandedness the user volunteers ("the libraries are dUTP") has no rule at all: the agent decides whether, and how, to turn it into one of the allowed values.
The check rejects an unknown replication unit or strandedness, but the reference release is free text that nothing checks.

**What can go wrong.** A wrong but allowed strandedness passes every check and miscounts reads, which gives a complete, plausible, wrong result.
A wrong pairing, written down as the contract asks, raises no warning either.

**Why it ranks first here.** Harm 9, slip-through 5: the next message shows the strandedness in its own column without asking, so you see it, but nothing asks you to check it.

**Proposed fix.** Offer each setting as a numbered list with what each value means, the way stage 02 already offers genomes and contrasts, and use the same list when you volunteer a strandedness; ask again on any other answer; the script writes the file and the history line.

Your answer:

### 2. What counts as "yes" before excluding samples or overwriting files

<!-- S01-yes -->
**What the agent decides on its own.** Two moments in stage 01 need the user's consent: excluding samples the user left out of the design, and overwriting samplesheets that already exist.
Only "cancel" is a fixed answer; any other reply ("ok", "yes, but keep sample 4") is the agent's to interpret.
The contract says each of the two switches that clear these gates needs the user's confirmation, but not what counts as one, and nothing in the code ties a switch to an answer.

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
GARS has a script that offers it as a menu, and the settings script lists it as single-cell's decision, but the router's steps only ever offer the genome, contrast and peak-type menus, and the command they give for writing the settings has no place for the chemistry; for single-cell that command stops with an error.
So the agent either adds the chemistry itself, turning the user's words into one of the listed values, or stalls.

**What can go wrong.** A wrong but listed chemistry runs to completion and, in the single-cell pipeline contract's words, "produces a scrambled matrix rather than an error".
The pre-flight check refuses only a chemistry the chosen aligner cannot run.

**Why it ranks first here.** Harm 9, slip-through 5: the single-cell step's human check tells you to compare cell counts with the number loaded, and names wrong chemistry as one cause.

**Proposed fix.** Add the chemistry menu to the router's settings step for single-cell, and show the choice in the confirmation message. The menu code already exists; only the contract omits it.

Your answer:

### 2. The user's words about the statistical model become a formula (a rule exists; nothing checks it)

<!-- R-formula -->
**What the agent decides on its own.** The differential-expression formula defaults to "~ condition", and the contract allows only a formula "the user gave you".
Users rarely give formula syntax; they say "account for batch" or "the donors are paired", and the agent can write the formula for them, which nothing detects.
The settings script checks only that each term names a column of the design table.

**What can go wrong.** A wrong covariate or interaction becomes the model that is tested, and every p-value changes.

**Why it ranks here.** Harm 9, slip-through 4: you are asked to confirm the formula before it is written, which is a real check only for someone who reads formula syntax.

**Proposed fix.** Offer formula choices built from the design table's own columns, the way the contrasts are already offered, and confirm them in the same message.

Your answer:

### 3. Which design factor the contrast compares

<!-- R-factor -->
**What the agent decides on its own.** The contrast menu is built from one factor of the design table, "condition" by default, and no contract mentions how to choose another.
When the design carries another factor the user cares about, the agent decides which factor the menu is built from.
(A contrast typed out in full is accepted only when it matches a pair on that same menu, so the factor, not the typing, is the open choice.)

**What can go wrong.** The comparison runs on the wrong factor. The router's own human check says of a wrong contrast that nothing downstream can detect it: it produces a complete, confident, wrong result.

**Why it ranks here.** Harm 9, slip-through 4: you are asked to confirm the contrast before it is written.

**Proposed fix.** The contract names the factor setting, the menu shows the factor beside each pair, and a design with more than one candidate factor is asked about.

Your answer:

## Stage 02, the sub-stages: running the pipelines

These ten contracts share two shapes (seven nf-core pipelines, three analyses that follow them), so each item below applies to several of them.

### 1. Carrying the input file into the analysis

<!-- D-input -->
**What the agent decides on its own.** Single-cell clustering and spatial cluster counts each need an input file found by the router. The analysis contract then starts afresh, so the path travels only in the conversation, and the agent carries it over or works it out again, sometimes in a later session.

**What can go wrong.** A wrong path analyses the wrong object.

**Why it ranks first here.** Harm 8, slip-through 5: the start message shows the input path without asking. The final check compares only which samples are present and that each has cells, so another file from the same pipeline run passes it.

**Proposed fix.** Each analysis finds its own input with GARS's resolver, as the differential-expression step already does.

Your answer:

### 2. Which AI model the history says ran the step (a rule exists; nothing checks it)

<!-- G-model -->
**What the agent decides on its own.** Every step that writes the project's history passes the agent's own model name to the script that writes it: registration, the samplesheet writer, each pipeline's and analysis's collecting step, and stage 03's final check.
The contracts ask for the exact name the agent's software reports, and to leave it out rather than guess; GARS's own decision record makes the model part of each result's provenance.

**What can go wrong.** The script puts whatever the agent passes, word for word, into the history entry and the run's record, and nothing compares it with the model actually running.
A wrong or guessed name is false provenance in the permanent record.
It is listed here because the pipelines are where it recurs most; it also appears in the full lists for stages 00, 01 and 03.

**Why it ranks here.** Harm 6, slip-through 8: no message shows the name back to you; only reading the history file reveals it.

**Proposed fix.** The script takes the model name from the software running the agent where it can, and otherwise records "unknown"; never from the agent's own words.

Your answer:

### 3. Naming where the input came from

<!-- D-supplier -->
**What the agent decides on its own.** When the three follow-on analyses collect their results, the agent passes the name of the step that produced their input; that name is written into the project's history as provenance. It comes from the conversation, often in a later session.

**What can go wrong.** A wrong name is false provenance in the permanent record.

**Why it ranks here.** Harm 6, slip-through 8, the same as the item above: nothing checks the line.

**Proposed fix.** The collecting step takes the producer's name from the resolver, not from the agent.

Your answer:

## Stage 03: custom analysis

### 1. The approved plan becomes code that nobody reviews (a rule exists; nothing checks it)

<!-- S03-scripts -->
**What the agent decides on its own.** In stage 03 the user approves a written plan, in their own terminal, before anything runs.
After approval, the agent writes the analysis scripts that carry the plan out. The contract says to execute the approved plan literally, and records itself that approval binds the plan, not the scripts.
The final check confirms only that the promised output files exist, are not empty, and came from recorded runs of unchanged scripts.

**What can go wrong.** A script that departs from the approved method, reads data the plan does not list, or computes the statistic differently passes every check.

**Why it ranks first here.** Harm 10, slip-through 8: this is the one place the agent writes the computation itself, its output is a scientific result, and no check flags a departure from the plan.

**Proposed fix.** Show the scripts for approval too, and lock their fingerprints into the approval record the way the plan's already is.

Your answer:

### 2. The order in which several analysis scripts run

<!-- S03-order -->
**What the agent decides on its own.** An analysis may need several scripts, one feeding the next. The contract says to submit every script, but gives no order and no way to make one wait for another; all of them share a single "done" marker, and the final check looks at each script's own run, not their order.

**What can go wrong.** A script that reads another's output can run before that output exists, and crash; or it can read a stale copy left by an earlier attempt, and the final check then accepts a wrong result.

**Why it ranks here.** Harm 10, slip-through 8: the stale-copy case passes every check; only the run records would show the order.

**Proposed fix.** The plan lists its scripts in order, and GARS runs them as one job, or with declared dependencies.

Your answer:

### 3. Which project and assay the analysis draws on

<!-- S03-assay -->
**What the agent decides on its own.** Stage 03 starts by listing the available results for "the relevant assay"; in a project with several assays, the agent picks one, and the plan's inputs inherit that choice.

**What can go wrong.** The plan is built on the wrong assay's results.

**Why it ranks here.** Harm 8, slip-through 4: the plan you approve lists its inputs, so a careful read catches it.

**Proposed fix.** List every assay's results and let the plan name the assay of each input.

Your answer:

## What else the map found

- **22 defects that need no model run to fix**, in `evals/step-map/DEFECTS.md`, each with the exact file and line, for the post-freeze fix batch that opens on 16 Oct. The file numbers 23: when a reviewer showed that a stage-wide table in the contract already routes part of them, two were withdrawn as first written (one stands in reworded form, the other is folded into it) and a third was reworded; later reviews narrowed several others. Each change is marked in the file, and nothing was deleted. The ones worth knowing about:
  - In a workspace that holds any non-public project, the safety layer refuses the job-submission, job-status, resolver and differential-expression commands exactly as the contracts spell them (38 places in 12 contracts), and accepts only a different spelling no contract mentions.
  - Once a job has been handed back to the user, no step the agent reaches refreshes its status, so a finished job can look "still running" until someone runs the status command by hand.
  - No contract says what happens on a non-public project, where the safety layer refuses most steps.
  - In every history entry after stage 00, the date is whatever the agent believes today's date is.
- **The first trial map of stages 00 and 01 mostly holds up.** Two of its findings did not survive the corrected check: it said the registration script's "create" and "link" steps had unhandled failure codes, but a table in the stage's own definitions routes them (one of them to a message whose wording is then wrong). Its top decisions (the classification, settings from free text, what counts as a yes) all remain in the top ranks.
- **The full map** is `evals/step-map/MAP.md`: every step, who acts, how much is already code, and every silent decision with its scores. Its facts were pulled out by code from GARS itself and can be re-derived; the judgments are mine and are marked as such.
