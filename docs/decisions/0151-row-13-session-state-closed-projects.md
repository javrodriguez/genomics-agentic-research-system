---
date: 2026-09-26
status: standing
kind: decision
touches:
  - gars/_system/project_state.py
  - gars/_system/build_projects_index.sh
  - gars/tests/test_session_state_closed.py
  - docs/implementation/row_13_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - the session-start render prints a closed project's sample count, unmade config keys, artifact types or HISTORY headers
  - projects/_index.md shows a closed project's design, samplesheet or furthest sub-stage
  - a planted marker in a closed project's HISTORY.md or OUTPUTS.tsv appears in the agent's context at session start
  - the index and the render disagree about which projects are closed
---
# Row 13 follow-up 0151: the session-start render and the index name a closed project only

Follow-up to [0107](0107-pg-nonpublic-projects-closed-to-reads.md) (closed projects) and
[0033](0033-a-session-boots-knowing-the-state.md) (the SessionStart render), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September
2026 and ruled by the lane's coordinator on 26 September 2026; no sentence in this record is the
owner's. 0152 is reserved for the lane's delegated approval of these protected changes; this
record does not write it.

## Context

The SessionStart hook, `gars/_system/session_state.sh` (0033), rebuilds `projects/_index.md`
with `_system/build_projects_index.sh` and prints `_system/project_state.py`'s render of every
project into the agent session's context. Neither was closed-aware (0107). For a closed
(non-public) project the render showed its sample count (`design filled (N samples)`), the names
of its unfilled config keys, its artifact types (the `OUTPUTS.tsv` type column), its created date
and its last HISTORY.md entry headers; the index showed its design and samplesheet state and its
furthest sub-stage. A hosted model's context therefore received facts about a closed project's
data that 0107 exists to keep out, and the index is a file the agent can read. The lane's runbook
review found it. On row 13's fixture the render printed the closed project's planted CODE marker
as an artifact type, and a HISTORY header carrying a marker verbatim.

## Decision

