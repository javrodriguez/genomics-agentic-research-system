# Guard messages build log

This is producer evidence for the refusal-text lane, not a decision record, change report, approval, or merge.
The branch is build/gars-guard-messages and the baseline is a80df2d.
Inventory commit: 67d1c34, with 73 refusal sites and renderers and an initially empty after column.
Decision-pin commit: 5891795, containing only the builder and its one JSONL fixture.
The builder generated the corpus against the unchanged a80df2d system tree and harvested all seven named modules successfully.
At the pin commit, `python3 -u gars/tests/build_refusal_corpus.py --check` gave `decision pin: 1705 refused, 461 allowed; OK`.
Red-first commit: 7a22ce5; `python3 -u gars/tests/test_refusal_messages.py` gave `Ran 8 tests in 91.674s`; `FAILED (failures=3254)`, with `decision pin: 1705 refused, 461 allowed; OK` inside that run.
Wording commit: 145ac23, with only the three permitted system files, moved existing assertions, and the inventory after column.
At the final tested source tree, `python3 -u gars/tests/test_refusal_messages.py` gave `Ran 8 tests in 98.878s`; `OK`, with the same green decision pin.
The evidence-only commit changes this build log; it leaves every tested guard, test, and fixture byte unchanged.
Every Python command used TMPDIR, TEMP, and TMP set to the job scratch twin, resolved at runtime from the repository root.
Every guard check was a direct JSON hook payload or a function call; no model or sub-agent tested the guard.

The payload field decodes to the exact captured JSON bytes; JSON Unicode escaping avoids literal machine paths and the tilde character in the fixture text.
The 74 compressed contexts retain guard-relevant fixture files, links, declarations, working directories, and changing dataset state.
Replay relocates the captured scratch bindings together; the recorded payload bytes remain immutable and are the keys compared between baseline and head.
Typed-only schema API cases are carried into Bash payloads, and the dispatcher refusal path is checked through parse_argv and authorize without executing a tool.
Historical and deliberately faulty guard copies in the existing tests contribute their payloads, rejudged by the pristine a80df2d guard for the pin.
`corpus test_policy_attacks: 31 rows`.
`corpus test_guard_hook: 204 rows`.
`corpus test_policy_faults: 3 rows`.
`corpus test_nonpublic_read_block: 1054 rows`.
`corpus test_pilot_doors: 238 rows`.
`corpus test_tool_schema_refusal: 8 rows`.
`corpus test_bash_lexer: 282 rows`.
`corpus registry: 333 rows`.
`corpus reported: 13 rows`.
`decision pin: 1705 refused, 461 allowed; OK`.
`old versus new: a80df2d refused=1705 allowed=461; head refused=1705 allowed=461; payload-byte diff length=0`.
The refused payload sets each contain 1335 unique byte strings and the allowed payload sets each contain 338; both set differences are empty.
`a80df2d lexer advice: 13 quoted literals accepted; 12 expansion/line-break forms refused; OK`.
`decision/check AST and the two mutation anchors unchanged; OK`.

| test | file and baseline line | old | new | reason |
|---|---|---|---|---|
| shared message constant | gars/tests/test_bash_lexer.py:15 | OPERATOR_MESSAGE = 'only one simple command; no shell operators or expansion' | OPERATOR_MESSAGE = 'one command per call: run each step as its own call' | Lexer actions now describe separate calls and literal quoting; exit and R-092 checks remain. |
| shared message constant | gars/tests/test_bash_lexer.py:16 | VOCABULARY_MESSAGE = 'value is outside the declared vocabulary' | VOCABULARY_MESSAGE = 'allowed values:' | Vocabulary now reports its enum; exit and R-092 checks remain. |
| denied | gars/tests/test_policy_attacks.py:72 | for word in (b'Rule', b'spec', b'typed call'): | for word in (b'R-', b'decision', b'Next: '): | Site-owned rule, citation and action replace the universal suffix; exit assertion remains. |
| test_no_verify_equals | gars/tests/test_policy_attacks.py:84 | b'R-096 forbids --no-verify' | b'--no-verify, including --no-verify=VALUE' | Citation follows the explanation; R-096 refusal still exits 2. |
| test_gitleaks_false | gars/tests/test_policy_attacks.py:87 | b'R-096 forbids git config' | b'git config hooks.gitleaks false disables the required secret scan' | Citation follows the explanation; R-096 refusal still exits 2. |
| test_class_flip_bound_to_row_6 | gars/tests/test_nonpublic_read_block.py:887 | self.refused(call(root, tool, {'file_path': DATASET}), 'R-092', root) | self.refused(call(root, tool, {'file_path': DATASET}), 'R-094', root) | Plain protected-write citation now names the actual rule instead of the generic suffix; no record rule exists here. |
| test_class_flip_bound_to_row_6 | gars/tests/test_nonpublic_read_block.py:888 | 'part of the GARS template' | 'protected template or machine-owned state' | Dataset state is machine-owned, not template code; exit assertion remains. |
| test_class_flip_bound_to_row_6 | gars/tests/test_nonpublic_read_block.py:890 | 'unregistered helper' | 'this helper, interpreter or executable is not registered' | Unregistered command now also lists the registered alternatives; exit and R-092 assertions remain. |
| test_every_registered_tool | gars/tests/test_nonpublic_read_block.py:468 | self.assertEqual(ours.stderr, reference.stderr) | self.assertEqual(decision(ours.returncode, ours.stderr.decode()),<br>                                             decision(reference.returncode, reference.stderr.decode()))<br>                            self.assertIn(b'Next: ', ours.stderr) | Historical guard adds the removed suffix; compare unchanged exit/type/field/rule and require the new action. |
| test_write_without_closed_project_unchanged | gars/tests/test_pilot_doors.py:351 | self.assertEqual((ours.returncode, ours.stderr), (theirs.returncode,<br>                                                                  theirs.stderr)) | self.assertEqual(decision(ours.returncode, ours.stderr.decode()),<br>                                 decision(theirs.returncode, theirs.stderr.decode()))<br>                if ours.returncode == 2:<br>                    self.assertIn(b'Next: ', ours.stderr)<br>                    self.assertIn(b'R-094', ours.stderr) | Historical guard has old prose; retain exit/type/field/rule equality plus protected-write citation and action. |
| test_guard_refuses_writes_and_the_direct_spelling | gars/tests/test_pilot_log.py:412 | b'part of the GARS template' | b'protected template or machine-owned state' | Pilot log is machine-owned state; exit assertion remains. |

All existing exit and field assertions remain; historical whole-text comparisons now compare exit, type, field, and rule and assert the new action.
The extra gate module is test_pilot_log.py because its machine-owned-state wording assertion moved.

