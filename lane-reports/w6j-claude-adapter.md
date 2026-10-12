Status: review round 1 passed (W6J-close-1), fold done; to merge with wave 6
head: ea091e59 (code; round 1 reviewed e0a76110). Base d56f8708 (S6b's closed head on the wave 6 merge), branch gap4/w6j-claude-adapter, worktree /Users/javrodher/aegis-builds/gap4-w6j.

# Lane w6j-claude-adapter: Gap Study round 4, slice S6c, the drive loop's agent side

_Written Sun 11 Oct 2026 21:15 EDT (`date`) by the slice's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-1b under Javier's standing delegation. Spec: plans/gap-study-round-4/s6b-checker-body-plan-2026-10-11.md (C6-C8, C13-C15, rulings D1-D8, the S6b hand-back rulings), w6i-review-r1-2026-10-11.md (W6I-R1-5, W6I-R2-1..3, Q-w6i-3)._

No image or container was built or run.
No model was run, no API was called, and no test used a network.
No login, `.env`, sealed, holdout, brief or saved-output path was read.
Nothing was pushed, merged or dispatched.

## Commits

| sha | stage |
|---|---|
| ae53ae2f | 1: carried W6I-R2-1, W6I-R2-2, W6I-R2-3; ownership transfer S6c-gap4-1 |
| 30bdf02b | 2: the Claude Code adapter (C15) |
| 5b31998a | 3: the marker / recovery / stop loop (C13) |
| 0661ed07 | 4: the cost read per call (C14) |
| e9cdf2db | 5: C6, C7, C8 written by the driver; the production checker callable |
| e0a76110 | 6: Q-w6i-3 and W6I-R1-5 |

## What each piece does, with its test

- `claude_code_adapter.py` (new). ClaudeCodeAdapter: one `docker exec` per turn through run_take.run_turn.
  The argv is round 3's one_turn with the plan's named changes for arms A and C: the routing pin's permission mode (a PENDING mode refuses the adapter), no `--allowedTools`, `--disallowedTools WebFetch WebSearch`, round 3's isolation flags, `--session-id` on the first turn and `--resume` after.
  The version comes from `claude --version` in its recorded form.
  read_stream reads only shapes recorded at harness 2.1.267: the committed haiku-prestudy stream-json probes, round 3's stream_split and stream_init_source, and the API-error probe. The harness's API-error record is never the agent's text or output.
  Tests A1-A4 in tests/test_claude_code_adapter.py.
- C13 in drive.py (`_Script`, `pause_evidence`): nothing is sent past an unheld marker (exact, case-sensitive: round 3's marker_holds).
  The recovery goes only when the reply holds the recovery's marker and not the step's, at most `at_most` times, on the same step n.
  The operator step (ruling D8) is keyed by the step's own n. Each line sent is one ledger row, and the outcome is round 3's vocabulary.
  The stop is classified by pause_adherence from the driver's rows, never by the driver. Tests D2-D6 in tests/test_drive_loop.py.
- C14: tokens once per (message.id, requestId) from the session file; total_cost_usd is the turn's printed figure; nothing is summed or derived. Test A5.
- C6, C7, C8 (drive.py `_environment`, `_take_records`): environment.json in round 3's schema before the first turn and again with each turn's credential source; the session file published through scrub.py and cross-checked with the streams; driver-ledger.json in round 3's schema binding environment.json's bytes, with the cost record and the cross-check. Test D7, through the real adapter on a fake box that writes a session file.
- The production wiring: claude_code_adapter_for, script_from_design, take_checker (check4 on the published transcript; readers-disagree when the readers disagree or no session file was written). Test D8 with the real check4 on the real design.
- Q-w6i-3: the adapter-open flag is set before start_take. Test D10.
- W6I-R1-5: R8-parser in test_checker_body re-runs R3 with agent_output from read_stream.
- W6I-R2-1: R7 drives a walk both ways; W6I-R2-2: the copy writes the hashed bytes (D1); W6I-R2-3: the w6i report's counts corrected.

## Measured (named for the reviewer)

A stream record's `message.usage.output_tokens` is the reply's start count: 3 and 4 against a result total of 286 on the haiku driver-argv probe.
The session file carries the final count (195 on the env-smoke turn), so C14 reads tokens from the session file.

## Red first, then green (Mac, `mac_slot.py light-ok`, `timeout -s INT 120`, Python 3.13.2 at /usr/local/bin/python3.13, `-B -W ignore`)

Every red used a byte backup, restored, `shasum -c` OK; each failed by assertion with 0 errors.
- D1 on the base drive.py: 1 run, 1 failure (the run tree held the table rewritten after the hash).
- test_claude_code_adapter with the module absent: 13 run, 12 failures.
- D2-D6 on stage 2's drive.py: 5 failures (the loop's names absent).
- A5 on stage 3's adapter: 1 failure (a call missing two classes read with None counts; costs.py refused it).
- D7, D8 on stage 4's drive.py: 2 failures (names absent).
- D10 on stage 5's drive.py: 1 failure (the adapter whose start raised was ended 0 times).
- R7's walk case and R8 have no behavioural red on their base (R7's rule was already folded; the parser existed since stage 2): their red is their witnesses.

