T4 PLAN: NOT READY

# Review of lane-reports/vendor-T4-PLAN.md at 52d653f0 (lane vendor-admission, T4 planning)

Fresh, independent reviewer, briefed by glitch-b5 on Javier's approved planning task ("vendor-t4: yes", Sat 17 Oct 2026, about 08:57 EDT); written Sat 17 Oct 2026, 09:27 EDT.
Code was read at harness head fb830f31 (branch codex/gap4-live-harness-20261013); `D/` is evals/gap-study-4/, and every code line cited below is at fb830f31.
Plan lines are cited as `plan:N` (vendor-T4-PLAN.md at 52d653f0).
Read-only: no code, test or fixture was changed, and nothing was run beyond reads.

## Verdict in one paragraph
The inventory is close to complete, and its line numbers check out: every `[reason]` site in check(), required_steps, operator_line_problems, continuation_problems, fixture_binding_problems, checkout_problems, the instruction checks, completion_problems, constant_problems, model_problems, published_email_problems and the round-4 checks is where the plan says it is.
Option (B) and session option (a) are sound directions.
The plan is still not ready to rule, for five reasons.
First, one READER classification compares two records the binding already forces equal, so that check could never fire (finding 1).
Second, the reach checks are planned over the view's mapped arguments, which drop arguments that Claude Code's reach readers do read (finding 2).
Third, the plan never says plainly where a vendor take ends up less strictly checked than a Claude Code take, and one fallback turns an independent check into the driver checking its own record (finding 3).
Fourth, the claim that the freeze keeps documented-only readers out of a frozen order is not true for T4's readers (finding 4).
Fifth, the one drive.py edit allowed before acceptance (P0) does not yet fix the whole contract between drive.py and the checker, so a later need would force Javier to accept again (finding 5).

## Findings

