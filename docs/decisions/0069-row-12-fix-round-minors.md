---
date: 2026-09-23
status: standing
kind: defect
touches:
  - gars/_system/executorlib.py
  - gars/_system/stage03_analysis.py
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/02_bioinformatics/CONTEXT.md
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_lifecycle_cancel.py
  - gars/tests/test_downstream_keys.py
  - gars/tests/test_lifecycle_faults.py
  - gars/tests/test_lifecycle_contracts.py
  - gars/tests/test_stage03_execution.py
  - gars/tests/test_approval_forgery.py
  - tests/run_tests.py
  - DEVELOPMENT.md
  - README.md
  - docs/implementation/row_12_change_report.md
symptoms:
  - stage-03 marker can be written by the agent without executor evidence
  - scripts/x.sh looks for scripts/PLAN.md instead of the analysis PLAN.md
  - cancel signals a finished job or guesses when scheduler state is unknown
  - parent STATUS routing omits VALIDATING ARTIFACT_MISSING and STALE
---
# Row 12 post-merge fix round: minors

## Context

Round 5 starts from public main `e59dfc0` on `build/gars-row-12-fix`.
[0066](0066-row-12-owner-approval-of-protected-changes.md) approved the merged row's
protected changes and explicitly left these four MINORs open. This producer record
addresses MINOR-1–4 and NOTE-2–4 of the supplied round-4 review. Its historical branch
numbers 0057–0059 refer to today's 0063–0065. Decisions 0063–0067 remain byte-identical.
This is neither owner merge approval nor a claim that the full row exit is met.

## The owner's reply and selected options

The owner, 23 Sep 2026, replied verbatim:

> 1B · 2A · 3A

The three option texts the owner chose from, quoted exactly:

1B:
> A, plus the executor owns the marker: it runs the agent's script inside a launcher that code generates, clears any marker before the run, and writes it only on exit 0. This is how stage 02's generated `submit.sh` works. Contract step 7 then stops telling the script to write it. Only B makes "execution-created" true

Where A is:
> Add the stage-03 marker to the guard and the settings deny list, and state honestly in a new record what that closes

2A:
> refuse the cancel and name R-077 in the refusal. That fits the rule that job state only ever comes from the scheduler, and it can't signal a PID that has since been reused.

3A:
> fix NOTE-2, NOTE-3 and NOTE-4. NOTE-2 is the missing sentence saying a stage prepared before the fix needs `prepare` again. NOTE-3 is a readable refusal for a same-key resubmit after CANCELLED. It sits on the same cancel path as MINOR-2. NOTE-4 is an unused test line. NOTE-1 stays open, because changing it needs your ruling on the durable state table.

## Decision

**The lane's specification and implementation.**

Everything in this section is **the lane's specification**, not the owner's words.

### MINOR-4: executor-owned stage-03 evidence

The analysis directory is the first two parts of the resolved script path relative to
the project: `03_custom_analysis/<NN_slug>`, regardless of the script's subfolder.
Approval uses that directory's PLAN.md before creating a launcher. This closes the
mismatch where `scripts/x.sh`, as instructed by create and contract step 7, looked for
`scripts/PLAN.md`. Approval, launcher, marker, exit file and submission record now share
the analysis root. A test submits `scripts/x.sh` through the real local backend.

Submit generates a unique launcher in analysis `run/` and hands that launcher to the
backend. It preserves the script's leading `#SBATCH` directives verbatim for Slurm.
The launcher clears an existing marker before running the script, writes the marker
only on exit 0, removes it on nonzero exit, and returns the script's exit code. The
existing LOCAL_RUNNER runs the launcher, putting its exit file and log beside it.
The agent never writes run/, either directly or from its scripts. Every script goes
through `executorlib.py submit` and must fail when any command fails (`set -euo pipefail`).
The **login-node route**, `Runs: login-node (user-requested)`, selects the local backend
through the same executor call; status and verify use the recorded backend.

The hook guards `projects/*/03_custom_analysis/*/run/*`,
`projects/*/03_custom_analysis/*/run/**/*` and
`projects/*/03_custom_analysis/*/.gars_submissions.jsonl`; settings has both Edit and
Write denies for each. This covers marker, launcher, local exit/log files, nested run
files and the submission record, using the same guard machinery as stage 02.

The submission record is an append-only JSON-lines list, one entry per submission,
with `script`, `script_sha256`, `launcher`, `launcher_sha256`, `job_id`, `executor`, and
`submitted_at` (UTC epoch seconds). A per-analysis run/.submission.lock serializes
submission checks and appends. Before another submission of a script, its latest entry
is polled through `_scheduler_status` on its recorded executor: terminal permits another
entry, running/pending refuses R-076, and unknown or a missing job identity refuses R-077.
Old entries and launchers are retained. No recovery or reservation-release command is added.

Verify retains approval, plan, declared-output and marker gates, and additionally
requires a nonempty submission record. For every script, its latest entry must have
script and launcher paths inside this analysis, unchanged SHA-256 values, and a
COMPLETED scheduler answer for that job on the recorded executor. A marker lacking
that binding is refused with “marker is not execution evidence.” An analysis submitted
before this fix has no record and is refused clearly; it needs executor submission
again. A run through no executor cannot pass verify.

