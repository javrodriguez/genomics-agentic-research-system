---
date: 2026-11-20
status: standing
kind: defect
touches:
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/_system/session_state.sh
  - gars/tests/test_every_tool_name.py
symptoms:
  - under Claude Code, a tool call named outside the eight judged names (Edit, Write, MultiEdit, NotebookEdit, Bash, Read, Glob, Grep) never reaches the guard
  - guard_hook.decide() returns allow for any tool name outside those eight, and for a missing, empty or non-string tool name
  - an MCP tool or claude.ai connector call writes over files.csv or into _system/ with no refusal from the guard
---
# The guard judges every tool name under Claude Code: judged, passed by exact name, or refused

Closes [0107](0107-pg-nonpublic-projects-closed-to-reads.md)'s "What this does not close" item 6 (tools the matcher does not name) and its Row 4 follow-up "widening the hook matcher" (OrgOS T38).
It makes [0042](0042-a-call-the-guard-cannot-judge-is-refused.md)'s rule, "a call the guard cannot judge is refused" (R-098, owner ruling 3A), true under Claude Code; 0042, 0107 and 0266 stay as written.
Rulings are the lane orchestrator's (glitch-e9, lane guard-default-deny), made under the owner's standing delegation; no sentence in this record is the owner's.

## Context

The owner's 15 Oct hand-off named the gap, for after the Gap Study round 4 results.
Under Claude Code two layers failed together.
The PreToolUse matcher in `gars/.claude/settings.json` was the exact-name list `Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Glob|Grep`, so Claude Code never called the hook for any other tool.
And `decide()` in `gars/_system/guard_hook.py` handled only those eight names; any other name, and a missing, empty or non-string `tool_name`, fell through to `return None` (allow).
The Codex arm (`codex_hook.py`, decision 0266) was already default deny: it judges `Bash`, `apply_patch` and `view_image`, passes a cited list of twelve names, and refuses every other name.

**Reproduction.** At the lane base `c5ba8425`, payloads built with `json.dumps` and piped to `gars/_system/guard_hook.py` with `CLAUDE_PROJECT_DIR` pinned to the checkout's `gars/` (outside paths named only as non-existent paths):

```
matcher in settings.json: ['Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Glob|Grep']
control Write into _system/    'Write'                        DENY  | Blocked: _system/evil.py is protected template or machine-owned state; a workspa
control Read outside           'Read'                         DENY  | <non-existent outside path> is outs
MCP write over files.csv       'mcp__filesystem__write_file'  ALLOW |
MCP write into _system/        'mcp__fs__write_file'          ALLOW |
MCP read outside               'mcp__fs__read_file'           ALLOW |
connector shape                'mcp__claude_ai_Gmail__send'   ALLOW |
PowerShell                     'PowerShell'                   ALLOW |
Monitor                        'Monitor'                      ALLOW |
Agent                          'Agent'                        ALLOW |
unknown future name            'FutureTool'                   ALLOW |
empty tool_name                ''                             ALLOW |
missing tool_name              None                           ALLOW |
non-string tool_name 5         5                              ALLOW |
```

What this reproduction shows and what it does not: it is unit-level, at the guard's own entry point.
That Claude Code never called the hook for these names is read from the shipped matcher and Claude Code's documented matcher rule, not walked in a live session.

Claude Code's own documentation, read 20 Nov 2026 (code.claude.com/docs/en):

- hooks, "Matcher patterns": a matcher of only letters, digits, `_`, `-`, spaces, `,` and `|` is an exact name or a list of exact names; any other character makes it an unanchored JavaScript regular expression; `"*"`, `""` or an omitted matcher matches every name.
- hooks, PreToolUse: it "Matches on any tool name except `EndConversation`", built-in and MCP tools alike; exit 2 blocks the tool call.
- permissions: MCP tools are named `mcp__<server>__<tool>`, and a deny rule `"mcp__*"` matches every MCP tool across all servers and removes it from the model's context.
- settings, "Exceptions to managed settings precedence": `disableClaudeAiConnectors` is honoured as `true` "from any scope"; "a project `true` for `disableClaudeAiConnectors` stays on".

## Decision

