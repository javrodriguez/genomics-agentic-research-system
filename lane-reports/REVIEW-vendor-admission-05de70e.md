VERDICT: PASS

# Review, round 2: lane vendor-admission, b0cf963b..05de70e5

Reviewer: a fresh, independent cloud reviewer, briefed by glitch-b5. Written Fri 16 Oct 2026, 22:05 EDT.
Head reviewed: 05de70e5 on lane/vendor-admission (unshallowed). Range touches 8 files: tests/test_vendor_admission.py,
tests/test_freeze_shapes.py, codex_adapter.py, gemini_adapter.py, three COPIED.d fragments, and the LANE file.

## Findings

None at MINOR or above.

What was checked, against the three scope items:

1. **Round 1 finding 1 is fixed as ruled.**
   - `tests/test_vendor_admission.py` adds `LEDGER_DAMAGE` (deleted, `{not json`), a `ledger` argument to `take_road`,
     `ledger_problems`, and `Refusals.test_va_an_unreadable_take_ledger_refuses_before_the_reader`. Each of the 4 cases
     (codex and gemini, deleted and unparseable) runs with a registered reader and `AGREED` otherwise. It must raise
     `VendorAdmissionRefused` naming "cross-check", with `Evidence.load` never entered.
   - The new `WITNESSES` entry flips `ledger_cross_check`'s `return None` to `{'status': 'agreed', 'why': None}`.
     `test_va_witness_an_unreadable_ledger_read_as_agreed_goes_red` asserts all 8 problems: every case both reaches
     `Evidence.load` and is not refused.
   - The witness bites. In-memory reproduction, no tracked file edited:
     - `ledger_problems(run)` on the real code gives `[]`.
     - Through the module's `mutant()`, single-quoted and double-quoted agreed-shape mutants each give 8 problems,
       for example `take codex ledger deleted: reached Evidence.load`.
     - A narrower mutant also goes red. It splits the handler so that only `ValueError` reads as agreed. It gives 4
       problems, from the unparseable cases of both vendors.
   - `run.py` is byte-identical between b0cf963b and 05de70e5. The red commit c0f2d06d carried the mutant in run.py,
     and 6841969a restored it.
   - So the new VA-ledger cases pass against b0cf963b's code, as expected. That code was already fail-closed (round 1
     said so). Their red evidence is the mutant, which is what ruling 1 asked for.
2. **Adapter docstrings.**
   - In `codex_adapter.py` and `gemini_adapter.py`, only lines 13-14 of the module docstring changed in each, and the
     line count is unchanged. They now say freeze.py refuses a design row of that harness (arm O, arm G) while
     SHAPES_SOURCE is not "recorded", naming `freeze.unrecorded_shapes_problem`.
   - The new FS-docs test binds that. Against b0cf963b's adapters in a scratch worktree (since removed, never
     committed), it fails twice (failures=2), once per adapter.
   - On this tree, `native_reader_registration.READER_SOURCES` (9 entries) and `CODEX_SOURCES` (5) contain no adapter
     file.
3. **No weakening.**
   - `git diff b0cf963b..05de70e5` is empty for graders/, check_take.py, run.py and every READER_SOURCES or
     CODEX_SOURCES file.
   - No existing assertion or witness changed. The generic witness loop still covers the three earlier entries on
     their roads.
   - The COPIED.d edits only extend reason strings: T1's VA-ledger, T3's FS-docs, the departures for the two adapters,
     and w11a/w11b's docstring note.

## Round 1 findings

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | MINOR | `ledger_cross_check`'s unreadable-ledger fallback had no case and no witness | FIXED |

## Tests and gates run on 05de70e5

All runs used `env -u CLAUDE_CODE_MESSAGING_TOKEN python3.12 -B`, from evals/gap-study-4, on named modules only.

**Named modules (all OK):**
- test_vendor_admission: 10
- test_vendor_admission_regrade: 3
- test_freeze_shapes: 6
- test_harness_bookkeeping: 21
- test_walk_grade_seam: 3

The counts are top-level methods. Round 1's 11 and 8 appear to count subtests.

**Gates (all rc=0):**
- copy_manifest --check
- build_draft --check
- lint_language
- freeze --check

**Not run here:** test_walk_runner whole, test_round4, the generated shards, and the athena battery (glitch-b5's).

## NITs

- The generic `test_va_witness_each_guard_site_removed_goes_red` also iterates the new entry. It has `roads=()`, so for
  that entry the loop only checks that the mutation site exists. That is harmless; the dedicated test does the biting.
- The VA-ledger cases cannot be red against pre-range code, because the code was already correct. The lane's red
  commit correctly used the mutant instead.
