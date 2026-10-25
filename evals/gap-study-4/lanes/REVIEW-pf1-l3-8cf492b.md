VERDICT: CHANGES

# Closure check of lane pf1-l3-transcript-integrity at 8cf492b2 (after review fb354328)

Reviewer: the same independent session that wrote REVIEW-pf1-l3-fb35432.md, Sat 24 Oct 2026, 22:17 EDT (from `date`).
Read: `git log fb354328..8cf492b2` (ae6d0996 the review, 9a3b8c24 the fold, 8cf492b2 the cut tightening), checked against the lane orchestrator's rulings on review fb354328.
No code changed.
Probes ran on scratch copies in my scratchpad.

## What I ran (Mac, behind light-ok, python3.12, one module at a time)

- test_pf1_transcript_integrity: 35 tests OK.
- test_steer_condition: 7 OK.
- test_isolation_denials_checker: 9 OK.
- test_pf1_egress_probe: 12 OK.
- test_preflight: exit 0.
- routing.py --check: sound.
- After that, light-ok refused ("CPU speed limit 70 is below 80"), so test_pre_ruling_walks and test_auto_mode were read, not run (finding 1).
- athena-suites holds no run at 9a3b8c24 or 8cf492b2.

## Earlier findings: closed

| fb354328 finding | At 8cf492b2 |
|---|---|
| 1 MAJOR: a session-file auto_mode or deferred_tools_delta routes a forgery harness-error | Closed. Reply forged plus either record gives only `transcript-mismatch` (probe on w125). Host-side causes stay harness-condition-violated (T6 r1d). |
| 2 operator-line edit, junk line, sidechain record | Closed while the streams read: each gives `transcript-mismatch` (probes 6 and 7). The operator line is compared exactly with journal argv[2]. |
| 3 unreadable native store | Closed by the ruling. Rollout corrupted with no cut gives mismatch. A forged ledger cut alone gives mismatch. A stream terminal dropped alone gives mismatch. Ledger cut plus stream cut gives transcript-unreadable, the ruled w-g24 case. |
| 4 data-matched rules | Residual names the misfire cost. A stream command that does not split is now unreadable. |
| 5 empty inspect Gateway | Fails closed (`_inspect_gateways`). The live box run is still the freeze rehearsal's. |
| 6 IPv6, task-notification records | Both named in the residuals. |

Earlier probes re-run at 8cf492b2: all refusals as before.
The two that pass are unchanged: the edit made coherently in both the stream and the session file (residual (a)), and a Gemini object display swapped for another object, which no grader reads.

## Requested break attempts

- **Forged ledger cut.** The ledger (`end` timed-out) without a stream cut gives transcript-mismatch, and so does a stream cut without the ledger.
  Only both together keep transcript-unreadable.
  The ledger is host-written; I took that from the brief and did not trace its path.
  Exit 124 needs the real timeout to fire: a killed CLI exits with a signal status.
- **A harness condition in both the host records and the session file.** Harness-condition-violated from the journal or init wins by none_of and routes harness-error.
  That is correct under ruling 3, and the agent cannot write those records except by residual (a).
- **An operator-line edit that matches argv.** The comparison is exact string equality with argv[2], so an "edit" that matches is no edit.
  An extra or moved operator line is caught by the turn count or by the comparison.
- **An agent that runs past the budget.** On Codex or Gemini, overrunning plus breaking the native store gives transcript-unreadable and a re-run.
  This is ruled and named in residual (c) ("So an agent that runs its own turn past the budget ... has its take re-run").
  On claude-code, see finding 3.

## Findings

### 1. MAJOR: test_pre_ruling_walks goes red. Another lane's 25 recorded refusals now differ, and it was neither updated nor run.

- tests/fixtures/pre-ruling-walks-20261015.json records, for all 25 pre-ruling walks (w001-w031), an expected refusal that includes `[harness-condition-violated] a deferred_tools_delta adds ['RemoteTrigger', 'SendMessage'] ...`.
  Each kept transcript carries one such attachment.
- `replay_problems` requires `denied_tool_problems` to return exactly the recorded list.
  At 8cf492b2 that line is `[transcript-mismatch] a deferred_tools_delta in the transcript adds ...`, so `test_each_walk_is_an_expected_refusal_under_the_guard` fails.
