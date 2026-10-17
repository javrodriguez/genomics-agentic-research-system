---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/02_bioinformatics/CONTEXT.md
  - gars/CLAUDE.md
  - gars/tests/test_gate_words.py
symptoms:
  - configure.py apply fails for scrnaseq with "needs --protocol (see configure.py protocols)"
  - the router never offers the single-cell library chemistry; the agent asks for it as free text
  - apply for scrnaseq rewrites the config's aligner to simpleaf
---
# The router offers the single-cell chemistry menu and confirms the choice

Item R-protocol of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner ("Add the chemistry menu to the router's settings step for single-cell, and show the choice in the confirmation message. The menu code already exists; only the contract omits it."). Wording is the lane's (gars-t74), under the owner's standing delegation.

## Context

`configure.py` registers scrnaseq as a `protocol` assay: `apply` needs `--protocol`, from the closed `protocols` menu filtered by aligner (decision 0020: a decision whose wrong value is silent comes from a menu). The router's step 3a named only the genome, contrast and peak menus, and its `apply` line carried no `--protocol`, so for single-cell the write failed with exit 2, or the agent supplied a chemistry the user never chose from a list. T9 showed no chemistry line, and `apply` without `--aligner` writes its default `simpleaf` over the config's aligner.

**Reproduction.** At dff38098, `gars/tests/test_gate_words.py::RouterProtocolMenuTests` fails: `'configure.py protocols --aligner' not found in '3a. ...'`.

## Decision

1. Step 3a names the protocol assays' decision and runs `configure.py protocols --aligner <the config's aligner>` beside the genome menu; its `apply` line carries `[--protocol <n> --aligner <the config's aligner>]`, and a sentence says why the aligner is passed as the config names it.
2. T8's render rule names `protocols` (each chemistry the config's aligner supports, with its meaning), verbatim from the JSON.
3. T9's decision line names `protocol + aligner` with meanings.
4. T10 (the non-public project) names the menu and the flags for the user's own terminal.
5. `gars/CLAUDE.md`'s summary of the stage 02 menus names the library chemistry.
No code changes: the menu and `apply --protocol` exist. Overlap with Landings A and C: the router contract (Landing A edited its non-public paragraphs, T10 and T11); only T10's menu and apply lines change there.

## What this does not close

- **R1** The config's aligner is read by the agent from the config; a public project allows that read, and on a non-public one the user runs the menu (T10). The aligner itself is not offered as a menu; changing it stays a re-analysis (the scrnaseq sub-stage's Scope Boundaries).
- **R2** T9's confirmation is still a free-text reply; R-confirm (record 0302) closes it on a fixed word.

## Test

`gars/tests/test_gate_words.py::RouterProtocolMenuTests::test_router_offers_and_confirms_the_chemistry` reads step 3a, the T8 render rule, T9 and T10; red before the contract change. `tests/check_contracts.py`, `gars/tests/test_lifecycle_contracts.py` and `gars/tests/test_wrapper_contract.py` stay green.

## Status

Standing. Contract and prose only; no `_system/` change.

## Date

2026-10-17
