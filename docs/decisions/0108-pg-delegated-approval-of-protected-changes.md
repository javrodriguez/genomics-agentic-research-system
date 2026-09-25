---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/tests/test_nonpublic_read_block.py
  - gars/tests/test_protected_paths.py
symptoms:
  - lane pg changes the guard hook, its settings and tests under the protected prefix gars/ with no owner approval record
---
# Lane pg: approval of its protected changes, under the owner's delegation

Addendum to [0107](0107-pg-nonpublic-projects-closed-to-reads.md), which stays byte-identical.
Every path this record touches is under a protected prefix (§9.3, R-094), so its change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0132](0132-doi-lane-delegated-approval-of-protected-changes.md).

## Context

Lane pg is item 2 of the rc/pg lane (decisions 0105-0109; item 1 is [0105](0105-rc-restore-log-reader-reads-the-table.md)).
It closes a non-public project to a guarded agent session (§6.1, §21 Q4; R-061, R-074), with one opening: a stage 00 registration of data a human has declared public.
It was built on its own branch from public main `0754ec6` by a headless Claude Code producer (Opus 5.5) in an isolated clone, and reviewed by fresh Claude Code contexts (Opus 5.5) from a separate checkout with no remote; producer and reviewer are the same model, a named cost (0013, 0014).
The lane took two producer commits, `f07074a` and `808bdbe`, each under the repository's own identity.
Reviews, both structural by the lane's instruction (no reviewer enumerated spellings around the rule): round 1 APPROVE WITH CHANGES (one MAJOR, four MINOR, three NOTE), fixed or answered in round 2; round 2 APPROVE WITH CHANGES (two MINOR, five NOTE), answered in this record.
Every review of the lane is kept outside the repository.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected changes as merged, on 2026-09-25.

