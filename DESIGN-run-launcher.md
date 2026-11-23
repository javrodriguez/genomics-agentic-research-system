# Lane run-launcher: the counted-run launcher for Gap Study round 4 (design, stage 0)

_Written Thu 22 Oct 2026 by the lane's builder (Claude Opus 5.5 medium sub-agent) for glitch-f1, under Javier's standing delegation._
_Base: study tree lane/run-launcher at 5292df49 (Part S, pinned at the freeze); aegis ops/gap4-run-launcher at fd18899 (Part T, not pinned)._
_No code is written until glitch-f1 rules on this design._
_Nothing was run on athena; no token, login, lease, credential, .env or holdout file was opened (paths are named only)._

Shorthand: **S** = `evals/gap-study-4/` in this clone; **FACTS** = `/Users/javrodher/aegis-builds/GAP4-RUN-LAUNCHER-FACTS-20261022.md`; **MAP** = `/Users/javrodher/aegis-builds/GEMINI-DEFER-MAP-20261022.md`; **CP2R** = `/Users/javrodher/glitch/plans/gap-study-round-4/CP2-requirements.md`; **COSTGATE** = `/Users/javrodher/aegis-builds/GAP4-COSTGATE-D8-20261021.md`.

## 0. The decisions this design asks for (answer by number)

1. **The go-record reader (merge with lane gemini-defer).** Recommended: R5 puts one reader in `batch.py`, `deferred_go(arm, *, root, repo) -> dict | None`, and this lane calls it by name. This lane builds stages S1-S2 without it, then merges lane/gemini-defer before stage S3 and wires to it. The alternative, this lane keeping its own reader, means two readers of one record and a drift test.
2. **The publication order check sits in `check_results.check_publication`** (one call line, separate from R7's hunk at S/check_results.py:289-343). Recommended yes. The alternative, a `run_builders.py --check-order` checks.d line, would only ever run on a tree with no takes, so it checks nothing.
3. **One pinned regex in `box/walk_launch.py`**: `EVIDENCE_BLOB` (S/box/walk_launch.py:140) also admits `evals/gap-study-4/takes/<slot>/<attempt>/evidence/blobs/<sha256>`. Without it, `fetch` refuses every take commit that carries a watcher blob (S/box/walk_launch.py:503-504). Recommended yes. The alternative is a copy of fetch's security code in Part T.
4. **The run token's path**: `/home/javier/gap4-secrets/claude-run/claude-run-token`, recorded as `run_builders.RUN_LOGIN_FILES["claude-run"]`, with no change to run_take.py. Recommended. The other option is overwriting the claude1 file's content in place, which needs no code but leaves the walk record and the counted run naming one path.
5. **The round's start (the ledger's `start`)**: Javier's D8 letter, Tue 6 Oct 2026 23:43:50 EDT (`2026-10-07T03:43:50Z`), the moment arms O and G were admitted. It predates every vendor walk (the first Gemini walk ran 14 Oct). Recommended.
6. **Google's walk-phase spend read**: the ledger refuses until each capped vendor has at least one read. Recommended: Javier's r4-g billing-page reading, which is already on the freeze-gate card as J6 (COSTGATE:91). Fallback, only on glitch-f1's word: the computed $16.87 high figure (COSTGATE:65, :171), recorded with source "computed, not a vendor read".
7. **Arm G's per-take cost registered now**, used only after a go: gemini-3.8-flash $0.78 and gemini-3.5-flash-lite $0.154 per take (COSTGATE:51-52, the high column). Then a later go needs no pinned change, which is what "runs exactly as registered" asks. Recommended yes.
8. **The rehearsal take's rows**: the first two arm A rows of the rehearsal clone's `take_order`, with their records discarded on athena after a closed summary. I cannot tell whether those rows carry held-out wordings (I may not read holdout data). If one does, the rehearsal shows that wording to the model once before the counted run. Recommended yes, or name another rule.
9. **Stage order on the freeze line**: Part S lands after lane gemini-defer, then the athena battery, then the freeze rehearsal and the rehearsal take (athena, solo), then `prefreeze-precheck`. Recommended.

## 1. What exists and what does not (verified this session)