The five mutations ran only in disposable scratch copies, each using the named committed test method without modifying the test or corpus.
Mutation (i) restored the old generic suffix; `RefusalMessagesTests.test_03_dynamic_next_steps`: `Ran 1 test in 152.779s`; `FAILED (failures=1705)`.
Mutation (ii) removed one site's alternative keyword; `RefusalMessagesTests.test_02_static_next_steps`: `Ran 1 test in 152.524s`; `FAILED (failures=1)`.
Mutation (iii) allowed one previously refused payload; `RefusalMessagesTests.test_01_decision_pin`: `Ran 1 test in 152.056s`; `FAILED (failures=1)`.
Mutation (iv) changed one record rule value; `RefusalMessagesTests.test_01_decision_pin`: `Ran 1 test in 73.471s`; `FAILED (failures=1)`.
Mutation (v) restored the misleading approval-store description for generic outside reads; `RefusalMessagesTests.test_04_approval_store_is_not_a_generic_path`: `Ran 1 test in 73.190s`; `FAILED (failures=1)`.

GATE summary lines follow verbatim, with the final source tree and scratch environment described above.
`python3 -u gars/tests/test_refusal_messages.py`: `Ran 8 tests in 98.878s`; `OK`.
`python3 -u gars/tests/test_guard_hook.py`: `Ran 7 tests in 33.210s`; `OK`.
`python3 -u gars/tests/test_policy_attacks.py`: `Ran 19 tests in 4.197s`; `OK`.
`python3 -u gars/tests/test_policy_faults.py`: `Ran 10 tests in 1.839s`; `OK`.
`python3 -u gars/tests/test_nonpublic_read_block.py`: `Ran 24 tests in 164.625s`; `OK`.
`python3 -u gars/tests/test_pilot_doors.py`: `Ran 17 tests in 62.543s`; `OK`.
`python3 -u gars/tests/test_tool_schema_refusal.py`: `Ran 8 tests in 0.480s`; `OK`.
`python3 -u gars/tests/test_bash_lexer.py`: `Ran 16 tests in 36.095s`; `OK`.
`python3 -u gars/tests/test_pilot_log.py`: `Ran 15 tests in 10.163s`; `OK`.
`python3 -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3, 6)) for p in sys.argv[1:]]; print('parsed', len(sys.argv) - 1)" gars/_system/guard_hook.py gars/_system/tool_call.py gars/_system/tools/policy.py gars/tests/build_refusal_corpus.py gars/tests/test_bash_lexer.py gars/tests/test_nonpublic_read_block.py gars/tests/test_pilot_doors.py gars/tests/test_pilot_log.py gars/tests/test_policy_attacks.py gars/tests/test_refusal_messages.py`: `parsed 10`.
`git diff --stat a80df2d -- .github evals docs/decisions gars/_system/tools/registry.json .claude gars/.claude` printed nothing.
`git diff --check` printed nothing.
Not verified: the whole suite, contracts gate, evidence-of-record runs, sealed evaluations, smoke sessions, live agent behavior, live scheduler behavior, and execution on a Python 3.6 interpreter.
No network access, push, remote addition, pull request, approval, or merge was performed.
Decisions 0175 and 0176 and the change report remain for Glitch.

## Round 2

L-1 replaces the encoded fixture; Round 1 encoding and compression did not satisfy the privacy rule.
All commits append to 8ee8d98; no commit was amended, rebased, or rewritten.
Red-first commit: c360033; `python3 -u gars/tests/test_refusal_messages.py FixturePrivacyTests`: `Ran 1 test in 0.063s`; `FAILED (failures=1)`.
The added-line read found runtime user names in generated config examples after the first portable-fixture commit 21a08f7.
Identity red-first commit: 2fb6c01; `python3 -u gars/tests/test_refusal_messages.py FixturePrivacyTests`: `Ran 1 test in 1.840s`; `FAILED (failures=1)`.
The follow-up adds a USER_NAME placeholder and regenerates from the baseline again; 21a08f7 remains in history under the append-only rule.
Final fixture commit: 29867dd, containing only the builder and fixture regenerated against a80df2d in a disposable scratch worktree.
Wording and assertion commit: 07cc6f8, shortening the registry advice while retaining the registered file-command names.
Machine roots use explicit placeholder tokens; replay substitutes runtime roots into the json.dumps payload templates.
Snapshots and hash-shared file text are plain JSON, with no base64 or compressed snapshot content and no printable-ASCII Unicode escapes.
Gzip fixture inputs are stored as decompressed text and rebuilt only in replay scratch.
The privacy test checks raw encoding, recursively checks decoded strings against runtime home, repository, and temp roots, and checks payload keys using the actual replay bindings.
The four existing malformed or non-object payloads remain pinned as malformed or non-object payloads.
`python3 -u gars/tests/test_refusal_messages.py FixturePrivacyTests`: `Ran 1 test in 1.313s`; `OK`.
`portable fixture: 2166 rows; 67 shared contexts; 172 shared plain file texts; 7419170 bytes`.
`5891795 versus regenerated a80df2d fixture: 2166 rows; decision-tuple diff length=0; payload keys unchanged`.
`old versus new: a80df2d refused=1705 allowed=461; head refused=1705 allowed=461; replayed payload-byte diff length=0`.
`unique replayed payload sets: refused=1334 allowed=330; both differences empty`.
The byte comparison used `python3 -u ../tmp/r2-compare-shared.py`, with identical runtime bindings for both guards and actual payload bytes compared only in memory.
The baseline pin used `python3 -u ../tmp/r2-base/gars/tests/build_refusal_corpus.py --check`.
The baseline harvest used `python3 -u ../tmp/r2-base/gars/tests/build_refusal_corpus.py` with all seven source modules green.
Baseline harvest: `Ran 19 tests in 0.799s`.
Baseline harvest: `OK`.
Baseline harvest: `Ran 7 tests in 4.622s`.
Baseline harvest: `OK`.
Baseline harvest: `Ran 10 tests in 2.083s`.
Baseline harvest: `OK`.
Baseline harvest: `Ran 24 tests in 283.145s`.
Baseline harvest: `OK`.
Baseline harvest: `Ran 17 tests in 24.173s`.
Baseline harvest: `OK`.
Baseline harvest: `Ran 8 tests in 0.314s`.
Baseline harvest: `OK`.
Baseline harvest: `Ran 16 tests in 2.755s`.
Baseline harvest: `OK`.
Baseline harvest: `harvested 2166 payloads in 67 contexts`.
`corpus test_policy_attacks: 31 rows`.
`corpus test_guard_hook: 204 rows`.
`corpus test_policy_faults: 3 rows`.
`corpus test_nonpublic_read_block: 1054 rows`.
`corpus test_pilot_doors: 238 rows`.
`corpus test_tool_schema_refusal: 8 rows`.
`corpus test_bash_lexer: 282 rows`.
`corpus registry: 333 rows`.
`corpus reported: 13 rows`.
`decision pin: 1705 refused, 461 allowed`; `OK`.

| test | file and Round 1 line | old | new | reason |
|---|---|---|---|---|
| test_07_registry_drives_advice | gars/tests/test_refusal_messages.py:173 | self.assertIn('fs.fixture', text) | Assert the dispatcher form and registry location; assertNotIn fs.fixture; retain the registered file-command assertion and add explicit command/R-092 field and rule assertions. | L-2 removes the exhaustive typed-tool list while keeping advice driven by the registry. |

