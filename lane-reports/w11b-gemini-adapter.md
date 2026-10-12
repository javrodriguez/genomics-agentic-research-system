# Lane w11b-gemini-adapter: arm G's adapter, on documented shapes

Gap Study round 4; glitch-2f (Lane-orchestrator) under Javier's standing delegation.
Brief: plans/gap-study-round-4/next-slices-plan-2026-10-12.md section 2, "w11b-gemini-adapter", with ruling Q-3 (build on the documented Gemini CLI shapes now).
Branch gap4/w11b-gemini-adapter from f14ab57b; worktree /Users/javrodher/aegis-builds/gap4-w11b.
This report is appended to, never rewritten.

## Stage 1: the tests first (Mon 12 Oct 2026 15:49 EDT, `date`)

Committed: tests/test_gemini_adapter.py, 15 SYNTHETIC fixtures under tests/fixtures/gemini-streams/ with their README labels, COPIED.d/w11b-gemini-adapter.json and checks.d/w11b-gemini-adapter.txt.
Red on the base (gemini_adapter.py and transcript_gemini.py absent), /usr/local/bin/python3.13, behind mac_slot light-ok and `timeout -s INT 120`:

- `test_gemini_adapter.py`: Ran 116 tests, FAILED (failures=116), 0 errors; every failure an AssertionError (114 "Lists differ" naming the module's missing names, 1 the adapter's name, 1 the witness registry's missing file).
- `test_gemini_adapter.py --witnesses`: FAILED (failures=99), "0/98 red; registry 98".

Gates on this tree: copy_manifest, build_draft, freeze and walk_register `--check` exit 0; lint_language and lint_pooling clean.

## Stage 2: the code, and the generated mutation sweep (Mon 12 Oct 2026 16:31 EDT, `date`)

Added: evals/gap-study-4/gemini_adapter.py (GeminiAdapter, read_stream, argv, exit_meaning, end_reason, SHAPES_SOURCE = "documented") and evals/gap-study-4/transcript_gemini.py (the closed tables, check_record, check_stats, error_text, GeminiParser; not registered in transcript_view.PARSERS), both claimed in this lane's fragment.
The test module grew after stage 1, in two steps: clause-level cases (each clause of each guard bound on its own) and glitch-2f's added requirement, a generated mutation sweep (`--generated-mutants`, shardable with `--shard i/n`, self-contained in the test file; the reviewer's w11a harness was copied to the worktree's untracked .scratch/ as a starting point, never edited in place, never committed).
Red re-run of the final test module on the base (both modules moved aside): Ran 121, FAILED (failures=121), 0 errors; witnesses 0/98 red.

Green on this head, /usr/local/bin/python3.13 behind mac_slot light-ok and `timeout -s INT 120`:

- `test_gemini_adapter.py`: Ran 121 tests, OK.
- `--witnesses`: 98/98 red, each by its own check's prefix, 0 errors (registry 98).
- `--generated-mutants`, eight shards: generated 938 mutants over the two files (statement deletion, condition True and False, boolean operand drop and swap, not-drop, comparison negation, assignment emptying, return None, string-literal change, int change, isinstance/callable/all/any forced True); killed 904, EQUIVALENT 34, survived 0, stale 0; 47 string literals inside `raise` statements skipped by the one listed rule (message text only).
  Shard 8 first hit the 120-second cap at load 23 and was re-run alone after light-ok: 111 killed, 6 equivalent.
- EQUIVALENT, 34 entries in four categories, each entry naming a token its own source line must hold (checked every run, so a drifted entry fails): import-plumbing 16 (the sys.path insert and the __future__ import, both files), identical-mutant 6 (a None written as None, a trailing `return None` deleted), falsy-alike 2 (`joining = False` made None, read only by `and joining`), message-label 10 (labels passed only into a refusal's message).
- Gates: copy_manifest, build_draft, freeze, walk_register `--check` exit 0; lint_language and lint_pooling clean over the folder and over the three new Python files named explicitly.

What the sweep changed in the code (each found by a survivor or by a clause that could be dropped with the suite green): the record check's event-type clauses on `severity`, `error` and `stats` were removed (EVENT_KEYS already confines each key to its event; a comment says so); the parser's redundant string checks were removed (check_record already refuses them); the end-turn rule lost its `results == 1` clause (two results are refused, so a success status implies one); read_stream refuses a stream that is not text instead of reading None as empty; the message raw type is the event type.

## Open questions, each with a proposed answer

- Q-w11b-1: the shapes marked "NOT in D8" (every `timestamp`; message role, content and delta; tool_use and tool_result keys; the error event's severity; the error object's keys; result status's two words; the per-model stats entry's keys; the tool table GEMINI_TOOLS and its argument keys; `gemini --version` printing a bare X.Y.Z) are this lane's reading, unverified (no network). Proposed: the first recorded stream (a bring-up walk) confirms or replaces each through a lane that cites the recording; SHAPES_SOURCE stays "documented" until then.
- Q-w11b-2: the Gemini stream records no permission mode, so the TurnResult's init is None on every turn (never filled from the argv the adapter passed), and routing reads a missing init as a mismatch: no arm G take routes clean as built. The model is checked inside the adapter instead (init.model and every stats.models key, refused on a difference). Proposed: the seam slice first looks for the mode in the session file under GEMINI_CLI_HOME at the bring-up walk; if it is not there, a named, pre-registered arm G rule reads the host's own record of the `--approval-mode` it passed as the mode record.
- Q-w11b-3: the routing pin's word for arm G's mode is this lane's "yolo" (the harness's own word); w11a chose "bypass" for arm O. Proposed: keep each harness's own word in routing.json's pin_profiles; the seam slice aligns the two tables.
- Q-w11b-4: D8:168 read literally refuses a turn whose stats.models holds any other key, so a harness side call on another model (a router or checker call) would refuse every turn. Proposed: keep the refusal; if the bring-up walk shows side-call keys, a ruling adds a pre-registered side-call table whose entries are kept apart, as Claude Code's modelUsage is.
- Q-w11b-5: an exit code off D8's four (a signal exit such as 137) refuses the turn, so no TurnResult comes back for it. Proposed: the driver treats an adapter's StreamError as a harness-side stop with the stream already on disk; if a walk shows signal exits, a box-side table maps 128+n to error and the cgroup counters decide an out-of-memory kill.
- Q-w11b-6: resuming by `-r <session id>` is shown in secondary sources only (D8:138). Proposed: the bring-up walk confirms it; meanwhile the adapter refuses a later turn whose init names another session.

## Owed, not in this lane's file list (carried)

- The freeze's refusal of any arm whose adapter has not been re-tested on a stream recorded at its first real walk (ruling Q-3): freeze.py is outside this lane's list, so it is owed to a later slice; SHAPES_SOURCE and the harness record are in place for it to read.
- Registration in transcript_view.PARSERS, harness_bookkeeping and agent_adapter's tables; drive.py's adapter admission; check_take readers and mode_binding expectations for gemini; routing markers; cost pricing (price_table PENDING); the real-box stub `gemini`; run_take's Gemini billing-route variables (PENDING: every real exec refuses until named).

RESUME HERE: review round (fresh opus-medium, threat model "every guard red by assertion when removed; nothing undocumented is accepted"), then fold.

Athena module list: tests/test_gemini_adapter.py; tests/test_gemini_adapter.py --witnesses; tests/test_gemini_adapter.py --generated-mutants (whole, or --shard i/n); test_agent_adapter.py; test_transcript_view.py; test_scaffold.py (whole); test_round4.py; the gates (copy_manifest, build_draft, freeze, walk_register --check; lint_language and lint_pooling over evals/gap-study-4/).

Correction (Mon 12 Oct 2026 16:29 EDT, `date`): the stage 2 heading above says 16:31; `date` read 16:28 when it was written. The heading stands as committed; this line is the record.
Correction to the correction: its own stamp should read 16:28 (`date` printed 16:28:32).
