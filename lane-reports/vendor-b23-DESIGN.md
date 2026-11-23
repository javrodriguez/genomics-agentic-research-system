# vendor-b23 design note: grading a Codex patch edit as a shell edit is graded (round 1, no code)

Local executor, Tue 20 Oct 2026, 17:40 EDT / 21:40 UTC, on `a76b4dd2` (branch lane/vendor-b23-20261020).
Ruling B23-1 (glitch-26): design first; stop for the ruling.
Inputs: the review of B22 (`/Users/javrodher/aegis-builds/REVIEW-vendor-b22-a76b4dd2.md`, its M1, m1, m2, n1 and n3), lane-reports/vendor-b22-DESIGN.md and vendor-b22-LANE.md.

## 0. The question and the short answer

After B22, a GPT take that edits a file through Codex's patch tool passes the stream adapter and enters the view as one `edit` or `write` call per change.
Three readers still hold it, so once arm O's other PENDING rows settle, only the takes in which the model chose its patch tool would stay ungraded:
- check_take's T-8:file-change leg (check_take.py:3775, 4816-4828) returns PENDING for any Codex stream that holds a file_change item;
- codex_native.read_rollout refuses a FileChange TurnItem (codex_native.py:157-158), which makes check_take's reach (vendor_raw_records, source 2) transcript-unreadable and makes the drive's cross-check `refused` once a Codex reader is registered;
- codex_native.read_exec refuses a file_change exec item (codex_native.py:317-318), so the cross-check's join refuses it too.

Short answer:
- The graded view already holds what the graders read (path, and write versus edit). No view grader reads edit content, for Claude or for Codex.
- The one reader that reads content is reach (T-8), which reads every string of every tool record. For a patch, the content lives in the rollout: the patch text in a READ response_item, and the FileChange item's per-file content, diff and rename target.
- So the change is in the rollout reader (admit and project FileChange on its pinned shape), the join (match file changes by order), check_take's reach (read the FileChange item, its path keys as values), and a T-8:file-change reader wired at the row's one site.
- Two gaps need a ruling: m1 (a started patch that never completes) and n3 (a rename). I recommend the view keep the attempted edit as an unanswered call (m1) and the T-8 reader hold a rename take under a named reason (n3). Sections 6 and 7.
- Two more gaps of the same kind turned up in the source (section 8). They are named for the ruling, not built.

## 1. Sources read

- openai/codex at `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`, B22's pin.
  - `git ls-remote https://github.com/openai/codex.git 'refs/tags/rust-v0.162.1^{}'` printed `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`.
  - I fetched it read-only (`git fetch --depth 1 --filter=blob:none origin 092d3acd...`) into this session's scratchpad, and `git rev-parse FETCH_HEAD` printed the same commit. Every file below was read with `git show 092d3acd:<path>`.
  - Short names used below: EP = codex-rs/exec/src/event_processor_with_jsonl_output.rs; EV = codex-rs/core/src/tools/events.rs; AP = codex-rs/core/src/tools/handlers/apply_patch.rs; CAP = codex-rs/core/src/apply_patch.rs; PR = codex-rs/protocol/src/protocol.rs; IT = codex-rs/protocol/src/items.rs; PO = codex-rs/rollout/src/policy.rs; IB = codex-rs/app-server-protocol/src/protocol/item_builders.rs.
- The lane clone at `a76b4dd2`: transcript_codex.py, codex_native.py, codex_adapter.py, check_take.py (its T4 vendor section), vendor_record_binding.py, native_reader_registration.py, drive.py (codex_cross_check), transcript_view.py (CC_TOOLS), the graders, build_draft.py, box/take_config.py, lane-reports/vendor-T4-TABLE.md and vendor-T4-PLAN.md.
- athena, read-only over `ssh athena`, file names only. Under `/home/javier`, at a depth of up to 7:
  - No `rehearsals/w-o*/.../native-turn-*.jsonl` holds the string `"FileChange"`.
  - The one turn stream that holds `"file_change"` is w-o38's `turn-1.jsonl`, whose rollout was never copied out (B22 section 1).
  - So no recorded rollout of a patch edit exists anywhere I can reach. Every rollout fact below comes from the source.