GATE summary lines follow verbatim at source commit 29867dd; each command used TMPDIR, TEMP, and TMP set to the job scratch twin.
`python3 -u gars/tests/test_refusal_messages.py`: `Ran 9 tests in 147.991s`; `OK`.
`python3 -u gars/tests/test_guard_hook.py`: `Ran 7 tests in 40.935s`; `OK`.
`python3 -u gars/tests/test_policy_attacks.py`: `Ran 19 tests in 4.588s`; `OK`.
`python3 -u gars/tests/test_policy_faults.py`: `Ran 10 tests in 2.144s`; `OK`.
`python3 -u gars/tests/test_nonpublic_read_block.py`: `Ran 24 tests in 209.392s`; `OK`.
`python3 -u gars/tests/test_pilot_doors.py`: `Ran 17 tests in 63.605s`; `OK`.
`python3 -u gars/tests/test_tool_schema_refusal.py`: `Ran 8 tests in 0.605s`; `OK`.
`python3 -u gars/tests/test_bash_lexer.py`: `Ran 16 tests in 49.574s`; `OK`.
`python3 -u gars/tests/test_pilot_log.py`: `Ran 15 tests in 11.452s`; `OK`.

Mutation proof reran against the new fixture in disposable scratch copies.
Mutation (i), restored generic suffix: `Ran 1 test in 148.393s`; `FAILED (failures=1705)`.
Mutation (ii), removed one alternative keyword: `Ran 1 test in 146.749s`; `FAILED (failures=1)`.
Mutation (iii), allowed a refused payload: `Ran 1 test in 145.699s`; `FAILED (failures=1)`.
Mutation (iv), changed one rule value: `Ran 1 test in 88.863s`; `FAILED (failures=1)`.
Mutation (v), restored the misleading approval-store text: `Ran 1 test in 88.575s`; `FAILED (failures=1)`.
`python3 -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3, 6)) for p in sys.argv[1:]]; print('parsed', len(sys.argv) - 1)" gars/_system/guard_hook.py gars/_system/tool_call.py gars/_system/tools/policy.py gars/tests/build_refusal_corpus.py gars/tests/test_bash_lexer.py gars/tests/test_nonpublic_read_block.py gars/tests/test_pilot_doors.py gars/tests/test_pilot_log.py gars/tests/test_policy_attacks.py gars/tests/test_refusal_messages.py`: `parsed 10`.
`git diff --stat a80df2d -- .github evals docs/decisions gars/_system/tools/registry.json .claude gars/.claude` printed nothing.
`git diff --check` printed nothing.
The new commits' added lines, including decoded fixture strings, were read for absolute paths, home paths, user names, and system temp paths; the final fixture passes that read and the strengthened privacy test.
Not verified: the whole suite, contracts gate, evidence-of-record runs, sealed evaluations, smoke sessions, live agent behavior, live scheduler behavior, and execution on a Python 3.6 interpreter.
No network access, push, remote addition, pull request, approval, or merge was performed.

## Round 3

Test-only commit: 2383f6f, appended to bd8b5ee without rewriting history.
The scanner walks every JSON string and key, recursively parses JSON text, scans strict base64 decodings of strings at least 16 characters long, and scans every successful zlib expansion.
The same scanner reads the complete raw fixture text; decoded bytes use UTF-8 with replacement for invalid bytes.
Checks use runtime home, repository, and user identities, the generic home-prefix expression with its ubuntu exception, and only the four supplied owner-token lengths and SHA-256 digests.
Every window of each supplied length is hashed over each nonempty lowercased text, with caches for distinct text and distinct lowercase text.
Failures collect row names and categories without printing matched private content; scanning continues through the whole fixture.
The reported string count is the number of distinct texts scanned; decoded_blobs counts successful strict base64 expansions, and zlib_blobs counts successful decompressions.
Strict base64 interpretations include hexadecimal hash identifiers; they need not be intentionally encoded fixture blobs.
Plant (i) supplies the red-first evidence: the unchanged 5891795 fixture was restored only in a disposable scratch copy after the test-only commit.
`python3 -u ../tmp/r3-privacy-plants/i/gars/tests/test_refusal_messages.py FixturePrivacyTests.test_whole_fixture_recursive_privacy`: `privacy scan: strings=7809 decoded_blobs=421 zlib_blobs=74 elapsed=362.917s`; `Ran 1 test in 362.927s`; `FAILED (failures=1)`.
The committed head then passed the same test.
`python3 -u gars/tests/test_refusal_messages.py FixturePrivacyTests.test_whole_fixture_recursive_privacy`: `privacy scan: strings=7455 decoded_blobs=256 zlib_blobs=0 elapsed=49.733s`; `Ran 1 test in 49.734s`; `OK`.
Plants (ii) and (iii) each append one named row in separate disposable scratch copies; every synthetic home prefix is constructed at runtime.
Plant (ii) carries the prefix in a JSON payload with escaped slashes.
`python3 -u ../tmp/r3-privacy-plants/ii/gars/tests/test_refusal_messages.py FixturePrivacyTests.test_whole_fixture_recursive_privacy`: `privacy scan: strings=7458 decoded_blobs=256 zlib_blobs=0 elapsed=42.143s`; `Ran 1 test in 42.145s`; `FAILED (failures=1)`.
Plant (iii) carries nested JSON with the prefix in a key inside a zlib-compressed base64 blob.
`python3 -u ../tmp/r3-privacy-plants/iii/gars/tests/test_refusal_messages.py FixturePrivacyTests.test_whole_fixture_recursive_privacy`: `privacy scan: strings=7461 decoded_blobs=257 zlib_blobs=1 elapsed=46.973s`; `Ran 1 test in 46.976s`; `FAILED (failures=1)`.
Both added-row failures name the corresponding planted row.

GATE summary lines follow verbatim; every Python command sets TMPDIR, TEMP, and TMP to the job scratch twin.
`python3 -u gars/tests/test_refusal_messages.py`: `privacy scan: strings=7455 decoded_blobs=256 zlib_blobs=0 elapsed=61.488s`; `Ran 10 tests in 116.887s`; `OK`.
`python3 -u gars/tests/test_guard_hook.py`: `Ran 7 tests in 19.881s`; `OK`.
`python3 -u gars/tests/test_policy_attacks.py`: `Ran 19 tests in 2.817s`; `OK`.
`python3 -u gars/tests/test_policy_faults.py`: `Ran 10 tests in 1.096s`; `OK`.
`python3 -u gars/tests/test_nonpublic_read_block.py`: `Ran 24 tests in 121.065s`; `OK`.
`python3 -u gars/tests/test_pilot_doors.py`: `Ran 17 tests in 38.744s`; `OK`.
`python3 -u gars/tests/test_tool_schema_refusal.py`: `Ran 8 tests in 0.331s`; `OK`.
`python3 -u gars/tests/test_bash_lexer.py`: `Ran 16 tests in 28.875s`; `OK`.
`python3 -u gars/tests/test_pilot_log.py`: `Ran 15 tests in 6.955s`; `OK`.
`python3 -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3, 6)) for p in sys.argv[1:]]; print('parsed', len(sys.argv) - 1)" gars/_system/guard_hook.py gars/_system/tool_call.py gars/_system/tools/policy.py gars/tests/build_refusal_corpus.py gars/tests/test_bash_lexer.py gars/tests/test_nonpublic_read_block.py gars/tests/test_pilot_doors.py gars/tests/test_pilot_log.py gars/tests/test_policy_attacks.py gars/tests/test_refusal_messages.py`: `parsed 10`.
`git diff --stat a80df2d -- .github evals docs/decisions gars/_system/tools/registry.json .claude gars/.claude` printed nothing.
`git diff --check` printed nothing.
The new added lines were read for private literals; no owner token, home path, or user name was authored into the test, log, or commit messages.
The fixture and production guard files are unchanged in Round 3; the GATE decision pin still covers all 2166 rows.
Not verified: the whole suite, contracts gate, evidence-of-record runs, sealed evaluations, smoke sessions, live agent behavior, live scheduler behavior, and execution on a Python 3.6 interpreter.
The five refusal-message mutations and old-versus-new comparison were not repeated in this test-only round; their Round 2 evidence remains above.
No network access, push, remote addition, pull request, approval, or merge was performed.

