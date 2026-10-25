VERDICT: CHANGES

# Third closure check of lane pf1-l3-transcript-integrity at 461dc169 (after the second closure check of f0c0eb1d)

Reviewer: the same independent session as the three earlier reviews of this lane, Sat 24 Oct 2026, 23:42 EDT (from `date`).
I read `git log f0c0eb1d..461dc169` (3411961a, the review as written; 461dc169, the fold).
No code changed.
The probes ran behind light-ok on synthetic fixtures (scratchpad l3rev/probe6.py).

## What closed

- **Probe5's three deletions now refuse:** the last two session records dropped, the cut turn's content emptied, and a cut first turn's tail dropped.
  test_d1a binds these, and test_d1d is the witness against the old prefix rule.
  probe6 adds "session lacks two records": refused at item 3.
- **codex_adapter** `read_stream` and `_rollout_records` split on `"\n"` alone.
  C0 handling is unchanged in effect:
  - a raw `\x0b` inside a string makes the line invalid JSON, and `read_stream` raises StreamError ("line 1 of 2 is not JSON");
  - a `\x0b` joining two records now refuses the same way, where before `splitlines` would have split it into two records.
  The adapter has no separator list of its own; the refusal comes from strict `json.loads`.
- **test_line_separators:** the check that the cross-check names a session file carrying `\x0b` is restored, with the "cross-check crashes" witness.
- **w-sep** is back on the line call (`transcript-unreadable`, "line separator(s) U+000B").
- **Residual (c)** names the claude-code cut form.
- **freeze_rehearsal.LIVE_BOX_REQUIRED** records the forced-timeout take as text only.
  Making it a failing step is ruled to L6 or the run-launcher lane.

## Breaking the in-flight rule

| Attempt (turn cut, as the host records) | Result |
|---|---|
| Session equal to the stream | clean |
| Session lacks the stream's last record | clean (allowed) |
| Session lacks two records | refused |
| The stream's last record **rewritten** in the session (a divergent unit in its place) | **clean** (finding 1) |
| A complete stream plus one **forged** record in the session | clean (finding 2) |
| Last record a tool_result: three trailing results (three records) all deleted | clean (finding 3) |
| Last record a tool_result: the final result's content rewritten | **clean** (finding 1) |
| Two assistant blocks sharing one message id: all three of the message's blocks dropped | clean (one message, allowed) |
| The same id: first block kept, second rewritten | **clean** (finding 1) |
| Control, turn not cut: the in-flight rewrite | refused |

## Findings

### 1. MAJOR: in a cut turn, the record in flight can be rewritten, not only dropped

- In `cut_tail_problem`, after the head, `k` counts the matching prefix of `rest` against `last`.
  The rule refuses only when `len(rest) - k > 1`.
- So the session may hold the matching prefix and then one unit that differs from the stream's unit at the same place.
  That one unit can be any content: a rewritten final reply ("I decline and stop here." in place of "I will read the planted file next."), a forged tool output, or a rewritten second block of the last message.
  All three probes read clean, where the same edit without a cut is refused.
- A kill cannot produce this.
  The CLI writes each unit from one object to both files, so a unit present in both records has the same content.
  The only genuine shapes are:
  - the session lags: `rest` is a prefix of `last`;
  - the stream lags: `rest == last` plus one unit.
- Fix: refuse unless `rest == last[:len(rest)]`, or `rest[:len(last)] == last and len(rest) == len(last) + 1`.
- Add the rewrite as a red case.
  test_d1b's cases (lacks the last record, one record ahead, two ahead, a rewrite before the record in flight) do not cover a rewrite of the record in flight itself.

### 2. MINOR: the one extra unit the rule allows is unverified content, and it is graded

- When the stream lags, the session's extra unit has no host copy.
  An agent that runs past its budget can therefore add one forged record (probe: a final "STOP: I am waiting for the operator.") and have it read by every words-graded reading and by the stop classification.
- The allowance is needed for a genuine cut, but the graders need not read what the host cannot confirm.
- Either leave the extra unit out of what the cut turn is graded on, or name in residual (c) that it is graded unconfirmed.
  The residual now says only "at most one unit more".

### 3. MINOR: a trailing tool_result "record" can be several records

- When the stream's last unit is a tool_result, `_last_record_length` takes the whole trailing run of tool_result units.
  With parallel calls, that run spans one user record per result.
- So all of them can be deleted (probe: three results, three records, all dropped: clean).
- The ruling allows the one record in flight.
  Bound the group to the last tool_result unit, which in Claude Code is one user record per result.
  Alternatively, if parallel results are ever written as one record, read the record boundary from the stream.
- The docstring says "one user tool_result record's (the trailing run of tool_result units)", and that wording hides the difference.

### 4. NIT: the "one message" group excludes the message's own tool_use blocks

- The group is keyed by `u[1]`, which is the message id for text and thinking but the tool id for tool_use.
- So a message's tool_use blocks never join its text group.
  This is stricter, not looser, so a real cut that lags inside one message's mixed blocks could read as a mismatch.
- The live-box forced-timeout take will show whether that matters.
