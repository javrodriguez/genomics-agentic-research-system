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

## Addendum, 2026-09-26: review round 2 rulings

2026-09-26 — the lane's rulings, under the owner's standing delegation, answering the first fresh-context review of this record (APPROVE WITH CHANGES). Every sentence here is the lane's; none is the owner's. The bytes above are unchanged.

- **F-1 (a name the list cannot carry).** A project directory name holding any control character (a code point below 0x20, or 0x7f) is never written verbatim anywhere. The render prints `## (unprintable project name) — closed (unclassified)` for it and nothing else; the index writes one row `| (unprintable project name) | closed (unclassified) | — | — | — | — | — |`; `--closed-list` never emits such a name. `build_projects_index.sh` decides those rows itself, before and without the list, by testing the name against the same 32 characters, and takes the name by parameter expansion rather than `$(basename)`, which drops a trailing newline. So no name can split a list record or rewrite another project's row. This holds for a public-classed project too.
- **F-2 (fail-closed branches).** Tested: a workspace whose `guard_hook.closed_projects` raises renders every heading, every `--project` output and every index row as `closed (unclassified)`; a `--closed-list` that exits non-zero, even after printing a line, closes every index row as `unclassified`.
- **F-3 (`--project` by its entry).** `--project` names and judges a project by its unresolved entry: the path's own name, and the guard's label when that entry sits in a workspace's `projects/`. A symlinked entry's heading therefore equals the full render's line for it.
- **F-4.** The change report's section "Review round 1 fixes — follow-up 0151, exit-line fix" keeps its heading; a dated correction line appended to the report says its source was the lane's gate, not a review round.
- **F-5 (a STATUS the writer could not have produced).** Adopted, fail closed: a closed project's sub-stage line prints its STATUS's first line only when that line is one `wrapperlib`'s writer can produce — a word of `STATUS_STATES`, `:<reason>` only after `FAILED` with a reason from `FAILURE_REASONS` or `EXIT_<n>`, then optionally the writer's job id and its UTC timestamp — and prints `unrecognized` otherwise. A bare state word (no timestamp) is accepted, as fixtures and older files write it. The state words are imported from `wrapperlib`, not copied. The public render is unchanged.
- **F-6.** `gars/CLAUDE.md`'s "State" section gains one sentence: a closed project shows only its name, class label and sub-stage states (0151). Nothing else in that file changes. This record's `touches` list, above, is not edited; `gars/CLAUDE.md` is named here instead.

Tests: `test_b_project_is_named_and_judged_by_its_entry`, `test_d_render_index_and_guard_agree_on_the_closed_set` (now with tab, newline, `nl<LF>open1` and trailing-newline names, and `open1`'s row compared before and after), `test_g_a_guard_that_cannot_judge_closes_everything`, `test_h_a_failing_closed_list_closes_every_row` and `test_i_closed_status_prints_only_a_writer_value`, in `gars/tests/test_session_state_closed.py` (11 tests).

## Addendum, 2026-09-26: review round 3 rulings

2026-09-26 — the lane's rulings, under the owner's standing delegation, answering the second fresh-context review of this record (APPROVE WITH CHANGES: N-1 and N-2 MINOR, N-3 and N-4 NOTE). Every sentence here is the lane's; none is the owner's. The bytes above are unchanged.

- **N-1 (the label lookup).** The render and `--project` never index the closed labels with a name the guard did not report: the label is `closed.get(name, "unclassified")`. A public-classed project whose name holds a control character therefore renders `## (unprintable project name) — closed (unclassified)` alone, and every other project renders as before; at the round-2 code it raised `KeyError` and the whole render was lost.
- **N-2 (correction).** The round-2 addendum above says the unprintable-name handling "holds for a public-classed project too". That was not tested then, and the render crashed on such a name. Tested now: `test_d_render_index_and_guard_agree_on_the_closed_set` adds a public-classed copy of `open1` named `pub<TAB>name` beside the closed `pilot`. It asserts that the full render and `--project` print the unprintable heading for it, that `open1`'s section is byte-identical to its section before the name existed, that `fresh`, `open1`, `pilot` and `sealed` all render, and that the index writes one more unprintable row.
- **N-3 (citations).** The reviews are cited by their review-kit folder names, not by a repository path, because they stay outside the repository. This round's producer was not given those folder names and may not read the review folders. So the report cites each review by its round and the commit it reviewed: round 1 of `352e49f`, round 2 of `a2429b1`. The lane adds the folder names.
- **N-4 (STATUS values).** A closed STATUS line prints only in a shape `wrapperlib.write_status` writes: a state word, or `FAILED:<reason>`, optionally followed by the writer's UTC timestamp. The one exception is `SUBMITTED` or `RUNNING`: they may carry `<job id> <timestamp>`. A job id after any other state, or a job id without a timestamp, prints `unrecognized`. The state words and the named reasons are imported from `wrapperlib`. `EXIT_<n>` and the two job-id states stay literals, because `write_status` holds them inline and exposes no name for them.

Tests: `test_d_render_index_and_guard_agree_on_the_closed_set` and `test_i_closed_status_prints_only_a_writer_value` (now with `COMPLETE 4242 <timestamp>`, `FAILED:EXIT_1 4242 <timestamp>` and `SUBMITTED 4242`, all `unrecognized`, and `RUNNING 4242 <timestamp>` and `FAILED:EXIT_1 <timestamp>`, both printed), in `gars/tests/test_session_state_closed.py` (11 tests).