## Round 4

This fix round appends to 2220f2a; no earlier commit was amended or rewritten.
Red-first test commit: 587a5f6; `python3 -u gars/tests/test_refusal_messages.py ReviewMessageTests`: `Ran 3 tests in 0.012s`; `FAILED (failures=4)`.
The four expected failures cover the unknown typed name with valid and invalid JSON and both read-only substring cases.
The unknown-name check still precedes JSON decoding, and its refusal retains exit 2, type tool_refusal, field args, and rule R-092.
F1 catches that named-tool Refusal separately and uses the same registry-derived next step as unregistered commands.
F2 changes only the leads to describe the matched command substrings, preserving both checks, their order, and the ruled Next sentence.
Focused green run, `python3 -u gars/tests/test_refusal_messages.py ReviewMessageTests`: `Ran 3 tests in 0.011s`; `OK`.
Builder and fixture commit: 3120436, regenerated against the unchanged a80df2d system tree in a disposable copy in the job's scratch folder.
The builder ran its seven baseline harvest modules; their summaries, in source order, follow.
Baseline harvest test_policy_attacks: `Ran 19 tests in 0.222s`; `OK`.
Baseline harvest test_guard_hook: `Ran 7 tests in 1.146s`; `OK`.
Baseline harvest test_policy_faults: `Ran 10 tests in 0.896s`; `OK`.
Baseline harvest test_nonpublic_read_block: `Ran 24 tests in 253.194s`; `OK`.
Baseline harvest test_pilot_doors: `Ran 17 tests in 23.930s`; `OK`.
Baseline harvest test_tool_schema_refusal: `Ran 8 tests in 0.351s`; `OK`.
Baseline harvest test_bash_lexer: `Ran 16 tests in 3.296s`; `OK`.
`harvested 2179 payloads in 67 contexts`.
The baseline system diff against a80df2d printed nothing before the regenerated fixture was copied back.
The existing rows were compared in order with 2220f2a using (name, exit, type, field, rule, dispatcher).
`existing decision tuples: 2166 rows; diff length=0`.
`new rows: 11 registry; 2 reported; 13 total`.

| new row | guard (exit, type, field, rule) | dispatcher (exit, type, field, rule) |
|---|---|---|
| fs.list-two-paths | 0, None, None, None | 0, None, None, None |
| fs.read-two-paths | 0, None, None, None | 0, None, None, None |
| fs.head-two-paths | 0, None, None, None | 0, None, None, None |
| fs.tail-two-paths | 0, None, None, None | 0, None, None, None |
| fs.metadata-two-paths | 0, None, None, None | 0, None, None, None |
| fs.checksum-two-paths | 0, None, None, None | 0, None, None, None |
| fs.lines-two-paths | 0, None, None, None | 0, None, None, None |
| fs.search-two-paths | 0, None, None, None | 0, None, None, None |
| fs.inspect-two-paths | 0, None, None, None | 0, None, None, None |
| fs.find-two-paths | 2, tool_refusal, args.paths, R-092 | 2, tool_refusal, args.paths, R-092 |
| fs.find-expression | 2, tool_refusal, args.paths, R-092 | 2, tool_refusal, args.paths, R-092 |
| unknown-typed-tool | 2, tool_refusal, args, R-092 | 2, tool_refusal, args, R-092 |
| read-gitleaks-false | 2, None, None, None | 0, None, None, None |

All ten file commands now have a two-path row, and find also has an expression after its path.
The two reported rows cover the unknown typed tool and the read-only hooks.gitleaks/false command.
`corpus registry: 344 rows`.
`corpus reported: 15 rows`.
`corpus test_bash_lexer: 282 rows`.
`corpus test_guard_hook: 204 rows`.
`corpus test_nonpublic_read_block: 1054 rows`.
`corpus test_pilot_doors: 238 rows`.
`corpus test_policy_attacks: 31 rows`.
`corpus test_policy_faults: 3 rows`.
`corpus test_tool_schema_refusal: 8 rows`.
`fixture totals: refused=1709 allowed=470 rows=2179`.
`old versus new: a80df2d refused=1709 allowed=470; head refused=1709 allowed=470; replayed payload-byte diff length=0`.
`unique replayed payload sets: refused=1338 allowed=339; both differences empty`.
The comparison replayed the new fixture against a80df2d and the final guard using shared runtime bindings, comparing the actual payload bytes in memory.
Wording, moved assertions, and inventory after-column commit: aa900bd.

| test | file and Round 3 line | old | new | reason |
|---|---|---|---|---|
| test_no_verify_equals | gars/tests/test_policy_attacks.py:84 | --no-verify, including --no-verify=VALUE | this command contains --no-verify, which can disable the required secret scan | F2 reports the actual substring trigger; the existing refusal and exit assertions remain. |
| test_gitleaks_false | gars/tests/test_policy_attacks.py:87 | git config hooks.gitleaks false disables the required secret scan | this command contains hooks.gitleaks and false, a combination that can disable the required secret scan | F2 covers read-only commands too; the existing refusal and exit assertions remain. |
| test_fixture_is_readable_and_portable | gars/tests/test_refusal_messages.py:242 | self.assertEqual(count, 2162) | self.assertEqual(count, 2175) | The thirteen added payloads are JSON objects; all encoding, privacy, malformed-row, and payload-key assertions remain. |

F4, projects/_index.md: the original next step named a Bash command the guard refuses, so the message now assigns that rebuild to the human.
F4, files.csv: the rewrite retained the machine-owned explanation and samples.csv cohort action but combined them into two sentences with an explicit Next marker and rule citation, exceeding the instruction to retain the original text.
F4, samplesheet: the rewrite retained the emitter and design-edit action but shortened the explanation and marked the action Next with a rule citation, exceeding the instruction to retain the original text.
F4, template catch-all: the old template-only description and git-pull advice did not fit machine-owned dataset and pilot-log state, so the wording identifies both classes and points to the owning writer or human template update.
F4 is recorded here only; none of those four messages changed in Round 4.

