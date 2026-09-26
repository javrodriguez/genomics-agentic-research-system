---
date: 2026-09-26
status: standing
kind: decision
touches:
  - scripts/session_turns.py
  - tests/test_session_turns.py
  - tests/fixtures/pilot/session_real_types.jsonl
  - tests/pilot_red_on_fault.py
  - docs/pilot/README.md
  - docs/implementation/row_13_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - session_turns refuses every real Claude Code session with `unclassifiable record line <n>`
  - a transcript record of type attachment, system, queue-operation, ai-title or another non-message type exits 2
  - the M4 cross-check cannot be run on a real session
---
# Row 13 follow-up 0150: session_turns grades a real transcript's harness records

Follow-up to [0140](0140-row-13-pilot-instruments.md) (row 13 step A, ruling L7), whose bytes are
unchanged. Every ruling here is **the lane's**, made under the owner's standing delegation of
23 September 2026 and ruled by the lane's coordinator on 26 September 2026; no sentence in this
record is the owner's.

## Context

`scripts/session_turns.py` (row 13 step A, 0140, ruling L7 (a)) accepted only records whose `type`
is `user` or `assistant` and refused anything else with exit 2, `unclassifiable record line <n>`.
The lane's runbook review found, and confirmed on real transcripts, that a real Claude Code session
transcript carries many other record types, so the M4 cross-check (human turns against logged
human spans) refused every real session. Step A's fixtures held only `user` and `assistant`
records, so no test could see it.

The evidence is a sanitized inventory of 40 real local transcripts, kept outside the repository.
It records type names, record counts, file counts and which keys each type carries, and no
content. 22 694 records, none unparseable:

| Type | Records | Files | Keys present (of those inventoried) |
|---|---|---|---|
| `assistant` | 6 442 | 40 | `isSidechain`, `message`, `parentUuid`, `timestamp`, `uuid` |
| `attachment` | 4 708 | 40 | `isSidechain`, `parentUuid`, `timestamp`, `uuid` |
| `user` | 3 715 | 40 | `isSidechain`, `message`, `parentUuid`, `timestamp`, `uuid`; `isMeta` on 568, `isCompactSummary` on 1 |
| `queue-operation` | 2 716 | 40 | `timestamp` |
| `atis-latch` | 1 269 | 40 | none |
| `last-prompt` | 1 263 | 40 | none |
| `ai-title` | 738 | 16 | none |
| `bridge-session` | 570 | 4 | none |
| `custom-title` | 406 | 1 | none |
| `agent-name` | 405 | 1 | none |
| `mode` | 284 | 1 | none |
| `file-history-snapshot` | 59 | 16 | none |
| `file-history-delta` | 57 | 12 | `timestamp` |
| `cost-state` | 37 | 37 | none |
| `system` | 25 | 5 | `isSidechain`, `parentUuid`, `timestamp`, `uuid`; `isMeta` on 4 |

Only some non-message types carry a `timestamp`, and only `user`, `assistant`, `attachment` and
`system` carry `isSidechain`.

## Decision

