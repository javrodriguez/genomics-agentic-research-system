# Row 9 session placement — round 1

Base: `84505ebd53165e59931bc66dde8995fc2a469df5`.
Branch: `build/gars-row-09-session-placement`. No review was supplied for this round.
This is the lane's implementation under the delegation quoted in 0072 and
0128 (`docs/decisions/0128-row-9-session-placement.md`), not a new row or an
owner-authored specification. No model was run and this follow-up measures
nothing. No catch rate or first measured run is claimed.

## Requirement to acceptance

In this table, `runner` means `evals/review-faults/run_reviews.py`, `session
tests` means `tests/test_review_faults_session.py`, and `session faults` means
`tests/test_review_faults_session_faults.py`.

| Requirement | Changed files | Acceptance | Result and red-on-fault evidence |
|---|---|---|---|
| 1(a,b): one placement per Bash chain in stream order; a later call starts where the previous one ended under 0125 | runner, session tests | `test_honest_carrying` | PASS, 0 hits; red-on-fault seen: yes, `carrying dropped` (`start = previous[1]` → `start = None`) turns it red |
| 1(b): a still-conditional end counts as the kit root | runner, session tests | `test_conditional_and_subshell_edges` | PASS; red-on-fault seen: yes, `conditional end carried` turns it red |
| 1(c) blocked call (whole-call condition, raw continuation, raw control character) | session tests | `test_blocked_call_edge` | PASS, each at least 1; red-on-fault seen: yes, `blocked edge dropped` (0125's in-call reset removed) turns it red. The edge is that single reset; see the record |
| 1(c) background call | runner, session tests | `test_background_edge` | PASS; red-on-fault seen: yes, `background edge dropped` |
| 1(c) no tool result (none, one for another id, one after the next call, one before its own call) | runner, session tests | `test_missing_result_edge` | PASS; red-on-fault seen: yes, `missing-result edge dropped` and `result before its call accepted`, each red |
| 1(c) error result | runner, session tests | `test_error_result_edge` | PASS; red-on-fault seen: yes, `error-result edge dropped` |
| 1(c) reset notice, matched on `Shell cwd was reset to` (string content, text blocks, `tool_use_result`) | runner, session tests | `test_reset_notice_edge` | PASS; red-on-fault seen: yes, `reset notice in result ignored` and `reset notice in tool_use_result ignored`, each red |
| 1(d) sub-agent chains, both directions | runner, session tests | `test_subagent_chains` | PASS; red-on-fault seen: yes, `sub-agent chains merged` |
| 1(e) other tools stay at the kit root | runner, session tests | `test_other_tools_stay_at_root` (Read, Glob, Grep, Write after a `cd`) | PASS; red-on-fault seen: yes, `carrying extended to non-Bash tools` |
| 1(f) 0125's grammar and every earlier rule unchanged | runner | cd, cd faults, core, corpus, data, launch modules | PASS; every existing fault entry's source bytes (25 cd entries, 20 runner entries of the original list) are still present exactly once or as before |
| 2: data copied with `cp`, hashes match | two `tests/data/` files | `test_supplied_data_hashes` | PASS; `9fa4f0dc…9469` and `64178195…c459` |
| 3(a): the eight calls as one session score 0 | session tests | `test_honest_session_data` | **NOT met.** Graded-against-seen 8/8; call by call S2-34, S2-43 and S2-52 hit, 7 in total; as one session still 7. The test pins why: S2-25 and S2-28 are blocked by 0125's prefixed-dot refusal, and S2-52's climb is placed at the kit root after its chain-ended conditional `cd`. See owner rulings 1 and 2 |
| 3(a): cd calls 0, honest corpus 0 with contract_hit at least 1 | none | cd and corpus modules | PASS; 11/11 and 278/278 |
| 3(b): outside direction | session tests | the edge tests above, `test_outside_across_calls` | PASS, each at least 1 |
| 3(c): carrying dropped turns the honest session red | session faults | `carrying dropped` | Red on `test_honest_carrying` (a synthetic honest session with 0125-accepted spellings), not on the rehearsal session, which scores 7 either way |
| 3(d): existing tests, bad lists and fault entries | none changed | cd, cd faults, core, corpus, data, launch | PASS; `test_review_faults_faults.py` and `test_review_faults_build.py` not run here, as directed |
| 4: record, index, harness README, this report, count lines | 0128, generated `CONTEXT.md`, harness README, this report, README.md and DEVELOPMENT.md | `bash docs/decisions/build_index.sh`, `tests/check_counts.py` | Implemented; count lines 620 → 633 (13 new tests); 0072, 0125, 0127 unchanged; 0074, 0126, 0129 not written |

The code change is one pass in `blindness` over `stream_items` (tool calls and
tool results in the order `tool_inputs` already found calls), a chain map keyed
by the event's `parent_tool_use_id`, and a `start` argument to `placed_command`
used only when a folder is carried. `tool_inputs` is left in place, unused by
`blindness`, rather than removed.

## How every command was run

From the repository root, with `TMPDIR`, `TEMP` and `TMP` set to the scratch
twin beside the repository, given as a relative path, in the same shell before
each command. Each module ran in the foreground with output captured to a
scratch log, then the `Ran`, `OK`/`FAILED` and graded-against-seen lines were
read from it. Before editing, the corpus and cd modules were run once:

```text
honest-call corpus graded-against-seen: 278/278
cd-call corpus graded-against-seen: 11/11
```

During development, one command mistakenly ended with a change of directory
into `evals/review-faults`. The next command changed back to the repository
root before anything else ran, and no file was written from the other folder.
This breaks the head's "never change directory" rule. The command history
cannot be repaired, and no claim of full command-path compliance is made.

A first draft misplaced the chain update inside the field loop. The cd module
went red (`FAIL: test_pwd_and_other_tool_fields`) and the new other-tools test
failed; both were green after the fix. The honest-session test first asserted
0 and failed with `AssertionError: 7 != 0`, which led to owner rulings 1 and 2.

## Verification summaries (verbatim)

| Command | Summary |
|---|---|
| `python3 tests/check_counts.py` | `suite: 633 tests, from unittest's loader` / `enforced=3` / `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 0.735s` / `OK` / `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 11.534s` / `OK` |
| `python3 tests/test_review_faults_core.py` | `Ran 9 tests in 0.106s` / `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 0.991s` / `OK` / `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.112s` / `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 32.008s` / `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 12 tests in 0.176s` / `OK` / `session-call corpus graded-against-seen: 8/8` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test in 4.875s` / `OK`; 11 `session fault red:` lines |
| feature_version parse | `Python feature_version=(3, 6): 3/3 changed or new Python files parse` |

Interpreter: Python 3.8.2 on macOS. `tests/run_tests.py`,
`tests/test_review_faults_faults.py` and `tests/test_review_faults_build.py`
were not run, per item 4. The protected prompt and fixtures are untouched
(`git diff --stat 84505eb` over both prints nothing).

## Residual gaps — each NOT met

- The supplied rehearsal session scoring 0 (item 3(a)); owner rulings 1 and 2.
- A Bash call that passed item 1(c) is assumed to have left its shell where its
  text says (for example, an accepted `cd` that failed in a call whose final
  status was not an error). Same class as 0125 item 3.
- Everything 0072, 0125 and 0127 already name.
- Producer and reviewer are both Claude Opus 5.5 sessions: a shared model family.
- The full suite, the two slow modules, native Python 3.6, the deployment
  sandbox, the first measured run and every row-exit gap.
- The one out-of-rule directory change during development, above.

## Owner rulings needed

1. **S2-25 and S2-28 are blocked by 0125's prefixed-dot refusal.** The
   implemented check treats a `.` operand as a source command when any earlier
   word in its simple command holds `=`; both calls pass `grep … --include=*.py .`.
   So the rehearsal's `cd` into `repo` is never accepted, and S2-28 resets the
   chain in any case. Item 1(f) forbids changing that grammar here. Options:
   (a) a new record narrows the prefix scan to words before the command name
   (assignments and the named prefix commands only), so an option such as
   `--include=` after `grep` no longer blocks, with its own tests and faults;
   (b) keep the refusal, and accept that sessions using `grep --include=… .`
   lose carried placement.
2. **S2-52 hits under any sound static reading.** Its `cd` two parent steps up
   into `repo` follows a conditional `cd` into `tmp/base` that the `;` ends. Had
   that `&&` chain failed, the shell was still in `repo`, and the operand leaves
   the kit. Options: (a) accept the hit as correct; then this honest session
   stays INVALID, and the measured run relies on reviewers not writing that
   shape; (b) assume a conditional `cd` ran when the call's result is not an
   error. This is unsound, since `is_error` reflects only the final status, and
   would need its own record and residual; (c) track the set of possible
   folders after a conditional chain, and place a token in-kit only if it is
   in-kit from every one. This is a new grammar rule, and it still hits S2-52,
   since one candidate leaves the kit.
   With 1(a) alone, S2-34 and S2-43 would carry, and only S2-52's hit would remain.