GATE summary lines follow verbatim for the bytes committed as aa900bd; the final documentation commit changes this build log and aligns the seven later inventory line references with the two-line handler insertion.
Every Python command used TMPDIR, TEMP, and TMP set to the job scratch twin from the repository root.
`python3 -u gars/tests/test_refusal_messages.py`: `Ran 14 tests in 217.606s`; `OK`.
`python3 -u gars/tests/test_guard_hook.py`: `Ran 7 tests in 22.636s`; `OK`.
`python3 -u gars/tests/test_policy_attacks.py`: `Ran 19 tests in 3.001s`; `OK`.
`python3 -u gars/tests/test_policy_faults.py`: `Ran 10 tests in 1.098s`; `OK`.
`python3 -u gars/tests/test_nonpublic_read_block.py`: `Ran 24 tests in 118.263s`; `OK`.
`python3 -u gars/tests/test_pilot_doors.py`: `Ran 17 tests in 37.350s`; `OK`.
`python3 -u gars/tests/test_tool_schema_refusal.py`: `Ran 8 tests in 0.360s`; `OK`.
`python3 -u gars/tests/test_bash_lexer.py`: `Ran 16 tests in 32.001s`; `OK`.
`python3 -u gars/tests/test_pilot_log.py`: `Ran 15 tests in 7.862s`; `OK`.
`privacy scan: strings=7467 decoded_blobs=247 zlib_blobs=0 elapsed=90.497s`.
`decision pin: 1709 refused, 470 allowed; OK`.
Both fixture privacy tests passed, including the recursive raw-text, JSON, strict-base64, and zlib scan.

Each mutation ran in a disposable copy in the job's scratch folder, leaving the committed guard and fixture unchanged.
Mutation (i), restored the generic suffix; `RefusalMessagesTests.test_03_dynamic_next_steps`: `Ran 1 test in 125.439s`; `FAILED (failures=1709)`.
Mutation (ii), removed one alternative keyword; `RefusalMessagesTests.test_02_static_next_steps`: `Ran 1 test in 123.497s`; `FAILED (failures=1)`.
Mutation (iii), allowed a previously refused payload; `RefusalMessagesTests.test_01_decision_pin`: `Ran 1 test in 119.459s`; `FAILED (failures=1)`.
Mutation (iv), changed one record rule value; `RefusalMessagesTests.test_01_decision_pin`: `Ran 1 test in 119.538s`; `FAILED (failures=1)`.
Mutation (v), restored the misleading approval-store text; `RefusalMessagesTests.test_04_approval_store_is_not_a_generic_path`: `Ran 1 test in 119.037s`; `FAILED (failures=1)`.
Mutation (f3), allowed exactly find _system _references; `RefusalMessagesTests.test_01_decision_pin`: `Ran 1 test in 124.109s`; `FAILED (failures=1)`.
`python3 -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3, 6)) for p in sys.argv[1:]]; print('parsed', len(sys.argv) - 1)" gars/_system/guard_hook.py gars/_system/tool_call.py gars/_system/tools/policy.py gars/tests/build_refusal_corpus.py gars/tests/test_bash_lexer.py gars/tests/test_nonpublic_read_block.py gars/tests/test_pilot_doors.py gars/tests/test_pilot_log.py gars/tests/test_policy_attacks.py gars/tests/test_refusal_messages.py`: `parsed 10`.
`git diff --stat a80df2d -- .github evals docs/decisions gars/_system/tools/registry.json .claude gars/.claude` printed nothing.
`git diff --check` printed nothing.
The new commits' added lines were read for private content, including the plain fixture, runtime identities, and owner-token digests; the source and evidence text were also read directly.
Not verified: the whole suite, contracts gate, evidence-of-record runs, sealed evaluations, smoke sessions, live agent or scheduler behavior, and execution on a Python 3.6 interpreter.
No network, push, remote addition, pull request, approval, or merge was performed.
Decision records and the change report remain for Glitch.

## Round 5

This round appends to 4a70851 on build/gars-guard-messages-clean; the older build/gars-guard-messages branch was not changed.
Red-first commit: 32c0f54, containing only the replay-binding regression test.
`python3 -u gars/tests/test_refusal_messages.py ReplayBindingsTests` at that commit: `Ran 1 test in 0.003s`; `FAILED (errors=2)`.
Both subcases failed with KeyError for TMPDIR after TMPDIR, TEMP, and TMP were removed in process; the context manager restored the environment afterward.
Fix commit: 2f8c84e, containing only the replay binding and the two stale protected-path assertions.
D2 binds JOB_SCRATCH to resolved tempfile.gettempdir(), the same temporary-directory choice used by replay, instead of requiring a TMPDIR environment key.
The new test covers both repository and materialized roots, payload substitution, absence of all three variables, and restoration of the original environment.
`python3 -u gars/tests/test_refusal_messages.py ReplayBindingsTests` after the fix: `Ran 1 test in 0.002s`; `OK`.
D1 retains the exit-2 assertion and now checks the workspace boundary and R-094; the adjacent Row 15 assertion was also stale.

| test | file and Round 4 line | old | new | reason |
|---|---|---|---|---|
| test_resolved_symlink_escape | gars/tests/test_protected_paths.py:53 | outside the workspace | inside the workspace root | Match the current resolved-write boundary explanation; the exit-2 assertion remains. |
| test_resolved_symlink_escape | gars/tests/test_protected_paths.py:54 | Row 15 | R-094 | The old separate-hook explanation was removed; assert the rule that refuses this write while retaining exit 2. |

The audit searched all test modules under gars/tests and tests, including indirect guard callers and the shared pilot fixture helper, and read the guard and dispatcher calls with their refusal assertions.
An AST scan compared assertion string fragments with the baseline and current refusal messages, alongside searches for the removed explanations and shared message constants.
`assertion audit: 83 test modules parsed; 3697 assertion calls inspected`.
The remaining old-only fragments were config/reference keys, a command supplied as input, and an intentional negative assertion against approval-store wording; none was another stale refusal expectation.
The module runs below include every direct guard/dispatcher caller found by the audit, the indirect approval caller, the policy role tests, and the existing GATE modules.
The tests/run_tests.py invocation selected GuardHookTests only, collected eight tests, and did not invoke whole-suite discovery.

Mode B exported TMPDIR, TEMP, and TMP to the job scratch twin for the full refusal-message module.
`python3 -u gars/tests/test_refusal_messages.py`: `Ran 15 tests in 109.882s`; `OK`.
Mode C removed all three variables with env -u and used an uncommitted sitecustomize.py in the job's scratch folder, supplied through PYTHONPATH, to bind Python's temporary-directory cache there before the test module loaded.
This startup file did not set any of the three environment variables or change a guard, fixture, test assertion, or replay function; it kept all temporary writes inside the required job scratch folder.
`env -u TMPDIR -u TEMP -u TMP python3 -u gars/tests/test_refusal_messages.py`: `Ran 15 tests in 111.031s`; `OK`.
`mode C startup: TMPDIR, TEMP and TMP absent; temp cache bound to job scratch`.
Both modes collected all 15 tests and passed the same unchanged decision pin.
Mode B: `decision pin: 1709 refused, 470 allowed; OK`.
Mode B: `privacy scan: strings=7467 decoded_blobs=247 zlib_blobs=0 elapsed=39.435s`.
Mode C: `decision pin: 1709 refused, 470 allowed; OK`.
Mode C: `privacy scan: strings=7467 decoded_blobs=247 zlib_blobs=0 elapsed=40.233s`.

