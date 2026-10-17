# T4 plan: vendor check readers for arms O (Codex) and G (Gemini)

Read-only design note for glitch-b5's ruling; nothing here is built, and T4 builds only after that ruling.
Written by the cloud executor of lane vendor-admission on Sat 17 Oct 2026, on Javier's typed word "vendor-t4: yes" (about 08:57 EDT).
Code was read at harness head fb830f31 (branch codex/gap4-live-harness-20261013, T0 and the walk-runner fix in it); `D/` is evals/gap-study-4/, and every line number is at fb830f31.
Classes used below: AS IS (applies as is), READER (applies with a vendor reader, which it names), BYTES (cannot be checked without real bytes, naming the walk evidence that settles it), N/A (does not apply, with why).
A BYTES item is never a pass: until its reader exists the vendor checker emits that item's existing reason id with a "no vendor reader yet" sentence, as prompt_snapshot_present's refusal does (D/check_take.py:1777).

## 1. Every reason, classified for codex and gemini

### 1a. The round-3 check() body (D/check_take.py:1566-1782)
- check:1580 readers-disagree (two user-turn counts): codex READER, the envelope's operator events (vendor_record_binding.bound_items, one per envelope from `sent`) against the ledger's turn rows; gemini READER, the same plus bound_items' native operator-record match (D/vendor_record_binding.py:131-139).
- check:1585 unknown-harness-origin: codex READER for the exec stream (transcript_codex's closed tables refuse an unknown record) and BYTES for harness-injected user content in the rollout, settled by a recorded rollout's response_item user records; gemini BYTES, settled by a recorded stream showing whether the CLI ever writes a non-operator user record.
- check:1593 no-first-agent-turn: both READER, an agent-text or tool-call event in the bound view (the adapters' agent_output rule, D/codex_adapter.py:37-38, D/gemini_adapter.py:39-40).
- check:1600 no-session-id: both READER, the envelope's `session_id` (the driver's) and `vendor_session_id` (section 2).
- check:1606 script-not-a-list: both AS IS (it reads the design view only).
- required_steps:1048 and 1079 stop-without-a-wait-point: both READER, the per-turn agent-text events of the bound view (turn k = envelope k) in place of tx.load's turns.
- required_steps:1060 and 1068 stop-at-held-marker: both READER, the same per-turn agent text.
- operator_line_problems:1115-1140 operator-lines: both READER for the comparison (it takes a list of lines, so it is reused as is on the envelope's operator events); codex BYTES for an independent read of the sent line, because exec's stream carries none (D/transcript_codex.py:35-36), settled by the registered rollout reader's UserMessage on a recorded walk.
- continuation_problems:1265-1274 continued-past-unheld-marker: both READER, the same turn list built from the bound view.
- fixture_binding_problems:1301-1337 fixture-binding: both AS IS (it reads driver-ledger.json, which the driver writes for every harness).
- check:1629 leak-in-operator-turn: both READER, the envelope's operator events, then the same leak_words test.
- check:1636 leak-in-loaded-context: both BYTES; context_text reads Claude Code attachment records (D/check_take.py:120-144), and where AGENTS.md text (codex) or GEMINI.md text (gemini) and environment context land is in no documented table; settled by a recorded rollout (codex) and a recorded session file (gemini) on the acceptance walk.
- check:1644 inherited-context (inherited_context): both READER for the working directory (the launch journal's actual-launch cwd, vendor_provenance.launch_facts, D/vendor_provenance.py:48-84), extra directories (the journal's argv) and tool servers (the per-take config bytes, vendor_provenance.pinned_files source "per-take-config"); both BYTES for the list of instruction files the CLI loaded, settled as for 1636.
- published_email_problems:714 account-email: both N/A as written (it reads Claude Code's session_context.userEmail, which no documented vendor record carries); whether a vendor stream carries any account identity is BYTES, settled by the sidecar scan over a recorded walk's retained streams.
- completion_problems:833-890 outcome-binding: both AS IS for the ledger legs (outcome vocabulary, exit codes); both READER for the "ended at the end of a turn" leg, codex turn.completed without turn.failed, gemini one result with status success (the adapters' end_reason rules).
- check:1662, 1668, 1672 outcome-binding (ledger turn rows against the script): both AS IS.
- check:1677 fixture-binding (ledger source): both AS IS.
- check:1682 study-materials-reached: both READER, the view's tool-call args (shell command, read/write/edit path, search pattern) and tool-result text; codex mcp_tool_call args map to `other {}` and are dropped by the view, so a vendor checker refuses any `other` call it cannot read (no tool server is configured in a take).
- check:1691 read-outside-the-checkout (outside_checkout_reads, outside_home_reads, outside_temp_reads): both READER over the same view strings; both BYTES for the CLI's own temp and home paths that legitimately appear in tool output (outside_temp_reads masks Claude's `/claude-N/` folder only, D/check_take.py:539), settled by a recorded walk's tool results.
- check:1699 project-name: both READER, the envelope's operator events against neutral_name of the driver's session id.
- check:1706 and 1748 invocation: both AS IS.
- check:1753, 1757, 1761 session-binding (row exists, row is this task/half, row committed): both AS IS (takes ledger only).
- check:1766 session-binding (sid equals uuid5 of the row commit): both READER, the envelope and ledger `session_id` (the driver's identity, D/drive.py:1145), plus the vendor-id binding of section 2.
- environment_problems:1395 environment-record: both READER once a ruled vendor block exists; the record is the driver's for every harness, but CHECKER_CONSTANTS' variable lists and credential_source_key name Anthropic variables only, and the adapters name each vendor's billing-route variables PENDING (D/codex_adapter.py:53-54, D/gemini_adapter.py:58-59).
- model_problems:761 model-binding: codex READER on the rollout's turn_context.model through the registered native reader (vendor_provenance.session_facts) plus codex_native.reroute_of; gemini READER on init.model and every key of result.stats.models, re-read by the checker rather than trusted from the adapter.
- constant_problems:898, 904, 908, 913 constant-binding: both AS IS once routing.json pins arms O and G (until then mode_for_arm returns _Unpinned and the take refuses, which is fail-closed).
- checkout_problems:1166 and 1173 checkout-binding: both BYTES; it reads Claude Code's session_context git status, and no documented vendor record shows the checkout's git state; settled by a recorded walk showing whether the rollout's environment context or Gemini's session file records it, failing which the ruling names the driver's own checkout record as the source.
- instruction_content_problems:1203-1218 and pinned_instruction_problems:2267-2280 checkout-binding: both N/A as written (they bind CLAUDE.md files a vendor does not load); the vendor analogue is READER, vendor_provenance.pinned_files source "pinned-instructions", and which files each CLI loads is BYTES as for 1636.
- check:1777 inherited-context (no prompt snapshot): both N/A as written (neither documented stream records a system prompt); replaced by the per-take config's pinned bytes (READER, pinned_files "per-take-config").
- check:1780 inherited-context (memory folder offered): codex N/A as written (no documented memory feature), with the config bytes pinned as above; gemini READER, the per-take config's memory file pinned empty, plus BYTES for whether its memory tool maps to a view tool kind, settled by a recorded stream.

### 1b. The round-4 checks (check4, D/check_take.py:1918-2013; check4_walk, 2384-2449; check_walk, 2327-2381)
- check4 and check4_walk CheckRefused lines (script, Design, half, pending, task/half, script match, run tree, event ids): both AS IS (design view only).
- check_walk:2343 session-binding (walk session id): both READER, the envelope's `session_id` against walk_session_id.
- check_walk:2348, 2352, 2355, 2358 session-binding (ledger present, task/half, ledger session, no row): both AS IS (ledger only).
- check_walk:2366 environment-record (row on a walk's record): both AS IS.
- check_walk:2371 session-binding (no model in the ledger): both AS IS.
- check_walk:2376 and 2379 inherited-context: as check:1777 and 1780.
- recorded_mode_problems:1900 constant-binding: codex READER on the rollout's turn_context.approval_policy through the registered reader, and BYTES for how the pin's "bypass" spells there, settled by a recorded rollout; gemini BYTES with no session source (the stream records no mode, Q-w11b-2), so the only reader is the launch journal's submitted argv, and whether that is enough is a ruling.
- check4:1967 and check4_walk:2426 constant-binding (ledger arm): both AS IS.
- design_tree_problems:2299 readers-disagree: both READER, the launch journal's cwd; codex also the rollout's cwd once recorded (BYTES).
- ledger_budget_problems:2466 and 2469 constant-binding: both AS IS.
- event_counts (study, email, outside; D/check_take.py:1910-1915): both READER, and the vendor counts must come from the same vendor readers as the vendor reasons, so check4's "check() and its reader disagree" invariant still holds.
- steer_condition_problems harness-condition-violated (D/check_take.py:2715-2738): both N/A (Claude Code's switches and auto_mode attachment; no documented vendor analogue).
- denied_tool_problems harness-condition-violated (D/check_take.py:2740-2818): both N/A as written (Claude Code's deny list and crossSessionInbound); the vendor analogue is READER on the pinned per-take config, and the tool set the CLI really offers is BYTES, settled by a recorded walk.
- transcript_line_problems:2878 and 2889 transcript-unreadable: both READER, bound_items' ViewError on any off-table line; note vendor_shell_commands only counts unread lines (D/check_take.py:3495-3520), so the checker must refuse a nonzero count on a completed take.
- subagent_file_line_problems:3046 and 3049 transcript-unreadable and subagent_problems:3063-3176 subagent-records: codex READER, collab_tool_call is off transcript_codex's tables, so delegation refuses; gemini BYTES, settled by a recorded walk showing its sub-agent chats; until then any delegate event refuses (transcript_view.DELEGATED_REFUSAL).
- subagent_leak_problems:3292 and 3297 leak-in-loaded-context, and subagent_reach_problems: both N/A while delegation refuses.
- command_problems:3473 and 3477 nested-agent: both READER, command_problems(vendor_shell_commands(folder, harness), harness), as the drive already runs it (D/drive.py:3326-3341).
- session_store_problems:3702-3732 nested-agent: both READER, but not as is: its closed shape is {harness, root, listings, sweeps} with harness claude-code (D/check_take.py:3706-3711), while the vendor doc adds nested_cli_calls and unread_stream_lines (D/drive.py:2623-2627), so T4 adds a vendor shape that re-derives vendor_store_violations and sweep_violations.
- session_store, own session: the drive's take.native_rel is not written to session-store.json (D/drive.py:2516, 2620-2627), so the checker must derive it from the vendor id and the listing, or the drive must record it (a READER_SOURCES edit; section 6).

## 2. Session binding when vendors mint their own ids
- Codex mints the thread id at turn 1 (D/codex_adapter.py:22-24) and Gemini mints the session id at turn 1 (D/gemini_adapter.py:23-25); neither id can be derived from a row commit or a walk id.
- Option (a): the take's identity stays the driver's uuid5 (`session_id` in the ledger and in every envelope); the vendor id is a bound alias, checked as one id across all envelopes, equal to the one id in each native stream (bound_items already does both), and equal to the native session file the store listing admits.
- Option (b): derive the project name and binding from the vendor id; refused, because the run tree and its project name exist before turn 1 mints the id.
- Option (c): impose the id; not available, because neither documented CLI accepts a caller-chosen session id.
- Option (d): a separate mapping record; it adds a record that says what the envelope already says.
- Recommendation: (a), with the checker reading the vendor id only from bound bytes (envelope, native stream, store listing), never from the adapter's own report.

## 3. Leaks, reach, operator lines, model and inherited context per vendor
- Leaks, codex: operator-turn leaks READER (envelope lines); loaded-context leaks BYTES (rollout instruction and environment records).
- Leaks, gemini: operator-turn leaks READER (envelope lines, matched by the native operator record); loaded-context leaks BYTES (GEMINI.md text is not in stream-json).
- Reach, codex: READER over command_execution commands and output and file_change paths; mcp_tool_call refused as unreadable.
- Reach, gemini: READER over tool_use args and tool_result text through GeminiParser's mapping.
- Operator lines, codex: READER on the envelope, with the independent read owed to the rollout reader (BYTES).
- Operator lines, gemini: READER on the envelope plus the native operator record.
- Model, codex: READER on the registered rollout reader and the reroute record; exec JSON carries none (D8:168).
- Model, gemini: READER on init.model and result.stats.models.
- Inherited context, both: READER for cwd, argv and per-take config bytes; BYTES for which instruction files were loaded and what entered the context.

## 4. How T4 meets T0
- T0 is in fb830f31: design_view admits codex and gemini rows (HARNESSES_WITH_SCRIPTS, D/check_take.py:2020, 2163-2166); check4 and check4_walk keep harness_guard (1933, 2394).
- T4 needs T0 (the vendor checker reads design.script and design.run_tree) and does not touch design_view.
- Option (A), admit in place: HARNESSES_WITH_READERS gains codex and gemini, and check4 and check4_walk dispatch to the vendor body right after harness_guard.
- (A) touches three R5 regions: the `HARNESSES_WITH_READERS = (CLAUDE_CODE,)` line, which is the start anchor of the "harnesses-with-scripts" span (that span must be re-anchored), plus a new span inside check4 and one inside check4_walk (harness_guard occurs twice, so both need two-line anchors).
- (A) moves assertions by ruling: test_vendor_script's test_v0_every_checker_entry_still_refuses_a_vendor_take and its two check4 witnesses, test_checker_body's r4_guard (tests/test_checker_body.py:458), its no-harness-guard witness (701) and the docstring at line 38.
- Option (B), appended vendor entry: check4 and check4_walk stay Claude-only and unchanged; T4 appends check4_vendor and check4_walk_vendor with their own VENDOR_HARNESSES_WITH_READERS guard; take_checker calls one appended dispatcher, check_take.checker_for(design).
- (B) touches no R5 region and moves no assertion (V0's "check4 refuses a vendor take" stays true), and costs one drive.py edit that must land before Javier's acceptance commit.
- Recommendation: (B), with that drive.py edit folded into the T0-review fix below, so every later vendor-reader change lands in check_take.py, outside READER_SOURCES and CODEX_SOURCES.
- T0-review item 1: routing.json's pin_profiles hold claude-code only, so walk_builders' pin_for (D/walk_builders.py:939-940) raises KeyError at batch.expected_pin (D/batch.py:418) for an O or G row; registering O and G profiles is CP5's (pin_profiles_status says they follow the rate-limit and spend-cap rules), and before then pin_for should refuse by name, which is a walk_builders.py change for its own ruling.
- T0-review item 2: take_checker reads the vendor envelope with Claude readers (no_output_nudges and agent_summary, D/drive.py:3603-3604) before check4 reaches harness_guard (D/drive.py:3601-3610).
- Fix before acceptance: take_checker calls check_take.harness_guard (or, under (B), the dispatcher's guard) on design.harness immediately after design_for and before any transcript read, and the side readings move behind a check_take function dispatched by harness.
- That fix is a drive.py edit (READER_SOURCES and CODEX_SOURCES), so it is red-first (a vendor take through take_checker refuses with the two readers patched to raise), ruled, and committed before Javier's acceptance records.

## 5. Fixture plan, documented shapes only
- Every fixture is synthetic and labelled DOCUMENTED in its name and its header comment, and a test asserts each adapter's SHAPES_SOURCE is "documented" while any fixture carries that label (ruling Q-3 precedent).
- Fixture F1, DOCUMENTED: a codex take folder (envelope transcript.jsonl, driver-ledger.json, turn-N exec streams with matching sha256, launch journals, session-store.json, environment.json), built from test_pending_codex_walk's generators.
- Fixture F2, DOCUMENTED: the same for gemini, built from test_pending_walk's accepted Gemini walk.
- Fixtures F3, DOCUMENTED: one variant per READER reason above that makes exactly that reason fire, and one per BYTES item showing its "no vendor reader yet" refusal.
- Fixture F4, DOCUMENTED: a walk folder per vendor for check4_walk_vendor (walk_session_id, no row).
- Re-test on recorded bytes before the freeze: every vendor reader on the acceptance walk's retained streams and rollout or session file.
- Also re-test: the BYTES items of section 1 (context records, git state, mode spelling, temp paths, delegation, account identity).
- Also re-test: vendor_store_violations and native_snapshot's stated assumptions (D/native_snapshot.py:16-18), Codex exec options before `resume` (D/codex_adapter.py:29) and Gemini `-r`.
- The freeze already refuses arms O and G while SHAPES_SOURCE is "documented" (T3), so no documented-only reader can reach a frozen order.

## 6. Files, tests, mutants, claims and the sources hazard
- P0 (pre-acceptance, ruled): D/drive.py take_checker guard-first plus the dispatcher call; test tests/test_vendor_check_road.py, red first; mutant: the guard line removed goes red.
- P1: D/check_take.py appended section "T4 VENDOR READERS" above `if __name__`, no line above it changed (R5's prefix rule holds); vendor_view(path, harness) over transcript_view.events on a BoundTranscript, ViewError mapped to transcript-unreadable.
- P1 tests: tests/test_vendor_check.py, red first on F1 and F2; mutants: ViewError swallowed, and an empty view read as clean, each go red.
- P2: check_vendor body for the AS IS and READER reasons, reusing the pure helpers (operator_line_problems, continuation_problems, fixture_binding_problems, constant_problems, ledger_budget_problems, context_leaks, command_problems, vendor_store_violations, sweep_violations).
- P2 tests: one F3 case per reason; mutants: each reason's guard deleted goes red, and each BYTES refusal deleted goes red.
- P3: check4_vendor and check4_walk_vendor (option B), the same CheckRefused preamble as check4 and the same event-count invariant; mutants: the guard, the invariant and the arm binding each dropped go red.
- P4: vendor session-store shape and own-session derivation; mutant: an extra listing entry admitted goes red.
- P5: vendor model, mode and environment readers; vendor constants appended as VENDOR_CHECKER_CONSTANTS, never edited into CHECKER_CONSTANTS (its region is pinned), with design_constants_sha256's coverage of it named in the ruling.
- P5 mutants: model mismatch admitted, and a PENDING billing-route variable defaulted, each go red.
- Claims: COPIED.d/vendor-admission.json claims the new test modules; checks.d/vendor-admission.txt runs them; check_take.py's departure is recorded where its owning lane records them (w10-walk-runner), and drive.py's in its owner's record.
- READER_SOURCES and CODEX_SOURCES: T4 edits none of them except P0's drive.py edit, which must be ruled and land before acceptance; transcript_view.py, vendor_record_binding.py and vendor_provenance.py are called, never edited.
- Hazard noted for glitch-b5, not T4's to change: transcript_codex.py, which bound_items uses to parse codex envelopes, is in neither READER_SOURCES nor CODEX_SOURCES (D/native_reader_registration.py:85-87, 160-161).
- Flag carried, not changed: pending_walk.coverage_status counts a pending walk superseded by a verified graded-true regrade with no checker reading (D/pending_walk.py:70-90); once T4 exists the ruling can require a vendor checker reading on the regrade road.

## 7. Size per piece (agent-hours, from this lane's measured rounds)
- Basis: T1-T3 took about 15 minutes of agent time in all, and each review fold about 10 minutes.
- P0 drive.py guard and dispatcher: 0.25 h build, 0.15 h fold.
- P1 vendor view: 0.25 h build, 0.15 h fold.
- P2 vendor check body: 0.75 h build, 0.25 h fold (largest: about 30 reasons and their fixtures).
- P3 vendor check4 entries: 0.25 h build, 0.15 h fold.
- P4 session store: 0.25 h build, 0.15 h fold.
- P5 model, mode and environment: 0.5 h build, 0.15 h fold, after the vendor-constants ruling.
- Fixtures F1-F4: 0.5 h, shared across pieces.
- Total: about 3 h build and about 1 h of folds; the brief's 16-30 h was a static guess before these rounds were measured.
- After the walks (not cloud): the BYTES items and the re-tests of section 5, sized when the recorded bytes exist.

## Rulings asked of glitch-b5
- R-1: option (B) of section 4, or (A) with its named region and assertion moves.
- R-2: session binding option (a).
- R-3: P0's drive.py edit (guard-first and dispatcher) before Javier's acceptance commit.
- R-4: the pin_for KeyError fix and who registers O and G pin profiles.
- R-5: whether the launch journal's argv is acceptable as gemini's only permission-mode source.
- R-6: the vendor instruction-file question (AGENTS.md and GEMINI.md against the pinned tree's CLAUDE.md files) is a design question, not T4's to answer.
