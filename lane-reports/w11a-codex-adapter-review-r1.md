# Review round 1: w11a-codex-adapter (construction)

_Written Mon 12 Oct 2026 15:48 EDT (`date`) by a fresh Claude Opus 5.5 reviewer, round 1._
Reviewed: branch gap4/w11a-codex-adapter, base f14ab57b, head 3cd99ebb (red 6aaf9a8e, code 6a410c07).
Threat model (as briefed): the adapter must never silently accept a shape it does not know, never invent a value, never read the agent's text as an API error or the reverse, never resume a different thread, never run without the pinned mode, and must report its shape source honestly; every guard red by assertion when removed.

## Verdict: CHANGES (4 MAJOR, 6 MINOR)

The code itself behaves correctly on every input I tried: each repro below is refused on the head.
The findings are guards the suite does not bind: each one can be weakened or removed with all 28 tests and all 13 witnesses green.

## What I ran (Mac, each batch behind `mac_slot.py light-ok`, `timeout -s INT 120`, python3.13)

- `tests/test_codex_adapter.py`: Ran 28 tests, OK.
- `tests/test_codex_adapter.py --witnesses`: "13/13 red; registry 13", OK.
- An AST mutation sweep of my own, in memory only (nothing written to the worktree): every comparison swapped, every `and`/`or` swapped and each operand dropped, every `not` dropped, every `if` forced True and False, every `raise` dropped, ints +1, short strings altered, assignments and returns set to None, `isinstance`/`all`/`callable` forced True.
  Each mutant was run against all eleven bound checks (S1-S3, P1, A1-A7) plus the version-form and name tests; a tc mutant was also rebuilt into codex_adapter.
  transcript_codex.py: 337 mutants, 75 survivors (27 of them message or table strings, the rest listed by finding below or equivalent).
  codex_adapter.py: 452 mutants, 143 survivors (45 strings).
  Equivalent survivors set aside: the sys.path preamble, the version cache, initial-state assignments, `mode` clauses redundant behind `mode not in MODE_FLAGS`, argv's mode check (a KeyError follows anyway), error_text's branch outside its only call site, display-only `isinstance` on result text, and tightening-only mutants (e.g. allowed-key names in the mcp entry, the later-turn `read["thread_ids"] and` clause).
- A targeted repro script confirming each MAJOR/MINOR below on the real module (refused) and on the single mutant (accepted, suite still green).

## Findings

### W11A-R1-1 MAJOR: end_reason's three clauses and the turn.failed count are each unbound

codex_adapter.py:232 and :130.
Dropping any one clause of `exit_code == 0 and read["completed"] == 1 and read["failed"] == 0` keeps the suite green; the witness failed-as-end-turn drops all three at once, so no single clause is witnessed.
Repro (suite `[]` on each mutant): `end_reason(1, False, {"completed": 1, "failed": 0})` reads `error` on the head and `end_turn` with the exit clause dropped; `end_reason(0, False, {"completed": 0, "failed": 0})` (a stream with no turn.completed) reads `end_turn` with the completed clause dropped; `{"completed": 1, "failed": 1}` reads `end_turn` with the failed clause dropped.
Line 130 forced False (turn.failed never counted): a stream holding turn.failed and turn.completed under exit 0 reads `error` on the head and `end_turn` on the mutant.
Why it matters: a failed or cut turn graded as a finished one.
Needed: one A6 case per clause (exit non-zero with a clean stream; exit 0 with no turn.completed; exit 0 with both turn.failed and turn.completed), each with its own witness.

### W11A-R1-2 MAJOR: the thread-id guards are unbound at every seat

codex_adapter.py:134-135 (read_stream's thread-id shape), :222-223 (argv's later-turn id check), :308 (turn 1 must name exactly one thread).
Each is removable with the suite green, and so are 134 and 222 together.
Repro with both shape checks removed: a turn-1 stream `{"type":"thread.started","thread_id":"--last"}` is refused on the head ("thread id off its shape") and on the mutant yields argv `codex exec --json -m m --dangerously-bypass-approvals-and-sandbox resume --last two`, i.e. resume whatever session is newest, not turn 1's thread.
`argv(..., session_id=None, first=False)` is refused on the head and no test calls it (a turn 1 with no thread.started).
Line 308 changed to `if read["thread_ids"]:` (turn 1 naming two threads takes the first) also survives.
Why it matters: "never resume a different thread" is bound only for a later turn that names a different, well-formed id (other-thread-resumed).
Needed: a turn-1 stream with an off-shape thread id, one with no thread.started, and one with two thread ids, each refused before turn 2 execs, with witnesses.

### W11A-R1-3 MAJOR: the required-key half of the closed tables is unbound

