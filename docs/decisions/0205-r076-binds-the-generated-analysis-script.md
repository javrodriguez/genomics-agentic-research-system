---
date: 2026-09-28
status: standing
kind: decision
touches:
  - gars/_system/wrapperlib.py
  - gars/_system/executorlib.py
  - gars/tests/test_r076_script_binding.py
  - gars/tests/test_downstream_keys.py
  - gars/tests/test_rerun_check.py
  - docs/implementation/r076_script_hash_build_log.md
symptoms:
  - a downstream stage's scripts/run_de.py (or run_scrna.py, count_clusters.py) edited after prepare is submitted and run under the prepared key
  - a module added beside the generated script (scripts/pandas.py) is imported by the job, and submit accepts it
  - a script changed after submit still collects under a manifest that names the prepared code
---
# R-076 binds the generated analysis script

Follow-up to [0063](0063-row-12-lifecycle-status-writer.md) (the R-076 key formulas) and to row 13's step B review 1 finding 2 (the residual 0141 named), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 by the lane's coordinator; no sentence in this record is the owner's.
0206 is the lane's delegated approval of the protected change; this record does not write it.

## Context

A downstream wrapper's `prepare` (rnaseq-de, scrna-qc-cluster, spatial-cluster-count) writes the analysis itself as a generated script under the stage's `scripts/` folder, and a `submit.sh` that runs it with `"$GARS_PY" "<stage>/scripts/<name>.py"`.
It then records the R-076 idempotency key, which `executorlib.prepared_key` recomputes from current bytes at submit and at collect.
The `downstream-v1` formula (`wrapperlib.input_key`) hashes each declared input, the config and the params; nothing under `scripts/` enters it.

Reproduced at public main `81c0d71` by `gars/tests/test_r076_script_binding.py`, for all three wrappers, with a real `prepare` and the backend patched:

1. One changed byte in the generated script, then `executor.submit`: accepted (`('42', None)`, the backend called once).
2. A file added beside the script (`scripts/pandas.py`): accepted. Python puts the script's own folder first on its import path, so that file is code the job runs.
3. The script deleted, or replaced by a symlink to the same bytes elsewhere: accepted.
4. The script changed after submit: `stage_record` (the collect and COMPLETE-gate binding) still binds.

Row 13's fix round 2 (0141) already refuses an agent's Write in a closed project, so the remaining routes are a human, an editor or sync client, any outside process, and an agent in a public project, where `READ_ONLY` has no `scripts/` line.

## Decision

1. **A new key formula, `downstream-v2`.**
   It is `downstream-v1`'s framing under the tag `GARS downstream v2`, then a NUL, then a framed walk of `<stage>/scripts/` (`wrapperlib.scripts_tree_digest`).
   The walk reads every entry by `lstat`, never following a link, in sorted relative-path order: a regular file frames its path, size and SHA-256; a symlink its path and link text; a folder its path; anything else its path and kind.
   A missing `scripts/` folder frames a state of its own; a `scripts/` that is itself a link or not a folder, and any folder the walk cannot list, have no key at all (the walk raises, so prepare fails and submit and collect refuse).
   Python can import from a folder it cannot list, so such a folder is never framed as empty (lane review r1 F-3).
   `downstream-v1` and `stage01-v1` are unchanged byte for byte.
2. **A downstream prepare records `downstream-v2`, and binds only what it generated.** Stage 01 keeps `stage01-v1`.
   Before computing the key, `write_reproducibility` requires `scripts/` to be a real folder holding exactly the scripts its `submit.sh` runs, each a regular file (`require_generated_scripts_only`); anything else refuses the prepare with a count, never a name, and asks for the extra entries to be removed.
   So a module added after prepare is refused at submit, the re-prepare that refusal asks for refuses too, and the module is never folded into a new key (lane review r1 F-2); a `scripts/` already linked elsewhere when prepare runs is refused the same way (F-1).
