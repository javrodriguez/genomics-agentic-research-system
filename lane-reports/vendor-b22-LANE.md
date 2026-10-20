Status: design stop (round 1)

## ROUND 1 (local executor, Tue 20 Oct 2026, 16:53 EDT / 20:53 UTC)

glitch-26's ruling B22-1: design first, no code. Base `19c7a88f` (B21 at `45239b01` plus B21-9's two check lines).

- Design note: lane-reports/vendor-b22-DESIGN.md.
- Reproduced on `19c7a88f` with a synthetic record of w-o38's shape: check_record raises `ShapeError: item.started carrying 'file_change': only ('command_execution', 'mcp_tool_call') are pre-registered there`, and read_stream raises the live text, word for word.
- Source: openai/codex `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d` (`git ls-remote ... 'refs/tags/rust-v0.162.1^{}'` printed it), fetched read-only into the session scratchpad.
  The pinned exec prints file_change in item.started (EP:343-351, 477-482; core events.rs:241-263), always with status `in_progress` (v2/item.rs:1028-1035), and its keys are exactly the table's entry.
- Counts (types, keys and enum values only):
  - 31 committed GPT walks, 76 turn streams: command_execution 188 started and 188 completed, agent_message 141 completed, thread.started, turn.started and turn.completed 76 each; no file_change, no other item type, no item.updated.
  - w-o38 turn 1, 26 lines: command_execution 8 started and 8 completed, agent_message 3, file_change 2 started (status `in_progress`) and 2 completed (status `completed`), one `update` change each, change keys `kind, path`.
- Recommendation: STARTED_ITEM_TYPES gains FILE_CHANGE, with a started file_change's status pinned to `in_progress`; CodexParser maps item.started:file_change to no view item, so the view keeps one call per change (otherwise pause_adherence and the other call readers would see a phantom `other` call).
  READ_SHAPES, codex_adapter.py, the Gemini and Claude tables: unchanged.
- Named for the ruling, not admitted: file_change kind `delete`, collab_tool_call (multi_agent on by default, spawn_agent offered, 0 seen), non-reroute error items. Ruled out by the box's config: todo_list and item.updated (update_plan off), web_search (disabled).
- Downstream, recorded only (B22-4): check_take's T-8:file-change PENDING row and codex_native's two "unsupported in this subset" refusals meet any take holding a file_change; today's walks stop at `pending-native-reader` before either runs.
- Not touched: code, tests, fixtures, the records clone, athena (read only). Nothing pushed.

RESUME HERE: design stop; waiting for glitch-26's ruling on section 6 (and the names in section 7).