- The loop, the take driver and the commit step are built: `batch.Batch` (S/batch.py:598), `drive.walk_driver(records="takes")` (S/drive.py:3866-3906) and `drive.TakeRepo` (S/drive.py:1564).
- `batch.main` refuses at S/batch.py:1417.
- No window, no ledger and no take builders exist anywhere (FACTS section 1; `grep` confirms no `wait_reset` outside tests).
- `batch.py --check` exits 0 on this tree ("routing.json ready"; run this session).
- **The vendor reset signals exist in the records.**
  Claude Code's stream writes `rate_limit_event.rate_limit_info.resetsAt` (epoch seconds) in every walk's `turn-N.jsonl` (348 files).
  Codex's native session writes `rate_limits.primary.resets_at` in `native-turn-N.jsonl` (89 files).
  Gemini's records carry no reset signal.
  routing.json's `reset_wait` is null for all three harnesses.
- **No stub agent can drive a production take.** `WalkDriver.adapter_for` admits only each harness's exact production class (`adapter_class_problems`, S/drive.py:3791, 3838-3845).
  Claude Code cannot be pointed at a stub model, because `ANTHROPIC_BASE_URL`-style routes are refused billing routes (S/drive.py, `BILLING_ROUTE_VARIABLES`).
  So the smallest rehearsal is a real arm A take, which bills no money (section 6).
- **`walk_launch.fetch` cannot be reused for takes as it stands.** It refuses while the run is in progress (S/box/walk_launch.py:898-900), and it admits gzip evidence blobs only under `rehearsals/<walk>/` (:140), at most 256 blobs and 64 MiB per fetch (:141-144).
  Walks average 1.9 blobs each, 12 at most (137 blobs over 74 vendor walks; counted this session).
- `drive.py` is in both hashed reader-source lists (S/native_reader_registration.py:85-87, :191), so this lane never edits it.
  `box/run_take.py` is in neither list, but nothing here needs it changed.
- Registration requires a clean committed repository except the open takes' folders (S/takes.py:376-396).
  So every runtime record this lane writes is committed by its own writer, and none is written while the loop runs.
- `TakeDriver.launch` calls `sidecar_for` before `spec_for` (S/drive.py:2153-2154), and both need the take's run tree.
  So the take's run tree is built before the sub-driver's launch, never inside `spec_for`.

## 2. Part S: in the study tree (pinned; lands before the pre-check)

### 2.1 Files

| File | Status | Change |
|---|---|---|
| `run_builders.py` | new, pinned | the run plan, order check, SpendLedger, UsageWindow, take road, CLI writers, rehearsal |
| `batch.py` | edited, pinned | `main()` only: the `--run` road (section 2.6); nothing above line 1395 moves |
| `check_results.py` | edited, pinned | one call in `check_publication` (decision 2) |
| `box/walk_launch.py` | edited, pinned | `EVIDENCE_BLOB` admits the takes path (decision 3) |
| `tests/test_run_builders.py` | new | every behaviour below, `--witnesses`, `--generated-mutants --shard k/n` |
| `tests/test_batch_run.py` | new | `batch.main --run` on the fake box |
| `tests/test_walk_launch.py` | edited | the takes-path admission and its bounds |
| `tests/test_pipeline.py` or `tests/test_check_results*.py` | edited | the order check through `check_results --ledger` |
| `COPIED.d/run-launcher.json`, `checks.d/run-launcher.txt` | new | the claim, and one command per line (the w12b pattern) |

The owners' entries (w7c for batch.py, w5b for check_results.py, live-box for walk_launch.py) get one note each naming this lane's edit, as w8c did.
Lane gemini-defer edits the w7c entry of batch.py too, so whichever lane lands second rebases that one note line.

### 2.2 The run plan and the frozen order

- `run_arms(pre, go)`: the registered arms that have rows (`pre["arms"]` less `optional_arms` with 0 rows), less every arm in `pre.get("deferred_arms", {})` that has no valid go record.
  On today's design that gives {A, O}.
