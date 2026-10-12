# Review round 1: w11b-gemini-adapter

_Written Mon 12 Oct 2026 16:40 EDT (`date`) by a fresh Claude Opus 5.5 reviewer, round 1._
Reviewed: branch gap4/w11b-gemini-adapter, base f14ab57b, head 2b0f16ff (tests 030d7d13, code 4da835dc).
Threat model (as briefed, as for w11a): closed shapes; nothing undocumented accepted; no invented values (missing usage refused, the model never defaulted); agent text never read as an API error; no different session resumed; exit 53 never end_turn; the shape source reported honestly; every guard red by assertion when removed.
Rulings applied: Q-3, Q-w11b-2 to Q-w11b-6 (glitch-2f).
The w11a reviews (gap4-w11a, lane-reports/w11a-codex-adapter-review-r1.md, rounds 1 and 2) set the bar.

## Verdict: CHANGES (2 MAJOR, 7 MINOR that loosen a check)

The rulings hold on the head: init stays None with its reason (Q-w11b-2), the mode word is "yolo" (Q-w11b-3), an extra stats.models key refuses (Q-w11b-4), an exit code off {0, 1, 42, 53} raises StreamError (Q-w11b-5), and a later turn whose init names another session refuses (Q-w11b-6).
Exit 53 reads `error`, never `end_turn`; an assistant message saying 429 is never an API error.
The two MAJORs are fail-open paths: a record dropped without a word, and a finished turn with no usage.

## What I ran (Mac, each batch behind `mac_slot.py light-ok`, `timeout -s INT 120`, python3.13)

- `tests/test_gemini_adapter.py`: Ran 121 tests, OK.
- `tests/test_gemini_adapter.py --witnesses`: "98/98 red; registry 98".
- The builder's sweep, sampled (athena runs it whole): `--generated-mutants --shard 2/8` gave 118 ran, 114 killed, 4 equivalent, 0 survived, 0 stale; `--shard 7/8` gave 117 ran, 111 killed, 6 equivalent, 0 survived, 0 stale; both say "generated 938" and "47 message-text strings skipped". This matches the claim.
- My own harness, in memory only (scratchpad, nothing written to the worktree), run against the builder's bound checks (`all_checks`): operators the builder's generator lacks: raise-string change, `.strip()` dropped, `fullmatch` to `match` and to `search`, a compiled regex loosened to `(.+)`, one element dropped from each literal tuple or list, one entry dropped from each dict literal, `X is True` to truthy `X`, boundary swaps (`>` to `>=` and kin), and `list`/`sorted`/`set` unwrapped.
  892 mutants; survivors other than raise strings and equivalents are named under the findings below (W11B-R1-4, R1-5, R1-7).
- A repro script on the head modules for every finding (results quoted in each finding).

## The EQUIVALENT list, audited against the source (34 entries: all hold)