The remaining GATE and audit module summary lines follow verbatim; every one used TMPDIR, TEMP, and TMP set to the job scratch twin.
`python3 -u gars/tests/test_guard_hook.py`: `Ran 7 tests in 23.389s`; `OK`.
`python3 -u gars/tests/test_policy_attacks.py`: `Ran 19 tests in 3.022s`; `OK`.
`python3 -u gars/tests/test_policy_faults.py`: `Ran 10 tests in 1.252s`; `OK`.
`python3 -u gars/tests/test_nonpublic_read_block.py`: `Ran 24 tests in 127.485s`; `OK`.
`python3 -u gars/tests/test_pilot_doors.py`: `Ran 17 tests in 39.725s`; `OK`.
`python3 -u gars/tests/test_tool_schema_refusal.py`: `Ran 8 tests in 0.410s`; `OK`.
`python3 -u gars/tests/test_bash_lexer.py`: `Ran 16 tests in 35.542s`; `OK`.
`python3 -u gars/tests/test_pilot_log.py`: `Ran 15 tests in 9.104s`; `OK`.
`python3 -u gars/tests/test_protected_paths.py`: `Ran 6 tests in 42.365s`; `OK`.
`python3 -u gars/tests/test_status_writer.py`: `Ran 10 tests in 5.647s`; `OK`.
`python3 -u gars/tests/test_stage03_execution.py`: `Ran 17 tests in 8.652s`; `OK`.
`python3 -u gars/tests/test_planted_faults.py`: `Ran 3 tests in 12.653s`; `OK`.
`python3 -u gars/tests/test_data_class_required.py`: `Ran 4 tests in 3.265s`; `OK`.
`python3 -u gars/tests/test_session_state_closed.py`: `Ran 11 tests in 12.329s`; `OK`.
`python3 -u gars/tests/test_lifecycle_faults.py`: `Ran 1 test in 50.323s`; `OK`.
`python3 -u gars/tests/test_closed_project_outputs.py`: `Ran 12 tests in 25.348s`; `OK`.
`python3 -u gars/tests/test_lifecycle_cancel.py`: `Ran 11 tests in 1.859s`; `OK`.
`python3 -u gars/tests/test_manifest_groups.py`: `Ran 19 tests in 66.779s`; `OK`.
`python3 -u gars/tests/test_approval_forgery.py`: `Ran 12 tests in 0.343s`; `OK`.
`python3 -u gars/tests/test_role_profiles.py`: `Ran 6 tests in 0.177s`; `OK`.
`python3 -u tests/run_tests.py GuardHookTests`: `Ran 8 tests in 5.721s`; `OK`.

`python3 -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3, 6)) for p in sys.argv[1:]]; print('parsed', len(sys.argv) - 1)" gars/_system/guard_hook.py gars/_system/tool_call.py gars/_system/tools/policy.py gars/tests/build_refusal_corpus.py gars/tests/test_bash_lexer.py gars/tests/test_nonpublic_read_block.py gars/tests/test_pilot_doors.py gars/tests/test_pilot_log.py gars/tests/test_policy_attacks.py gars/tests/test_protected_paths.py gars/tests/test_refusal_messages.py`: `parsed 11`.
`git diff 4a70851 -- gars/tests/fixtures` printed nothing; the fixture was not regenerated and remains byte-identical.
`git diff 4a70851 -- gars/_system` printed nothing.
`git diff --stat 4a70851 -- .github evals docs/decisions gars/_system/tools/registry.json .claude gars/.claude` printed nothing.
The original protected-path comparison from a80df2d reports only decision 0175 and its index entry, 106 inserted lines already present at 4a70851; this round adds no protected-path changes.
`git diff --check` printed nothing.
The new commits' added lines were read for private content; no literal absolute path, home path, user name, system temp path, or owner-token digest match was found.
The final evidence commit changes only this build log and leaves every tested source byte unchanged.
Not verified in this round: the whole suite, a Linux-host rerun, the system-default temp location without the scratch-only startup file, execution on a Python 3.6 interpreter, contracts/evidence-of-record/evaluation runs, or live agent and scheduler behavior.
The six prior mutation witnesses and the baseline-versus-head payload comparison were not repeated in this test-only round; their Round 4 evidence remains above, and both current replay modes preserve every pinned decision.
No network access, push, remote addition, pull request, approval, merge, or history rewrite was performed.

## Round 6

This round appends to 7776585 on build/gars-guard-messages-clean; the older build/gars-guard-messages branch was not changed.
At 7776585, `python3 -u gars/tests/test_secret_containment.py SecretContainmentTests.test_committed_tree_has_zero_findings`: `Ran 1 test in 14.968s`; `FAILED (failures=1)`.
The real scanner found the captured cache-key assignment; its value is a synthetic downstream-v1 idempotency hash, not a credential.
The same value also appears in the captured reproducibility manifest, so both submit.sh and reproducibility/manifest.json are omitted from the two target snapshots.
The affected captured files belong to prepared/gars/projects/pilot/02_bioinformatics/rnaseq_bulk/02_rnaseq-de in the pilot-doors fixture.
A disposable copy in the job's scratch folder was checked out at a80df2d, and its system-tree diff against a80df2d printed nothing.
A scratch-only copy of the builder harvested the baseline pilot-doors module with the original row numbering and selected exactly test_pilot_doors-1329 and test_pilot_doors-1341.
For each selected row it removed both files from the captured state, materialized that state in fresh scratch, asserted both files absent, and judged the relocated json.dumps payload with the unchanged baseline guard and dispatcher refusal path.
The baseline pilot-doors harvest: `Ran 17 tests in 7.948s`; `OK`.
`harvested 2 payloads in 2 contexts`.
`baseline omitted-file proof: test_pilot_doors-1329: {"dispatcher": null, "exit": 2, "field": null, "rule": null, "type": null}; tuple diff length=0`.
`baseline omitted-file proof: test_pilot_doors-1341: {"dispatcher": null, "exit": 0, "field": null, "rule": null, "type": null}; tuple diff length=0`.
`baseline omitted-file proof: 2 rows; both payload templates identical; OK`.
Both comparisons passed before the working fixture was edited; a differing decision would have stopped D3 without a fixture commit.
Fixture-only commit: 300657b, changing exactly two JSONL lines.
The first row's two captured texts had no other references and were removed from file_texts with their file entries.
The second row's two captured texts are referenced by four later snapshots; their shared text values are now empty strings, and both file entries are removed from the target snapshot.
Those four later snapshots retain empty files outside their active workspace; their serialized rows, lookup identifiers, and all other captured values stay unchanged.
Existing context and shared-text lookup identifiers are retained so the other rows require no byte changes.
`byte-identical fixture rows: 2177; changed rows: test_pilot_doors-1329, test_pilot_doors-1341`.
`removed cache-key values: absent from the fixture and every other tracked file; OK`.
Every row's payload, exit, type, field, rule, and dispatcher decision remains unchanged.
After committing the fixture, `python3 -u gars/tests/test_secret_containment.py SecretContainmentTests.test_committed_tree_has_zero_findings`: `Ran 1 test in 10.360s`; `OK`.
`committed-tree gitleaks: 0 findings`.
The committed-tree check used the installed real gitleaks and the unchanged gars/.gitleaks.toml; no allowlist or scanner bypass was added.

