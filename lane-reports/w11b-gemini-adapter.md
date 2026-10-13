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

## Stage 3: review round 1 fold, the tests first (Mon 12 Oct 2026 17:58 EDT, `date`)

Review round 1 (d03f43e1, lane-reports/w11b-gemini-adapter-review-r1.md) was CHANGES: 2 MAJOR, 7 MINOR. glitch-2f's ruling w11b-R1-fold: fold all nine; rulings Q-w11b-2 to -6 hold.
The reviewer's repro and harness were copied to the worktree's untracked .scratch/review-r1/ (not edited in place, not committed).
Committed in this stage: the test module and the fixture README's RECORDED wording, both run against the pre-fold code (gemini_adapter.py and transcript_gemini.py at 4da835dc).
Red: Ran 135, FAILED (failures=99), 0 errors (88 of them witnesses whose anchors name fold code that does not exist yet, plus the generated-sweep baseline, the stale EQUIVALENT list and the anchor registry).
Each finding red by its own check's line on the pre-fold code:

- W11B-R1-1: "A1-stream: a line that is not JSON before the last accepted it"; "A1-stream: a stream holding ' ' inside a command and an error message reads ([], False, '', None, 6, [])", and the same for '\x85'; "A8-turn: a line of bytes that are not UTF-8 before the last accepted it" (the old test that pinned the tolerance, inverted).
- W11B-R1-2: "S4-stats: the record check accepted it: a successful result with no stats" (and the parser); "A4-stats: a successful result with no stats accepted it" (the old A4 acceptance, inverted).
- W11B-R1-3: "A5-model: stats naming no model and no init accepted it".
- W11B-R1-4: S3-words, 24 lines: delta 'yes' and 1, timestamp an object and an int, session_id 5, model a list, output a list, an error event's message 5, error.type an object and error.message 5 on a result and a tool_result.
- W11B-R1-5: one single-change test per required key per event, through decode, the parser (S2-key) and read_stream (A1-stream). They pass on the pre-fold code, which refuses each by a ShapeError or a KeyError. The binding is new: the generated sweep's element-drop operator now kills every drop of a required key (the fold dropped `type` from the required tuples, where the event lookup already refuses it, and made tool_kind read its required keys by index).
- W11B-R1-6: "A6-argv: an argv with the model --sandbox accepted it", "-s", "a model holding a space", "an adapter made with the model --sandbox accepted it"; "A5-model: a stream read against model '--sandbox' accepted it".
- W11B-R1-7: the suffixed prints ("0.63.0-nightly.20261012", "0.63.0 extra", "0.63.0.1") pass on the pre-fold code, which already uses fullmatch; they bind the fullmatch-to-match mutant (witness version-matched, the sweep's fullmatch-match).
- W11B-R1-8: "A6-argv: a later turn with session id 'latest' accepted it", '1', '42'; "A7-session: an init session id 'latest' accepted it", '0', '17'.
- W11B-R1-9: RECORDED_LABEL, as w11a's, fullmatch "RECORDED at walk <id>, gemini-cli <X.Y.Z>."; a unit test refuses five partial labels; the README now says exactly that.

The generated sweep gained the reviewer's operators where they apply: boundary swaps, `is True` to truthy, fullmatch to match and to search, regex loosening, one element of a literal tuple or list dropped, one dict-literal entry dropped, `.strip()` dropped, list/sorted/set unwrapped (21 kinds in all).

Correction: the stage 3 heading says 17:58; `date` read 17:43 when it was committed (26a26789). The heading stands as committed; this line is the record.

## Stage 4: review round 1 fold, the code (Mon 12 Oct 2026 17:45 EDT, `date`)

What changed, by finding:

- W11B-R1-1 (MAJOR): read_stream splits on "\n" only (never str.splitlines); a line that is not JSON refuses unless it is the stream's last non-blank line (a cut stream, undecoded 1).
- W11B-R1-2 (MAJOR): check_record refuses a result whose status is success and which carries no stats, so end_turn never reads with usage unmeasured; a failed result may still carry none.
- W11B-R1-3: read_stream refuses a stream whose stats name no model while the call has no init.
- W11B-R1-4: VALUE_TYPES, one exact type per key (`type(v) is`), and ERROR_OBJECT_TYPES for the error object; delta is a bool; the content and tool-id string checks and the error-object and stats object checks it replaces were removed; error_text reads checked records by index.
- W11B-R1-5: `type` left the required tuples (the event lookup refuses a record without it); tool_kind reads tool_name and parameters by index, so dropping either from the required tuple fails instead of passing.
- W11B-R1-6: _MODEL_ID (box/take_config.py's _MODEL shape, alphanumeric first) at the three seats: read_stream, argv (before the argv is built) and the constructor.
- W11B-R1-8: _SESSION_ID refuses `latest` and an all-digit id, in the init and in argv.
- W11B-R1-7 and W11B-R1-9: test-side only (above).

Green on this head, /usr/local/bin/python3.13, every batch behind mac_slot light-ok and `timeout -s INT 120`:

- `test_gemini_adapter.py`: Ran 135 tests, OK.
- `--witnesses`: 111 red, each by its own check, 0 errors (registry 111; 19 entries were replaced or removed with the code they named, one dropped as equivalent on JSON input: exact type against isinstance differs only for a bool or a subclass, and no VALUE_TYPES entry is an int).
- `--generated-mutants`, 16 shards (each under the 120-second cap): generated 1154 over the two files, killed 1114, EQUIVALENT 40, survived 0, stale 0; 50 strings inside `raise` statements skipped by the one listed rule. Re-sampled after the allow-list went in: shard 3 of 16 (68 killed, 4 equivalent) and shard 11 of 16 (72 killed).
- EQUIVALENT, 40 entries in seven categories, each naming a token its line must hold: import-plumbing 16, message-label 10, identical-mutant 7, falsy-alike 2, typed-bool 2 (`delta is True` where VALUE_TYPES makes delta a bool), message-order 2 (sorted() only orders a refusal's message), sequence-alike 1 (list(VERSION_ARGV), which run_take takes as a tuple too).
- Gates: copy_manifest, build_draft, freeze, walk_register `--check` exit 0; lint_language and lint_pooling clean over evals/gap-study-4/ and over the three new Python files named explicitly.
  lint_language flags two ratio shapes in this report's stage 2 section (lines 22 and 27); the report is outside the gated folder and append-only, so they stand, and later sections avoid the shape.

Residual for the seam slice (not this lane's files): claude_code_adapter.py:100 and codex_adapter.py:116 also split their streams with str.splitlines.
Observations from the review carried as they stand: an error event followed by a success result under exit 0 reads end_turn with the error in api_errors; duplicate JSON keys read last-wins; tool_result ids are not paired against tool_use ids in read_stream; GEMINI_SETTINGS does not pin Gemini's sandbox off (it is off by default, and nothing in argv or the exec environment turns it on).

RESUME HERE: review round 2 (fresh opus-medium; re-run the sampled shards and the reviewer's operator set on the fold, and confirm each finding red by its own check's line).

Athena module list: tests/test_gemini_adapter.py; --witnesses; --generated-mutants (whole, or --shard i/n, 16 shards keep each under 120 s on the Mac); test_agent_adapter.py; test_transcript_view.py; test_scaffold.py (whole); test_round4.py; the gates (copy_manifest, build_draft, freeze, walk_register --check; lint_language and lint_pooling over evals/gap-study-4/).

Correction (Mon 12 Oct 2026 17:46 EDT, `date`): lint_language over this report flags four lines, not two: the ratio shapes at lines 14, 22 and 27 (stages 1 and 2), and the residual line in stage 4, where the line number of claude_code_adapter.py reads as the banned hundred. The report stays outside the gated folder and append-only.
That correction's own stamp should read 17:45 (`date` printed 17:45:43).

## Stage 5: ruling w11b-close-1, the tests first (Mon 12 Oct 2026 18:05 EDT, `date`)

Review round 2 (9d7c8c8b) passed with one MINOR; glitch-2f's ruling w11b-close-1 folds it and the reviewer's case observation.
Red on the stage 4 code: Ran 138, FAILED (failures=43), 0 errors (38 witnesses whose anchors name the fold's code, the sweep baseline, the anchor registry, and A1, A6, A7).
Own lines:

- W11B-R2-1: "A1-stream: a stream whose only non-blank line is not JSON accepted it", for 'Error: quota exceeded\n', a lone cut '{"type": "ini' and a junk line among blank lines.
- The case observation: "A6-argv: a later turn with session id 'LATEST' accepted it" and 'Latest'; "A7-session: an init session id 'LATEST' accepted it" and 'lAtEsT'.

## Stage 6: ruling w11b-close-1, the code (Mon 12 Oct 2026 18:38 EDT, `date`)

- W11B-R2-1: read_stream refuses a stream whose only non-blank line is not JSON (`n != len(lines) or n == 1`), so the driver treats it as a harness-side stop (Q-w11b-5); a cut last line after real records still reads undecoded 1.
- _SESSION_ID refuses `latest` in any case (`(?!(?i:latest)$)`), in the init and in argv.
- Witnesses added: lone-junk-accepted, midstream-clause-dropped (each clause of the new condition on its own), session-latest-case-sensitive.
- The stage 4 EQUIVALENT keys whose line numbers moved were re-keyed by kind, digest and text; one was first re-keyed onto the wrong `return None` (exit_meaning's, which the suite kills); the sweep reported it STALE, and it was corrected to the `_end` method's.

Green on this head, every batch behind mac_slot light-ok and `timeout -s INT 120`:

- `test_gemini_adapter.py`: Ran 138 tests, OK.
- `--witnesses`: 114 red, registry 114, 0 errors.
- `--generated-mutants`, 16 shards: generated 1159, killed 1119, EQUIVALENT 40, survived 0, stale 0 (shards 4 and 5 re-run after the re-key fix; 50 raise strings skipped by the rule).
- Gates: copy_manifest, build_draft, freeze, walk_register `--check` exit 0; lint_language and lint_pooling clean over evals/gap-study-4/ and over the three Python files named explicitly.

RESUME HERE: athena on this head (glitch-2f re-runs it), then the merge after wave 10.

Athena module list: tests/test_gemini_adapter.py; --witnesses; --generated-mutants (whole, or --shard i/n); test_agent_adapter.py; test_transcript_view.py; test_scaffold.py (whole); test_round4.py; the gates (copy_manifest, build_draft, freeze, walk_register --check; lint_language and lint_pooling over evals/gap-study-4/).
