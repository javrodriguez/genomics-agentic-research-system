---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/configure.py
  - gars/02_bioinformatics/CONTEXT.md
  - gars/CLAUDE.md
  - gars/_references/config_schema.md
  - gars/tests/test_configure_confirm.py
  - gars/tests/test_gate_words.py
  - gars/tests/test_r164_writer_recovery.py
  - gars/tests/test_r164_params_mapping.py
  - tests/run_tests.py
symptoms:
  - configure.py apply writes a contrast, formula or chemistry other than the one T9 showed
  - "configure.py apply refuses: no dry run is recorded for <assay>"
  - "configure.py apply refuses: this write differs from the dry run shown"
  - a free-text reply such as "yes but use batch" is taken as confirmation and the config is written
---
# A config write equals the dry run the user was shown

Item R-confirm of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner ("A fixed word ("write"), and the settings script refuses a write that differs from the trial run you saw."). Wording is the lane's (gars-t74), under the owner's standing delegation; the frozen-row change below is glitch-b5's named ruling of Sat 17 Oct 2026. The approval record for the `_system/` change is glitch-b5's at landing.

## Context

Router step 3a runs `configure.py apply --dry-run`, shows the would-be config in T9, and on confirmation re-runs without `--dry-run`. Nothing tied the second call to the first: the write took whatever flags it was given, so a write with another contrast, formula or chemistry than T9 showed, or with no dry run at all, was accepted (exit 0) and wrote a harm-9 setting the user never saw. T9 closed on "Confirm to write it", so a reply such as "yes, but adjusted for batch" read as confirmation.

**Reproduction.** At a3524713, `gars/tests/test_configure_confirm.py` fails seven tests and errors in one (`FAILED (failures=7, errors=1)`): each write after a different, missing, other-assay or refused dry run, or onto a changed config, exits 0 where 1 is expected; the control (same-argument write) passes. `test_gate_words.py::RouterWriteGateTests` fails: T9 ends "Confirm to write it".

## Decision

1. A clean `apply --dry-run` records `_config/.<Assay ID>.dry_run.json`: the assay, the sha256 of the exact text it would write, and the settings it resolved (genome, contrast, formula, peak type, protocol, aligner, as present). A refused dry run records nothing.
2. `apply` without `--dry-run` computes the text as before and writes only when that text's sha256 equals the record's. Otherwise it refuses with exit 1 (the existing refusal code, which step 3a already routes to T8) and the config keeps its bytes: no record, or one not exactly the shape the script writes, says "no dry run is recorded"; different settings name both the dry run's and this write's; equal settings with different bytes say the config changed since the dry run.
3. The record is kept after a write and is not single-use, unlike stage 01's (record 0300): it binds bytes, not a gate, and re-applying the shown settings to the written file yields the same bytes, so a repeat can only rewrite what the user saw. Any change of settings or of the file underneath needs a new dry run.
4. T9 closes on the one word `write`; step 3a writes only on it and on any other reply re-runs the dry run and sends T9 again; T10 gives the user's own terminal the dry-run line first. `gars/CLAUDE.md` and `_references/config_schema.md` say the same by description.
5. Callers that applied with no dry run, the path this item outlaws, now run the same argv with `--dry-run` first and assert its exit 0, with every earlier assertion kept: nine tests in `tests/run_tests.py`, the `apply` helper of `gars/tests/test_r164_params_mapping.py` (which `test_r164_keyed_lookups.py` also drives), and the `configure_apply` row of the frozen Landing C file `gars/tests/test_r164_writer_recovery.py`, under glitch-b5's ruling 1 of Sat 17 Oct 2026 (an overlap with Landing C named in the commit). Callers that expect a refusal before the write are unchanged: the refusal comes first.

## What this does not close

- **The record is not guarded.** `_config/` is agent-writable (the agent may edit configs), so a Write of a forged record with the right sha256 passes. That is deliberate forgery, as in 0299 R2; a one-line guard rule (`projects/*/_config/.*.dry_run.json`) would close the Write path, and the frozen guard is glitch-b5's to change.
- The record proves the script showed the text, not that the user read it or replied `write` (0299 R1); no live session has walked the gate.
- Lane gars-ms21's T57 may add `compute.mem` to what `apply` writes. The record hashes the text as written, so it follows any such key, but the bytes-equal control is to be re-checked once T57 lands.
- A reproduction package copies `_config/` whole (`claims/package_run.py`), so it now carries the record: a hash and the settings already in the config.
- The dry run's record write is atomic (`workspace.atomic_open`) but has no row of its own in the writer-recovery table; that frozen table gains one when it is next opened.

## Test

`gars/tests/test_configure_confirm.py` (nine tests): another contrast, formula or chemistry than the dry run; no dry run; another assay's dry run; a refused dry run; a config changed since; hand-made records of other shapes (subtests); and the control, a same-argument write equal to the preview byte for byte, again on re-apply. `gars/tests/test_gate_words.py::RouterWriteGateTests`: T9's closing word, step 3a's re-ask, T10's dry-run line.
Mutation: `unmatched_dry_run` returning nothing turns the eight refusal tests red (`FAILED (failures=11)`, counting subtests).

## Status

Standing.

## Date

2026-10-17
