VERDICT: CHANGES

# Review, round 1: lane vendor-admission, 22af84a2..bea6e501 (T1, T2, T3)

Reviewer: a fresh, independent cloud reviewer, briefed by glitch-b5. Written Fri 16 Oct 2026, 21:48 EDT.
Head reviewed: bea6e501 on lane/vendor-admission (unshallowed). T0 is not in this range. It waits for Javier.

## Findings

1. **MINOR: a new fail-closed default has no witness. If an absent or unreadable take ledger read as "agreed", nothing would go red.**
   - Where: `evals/gap-study-4/run.py:85-92` (`ledger_cross_check`), called by `grade_committed` at `run.py:279`.
   - Scenario: the take road takes its cross-check from `ledger_cross_check(path)`. When `driver-ledger.json` is missing or is not JSON, the function returns `None`, and admission refuses. That is correct today. But no test drives that branch. Every take-road case in `tests/test_vendor_admission.py` (`cases()`, lines 66-80) has a readable ledger and only varies its `cross_check_status` key. So if the `except` branch were changed to return the agreed shape, all of `Refusals`, `Controls` and `Witnesses` would stay green. Then a codex or gemini take with an unreadable ledger would reach `Evidence.load` and its grader. That is the threat model's own probe, "a missing record ... reads as agreed". The brief also says "every new check has a mutant that goes red".
   - Repro (in memory only; no tracked file was edited):
     - Build the mutant with the module's own `mutant()` helper, replacing `    except (OSError, ValueError):\n        return None\n` with `    except (OSError, ValueError):\n        return {'status': 'agreed', 'why': None}\n`.
     - Run every `Refusals` and `Controls` method with the module's `run` bound to the mutant. The tests have to be called directly, because `unittest`'s runner re-runs `setUpModule` and rebinds `run`. Result: all pass, so the mutant SURVIVED.
     - Then run `take_road(mutant, h, {h: stand_in_reader}, AGREED)` with the moved ledger overwritten by `{not json` (for h in codex and gemini).
     - Real code: `VendorAdmissionRefused ... the native cross-check is None`, and `Evidence.load` is not reached.
     - Mutant: `Evidence.load reached`, graded `{'label': 'synthetic', ...}`, for both vendors.
   - Fold: add a take-road case with the ledger deleted and another with it unparseable, both refusing with "cross-check" before `Evidence.load`. Add a witness in `WITNESSES` that flips that `return None` and goes red. Commit them red-first, against a mutant.

No MAJOR was found. I probed each MAJOR item in the threat model, as follows:
- Every caller of `Evidence.load` and `grade_walk_folder` outside tests has been traced.
  - `grade_committed` admits before the load.
  - `grade_walk` admits after the pending check and before the load, whichever `grade` stands in. That covers `walk_runner.py:236,253` and the L6 recheck at `run.py:402`, where `readers=None` means the production registry. There a refusal is a `ValueError`, so it is reported as "cannot be regraded": fail-closed.
  - `regrade_doc` admits its own re-derived `cross` with the registry it holds (`walk_regrade.py:157`), and never the ledger's.
  - `native_reader_registration.py:403` calls `grade_walk` only on a pending walk, which returns before admission, so there is no recursion into `production_readers`.
  - `drive.py:2426` (`_operator_check`) is outside this lane's files and outside grading.
- `RegistrationRefused` is re-raised as a refusal and never swallowed. An empty registry refuses. `{harness: None}` refuses. The cross-check must be exactly `{"status": "agreed", "why": None}`.
- `git diff 22af84a2..bea6e501` is empty for `graders/`, `check_take.py`, `drive.py`, `transcript_view.py`, `vendor_provenance.py`, `native_snapshot.py` and `native_reader_registration.py`.
- claude-code's road is unchanged: `vendor_admission` returns at once for any other harness.
- `TABLE` is unchanged. `VENDOR_CANDIDATES` is read by nothing outside tests. `harness_bookkeeping --check` still reports only claude-code.
- The freeze has one write road, `freeze.main`. `freeze_rehearsal` runs it as a subprocess, and `check_results` and `prereg` only read from it. The new check sits before `prepare` and before any write, in both preview and `--write`. A claude-code-only draft passes (tested). A row of a vendor harness whose adapter is "documented" refuses and names its arm.
- Every COPIED.d and checks.d claim was read against its file and matches. `copy_manifest --check` is clean.

