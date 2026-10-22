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