**Ruling 0150 (the lane's).**

1. Only a `user` record can be a human turn, and only an `assistant` record can be agent activity.
   Their classification is unchanged: L2, L6, L7's flag handling, tool results, meta, the window,
   the attention intervals and the printed line.
2. A record whose `type` is any other non-empty string is a **harness record**. It is graded
   (counted in `graded <n> of <n> records`). It is never a human turn, never the predecessor that
   starts an outside turn's attention interval, never agent activity and never part of the
   session window. Its content, flags and timestamp are not examined: it needs no timestamp, and
   an unparseable one does not refuse it.
3. These are still unclassifiable (exit 2, with today's codes): a line that is not a JSON object;
   a missing, null, empty or non-string `type`; and every `user`/`assistant` failure that is
   unclassifiable today.
4. The printed line keeps today's shape byte for byte, with no new field. Its consumers,
   `scripts/unit_economics.py`'s quantities reader and the bring-home keep-list in
   `gars/_system/tools/closed_output.py`, do not change.

**The lane's rulings on the producer's first pass** (26 September 2026, under the same
delegation), which answered the four questions the producer raised before implementing:

- **R1: a named expectation change.** Three existing cases in `tests/test_session_turns.py`
  asserted that a non-empty string type other than `user`/`assistant` exits 2. They now assert the
  new rule: the record is graded as harness and every other number is unchanged. The three cases:
  - `test_unclassifiable_records_exit_2`: `{'type': 'summary', 'timestamp': …}` was
    `unclassifiable record line 2`. It is now graded, and the line is `graded 3 of 3 records` with
    every other number 0.
  - `test_unknown_type_exits_2_whatever_its_flags`: `"type":"banana"` (the round-3 reviewer's
    far-future record) and `"type":"system"`, each with each of the three flags. Each exited 2.
    Each is now graded and yields the fixture's line with `graded 15 of 15`, and so moves no
    minute and not `outside window`.

  Why: `system` is a real type (25 records in 5 files), and ruling 0150 makes every such type
  harness. R1 supersedes L7 (a) **for non-empty string types only**. The missing and null cases
  in the same method keep asserting exit 2 with today's code, and so do non-object lines. L7's
  other parts stand. The method keeps its name so that 0140's and the report's references to it
  still resolve, and its comment states the narrowing. This is the only change to an existing
  assertion.
- **R2.** The red-on-fault entry "an unknown type classified by its flags" is retired, because
  its guard is the one this ruling removes. It is replaced by "a missing type accepted
  (non-message type)" and "an unknown type skipped instead of graded (non-message type)".
- **R3.** The new fault names carry the qualifier " (non-message type)". The existing faults "a
  harness record counted as a human turn" and "a harness record starting an attention interval"
  (the flag-harness records of L2/L6) keep their names and meaning.
- **R4.** Harness records are counted in `graded <n> of <n> records` and nowhere else: not in
  `outside window` and not in any minutes. So **graded = message records inside the window +
  `outside window` + harness records**. The script's docstring and `docs/pilot/README.md` state
  this invariant.

In the code, `classify` returns `"harness_type"` for such a record. That name keeps it distinct
from L2/L6's flag-harness class `"harness"`. `count` adds the record to `graded` and skips it
everywhere else.

**Producer and review.** A headless Claude Code context (Claude Opus 5.5) produced this change.
A separate fresh Claude Opus 5.5 context reviews it from a blind kit. Both are the same model
family, so the review's independence rests on the fresh context and the blind kit alone
(0009, 0013, 0014).

**A repair to the driver found while running it.** In `tests/pilot_red_on_fault.py`, the anchor
of "a malformed quantity line ignored", `raise Refused("quantity_malformed")`, appears twice in
`scripts/unit_economics.py` since step B added a second raise for an off-shape session line. The
driver therefore aborted with `anchor … found 2 times` before reaching its summary. The anchor now
includes its `if QUANTITY_PREFIX.match(line):` line, which is the occurrence the fault targeted
when it was written. The fault itself is unchanged, and `scripts/unit_economics.py` is untouched.

## What this does not close

- **A forgotten span with no human turn in it.** `outside minutes` is still a lower bound (L1).
- **The harness format can change again.** A new record type is harness by default, and that is
  safe for bookkeeping records. **Residual:** a new *message* type that carries human input
  (anything other than `user`) would be graded as harness and missed as a human turn, with no
  refusal to flag it. Only a fresh inventory of real transcripts would show it.
- **The inventory is keys and counts, not content.** Nothing here checks that no current
  non-message type carries typed human input. That conclusion rests on the type names and on
  which records carry `message` (only `user` and `assistant` do).
- **No real session has been run through the cross-check.** The fixture is synthetic and built
  from the inventory's type and key lists. Row 13's exit remains NOT met.
- **Not run by this producer:** the whole suite (`tests/run_tests.py`), which the lane runs
  elsewhere; execution on Python 3.6, 3.7 and 3.11.

## Test

- `tests/test_session_turns.py::test_real_record_types_graded_as_harness` covers test (a).
  `tests/fixtures/pilot/session_real_types.jsonl` holds one or more records of each of the 15
  inventory types, each type with only the keys the inventory lists for it, interleaved with the
  step A fixture. Harness records sit inside and outside human spans, before the window, in the
  far future, and just before the 10:12:30 outside turn. Stripped to `user`/`assistant` it equals
  `session.jsonl` byte for byte. Both files give the same value for all seven non-`graded`
  numbers, and each `graded` count equals its own file's record count (34 and 14).
- `test_harness_type_never_timed` covers test (b). It uses seven harness records, with far-future,
  pre-window, unparseable, numeric and absent timestamps, non-boolean flags, and a `message` that
  looks human. Each is inserted at four positions, including just before the outside turn, and
  then all are inserted at once. Every run gives the fixture's line with only `graded` changed.
  The seven records alone give zero turns, zero minutes and `outside window: 0`.
- `test_missing_or_non_string_type_exits_2` covers test (c): a missing, null, empty, integer,
  boolean, list or object `type`, and non-object lines, each give `refused: unclassifiable record
  line 2`.
- Tests (a) and (b) are red against `67c49e4`'s script with exit 2
  (`refused: unclassifiable record line 1`) and green after the change.
- Red-on-fault (`tests/pilot_red_on_fault.py`) adds four faults, each RED: "a harness record
  counted as a human turn (non-message type)", "a harness record starting an attention interval
  (non-message type)", "an unknown type skipped instead of graded (non-message type)" and "a
  missing type accepted (non-message type)". The driver reports `red-on-fault: 35/35 RED`.

## Status

Standing. Implemented on the branch `build/gars-row-13-0150` and tested on fixtures. The fresh-
context review has not happened in this record, and nothing here is approved or merged.

## Date

2026-09-26
