Status: STOPPED at the proposal (three design choices open); nothing built

RESUME HERE: the Lane-orchestrator's ruling on D1, D2 and D3 below

# Lane w10-walk-runner: Gap Study round 4, the CP6 walk runner (proposal)

Written Mon 12 Oct 2026, 13:05 EDT (`date`), by the lane's only writer (Claude Opus 5.5), assigned by the Lane-orchestrator under Javier's standing delegation.
Branch `gap4/w10-walk-runner`, base `f14ab57b` (wave 9, review PASS; athena running).
This commit holds this report only.
Nothing was pushed, merged or spent.
No model, network, Docker, credential, salt or holdout was used.

## What the records already fix

- The chain is named by Q-w8a-6: walk rows → `walk_driver(records="walks")` → `run.write_walk_grade` → `WalkRepo.commit_walk`.
- Q-w9-2 (ruled): the runner calls `walk_driver(records="walks")` and so gets the W1 pre-launch check (`walk_launch_problems`) for free.
- Layout A (ruling W8-layout-1): one walk is one folder, `rehearsals/<walk>/`; a retry is a new walk id; "a walk that dies is still a walk, committed with its reason" (rehearsals/README.md).
- Plan CP6 (line 877-878): every walk is graded but never counted, and "the v4 graders and the evidence readers meet real box end states before the freeze, and their outputs are read".
- Q-w7b-3: the CLI that builds `walk_driver` from the real box (DockerRuntime, login file, counters, identity and run-tree builders) needs CP2/CP6 values and is not wired.

## What a probe showed

Scratch probe (outside the repository): `/private/tmp/claude-501/-Users-javrodher-glitch/e9abd60b-365d-4ad4-ada0-6d50eeb54887/scratchpad/w10/probe_walk.py`.
It drives one walk on test_walk_wiring's fake box (the REAL Claude Code adapter and the REAL check4 on the real design, as E1 does) with `records="walks"`, then `write_walk_grade` (a stand-in grader) and `WalkRepo.commit_walk` in a scratch repository.
Each run was behind `mac_slot.py light-ok` and `timeout -s INT 120`, with python3.13, and exited 0.

