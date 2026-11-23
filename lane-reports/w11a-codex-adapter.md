Status: built, red first then green; awaiting the fresh opus-medium review round (construction; threat model "every guard red by assertion when removed; nothing undocumented is accepted").
head: 6a410c07 (code). Base f14ab57b (wave 9, athena PASS), branch gap4/w11a-codex-adapter, worktree /Users/javrodher/aegis-builds/gap4-w11a.

# Lane w11a-codex-adapter: Gap Study round 4, arm O's adapter on documented shapes

_Written Mon 12 Oct 2026 15:36 EDT (`date`) by the slice's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-2f under Javier's standing delegation. Spec: plans/gap-study-round-4/next-slices-plan-2026-10-12.md section 2 ("w11a-codex-adapter") and its shared hard rules; D8-non-claude-arms.md lines 95-185 and 445-501; ruling Q-3 (glitch-2f): build on the documented Codex event shapes now._

No image or container was built or run.
No model was run, no API was called, no Codex was launched, and no test used a network.
No login, `.env`, credential, sealed, holdout, brief or saved-output path was read.
Nothing was pushed, merged or mirrored.
The files drive.py, walk_runner.py, check_take.py, run.py, walk_register.py, mode_binding.py, transcript_view.py, agent_adapter.py, harness_bookkeeping.py, routing.json, routing.py, batch.py, build_draft.py, prereg-draft.json, box/* and graders/* were not edited.

## Commits

| sha | stage |
|---|---|
| 6aaf9a8e | 1: the tests, the synthetic fixtures and their labels, the copy-record fragment, the local checks (red on the base) |
| 6a410c07 | 2: codex_adapter.py and transcript_codex.py (green) |
| (this file) | 3: the lane report |

## What each piece does, with its test

- `transcript_codex.py` (new). The pre-registered tables of a `codex exec --json` stream, kept in two grades.
  From D8 section 1: the seven event types, the five item types and the four usage keys.
  Not in D8 (this lane's reading of Codex's exec event schema, unverified here because the lane has no network; Q-w11a-1): thread.started.thread_id, turn.failed.error.message, error.message, each item's id and type and per-type keys, file_change's changes of {path, kind}, which item types an item.started may carry.
  `check_record` refuses any event type, item type or key off the tables (`ShapeError`), never reads it on a guess.
  `CodexParser` maps one line into `transcript_view.RawItem`s in the view's closed vocabulary: agent_message to agent-text, reasoning to agent-reasoning, command_execution to a shell call (item.started) and its result (item.completed), file_change to one write (add) or edit (update) call and result per change, mcp_tool_call to other.
  It is NOT registered in `transcript_view.PARSERS`; the tests put it in a copy of the table for the test only and check the real table is unchanged.
  Tests S1-S3, P1.
- `codex_adapter.py` (new). `CodexAdapter(AgentAdapter)`, name "codex" (run_take.CODEX).
  One `codex exec --json -m <model> <mode flags> [resume <thread id>] <line>` per turn through run_take.run_turn (D8:107-112).
  `-m` on every exec; `resume` after turn 1 only, with the thread id read from turn 1's thread.started (Codex mints it); a later turn whose stream names another thread is refused.
  The routing pin's permission mode is looked up in `MODE_FLAGS` ("bypass" to `--dangerously-bypass-approvals-and-sandbox`, D8:110); a PENDING, absent or unknown mode refuses the adapter's making.
  A line that starts with "-" is refused (it would be read as a flag).
  `read_stream`: api_errors from error events and turn.failed only, each {status None, type the event type, text the harness's own message}; the agent's text is never one.
  agent_output from item.completed of agent_message (non-blank), command_execution, file_change or mcp_tool_call; reasoning alone is not output.
  usage from turn.completed.usage: a missing key or a key with no entry is refused, never 0; a turn with no turn.completed has usage None (unmeasured).
  `read_rollout`: the init {model, permission_mode, version} from the turn_context records the rollout gained during the turn (model, approval_policy) and the session_meta's cli_version; none gained, or a field not a string, is init None with its reason in the turn record; never the requested model (exec JSON carries no model, D8:168).
  end_reason: timed-out; end_turn only on exit 0 with one turn.completed and no turn.failed; error otherwise.
  `SHAPES_SOURCE = "documented"`, reported by `harness_record()` and in every turn record; A7 holds it at "documented" while no fixture in tests/fixtures/codex-streams/ is labelled RECORDED.
  Tests A1-A7 and two plain tests (a version off its form refuses; the adapter's name is run_take.CODEX).
- `tests/fixtures/codex-streams/` (new): 15 SYNTHETIC JSON Lines fixtures (12 streams, 3 rollouts) and a README that labels each one "SYNTHETIC, from D8 section 1 documentation, not a recorded stream."; its header says the rollout shapes and the keys named "NOT in D8" are this lane's reading. A7 fails on an unlabelled file.

## Red first

Stage 1 (6aaf9a8e) was run with codex_adapter.py and transcript_codex.py absent from the tree, the tests and fixtures present:
`timeout -s INT 120 /usr/local/bin/python3.13 -B -W ignore evals/gap-study-4/tests/test_codex_adapter.py` exited 1: "Ran 28 tests", "FAILED (failures=28)", 0 errors.
Each bound check failed by its own line ("<file> has no <names>"); each witness test failed by its first assertion (the bound check is not green on the absent module); the registry test failed by "does not exist".

## Green

On 6a410c07, the same command exited 0: "Ran 28 tests", "OK".
`... test_codex_adapter.py --witnesses` exited 0: "Ran 14 tests", "OK", the summary line, which counts 13 witnesses red in a registry of 13.

## Witnesses (each a whole-file edit compiled in memory, red by its own bound check, 0 errors)

| witness | file | edit | bound check |
|---|---|---|---|
| unknown-event-accepted | transcript_codex.py | the unknown-event refusal dropped | S1-event |
| unknown-item-accepted | transcript_codex.py | the unknown-item refusal dropped | S2-item |
| unknown-key-accepted | transcript_codex.py | the key closure emptied | S3-key |
| reasoning-as-text | transcript_codex.py | reasoning mapped to agent-text | P1-view |
| delete-as-write | transcript_codex.py | a delete change accepted as write | P1-view |
| agent-text-as-error | codex_adapter.py | an agent_message also read as an API error | A2-error |
| usage-zero | codex_adapter.py | a missing usage key read as 0 | A3-usage |
| resume-first | codex_adapter.py | resume on every turn, the first included | A4-argv |
| model-first-only | codex_adapter.py | -m on the first exec only | A4-argv |
| model-defaulted | codex_adapter.py | a missing init filled with the requested model | A5-model |
| failed-as-end-turn | codex_adapter.py | exit 0 read as end_turn whatever the stream says | A6-turn |
| other-thread-resumed | codex_adapter.py | a later turn naming another thread accepted | A6-turn |
| shapes-recorded | codex_adapter.py | SHAPES_SOURCE set to "recorded" | A7-source |

The brief's minimum set is covered: an unknown event refused (unknown-event-accepted), an unknown item type refused (unknown-item-accepted), the agent's text never an api_error (agent-text-as-error), the model from the rollout and never defaulted (model-defaulted), resume after turn 1 only (resume-first), -m on every exec (model-first-only), a missing usage field refused, never zero (usage-zero), SHAPES_SOURCE not "recorded" while no recorded fixture exists (shapes-recorded).

## Checks run on the Mac (each behind `mac_slot.py light-ok`, `timeout -s INT 120`, python3.13, one process)

- Gates on the head: copy_manifest.py --check 0, build_draft.py --check 0, freeze.py --check 0, walk_register.py --check 0.
- lint_language.py evals/gap-study-4/: "clean — 93 input(s) scanned, 23 excused line(s) on record" (no allowlist edited); lint_pooling.py evals/gap-study-4/: "clean — 93 file(s) and 0 commit(s) scanned".
- Neighbours that sweep the tree or read the seam: test_transcript_view.py OK (20), test_agent_adapter.py OK (35), test_harness_bookkeeping.py OK (14), test_cp8_prep.py OK (4), test_walk_layout.py OK (14, 118.9 s), test_pause_adherence.py OK (30).
- test_walk_wiring.py was stopped by its 120 s timeout on the loaded Mac (load near 16) before it finished: no verdict here; it goes to athena.

## Ruling Q-3 and the freeze

The freeze-side refusal is OWED, not built: freeze.py is outside this lane's closed file list.
What is owed: `freeze.py --check` (or the freeze itself) refuses any arm whose adapter's `SHAPES_SOURCE` is not "recorded", where "recorded" is reachable only when tests/fixtures/codex-streams/ holds a fixture labelled RECORDED with the walk and harness version it was captured at (A7 already refuses "recorded" without one).
Proposed home: the seam slice that registers both adapters, or a one-file freeze slice after it.

## Carried (not in scope here)

- Registration in transcript_view.PARSERS, harness_bookkeeping.TABLE and agent_adapter's tables; drive.py's adapter admission (A1); check_take readers and mode_binding expectations for codex; routing markers and OpenAI's spend-cap codes; per-call cost (price_table PENDING); the real-box stub `codex`.
- run_take.VENDOR_BILLING_ROUTE_VARIABLES[CODEX] stays PENDING, so every real Codex exec refuses (NotReady) until named; the tests fill it with an empty tuple for the fake only.
- take_config's CODEX_REASONING_EFFORT stays PENDING.
- The driver's side of `rollout_for(n)`: copying the rollout from the config folder after each turn (Q-w11a-8).

## Questions, each with a proposed answer

- Q-w11a-1: the shapes not in D8 (each item's keys, thread.started.thread_id, the error messages' keys, the rollout's session_meta and turn_context records, the `codex-cli X.Y.Z` version form). Proposed: glitch-2f adds them to the docs read of plan item 2 (Codex's non-interactive page at the version to be pinned) before the first arm O walk; the first recorded stream re-tests them; any difference is a fold slice before the freeze, citing the recording.
- Q-w11a-2: the Codex stream carries no operator line, so a view of the streams alone numbers every event turn 0 and `require_operator_lines` cannot bind a Codex take. Proposed: the seam slice builds a Codex take's transcript as the per-turn streams in order, each preceded by one host-written operator record holding the ledger's sent line, pre-registered in CodexParser as a host record type (never Codex's).
- Q-w11a-3: a file_change with kind "delete" is refused (the view has no delete kind). Proposed: the seam slice maps delete to write {path} (a delete changes that path), with a test; until then a real delete stops the view, by design.
- Q-w11a-4: the routing pin's word for arm O's mode is this lane's ("bypass"). Proposed: the mode_binding/routing seam slice adopts "bypass" and expects the rollout's approval_policy "never" on every turn (the init's permission_mode).
- Q-w11a-5: whether exec's options are read before `resume` at the pinned version, and whether a resumed exec writes thread.started. Proposed: confirmed at the bring-up walk; the argv order changes only in a fold slice with a test.
- Q-w11a-6: api_errors carry status None (the documented error events carry only a message). Proposed: routing matches per-vendor text markers on `text` (the routing slice, with OpenAI's codes); the adapter never parses a status from the words.
- Q-w11a-7: item.updated and the item types web_search, todo_list and error are refused because D8 does not name them. Proposed: keep refused (config.toml disables web search); if the first recorded stream carries todo_list or item.updated, a fold adds them as harness events, citing the recording.
- Q-w11a-8: `rollout_for(n)` needs the rollout copied out host-side after each turn. Proposed: the driver half of the seam slice copies `$CODEX_HOME/sessions/**/rollout-*.jsonl` (one file per take, else refused) after each turn, as drive.py does for Claude Code's session file.

No decision is left OPEN; each question above carries its proposed answer.

## Counts

- 28 tests in tests/test_codex_adapter.py: red 28 failures and 0 errors on the base; green 28 passed.
- 13 witnesses, 13 red by their own bound check, 0 errors.
- 15 synthetic fixtures plus their README; 0 recorded.
- New files: codex_adapter.py, transcript_codex.py, tests/test_codex_adapter.py, tests/fixtures/codex-streams/ (16 files), COPIED.d/w11a-codex-adapter.json, checks.d/w11a-codex-adapter.txt, this report.

RESUME HERE: review round 1 (fresh opus-medium, construction) on 6a410c07; then athena --solo on the head running the list below; then merge after the wave 10 merge (conflicts expected in derived bookkeeping only).

## Modules athena must run

- tests/test_codex_adapter.py, and tests/test_codex_adapter.py --witnesses
- tests/test_agent_adapter.py
- tests/test_transcript_view.py
- tests/test_walk_wiring.py (timed out on the loaded Mac; no verdict here)
- tests/test_scaffold.py (whole)
- test_round4.py
- the gates: copy_manifest.py --check, build_draft.py --check, freeze.py --check, walk_register.py --check; lint_language.py evals/gap-study-4/ and lint_pooling.py evals/gap-study-4/

---

# Review round 1 fold (ruling w11a-R1-fold, glitch-2f)

_Appended Mon 12 Oct 2026 16:08 EDT (`date`) by the slice's builder. Review: lane-reports/w11a-codex-adapter-review-r1.md (bf52ad2d), CHANGES, 4 MAJOR and 6 MINOR. This section supersedes the Status line, the RESUME HERE line and the athena list above; nothing above is rewritten._

Status: review round 1 folded, red first then green; awaiting review round 2.
head: f61fd4af.

## Commits

| sha | stage |
|---|---|
| 65e38285 | 4: one bound check per finding, each case changing one thing (red) |
| 32de8b98 | 5: the fold code for stage 4 (green for it), the generated mutation sweep, B9, B11 and cases for the sweep's first survivors (red on this commit's code) |
| f61fd4af | 6: the fold code for stage 5 (green); the sweep at 0 survivors |
| (this append) | 7: the report |

## Red first

- Stage 4 on 3cd99ebb's code: 39 tests, 4 failures by assertion, 0 errors; 37 red lines (kept in the untracked `.scratch/red-r1-fold.txt`): the record check typed no value (agent_message text 5, reasoning text 5, command 5, exit_code "0" or true, error message 5, turn.failed message 5, status 5, server 5), did not check a file_change's changes (empty, not a list, an entry not an object, a path of 5, an entry without kind), read_stream raised AttributeError on a text of 5, and read_stream accepted a line that is not JSON as the first line, a middle line and the second of two last lines.
- Stage 5 on its own code: 6 red lines, each by assertion: an event or item type that is a list raised TypeError, not a typed refusal, in the record check, the parser and read_stream (`.scratch/red-r1-fold-2.txt`).
- The other new cases bind code that already refused (the review's point: the guards were right and unbound).

## Each finding, folded

| finding | bound by |
|---|---|
| W11A-R1-1 end_reason's three conditions, the turn.failed count | B1-end: a non-zero exit with a clean stream, exit 0 with no turn.completed, exit 0 with a turn.failed, no exit code, the clean case, a timed-out exec; a stream with turn.failed and turn.completed counts both and ends error through the adapter |
| W11A-R1-2 the thread id at three seats | B2-thread: read_stream refuses "--last", "", "a b", 5; argv refuses a later turn's id of None, "--last", "", 5; turn 1 with no thread.started and turn 1 with two thread ids each refuse turn 2 before its exec; turn 1 naming "--last" is refused with no resume exec; one thread named twice still resumes; a later turn whose stream names no thread is accepted (Q-w11a-5) |
| W11A-R1-3 the missing-key check | B3-required (record check) and B3-stream (read_stream): 14 records, each dropping one required key |
| W11A-R1-4 the rollout init | B4-rollout: two models in one turn refused; no or non-string or empty approval_policy or model, no or two session_metas, a session_meta without cli_version or not an object, each init None with its reason; the last of one turn's turn_contexts is the one read; blank lines skipped; a line that is not JSON or not an object refused |
| W11A-R1-5 usage values, two turn.completed | B5-usage: output_tokens true, -5, a float, "3", None each refused; 0 read as 0; two turn.completed refused |
| W11A-R1-6 empty model and line | B6-empty: argv with model "", None, 5 and line "", None, 5; the adapter's making with model "", None, 5; each callable that is not one; a pin that is not an object |
| W11A-R1-7 a blank agent_message | B7-blank: "", "   " and a newline-tab message are not output; each output item type alone is; a started, never completed call is not; texts join without the empty one |
| W11A-R1-8 value types; text 5 | B8-types (record check and parser) and B3-stream (read_stream): 27 values off their type, each a typed refusal; `text: 5` is now a StreamError |
| W11A-R1-9 A7 and the report line | A7 counts a fixture as recorded only when its label reads "RECORDED at walk <id>, codex-cli <X.Y.Z>."; a RECORDED word without both is a problem line; test_a7_a_recorded_label_needs_its_provenance drives both shapes |
| W11A-R1-10 undecoded lines | B10-cut: a line that is not JSON is accepted only as the last non-blank line (undecoded 1); as the first line, a middle line or the second of two last lines it refuses; B9 a cut last line holding an undecodable byte |

Correction to the section "Ruling Q-3 and the freeze" above: the parenthesis "(A7 already refuses "recorded" without one)" overclaimed at 3cd99ebb, where A7 counted any RECORDED word.
From f61fd4af it holds: A7 refuses "recorded" unless a fixture's label names the walk and the harness version.

## The generated mutation sweep (ruling item 2)

`tests/test_codex_adapter.py --generated-mutants [--shard i/n]`, self-contained in the test file, built from the reviewer's harness.
Kinds: a statement replaced by `pass`; an if, elif, while or conditional test forced True and False; one operand of an and/or dropped; a `not` dropped; one comparison negated; an assignment's value emptied to None; a string literal changed.
A transcript_codex mutant also rebuilds codex_adapter on it.
A mutant is killed when it does not build or any bound check of its file returns a line.
One rule instead of entries: string literals inside a `raise` are not mutated (message words; every refusal is told apart by its exception type).
Everything else not killed is in `EQUIVALENT` with a reason: 36 entries (14 the import preamble in the two files, 10 what-labels passed to `_keys`/`_types`, 4 labels in the callable check's TypeError, 2 in argv's StreamError, 2 why_no_init reason words, the change ref's `#` joiner, 2 attributes whose starting value is already None, and `_contexts = 0`, read only as a slice start).
An entry that names no generated mutant fails, in the sweep and in the plain suite (TestGeneratedMutantRegistry); an entry whose mutant is killed fails in the sweep.
Result on f61fd4af (four shards on the Mac): 867 mutants (the review counted 789 under a wider set of kinds), 831 killed, 36 equivalent, 0 survivors, 0 stale.
Of the 831: 581 killed by a bound check's own line, 220 by a crash inside a check (an ERROR line, for example a deleted assignment leaving a name unbound), 30 at build.
The reviewer's `.scratch/repro.py` no longer runs to its end on the fold (its text anchors name the old code, and its `suite` calls only the checks S1-S3, P1, A1-A7); the sweep runs every check, B1-B11 included.

