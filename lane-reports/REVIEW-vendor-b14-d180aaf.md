VERDICT: CHANGES

# Review: lane vendor-b14, range 00942460..d180aaf7

A fresh cloud reviewer for glitch-26 (the Lane-orchestrator), 2026-10-19. I did not write this change. I changed no code.
Scope: B15 (the arm O usage table) and B14 (round 1's design note, plus round 2's R-B14-1 helper aliases, R-B14-2 invoke_agent exclusion and R-B14-3 strict identity), read against the lane file, B14-DESIGN-NOTE.md and the section 6 table of PLAN-codex2-signin-road-2026-10-18.md.

## Findings

1. MINOR: the review's own mutant check was not run, because a safety check refused a command.
   Where: this review, the CHECKS item "two mutants of your own on a scratch copy outside the clone".
   What happened: the command that set up the two scratch copies began with an `rm -rf` of a scratch path held in a shell variable. The built-in safety check refused it as an unresolvable removal target, and nothing was run.
   The prompt says never to reword or route around a refusal, so I record it here and ran no mutants.
   The two mutants I planned, both in box/take_config.py `_gemini`, are left for a follow-up review:
   (a) drop the unread-model refusal at lines 303-304 and fall back to `GEMINI_ROW_ALIASES.get(model, {})` at line 316. TestB14HelperPins's `files_for(..., "gemini-3-flash-preview")` case should turn that red.
   (b) drop the "helper alias set twice" refusal at lines 317-318 (see finding 3).
   The lane's own mutants did run, and they are red as registered (see Checks).

2. MINOR: R-B14-1 creates a new difference between the arms, and the section 6 table does not name it.
   Where: lane-reports/PLAN-codex2-signin-road-2026-10-18.md line 268 has a row for R-B14-2 only.
   What changed: after R-B14-1, every arm G helper call (loop detection and its double check, chat compression, the agent-history summarizer) runs on the row's own model. Before, the pinned CLI sent these to gemini-3-flash-preview or gemini-3-pro-preview, which became customtools here.
   Arm A goes the other way. Its harness's side calls stay on Claude Code's small model, and the adapter admits them by a closed list (evals/gap-study-4/claude_code_adapter.py lines 314-317, SIDE_MODELS = ("claude-haiku-4-5-20251001",)).
   So on helper models, arm A runs as shipped, while arm G is repointed from its shipped defaults onto the measured row.
   That changes arm G's road: the row's model now serves, and is billed for, work the vendor would have given a different model.
   It is also an asymmetry with arm A.
   The lane file says R-B14-3 adds no named difference, which is true of the identity check. It says nothing about R-B14-1.
   Missing check: a section 6 row for "vendor-b14 round 2 (ruling R-B14-1)". It should name what moved (the six aliases and their shipped models, box/take_config.py lines 99-102), state that arm A's side calls stay on SIDE_MODELS, and cite TestB14HelperPins as the bound.
   Arm A's road and bytes do not move in this range. The only arm A text touched is the plan's prose row. claude_code_adapter.py and run_take.py are unchanged.

3. NIT: the new "helper alias set twice" refusal has no test that fails without it.
   Where: evals/gap-study-4/box/take_config.py lines 317-318.
   Why: nothing in tests/ reaches this refusal. A grep for "set twice" in tests/test_take_config.py finds nothing. With today's values the restated chat-base-3 never collides with a helper alias, so deleting the refusal leaves every current test green. That is a structural reading; finding 1 explains why it was not confirmed by a mutant.
   Missing check: a TestB14HelperPins mutant that patches a GEMINI_ROW_ALIASES row, or GEMINI_THINKING's value, to carry a helper alias's name, and expects Refused.

4. NIT: pinning loop-detection-double-check to the row's model changes one branch of the CLI's behaviour beyond which model serves the call.
   Where: bundle/chunk-NR7L3FXV.js lines 344238-344255 of the verified 0.64.0 tarball.
   What changes: when the double-check model's availability snapshot is unavailable, the loop detector confirms a loop on the flash check alone.
   That model is now the row's model, so a row model marked unavailable (for example after a terminal quota) also skips the double check. Before, a separate pro model was asked.
   This only arises once the main model is already unavailable, when the take is failing anyway. The design note's section 3 correction could name it in one sentence.
   No other path I read changes behaviour. The customAliases layering (lines 342154-342158) replaces the built-in entry by name. Each entry restates its built-in's `extends`: gemini-3-flash-base and loop-detection-double-check extend base, and the compression and summarizer aliases extend nothing (lines 362386-362556). The built-ins carry no generateContentConfig to lose. The main conversation's alias chain (gemini-3.8-flash, then chat-base-3, then chat-base, then base) does not pass through any repointed alias.

