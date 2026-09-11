# What was done with each finding of `prefreeze-14.md`

Review 14 read the pre-registration at sha256 `4db26b55277d9f38260e6a4c2ab7e9205ecbde2785c4a1af404698e6aae9cece` and ruled **do not freeze**, with three blockers and seven follow-ups.
It read review 13's two blockers closed in the code, could not reopen either, and upheld the six layer verdicts.
Each finding was checked against the code before any change, and each held.
Every fold has a test and a mutation run green before it was broken, except where a line below says why a mutation cannot be hosted.
Ruling 18 in `PROTOCOL.md` records what changed.
The next pre-freeze review will be `prefreeze-15.md` in this folder.

## The three blockers — folded

**BLOCKER 1 — a pause was uncapped and carried no evidence.** Folded.
`takes.py --add` refuses a fourth pause in a cell (`pause_cap`), as it refuses a fourth rehearsal.
`--ledger` requires a pause ledger to name a marker from `driver_constants.rate_limit_markers` and to record when the pause started and ended; a test binds that list to the driver's.
`run.py` records each cell's pauses beside its rehearsals.
The review is right that none of this makes a pause unforgeable; the limitations lines say so.
Tests: `TheTakeLifecycle` refuses a fourth pause, `TheAttemptIsReDerivedFromItsBytes` refuses a pause naming an unlisted marker, `TheRunnerEnumeratesByLedger` counts pauses. Watched failing with the cap removed, and with the evidence check removed.

**BLOCKER 2 — a withheld recovery manufactured `did-not-reach`.** Folded.
For a stop at a step that carries a recovery, the take checker now requires either the recovery line in the transcript after the step's line, or the recovery's own marker absent from the reply.
`TheStopProofReadsTheRecovery` refuses the review's stop at "Welcome. Project title?" with no recovery sent, and passes the same stop with the recovery sent and unanswered, and a stop at a reply holding neither marker.
Watched failing with the clause removed.

**BLOCKER 3 — the instruction file was bound by its path only.** Folded.
The take checker reads the session's recorded git status and requires the driver's checkout: git user `gars`, a clean status and one commit named `checkout`, values pre-registered and bound by test to the driver's constants.
It also reads the content of each instruction file the session loaded and requires it to equal the pinned tree's file, trailing whitespace ignored; the two built-checkout walks showed the harness drops only the file's final newline.
The freeze now pins the root `CLAUDE.md`, and the gars tree was already bound.
`TheCheckoutIsBound` passes the real walk, and refuses the same walk with a sentence appended to its instruction file, as the review did, and with another git user.
Watched failing with the git-status check removed, and with the content check removed.
Binding every tool result to the tree is not attempted: the graders read the agent's replies and tool calls, not tool results, and a limitations line says the files the agent was shown are bound through the pinned tree and not read back.

## The follow-ups

**F1 — an unknown session id with an empty ledger.** Folded: that check now runs before the empty-ledger return. `TheLedgerSeesEveryFolder`, watched failing.

**F2 — timed-out and aborted are the driver's record.** Stated, not checked, because a timeout is not provable from a session file: a limitations line says the two labels come from the driver's per-turn record and `did-not-reach` is proven from the transcript.

**F3 — a never-attempted row at the end of an axis.** Folded: once results are committed, `--ledger` reports any registered row never attempted. The state strings the goal fixes are unchanged. `TheLedgerSeesEveryFolder`, watched failing.

**F4 — the promised limitations line did not exist.** Folded: `limitations_lines` fixes seven sentences, and `threat_model` states what the checks defend and what they cannot. `TheThreatModelAndLimitationsAreStated`.

**F5 — the order seed is a sha the operator mints.** Folded: the freeze refuses unless the seed commit lands exactly one review report and that report has exactly one commit in history, and records the report's path and sha256. `TheSeedReviewIsCommittedOnce` runs on this repository's own history and refuses a commit that lands no report; the mutation battery's sandbox has no such history, and its not-applicable list says so.

**F6 — the snapshot matched any line.** Folded: it is read from an attachment of that type. `TheAutoMemorySectionIsBound`, watched failing.

**F7 — an instruction file placed between turns becomes a capped rehearsal.** Stated as a limitations line, since that is the design's answer.

## Blindness of this review

Recorded in `prefreeze-14-blindness.txt`, read from the reviewer's own session file.
None of the operator's own material reached its loaded context.
The one personal item it carried is the account email the harness injects into every session (Ruling 10).
