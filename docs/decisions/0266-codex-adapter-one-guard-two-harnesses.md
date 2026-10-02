---
date: 2026-10-01
status: standing
kind: decision
touches:
  - AGENTS.md
  - gars/AGENTS.md
  - gars/_system/guard_hook.py
  - gars/_system/codex_hook.py
  - gars/_system/tools/pins.py
  - gars/_references/tool_pins.json
  - gars/.codex/hooks.json
  - gars/.codex/config.toml
  - gars/.claude/settings.json
  - gars/tests/test_codex_adapter.py
  - gars/tests/test_refusal_messages.py
  - gars/tests/pilot_fixture.py
  - docs/architecture.md
  - DEVELOPMENT.md
symptoms:
  - a Codex session in gars/ runs with no guard and no state render
  - Codex never reads CLAUDE.md
  - a nested .codex/config.toml or AGENTS.override.md is writable
  - a Write or Read of a ~/ path is judged inside the workspace while Claude Code resolves it under the home directory
---
# One guard, two harnesses: GARS runs under Codex with the same guard decisions

## Context
GARS's stage contracts are plain files with no harness in them.
What was Claude-only is the entry file a fresh agent reads, and the wiring of the PreToolUse guard (`gars/_system/guard_hook.py`) and of the SessionStart state render (`gars/_system/session_state.sh`), which only Claude Code loads, through `gars/.claude/settings.json`.
So a Codex session in `gars/` ran with no guard and no state render, as decision 0042's "Guard scope" line says: "A session at the repository root, or another harness, runs unguarded".
Codex reads `AGENTS.md` files from the git root down to its working folder, never `CLAUDE.md`, so it never learned the binding rule in `gars/CLAUDE.md`.
Codex also reads files Claude Code does not: a `.codex/` layer at every level from the git root down (the closest one wins, including `[features] hooks = false`), and `AGENTS.override.md`, which replaces `AGENTS.md` in its folder; none of them was protected.
Spec R-161 says the three project-local mechanisms run "under one harness's hook format"; supporting a second harness changes that rule, so it needs this record.

The owner, typed in the glitch-25 window on 1 Oct 2026 (the message arrived before 19:23 EDT; that is the planning clock read, not his typing time): `1 yes · 2 codex · 3 before freeze`.
It answered these three calls, quoted unelided from the message he was replying to:

> 1. **A spec change.** R-161 says GARS runs "under one harness's hook format". Supporting several platforms changes that, so it needs a decision record and your yes. I recommend **yes**, recorded as decision `0xxx` (number assigned when written).
> 2. **Which platforms.** I recommend **Codex only for now**, since it's installed and testable. Gemini later.
> 3. **The freeze.** New features stop **Tue 6 Oct**, and portability isn't one of the three exceptions. Steps 1–2 plus the Codex proof fit by Monday if we start tomorrow. Otherwise it waits until after 16 Oct. I recommend **doing it before the freeze**. "Works with any agent, here's the test" is exactly the kind of thing a hiring scientist can check in minutes. But it's competing with Friday's HHMI and OpenRefinery applications, so those go first tomorrow morning.

Built on branch `gars-codex-port` from public main `c9fe683` in a `--no-local` lane clone with no remote, red first.
This record is written in the build lane.
The lane's in-spec calls are the lane executor's, and the coordinator's rulings (Row-orchestrator glitch-4a, under the owner's 23 September 2026 delegation) are the coordinator's; each is labelled, and none of them is the owner's.

## Decision

1. **R-161 is read as one decision core under each supported harness's hook format.** The core is `guard_hook.decide(payload, root=None)`: `main()`'s decision with every check, its order and every message as at `c9fe683`. Claude Code runs `guard_hook.py` as before; Codex calls `decide` through `_system/codex_hook.py`, with the root fixed to that file's own `gars/` folder. Supported today: Claude Code, and Codex 0.154 (verified); 0.144 source-checked for the same hook, `updatedInput` and parser semantics (review r1b, against the rust-v0.144.0 source); earlier releases untested.