- **import-plumbing (16):** gemini_adapter.py:65, 72-74 and transcript_gemini.py:45, 51-53 (the `__future__` import and the sys.path insert, incl. `insert(0` to `insert(1`). The test puts the module folder on sys.path first (test line 79-80), and no annotation is evaluated at runtime.
- **falsy-alike (2):** gemini_adapter.py:125 and :141, `joining = False` to None. The only reader is `and joining` at :154; :158 overwrites it. Holds.
- **message-label (10):** gemini_adapter.py:185 (`'line'`, `'model'`) reach only the f-string at :187; :246 (three callable labels) reach only the TypeError at :248; transcript_gemini.py:127, :135, :145 (two), :171 pass `what` into `_keys`, which uses it only in its two raises (:113, :116). Holds.
- **identical-mutant (6):** gemini_adapter.py:203 and :306 (`return None` to `return None`, and :306 deleted at a method's end), :255 and :256 (`= None` to `= None`), transcript_gemini.py:212 (`return None`). Holds.
- The MESSAGE_TEXT_RULE (47 raise strings skipped): my raise-string operator found no check or logic that reads them; the rule holds.

## Findings

### W11B-R1-1 MAJOR: a record whose text holds U+2028 or U+0085 is dropped without a word, and a non-JSON line anywhere is tolerated

gemini_adapter.py:126 (`text.splitlines()`) and :130-134 (a line that is not JSON is counted and skipped wherever it sits); the test pins the second at test line 808 (a mid-stream junk line must be accepted with `undecoded` 1).
Python's `str.splitlines` also splits on U+2028, U+2029, U+0085, U+001C-001E and others; Node's `JSON.stringify` writes U+2028 and U+0085 raw inside strings (verified here: `node -e 'JSON.stringify({c:"a b\u0085c"})'` prints the raw bytes e2 80 a8 and c2 85).
That Gemini CLI writes stream-json through `JSON.stringify` is my inference (a Node CLI), not checked against its source.
Repro (head): `read_stream(init + tool_use{"command":"echo a b"} + result success, model=M)` gives `tool_ids []`, `agent_output False`, `undecoded 2`, and `end_reason` `end_turn`: the agent's own tool call has vanished.
A failed result whose error message holds U+2028 gives `status None`, `api_errors []`: the API error is lost.
An assistant message holding U+0085 gives `agent_text ''`, `agent_output False`.
Why it matters: the agent writes the characters, and the record leaves the turn silently (agent_output decides first_turn_started; api_errors feed routing).
The sibling w11a was held to this at W11A-R1-10, and its fold refuses a non-JSON line anywhere but the last (codex_adapter.py:122, B10-cut); w11b carries the old tolerance and a test that binds it.
The memory lesson already says it: split JSONL on newline only.
Needed: split on "\n" only, refuse a non-JSON line that is not the stream's last, and invert test line 808; one witness for each.
(claude_code_adapter.py:100 and codex_adapter.py:116 also use `splitlines`; in w11a's fold that is a false refusal rather than a drop. A cross-arm note for the seam slice, not this lane's file.)

### W11B-R1-2 MAJOR: a successful result with no stats reads end_turn with usage None

transcript_gemini.py:71 (`stats` allowed, not required, on a result), gemini_adapter.py:172 and :214; test line 618 binds the acceptance (A4, "a result with no stats" must be accepted, stats None).
Repro (head): `read_stream(init + {"type":"result","status":"success"})` gives `stats None`, and `end_reason(0, False, read)` gives `end_turn`.
Why it matters: the threat model says missing usage is refused; D8 section 1 says the result event carries stats; the per-call usage is what the walk gate extrapolates against the $400 cap, so an unmeasured finished turn undercounts spend.
The sibling holds the line: Codex's turn.completed requires `usage` (transcript_codex.py:68), so every w11a end_turn is measured.
Needed: stats required on a result (at least on a `success` one), A4 inverted to a refusal, and a witness.

### W11B-R1-3 MINOR (loosens a check): D8:168's model check can run on nothing

gemini_adapter.py:144-150 and :172-177 (an empty `stats.models` passes; init is optional), with :290 (a later turn with no init is accepted).
Repro (head): a stream holding only `{"type":"result","status":"success","stats":{...,"models":{}}}` reads `init_model None`, `served_models []`, `end_turn`.
So a turn can end clean with no record naming any model, and (on a later turn) no record naming the session.
Needed: end_turn only when at least one model record (init.model or a stats.models key) names the row's model, or refuse an empty `stats.models` whose counts are non-zero; a witness.

### W11B-R1-4 MINOR (loosens a check): value types are not closed

transcript_gemini.py:64-72, :203-213; gemini_adapter.py:154, :158, :170-171.
Repro (head), each accepted: an error event `{"type":"error","message":5}` gives an api_error with `text None`; `"delta":"yes"` on an assistant message; `timestamp` as an object; a failed result whose `error.type` is a dict (it lands in api_errors as `{"a":1}`); a tool_result whose `output` is a list.
My `X is True` to truthy mutant at gemini_adapter.py:154 and :158 survives (delta's value is not bound).
The sibling's fold added a value-type table and B8-types for this class (W11A-R1-8).
Needed: a per-key value-type table (strings for message, timestamp, error.type/message, output; bool for delta) and one witness.

### W11B-R1-5 MINOR (loosens a check): two required keys are unbound, and four are bound only by a crash nobody runs

transcript_gemini.py:65 and :70 (and :66, :67, :69, :71).
My element-drop survivors: removing `message` from the error event's required keys (:70) makes `{"type":"error"}` accepted everywhere, as an api_error with text None; removing `session_id` from init's (:65) makes an init with no session id pass check_record and GeminiParser (read_stream then dies with a KeyError, not a StreamError).
Removing `role`, `content` (:66), the tool_result's `tool_id` (:69) or the result's `status` (:71) survives too: each then fails by a KeyError inside check_record, but no check feeds such a record, so not even a crash kills them.
This is W11A-R1-3's class (MAJOR there); here it is MINOR because S2 binds the init model, the tool_use parameters and the error object's message, and the rest fail closed.
Needed: one refused record per required key (through decode and read_stream), with a witness.

### W11B-R1-6 MINOR (loosens a check): a model that looks like a flag enters argv

gemini_adapter.py:185-192 (argv) and :249 (the constructor): the model is checked as a non-empty string only.
Repro (head): `argv("hi", model="--sandbox", mode="yolo", session_id=None, first=True)` returns `['gemini', '-p', 'hi', '-o', 'stream-json', '-m', '--sandbox', '--approval-mode', 'yolo']`; `model="-s"` likewise.
No other seat can carry an unpinned flag: the line is refused when it starts with "-" (:188), the mode flags are fixed (:89), the session id must start alphanumeric (:96), and run_take's `_check_argv` checks types only (run_take.py:220-225); the container env carries only `exec_values` (run_take.py:423-431), so no `GEMINI_SANDBOX` can ride.
Whether yargs reads `-m --sandbox` as the `--sandbox` flag is my inference, not run.
The model is study data, not the agent's, and box/take_config.py's `_MODEL` regex (alnum first) exists but is not applied here; w11a's argv has the same gap.
Needed: refuse a model that does not fullmatch a model-id shape (take_config's `_MODEL` will do) at both seats, with a witness.

### W11B-R1-7 MINOR (loosens a check): the version's full match is unbound

gemini_adapter.py:264 (VERSION_FORM at :87).
My `fullmatch` to `match` mutant survives: A8's bad prints ("Gemini CLI 0.63.0", "0.63", "v0.63.0", a failed exit, None) all fail at the start, so none tests a tail.
Under the mutant `0.63.0-nightly.20261012` reads as the pinned `0.63.0`.
Needed: one bad print with a suffix (and one with trailing words) in A8.

### W11B-R1-8 MINOR (loosens a check): the session-id shape admits `-r`'s documented non-id selectors

gemini_adapter.py:96 (`_SESSION_ID`), used at :151 and :194.
D8:138 says `-r` is documented with `latest` or an index; both pass the shape.
Repro (head): an init with `session_id "latest"` is accepted, and `argv(..., session_id="1", first=False)` ends `-r 1` (resume by index).
With a later turn's missing init accepted (:290), a turn could resume whatever session is newest and pass.
Reachable only if the harness names such an id, so MINOR.
Needed: refuse `latest` and an all-digit id at both seats, with a witness (the bring-up walk then fixes the real id shape).

### W11B-R1-9 MINOR (loosens a check): A9 accepts a RECORDED label with no provenance, and the fixture README overclaims it

tests/test_gemini_adapter.py:842 counts any label whose kind is RECORDED; tests/fixtures/gemini-streams/README.md line 6 says "recorded" is reachable only with a file "labelled RECORDED, with the walk and harness version it was captured at".
This is W11A-R1-9 again; the sibling's fold binds the full label (`RECORDED at walk <id>, codex-cli X.Y.Z.`, fullmatch).
Needed: the same fullmatch for `gemini-cli X.Y.Z`, or the README line corrected.

## Observations (not findings)

- An `error` event (even severity `error`) followed by a `success` result under exit 0 reads `end_turn`; the error stays in api_errors, so routing still sees it. The walk should say whether Gemini's error event is ever fatal.
- Duplicate JSON keys are read last-wins: `{"type":"result","status":"error","status":"success"}` reads `success`. A harness anomaly only (the agent's text is escaped inside strings).
- tool_result ids are not paired against earlier tool_use ids in read_stream.
- GEMINI_SETTINGS (take_config.py:49-52) does not pin Gemini's sandbox off; it is off by default and nothing in argv or the exec env can turn it on (W11B-R1-6 aside). For the seam slice.
- The worktree's untracked `.scratch/` holds the w11a reviewer's harness copy; nothing of it is committed.

## Stop rule

Two MAJORs, so not a PASS.
Round 2 should re-run the sampled shards, re-run my operator set on the fold, and confirm each finding above is red by its own check's line.
