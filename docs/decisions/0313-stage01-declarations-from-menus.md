---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/configure.py
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/tests/test_stage01_declare.py
symptoms:
  - "is not on the strandedness menu; reply with a menu number" from configure.py declare
  - "does not declare strandedness; its declarations:" from configure.py declare
  - "this helper, interpreter or executable is not registered" for configure.py declare (registry hunk not applied)
  - a stage 01 declaration written in the user's own words, e.g. "dUTP"
---
# Stage 01's declarations are numbered menus, written by the script

Item S01-declare of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner. Wording is the lane's (gars-t74), under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing, and so is the registry entry, which the lane may not write: `lanes/gars-t74/S01-declare-registry.patch`. It builds on 0019 (stage 01's declarations live in `_config/<Assay ID>.yaml`) and 0020 (a decision whose wrong value is silent comes from a menu).

## Context

Stage 01 asked for RNA strandedness and the RNA/ATAC replication unit, reference release and pairing in T9 as free text, and the agent wrote "exactly the user's values" into the config and a HISTORY line quoting them. A user who says "the libraries are dUTP" has answered the scientific question but not with a value stage 01 accepts, and the agent translated it; a translation that is merely wrong (forward for a dUTP library) validates, runs and gives a confident wrong answer. Stage 02 already offers genomes, contrasts, peak types and chemistries as numbered menus; stage 01 did not.

**Reproduction.** At 0729ac3b, `gars/tests/test_stage01_declare.py` fails all nine (`FAILED (failures=14, errors=1)`, subtests counted): `configure.py declare` does not exist (argparse exit 2 for every command), the guard refuses it as unregistered, and the stage 01 contract names no menu.

## Decision

1. `configure.py declare --project P --assay A` lists the declarations stage 01 checks for that assay (strandedness for `rnaseq_bulk`; `unit_of_replication`, `reference_release`, `paired` for `rnaseq_bulk` and `atacseq_bulk`) and which required ones are undeclared.
2. `--key K` prints K's numbered menu, each value with what it means. strandedness, unit_of_replication and paired offer exactly the values stage 01 accepts (a test keeps the sets equal); the reference release is offered from `_references/genomes.md`'s rows, as `<ID> <annotation release>`.
3. `--key K --select N` writes exactly the menu's value as K's top-level line (every other line kept; a missing key is added after `reference_release`) and appends `<date> <assay> K: value; chosen from the configure.py declare menu, option N` to `HISTORY.md`, the declaration-line format stage 01's provenance record already reads. A menu number or the exact menu value is accepted; anything else exits 1 with the same menu and nothing written. A key the assay does not take is a usage error (exit 3).
4. The stage 01 contract: step 2 runs the overview, then each undeclared key's menu, sends T9 with them, and on a number per key runs `--select`; any other reply, in the user's own words or off the menu, gets T9 again. The agent never writes a declaration into the config or HISTORY.md itself.
5. The registry entry `configure.declare` (assay enum `rnaseq_bulk`, `atacseq_bulk`; key enum the four keys; roles as `configure.apply`) is a hunk for glitch-b5. Until it is applied the guard refuses the command and `test_the_guard_admits_the_declare_command` stays red.

## What this does not close

- **The guard does not refuse a hand edit of the declaration keys.** The agent can still write `_config/<Assay ID>.yaml` directly; the contract forbids it, and a guard rule would be a frozen-file hunk. The HISTORY line written by `declare` is the provenance a hand edit lacks.
- **The HISTORY line no longer quotes the user.** It names the menu option; the user's own words are in the session, not the record. The format still locates a declaration and does not authenticate its author (Definitions).
- **The release is checked against the registry only when chosen here.** stage 01 still accepts any nonblank release already in a config.

## Test

`gars/tests/test_stage01_declare.py` (9 tests): the overview; each menu equal to stage 01's values, numbered, with meanings; a number writes exactly the menu value, one changed line, and the history line stage 01's provenance finds; five free-text and off-menu answers refused with nothing written; the release menu from the registry; pairing added where absent; a key the assay does not take; the guard admits the command (green only with the registry hunk applied); the contract runs the menu.
Mutation: declare writes the typed value `FAILED (failures=5, errors=1)`.

## Status

Standing.

## Date

2026-10-17
