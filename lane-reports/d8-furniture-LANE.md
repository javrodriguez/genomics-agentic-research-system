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

## Stages

(filled as committed)
