status: done

# Lane w4c-cp2-sidecar-scan: CP2 sidecar (snapshots, watcher, health) and the commit scan

Base `48f100563e68f4798defd96fb1bf483dd679c940` (`gap4/wave3-merge`).
Code head `660c07d2` on `gap4/w4c-cp2-sidecar-scan`; this report is committed alone after it and changes no code.
Everything here is code on fakes: no image was built, no container was created or run, and no model was run.
Nothing was pushed or merged.
No wave 1-3 file was edited, and `graders/endstate.py` is unchanged.

## What changed (files)

| Path | Status | What |
|---|---|---|
| `evals/gap-study-4/box/sidecar.py` | new | The host argv builders (`create_argv`, `start_argv`, `ctl_argv`, `rm_argv`, `parse_reply`, `parse_completed`, `expect_from_argv`) and the in-container `serve`/`ctl` program: the whole-tree snapshotter, the watch plan, the watcher state machine behind an injected factory, and the health records on an injected host clock. |
| `evals/gap-study-4/box/scan_record.py` | new | `scan(files, secrets, *, rules_scanner, holdout_matcher=None)` (interface 14), `read_login`, `passed`. |
| `evals/gap-study-4/tests/test_sidecar.py` | new | 98 tests, 57 mutants red. It also holds interface 10's `ast` check (`--process-check`). |
| `evals/gap-study-4/tests/test_scan_record.py` | new | 35 tests, 13 mutants red. |
| `evals/gap-study-4/COPIED.d/w4c-cp2-sidecar-scan.json` | new | This lane's fragment; every file listed as `new`. |
| `evals/gap-study-4/checks.d/w4c-cp2-sidecar-scan.txt` | new | Both test files, the process check (planted positives first), and a grep that neither module types a harness name. |
| `lane-reports/w4c-cp2-sidecar-scan.md` | new | This report (authorised by the lane lead after the build). |

## Commits

| Commit | What |
|---|---|
| `8a991045` | The checkpoint tests, red against a stub module (5 errors of 7). |
| `59735521` | The sidecar, checkpoint green (7 tests). |
| `67256677` | The full sidecar tests, each guard with its mutant. |
| `05ebfc3a` | `scan_record`, and the checks file in full. |
| `82f39fd3` | No snapshot before `begin` or after `finish`. |
| `06914816` | Fold of the builder's own review, round 1 (it landed before the lane lead's rule "no further reviewer"). |
| `a8f7552e` | Fold 1: the red tests (98 ran: 2 failures, 76 errors). |
| `660c07d2` | Fold 1: the fixes, green. |

## Runs on 660c07d2

Each run was gated on `light-ok`, run alone in the foreground, at 18:35 EDT on Thu 8 Oct 2026.

- `tests/test_sidecar.py`: "Ran 98 tests ... OK", "mutants run red in this file (57)".
- `tests/test_scan_record.py`: "Ran 35 tests ... OK", "mutants run red in this file (13)".
- `tests/test_sidecar.py --process-check`: 8 planted positives refused, then `box/sidecar.py: ok`, `box/scan_record.py: ok`, "process check: ok".
- `copy_manifest.py --check` after `git add`: "ok: 111 files from 8 fragment(s)".
- The no-harness-name grep: exit 0.
- Not run here, by the brief: `test_round4.py`, `run_checks.py` and the whole suite (the lane lead runs them on athena).
- Not checked: a real Python 3.11 run. The Mac has none, so 3.11 rests on `ast.parse(feature_version=(3, 11))` in the tests.

## Decisions (this lane's own unless named)

