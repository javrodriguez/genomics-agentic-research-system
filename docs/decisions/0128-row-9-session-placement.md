---
date: 2026-09-25
status: standing
kind: defect
touches:
  - evals/review-faults/run_reviews.py
  - evals/review-faults/README.md
  - tests/test_review_faults_session.py
  - tests/test_review_faults_session_faults.py
  - tests/data/review_faults_session_calls.jsonl
  - tests/data/review_faults_session_calls_README.md
  - docs/implementation/row_9_session_placement_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - honest session that changed into repo in one Bash call scores hits on later parent-step paths
  - parent-step tokens in a Bash call with no cd are placed against the kit root although the shell kept its folder
---
# Row 9 blindness audit carries Bash placement across a session's calls

## Context

This is a narrow follow-up to row 9 at `84505eb`, whose harness contract is
[0072](0072-row-9-review-fault-harness-code-half.md), whose command-field
placement is [0125](0125-row-9-cd-aware-placement.md) and whose data operands
are [0127](0127-row-9-data-operands.md). It changes only where the blindness
audit in `evals/review-faults/run_reviews.py` places a relative token at the
start of a Bash call.

0125 rested on a factual premise: every Bash call starts at the kit root, and
"no placement is ever carried from one call to the next". **That premise is
false for the reviewer's tool.** Claude Code's Bash tool keeps its working
directory from one call to the next. The deployment's end-to-end rehearsal at
`84505eb` shows it: one call changed into the kit's `repo` folder, and the next
call, with no `cd` of its own, ran a successful `sed -n 235,260p` of a path under
`gars/_system/wrappers/` that exists only under `repo/`. Three later calls wrote
a parent-step path to `tmp` (the kit's own tmp folder, one step up from
`repo/`) with no `cd` of their own; placed against the kit root, they scored
7 hits and made an honest session INVALID. In the measured run an INVALID record is final.

0072 records the owner's delegation on 23 September 2026, quoted exactly:

> I delegate to you all the decisions necssary to finish row9, use your best judgement. Only ask me for critical choices

Everything below is **THE LANE'S SPECIFICATION, UNDER THE OWNER'S DELEGATION**.
It attributes no words or choices in it to the owner. The lanes' coordinator
assigned record number 0128 under the same delegation. Records 0072, 0125 and
0127 are append-only and are not edited; 0074, 0126 and 0129 are not written.

## Decision

Item 1 corrects 0125's premise. The audit models what the tool does: the
working directory a Bash call ends in is where the next Bash call starts, when
the audit can prove it, and the kit root, the fail-closed placement, whenever it
cannot.

1. (a) The audit keeps one placement folder per chain of Bash calls, taken in
   stream order. The first Bash call of a chain starts at the kit root.
   (b) Each later Bash call starts at the placement in force at the end of the
   previous Bash call of the same chain, as 0125's rules leave it: its accepted
   `cd`s, its resets and its `&&` limit. A conditional placement that its chain
   ended has already returned to the kit root, and a placement still
   conditional at the end of the call counts as the kit root for the next call.
   (c) Fail-closed edges: the next call starts at the kit root instead when the
   previous Bash call
   - was blocked by any of 0125's whole-call conditions or its raw-text guard
     (item 4, item 8): the audit cannot say where such a call's shell went.
     0125 already places every word of a blocked call, including its end, at
     the kit root, and that one reset is the edge; a carried start does not
     survive it;
   - ran in the background (`run_in_background` present with any value other
     than `false`): its shell may still be running when the next call starts;
   - has no tool result in the stream **before the next Bash call of its
     chain**: without a result the audit cannot know the call finished. A
     result that precedes its own call, or names an unseen call, does not
     count;
   - has a tool result marked as an error (`is_error` present with any value
     other than `false`): the call may have stopped before or after its `cd`;
   - has a tool result whose text says the tool reset its working directory.
     The matched text is the stable prefix `Shell cwd was reset to`, as a
     substring of any string in the `tool_result` block or in the result
     event's `tool_use_result` value (its stdout and stderr). Matching a
     substring anywhere over-resets, which is fail-closed.
   (d) Calls made by a sub-agent (the stream event carries a
   `parent_tool_use_id`) form their own chain, one per parent id, starting at
   the kit root; they never move the main chain's placement, and the main chain
   never moves theirs.
   (e) Only Bash calls carry a working directory, and only a Bash call's own
   top-level `command` field starts at the carried folder. Every other tool's
   relative paths (Read, Glob, Grep, Write, Edit and the rest) stay placed
   against the kit root, and other tools' calls neither move nor break a Bash
   chain.
   (f) Everything else 0072, 0125 and 0127 specify is unchanged, including
   0125's acceptance grammar for a `cd`, which is the only way a placement ever
   moves deeper than the kit root.

