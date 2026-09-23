---
date: 2026-09-22
status: proposed
kind: defect
touches:
  - gars/_system/executorlib.py
  - gars/_system/wrapperlib.py
  - gars/tests/test_lifecycle_executor.py
  - gars/tests/test_lifecycle_faults.py
  - gars/tests/test_no_false_completion.py
  - docs/implementation/row_12_change_report.md
symptoms:
  - corrected inputs cannot submit after a recorded failure or cancellation
  - re-prepare detaches status from a running job and permits overlapping submission
  - forged-record completion test passes for an unavailable scheduler instead of the binding
---
# Row 12 corrected-inputs addendum

Addendum to [0058](0058-row-12-review-addendum.md) and
[0057](0057-row-12-lifecycle-status-writer.md). Both retain their original bytes.
This is a producer correction in response to the supplied round-2 review, not an
owner approval. The approved row-4 base remains `d17573a`; 12A and 13A still apply.

## Correction to the recorded behavior

0058's blanket terminal refusal wedged **all** FAILED/CANCELLED stages, even after
corrected inputs and prepare produced a different key. It did not merely refuse a
same-key retry. Its only physical workaround was an unguarded human deleting STATUS;
that was not a supported or documented recovery procedure. Do not use that workaround:
it discards authority and does not reconcile the job or its reservation.

Submit now retains the refusal for every previously recorded key. A new key may
replace a recorded FAILED/CANCELLED attempt after the normal prepared-input/config
checks. The new reservation has an optional `supersedes_key` identifying the previous
attempt. `write_status(..., submission_key=key)` allows SUBMITTED from that terminal
only when the current prepared key, accepted new job record, different superseded key,
previous record's stage, and previous terminal reason all agree. There is no force/reset
flag and no agent-writable status path. COMPLETE, REJECTED and terminals without a
matching failed/cancelled record still refuse this corrective transition.

`supersedes_key` is the linkage explicitly requested by MAJOR-1. Existing records need
no rewrite; an absent link means an initial attempt. The tests use old-format records
as well as linked attempts. Rolling back this implementation restores the earlier
conservative refusal; it does not require erasing records or migrating STATUS values.
This does not implement the owner-gated same-key retry policy or a new approval system.

A definite backend refusal releases only the new reservation and preserves the previous
terminal STATUS. An ambiguous submission retains its reservation and the previous
terminal STATUS; further submissions refuse. Preserve records, logs and work and request
owner reconciliation for ambiguity, conflicting records, or legacy terminal evidence.
The owner still must select the supported recovery operation; deleting STATUS or a
reservation is not offered as that operation.

## Tracking the submitted attempt

Status validates the recorded key against its reservation filename and derives the stage
from the record's canonical generated-script path. It deliberately does not hash the
**current** preparation: prepare can overwrite that script and its inputs, and their
new digest cannot identify the old submitted job. The guarded submission record retains
the identity validated at submission. Collect and the COMPLETE writer still recompute
current inputs and require the record to belong to that stage. This remains guarded-
session protection; it does not authenticate arbitrary unguarded same-UID record edits.

Submit refuses a different key while any stage record has a non-terminal or unresolved
scheduler state, including unknown/unreachable and ambiguous submissions. Poll the old
job first. Submit and status share the reservation lock, so status cannot overwrite a
record while another caller reserves a corrective attempt. Terminal scheduler evidence
is retained when accounting later disappears. A late status poll for a superseded job
may report its scheduler answer but cannot write the replacement attempt's STATUS.
The job-id suffix comes from the polled record even if the manifest now names a new key.

## Test and remaining rulings

The forged-record test now holds scheduler COMPLETED for both collect and direct
write_status, and requires the binding-specific refusal. Its script-identity mutant
must fail. Additional mutants restore the terminal wedge, current-manifest rebinding,
and overlapping submission; each must fail its named behavioral regression.

[The round-3 report](../implementation/row_12_change_report.md#review-round-3-fixes)
records commands, verbatim results and remaining owner questions. The timestamp proposed
in NOTE-3 is deferred with the existing cancellation timing/schema ruling: submission
wall time is not a measurement of consumed compute. No cancellation, classifier, bounded
retry, downstream key, collect-failure mapping, contract expansion, row-15 work, protected
study edit, owner approval, full row exit or live scheduler acceptance is claimed.
