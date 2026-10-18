---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/configure.py
  - gars/02_bioinformatics/CONTEXT.md
  - gars/_references/config_schema.md
  - gars/tests/test_configure_formulas.py
symptoms:
  - "formula NN (...) is not estimable" from configure.py apply
  - "formula term ... is not estimable" from configure.py apply
  - "... is not a number on the formula menu" from configure.py apply
  - formula_warning "was typed, not chosen from configure.py formulas"
  - "this helper, interpreter or executable is not registered" for configure.py formulas (registry hunk not applied)
---
# Formula choices are built from the design's own columns

Item R-formula of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner. Wording is the lane's (gars-t74), under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing, and so is the registry entry the lane may not write: `lanes/gars-t74/R-formula-registry.patch`. It builds on 0020 (a decision whose wrong value is silent comes from a menu) and 0302 (a write equals the dry run shown).

## Context

Stage 02 offered the contrast as a menu but took `de.formula` as free text ("`~ batch + condition` to control for batch"); `apply` checked only that each term was a design column. A user had to know the formula syntax, and a covariate nested in the condition (each batch under one condition) passed the term check and gave DESeq2 a design it cannot fit, or a result that silently absorbs the effect of interest.

**Reproduction.** At 29367a2a, `gars/tests/test_configure_formulas.py` fails all seven (`FAILED (failures=5, errors=2)`): there is no `formulas` subcommand (exit 2); `apply --formula 2` writes the formula `2`; a typed formula carries no warning (`KeyError: 'formula_warning'`); the guard refuses the command; the router names no formula menu.

## Decision

1. `configure.py formulas --project P --assay A [--factor condition]` reads `01_samplesheets/<A>_design.csv` and numbers `~ <factor>` ("<factor> only"), then `~ <column> + <factor>` for each column that is not one of the assay's design columns or the factor and that has at least two values, in design order ("adjusted for <column>"; "paired by subject" for `subject`).
2. A column nested in the factor (every value under one factor level) or blank for any sample is listed `estimable: false` with the reason, never as a choice.
3. `apply --formula <n>` writes that menu formula and refuses one not estimable. A token of digits only that is not a menu number is refused with the numbered menu and nothing written, never taken as a formula (run 11 ruling 2, REVIEW-a745042 finding 2). A formula typed instead is still checked term by term: every column it names other than the factor, offered on the menu or not, is refused when it is blank for any sample, has one value for every sample, or is nested in the factor (run 11 ruling 4, REVIEW-a745042 NIT 2). A typed formula equal to a menu entry (white space aside) is written as that entry with no warning, and refused where that entry is not estimable; any other is written with `formula_warning` that it was not chosen from the menu; T9 shows the warning verbatim. With no `--formula` the presented default `~ condition` is unchanged. This takes the plan's "accepted with a printed warning" branch; refusing typed formulas outright is left to a ruling.
4. The router contract: step 3a runs `formulas` beside `contrasts` and passes `--formula <n>`; T8 renders both menus; Scope says never to compose a formula; T9 and T5 follow. `config_schema.md`'s decision table says the formula comes from the menu.
5. Registry hunk: `configure.formulas`, the same shape and roles as `configure.contrasts`. `apply`'s entry is unchanged (its `--formula` flag exists).

## What this does not close

- **Only single covariates are offered.** `~ batch + subject + condition` and interactions are typed formulas, with the warning; whether two covariates are jointly estimable is not checked.
- **Estimability is blanks, one value and nesting only.** A covariate that crosses the factor in one sample but is otherwise aliased is offered; DESeq2's own rank check remains the last word.

## Test

`gars/tests/test_configure_formulas.py` (10 tests): the menu from the design's columns, numbered with meanings; a nested column not a choice and refused by apply; a one-value column not offered; a menu number writes that formula; a number off the menu refused with the menu (red at 90044abe); a typed formula written with a warning and a non-column term refused; a typed formula naming a one-value, blank or nested column refused, and one equal to a menu entry written as that entry (red at 5ebec57b); the guard admits the command (green only with the registry hunk); the router contract.
Mutation: apply ignores menu numbers `FAILED (failures=2, errors=1)` (the errors row is the guard's, waiting on the hunk).

## Status

Standing.

## Date

2026-10-17
