T4 PLAN: NOT READY

# Review (round 2) of lane-reports/vendor-T4-PLAN.md v2 at 52b1f37a (lane vendor-admission, T4 planning)

Fresh, independent reviewer, briefed by glitch-b5 on Javier's approved planning task ("vendor-t4: yes", Sat 17 Oct 2026, about 08:57 EDT); written Sat 17 Oct 2026, 10:57 EDT.
Lane head reviewed: 745a4e26 (unmoved). Code read at harness head fb830f31 (branch codex/gap4-live-harness-20261013); `D/` is evals/gap-study-4/, and every code line cited is at fb830f31.
Plan lines are cited as `plan:N` (vendor-T4-PLAN.md at 52b1f37a, 222 lines).
Read-only: no code, test or fixture was changed, and nothing was run beyond reads.

## Verdict in one paragraph
v2 closes all eleven round-1 findings on the code, not just on its own say-so: the codex readers-disagree is now a real comparison against the rollout's CLI-written UserMessage, the reach readers read raw leaves, the comparability table and the withdrawn checkout fallback are there, the freeze gets its own fail-closed legs, and the drive.py-checker contract is complete.
The inventory's line numbers check out again (every reason site in check(), the helpers it calls, check4, check4_walk, check_walk and the round-4 problem functions).
It is not ready to rule for one new MAJOR: the arm O reach row is rated SAME, but the codex reach readers read only CommandExecution records, while the rollout's model-facing tool-call and tool-output records are accepted and skipped by read_rollout and read by nothing (new finding 1).
Five new MINORs tighten what the table and the freeze gate promise; none of them weakens a check if left alone, but each makes a sentence of the plan untrue.

## Round 1's findings
| # | Round-1 finding | Status | Why (checked against fb830f31) |
|---|---|---|---|
| 1 | MAJOR: codex readers-disagree could never fire | CLOSED | plan:18-21 compare read_rollout's per-turn UserMessage (D/codex_native.py:159-162, read_rollout at 191, the no-UserMessage refusal at 276) against envelope and ledger `sent`, count and text; bound_items does force envelope and ledger equal (D/vendor_record_binding.py:99-104) and codex_join_session never compares `sent` (D/native_reader_registration.py:178-207), so the new comparison is the only one and is real; gemini's carries readers-disagree with the ViewError (vendor_record_binding.py:138-139) as backstop. Red-first case and mutant at plan:179. |
| 2 | MAJOR: reach over the view's mapped args | CLOSED for gemini; superseded for codex by new finding 1 | plan:112-121 read every string leaf of raw records, not map_tool's mapped args (D/transcript_view.py:206-233); gemini's list_directory, write_todos, write_file and replace leaves (D/transcript_gemini.py:96-107) are now read on both sources. Codex covers exec command_execution and rollout CommandExecution only; see new finding 1. |
| 3 | MAJOR: silently weaker checks; driver checking itself | CLOSED | Section 3's table exists (plan:85-109); the checkout fallback is withdrawn (plan:48, 95); input-side legs are named as such and the rows are PENDING (plan:34, 50-51, 94); arm O's model is NOT COMPARABLE as "requested, no reroute observed" (plan:97; D/native_reader_registration.py:165-167); arm G's mode is NOT COMPARABLE (plan:60, 98); option (a)'s legs are named (plan:78-83). The table's completeness and two of its ratings are new findings 2, 3 and 5. |
| 4 | MAJOR: the freeze lets documented-only readers through | CLOSED | plan:155-161: unrecorded_shapes_problem (D/freeze.py:314-329, called at 440 before any write) gains leg (ii) VENDOR_CHECK_SHAPES_SOURCE and leg (iii) production_readers (D/native_reader_registration.py:595-619), red-first in tests/test_freeze_shapes.py, landing first (PF, R-8). What flips leg (ii) is new finding 4. |
| 5 | MAJOR: P0 did not fix the whole drive.py contract | CLOSED | C1-C8 (plan:134-142) match take_checker (D/drive.py:3586-3614) and the publish step (2600-2633) and the drive's checks on the checker's record (2878-2890); edit A is the only drive.py edit; the side function lives in check_take.py, so later vendor values change no drive.py byte; native_rel is derived by the checker from the one admitted listing entry (D/check_take.py:3607-3630). Where the vendor constants enter the design view is new finding 6. |
| 6 | MINOR: account-email half N/A, half BYTES | CLOSED | plan:35 and plan:102 take the sweep this review's round 1 asked for, bounded by the drive's masked-email check (D/drive.py:2886-2891). Its PENDING label is new finding 3. |
| 7 | MINOR: pin_for has no red-first plan | CLOSED | P0b (plan:175-176): batch.expected_pin's bare lookup (D/batch.py:418, reached via D/walk_builders.py:939-940) refuses by name; red today on KeyError; mutant restoring it; neither file is in a source list. |
| 8 | MINOR: descriptions option (B) makes false | CLOSED | plan:127-130 name the r4c9-comment span (tests/test_walk_runner.py:1073), harness_guard's message (D/check_take.py:2117-2121, base prefix after the checker-constants end anchor) and V0's test name (D/tests/test_vendor_script.py:119-120), each for R-1. NIT 2 adds one more. |
| 9 | MINOR: fixture-label test direction reversed | CLOSED | plan:160 mirrors A7-source (D/tests/test_codex_adapter.py:708-711): "recorded" is refused while an item lacks a RECORDED fixture with provenance; DOCUMENTED fixtures never constrain the adapter's own flip. |
| 10 | MINOR: sizes not believable | CLOSED | plan:188-195 re-derive at about 5 minutes per guarded check; 44 x 5 min is about 3.7 h for P2, and the pieces sum to 6.2 h as stated. New finding 1 adds one reader (about 0.2 h). |
| 11 | MINOR: R-6 blocks P2 and P5 | CLOSED | plan:204-205 adopt it as Javier's design ruling, name what it unblocks, and the instruction legs refuse until then (plan:49). |
| - | Round 1's five NITs | CLOSED | plan:222 maps each; each checks out (nested_agent_flag_problems at D/check_take.py:1963, 2423, body 3523-3525; gemini delegation as an unknown tool name; check_walk 2336 and walk_session_id 2323 listed; P0's test renamed; class words mapped at plan:12). |

