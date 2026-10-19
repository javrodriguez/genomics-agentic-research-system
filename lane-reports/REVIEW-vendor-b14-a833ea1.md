VERDICT: PASS

# Review: lane vendor-b14, range 9e62b541..a833ea17 (round 3)

A fresh cloud reviewer for glitch-26 (the Lane-orchestrator), 2026-10-19. I did not write this change, and I changed no code and no test.
Scope: round 3 (rulings R-B14-4 to R-B14-7 on the review of d180aaf7; R-B14-1 stands). I read it against the first review, the ROUND 3 SUMMARY in vendor-b14-LANE.md, B14-DESIGN-NOTE.md, plan section 6, box/take_config.py and claude_code_adapter.py, and the verified Gemini CLI 0.64.0 tarball.

## Findings

No MAJOR, MINOR or NIT finding. The notes below record what I checked for each point of the threat model.

1. First review, finding 1 (own mutants not run): closed. R-B14-7 registers two writer mutants in TestB14HelperPins (tests/test_take_config.py lines 376-397 and 469-471). Each is red alone with the intended message: "unread-model refusal dropped" gives "a gemini config was placed for a model whose helper aliases are not read", and "set-twice refusal dropped" gives "gemini-3.8-flash: a gemini config was placed with helper alias 'gemini-3-flash-base' set twice". The witness line is checks.d/vendor-admission.txt line 98. I also ran both of the mutants I had planned, as source edits on a scratch clone outside this one (see Checks). Both are red.

2. First review, finding 2 (R-B14-1 not named in plan section 6): closed. PLAN-codex2-signin-road-2026-10-18.md line 269 names:
   - each pinned alias and the model 0.64.0 ships it on;
   - where take_config pins and writes them;
   - that arm G's helper calls now run on, and are billed to, the row's model;
   - that arm A's side calls stay on SIDE_MODELS;
   - TestB14HelperPins as the bound.

   Every cited line holds the text claimed:
   - Tarball: sha256 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6. I unpacked it outside the clone and only read it. bundle/chunk-NR7L3FXV.js has sha256 d566e81b....
     - gemini-3-flash-base, "extends: base", on gemini-3-flash-preview: 362386/362389.
     - loop-detection extends gemini-3-flash-base: 362486-362487.
     - loop-detection-double-check, "extends: base", on gemini-3-pro-preview: 362490/362493.
     - chat-compression-3-flash on gemini-3-flash-preview: 362522/362524.
     - chat-compression-3.1-flash-lite on gemini-3.1-flash-lite: 362527/362529.
     - chat-compression-default on gemini-3-pro-preview: 362547/362549.
     - agent-history-provider-summarizer on gemini-3-flash-preview: 362552/362554.
   - box/take_config.py: lines 99-102 are GEMINI_HELPER_ALIASES and GEMINI_ROW_ALIASES. Lines 316-320 are the loop that writes customAliases and the assignment.
   - claude_code_adapter.py: lines 314-317 are the ruling comment and SIDE_MODELS = ("claude-haiku-4-5-20251001",). Lines 381 and 399 are the two reads that make a key off the list a mismatch.

   The claim that arm A runs as shipped also holds in run_take. ANTHROPIC_SMALL_FAST_MODEL and the ANTHROPIC_DEFAULT_HAIKU_MODEL names are on CLAUDE_BINARY_SWEEP_REFUSED (box/run_take.py lines 469-482), so a take cannot repoint arm A's small model.

   Arm differences this lane makes:
   - R-B14-1 is named at line 269, and R-B14-2 at line 268.
   - R-B14-3 adds no difference.
   - B15 is a reader table for arm O and moves no road.

   I found none still unnamed. Finding 4 below changes a branch inside arm G only. It is in the design note, and it is not a difference between the arms.

3. First review, finding 3 (the set-twice refusal has no test): closed. set_twice_refused (tests/test_take_config.py lines 400-413) puts gemini-3-flash-base into GEMINI_THINKING's value and expects "set twice" for both rows. test_helper_alias_set_twice_refused runs it, and so does TestB14HelperPins.check (line 455). With box/take_config.py lines 317-318 deleted, it is red on a scratch clone (my mutant 1).

