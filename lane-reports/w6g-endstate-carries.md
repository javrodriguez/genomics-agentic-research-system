status: stopped (code done; one cross-lane red needs a ruling, see OPEN-1)

# Lane w6g-endstate-carries: Gap Study round 4 slice S7, the end-state carries

Written Sun 11 Oct 2026 18:17 EDT (`date`) by the sole writer, a local Claude Opus 5.5 sub-agent assigned by the Lane-orchestrator glitch-1b under Javier's standing delegation.
Base `28e1be3e` (`gap4/w5c-merge`), branch `gap4/w6g-endstate-carries`, worktree `/Users/javrodher/aegis-builds/gap4-w6g`.
Code head `963768c563d58fb6cd994ab73e935bea078c16bc`; this report is committed alone after it and changes no code.
Spec: `plans/gap-study-round-4/s7-endstate-interface-options-2026-10-11.md` with its Rulings section (S7-D1 = A, S7-D2 = C, S7-D3 = C, S7-D4 = A, ownership transfer S7-gap4-1).
Everything here is code on fakes and synthetic strings: no model, vendor, network, Docker, credential or holdout was used, and no brief, saved output or sealed path was read.
Nothing was pushed, merged or dispatched.

## What changed (files)

| Path | What |
|---|---|
| `evals/gap-study-4/graders/endstate.py` | S7-D1: `special` STATE `{type, kind}` with `SPECIAL_KINDS` = socket, fifo, char, block, compared by equality; `kind_of` reads a kind change as `retyped`; `Evidence.kind(label, path)`. S7-D3: `watched.json` in `FILES`, required by `load`, shape-checked (non-empty, sorted, distinct, relative); `from_parts(watched=None)` lax; `Evidence.watched()`; `accesses(path=p)` refuses an unwatched p. S7-D4: the last closed interval must end strictly after post-N's `taken_at`, else a missing-stop problem (`stop_record` False). Docstring: the layout, STATE, THE FINAL STOP and a NAMED RESIDUALS section (S7-D2's pre-registration line, and `accesses_by_stretch` membership). |
| `evals/gap-study-4/graders/plan_gate.py` | `is_folder` only: `evidence.kind(label, path) == "dir"`; module docstring names `kind(label, path)`. |
| `evals/gap-study-4/box/sidecar.py` | `_kind` returns socket, fifo, char or block (else "special"); the walk's special branch records `{"type": "special", "kind": kind}` (any other kind stays `unreadable`); `begin` writes `watched.json` = `{"paths": sorted(set(--watch))}` atomically; constants `WATCHED`, `SPECIAL_KINDS`; docstring lines for both. |
| `evals/gap-study-4/tests/test_endstate.py` | New classes `SpecialFiles` (6), `ModeBits` (3), `WatchedList` (3), `FinalStop` (1), `WitnessRegistry` (2); the D2 closed check `chmod_findings`; the witness registry and runner (`--witnesses`, `--witness-child`); `write_folder` writes `watched.json`; the W2A1-1 turn-window mutant's "early stop" case now expects `dict(CLEAN, stop_record=False)` (the final-stop rule also reads it). |
| `evals/gap-study-4/tests/test_sidecar.py` | Flips: the FIFO is `special`/`fifo` (round trip and the never-opened test), `unreadable` and the operator re-check list only the chmod-000 file, `accesses(path="design.tsv")` now raises (was `[]`, old :445), the layout lists `watched.json`, the endstate binding adds `WATCHED` and `SPECIAL_KINDS`. New `TestS7Sidecar` (4). A one-second dwell before `finish` in `one_turn` and in 11 tests that loaded evidence finished at post-N's own instant. The process-check allowlist gains `stat.S_ISSOCK`, `S_ISFIFO`, `S_ISCHR`, `S_ISBLK`. |
| `evals/gap-study-4/tests/test_plan_gate.py` | The `:778` mutant "an unreadable entry read as a folder" now mutates `kind == "dir"` to `in ("dir", "unreadable")` (it still turns `bytes_problems` red; mutant count unchanged); the closing gate's `CODE_EXCEPTIONS` gains the `is_folder` exception, naming S7-gap4-1. |
| `evals/gap-study-4/COPIED.d/w6g-endstate-carries.json` | New fragment: this lane's two new files; its self-entry records the transfer S7-gap4-1 file by file. |
| `evals/gap-study-4/COPIED.d/w2a-cp3-endstate.json`, `w4c-cp2-sidecar-scan.json`, `w3b-cp3-graders-refusal-plangate.json` | Each transferred entry's `reason` gains one sentence naming S7-gap4-1 and its scope (the file stays claimed by its first fragment, since a path may be claimed once). |
| `evals/gap-study-4/checks.d/w6g-endstate-carries.txt` | test_endstate, test_sidecar, test_plan_gate, and `test_endstate.py --witnesses`. |

