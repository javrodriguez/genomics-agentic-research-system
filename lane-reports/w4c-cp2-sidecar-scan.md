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

## Fold 2 (lane review round 1)

The source is the lane review, round 1 (`w4c_r1_findings.md`, verdict CHANGES, on `4bb964f8`).
Every decision below is the lane lead's (the gap4 lane lead, Thu 8 Oct 2026); glitch-f3's Q1 and Q2 rulings from fold 1 still bind.
Red tests `0a3b7f45` (sidecar 116 tests: 8 failures, 14 errors; scan_record 49: 3 failures, 9 errors), fixes `66ed845e`.
On `66ed845e`: `test_sidecar.py` "Ran 116 tests ... OK", 67 mutants red; `test_scan_record.py` "Ran 49 tests ... OK", 20 mutants red; `--process-check` 27 planted forms refused, both modules ok; `copy_manifest.py --check` ok.
Each new mutant was also proved red by a single whole-file swap in a `git archive` copy of the head, one process each; the copy diffed equal to the head afterwards.

| Finding | Fix | Test | Mutant (whole-file swap, closing line) |
|---|---|---|---|
| W4C1-1 (MAJOR) the ast check was a deny-list | Default-deny by construction: per-module import allowlists of attribute chains (a module name is only ever the root of an allowed chain, so `x = os`, `socket.os`, `os.__dict__`, `os.popen`, `argparse._os`, `os.path.os` and `sys.modules` are refused); closed `from` imports; the builtins getattr, setattr, delattr, vars, globals, locals, `__import__`, exec, eval, compile, `__builtins__` and breakpoint refused anywhere; any `**` keyword refused; subprocess used only inside `inotifywait_factory`, with Popen only as a call. The modules lost their own `getattr` and `globals()` uses (`os.O_CLOEXEC`; `pending()` reads an explicit map). | `TestProcessCheck`: all 27 planted forms (every form in the finding, and the earlier ones) refused when applied to the real `box/sidecar.py`; both modules pass. | refused builtins emptied: "process check: 6 problem(s)", exit 1; os allowlist widened: "process check: 3 problem(s)"; `**` allowed: "process check: 1 problem(s)" |
| W4C1-2 (MAJOR) stderr never drained after established | `_InotifyWatcher` drains stderr on every `read_ready`; each complete stderr line after "established" becomes a `STDERR_EVENT` (the line's class only, never its text), which is outside every table, so the watcher is stopped with a non-zero code. The `inotifywait_format` reason names the stderr lines. The inotify-tools behaviour is the reviewer's recollection, unverified; the fix fails closed either way. | FakeProc pipes, format filled in memory: a line after established faults; a line before it does not. | stderr ignored: "FAILED (failures=1)" |
| W4C1-3 (MAJOR) an empty input passed | `scan` raises ScanError on an empty `files`, and on `secrets` with no `token` or `key` entry. | both refusals; a token alone and a key alone accepted | empty files: "FAILED (failures=1)"; no token or key: "FAILED (failures=2)" |
| W4C1-4 (MAJOR) three clauses with no mutant | (a) `ctl_dir_ok()`: CTL_DIR under /tmp or /run, outside the evidence mount and the program folder, asserted at module load; (b) `_rearm_order_ok`; (c) `_owned`. | (a) `/srv/ev/ctl`, `/srv/ctl`, `/srv` refused; (b) a re-arm before its snapshot refused; (c) a login file owned by another uid (geteuid patched) refused | (a) "FAILED (failures=1)"; (b) "FAILED (failures=2)"; (c) "FAILED (failures=1)" |
| W4C1-5 (MINOR) a moved consequential folder skipped the paths beneath | The guard dropped (`_move_targets` returns every consequential path beneath). | watch `out` and `out/plan.json`; `out` moved away logs both deletes | "FAILED (failures=1)" |
| W4C1-6 (MINOR) kernel-forced names (IGNORED, UNMOUNT) | Named, no code change: the `inotifywait_events` PENDING reason, the module docstring and this report. | the reason text asserted | none (text only) |
| W4C1-7 (MINOR) a new folder's race under -r | Named, no code change: the `watch_establish_s` PENDING reason, the docstring and this report. | the reason text asserted | none (text only) |
| W4C1-8 (NIT) a watch path starting with "-" | `watch_path_ok`: no segment may start with "-" (create_argv and Sidecar). | `-x`, `a/-b`, `--run-tree` refused | "FAILED (failures=3)" |
| W4C1-9 (NIT) a non-object request killed PID 1 | `_handle_request` with `_request_ok` (isinstance dict); serve uses it. | a list, a number, a string, non-JSON: each an ok false reply | "FAILED (errors=3)" |
| W4C1-10 (NIT) five green mutants | One test each: nothing logged after a fault; a death while arming seen at once (`_arm_gave_up`); MIN_LENGTH email 6; `_survived`; `_finding_ok`. | as named | after a fault "FAILED (failures=1)"; death while arming "FAILED (failures=1)"; email 1 "FAILED (failures=1)"; survival "FAILED (failures=1)"; finding shape "FAILED (errors=1)" |
| W4C1-11 (NIT) a non-callable rules scanner | `_require_scanner`: NotReady unless callable. | `RULES_SCANNER`, a string, a number | "FAILED (errors=3)" |

Interface changes, stated exactly:
- `box/sidecar.py`: `Sidecar`, `create_argv` and the rest keep their signatures; a watch path with a segment starting with "-" is now refused (ValueError). New names: `ctl_dir_ok()`, `watch_path_ok(p)`, `STDERR_EVENT`, `_handle_request(sc, raw)`. Importing the module raises RuntimeError if CTL_DIR breaks `ctl_dir_ok()`.
- `box/scan_record.py`: `scan` keeps its signature; it now raises ScanError on an empty `files` or on `secrets` with no `token` or `key`, and NotReady (not TypeError) on a non-callable `rules_scanner`.
- No PENDING field was added or removed; three reasons gained text (W4C1-2, -6, -7).

Named residuals added (stub-take measurements): the names the kernel delivers whatever the subscription (IGNORED, UNMOUNT), which are watcher faults until measured; and the `-r` race, a file made and read inside a just-made folder before inotifywait watches it, which logs nothing.

## Fold 3 (lane review round 2)

The source is the lane review, round 2 (`w4c_r2_findings.md`, verdict CHANGES, on `d06b3586`).
Every decision below is the lane lead's (the gap4 lane lead, Thu 8 Oct 2026).
The standing rule is glitch-f3's, under Javier's delegation (Thu 8 Oct): no reviewer or builder writes guard-evasion probes; isolation and guard work is built and judged by construction, and a missing guard is reported in words. This fold adds no evasion form to PLANTED; its mutants only widen or empty this lane's own allowlists.
Red tests `0451c9bc` (sidecar 135 tests against the `d06b3586` source: 15 failures, 5 errors), fixes `215768f7`.
On `215768f7`: `test_sidecar.py` "Ran 135 tests ... OK", 76 mutants red; `test_scan_record.py` "Ran 49 tests ... OK", 20 mutants red; `--process-check` "process check: ok"; `copy_manifest.py --check` ok.
Each new mutant was proved red by a whole-file swap in a `git archive` copy of the head, one process each; the copy diffed equal to the head afterwards.

| Finding | Fix | Test | Mutant (whole-file swap, closing line) |
|---|---|---|---|
| W4C2-1 (MAJOR) attribute chains not rooted at a module were never examined | Attribute names are default-deny: each box module's closed vocabulary of every `Attribute.attr` it uses, derived once from its source and committed in BOX_MODULES (`attrs`); any other attribute name is refused whatever its root, and so is any attribute whose name starts with `__`, even when listed. The modules' three `type(e).__name__` uses became `_type_name(e)`. | each vocabulary equals the module's own attributes, with no dunder; a dunder listed in the vocabulary is still refused | vocabulary and os chain widened by `popen`: "planted os.popen: NOT REFUSED", "process check: 1 problem(s)" (and the whole test file "FAILED (failures=2)"); vocabulary emptied: "process check: 1 problem(s)"; dunder rule dropped: "FAILED (failures=1)". A swap widening the os chain alone stays green: the vocabulary still refuses `popen`, so that layer is equivalent there by design |
| W4C2-2 (MAJOR) the stderr drain loop had no red mutant | The loop is factored (`_drain_stderr`). | a stderr pipe kept open and written after `established()` and after a first `read_ready` faults | drain loop removed: "FAILED (failures=2)" |
| W4C2-3 (MAJOR) any text before the marker was discarded | `INOTIFYWAIT_FORMAT` gains a closed `setup_lines` list (still PENDING, named in its reason). Any other complete line before the marker, or text before the marker on its own line, sets `setup_failed()`, and `_arm_gave_up` fails the arm at once: no watcher-start, sidecar broken. | an unknown pre-marker line fails, a setup line passes; a sidecar whose watcher reports a setup failure fails `begin` at once with no health record | any setup line accepted: "FAILED (failures=1)"; setup failure unseen by the arm: "FAILED (failures=2)" |
| W4C2-4 (MINOR) an unterminated stderr tail was never counted | Once the watcher has exited (`_tail_counts`), a non-empty remainder is one more STDERR_EVENT. | an exited watcher's tail faults; a running one's does not yet | tail never counted: "FAILED (failures=1)" |
| W4C2-5 (NIT) CTL_DIR not normalised | `ctl_dir_ok` requires `normpath(CTL_DIR) == CTL_DIR` and a non-empty segment under `/tmp/` or `/run/`; the unreachable program-folder clause is dropped; the module-load raise is named as equivalent to the test while the constant is pinned. | `/tmp/../srv/ev/ctl`, `/tmp/`, `/run/`, `/tmp`, `/tmp//w` refused; `/tmp/w-ctl`, `/run/w` accepted | normpath clause dropped: "FAILED (failures=2)" |
| W4C2-6 (NIT) a deeply nested request killed PID 1 | `_REQUEST_ERRORS = (ValueError, RecursionError)`. | 100,000 nested `[` is an ok: false reply, the sidecar still `new` | RecursionError uncaught: "FAILED (errors=1)" |
| W4C2-7 (NIT) the factory's Popen call shape was open | The ast check pins it: one positional argument, the name `argv`, and keywords exactly `stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, close_fds=True`. | the real factory passes; a factory with an added `cwd=` keyword is refused | Popen shape check dropped: "FAILED (failures=1)" |

Interface changes, stated exactly:
- The watcher protocol the `Sidecar` reads gains `setup_failed() -> bool`. Every injected watcher must provide it (the test fake returns False).
- `INOTIFYWAIT_FORMAT`, once filled, is a dict that also holds `setup_lines`: the closed list of stderr lines allowed before the marker. It is still PENDING.
- `ctl_dir_ok()` is stricter, as above. `_type_name(e)` and `_REQUEST_ERRORS` are new module names.
- No signature changed; no PENDING field was added or removed; `scan_record.py` is unchanged in this fold.

Named residual: the ast check is judged by construction, not by adversarial probing.

## Fold 4 (lane review round 3)

The source is the lane review, round 3 (`w4c_r3_findings.md`, verdict CHANGES, on `87594602`).
Every decision below is the lane lead's (the gap4 lane lead, Thu 8 Oct 2026); glitch-f3's standing rule (no guard-evasion probes; build and judge by construction) binds, and this fold plants no new form: its ast mutants only widen or empty this lane's own lists.
Red tests `64be688e` (sidecar 144 tests against the `87594602` source: 8 failures, 2 errors), fixes `cd0af616`, a test binding `433ba85b`.
On `433ba85b`: `test_sidecar.py` "Ran 144 tests ... OK", 81 mutants red; `test_scan_record.py` "Ran 49 tests ... OK", 20 mutants red; `--process-check` "process check: ok"; `copy_manifest.py --check` ok.
Each new mutant was proved red by a whole-file swap in a `git archive` copy of the head, one process each; the copy diffed equal to the head afterwards.

| Finding | Fix | Test | Mutant (whole-file swap, closing line) |
|---|---|---|---|
| W4C3-1 (MAJOR) free bare names were default-allow | Each BOX_MODULES entry gains a closed `names` set: the free (unbound) Load names its source uses, derived once (sidecar.py 31, scan_record.py 22). Any other free Name is refused; a dunder bare name is refused unless pinned (`__name__` in sidecar.py, `__file__` in scan_record.py). Names bound in the module (defs, classes, parameters, assignments, imports, except-as) are exempt. The 12-name builtin denylist stays as a second layer. | each set equals its module's own free names; a free name outside the set is refused | widened (`eval` added): "FAILED (failures=2)"; emptied: "process check: 1 problem(s)"; the free-name rule dropped: "FAILED (failures=2)" |
| W4C3-2 (MINOR) a filled format's shape was unchecked | `_format_ok`: a filled INOTIFYWAIT_FORMAT must have exactly FORMAT_KEYS (`fields`, `separator`, `established`, `setup_lines`), `setup_lines` a list or tuple of non-empty strings, and no PENDING anywhere; otherwise `pending()` still names `inotifywait_format`. | seven bad fills read PENDING (setup_lines "PENDING", a str, missing, [""], ["PENDING"], an extra key, established "PENDING"); a good fill reads ready | shape unchecked: "FAILED (failures=7)" |
| W4C3-3 (NIT) the kill on a failed arm had no mutant | Factored as `_abandon(w)`. | the abandoned fake is force-stopped (rc -SIGKILL) | kill dropped: "FAILED (failures=1)" |
| W4C3-4 (NIT) two equivalent mutants | The non-empty-segment clause of `ctl_dir_ok` is dropped (normpath already refuses `/tmp/` and `/run/`). The fault latch in `established()` stays and is named equivalent here: without it the bad line stays in the buffer and the fault recurs. | the fold 3 `ctl_dir_ok` cases still hold | none (the clause is gone; the latch is equivalent) |
| W4C3-5 (NIT) the last drain's fault was dropped | `pump` passes `fault = not self._drain()` to `stop_exit_code`, and the problem text says "and faulted". The test has the watcher exit between the first drain and the poll, so only the second drain sees the faulting line (a first version let the first drain catch it, and its swap stayed green; `433ba85b` binds it). | the problem names the fault; the stop is non-zero | last-drain fault dropped: "FAILED (failures=1)" |

Interface changes, stated exactly:
- `box/sidecar.py`: new names `FORMAT_KEYS`, `_format_ok(fmt)` and `Sidecar._abandon(w)`. `pending()` names `inotifywait_format` while a filled format fails `_format_ok`. `ctl_dir_ok()` drops a redundant clause, with the same accepted set. No signature changed; no PENDING field was added or removed.
- `box/scan_record.py`: unchanged.
- The ast check (`tests/test_sidecar.py`): BOX_MODULES entries gain `names`.

Named residual (carried): the ast check is judged by construction, not by adversarial probing.

## Fold 5 (lane review round 4: the two MINORs)

Round 4, on `d6cd1b2b`, returned PASS with no MAJOR, so the review loop is closed. Under the stop rule only the two MINORs that loosen a check are folded (the lane lead's decision); the NITs stay named below.
Every decision below is the lane lead's; glitch-f3's standing rule (no guard-evasion probes) binds. The one positive this fold adds for W4C4-1 is the guarded case itself (a parameter named after a builtin), on a two-line source of its own, never on a real module.
Red tests `810dafa1`, fixes `f6ab31dd`. **Both were committed under the Mac hold, with no test, swap or `copy_manifest --check` run.** Both edited files were only parsed at feature_version 3.11. The gates and one whole-file swap per new mutant run after the lift; athena runs the battery.

| Finding | Fix | Test | Mutant |
|---|---|---|---|
| W4C4-1 (MINOR) a binding exempted a builtin's name module-wide | In the ast check, each BOX_MODULES entry gains a closed `rebinds` set, pinned empty for both modules (neither binds a builtin or dunder name today, read by `ast`). Any binding of a builtin's name or a dunder bare name outside it is refused. `free_names` no longer exempts such a name because the module binds it somewhere, so its reads stay free and must be pinned in `names`. Methods directly in a class body (`__init__`) bind an attribute, not a bare name, and are not counted. No module change. | each `rebinds` set equals the module's own (empty); the planted positive is refused with exactly the rebind message, and `len` stays free | rebinds widened; the rule dropped (the fold 4 module-wide exemption back) |
| W4C4-2 (MINOR) `_format_ok` typed only `setup_lines` | `fields` a list or tuple of distinct non-empty strings holding `path` and `events`; `separator` and `established` non-empty strings; the PENDING test over elements, never over a string's letters. Absorbs W4C4-5. | the bad fills now also include `fields` "PENDING", "x", [], [""], a dict, None, without `events`, with a duplicate, with a PENDING element; `separator` "", None, "PENDING"; `established` "", None | fold 4's `_format_ok` put back (fields "PENDING" reads ready) |

Named, not fixed (the lane lead's decision, under the stop rule):
- **W4C4-3 (NIT):** the subprocess site is matched by the innermost enclosing def's bare name, so a nested def or a method with that name would count. The one-call rule and the pinned Popen shape still hold.
- **W4C4-4 (NIT):** `INOTIFYWAIT_ARGV` and `INOTIFYWAIT_EVENTS` are compared with PENDING as whole values only. Each fails closed if a list carries "PENDING".
- **W4C4-5 (NIT):** absorbed by the W4C4-2 fix (a `fields` of None or an int no longer raises in `pending()`).
- **W4C4-6 (NIT):** `FORMAT_KEYS` has no mutant of its own; it is bound indirectly by the good-fill assertion.

Interface changes, stated exactly:
- `box/sidecar.py`: `_format_ok` is stricter, as above; new helper `_str_list(v)`. No signature changed; no PENDING field was added or removed.
- The ast check in `tests/test_sidecar.py`: each BOX_MODULES entry gains `rebinds` (empty); new helpers `bindings`, `shielded_bindings` and `BUILTIN_NAMES`.
- `box/scan_record.py`: unchanged.

## Lessons

- A rename between a container's `/tmp` and a bind mount crosses mounts and fails; tests on one host filesystem hide it. A fake rename that fails between folders made it visible on the Mac.
- Fixing one review finding opened another: watching every folder above a path caught a moved folder but made a deleted one a fault. Ask "does this make the very behaviour being measured ungradable?" before failing closed.