- `run_rows(pre, history, arms=None, limit=None)` returns `[r for r in pre["take_order"] if r["arm"] in arms]`, in frozen order and never re-sorted.
  It drops every slot that has a final committed outcome, then cuts the list at `limit`.
  `arms`, when given, must be a subset of `run_arms` and only narrows it, keeping the order (the rehearsal uses `--arms A`).
  Owed re-runs are not final, so they stay at their frozen position, and Batch's own `row_problems` checks the rest.
  Unruled slots still reach Batch, which refuses them by name. That refusal is correct: a ruling comes first.
- `order_problems(rows, pre)` is the publication check.
  Take the order in which each slot is first registered in `takes.json` (attempt 1; attempts above 1 must follow their slot's attempt 1).
  Within each launch part, that order must be a subsequence of `take_order`'s slots.
  The base part is every registered arm less the deferred ones; each deferred arm is its own part.
  The parts are needed because a G follow-up registers its rows after A and O rows that come later in `take_order`, so one global subsequence test would fail an honest later go.
  Called from `check_results.check_publication`. The freeze rehearsal's single registration (`take_order[0]`) passes it.

### 2.3 SpendLedger

- `SpendLedger(root, repo, pre, history_fn, clock)`. `read()` returns exactly `batch.LEDGER_KEYS` (S/batch.py:476):
  - `now`: `clock()` as an aware ISO string. It is recorded only and never decides the hold (Q-w7c-1).
  - `start`: `ROUND_START`, a pinned constant with its source (decision 5).
  - `spend`: every record of the committed runtime record `run-ledger.json` (outside COPIED.d, like `takes.json`), projected to `{vendor, at, usd}`.
    No record is ever dropped or trimmed, and Google's walk-phase read is one of them.
    Stored records have closed keys `{vendor, at, usd, source, by}`.
    `vendor` must be in `costs.CAPS`; `usd` is a decimal string; `at` lies between `start` and now.
    `read()` refuses when any capped vendor has no record (decision 6).
  - `walks`: one entry `{vendor, model, agent, tries_left, cost_per_try}` per money-billing (arm, model) of `run_arms`.
    `tries_left` is that pair's planned rows whose slot is not yet final.
    No G entry appears while G has no go record, because G is not in `run_arms`.
    `cost_per_try` comes from the pinned `COST_PER_TRY`.
    O is `"0"` for both models. Source: Codex2 subscription, accounts.json `openai-api.spend_cap_usd` 0 under Javier's 13 Oct 2026 ruling "existing subscriptions only" (COSTGATE:21-22, NIGHT 21 Oct 22:25: "OpenAI spends 0").
    G is per decision 7; without it a G go refuses.
  - `trimmed`: the committed `run-ledger.json` `trimmed` record, or null until Javier's "caps trimmed".
- The writers: `run_builders.py spend-read --vendor --usd --at --source --by` and `run_builders.py trimmed ...`.
  Each appends one record and makes one commit, and each refuses a dirty repository.
  The file's history must append exactly one unchanged record per commit (the `takes.row_commits` pattern, S/takes.py:342-353).
  Both writers run only while no loop runs.
- **Reproduced need**: a ledger whose `walks` lists G while G is deferred can make `walk_gate` say stop and so block every O wave (MAP section 3). A mutant that emits G walks goes red on that scenario.

### 2.4 UsageWindow (CP2R:58-63)

- `wait_reset()` reads `repo.history()`.
  It takes the pause outcomes (committed pauses, or rulings that route pause) in the tail `batch.restart_waits` uses.
  For each one it reads the vendor's own reset signal from that take's committed files, through `git show HEAD:` (committed bytes, never the working tree):
  - claude-code: the last `rate_limit_event` whose `status` is not `allowed`, else the last one, gives `rate_limit_info.resetsAt`;
  - codex: the last `rate_limits` record gives the largest `resets_at` among windows with `used_percent` >= 100, else the largest overall;
  - gemini: no signal exists, so it raises, naming routing's residual ("a Gemini pause past its window is a stop"). The loop then stops as failed (W1B2-5).
- It waits until the clock reaches the latest reset plus a 120 s margin.
  It returns promptly when that time has already passed, and sleeps in chunks of at most 300 s, re-reading the injected clock.
- It raises, so the loop stops `failed` with the reason in `stopped`, on: a pause with no signal, a reset more than 8 days ahead or more than 1 day behind, unreadable files, or a harness with no reader.
- A spend-cap stop is routing's `spend_cap_refusal` row, which stops for a ruling and never pauses.
  The run summary prints it as `"stop": "spend event"`, never as a window (CP2R:62).

### 2.5 The take road (production builders for takes)

It mirrors walk_builders' builders (S/walk_builders.py:1238-1300) and reuses every value that is not walk-specific: runtime, take spec, sidecar road, proxy road, locks, versions, budgets, exclusions, rules scanner, machine gate, ownership, settings guard, `pin_for` and `design_for`.

- **A composite driver** (`RunDriver`) holds one `drive.walk_driver(records="takes")` per harness in `run_arms`.
  Each sub-driver has its own login file, secrets, lock path and one `ProxyLaunch` per harness per run process (a static rendered `proxy.conf`).
  It routes `launch(row)` by the row's harness and records `container_id -> sub-driver`, so `drive(row, cid)`, `remove(cid)`, `record_files` and `on_published` reach the right one.
  Batch sees exactly the three-method contract (S/batch.py:205-216).
- **Per take**, in `RunDriver.launch`:
  1. `drive.launch_problems(sub, row)` runs first, so a take that does not match its records is refused before anything is built. The sub-driver's own launch repeats it; the check is read-only.
  2. The take's identity is read from its open registration: row index and `takes.row_commits()[index]`, then `session_id = takes.session_id_for(row_commit)`. The keys are exactly `drive.IDENTITY_KEYS`.
  3. The run tree: `drive.clean_run_tree(commit, session_id, exclude)` plus `walk_builders.place_instruction_file` and `place_agent_home` (the walk's `build_run_tree`, keyed by the take's session instead of `walk_session_id`).
  4. The fixture: `walk_builders.build_walk_fixture(row, tree, neutral_name(session_id))`, unchanged.
  5. For a Codex row, a `CodexLeaseRoad` per take: freshness is checked against that take's budget at its launch, and the lease is placed by `spec_for` into the take's config folder.
  6. `sub.launch(row)`. On any refusal before a container exists, the run tree is removed.
- **Cleanup**: a take's run tree is removed in `on_published`, after its commit lands.
  A take whose outcome is blocked, or failed after its drive started, keeps its run tree for a human, as a held walk does.
- **Logins**: arm A reads the run token by name (`walk_builders.login_file_by_name` on `RUN_LOGIN_FILES["claude-run"]`, decision 4). Arm O uses the codex2 lease (`run_take.LEASE_SOURCES`). Arm G, after a go only, uses r4-g.
- **One TakeRepo** for the run. Its `secrets()` is the union of every run harness's secrets read at scan time: the run token, the lease tokens, and the account emails.
  Scanning an A take for Codex tokens too is stricter, never weaker.
  `record_files` and `on_published` come from `RunDriver`. `holdout_matcher` is None ("not-checked", as for walks; S/drive.py:1572).
- `missing(builders)` refuses by name before anything is built, as walk_builders' `cli` does.

### 2.6 batch.py main

```
batch.py --run [--arms A,O] [--limit N] [--serial] [--foreground]
```

- Existing order kept: `--states`, start problems, `--check`, then the nohup rule.
- `--run`: `prereg.require_frozen`, then `run_builders.build_run(...)`, which refuses by name on any missing builder and returns `(driver, repo, window, ledger, rows)`.
  Then `Batch(driver, repo, window, ledger=ledger).run(rows)`, never passing `history=` (W1B4-6 i).
  It prints one JSON summary line (state counts, `stopped`, the spend-event mapping) and exits 0 when the queue drained, 1 when stopped or refused, 2 when refused before building.
- Without `--run`, the old refusal text stays exactly as it is, so every existing test and checks.d line holding it stays green.

### 2.7 The rehearsal entry (`run_builders.py rehearse`)

See section 6.

## 3. Part T: aegis ops (not pinned)

`ops/gap4_run_launcher.py`, modelled on `ops/gap4_regrade_driver.py` (aegis fd18899). It imports the study's modules by path from the checkout it is pointed at.

- `ship`: requires a clean records clone at the line's exact tip, as `make_plan` does.
  It reads `RUN_LOGIN_FILES`, `LEASE_SOURCES` and the account-record path with `ast`, never running them, and stat-checks them on athena. It never opens them.
  Then it runs `walk_launch.ship` unchanged and copies this file into the child, reading each sha256 back.
- `run [--limit N]`: the regrade driver's run command, copied: the O_EXCL claim under hold `gap4-run-<child>`, the athena gate, then `athena-reserve hold` around `nohup env <gate env> <commit identity> python3 -B <repo>/evals/gap-study-4/batch.py --run`. It writes `walk.pid` and `walk.exit`.
  A restart after a stop is the same verb in the same child; Batch resumes from committed outcomes.
- `status`: `walk_launch.status`, unchanged.
- `progress`: on athena, counts outcomes by `state` and prints only closed labels and integers. Athena-made words are never echoed.
- `fetch`: once the run has ended, cuts athena's chain into parts that each stay within walk_launch's blob caps (counted on athena as integers per commit), creates a ref for each part, and calls `walk_launch.fetch` unchanged once per part. Each part's head is the previous part's tip.
- `rule` and `night-rule`: run `takes.py --ruling ...` and `run_builders.py night-ruling ...` in the child, with arguments checked against closed shapes.
  Rulings commit in the run's own repository; nothing is typed by hand on athena.
- `rehearse`: section 6.
- The trim record, if the run reaches 31 Oct 23:30 UTC: `run_builders.py trimmed` run in the child through the same road (named residual R3, section 8).

## 4. The run token (decision 4)

- The freeze gate issues "a fresh run token" (ETA freeze-gate), and `run_take.WALK_LOGIN_FILES` names only the walk files (S/box/run_take.py:369-370).
- Recommended path: `/home/javier/gap4-secrets/claude-run/claude-run-token`.
  It is one line, `CLAUDE_CODE_OAUTH_TOKEN=<token>`, in its own mode-700 folder beside the walk folders.
  Javier fills it by the one key road; no session reads it.
  `walk_builders.account_emails_path` keeps working, because it reads only `WALK_LOGIN_FILES`' folders.
- **The minimal pinned change is the constant `RUN_LOGIN_FILES` in the new `run_builders.py`, which must land before the pre-check anyway.** run_take.py does not change.
  `run_take.read_login` and `check_login_place` are path-generic (S/box/run_take.py:1498-1540), and `scan_record.read_login` checks the variable name, not the path.
- Part T's `ship` stat-checks the path on athena and refuses to ship when it is absent. Filling it is an owner step.

## 5. The take order and the deferral, end to end

- Launch: `run_rows` gives A and O in frozen relative order, and G only after a go record.
- Defence in depth: lane gemini-defer's R5 makes `Batch.row_problems` refuse a deferred arm's row without a go record.
- Money: no G `walks` entry while G is deferred; every spend read is kept.
- Publication: `order_problems` through `check_results --ledger`.

## 6. The rehearsal take (B19-16)

- B19-16 (lane-reports/vendor-b19-LANE.md:19) wants the first run in which the production TakeDriver and TakeRepo launch one take while another drives.
  `freeze_rehearsal.py` drives no take (S/freeze_rehearsal.py:9-10).
  It also cannot host one: it leaves `take_order[0]` registered with no outcome, so any later register in that clone is refused (W1B4-1).
- **The smallest rehearsal take: two real arm A takes** (claude-code on the run token, no money per call), registered and driven through `batch.py --run --arms A --limit 2`.
  The second take's launch happens while the first is driving: Batch launches serially and submits each drive at once (S/batch.py:1023, :1235).
  The rehearsal asserts this from the driver's own launch and drive timestamps.
- **Where**: on athena, solo, under the hold, in a throwaway clone inside a Part T child.
  `run_builders.py rehearse` clones with `--no-local`, removes the remote, freezes with `freeze.py --rehearsal` through `freeze_rehearsal.freeze_command` and its synthetic holdout file (imported, never edited), commits the frozen state, then runs the two takes.
  It writes a closed summary: per take, state, route, commit, and launch/drive times; plus the overlap verdict.
  Part T's `rehearse` copies the summary back through the canary scan, as the regrade driver's `results` does. The clone is then removed. Nothing reaches the records clone.
- Time: two takes at 7-30 min each, overlapped (FP:289 via FACTS:75), plus about 5 min for the clone and freeze.
- It runs after the freeze rehearsal and before `prefreeze-precheck` (decision 9).

## 7. Tests, mutants and hours per stage

Every behaviour is red first.
Mutants follow the w12b pattern: hand witnesses under `--witnesses`, plus a generated sweep over every top-level function of run_builders.py and `batch.main`, sharded.
Focused modules run on the Mac behind `mac_slot.py light-ok`; the athena battery is glitch-f1's.

| Stage | Commits | Red-first tests | Mutants that must go red | Hours low / mid / high |
|---|---|---|---|---|
| S1 plan, order, ledger, window | run_builders.py (logic), tests | frozen subsequence kept; G absent without go, present with go; final slots dropped, owed kept; `--arms` narrows only; order check per part (G-after-A/O passes, a swap fails); ledger exact keys; no G walks; every spend kept; refuse without a Google read; O cost "0" with source; append-only file history; window per harness (claude resetsAt, codex resets_at), prompt return when already reset, Gemini raises, bounds, spend cap never waits | re-sort; drop arm filter; accept a go with `by` not Javier; keep final slots; order check always passes; one global part; emit G walks; filter spend by month or `at`; no-Google allowed; window returns at once; Gemini default wait; past reset sleeps again; bound removed | 2 / 3 / 4 |
| S2 take road | run_builders.py (builders, RunDriver), tests | two overlapping takes, A and O, on the fake box end to end (registered, launched, driven, committed); one run tree per take, removed at publish, kept on blocked; launch refused before any tree; identity from the registration commit; run token path, never claude1; union secrets on every commit; Codex lease per take | shared run tree; walk session id; tree built before the records check; tree left after publish; claude1 login; secrets of the row's harness only; `cid` routed to the wrong sub-driver | 3 / 4 / 5.5 |
| S3 wiring (after merging gemini-defer) | batch.py main, check_results hook, walk_launch regex, COPIED.d, checks.d | `--run` builds and runs on fakes; old refusal kept without `--run`; nohup rule; never passes `history=`; `--check` unchanged; order check reached through `--ledger`; takes blob path admitted, any other path refused | refusal left in place; nohup skipped; `history=` passed; ledger None for O; hook removed; regex widened to any path | 1.5 / 2 / 3 |
| S4 rehearsal | run_builders.py `rehearse`, tests | clone guard (never the source repository); frozen clone built; two takes overlap (fake); summary closed fields only | serial launch passes; writes into the source repository; summary echoes words | 1 / 1.5 / 2 |
| T1 ops launcher | ops/gap4_run_launcher.py, test | ship stat-checks the run token and refuses absent; run command under the hold; progress closed; fetch parts within caps; rule shapes | hold dropped; token not checked; part over the cap; athena words echoed | 2 / 3 / 4 |
| Folds after review | either | per finding | per finding | 1 / 2 / 4 |

Total builder time: about 10.5 h low, 15.5 h mid, 22.5 h high.
Part S alone (S1-S4) is 7.5 / 10.5 / 14.5 h; Part T adds 2-4 h.
That is above the facts file's 4.5-10 h, which assumed one road for walks and takes. The composite driver and the per-take run tree are the measured difference.

## 8. Named residuals

- R1. **A Codex lease that ages out mid-run** (JWT expiry, or `last_refresh` older than 7 days, S/walk_builders.py:420-421) refuses the next O launch. Batch commits that take `failed` with nothing run, and the loop stops. The fix is Javier's fresh `codex login --device-auth`, then a restart.
- R2. **athena is held for the whole run** (A 540 plus O 360 takes). Every suite launched meanwhile is refused `reserved`, the battery included. This is walk_launch's hold, with its named limits (S/box/walk_launch.py:28-41).
- R3. **The month turn**: an O wave at or after 31 Oct 23:30 UTC stops the loop until "caps trimmed" is committed in the child (Part T road).
- R4. **The holdout matcher is None on athena**, so takes record "not-checked", as walks do.
- R5. **The proxy configuration is shared** across one harness's concurrent takes (one rendered `proxy.conf`). It is bind-mounted `readonly` into each proxy container (S/box/run_take.py:1863, verified), so no take can change another's.