## New findings

### 1. MAJOR: arm O's reach row is rated SAME, but the rollout's model-facing tool records are read by nothing
- Plan: plan:91 (reach row, arm O "SAME on raw exec items and rollout CommandExecution items"), plan:114-118 (the codex evidence: exec command_execution leaves and rollout CommandExecution leaves).
- Code: read_rollout accepts every response_item whose type is in RESPONSE_ITEMS and skips it unread (D/codex_native.py:230-233); RESPONSE_ITEMS holds the model-facing tool records (function_call, function_call_output, local_shell_call, custom_tool_call, custom_tool_call_output, tool_search_call, tool_search_output, web_search_call; D/codex_native.py:69-72).
- Nothing in read_rollout, codex_join_session (D/native_reader_registration.py:178-207) or the plan requires each such record to have a CommandExecution counterpart; the exec stream's view refuses items it does not project (D/codex_native.py:317-318), but a tool record that produces no turn item and no exec item reaches neither source.
- Claude Code's reach readers read every string of every tool input and result in the session file (D/check_take.py:209-214, _tool_strings 302-322); the plan already treats the same skipped response_item family as unread for unknown-harness-origin (plan:22), but not for reach.
- So the SAME rating rests on an unproven pairing: that every model-facing tool record in the rollout is mirrored by a CommandExecution item.
- Consequence for the study: arm O's study-materials-reached and outside-reach events (event_counts, D/check_take.py:1910-1915) could be counted over fewer records than arm C's, with the table publishing them as comparable.
- Fix: the codex reach reader also reads every string leaf of every response_item tool-call and tool-output record of the accepted rollout (they are CLI-written and already parsed), or a rollout whose tool records do not pair one to one with its CommandExecution items is held PENDING under a non-event reason id until a recorded rollout settles it; either way, plan:91's row says which.
- Red-first test: a codex F3 rollout holding a response_item tool-call record that names the checkout's evals/ and no CommandExecution counterpart raises study-materials-reached (or the named PENDING refusal); a mutant that reads CommandExecution items only goes red.

