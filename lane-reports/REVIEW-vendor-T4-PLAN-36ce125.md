T4 PLAN: READY TO RULE

# Review (round 4) of lane-reports/vendor-T4-PLAN.md v4 and vendor-T4-TABLE.md at 36ce125f (lane vendor-admission, T4 planning)

Fresh, independent reviewer, briefed by glitch-b5 on Javier's approved planning task ("vendor-t4: yes", Sat 17 Oct 2026, about 08:57 EDT); written Sat 17 Oct 2026, about 12:20 EDT.
Lane head reviewed: 9d49759c (the plan and table at 36ce125f). Code read at harness head fb830f31 (branch codex/gap4-live-harness-20261013); `D/` is evals/gap-study-4/, and every code line cited is at fb830f31. fb830f31..cbf3c231 is four commits touching build_draft.py, prereg-draft.json, routing.json, routing.py, their tests, a fixture and a claim; none of the code lines this review cites moved.
Plan lines are cited as `plan:N` (vendor-T4-PLAN.md, 216 lines) and table lines as `table:N` (vendor-T4-TABLE.md, 43 lines; rows T-1 to T-24).
Read-only: no code, test or fixture was changed, and nothing was run beyond reads.

## Verdict in one paragraph
v4 closes round 3's MAJOR and all three MINORs on the code. R-9's road (plan:126-131) matches the real gap: coverage_status's pending branch at D/pending_walk.py:86-88; the recheck refusal at D/walk_regrade.py:85 and 520-522; _check_fields refusing a pending check.json at 448-458, called at 514; production_checker's ledger cross_check at 473. The plan's four parts and three mutants close it.
The four 12:08 rulings are carried as written.
The table has one row per check, and on every row the PRINCIPLE holds as stated: a vendor check is SAME, or PENDING (it refuses), or NOT COMPARABLE (published, and asked as R-7).
Sizes re-add to 7.7 h.
No MAJOR survives at the stop-at-nits bar. There are two new MINORs:
- the definition of a "string leaf" leaves out JSON object keys, which Claude Code's study-materials reader does see;
- nothing ties a key settled to SAME to a reader that actually runs at its call site.

Both can be folded while building P1 and PF, without another plan round.

