# Lane d8-furniture (Gap Study round 4): D8's per-harness furniture lists, the awareness scan's harness support, and the hook note

Lane agent: Opus 5.5 medium, for glitch-f1, under Javier's standing delegation.
Clone: `/Users/javrodher/aegis-builds/d8-furniture-20261021` (self-contained `git clone --no-local`; no alternates), branch `lane/d8-furniture` from `dry/all-225` = `d5c0f7989083990f0eb76308b8eb79f86e41d7e4`.
Opened Wed 21 Oct 2026 22:33 EDT (clock read with `date`).
Inputs: `/Users/javrodher/aegis-builds/D8-READ-w-o46-20261021.md`, `/Users/javrodher/aegis-builds/D8-READ-w-g21-20261021.md`, `/Users/javrodher/aegis-builds/GAP4-COSTGATE-D8-20261021.md` section 2, `/Users/javrodher/aegis-builds/ARM-A-HOOKS-20261021.md` (added mid-lane by glitch-f1), D8 lines 346-353 and 466-494.

## Survey (read-only, before the design; scratch scripts under the session scratchpad `d8f/`)

- All 225 walks were inventoried by record kind and key path (`survey.py`; no value printed): 38 Codex, 36 Gemini, 151 Claude.
- Every Codex and Gemini native snapshot is a byte prefix of the next (Codex 51 pairs, Gemini 14 pairs, 0 failures), so the last snapshot is the whole session.
- **Account-identifying fields exist only in Codex**: `session_meta.payload.creator_user_id` and `.creator_account_id` (one distinct value each over 38 walks); account-plan fields `event_msg/token_count.payload.rate_limits.plan_type` and `.credits.{has_credits,unlimited,balance}` (one distinct value each).
- **Gemini has none**: its one candidate, the header's `projectHash`, equals sha256 of the run-tree path in 36 of 36 walks (checked by equality, no value printed), so it identifies the run tree, not an account.
- **Claude** carries account-plan fields only: stream `system/init.apiKeySource`, `rate_limit_event.rate_limit_info.*`, `usage.service_tier`.
- No email-shaped string sits in any CLI-written field of any walk; the only ones (82 in Gemini walks, 302 in Claude) are GitHub noreply or anthropic.com addresses inside tool output and Claude's `remote_session_change` commit text.
- **Post-B22 Codex differs** (w-o39..w-o44 and w-o47 are post-B22; w-o7..w-o37 and w-o46 pre-B22): one developer record instead of three (no `multi_agent.role_instructions` / `multi_agent.mode_instructions`), `session_meta.payload.multi_agent_version` and `turn_context.multi_agent_version` read `disabled` (pre: absent and `v2`), and `world_state` loses `multi_agent_mode` and `multi_agent_usage_hint`.
  w-o7 and w-o8 also carry a `plugins.recommendations` developer item (before B18's plugins-off).
- **Gemini re-sends its session context mid-session** in three walks (w-g14 native-turn-4 line 517, w-g32 native-turn-3 line 514, w-g47 native-turn-2 line 605): a `user` record whose first text is the `<session_context>` block and whose second text equals turn 1's operator prompt (equality checked against the ledger).
- Arm A hooks (glitch-f1's addition), re-counted here independently: 151 walks, 348 Claude turn launches, every cwd `/tmp/run-<8 hex>` (the run tree's root), every `--setting-sources` `project,local`, 0 records with a hook key, type or subtype, every settings-guard baseline exactly `gars/.claude/settings.json`.

## Design

1. **`box/scan_record.py` FURNITURE** becomes `{harness: (entry, ...)}` for `claude-code`, `codex` and `gemini`.
   Each entry is a dict with exactly `file` (`session` or `stream`), `record` (the record kind, by the rule in item 2), `fields` (dotted paths whose string leaves the CLI wrote; `[]` steps into every list item, `[n]` into one; `*` the whole record), `account` (`None`, `identifying` or `plan`) and `evidence` (walk `folder/file:line` strings under `rehearsals/` that show the record kind there).
   Fields that copy the model's or the operator's words (Codex `task_complete.last_agent_message`, Gemini `$patch` contents, Claude `last-prompt`) are left out of `fields`, or named in the entry when the view already treats the record as harness.
   Account fields are entries of their own, so a scan excludes or masks them by position; no value is ever written down.
   The module stays data-only for this (no new import, builtin or attribute: test_sidecar's default-deny audit stays unchanged); `account_positions(harness)` is a comprehension over the existing names.
2. **Record kinds** are interpreted in `awareness_furniture.py` (`record_kind(harness, file, rec)`): Codex `type[/payload.type][/role]`, with an operator-free CLI-injected user message as `response_item/message/user:injected` (every `content_item_kinds` entry in {`agents_md.instructions`, `environments.environment_context`} and no `metadata.retained_source`, the read's discriminator); Gemini `type`, `user:session_context`, `$set:<keys>`, `$patch`, `<header>`; Claude `type[/subtype]` and `attachment:<type>`.
   Every record kind of a scanned native session must be a FURNITURE kind, or the check fails naming the kind: the list is complete by check, not by assertion.
3. **`awareness_furniture.py`** gains `--harness` (default `claude-code` over round 3, unchanged).
   For `codex` and `gemini` (default: every `rehearsals/w-o*` or `w-g*` walk) it scans three families, each row's raw type naming its family: the view's harness events from the stream (as before); `furniture:<record kind>` from the native session's FURNITURE positions, account fields excluded; and `native-result:<tool>` from the native session's tool results, because the stream drops them (Gemini `read_file` output is `""` in the stream) or keeps more than the model saw (Codex).
   Gemini resume re-records (`<id>_response`) are skipped so a result counts once.
   Native-result rows are not furniture: they are the agent-visible environment the stream withholds, scanned so a zero is a reading.
4. **build_draft** renders `furniture.<harness>` from FURNITURE (one string per entry, the version line first, taken from `version_pins`, never typed), so the prereg names gemini-cli 0.64.0 and codex-cli 0.162.1 there; every other place the prereg names a vendor version already names these two (checked: `box_residuals/5,6`, `routing_markers/rate_limit_markers/gemini/source`, `image_locks`, `version_pins`).
5. **The hook note (glitch-f1's addition):** build_draft adds `deterministic_layer_note` with rounds 1-3's text read from `evals/gap-study-3/prereg.json` at build time (bound byte-equal to rounds 1 and 2), the arm A round-4 evidence, and the vendor arms' line: the switches read from `take_config` (`[features] hooks = false`, `hooksConfig.enabled = false`) with the hook positive control as their evidence, PENDING until that lane's record lands.

## Derived files

`evals/gap-study-4/prereg-draft.json` is written only by `python3 evals/gap-study-4/build_draft.py`.
Lane freeze-gates-fix regenerates the same file for another cause; **after both lanes merge, re-derive `prereg-draft.json` with build_draft and commit the result** (never merge the two JSON diffs by hand).
This lane's regeneration (stage 4) changed five top-level keys: `furniture` and `deterministic_layer_note` (this lane's cause), `pending` and `stats_design` (which follow), and `checked_against`, which the base draft held as `{"sessions_read": 0, "status": "PENDING"}` while build_draft at the same tree reads 225 sessions: the base draft was stale for that key, not this lane's cause, and likely the other lane's.
`build_draft.py --check` and the stage-4 lint (lint_language, lint_pooling: 0 findings) were run on the regenerated file.

## Stages

1. `f87790b2` lane file, survey and design.
2. `bd0bb737` `scan_record.FURNITURE` per harness, `FURNITURE_KEYS`, `ACCOUNT_CLASSES`, `account_positions()`; `tests/test_scan_record.py` TestFurniture and TestPending, red first (3 failures, 5 errors), then green (209 tests); test_sidecar's default-deny audit unchanged and green (TestFold3Ast, TestFold5: 12 tests).
3. `27b7aef6` `awareness_furniture.py --harness`, `record_kind`, `native_counts`; `tests/test_awareness_furniture.py` class Native, red first (4 failures, 9 errors), then green (18 tests); every FURNITURE evidence line is opened and holds its record kind; the lists are complete on w-o46, w-o47, w-g21 and w168.
4. `2207269a` build_draft: `furniture_lists()` and `layer_note()`; test_build_draft clauses R15.furniture and R34.hooks red on a fresh build, then green, four READY_MUTANTS red, LayerNote recounts arm A from the walks; `prereg-draft.json` regenerated by `build_draft.py` (pending 22 to 20: three furniture slots and `/checked_against/status` closed, two hook-control evidence slots opened).

## The awareness scan over all 74 vendor walks (`awareness_furniture.py --harness codex|gemini`, behind light-ok)

- codex: exit 0, **0 match rows over 38 walks** (stream harness events, native furniture, native results).
- gemini: exit 0, **2 match rows over 36 walks**, both in w-g17 and both the phrase "gap study": `furniture:gemini` count 2 (the grep tool call's CLI-built `resultDisplay`, native-turn line 128) and `native-result:grep_search` count 3 (lines 129 and 154).
  They are the agent's own `grep_search` hitting the run tree's `README.md` line 28, which names "The Gap Study" (the pinned GARS tree 844a4ce0's README, line 28).
  That is not CLI furniture; it is a study word the agent can read in every arm's run tree (handed back below).
- round 3 (default, unchanged): exit 0, 0 rows over 54 transcripts.
- Every native session of the 74 walks passed the completeness check (every record kind is a FURNITURE kind) and the prefix check.

## Triage of the reads' other findings

Fixed here: the furniture lists (scan_record, prereg) and the prereg's CLI versions (named in each furniture list's first line from the image locks; every other version the prereg names was already 0.162.1 or 0.64.0: `box_residuals/5,6`, `routing_markers/rate_limit_markers/gemini/source`, `image_locks`, `version_pins`).
Handed back, named (none is furniture or the prereg, and several need a READER_SOURCES file):
- `claude_version` holds the vendor CLI version in vendor `driver-ledger.json` and `environment.json`; `check_take.py:1461` compares the two (writer: drive.py, a READER_SOURCE).
- Vendor `environment.json` `name_patterns.harness` lists Anthropic and cloud names only, and `credential_source.key` is Claude's `system/init.apiKeySource` (writer: box/run_take.py).
- `permission_mode` "unrecorded" on vendor walks, while the prereg's `version_pins` pin `bypass` and `yolo` (ledger writer: drive.py).
- preflight's `google_project_tier` and `token_visible_to_children` recorded PENDING (box/preflight.py).
- preflight's agent-non-root text "uid 10001" against the recorded 10003: **not a discrepancy** by the image locks (agent 10001, keepalive 10003, prereg `image_locks`), as the Codex read found; the detail could name both uids (box/preflight.py), cosmetic.
- `.gemini/projects.json`, `settings.json` and `tmp/<project>/logs` listed in postflight but never captured (session-store sweeps only `.gemini/tmp` chats).
- Codex `turn.completed.usage` is thread-cumulative after a resume: no code found that sums it (`costs.py:100-111` sums per-call usage as given; no caller in `drive.py` or `box/run_take.py` feeds it Codex stream usage; every ledger's `cost` is null), so only the cost-gate document overcounts; a per-turn source is `token_usage_record.turn_token_usage`.
- No Codex record names a served model (every model field echoes the request); the prereg's arm O `served_model_rule` is routing's SERVED_MODEL_LIMIT already.
New from this lane:
- **A study word in every run tree**: GARS's `README.md` line 28 "The Gap Study" (w-g17's grep found it); D8 says no study word appears anywhere the agent can read.
- **Gemini re-sends its session context with turn 1's prompt mid-session** (w-g14 native-turn-4 line 517, w-g32 native-turn-3 line 514, w-g47 native-turn-2 line 605): a native reader counting operator prompts or context records would double count (gemini_projection.py, a READER_SOURCE).
- **`checked_against` reads 0 context-record bytes on vendor sessions** (regenerated draft: every `rehearsals/w-g*` and `w-o*` session shows `context_records_bytes` 0), so the leak check sees none of the vendor CLIs' instruction furniture (build_draft `checked_sessions` / check_take).
- `owner_value_missing([], "list")` reads an empty list as supplied (`build_draft.py`, tested so in `test_structured_inputs_retain_their_types`); `furniture_lists` never renders an empty one, but the slot would accept it.
- The box user name `dana` is agent-visible through `ls -la` (w-g21 read item 8); it is box furniture, not CLI, and already in the prereg's `box_users`.

## Checks run (all behind `mac_slot.py light-ok`, or the heavy slot where named)

- Touched modules, red first then green: test_scan_record (209 tests), test_awareness_furniture (18), test_build_draft's Readiness clauses on one fresh build (R15.furniture, R34.hooks, four mutants red), test_auto_mode (6), test_sidecar TestFold3Ast and TestFold5 (12).
- `build_draft.py --check`: "ok: the committed draft is what build_draft.py builds".
- One-process hazard check, light: test_awareness + test_awareness_furniture + test_b25_real_shapes (55, 0 failures); test_scaffold + test_scan_record + test_scan_witness (268, 0 failures); test_awareness + test_scan_record + test_scan_witness (238, 0 failures).
- Heavy slot (`mac_slot.py run --kind heavy --owner d8-furniture`, acquired 00:23, about 20 minutes): test_awareness + test_build_draft (whole) + test_prereg_order + test_prereg_status + test_agent_tool in one process, 100 tests, **1 failure: test_build_draft Description.test_commitments, clause R9.sessions**.
  It is **pre-existing at the base**: `description_problems(describe())` returns `['R9.sessions']` in a detached worktree at d5c0f798 too (worktree removed after).
  R9.sessions expects `checked_against` to read 0 sessions, and describe() at this tree reads 225 (the walks merged into dry/all-225); the same staleness as the base draft's `checked_against`, so it belongs with lane freeze-gates-fix, not here.

## Fold (glitch-f1, Thu 22 Oct 2026): the list owner slot refuses an empty list

- `build_draft.owner_value_missing(value, "list")` now reads an empty list as missing (before: `all()` of nothing passed).
- `tests/test_build_draft.py` `list_slot_problems()` and two OwnerSlots tests: the three `/furniture/<harness>` slots (the only list-kind slots) refuse an empty list and a missing one, and the committed draft's three lists are non-empty and supplied. Red first (3 problems, one per harness), then green; the witness (the old rule patched back) goes red. `test_structured_inputs_retain_their_types` now supplies a one-line list instead of `[]`.
- FURNITURE is non-empty for every harness in the committed tree (codex 24 entries, gemini 12, claude-code 35; TestFurniture's shape check requires non-empty). `build_draft.py --check` still passes: the draft is unchanged.

## Fold 2 (glitch-f1's rulings, Thu 22 Oct 2026; GAP4-PREFREEZE-RESIDUALS-20261022.md), stage 8 `3c23d8c8`

- `run_tree_residual`: rounds 2-3's `run_location.residual`, `permitted_sweep_files` and `permitted_sweep_files_rule`, read at PRIOR_COMMIT and refused unless the two rounds agree; w-g17 named as the one observed case of 225 (native-turn-1 lines 123-153, tool names verified); the awareness caveat; D8's addendum of 22 Oct 01:01 EDT (line 698) correcting line 349.
- `box_residuals[0].finding`, per harness: claude-code visible (W-3b); gemini visible, measured here: `GEMINI_API_KEY=` in the agent's env output in 10 of 36 walks (the ten listed), 66 occurrences, all masked, 0 unmasked (no value printed); codex inferred readable by child processes from the static read (lease mode 600 `box/run_take.py:1398`, folder 700 owned by the agent's mapped uid `:1421-1424`, the grant `box/ownership.py:171`, every exec as 10001:10001 `:62`), measured: 0 of 38 GPT walks' streams, rollouts or transcripts name auth.json.
- A ninth box residual "arm G project tier": D8 mitigation 1 (D8 line 388) enforced only by the owner's recorded fact "Google Paid, cap $140" (plans/gap-study-round-4.md line 2129, verified); `box/preflight.py` records `GOOGLE_PROJECT_TIER` (that fact and its source) in place of the PENDING literal, and drops it from RECORDED_PENDING. Preflight's `token_visible_to_children` stays the literal PENDING (the finding is the walks').
- Red first: Fold2 (1 failure, 2 errors), test_preflight (1 failure); then green; witnesses red; R8.residuals updated (9 residuals); pending 20 to 19.

## Review fold (REVIEW-d8-furniture-e692ce7.md: M1, m1, m2, m3, n1), stage 9

- M1: FURNITURE no longer counts the model's words. Gemini's `gemini` entry drops `toolCalls[].description` and `toolCalls[].resultDisplay`; the stream `tool_result` keeps `error.type` only (n1); Claude's `attachment:queued_command`, `system/task_started`, `system/task_notification` and `system/background_tasks_changed` are narrowed to their CLI keys.
  The real-walk test `ReviewFold.test_no_furniture_position_holds_the_models_words_on_any_walk` reads all 225 walks (about 6 s): each record's model strings (tool-call arguments, written file text, Bash commands, messages, thoughts), gathered in file order, are searched for in every furniture leaf; bare paths, strings under 16 characters, and strings the model copied from the CLI's own text written before its first words are not counted (the last because Gemini's session context lists the repository's files and is re-sent mid-session).
  Red first: 16 positions (exactly the review's list), then 0. Witness: listing `toolCalls[].description` again goes red.
- Re-run over the walks: codex 0 rows over 38; gemini **1 row over 36**: w-g17 "gap study" now only as `native-result:grep_search` (3), the agent's own search results, no longer `furniture:gemini`; round 3 0 rows over 54.
- m1: the claude-code list adds `attachment:auto_mode`, `attachment:deferred_tools_record`, `ai-title` (type and sessionId only: its title is a model's summary), the session `system` record and `user:no-visible-output-nudge`, none carried by any round-4 walk, so cited to the view's own table lines (`transcript_view.py:278, 280, 304, 305, 331`; the test checks each cited line names the kind); and `user:scheduled-wakeup`, carried by 8 Claude walks (evidence w033 line 96, w116 line 86), envelope only, since its content is the model's own prompt. `record_kind` names the two isMeta shapes.
- m2: completeness is now tested on every walk (`test_the_lists_are_complete_on_every_walk`), and the review's two mutants (drop `attachment:queued_command`, drop `system/task_started`) go red in `test_witness_a_dropped_kind_goes_red`.
- m3: `usage.service_tier` is an account-plan entry in the claude session `assistant`, stream `assistant` and `result/success`.
- Draft regenerated (pending stays 19); lint 0; Readiness clauses and four mutants red; test_awareness_furniture 22 OK, test_scan_record 209 OK, test_sidecar audit 12 OK.

## Closure fold (REVIEW-d8-furniture-e692ce7.md Closure: c1, c2 and three NITs), stage 10

- c1: `tests/test_build_draft.py` `stage8_recount()` re-derives from the walks every count and list stage 8 published (the Gemini key walks and their list, the final-snapshot and stream counts, the 11 source tool calls by command, the "gap study" walks per harness, the auth.json walks); `Stage8Recount` binds the phrases rendered from it to both build_draft's text and the committed draft. Red first: 6 failures; then green. Witnesses: 45 to 46, "0 of the 38 Codex" to 37, w-g12 dropped: each red.
- c2: reproduced here: 66 occurrences across all committed Gemini files, of which the final snapshots hold 45 and the streams 11 (the earlier snapshots repeat the rest); 11 tool calls: 8 `env`, 2 `env | grep -i gemini` (w-g12, w-g24), 1 `python3 .tmp/check_policy.py` (w-g24). The finding now publishes the final-snapshot and stream counts separately, each with what it counts, and names the sources as env listings and one script's output.
- NITs: the Codex exec user is cited at its constant (run_take.py:62) and its enforcement (:1266-1267, :1282; the Codex road :1438-1439, :1447); the observed text says 1 of w-g17's 3 matches is the CLI echoing the model's own pattern ("No matches found for pattern", line 154; the other 2 are README line 28 at line 129); the six view-cited claude-code kinds render "admitted by the view, carried by no walk", and the session `system` entry drops its content (it can carry an operator's slash command).
- Draft regenerated (pending 19); lints 0; test_build_draft Stage8Recount, Fold2, LayerNote, OwnerSlots 13 OK; Readiness clauses green and four mutants red; test_awareness_furniture 22, test_scan_record 209, test_preflight 59 OK; R9.sessions still the base's own red.

## Athena battery on 98a1bae7 (gap4-d8f-98a1bae-98a1bae-20261022T083748Z): 28 FAIL lines read against d5c0f798

Every command ran on the Mac in its own process, behind light-ok (test_build_draft and its witnesses in the heavy slot), once in a detached worktree at d5c0f798 and once at the lane head; failing test names and last output lines compared.
Lane's own, fixed:
- `w4c-cp2-sidecar-scan.txt:11` (CP2's grep: scan_record.py named the harnesses): stage 11 moves the tables to `box/harness_furniture.py` (data only, in test_sidecar's BOX_MODULES audit; claimed by the new `COPIED.d/d8-furniture.json`); scan_record reads them generically. The grep is green; copy_manifest --check ok.
- `test_walk_layout` L1OneName (`awareness_furniture.py` spelled the rehearsals root): it now takes `mode_binding.WALKS_DIR` (stage 11).
- `lint_language`: the new fragment's text added one finding ("out of"), reworded before commit; head and base now both carry the same 5 findings, all in native-readers review files.
- `test_build_draft` Description.test_mode_residual_is_bound (expects 8 box residuals; fold 2 added the ninth): count updated (stage 12).
Same failing names and messages at d5c0f798 (pre-existing): test_native_snapshot (3, twice in the battery), test_native_history_record (2), test_vendor_take_records (3), test_vendor_checker_road (4), test_native_reader_registration (2), test_pending_walk (23), walk_regrade --check (28 problems), test_codex_identity (1), test_pending_codex_walk (8), test_vendor_admission (1), test_vendor_admission_regrade (3), test_vendor_walk_road (2 tests, 6 failures), test_freeze_shapes (1: test_fs_check_the_committed_draft_names_every_leg), test_rehearsals (1), test_walk_layout L7 (1), mode_binding --walks --check (74 of 225 walks drift), lint_language (5), test_build_draft Description.test_commitments (R9.sessions) and its six `--witnesses` runs (each times out at base and head).
test_build_draft's Readiness.test_committed_writer fails at base (its committed draft is stale) and passes at head (regenerated).
test_round4 (the whole battery) was not run on the Mac; its reds are the module reds above.