### 2. MINOR: session-binding is rated SAME on legs that prove freshness, not that the session followed its row's commit
- Plan: plan:78-83 (legs 1-4, "so section 3 rates it SAME"), plan:101.
- Code: Claude Code's check compares the CLI-recorded id against uuid5 of the row's commit (D/check_take.py:1761-1771), so the CLI's own bytes show the session started after that commit existed ("or the row was committed after the fact").
- Legs 1-4 show the vendor session is fresh, single and the same across turns; legs 1 and the envelope id are driver-written; none ties the vendor bytes to the row commit.
- The one CLI-written leg that does is already in the plan but not named here: the project name, neutral_name(sid) = "run-" plus the first 8 hex of the uuid5 (D/check_take.py:102-103), must appear in the operator lines (plan:41), and those lines are bound to the CLI-written rollout UserMessage or gemini stream and snapshot user records (plan:18-20, 29).
- That leg carries 32 bits of the commit-derived id, where Claude Code's carries the whole id.
- Consequence for the study: the table publishes the vendor pre-registration binding as identical to Claude Code's when its commit-ordering leg is narrower.
- Fix: name the project-name leg as leg 5 of option (a), state its width, and either keep SAME with that stated difference for glitch-b5 to accept, or move the commit-ordering leg to R-7's NOT COMPARABLE list.

