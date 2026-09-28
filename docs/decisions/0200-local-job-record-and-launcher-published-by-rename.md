---
date: 2026-09-28
status: standing
kind: decision
touches:
  - gars/_system/executorlib.py
  - gars/tests/test_r164_writer_recovery.py
symptoms:
  - a write fault while the local backend records a started job leaves a torn job record, and status then fails to parse it
  - a write fault while stage 03 writes its launcher leaves a truncated run/launch-*.sh, and the run is later refused with R-135
---
# The local job record and the stage-03 launcher are published by rename

Follow-up to [0087](0087-row-3-followup-suite-strengthening.md)'s round-5 addendum, ruling (a), and to [0195](0195-local-exit-record-published-by-rename.md), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and ruled by the lane's coordinator on 28 September 2026; no sentence in this record is the owner's.
0201 is the lane's delegated approval of the protected change; this record does not write it.

## Context

0087's round-5 addendum named four non-atomic writers of recorded state as real R-164 class-2 defects and left them to "a later, non-test-only item with its own approval record", which would then add their rows to `gars/tests/test_r164_writer_recovery.py`.
This record closes the first two, the two a scratch probe observed:

1. **`executorlib._local_submit`'s job record** (`<project>/.gars_local_jobs/<pid>.json`) was written with a plain `open(..., "w")` after the job had been detached. A fault part-way through left a torn record at the published name, and `_local_status` then raised on `json.loads` for that job.
2. **`executorlib._analysis_launcher`'s launcher** (`run/launch-<uuid>.sh`) was written with `Path.write_bytes`. A fault part-way through left a truncated launcher at the published name, which 0087 observed refused later with R-135.

**Reproduction.** The two new rows in the writer-recovery table drive each writer through the table's injector, which matches a fault by destination file: a refused open, a write that lands half its data and then fails, a refused fsync, a refused rename, and the same write fault on a first write.
The job-record row answers the detach in-process with a fixed pid, so no job starts and the record is the only file written; the launcher row pins the uuid so the destination has a known name, and its script carries a kept `#SBATCH` directive with a byte that is not UTF-8.
At `0d9954c` both rows fail 4 of 5 steps on the development Mac, 28 September 2026: the half write lands on the published name (a torn record, a truncated launcher), and the fsync and rename faults are never reached because neither writer fsyncs or renames.
The refused open passes at the baseline as well, the honest control.

## Decision

**Ruling 0200 (the lane's).**

1. **The job record** is written through the house helper `workspace.atomic_open` (a sibling `name.tmp`, fsync, `os.replace`, the temp removed on any failure), as `executorlib`'s submission record (`_save_record`) and failure record (`record_failure`) already are.
2. **The launcher** is written through `_publish_bytes`, a bytes twin of that helper in `executorlib`, because the launcher keeps the script's leading directives byte-for-byte and they need not be UTF-8.
3. On success the bytes, names and modes written are those of the old writers.

In-spec choices (the lane's): the house helper's fixed `.tmp` sibling, not a `mkstemp` name, for consistency with every other `atomic_open` writer; a bytes twin in `executorlib`, not a new mode on `workspace.atomic_open`, to keep the change inside the one file 0087 named; the two observed writers only.

Rejected alternatives: decoding the directives to use the text helper (it would refuse or alter a directive that is not UTF-8); cleaning a torn record up in the reader (the torn file would still be the published record).

## What this does not close

- **R1** A fault while writing the job record leaves the detached job running with no record; `status` reads `FAILED` for it ("nothing here started that job"), as for any absent record. Before this change the same fault left a torn record that `status` could not parse.
- **R2** The other two writers of 0087's ruling (a), the `ANALYSIS_SUBMISSIONS` append and stage 00's project creation, and stage 03 create's allocated folders (the later round-7 finding), stay open.
- **R3** A link planted at the `.tmp` sibling's name is followed, as by every `atomic_open` writer in GARS and by the plain `open` this replaces. `.gars_local_jobs/*` is on the guard's protected-path list; the launcher's name carries a random uuid.

## Test

`gars/tests/test_r164_writer_recovery.py` gains two rows, `executorlib._local_submit` and `executorlib._analysis_launcher`, each with the table's five steps and its fixed postcondition: the fault surfaces, the destination keeps its prior bytes exactly (or stays absent on a first write), and no file or directory appears anywhere in the fixture tree.
They must fail when the job record goes back to a plain `open` (the record row), when the launcher goes back to `write_bytes`, when `_publish_bytes` drops its fsync, when it keeps its temp on failure, and when it writes the published name directly (the launcher row).
The lane's mutation proof at the branch head killed all five.
The landing's evidence is recorded in 0201.

## Status

Standing. The change record for the torn local job record and stage-03 launcher; its protected-change approval is 0201.

## Date

2026-09-28