## Checks on f61fd4af (Mac, each behind `light-ok`, `timeout -s INT 120`, python3.13)

- tests/test_codex_adapter.py: 42 tests, OK. --witnesses: the summary line counts 13 witnesses red in a registry of 13. --generated-mutants in four shards: each exit 0, as above.
- Gates: copy_manifest, build_draft, freeze and walk_register --check, each exit 0. lint_language and lint_pooling on evals/gap-study-4/: clean.
- test_transcript_view.py OK (20), test_agent_adapter.py OK (35), test_harness_bookkeeping.py OK (14).

## For the seam slice (ruling item 3)

- Compare `CodexAdapter.version()` (`codex --version` in the take container) with the pin's `version`, and with the init's version (the rollout's cli_version), on every take; today nothing calls version() from a turn and nothing compares the three.
- Compare the init's permission_mode (the rollout's approval_policy, "never" under the bypass flag) with the pin's mode ("bypass") through a pre-registered map, on every turn (Q-w11a-4).

## Questions added

- Q-w11a-9: should a mutant killed only by a crash inside a check (220 of 831) be required to die by a bound check's own line instead? Proposed: no for this round; a crash is a check that did not return clean, it prints as an ERROR line, and the sweep counts it separately so a reviewer can see the split; turning crash kills into own-line kills case by case is a later tightening, not a merge gate.

RESUME HERE: review round 2 (fresh opus-medium, construction) on f61fd4af, re-running the generated sweep; then athena --solo on the head with the list below; then merge after the wave 10 merge.

## Modules athena must run (supersedes the list above)

- tests/test_codex_adapter.py; tests/test_codex_adapter.py --witnesses; tests/test_codex_adapter.py --generated-mutants (whole)
- tests/test_agent_adapter.py
- tests/test_transcript_view.py
- tests/test_walk_wiring.py (timed out on the loaded Mac at 3cd99ebb; no verdict here)
- tests/test_scaffold.py (whole)
- test_round4.py
- the gates: copy_manifest.py --check, build_draft.py --check, freeze.py --check, walk_register.py --check; lint_language.py evals/gap-study-4/ and lint_pooling.py evals/gap-study-4/