### 1. MAJOR: readers-disagree for codex is classified READER on a comparison that can never fail
- Plan: plan:12 (check:1580 readers-disagree, codex READER, "the envelope's operator events ... against the ledger's turn rows"), and plan:19 and plan:77 (operator lines, independent read deferred to BYTES).
- Code: vendor_record_binding.bound_items already refuses unless every envelope's `sent` equals its ledger turn's `sent` and the envelope count equals the ledger's stream inventory (D/vendor_record_binding.py:99-104 and the `ledger.get("streams") != names` check after the loop); the exec stream carries no operator record (D/transcript_codex.py:35-36), and bound_items requires none for codex (D/vendor_record_binding.py:138-139).
- So for codex, "envelope operator events against ledger rows" compares two records that the driver writes, which the view has already forced equal: on any bound view the check is constant-false.
- Round 3's readers-disagree compares two readers of bytes the CLI wrote (tx.load's turns against user_text_records, D/check_take.py:1573-1583).
- The independent reader already exists and is registered: vendor_provenance.session_facts returns each native interaction's `sent` (D/vendor_provenance.py:138-168, SESSION_KEYS at :40) through native_reader_registration.codex_reader (D/native_reader_registration.py:165-174); codex_join_session does not compare `sent` (D/native_reader_registration.py:178-207), so nothing on the drive road covers it either.
- For gemini the second reader is real (the stream's own user record, D/vendor_record_binding.py:138-139), but a mismatch there surfaces as a ViewError, which maps to transcript-unreadable, never as readers-disagree; the plan should say which reason id it carries.
- Consequence for the study: arm O would carry a readers-disagree check that cannot fire, while arm C's can, so "no readers-disagree" would mean different things across arms.
- Fix: classify codex readers-disagree as READER on session_facts(...)["sent"] over the take's last retained rollout, per ordinal (count and text against the envelope), with the rollout's user-message shape BYTES; fold plan:19's "independent read" into the same reader, rather than leaving it BYTES with no named function.
- Red-first test: an F3 codex fixture whose rollout's user message differs from the envelope's `sent` must raise readers-disagree; a mutant that reads the envelope twice goes red.

### 2. MAJOR: the reach readers are planned over the view's mapped arguments, which is narrower than what Claude Code's readers see
- Plan: plan:29-30 (study-materials-reached and read-outside-the-checkout "READER, the view's tool-call args ... over the same view strings"), plan:75-76.
- Code: Claude Code's reach readers read every string of every tool input and result (`json.dumps(x.get("input"))`, D/check_take.py:209-214; _tool_strings walks the whole input, D/check_take.py:302-322).
- The view keeps only the keys an entry maps (transcript_view.map_tool, D/transcript_view.py:206-233), and Gemini maps `list_directory` and `write_todos` to OTHER with an empty mapping (D/transcript_gemini.py:106-107).
- So a Gemini `list_directory` of `evals/...`, or of a path outside the run tree, has no argument in the view; `replace`'s strings and `write_file`'s content are dropped as well (D/transcript_gemini.py:100-101).
- Consequence for the study: study-materials-reached and the outside-reach events are routing events (event_counts, D/check_take.py:1910-1915, summed into outside_reach); arm G would be counted on fewer strings than arm C, so reach rates are not comparable across arms, and a reach could pass unseen.
- Fix: the vendor reach readers read the RAW native tool arguments and results of each bound record (the parser's input record, every string leaf, as _tool_strings does), not the view's mapped args; the view is used only to establish that the record is on the closed tables.
- Codex's `mcp_tool_call` refusal (plan:29) stays as written.
- Red-first test: an F3 gemini fixture with `list_directory {dir_path: "<checkout>/evals"}` must raise study-materials-reached; a mutant that reads the view args instead goes red.

### 3. MAJOR: the plan never says plainly where a vendor take is checked less strictly than a Claude Code take, and one fallback turns an independent check into the driver checking its own record
The brief's item (3) asks the plan to keep a vendor take as strictly checked as a Claude Code take, or to say plainly where it cannot and what that means for comparability. The plan replaces several session-side reads with input-side ones and calls them READER or N/A, without saying they are weaker:
- (a) Checkout: plan:38 ends "failing which the ruling names the driver's own checkout record as the source".
  - checkout_problems exists to check the driver's checkout against what the SESSION recorded (D/check_take.py:1145-1175).
  - With the driver's own record as the source, the driver checks itself, so the check can never disagree.
  - Absent a session-side record, this leg must stay BYTES and refuse ("no vendor reader yet", plan:7). Otherwise the ruling must name it as an unchecked leg for arms O and G.
- (b) Prompt snapshot, memory and tool servers: plan:24, 40 and 41 replace the session's own record (prompt_snapshot_present, memory_section_offered, deferred_tools_delta in inherited_context, D/check_take.py:644-694, 921-960) with the per-take config's pinned bytes.
  - pinned_files' own docstring says this "proves byte correspondence, not that a CLI actually loaded these files" (D/vendor_provenance.py:115-121).
  - The plan should call this an input-side check, weaker than the Claude Code check, until a recorded walk shows a session-side record.
- (c) Model: codex's reader is the rollout's turn_context model, which is the REQUESTED model (D/native_reader_registration.py:165-167). The served model is seen only when a reroute error item appears (codex_join_session's served_models).
  - model_problems for Claude Code reads the model on every assistant record (D/check_take.py:742-764).
  - The plan (plan:36, 80) should say that arm O's model binding means "requested, and no reroute observed", not "served".
- (d) Permission mode: R-5 (plan:140) asks whether gemini's argv is acceptable as its only mode source, but does not say what accepting it means. It means arm G's mode is checked as submitted, never as observed, whereas Claude Code's is checked as recorded (recorded_mode_problems, D/check_take.py:1894-1901).
- (e) Session identity: under option (a) (plan:66, 70), the envelope's `session_id` and the ledger are both written by the driver.
  - For Claude Code, by contrast, the CLI's own record carries the imposed id.
  - What ties the vendor bytes to the row is the launch journal: turn 1's argv resumes nothing, and every later argv resumes exactly that vendor id (launch_facts, D/vendor_provenance.py:57-79, the FIRST_TURN rule at :59-60). The stream digests in the envelope and the store listing holding only one session add to that.
  - Option (a) must name these legs, the launch journal for every ordinal and the turn-1 listing, as what makes the session fresh and unique. Without them, a resumed earlier session is bound only by the driver's word.
- Fix: add one section, a table with one row per check, that states for each vendor whether the check is session-side as strong as Claude Code's, input-side (weaker), driver-attested (weaker), or refused until bytes exist. For each weaker row, it states what the ruling accepts for the study's cross-arm comparison. Then remove plan:38's fallback to the driver's own record.

### 4. MAJOR: the freeze does not keep T4's documented-only readers out of a frozen order
- Plan: plan:106 ("The freeze already refuses arms O and G while SHAPES_SOURCE is "documented" (T3), so no documented-only reader can reach a frozen order").
- Code: freeze.unrecorded_shapes_problem reads only each adapter module's SHAPES_SOURCE (D/freeze.py:314-329, SHAPES_ADAPTERS).
- An adapter flips to "recorded" on its own re-test, which needs only a RECORDED adapter fixture (D/tests/test_codex_adapter.py:708-711), and nothing in that flip requires T4's readers to have been re-tested.
- So once both adapters are re-tested, T4's READER items built on documented shapes reach a frozen order unchecked. Examples are gemini init.model and stats.models, codex file_change paths, and the vendor session-store shape.
- Consequence for the study: the arms O and G checkers could be frozen on shapes that no recorded byte has confirmed, which is exactly what ruling Q-3 forbids for the adapters.
- Fix: give T4 its own fail-closed gate, red-first. Either a checker-side VENDOR_CHECK_SHAPES_SOURCE per harness that freeze.unrecorded_shapes_problem also reads, or a freeze refusal while any vendor check fixture is labelled DOCUMENTED only, with a test that flips it.
- The re-test list (plan:103-105) then becomes the condition that flips that gate. Each listed item names the recorded file it runs on and what counts as a pass.

### 5. MAJOR: P0 is the only drive.py edit allowed before acceptance, but it does not yet fix the whole contract between drive.py and the checker
- Plan: plan:62 (own session: "the checker must derive it ... or the drive must record it (a READER_SOURCES edit; section 6)"), plan:94-95, plan:109, plan:119.
- Code: drive.py is in READER_SOURCES and in CODEX_SOURCES (D/native_reader_registration.py:85-87, 160-161), so any drive.py edit after Javier's acceptance commit forces a new acceptance.
- take.native_rel is set at D/drive.py:2516 but is not written to session-store.json (D/drive.py:2620-2627).
- take_checker also records three side readings for the take: checker_constants_sha256, no_output_nudges and agent_summary (D/drive.py:3602-3604).
- The plan leaves the native_rel choice open. P0 lists only drive.py (plan:109), yet P0 calls a dispatcher (`check_take.checker_for`) and "a check_take function dispatched by harness" for the side readings (plan:94). Both must exist in check_take.py when P0 lands.
- The plan also does not fix the return shape of the dispatcher and the side readings for a vendor take. For example, what are agent_summary and no_output_nudges for codex and gemini, and does the constants digest cover VENDOR_CHECKER_CONSTANTS?
- Consequence for the study: if any of these turns out to need data from drive.py after acceptance, Javier must accept again, which is the sequencing hazard the lane exists to avoid.
- Fix: decide the native_rel question now.
  - My recommendation is that the checker derive it: the one file entry in the publish listing, which vendor_store_violations already constrains to exactly one session file (D/check_take.py:3607-3630).
  - That listing must also agree with the retained snapshots' count and with the vendor id's 8-character prefix for gemini (D/native_snapshot.py:7-18).
  - If the derivation is ruled out, recording native_rel moves into P0.
- Also list P0's check_take.py append (the dispatcher, which refuses vendors until P3, and the side-reading dispatcher) and its fixed return contract in P0's file list. The red-first test pins that contract.

### 6. MINOR: account-email is half N/A and half BYTES, and the vendor email event count is undefined
- Plan: plan:25 ("N/A as written ... whether a vendor stream carries any account identity is BYTES") and plan:54 (event_counts READER).
- Code: published_email_problems (D/check_take.py:697-716) feeds EVENT_EMAIL (D/check_take.py:1910-1915), and the drive refuses a checker record without ACCOUNT_EMAIL_EVENT among its events (D/drive.py:2883-2885).
- The plan never says whether, before the walk, the vendor checker emits nothing (N/A) or refuses (BYTES, by plan:7's rule), nor what count it gives EVENT_EMAIL.
- Fix: classify it BYTES. Until it is settled, EVENT_EMAIL for a vendor take is counted by a sweep of every published vendor file (envelope, streams and snapshots) for the operator account's identity string, the sidecar-scan reading the plan names. N/A follows only once the recorded walk shows no identity field.

### 7. MINOR: T0-review item 1 has no red-first plan
- Plan: plan:92.
- Code: D/walk_builders.py:939-940 leads to D/batch.py:418, a bare KeyError on `table["pin_profiles"][harness][row["model"]]`.
- The plan says pin_for "should refuse by name" but gives no test, file list, mutant or owner. Item (6) of the brief asks for one.
- Fix:
  - A test drives walk_builders' real pin_for on a codex row and a gemini row against today's routing.json. It must raise a named refusal naming CP5's pin_profiles; today it raises KeyError (red).
  - A mutant that restores the bare lookup goes red.
  - The file is batch.py or walk_builders.py, neither of which is in READER_SOURCES or CODEX_SOURCES.
  - The owner is CP5's lane or this lane, by ruling R-4.

### 8. MINOR: option (B) leaves descriptions that become false, in pinned regions and in a test name
- Plan: plan:89-91 ("touches no R5 region and moves no assertion").
- Code: three descriptions stop being true once vendor readers are appended to check_take.py.
  - The R4C-9 comment, in the r4c9-comment span of tests/test_walk_runner.py's BOOTSTRAP_SPANS, ends "every vendor take is still refused until a vendor reader exists here" (D/check_take.py:2005-2009).
  - harness_guard's refusal says "has no record readers in check_take.py" (D/check_take.py:2117-2121; the body is base prefix, after the checker-constants span's end anchor).
  - V0's test is named "every checker entry still refuses a vendor take" (D/tests/test_vendor_script.py:119-120).
- Each assertion stays green, but each description lies once check4_vendor exists. This is the CLAUDE.md lesson about grepping for a description, not just an identifier.
- Fix: name the r4c9-comment region in R-1 with the ruling it needs (re-pin its sha256 with an updated sentence, or a ruling that it stays as is). Also name V0's rename together with a new V0 witness: take_checker's production road reaches check4 only through checker_for.

### 9. MINOR: the fixture-label test reverses its precedent
- Plan: plan:98 ("a test asserts each adapter's SHAPES_SOURCE is "documented" while any fixture carries that label").
- Code: the precedent holds the reverse direction: "recorded" is refused while no RECORDED fixture exists (D/tests/test_codex_adapter.py:708-711).
- As planned, the test would forbid an adapter's flip to "recorded" while any DOCUMENTED unit fixture remains, which ties T4's unit fixtures to the adapter's gate.
- Fix: mirror the precedent on finding 4's checker-side gate. That gate may read "recorded" only when every READER item has a RECORDED fixture with provenance.

### 10. MINOR: the sizes for P2 and for the folds are not believable
- Plan: plan:124-132.
- From the plan's own basis, T1-T3 was three guards, each red-first with one mutant, in about 15 minutes: about 5 minutes per guarded check.
- P2 has about 30 reasons plus about 12 BYTES refusals, each with an F3 variant, a red-first commit and a mutant (plan:113). At the same rate that is about 3.5 h for P2 alone, against the 0.75 h planned.
- Findings 1, 2 and 5 add the native-sent reader, the raw-argument reach readers and P0's check_take.py half.
- Fix: size P2 per reason (about 5 min each, about 3.5 h). That puts the total at about 6-7 h build and about 2 h of folds, still well below the brief's 16-30 h.

### 11. MINOR: the vendor instruction-file question (R-6) blocks part of P2 and P5, and the plan parks it
- Plan: plan:39 and plan:141.
- Code: pinned_instruction_problems binds the CLAUDE.md files of the pinned tree (INSTRUCTION_NAMES, D/check_take.py:2225; 2248-2283).
- The system under test is a workspace whose entry point is a CLAUDE.md. Which file Codex and Gemini are pointed at (AGENTS.md, GEMINI.md, or a configured fallback name) decides what arms O and G measure. It also decides which bytes the "pinned-instructions" reader binds.
- Fix: say that this leg refuses ("no vendor reader yet") until Javier rules it, and that P2's checkout-binding cases cannot be written before that ruling. It is a design question for Javier, raised now, not a T4 detail.

## Recommendations on the plan's open questions
- R-1: option (B), with finding 8's region and V0 rename named in the ruling. (B) keeps every Claude Code byte of check4 and check4_walk pinned, and puts all later vendor work in appended check_take.py code that is outside READER_SOURCES and CODEX_SOURCES.
- R-2: option (a), with finding 3(e)'s legs made explicit: the launch journal for every ordinal (turn 1 resumes nothing, later turns resume exactly the vendor id), one vendor id across envelopes, native streams and the publish listing's one session file, and the listings at every turn holding only that file.
- R-3: yes, P0 before Javier's acceptance commit, but only once finding 5 is folded, so that P0 is the complete contract between drive.py and the checker. Its red-first test as written (a vendor take through take_checker, with the two readers patched to raise) is concrete and sufficient for the guard.
- R-4: pin_for refuses by name now (finding 7), in this lane or the walk-builders owner's. CP5 registers the O and G pin_profiles under its rate-limit and spend-cap rules. Registration is not T4's job.
- R-5: accept the launch journal's argv as arm G's mode source only as an input-side check, recorded as such in finding 3's table. Add a BYTES item for the recorded walk: any approval or confirmation event in the stream refuses.
- R-6: Javier's design ruling, owed before P2's checkout-binding cases and P5 (finding 11). The vendor leg refuses until then.
- Coverage flag (plan:121): once T4 exists, rule that a pending walk counts as coverage only when its regrade road also carries a vendor checker reading under the constants in force (pending_walk.coverage_status, D/pending_walk.py:73-90). Until then, keep it flagged.
- Hazard (plan:120), wider than stated: transcript_codex.py is in neither list. vendor_record_binding.py and transcript_view.py, which bound_items and the codex view run through, are in READER_SOURCES (gemini) but not in CODEX_SOURCES (D/native_reader_registration.py:85-87, 160-161). So a codex acceptance binds none of the three files that read the codex envelope. That is glitch-b5's to rule, not T4's to change.

## NITs
- plan:60 cites command_problems (3473, 3477); the call check4 actually makes is nested_agent_flag_problems (D/check_take.py:1963, 2423; body at 3523-3525), and the vendor body should name it.
- plan:58: Gemini has no DELEGATE mapping (D/transcript_gemini.py:96-107), so a Gemini sub-agent tool refuses as an unknown tool name (map_tool's ViewError), not through DELEGATED_REFUSAL; the effect (refusal) is the same.
- plan:44 and plan:46: the CheckRefused lines of check_walk (D/check_take.py:2336) and walk_session_id (2323) are not listed beside check4's; they are refusals rather than reasons, so AS IS, but say so.
- plan:109: the new module name test_vendor_check_road.py sits beside the existing tests/test_vendor_checker_road.py; pick a name that cannot be misread for it.
- plan:6 abbreviates the brief's four classes (AS IS, READER, BYTES, N/A); map each to the brief's wording once, for a reader who has only the brief.
