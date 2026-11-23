# The vendor checker road (live harness integration slice)

Parent: `9b37e185`. Writer: Claude Code harness lane, 14 Oct 2026 01:22 EDT, under glitch-06's conditional ruling on the `take_checker` road.

## Registered text, quoted first (the ruling's condition)

`/Users/javrodher/glitch/plans/gap-study-round-4/D8-non-claude-arms.md`, line 172, the per-harness table's "Transcript" row:

> | Transcript | host-captured stream-json, cross-checked with the session file | host-captured `--json` stream, cross-checked with the rollout file | host-captured stream-json, cross-checked with the session file under `GEMINI_CLI_HOME` |

The three columns are Claude Code (arm A), Codex CLI (arm O) and Gemini CLI (arm G).

`/Users/javrodher/glitch/plans/gap-study-round-4.md`:
- Line 567: "The graded record is the stream-json the host captures (727-729), cross-checked against the session file copied out of the config folder."
- Line 199: "each operator-side reason the copied checker keeps (operator lines, checkout binding, outcome binding, readers disagreeing and the rest of round 3's `rehearsal_reasons`) … its own row in `routing.json`: a rehearsal before the first turn, `harness-error` after it".
- CP6 (lines 868-890) says walks are "graded but never counted" and that only what was walked is pre-registered. It says nothing about grading a vendor take without its native cross-check.

My reading: the registered graded record is the host-captured stream cross-checked with the native record, for every arm. A vendor take whose native cross-check cannot run yet (no reviewed reader) is therefore not gradable under the registered text. The ruling's condition holds, so I took the second shape.

## Change: the second shape

- `routing.json` has no pending row. Adding one would be a new rule, so routing is not touched.
- The driver stops such a take with a typed `NativeCrossCheckPending`, a subclass of `DriveRefused`. It is raised after cleanup, postflight, the ledger (with `cross_check_status: pending`) and the scan, and before the checker.
- Batch records the take `failed` after its drive started. That means a ruling is needed, and the take is never graded, never re-run, never readers-disagree, and never a harness-error for the nightly count; it is counted apart, under `failed_after_drive_started`.
- A refused native cross-check stays readers-disagree. Its problem is in `cross_check`, and the checker adds the reason.
- Review nit (batch-5): `take_checker` now treats `cross_check is None` explicitly as a pending native cross-check and raises `NativeCrossCheckPending`. A pending check is never read as agreement through falsiness. An empty list `[]` still means agreement, which is what Claude takes produce.
- The first shape (publish a vendor transcript from the bound envelope and grade from it) is not built. It becomes the right road once a reviewed native reader can run the cross-check, or if the orchestrator rules that grading may precede it.

## Verification (each run behind a fresh light gate)

- **Red:** `tests/test_vendor_checker_road.py`, the first three tests:
  - 2 failures: a pending Gemini and a pending Codex take each raised nothing.
  - 1 failure through batch: the take was `blocked`, not `failed`.
  - This red came after the test fakes were set up. The vendors' PENDING billing names were patched empty, the money gate was patched out as W7C's concern, and the Codex row was pre-registered, all test-only.
- **Green:** `test_vendor_checker_road` 4/4 (the checker None test was added with its change). Neighbours: `test_vendor_take_records` 4/4, with its pending expectation updated to the typed stop. Also `test_native_history_record` 3, `test_native_snapshot` 9, `test_executed_turn_refusal` 10, `test_drive_loop` 27, `test_batch` 118.
- **Mutants:**
  - Three killed by assertion: no pending stop, the pending stop untyped, and the checker reading None as agreement.
  - "Refused also stopped as pending" survives as equivalent on the tested road. A refused status there comes from a snapshot that was not retained, and that already stops the take earlier.

## Not run, owed

- The merged-head athena suite.
- Independent review.
- A Javier or orchestrator ruling if grading a vendor stream before its native cross-check is wanted. That would be the first shape, and it needs a rule the registered text does not hold.

## Addendum, 14 Oct 2026 01:37 EDT: the pending stop is departure D-INT-1

The batch-6 review corrected this report. The typed stop (`NativeCrossCheckPending`) is a named departure, not a direct consequence of the registered text.

The registered text says what is graded: the captured stream cross-checked with the native record. It does not say what happens to a take whose cross-check cannot run yet. Stopping such a take for a ruling is the orchestrator's choice.

**D-INT-1:** ruled by glitch-06, 14 Oct 2026, under the standing delegation. It sits next to D-3a-1 in `live-harness-next-integration-addendum-2026-10-14.md`.

Consequence, stated plainly: until a native reader is registered for a vendor (`native_reader_registration`, through a committed acceptance record), every take of that vendor stops the run for a ruling. **The vendor arms cannot run unattended.**