## Verification against the pinned sources

B15: I fetched only the two cited files at openai/codex 092d3acd into a scratch folder outside the clone.
- exec_events.rs sha256 is dafa872d7e86..., and event_processor_with_jsonl_output.rs is bc296541b385..., both matching codex_usage_sources.FILE_SHA256.
- struct Usage (lines 59-73) has exactly the five i64 fields at lines 63, 65, 68, 70 and 72.
- No field has skip_serializing_if. The file uses it only at lines 272 and 303. Line 67's serde(default) applies to deserializing only.
- No serde(flatten) or rename touches Usage.
- turn.completed is built in one place, line 533, from usage_from_last_total (lines 118-130), which sets all five fields.
- USAGE_KEYS equals the struct, in order. No field is missing and none is invented. A line missing a field refuses, and so does an extra key or a value that is not a count (U3, and the witnesses).

B14: I took the npm tarball @google/gemini-cli 0.64.0 and verified its sha256 as 891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6. I unpacked it outside the clone and read it only; nothing in it was run.
- The three files' sha256 values match VALUE_SOURCES: chunk-NR7L3FXV d566e81b..., chunk-FLKY6NH5 f6a4ddd4... and gemini-Q2GRYIAK 7702da31....
- Every line cited in GEMINI_HELPER_ALIASES and GEMINI_AGENT_EXCLUSION holds the text claimed: the definitions, model lines, use lines, layering lines, F:13409, F:13371, F:13925 and G:8674.
- I swept every `modelConfigKey: { model: ... }` call site in core. Each one names an alias that is pinned or follows a pinned one: llm-edit-fixer, next-speaker-checker, loop-detection, web-search, web-fetch and context-snapshotter extend gemini-3-flash-base. The rest are unreachable under these settings:
  - edit-corrector is gated by disableLLMCorrection at line 310738.
  - summarizer-default is reached only from listSessions (G:16903).
  - classifier serves auto models only.
  - context-calibrator is a countTokens call under contextManagement.
- Two agents run on PREVIEW_GEMINI_FLASH_MODEL with no alias:
  - the codebase investigator, unreachable once invoke_agent is excluded;
  - the auto-memory SkillExtractionAgent (line 384388), gated by experimental.autoMemory, default false (F:14619, G:8606).
- I found no other tool registration that exposes a subagent. createToolRegistry registers AgentTool alone (line 382849), and the other registerTool calls are MCP discovery or the subagent's own registry.
- Compression for gemini-3.8-flash maps to chat-compression-3-flash (lines 337043-337045). For gemini-3.5-flash-lite (LATEST_GEMINI_FLASH_LITE_MODEL, line 279990) it maps to chat-compression-3.1-flash-lite (line 337051). Both are pinned per row, and chat-compression-default is pinned for every row.
- No alias entry is invented, and I found no reachable route left that would put another model's requested id into stats. What the server reports as modelVersion stays outside the package, as the note says.

Fail-open: none found.
- `_gemini` refuses a model with no GEMINI_ROW_ALIASES entry (lines 303-304). This is checked before any file is placed.
- tools.exclude is a new list that adds to D8's two tools.
- customAliases is a new mapping. GEMINI_THINKING is not mutated, which the in-place mutant binds.
- gemini_adapter's identity check is untouched (R-B14-3). A stream showing invoke_agent still refuses as a delegation.

## Checks run

Each module ran in the foreground under `env -i` with only PATH, HOME, LANG and TMPDIR set. TMPDIR was a scratch folder outside the clone, CLAUDE_CODE_MESSAGING_TOKEN was unset, and the tree was d180aaf7.

| Check | Result |
|---|---|
| test_codex_usage_source | 3 tests, OK |
| test_codex_adapter | 55 tests, OK |
| test_take_config | 11 tests, OK |
| test_gemini_adapter | 143 tests, OK |
| test_walk_builders | 94 tests, OK |
| test_live_box | 38 tests, OK |
| test_build_draft | 49 tests, OK |
| test_run_take | 68 tests, OK |

The lane's witness lines in checks.d/vendor-admission.txt for B15 and B14 (lines 83-94, five commands) all exit 0:
- test_codex_usage_source passes.
- test_codex_usage_source --witnesses reports 9/9 red.
- check_vendor_sources P2 on the B15 files passes.
- test_take_config passes, with its TestB14HelperPins mutants red, among them "tools.exclude dropped".
- check_vendor_sources P2 on the B14 files passes.

Pinned source reads: the Codex files at 092d3acd and the Gemini 0.64.0 tarball. All hashes match, as above.

Own mutants: not run, because a safety check refused the command (finding 1).

Not run, as the prompt forbids: any walk, take, container, Gemini CLI, Codex or vendor call, and any login, token, lease or account file.