2. **The envelope mapping.** Codex's PreToolUse sends `{tool_name, tool_input, cwd, …}`; the adapter maps each call to the guard's own shape and holds no protected-path list and no shell rule of its own:

   | Codex call | Judged as |
   |---|---|
   | `Bash` (`exec_command`, `shell`) | the guard's Bash rule on the same command, from the payload `cwd`; on allow, the call is rewritten (`updatedInput`) to `cd -- <that cwd> && <command>`, because Codex runs a command in a `workdir` it never tells the hook; our own prefix coming back is judged on its remainder, and a prefix naming any other folder is judged as written |
   | `Bash` containing the word `apply_patch` or `applypatch` | the guard's Bash rule, unchanged (it refuses it, as it refuses the same command from Claude Code); the refusal's one `Next:` names the `apply_patch` tool |
   | `apply_patch` Add File | `Write` of the path, with the added lines |
   | `apply_patch` Update File | `Edit` of the path, removed lines as `old_string`, added as `new_string` |
   | `apply_patch` Delete File | `Write` of the path with empty content (Claude Code cannot delete through the guard either: `rm` is not a registered call); refused when the path is a symbolic link |
   | `apply_patch` Update with Move to | `Edit` of the source and `Write` of the destination; refused if either is, or if the source is a symbolic link |
   | `apply_patch` that the guard cannot judge | refused: an `*** Environment ID:` line (another filesystem), an empty patch, a missing Begin or End marker, an unknown header, any line separator other than `\n`, a control character or a scheme prefix in a path, a Move with no change |
   | `view_image` | `Read` of its path; refused when it names an `environment_id` |
   | `update_plan`, `request_user_input`, `spawn_agent`, the four `multi_agent_v1…` tools, `send_message`, `followup_task`, `interrupt_agent`, `list_agents`, `wait_agent` | allowed: they touch no file, and a sub-agent's own calls run PreToolUse in its own session; each is cited to the Codex source in `codex_hook.py` |
   | everything else, `mcp__*` included | refused: the guard cannot judge it (R-098) |

   Every exit is 0 or 2 with text: the adapter catches `BaseException` and refuses, because under Codex an empty stderr, a crash, any other exit code or a timeout lets the call through. The import of the guard sits inside that net: a guard that fails to import refuses every call, and stops the first turn at session start. A call the adapter cannot read gets the guard's own `UNREADABLE` text, so a malformed envelope is refused with the same first line under both harnesses.

   A symbolic link at a Delete File or a Move's source is refused because the guard judges every path by the file it resolves to, while those two entries act on the link itself; judged by its target, a link at a machine-owned place pointing at a free file would pass (review r1, R1-4; the lane executor's form of the coordinator's ruling, which asked for the unresolved path to be judged as well: the guard resolves every path, so the adapter refuses the link instead, which covers every case that ruling refuses and also a free link, which Claude Code cannot delete at all).

   An `allow` with `updatedInput` does not bypass Codex's own approval: Codex maps it to "continue with the rewritten input" and dispatches the call through its normal handler path, approvals included (`core/src/tools/registry.rs` at rust-v0.154.0, lines 592-618: `PreToolUseHookResult::Continue { updated_input: Some(…) }` replaces the invocation; review r1b's source read).

3. **Wiring.** `gars/.codex/hooks.json` arms PreToolUse and SessionStart (matcher `.*`, no `async`, no `timeout`). Its launcher walks up from the session folder to the git root as Codex itself finds it (a `.git` file, or a `.git` folder holding `HEAD`) and runs `<root>/gars/_system/codex_hook.py`, so a planted look-alike in a project folder is never reached; Codex's hook trust covers the command, not the script it runs. SessionStart runs `session_state.sh` and passes its output through; a pin failure (its exit 2) becomes `{"continue": false, "stopReason": …}`. `gars/.codex/config.toml` sets `web_search = "disabled"`, the counterpart of Claude Code's `WebSearch`/`WebFetch` deny; Codex honours that key in a project layer. There is no Windows hook command: GARS does not run on Windows (bash helpers, Nextflow on HPC).

4. **The protected set grows to cover what Codex reads** (READ_ONLY, mirrored in `.claude/settings.json`; `.codex/` is protected like `.claude/`, R-094 by analogy):
   - `.codex/*`, `.codex/**/*`, `*/.codex/*`: every Codex layer below the git root loads under the root's trust with no review, and a nested one could switch the hooks off;
   - `AGENTS.override.md`, `*/AGENTS.override.md`: it replaces `AGENTS.md`, so it could replace the front door;
   - `.git`, `.git/*`, `*/.git`, `*/.git/*`: a planted git folder moves the root Codex walks from, and its hooks would run on a human's git commands (the root-level pair is the lane executor's addition to the plan's list);
   - `.agents/*`, `.agents/**/*`, `*/.agents/*`: Codex loads repository skills from `.agents/skills/` into the session's context at start (review r1b, F1); no GARS stage or tool writes there (searched in the repository);
   - `repo:.codex/*`, `repo:AGENTS.override.md`, `repo:.agents/*`: the repository-level layers; the root allow-list already refuses these, and the entries keep the settings mirror complete.

   `PROTECTED_PREFIXES` gains `.codex/`. `pins.py` inventories every file under any `.codex` folder, and `tool_pins.json` pins the two shipped files by sha256, so a changed or extra layer refuses the session (R-099).