**Ruling 0151 (the lane's).**

1. A project is closed exactly as 0107 decides it: `project_state.py` imports `closed_projects`
   and `project_is_public` from `_system/guard_hook.py` (no copy). A project the guard cannot
   judge is closed.
2. A closed project renders as exactly one heading line `## <name> — closed (<label>)`, the label
   being the guard's (`deidentified_under_agreement`, `identifiable` or `unclassified`), then one
   line `- <sub-stage directory name>: <first line of its STATUS, or NOT_STARTED>` per stage 02
   sub-stage, and nothing else. `--project` on a closed project prints the same.
3. A closed project's index row is `| <name> | closed (<label>) | — | — | — | — | — |`. The index
   stays bash; it reads the closed set from `project_state.py --closed-list`, which prints one
   `<name><TAB><label>` line per closed project from the same function (`closed_labels`) the
   render uses.
4. A public project's render and index row, and everything when no closed project exists, are
   byte-identical to `1a009a4`'s.
5. Nothing else changes: not the hook's order, not the guard, not STATUS semantics.

**How the producer applied rule 1 (fail closed), where the ruling does not spell it out.**

- If `guard_hook.closed_projects` raises (for example `projects/` unreadable), the render treats
  every project as closed `unclassified`. If `--closed-list` fails, the index writes every row as
  `closed (unclassified)`.
- `--project` judges the project in its own workspace (`<dir>/projects/<name>`); a project
  outside a `projects/` directory, or one that workspace's list does not name, is closed
  `unclassified` unless `project_is_public` says it is public.
- A closed project's STATUS is read only as 0107 leaves it readable: a regular file at its own
  path, never through a symlink and never a FIFO (`guard_hook._regular_text`). A STATUS that is
  anything else, or any other error while rendering a closed project, prints the heading line
  alone, never an exception's text. The ruling's line shape admits no third value, so the
  producer chose fewer lines over a line whose value was not read.
- The closed render walks `02_bioinformatics/<assay>/<sub-stage>/` directly, sorted by assay then
  sub-stage; the assay name is not printed.

**Producer and review.** A headless Claude Code context (Claude Opus 5.5) produced this change.
A separate fresh Claude Opus 5.5 context reviews it from a blind kit. Both are the same model
family, so the review's independence rests on the fresh context and the blind kit alone
(0009, 0013, 0014).

## R-042: every changed behaviour

Each test is in `gars/tests/test_session_state_closed.py`; each was run against `1a009a4`'s
`project_state.py` and `build_projects_index.sh` and failed there, then passed after.

| Changed behaviour | Test that the new code passes and `1a009a4`'s does not |
|---|---|
| a closed project's render and index row carry no marker, sample count, config key, artifact type, created date or HISTORY header | `test_a_closed_detail_never_reaches_the_session` (runs the real `session_state.sh`) |
| a closed project's render, `--project` render and index row have exactly the rule's shape | `test_b_closed_lines_are_the_rule_shape` |
| a closed project's STATUS reached through a symlink is not followed; the heading prints alone | `test_f_closed_status_read_only_as_its_own_file` |
| `--closed-list` exists; the render, the index and `guard_hook.closed_projects` agree on the closed set, including a public-classed project whose `dataset.tsv` is mode 0 (closed `unclassified`) | `test_d_render_index_and_guard_agree_on_the_closed_set` |
| a HISTORY header carrying a marker on a closed project never appears | `test_e_planted_history_header_never_appears` |

Unchanged, and guarded (green before and after): `test_c_public_render_and_row_are_byte_identical`
(`open1`'s section of the full render, its index row and its `--project` render, against
`1a009a4`'s code on the same workspace) and `test_c_no_closed_project_changes_nothing` (a
workspace with only a public project: the full render and the whole index but its `Last built`
line, byte for byte). `tests/run_tests.py`'s `ProjectStateTests` use a public fixture and are
unchanged and green.

## What this does not close

- **The transcript and anything a human types.** A human who pastes closed detail into the
  session, or reads it aloud to the agent, is not stopped by this.
- **STATUS values and sub-stage names remain visible by design**, as does a closed project's
  name and class label. A STATUS whose first line a human wrote carries whatever they wrote.
- **Other describers of the render.** `gars/CLAUDE.md`'s "State" section still describes the
  catch-up as "how far each assay got, which decisions are unmade, the last HISTORY entries"
  without saying a closed project shows only its STATUS lines. This change may not touch it; a
  later change should.
- **An index written before this change** keeps its old rows until the hook next runs.
- **Not run by this producer:** the whole suite (`tests/run_tests.py`), which the lane runs
  elsewhere; execution on Python 3.6, 3.7 and 3.11.

## Test

`python3 gars/tests/test_session_state_closed.py` prints the reserved line `EXIT session state
(fixture): closed projects name and status only` and reports `Ran 7 tests` / `OK`. Against
`1a009a4`'s two scripts it reports `FAILED (failures=5)`: tests a, b, d, e and f fail and the two
c tests pass. The faults that must make it fail: printing any of the old render's lines for a
closed project; following a symlinked STATUS; a `--closed-list` that disagrees with the guard.

## Status

Standing. Implemented on the branch `build/gars-row-13-0151` and tested on fixtures. The fresh-
context review has not happened in this record, and nothing here is approved or merged; the
lane's delegated approval, if given, is 0152.

## Date

2026-09-26

## Addendum, 2026-09-26: the exit line

2026-09-26 — the lane's ruling, under the owner's standing delegation: the lane's gate reads a module's reserved `EXIT ` line only at the start of a line, so `test_session_state_closed.py` now prints `EXIT session state (fixture): closed projects name and status only` once, from its `__main__` block after the tests have run and only when all passed (stderr flushed first), instead of inside test (a), where the verbose runner put it after `... ` on the same line; nothing else changes.
