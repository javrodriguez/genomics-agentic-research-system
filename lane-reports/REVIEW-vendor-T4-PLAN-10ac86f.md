T4 PLAN: NOT READY

# Review (round 3) of lane-reports/vendor-T4-PLAN.md v3 and vendor-T4-TABLE.md at 10ac86ff (lane vendor-admission, T4 planning)

Fresh, independent reviewer, briefed by glitch-b5 on Javier's approved planning task ("vendor-t4: yes", Sat 17 Oct 2026, about 08:57 EDT); written Sat 17 Oct 2026, 11:32 EDT.
Lane head reviewed: 328e5365 (unmoved). Code read at harness head fb830f31 (branch codex/gap4-live-harness-20261013); `D/` is evals/gap-study-4/, and every code line cited is at fb830f31.
Plan lines are cited as `plan:N` (vendor-T4-PLAN.md, 191 lines) and table rows as T-N (vendor-T4-TABLE.md, 39 lines), both at 10ac86ff.
Read-only: no code, test or fixture was changed, and nothing was run beyond reads.

## Verdict in one paragraph
v3 closes round 2's MAJOR and all five MINORs on the code: the closed partition of RESPONSE_ITEMS (plan:89) is exactly the code's seventeen types (D/codex_native.py:69-72; 8 READ, 5 NOT TOOL RECORDS, 4 REFUSED, no overlap, nothing missing), the fail-closed refusals route as stated on both roads (transcript-unreadable is an operator reason and harness-error after turn 1 on a take; on a walk it is outside CONSTANT_BOUND_REASONS, D/check_take.py:2452-2453, so it behaves exactly as a Claude Code walk with that reason), Design.replace exists for the vendor view (D/check_take.py:2148-2149), and the eight NITs check out.
The 11:10 rulings 1 to 5 are carried as written.
It is not ready to rule for one new MAJOR: ruling 6 adopts R-9, but no piece, test, mutant or size builds it, and the code path it is meant to close (a pending vendor walk counted as coverage on a regrade no checker read) survives T4 as planned (new finding 1).
Three new MINORs tighten the account-email row, the binding of VENDOR_PENDING_ROWS to the checks that raise PENDING, and what "every string leaf" means for a JSON-encoded leaf.

## Round 2's findings
| # | Round-2 finding | Status | Why (checked against fb830f31) |
|---|---|---|---|
| 1 | MAJOR: arm O reach skips response_item tool records | CLOSED | plan:88-91 add source 3 over every RESPONSE_ITEMS tool-call and tool-output record of the accepted rollout (read_rollout skips them at D/codex_native.py:230-233); the partition at plan:89 equals RESPONSE_ITEMS (D/codex_native.py:69-72) type for type, and plan:90 binds that equality by a test; REFUSED types and any type outside the partition refuse under transcript-unreadable, never an event id; T-8 says SAME only with source 3; the review's red-first test and CommandExecution-only mutant are at plan:97, with an unreadable-record mutant at plan:98. New finding 4 tightens what a leaf is. |
| 2 | MINOR: session binding SAME on freshness legs only | CLOSED | Leg 5 (plan:75-77) is the project name, neutral_name = "run-" plus the first 8 hex of the id (D/check_take.py:102-103), bound to CLI-written user records through readers-disagree; its 32-bit width is stated in T-20 against the whole-id leg (D/check_take.py:1761-1771), as ruling 2 requires. |
| 3 | MINOR: PENDING per road and event ids | CLOSED | plan:12-13 and the table header (lines 6-8) define PENDING per road; the take side matches routing.json (every operator reason routes harness-error after turn 1; transcript-unreadable is in operator_reasons_round4); the walk side matches pending_walk.checker_standing (D/pending_walk.py:150-208); no PENDING row names study-materials-reached, account-email or read-outside-the-checkout (checker_reasons_become_events); reach PENDING uses transcript-unreadable. The account-email row's argument is new finding 2. |
| 4 | MINOR: freeze opens on unsettled PENDING rows; re-test has no independent value | CLOSED | plan:123-128 add the settled condition to leg (ii) through check_take.VENDOR_PENDING_ROWS, bound in FS-check with a witness; plan:135-143 name an independent expected value and a recorded record per READER item, and keep leg (ii) closed for an item the acceptance walk does not exercise. How the map is bound to the code is new finding 3. |
| 5 | MINOR: table not one row per check | CLOSED | T-1, T-2, T-4, T-7 and T-17 are present with ratings; every reason site of plan sections 1a and 1b maps to a row (NIT 2 below names two cells that under-describe their row). |
| 6 | MINOR: where vendor constants enter the view | CLOSED | plan:115-118: an appended vendor_view takes design_view's Design (design_view's key check at D/check_take.py:2169-2170 and its shadow rule at 2178-2180 untouched) and returns Design.replace (D/check_take.py:2148-2149) with the vendor block and its _pending_paths (2124); the walk harness is read from driver-ledger.json agent.harness, as walk_regrade already does (D/walk_regrade.py:139, 520); check.json carries no harness (CHECK_KEYS, D/pending_walk.py:92). Ruling 5 is carried. |
| N1-N8 | Round 2's NITs | CLOSED | README label lists (plan:132; D/tests/test_codex_adapter.py:100-104); the HARNESSES_WITH_READERS sentence (plan:103); one-line reading (plan:85); the codex filename's whole thread id (plan:113; D/native_snapshot.py:101-103); reason site 3297 (correct: the append is at D/check_take.py:3297); leg (iii)'s named refusal (plan:125); disjointness lines (plan:156); 191 lines with the table split out. |

