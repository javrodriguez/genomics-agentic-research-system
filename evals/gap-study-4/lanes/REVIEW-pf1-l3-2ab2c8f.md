VERDICT: CHANGES

# Fourth closure check of lane pf1-l3-transcript-integrity at 2ab2c8f5 (after the third closure check of 461dc169)

Reviewer: the same independent session as the four earlier reviews of this lane, Sun 25 Oct 2026, 00:22 EDT (from `date`).
I read `git log 461dc169..2ab2c8f5` (c99b8c78 the review as written, 2ab2c8f5 the fold).
No code changed.
I worked behind light-ok with python3.12.
The probes are scratchpad l3rev/probe6.py, l3rev/probe7.py and l3rev/dumplines.py; the 461dc169 tree was taken by `git archive` into the scratchpad.

## 1. probe6, re-run: all four in-flight breaks now refuse

| Attempt (turn cut, as the host records) | 461dc169 | 2ab2c8f5 |
|---|---|---|
| The record in flight rewritten | clean | refused: "record in flight differs ... a cut drops units, it never changes one" |
| The last tool_result rewritten | clean | refused |
| Same-id blocks, the second one forged | clean | refused at its item 2 |
| Three trailing results, three records, all deleted | clean | refused at item 4 ("before the record in flight") |
| The last result alone missing | clean | clean (allowed: a tool_result in flight is the last result alone) |
| The last message's blocks, one message id, all missing | clean | clean (allowed: one message) |
| One forged record after the complete stream | clean | clean in the content check, and the line is dropped from grading (part 3) |

Units now group by message id: a tool_use unit carries its message id last, and `_message_id` reads it.
probe7 adds: the stream lagging by two units refuses; the session lagging (the record in flight absent) is clean, with nothing dropped.

## 2. The grading path: byte-identical on every committed claude-code walk

- `run.transcript_lines` ran over the 151 claude-code walks (selected by `driver-ledger.json` `agent.harness`), once from the 461dc169 tree and once from 2ab2c8f5, against the same rehearsals folder.
  The rehearsals are unchanged between the two commits.
- Each output records the sha256 of the joined BoundTranscript lines and the line count, per walk.
- Both runs print 151 walks and the digest `569d3fb40753601c2fb2f994bbb03d172d06ca070636e1acd8064d930702ea76`.
  `cmp` of the two JSON files reports BYTE-IDENTICAL.
- Why it holds: no committed walk has a host-recorded cut (only w-g24 does, and it is Gemini).
  So `confirmed_transcript_text` returns None, and the original path is used unchanged.

## 3. The drop condition: verified, with one gap (finding 1)

`unconfirmed_session_lines` drops a line only when all of these hold:
- the take folder's ledger, which is host-written, records the turn as cut (`host_recorded_cuts`: end timed-out or exit 124, by `n`);
- the turn's session units are exactly the stream's units plus one;
- the units before that one equal the stream's, unit for unit;
- the turn's last content-bearing line carries that single unit and nothing else.

`run.transcript_lines` applies it only when the ledger's harness is claude-code.

In probe7, a line is dropped only in "stream lags by one: extra text record".
Nothing is dropped in:
- the same session with no host cut (that refuses as a mismatch);
- a rewritten record in flight;
- a stream lagging by two;
- a session that lags.

Every drop is of the one line the host cannot confirm.
The check-side readers (study_paths_read, the event counts, the nudge and Agent summaries in walk_regrade) still read that line, so it can only count against the agent.
The grader is handed a temporary BoundTranscript.
No grader reads `.path` (grep of graders/ and run.py), so a path to a deleted folder is never followed.

## 4. A unit sharing a line with a confirmed unit: never dropped, but this does not fail strict (finding 1)

- Probe: the session's last line is one assistant record holding two text blocks, the confirmed "Next." and then "FORGED STOP".
- `content_problems` reads clean, because the stream lags by one and the extra unit sits after the record in flight.
- `unconfirmed_session_lines` drops nothing, since the line carries two units.
- So that is correct for "never dropped": no line is cut in two and no confirmed unit is lost.
- But the forged unit then reaches the graders, which is the opposite of "the extra unit is never graded".
  The case fails open, not strict.
- A second probe, with the extra unit on a two-unit line after a complete stream, gives two items more and refuses.
  So only the shape in the first probe gets through.

## Findings

### 1. MINOR: the ruling "the extra unit is never graded" does not hold when the extra unit shares its line with the confirmed last unit

- An agent that runs past its budget can write its last record as one assistant record with two blocks: the confirmed one, then a forged one.
  The forgery passes `cut_tail_problem` and is handed to every words-graded reading and to the stop classification.
- The CLI never writes this shape.
  Across the 151 committed claude-code walks, the main-thread session and stream records holding more than one text, thinking, tool_use or tool_result block number 0 and 0.
- Fail strict, in one of two places:
  - in `cut_tail_problem`, refuse the stream-lags-by-one shape when the extra unit is not alone on its line (transcript-mismatch); or
  - in `unconfirmed_session_lines`, return a marker so the checker refuses rather than grade.
- Add the probe7 case ("extra unit in the same line as the confirmed last unit") as a red test.
  The new tests do not cover it.

Stop: the rest is clean.