### 3. MINOR: PENDING is "refused under its existing reason id", which does not hold for the event ids or on the walk road
- Plan: plan:10, plan:12, plan:107 ("no PENDING row ever passes a take"), plan:35 and plan:102 (account-email PENDING, sweep-counted), plan:117 (codex file_change "PENDING").
- Code: check4 lifts study-materials-reached, account-email and read-outside-the-checkout into events, never reasons (D/check_take.py:1970-1982, and check4_walk at 2441; routing.json checker_reasons_become_events), and raises CheckRefused when a lifted id disagrees with its count.
- So a PENDING refusal written under one of those ids is either counted as an event or trips the invariant; and the account-email row as written is a count that passes at zero, which plan:107 says no PENDING row does.
- On the walk road, a walk is graded whatever its reasons and counts as coverage unless a reason is in CONSTANT_BOUND_REASONS (D/check_take.py:2452-2453; pending_walk.checker_standing, D/pending_walk.py:150-208), so a PENDING inherited-context, leak-in-loaded-context or harness-condition-violated on a vendor walk does not hold it; for a take every operator reason routes harness-error after the first turn (routing.json driver_decided_reasons' source).
- Consequence for the study: built literally, the account-email and file_change rows behave differently from what the table publishes, and "held pending" means something different per road.
- Fix: say what PENDING does on each road (take: refused, harness-error; walk: recorded, counted as coverage only as a Claude Code walk with that reason is); give every PENDING refusal on an event-id row a non-event reason id; relabel account-email as "counted by sweep" with the argument that the sweep is at least as wide as Claude Code's one-field read (D/check_take.py:697-716), or hold it under a non-event id.

### 4. MINOR: the freeze can open on an arm whose PENDING rows are unsettled, and the re-test's pass rule has no independent expected value
- Plan: plan:160 (leg (ii) needs RECORDED fixtures for READER and SAME items only), plan:169-170.
- Code: leg (ii) as bound would read "recorded" while PENDING rows remain; every PENDING row that fires on every vendor take (prompt snapshot, loaded context, checkout git status, denied tools, codex unknown-harness-origin; plan:94-99) then routes every take of that arm harness-error.
- plan:169's pass rule ("the reader returns the recorded value without refusing") compares the reader with itself.
- Consequence for the study: an order can freeze with arms O and G able to produce no graded take, which the freeze is meant to prevent.
- Fix: leg (ii) also requires every PENDING row of that harness settled (SAME with a RECORDED fixture, or NOT COMPARABLE by a recorded ruling), bound in the same FS-check test; each READER item's re-test names its independent expected value (the ledger's sent, the routing pin's model, the run tree, the uuid5) and the recorded record that exercises it; an item the acceptance walk does not exercise keeps leg (ii) closed until a recorded walk does or a ruling settles it.

### 5. MINOR: the comparability table is not one row per check
- Plan: plan:85 ("one row per check").
- Missing rows: no-first-agent-turn (check:1593), no-session-id (check:1600; for a vendor it reads the driver-written envelope id), the stop and marker family (required_steps 1048-1079, continuation_problems 1265-1274), environment-record with its PENDING billing-route leg (plan:45; D/codex_adapter.py:53-54, D/gemini_adapter.py:58-59), and design_tree_problems' readers-disagree (D/check_take.py:2299; arm G PENDING per plan:62).
- Consequence for the study: the table is what the study publishes; a reader of it alone misses arm G's run-tree leg and both arms' environment-record PENDING leg.
- Fix: add the rows with their ratings; most are SAME on the bound view.

### 6. MINOR: where the vendor constants enter the design view is not said
- Plan: plan:146, P5 (plan:182: VENDOR_CHECKER_CONSTANTS appended, the merged digest, a PENDING billing-route variable refusing).
- Code: design_view refuses any constants block whose keys are not exactly CHECKER_CONSTANTS' (D/check_take.py:2169-2170, base prefix and design-view spans), so a vendor block cannot reach design.pre or design.pending through it; R4C-7 reads the take only through its view (the R4C-7 comment, D/check_take.py:1992-1998); check.json carries no harness key (CHECK_KEYS, D/pending_walk.py:92), which pending_walk's harness-aware `now` would need.
- Consequence for the study: P5 would either read vendor constants beside the view, or edit design_view's spanned and base-prefix code, which no ruling names; and a vendor walk's standing would be judged without knowing its harness.
- Fix: name the road (an appended vendor view wrapper in check_take.py that builds design_view's Design and adds the vendor block and its PENDING paths, or a ruled span), and where pending_walk and walk_regrade read a walk's harness.

## Recommendations on the plan's open questions
- R-1: option (B). Re-pin the r4c9-comment span; reword harness_guard's message under a new BOOTSTRAP_SPANS entry in the same commit (NIT 2); rename V0 with its new witness.
- R-2: option (a) with legs 1-4 plus finding 2's leg 5, its width stated for glitch-b5's acceptance.
- R-3: yes: edit A as the only drive.py edit, before Javier's acceptance commit; the P0 test (vendor take refused before either side reading; claude-code record byte-identical; two mutants) is concrete and sufficient.
- R-4: yes, P0b in this lane; CP5 registers the O and G pin_profiles.
- R-5: yes, arm G's mode NOT COMPARABLE, with the approval-event BYTES leg.
- R-6: Javier's design ruling, owed before P2's instruction and loaded-context cases and P5's pinned-instructions binding.
- R-7: rule the four rows, and finding 2's commit-ordering leg if it is not kept SAME; finding 1 should be fixed rather than ruled.
- R-8: yes, PF first, with finding 4's PENDING-settled condition added to leg (ii).
- R-9: yes; the coverage flag stands until a vendor regrade carries a checker reading under the merged constants.

## NITs
- 1. plan:164 labels fixtures "in its name and header comment": a JSONL fixture cannot carry a comment line under the closed readers; use a README label list as codex-streams does (D/tests/test_codex_adapter.py:102-104, 192).
- 2. HARNESSES_WITH_READERS (D/check_take.py:2017, in the harnesses-with-scripts span's start anchor) also becomes a false description once vendors are read; say in the re-pinned R4C-9 sentence that it names check4's harnesses, not every harness with readers.
- 3. plan:113 "every string leaf of that same raw record": bound_items returns RawItems without the raw line (D/transcript_view.py:195-203); say P1 re-reads the digest-bound stream file line by line and runs the same parser on each line, so the table proof and the leaf read are over one line.
- 4. plan:149 checks the gemini filename's 8-character prefix; say the codex derivation checks the rollout filename's thread id too.
- 5. plan:69 cites subagent_leak_problems:3292, which is its docstring; the reason site is 3297.
- 6. Leg (iii) (plan:156): production_readers raises RegistrationRefused on a record that does not hold; the freeze leg should turn that into its named refusal, not a traceback.
- 7. plan:184: a checks.d line per piece asserting its files are disjoint from READER_SOURCES and CODEX_SOURCES (read from the module) would make "edits none except A" a red check rather than a sentence.
- 8. The plan is 222 lines against the brief's "under about 200".