3. **Submit refuses a `downstream-v1` stage** with the existing `R-076: idempotency_key_missing_or_changed; run prepare`: a stage prepared before this landing is prepared again, never submitted with an unbound script.
   `stage_record` still accepts `downstream-v1`, so a job submitted before the landing still collects.
4. **Lane ruling: no `READ_ONLY` line for `projects/*/02_bioinformatics/*/scripts/*`** (row 13 re-review 2's NOTE asked that it be considered).
   The key refuses a changed script at submit whoever wrote it, and refuses to collect after a change made while the job waited.
   The line would stop only an agent in a public project, which can already run code of its own through Bash, and whose edit is refused at submit; the re-prepare that refusal asks for regenerates the script and refuses while anything else is left in `scripts/`.
   It would also be a guard change (`guard_hook.py`, the `settings.json` deny lists and their drift tests) for no harm the key leaves open.
5. **A replay's key is its own.**
   The generated script names its project and stage, so a `downstream-v2` key is bound to its location, and row 6's reproduction (`scripts/rerun_check.py`, 0097) now prepares each replay under a key of its own.
   Nothing in `rerun_check.py` compares keys; its test did, and now asserts that the replay's key is its recomputed v2 key and that the relocation-invariant part (the inputs and params, which is the v1 key) equals the original's.

## Rejected alternatives

- **Hash only the one generated script.** It misses the added-module route (item 2 above).
- **Record the prepared file list in the manifest and hash only those files.** Same miss: an added file is outside the list.
- **Have prepare empty `scripts/` before writing.** It would delete files a human put there; prepare refuses instead and the human removes them.
- **Verify the script at job start inside `submit.sh`.** It closes the queue-wait window, but it changes the `submit.sh` generator for every wrapper; collect already refuses the output of a script changed while queued.
- **Change `downstream-v1` in place.** Every job submitted before the landing would stop collecting, because collect recomputes the key.
- **Accept `downstream-v1` at submit.** A stage prepared before the landing would keep the gap until someone re-prepared it.

## What this does not close

- **R1 The queue wait.** A script changed after submit and before the scheduler starts the job still runs; collect and the COMPLETE gate then refuse its output, but the compute is spent.
- **R2 Other executed code.** `submit.sh`'s own body (read-only to the agent since row 12), `_system/` code and the job's environment are not in the key.
- **R3 Jobs already submitted under `downstream-v1`** keep their unbound script until they are prepared again.
- **R4 A check-then-use window** between the key's recomputation at submit and the scheduler reading the script (milliseconds on the local executor).

## Test

`gars/tests/test_r076_script_binding.py`, red at `81c0d71` (`FAILED (failures=15, errors=3)`), green after:

- C1 a same-size one-byte change is refused at submit, the backend never called, no record written;
- C2 an added module is refused; C2b a deleted script and a symlinked script are refused;
- C3 the prepared script submits once, and a later change makes `stage_record` raise;
- C4 re-running prepare restores the script and the key (the green control);
- C5 a coherent `downstream-v1` stage is refused at submit and a v1 record still binds collect;
- C6 an added module is refused at submit, the re-prepare refuses and leaves it in place, and only its removal lets the stage prepare and submit;
- C7 a `scripts/` folder linked elsewhere before prepare fails the prepare, and an edit behind the link is refused at submit;
- G1-G4 every tree difference changes the key (content, rename, add, folder, nested file, link), the same tree gives the same key, v1 ignores `scripts/`, a missing `scripts/` differs from the real one and a linked one has no key, and a folder the walk cannot list raises.

Mutations, each killed by the named test: (i) v2 skips the walk (C1); (ii) files framed without their digest (C1); (iii) links followed (C2b); (iv) folders not framed (G1); (v) prepare writes v1 (C3); (vi) submit accepts v1 (C5); (vii) a linked `scripts/` folder is walked (G3); (viii) prepare binds whatever `scripts/` holds (C6); (ix) the walk skips a folder it cannot list (G4); (x) prepare accepts a linked `scripts/` folder (C7).

## Status

Standing. Implemented on a lane branch; the delegated approval of the protected change is 0206.

## Date

2026-09-28