- No transcript, rollout or session content was printed, copied or committed.

## 2. What one patch edit leaves in each record

The patch tool is `apply_patch`, a freeform custom tool: its input is the patch text (AP:279, 289-291, 317).
In code mode (the box's sessions), every tool other than `exec` and `wait` may be called from inside `exec`'s JavaScript (codex-rs/code-mode-protocol/src/description.rs:262-264).
The 31 committed GPT walks' 76 rollouts hold only `custom_tool_call` records named `exec` (B22 section 4a).
So the patch text sits either in an `exec` call's input (nested) or in an `apply_patch` call's input (direct).
Both are `custom_tool_call` response_items, which are READ by check_take (CODEX_RESPONSE_READ, check_take.py:3973).
Which of the two holds it is inferred, not seen: no recorded rollout holds a patch.

| record | what a patch edit leaves | source |
|---|---|---|
| exec stream, item.started | `file_change` {id `item_<n>`, changes [{path, kind}], status `in_progress`}, written at the tool's Begin stage, before the patch runs | EV:241-263; AP:544; EP:343-351, 477-482 |
| exec stream, item.completed | the same changes, status `completed` or `failed` (declined prints `failed`), same exec id | AP:572; EV:275-360, 599-619; EP:182-206, 337-341 |
| exec stream, per change | `path` (the source path, a lossy string) and `kind` add / delete / update; an update with a rename prints `update` with no destination | IB:342-363; EP:190-196 (`Update { .. } => Update` at :194) |
| exec stream, the content | none (exec drops the diff) | EP:182-206 |
| rollout, event_msg item_completed | `FileChange` {id (the call id), changes {<source path>: change}, status, stdout, stderr}; auto_approved is absent (None) on the completed item | EV:605-615; IT:411-426; PO:249, 280 |
| rollout, each change | `{"type": "add", "content"}`, `{"type": "delete", "content"}` or `{"type": "update", "unified_diff", "move_path"}`; `move_path` is the rename target or null | PR:4228-4240; CAP:64-90 |
| rollout, status | `completed`, `failed` or `declined` (snake_case) | PR:3764-3770 |
| rollout, started | not written (paginated history drops ItemStarted and PatchApplyBegin) | PO:201, 211 |
| rollout, response_item | the patch text, in a `custom_tool_call` input, and the tool's reply in `custom_tool_call_output` | AP:279, 317 |
| end-state snapshots | the files as the patch left them, as for any shell write | graders/endstate.py (reads snapshots only; B22 section 5) |

Rollout ordering: `changes` is a Rust HashMap, so its key order is unspecified.
The exec stream's list is the same paths sorted (IB:351), so a join must compare sorted paths.

## 3. Who reads an edit, and what each reader needs

Shell edit (any arm): a `shell` call with its command text, and its result.
Claude Write/Edit: a `write` or `edit` call with `{path}` only. transcript_view's CC_TOOLS drops content, old_string and new_string from the view (transcript_view.py:258-259).
Codex patch after B22: one `write` (add) or `edit` (update) call with `{path}` per change, plus its result.

| reader | reads | needs from a patch | met today? |
|---|---|---|---|
| pause_adherence | every tool-call (graders/pause_adherence.py:253) | one call per change, at the time it was made | yes for a completed patch; m1 for a started-only one (section 7) |
| precondition_refusal | write and edit paths, shell command text (precondition_refusal.py:360-363, 451-485) | path, write versus edit | yes |
| new_tasks | write and edit paths after the probe (new_tasks.py:542-547) | path | yes; for a rename, see n3 (section 6) |
| scope_read | read, write and edit paths, shell commands, search patterns (scope_read.py:231-241) | path | yes |
| plan_gate | shell commands only | nothing | yes |
| endstate and the end-state graders | snapshots only | nothing from the stream | yes |
| reach, T-8 (study-materials-reached, read-outside-the-checkout) | every string of every tool input and result (check_take.py:302-322; study_paths_read reads json.dumps, keys too) | every string of the patch: paths, content, diff, rename target | partly: the stream's paths are read (_codex_exec_records) and the response_item patch text is read (source 3), but the rollout's FileChange item refuses the whole rollout (codex_native.py:157-158), so the take reads transcript-unreadable |
| the drive's cross-check (codex_join_session, once a Codex reader is registered) | the exec stream joined to the rollout by order and type | file changes matched between the two | no: read_exec refuses file_change (codex_native.py:317-318) |

So no view grader needs anything more, and parity is decided in the rollout reader, the join and reach.

## 4. codex_native's two refusals: what they guard, and what reading FileChange needs

**What they guard.** Both are the subset's fail-closed rule: a record whose shape the reader has not pinned is refused, never projected on a guess.
- `_item` (codex_native.py:153-158) projects only UserMessage, AgentMessage, Reasoning and CommandExecution.
- read_exec (:315-318) accepts only agent_message, reasoning, command_execution and the reroute error.
- The T4 table records the same choice (vendor-T4-TABLE.md row 8: "file_change content PENDING (transcript-unreadable; the cross-check already refuses it, D/codex_native.py:82, 317-318)"; vendor-T4-PLAN.md:98: "until a recorded rollout shows the patch record and a reader of its text exists").

**What reading it needs, from the pin.**
1. read_rollout `_item`: admit `FileChange` only on its pinned shape:
   - item keys exactly {type, id, changes, status, stdout, stderr}: emit_patch_end always sets status, stdout and stderr and leaves auto_approved None (EV:605-615), and IT:414-425 skips None fields;
   - `id` is a non-empty string;
   - `status` is in (`completed`, `failed`, `declined`);
   - `stdout` and `stderr` are strings;
   - `changes` is a non-empty object whose keys are non-empty strings, each value one of: {type `add`, content str}; {type `update`, unified_diff str, move_path str or null}.
   - `delete` stays refused, as in the stream tables (Q-w11a-3; section 8b).
   Project it into the turn's output as `{"kind": "file_change", "status", "changes": [(path, kind, move_path)] sorted by path}`.
   Docstring: the FileChange line moves from "every other tag refuses" into the projected list, citing IT:411-426, PR:4228-4240, PR:3764-3770, EV:599-619 and PO:249-280.
2. read_exec: PROJECTED_EXEC_ITEMS gains `file_change`. The completed one joins `items` and the started one is skipped, exactly as command_execution is (codex_native.py:319-320).
3. join: the stream's completed file_change items and the rollout turn's file_change outputs are compared by order, as commands are (codex_native.py:412-420):
   - equal counts ("file change count disagrees");
   - per pair, the stream's paths equal the rollout's sorted keys, and kinds equal (add to add, update to update);
   - status agrees: `completed` to `completed`, and `failed` to `failed` or `declined` (EP:201-203).
   The stream cannot show a rename, so a rename agrees here on its source path; section 6 is where it is read.
   join's result gains `file_changes` (a count). codex_join_session's shapes stay as they are (native_reader_registration.py is not edited; Q6).
4. Known false-refusal risks, named as the docstring names its others (review nit N11): a FileChange with an auto_approved key (only the Begin item sets it, and paginated history does not persist ItemStarted); a non-UTF-8 path (to_string_lossy makes the stream's path differ from the key); a patch whose two hunks name one file (the HashMap keeps one). None is admitted unseen.

codex_native.py is in native_reader_registration.CODEX_SOURCES. No codex-acceptance.json exists (`find evals/gap-study-4 -name codex-acceptance.json` printed nothing), so no registration moves. tests/check_vendor_sources.py must not list this lane's files under a T4 piece.

## 5. check_take: reach over FileChange, and the T-8:file-change reader

**Reach (source 2).** _codex_rollout_records (check_take.py:4044-4067) adds every FileChange item as one tool record, as it adds CommandExecution:
- `changes` is handed to reach as a list of {path, ...change} built from the map. _tool_strings walks dict values, never keys (check_take.py:313-321), so a path that stayed a key would be read by study_paths_read (json.dumps) and missed by outside_checkout_reads.
- asked: id and changes (path, content, unified_diff, move_path); returned: VENDOR_RETURNED_FIELDS gains `"FileChange": ("stdout", "stderr")`.
- The stream's file_change items are already read (_codex_exec_records, check_take.py:4030-4041), and so is the patch text in its response_item (source 3).
- Multiplicity (not new, for the record): reach counts read-outside-the-checkout once per mention. A Codex patch path then appears in the started and completed stream items, the FileChange item and the patch text, as a Codex command already appears in four records. A Claude Edit names its path once.

**The row.** T-8:file-change stays PENDING in this lane.
A SAME row needs a RECORDED fixture labelled at a walk on codex-cli (check_take.py:3803-3820), and no recorded rollout holds a FileChange (section 1).
Settling it waits on the same gate as every other arm O row. Today T-16 and T-18 refuse every Codex take unconditionally (check_take.py:4787-4797), and VENDOR_READER_ITEMS["codex"] names no fixture.
What this lane changes is the site.
- Today, `vendor_file_change_problems` returns `vendor_pending("codex", "T-8:file-change", None)`. It will hand in a named reader, `vendor_file_change_reads`, with the take's path.
- While the row is PENDING, the refusal text is byte for byte today's.
- Once the row is settled, the reader decides. A take that edits through the patch tool then goes unread only for a named reason, never because of the tool it chose.

**The reader, `vendor_file_change_reads(path)`** (a function of check_take.py, as vendor_row_problem requires):
- [] when every turn's completed stream file_changes join the last retained rollout's FileChange items under section 4's rule 3;
- `[transcript-unreadable] ...` naming the first disagreement when they do not join (a patch edit whose content no record holds);
- the n3 hold (section 6) and the m1 rule (section 7) as ruled.

## 6. NIT n3: a rename

- What Codex prints: a patch with `*** Update File: a` and `*** Move to: b` prints in the stream as one change {path a, kind update} (EP:194). The rollout keeps it as {a: {type update, unified_diff, move_path b}} (CAP:76-83).
- So the view reads it as an edit of a, and nothing in the view names b. new_tasks and precondition_refusal match paths, so a rename into a guarded or generated path would not be seen.
- Nothing in the stream tells a rename from a plain update. Only the rollout can. A view built from the rollout is wider than B23-5 allows.
- Recommendation (Q2): the T-8 reader holds a take whose rollout holds a FileChange update with a non-null move_path, as `[transcript-unreadable] a rename through the patch tool (a -> b): the exec stream names only the source path`. The take is held under a named reason, so it is counted, never read as an edit of a.
- The alternative is to read it as an edit of the source path and name that as a difference.
- No committed walk holds a rename, and the shell road's `mv` is a shell call whose text the graders already read.

## 7. Review m1: a started file_change with no completion

- When it happens: exec closes every unfinished started item at turn end, whatever the turn's status (EP:370-385, called at :524 before the status match). A started-only file_change therefore remains only when exec itself is killed, as by a take's timeout.
- Why it matters: timed-out takes are graded (check_take.py:811-906: `timed-out` is an outcome the graders read, "2 of 3, one timed-out").
- After B22 the view maps item.started:file_change to nothing (transcript_codex.py:217-219), so such an attempted edit vanishes.
- A started-only command, by contrast, stays in the view as a call with no result. A Claude session writes its tool_use before the tool runs, so a killed Claude Edit stays a call too.

Recommendation (Q1): option C, the view keeps the attempted edit, which is parity with both:
- item.started:file_change maps to one tool-call per change (add to write, update to edit, {path}, ref `<id>#<i>`). item.completed:file_change maps to its results only.
- CodexParser keeps one map per stream: exec id to the started change list. It is reset at thread.started, which opens every exec stream; vendor_record_binding and vendor_shell_commands both drive one parser across a take's streams.
- A completed file_change refuses (ShapeError) when its id has no started record in the stream, or when its changes are not the started record's in the same order.
  - The pinned handler emits Begin before it runs the patch and Finish after it (AP:544, 572), and both carry the same `changes` (EV:241-263, 599-615).
  - Exec gives a completed item with no started one a fresh id (EP:337-341), so that case would come only from another writer.
- A second item.started with the same id refuses.
- The view of a w-o38-shaped stream is unchanged: each started record is followed directly by its completion, so the calls and results come in the same order with the same refs.
- The committed walks hold no file_change, so they read identically.
- Cost: CodexParser's per-line statelessness, B22-6's "started maps to nothing" (reversed by this ruling), and a ShapeError raised by the view that check_record does not raise (the adapter admits the stream; the check refuses it as transcript-unreadable).

Option B, narrower and in the review's words: refuse a stream whose started file_change id has no item.completed with that id.
- The view cannot see a stream's end per line, so the refusal sits in the T-8 reader (`[transcript-unreadable] a patch the take's cut left unfinished`).
- The take is held rather than misread, but takes cut mid-patch leave the graded set, which is a small selection on a timed-out take's last tool.

## 8. Two further gaps of the same kind (named for the ruling, not built)

**8a. A patch the tool refuses before Begin vanishes.**
- When it happens: a patch that does not parse, or fails verification (AP:322-328, 362-381, 466; prepare_apply_patch's `?` at AP:525, before AP:544), returns an error to the model and emits no FileChange item at all.
- Where it is still visible: the stream and the view hold nothing for it. The rollout holds only the patch text and the error reply, in the custom_tool_call records, and nested in `exec` when in code mode.
- The Claude side: a Claude Edit that fails (old_string not found) stays a call with an error result.
- Effect: pause_adherence would not count a malformed patch attempt made after a wait point, so arm O would read more adherent than it acted.
- A structural reader would have to parse `exec`'s JavaScript, or match the error text, and both are fragile.
- Recommendation (Q5): record it as a named difference now, and measure it from the first recorded rollouts. Not in B23.

**8b. `delete` stays refused (Q-w11a-3), in the stream and so in the take.**
- What happens: a patch that deletes a file is refused by check_record, so read_stream raises StreamError at the drive and the walk is held, as w-o38 was held before B22.
- Selection: that is the same kind as M1, on a different patch kind. Its truthful reading needs a ruling on what a delete is in the view, which has no delete kind; a shell `rm` is a shell call.
- Content note: the rollout keeps the deleted file's content (CAP:73-75), which reach would read as asked.
- Recommendation (Q4): a follow-up lane after a recorded rollout. Not in B23.

## 9. Proposed build for B23-2 (after the ruling)

Product files: codex_native.py, check_take.py, and transcript_codex.py (only if Q1 is option C).
Not touched: codex_adapter.py and READ_SHAPES, vendor_record_binding.py, drive.py, native_reader_registration.py, every Gemini and Claude table, the scanner, preflight, postflight, sidecar and bookkeeping.

Red first, from synthetic records shaped like w-o38's (types, keys and counts only; invented paths; no recorded bytes):
- R1, rollout: a turn holding a FileChange {update, move_path null, status completed} beside a CommandExecution. read_rollout refuses it today with "TurnItem 'FileChange' is unsupported in this subset"; green, it projects one file_change output.
- R2, exec: a stream with started and completed file_change. read_exec refuses it today with "item 'file_change' is unsupported in this subset"; green, join agrees with R1's turn, and its `file_changes` is 1.
- R3, reach: a take whose rollout and stream hold a patch to a path outside the checkout. vendor_reach reads transcript-unreadable today; green, it reads read-outside-the-checkout with the path.
- R4, the site: with the row settled in a test (the existing `settled` helper), vendor_file_change_problems calls `vendor_file_change_reads` and returns [] for a joined take. While the row is PENDING, the text is byte for byte today's.
- R5, n3: a rename in the rollout gives the named hold.
- R6, m1, as ruled: option C, a cut stream holding a started-only file_change, whose view holds the edit call with no result; or option B, the named refusal.

Witnesses, each red alone:
- FileChange dropped from the projected list;
- the status pin widened, so a `pending` status passes;
- a key added to the item, or auto_approved admitted;
- `delete` admitted;
- the join's path comparison made unsorted, then dropped;
- the declined-to-failed status rule dropped;
- the path keys handed to reach as keys, not values (outside_checkout_reads misses the path);
- the reader not handed in at the site;
- the rename hold dropped;
- for option C: the started mapping returned to nothing (the cut stream's call vanishes), and the parser state not reset at thread.started (a second stream's `item_0` collides).

Unchanged readings, checked:
- every Claude and Gemini fixture's view and reach is byte-identical before and after;
- B22's `--walks` against the records clone reads the same 76 streams of 31 walks identically before and after (sha256 of the readings);
- test_codex_native, test_codex_adapter (D8_ITEMS and EVENT_TYPES pins), test_codex_started_file_change, test_vendor_body (its "file_change read as clean" mutant follows the site's new text), test_vendor_check and test_take_config stay green on the Mac where each fits under its bound;
- `--generated-mutants` and the suites are athena's.

Records:
- COPIED.d reasons gain one B23 sentence for each edited file, and the new test claim rides with its red commit (F21-2).
- The lane file names the commits and quotes the runner lines.

## 10. B23-3: the parity note (text proposed; built through build_draft.py after the ruling)

One entry, appended to build_draft.py's `parity_notes` after "silent_turn_reminder". It is the only change in prereg-draft.json, and `build_draft.py --check` must print ok:

```
{"of": "Delegation (vendor arms)", "text": "Both vendor arms run with delegation switched off, because the study refuses delegation on the vendor side. Arm G's settings add invoke_agent, Gemini CLI's sub-agent tool, to tools.exclude beside D8's two web tools (R-B14-2, glitch-26). Arm O's config.toml sets [agents] enabled = false, which makes Codex's multi-agent version Disabled ahead of the model catalog's v2, so its six collaboration tools (spawn_agent, send_message, followup_task, wait_agent, interrupt_agent, list_agents) and its two multi-agent developer sections are not offered (B22-10, glitch-26, 20 Oct 2026). The Claude arm keeps its Agent tool and reads its sub-agents' records as the agent's own (the notes Agent and Agent grading). That is the named difference: the Claude arm may delegate, and neither vendor arm is offered a delegation tool. No committed vendor practice walk called one, and the GPT practice walks before 20 Oct, which were offered Codex's six tools, are not byte-comparable with later walks on those prompt sections."}
```

The facts in it are cited at box/take_config.py:72-78, 131-132 and 444-446, and in lane-reports/vendor-b22-DESIGN.md section 10.
The "20 Oct" date for B22-10 is from take_config.py:72. R-B14-2's date is not written in take_config.py, so the note gives none.

## 11. B23-4

B23-4's correction line about world_state.rs:108-138 and turn.rs:1294 is in lane-reports/vendor-b23-LANE.md. B22's design note stays as written.

## 12. For the ruling

1. **Q1 (m1).** Option C (the view keeps a started patch as an unanswered call; section 7) or option B (the T-8 reader refuses a cut patch). Recommended: C.
2. **Q2 (n3).** The T-8 reader holds a rename under a named reason, or reads it as an edit of the source path as a named difference. Recommended: hold.
3. **Q3 (the row).** T-8:file-change stays PENDING with its reader wired at the site, and settles SAME only on a RECORDED fixture from a walk whose retained rollout holds a FileChange.
   That needs a GPT walk that edits through the patch tool and copies its rollout out (athena; the walk operator's). w-o38 shows gpt-6-luna does choose the patch tool, but its rollout was not kept.
   Recommended: yes, with no flip in this lane.
4. **Q4 (delete).** Q-w11a-3 stands in B23. A follow-up lane rules what a deleted file is in the view, after a recorded rollout.
5. **Q5 (a patch refused before Begin).** It is a named difference in the lane file now and is measured from the first recorded rollouts. Not built here.
6. **Q6.** codex_join_session's shapes do not gain a file_changes count (it would edit native_reader_registration.py). Recommended: no, under B23-5; the acceptance review can read join's count.

## 13. Not touched

No code, no test, no fixture.
The records clone and athena were read only (athena: file names only).
No push, no mirror, no athena run.

## 14. Addendum (Q5, appended Tue 20 Oct 2026, 17:48 EDT / 21:48 UTC): which record carries a patch refused before Begin

glitch-26's ruling Q5: if a record carries the attempt, read it as an edit call with a refused result in the view; if none does, it becomes a named limitation of arm O in the parity notes.
Source: the same pin, read from the commit's tarball (`codeload.github.com/openai/codex/tar.gz/092d3acd...`, extracted in the session scratchpad and searched with grep).
Counts: the 31 committed GPT walks' 76 rollouts in the records clone, read through `git show`, counts and key names only.

**How arm O reaches the patch tool.**
- Both arm O models' catalog entries set `"tool_mode": "code_mode_only"` and `"apply_patch_tool_type": "freeform"` (models-manager/models.json, gpt-6-luna and gpt-6.1-sol).
- requested_tool_mode takes the model's tool_mode first (core/src/tools/mod.rs:76-85).
- ApplyPatchHandler keeps the default exposure, Direct (codex-rs/tools/src/tool_executor.rs:113-115), which is available in code mode (:93-96).
- Under code_mode_only, a nested-capable tool is hidden from the model's direct list (core/src/tools/spec_plan.rs:838-850).
- So arm O calls apply_patch only from inside an `exec` cell's JavaScript. The rollouts agree: their 423 custom_tool_call records are all named `exec`.

**What each record holds for a patch refused before Begin.** Begin is reached only after the patch parses and verifies (AP:322-381, then execute_verified_patch, Begin at AP:544).
- Exec stream: nothing. A tool call emits no turn item of its own (core/src/stream_events_utils.rs:340-357: the call is dispatched; only non-tool items become turn items there). The handler returns its error to the cell before any emitter runs. No core/src/tools/code_mode file emits a turn item (grep for emit_turn_item over core/src: the emitters are the tool events, MCP, hooks, review, compaction, user shell and the named handlers; code mode, the router and the registry are not among them).
- Rollout event_msg: nothing, for the same reason: no TurnItem exists to persist.
- Rollout response_item metadata: the executed-call recorder (core/src/tools/executed_tool_calls.rs:490-593) would record a nested call's name and arguments. It is gated on Feature::ExecutedToolCallMetadata, `default_enabled: false` (features/src/lib.rs:1111-1114), and the box sets only hooks and plugins (box/take_config.py:69).
  The committed rollouts confirm it: 989 of 1888 response_items carry metadata, with the key sets {client_authored, fallback_token_limit_override} (423, the exec outputs) and {client_authored, mcp_attribution, retained_source, user_input_order} or subsets (566, messages); none records a call.
- Hooks: the one FunctionCallOutput turn item is a hook's (core/src/hook_runtime.rs:755), and hooks are off in the box.
- What remains: the attempt survives only as text, inside the `exec` cell's JavaScript (the custom_tool_call input) and in whatever the cell printed back (its output). Reading that program as calls would be a guess at what code ran, which the closed rule refuses.

**Conclusion.** No record carries a patch refused before Begin as a call, so per Q5 it is a named limitation of arm O, built as a second parity-note entry beside the delegation entry (B23-3).
Text:

```
{"of": "Patch refused before it starts (arm O)", "text": "A named limitation of arm O. Both arm O models reach Codex's patch tool (apply_patch) only from inside the exec tool's JavaScript cell (their catalog sets tool_mode code_mode_only), and the tool writes its file_change record only once a patch has parsed and been verified. A patch it refuses before that (one that does not parse, or fails verification) leaves no structured record: no exec-stream item, no rollout item, and no executed-call metadata (that Codex feature is off by default and the box leaves it off; 0 of the 989 metadata records in the 76 rollouts of the 31 committed GPT practice walks record a call). It survives only as text in the cell's program and in what the cell printed back, which no reader parses as calls. So such an attempt is not a call in arm O's view: pause_adherence does not count it and no path grader sees it, while a Claude Edit its tool refuses stays a call with an error result. A refused patch changes no file, so the end-state graders read the same. The gap can only make arm O read more adherent than it acted, by the refused patch attempts, which the study's records cannot count."}
```

**One deviation from section 7, flagged.**
- Section 7 proposed that a completed file_change whose id has no started record in its stream refuses. I am not building that.
- Why: the committed D8 fixture `tests/fixtures/codex-streams/turn1-tools.jsonl` and test_vendor_body's file_change case hold completed-only file_changes. Exec itself prints a completed item with no started one under a fresh id (EP:337-341).
- What I build instead: a completed file_change with no started record keeps today's mapping (its calls and results at the completion), so every existing reading stays byte-identical.
- What still refuses: a completed file_change whose started record exists in the stream but whose changes differ, and a second item.started with the same id.