transcript_codex.py:113-115 (`_keys`'s missing-key refusal).
Setting `missing = []` keeps every test green (S3 only tests extra keys).
Repro: the stream `thread.started` / `{"type":"error"}` / `{"type":"item.completed","item":{"id":"i1","type":"command_execution"}}` / `turn.completed` is refused on the head; on the mutant read_stream accepts it, with an api_error whose text is None and a command_execution with no command counted as agent output and a tool id.
Needed: one refused record per entry that drops a required key (at least `error` without message, an agent_message without text, a command_execution without command), through both decode and read_stream, with a witness.

### W11A-R1-4 MAJOR: the rollout init guards are unbound

codex_adapter.py:198-199 (two models in one turn), :204 (all three init fields non-empty strings), :201 (exactly one session_meta).
Repro (each mutant suite `[]`): a rollout with turn_contexts naming models "a" then "b" in one turn is refused on the head and reads init model "b" on the mutant (one picked, which the docstring says never happens); a turn_context with no approval_policy reads init None on the head and `{"model": "a", "permission_mode": None, "version": "0.1.0"}` on the `if True` mutant (TurnResult does not type-check init values, agent_adapter.py:162, so it would pass through); two session_meta records read init None on the head and take the first's cli_version on the mutant.
Why it matters: the init is the served-model record (D8:168); A5 only exercises the "no new turn_context" path.
Needed: A5 cases for two models in one turn, a missing or non-string field, and zero or two session_metas, with witnesses.

### W11A-R1-5 MINOR (loosens a check): usage count clauses and the two-turn.completed refusal are unbound

codex_adapter.py:99 and :140-141.
Dropping `not isinstance(v, bool)` accepts `output_tokens: true`; dropping `v >= 0` accepts `output_tokens: -5`; both are refused on the head; suite green.
Removing the two-turn.completed refusal also survives.

### W11A-R1-6 MINOR (loosens a check): the empty model and empty line guards are unbound at both seats

codex_adapter.py:214-215 and :268-269.
With both removed the suite is green and `argv("x", model="", ...)` yields `-m ""`, a model pin with no model.

### W11A-R1-7 MINOR (loosens a check): a blank agent_message counted as output is unbound

codex_adapter.py:154.
Replacing `(it != tc.AGENT_MESSAGE or (item.get("text") or "").strip())` with `True` survives; a whitespace-only agent_message reads agent_output False on the head and True on the mutant (agent_output decides first_turn_started).

### W11A-R1-8 MINOR (loosens a check): the value-type guards in transcript_codex are unbound, and read_stream does not type-check agent text

transcript_codex.py:126, 134, 137, 142, 148, 160, 179, 217, 221 each survive removal.
Most then crash untyped rather than accept, but two become silent accepts: an item id of `""` (line 148) and a file_change with `changes: []` (line 217, no call emitted).
Separately on the head: `read_stream('{"type":"item.completed","item":{"id":"i","type":"agent_message","text":5}}')` raises AttributeError (codex_adapter.py:154), not a typed StreamError; check_record checks keys, not value types.

### W11A-R1-9 MINOR (loosens a check): A7 accepts a RECORDED label with no provenance, and the lane report overclaims it

tests/test_codex_adapter.py `a7_source` counts any README line `- \`f\`: RECORDED...` regardless of the rest of the line.
lane-reports/w11a-codex-adapter.md:86 says "recorded" is reachable only with a fixture labelled RECORDED "with the walk and harness version it was captured at (A7 already refuses "recorded" without one)"; A7 refuses only a missing RECORDED word, not missing walk or harness version.
Repro (on a scratch copy of the fixture folder, never the worktree): add `- \`x.jsonl\`: RECORDED` to the README plus an empty x.jsonl, point the test's FIXTURES at the copy, and compile codex_adapter with SHAPES_SOURCE = "recorded": `a7_source` returns `[]`.
Either bind the provenance fields in A7 or correct the report line.

### W11A-R1-10 MINOR (loosens a check): undecoded lines are tolerated anywhere, and their count is unbound

codex_adapter.py:119-123.
The docstring (line 112) says "a cut stream's last line"; on the head `read_stream("garbage\n{...turn.started...}\nmore garbage")` returns `undecoded: 2` without refusal, and the `bad += 1` count survives being set to None or +2 (A1 checks only 0).
The Claude Code adapter has the same tolerance, so this is a precedent, but nothing binds the count that the turn record carries.

## Observations (not findings)

- `version()` is never called by `_turn`; the init's version is the rollout's cli_version and nobody compares it with `codex --version` or the pin's `version`. The init's permission_mode ("never") is likewise not compared with the pin's "bypass". Both are carried by the report (Q-w11a-4, mode_binding); worth naming in the seam slice's brief.
- The rollout's record types and turn_context keys are not closed; the report is explicit that the rollout is read for three fields only (Q-w11a-1).
- Ruling Q-3: SHAPES_SOURCE is "documented", reported in harness_record and every turn record, and the shapes-recorded witness is red. Holds, subject to W11A-R1-9.
- The brief's minimum witness set is present and each of the 13 witnesses goes red by its own check.

## Stop rule

Four MAJORs, so not a PASS. Round 2 should re-run my mutation sweep (or an equivalent) on the fold and confirm each named survivor is killed by its own check.
