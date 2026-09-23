---
date: 2026-09-22
status: standing
kind: defect
touches:
  - gars/_system/executorlib.py
  - gars/_system/wrapperlib.py
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/_system/wrappers/
  - gars/02_bioinformatics/
  - gars/tests/
  - docs/implementation/row_12_change_report.md
symptoms:
  - editing a prepared key permits a duplicate scheduler submission
  - editable execution records can attribute another job's success to a failed stage
  - a definite scheduler refusal permanently consumes a submission key
  - terminal STATUS regresses when scheduler accounting expires
---
# Row 12 review addendum

Addendum to [0063](0063-row-12-lifecycle-status-writer.md), whose original bytes remain
unchanged. This records producer fixes responding to the supplied independent review;
it is not an owner approval. Base for row 12 remains the approved row-4 head `d17573a`.
The owner's 12A and 13A rulings continue to apply. No state files are migrated.

## Corrections

Submit recomputes the exact R-076 digest from the current params.yaml bytes, the input
samplesheet named by those generated params, and the assay config derived from the stage
path. Both the manifest digest and the single script comment must match. Collect locates
the submission by that recomputed key and checks the recorded script's stage identity.
The COMPLETE writer repeats that binding and requires scheduler success as well as the
marker and output index for a recorded job. An edited backend cannot supply another
executor's success. Legacy unrecorded collection and downstream missing-key submission
remain explicitly outside these guarantees, pending the scope/input rulings below.

The workspace guard protects submission records, local job records, local exit sidecars,
completion markers, generated manifests, params and submit scripts, and the writer lock.
These are machine evidence; an agent must run prepare or a typed executor call. Protection
compares paths case-insensitively, including STATUS, files.csv and PLAN.md.approved. The
settings list is generated from the same READ_ONLY patterns. This is guarded-session
protection, not protection against an unguarded process owned by the same OS user.

Definite non-submission releases the reservation: failed validation, an unavailable backend,
or a positive nonzero scheduler exit without a printed job id. Successful invocation with
no parseable job id, signal termination, a job id accompanied by an error exit, and a failure
after the local process may have launched retain the reservation as ambiguous. The external
return shape is unchanged: `(job_id, detail)` and the existing JSON error string.

Ambiguous recovery is deliberately a stop: retain the record, script, logs and work; do not
resubmit, delete the reservation, or infer rejection from a missing accounting answer. The
owner must reconcile the submission with scheduler evidence. A supported record-binding or
reservation-release command needs a ruling on its evidence and authorization; none is invented
here. The contract addition describing that recovery remains an explicit owner action because
13A limits the permitted edits to the former STATUS instructions.

The shared writer serializes its read/validate/replace under a stage lock. Any transition
from COMPLETE, CANCELLED, REJECTED or FAILED (including qualified failure) refuses; writing
the same terminal state is an idempotent no-op. Status still reports the scheduler response
or error, but cannot rewrite a terminal STATUS even after accounting retention expires.
There is no general terminal-reset switch. A retry/corrective path remains stopped for the
owner's failure policy and approval binding, not implicitly authorized by this addendum.

The wrapper sweep now checks every STATUS substring outside comments or actual
`wl.write_status(...)` calls, as well as the existing AST write check. Four descriptive
module docstrings spell this as the lifecycle state file; behavior is unchanged. The minimum
wrapper count remains ten; adding wrappers no longer fails merely because there are eleven.
Computed, copied and formatted STATUS paths are each planted in disposable source copies
and must make the real sweep fail. Authoring-generator output still needs the scope ruling.

Redundant status calls are removed from the already typed submit steps and from repeated
poll branches. Four inherited raw-sbatch submission steps and collect-failure state wording
remain pending the explicit scope/state rulings; no wider contract rewrite is claimed.

## Owner decisions and acceptance

No new failure taxonomy, downstream key schema, retry threshold, cancellation timing schema,
or action-approval schema is chosen by this producer. The current round explicitly requires
stopping when these choices are left to the owner; the review's recommendation to adopt
provisional defaults is not an owner ruling. The complete options, per-finding dispositions,
protected-path approval action, template refresh and other residuals are in
[the round-2 report](../implementation/row_12_change_report.md#review-round-2-fixes).

The named test results and red-on-fault witnesses in that report delimit these fixes.
Full row-12 exit, real Slurm/Nextflow acceptance, Python 3.6.8 execution, Stage-3 reconciliation
and the outstanding owner-gated behavior are not claimed. Row 15, the pinned study trees,
CI, skills and pin inventory are unchanged. Merge still requires the owner's approval and
the separate study's done commit.

_Renumbered at merge, 2026-09-22: this record was written as 0058 on its branch and takes 0064 on main, because the row-5 fix and rows 15, 4, 11 and 12 numbered their decisions independently (merge order: row-5 fix, 15, 4, 11, 12). Its number, link targets and the numbers of other rows' records it cites are the only edits; branch-time number notes are left as written._