1. **`gars/_system/guard_hook.py`**, additions only (zero removed lines): the closed-project rule of 0107 points 1-5 (`project_is_public`, `closed_projects`, `closed_hit` and their helpers, module-level so row 13 can import them); the declaration reader `declared_sources` and the declared-registration check; the Q8 check `first_public_classification`; the `rg --pre` refusal; the edit-family refusal `closed_edit_refusal` (round 2); their call sites in `main()` and `check_bash`; a dedicated `check_write_tool` branch for `data_sources.tsv`; and exactly one new `READ_ONLY` line, `"data_sources.tsv",`, before the list's closing bracket, with row 6's `dataset.tsv` line byte-identical. `CLOSED_PROJECT_DOORS` is empty.
2. **`gars/.claude/settings.json`**: exactly the two deny entries `Edit(data_sources.tsv)` and `Write(data_sources.tsv)`, placed after row 6's `dataset.tsv` pair, nothing removed. The lane's specification requires them: "one new `READ_ONLY` line `"data_sources.tsv",` … and its matching pair `"Edit(data_sources.tsv)",` and `"Write(data_sources.tsv)",` in `gars/.claude/settings.json`, placed immediately after row 6's `dataset.tsv` pair, nothing removed, so `test_settings_equal_guard_patterns` holds" (its point 3), and its boundary allows "`gars/.claude/settings.json` (exactly the one pair)". The review brief's older line that item 2 leaves `gars/.claude/` unchanged predates that specification (review round 2, F1).
3. **`gars/tests/test_nonpublic_read_block.py`**: new, 20 tests (19 at the build, one added in round 2; 0107's Test section says 19; review round 2, F3).
4. **`gars/tests/test_protected_paths.py`**: the one named expectation change, `test_normal_project_edit_positive_control` moved to a temp root with no projects.

Outside the protected prefix, and recorded here for completeness: the `.gitignore` line `gars/data_sources.tsv`, the suite count in `README.md` and `DEVELOPMENT.md`, the index, and the lane's change report.

## The lane's rulings, as worded (review rounds 1 and 2, F7)

All are the lane's, under the owner's standing delegation of 23 Sep 2026.

- Q3: `rg --pre` is closed in this item as a named row 4 defect, shown executing first.
- Q4: a project with no `dataset.tsv` is closed; the stage 00 trace shows no read inside the project before `finalize`.
- Q5: the per-tool flag allowlist is a row 4 follow-up, named, not built here.
- Q6: widening the hook matcher is a row 4 follow-up; the unmatched tools are residual 6.
- Q7: the whole project is closed apart from `00_data/dataset.tsv` and the `STATUS` files.
- Q8: only a human, or a protected declaration, supplies a `public` class.
- Every registered tool is refused on a closed project unless it is a door; the doors list starts empty and row 13 adds each door only for a tool whose output passes its keep-list filter.
- Amendment 1: the declaration `gars/data_sources.tsv`, written only by a human, public-only, machine-local; declared registration opens `inspect`, `link` and `finalize --data-class public` on a registrable project.
- Its review-round-3 fixes: containment (a source that equals, contains or lies inside the workspace root, `projects/`, a project, `_system/`, `_references/`, `_templates/`, `.claude/` or the approval store invalidates the whole file); the exemption lifts the refusal only for hits on the target project; `inspect` only on a declared source; `link` refused on any project outside a declared registration, and `--force` refused inside one; a registrable project holds nothing beyond `create`'s stamp and raw entries (`CREATE_STAMP`, drift-tested); the one `READ_ONLY` line before the closing bracket; the dedicated Write message; a dangling or outward raw entry counts as undeclared.
- The STATUS exemption (review round 2, F4): the lane keeps the specification's binding, every file named exactly `STATUS`, as ruled before the build (the lifecycle files `write_status` writes hold only a state word). Residual 18, that a `STATUS` elsewhere in a closed project is readable whatever it holds, stays NOT met; binding the exemption to the sub-stage and custom-analysis directories is a row 13 follow-up.

## What this does not close

- Every residual 0107 names (1-17, and 18 from its round 2 addendum), each NOT met.
- The README evidence and public claims are unchanged; no measured §17 row changes.
- Spelling coverage rests on the builder's red-first grid: no independent reviewer attacked the token spellings, and a producer and reviewer on one model share blind spots.

## Test

Glitch verified the merge candidate `bf5b0d9` (lane head `808bdbe` merged onto public main `a779084`, then the count commit) independently, each evidence run alone on its machine, with a process snapshot of every account at its start and end.

- The owner's workstation (macOS, Python 3.8.2), with Docker answering and row 5's scratch folder set as CI sets it: `Ran 701 tests`, `OK (skipped=13)`.
- The build node's owner account (Linux, Python 3.13.5), from a fresh clone of a bundle: `Ran 701 tests`, `OK (skipped=80)` without containers, and `OK (skipped=107)` with `TMPDIR` also unset; contracts, counts, decision links and the DoD check clean.
- Red at parent: the new module on `a779084`'s tree gives `FAILED (failures=480, errors=25, skipped=1)` over 20 tests.
- An independent mutation sample on the build node, each plant restored from a byte backup and compared by SHA-256: the Read-branch call removed (18 failures), the `check_bash` call removed (454), an unreadable or missing `dataset.tsv` read as public (137); green again after each restore. The producer's own table covers P1-P31 and the round 2 plants.
- A stand-in for GARS's pre-push gate (0107's R-042 items 2, 3 and 9; review round 1, F5): the gate's own command, `python3 tests/run_tests.py` at the checkout root, in a scratch working copy on the owner's workstation holding a copy of that machine's live projects (36 projects, none with a `dataset.tsv`, so all 36 closed), gives `Ran 701 tests`, `OK (skipped=75)`; the pre-lane `test_protected_paths.py` in the same copy fails `test_normal_project_edit_positive_control`, so the copy exercises the change. The live projects never left that machine, and the copy was deleted after the run. It is a stand-in: GARS's own pre-push hook is not armed on that machine.
- The outgoing range `a779084..bf5b0d9` has no gitleaks finding under either ruleset, no canary and no private address or path.

## Status

Standing. Approval of lane pg's protected changes only.

## Date

2026-09-25