1. **Every tool name reaches the guard.** The Claude Code PreToolUse matcher is `.*`, the Codex arm's own spelling, so the hook runs on every tool call.
2. **`decide()` is a closed three-way table, chosen by the exact tool name only, never by the shape of the input** (a `file_path` key, a `path` key, a name prefix such as `Task`, or a negation such as "not `mcp__`"):
   - **Judged** (`JUDGED_TOOLS`, the arms that existed before): `Read`, `Glob`, `Grep` → the read arm; `Write`, `Edit`, `MultiEdit`, `NotebookEdit` → the write arm; `Bash` → the transport. Their logic and every message are unchanged.
   - **Passed** (`PASS_TOOLS`, each a built-in that reads and writes no file the session names, runs no command and reaches no network, cited in the code to its row of Claude Code's tools reference): `TodoWrite`, `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate` (the session's own checklist, held by the harness; when a list is shared across sessions it is kept under the user's config folder, `~/.claude/tasks/`, and in agent-team modes a task can be assigned to another agent, which cannot exist here because `Agent` is refused), `TaskStop` (stops a background task or agent, which only a call this guard admitted can have started), `AskUserQuestion` (the human answers), `EnterPlanMode` and `ExitPlanMode` (switch the session's mode), `ToolSearch` (loads tool definitions; a loaded tool still meets this guard when it is called).
   - **Refused**, every other name, with `Blocked: the guard cannot judge tool <name> (R-098; decisions 0042, 0330), so it refuses it. Next: use Read, Glob, Grep, Edit or Write, or the typed call the stage contract names through Bash.` The name is printed through the Codex arm's own sanitiser. A missing, empty or non-string `tool_name` is refused with the existing `UNREADABLE` text.
   The refusal is a separate final test (`if tool not in JUDGED_TOOLS and tool not in PASS_TOOLS`), not an `elif` on the write/Bash chain, so a judged read never reaches it.