Green at the stage-6 code head, each rc 0 ending in a bare OK: test_drive_loop 23 (13 witnesses), test_checker_body 26 (11), test_claude_code_adapter 17 (8), test_box_integration TestBoundChecks + guard + stub 22 and TestTheTakePath 17, test_check_take 15 (5), test_mode_binding 6 (1), test_drive_commit 31 (10); copy_manifest --check (252 files, 36 fragments), probes4 --check (1690 cells, 0 defects), build_draft --check, freeze --check, mode_binding --check; the check_take byte binding and w6e's drive.py prefix binding, rc 0.

New witnesses, each red by its own check, 0 collateral, 0 errors: table-reread, continued-past-unheld-marker, recovery-never-sent, recovery-unbounded, marker-casefold, abort-before-output, turn-ends-dropped, no-cross-check, session-raw, env-per-turn-dropped, cross-check-unrouted, missing-transcript-graded, open-after-start (drive.py); init-any-record, api-error-as-agent, allowed-tools-back, mode-constant, exit-ignored, count-records, missing-class-as-zero, zero-dollars-per-call, parser-blank-text (claude_code_adapter.py); walk-instructions-from-head (check_take.py).
All 21 S6/S6b drive.py witnesses, w6e's 10 and the check_take witnesses stay red with their earlier counts.

Not run on the Mac: the whole test_scaffold, test_pipeline and run_checks (athena's). test_round4 runs test_drive_loop beside test_box_integration and test_checker_body in one process; it imports both as helpers and calls test_box_integration's setUpModule itself, which athena's battery must confirm.

## Departures (for glitch-1b)

- w6j-1: test_scaffold's copied_modules also reads w6j's fragment (recorded in w1a's entry).
- w6j-2: test_box_integration.py moved to w6j; its rig passes the new identity_for, setUpModule fills run_take's PENDING FALLBACK_ENV with none for the fake runtime, DuckAdapter gains version().
- w6j-3: TakeDriver gains a required `identity_for` (session id, row, row commit, source, fixture record, gars tree): the fixture builder and the row registration are not built, so the driver is handed what they know.
- w6j-4: environment.json records the names the exec passes (run_take.exec_values and the login name); the image's own environment is preflight's record.
- w6j-5: script_for may return plain strings (a step with no marker) beside steps, so S6's and S6b's synthetic scripts run unchanged; the production road is script_from_design, which keeps markers.

## Questions for glitch-1b

- Q-w6j-1: "total_cost_usd per call": Claude Code prints it per exec (turn), not per API call; read as tokens per call, dollars per turn, never derived. Confirm.
- Q-w6j-2: the stream's `request_id` and the session file's `requestId` are assumed to name the same call: no paired recording exists. The cross-check refuses if they differ, so the first real walk (CP6) checks it.
- Q-w6j-3: a result record with is_error true is read as an API-error entry typed by its subtype; stderr is not read (round 3 found no rate limit there).
- Q-w6j-4: a stream-vs-session disagreement, or no session file, routes as readers-disagree (round 3's id, meaning widened to the two readers of one take).
- Q-w6j-5: the init's `tools` list is recorded per turn but not checked (routing checks model, mode and version only); the plan names tools.
- Q-w6j-6: reading the session file host-side under the user-namespace map (ownership) is CALLER_PENDING, measured at the stub take.

## Not built, and why

- The full end-to-end acceptance (a take through TakeDriver with the real check4, no spy, routing end-turn) is covered in two halves: D7 drives the real adapter and writes every record, D8 runs take_checker with the real check4. Joining them needs walk-measured constants whose environment_record equals the driver's published name patterns, and a fixture record from a fixture builder that is not built; both are CP6 inputs, not guessed here.
- The version-specific record shapes and the isMeta scan stay CP2 real-box / CP6 items (s6b plan, section 1).

## Fold of review round 1 (W6J-close-1, glitch-1b, 11 Oct)

Round 1 passed with no MAJOR (plans/gap-study-round-4/w6j-review-r1-2026-10-11.md). All four items are folded at ea091e59 (written 21:46 EDT, `date`).
- W6J-R1-1: a session file the cost reader refuses is a cross-check problem: cost None, readers-disagree from take_checker, and the take still reaches its ledger, scan and checker. D7 now covers one call written twice (output 3 then 286) and a usage record with no requestId. Witness cost-refusal-raises.
- W6J-R1-2: a session record whose sessionId is not a string is a cross-check problem, never a TypeError. A6; witness null-id-unreported.
- W6J-R1-3: _Script refuses steps not numbered exactly 1..k in order; TakeDriver's strict_script (True in the CP6 production wiring) refuses bare lines. D11; witnesses any-numbering, strict-ignored.
- W6J-R1-4: the result record's error branch and `error` key are named unevidenced in the adapter's docstring until CP6 records an error result.

Red first on e83910cf's bytes (byte backups restored, `shasum -c` OK), by assertion with 0 errors: D7 and D11 2 failures, A6 1 failure.
Green at ea091e59, each rc 0 with a bare OK: test_drive_loop 27 (16 witnesses), test_checker_body 26 (11), test_claude_code_adapter 19 (9), test_box_integration bound checks 22 and take path 17, test_check_take 15, test_mode_binding 6, test_drive_commit 31 (10); all 21 S6/S6b witnesses red with their counts; copy_manifest, probes4 (0 defects), build_draft, freeze, mode_binding checks; both binding lines.

RESUME HERE: hand-back at ea091e59; merge with wave6 (orchestrator)