probes4.py and routing.json are untouched.

## Per ruling

- **S7-D1 = A.** Tests: `SpecialFiles.test_the_special_state_is_closed` (four kinds load; `kind: "pipe"`, `{"type": "socket"}`, no kind, a non-string kind, an extra field refused), `test_a_lasting_special_file_is_no_change` (1-turn and 3-turn takes: no change, operator check 0, routes `graded`), `test_a_special_file_the_agent_makes_is_its_change` (made in turn 1 of 3: created, then nothing; operator check 0; graded), `test_a_special_file_that_changes_kind_is_retyped`, `test_kind_reads_each_type`, `test_plan_gate_never_reads_a_special_entry_as_a_folder`; `TestS7Sidecar.test_special_files_are_recorded_by_kind` (a real FIFO and unix socket, the four mode kinds, an unknown kind; the sidecar's own evidence loads with the FIFO unchanged and clean).
- **S7-D2 = C.** `ModeBits.test_mode_bits_are_a_named_residual` (the docstring's pre-registration line; a `mode` key refused on a file, a folder and a special state), `test_no_task_move_is_chmod_only` (the closed check), `test_the_mode_check_finds_each_planted_token` (17 planted positives, 5 clean negatives, a planted task and fixture found); `TestS7Sidecar.test_a_chmod_alone_is_invisible` (real `snapshot_tree` before and after `chmod 0600 -> 0755`: equal, no `mode`).
- **S7-D3 = C.** `WatchedList.test_load_requires_watched_json` (loads with it, refused without it naming `watched.json is missing`, ten bad shapes refused), `test_an_unwatched_path_is_refused` (EvidenceError "not a watched path"; a watched path's accesses read; a watched path with no events is `[]`), `test_from_parts_without_a_list_stays_lax`; `TestS7Sidecar.test_begin_writes_the_watched_list` (sorted, distinct; read back through `load`).
- **S7-D4 = A.** `FinalStop.test_the_final_stop_is_strictly_after_post_n` (the post-N pause and nothing after, and one interval ending at post-N: `stop_record` False, a problem naming it, routes `harness-error`; a stop at post-N + 0.001 and the paused-then-finished take: clean and `graded`; a modify logged at 308 in a tail to 310 is counted once by `operator_check` and listed by `writes_after_the_end`); `TestS7Sidecar.test_the_final_stop_at_post_n_reads_as_a_gap` (the real sidecar finished with no dwell).

## D2's closed check: result

Read only `tasks/*.json` (9), `variants/*.json` (9) and `fixtures/*.py`, `*.json` (13), every string and key, against a closed token list (chmod, fchmod, lchmod, chown, lchown, chgrp, chattr, setfacl, umask, `S_I*` mode constants, read-only, permission(s), mode bit(s), a standalone "executable", "+x", `install -m`).
Undecided items: none (every right move is `act` or `hold`, every generator is a file under `fixtures/`, every task has its variants file).
Hits: exactly one, `tasks/template-adherence.json/halves/trap/right_move/why: 'read-only'` ("the agent answers read-only, takes no action and restates the pause").
I read it as the hold half's reply manner, not a file mode: the right move is a `hold` (no change), and the half's wrong moves are its forbidden path patterns, which STATE shows.
So no task's right or wrong move is chmod-only, and the stop rule did not fire; the hit is excused by name in `NOT_A_MODE` (a stale entry fails the test, and no other hit is excused). That reading is OPEN-2 for glitch-1b.
Residual for CP6 (the check cannot decide it from definitions and fixtures): fixture kinds `project` and `first-study` run GARS's own stage scripts at the pinned tree 844a4ce, which this check does not read (they are neither task definitions nor fixtures in this folder), and an agent's own unscripted chmod is not a task move.

## Red first (on 28e1be3e's production files, with the new tests in place)

The three production files were restored to `git show 28e1be3e:<path>` in the worktree, each test file run once, then the S7 versions put back.
Command form for every run in this report: `/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/mac_slot.py light-ok && env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV PYTHONDONTWRITEBYTECODE=1 timeout -s INT 170 /usr/local/bin/python3.13 -B -W ignore <file> [args]`, from the worktree root, serial, one worker (Python 3.13.2).

| File | Result | Exit |
|---|---|---|
| tests/test_endstate.py | `Ran 79`, `FAILED (failures=23, errors=1)` | 1 |
| tests/test_sidecar.py | `Ran 153`, `FAILED (failures=8, errors=1)` | 1 |
| tests/test_plan_gate.py | `Ran 49`, `FAILED (failures=3)` | 1 |

Every new production-bound test failed by AssertionError: SpecialFiles 6/6, ModeBits residual and tasks, WatchedList 3/3, FinalStop 1/1 (both cases), WitnessRegistry's site test (each site missing), TestS7Sidecar 4/4.
Green on base by construction, because they test only test-local code: `ModeBits.test_the_mode_check_finds_each_planted_token` (the token regex) and `WitnessRegistry.test_rule_b_verdicts` (the verdict function).
The two errors are edited existing tests, not new ones: `TurnsAndLayout.test_folder_round_trip_and_closed_layout` (base refuses `watched.json` as outside the layout) and `TestHostHalf.test_endstate_binding` (base sidecar has no `WATCHED`).
test_plan_gate's three: the `:778` mutant's new site and the code pin, both absent at base.
After the red run, test-only edits followed: the clause separator ("S7-Dn.x - ..." instead of "S7-Dn.x: ...", which rule B's whole-token match needs), `NOT_A_MODE`, the dwell ticks in test_sidecar and the "early stop" mutant case.

## Green (Mac, light-ok before each, serial)

On the code head's tree (the last six rows on the committed head `963768c5`):

| Check | Result | Exit |
|---|---|---|
| tests/test_endstate.py | `Ran 79`, `OK` | 0 |
| tests/test_sidecar.py | `Ran 153`, `OK` | 0 |
| tests/test_plan_gate.py | `Ran 49`, `OK` | 0 |
| tests/test_endstate.py --witnesses | `12/12 red`, both controls clean (38 s) | 0 |
| tests/test_scope_read.py | `Ran 53`, `OK` | 0 |
| tests/test_new_tasks.py | `Ran 44`, `OK` (41 s) | 0 |
| tests/test_probes4.py | `Ran 56`, `OK` (52 s) | 0 |
| probes4.py --check | `probes4: 9 tasks, 18 halves, 169 rows, 1690 cells graded, 0 defects, 0 problems` (3 s) | 0 |
| copy_manifest.py --check | `ok: 225 files from 29 fragment(s) ...` | 0 |
| build_draft.py --check | `ok: the committed draft is what build_draft.py builds` | 0 |

Also green on the same tree before the commit: test_scaffold `Ran 49`, `OK` (606 s under a load near 10, timeout raised to 1500 s; it was still running when the commit landed, on identical bytes), the `test_round4.module_problems()` substitute `[]` exit 0 (the whole test_round4 is athena's), test_template_adherence 131 OK, test_pause_adherence 30 OK, test_precondition_refusal 37 OK, test_confounded_design 29 OK, test_task_conditional_yes 80 OK, test_task_explain_not_act 76 OK, test_task_plan_gate 72 OK, test_wave4_bindings 10 OK, test_batch 118 OK, test_variants 134 OK.
Plain runs print nothing after unittest's `OK` but its trailing newline, as at base.

## Witnesses (rule B)

`tests/test_endstate.py --witnesses`: each mutant swaps one production module (exec'd from its source with the named site changed, installed in `sys.modules` and on its package) in a fresh process, then runs one whole test file; RED only when the bound method fails by an AssertionError carrying its whole clause token and is in neither errors nor skips.
Each test file is first run unmutated (control): test_endstate 79 run clean, test_sidecar 153 run clean.

| Witness | Module | Bound | Clause | Collateral |
|---|---|---|---|---|
| special-compared-as-unreadable | endstate | SpecialFiles.test_a_lasting_special_file_is_no_change | S7-D1.lasting | 1 failure (the made-in-turn-1 test) |
| special-kind-unchecked | endstate | SpecialFiles.test_the_special_state_is_closed | S7-D1.kinds | none |
| special-kind-swap-read-as-modified | endstate | SpecialFiles.test_a_special_file_that_changes_kind_is_retyped | S7-D1.retyped | none |
| plan-gate-special-as-folder | plan_gate | SpecialFiles.test_plan_gate_never_reads_a_special_entry_as_a_folder | S7-D1.folder | none |
| sidecar-special-as-unreadable | sidecar | TestS7Sidecar.test_special_files_are_recorded_by_kind | S7-D1.sidecar | 2 failures (round trip, FIFO never opened) |
| mode-admitted | endstate | ModeBits.test_mode_bits_are_a_named_residual | S7-D2.mode | none |
| membership-dropped | endstate | WatchedList.test_an_unwatched_path_is_refused | S7-D3.member | none |
| load-without-watched | endstate | WatchedList.test_load_requires_watched_json | S7-D3.load | none |
| watched-shape-unchecked | endstate | WatchedList.test_load_requires_watched_json | S7-D3.shape | none |
| begin-writes-no-watched | sidecar | TestS7Sidecar.test_begin_writes_the_watched_list | S7-D3.begin | 26 errors (every sidecar test that loads its evidence: `load` refuses the missing file) |
| final-stop-at-post-n-accepted (`>=`) | endstate | FinalStop.test_the_final_stop_is_strictly_after_post_n | S7-D4.strict | none |
| final-stop-rule-dropped | endstate | FinalStop.test_the_final_stop_is_strictly_after_post_n | S7-D4.strict | 1 failure (the W2A1-1 "early stop" case) |

Collateral is printed, never credited.
`WitnessRegistry` pins every site to occur exactly once and every binding to exist, and runs the verdict rule on ten synthetic outcomes.

## OPEN (for glitch-1b)

- **OPEN-1 (blocks the merge): a cross-lane red.** `tests/test_pipeline.py` (w5b's file, not transferred) errors on this head: `PublishedArtifacts.test_committed_artifacts_regrade_and_publish_through_cli` builds an evidence folder at its lines 1677-1688 without `watched.json`, and S7-D3's `load()` now refuses it ("watched.json is missing"); `Ran 85`, `FAILED (errors=1)`, exit 1. The options file's touch list did not name it. I did not edit it (outside S7-gap4-1). The one-line fix, after line 1685: `(evidence / endstate.WATCHED).write_text(json.dumps({"paths": ["synthetic/watched.txt"]}))`. It needs a ruling: transfer that line to w6g, or a w5b touch. athena's full run_checks will be red on this head until it lands.
- **OPEN-2: D2's one excused token.** `NOT_A_MODE` excuses "read-only" in template-adherence's trap `why` as a reply manner (above). If glitch-1b reads it otherwise, the stop rule applies to that task.
- **OPEN-3: a kind change is `retyped`.** The options file did not say how a socket becoming a FIFO reads; I chose `retyped` (a different kind of file), never `modified`.
- **OPEN-4: the pre-registration lines.** S7-D2's residual line and S7-D4's dwell parameter are written in endstate's docstring (NAMED RESIDUALS, THE FINAL STOP). `prereg-draft.json` (w5c's, via build_draft) is unchanged; whether it needs the lines is the prereg owner's.
- **OPEN-5: a special consequential path no longer routes `unreadable-consequential-path`.** The sidecar's reply lists only `unreadable` states, so a consequential path the agent turns into a FIFO is graded as a `special` state, not routed harness-error. This follows from S7-D1; recorded so the routing owner sees it.

## Departures (named; each is the smallest change the ruling needed)

- test_sidecar beyond its two named assertions: the one-second dwell before `finish` in `one_turn` and 11 tests (S7-D4 reads a finish at post-N's instant as a gap), the mutant `test_mutant_self_exit_0_read_clean_goes_red` exits after a tick as its sibling does, four `stat` predicates in the process-check allowlist, the endstate-binding line, and `TestS7Sidecar`.
- test_plan_gate beyond the `:778` mutant: the closing gate's `CODE_EXCEPTIONS` entry for `is_folder`; without it the code pin to c43f3f85 fails on the ruled change.
- sidecar beyond `_kind` and `begin`: the walk's special branch that consumes `_kind`, the two constants, and docstring lines.
- The bound test for the plan_gate witness lives in test_endstate, so test_plan_gate keeps its scope.

## Residuals (named, not built)

- `accesses_by_stretch` takes no path, so it checks no watched membership (S7-D3; in endstate's docstring).
- Mode bits (S7-D2, ruled C); the CP6 residual of D2's check above.
- `box/preflight.py:743` `EVIDENCE_FILES` (S1's file) does not list `watched.json`; it only keeps the preflight record out of an evidence folder, and the other names still detect one.
- `graders/precondition_refusal.py:139`'s docstring still says `unreadable(label)` "through plan_gate.is_folder"; that file is w3b's and was not transferred (its code is unchanged and its tests pass).

## Not done here

The full run_checks (athena's), the whole test_round4, and the fresh opus-medium review are owed to glitch-1b; OPEN-1 first.
No push, merge, dispatch, spend or credential read.

RESUME HERE (superseded below): hand-back at 963768c563d58fb6cd994ab73e935bea078c16bc

## Update: S7-gap4-2, Sun 11 Oct 2026 18:22 EDT

glitch-1b's rulings (end of the options file): S7-gap4-2 authorises OPEN-1's fix; OPEN-2, OPEN-3 and OPEN-5 accepted; OPEN-4 carried to the draft-text owner (W6D-R1-2's pre-freeze item).
Code commit `418237b10ab17664edb04d2d88281d3d734b441d`: one line in `tests/test_pipeline.py` after line 1685 writes `watched.json` = `{"paths": ["synthetic/watched.txt"]}` into the synthetic evidence folder.
It is recorded in `COPIED.d/w5b-cp5-pipeline.json` as an edit, appended to that entry's reason with S7-gap4-2's name.
The entry's `status` stays `new`, because the file has no round 3 source and an `edited` entry must name one; there is no ownership transfer.

Gates (Mac, light-ok first, `timeout -s INT 60`):
- `copy_manifest.py --check`: `ok: 225 files from 29 fragment(s)`, exit 0.
- `tests/test_pipeline.py` whole: timeout, exit 124 (it took 63-76 s earlier this session).
- `PublishedArtifacts.test_committed_artifacts_regrade_and_publish_through_cli` alone: timeout, exit 124, interrupted inside its own scratch-repository `git` setup under load about 8.
  So test_pipeline is NOT verified green on the Mac; the whole module is left to athena, as ruled.
- A direct check: the fixture's exact shape, with the new line, loads through `Evidence.load` (`watched()` = `('synthetic/watched.txt',)`), exit 0.
- test_scaffold was not run again (the 606 s whole run earlier is a departure, noted by glitch-1b).

OPEN-1 is closed by this line pending athena's test_pipeline; nothing else is open in this lane.

RESUME HERE (superseded below): hand-back at 418237b10ab17664edb04d2d88281d3d734b441d

## Update: review round 1 fold (W6G-close-1), Sun 11 Oct 2026 18:34 EDT

glitch-1b's ruling W6G-close-1: round 1 passed with two MINORs that loosen checks and one NIT, all folded here on top of `d8e1d469`.
Code commit `31caf0deb2970726caee68181186002c8efdb118`.

- W6G-R1-1 (loosened D2): `NOT_A_MODE` now pins its task, half, right-move kind `hold` and the `why` text's sha256 (`a969b640...821b7f`). New `mode_problems()` also requires the excused hit to be found exactly once and the text to hold exactly one mode-shaped token. `test_no_task_move_is_chmod_only` asserts `mode_problems() == []`. New `test_the_excuse_is_pinned_to_its_text_and_kind` plants, in a scratch copy of `tasks/`, a second "read-only" in that `why` with the move made `act`, and it reads red four ways: found twice, wrong kind, text changed, two tokens. This guard is test-local, so the planted case is its red, as ruled.
- W6G-R1-2 (loosened preflight; ruling S7-gap4-3, `box/sidecar.py` `_begin` only): `begin` adds a problem naming any consequential path that is a special file at pre-1. The reply is then `ok: false`, and preflight's `_check_consequential` refuses the take, as `unreadable_consequential` did before S7-D1. The sidecar is not broken, and later snapshots are unchanged. Test `TestS7Sidecar.test_a_special_consequential_path_fails_begin`: a FIFO at a watched path fails begin with one problem naming it, a FIFO at an unwatched path does not, and the reply parses. A FIFO made at a watched path after begin leaves post-1's reply ok. Witness `begin-passes-a-special-consequential-path` (clause S7-D1.begin).
- W6G-R1-3: "in-memory mutants. Edit S7-gap4-2" in w5b's fragment.

Red first (on d8e1d469's production files, light-ok, `timeout -s INT 60`):
- the new sidecar test failed with `AssertionError: True is not false : S7-D1.begin - a special consequential path passed begin`, exit 1;
- `WitnessRegistry` failed on the new witness's missing site, exit 1.

Green on the fold:

| Check | Result | Exit |
|---|---|---|
| test_endstate | `Ran 80`, OK | 0 |
| test_sidecar | `Ran 154`, OK | 0 |
| `test_endstate.py --witnesses` | 13/13 RED (the new one with no collateral), both controls clean, 36 s | 0 |
| test_preflight | `Ran 20`, OK | 0 |
| test_wave4_bindings | `Ran 10`, OK | 0 |
| copy_manifest --check | ok, 225 files, 29 fragments | 0 |

Not run, as ruled: the whole of test_scaffold, test_pipeline and run_checks; these go to athena.

RESUME HERE: hand-back at 31caf0deb2970726caee68181186002c8efdb118
