# T4 plan v2: vendor check readers for arms O (Codex) and G (Gemini)

Read-only design note for glitch-b5's ruling; nothing here is built, and T4 builds only after that ruling.
v1 was written Sat 17 Oct 2026 on Javier's typed word "vendor-t4: yes" (about 08:57 EDT) and reviewed NOT READY (REVIEW-vendor-T4-PLAN-52d653f: 5 MAJOR, 6 MINOR).
v2 folds that review under glitch-b5's rulings of Sat 17 Oct 2026, 10:25 EDT; section 12 maps each finding to where it landed.
Code was read at harness head fb830f31 (branch codex/gap4-live-harness-20261013); `D/` is evals/gap-study-4/, and every line number is at fb830f31.

PRINCIPLE (glitch-b5, governing every section): the Gap Study compares models, so a GPT or Gemini take is checked at least as strictly as a Claude Code take on every check.
Where this plan cannot match a check for a vendor, section 3's table says so, that check is NOT COMPARABLE for that arm, and the study publishes it as such; nothing is silently weaker.
A check whose only source would be the driver's own record is never a pass: it holds the take pending (refused under its existing reason id with "no vendor reader yet", as D/check_take.py:1777 does) until an independent reader exists or a ruling marks it NOT COMPARABLE.

The brief's four classes, as used in section 1: AS IS = APPLIES AS IS; READER = APPLIES WITH A VENDOR READER (the reader is named); BYTES = CANNOT BE CHECKED WITHOUT REAL BYTES (the walk evidence that settles it is named; until then the take is held pending, never passed); N/A = DOES NOT APPLY (why is given).
Section 3's comparability classes: SAME (the vendor check reads CLI-written bytes for the same fact, at least as strictly), PENDING (BYTES: held pending until recorded bytes settle it as SAME or, by ruling, NOT COMPARABLE), NOT COMPARABLE (known now to be weaker or different for that arm; any partial check still runs and must pass, and the study publishes the check as NOT COMPARABLE for that arm).

## 1. Every reason, classified for codex and gemini