5. **A pre-existing hole on public main, write and read, is closed here.** Claude Code resolves a tool path that starts with `~/` (or is exactly `~`) under the home directory, while the guard joined it to the session folder and judged it inside the workspace, so a `Write` of `~/.codex/config.toml` and a `Read`, `Glob` or `Grep` of a `~/` path were allowed whenever no closed project existed. The guard now expands exactly those two spellings before its existing inside-the-root checks, so the root allow-list refuses them with its existing messages; no home path is enumerated (the lane executor's call; the coordinator's ruling of 1 Oct required a write to a home `.codex/config.toml` to be closed through the root allow-list, and the read side shares the cause).

6. **R-099 per harness, exactly.** Under Claude Code, a SessionStart exit 2 is shown, not enforced. Under Codex, `continue: false` stops the first turn only, and is lost if login-profile text reaches the hook's stdout before it. The `.codex` files are pinned, so a changed one fails the pins check at every session start.

7. **The front door is `AGENTS.md`.** `gars/AGENTS.md` keeps its ten R-160 headings and gains the binding rule, a pointer to `CLAUDE.md` and the signal that no state render means no guard; a new tracked root `AGENTS.md` points developers at `CLAUDE.md`. Both `CLAUDE.md` files stay byte-identical, because the Gap Study pre-registrations pin the root one and `contract_quotes.json` binds the workspace one. The proposal the owner saw moved `gars/CLAUDE.md`'s body into a neutral `WORKSPACE.md`; not doing so is the lane executor's call, for the reason just given.

8. **0042 stays standing.** Its "Guard scope" limitation is narrowed for Codex sessions started in `gars/` with trusted hooks; the rest of 0042 holds.

The lane executor's other in-plan calls: the launcher's `HEAD` rule above; the shell-wrapped `apply_patch` refusal carries exactly one `Next:` (decision 0175); the adapter refuses a payload `cwd` that is not absolute, and a `view_image` with an `environment_id`; and the pilot fixture copies `.codex` as the shipped workspace does, because its pins now name it.

## What this does not close
1. The workdir pin works only when the hook's JSON reaches Codex intact; if login-profile text reaches stdout first, Codex runs the original command in its `workdir`, and relative paths in it were judged against the session folder. Measured on the build Mac: `$SHELL -lc 'true'` writes 0 bytes to stdout. Codex does not fire PreToolUse again on the rewritten call (Codex source, `core_registry.rs`).
2. `write_stdin` never reaches PreToolUse, so input typed into a command that is already running is not checked. The guard's Bash transport admits registered typed calls and read-only filesystem commands; none of them is an interactive reader of stdin.
3. exec_command's `shell` parameter is not sent to the hook, so a shell the model chooses interprets a command the guard judged as POSIX shell. No project-layer key turns the parameter off in Codex 0.154.
4. exec_command's `environment_id` is not sent to the hook either, so in a multi-environment session a command runs against a filesystem the guard did not judge.
5. Codex fails open on a hook crash, a timeout or a host kill, as Claude Code does. The adapter never crashes by its own hand (every path exits 0 or 2 with text).
6. The hooks load only after the folder is trusted and both are approved under `/hooks`, and under `codex exec` only when already trusted. `AGENTS.md`'s "no render, stop and ask" line is the signal, and it is one-sided: the two hooks are approved separately, so a session with the SessionStart hook approved and the PreToolUse hook not approved shows the state render with no guard. A render proves only the session-start hook; `gars/AGENTS.md` and the README say to approve both.
7. A session at the repository root, or another agent, runs unguarded.
8. User-level Codex configuration (`~/.codex/config.toml`: MCP servers, `[features]`, user hooks) is outside R-099, as Claude Code's user-level configuration is. CP0 measured a guarded write to it: refused when spelled as an absolute path, allowed when spelled `~/.codex/config.toml` until item 5 of the Decision closed it.
9. Nested `AGENTS.md` files are not protected; they are prose, like nested `CLAUDE.md` files under Claude Code. `.agents/` is protected (item 4 of the Decision), and only its `SKILL.md` files are pinned.
10. The tool list was verified for Codex 0.154 only; a later release may rename tools or change the envelope, and a renamed tool is refused until listed.
11. 0042's known passes apply unchanged under both harnesses.
12. Recorded and not changed here: the pins check's refusal carries no `Next:` sentence (it becomes Codex's `stopReason` as it is); and a `Glob` pattern, as distinct from its `path`, is not checked against the root while no closed project exists.
13. Tool paths without a function-call payload never reach PreToolUse in Codex 0.154: the code-mode `exec` cell and its `wait`, `tool_search`, and freeform extension tools. Code mode is off by default, and turning it on takes a user-level layer (item 8) or a protected project layer; the tool calls it makes go through normal dispatch and are hooked (review r1b, N2).
14. A `~/` path in an `apply_patch` entry is judged as the home directory, while Codex would write it literally under the session folder; that divergence only over-refuses (review r1b, N3).

