# What was done with each finding of `prefreeze-13.md`

Review 13 read the pre-registration at sha256 `469e883be2fc0d9ea5a9ca082ea2c792e115a68014e682836060d4979d8deab2` and ruled **do not freeze**, with two blockers and six follow-ups.
It read review 12's three blockers closed in the code and upheld all six layer verdicts.
Each finding was checked against the code before any change, and each held.
Every fold has a test and a mutation, and each mutation's guard was run green before it was broken.
Ruling 17 in `PROTOCOL.md` records what changed.
The next pre-freeze review will be `prefreeze-14.md` in this folder.

## The two blockers — folded

**BLOCKER 1 — a folder whose ledger names no session id was invisible to `--ledger` and graded by `run.py`.** Folded.
`takes.unattributed_attempts()` lists every folder under `transcripts/`, `rehearsals/` and `pauses/` that holds a ledger or a transcript and that no attempt's ledger ties to a session id; the walk-era `rehearsals/plan-gate/1/` is excepted by name, as the pre-registration names it.
`--ledger` reports each such folder before anything about rows, so a planted folder is found even with an empty ledger.
`run.py` refuses a ledger that names no take, no session id or no attempt record, where it used to default the attempt to graded.
`TheLedgerSeesEveryFolder` plants the review's folder, a transcript with no ledger and the walk-era rehearsal, and requires the first two listed and the runner to refuse; watched failing with the listing emptied, and with the runner's refusal removed.

**BLOCKER 2 — the checker proved a stop and never a continuation.** Folded.
`continuation_problems()` requires, for each step with a marker followed by a further operator line, the marker in the agent's text before that line; around a recovery, its own marker before it, the step's marker absent there and present after it.
A new reason id, `continued-past-unheld-marker`, is on the pre-registered list.
`EveryContinuationIsProven` refuses the review's take with every reply "Sure, done.", refuses a recovery sent where its marker was not held, and passes both valid walks as they were driven; watched failing with the continuation check removed.

## The follow-ups

**F1 — the model binding refused the harness's own records.** Folded on a measurement.
A one-turn session on a model id that does not exist wrote one assistant record, with model `<synthetic>` and `isApiErrorMessage: true` (`api-error-probe.txt`).
That flag now exempts a record from the model binding and from counting as an agent turn, and `harness_assistant_records` pre-registers the shape; a `<synthetic>` record without the flag is still bound.
The study-materials check now reads tool inputs and tool results, never the agent's prose.
`TheHarnessOwnAssistantRecords`, watched failing with the exemption removed and with prose read again.

**F2 — a registered row never attempted was not a problem.** Folded.
After the freeze, `--ledger` reports a row never attempted while a later row on its axis was.
`TheTakeOrderIsEnforced`, watched failing with that check removed.

**F3 — the checkout's tree was bound to nothing.** Folded.
The driver refuses a take whose HEAD carries a gars tree other than the pinned one, the take checker binds the tree the ledger records, and `run_location.how_built` now says the checkout is exported from HEAD.
`TheModelAndTheConstantsAreBound`, watched failing with the tree comparison removed.

**F4 — published bytes were bound only by a sidecar.** Folded.
`attempt_problems()` requires the ledger's `published.sha256_after` to equal the transcript's bytes.
`TheAttemptIsReDerivedFromItsBytes` appends a record to a transcript and requires it found; watched failing with the comparison removed.

**F5 — the auto-memory check could pass having read nothing.** Folded.
A take must carry a system-prompt snapshot, and the harness version the phrase was read at is recorded.
`TheAutoMemorySectionIsBound`, watched failing with a missing snapshot passing.

**F6 — `resets` made a pause.** Folded.
The marker is gone and the rest are matched as whole words; a reset connection and a four-digit status are no longer a pause.
`TheRateLimitMarkersAreBounded`, watched failing with `resets` put back.

**The residual.** Stated in the pre-registration as `binding_residual`: the session binding cannot show that only one session was opened for an id, and the limitations will say so.

## Blindness of this review

Recorded in `prefreeze-13-blindness.txt`, read from the reviewer's own session file.
None of the operator's own material reached its loaded context, and with the auto-memory switch set this time, the harness's memory instructions were absent too.
The one personal item it carried is the account email the harness injects into every session (Ruling 10).
