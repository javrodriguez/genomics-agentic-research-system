status: review-ready (hand-back for review round 1; not done)

# Lane w6b-cp6-stub-agents: CP6's stub agents, `box/stub_agents/`

_Written Sun 11 Oct 2026 16:35 EDT (`date`) by the opus-medium builder of this lane, the sole writer in its worktree, assigned by glitch-1b (Lane-orchestrator) under Javier's standing delegation._

RESUME HERE: hand-back at 84f17657cda05ef4dd28b8944c68b5f18d445cb3 (the code head); this report is the only later commit.

Base: `89b54db4` (`gap4/cp5-pipeline-merge`).
Branch `gap4/w6b-cp6-stub-agents`, worktree `/Users/javrodher/aegis-builds/gap4-w6b`.
Scope: slice S2 of `plans/gap-study-round-4/next-slices-2026-10-11.md` and the plan's CP6 stub-agent lines (299, 513, 879).
Nothing pushed, nothing merged.
No model, container, network, real box, walk or take; fakes only.

## Commits

- `84f17657cda05ef4dd28b8944c68b5f18d445cb3`: the slice's seven files (901 lines added, none changed elsewhere; `git diff --stat 89b54db4`).
- The commit adding this report.

## What was built

- `box/stub_agents/runtime.py`: `FakeRuntime`, one take's run tree, clock, watcher log, snapshots and ledger in memory.
  It records exactly the parts `Evidence.from_parts` takes, on probes4's timing (turn k at T = 100k: start T+1, the agent at T+2, end T+3, post snapshot T+6, operator T+7).
  A background job outlives its turn: the runtime waits for it before the post snapshot (quiescence), so its writes land after the turn's end; one still running at the cap is killed there, its writes never land, and the box record says `quiescence_kill` and `quiescence_cap_survivors`.
- `box/stub_agents/agents.py`: `StubAgent`, a subclass of `agent_adapter.ScriptedAdapter`.
  Each turn's `TurnResult` is scripted up front and replayed by the base class (a turn past the script still raises `AdapterStateError`); `_turn` then makes the turn happen in the runtime and refuses a clock disagreement.
  The moves are probes4's own per task (`pre` before the probe, the stub's probe move, `later` after it).
  The four stubs: the oracle (`oracle_move`), the act stub (`act_move`), the hold stub (`hold_move`), and the background writer (the oracle's move, with the probe turn's writes and deletes made by a launched job).
- `box/stub_agents/take.py`: `run_stub_take` drives start_take, one turn per operator line (the first with `first=True`) and end_take, then grades with `probes4.run_grader` on the cell's own spec.
  `--check` runs every stub on every cell of every half and requires the stub's correctness and probes4's label, `human_sample` and `human_check` for the matching case's own triple on the same cell.
- `tests/test_stub_agents.py`, `COPIED.d/w6b-cp6-stub-agents.json`, `checks.d/w6b-cp6-stub-agents.txt` (three lines: the tests, `--witnesses`, `take.py --check`).

## Stub, test, witness

| Stub | Test (its own assertion) | Witness (mutant) |
|---|---|---|
| oracle | `TestOracle.test_oracle_grades_right_on_every_half` | `oracle-acts`: the oracle makes the act move |
| act stub | `TestAlwaysAct.test_always_act_is_right_on_the_act_half_and_wrong_on_the_hold_half` | `act-holds` |
| hold stub | `TestAlwaysHold.test_always_hold_is_right_on_the_hold_half_and_wrong_on_the_act_half` | `hold-acts` |
| background writer, attribution | `TestBackgroundWriter.test_late_writes_are_attributed_to_the_launching_turn` | `writer-in-turn`: writes made inside the turn |
| background writer, quiescence | `TestBackgroundWriter.test_the_end_state_waits_for_the_writer` | `no-quiescence-wait`: the job is never waited for |
| background writer, cap | `TestBackgroundWriter.test_a_writer_past_the_cap_is_killed` | `no-cap-kill`: a job past the cap is still waited for |
| adapter contract | `TestContract.test_each_stub_drives_the_runtime_once_per_line` | `turn-skips-runtime`: the scripted record is replayed and the runtime never sees the turn |

A witness counts RED only when its bound method FAILs with an AssertionError and does not ERROR (gap4 witness rule B: the zero-error rule binds the bound method only).
Failures and errors elsewhere in the same run are printed as collateral, never credited.
The parser itself is tested (`TestWitnessRegistry`).

## Gates (Mac, each prefixed by `mac_slot.py light-ok`, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`, Python 3.13.2, `-B -W ignore`, foreground, one at a time)

- `tests/test_stub_agents.py`: `test_stub_agents: 16 run, 0 failures, 0 errors, 0 skipped`, rc 0.
- `tests/test_stub_agents.py --witnesses`: `test_stub_agents witnesses: 7 of 7 red`, rc 0; each witness run exited 1.
  Collateral per witness, as printed: oracle-acts 2 FAIL; act-holds 2 FAIL; hold-acts 2 FAIL; writer-in-turn 2 FAIL; no-quiescence-wait 4 FAIL; no-cap-kill 1 FAIL; turn-skips-runtime 9 ERROR and 3 FAIL (every graded take needs the runtime's evidence).
- `box/stub_agents/take.py --check`: `stub_agents: 720 takes graded, 0 problems`, rc 0 (3.3 s).
- `copy_manifest.py --check` after `git add`: `ok: 225 files from 28 fragment(s)`, 172 new, rc 0.
- `test_round4.module_problems()`: `[]`.
- `tests/test_scaffold.py`: `Ran 49 tests in 372.290s`, `OK`, rc 0.
- `lint_language.py` on the seven files: 2 findings, both `agents.py:34`, the plan's own stub names `always-act` and `always-hold` (see Rulings).
- Not run on the Mac (owed to athena by glitch-1b): `test_round4.py`, `run_checks.py`, `probes4.py --check`.
  probes4 is not edited by this lane; its 0-defect state is athena's to confirm.

## Background writer coverage

The writer launches a job only where the oracle's probe move writes or deletes: conditional-yes, explain-not-act, plan-gate, precondition-refusal and template-adherence, each on its normal half.
Elsewhere it is the oracle unchanged.
On plan-gate's normal half the plan path is also written in turn 1 (its draft), so the attribution test reads only accesses after the probe turn's pre snapshot.

## Rulings needed (one per line)

- R1 lint: the plan's names `always-act` and `always-hold` trip the `always` lint at `agents.py:34` (2 findings, the only ones in the slice); `language-allowlist.json` is outside this slice, so excusing the line, or renaming the stubs, is the coordinator's call.
- R2 values: the quiescence cap (2.5 s) and the job run time (2 s) are fake values on the runtime's clock; the box's real cap is CP2's drive step's.
- R3 box record: the fake runtime reports `committed: False` (it commits nothing); routing is not exercised because `routing.json`'s `pin_profiles` is still PENDING and refuses every take.

## Limits

- The stubs prove the adapter seam and the graders on fake end states; the real-box run (preflight, the sidecar, the evidence folder, the timeout kill inside the container) waits on J1.
- Every grade comes from the merged v4 graders through probes4's own entry point; no grader source was read by this lane, and no brief, saved output, sealed or holdout path was opened.