- **Watch plan:** the whole run tree, recursively (fold 1, Q2, glitch-f3's ruling).
- **Folder moves:** a folder renamed away from a consequential path's chain logs a `delete` for each consequential path beneath it; a folder renamed onto it logs a `modify`. An `rm -rf` logs its own per-path deletes. Neither is a fault.
- **Faults:** only an event name outside the closed table, or an event that maps to no run-tree path. A queue overflow writes its own `queue-overflow` record and does not stop the watcher; that record already routes the take as a gap.
- **Flags:** `ISDIR` and `CLOSE` are modifiers, not ops; `CLOSE` is inferred, not measured.
- **Exit codes:** a deliberate stop that ends by SIGTERM records 0; a fault, or an exit nobody asked for, never records 0 (it records its code, or 1).
- **A watcher that exited before the stop request** is not a requested stop: it records its code (an exit 0 records 1) and breaks the sidecar.
- **After a death or a failed re-arm** the sidecar stays broken: later snapshots are still taken (endstate needs every label to load) but reply ok: false; `finish` writes no second stop.
- **Labels** come in take order only; a wrong one is refused and writes nothing; no snapshot before `begin` or after `finish`.
- **Stamps:** every event stamp is held between the last health record and the current clock reading, so the health records stay in time order and no access lands after its stop.
- **Temp files** (fold 1, Q1, glitch-f3's ruling): each sits beside its destination under a dot-name (`snapshots/.tmp-<label>-<n>`, `blobs/.tmp-<sha256>-<n>`, `.tmp-<name>-<n>` in the evidence root) and is renamed within one mount; `finish` removes any temp the sidecar made; a leftover makes `Evidence.load` refuse the folder.
- **`create_argv` refuses:** an image that is not `sha256:<64 hex>`, a root user, a run tree overlapping `/srv/ev`, `/opt/w` or the control folder, commas or quotes in paths, and an empty or duplicated watch list. A container is named only by its 64-hex recorded id.
- **`expect_from_argv`** parses `create_argv`'s output into interface 13's shape, with `cap_add: ["PENDING"]`.
- **The scan:** only `transcript`, `stream` and `session` are masked; a mask that would break a JSON line is refused rather than written; a value inside a longer one is masked once, as the longer one; every other kind's hit, every rules-scanner finding and every holdout hit is refused.
- **`read_login`** refuses a link, a mode other than 600, a file not owned by its reader, a file inside a git repository, more than 64 KiB, and anything but exactly one `NAME=` line.
- **The process guard** sits in `setUpModule`/`tearDownModule`, so it never patches the other lanes' modules in the battery (fold 1, Q5, the lane lead's call: accepted).
- **Neutral names:** interface 16's neutrality test is out of scope for this lane; nothing it writes is mounted in the take container.
- **C3 names:** this lane holds `UNREADABLE_CONSEQUENTIAL_KEY` and `UNREADABLE_CONSEQUENTIAL_ROW`; the two quiescence-cap constants are `run_take`'s.

## Fold 1

The source is the builder's own review, two rounds, by one fresh opus-medium agent.
Round 1 was folded at `06914816`; fold 1 folds the rest under glitch-f3's rulings (Q1, Q2) and the lane lead's calls (Q3 to Q5).

| Finding | Fold |
|---|---|
| R1 MAJOR 1, the cross-mount rename (glitch-f3's ruling Q1) | Every temp beside its destination, renamed within one folder; `finish` sweeps. A fake rename that raises EXDEV when the parent folders differ: a take under it is green; the old private-folder layout and a temp in `/tmp` are each red. A planted leftover in `snapshots/`, the root or `blobs/` makes the load refuse. A `finish` without its sweep: mutant, red. |
| R1 MAJOR 2, a self-exit 0 read clean | Folded at `06914816`: an exit nobody asked for never records 0. |
| R1 MAJOR 3, a stale watch | Folded at `06914816`, then replaced by Q2's recursive whole-tree watch. |
| R1 MINOR 4-9, NIT 10-12 | Folded at `06914816`. |
| R2 MAJOR 1, a chain folder deleted or moved (glitch-f3's ruling Q2) | The whole tree watched recursively; per-path delete or modify for a moved folder; an `rm -rf` logs its own deletes; no fault. Tests: an `rm -rf`, a move, a folder moved onto the chain. Mutants, all red: a move as a fault, a move with no per-path event, an `rm -rf` as a fault, an unmapped event ignored. |
| R2 MINOR 2, the watch count | Two new PENDING values; the fake and the real watcher both watch the whole tree. |
| R2 NIT 3, a self-exit just before the stop request | `_stop` checks `poll()` first; such an exit is not "requested". Test and mutant, red. |
| R2 NIT 4, a folder event's trailing slash | The real parser strips it, and maps a path outside the run tree to None (a fault). Tested on pipes with the format filled in memory, no process started; mutant red. |
| R2 NIT 5, a stream stamp later than the clock | Capped at the current clock reading. Test and mutant, red. |
| R2 NIT 6 | No change (the reviewer called the honest assertion fine). |
| Q3 (the lane lead's call) | Re-staging and re-hashing each staged blob after masking stays with the drive and commit step, named in `scan_record`'s docstring. |
| Q4 (the lane lead's call) | Not built; named under "Not in wave 4". |
| Q5 (the lane lead's call) | The guard in `setUpModule`/`tearDownModule` is accepted. |

## PENDING values

`sidecar.pending()`, exactly these six (the real factory and `serve` raise `NotReady` while any is pending):
- `inotifywait_argv`: the command line at the pinned inotify-tools in the sidecar image.
- `inotifywait_format`: the output line's fields and separator, and the "watches established" line.
- `inotifywait_subsecond`: whether its stamps carry sub-second times (otherwise each event is stamped at arrival).
- `inotifywait_events`: the `-e` subscription, which must be exactly `EVENT_OPS`' names.
- `inotify_watch_count`: how many watches a recursive watch of a real run tree takes, `.git` included, against the box's per-user limit (fold 1).
- `watch_establish_s`: how long that watch takes to establish, which `ESTABLISH_TIMEOUT_S` (30 s) must exceed (fold 1).

`scan_record.pending()`, exactly these two (each refused on a real use):
- `rules_scanner`: gitleaks' rules on athena, over the take's record folder only, never the Brain root.
- `furniture`: per-harness positions of the fields a CLI writes itself into its stream or session file (W4BR-w4c-10).

Also pending, outside the two maps:
- the runtime's spelling of the added capability in inspect (`expect_from_argv` returns `cap_add: ["PENDING"]`);
- whether the non-root sidecar holds `DAC_READ_SEARCH` effectively (the lane lead's decision 2; measured on the stub take);
- whether `inotifywait -r` follows a renamed folder's paths;
- the holdout matcher's provider (ruling C4; until it exists every scan records `not-checked`, cleared by the deferred Mac gate inside aegis);
- whether persistent special files route every multi-turn take `harness-error` (W2A fold 1 question 3).
All are measured on the stub take or decided at the drive step.

## Named residuals

- **Special files:** a socket, FIFO or device is recorded as `unreadable`. A test asserts two persistently unreadable paths count as unexplained in the operator check.
- **Mode bits:** STATE has no `mode`, so a chmod alone is invisible.
- **The scan's exact-value search** misses a value split across a line break, a value present only in a JSON escape, and an email in another letter case (typed cases in the tests for the first two).
- **Harness furniture** would inflate the event count until `furniture` is measured; each masked entry carries its line and byte offset so the drive step can separate it later.

## Not in wave 4

The lane lead's call Q4: these carry to CP2-requirements, because `graders/endstate.py` is w2a's file.
- **A `special` STATE type** for sockets, FIFOs and devices. Today they read as `unreadable`: an existing socket reads as a phantom `unknown` change in turn 1, and a socket the agent makes routes the take `harness-error` and forces a re-run.
- **Mode bits** in STATE.
- **The watched list in the evidence:** accesses are logged on the exact consequential paths only.
- **A stop strictly after post-N:** whether the reader should require one; the watcher runs until `finish`.

Carried to the drive and commit step (Q3): re-staging and re-checking each staged blob against `sha256_after` after a scan that masked anything.

## Open questions for the lane lead

1. **Queue overflow.** glitch-f3's Q2 ruling lists "its queue overflows" among the faults. This lane keeps an overflow as its own health record without stopping the watcher (the record already routes the take as a gap). Stopping the watcher as well is a one-line change.
2. **Merge bindings this lane feeds:** `sidecar.create_argv`'s default `user` (binding 1), `expect_from_argv` against preflight's `sidecar_expect` (binding 4, `cap_add` PENDING), `scan_record.read_login` on the union of both lanes' login fixtures (binding 5), `sidecar.PROGRAM` against the sidecar Dockerfile's copy target (binding 6), and the reply field `unreadable_consequential` with the two C3 constants (binding 7).

## Lessons

- A rename between a container's `/tmp` and a bind mount crosses mounts and fails; tests on one host filesystem hide it. A fake rename that fails between folders made it visible on the Mac.
- Fixing one review finding opened another: watching every folder above a path caught a moved folder but made a deleted one a fault. Ask "does this make the very behaviour being measured ungradable?" before failing closed.
