# G7: how a real CP6 walk is launched on athena (box lane, 15 Oct 2026)

Written 01:02 EDT, clock read first, for glitch-6b's readiness review of the final merged head `383e5c2f`.
Every fact below is either **read** (the source is named) or marked **NO RECORD**.
Nothing here is invented to fill a gap: where no record or code says how a step is done, the gap is named, along with the decision it needs.

## The verdict first

1. **No road launches a real walk on `383e5c2f` today, from any host.**
   `walk_runner.py` refuses (exit 2), naming 11 missing production builders, before anything is built.
   Evidence: `walk-launch-road-20261015/walk-runner-refusal-383e5c2f.txt`, run on the Mac over a `git clone --shared` of the merge clone at `383e5c2f`, with GAP4_ATHENA_SUITE and GAP4_MACHINE_BOOKING unset.
   The 11 missing builders are `runtime`, `config_parent`, `sidecar_for`, `proxy`, `lock_path`, `hosts`, `agent_version`, `design_for`, `budgets`, `run_tree_exclude` and `machine_gate`.
   `walk_builders.production_builders` (lines 545-605) returns them as `Missing` and nothing on the tree fills them: no module other than `walk_runner.py` and `walk_builders.py` mentions `production_builders` or `walk_builders.cli` outside tests.
   Seven of the eleven are real-box values the box lane has measured (the stub takes' runtime, sidecar and proxy launches, locks, hosts and resources), but no production builder set wires them.
   Four (`agent_version`, `design_for`, `budgets`, `run_tree_exclude`) are PENDING pre-registered values that the code says "a walk measures", which a walk cannot do while they are missing.
2. **The P-2 machine gate cannot work as built, on either host** (`machine_gate.py`, harness lane `9425bf62`):
   - **On the Mac it is closed forever.** Over the Mac's real `athena_suite.py list` (1202 lines), `machine_gate.problems` returns 853 problems.
     844 come from `launched=busy` runs: launches that athena refused with exit 4 (`athena_suite.py` line 119, "4 athena busy"; `athena_suite_remote.py` `work()` writes `busy` and never `started`), which never ran.
     `NOT_RUNNING_LAUNCH` admits only `refused`, and test_machine_gate has no busy case.
     The other 9 are `launched=started` runs whose verdict was never fetched, the oldest from 5 Oct.
     Evidence: `walk-launch-road-20261015/machine-gate-over-real-list.json`.
   - **On athena it would fail open.** `athena_suite.py list` reads only the Mac-local folder `~/aegis-builds/athena-suites` (`LOCAL_ROOT`, line 140) and prints nothing when that folder is absent (`cmd_list`).
     athena has no such folder, and no `athena_suite.py` within depth 4 of `/home/javier` (read over ssh, 01:00 EDT).
     An empty list gives `problems("", False) == []`, so a gate pointed there would open while a suite runs.
3. **The machine the walk must run on is athena, as `javier`**, from code, not from any walk record (see "Host" below).
   No record names a walk clone on athena, how the merged tree gets there as a git repository, or how the committed walk comes back. Each is **NO RECORD**.

## The road, step by step

### Host and account

- **Host: athena, as javier, on javier's rootless Docker.** This is read from code and the box lane's runs, not written anywhere as the walk's host:
  - `run_take.DockerRuntime` runs `docker` locally (`subprocess.run`); `RUNTIME_ENV_NAMES` carries `DOCKER_HOST` and `XDG_RUNTIME_DIR` only from the caller.
  - `create_argv` bind-mounts host paths (the run tree, the config folder, the evidence folder), so the driver must run on the Docker host.
  - The locked images (`box/image.lock`, `codex/`, `gemini/`, `sidecar/`, `egress/`; unchanged between `1cde8066` and `383e5c2f`) live in javier's rootless Docker 29.8.1 on athena, where all six stub takes ran.
  - The walk login files are athena paths: `run_take.WALK_LOGIN_FILES` = `/home/javier/gap4-secrets/claude1/claude-walk-token` and `/home/javier/gap4-secrets/r4-g/gemini-walk-login`.
  - The rules scanner's pinned binary is `/home/javier/gap4-tools/gitleaks-8.30.1/gitleaks` (`scan_record.RULES_SCANNER`).
  - athena: Python 3.13.5, git 2.47.3, Docker server 29.8.1 (read over ssh, 01:00 EDT).
- **Never the athena-suite account.** That account is the suite runner's alone: `athena_suite_remote.run_is_solo` gives "the account is one run's at a time".
- **The model account: Claude1** for the CP6 walks (`walk_builders.WALK_ACCOUNT = "claude1"`; the "glitch-06's queue item 2" comment).
  The login file exists: mode 600, owner javier, 133 bytes, modified 14 Oct 19:19.
  Only `stat` was read; the contents were not read and verify_walk_login.py was not run.

### How the merged tree gets there: NO RECORD for a walk

- The stub take's road ships **a `git archive` tar of a file list** (`stub-take-20261014/`; run 6 shipped 33 files, and run 7 below ships 36).
  **That road cannot carry a walk.** The walk needs a git repository:
  - `drive.REPO = HERE.parent.parent`, and `drive.records_repo(root)` runs `git rev-parse --show-toplevel` and refuses outside a repository.
  - `WalkRepo.commit_walk` commits the walk folder and its register entry, and refuses an untracked register.
  - `build_run_tree` checks out `variants.PINNED_TREE` `844a4ce0` from `drive.REPO`, and `844a4ce0` is an ancestor of `383e5c2f` (`merge-base --is-ancestor`, exit 0).
- So a walk needs a **full-history repository** of the merged head on athena.
  The nearest existing road is athena_suite's own bundle shipping (a `bundle_sha256` is passed to `athena_suite_remote.work`), but that ships to the athena-suite account for a suite, not a walk.
- **Decision needed:** a `git bundle` of the merged branch, gitleaks-scanned on the Mac, then scp to a new mode-700 javier folder and cloned there.
  Its path must be neutral: the stub take's run 3 showed that `gap4` in the run-tree path fails preflight's `run-tree-path-neutral`.

### The environment the runner needs

- **The machine gate, `GAP4_ATHENA_SUITE` and `GAP4_MACHINE_BOOKING`** (`machine_gate.gate_from_env`, lines 68-80):
  - Both must be absolute.
  - `GAP4_ATHENA_SUITE` must be an existing file.
  - The folder of `GAP4_MACHINE_BOOKING` must exist.
  - The docstring says "the operator's runner names both on its own machine": the aegis checkout's `athena_suite.py` and "that machine's `.machine-reserved`".
  - Those are Mac concepts. `.machine-reserved` is the Mac's mac_slot booking, and the list is the Mac's local record. Neither exists on athena (finding 2).
  - **athena's own reservation is a different file:** `/srv/aegis-handoff/machine/reserved.json` (FOREMAN-RUNBOOK section 13; `athena_suite_remote.RESERVATION`).
    Pointing `GAP4_MACHINE_BOOKING` at it collides with the road below: a walk holding that reservation would refuse its own launch, because `machine_gate` reads any file that exists as booked.
- **No record names the other variables** a walk process needs beyond `run_take.RUNTIME_ENV_NAMES` (`PATH`, `HOME`, `DOCKER_HOST`, `XDG_RUNTIME_DIR`) for the Docker client.
  The stub takes ran with javier's login environment over ssh.

### Gating against athena suites (P-2: no suite while a take runs)

- **A take must not start while a suite runs.** That is machine_gate's job, and it is broken on both hosts (finding 2).
  The box lane's working substitute, used for the stub takes, is `athena-gate.sh`: the named run's `athena_suite.py status` is not `state=running`, and athena has 0 `athena-suite` processes.
  The copy for run 7 also requires 0 javier containers: `stub-take-20261015/athena-gate.sh`.
- **A suite must not start while a take runs.** A road exists in records:
  - `athena-reserve hold --by <token> <cmd…>` (FOREMAN-RUNBOOK section 13) keeps a 29-minute lease on `/srv/aegis-handoff/machine/reserved.json`, re-written every 10 minutes and cleared on exit.
  - `athena_suite_remote.work` checks `reservation_block` first, so a suite launched during the hold is refused `busy` ("reserved").
  - `athena-reserve` is not installed on athena: `command -v` found nothing. Per the runbook it "is run over stdin from the Mac"; its source is `aegis/ops/node1/athena-reserve`.
- **Decision needed:**
  - wrap the walk in `athena-reserve hold`;
  - make machine_gate's athena reading the reservation file and the athena-suite process count rather than the Mac's list, without its own hold counting against it;
  - treat `busy` as not running, and read stale `started` runs by `status`.

### How walk records, transcripts and commits come back to the Mac: NO RECORD

- What the code fixes:
  - the walk's records and register entry are committed in the athena repository by `WalkRepo.commit_walk`;
  - the per-take config folder is deleted only on a clean drive, and kept for a human otherwise (`walk_runner` step 6).
- No record says how that commit reaches the Mac.
- **Decision needed:** a `git bundle` of the walk commits on athena, made after the walk, then scp to the Mac and gitleaks over the bundle's new objects. Then `git fetch` into a box-lane scratch clone, and integration merges.
  Publish every trace before teardown (the MEMORY lesson, 1 Oct).

## Blockers no record covers, for glitch-6b

1. **The 11 missing production builders on `383e5c2f`.** No builder set exists that wires the measured box values, and four values are PENDING pre-registered constants.
   This is the critical path for 09:00. I recommend the harness lane owns a `production_builders` fill for an A-arm Claude walk, with the four PENDING constants ruled.
2. **machine_gate:** closed forever on the Mac (busy and stale started runs), and fail-open on athena (an empty list). This is a harness-owned defect.
3. **No walk repository on athena,** and no road there or back (a bundle both ways is proposed above).
4. **The athena reservation collides with machine_gate's booking reading** if both point at `reserved.json`.
5. **`athena-reserve` is not installed on athena;** it is run over stdin from the Mac.

## What this lane did not draft

No ops launch script was written.
Every step it would automate depends on decisions 1-4 above, and blocker 1 means no script could launch a walk on this head.
Once they are ruled, a box-owned `walk_launch.sh` can be drafted red-first: gate, bundle out, hold plus run, bundle back.
