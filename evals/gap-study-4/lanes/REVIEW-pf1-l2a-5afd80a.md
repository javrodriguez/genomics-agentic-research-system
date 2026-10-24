VERDICT: CHANGES

# Review of lane pf1-l2a (routing and rulings), head 5afd80a7

Reviewer: a fresh opus reviewer, Sat 24 Oct 2026 (19:35-19:41 EDT by `date`).
Scope: commits 332577d2, d10f662e, e5f7ea44 and 5afd80a7 on 96c1d959, against pre-freeze review 1's MAJOR 5, MAJOR 8 and m17 and the approved fold plan.
Code was read, not changed.
The probes were synthetic histories built from the lane's own test helpers, run with python3.12 behind `mac_slot.py light-ok`.
The probe script is at /private/tmp/claude-501/-Users-javrodher-glitch/5da39513-9adc-4587-8d29-3722641cf776/scratchpad/l2a/probe.py.

## Findings

### 1. MAJOR: a ruling can re-run an aborted take whose cause is a counter rise the agent can produce

`batch.RERUN_FAULT_ROWS` includes `cgroup-kill`.
That row routes `aborted`, and its own source quotes the plan as "aborted ... never re-run".
The agent can raise the out-of-memory or pids counter itself, by allocating memory or forking without limit.
The table already counts that as the model's outcome: by glitch-b5's ruling 3, only harness-condition-violated makes it a harness fault.
So a take is stopped for some other reason (in the probe, an unlisted checker reason) while its counters rose.
The door then accepts `re-run` and `route harness-error`.
- Probe 2: `oom_kill_delta 1` plus an unlisted reason gives ACCEPTED for both re-run and harness-error.
- The same records without the unlisted reason route `('aborted', ['cgroup-kill'])`.

The publication check only refuses when the end state reads wrong.
An aborted take with a clean end state therefore leaves the denominator and gets a fresh try.
That turns an outcome that counts against holding into a re-run, by a ruling, for something the agent did.

The orchestrator's ruling 2 lists "a cgroup or pids counter rise" as a fault row, so this needs a new ruling, not a builder fix.
Recommended: take `cgroup-kill` out of `RERUN_FAULT_ROWS`, so that after the first turn a counter rise is ruled aborted (or graded).
Keep re-runs for an API error and a watcher gap only.
A harness-condition-violated reason already routes harness-error through its own row.

### 2. MAJOR: the door accepts re-runs that publication will refuse, and nothing can undo them

The door (`takes.validate_ruling`, which calls `history_problems`) never reads the end state.
`check_results.ruled_rerun_problems` reads it only in `run.produce`, after the re-run has been driven.
- Probe 4: an after-first-turn take with an API error and an unlisted reason gives `re-run` ACCEPTED at the door.
- Probe 4b: the same history, with an end state that reads wrong, is refused at publication.

`_ruling_problems` refuses a second ruling on a take ("ruled twice"), and the history is append-only.
So an honest operator who followed the door ends with a record set that cannot be published, and has no supported way back.
That also creates pressure to edit history after the freeze.
Integrity holds, because the check fails closed, but the round can be bricked.

Fix (cheap): at `takes.commit_ruling`, for an after-first-turn or unknown-phase take, run the same check on the committed take folder (`run.grade_committed`, then `grade_views(...)["excluded"]`) and refuse before writing.
Keep `ruled_rerun_problems` as the second check.

### 3. MINOR: a take with no records can in effect only be ruled aborted, and the door does not say so

When the drive raised after it started (`records None`, `ruled_phase` unknown), the door accepts every choice.
- Probe 10: re-run, rehearsal, pause and graded are all ACCEPTED.

At publication, re-run, rehearsal and pause need a grader reading that is not wrong, and a take that cannot be graded counts as wrong.
`graded` makes `produce` call `grade_committed`, which raises if the take folder is not committed.
- Inferred, not run end to end: for a driver crash with no committed evidence, `aborted` is the only ruling that can be published.
- So a harness crash would count against holding.

This is "fails closed" as ruled, but in the direction that charges the model, and the door gives no warning.
Recommended: decide it explicitly in the ruling rule (either aborted, or re-run when nothing was committed), and enforce that at the door (with finding 2).

### 4. MINOR: a pin mismatch after the first turn has no road to a re-run