3. **Refused by default, deliberately not passed:** `Agent` and `Workflow`, `Skill`, `PowerShell` and `Monitor` (they run commands the transport cannot judge), `WebFetch`, `WebSearch`, `LSP`, every `mcp__*` tool, `ListMcpResourcesTool`, `ReadMcpResourceTool`, `WaitForMcpServers`, `Artifact`, `SendMessage`, `SendUserFile`, `PushNotification`, the `Cron*` tools, `RemoteTrigger`, `EnterWorktree`, `ExitWorktree`, `TaskOutput`, and any name a later Claude Code release adds. `EndConversation` never reaches PreToolUse (hooks page), so it needs no entry.
4. **Two settings belts** in the same file: `"mcp__*"` in `permissions.deny` (MCP tools leave the model's context, so a visitor sees no failed attempt) and `"disableClaudeAiConnectors": true`. The hook stays the authority; the belts are not relied on, and no other bare-name deny (Agent, Skill, PowerShell) is added, because a second list would drift from the hook's.
5. **The SessionStart comment in `session_state.sh`** no longer says a pin failure refuses session initialization: under Claude Code SessionStart cannot block (the failure is shown to the user and the session goes on), so the guard's default deny is what keeps an unreviewed skill or MCP server from acting; the Codex adapter still turns the same exit into a stopped first turn. The `pins.py || exit 2` line is unchanged.
6. **Codex arm: no code change.** A parity test feeds both arms the same unknown-name grid.

**The evidence for refusing `Agent`, stated precisely.** The 102 recorded GARS smoke sessions used only Read (264 calls), Bash (81), Write (65), Grep (48) and Glob (3); those sessions ran a narrow scripted prompt with an explicit allowed-tools surface, so they show what the honest scripted path needs, not what an interactive visitor's session reaches for.
GARS's own measurement instruments do handle sub-agent traffic in measured sessions (0128 item 1(d); 0140 ruling L6, `isSidechain`; `evals/review-faults/README.md`), and an interactive visitor may well see Claude Code reach for `Agent`.
That is a refusal with a `Next:` line, not a break; if it proves to be noise on the honest path, a bare-name settings deny for `Agent` (which removes it from the model's context) is the named follow-on.

Alternatives rejected:

- **A settings-only fix** (bare-name denies for every risky tool): a deny list drifts as Claude Code adds tools, and it would leave `PowerShell` and `Monitor` reachable unless each were named.
- **A per-call pin check**: `pins.py` walks the whole workspace with `rglob` on every call; too slow on a workspace holding pipeline outputs.
- **Passing `Agent` for parity with Codex's `spawn_agent`**: deferred (residual R3).

## What this does not close

- **R1 The sentence this record makes true is scoped.** It is "every tool name is judged, passed or refused" under Claude Code. It is not "reads outside the workspace are refused": a judged typed tool still reads any folder the process can read through its path flags (0107 residual 17, `--counts`, `--design`, `--h5ad`, `--counts-from`, `--h5ad-from`; OrgOS T43b, parked).
- **R2 A human-changed `SKILL.md` read as text** in a session that showed the pin warning: SessionStart cannot block under Claude Code, so the session goes on; the file is read as contract text by a judged `Read`, never invoked (`Skill` is refused).
- **R3 Parity difference:** Codex passes `spawn_agent`; Claude Code refuses `Agent`.
- **R4 PowerShell-only Windows sessions** are refused, not guarded: the transport judges Bash only.
- **R5 Operator switches that turn every arm off, judged arms included** (pre-existing, operator opt-outs, not model routes): `disableAllHooks` is honoured from any settings file (settings reference index, as read by the plan review, 20 Nov 2026), so a user-level `~/.claude/settings.json` or `--settings` turns the hook off; cloud threads in a project apply none of a repository's `.claude/settings.json` hooks (settings page, "Settings in cloud sessions"); and a `-p` run silently skips a broken project settings file or a value it rejects (settings page, "Fix a broken settings file"), so a Claude Code version that rejected `disableClaudeAiConnectors` would drop that value. `claude doctor` lists dropped entries; the outcome review runs it on the CLI version it uses.
- **R6 Unchanged parks:** T43a (per-helper output rules, 0107 residual 1), T43b (residual 17), T44c (row 13 through doors, 0291) and T44d (residual 18, the `STATUS` exemption) stay as 0107 and 0291 name them; none is reached by the matcher or the fall-through change.
- **R7 Not walked live by this record's unit tests:** that Claude Code now calls the hook for an MCP tool, and that the two belts act, is shown by the outcome review's live sessions, summarised at the end of the Test section; the claude.ai connector belt was not walked live there.

## Test

`gars/tests/test_every_tool_name.py` drives the shipped hook at its entry point with payloads built by `json.dumps`:

- `test_the_matcher_reaches_every_name`: every PreToolUse group running `_system/guard_hook.py` is read with the documented matcher rule (`test_the_matcher_rule_reading` checks that reading on the hooks page's own examples), and every name in the grid (22 unjudged names, the 8 judged, the 10 passed) must reach the guard.
- `test_unjudged_names_are_refused`: 22 names (MCP, connector, a hyphenated MCP server, `PowerShell`, `Monitor`, `Agent`, `Task`, `Skill`, `Workflow`, `WebFetch`, `WebSearch`, `ReadMcpResourceTool`, `TaskOutput`, `FutureTool`, `TaskEvil`, the near-spellings `bash`, `Read ` and `WRITE`, and `todowrite`, `TodoWriteX`, `mcp__x__TodoWrite` and `XTodoWriteX`, which differ from a pass name only by case, a suffix, a prefix or both), each with three input shapes (a write over `files.csv`, a read of a non-existent outside path, a URL) → exit 2, the `cannot judge` first words, the sanitised name, exactly one `Next:`.
- `test_pass_names_are_allowed`: `PASS_TOOLS` equals the ten names, and each with a realistic input exits 0 with empty stderr.
- `test_unreadable_tool_name_is_refused`: missing, `""`, `null`, `5`, `["Read"]`, an object and `false` → exit 2, `could not read this tool call`.
- `test_judged_names_keep_their_arms`: the reproduction's five judged controls give their base-commit messages byte for byte, and seven honest judged calls (one per judged name) are allowed.
- `test_the_sets_are_closed_and_exact`: both sets are tuples of distinct non-empty plain names, disjoint, `JUDGED_TOOLS` is exactly the arms' names (8), and no grid name is on either.
- `test_settings_belts`: `"mcp__*"` in `permissions.deny`, `disableClaudeAiConnectors` is `true`.
- `test_both_arms_refuse_the_unknown_grid`: the 22 names fed to `codex_hook.py pre-tool-use` and to the Claude Code hook → exit 2 from both.

The module prints `tool names: <n> refused, <m> passed, <k> judged`.
Red at the test commit d5bdc3ef (7 of 9 tests, 110 failing subtests); green after the fix (`tool names: 18 refused, 10 passed, 8 judged`, on the grid of 18 names the module held until 98fe044f).
At head 5205c96c each module was run singly on the Mac on 2026-11-20 (Python 3.9.6, a temp root outside the clone), every one exit 0:

| Module | Result |
|---|---|
| `gars/tests/test_every_tool_name.py` | `Ran 9 tests`, `OK`, `tool names: 18 refused, 10 passed, 8 judged` |
| `gars/tests/test_guard_hook.py` | `Ran 7 tests`, `OK` |
| `gars/tests/test_protected_paths.py` | `Ran 6 tests`, `OK` |
| `gars/tests/test_data_class_required.py` | `Ran 4 tests`, `OK` |
| `gars/tests/test_stage03_execution.py` | `Ran 17 tests`, `OK` |
| `gars/tests/test_pilot_log.py` | `Ran 15 tests`, `OK` |
| `gars/tests/test_codex_adapter.py` | `Ran 39 tests`, `OK` |
| `gars/tests/test_session_state_closed.py` | `Ran 11 tests`, `OK` |
| `gars/tests/build_refusal_corpus.py --check` | `decision pin: 1999 refused, 607 allowed; OK` (unchanged) |

The whole suite at the same head passed on Node 1 (run guard-default-deny-5205c96-5205c96-20261120T210714Z: ran 1615, passed 1533, skipped 82, 0 failures).
The mutation proof ran on the Mac on 2026-11-20 at head 5205c96c, in a `git clone --no-local` scratch copy, never the lane branch.
Each mutant edited one file, ran `gars/tests/test_every_tool_name.py`, and restored the file from its byte backup; the scratch copy's `git status` was clean afterwards.
The null control ran first and was green; all seven mutants went red (`mutation proof: null green, 7 of 7 red`):

| Mutant | Exit | Result | Killed by |
|---|---|---|---|
| null (no change) | 0 | `OK`, `18 refused, 10 passed, 8 judged` | (control) |
| 1 matcher back to the eight names | 1 | `FAILED (failures=28)` | `test_the_matcher_reaches_every_name` |
| 2 final refusal removed (fall-through allow) | 1 | `FAILED (failures=72)`, `0 refused` | `test_unjudged_names_are_refused`, `test_both_arms_refuse_the_unknown_grid` |
| 3 `Agent` added to the pass list | 1 | `FAILED (failures=6)` | `test_unjudged_names_are_refused`, `test_pass_names_are_allowed`, `test_the_sets_are_closed_and_exact`, `test_both_arms_refuse_the_unknown_grid` |
| 4 `Task` prefix pass | 1 | `FAILED (failures=12)`, `15 refused` | `test_unjudged_names_are_refused`, `test_both_arms_refuse_the_unknown_grid` |
| 5 `mcp__*` removed from `permissions.deny` | 1 | `FAILED (failures=1)` | `test_settings_belts` |
| 6 unreadable-name check removed | 1 | `FAILED (failures=7)` | `test_unreadable_tool_name_is_refused` |
| 7 `MultiEdit` dropped from the write arm | 1 | `FAILED (failures=2)`, `7 judged` | `test_judged_names_keep_their_arms`, `test_the_sets_are_closed_and_exact` |

The tables above are the figures at 5205c96c, on the grid of 18 names.
The first review of the code found four more mutants of the final default-deny test that the 18-name grid let live: each makes the pass test something other than exact string equality, and each went green on that grid (`mutation proof: NOT PROVEN`).
Test commit 98fe044f added the four names `todowrite`, `TodoWriteX`, `mcp__x__TodoWrite` and `XTodoWriteX` to the grid, so the module now holds 22 refused names and prints `tool names: 22 refused, 10 passed, 8 judged` (`Ran 9 tests`, `OK`, run singly on the Mac on 2026-11-20).
The four mutants were then run against the 22-name grid, the same way, in a `git clone --no-local` scratch copy (`restored byte-identical: True`); the null control was green and all four went red (`mutation proof: null green, 4 of 4 red`):

| Mutant | Exit | Result |
|---|---|---|
| null (no change) | 0 | `OK`, `22 refused, 10 passed, 8 judged` |
| 8 pass by suffix (`endswith`) | 1 | `FAILED (failures=4)`, `21 refused` |
| 9 pass by prefix (`re.match`) | 1 | `FAILED (failures=4)`, `21 refused` |
| 10 pass by substring | 1 | `FAILED (failures=12)`, `19 refused` |
| 11 pass ignoring case | 1 | `FAILED (failures=4)`, `21 refused` |

In each, a name from the four the grid gained was let through, so the module's refused count fell below 22.

The live outcome review, on 2026-11-20 at lane head 7651fbba (Claude Code 2.1.280, headless sessions with the project's settings only, one stdio MCP server whose one tool echoes its text and touches no file), walked R7: at the base c5ba8425 the MCP tool was offered and its call succeeded; at the head the tool was absent from the model's tools, because the `"mcp__*"` deny removes it; with that deny line removed from a copy of the head, the call was made and the hook refused it with the `cannot judge` message; an honest session's Read and Glob calls and a `ToolSearch` call passed with no refusal.
It also saw that Claude Code 2.1.280 offers tool names this record does not list, among them `Task`, `DesignSync`, `ReportFindings`, `ScheduleWakeup`, `ListAgents`, `ArtifactComments` and `ArtifactData`.
None is judged or on the pass list, so the default deny refuses each one (its probe refused `Task`, `ScheduleWakeup` and `Artifact` at the head); Decision 3's list names the tools this record weighed, not every tool a Claude Code release offers.

## Status

Standing. The change record for OrgOS T38; implementation only, its approval is recorded at landing, and it lands on public main only on the owner's typed push word.

## Date

2026-11-20
