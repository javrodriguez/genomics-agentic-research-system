# Lane vendor-settle (Gap Study round 4): settlement of the vendor rows, legs i and ii of the freeze

Status: stages K and K2 committed (heads below); C and G may branch from the K2 head.
Clone: /Users/javrodher/aegis-builds/vendor-settle-20261021 (made with `git clone --no-local`, no alternates; branch `lane/vendor-settle` from `dry/vendor-74` = 0554fd6a0c4729295d14e25ba12678449506e727).
One writer (the K/K2 builder, an Opus 5.5 medium lane agent of glitch-f1 under Javier's standing delegation); the C (Codex) and G (Gemini) builders branch from the K2 head.
Never pushed.

## Rulings this lane builds on (quoted)

- Design: plans/gap-study-round-4/vendor-settle-DESIGN-2026-10-21.md (Glitch Brain); review: /Users/javrodher/aegis-builds/REVIEW-vendor-settle-DESIGN-2026-10-21.md.
- glitch-f1, Wed 21 Oct 21:56 EDT, "RULED under the delegation" item (4): "settlement design: T-17 option B (NC, three-leg partial check, so Codex stays accepted); T-18 Codex NC with the proxy partial check (it fires on 31 practice-walk rechecks, named); recommended_plugins not offered context; S0 upgrades to SAME only with a cited pinned-source line; T-8 NC now (no new walk); fixture copies are scanned like the walk files; a settlement addendum to the T4 table; w-g47 only if w-g14 lacks the shape; the build may base on dry/vendor-74; the design review (running) proposes a parallel split, since 22-30 builder hours makes settlement the longest pole."
- glitch-f1, Wed 21 Oct 22:01 EDT, "SETTLE DESIGN REVIEW CHANGES": "RULED: MAJOR 1 collect every <session_context> text from the raw records including $patch.updates (mutant red on w-g13 or w-g14); MAJOR 2 T-16 reads thread_settings' permission_profile (codex_native.py:96-99) and turn_context's sandbox_policy where present, green on w-o46, red on a plant; MAJOR 3 the new sweeps read decoded text, and the same blind spot in the existing context_text (check_take.py:2827-2832) is investigated read-only first ... MINORs adopted (reachable plants; T-18 Codex partial adds "no recommended_plugins section", take_config.py:255-262 reverses my earlier call; "main" spelled with the drive.py:381 cite; vendor_reach for Gemini after T-4/T-11; base dry/vendor-74). The split adopted: K skeleton (one builder, 2-3 h, merged first), then C (Codex) and G (Gemini) in parallel (7-9 h each), then V converge (2-3 h) and athena".
- glitch-f1, Wed 21 Oct 22:26 EDT, "CONTEXT-SWEEP GAP read": "RULED option A: fix before the freeze with a decoded-text sweep (keys included, the snippet carve-out kept), in lane vendor-settle as stage K2 right after the skeleton (one writer for check_take.py), with a planted escaped-newline test red first; the pins it moves (checks.d/w6j-claude-adapter.txt, test_walk_runner's R5 span, test_edited_text_file 271-310) are updated under this ruling, each update naming it; the freeze rehearsal runs after it anyway."

## Stage K: the shared skeleton (behaviour-neutral)

Commits (clock read with `date`; K built Wed 21 Oct 22:02-22:45 EDT):
- K.1 `783b98eeece1a61144223c055a26e0bd22c9be4b`: check_take.py only.
  Every one-line codex/gemini ternary at a `vendor_pending` site is two statements, with an unchanged line (`else:`, `return out`, or the `if`) between any Codex and Gemini statement, so C and G edit disjoint lines.
  Sites widened for the readers: `vendor_origin_problems`, `vendor_loaded_context_problems`, `vendor_inherited_cwd_problems`, `vendor_instruction_file_problems`, `vendor_checkout_problems`, `vendor_prompt_problems`, `vendor_denied_tool_problems` take `(path, harness, design)`; `vendor_recorded_mode_problems` takes `(path, harness, design, arm)`; `vendor_round4_problems(path, design, arm=None)` and `_vendor_road` passes `arm=arm` (test_vendor_body calls it without one; T-16's reader must treat `arm=None` itself, or read the ledger's arm).
  `VENDOR_READER_ITEMS` is one literal line per item.
  Two marked spans at the end of the T4 span (before `if __name__`).
- K.2 `42d43a2c250de0b00ce4b27d0f2116c59e2cbf22` (S1): five RECORDED take folders, `tests/fixtures/recorded-codex-w-o46`, `-w-o47`, `-w-o7`, `recorded-gemini-w-g21`, `-w-g14`, each the committed blobs of `rehearsals/<walk>/` minus `evidence/` (897,834 / 486,726 / 450,490 / 1,133,035 / 3,273,789 bytes, equal to the design's probe4 figures), each blob checked equal to the walk ref's blob in gap4-walk-records-20261019 (walk refs: w-o46 `walk/w-kbm1P3ZO` ae6bec92, w-o47 `walk/w-PhMO8vDv` 61a41792, w-o7 `walk/w-OMeE6P4y` 68fff362, w-g21 `walk/w-vNjKNXbo` e2c30e0c, w-g14 `walk/w-GDVAbBBf` ef903feb).
  README.md labels each file `RECORDED at walk <walk>, codex-cli 0.162.1.` / `gemini-cli 0.64.0.` (versions read from each ledger's `agent.version`); PROVENANCE.json per file: source, blob, sha256, bytes; walk ref and walk commit, never a dry merge sha.
  COPIED.d/vendor-settle-k.json claims every new file.
  lint_language.py skips a copy whose bytes equal its PROVENANCE sha256 (README.md and PROVENANCE.json still linted).
  DEVIATION, raised for glitch-f1: this is a lint scope change I made under ruling (4) "fixture copies are scanned like the walk files" (walk files are never linted); without it the whole-tree lint (checks.d/w8e-lint-reds.txt) gains 18 findings, all `[ratio-slash]` on `sessions/2026/10/20` paths in w-o46 session-store.json (15) and postflight.json (3). The alternative is 18+ exact-line allowlist entries. Revert = drop the lint_language.py hunk of K.2.
- K.3 `86e95b408c4971c48b40e343e9d03e02f219b2f4`: tests/vendor_settle_codex.py and tests/vendor_settle_gemini.py (SAME_FIRES, CLEAN_CASES, NC_CASES, empty); test_vendor_check.py merges them (`SETTLE_MODULES`, `SAME_FIRES = merged("SAME_FIRES")`) with VP-settle, VP-provenance and VP-plant; tests/vendor_plant.py (the plant helper); test_round4.py HELPERS names the three helpers; checks.d/vendor-settle-k.txt.

Behaviour-neutral proof:
- Digests, computed by /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/k/digests.py on a `git archive` of 0554fd6a (before) and on the K head (after), `diff` empty, "DIGESTS BYTE-EQUAL": checker_constants_sha256 `b08b5496fe2831c950b200bde0c2bd230d16489cd55ac2bb9c8ff1af93327f1b`; vendor codex `d045bef4cf91bff20e2e9ced76345114e63782bd7550260d3dbae5eda336b7bd`; vendor gemini `23e22d15468f5e307567c3b29c5cbb980b2ee097ebfadd77781d2248440d43ad`; VENDOR_PENDING_ROWS, VENDOR_READER_ITEMS (`5734250305e3...`, order kept) and VENDOR_CHECK_SHAPES_SOURCE (`documented` both) equal; every row PENDING.
- No file in READER_SOURCES or CODEX_SOURCES changed (`check_vendor_sources.py P2 ...` exit 0; `git diff --name-only 0554fd6a..HEAD` names none of them).
- Merge simulation (scratch clone, removed): a Codex branch handing a reader into all 11 Codex None sites, all 15 Codex item lines, its rows block, its span and vendor_settle_codex.py, and a Gemini branch doing the same for Gemini, merge with no conflict (22 sites changed in the result).

Checks (each after `mac_slot.py light-ok --work gap-study-r4` exit 0, run from /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/k/run_vendor_tests.sh, one process per module, 22:35-22:47 EDT):
- test_vendor_check 33 OK; test_codex_adapter 64 OK; test_gemini_adapter 146 OK; test_vendor_body 11 OK; test_vendor_entries 8 OK; test_vendor_roads 13 OK; test_take_checker_dispatch 5 OK; test_checker_constants 27 OK.
- test_freeze_shapes 9 run, 1 failure: `test_fs_check_the_committed_draft_names_every_leg` expects `arm O (codex): leg iii:`; the same test fails on a worktree of the untouched base 0554fd6a (22:28 EDT, FAILED failures=1), so it is a pre-existing red of the dry line (leg iii no longer fires once the vendor walks are registered), not K's.
- Hazard check, one process: `python3 -m unittest test_vendor_body test_vendor_check test_vendor_entries` Ran 52 OK.
- copy_manifest --check ok (661 files, 62 fragments at the K2 head); lint_language on the five folders clean (10 inputs: the READMEs and PROVENANCE files); test_round4.module_problems() [].
- Two checks ran without a light-ok gate, both under a second: one lint of two fixture folders (22:27) and one in-process run of test_context_sweep's problem list (22:49). Said here, not hidden.

Observation for glitch-f1 (not fixed, outside K): on the clean w-o46 copy, `vendor_reach(path, "codex", run_tree=vendor_session_cwd(...))` reports one `[read-outside-the-checkout]` whose path is `<tmp>/run-8617d222\\nCLAUDE.md\\nDEVELOPMENT.md\\n...`: a literal backslash-n joined listing read as one path. That is an event line (outside_reach) on a walk the C builder will regrade; it looks like the same escaped-text family as MAJOR 3 and should be read before the w-o46 SAME fixtures assume a clean reach.

### Append points for C and G (line numbers at the K2 head 5fe6a9bb)

- check_take.py VENDOR_PENDING_ROWS: Codex block 3819-3832, Gemini block 3833-3845 (each row edited in place).
- check_take.py VENDOR_READER_ITEMS: Codex lines 3916-3930, Gemini lines 3933-3947 (one item per line, value a `"<folder>/<file>"`).
- check_take.py reader spans: Codex between 5405-5410 banner and `# ---- END SETTLE: CODEX READERS` (5411); Gemini between the 5416-5420 banner and `# ---- END SETTLE: GEMINI READERS` (5421). Append directly above the END line.
- check_take.py site lines (hand the reader in place of `None`): Codex T-5 4389, T-10 4471, T-12:offered-context 4526, T-12:instruction-files 4565, T-17:billing-route 4718, T-13 4796, T-14 4797, T-12:prompt-snapshot 4809, T-12:memory 4810, T-16 4909, T-18 4917 (T-8:file-change already hands in vendor_file_change_reads, 4983); Gemini T-10 4473, T-11 4496, T-12:offered-context 4528, T-12:instruction-files 4567, T-17:billing-route 4720, T-13 4799, T-14 4800, T-12:prompt-snapshot 4812, T-12:memory 4813, T-4 4882, T-18 4919.
- tests: C writes only tests/vendor_settle_codex.py, G only tests/vendor_settle_gemini.py; plants through tests/vendor_plant.planted; new files claimed in their own fragments COPIED.d/vendor-settle-c.json / vendor-settle-g.json and checks.d/vendor-settle-c.txt / -g.txt (lane name = file name), never in vendor-settle-k*.json.
- Shared, left for V: VENDOR_CHECK_SHAPES_SOURCE (one line), TABLE_STATES and the VP-rows/VP-fixtures/VP-reader-items rewrites, the adapters' SHAPES_SOURCE flips (C: codex_adapter.py, G: gemini_adapter.py, each its own file). A helper both arms need (T-17's shared partial) is written by C in its span with a harness argument; G calls it after merging C, or writes its own and V folds them.

## Stage K2: the Claude arm's loaded-context sweep reads decoded text

Commits: K2 red `3a3d7be07cca05bfb08abf679983355bbc81ae6d` (tests/test_context_sweep.py, COPIED.d/vendor-settle-k2.json, checks.d/vendor-settle-k2.txt); K2 green `5fe6a9bbcb64c371580fcc70932a69ba35a9799f` (check_take.py, tests/test_edited_text_file.py, the test's witness spelling).

What changed: `_swept_attachment_line` returns `_decoded_text(_cut_attachment_line(rec, line))`.
`_cut_attachment_line` is the old body unchanged (raw line, snippet value emptied, every review r6/r7 guard); `_decoded_text` reads the cut line with `object_pairs_hook=_AllPairs`, so every key and value in order, strings decoded, every copy of a duplicated key kept.
context_text (check_take.py:120-144) is untouched, so checks.d/w6j-claude-adapter.txt's round-3 byte pin and test_walk_runner's R5 context-text span do not move (both run green below); the one pin that moved is test_edited_text_file's E-raw lines, now on `_cut_attachment_line`, each naming the ruling.
check(), subagent_leak_problems and leak_grep read the decoded text through context_text (CS-callers proves the last two).

Red first (on 3a3d7be0, 22:49 EDT): test_context_sweep FAILED (failures=4); the problem list: the five planted escaped cases name [] not ['evaluation'], the filename-after-newline case names no leak, the bare `allowlist` after a newline is forgiven, subagent_leak_problems and leak_grep's derive miss the word.

Green (5fe6a9bb, light-ok 22:51 and 22:57 EDT): test_context_sweep 2 OK (three witnesses red); test_edited_text_file 10 OK (its seven leak mutants still red); test_jsonl_split 5 OK; test_walk_runner 89 OK; test_agent_tool 17 OK; test_checker_body 30 OK; test_claude_code_adapter 28 OK; w6j's byte-pin line exit 0; test_vendor_check 33 OK; hazard check one process `test_claude_code_adapter test_context_sweep test_edited_text_file test_jsonl_split` Ran 45 OK; leak_grep --check ok (74 sessions in this tree); copy_manifest --check ok.

Proof no verdict changes: /private/tmp/claude-501/-Users-javrodher-glitch/de671dc9-9274-4a09-b079-1f80eb793658/scratchpad/k/k2_sweep.py runs a tree's own `context_leaks(context_text(...))` over every claude-code walk at d5c0f7989083990f0eb76308b8eb79f86e41d7e4 (blobs by `git show` in freeze-dry-20261021): before (base check_take, identical outside rehearsals to d5c0f798 by `git diff --name-only`) and after (K2 head), 151 walks each, 0 walks flagged, hit totals `{'allowlist': [302, 0]}`; per-walk leak sets equal: True; whole result files equal: True (k2-before.json, k2-after.json in that folder).
Digest after K2: checker_constants_sha256 `b08b5496fe2831c950b200bde0c2bd230d16489cd55ac2bb9c8ff1af93327f1b`, both vendor digests unchanged ("DIGESTS BYTE-EQUAL (K2)").

Open for glitch-f1: prereg-draft.json's edited_text_file departure says the sweep reads the "raw line with only the snippet's value cut" (test_e_draft_names_the_leak_scope pins that wording); still true of the cut, but the draft does not yet say the cut is then decoded. I did not touch the draft (a build_draft output); a wording addendum is yours to rule. The freeze rehearsal must re-run on the new tree (check_take.py is pinned, freeze.py:131-132).

## Stage C: the Codex rows (arm O)

Builder: an Opus 5.5 medium lane agent of glitch-f1 under Javier's standing delegation, sole writer of clone /Users/javrodher/aegis-builds/vendor-settle-c-20261021, branch `lane/vendor-settle-c` from `e350601fb100cf62f245a5ca18ed49cf8949a5e6` (Wed 21 Oct 23:12 to Thu 22 Oct 00:25 EDT, clock read with `date`).
Never pushed.
Every check ran after `mac_slot.py light-ok --work gap-study-r4` exit 0 (a wait loop, never an override); no heavy run, no whole suite.

Commits:
- C1 red `c40bcf93`, C1 `04b5c045`: K's open point 2 (below).
- `482bd786`: lane freeze-gates-fix S1 cherry-picked (`git cherry-pick -x d05e226430201ebec1a947e2921f9405518d84c3`, fetched by exact SHA from /Users/javrodher/aegis-builds/freeze-gates-fix-20261021 on glitch-f1's adjustment; no conflict): mode_binding.codex_mode_records and CODEX_MODE_RECORD, which T-16 reuses.
- C2 `6daeb5c1`: the 12 rows, readers, sites, the 15 READER items.
- C3 `bec24e15`: leg i prepared, checks.d/vendor-settle-c.txt, COPIED.d/vendor-settle-c.json.

### Rows (check_take.py VENDOR_PENDING_ROWS codex block; readers in the Codex span)

SAME, fixture `recorded-codex-w-o46/transcript.jsonl`; each has a SAME_FIRES plant (scoped: adds only its reason, no sibling), a clean case against the test's own plain-json reading, and a hollow-reader witness (red):
- T-5 `vendor_codex_origin_reads`: user parts = operator lines in order + one AGENTS.md + one environment_context; developer tags in the closed six. Plant: an extra part beside turn 2's "skip".
- T-10 `vendor_codex_loaded_context_reads(path, pre)`: context_leaks over `_decoded_text` (MAJOR 3) of session_meta, world_state, developer messages, AGENTS.md and environment parts. Plant: " eval" in collaboration_mode.
- T-12:instruction-files `vendor_codex_instruction_files_reads`: AGENTS.md header directory and world_state.agents_md.directory inside the session folder. Plant: header names /opt/cfg.
- T-12:prompt-snapshot `vendor_codex_prompt_reads`: base_instructions.text non-empty. Plant: text "".
- T-14 `vendor_codex_instruction_content_reads(path, design)`: both AGENTS.md copies equal the pinned CLAUDE.md of their directory (design.instructions). Plant: one word in world_state.agents_md.text.
- T-16 `vendor_codex_recorded_mode_reads(path, design, arm)`: mode_binding.codex_mode_records (one reading, not re-spelled), one turn_context per turn with CODEX_MODE_RECORD's pair, plus thread_settings approval_policy and permission_profile.type "disabled" (MAJOR 2, codex_native.py:96-99); arm None reads the ledger's arm. Plant: turn 2's approval "on-request"; extra tests fire on a thread_settings approval and a turn_context sandbox; a test proves the mode_binding reading is the one used.

NOT COMPARABLE, `ruling` = glitch-f1's adopted text verbatim (sha256 of the ruling file when copied: ddc65e14d17b019c02869e42578694d894a6dc21521b8ab7214d332ce871642e; equality checked by script against the file); each plant the ruling names fires its reason only, and the partial replaced by `return []` goes red:
- T-8:file-change `vendor_file_change_reads` (existing): synthetic unjoined patch and rename through the settled site.
- T-12:offered-context `vendor_codex_offered_partial`: every root list exactly [cwd], app/plugin sections off, no recommended_plugins, no additional_tools, skills only from /opt/cfg/skills/.system. Plant: an outside root in session_meta.
- T-12:memory `vendor_codex_memory_partial`: world_state key sets, no memory-named key (SessionMeta.memory_mode, protocol.rs:3210, included), sections within the six. Plants: a `memories` key; a `<memories>` section.
- T-13 `vendor_codex_checkout_partial`: one git {branch, commit_hash}, branch "main" (drive.py:381), 40-hex hash. Plants: git null; branch "other".
- T-17:billing-route `vendor_billing_route_partial(path, harness, pre)` (shared; stage G may call it): environment record names, TAKE_ENV and refused set, Codex provider and plan (Gemini: the pinned auth setting). Plants: CODEX_ACCESS_TOKEN in names_present; TAKE_ENV patched; provider "oss".
- T-18 `vendor_codex_tools_partial`: no multi-agent or recommended_plugins section, no additional_tools, sections off, rebuilt config.toml turns agents, plugins and web search off. Plant: multi_agent_role into w-o47.

Over the 38 committed GPT walks (rehearsals/w-o*, read in place): every SAME reader reads [] on 38 of 38; T-18 fires on 31 (every pre-B22 walk, w-o46 included, as ruled); T-12:offered-context and T-18 also read the recommended_plugins section on w-o7 and w-o8 (the adopted amendment; the design's open call 3 is reversed by it).
check4_walk_vendor on the 38: 38 carry `[constant-binding] the take ran in permission mode 'unrecorded'` (check_take.constant_problems on the ledger, not a stage C row), 31 harness-condition-violated, 2 inherited-context.

### K's open point 2 (ruled in the C brief)

It is the escaped-text family: w-o46 native-turn-3 line 16 is a code-mode custom_tool_call_output whose part text is a JSON document; read encoded, `<run tree>\nCLAUDE.md\n...` was one path outside the run tree, and an outside path after an escaped newline was unseen.
Fix (red first, c40bcf93 then 04b5c045): `_codex_rollout_records` hands RETURNED records through `vendor_codex_returned_documents`, which reads a returned text that parses as a JSON object or array as its decoded keys and values.
vendor_reach over all 38 GPT walks, base e350601f (git archive) against C1: 36 identical; w-o46 and w-o12 each lose the same false event (their listings sit in the run tree); nothing gains an event.
NOT fixed, for glitch-f1: w-o11, w-o13 and w-o26 keep the same-class false event, from a text that opens with the CLI's `Warning: truncated output (original token count: N)\nTotal output lines: M\n\n` header and whose JSON body was cut, so it does not decode; w-o30's 5 events name a real /tmp file outside the run tree.

### Leg i (prepared; stage V flips)

CLegI drives codex_adapter.CodexAdapter on the RECORDED w-o46 streams and rollouts (three resumed turns) and w-o47 (gpt-6-luna) through test_codex_adapter's FakeRuntime and stubbed run_turn; text, end reason, agent output, thread ids, usage and requested context equal plain-json values.
For V: copy w-o46 turn-1..3.jsonl, session/native-turn-1..3.jsonl and w-o47 session/native-turn-1.jsonl flat into tests/fixtures/codex-streams (labels "RECORDED at walk w-o46, codex-cli 0.162.1." / w-o47), flip SHAPES_SOURCE, rename test_a7, rewrite the shapes-recorded witness.
Docstring text for codex_adapter.py lines 9-14, proposed: "SHAPES_SOURCE. The stream and rollout shapes this module reads were re-tested on the streams and rollouts recorded at walk w-o46 (codex-cli 0.162.1, three resumed turns) and the rollout of walk w-o47 (gpt-6-luna), listed in tests/fixtures/codex-streams/README.md, against values derived independently with plain json (tests/vendor_settle_codex.py CLegI); the adapter reports the word in its harness record and in every turn record, and freeze leg i reads it." (it must not contain the literal assignment text, NIT 1). Line 54's "run_take's billing-route variables for Codex (PENDING ...)" is stale since 14 Oct (run_take.py:663-686).

### READER items

All 15 Codex items name `recorded-codex-w-o46/transcript.jsonl`; each item's own reader on the clean copy equals the test's reading (T-8 also its record count; T-15 also on w-o47).
Re-planted on the recorded copy and firing: T-3, T-4, T-9, T-15, T-24; the other ten F3 re-runs are left for lane R.

### Source read (S0, Codex)

Pinned retained source /Users/javrodher/aegis-builds/gap4-codex-rollout-audit-20261014/src (commit 092d3acd): bypass sets SandboxMode::DangerFullAccess (exec/src/lib.rs:343-347) and exec sets AskForApproval::Never (:591); SandboxPolicy "danger-full-access" (protocol.rs:1088-1091).
No memory setting is named in the retained tree (no config crate retained); SessionMeta.memory_mode (protocol.rs:3210) is thread memory-generation metadata, read by the memory-key leg. So T-12:memory's settings leg is dropped, and the adopted text's "(else that leg is dropped and this text says so)" needs glitch-f1's amended wording.
No line upgrades T-12:offered-context (the connector-rendering code is not in the retained tree).

### Tests

vendor_settle_codex.py run directly: 16 OK; with test_codex_adapter (64 OK), test_mode_binding (12 OK) and test_vendor_roads (13 OK) in one process: 105 OK, environment unchanged, sys.path order moved only by test_mode_binding (freeze-gates-fix's own module, alone too).
test_take_checker_dispatch 5 OK, test_checker_constants 27 OK, copy_manifest --check ok (663 files, 63 fragments), check_vendor_sources P2 exit 0 (no READER_SOURCES or CODEX_SOURCES file changed).
Red by design until stage V rewrites them (each pins every row PENDING or every item None, or runs synthetic F1 takes that carry none of the CLI records the settled readers read): test_vendor_check VPRows (2 tests), VPHelper pending (12 subtests), VPFixtures recorded-shapes count, VPReaderItems unrecorded-here, VPSameFires settled-row (its synthetic map meets the live SAME rows); test_vendor_body 9; test_vendor_entries 4; test_codex_patch_reads K2Site (expects the PENDING text).
Digest after C: checker constants unchanged `b08b5496fe2831c950b200bde0c2bd230d16489cd55ac2bb9c8ff1af93327f1b`; vendor codex `c03837df0258ea0dfd2bf89018511378b5e7ad1c29c2f1623eedaf0f85e74959` (was d045bef4..., moved by the settled rows as designed); gemini unchanged.
Left for V: the shared site docstrings still say "PENDING ... unread" (shared lines, not edited here).
