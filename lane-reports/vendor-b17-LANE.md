Status: needs-review

## ROUND 6 SUMMARY FOR REVIEW (local executor, 2026-10-20 00:33 UTC; glitch-26's rulings B17-20 to B17-22 and NIT 3 on REVIEW-vendor-b17-8776055a)

Red commit 55f33a56 (tests only): Ran 193 tests, FAILED (failures=8), all in TestB17Round6.
Green commit 160dda35. Three earlier witnesses were extended to drop the new checks too: round 5's "escaped span is one exact literal" (now a read's literal beside a changed one), round 4's "call id" and round 5's "exec pair's window" (each also drops the one-window filter).
- B17-20 (MINOR 1): a gpt-6.1-sol fixture whose read holds non-ASCII text, with the literal raw, is admitted. Witness "the literal keeps non-ASCII raw" (both ensure_ascii=False turned True) is red alone.
- B17-21 (NIT 1): a CommandExecution is a source only inside exactly one exec window, and a call with more than one output admits nothing. Witnesses "one window per read" (the reviewer's W2) and "one output per call" (W6).
- B17-22 (NIT 2): the literal is ensure_ascii=False only, exactly one per read, and at a JSON value position (after `:`, `[` or `,`).
  - Refused: the ASCII-escaped form, L1 (two literals), L7 (after a previous string's closing quote), and a literal after text.
  - Witnesses "the literal is a JSON value" and "one literal per read".
  - Census by the reviewer's swap method (census_r5r.py, run unchanged, output scratchpad/b17-census-r6.out). Every one of the 108 CommandExecutions is in exactly one window, with one call and one output.
    - gpt-6-luna: 32 verbatim (26 + 2 admitted; 4 with copy hits 1, refused only by the method's short anchor) and 4 lossy.
    - gpt-6.1-sol: 60 literals (31 + 26 admitted; 3 with copy hits 1) and 12 lossy.
    - So 92 of 92 non-lossy outputs carry an admissible copy under the tightened rule.
- NIT 3: design note line 55 amended (the anchor), and section 7 gains the ruled sibling-functionResponse limit and round 6's rules and census.
- Pins: unchanged (no shape record changed; Gemini d1250532…, Codex ea250707…).
Counts (Python 3.13.2 on /usr/local/bin; modules after light-ok, the lane run under heavy bookings):
- test_scan_record: Ran 193, OK; 119 mutants red.
- test_gemini_adapter: Ran 145, OK; --witnesses Ran 115, OK.
- test_codex_adapter: Ran 56, OK; --witnesses Ran 17, OK.
- test_sidecar: Ran 157, OK (1 skipped); --process-check exit 0.
- test_scan_witness: Ran 10, OK.
- check_vendor_sources B17 exit 0; EB drive.py exit 0.
- The lane's 64-line witness run: 22 + 22 + 20 ran, 0 failed.

RESUME HERE: review stop (round 6)

## ROUND 5 SUMMARY FOR REVIEW (local executor, 2026-10-19 23:51 UTC; glitch-26's rulings B17-17 to B17-19 and NITs 2, 3, 5 on REVIEW-vendor-b17-baef7c51)

Red commit f99fd6b6 (tests only): Ran 187 tests, FAILED (failures=15, errors=19), all in the B17 classes.
Green commit 019cdc7e:
- B17-17 (MAJOR 1):
  - Census (design note section 7, census_r5.py, counts only), each CommandExecution against its own exec pair:
    - gpt-6-luna: 32 verbatim, 0 escaped, 0 double-escaped, 4 lossy.
    - gpt-6.1-sol: 0 verbatim, 60 one JSON string literal escaped once, 0 double-escaped, 12 lossy.
  - The 16 lossy outputs are middle truncations: a truncation marker, 50 to 90 percent of lines present, the first half absent.
  - Admitted, as ruled in (a): the escaped span as one JSON string literal whose single json.loads equals the read's output exactly. Its opening quote must not be escaped, and both non-ASCII forms are accepted. The 60 are all in this form.
  - Not built: no double-escape exists, so none is admitted.
  - Lossy outputs stay refused, recorded as a known limit (16 of 108).
  - Fixtures: gpt-6-luna verbatim and gpt-6.1-sol as a JSON object holding the literal, each admitted.
  - Refused, with their tests: a double-escaped output, a literal of a changed output, an escaped quote before the literal, and a middle truncation.
  - Witness "the escaped span is one exact literal".
- B17-18 (MINOR 1): `_copy_hits` counts distinct positions of the ruled line, never matches.
  - The reviewer's D1 to D4b: D1 and D2 are admitted, and D3, D4 and D4b refuse their exec output.
  - Witnesses "a position counts once" (the dedupe dropped) and "every position counts" (the count capped at one).
- B17-19 (NIT 1): an exec output's sources are only the CommandExecutions between its own exec call's line and its own line.
  - Witness "the exec pair's window".
  - The reviewer's B1 now refuses the read-less exec's output.
  - The call-id witness now drops both id lookups, the tool's and the window's.
- NIT 2:
  - P2: the CommandExecution's record must hold payload.type item_completed (RECORD keys may be dotted).
  - P10: each shape names its file kinds, so no rollout shape reads a stream file.
  - O25: a functionResponse inside a toolCalls entry's result must carry that entry's id (a position anchor).
  - Each has a data witness.
  - Risk for review: if Gemini ever records sibling responses inside one entry's result (updateMessagesFromHistory, design note 1.3), that copy now counts as a second, unadmitted copy of the line, and the record refuses.
- NIT 3: test_the_copy_and_wrapped_schema_refuses.
  - The reviewer's mutants are killed: C (`_copy_ok` always True) fails 6 subtests, and H (the wrapped schema dropped) fails 4.
  - Both were applied in scratch copies.
- NIT 5: the rollout CommandExecution's tool is kind "argv" (list form only). Witness "the argv's list form"; P7 refuses.
- NIT 4: recorded, no change.
- Pins moved, each because its records changed: Gemini d1250532… (anchors, kinds), Codex ea250707… (argv, payload.type, kinds). drive.py and check_vendor_sources.py are unchanged.
- The reviewer's probe_r4 on 019cdc7e:
  - C0, D1, D2, B2, B6, B7 and B9 are admitted.
  - D3, D4, D4b and D5 refuse the extra copy.
  - B1, B3, B4, B5, B8 and B10 refuse.
  - P1 to P10 refuse.
Counts (each module after light-ok, the lane run under mac_slot run --kind heavy; Python 3.13.2 on /usr/local/bin):
- test_scan_record: Ran 187, OK; 113 mutants red.
- test_gemini_adapter: Ran 145, OK; --witnesses Ran 115, OK.
- test_codex_adapter: Ran 56, OK; --witnesses Ran 17, OK.
- test_sidecar: Ran 157, OK (1 skipped); --process-check exit 0.
- test_scan_witness: Ran 10, OK.
- check_vendor_sources B17 exit 0; EB drive.py exit 0.
- The lane's 64-line witness run: 22 + 22 + 20 ran, 0 failed.
Integration: the round 4 merge int/vendor-b17-merge-r4-20261019 is at 9c0b8861 (dc3c1e02 + baef7c51). Its checks were all green before round 5: B17/EB exit 0, the six modules and test_vendor_envelopes OK, test_run_take Ran 68 OK, build_draft and copy_manifest --check ok, and the 66 witness lines 0 failed. Round 5's head merges into it as a second commit.

(round 5's stop, superseded by round 6's line above: review stop (round 5))

## ROUND 4 SUMMARY FOR REVIEW (local executor, 2026-10-19 23:16 UTC; glitch-26's rulings B17-16a to B17-16d, MINOR 1 and the NITs, on REVIEW-vendor-b17-dd2d0398)

Red commit 7a797ec9 (tests only): the Codex rollout fixtures in the census's real shape (custom_tool_call `exec` with a string input, CommandExecution with source unified_exec_startup, custom_tool_call_output as input_text items; no record text copied); TestB17Round4 and the reshaped round 1 to 3 tests. Run on 7a797ec9: Ran 176 tests, FAILED (failures=20, errors=12), all in the B17 classes.
Green commit 2f267f7a:
- B17-16a: the rollout CommandExecution admits on its own argv again, a joined shape (copies "same", aggregated_output, at payload.item of an event_msg), its wrapper pinned to [/bin/bash, -lc, script] (tool `flags`); witness "16a the CommandExecution's -lc"; refusal subtests for another file and a nested shell.
- B17-16b: a copy shape (`copy_of`, tool kind "copy"): a custom_tool_call_output admits the ruled line only inside a verbatim copy of the aggregated_output of a CommandExecution that 16a admits in the same file, its call a custom_tool_call `exec` of the same call id; the record's "nowhere else" guard still counts every copy of the line. Witnesses, each red alone: an admitted read in the file, the span is a verbatim copy, the exec tool, the call id, nothing else in the output.
- B17-16c: admission tests (exec output equal to, around and after the copy; probe U1 and U2 now ruled=[2] and ruled=[3, 4]); refusal tests: no admitted read in the file, a read of another file, a changed span, another custom tool (`wait`), a mismatched call id, the line again outside the copy.
- B17-16d: design note section 6. Both arm O models are code_mode_only in the pinned catalog (models-manager/models.json lines 177/193 and 524/540; core/src/tools/mod.rs:75-97; spec_plan.rs:838-850; code-mode-protocol lib.rs:54-55, description.rs:262-263), and the committed w-o7 to w-o14 rollouts hold 97 custom_tool_call `exec` records, 97 custom_tool_call_output records and no function_call or function_call_output. So both function_call shapes are removed, and round 3's exec_command `shell` and `tty` checks (tool `shell_arg`, `refuse`) went with them.
- NIT 2 (folded): each position is (path, record), the record's top-level `type` among the named values (Gemini stream tool_use/tool_result, messages gemini/user, Codex item.started/item.completed, event_msg, response_item); witnesses "NIT 2 a stream item's event type" and "NIT 2 a response's message type".
- Pins moved, each because its records changed: Gemini READ_SHAPES 0ee23c45... (record types, copy_of), Codex 906ab0ba... (B17-16, NIT 2). drive.py and check_vendor_sources.py are unchanged.
Recorded (NIT 3, NIT 4, and round 4's limit):
- NIT 3: the Codex stream cannot see `tty`. A tty exec's command_execution is held only by its CRLF bytes.
- Round 4's limit: the same now holds in the rollout. `tty` is inside the exec script's text, which no shape reads, and the reviewer's O2 (a function_call with tty true beside an LF CommandExecution) is admitted on the CommandExecution's own argv. No real record holds a function_call.
- NIT 4: B17-11 widens one Claude case. A tool_use copy nested off message.content no longer counts as a second copy of its id. This is the ruling as written, and the census shows no nested block in the 151 committed arm A walks.
- NIT 1 is moot under 16a. NIT 5 needs nothing.
MINOR 1, the athena rescan with 2f267f7a's scan_record and drive.scan_read_shapes for arm G, nothing printed but paths, lines, key paths and booleans:
- How it ran: a git archive of evals/gap-study-4 plus the doc, in /home/javier/b17-rescan.8LGEiMcA. Each walk folder was copied into that folder before scanning, and the scanner was the pinned gitleaks 8.30.1. The scratch folder was removed afterwards and nothing else was touched. drive.walk_files refused each held folder, so per-file kinds were used, and every file had a kind.
- w-g9 (child w-gZYiruEu): 40 files, ruled [], refused turn-1.jsonl:198, session/native-turn-1.jsonl:463 and session/native-turn-2.jsonl:463, each generic-api-key.
  - turn-1.jsonl:198: a tool_result with the line once at `output`.
  - Both native files at line 463: a gemini message with the line once at `toolCalls.*.resultDisplay`. The entry's one functionResponse output (40,257 characters) does not hold it; the display is 1,354,158 characters.
  - The matching call, one copy, is a run_shell_command whose command fails _ruled_bash. It is one segment, it tokenises, its first word is off the allow-list, and it does not name the doc. It has no newline, `#`, substitution, unquoted backslash or shell token.
  - So the stream and session shapes are the designed ones. The command is not a read of the doc that OD57 admits, and the refusal holds as Claude's Bash rule would hold it. No shape changed (reported to glitch-26).
- w-g3, w-g5 and w-g7: 34 files each, ruled [] and refused [].
Counts (light-ok for each module, the lane run under mac_slot run --kind heavy; /usr/local/bin first on PATH, Python 3.13.2), on the tree committed as 2f267f7a:
- test_scan_record: Ran 176, OK; 106 mutants red.
- test_gemini_adapter: Ran 145, OK; --witnesses Ran 115, OK.
- test_codex_adapter: Ran 56, OK; --witnesses Ran 17, OK.
- test_sidecar: Ran 157, OK (1 skipped); --process-check exit 0.
- test_scan_witness: Ran 10, OK.
- check_vendor_sources B17 (the round's files) exit 0; EB drive.py exit 0.
- The reviewer's probe_r3: U1 ruled [2], U2 ruled [3, 4], U3 ruled [3], U4 refused [2]. O1 to O4 are admitted on the CommandExecution's own argv (16a). Every other over-admission attempt is still refused, apart from O23, O24, O25, O29, O31, O41, O42 and O44, admitted as before.
- The lane's witness run: all 64 command lines in three heavy bookings, 22 + 22 + 20 ran, 0 failed.
Left unrun (athena's): the adapters' generated sweeps and the full suite. The integration merge clone vendor-int-b17-20261019 was stopped as ruled: merge head 4fc1322a and the B17 merge 9b9e71fc (amended to resolve test_vendor_envelopes' edit D pin) stand untouched, to be redone on top of round 4.

(round 4's stop, superseded by round 5's line above: review stop (round 4))

## ROUND 3 SUMMARY FOR REVIEW (local executor, 2026-10-19 22:20 UTC; glitch-26's rulings B17-10 to B17-15 on REVIEW-vendor-b17-a051f6e3)

Red commit 2d707249 (tests only): forged nested call/result nodes on each arm and file kind (Gemini stream, Gemini session, Codex stream, Codex rollout) and on the Claude path (the reviewer's probe_claude_nested record); exec_command's shell argument; tty output with LF and CRLF; debug-mode output; grep_search; PTY CRLF; read_file's resultDisplay; the image shell; a swapped call-site argument; each with a witness. Run on 2d707249: Ran 153 tests, FAILED (failures=29, errors=4), every one in TestB17Round3, TestB17Round3Wiring or the reshaped TestB17ReadShapes wrapper witnesses; every other test green.
Green commit a7760094:
- B17-10: a read shape's nodes are found only at fixed record positions (`at` paths from the record's root, replacing `under`): Gemini stream the line itself; Gemini session calls at a message's toolCalls[*], functionResponse parts at an entry's result[*], a user turn's content[*], and the same under $patch and $patch.updates[*]; Codex stream the line's `item`; rollout the line's `payload` and `payload.item`. Nothing inside a call's arguments is a call or a result.
- B17-11: the Claude path reads tool_use and tool_result blocks only at message.content[*] (_CLAUDE_AT), and the record's own toolUseResult/tool_use_result only when every such top-level tool_result is ruled.
- B17-12: exec_command's `shell` argument must be one of the tool's shells; a rollout CommandExecution item is now paired to its function_call (same checks) and its own argv must also be the image shell's wrapper (result "own").
- B17-13: grep_search, PTY CRLF, write_stdin, bash -lfc and debug-mode output each have a test and a witness; `tty: true` refuses whatever the line ending (tool "refuse": {"tty": true}).
- B17-14: B17_SITES binds `row` in TakeRepo._commit_step and TakeDriver.drive and `entry` in WalkRepo._commit_walk; the wrapper and shell argument admit only the arm O image's /bin/bash (box/codex/Dockerfile:18, `useradd ... --shell /bin/bash dana`), _WRAP_SHELL removed; the session resultDisplay shape admits run_shell_command only.
- B17-15: recorded, no change.
- Changed beyond the rulings' words, each forced by them: the round-1 Codex stream admission's zsh case became a /bin/bash -c case (zsh is not an image shell); the round-2 wrapper-length and wrapper-shell witnesses now carry the function_call line (a CommandExecution item's call is its function_call); the -lfc witness uses /bin/bash so the flag alone holds it; both adapters' READ_SHAPES byte pins were recomputed (Gemini 0b69a53c..., Codex e9e87e29...). drive.py is unchanged in this round.
The reviewer's probes on a7760094's tree: probe_nested A to D all refused (ruled=[]), probe_claude_nested refused, probe_more: debug-mode, cross-arm, fish shell (with and without the CommandExecution copy), tty LF and /tmp/x/bash all refused; read_file of /tmp/other/_references/environment.md still admitted (the path ends in the doc, as B17-7 rules).
B17-11 regression proof: log /private/tmp/claude-501/-Users-javrodher-glitch/53dfdf22-47a7-465a-873b-7e472f6f10e7/scratchpad/b17regress.HDds/out.log, tool and 7dc0cf9e module in scratchpad/b17regress-tool/. Every gap-study-4 walk folder on every walk/* branch of the ten gap4-walk-records-* clones, read through git ls-tree/cat-file into scratch copies, scanned by 7dc0cf9e's scan_record and by this round's (with no shapes, and with the folder's arm's shapes), the local gitleaks 8.30.0 as the rules scanner: "walk folders 159, record files 5045, findings (old) 0, files with no scan kind 0, differences 0" (159 per-folder lines, all 0/0 under all three). What it shows: no new refusal and no new admission on today's committed records. What it does not show: detection still working, since the old scanner found nothing on any folder (a count-only check found no committed walk file holding the ruled line's first 40 characters; the same gitleaks flags line 175 of the doc itself, so the scanner reads that rule). The tests and mutants carry detection.
Counts (each one foreground process; the lane run under mac_slot run --kind heavy, the others after light-ok; /usr/local/bin first on PATH, Python 3.13.2), on the tree committed as a7760094: test_scan_record Ran 153 OK, 99 mutants red; test_gemini_adapter Ran 145 OK, --witnesses 115 OK; test_codex_adapter Ran 56 OK, --witnesses 17 OK; test_sidecar Ran 157 OK (1 skipped), --process-check exit 0; test_scan_witness 10 OK; check_vendor_sources B17 (the round's files) exit 0, EB drive.py exit 0; the lane's witness run, all 64 command lines of checks.d/vendor-admission.txt in two heavy bookings: lines 1-32 ran 32, failed 0 (411 s); lines 33-64 ran 32, failed 0 (145 s).
Left unrun (athena's): both adapters' generated mutation sweeps and the full athena suite. Not touched: the athena door's twin (glitch-26's list).

(round 3's stop, superseded by round 4's line above: review stop (round 3))

## ROUND 2 SUMMARY FOR REVIEW (local executor, 2026-10-19 18:38 UTC; glitch-26's rulings B17-5 to B17-9)

Red commit 03efe11d (tests only): test_scan_record.py's shape tests now pass each arm's READ_SHAPES through read_shapes; new TestB17ReadShapes (the empty default against every OD57 fixture, the shape schema, B17-6, B17-7's four refusals, 11 witnesses) and TestB17Wiring (scan_read_shapes by arm, the three scan calls, piece B17). Run on 03efe11d: Ran 144 tests, FAILED (failures=4, errors=155), every failure and error in TestOD57OtherArms, TestB17ReadShapes or TestB17Wiring (143 "scan() got an unexpected keyword argument 'read_shapes'", 10 "module 'drive' has no attribute 'scan_read_shapes'", "'B17' is not a piece of the plan", the adapters' missing READ_SHAPES); every earlier test green.
Green commit 7cdba6b7:
- box/scan_record.py: a closed, role-named read-shape schema (no vendor word) and scan/scan_with_witness(..., read_shapes=()); OD57's five constraints in its own code; a read_file admitted only when its path names the doc; a wrapper unwrapped only as exactly [bash|zsh|sh, -lc|-c, script], the script through _ruled_bash; the one new prefix "Output: " on a Gemini shell output's first line (after its <untrusted_context> line); B17-6: every copy of a session call id must be the same name and args. With () the scan makes the same calls as before (_rules is called with two arguments, as an existing mutant test patches it).
- gemini_adapter.py (at the module's end, so the generated sweep's line keys do not move) and codex_adapter.py: READ_SHAPES, each line cited to the pinned sources; each adapter's tests pin the records' bytes (a15_read_shapes, b14_read_shapes) so their generated sweeps kill every mutant of them.
- drive.py: scan_read_shapes(row) (by the arm, through routing.PAID_HARNESSES; () for any other arm or a row whose declared harness is not its arm's) and one line `read_shapes=scan_read_shapes(row|entry),` in each of the three scan calls, nothing else.
- Piece registration: check_vendor_sources.py P2 drive.py refuses ("piece P2 edits drive.py, which is in READER_SOURCES or CODEX_SOURCES"), so B17 is registered as its own piece in the tool's own way: PIECES and ALLOWED gain "B17" (drive.py only); B17_HELPER_SHA256 f2ad5a5fae8467f8545fd55bb7295a1647d3af7568e8ec1c4a32ec9f992bd713 pins scan_read_shapes' text; b17_spans/b17_problems/without_b17 bind its exact lines (the helper after two blank lines, three keyword lines, one per scan call); edit_b_problems and without_edits read drive.py with B17's lines taken out, so every other line is still held to PRE_EDIT_B_DRIVE_SHA256 with edits B and C, unchanged; any trace of B17 off its exact form is reported. Piece EB's lines stay green; TestB17Wiring's mutants (a keyword line changed or dropped, the helper changed, another line moved) each refuse.
- checks.d/vendor-admission.txt: test_scan_record, test_sidecar, both adapters' tests, and `check_vendor_sources.py B17 drive.py box/scan_record.py gemini_adapter.py codex_adapter.py tests/check_vendor_sources.py tests/test_scan_record.py tests/test_gemini_adapter.py tests/test_codex_adapter.py checks.d/vendor-admission.txt`.
Counts, each one foreground process after mac_slot light-ok, env -i with /usr/local/bin first on PATH (Python 3.13.2), on the tree committed as 7cdba6b7: test_scan_record Ran 144, OK, 75 mutants red (11 of them B17's: the read's path, the script, the wrapper's length, shell and flag, a stream call found once, B17-6, a response's name, a joined result is its own call, the prefix's line, the tool binding); the 20 round-1 subtests green; test_gemini_adapter Ran 145 OK, --witnesses Ran 115 OK; test_codex_adapter Ran 56 OK, --witnesses Ran 17 OK; test_sidecar Ran 157 OK (1 skipped), --process-check exit 0; test_scan_witness Ran 10 OK; the lane's witness run, every command line of checks.d/vendor-admission.txt (64 lines, build_draft --check among them), 64 exit 0, 0 failed (809 s wall, .machine-reserved absent); beside it test_drive_commit 31, test_drive_ownership 44, test_walk_runner 89, test_wave4_bindings 13, test_walk_layout 14, test_rules_scanner 9, test_drive_box_seams 6, test_native_reader_registration 7, test_box_integration 61, test_drive_loop 27, test_walk_launch 49, each OK.
Left unrun (athena's): the generated mutation sweeps of both adapters (wave10-merge's 16 Gemini shards, w11a's Codex --generated-mutants) and the full athena suite.
Note for review: drive.py is in READER_SOURCES and CODEX_SOURCES; no acceptance record exists in this tree, so nothing accepted moves, but any later acceptance binds the new drive.py.

(round 2's stop, superseded by round 3's line above: review stop (round 2))

## SUMMARY FOR REVIEW (round 1, local executor, 2026-10-19 16:22 UTC)

Design (lane-reports/B17-DESIGN-NOTE.md): Gemini reads the doc through read_file and run_shell_command, Codex only through exec_command (its one shell tool family, openai_models.rs:316-320); there is no Codex file-read tool.
Shapes: Gemini stream tool_use/tool_result paired by tool_id, output carries only a shell read's stdout; Gemini session toolCalls entries (call and functionResponse result in one object, text in response.output and resultDisplay), the function-response user turn, and $patch updates; Codex stream command_execution items (call and output in one item, command a shlex-joined bash -lc wrapper); Codex rollout function_call (arguments a JSON string), function_call_output (output a string or input_text items; keys call_id, output, optional id, name, namespace, closing the cloud's open point) and event_msg item_completed CommandExecution (argv list).
Proposal: OD57's five constraints unchanged; a role-named, closed shape vocabulary in scan_record.py with no vendor word; per-arm shape records in gemini_adapter.py and codex_adapter.py; passed by the drive as a new read_shapes argument (default empty keeps today's Claude admission byte for byte). A read_file is admitted only when its path names the doc; a wrapper is unwrapped only as exactly [bash|zsh|sh, -lc|-c, script], the script then through _ruled_bash; Gemini shell output gets one extra first-line prefix, "Output: ".
Open points for glitch-26: O1 (Gemini re-appends whole messages, so "call found by its id exactly once" is proposed as exactly one distinct call per id), O2 (grep_search not admitted, as Claude's Grep is not), O4 (PTY and write_stdin output refused), O5 (zsh -lfc refused), O6 and O8 (which w-g9 files and tool, not checked: no walk record read); the athena door's list is section 4 of the note.
Red commit da83077f (tests and note; no code change): 20 subtests in 6 shape methods fail at assert_admitted's refused check, each refused with "the rules scanner's rule 'generic-api-key'" (Gemini stream 3, Gemini session tool calls 4, re-append 1, function response and $patch 2, Codex stream 4, Codex rollout 6); the 2 refusal methods are green.
Module counts: the whole test_scan_record.py, one foreground run (1 s) under env -i with Python 3.13.2 after mac_slot light-ok: Ran 109 tests, FAILED (failures=20), every failure one of the new red subtests; 53 mutants run red.
Note: under /usr/bin/python3 (3.9.6) the same module also errors in TestLeaseTokens (import drive reaches transcript_gemini's dataclass kw_only, Python 3.10+), an interpreter mismatch, not this round's change.
Deviation: no Grep tool was available in this session, so searches used shell grep over code and vendor sources only (never lane notes or the ruled doc).

(round 1's stop, superseded by round 2's line above: design stop; glitch-26 ruled the design as B17-5 to B17-9)

BLOCKED ON glitch-26: in round 1 (B17-1), a safety check refused a read-only shell grep over lane-reports/vendor-b14-LANE.md and the earlier design notes for how earlier lanes fetched the pinned Codex source (openai/codex at commit 092d3acd, as codex_usage_sources.py names it); nothing of B17-1's note or B17-2's tests is written yet; may the round go on, and from what source and by what means should the Codex arm's read shapes be read (the public openai/codex repository is outside this session's GitHub scope)?

## Progress

- 2026-10-19 15:12 UTC: branch lane/vendor-b17 made from origin/lane/vendor-admission at 7dc0cf9e (checked); round 1 starts (rulings B17-1 to B17-3).
- 2026-10-19 15:20 UTC: B17-1 begun: read box/scan_record.py (RULED_LINES 116-120, _ruled_tool 570-579, _tool_result_strings 596-618, _ruled_text 621-643) and tests/test_scan_record.py class TestOD57Ruling (1202-1356); gitleaks v8.28.0 installed for the pre-push check. Then a safety check refused a read-only grep of earlier lane reports; stopped per the lane's rule (see BLOCKED above). No change to any code or test.
- 2026-10-19 15:27 UTC: ruling B17-4 received (the round goes on; no earlier lane reports read, no openai/codex fetch; Codex record shapes read from the harness's own Codex code and tests; uncited Codex source lines become open points; Gemini from the verified 0.64.0 package, read only). Lane resumed at 6ba72b22.
- 2026-10-19 15:55 UTC: B17-1 research done, nothing written to the note or the tests yet. Read: scan_record.py, test_scan_record.py's OD57 fixtures, codex_adapter.py, transcript_codex.py, codex_native.py, codex_usage_sources.py, test_codex_native.py's fixtures, transcript_gemini.py, gemini_tool_sources.py, gemini_projection.py, gemini_session_replay.py, checks.d/w4c-cp2-sidecar-scan.txt. Gemini CLI 0.64.0 fetched by npm pack into a mktemp folder outside the clone, tarball sha256 checked equal to the pin (B17-4), read only with the Read and Grep tools. Shapes found (for the note): Gemini stream tool_use/tool_result paired by tool_id, output is the string display (gemini-Q2GRYIAK.js 12223-12229, 12351-12361; 11830-11856), so read_file never carries the doc's text there (chunk-NR7L3FXV.js 254084-254096, 314462-314470) and run_shell_command does (326232-326233); Gemini session: whole gemini messages re-appended with toolCalls[].result functionResponse {id, name, response.output} (286885-286889, 286975-287024, 334058-334073, 289967-289975), shell output wrapped in untrusted_context with an Output: prefix (326193, 326352, 274616-274620), $patch tool-result updates (287199-287265) and user functionResponse messages (333285); Codex from the harness only: exec stream command_execution items by synthetic id with aggregated_output, rollout event_msg item_completed CommandExecution (items.rs:244-281 as codex_native cites), response_item function_call_output keys not cited (an open point). Then a safety check refused a one-line shell command that would have printed the byte count of the ruled doc line; stopped per the lane's rule (see BLOCKED below). No change to any code or test.

BLOCKED ON glitch-26: in round 1 (B17-1), a safety check refused a shell command counting the bytes of line 175 of gars/_references/environment.md (the OD57 ruled line; the tests read it at test time anyway, so the round does not need that command); may the round go on to write the design note and the red tests with no shell read of that doc?

- 2026-10-19 16:22 UTC: Javier's "b17-local yes" (T101): the round resumed locally on the Mac at 67075247 (worktree branch work/b17-local-20261019); both BLOCKED lines above are answered by it. Pins checked: Codex source HEAD 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d, Gemini 0.64.0 tarball sha256 891a794e...8365e6. B17-1 note and B17-2 tests written and committed red at da83077f; B17-3 run and summary above. Nothing pushed.
- 2026-10-19 18:38 UTC: round 2 on glitch-26's rulings B17-5 to B17-9: red at 03efe11d, green at 7cdba6b7, piece B17 registered in check_vendor_sources, the lane's 64-line witness run all exit 0; the round-1 RESUME HERE line is replaced by round 2's as ruled. Nothing pushed.
- 2026-10-19 22:20 UTC: round 3 on glitch-26's rulings B17-10 to B17-15 (review a051f6e3, CHANGES): red at 2d707249, green at a7760094, the B17-11 walk-record comparison 0 differences over 159 folders and 5045 files (0 findings under either scanner), the lane's 64-line witness run all exit 0 under two heavy bookings. Nothing pushed.
- 2026-10-19 23:16 UTC: round 4 on glitch-26's rulings B17-16a to B17-16d, MINOR 1 and NIT 2 (review dd2d0398, CHANGES): red at 7a797ec9, green at 2f267f7a, design note section 6, the athena rescan of w-g9, w-g3, w-g5 and w-g7 (scratch removed), the lane's 64-line witness run all exit 0. The integration merge clone was stopped as ruled. Nothing pushed.
- 2026-10-19 23:51 UTC: round 5 on glitch-26's rulings B17-17 to B17-19 and NITs 2, 3, 5 (review baef7c51, CHANGES): the exec-output census in design note section 7, red at f99fd6b6, green at 019cdc7e, the lane's 64-line witness run all exit 0. Nothing pushed.
- 2026-10-20 00:33 UTC: round 6 on glitch-26's rulings B17-20 to B17-22 and NIT 3 (review 8776055a, CHANGES): red at 55f33a56, green at 160dda35, the reviewer's census re-run (92 of 92), the lane's 64-line witness run all exit 0. Nothing pushed.
