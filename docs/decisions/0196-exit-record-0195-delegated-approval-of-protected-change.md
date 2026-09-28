---
date: 2026-09-28
status: standing
kind: decision
touches:
  - gars/_system/executorlib.py
symptoms:
  - follow-up 0195 changes the local runner string and the local status reader under the protected prefix gars/_system/ with no owner approval record
---
# Local exit-record follow-up 0195: approval of its protected change, under the owner's delegation

Addendum to [0195](0195-local-exit-record-published-by-rename.md), which stays byte-identical.
The file this record approves is protected (`gars/_system/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such: **approved by Glitch under Javier's 23 Sep delegation**; no sentence in it is the owner's.
Its shape follows [0186](0186-fs-vocabulary-0185-delegated-approval-of-protected-change.md).

## Context

Follow-up 0195 publishes the local executor's exit record by rename and makes `_local_status` read an empty record as no verdict.
The lane's coordinator (glitch-a1, writing under the owner's standing delegation and not in the owner's words) ruled on 28 Sep 2026 that the lane builds on `81c0d71` (the local main, which public main fast-forwards to), that no Codex seat is used, and that the evidence runs once, on the final merge.
It was built on its own branch from `81c0d71` by a Claude Code producer (Opus 5.5) in an isolated clone (session `975c72c7-a724-4ec8-b4b9-01326bbbffa4`), and reviewed once by a fresh Claude Code context (Opus 5.5) from a separate checkout with no remote that never saw the producer's transcript.
**Same-model cost.** The producer and the reviewer are the same model; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent). The review was kept independent by a fresh context, a separate no-remote checkout, a stated threat model, and no access to the producer's transcript.
Producer commits, each under the repository's own identity, red-first: `b9b69fb` (the new test module and the cancel subtest, red at `81c0d71`), `505b0ac` (the fix), `5119c3e` (0195 and the build log), `f6807bb` (the index and the suite totals).
Review, kept outside the repository and cited by its kit folder:
`gars-exit-record-race/reviews/r1` APPROVE on `81c0d71..5119c3e` (two NOTE; no MINOR or worse, so the review loop ended).
F-1, NOTE: the new module does not see a dropped publish on the trap path (C5 accepts an absent record); `test_lifecycle_cancel.py`'s `test_real_local_cancel_terminates_worker` does, and the reviewer ran that mutation red. A temp file placed in `$TMPDIR` would pass every test and is held by review of the one line (`mktemp "$3.XXXXXX"`). Accepted as NOTE.
F-2, NOTE: the decision index was not rebuilt in the reviewed range; it was rebuilt in `f6807bb`.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged.

1. **`gars/_system/executorlib.py`**: the `LOCAL_RUNNER` string (the normal path and the TERM trap publish through a `mktemp` sibling in the record's directory and `mv -f`, with `code=$?` captured first), its two-line comment, and `_local_status`'s empty-record fall-through to the pid check. Every other line is as at `81c0d71`.

Outside the protected prefixes, recorded for completeness: the new `gars/tests/test_local_exit_record.py`, the empty-record subtest in `gars/tests/test_lifecycle_cancel.py`, 0195, `docs/implementation/exit_record_build_log.md`, the index, and the README and DEVELOPMENT counts and skip figures.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0195 (writer and reader; a `mktemp` sibling; the exit record only), the coordinator's rulings for the run named above, and the review dispositions above.

## What this does not close

- 0195's R1 to R5.
- The reviewer's F-1: a temp path in `$TMPDIR` is held by review, not by a test.

## Test

Glitch verified the landing merge `bd2d17a` (branch head `f6807bb` merged onto `81c0d71`), each evidence run with a process snapshot at its start and end.

- Pre-flight, 28 Sep: the `ulimit -f 0` freeze left an empty record at `81c0d71` on this Mac (bash 3.2.57) and on the build node's owner account (bash 5.2.37), on the normal and the trap path.
- This Mac (macOS, Python 3.8.2), a fresh clone of the merge, with Docker answering and row 5's scratch folder and `TMPDIR` set as CI sets them: `Ran 1192 tests`, `OK (skipped=14)`, README's mode-A figure; contracts, counts and the pre-registration check clean; the repository status clean after the run; the snapshots show no other suite, Codex or Claude run. Its `evals/test_harness.py` step ended with 13 errors, `str.removesuffix` and `ast.unparse`, Python 3.9 APIs this Mac's Python 3.8.2 lacks, as 0186 recorded; the same step at the merge under Python 3.12.9 (CI's version) was `Ran 44 tests`, `OK`, and the build node's was 44 OK, so the red is the interpreter's, not this change's.
- The build node's owner account (Linux, Python 3.13.5), fresh bundle clone of the merge, solo (the snapshots at the start, between the runs, after them and at the end show no other suite, Codex or Claude on any account): `Ran 1192 tests`, `OK (skipped=82)` without containers; with `TMPDIR` also unset, `Ran 1192 tests`, `OK (skipped=124)`; contracts and counts clean; the evaluation harness 44 OK and the pre-registration check clean.
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the records commit's `README.md` with the `TMPDIR`-unset Linux run's log: `plain run: Ran 1192 tests, OK, skipped 124` and `ok: 124 skips, at most 124 documented` (a planted 125 fails it).
- A mutation proof on `executorlib.py` as merged (sha256 `e3d16bf0b4b60bf7a3b42a52098351541553615c4cfe3d7e1798ed3ca693fbeb`, the same bytes at `505b0ac` and `f6807bb`), run on this Mac in the build clone at `505b0ac` and on the build node's owner account from a clean copy of `f6807bb`: six mutants (the writer back to `echo $? > "$3"`; the `mv` dropped; the trap back to `echo 143 > "$3"`; the reader returning `FAILED` for an empty record; the reader returning `RUNNING` without the pid check; `code=$?` captured after `mktemp`), each killed by its named test, 6 of 6 on each host, the file restored and its sha256 verified after each. The build node's first pass read 4 of 6 because the instrument parsed unittest's verbose `... FAIL` suffix, which a Python 3.13 `DeprecationWarning` printed mid-test split onto another line; a by-hand run of the (ii) mutant showed its named test failing, the instrument was changed to read the `FAIL:` summary headers, and a re-run from a fresh copy read 6 of 6. Both passes are kept in the lane's kit.
- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at `bd2d17a`'s tree, each `export_complete`, prompt and suite hashes equal to the previous record's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260928-guard-messages.json`, floor `evals/runs/smoke/smoke-20260926-row-14-activation.json`; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20260928-exit-record.json`). The lane's own Python 3.12 harness re-run overlapped it on this Mac.

## Status

Standing. Approval of follow-up 0195's protected change only.

## Date

2026-09-28
