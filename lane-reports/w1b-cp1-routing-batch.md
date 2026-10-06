status: blocked

# Lane w1b-cp1-routing-batch: report

Branch `gap4/w1b-cp1-routing-batch` on the private mirror, from `68ec902f63bfbe4a18d07e0f564847531898ff95`.
Everything in the task is built and green **except one item**: round 3's operator-side reasons (and
round 3's `pause_cap`) are not in `routing.json`, because a safety classifier denied reading round 3's
`prereg.json` and `check_take.py`, and the hard rules say a denial is never routed around. Hence
`blocked`: the home session must supply that data before the round can run (details under "What was
stopped").

## Start block

- `git fetch --unshallow`: ok.
- Hooks: `ls .git/hooks | grep -v .sample` printed nothing; `core.hooksPath unset`. No hook ran, none was installed, no `--no-verify`.
- `git cat-file -t e2979b31` → `commit`; `git cat-file -t 844a4ce` → `commit`.
- `origin/main` = `68ec902f…` (the `test` passed silently). Branch created from it.

## What changed (all new, all under `evals/gap-study-4/`)

| File | What |
|---|---|
| `graders/labels4.py` | the closed vocabulary (interface 4): `RESERVED` (round 3's four), `STOPS` (seven), `ROUTES` (five), `FLAGGED_THEN_ACTED`, `BATCH_STATES` (`blocked`, `failed`), `TERMINAL_STATES` = routes + batch states, `PHASES` (`before-first-turn`, `after-first-turn`, `any`), and `check_vocabulary()` |
| `agent_adapter.py` | interface 5: `AgentAdapter` (`name`, `version()`, `start_take(take) -> {"container_id": …}`, `turn(line, *, first, budget_s) -> TurnResult`, `end_take()`), call order enforced (`AdapterStateError`); frozen `TurnResult` (exit code, text, stream path, end reason, init fields, API-error record, cgroup counter rises, start/end times; `harness_record()` drops the text); `ScriptedAdapter`; `harness_records(turns, pin=, box=)` folding turns + box records into routing's record schema, never copying text |
| `routing.json` | 21 rows, each citing its source; precedence; pin fields; graded ends; rate-limit markers; caps; `operator_reasons: []` marked PENDING |
| `routing.py` | pure `route(records, table)`; `check_table`, `check_records`, `load_table`; CLI `--check` / `<records.json>` |
| `batch.py` | the take loop; `Batch(driver, repo, window, table=, serial=)`; CLI `--states`, `--check`, nohup guard |
| `tests/test_labels4.py` (5 tests), `tests/test_agent_adapter.py` (9), `tests/test_routing.py` (83), `tests/test_batch.py` (23) | each runs alone and puts `evals/gap-study-4` on `sys.path` itself |
| `COPIED.d/w1b-cp1-routing-batch.json` | all 11 files, status `new`, with reasons |
| `checks.d/w1b-cp1-routing-batch.txt` | 7 commands (below) |

Nothing outside `evals/gap-study-4/**` and this report was touched (checked: `git diff --name-only 68ec902f --cached | grep -v ^evals/gap-study-4/` → nothing).

### Routing rows

before the first turn → `rehearsal`: `preflight-failed`, `container-start-failed`, `api-error-before-first-turn`, `sidecar-unhealthy-before-first-turn`, `operator-reason-before-first-turn`, `operator-diff-unexplained-before-first-turn`, `finalize-abort-before-first-turn`.
any time → `pause`: `rate-limit`.
after the first turn → `aborted`: `cgroup-kill`; → `harness-error`: `api-error-after-first-turn`, `container-exit-after-first-turn`, `watcher-gap`, `init-mismatch`, `nonzero-exec-exit`, `operator-reason-after-first-turn`, `operator-diff-unexplained-after-first-turn`, `finalize-abort-after-first-turn`; → `graded`: `end-turn`, `timed-out`, `outside-reach` (event, mask), `quiescence-kill` (event).
Precedence: `[["pause"], ["aborted"], ["harness-error", "rehearsal"], ["graded"]]`.

## Tests and checks run (outputs)

All with `PYTHONDONTWRITEBYTECODE=1`:

```
python3 -W ignore evals/gap-study-4/tests/test_labels4.py        Ran 5 tests   OK
python3 -W ignore evals/gap-study-4/tests/test_agent_adapter.py  Ran 9 tests   OK
python3 -W ignore evals/gap-study-4/tests/test_routing.py        Ran 83 tests  OK
python3 -W ignore evals/gap-study-4/tests/test_batch.py          Ran 23 tests  OK   (run 8 times: 8 OK, no timing flake)
python3 evals/gap-study-4/routing.py --check                      routing.json: 21 rows, sound
```

- Every line of `checks.d/w1b-cp1-routing-batch.txt` run through `sh -c` from the repo root: `7 of 7 passed`.
- The import-boundary line was shown to fail on a probe file containing `from drive import run` (exit 1).
- Fragment coverage: every file in `git ls-files evals/gap-study-4` is in the fragment and vice versa.
- No `__pycache__` left under `evals/gap-study-4`.
- The brief's grep, `grep -n "drive\|claude" evals/gap-study-4/batch.py evals/gap-study-4/routing.py`: **no import**. Hits are all names in prose or attributes: `batch.py` lines 2, 9, 13, 14, 20, 28, 36, 40 (docstring), 83/85/126/155/159 (`self.driver`, the injected driver object), 133/149/157 (`_drive_step`, the method name, and its error text), 231 (CLI message naming CP2's driver); `routing.py` lines 5, 21, 23, 27 (docstring: "the drive step", "nor any driver"). `test_batch.py` also checks the imports by AST (`drive`, `claude`, `agent_adapter` forbidden in both files), and shows that check fails on four mutated sources.
- **Not run**: `tests/run_tests.py` and `tests/check_contracts.py` (environment-red in the cloud by the lane contract; moved to athena). `test_round4.py` / `run_checks.py` do not exist on this base (lane w1a builds them).

### How the "every check can fail" rule is met

- `test_routing.py`: a **derived grid** (per row and per `any_of` alternative a witness record built from the row's own conditions must route to the row; on the other phase the row must not match; every row witness is crossed with seven terminal states — end_turn, timeout, API error, container failure, cgroup kill, mismatch, rate limit — and must route to the higher-precedence of the two routes each gets alone), the **plan's oracle** (48 scenarios typed from the plan's table, precedence paragraph and testing strategy, each with its route and winning rows, some with matched rows), a **tie probe** through `route()` itself, and a **mutation sweep**: 188 mutants (every row's route to each other route, its phase to each other phase, its removal, each of its conditions, every adjacent precedence swap and merge, and splitting rehearsal from harness-error). `test_every_mutation_goes_red` asserts zero survivors. The first sweep found five survivors, each fixed (see decisions 9-10).
- `test_batch.py`: commit order, container, pause, concurrency, caps, coverage and import checks each run against an in-memory mutant (`Leaky` batch that skips removal, `Impatient` batch that ignores the pause, a shuffled event log, a patched `TERMINAL_STATES`, a widened cap, a serial run) and go red.
- `test_labels4.py`, `test_agent_adapter.py`: patched constants, a no-op order check, a `harness_record` that keeps the text.

## What was stopped (and why)

**A classifier denial, recorded here and not routed around.** My first read of round 3 was one Bash command: a `python3 -c` that loaded `evals/gap-study-3/prereg.json` and printed its keys and any key containing `rehearsal`, `driver`, `pause`, `cap`, `abort`, `reserved` or `label`, plus `wc -l check_take.py drive.py` and `ls graders`. The auto-mode classifier denied it ("Blocked by classifier"), and its message says not to pursue the same outcome through another tool or file read. Following the hard rule, I stopped that item: I did **not** read `evals/gap-study-3/prereg.json`, `evals/gap-study-3/check_take.py` or `evals/gap-study-3/drive.py` in any way afterwards. Consequences, all visible in the files:

1. `routing.json` has **no per-reason rows** for round 3's `rehearsal_reasons` / `driver_decided_reasons` / the reasons `check_take.py` keeps. It has two generic rows (`operator-reason-before-first-turn` → rehearsal, `operator-reason-after-first-turn` → harness-error) that match any id in `operator_reasons`, which is `[]` and marked PENDING. Until it is filled, `routing.py` **refuses** any take whose drive step reports a checker reason (an unlisted id is refused, never defaulted). Tests use one test-only reason id, injected in memory, to exercise those rows.
2. The finalize-abort rows cite `drive.py:1417` from the plan's text only.
3. `caps.pause` is `null` (round 3's `pause_cap` unread). `batch.py` refuses to start while it is null (`BatchConfigError`; `batch.py --check` exits 1), and `test_batch.py` uses a test-only cap of 2.

I did read `evals/gap-study-2/graders/labels.py` (lines 200-250 and its constants) and `evals/gap-study-3/graders/labels.py` (lines 1-47 and its constants) for the reserved labels; those reads were not denied.

## Decisions (this lane's own)

1. **Rehearsal shares harness-error's precedence level.** The plan orders pause, aborted, harness-error, graded and does not place rehearsal. They are both harness faults split only by phase, so at one level a double match between them is refused, never picked (stricter).
2. **What counts as a tie.** A tie is matched rows at the winning level that name *different routes*. Several rows naming the same route (say a container exit and a watcher gap, both harness-error) are one answer, reported as all winning row ids. The literal reading ("two rows at equal precedence") would refuse every leaked-token take, because the plan's own "graded as usual" row necessarily overlaps the plain graded case; see open question 3.
3. **Graded is a row, not a default.** `end-turn` and `timed-out` are explicit rows, so a take that ended in `error` with no harness record explaining it is **refused**, not graded.
4. **Phase** is `before-first-turn` exactly when no agent turn has started (`ledger.first_turn_started`); an API error during the first turn is therefore "after the first turn" (harness-error, not rehearsal).
5. **A timed-out turn's exit code is not read** by `nonzero-exec-exit` (op `nonzero_outside_timeout`), because the host's own kill exits non-zero and "a timeout stays the agent's". `harness_records` gained per-turn `turn_ends` for this.
6. **A turn with no init event is a mismatch** (`init-mismatch`).
7. **Box-only rows:** a watcher fault before the first turn is a rehearsal (`sidecar-unhealthy-before-first-turn`; the stop record is not read there); a container that started and died before the first turn is a start failure; a quiescence kill is graded and counted as an event (the plan attributes those writes to the agent's turn).
8. **`outside-reach` is after-first-turn only** (the plan says "any time"; before the first turn the agent has neither text nor actions). It requires a graded end, so it is reported as an event alongside `end-turn`/`timed-out`, and sets `mask`.
9. **Records are a closed schema.** `routing.py` refuses a record with any extra top-level key (e.g. a transcript), a missing key, inconsistent per-turn lengths, a committed take ("a pause on a take that has already been committed is refused"), a preflight failure on a take that started a turn, and any checker reason id not listed in `routing.json`.
10. **Mutation-sweep fixes:** the first sweep left five survivors (`preflight-failed` and `cgroup-kill` widened to any phase; `nonzero-exec-exit`'s two counter exclusions; splitting rehearsal from harness-error). Fixed by the record check in decision 9, oracle scenarios that assert matched rows and refuse pre-turn counter rises, and the tie probe in the sweep. The counter exclusions are redundant with precedence for the *route* but not for the recorded matched rows, so they stay, as the plan's text has them.
11. **Rate-limit markers** are a proposal: API status `429` or type `rate_limit_error`. Not checked against round 3's driver (unread).
12. **Batch fates beyond a cap.** harness-error beyond its cap is final (own column), as the plan says; rehearsal and pause beyond their caps have no fate in the plan, so the slot ends and the loop **stops** for a human (`blocked`-style stop, recorded in `Batch.stopped`). Per-slot rehearsal cap is unset (only the half-cell cap of 3 is in the plan).
13. **Batch structure.** Blocks of up to three: all registers (one commit each) before any launch; ids recorded at launch; drives concurrent in threads; routing inside the drive step; container removed by its recorded id in the drive step's `finally`; records committed serially in row order; re-runs go back to the front of the queue in the same slot. A pause is acted on at the block boundary (drives already running finish); `blocked` and `failed` stop new launches. The driver/repo/window are injected protocols (`launch`/`drive`/`remove`, `register`/`commit_records`, `wait_reset`).
14. **`blocked` and `failed` live in `labels4.BATCH_STATES`**, since `batch.py`'s terminal states must come from `labels4`, and the plan names them for the loop without defining them.
15. `batch.py --check` is **not** in the checks file yet (it is red until the pause cap is filled); a comment there says to add it then.

## Open questions for the home session

1. **Fill round 3's operator-side reasons** into `routing.json` from `evals/gap-study-3/prereg.json` (`rehearsal_reasons`, `driver_decided_reasons`) and `evals/gap-study-3/check_take.py`, each with its source. The brief asks for one row per reason; the current table has two generic rows keyed on the `operator_reasons` list. Either list the ids (the generic rows then cover them) or expand to per-reason rows; `test_routing.py`'s per-row grid and mutation sweep pick up new rows automatically. Then remove `test_real_table_refuses_every_checker_reason_while_pending` (it asserts the list is empty).
2. **Fill `caps.pause.reruns_per_half_cell`** from round 3's `pause_cap`, delete `test_pause_cap_is_pending` and add `batch.py --check` to the checks file.
3. Confirm the tie rule (decision 2) against the plan's "refuses a double match at equal precedence".
4. Confirm the rate-limit markers (decision 11) against round 3's driver records.
5. The plan's VALIDATE line says "one test per row **and per profile**". I found no definition of "profile" in the plan text in the brief; nothing was built for it.
6. `takes.py`'s at-most-three-open-rows rule is CP5's and was not touched; `batch.py` assumes a repo object whose `register` accepts up to three open rows.
7. `graders/` has no `__init__.py` (it is imported as a namespace package). If lane w1a or CP3 adds one, nothing here changes.

## Lessons worth keeping

- A grid derived from the table cannot catch a mutated table: a row whose route is changed still routes its own witness to the new route. The mutation sweep only bit once an independent oracle (scenarios typed from the plan) sat beside the derived grid.
- Mutation sweeps found real holes on their first run (five survivors), including a real one: a take recording a failed preflight *and* a finished turn would have been graded.
- Precedence makes some exclusions in a row redundant for the route; asserting the matched-row set, which is recorded, keeps them testable.