Two readings of item 1(c) are this record's, both stricter than a looser
reading: "no tool result" means none before the next Bash call of the chain,
and background, error and notice checks treat any value other than an explicit
`false` (or absence) as the edge. Neither adds a rule beyond item 1.

**Named residual:** the audit assumes a Bash call that passed item 1(c) left
its shell where its text says. A `cd` the grammar accepted but that failed at
run time, in a call whose final status was not an error, carries a folder the
shell never reached. This is the same text-versus-execution class as 0125
item 3's named residual; the sandbox (0072 item 20(a)) remains the enforcement
wall.

**The rehearsal session still scores 7.** With item 1 in place and 0125's
grammar unchanged, as item 1(f) requires, the eight supplied calls scored as one
session still score 7 hits, the same as call by call:

- S2-25 (the `cd` into `repo`) and S2-28 are blocked by 0125's prefixed-dot
  refusal (round 3, "a dot following prefix words and their options or option
  operands is conservatively treated as a source command"): the implemented
  check counts any earlier word holding `=` in the simple command, and both
  calls pass `grep … --include=*.py .`. So S2-25's `cd` is never accepted, and
  S2-28 would reset the chain even if it were.
- S2-52's `cd` two parent steps up and into `repo` follows a conditional `cd`
  into `tmp/base` (one parent step up, after `&&`) and a `;`. 0125's chain
  limit returns the placement to the kit root at that `;`, so the operand is
  placed outside the kit. Statically that hit is sound: had the `&&` chain
  failed, the shell was still in `repo` and the operand does leave the kit.

The head's acceptance that this session scores 0 is therefore **NOT met**.
Meeting it needs a change to 0125's grammar or a new assumption, which item
1(f) and the lane's rules forbid; the options are recorded as owner rulings in
the change report.

**How this change was built.** A headless Claude Opus 5.5 session produced it,
and a separate fresh Claude Opus 5.5 session reviews it. Producer and reviewer
therefore share a model family, a cost this record names as residual.

## What this does not close

Covered: an honest session that changes directory inside its kit once, by a
spelling 0125's grammar accepts, and uses parent-step paths in later calls is
not made INVALID (`test_honest_carrying`). An outside read by any spelling
0072, 0125 and 0127 name still turns INVALID, including across calls and after
every fail-closed edge.

Not covered, each **NOT met** here:

- The supplied rehearsal session scoring 0 (above; owner rulings 1 and 2 in the
  change report).
- The residual above: a call that passed item 1(c) is assumed to have left its
  shell where its text says.
- Everything 0072, 0125 and 0127 already name, including shell indirection,
  interpreter program text, unparsed constructs, failed accepted `cd` and
  audit-time symlink resolution.
- The shared model family of this change's producer and reviewer.
- The full suite (`tests/run_tests.py`), `tests/test_review_faults_faults.py`
  and `tests/test_review_faults_build.py` (run separately by the deployment),
  native Python 3.6, the deployment sandbox, the first measured run and every
  row-exit gap. No model is run and no catch rate is claimed.

## Test

Acceptance is stdlib unittest in `tests/test_review_faults_session.py`,
collected by `tests/run_tests.py`, with every outside path built at run time;
no shell text is executed, no model or network is used. The supplied calls and
README were copied with `cp` and hash as supplied
(`9fa4f0dc…9469`, `64178195…c459`), pinned by `test_supplied_data_hashes`.

- `test_honest_session_data`: the eight calls, built in order each with its
  result, as one session: graded-against-seen 8/8; call by call S2-34, S2-43
  and S2-52 hit, 7 in total; as one session no more than that; and the three
  0125 refusals above are pinned (S2-25 and S2-28 blocked, S2-52's climb placed
  at the kit root).
- `test_honest_carrying`: `cd repo` then a parent-step path to `tmp` in later calls, across an
  intervening Bash and Read call, and the rehearsal's shape with accepted
  spellings, score 0.
- Outside direction, each at least 1: `test_outside_across_calls` (a climb above
  the kit after a `cd` into repo, and a rejected later `cd`);
  `test_blocked_call_edge`, `test_background_edge`, `test_missing_result_edge`,
  `test_error_result_edge`, `test_reset_notice_edge` (one per edge);
  `test_conditional_and_subshell_edges` (`false && cd repo`, a subshell `cd`,
  a nested-shell `cd`); `test_subagent_chains` (both directions and two
  sub-agents); `test_other_tools_stay_at_root` (Read, Glob, Grep, Write).

Red-on-fault, in the cd-fault list shape, in
`tests/test_review_faults_session_faults.py`: eleven disposable mutations each
pass an unfaulted control and then turn their named test red — carrying
dropped (`test_honest_carrying`), each edge dropped in turn (blocked,
background, missing result, result before its call, error, notice in the result
block, notice in `tool_use_result`, still-conditional end), sub-agent chains
merged, and carrying extended to non-Bash tools. Carrying dropped cannot turn
the rehearsal session red, since it scores 7 either way; its witness is the
synthetic honest session. Every existing fault entry's source bytes remain
present.

Results on the build host (Python 3.8.2, macOS; scratch outside the checkout):

| Command | Result |
|---|---|
| `python3 tests/check_counts.py` | `suite: 633 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 0.735s`; `OK`; `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 11.534s`; `OK` |
| `python3 tests/test_review_faults_core.py` | `Ran 9 tests in 0.106s`; `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 0.991s`; `OK`; `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.112s`; `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 32.008s`; `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 12 tests in 0.176s`; `OK`; `session-call corpus graded-against-seen: 8/8` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test in 4.875s`; `OK`; eleven `session fault red:` lines |

`Python feature_version=(3, 6): 3/3 changed or new Python files parse`.
`tests/run_tests.py`, `tests/test_review_faults_faults.py` and
`tests/test_review_faults_build.py` were not run here, as the head directs.
Details are in `docs/implementation/row_9_session_placement_change_report.md`.

## Status

Standing lane specification and implementation record, pending the separate
review named above. Item 1 is implemented; the rehearsal acceptance is NOT met
and waits on the owner rulings named in the change report. This producer does
not approve or merge its own work, and this follow-up measures nothing.

## Date

2026-09-25

## Addendum 2026-09-25 — round B: the lane's rulings on round 1's two questions

Round 1 stopped with the rehearsal target not met under 0125's unchanged
grammar and asked two questions. **The lanes' coordinator ruled both under the
owner's delegation (item 5 of the head, 25 Sep 2026). What follows is the
lane's specification and the lane's rulings, under that delegation; none of it
is attributed to the owner.** It amends item 1 and item 3 where they differ.
The frontmatter above is left as round 1 wrote it, since round 1's bytes stay
an exact prefix of this file. Round B also touches
`evals/review-faults/review_record.py`,
`evals/review-faults/schema/review_record.schema.json`,
`evals/review-faults/score.py`, `evals/review-faults/testing.py` and
`tests/test_review_faults_core.py`.

### Ruling 1 (the lane's ruling, option (a)): the dot scan looks before the command name

This amends 0125's grammar. A `.` is a dot command only at the start of a simple
command or when every word before it in that simple command is an assignment
(`NAME=`, `NAME+=`, `NAME[…]=`), one of the named prefix commands (`builtin`,
`command`, `exec`, `time`, `env`, `coproc`, `nohup`, `!`), an option of a named
prefix command already seen (with the value word of `env -u/-C/-S`, `exec -a`
and `time -o/-f` and their long forms), or a reserved word that opens a
command (`if`, `then`, `elif`, `else`, `while`, `until`, `do`, `{`). The first
other word is the command name, and a `.` after it is that command's operand:
`grep -rn x --include=*.py .` no longer blocks the call. `X=1 . file`,
`env . file`, `command . file`, `X=1 env -u NAME . file`,
`time -f elapsed . file` and `if . file` still block. The option-skipping is
the lane's reading of "the named prefix commands": their options are not a
command name. It leaves the old scan's verdict on every shape the cd tests pin.

### Ruling 2 (the lane's ruling, option (d)): ambiguous, published

A `cd` joined by `&&` may not have run. The audit now places every relative
token of every chain twice.

- **Pessimistic:** round 1's rule as it stands. A conditional `cd`'s placement
  returns to the kit root at its chain's end and counts as the kit root for the
  next Bash call.
- **Optimistic:** an accepted `cd` joined by `&&` ran. The call's placement
  never becomes conditional, so it survives its chain's end and carries to the
  next call. It uses every other rule unchanged: 0125's grammar with ruling 1,
  item 1 (c)-(f), and 0127's data contexts. A `cd` that 0125 rejects resets
  both placements to the kit root.
- **Fail-closed edges.** The next call starts at the kit root in both
  placements after any edge of item 1 (c), as in round 1. A call that itself
  hit an edge (a background call; its result missing, an error, or carrying the
  reset notice) keeps its own `&&` `cd`s conditional in the optimistic
  placement too, since "unless its call hit any fail-closed edge". The
  optimistic start it inherited from earlier calls is kept, because those calls
  passed their edges. A result is known only when the stream has been read, so
  each call's tokens are judged at the end of the stream. A blocked call is
  already at the kit root in both placements.

For each token:

| Pessimistic | Optimistic | Counted |
|---|---|---|
| outside | outside | hit (the record INVALID, as today) |
| outside | inside | `ambiguous`, not a hit |
| inside | outside | hit |
| inside | inside | clean |

The third row is the lane's reading, because the ruling names no exemption for
it and rule 1 of the round forbids a widened one. It arises only through a
symlink that the optimistic folder reaches and the kit root does not. Before
round B it was clean. It is now a hit, since the `cd` may have run.

The envelope's blindness object gains an integer `ambiguous` beside `calls` and
`hits`. It is required by the schema, so the contract-drift test's rule that
every object requires exactly its properties still holds. It is checked by the
validator and carried in the drift fixture (`testing.record`).
`review_record.read_ambiguous` reads a record written before the field existed
as `ambiguous` 0, without changing the stored record, and `invalid_reasons`
judges that completed copy. A non-zero `ambiguous` never makes a record
INVALID. A negative or non-integer one fails validation. `score.py` records
`ambiguous` and `ambiguous_absent` on every attempt in the run file, and the
total over every record read as the result's `ambiguous`. None of these is
masked, since masking touches only strings and identity keys. `print_score`
prints `ambiguous N (every record read)` and one
`<case> attempt <n> ambiguous <k>` line per record. It adds
`(written before the ambiguous field; read as 0)` for a record that lacked it.

### What round B does not close

- **Named residual.** A session that makes an `&&` link fail on purpose, and
  then reads relative to the skipped `cd`, is counted ambiguous, not INVALID.
  The measured run's sandbox is the wall for that read. The audit never turns
  "cannot know" into "clean": the ambiguity stays visible in every record and
  in the published results.
- The call-level assumption of item 4's residual line stands for both
  placements. An `is_error` false result is taken as a call that passed its
  edges, although it reflects only the final status.
- The ruling-1 prefix list is closed. A prefix command outside it (for example
  `sudo`, `timeout`, `nice`) followed by `.` is not treated as a dot command,
  as under the old scan.
- Everything 0072, 0125, 0127 and round 1 already name. Producer and reviewer
  are both Claude Opus 5.5 sessions (this round's producer is a headless
  session; its reviewer is a separate fresh session), a shared model family.

### Test (round B)

- `test_honest_session_data`: the eight calls as one session score **0 hits and
  exactly 1 ambiguous**, printed as `session-call corpus hits: 0, ambiguous: 1`,
  with graded-against-seen 8/8. The ambiguous token is S2-52's two-step climb
  into `repo` after its chain-ended conditional `cd` into `tmp/base`: at the
  kit root pessimistically, and at `tmp/base` optimistically. S2-25 and S2-28
  are no longer blocked. Call by call from the kit root, the three calls still
  score 7.
- `test_dot_operand_ruling`: the grep shape does not block, within one call and
  across calls; six prefixed spellings still block, within and across calls.
- `test_ambiguous_across_calls`: a conditional `cd` into repo, then a later
  parent-step read inside the kit only if it ran, gives (0 hits, 1 ambiguous),
  also across an intervening call. The same read after the same `cd` marked
  is_error gives at least 1 hit and 0 ambiguous. The background, missing-result,
  reset-notice and blocked edges each give at least 1 hit, and a sub-agent read
  after a main-chain conditional `cd` also gives at least 1.
- `test_ambiguous_within_call`: the same shape inside one call gives (0, 1). With
  an error result, no result, or a background call it gives (1, 0).
- `test_ambiguous_both_ways_outside`: a read outside under both placements after
  a conditional `cd` is a hit with 0 ambiguous. This holds across calls and
  within one call, and for an absolute path too.
- `test_optimistic_only_outside`: a parent-step path through a symlink that only
  the optimistic folder reaches is a hit.
- Round 1's `test_conditional_and_subshell_edges` now asserts (0 hits, 1
  ambiguous) for `false && cd repo`, as ruling 2 amends item 3(b). Its subshell
  and nested-shell entries still hit. `test_honest_carrying` also asserts 0
  ambiguous.
- `ContractTests.test_ambiguous_blindness_count` and
  `ScoreTests.test_ambiguous_counts_published` cover the envelope, legacy
  records, the run file and the printed lines.

Red-on-fault, in `tests/test_review_faults_session_faults.py`: 18 entries, each
red. Round 1's eleven are kept. Two of them, `background edge dropped` and
`conditional end carried`, now mutate the lines that replaced round 1's shared
condition. Seven are new:

- `old dot scan restored`, red on `test_dot_operand_ruling` and
  `test_honest_session_data`;
- `ambiguous counted as a hit`, red on the honest session;
- `ambiguous counted as clean when optimistic is also outside`;
- `optimistic placement applied after an error result`, red on
  `test_ambiguous_within_call`;
- `optimistic-only outside counted clean`;
- `optimistic carrying dropped`;
- `conditional cd never assumed to run`.

Every other fault entry's source bytes (the 25 cd entries and the original
list's runner entries) match the same number of times as before round B. This
was checked by counting each entry's bytes before and after.

Results on the build host (Python 3.8.2, macOS; scratch outside the checkout):

| Command | Result |
|---|---|
| `python3 tests/check_counts.py` | `suite: 640 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 1.532s`; `OK`; `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 12.223s`; `OK`; 25 `cd fault red:` lines |
| `python3 tests/test_review_faults_core.py` | `Ran 11 tests in 0.100s`; `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 1.822s`; `OK`; `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.197s`; `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 29.801s`; `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 17 tests in 0.535s`; `OK`; `session-call corpus graded-against-seen: 8/8`; `session-call corpus hits: 0, ambiguous: 1` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test in 9.144s`; `OK`; 18 `session fault red:` lines |

`Python feature_version=(3, 6): 7/7 changed or new Python files parse`.
`tests/run_tests.py`, `tests/test_review_faults_faults.py` and
`tests/test_review_faults_build.py` were not run, as the head directs.

### Status (round B)

Rulings 1 and 2 are implemented, and the rehearsal acceptance is met: 0 hits and
1 ambiguous. The work waits on the separate review. This producer does not
approve or merge its own work, and this follow-up measures nothing.

## Owner rulings needed

None.

## Addendum 2026-09-25 — round C: the command word by grammar (review 1)

Review 1 judged round B's head and found one MAJOR (F1) and five NOTEs. **The
lanes' coordinator ruled the fix under the owner's delegation (item 6 of the
head, 25 Sep 2026). What follows is the lane's specification, under that
delegation; none of it is attributed to the owner.** It amends 0125's
dot-command rule and round B's ruling 1 where they differ. Round 1's and round
B's bytes of this file stay an exact prefix. Round C touches only
`evals/review-faults/run_reviews.py`, `tests/test_review_faults_session.py`,
`tests/test_review_faults_session_faults.py`,
`tests/test_review_faults_cd_faults.py`, the count lines of `README.md` and
`DEVELOPMENT.md`, this file and the change report.

### The fix (the lane's specification): the command word is found by shell grammar

Round B's scan walked back from a `.` to the nearest operator word. A
redirection operator is an operator word, so `>o . ./f` left `o` as the
apparent command name and the `.` as its operand, although bash sources the
file in the current shell. A sourced `cd` could then move the shell while the
audit kept carrying the deeper folder, so an outside read in a later call
scored 0 hits and 0 ambiguous. Within one call the gap was already 0125's;
carrying made it span calls.

The dot scan now walks each simple command forward. It starts after the
preceding separator (`;`, `&`, `&&`, `|`, `||`, `|&`, a newline, `(` or `)`,
including when one is merged with a redirection into one operator word, such as
`;>`). It then skips:

- variable assignments (`NAME=`, `NAME+=`, `NAME[…]=`);
- redirections together with their targets: every operator word that ends in a
  redirection (`<`, `>`, `>>`, `<<`, `<<<`, `<>`, `>|`, `>&`, `<&`, `&>`,
  `&>>`) takes the next word as its target, and a file-descriptor word (digits,
  or `{name}`) directly before a redirection is skipped with it;
- the named prefix commands (`builtin`, `command`, `exec`, `time`, `env`,
  `coproc`, `nohup`, `!`) with their options, and the value word of
  `env -u/-C/-S`, `exec -a` and `time -o/-f` and their long forms;
- the reserved words that open a command (`if`, `then`, `elif`, `else`,
  `while`, `until`, `do`, `{`).

The first word left is the command word. A `.` there is a dot command, and it
blocks placement for the call as 0125 requires; `source` blocks anywhere, as
before. A `.` anywhere else is an operand, so ruling 1 stands:
`grep -rn x --include=*.py .`, `grep x . >o` and `2>o grep -rn x .` do not
block. A digit word separated by a space from a following redirection is also
skipped as a descriptor. That reading is wrong in bash, where the digit word is
the command word, but it only blocks more calls, so it fails closed.

### Review 1's NOTEs

- **F2, shell indirection across calls.** After `cd repo`, a call such as
  `c=cd; $c` with a parent step moves the shell up unseen, and carrying lets a
  later read score 0. This is 0125's named shell-indirection residual. Carrying
  (item 1 (b)) now lets it span calls. It is named residual here, not closed.
- **F3, stream order and separate sub-agent chains.** Item 1 (a) places a
  chain's Bash calls in stream order, and item 1 (d) gives each sub-agent its
  own chain. Both are assumptions about the tool. If the tool ran parallel Bash
  calls out of stream order, or shared one shell between a sub-agent and the
  main chain, an outside read could score 0. Named residual, tied to items
  1 (a) and 1 (d).
- **F4, a statically failing `&&` link.** `false && cd repo; true` followed by
  a read outside the kit counts ambiguous, not a hit. This is exactly ruling 2's
  named residual; the measured run's sandbox is the wall for that read.
- **F5, the count prose.** The deployment fixes it at landing. Round C changes
  only the numbers that `tests/check_counts.py` enforces.
- **F6, the index entry.** Round B's added files
  (`evals/review-faults/review_record.py`, its schema, `score.py`,
  `testing.py` and `tests/test_review_faults_core.py`) are listed in round B's
  addendum in prose because the frontmatter is round 1's bytes, which stay an
  exact prefix of this file. So the regenerated `CONTEXT.md` row does not name
  them.

### What round C does not close

- F2, F3 and F4 above, as named.
- A prefix command outside the closed list (for example `sudo`, `timeout`,
  `nice`) followed by `.` is still not a dot command, as under rounds 1 and B.
- Everything 0072, 0125, 0127, round 1 and round B already name. Producer and
  reviewer are both Claude Opus 5.5 sessions (this round's producer is a
  headless session; its reviewer is a separate fresh session), a shared model
  family.

### Test (round C)

New: `test_dot_after_redirection` in `tests/test_review_faults_session.py`.
Review 1's five spellings (`>o . ./f`, `<i . ./f`, `2>&1 . ./f`,
`X=1 2>o . ./f`, `>o command . ./f`), plus `&>o . ./f`, `2>>o . ./f`,
`{fd}>o . ./f` and `true;>o . ./f`, each score at least 1 hit when a parent-step
read that is inside the kit only if placement carried follows in the same call,
in the same call after a `cd` into `repo`, or in a later call. The grep shapes
above score 0 hits and 0 ambiguous. The eight session calls still score 0 hits
and exactly 1 ambiguous.

Faults:

- new, `walk-back-to-the-operator dot scan restored`: every operator word ends
  the prefix run and no redirection takes a target. It turns
  `test_dot_after_redirection` red.
- re-pointed, `old dot scan restored` (session faults): round C replaced the
  bytes it mutated, so it now adds 0125's scan (any prefix word or `=` since the
  nearest operator) to the new check. It still turns `test_dot_operand_ruling`
  and `test_honest_session_data` red.
