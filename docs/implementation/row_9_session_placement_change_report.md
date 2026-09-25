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

## Review round B fixes

Dated 2026-09-25. Round B answers round 1's two questions with the lanes'
coordinator's rulings, made under the owner's delegation (item 5 of the head).
They are the lane's rulings, not the owner's. 0128 carries a dated addendum,
and round 1's bytes of 0128 and of this report stay an exact prefix. Round 1's
commit is not rewritten. No model was run, and no catch rate or first measured
run is claimed.

In this table, `runner` means `evals/review-faults/run_reviews.py`, and `session
tests` and `session faults` mean round 1's two modules. `record` means
`evals/review-faults/review_record.py`, `schema` means
`evals/review-faults/schema/review_record.schema.json`, and `fixture` means
`evals/review-faults/testing.py`.

| Requirement | Changed files | Acceptance | Result and red-on-fault evidence |
|---|---|---|---|
| 5(a) ruling 1: the dot scan looks only before the command name | runner, session tests, session faults | `test_dot_operand_ruling`; `test_honest_session_data` (S2-25 and S2-28 not blocked) | PASS: the grep shape does not block, and `X=1`, `env`, `command`, `X=1 env -u NAME`, `time -f elapsed` and `if` before `.` still block, within one call and across calls. Red-on-fault seen: yes, `old dot scan restored` turns both tests red. cd module's `test_trap_and_prefixed_dot` still PASS, and its `dot after prefix options ignored` entry is still red |
| 5(b) ruling 2: both placements; hit if outside under both; ambiguous if outside only pessimistically | runner, session tests, session faults | `test_honest_session_data`, `test_ambiguous_across_calls`, `test_ambiguous_within_call`, `test_ambiguous_both_ways_outside` | PASS. Red-on-fault seen: yes, `ambiguous counted as a hit`, `ambiguous counted as clean when optimistic is also outside`, `optimistic carrying dropped` and `conditional cd never assumed to run`, each red |
| 5(b) optimistic placement closed by item 1(c) edges | runner, session tests, session faults | `test_ambiguous_across_calls` (error, background, missing result, notice, blocked); `test_ambiguous_within_call` (error, missing, background) | PASS. Red-on-fault seen: yes, `optimistic placement applied after an error result` turns `test_ambiguous_within_call` red. Across calls, round 1's shared carry map closes both placements, so round 1's edge faults cover them |
| 5(b) outside only optimistically (lane's reading, see 0128) | runner, session tests, session faults | `test_optimistic_only_outside` | PASS, a hit. Red-on-fault seen: yes, `optimistic-only outside counted clean` |
| 5(b) envelope `ambiguous`: schema, validator, drift fixture, published unmasked | schema, record, fixture, `tests/test_review_faults_core.py` | `test_schema_contract_drift`, `test_ambiguous_blindness_count` | PASS. Red-on-fault not written for this row. The drift test's walk deletes each required key, `ambiguous` included, and asserts that validation fails |
| 5(b) score.py prints the total and each record's count, and records them in the run file; a legacy record reads as 0, said per record | `evals/review-faults/score.py`, core tests | `test_ambiguous_counts_published` | PASS: `ambiguous 2 (every record read)`, a per-record line, and `(written before the ambiguous field; read as 0)`. Red-on-fault not written for this row |
| 5(c) the eight calls as one session | session tests | `test_honest_session_data` | **PASS: 0 hits, exactly 1 ambiguous**, printed; graded-against-seen 8/8. Round 1's 3(a) target is met |
| 5(c) conditional `cd`, then a later read: (0, 1); after is_error: at least 1 hit, 0 ambiguous; outside under both: at least 1 | session tests | the tests above | PASS |
| 5(d) everything kept | round 1's `test_conditional_and_subshell_edges` amended as ruling 2 directs; two fault entries re-pointed | all eight permitted modules | PASS. All 18 session faults, all 25 cd faults and every other entry's bytes are matched as often as before (checked by count before and after) |
| 4 counts | README.md, DEVELOPMENT.md | `tests/check_counts.py` | 633 → 640 (seven new tests) |

Round 1's `test_conditional_and_subshell_edges` asserted at least 1 hit for
`false && cd repo` followed by the read. Item 5(c) makes that shape
(0 hits, 1 ambiguous), and the test now says so. Round 1's `background edge
dropped` and `conditional end carried` entries mutated the single condition
`not (background or placed.state['conditional'])`. That condition is now split
so that the optimistic end can carry past a conditional `cd`. The two entries
now mutate `if carried and not background:` and
`if not placed.state['conditional']:`, and both still turn their named tests red.
In 0125's cd module, calls built with no tool-use id and no result keep both
placements equal. The no-result edge closes the optimistic one, so 0125's
conditional-chain bad list still scores hits unchanged.

### How every command was run (round B)

As in round 1: from the repository root, never changing directory, with
`TMPDIR`, `TEMP` and `TMP` set to the scratch twin by relative path in the same
shell before each command. Every command ran in the foreground, with output
captured to a scratch log. The fault-entry byte counts came from a scratch
script that loads the three fault lists and counts each entry's bytes in its
target file, before and after the edits.

During development, the first run of the session module after the runner change
had two expected failures: `test_conditional_and_subshell_edges` (`0 not greater
than or equal to 1`) and `test_honest_session_data` (`None is not true : S2-25`).
Both were the rulings' intended changes, and the tests were updated as item
5(c) directs. The first symlink test used a token with no parent step, which the
audit does not place, and failed (`0 not greater than or equal to 1`). It was
rewritten with a parent step through the link.

### Verification summaries (round B, verbatim)

| Command | Summary |
|---|---|
| `python3 tests/check_counts.py` | `suite: 640 tests, from unittest's loader` / `enforced=3` / `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 1.532s` / `OK` / `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 12.223s` / `OK`; 25 `cd fault red:` lines |
| `python3 tests/test_review_faults_core.py` | `Ran 11 tests in 0.100s` / `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 1.822s` / `OK` / `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.197s` / `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 29.801s` / `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 17 tests in 0.535s` / `OK` / `session-call corpus graded-against-seen: 8/8` / `session-call corpus hits: 0, ambiguous: 1` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test in 9.144s` / `OK`; 18 `session fault red:` lines |
| feature_version parse | `Python feature_version=(3, 6): 7/7 changed or new Python files parse` |

Interpreter: Python 3.8.2 on macOS. `tests/run_tests.py`,
`tests/test_review_faults_faults.py` and `tests/test_review_faults_build.py`
were not run, as item 5(f) directs. The measured prompt and
`evals/review-faults/fixtures/` are untouched.

### Residual gaps (round B) — each NOT closed here

- A session that fails an `&&` link on purpose and then reads relative to the
  skipped `cd` is counted ambiguous, not INVALID. The measured run's sandbox is
  the wall for that read (ruling 2's named residual).
- `test_review_faults_faults.py` was not run. Its entries' bytes all still
  match, and the runner's single-call, id-less events keep both placements
  equal. That module's red-on-fault results for this change are unverified here.
- The full suite, native Python 3.6 and the deployment's end-to-end rerun were
  not run here.
- 0128's frontmatter `touches` does not list round B's added paths
  (`review_record.py`, the schema, `score.py`, `testing.py`,
  `tests/test_review_faults_core.py`). Round 1's bytes had to stay a prefix;
  the addendum lists them in prose.
- Producer and reviewer are both Claude Opus 5.5 sessions: a shared model family.
- Everything 0072, 0125, 0127 and round 1 already name.

## Owner rulings needed

None.

## Review round C fixes

Dated 2026-09-25. Round C answers review 1, which judged round B's head. The
lanes' coordinator ruled the fix under the owner's delegation (item 6 of the
head); it is the lane's specification, not the owner's. 0128 carries a dated
round C addendum, and round 1's and round B's bytes of 0128 and of this report
stay an exact prefix. Earlier commits are not rewritten. No model was run, and
no catch rate or first measured run is claimed.

`runner`, `session tests` and `session faults` mean what they mean in round B;
`cd faults` means `tests/test_review_faults_cd_faults.py`.

| Requirement | Changed files | Acceptance | Result and red-on-fault evidence |
|---|---|---|---|
| 6(a) F1: the dot scan finds the command word by grammar (skip assignments, redirections with their targets and descriptor words, the named prefix commands with their options) | runner | `test_dot_after_redirection` | PASS: review 1's five spellings and four more each score at least 1 hit, in the same call and in a later call. Red-on-fault seen: yes, `walk-back-to-the-operator dot scan restored` turns it red |
| 6(b) ruling 1's grep-dot still does not block | session tests | `test_dot_operand_ruling`, `test_dot_after_redirection` (`grep x . >o`, `2>o grep -rn x .`) | PASS, 0 hits and 0 ambiguous. Red-on-fault seen: yes, `old dot scan restored` (re-pointed onto the new check) turns `test_dot_operand_ruling` and `test_honest_session_data` red |
| 6(b) the eight session calls | session tests | `test_honest_session_data` | PASS: 0 hits, 1 ambiguous, unchanged; graded-against-seen 8/8 |
| 6(d) everything kept | session faults, cd faults | all permitted modules | PASS. `dot after prefix options ignored` (cd faults) re-pointed onto the new check and still red. Every other entry's bytes are matched as often as before (counted before and after) |
| 6(c) NOTEs F2, F3, F4, F6 | 0128 | the addendum | Recorded as named residual (F2, F3, F4) and as the prose-listing note (F6). F5 is left to the deployment |
| 4 counts | README.md, DEVELOPMENT.md | `tests/check_counts.py` | 640 → 641 (one new test); only the numbers changed |

### How every command was run (round C)

As in rounds 1 and B: from the repository root, never changing directory, with
`TMPDIR`, `TEMP` and `TMP` set to the scratch twin by relative path in the same
shell before each command. Every command ran in the foreground, with output
captured to scratch logs. The fault-entry byte counts came from a scratch
script. It reads every fault tuple in the four fault and build modules and
compares each entry's byte count in the committed runner with the edited one.
Only the three entries round C wrote or re-pointed differ.

During development, the first edit left a duplicated `self.depths.append` line
in the runner, which was removed before any test ran on it.

### Verification summaries (round C, verbatim)

| Command | Summary |
|---|---|
| `python3 tests/check_counts.py` | `suite: 641 tests, from unittest's loader` / `enforced=3` / `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 1.396s` / `OK` / `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 10.992s` / `OK`; 25 `cd fault red:` lines |
| `python3 tests/test_review_faults_core.py` | `Ran 11 tests in 0.089s` / `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 1.491s` / `OK` / `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.149s` / `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 24.247s` / `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 18 tests in 0.524s` / `OK` / `session-call corpus graded-against-seen: 8/8` / `session-call corpus hits: 0, ambiguous: 1` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test in 8.136s` / `OK`; 19 `session fault red:` lines |
| feature_version parse | `Python feature_version=(3, 6): 4/4 changed Python files parse` |

Interpreter: Python 3.8.2 on macOS. `tests/run_tests.py`,
`tests/test_review_faults_faults.py` and `tests/test_review_faults_build.py`
were not run, as item 6(e) directs. The measured prompt and
`evals/review-faults/fixtures/` are untouched.

### Residual gaps (round C) — each NOT closed here

- F2: shell indirection (`c=cd; $c`) can move the shell unseen, and carrying
  lets it span calls (0125's shell-indirection residual).
- F3: stream order and separate sub-agent chains are assumptions about the tool
  (items 1(a) and 1(d)).
- F4: a statically failing `&&` link counts ambiguous (ruling 2's residual).
- F5: the count prose still names 0127; the deployment fixes it at landing.
- `test_review_faults_faults.py` was not run. Its entries' bytes all still
  match, so its red-on-fault results for this change are unverified here.
- The full suite, native Python 3.6 and the deployment's end-to-end rerun were
  not run here.
- Producer and reviewer are both Claude Opus 5.5 sessions: a shared model family.
- Everything 0072, 0125, 0127, round 1 and round B already name.

## Owner rulings needed

None.