## Round 3's findings
| # | Round-3 finding | Status | Why (checked against fb830f31) |
|---|---|---|---|
| 1 | MAJOR: R-9 is adopted but no piece builds it | CLOSED | Plan:126-131 (section 6) build it in P5, and plan:181 and plan:213 map it. Part (a) widens RECHECK_HARNESSES (D/walk_regrade.py:85) in the same piece and routes recheck_doc through checker_for. Part (b) admits a pending check.json only on a regrade.json that re-derives and grades the walk true. That check.json is the one _check_fields refuses today (D/walk_regrade.py:448-458, 514), and the regrade's own cross_check replaces the ledger's (production_checker, 473), which C2 would refuse. Part (c) makes the pending branch (D/pending_walk.py:86-88) count only through checker_standing's pending road over latest_recheck (211), under the same rules as a checked walk, among them CONSTANT_BOUND_REASONS (D/check_take.py:2452-2453) and the merged digest in force. Part (d) has walk_regrade --check re-derive vendor rechecks (regrade_problems, 277-300). That is the same bar a Claude Code recheck meets: latest_recheck binds only the sha256, and re-derivation is --check's (D/pending_walk.py:216-217). The red-first test and its three mutants are at plan:131, and P5 is sized at plan:197. NIT 1 names one line the build must also change. |
| 2 | MINOR: account-email names no string and no unit | CLOSED | Plan:51-53 and T-9 (table:23, 40-41) name the strings for each harness: the operator's address plus the codex ChatGPT account, or the Google account that owns the gemini key. They reach the scan as ("email", value) secrets read when the scan runs. Today lease_secrets and login_secrets (D/walk_builders.py:223-252) hand over tokens only, so P2 adds those pairs (plan:162). The unit is 0 or 1 per take, as C's is (D/check_take.py:697-716, 1910-1915). The drive's bound stays (D/drive.py:2886-2891). The scan's residuals are stated from box/scan_record.py's own NAMED RESIDUALS paragraph (lines 37-39). The ruling is carried. |
| 3 | MINOR: nothing binds VENDOR_PENDING_ROWS to the PENDING refusals raised | CLOSED | Plan:16 and plan:146-147: one helper, check_take.vendor_pending(harness, key), refuses with the reason id read from the map, and an unknown key raises KeyError. VP-keys reads the literal call keys from the AST and checks them equal to the map's keys for each harness; a non-literal argument fails the test, and the refusal text may occur only inside the helper. Three mutants cover it. The table lists every key (table:10), and each PENDING cell of T-4 to T-18 maps to one. The ruling is carried. New finding 2 tightens what "settled" lets through. |
| 4 | MINOR: a JSON-encoded leaf is read as encoded text | CLOSED | Plan:86 decodes any leaf the record type defines as a JSON document, codex function_call arguments by name, and names each such field in the partition table. A leaf that does not decode refuses under transcript-unreadable and never falls back to its text. Plan:98 adds the escaped-path F3 case, reachable only after decoding, with two mutants; P1's mutants (plan:159) and T-8 (table:22) carry it. The ruling is carried. New finding 1 is about keys, not encoding. |
| N1 | neutral_name lines | CLOSED | Plan:75 and T-20 cite 102-103, and `def neutral_name` is at D/check_take.py:102. |
| N2 | T-24's READER leg and ledger-row sites | CLOSED | Table:38 names "ended at the end of a turn" as READER for each arm, and check:1753, 1757, 1761 and check_walk:2348-2371. |
| N3 | REFUSED versus tool records | CLOSED | Plan:89 refuses a REFUSED record whatever it is. |
| N4 | claude-code standing and the ledger | CLOSED | Plan:125: `now` falls back to today's digest when there is no ledger, an unreadable one, claude-code or any other harness, so arm C reads byte for byte as before. A vendor walk misread on that fallback reads stale, which is fail-closed. |
| N5 | no gemini walk counts until T-4 settles | CLOSED | Table:8 says so and extends it to the other constant-bound PENDING rows. |
| N6 | sizes | CLOSED | Plan:194-199 re-add to 7.7 h (0.35 + 0.25 + 0.1 + 0.7 + 3.85 + 0.25 + 0.45 + 1.05 + 0.5 + 0.2). P1 at 8 x 5 min, P2 at 44 x 5 min + 0.15 h and P5 at 13 x 5 min agree with the stated basis. |

## The four 12:08 rulings
- R-9 is built in P5: carried (plan:126-131, 197, 213). Coverage counts a pending vendor walk only with a verified checker reading under the merged constants, through the widened recheck road, read through checker_standing.
- The account-email sweep names its strings for each harness and counts 0 or 1 per take: carried (plan:51-53, T-9).
- Every vendor PENDING refusal goes through one helper keyed by VENDOR_PENDING_ROWS, with a test binding the helper's keys to the map: carried (plan:146-147, P2's mutants at plan:161).
- A JSON-encoded leaf is decoded before its leaves are read, and an undecodable one refuses under transcript-unreadable: carried (plan:86, 98, 159).

