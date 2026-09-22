---
date: 2026-09-21
status: standing
kind: defect
touches:
  - infra/backup/row05.py
  - tests/test_row05_backup.py
  - infra/compose/postgres.compose.yml
  - README.md
  - DEVELOPMENT.md
symptoms:
  - "result=FAIL reason=archive_unreadable" from the first real pg_backup.sh on hardware
  - "gpg: error writing to '-': Broken pipe" when the read-back pipe's stderr is shown
  - Row05DatabaseTests setUp fails with command_failed in the first cases of a run, a different number each run
---
# The archive listing reads the whole archive, and the database fixture waits for loopback

## Context

Row 5's first run on real hardware (a Debian 13 node, PostgreSQL 16 in the repository's compose file, gpg 2.4.7, a 25.6 MB custom-format dump) printed `result=FAIL reason=archive_unreadable`.
Replaying the engine's own commands stage by stage with stderr visible showed:

- the dump, encrypt and decrypt were byte-identical end to end;
- `pg_restore -l` fed the whole plaintext exited 0 with the listing;
- inside the `stream()` pipe, `gpg --decrypt` exited 2 with `error writing to '-': Broken pipe`.

`pg_restore -l` reads the archive header and table of contents, prints the listing, and exits 0 without reading the rest of its input.
On any archive larger than the pipe buffers, the decrypt feeding it is cut off, and `stream()` fails because a producer exited non-zero.
The same pipe ends the drill's read-only listing, so every dry run and destroy would fail with `restore_failed`.
The offline tests never saw it: their `pg_restore` stub reads all of stdin.
The live-Postgres tests use a two-row table, whose archive fits in a pipe buffer.

The same session found the cause of the live-Postgres `setUp` errors that 0051 recorded and left alone.
The fixture treated the container's `healthy` status as ready.
The image's healthcheck is `pg_isready` over the Unix socket, which also answers the socket-only server that initialisation runs first.
The engine connects over `127.0.0.1`, so the first cases found nothing listening there and raised `command_failed`.

## Decision

`restore_list()` runs `sh -c 'pg_restore -l; rc=$?; cat >/dev/null; exit $rc'`, in the container or on the host.
The listing still goes to stdout, the rest of the input is drained, and `pg_restore`'s own exit status is kept, so a real listing failure is still a failure.
The database fixture counts the container as ready only when it is `healthy` **and** a loopback `SELECT 1` answers, within the fixture's 60-second startup bound (each readiness probe gets only the time that remains).

## Why

The old pipe failed closed, not open.
gpg's exit status was always checked: an archive small enough to fit in the pipe buffers was fully decrypted and integrity-checked, and a larger one was cut off and failed.
So no damaged archive ever passed; every archive past the pipe buffers failed, damaged or not.
With the drain, large archives pass, still under gpg's full integrity check.
A `pg_restore` that fails early still ends the pipe non-zero after the drain, so no failure is swallowed.
The cost is time: the drill now decrypts the whole archive twice (once to list, once to restore), and both count toward the 60-minute RTO.
The fixture change is test-only; no engine behaviour depends on it.

## Evidence

On 2026-09-21, Python 3.13.2 on macOS, Docker answering:

| Run | Result |
|---|---|
| New offline tests (4 MB dump, a `pg_restore` stub that reads only the first 4096 bytes), with `restore_list` reverted | both FAIL: `archive_unreadable` (backup) and `restore_failed` (drill) |
| The same tests with the fix | OK |
| `test_row05_backup.py` at `c934f6d`, fixture unchanged | `Ran 39 · FAILED (errors=5)`, every error in `Row05DatabaseTests.setUp` |
| `test_row05_backup.py` with both changes | `Ran 41 · OK`; all 17 live-Postgres tests pass, including `test_dry_run_and_cold_destroy` against the real `pg_restore` |
| `run_tests.py` as CI sets it (`GARS_ROW5_SCRATCH`, `TMPDIR`), Docker answering | `Ran 238 · OK (skipped=11)` |
| `run_tests.py` with `TMPDIR` set but no `GARS_ROW5_SCRATCH` (a macOS cold clone) | `Ran 238 · OK (skipped=52)` |
| `run_tests.py` with neither variable set (as on Linux) | `Ran 238 · OK (skipped=54)` |

Without the fixture change, the `setUp` errors appeared in all four earlier runs, 3 to 5 each.
`check_counts.py` is clean (enforced=3) and `check_contracts.py` reports 14 contracts clean.
