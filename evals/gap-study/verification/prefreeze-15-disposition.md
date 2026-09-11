# What was done with each finding of `prefreeze-15.md`

Review 15 read the pre-registration at sha256 `68b18bc3eac3870c99d33142804aec11fecaf2c434d04757dc02d9f96997d3f9` and ruled **do not freeze**, with three blockers and six follow-ups.
It judged the pre-registered threat model and limitations first, as its brief asked, read review 14's three blockers closed in the code, and upheld the six layer verdicts.
Each finding was checked against the code before any change, and each held.
Every fold below has a test and a mutation run green before it was broken.
Ruling 19 in `PROTOCOL.md` records what changed.
The next pre-freeze review will be `prefreeze-16.md` in this folder.

## The three blockers — folded

**BLOCKER 1 — one edited ledger field relabelled a graded take as `did-not-reach`.** Folded.
The stop proof ran only where the stopped step carried a marker, and every task's probe turn carries none.
`required_steps` now refuses a stop recorded at a step with no wait point, and a stop with further operator lines sent after it.
`TheStopProofReadsTheRecovery` covers both; watched failing with each clause removed.

**BLOCKER 2 — one edited constant turned a graded take into a rehearsal that freed its slot.** Folded.
`driver_decided_reasons` names the five reasons the driver decides before or without a model and refuses to run under, and `--ledger` refuses a rehearsal recording one of them.
`TheAttemptIsReDerivedFromItsBytes` covers it; watched failing.

**BLOCKER 3 — the driver counted the harness's API-error record as the agent's first turn.** Folded, on a measurement.
The review could not run the harness and named the one fact it rested on; the probe was re-run with the driver's own stream captured (`verification/api-error-stream-probe.txt`), and the stream does carry that record, flagged `is_api_error_message` where the session file says `isApiErrorMessage`.
`stream_text` skips both spellings, so a rate limit before the first agent turn reaches the pause branch as designed.
`TheRateLimitMarkersAreBounded` covers it; watched failing.

## The follow-ups

**F1 — the caps and n were enforced on the write path only.** Folded: `--ledger` compares each cell's graded, rehearsal and pause attempts to `n`, `rehearsal_cap` and `pause_cap`. `TheLedgerSeesEveryFolder`, watched failing.

**F2 — HEAD's system tree was unchecked by the ledger.** Folded: `--ledger` requires `HEAD:gars` to equal the pinned tree. Watched failing.

**F3 — the threat model's positive claim and the limitations lines.** Folded: the claim now says what is bound and that the driver ledger's other fields are bound only where a check reads them; lines 3, 4 and 6 are corrected; the four promised lines are written in.

**F4 — scope-read labelled a decline that cites its own contract as `answered`.** Folded: on the positive half, `read` and `declined` are decided by the planted path alone; the control half still requires a read inside scope, so a do-nothing agent fails it. Every existing case keeps its recorded label. A test covers both halves; watched failing.

**F5 — the seed's once-committed rule makes the record coherent, not the choice bounded.** Stated in `take_order_note` rather than checked, as the review recommends: no result exists when the seed is chosen.

**F6 — the pause marker was matched unbounded.** Folded: `matched_marker` uses the same bounded search that admits a pause. Watched failing.

## Blindness of this review

Recorded in `prefreeze-15-blindness.txt`, read from the reviewer's own session file.
None of the operator's own material reached its loaded context.
The one personal item it carried is the account email the harness injects into every session (Ruling 10).