**Correction to 0063:** its claim “requires an execution-created completion marker”
was not true for stage 03 at the merged implementation: the agent could write that
marker and its own script was told to produce it. This record corrects that claim in
its own text; 0063 is not edited. The launcher plus guarded record and scheduler binding
supply the execution evidence required by this fix.

### MINOR-2: cancellation fails closed

Inside the records lock the order is: job/backend check; terminal recorded state;
terminal stage STATUS; one `_scheduler_status` poll; scheduler_start and record save;
age gate; signal, then CANCELLED. Terminal recorded/stage checks retain their behavior.

A terminal poll is passed as `observed` to `_status_locked(..., observed=None)`, which
uses it instead of polling again and takes no records lock of its own. Cancel records
that result through status's existing writer path and refuses with the recorded state
in its reason; scheduler CANCELLED returns ok=true, as does the existing terminal case.
Scheduler COMPLETED with no marker follows status's existing ARTIFACT_MISSING behavior.
An unknown answer returns exactly `R-077: scheduler state unknown; cancel refused: <detail>`.
It signals nothing and changes neither record nor STATUS: no STALE write. Local exit
files supply terminal evidence; a vanished PID with no exit file reads FAILED.

### MINOR-1, MINOR-3 and notes

Tests now pin M8 (local record under Slurm descriptor; no scancel), M9 (COMPLETE stage
while a stub scheduler would answer RUNNING; no sacct, scancel or os.kill), and M11
(a downstream manifest coherently keyed to another assay's config; no backend submit).
Each has a fault plant that fails its named regression.

The parent contract's STATUS paragraph lists SUBMITTED, RUNNING, VALIDATING,
ARTIFACT_MISSING, STALE, COMPLETE, FAILED:<reason> and CANCELLED. Steps 5–9 and T2/T3
route intermediate states to step 10 and the sub-stage collect step; CANCELLED follows
FAILED to the user's decision. Stage 03 reports failures through scheduler logs and
executor status; verify alone writes its STATUS. The drift test derives states from
write_status arguments across _system, wrappers and authoring templates, _status_locked
literals, and BUILTINS/template status_map values. It normalizes failure reasons,
PENDING → SUBMITTED and the standing writer alias COMPLETED → COMPLETE, and asserts
all eight required states are derived before comparing the STATUS paragraph.

NOTE-2 adds the re-prepare sentence to DEVELOPMENT and the appended report: stages
prepared before the key fix must run prepare again before submit or collect.
NOTE-3 returns `R-152: retry_refused: the job was cancelled; prepare corrected inputs`
for a CANCELLED record, without changing classify or ruling 3's mapping.
NOTE-4 removes the unused project creation in ExecutorSeamTests.test_01.
NOTE-1 stays open: surviving accounting loss needs an owner ruling on the durable state table.

## Threat model

Covered: an agent session holding Write, Edit and Bash under guard_hook.py and settings.json.
Within that boundary it must not create stage-03 marker, launcher or submission record
by any tool or shell spelling the guard already refuses for stage 02; pass verify with
a marker its own script or command wrote outside an executor-launched run; cancel a
finished job; or guess a cancel when the scheduler cannot answer. The tests exercise
these guards, actual local launcher exit evidence, stub scheduler refusals and fault
plants in disposable copies. This is a guarded-session claim, not separate-user isolation.

## What this does not close

- An approved script body that does no real work and exits 0; the plan's declared-output
  gate still applies.
- The window between cancel's poll and its signal.
- PID reuse while a local job still reads RUNNING.
- Real Slurm/sacct/scancel output shapes, live scheduler acceptance (including R-076),
  Python 3.6.8 execution, separate OS users, and the harness's settings glob semantics.
- Ambiguous submission recovery (ruling 9): stop, retain evidence and work; no supported
  reconciliation or reservation release is invented here. Crash/acceptance ambiguity
  is not solved by stage-03 tracking.
- Published benchmark pins (ruling 10): remain deferred and untouched.
- NOTE-1: accounting loss can leave VALIDATING → STALE; durable completion and unattended
  reconciliation require the later durable state table ruling.
- Full row-12 exit remains NOT met. A review in an independent context on the same OS
  user is not an external human seal. Row 15's files and separate-user deployment stay
  outside this round.

## Owner rulings needed

No new implementation ruling is requested. Protected-path approval at merge remains
an owner action under R-094/spec §9.3: guard_hook.py, settings.json, and both changed
CONTEXT.md contracts require a separate owner commit, record **0070**, in the shape
of 0066. The producer never writes 0070 and never claims that approval. Earlier owner
questions above remain open and are not decided here.

## Test

The round-5 section of the [change report](../implementation/row_12_change_report.md#review-round-5-fixes-post-merge-on-e59dfc0)
records the commands, verbatim summaries and named red-on-fault witnesses. Contract
plants run against disposable copies of both parent CONTEXT.md files. No live scheduler
or sealed evidence is substituted by these tests.

Rounds 6 and 7 may only append a dated addendum after this record's last byte and rerun
`docs/decisions/build_index.sh`. They never rewrite this record's existing bytes.

## Status

Standing implementation record for the producer fix; independent review and protected-path owner approval remain pending.

## Date

2026-09-23