4. First review, finding 4 (the loop detector's double check): closed. B14-DESIGN-NOTE.md line 102 says it in one sentence. The cited lines match the bundle:
   - 344238-344240: doubleCheckModelName is resolved from the alias.
   - 344246-344247: the availability snapshot is checked.
   - 344248-344255: the detector returns isLoop true, confirmedByModel loop-detection.
   - 344257: the second query, which that return skips.
   - 362493: the shipped model.

   The sentence leaves out the flash-confidence threshold at line 344241. Only a flash result over that threshold reaches the branch. The sentence's meaning does not change.

5. Scope (threat-model point 4): round 3 moves nothing beyond its summary. `git diff --stat 9e62b541..a833ea17` lists only five files:
   - checks.d/vendor-admission.txt: +4, one comment and one command.
   - tests/test_take_config.py: +48, the import, writer_mutant, the two spans, set_twice_refused, one test, and two mutants in the list.
   - B14-DESIGN-NOTE.md: +2.
   - The plan: +1 row.
   - The lane file: status, summary and progress.

   box/take_config.py, gemini_adapter.py, claude_code_adapter.py, run_take.py and prereg-draft.json do not move, and build_draft --check is ok.

6. The summary's observation (threat-model point 5): it is accurate, and it leaves no gap in what is placed. _gemini merges the row over the helper aliases with dict(GEMINI_HELPER_ALIASES, **GEMINI_ROW_ALIASES[model]) (box/take_config.py line 316). The merge comes before the refusal at line 317, so a row that reuses a helper alias's name replaces that entry silently and never reaches "set twice".

   What gets placed is still bound in two ways:
   - Line 319 always writes modelConfig.model as the row's model, so the override cannot move any helper call off the row.
   - TestB14HelperPins.check compares every placed entry with the test's own literal expectation (tests/test_take_config.py lines 299 and 352-357, compared at 436-439).

   I ran two mutants on this. Mutant 3 sets the gemini-3.8-flash row to carry "gemini-3-flash-base": {}, which loses "extends": "base". It is red in TestB14HelperPins, TestContents and TestR3Values. Mutant 4 has the row carry the same entry the helper map holds. It is green, and it places the same bytes, so nothing changes.

   The refusal's own reach therefore stops at R3's restated customAliases (GEMINI_THINKING's value), which matches its comment at lines 312-313. If glitch-26 wants a row-over-helper overlap refused by name and not only by value, the missing check is at box/take_config.py line 316: refuse when `set(GEMINI_ROW_ALIASES[model]) & set(GEMINI_HELPER_ALIASES)` is non-empty. That is a choice, not a defect today, so I do not count it as a finding.

## Checks run

Each check below ran in the foreground on a833ea17, under `env -i` with only PATH, HOME, LANG and TMPDIR set. TMPDIR was a mktemp folder outside the clone.

| Check | Result |
|---|---|
| test_take_config (with TestB14HelperPins: 10 of 10 mutants red) | 12 tests, OK |
| test_gemini_adapter | 143 tests, OK |
| test_run_take | 68 tests, OK |
| test_walk_builders | 94 tests, OK |
| test_build_draft | 49 tests, OK |
| test_codex_usage_source | 3 tests, OK |
| test_live_box | 38 tests, OK |
| build_draft.py --check | ok: the committed draft is what build_draft.py builds |
| Witness run: every command line of checks.d/vendor-admission.txt | 53 of 53 exit 0 |

My own mutants ran on a local clone at a833ea17 in a mktemp folder outside this clone. I edited box/take_config.py there and restored it from a saved copy after each mutant. git status on the scratch clone was clean afterwards.

| Mutant | Result |
|---|---|
| 1. Set-twice refusal deleted (lines 317-318) | Red: test_helper_alias_set_twice_refused fails with "gemini-3.8-flash: a gemini config was placed with helper alias 'gemini-3-flash-base' set twice". test_b14_helper_pins also fails, because its writer mutant's span is gone. |
| 2. Unread-model refusal deleted (lines 303-304), with `GEMINI_ROW_ALIASES.get(model, {})` | Red: test_b14_helper_pins fails. TestB14HelperPins.check returns ["a gemini config was placed for a model whose helper aliases are not read"]. |
| 3. Row carries a helper alias name with a different entry | Red (finding 6). |
| 4. Row carries a helper alias name with the same entry | Green, same bytes placed (finding 6). |

Pinned source read: @google/gemini-cli 0.64.0 from the npm registry, tarball sha256 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6 and chunk-NR7L3FXV.js sha256 d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c, both matching. I unpacked it outside the clone and read it only. Nothing in it was run.

Not run, as the prompt forbids: any walk, take, login, container, Gemini CLI, Codex or vendor call, and any real login, token, lease or account file. No safety check refused a command in this review. The scratch folders are left in place.
