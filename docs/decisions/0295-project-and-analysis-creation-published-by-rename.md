---
date: 2026-10-16
status: standing
kind: decision
touches:
  - gars/_system/stage00_register.py
  - gars/_system/stage03_analysis.py
  - gars/_system/project_state.py
  - gars/tests/test_r164_writer_recovery.py
symptoms:
  - a fault while stage 00 create copies the stamp or seeds _config/ leaves a half project at projects/<title>, and every later create of that title is refused with T7
  - a fault while stage 03 create publishes PLAN.md leaves an analysis folder with scripts/ and results/ but no plan, and the next create numbers past it
  - project_state lists a dot-named folder under projects/ as a closed project
---
# Project and analysis creation are published by rename

Follow-up to [0200](0200-local-job-record-and-launcher-published-by-rename.md), whose residual R2 named three writers still open: the stage 03 submissions append, stage 00's project creation, and stage 03 create's allocated folders.
Every ruling here is **the lane's** (lane gars-ms21, task 5), made under the owner's standing delegation and directed by glitch-b5's round 3 ruling of 16 October 2026; no sentence in this record is the owner's.
This record writes no approval; the landing's approval record is glitch-b5's.

## Context

1. **`stage00_register.py create`** copied the project stamp straight onto `projects/<title>` with `shutil.copytree`, then made each assay's `raw/` and seeded `_config/` in place. A fault part-way left a half project at the published name: `create` refuses an existing title (T7), so the user could not retry without deleting it by hand, and the guard and the index judged it as a project.
2. **`stage03_analysis.py create`** made `NN_<slug>/`, `scripts/` and `results/` before publishing `PLAN.md`. A fault at `PLAN.md` left the three folders with no plan; the next `create` counted the folder and numbered past it. The writer-recovery table's row for this call excused those folders as an open question (`creates`).
3. **The submissions append** (`executorlib._submit_analysis`, `.gars_submissions.jsonl`) appends a line with `open('a')`; a fault part-way leaves a torn last line, and `_analysis_entries` then fails to parse the whole history. Its fix is held, see R2.

**Reproduction.** Three new rows in `gars/tests/test_r164_writer_recovery.py` drive each writer through the table's injector (lane commit 5a945b24, red on this container, 16 October 2026):

- `stage00_register create`: the destination is the project folder, absent before every run; the steps are the rename into place and four helper faults (a stamp copy that lands one file then fails, a seeded config whose write lands half its text, a refused `copy2`, a refused `Path.mkdir`). At base all five fail: the four faults leave a half project, and the rename is never reached.
- `stage03_analysis create allocated folders`: the existing row's call and destination (`PLAN.md`), with nothing excused but the stage root `03_custom_analysis/` (a container, as `projects/` is). At base all four steps fail, each leaving `01_fixture/`, `scripts/` and `results/`.
- `executorlib._submit_analysis submissions record`: approval, venue, scheduler and the submit itself answered in-process. At base four of five fail (write, fsync, replace, first write); the refused open passes, the honest control.

A fourth test, `CreationSiblingTests.test_a_creation_sibling_is_no_project`, fails at base: `project_state` rendered `projects/.fixture-abcd1234` as `closed (unclassified)`.
The table now compares a folder destination by its listing, where it compared bytes; a file destination is compared exactly as before.

## Decision

**Ruling 0295 (the lane's).**

1. **Stage 00 create** builds the project in a sibling `projects/.<title>-XXXX` (reserved by `tempfile.mkdtemp`, then removed so `copytree` makes it with the stamp's mode), refuses if `projects/<title>` appeared meanwhile, and renames the sibling into place. Any failure removes the sibling and re-raises. A title can never start with a dot (`sanitize_title` keeps `[A-Za-z0-9_-]` and strips leading `_` and `-`), so the sibling is never a project's name.
2. **Stage 03 create** makes the analysis folder and its `scripts/` and `results/` in a sibling `03_custom_analysis/.<NN_slug>-XXXX`, which the numbering never counts (it reads only `^\d\d_` names), renames it into place, then publishes `PLAN.md` in its own folder by `workspace.atomic_open` as before; if the plan cannot be published, the folder is removed.
3. **`project_state.py`** skips a dot-named entry of `projects/`, as `build_projects_index.sh`'s glob already does, so neither render reads a creation sibling as a project.
4. On success the bytes, names and modes written are those of the old writers: a snapshot of a two-assay project and one analysis (every path, mode and SHA-256, and `create`'s JSON) is identical before and after.

In-spec choices (the lane's): `PLAN.md` stays published in its final folder rather than in the sibling, because the existing `stage03_analysis create` row binds its publication there and moving it would change that row's assertion; the folder-listing comparison in the table's runner, the only change to shared test code; a dot name for both siblings, the shape the task named, with `project_state` taught to skip it rather than an underscore name the task did not name.

Rejected alternatives: removing the folders in place without a sibling (a crash mid-way would still publish a half project under its real name); building the project anywhere outside `projects/` (not guaranteed to be on the same filesystem, so the rename could fail).

## What this does not close

- **R1** A stage 03 job is submitted before its history line is written: a fault at the line leaves a submitted job with no record, and the submission is refused with R-135. Named by the task; unchanged here.
- **R2** The submissions append is not yet changed. Its fix (the history rewritten through `workspace.atomic_open`, the existing file's mode kept, success bytes identical) is drafted in the lane and turns its row green, but it removes the code text a standing mutation in `gars/tests/test_lifecycle_faults.py` (`stage03 submission history overwritten`) anchors on. Re-pointing that anchor is an assertion change and waits on a named ruling; the equivalent mutation on the patched code (drop the previous history) turns the same witness red.
- **R3** A process killed outright (not a raised fault) while building leaves its dot sibling. The index and `project_state` skip it; the guard's closed-project scan, which this record does not change, reads it as a closed project, the conservative side.
- **R4** Stage 03: a kill between the rename and `PLAN.md`'s publication leaves the folder without a plan, as before, in a narrower window.
- **R5** Python 3.6 has no no-replace rename: a folder created at the destination by some other writer between the existence check and the rename could be replaced if it is empty. A concurrent GARS `create` publishes a non-empty folder, which the rename refuses.

## Test

`gars/tests/test_r164_writer_recovery.py` gains the rows `stage00_register create` and `stage03_analysis create allocated folders` (and the held `executorlib._submit_analysis submissions record`), each with the table's fixed postcondition: the fault surfaces, the destination keeps its prior state exactly (absent for a project), and no file or folder appears anywhere in the fixture tree. `CreationSiblingTests.test_a_creation_sibling_is_no_project` binds item 3.
They must fail when stage 00 keeps its sibling on failure (four of five steps), when stage 03 keeps its folders after a failed plan (four of four), and when `project_state` reads dot names again; the lane's mutation run at the fix commit turned each red.

## Status

Standing, except R2's writer, which waits on glitch-b5's ruling.

## Date

2026-10-16