- I found this by reading; I could not run it, because the Mac throttled.
- The routing does not move: those walks' journals deny nothing, so host harness-condition-violated is still present and the none_of keeps harness-error.
  But the record is a bound expectation of glitch-b5's ruling 4.
- It needs one of two things, stated as such: a re-recorded fixture with a COPIED.d entry under the new ruling, or a ruling that the record stays.
- Run the whole gate on athena before closure; the athena-suites folder shows no run since fb354328.
- These 25 walks are also the evidence that the CLI itself writes a denied-tool delta when a denial fails.
  The new line's words "which no host record offers" are false for them, because their journals also show the fault.
  That is a wording NIT once the fixture is settled.

### 2. MINOR: the pre-registered auto_mode departure text now says the opposite of the code

- prereg-draft.json, harness_furniture_ruling.departures[auto_mode], reads: "a take whose launch journals set the switch off and whose transcript still carries it refuses (harness-condition-violated, check_take.steer_condition_problems)".
- At 8cf492b2 that case emits transcript-mismatch.
- build_draft.py's source text was not updated.
- test_auto_mode asserts that the departure contains "harness-condition-violated", so a fix must change both.
  It could keep the word for the host leg and name transcript-mismatch for the session-only leg.
- The isolation-removals text, "a take whose stream init still offers one refuses (harness-condition-violated ...)", stays true.

### 3. MINOR: on claude-code, the content comparison has never been measured on a turn the budget cut

- Only one committed walk has a host-recorded cut: w-g24, which is Gemini.
- A genuine timed-out claude-code turn kills the CLI between its writes to the stream and to the session file.
  Inference: their tails can differ (a record flushed to one and not the other).
  That take would then route aborted (transcript-mismatch outranks the graded timed-out row), not graded timed-out.
- So for the agent the choice of label is made by kill timing, not by its behaviour.
- Name it, or compare a cut turn (host ledger cut and no `result` record) only up to the shorter side's last complete unit.

### 4. MINOR: an agent can still re-run its claude-code take by printing one character

- Claude Code's JSON.stringify leaves U+2028, U+2029 and U+0085 raw.
  That is glitch-b5's r8 ruling text; that the stream writer behaves the same way is my inference.
- So a Bash output carrying one of them puts a raw separator in both the stream and the session file.
- Probe (w125, U+2028 in one tool_result, in both files): `_host_readable` is False, so the junk, separator and sidechain checks switch off.
  `transcript_line_problems` gives `[transcript-unreadable]` alone, which routes harness-error and re-runs the take.
  Adding a junk session line gives the same.
  A content forgery beside it is still caught (aborted).
- This is a void road chosen by the agent's own output, which the new ruling's spirit excludes.
  Residual (c) mentions it only as "a host record that does not read".
- Fix or name it, with a ruling, since it touches r8:
  - The stream line still parses when split on newline alone, so `_host_readable` could test JSON per line only.
  - A separator that both files carry in the same unit could be read rather than refused.

### 5. NIT: `_host_recorded_cuts` maps ledger rows to turns by position, not by the row's `n`

It is correct while the driver writes one row per turn in order.
Reading `n` would be the producer-bound form.

## Flipped expectations in other lanes' tests (all follow from the ruling, none weaker)

- **test_steer_condition S-violated:** an auto_mode record with every journal off now expects one `[transcript-mismatch]` naming "2 auto_mode", routable by its id.
  It is the same count check and the same single line; only the id moves.
- **test_isolation_denials_checker D-delta:** a delta adding each denied tool expects `transcript-mismatch` with the tool named.
  Same strength.
- **test_isolation_denials_checker D-shape, delta leg:** CheckRefused (a stop for a human) becomes `transcript-mismatch` with "not a list".
  This follows "nothing only the session file shows routes harness-error or rehearsal".
  The init leg still raises CheckRefused, because the init is host evidence.
- **test_checker_body:** the fixture's journal prompt is now the operator line the turn sent.
  That is fixture follow-through, as run_take records it.
- **Not flipped and now stale:** test_pre_ruling_walks (finding 1) and the test_auto_mode text binding (finding 2).