## New findings

### 1. MAJOR: R-9 is adopted but built by no piece, so a pending vendor walk still counts as coverage with no checker reading
- Plan: plan:181 (R-9 "yes: once T4 exists, a pending walk counts as coverage only when its regrade road also carries a vendor checker reading"), against section 9's pieces (plan:147-156) and section 10's sizes (plan:160-168), none of which names pending_walk.coverage_status or a vendor recheck road.
- Code: coverage_status returns None (counted) for a pending walk whenever a verified regrade grades it true (D/pending_walk.py:86-88, via _regrade_state 52-67), and regrade_doc does not re-derive the checker reading (D/walk_regrade.py:25-26); checker_standing, which P5 edits, is reached only on the graded-true branch (D/pending_walk.py:84-85), never on the pending one.
- The recheck road, the one place a later checker reading of a walk is written, refuses every vendor walk (RECHECK_HARNESSES = ("claude-code",), D/walk_regrade.py:85, refused at 520-522); plan:117 cites line 520 but no piece opens that road for codex or gemini.
- A Claude Code walk counts only through checker_standing (no constant-bound reason, checked under the constants in force); a pending vendor walk regraded after registration counts with no check at all, which is the coverage flag the lane has carried since round 1 (pending_walk.py:86-88).
- Consequence for the study: walk coverage (walk_plan and fixture_walk.walk_coverage, D/fixture_walk.py:273-279) counts vendor walks that no checker read while arm C's walks must pass one; that is a silently weaker count, and ruling 6's R-9 is carried in words only.
- Fix: add R-9 to a piece (P5 is the natural home): coverage_status's pending branch counts a pending vendor walk only when a verified checker reading under the merged constants in force exists for it (a vendor recheck road through checker_for, RECHECK_HARNESSES widened in the same piece, its result read through checker_standing), else reports why; red-first test: a pending codex walk with a verified graded-true regrade and no checker reading is not counted; mutant: the pending branch returning None on "graded" alone goes red; size it (about 0.2-0.3 h on the plan's own basis).

