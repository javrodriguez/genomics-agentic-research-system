VERDICT: CHANGES

# Second closure check of lane pf1-l3-transcript-integrity at f0c0eb1d (after the closure check of 8cf492b2)

Reviewer: the same independent session as REVIEW-pf1-l3-fb35432.md and REVIEW-pf1-l3-8cf492b.md, Sat 24 Oct 2026, 23:03 EDT (from `date`).
Read: `git log 8cf492b2..f0c0eb1d` (7e3ae1bf the review, 3739ef7a the fold, f0c0eb1d the checks list), checked against the lane orchestrator's rulings 1-5 on the closure check of 8cf492b2.
No code changed.
My probes ran on synthetic fixtures and scratch copies in my scratchpad, behind light-ok.

## Evidence

- athena run pf1-l3-close-f0c0eb1-20261025T025259Z: PASS-SUBSET, 16/16 at commit f0c0eb1d80e8, from summary.txt and run.log.
  It covers every checks.d line, including test_pre_ruling_walks, test_line_separators, test_walk_runner, test_auto_mode, test_steer_condition and test_isolation_denials_checker.
- Earlier findings 1, 2 and 5 are closed under rulings 1, 2 and 5:
  - the 25 pre-ruling walks keep their recorded harness-condition-violated lines (athena line 11 PASS);
  - the auto_mode departure text names both legs;
  - `_host_recorded_cuts` reads each row's `n`.
- Finding 4 is closed for claude-code under ruling 4, with one exception (finding 2 below).

## The four checks asked for

**1. Can an agent make a host record look as if it offers a tool or a steer switch it does not?**
- I found no road.
- `host_shown` and `steer_on` are filled only from the launch journals, from `_journal_gaps` (journals and the turn-stream file set beside the transcript) and from the stream inits.
- The journals and that file set are written by the driver on the host.
- The stream inits are the host's capture of stdout.
  An agent can reach them only by a child writing into the CLI's own stdout pipe.
  That is residual (a), and such an init raises harness-condition-violated by itself anyway.
- A delta that adds one tool the host shows and one it does not is still a mismatch for the second (`set(offered) <= host_shown`).
- The silent-turn switch does not set `steer_on`; only the steer switch does.
  That is right, because only the steer gates auto_mode.

**2. Is the cut-turn shortening used only when the host records the cut?**
- Yes.
  In check_take, `cut = _host_recorded_cuts(path)`: ledger rows ending timed-out or exiting 124, by `n`.
  The live C6 (claude_code_adapter cross_check) reads the turn records' `timed_out` or `exit_code` 124, which are driver data.
- An agent cannot forge a ledger cut, because exit 124 needs the real budget to fire.
- But how far it shortens is not bounded (finding 1).

**3. Does reading the three separators as text reopen a junk-line road?**
- Not in the checker.
- Every reader of the session file, the turn streams and the native stores that I traced splits on `\n` alone:
  - transcript_view.jsonl_lines;
  - claude_code_adapter `_records` and `_content_records`;
  - codex_native `_json_lines`;
  - study_paths_read and its siblings.
- A line made only of U+2028 or U+0085 is blank to every one of them (Python treats them as whitespace) and carries no record.
- A record prefixed with U+0085 fails `json.loads`.
  The checker counts it as a junk line (transcript-mismatch while the streams read), and the view refuses it.
- Two records joined by U+2028 are not JSON, and test_line_separators still refuses that.
- The graders' readers do not call `str.splitlines`.
  Its uses in round2.py serve fixture_walk only.
- The exception is outside the checker: the live Codex adapter (finding 2).

**4. Do the other lanes' tests this lane changed still assert what their owners meant?** See findings 3 and 4.
- test_auto_mode and test_steer_condition follow from ruling 2.
  test_steer_condition's mutant moves its anchor to the new `if count and steer_on:` line.

## Findings

### 1. MAJOR: in a turn the host records as cut, an agent can delete any tail of its session file, the whole turn included, and the comparison passes