1. `faked` (E1's world, where `takes.load_rows()` answers a registered row): the walk launches into `rehearsals/w-probe-1/`, 3 turns, `checker_reasons: []`, and is committed as "Commit one walk; never counted" with 25 files.
   The mechanical chain works.
2. `prefreeze` (`takes.load_rows()` and `row_commits()` answer nothing, which is how a real study stands before the freeze): the same walk gives `checker_reasons: ['session-binding']`, and it is still committed.
   That reading is computed, then dropped: it is in the dict `drive()` returns and in no file of the walk folder.
3. `preflightfail` (preflight fails): the folder holds launch, preflight, postflight, teardown, proxy.log and evidence/, and no `driver-ledger.json`.
   `write_walk_grade` raises `FileNotFoundError ... driver-ledger.json`, so the walk cannot be committed.
   Its folder stays unregistered under `rehearsals/`, which makes `walk_register --check` fail.
4. In every variant the per-take config folder is left behind (`cfg-...`), because nothing calls `driver.published`.

Code reads behind 2 and 3:
- `drive.take_checker` always calls `check4(..., take.identity["row"], False, ...)`, so a walk is checked as a take against takes.json.
  check4's `is_walk=True` is round 3's meaning: no ledger row, AND the script truncated before the probe (check_take.py:1610).
  A round-4 walk sends the whole script, probe included, because it must be graded.
- `driver-ledger.json` is written only in `_take_records`, reached only `if ok and turns` (drive.py `TakeDriver.drive`).
  `WALK_REQUIRED` and `walk_register`'s content rule both require it.
- The readers count a walk by its `transcript.jsonl` (`mode_binding.record_transcripts`), so a walk that dies without one is in the register and invisible to mode_binding, fixture_walk, build_cases and leak_grep (L9's "readers agree").

## Open design choices (options, recommendation)

D1. How a walk is checked, and where the reading lives.
- (a) check4 gains a round-4 walk road: no takes.json row, the FULL wording script, the session id bound to the walk's identity (D2), and the ledger, model, environment and tree checks as for a take.
  `take_checker` uses it when the driver's `records` is "walks".
  The reading (reasons, events, and the route `routing.route` gives the records) is written into a new walk record, `check.json`, in the closed map (kind ledger) and required.
- (b) The take road stays, and the reading is persisted as it is; every walk then carries `session-binding`, which drowns the reasons that matter.
- (c) Walks are not checked; only graded.
  This contradicts plan line 878.
- Recommendation: (a).
  `check.json` stays apart from `grade.json` because `run.py --walks --check` regrades `grade.json` byte for byte, and the checker's reading needs the design view and pin, which the regrade does not have.

D2. A walk's identity (the caller's `identity_for`; no production builder exists yet, Q-w7b-3).
- (a) `session_id = uuid5(takes.namespace(), "walk/" + <walk id>)`, `row` None, `row_commit` None (check_take already models `row_commit` None for a walk); the project name follows from the session id as for a take.
- (b) The session id from the commit that adds the walk's register entry.
  That commit is made after the walk runs, so it cannot be known at launch.
- Recommendation: (a). The binding is deterministic and checkable from the walk id alone, and D1's walk road checks it.

D3. A walk that dies before its driver ledger exists.
- (a) The driver writes `driver-ledger.json` on every road where the record folder exists (pre-turn refusals included).
  This touches TakeDriver for takes too, and the ledger readers would meet a ledger without turns.
- (b) Walks only: the required set becomes `grade.json` plus either `driver-ledger.json` or `preflight.json`/`refusal.json`.
  `grade_walk` writes `{"graded": false, "why": ...}` from refusal.json or preflight.json.
  The readers count walks from the register, so a transcript-less walk is counted the same way everywhere (L9).
- (c) Such a walk is never committed: the runner reports it and leaves the folder for a human.
  This contradicts "a walk that dies is still a walk, committed with its reason".
- Recommendation: (b), for pre-turn refusals only.
  A `DriveRefused` from the drive scan or postflight is different: it may mean an unmasked secret or a credential left behind.
  It is never committed, the folder is kept for a human, and `walk_register --check` going red is the correct signal.
  A `LaunchRefused` (W1) makes no folder, so there is nothing to commit; the runner reports it and moves on.

## Settled in-plan (no ruling needed; how I would build it)

- A new module `walk_runner.py` with a library function that runs walks serially, one at a time.
  For each walk it does: W1 launch (through `walk_driver(records="walks")`), drive, remove, `write_walk_grade`, `WalkRepo.commit_walk`, then `driver.published` (finding 4).
  It does not use `batch.Batch`, whose slot, registration and window machinery is take-only (WalkRepo refuses `register`).
- A walk spec is the register entry's fields plus the cell (pressure or repeat) and the agent.
  The row is built from it, with `slot` equal to the walk id, because the driver keys its takes by slot.
- Claude walks only.
  `walk_driver` admits only the production ClaudeCodeAdapter, so arm O and G walks need their adapters and w7c's spend gate first.
- The CLI refuses, naming Q-w7b-3, until the production builders exist.
- Tests on the fake box, red first, each with a witness: the chain end to end; W1 reached through the runner; a pre-turn death committed with its reason (D3); a scan refusal never committed; no file under `takes/`; the config folder deleted; `walk_register --check` "ok: 1 registered walk(s)".

## Not covered

- Coverage (README Q3) and publication (Q6) stay open.
- Q-w8a-5 still applies: `mode_binding --walks --check` fails on any real walk until the pins are filled.

## Modules athena must run

- None for this commit, which is a report only.
