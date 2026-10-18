---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/authoring/create_bioinformatics_skill.py
  - gars/tests/test_history_model.py
symptoms:
  - "it takes exactly one plain parameter named args, binds neither args nor ws and never calls locals, globals, vars or sys._getframe" from conform
---
# The fold of REVIEW-f3c7520: conform pins the name args and the module ws

The fold of the fresh review of lane gars-t74's run 8 (`lanes/gars-t74/REVIEW-f3c7520.md`), under glitch-b5's rulings of Sat 17 Oct 2026 (`lanes/gars-t74/RULINGS.md`). Wording is the lane's, under the owner's standing delegation; the approval record for the `_system/` change is glitch-b5's at landing. It builds on 0310, which is not edited.

## Context

**Finding 1 (MINOR).** 0310's allow-list inspects loads of the name `args` only. Nothing held that name to the namespace or `ws` to the module, so `def cmd_collect(ns):` with `args = ns` and a later `ns.model`, or `ws` rebound to an object whose `history_model` returns the flag, read the flag with conform green.

**NIT 1.** `locals()["args"].model` and `sys._getframe().f_locals["args"].model` reach the namespace without a load of the name and passed conform.

## Decision

1. **The name is pinned (ruling 1).** `cmd_collect`'s signature is exactly one plain parameter named `args`: no default, no `*` or `**`, no positional-only or keyword-only parameter. Inside the function any binding of `args` or `ws` fails: a store or delete, a for, with or comprehension target, a walrus, a nested def's or lambda's parameter, a nested def or class of that name, an import as, an except as, a global or nonlocal declaration, a match capture. Every shipped wrapper conforms unchanged.
2. **No namespace by reflection (ruling 2, NIT 1).** Any reference in `cmd_collect` to the names `locals`, `globals`, `vars` or `_getframe`, or to an attribute `_getframe`, fails, called or not, so an alias cannot hide one.

## What 0310 now closes

- **The renamed parameter and the rebound `ws`: closed.** With the name pinned, every load the allow-list reads is the namespace, and the one permitted call is the module's.
- **`locals`, `globals`, `vars`, `sys._getframe`: closed** inside `cmd_collect`.

## What this does not close

- Other reflection that never names these (`inspect.currentframe()`, a traceback's frame, `gc.get_referrers`) is not listed; the rule names what the ruling names.
- conform reads `cmd_collect` only; a module-level helper, a module-level rebinding of `ws`, or one that reads `sys.argv` is outside the rule, as under 0303 and 0310.

## Test

`gars/tests/test_history_model.py` `AuthoringTests` (2 new, 23 in the module): `test_conform_pins_the_name_args_and_never_lets_args_or_ws_be_rebound`, the review's two reproductions, and `test_conform_refuses_a_collect_that_reaches_the_namespace_without_naming_it`, the NIT's two; red at 809355b0 (`FAILED (failures=4)`, each `0 != 1`, conform ok true). A third row in the first (8455f3bd) is a witness for the signature clause: `args` a defaulted second parameter, nothing rebound; red against 809355b0's conform. Mutations: the signature check off `FAILED (failures=1)`; the store check off `FAILED (failures=1)`; the reader names off `FAILED (failures=1)`; the `_getframe` attribute off `FAILED (failures=1)`. `test_every_shipped_wrapper_still_conforms` green.

## Status

Standing.

## Date

2026-10-17