### 1a. The round-3 check() body (D/check_take.py:1566-1782)
- check:1580 readers-disagree (operator turns): codex READER, a real comparison of two independent records: the CLI-written rollout's per-turn UserMessage text (codex_native.read_rollout's turns[k]["sent"], D/codex_native.py:159-162, 191, 276) against envelope k's and ledger turn k's `sent`, count and text, per ordinal.
- That codex comparison is new: bound_items forces envelope and ledger equal (D/vendor_record_binding.py:99-104) and codex_join_session never compares `sent` (D/native_reader_registration.py:178-207), so the v1 envelope-against-ledger reading could never fire and is withdrawn.
- check:1580 readers-disagree, gemini READER: the vendor checker's own comparison, run before the view, of each stream's user record (gemini_stream_join's call["sent"], D/gemini_stream_join.py:57-72) and of the native snapshot's interaction `sent` (gemini_projection via the registered reader) against envelope k's `sent`; a mismatch carries readers-disagree.
- bound_items' own gemini operator-record refusal (D/vendor_record_binding.py:138-139) stays as a backstop and surfaces as transcript-unreadable (its ViewError), never as a pass.
- check:1585 unknown-harness-origin: codex BYTES for user or developer text the CLI injects as rollout response_item messages, which read_rollout skips unread (D/codex_native.py:230-233), settled by a recorded rollout's response_item message records; until then a codex take is held pending on this leg.
- check:1585, gemini READER: a non-operator user message in the native snapshot is an extra interaction or a `sent` mismatch, which join_session refuses (D/native_reader_registration.py:123-148) and take_checker turns into readers-disagree (D/drive.py:3612-3613); BYTES for whether 0.64.0 ever writes one, settled by a recorded snapshot.
- check:1593 no-first-agent-turn: both READER, an agent-text or tool-call event in the bound view (D/codex_adapter.py:37-38, D/gemini_adapter.py:39-40).
- check:1600 no-session-id: both READER, the envelope's `session_id` (the driver's) and `vendor_session_id`, each bound as section 2 says.
- check:1606 script-not-a-list: both AS IS (design view only).
- required_steps:1048 and 1079 stop-without-a-wait-point: both READER, the per-turn agent-text events of the bound view (turn k = envelope k).
- required_steps:1060 and 1068 stop-at-held-marker: both READER, the same per-turn agent text.
- operator_line_problems:1115-1140 operator-lines: both READER, reused as is on the envelope's lines, which the readers-disagree comparison above has already bound to the CLI-written record of each turn (rollout for codex, stream and snapshot for gemini).
- continuation_problems:1265-1274 continued-past-unheld-marker: both READER, the same turn list.
- fixture_binding_problems:1301-1337 fixture-binding: both AS IS (driver-ledger.json, which the driver writes for every harness, Claude Code included).
- check:1629 leak-in-operator-turn: both READER, the envelope's lines (bound as above), then the same leak_words test.
- check:1636 leak-in-loaded-context: both BYTES; context_text reads Claude Code attachment records (D/check_take.py:120-144); settled by a recorded rollout's response_item instruction and environment messages (codex) and a recorded snapshot or stream showing GEMINI.md text (gemini), and by ruling R-6 on which instruction files each CLI is pointed at.
- check:1644 inherited-context: both READER for extra directories (the launch journal's argv) and tool servers (the per-take config bytes, pinned_files "per-take-config"), each input-side (section 3); codex READER for the working directory on the rollout's turn_context.cwd (D/codex_native.py:236-240); gemini BYTES for it (the native cwd is None, D/gemini_projection.py:12-14), settled by a recorded snapshot or listing; both BYTES for the instruction files the CLI loaded.
- published_email_problems:714 account-email: both BYTES (review MINOR 6): until a recorded walk shows no account-identity field, EVENT_EMAIL for a vendor take is the count of the operator account's identity string in a sweep of every published vendor file (envelope, turn streams, retained snapshots), and that count is bounded by the sidecar scan's masked hits (D/drive.py:2883-2890); it becomes N/A only once the recorded walk shows no identity field.
- completion_problems:833-890 outcome-binding: both AS IS for the ledger legs; both READER for "ended at the end of a turn" (codex turn.completed without turn.failed, gemini one result with status success).
- check:1662, 1668, 1672 outcome-binding (ledger turn rows against the script): both AS IS.
- check:1677 fixture-binding (ledger source): both AS IS.
- check:1682 study-materials-reached: both READER on the raw native records, section 4 (not the view's mapped arguments).
- check:1691 read-outside-the-checkout (outside_checkout_reads, outside_home_reads, outside_temp_reads): both READER on the same raw records; no vendor temp or home path is masked until a recorded walk shows which the CLI itself prints (D/check_take.py:539 masks only Claude's `/claude-N/`), which errs strict, never lax.
- check:1699 project-name: both READER, the envelope's lines against neutral_name of the driver's session id.
- check:1706 and 1748 invocation: both AS IS.
- check:1753, 1757, 1761 session-binding (row exists, row is this task/half, row committed): both AS IS (ledger only, as for Claude Code).
- check:1766 session-binding (sid equals uuid5 of the row commit): both READER, the envelope and ledger `session_id` plus section 2's legs.
- environment_problems:1395 environment-record: both READER once a ruled vendor block exists (P5); the record is the driver's for every harness, Claude Code included; a vendor billing-route variable still PENDING (D/codex_adapter.py:53-54, D/gemini_adapter.py:58-59) refuses.
- model_problems:761 model-binding: codex READER on the rollout's turn_context.model (REQUESTED, D/native_reader_registration.py:165-167) plus the reroute item (the served model, seen only when rerouted, D/codex_native.py:84-106); gemini READER on init.model and every key of result.stats.models, re-read by the checker.
- constant_problems:898, 904, 908, 913 constant-binding: both AS IS once routing.json pins arms O and G (until then the take refuses).
- checkout_problems:1166 and 1173 checkout-binding: both BYTES; Claude Code's check reads the session's own git status and refuses when the session recorded none (D/check_take.py:1145-1166); the vendor leg refuses the same way until a recorded walk shows a session-side record of the checkout, and the driver's own checkout record is never its source (v1's fallback is withdrawn).
- instruction_content_problems:1203-1218 and pinned_instruction_problems:2267-2280 checkout-binding: both BYTES and blocked on R-6 (Javier's design ruling on which instruction file each CLI is pointed at); the leg refuses until then.
- check:1777 inherited-context (no prompt snapshot): both BYTES; neither documented stream records a system prompt, so the leg refuses until a recorded walk shows a session-side record; the per-take config's pinned bytes still run as an input-side leg.
- check:1780 inherited-context (memory folder offered): codex BYTES (no documented memory feature; settled by a recorded rollout showing none offered); gemini BYTES (the memory file pinned empty is input-side; whether the memory tool is offered is settled by a recorded stream).

### 1b. The round-4 checks (check4, D/check_take.py:1918-2013; check4_walk, 2384-2449; check_walk, 2327-2381)
- check4 and check4_walk CheckRefused lines (script, Design, half, pending, task/half, script match, run tree, event ids): both AS IS (design view only); so are check_walk's CheckRefused line (2336) and walk_session_id's (2323), which are refusals, not reasons.
- check_walk:2343 session-binding (walk session id): both READER, the envelope's `session_id` against walk_session_id, plus section 2's legs.
- check_walk:2348, 2352, 2355, 2358 session-binding: both AS IS (ledger only).
- check_walk:2366 environment-record: both AS IS.
- check_walk:2371 session-binding (no model in the ledger): both AS IS.
- check_walk:2376 and 2379 inherited-context: as check:1777 and 1780.
- recorded_mode_problems:1900 constant-binding: codex BYTES, the rollout's turn_context.approval_policy is carried raw and never accepted (D/codex_native.py:43-44), settled by a recorded rollout's spelling of the pin; gemini NOT COMPARABLE (no session-side mode record: the stream records none, Q-w11b-2, and the native mode is None), so the launch journal's argv is checked as submitted, plus a BYTES leg: any approval or confirmation event in a recorded stream refuses (R-5).
- check4:1967 and check4_walk:2426 constant-binding (ledger arm): both AS IS.
- design_tree_problems:2299 readers-disagree: codex READER on the rollout's turn_context.cwd against the run tree, with the launch journal's cwd as a second leg; gemini BYTES as check:1644's cwd.
- ledger_budget_problems:2466 and 2469 constant-binding: both AS IS.
- event_counts (study, email, outside; D/check_take.py:1910-1915): both READER from the same vendor readers as the vendor reasons, so check4's "check() and its reader disagree" invariant holds for the vendor entries too.
- steer_condition_problems harness-condition-violated (D/check_take.py:2715-2738): both N/A (Claude Code's switches and auto_mode attachment; no vendor analogue exists to be weaker than).
- denied_tool_problems harness-condition-violated (D/check_take.py:2740-2818): both BYTES for the tool set the CLI really offers (settled by a recorded walk's tool declarations); the pinned per-take config is an input-side leg that still runs.
- transcript_line_problems:2878 and 2889 transcript-unreadable: both READER, bound_items' ViewError on any off-table line, and a nonzero vendor_shell_commands unread count on a completed take refuses (D/check_take.py:3495-3520).
- subagent_file_line_problems:3046 and 3049, subagent_problems:3063-3176: both READER as a refusal: codex collab_tool_call is off transcript_codex's tables, and gemini has no DELEGATE mapping, so a gemini sub-agent tool refuses as an unknown tool name (map_tool's ViewError, D/transcript_gemini.py:96-107), not through DELEGATED_REFUSAL.
- subagent_leak_problems:3292 and 3297 and subagent_reach_problems: both N/A while delegation refuses (section 3 names what that means for the study).
- nested_agent_flag_problems (check4:1963, check4_walk:2423; body 3523-3525) nested-agent: both READER, command_problems over vendor_shell_commands(folder, harness), as D/drive.py:3326-3341 runs it.
- session_store_problems:3702-3732 nested-agent: both READER through a vendor shape (P4): the vendor doc's keys are {harness, root, listings, sweeps, nested_cli_calls, unread_stream_lines} (D/drive.py:2621-2627), and the checker re-derives vendor_store_violations and sweep_violations itself rather than trusting the driver's vendor_nested_problems verdict (D/drive.py:2629-2633).
- Own native session: the checker derives it (section 6), so no drive.py change records it.

## 2. Session binding when vendors mint their own ids
- Codex mints the thread id at turn 1 (D/codex_adapter.py:22-24) and Gemini mints the session id at turn 1 (D/gemini_adapter.py:23-25); neither can be derived from a row commit or a walk id, and neither CLI accepts a caller-chosen id.
- Option (b), the project name from the vendor id, is refused (the run tree is named before turn 1); option (c), an imposed id, is unavailable; option (d), a mapping record, restates the envelope.
- Recommendation, option (a): the take's identity stays the driver's uuid5 (`session_id` in the ledger and every envelope), and the vendor id is a bound alias read only from bound bytes, never from the adapter's report.
- Because the driver writes both the envelope and the ledger, option (a) passes only with all of these legs, each a refusal when it fails (review finding 3(e)):
- Leg 1, the launch journal for every ordinal: turn 1's argv resumes nothing (vendor_provenance FIRST_TURN, D/vendor_provenance.py:39, 59-60) and every later turn's argv resumes exactly the vendor id.
- Leg 2, one vendor id across every envelope, every turn stream's thread.started or init record, and the native snapshot (bound_items, D/vendor_record_binding.py:118-137; the snapshot's session id through the registered reader).
- Leg 3, CLI-written freshness: the last retained snapshot holds exactly one interaction per stream (join_session and codex_join_session refuse an extra one, D/native_reader_registration.py:123-148, 189-190), so a resumed earlier session, which carries earlier interactions, refuses.
- Leg 4, the store listing at every turn holds only that one session file (vendor_store_violations, D/check_take.py:3607-3630), the derived own session agreeing with the vendor id (section 6).
- With legs 1-4 the vendor binding rests on CLI-written bytes (legs 2-3) as Claude Code's does on its session file's imposed id, so section 3 rates it SAME.

## 3. Comparability table (one row per check; C = Claude Code, the reference)
| Check | C reads | Arm O (codex) | Arm G (gemini) | What the study publishes |
|---|---|---|---|---|
| readers-disagree, operator turns | two readers of the CLI session file | SAME: rollout UserMessage vs ledger, per ordinal | SAME: stream user record and snapshot `sent` vs ledger | comparable |
| unknown-harness-origin | non-operator user records in the session file | PENDING: rollout response_item messages unread | SAME via the join's interaction count and `sent` match (reason id readers-disagree) | comparable once O is settled |
| operator-lines, leak-in-operator-turn, project-name | the session file's user records | SAME (lines bound to the rollout) | SAME (lines bound to stream and snapshot) | comparable |
| reach: study-materials-reached, outside reads | every string of tool inputs and results in the session file | SAME on raw exec items and rollout CommandExecution items (section 4); file_change content PENDING (refused today) | SAME on raw stream tool records and snapshot toolCalls (section 4) | comparable; O's file edits refuse until settled |
| leak-in-loaded-context | attachment records in the session file | PENDING (rollout instruction messages, R-6) | PENDING (snapshot or stream, R-6) | held pending |
| inherited-context: cwd | session record | SAME: rollout turn_context.cwd | PENDING: no native cwd | held pending for G |
| inherited-context: extra dirs, tool servers, prompt snapshot, memory | session records (deferred tools, prompt snapshot, memory section) | PENDING; argv and pinned config run as input-side legs | PENDING; same | held pending; NOT COMPARABLE by ruling if no session-side record exists |
| checkout-binding (git status) | the session's own git status | PENDING; never the driver's record | PENDING; same | held pending; NOT COMPARABLE by ruling if no session-side record exists |
| checkout-binding (instruction files) | CLAUDE.md bytes of the pinned tree | PENDING on R-6 | PENDING on R-6 | held pending |
| model-binding | the model on every assistant record (served) | NOT COMPARABLE: requested model per turn, served model seen only on a reroute | SAME: init.model and every stats.models key | O's model binding is "requested, no reroute observed", never "served" |
| constant-binding: permission mode | the session's recorded mode | PENDING: approval_policy spelling unverified | NOT COMPARABLE: argv as submitted, no session-side record; approval events refuse | G's mode is "submitted", never "observed" |
| harness-condition-violated: denied tools | the session's offered tools | PENDING; pinned config input-side | PENDING; same | held pending |
| harness-condition-violated: steer conditions | Claude Code switches | N/A | N/A | not a check for O and G |
| session-binding | the CLI session file carries the imposed id | SAME with section 2's four legs | SAME with section 2's four legs | comparable |
| account-email | session_context.userEmail | PENDING: sweep count, bounded by the scan | PENDING: same | sweep-counted until settled |
| nested-agent (store, sweeps, commands) | driver-recorded listings and session commands | SAME: same listings, CLI-written exec commands | SAME: same listings, stream commands | comparable |
| sub-agents (delegation) | Agent calls admitted and checked | NOT COMPARABLE: any delegation refuses the take | NOT COMPARABLE: same | O and G cannot delegate; C can; Agent-parity analyses exclude O and G |
| transcript-unreadable | closed reader of the session file | SAME: closed tables, unread lines refuse | SAME | comparable |
| outcome, fixture, ledger, script, invocation | driver ledger and design | SAME (same records for every arm) | SAME | comparable |
- Every PENDING row holds the take pending, under its existing reason id with "no vendor reader yet"; no PENDING row ever passes a take, and none falls back to a driver-written record.
- A PENDING row becomes SAME when its reader is built and re-tested on recorded bytes, or NOT COMPARABLE only by a glitch-b5 ruling that the study then publishes; the input-side legs named in the row still run and must pass in either case.
- The four NOT COMPARABLE rows known now (O model, G permission mode, O and G delegation, and the steer N/A) are asked of glitch-b5 as R-7.

## 4. Reach readers: what the agent actually executed, over the evidence C's readers see
- C's reach readers read every string of every tool input and tool result in the CLI-written session file (D/check_take.py:209-214, _tool_strings 302-322); the vendor readers match that on CLI-written bytes, never on the view's mapped arguments (transcript_view.map_tool keeps only mapped keys, D/transcript_view.py:206-233).
- The view is used only to prove each record is on the closed tables; the reach strings are then every string leaf of that same raw record (the walk _tool_strings does).
- Codex evidence: each turn's exec stream turn-<k>.jsonl (bound to its envelope by sha256, bound_items), every string leaf of each command_execution item (command and aggregated_output).
- Codex evidence, second source: the take's last retained rollout, <take>/session/native-turn-<n>.jsonl (native_snapshot.retain_bytes, D/native_snapshot.py:225-237, retained at D/drive.py:2516-2517), every string leaf of each CommandExecution item (its executed argv list `command` and aggregated_output, D/codex_native.py:179-189), read only after read_rollout accepts the file.
- Codex: aggregated_output is the full output of what ran, a superset of the model-facing (possibly truncated) result, so reading it is at least as strict as C's tool-result read.
- Codex file_change items carry paths only, no content (D/transcript_codex.py:30-31), and the cross-check already refuses any file_change (PROJECTED_EXEC_ITEMS, D/codex_native.py:82, 317-318), so such a take never grades; the vendor checker also refuses it (PENDING) until a recorded rollout shows the patch record and a reader of its text exists.
- Codex mcp_tool_call stays refused (no tool server is configured in a take), as do web_search and todo_list (off the tables).
- Gemini evidence: each turn's stream turn-<k>.jsonl, every string leaf of each tool_use's parameters and each tool_result's output, including list_directory's dir_path, write_todos, run_shell_command's dir_path, write_file's content and replace's strings, all dropped by the view's mapping (D/transcript_gemini.py:96-107).
- Gemini evidence, second source: the take's last retained native snapshot (same folder), every string leaf of each recorded toolCalls entry's args, result (the model-facing functionResponse) and resultDisplay, read only after gemini_projection.project accepts the file (D/gemini_projection.py:28-33, 234-235).
- Red-first tests: a gemini F3 fixture with list_directory {dir_path: "<checkout>/evals"} raises study-materials-reached; a codex F3 fixture whose rollout CommandExecution argv reaches outside the run tree while its exec command string does not raises the outside reason; mutants that read the view's mapped args instead, or skip the second source, go red.

## 5. How T4 meets T0 (option B) and the descriptions it makes false
- T0 is in fb830f31: design_view admits codex and gemini rows (HARNESSES_WITH_SCRIPTS, D/check_take.py:2020); check4 and check4_walk keep harness_guard (1933, 2394).
- Option (B): check4 and check4_walk stay Claude-only and unchanged; T4 appends check4_vendor and check4_walk_vendor behind their own guard, and take_checker reaches them only through P0's dispatcher.
- (B) touches no R5 code region and moves no assertion; option (A), admitting vendors into check4 in place, would re-anchor the "harnesses-with-scripts" span and add two spans, and is not recommended.
- Three descriptions become false once vendor readers exist (review MINOR 8), each named for ruling R-1:
- The R4C-9 comment's last clause, "every vendor take is still refused until a vendor reader exists here" (D/check_take.py:2005-2009), inside the r4c9-comment span of BOOTSTRAP_SPANS (tests/test_walk_runner.py:1073): re-pin its sha256 with a sentence saying vendor takes are read by the appended vendor entries through checker_for.
- harness_guard's refusal text, "has no record readers in check_take.py" (D/check_take.py:2117-2121, base prefix): reword to "check4 reads claude-code only; vendor takes go through checker_for", a base-prefix edit that needs its own ruling, or a ruling that it stays as is.
- V0's test name test_v0_every_checker_entry_still_refuses_a_vendor_take (D/tests/test_vendor_script.py:119-120): rename to test_v0_check4_still_refuses_a_vendor_take, plus a new V0 witness that take_checker's production road reaches check4 only through checker_for.

## 6. The whole drive.py-checker contract, and P0
drive.py is in READER_SOURCES and CODEX_SOURCES (D/native_reader_registration.py:85-87, 160-161), so every drive.py edit must land before Javier's acceptance commit; T4 needs exactly one, edit A.
The contract, as drive.py uses the checker today (D/drive.py:3585-3614, 2600-2633, 2870-2890):
- C1, inputs: take_checker gets design_for(row, take), the take's folder, identity and cross_check, and records "takes" or "walks".
- C2, pending: cross_check None raises NativeCrossCheckPending before any read (3593-3594); vendors keep this, since cross_check is None while no native reader is registered.
- C3, transcript: no transcript.jsonl gives readers-disagree (3597-3598); the vendor envelope is transcript.jsonl, so this holds as is.
- C4, side readings: take.checker_constants_sha256, take.no_output_nudges and take.agent_summary (3602-3604), later read by walk_runner into check.json and by pending_walk.checker_standing (D/pending_walk.py:135-147, 190-207) and walk_regrade (D/walk_regrade.py:238-246).
- C5, the check: check4 or check4_walk returning {"reasons", "events"} (3605-3610).
- C6, cross-check: a non-empty take.cross_check adds readers-disagree (3612-3613).
- C7, return: exactly CHECKER_KEYS, one non-negative int per event id, ACCOUNT_EMAIL_EVENT present and not above the scan's masked emails (2878-2890).
- C8, session store: the drive writes session-store.json with the vendor keys of section 1b (2621-2627) and judges vendor_nested_problems itself (2629-2633); take.native_rel is not written (2516).
What P0 must change before acceptance, and only this:
- Edit A (drive.py, take_checker, lines 3600-3610): right after design_for, call `_ct.checker_for(design)` before any transcript read; it returns (entry, side) or raises CheckRefused for a harness with no reader (codex and gemini until P3, the same exception check4's harness_guard raises today, only earlier); then `take.checker_constants_sha256, take.no_output_nudges, take.agent_summary = side(path, design)` and `got = entry(path, row, design, row_index=take.identity["row"], records=records)`.
- P0's check_take.py half (appended, outside both source lists): checker_for, whose claude-code entry calls exactly today's check4 and check4_walk and whose side function returns exactly today's three values, so a claude-code take's record is byte-identical before and after.
- The fixed vendor side contract, decided now so no later drive.py edit is needed: checker_constants_sha256 is the digest of CHECKER_CONSTANTS merged with VENDOR_CHECKER_CONSTANTS[harness] (P5), and pending_walk's `now` becomes harness-aware (P5, pending_walk.py, outside both lists).
- no_output_nudges is 0 for a vendor take, a real reading, not a default: section 1a's readers-disagree refuses any non-operator user record, so a checked vendor take carries no harness re-delivery.
- agent_summary is today's shape with zero Agent calls and no sub-agent models, true by construction because any delegation refuses the take (section 1b); nested_cli_calls stays the drive's count from session-store.json.
- native_rel is derived by the checker, not recorded by the drive: the one file entry in the publish listing (vendor_store_violations admits exactly one, D/check_take.py:3607-3630), which must agree with the retained snapshot count and, for gemini, with the vendor id's first 8 characters in the filename (D/native_snapshot.py:12-14).
- C8's driver verdict stays as an extra refusal (never a pass); the checker re-derives the same rule independently in P4.
- No second drive.py edit is planned; if the build finds one, it stops `blocked` and names it for a ruling, never edits.
- P0 test (red first): tests/test_take_checker_dispatch.py (named so it cannot be misread for tests/test_vendor_checker_road.py): a vendor take through take_checker with no_output_nudges and agent_summary patched to raise refuses with CheckRefused before either is called; a claude-code take's {checker_reasons, checker_events} and three side readings are equal before and after; mutants: the dispatcher call moved after the side readings, and the claude-code entry calling a different check, each go red.

## 7. The freeze gate for documented-only readers
- Today freeze.unrecorded_shapes_problem (D/freeze.py:314-329, called by main at 440 before prepare or any write) reads only each adapter's SHAPES_SOURCE, which flips on the adapter's own re-test (D/tests/test_codex_adapter.py:708-711), so it alone cannot keep T4's readers out of a frozen order (review MAJOR 4).
- The gate, enforced in the same function: an arm O or G row refuses unless all three hold for its harness: (i) the adapter's SHAPES_SOURCE is "recorded" (T3, as now); (ii) check_take.VENDOR_CHECK_SHAPES_SOURCE[harness] is "recorded", an absent key or table refusing; (iii) native_reader_registration.production_readers() holds that harness, which needs Javier's committed acceptance on a recorded walk (D/native_reader_registration.py:595-607).
- Each refusal names the arm and the leg, e.g. "arm G (gemini): check_take.VENDOR_CHECK_SHAPES_SOURCE is 'documented'".
- This piece (PF) lands first, before any T4 reader, so no build order can reach a frozen draft with documented-only readers.
- Test (red first): tests/test_freeze_shapes.py gains FS-check: with both adapters patched "recorded", main refuses while (ii) is absent or "documented" and while (iii) is empty, naming the leg; passes only with all three; a claude-code-only draft passes unchanged; witnesses deleting leg (ii) and leg (iii) each go red.
- Binding (review MINOR 9, mirroring A7-source): tests/test_vendor_check.py refuses VENDOR_CHECK_SHAPES_SOURCE "recorded" for a harness while any READER or SAME item of that harness lacks a fixture labelled RECORDED with its provenance; DOCUMENTED fixtures never constrain the adapter's own flip.
- The flip to "recorded" is the re-test of section 8, item by item.

## 8. Fixture plan, documented shapes only
- Every fixture is synthetic and labelled DOCUMENTED in its name and header comment.
- F1 DOCUMENTED: a codex take folder (envelope transcript.jsonl, driver-ledger.json, turn-<k> exec streams with matching sha256, launch journals, session/native-turn-<k>.jsonl rollouts, session-store.json, environment.json), from test_pending_codex_walk's generators.
- F2 DOCUMENTED: the same for gemini, from test_pending_walk's accepted Gemini walk.
- F3 DOCUMENTED: one variant per READER reason that fires exactly that reason, and one per PENDING item showing its "no vendor reader yet" refusal.
- F4 DOCUMENTED: a walk folder per vendor for check4_walk_vendor.
- Re-test on recorded bytes, each flipping its item in VENDOR_CHECK_SHAPES_SOURCE's evidence: every READER item on the acceptance walk's retained streams and snapshot (pass: the reader returns the recorded value without refusing, and its F3 mutant still goes red on the recorded copy).
- Settle on recorded bytes: each PENDING row of section 3 (pass: a reader is written and re-tested, or glitch-b5 rules it NOT COMPARABLE), plus vendor_store_violations' and native_snapshot's stated assumptions (D/native_snapshot.py:16-18), Codex exec options before `resume` (D/codex_adapter.py:29) and Gemini `-r`.

## 9. Files, tests, mutants and claims per piece
- PF freeze gate: D/freeze.py unrecorded_shapes_problem; tests as section 7.
- P0 dispatcher: D/drive.py edit A plus check_take.py checker_for; tests as section 6.
- P0b pin_for (review MINOR 7): D/batch.py expected_pin raises a named refusal for a harness or model with no pin profile ("routing.json's pin_profiles hold no codex/<model> profile; CP5 registers it") in place of the bare KeyError at batch.py:418.
- P0b test (red first): tests/test_pin_for_vendor.py drives production_builders()["pin_for"] (D/walk_builders.py:939-940) on the committed draft's first codex and gemini rows against today's routing.json; today it raises KeyError (red); the mutant restoring the bare lookup goes red; batch.py and walk_builders.py are in neither source list.
- P1 vendor view and raw records: check_take.py appended section "T4 VENDOR READERS" above `if __name__`; vendor_view over bound_items with ViewError mapped to transcript-unreadable, and raw_tool_strings (section 4) over both sources; tests/test_vendor_check.py red first on F1 and F2; mutants: ViewError swallowed, an empty view read as clean, and the view's args read in place of raw leaves, each go red.
- P2 vendor check body: one function per reason of section 1, reusing the pure helpers (operator_line_problems, continuation_problems, fixture_binding_problems, constant_problems, ledger_budget_problems, context_leaks, nested_agent_flag_problems, command_problems); one F3 case per reason; mutants: each reason's guard deleted, and each PENDING refusal deleted, go red.
- P2's readers-disagree cases (review MAJOR 1): a codex F3 rollout whose UserMessage differs from the envelope's `sent` raises readers-disagree, and so does one with an extra turn; a mutant reading the envelope twice goes red; a gemini F3 stream whose user record differs raises readers-disagree, not transcript-unreadable.
- P3 entries: check4_vendor and check4_walk_vendor with check4's CheckRefused preamble and the event-count invariant; checker_for admits them; mutants: the guard, the invariant and the arm binding each dropped go red.
- P4 session store: the vendor shape, native_rel derivation and section 2's legs 1-4; mutants: an extra listing entry admitted, a turn-2 argv resuming another id admitted, and an extra native interaction admitted, each go red.
- P5 model, mode, environment and constants: VENDOR_CHECKER_CONSTANTS appended (never edited into CHECKER_CONSTANTS), the merged digest of section 6, pending_walk's harness-aware `now` and walk_regrade's vendor side readings; mutants: model mismatch admitted, a PENDING billing-route variable defaulted, and a vendor walk read as current under the Claude-only digest, each go red.
- Claims: COPIED.d/vendor-admission.json claims the new test modules; checks.d/vendor-admission.txt runs them; check_take.py's departure is recorded in w10-walk-runner, freeze.py's in w8b-holdout-digests, batch.py's in its owner's record, and drive.py's in its owner's record.
- Source lists: T4 edits no READER_SOURCES or CODEX_SOURCES file except P0's edit A; transcript_view.py, vendor_record_binding.py, vendor_provenance.py, codex_native.py and gemini_projection.py are called, never edited.
- Hazard for glitch-b5, not T4's to change: transcript_codex.py is in neither list, and vendor_record_binding.py and transcript_view.py are in READER_SOURCES but not CODEX_SOURCES, so a codex acceptance binds none of the three files that read the codex envelope (D/native_reader_registration.py:85-87, 160-161).

## 10. Size per piece (agent-hours, re-derived from this lane's measured rounds)
- Basis: T1-T3 were three guarded checks, each red-first with one mutant, in about 15 minutes, so about 5 minutes per guarded check; each review fold took about 10 minutes.
- PF freeze gate: 2 legs and their witnesses, about 0.2 h.
- P0 dispatcher and side contract: 3 guarded behaviours, about 0.25 h; P0b pin_for: 1, about 0.1 h.
- P1 view and raw readers: 4 guarded behaviours over two sources per vendor, about 0.35 h.
- P2 check body: about 30 READER reasons and about 14 PENDING refusals, each with an F3 case and a mutant, 44 x 5 minutes, about 3.7 h.
- P3 entries: 3, about 0.25 h; P4 store and binding legs: 4, about 0.35 h; P5: 6, about 0.5 h.
- Fixtures F1, F2 and F4: about 0.5 h (F3 is counted in P2).
- Total build: about 6.2 h; folds: about 10 minutes per review round, one round per piece and two more for P2, about 1.5-2 h; together about 8 h, below the brief's 16-30 h.
- After the walks (not cloud): the re-tests and PENDING rows of section 8, sized when recorded bytes exist.

## 11. Rulings asked of glitch-b5
- R-1: option (B), with section 5's three descriptions: re-pin the r4c9-comment span, reword or keep harness_guard's base-prefix message, and rename V0 with its new witness.
- R-2: session binding option (a) with section 2's four legs.
- R-3: P0's edit A as the only drive.py edit, with section 6's contract, before Javier's acceptance commit.
- R-4: P0b in this lane (batch.py refuses by name); CP5 registers the O and G pin_profiles under its rate-limit and spend-cap rules.
- R-5: arm G's permission mode is NOT COMPARABLE (argv as submitted), with the BYTES leg that any approval or confirmation event refuses.
- R-6, adopted as the review recommends: which instruction file Codex and Gemini are pointed at (AGENTS.md, GEMINI.md or a configured fallback name, against the pinned tree's CLAUDE.md) is Javier's design ruling, owed before P2's checkout-binding and loaded-context cases and P5's pinned-instructions binding; those legs refuse until then.
- R-6 unblocks: P2's instruction-content and loaded-context cases, the F1 and F2 instruction files, the pinned-instructions expected hashes in P5, and the instruction-file legs of inherited-context.
- R-7: the NOT COMPARABLE rows of section 3 (arm O model, arm G mode, O and G delegation, the steer N/A), each published as such by the study.
- R-8: PF's freeze gate (legs ii and iii) first, before any T4 reader.
- R-9 (coverage flag carried): once T4 exists, a pending walk counts as coverage only when its regrade road also carries a vendor checker reading under the merged constants in force (pending_walk.coverage_status, D/pending_walk.py:70-90).

## 12. Where each v1 review finding landed
- MAJOR 1 (readers-disagree never fails for codex): section 1a's first four lines, section 3 row 1, P2's readers-disagree cases.
- MAJOR 2 (reach over mapped args): section 4, section 3's reach row, P1's raw readers.
- MAJOR 3 (silently weaker checks, driver checking itself): section 3, the PRINCIPLE lines at the top, section 1a's checkout line (fallback withdrawn), section 2's legs.
- MAJOR 4 (freeze lets documented readers through): section 7 and PF.
- MAJOR 5 (drive.py contract incomplete): section 6, P0.
- MINOR 6 (email): section 1a's account-email line, section 3's account-email row.
- MINOR 7 (pin_for): P0b in section 9, R-4.
- MINOR 8 (descriptions made false): section 5, R-1.
- MINOR 9 (fixture-label test direction): section 7's binding line.
- MINOR 10 (sizes): section 10.
- MINOR 11 (instruction files): R-6, adopted; section 1a's instruction lines.
- NITs: nested_agent_flag_problems named (1b); gemini delegation refuses by unknown tool name (1b); check_walk's and walk_session_id's CheckRefused lines listed (1b); P0's test renamed (section 6); the brief's class words mapped (top).