## Tasks against their Done lines

| Task | Done line | Status |
|---|---|---|
| T1 | No road reaches `Evidence.load` for a vendor take without a registered reader and an agreed cross-check, even with vendor TABLE entries present. | MET in code. The test coverage gap is finding 1, which is MINOR. |
| T2 | Candidates exist, grounded and tested; TABLE is unchanged; production `Evidence.load` still refuses vendor takes. | MET. Cited lines spot-checked: codex_adapter.py:41; box/run_take.py:68, 93, 152, 160-165; native_snapshot.py:9-20, 84. |
| T3 | The freeze cannot pass an arm whose adapter was never re-tested on a recorded stream. | MET |

## Tests and gates run on bea6e501

All runs used `env -u CLAUDE_CODE_MESSAGING_TOKEN python3.12 -B`, from evals/gap-study-4, on named modules only.

**Named modules (all OK):**
- test_vendor_admission: 11 tests
- test_vendor_admission_regrade: 3 tests
- test_harness_bookkeeping: 21 tests
- test_freeze_shapes: 5 tests
- test_walk_grade_seam: 8 tests
- test_pending_walk: 23 tests
- test_pending_codex_walk: 3 tests

**Gates (all rc=0):**
- copy_manifest --check
- build_draft --check
- lint_language evals/gap-study-4/
- walk_regrade --check
- freeze --check
- harness_bookkeeping --check

**Red-first proof against 22af84a2's code.** I made a scratch `git archive` copy, never committed, and put bea6e501's test files into it.
- test_vendor_admission: failures=5, errors=4 (no `VendorAdmissionRefused`, `grade_walk() got an unexpected keyword argument 'readers'`, and the witness sites are absent).
- test_vendor_admission_regrade: failures=3 (the extra-key and unregistered cases were graded instead of refused).
- test_freeze_shapes: failures=4, errors=1 (no `unrecorded_shapes_problem`, and the O/G drafts were not refused).
- test_harness_bookkeeping: the VendorCandidates tests raise AttributeError on `VENDOR_CANDIDATES`.
- test_walk_grade_seam: E-vendor fails on the `readers=` keyword.
- Some pre-existing TheTable tests and `test_fs_check_mode_is_unchanged` also error in the scratch copy. That is because it has no git history (`e2979b31`). Those errors are environmental and are not counted here.

**Extra in-memory mutants:**
- Replacing the production registry with an all-registered one: KILLED (by `test_va_production_readers_on_this_tree_refuse` and `test_va_a_refusing_registry_refuses_the_take`).
- Dropping `type(cross) is not dict`: survives. It is equivalent apart from dict subclasses, so it is not reported.
- An unreadable ledger reading as agreed: SURVIVED (finding 1).

**Not run:** test_walk_runner as a whole, test_round4, the generated shards and the athena battery. The battery is glitch-b5's to run.

## NITs

- `run.VENDOR_HARNESSES` and `AGREED_CROSS_CHECK` copy `drive.VENDOR_HARNESSES` and drive's agreed shape (`run.py:58-59`), and no test pins them equal. If a third vendor were added to drive, it would pass admission unguarded. It would still be stopped later by `UnknownHarness` while TABLE lacks it.
- T1's Done line says "no road reaches Evidence.load". But admission keys on the row's harness (`row["agent"]`), while `require_evidence_identity` runs after the load. So a row with no harness or a claude-code harness, carrying vendor evidence, does reach `Evidence.load`. Admission does not stop it; the identity check after the load refuses it before any grader. That is safe for grading, but the wording of the claim is stronger than the code.
- `codex_adapter.py:13-14` and `gemini_adapter.py` still say the freeze-side refusal is "owed to a later slice" (the executor flagged this too). Their text is now stale.
- glitch-b5 should note (the executor's item 1): the committed draft has O and G rows, so the freeze step of `freeze_rehearsal.py` will now refuse until recorded shapes land. This is ruling Q-3 working as written.