## Test
- `gars/tests/test_codex_adapter.py`, red first: at `c9fe683`'s code (with the front door), `Ran 35 tests`, `FAILED (failures=57, errors=234)`; at `31d95d0`, every group but the parity replay `Ran 34 tests`, `OK`.
- The parity replay (group 2) derives Claude Code's verdict live (`judge()`, which runs `guard_hook.main`) and the Codex envelope's over the same fixture rows: for Bash, Write and Edit (2568 rows) through `codex_hook.run`, and for the 5 malformed rows through `codex_hook.main` on a Codex envelope with the same defect. Every graded row compares the exit and the first stderr line byte for byte; allowed Bash rows also compare the folder-pin rewrite. The count line: `graded 2573 / seen 2606: Bash 2520, Write 32, Edit 16, malformed 5; not Codex tools: Read 17, Grep 8, Glob 5, MultiEdit 2, NotebookEdit 1`.
- The mutation proof at `31d95d0`, in a disposable copy: 14 mutants (apply_patch allows all; only the first entry checked; a Move's destination unchecked; the root from the working folder; a crash exits 1; a refusal with empty stderr; an unknown tool allowed; a pins failure passed through as exit 2; READ_ONLY without `*/.codex/*`; the launcher taking the first adapter above the working folder; the rewrite prefix dropped; another folder's prefix stripped before judging; a `KeyboardInterrupt` escaping; an `Environment ID` ignored), all 14 killed, each by a named test.
- The tilde hole, red first through `guard_hook.main` with json-built envelopes and a temporary home: before, `Write ~/.codex/config.toml`, `Read ~/x.txt`, `Glob` and `Grep` of `~` exit 0; after, exit 2 with the root allow-list and R-073 messages; group 11 holds it under both harnesses.
- `test_refusal_messages.py`'s static scan covers `codex_hook.py`; a refusal with no `Next:` planted in a temporary copy turns it red.
- Unchanged for Claude Code: `build_refusal_corpus.py --check` prints `decision pin: 1995 refused, 611 allowed; OK` before and after.
- The whole suite at `a4b3efc` on the lab's Linux test host: `ran 1282, passed 1200, failures 0, errors 0, skipped 82`. `tests/check_counts.py` 1282 clean, `tests/check_contracts.py` 14 clean, `evals/gap-study/check_results.py` clean.
- Review round 1 (two independent fresh-context reviews of `d001f48`, both CHANGES; one with 2 MAJOR: the version floor and the malformed-row parity statement), answered on the branch, each code change red first: the malformed rows' first lines differed ("read this Codex tool call" against "read this tool call") at `d001f48` and are equal now, bound in group 2; a broken `guard_hook.py` made the adapter exit 1 (fail-open under Codex) and now refuses (group 7, `test_guard_import_failure_refuses`, 4 subtests red then green); a Delete or Move source on a link at `projects/p/02_bioinformatics/r/run/out.txt` pointing at a free file was allowed and is refused (group 3, 3 subtests red then green); `.agents/` writes were allowed under both harnesses and are refused (group 11, 36 subtests red then green). Mutants of each new check (the import refusal skipped, the link check skipped, `.agents` dropped from READ_ONLY) are each killed by those tests.
- **The live Codex session: pending: Javier's CP3 run.** The hook events at session start and on each shell command, the state render in the session's context, the folder pin on executed commands and the tool names used are recorded in a dated follow-up once the session id is handed back.

## Status
Standing. Built and tested on the branch; the protected-change approval is decision 0267, whose owner slot is empty until the owner types his yes.

## Date
2026-10-01