- In `content_problems`, a cut turn's units are cut to `min(len(stream), len(sess))` on both sides, so only the common prefix is compared.
- Probe on t.two_turns(), with cut={2} on the last turn:
  - with turn 2's last two session records dropped, the uncut check refuses ("at item 2 ... the session file nothing"), and the cut check returns `[]`;
  - with turn 2's content emptied and only its operator line kept, the result is still `[]`.
- An agent that runs its turn past the budget (a real cut, which the take routes graded timed-out) can therefore remove its own last records from the file the graders read.
  It could remove, for example, a Read of the study's materials (study_paths_read reads transcript.jsonl), or the reply a words-graded reading scores.
  The edited transcript is then graded.
- That is the threat model's first line: an agent able to write files must not make an edited transcript pass.
- Ruling 3 says "compared only up to its last complete unit".
  A kill can only fall between two writes of the record in flight, so the allowance should be no wider than that record.
- One bound that keeps the ruling's purpose:
  - the session file may lack only the units of the stream's last record (one assistant message by its id, or one user tool_result record);
  - it may hold at most one record the stream lacks;
  - everything before that must be equal.
- c3a and c3b test only a gap of one record, so a bound like this keeps them green, and a "drop three records" witness would turn red.
- No real cut has been measured: no committed claude-code walk holds one.
  A forced-timeout stub take on athena would show the real gap before the freeze.

### 2. MINOR: residual (c) says "every reader splits on newline alone", but the live Codex adapter does not

- codex_adapter.py `read_stream` (line 138, `text.splitlines()`) and `_rollout_records` (line 233) still split on every Unicode line boundary.
- Inference, not verified on the pinned binary: Codex's serde_json, like Node, leaves U+2028, U+2029 and U+0085 raw inside strings.
- If so, an agent that prints one of them in a command's output splits a stream line in two.
  `read_stream` then raises StreamError ("line n of m is not JSON") on a line that is not the stream's last, so the live turn is refused.
  That reopens, on arm O, the one-character void road that ruling 4 closes for claude-code.
- No committed stream or native store holds any of the three characters (0 walks), so nothing measures it either way.
- Fix: split on `"\n"` in both places, as gemini_adapter already does (line 139, with its own comment saying why).
  Otherwise, narrow the residual's claim to the checker's readers.

### 3. MINOR: test_line_separators lost its check of the cross-check's separator refusal and its crash witness

- Before, `driver_problems` asserted that `cross_check` names a session file carrying a separator.
  A witness ("the cross-check crashes": `except StreamError` turned into `except KeyError`) proved that `cross_check` turns a StreamError from `_records` into a problem.
  Both used U+2028.
- The fold changed the assertion to "U+2028 is not refused" and dropped the witness.
- `cross_check` still has that road for the C0 separators (claude_code_adapter.py line 601-602, `_records` then `except StreamError`), but no test now drives it.
- The owner meant: a session file the driver cannot split is named, never crashed on.
- Keep both, using `"\x0b"`.
  The new JSON-legal assertions and the "refused again" mutant can stay beside them.

### 4. NIT: test_walk_runner's w-sep no longer witnesses check4_walk's line call

- The case existed to catch the d7107255 survivor: each later claude-code call, on its own, in check4_walk.
  With U+2028 read as text, it now witnesses the content call instead (expected "differs from the host-captured stream").
- The static AST check in test_line_separators (line 163) still shows that check4_walk calls transcript_line_problems, so the wiring is covered.
  A behavioural witness of that call's result is not.
- Using `"\x0b"` in the w-sep text would give both:
  - `[transcript-unreadable] ... line separator(s) U+000B` from the line call;
  - the record call's mismatch.

### 5. NIT: a claude-code cut take with a cut-short last session line re-runs, and residual (c) names that only for the native store

- `transcript_record_problems` excuses the last session line of a cut take.
  `transcript_line_problems` does not, so a genuinely cut-short line gives transcript-unreadable and a re-run.
- That matches ruling 3's w-g24 treatment.
  It also means an agent that overruns can append one junk line and have the take re-run.
- Residual (c) says this for "leaves its native store unreadable" (Codex, Gemini); add the claude-code form.