GATE and additional module summary lines follow verbatim for the bytes committed as 300657b; the final evidence commit changes only this build log.
Every Python command used TMPDIR, TEMP, and TMP set to the job scratch twin, and every command ran from the repository root.
`python3 -u gars/tests/test_refusal_messages.py`: `Ran 15 tests in 123.836s`; `OK`.
`python3 -u gars/tests/test_guard_hook.py`: `Ran 7 tests in 21.645s`; `OK`.
`python3 -u gars/tests/test_policy_attacks.py`: `Ran 19 tests in 2.533s`; `OK`.
`python3 -u gars/tests/test_policy_faults.py`: `Ran 10 tests in 1.052s`; `OK`.
`python3 -u gars/tests/test_nonpublic_read_block.py`: `Ran 24 tests in 125.862s`; `OK`.
`python3 -u gars/tests/test_pilot_doors.py`: `Ran 17 tests in 35.887s`; `OK`.
`python3 -u gars/tests/test_tool_schema_refusal.py`: `Ran 8 tests in 0.352s`; `OK`.
`python3 -u gars/tests/test_bash_lexer.py`: `Ran 16 tests in 31.046s`; `OK`.
`python3 -u gars/tests/test_pilot_log.py`: `Ran 15 tests in 7.452s`; `OK`.
`python3 -u gars/tests/test_protected_paths.py`: `Ran 6 tests in 50.440s`; `OK`.
`python3 -u gars/tests/test_secret_containment.py`: `Ran 4 tests in 20.352s`; `OK`.
`privacy scan: strings=7395 decoded_blobs=243 zlib_blobs=0 elapsed=53.024s`.
`decision pin: 1709 refused, 470 allowed; OK`.
All 2179 fixture rows still replay with the same guard and dispatcher decisions, and both fixture privacy tests pass.
The whole secret-containment module also reports `committed-tree gitleaks: 0 findings` and `canary: 0/9`.

`python3 -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3, 6)) for p in sys.argv[1:]]; print('parsed', len(sys.argv) - 1)" gars/_system/guard_hook.py gars/_system/tool_call.py gars/_system/tools/policy.py gars/tests/build_refusal_corpus.py gars/tests/test_bash_lexer.py gars/tests/test_nonpublic_read_block.py gars/tests/test_pilot_doors.py gars/tests/test_pilot_log.py gars/tests/test_policy_attacks.py gars/tests/test_protected_paths.py gars/tests/test_refusal_messages.py`: `parsed 11`.
`git diff 7776585 -- gars/_system gars/.gitleaks.toml` printed nothing.
`git diff --check` printed nothing.
The new commits' added lines were read for private content, including the two changed fixture rows and this evidence text; no private path, user name, owner-token digest match, or removed cache-key value was found.
Not verified in this round: the whole suite, a Linux-host rerun, execution on a Python 3.6 interpreter, contracts/evidence-of-record/evaluation runs, or live agent and scheduler behavior.
The prior refusal mutations and full baseline-versus-head payload comparison were not repeated in this fixture-only round; both omitted-file baseline comparisons and the full current decision pin are green.
No network access, push, remote addition, pull request, approval, merge, history rewrite, system-code change, or gitleaks-configuration change was performed.


## Round 7

Work stayed on build/gars-guard-messages-r7, completing the supplied merge of public main 868a1b2019e8b5824c8aa0874dd292c53691160c with the published lane head 35aeee4.
Merge commit f8d56b5 retains public main's checks and ordering, adds next steps to the 0185 refusals, and takes public main's README and DEVELOPMENT line shapes with the loader-derived total of 1187.
The resolution retained find's one-path and declared-predicate meaning, renders predicate names from the registry, preserves the required unquoted-glob substring, and adds glob characters to the literal-quoting advice.
`baseline control-flow comparison: 6 functions; checks, order, fields and rules unchanged; OK`.
`baseline advice probes: 4 json.dumps payloads; exit 0 each; OK`.
`baseline refusal-site probes: 8 json.dumps payloads; expected exit 2, fields and R-092; OK`.
The first scratch advice probe lacked the workspace environment binding and refused its outside-root path; rerunning with the explicit workspace binding produced the four allowed results above.
At f8d56b5, `python3 -u gars/tests/test_refusal_messages.py`: `Ran 15 tests in 80.049s`; `FAILED (failures=1)`.
The static next-step check passed at that merge commit; the single failure was the old decision pin at test_nonpublic_read_block-1016, the first accepted 0185 change.
The builder and fixture were copied into a disposable copy in the job's scratch folder at 868a1b2019e8b5824c8aa0874dd292c53691160c, and the builder was invoked from the repository root against that copy's unchanged system tree.
The builder entry point is `gars/tests/build_refusal_corpus.py`; the baseline system diff was empty before and after harvesting.
The existing fixture supplies row names keyed by source and portable payload so newly inserted calls do not renumber old rows.
The builder retains Round 6's omission of the two unused pilot output files, excluding their cache-key text before any snapshot serialization.
Builder and fixture commit f950965 pins public main 868a1b2, including test_fs_vocabulary and a valid and invalid value for every registry predicate plus an undeclared predicate.
`harvested 2606 payloads in 69 contexts`.
Baseline harvest module summaries, in source order:

`test_policy_attacks`: `Ran 19 tests in 0.276s`; `OK`.
`test_guard_hook`: `Ran 7 tests in 1.657s`; `OK`.
`test_policy_faults`: `Ran 10 tests in 0.891s`; `OK`.
`test_nonpublic_read_block`: `Ran 24 tests in 231.247s`; `OK`.
`test_pilot_doors`: `Ran 17 tests in 19.475s`; `OK`.
`test_tool_schema_refusal`: `Ran 8 tests in 0.285s`; `OK`.
`test_bash_lexer`: `Ran 17 tests in 2.842s`; `OK`.
`test_fs_vocabulary`: `Ran 21 tests in 2.275s`; `OK`.

Shared decisions against 35aeee4, including every dispatcher decision:

