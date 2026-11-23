# Batch-8 fix review fold: coverage counts only graded walks (addendum)

Writer: Claude Code harness lane, 14 Oct 2026, under glitch-06's order after `review-harness-b8fix.md` (a0ad297a PASS, 1b1f428c PASS, 9649aa0a CHANGES).
Parent: `a36a5743`. One commit, red first.
Earlier reports stay as written; this addendum corrects `batch8-fold-2026-10-14.md`.

## Retraction

`batch8-fold-2026-10-14.md` called the byte comparison in `pending_walk._verified_regrade` equivalent, "the registration gate refuses any walk whose regrade does not re-derive".
That premise is false.
The registration gate reads only the one walk the acceptance record names, so for any other pending walk the comparison is the only guard.
The reviewer showed two live survivors there (bytes dropped, and the graded check dropped).
Both are now killed by tests (below).

## What CP6 registers (quoted)

`plans/gap-study-round-4.md`, CP6, line 877: "That is about 170 walks. They are rehearsals: graded but never counted, each committed with its reason."
Line 878: "**Every walk is graded but never counted.** The v4 graders and the evidence readers meet real box end states before the freeze, and their outputs are read."
`prereg-draft.json` says of the CP6 walks on two tasks: "The walks are never graded into results" (that is about results, not coverage).
Neither text counts a committed but ungraded walk (for example one refused before turn 1) as coverage.
So the default ruling applies.

## The ruling, as built

A walk covers its spec only when its `grade.json` is graded true, or when it is a pending vendor walk that a verified graded-true regrade supersedes (`pending_walk.coverage_status`).
Every other registered walk is reported with its reason and never counted:

| Reason | When |
|---|---|
| pending | a pending walk with no verified regrade, including a regrade that does not re-derive |
| regrade refused | a pending walk whose regrade re-derives honestly with `graded: false` (its native cross-check refused) |
| not graded | any other `graded: false` grade, for example a walk refused before its first agent turn |
| grade unreadable | `grade.json` missing, not JSON, or not an object: fail closed |

- `walk_plan --coverage` prints "`<reason>`, not counted: walk '`<id>`': only a graded walk covers its spec".
- Its prose now says each registered walk's `grade.json` is read, and a pending walk's `regrade.json`.
- `pending_walk`'s docstring is corrected.
- `fixture_walk.walk_coverage` never counts a pending walk or one whose verified regrade refused, even one that holds a transcript. That is now bound, not left to the road writing no transcript.

## NITs

- A stray `source` key on the `native-readers/**` pattern entry is refused.
- `copy_manifest --check`'s ok line now counts files by status, apart from the pattern entry, and names how many reader records it claims.
- Accepted as procedural, per the ruling: files claimed under `native-readers/` bypass the per-file byte guards (round 3's record blobs), because Javier's acceptance commit is reviewed.

## A red found on the way: test_pipeline

`tests/test_pipeline.py` (FreezeCoverage, the rehearsal clone) had been red on this branch since `15429361`.
`run.py --all` failed with ModuleNotFoundError because `run.py` imports `pending_walk` and the clone did not copy it.
The athena subsets did not include `test_pipeline`.
The clone now copies `pending_walk.py`, and the suite runs 85/85.

## Verification (behind a light gate)

- Red first: P18 against the parent's `pending_walk` and `walk_plan` errors (no `uncounted`).
  The reviewer's two `_regrade_state` survivors are the parent's behaviour, and both are now killed.
- On the Mac, every touched module whole:

| Suite | Result |
|---|---|
| `test_walk_plan` | 18/18, witnesses 39/39, generated 263/263 killed in 4 shards |
| `test_pending_walk` | 21/21 |
| `test_native_reader_registration` | 7/7 |
| `test_walk_layout` | 14, witnesses 21/21 |
| `test_walk_runner` | 79, witnesses 72/72 |
| `test_pipeline` | 85/85, after the fix |
| `test_scaffold` | 49/49 |
| `copy_manifest --check` | ok |
- Mutants, all killed:
  - bytes-dropped and graded-dropped in `_regrade_state` (the reviewer's two survivors);
  - an unreadable grade counted, an ungraded walk counted, and a non-object grade counted;
  - a pending walk counted in `fixture_walk` (killed by an error, since it is compiled in place);
  - a stray `source` admitted.
