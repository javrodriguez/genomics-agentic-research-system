---
date: 2026-08-20
status: standing
touches:
  - gars/_system/integrity.py
  - gars/00_initialize_project/CONTEXT.md
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/_system/stage00_register.py
  - gars/_system/stage01_samplesheet.py
---
# Deep file-integrity verification moves to stage 01, and is opt-in

**Question.** Stage 00 decompressed every registered FASTQ to verify it. On the first real cohort
— 38 samples, 152 files, **48 GB** — that step never completed, and it was verifying files the
user was about to exclude.

**Decision: split the check by stage, and ask before doing the expensive half.**

| Stage | Checks | Cost | Default |
|---|---|---|---|
| 00 | link resolves, non-empty, gzip magic | metadata only | on (`quick`) |
| 01 | full decompression of the **included** files | O(data) | **off** |

## Why the split falls here

Stage 00 registers everything the user pointed at. **The user does not choose which samples to
analyse until the 00 → 01 gate.** Deep-verifying at registration therefore spends the cost on
files that are about to be dropped — on the real cohort, potentially 48 GB of reading to validate
a 4-sample pilot.

Stage 01 is the first moment the included subset exists, and the last moment before hours of
pipeline compute. That is exactly where a truncated FASTQ is cheap to catch and expensive to miss.

This refines the existing doctrine rather than breaking it. "File-level checks belong to stage 00"
still holds for the checks that cannot be deferred: a link that does not resolve means
registration itself failed. What moves is only the part whose cost scales with data the user has
not yet chosen.

## Why it is opt-in

FASTQs normally arrive from a sequencing core that has already validated them. Re-decompressing
them by default taxes every project for a failure that is rare and, by then, someone else's. The
contract now **asks**, quoting the measured cost of the included subset, and the answer is
recorded — `HISTORY.md` carries `Deep file-integrity verification: full|none`, so a project can
always name the verification it received.

**Never downgrade it unprompted.** A faster mode is exactly the shortcut an agent under time
pressure takes; the contract forbids choosing one on the agent's own initiative, and the record
makes any downgrade visible afterwards.

## Deep verification is scheduled work

Above ~10 GB the contract submits the check with `sbatch` instead of running it inline. This is
not a new rule: [0010](0010-skill-chaining-defects-and-adaptation.md) already established it after
a pure-Python DE step was SIGKILLed on a login node. The integrity check broke a rule the project
had already learned.

The proximate cause of the failed runs was in fact the login node's **memory cgroup** — a 4 GB
budget shared across every process the user owns there, which the OOM killer enforces on whatever
is running rather than on whatever is at fault. But the cgroup only got the chance because 48 GB
of GPFS reading was happening on a shared login node at load average 100. Both are reasons to
schedule it.

## What measurement changed

Assumptions that did not survive contact with the data:

- **Python's `gzip` is faster than the system `gzip -t` binary here** — 15.6 s vs 26.0 s on a
  666 MB file. Shelling out to C would have been a pessimisation.
- **The work is I/O-bound, not CPU-bound.** A pass reading two bytes per file took 3m51s wall at
  0.1 s of CPU.
- **Concurrency past 4 buys nothing** — 4 and 16 workers measured the same ~130 MB/s.
- **It does not leak** — peak RSS ~70 MB.

The general lesson: **an O(data) gate needs a measured cost in its contract, not an adjective.**
"Expect minutes on a real cohort" was written without ever having run one.