`shared decision change: fs.find-expression: {"new": {"dispatcher": {"exit": 0, "field": null, "rule": null, "type": null}, "exit": 0, "field": null, "rule": null, "type": null}, "old": {"dispatcher": {"exit": 2, "field": "args.paths", "rule": "R-092", "type": "tool_refusal"}, "exit": 2, "field": "args.paths", "rule": "R-092", "type": "tool_refusal"}}`.
`shared decision change: test_nonpublic_read_block-1016: {"new": {"dispatcher": {"exit": 2, "field": "command", "rule": "R-092", "type": "tool_refusal"}, "exit": 2, "field": "command", "rule": "R-092", "type": "tool_refusal"}, "old": {"dispatcher": {"exit": 0, "field": null, "rule": null, "type": null}, "exit": 2, "field": null, "rule": null, "type": null}}`.
`shared decision change: test_nonpublic_read_block-1018: {"new": {"dispatcher": {"exit": 2, "field": "command", "rule": "R-092", "type": "tool_refusal"}, "exit": 2, "field": "command", "rule": "R-092", "type": "tool_refusal"}, "old": {"dispatcher": {"exit": 0, "field": null, "rule": null, "type": null}, "exit": 2, "field": null, "rule": null, "type": null}}`.
`shared decision change: test_nonpublic_read_block-1023: {"new": {"dispatcher": {"exit": 2, "field": "command", "rule": "R-092", "type": "tool_refusal"}, "exit": 2, "field": "command", "rule": "R-092", "type": "tool_refusal"}, "old": {"dispatcher": {"exit": 0, "field": null, "rule": null, "type": null}, "exit": 2, "field": null, "rule": null, "type": null}}`.
`shared decision change: test_nonpublic_read_block-1024: {"new": {"dispatcher": {"exit": 2, "field": "command", "rule": "R-092", "type": "tool_refusal"}, "exit": 2, "field": "command", "rule": "R-092", "type": "tool_refusal"}, "old": {"dispatcher": {"exit": 0, "field": null, "rule": null, "type": null}, "exit": 2, "field": null, "rule": null, "type": null}}`.
`shared rows: 2179; changed: 5 accepted; identical: 2174; unexpected decision diff length=0`.
`added rows: registry: 16`.
`added rows: test_bash_lexer: 18`.
`added rows: test_fs_vocabulary: 393`.
`new corpus: 2606 rows; 1995 refused, 611 allowed`.
All other sources added zero rows, and every one of the 2179 prior row names remains present.
Both baseline replay and head replay report the following identical source counts and totals:

`corpus test_policy_attacks: 31 rows`.
`corpus test_guard_hook: 204 rows`.
`corpus test_policy_faults: 3 rows`.
`corpus test_nonpublic_read_block: 1054 rows`.
`corpus test_pilot_doors: 238 rows`.
`corpus test_tool_schema_refusal: 8 rows`.
`corpus test_bash_lexer: 300 rows`.
`corpus test_fs_vocabulary: 393 rows`.
`corpus registry: 360 rows`.
`corpus reported: 15 rows`.
`decision pin: 1995 refused, 611 allowed; OK`.
The baseline builder's `--check` replay and the head decision-pin test compare every exit, type, field, rule and dispatcher decision exactly; both pass.

No assertion in test_fs_vocabulary needed moving: its predicate-name, operator, glob-substring, exit, field and rule assertions all pass unchanged.
The existing registry-advice test now also checks registry-derived find predicates and the new refusal alternatives without adding a test method.
Moved-assertions table:

| Test | File and line | Old | New | Reason |
|---|---|---|---|---|
| FixturePrivacyTests.test_fixture_is_readable_and_portable | gars/tests/test_refusal_messages.py:336 | self.assertEqual(count, 2175) | self.assertEqual(count, 2602) | The 427 added payloads are JSON objects; all prior key-shape, malformed-payload and privacy assertions remain. |

Pre-commit privacy gate, `python3 -u gars/tests/test_refusal_messages.py FixturePrivacyTests`: `Ran 2 tests in 38.981s`; `OK`.
`privacy scan: strings=8466 decoded_blobs=244 zlib_blobs=0 elapsed=37.768s`.
Every Python invocation used TMPDIR, TEMP and TMP bound to the job's scratch folder.

Final targeted GATE summaries:

`python3 -u gars/tests/test_refusal_messages.py`: `Ran 15 tests in 123.138s`; `OK`.
`python3 -u gars/tests/test_fs_vocabulary.py`: `Ran 21 tests in 32.419s`; `OK`.
`python3 -u gars/tests/test_bash_lexer.py`: `Ran 17 tests in 26.805s`; `OK`.
`python3 -u gars/tests/test_secret_containment.py`: `Ran 4 tests in 14.939s`; `OK`.
`python3 -u gars/tests/test_protected_paths.py`: `Ran 6 tests in 34.901s`; `OK`.
`python3 -u gars/tests/test_guard_hook.py`: `Ran 7 tests in 16.328s`; `OK`.
`python3 -u gars/tests/test_policy_attacks.py`: `Ran 19 tests in 2.166s`; `OK`.
`python3 -u gars/tests/test_policy_faults.py`: `Ran 10 tests in 0.827s`; `OK`.
`python3 -u gars/tests/test_nonpublic_read_block.py`: `Ran 24 tests in 103.614s`; `OK`.
`python3 -u gars/tests/test_pilot_doors.py`: `Ran 17 tests in 28.506s`; `OK`.
`python3 -u gars/tests/test_tool_schema_refusal.py`: `Ran 8 tests in 0.290s`; `OK`.
`python3 -u gars/tests/test_pilot_log.py`: `Ran 15 tests in 5.942s`; `OK`.
`privacy scan: strings=8466 decoded_blobs=244 zlib_blobs=0 elapsed=59.909s`.
`decision pin: 1995 refused, 611 allowed; OK`.
The real committed-tree scan after f950965 reports `committed-tree gitleaks: 0 findings`; the whole secret-containment module also reports `canary: 0/9`.

`python3 -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3, 6)) for p in sys.argv[1:]]; print('parsed', len(sys.argv) - 1)" gars/_system/guard_hook.py gars/_system/tool_call.py gars/_system/tools/policy.py gars/tests/build_refusal_corpus.py gars/tests/test_bash_lexer.py gars/tests/test_nonpublic_read_block.py gars/tests/test_pilot_doors.py gars/tests/test_pilot_log.py gars/tests/test_policy_attacks.py gars/tests/test_protected_paths.py gars/tests/test_refusal_messages.py gars/tests/test_fs_vocabulary.py`: `parsed 12`.
`python3 tests/check_counts.py`: `suite: 1187 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite`.
The initial totals check reported three claims at 1172 against the collected 1187; only those current counts were updated, retaining the historical skip-count sentence.
`git diff 868a1b2019e8b5824c8aa0874dd292c53691160c -- gars/_system/tools/registry.json .github evals docs/decisions .claude gars/.claude` shows only the inherited lane record docs/decisions/0175-guard-messages.md and its single added index row in docs/decisions/CONTEXT.md.
Registry, workflow, evaluation and settings bytes match public main; no decision record was authored or edited in this round.
`git diff 868a1b2019e8b5824c8aa0874dd292c53691160c --name-only -- gars/_system` prints only gars/_system/guard_hook.py, gars/_system/tool_call.py and gars/_system/tools/policy.py.
`git diff --check` printed nothing.
The added code, inventory and fixture lines were read for private content, including a full added-line runtime-identity and owner-token digest check; the new fixture's whole-file recursive privacy scan also passed.
The final evidence text was read before committing for the same private-content constraints.
Not verified in this round: the whole suite, a Linux-host rerun, execution on a Python 3.6 interpreter, contracts/evidence-of-record/evaluation runs, live agent or scheduler behavior, or another run of the earlier mutation plants.
No network access, push, remote addition, pull request, approval, history rewrite or other-branch change was performed.

## Owner rulings needed

None.