## The PRINCIPLE and the table
- One row per check: every reason site of plan sections 1a and 1b maps to a row from T-1 to T-24. The rows of section 1b that are refusals rather than reasons (CheckRefused lines, the mcp_tool_call, web_search and todo_list refusals, gemini's approval-event refusal) are refusals for every arm and need no row.
- Each PENDING cell refuses on the take road and is never counted on the walk road unless a Claude Code walk with the same reason would be (table:6-7, against D/pending_walk.py:150-208).
- Each NOT COMPARABLE cell (T-15 O, T-16 G, T-22 O and G, and T-19's N/A) states what the study publishes and is asked as R-7.
- No row is silently weaker, except the leaf definition in new finding 1, which bears on T-8's SAME.

## New findings

### 1. MINOR: "every string leaf" leaves out JSON object keys, which C's study-materials reader sees
- Plan: plan:85-86, 88, 94 and 95 ("every string leaf" of codex sources 1-3 and the gemini sources), and T-8 (table:22).
- Code: C's study-materials-reached reader matches over json.dumps of each tool_use input and each tool_result content (D/check_take.py:209-214). That serialisation includes object keys, so a key that names the study's materials is seen. _tool_strings (302-322) reads values only and backs the other reach reasons.
- For a vendor record, a "string leaf" means a value. A decoded function_call arguments object, a gemini toolCalls args, result or resultDisplay, or a stream tool_result output that carries a path as an object key would then be read for read-outside-the-checkout as C reads it, but not for study-materials-reached.
- Consequence for the study: T-8's SAME for study-materials-reached rests on reading less than C reads, in one structural place. This is not reproduced on recorded bytes; no recorded vendor record is known to key an object by path.
- Fix (P1, no new plan round): the vendor reach reader reads every string of a record, keys and values, for study-materials-reached, as C's serialised blob does. Add one F3 case whose study path occurs only as an object key, with a values-only mutant going red. Reading keys for read-outside-the-checkout as well would be stricter than C and is not required.

### 2. MINOR: a key settled to SAME silences its refusal, and nothing ties the settle to a reader at that site
- Plan: plan:146 (vendor_pending returns None once a key is settled, and "its reader ... then decides"), plan:144 and plan:150 (leg (ii) and the fixture binding require a SAME key to name a fixture labelled RECORDED), and plan:187 (section 8, the re-test).
- Code: none yet. The structure planned is that a call site reads vendor_pending's None as "no refusal". VP-keys binds only the call keys to the map's keys, and the fixture binding checks only the fixture's label.
- Changing a key's state from PENDING to SAME, naming a RECORDED fixture, makes every call site for that key fall through. Nothing tested shows that a reader runs at that site, or that the named fixture's F3 case still fires the row's reason. Section 8 requires that re-test but does not bind it in code.
- Consequence for the study: a row can become SAME in the map, and then in the published table, with no vendor reading behind it. The freeze's leg (ii) would open on it.
- Fix (PF and P2): settling a key must carry its reader. One option is vendor_pending(harness, key, reader), which calls the reader once the key is settled and refuses while it is PENDING. The other is for the fixture-binding test to require each SAME key's named RECORDED fixture to have an F3 variant that fires the row's reason id through that call site. Either needs a mutant: a key settled with a reader that returns nothing goes red.

## NITs
- 1. R-9 part (a): recheck_doc writes its digest from ct.design_constants_sha256(design) (D/walk_regrade.py:545). On vendor_view's Design that digest covers CHECKER_CONSTANTS keys only (D/check_take.py:2485-2496), so a vendor recheck would record the Claude-only digest and read stale forever. That is fail-closed, and the red-first counted case would catch it, but plan:128 should name the line: for a vendor walk, the digest is vendor_design_constants_sha256 and must equal the side's digest.
- 2. R-9 part (c): checker_standing's road for a checked walk validates check.json's keys, route, route_refused and events (D/pending_walk.py:166-172). Plan:130 should say which of those the pending road does without (none of them exist on a pending walk). It should also say the road still requires check.json to be exactly pending_walk.check_doc's document (D/pending_walk.py:44-49), so a hand-edited pending check.json reads "check unreadable".
- 3. Plan:51: "read by name at scan time from the box's account record". No such record of the vendor account addresses exists at fb830f31; walk_builders hands the scan tokens only (D/walk_builders.py:223-252). Name the record's owner and file in P2, or list it as owed, as R-6 is.
- 4. Sizes: the 5 min per guarded check basis comes from T1-T3, which reused fixtures. Most of P2's 44 checks need a new F3 variant, so 3.85 h is a floor. The 1.5-2 h fold allowance is where an overrun lands; the total is still well below the brief's 16-30 h.
