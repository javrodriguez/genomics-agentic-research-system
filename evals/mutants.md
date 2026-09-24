# Row 3 sealed-mutant record

State: **sealed (independent_context)**. Score: **5/10 killed at 2a65dbf (first run, development evidence)**. Row 3 exit: **NOT met as development evidence; public claim unmeasured — needs external_human_seal**.
The producer has not authored or inspected the sealed set; the ten rows below are transcribed
mechanically from the runner's stdout at the run SHA by the coordinator's transcriber, not by
the sealer (decision 0086, gap d). Public runner-control faults are not members of this set.

Seal type: `independent_context`. Sealer identity: independent Codex assistant context; model identified by the session instructions as GPT-6. No more specific backend model identifier was supplied. Seal date: 2026-09-15.
Source SHA: `f76492b` (derived, not supplied: hash match 55/55 of the seal's supplied-input
inventory; the seal names no commit). Hashes of the ten diffs and expected records: each
row's `mutant_diff_sha256` and `expected_sha256` in the run record, 20/20 equal to the
seal's list. Environment/skips: macOS, Python 3.13.2, 9 environment skips in the baseline
suite. First-run score: 5/10 killed at run SHA `2a65dbf0c6383cc71b97bf19f0838482d542f1be`. Public credibility claims require
`external_human_seal`. Run record: [2026-09-23-2a65dbf-first-run.json](mutation-runs/2026-09-23-2a65dbf-first-run.json).
See [MUTANTS-INTERFACE.md](MUTANTS-INTERFACE.md) for the complete handoff.

| Slot | Mutant id | Requirement attacked | Killing test or `survived` | Run SHA | State |
|---|---|---|---|---|---|
| 01 | M01 | R-164 | `__main__.GuardHookTests.test_denies` | `2a65dbf` | killed |
| 02 | M02 | R-164 | `test_pre_push.PrePushTests.test_each_empty_tree_refuses (tree='tests/test_gate_sample.py')` | `2a65dbf` | killed |
| 03 | M03 | R-164 | `survived` | `2a65dbf` | survived |
| 04 | M04 | R-164 | `__main__.ExecutorSeamTests.test_00_slurm_default_is_byte_identical` | `2a65dbf` | killed |
| 05 | M05 | R-164 | `survived` | `2a65dbf` | survived |
| 06 | M06 | R-164 | `__main__.ExecutorSeamTests.test_05_local_backend_walks_submit_to_completed` | `2a65dbf` | killed |
| 07 | M07 | R-164 | `survived` | `2a65dbf` | survived |
| 08 | M08 | R-164 | `survived` | `2a65dbf` | survived |
| 09 | M09 | R-164 | `__main__.SpatialviTests.test_04_collect_gates_per_sample_and_never_takes_the_raw_h5ad` | `2a65dbf` | killed |
| 10 | M10 | R-164 | `survived` | `2a65dbf` | survived |

Record `ineffective` explicitly if returned; never convert it into a kill or silently remove
it from the denominator. A changed seal is a separate run with retained first-run evidence.
The sealer fills this document from its own run after the producer commit.