`Batch._route` blocks a take whose driver pin differs from the registered profile.
That is a fault on the harness side by construction, because the agent never writes `records.pin`.
After the first turn the door now refuses re-run and harness-error for it.
- Probe 3 and 3b: both REFUSED.

So the take has to be graded into the cell under the wrong pin, or aborted against holding.
Recommended: treat a recorded pin mismatch as a harness fault at the door (beside `RERUN_FAULT_ROWS`), or name the case in the ruling rule.

### 5. NIT: `agent_event_rows` accepts any graded after-first-turn row

Widening it to a harness-error row is refused.
- Probe 8: `api-error-after-first-turn` is refused.

Widening it to `end-turn` passes `check_table`.
- Probe 8b: `[]`.

This hides nothing.
Such a table edit also changes routing.sha256 in the draft, and `stats.AGENT_EVENTS` is bound to the ids by the lane's test, so it cannot pass silently.
A closed allow-list in `_agent_event_problems` would make the check say what it means.

### 6. NIT: two items the fold plan gives to L2a or L4 are not built here, and nothing tracks them

- A process left alive at the cap together with a watcher queue overflow (which the agent can provoke) routes harness-error by `watcher-gap`.
  Probe 7: `('harness-error', ['watcher-gap'])`.
  The source of `agent_event_rows` says this road is owed a line in box_residuals, but nothing tracks that debt, so L4 must carry it.
- The fold plan's L2a scope also listed m16 (the probes4 dispatch).
  This lane's brief and diff do not touch it, and it must land before L5.

## Checked and holding

- **Fault row taken from another take:** refused.
  Probe 1: a re-run of s1 with the API error on s2 is refused.
  `taken` is keyed by the ruling's own (slot, attempt).
- **Pause or harness-error used to dress up a re-run:** both are in `RERUNNING_ROUTES` and are gated the same as re-run.
  `test_pf1` already covers "after, no harness fault, pause/harness-error".
- **Rulings with an empty why or cite, a whitespace why, a None why or a missing key:** refused (lane test P8).
  The door's CLI passes `--why` and `--cite` through.
- **Re-run that also names a route:** refused (probe 6).
- **Condition outside PROOF_CONDITIONS:** `no_match_problems` refuses it (probe 9).
- **routing.py --check on the Mac:** 22 rows, 21 no-match classes in 4 (phase, end) pairs, each with its default.
- **No-match defaults:** binding at the door through `ruling_rule_problems` (lane test P17).
- **Record fields:** `agent_events` and `ruled` are appended after `views`, so `TAKE_FIELDS[:8]` is unchanged.
  It is read by run.py, check_results.py, takes.py:361 and drive.py:4235.
  No committed JSON holds take records.
- **READER_SOURCES:** none of the nine files is in the diff.
  drive.py and vendor_provenance.py are untouched.
- **Pinned walk grades:** outside routing.json and this lane's COPIED.d entry, no committed data names the two re-routed rows.
  The battery's `run.py --walks --check`, `walk_register.py --check` and `build_draft.py --check` passed.
- **Cap-row comment (e5f7ea44):** a one-line change in place, so no line moved.
- **Battery cause C:**
  - The log has 6 test_pipeline errors, each "take record keys: missing ['agent_events', 'ruled']".
  - 5afd80a7's `take_record` now builds `TAKE_FIELDS[:8]` plus route, cell_state, label, views, agent_events and ruled, which is exactly `stats.TAKE_FIELDS`.
  - Run on the Mac at 5afd80a7: test_pipeline 88 run, 0 failures, 0 errors; test_pf1_routing_rulings 12 OK.
  - I did not re-run test_round4.
    Its 6 errors are attributed to the same fixture by the commit message.
    The log shows its failures as rounds.json (cause A), and I could not see its error lines in the truncated log.
- **The other 12 reds:**
  - Cause A, rounds.json unclaimed: freeze_shapes ×3, freeze --check ×3, copy_manifest ×3, and test_round4's failures.
  - Cause B, prefreeze-1.md not committed: rounds.py ×2.

## Not verified

- I did not check whether the agent can make a later turn's init event differ (the config folder can be written by the agent, MAJOR 7).
  If it can, init-mismatch is another road from the agent to harness-error.
  That belongs to lane L3.