### 2. MINOR: the account-email row's "at least as wide" argument names neither the string swept nor the unit counted
- Plan: plan:36, T-9 and table:37 ("the count of the operator account's identity string over every published vendor file"; "every case C's read refuses has a sweep hit").
- Code: C's reading is the presence of a field, whatever its value (session_context.userEmail, D/check_take.py:697-716), and counts at most one per take (event_counts takes len of a list that returns at the first hit, D/check_take.py:1910-1915); the drive bounds the checker's count by the scan's masked email hits (D/drive.py:2886-2890).
- The plan does not say which identity string the sweep counts for codex and for gemini (each CLI signs in to its own vendor account), so "every case C's read refuses has a sweep hit" holds only if the vendor's identity field, when present, carries exactly that string; and the sweep counts instances across files, where C counts zero or one per take.
- Consequence for the study: the table publishes account-email as comparable while arm O and G counts are per instance and arm C's are per take, and a vendor identity field carrying an address other than the swept one is counted by neither the sweep nor a field read.
- Fix: name the swept strings per harness (each vendor account's address, plus the operator's), say the per-take count is 0 or 1 as C's is (any hit counts one), and keep the drive's masked-hit bound; or rate T-9 NOT COMPARABLE for the unit with the reason stated.

### 3. MINOR: nothing binds VENDOR_PENDING_ROWS to the PENDING refusals the checker actually raises
- Plan: plan:124 (leg (ii) refuses while any VENDOR_PENDING_ROWS value is "PENDING"), plan:128-129 (FS-check and the A7-source mirror).
- Code: leg (ii) would read only the map's own values (the freeze reads constants, not the table, D/freeze.py:314-329); the table is a lane report, outside the code the freeze reads.
- A PENDING refusal written in P2 (or a row's PENDING leg such as T-17's billing route) with no key in VENDOR_PENDING_ROWS is never asked to settle, so leg (ii) can open on an arm whose checker still refuses every take under that row.
- Consequence for the study: the freeze guard round 2 finding 4 asked for holds only for the rows someone remembered to list.
- Fix: one source of truth: each vendor PENDING refusal is raised through a helper keyed by its VENDOR_PENDING_ROWS row, and a test asserts the set of keys the helper is called with (read from the module) equals the map's keys per harness; mutant: a PENDING refusal raised outside the helper, or a key dropped from the map, goes red.

### 4. MINOR: "every string leaf" reads a JSON-encoded leaf as its encoded text, where C reads decoded tool input
- Plan: plan:85 and plan:88 (source 3 reads every string leaf of every RESPONSE_ITEMS tool-call and tool-output record).
- Code: C's reach reader reads tool_use input objects as decoded values, re-serialised (D/check_take.py:209-214, _tool_strings 302-322); a rollout function_call record carries its arguments as one JSON-encoded string, so its leaf is the encoding, not the values the tool ran with; the source-3 records are exactly those with no CommandExecution counterpart carrying a decoded argv.
- Consequence for the study: arm O's source-3 reach would compare encoded text where arm C compares decoded values, so T-8's SAME rests on an unstated equivalence.
- Fix: say that a leaf the record type defines as a JSON document (function_call arguments, and any tool output so defined) is decoded and its own leaves read, a leaf that does not decode refuses under transcript-unreadable, and add an F3 case whose path is reachable only after decoding, with a mutant reading the encoded leaf going red.

## NITs
- 1. plan:75 and T-20 cite neutral_name at D/check_take.py:101-102; it is 102-103.
- 2. T-24 rates outcome-binding "driver ledger and design ... same records for every arm", but plan:37 reads "ended at the end of a turn" from the vendor stream (READER); and the ledger-row session-binding sites (check:1753, 1757, 1761; check_walk:2348-2358, 2371) appear in no row's cell. Name both in T-24.
- 3. plan:89 lists compaction, compaction_summary and context_compaction under REFUSED, which plan:90 describes as tool records; say REFUSED refuses the take whatever the record is.
- 4. plan:118: a claude-code walk with no driver-ledger.json would newly read "check unreadable"; say whether claude-code standing reads the ledger at all, so arm C's coverage is byte-for-byte unchanged.
- 5. T-4 for arm G is PENDING under readers-disagree, which is in CONSTANT_BOUND_REASONS, so no gemini walk counts as coverage until it is settled; correct and strict, but worth one sentence in the table header so the walk plan expects it.
- 6. Sizes: new finding 1 adds about 0.2-0.3 h and finding 4 about 0.1 h to P1; the 7.2 h build otherwise re-adds as stated (0.35 + 0.25 + 0.1 + 0.6 + 3.7 + 0.25 + 0.45 + 0.75 + 0.5 + 0.2).