- re-pointed, `dot after prefix options ignored` (cd faults): it now replaces
  the command-word check with the bare command-start check. It still turns
  `test_trap_and_prefixed_dot` red.

Every other fault entry's source bytes, in all four fault lists, match as many
times as before round C. This was checked by counting each entry's bytes in the
runner before and after.

Results on the build host (Python 3.8.2, macOS; scratch outside the checkout):

| Command | Result |
|---|---|
| `python3 tests/check_counts.py` | `suite: 641 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/test_review_faults_cd.py` | `Ran 32 tests in 1.396s`; `OK`; `cd-call corpus graded-against-seen: 11/11` |
| `python3 tests/test_review_faults_cd_faults.py` | `Ran 1 test in 10.992s`; `OK`; 25 `cd fault red:` lines |
| `python3 tests/test_review_faults_core.py` | `Ran 11 tests in 0.089s`; `OK` |
| `python3 tests/test_review_faults_corpus.py` | `Ran 1 test in 1.491s`; `OK`; `honest-call corpus graded-against-seen: 278/278` |
| `python3 tests/test_review_faults_data.py` | `Ran 5 tests in 0.149s`; `OK` |
| `python3 tests/test_review_faults_launch.py` | `Ran 20 tests in 24.247s`; `OK` |
| `python3 tests/test_review_faults_session.py` | `Ran 18 tests in 0.524s`; `OK`; `session-call corpus graded-against-seen: 8/8`; `session-call corpus hits: 0, ambiguous: 1` |
| `python3 tests/test_review_faults_session_faults.py` | `Ran 1 test in 8.136s`; `OK`; 19 `session fault red:` lines |

`Python feature_version=(3, 6): 4/4 changed Python files parse`.
`tests/run_tests.py`, `tests/test_review_faults_faults.py` and
`tests/test_review_faults_build.py` were not run, as the head directs.

### Status (round C)

Review 1's F1 is fixed, and its NOTEs are recorded above. The work waits on
the separate review. This producer does not approve or merge its own work, and
this follow-up measures nothing.

## Owner rulings needed

None.
