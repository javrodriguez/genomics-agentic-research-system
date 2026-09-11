# What was done with each finding of `prefreeze-12.md`

Review 12 read the pre-registration at sha256 `f117a6347c7e2614e48f6ffd5ae104827872ff9e1543ae8509c9fbdb48592773` and ruled **do not freeze**, with three blockers and nine follow-ups.
Each finding was checked against the code before any change, and each held.
Every fold below has a test and a mutation, and each mutation's guard was run green before it was broken.
Ruling 16 in `PROTOCOL.md` records what changed in the rules a take is held to.
The next pre-freeze review will be `prefreeze-13.md` in this folder.

## The three blockers — folded

**BLOCKER 1 — scope-read's positive probe could not pass the take checker.** Folded.
The checker matched each scripted line by a head with the per-take path blanked, tested by containment.
It now renders each scripted line and recovery from the take's project and the source its fixture kind implies (`source_by_fixture_kind`, now in the pre-registration), and compares whole lines after whitespace normalisation.
A take's ledger must record that same source.
`EveryTaskScriptPassesTheChecker` renders both halves of every task's script the way `drive.py` renders them, under neutral names that carry `05`, with and without the recoveries firing, and requires no refusal; a line sent with another source is refused.
Watched failing: with the source blanked in the rendered line again, that test goes red.

**BLOCKER 2 — an attempt's kind came from its folder.** Folded.
`check_results.py --ledger` re-derives every committed attempt through `attempt_problems()`.
The ledger's recorded kind must equal its folder; a graded take must pass the take checker with its row; a rehearsal must carry WHY.md and either the driver's death before the first agent turn or exactly the checker's reasons; a pause must record a pause and no agent text.
`TheAttemptIsReDerivedFromItsBytes` builds each shape, including a graded take moved into `rehearsals/` with its ledger untouched, and requires the move to be found.
Watched failing: with the kind comparison removed, and separately with the graded re-check removed.

**BLOCKER 3 — the model and the budget were the driver's word.** Folded.
Every assistant record must carry the model the attempt is registered to, for walks and takes.
A take's recorded turn budget and permission mode must equal the frozen constants, and the driver refuses a budget above the registered one as well as below.
Two reason ids were added: `model-binding` and `constant-binding`.
The runner now records the model each graded take was read under.
`TheModelAndTheConstantsAreBound` runs the checker on number-fidelity walk 2 with its model ids rewritten, as the review did, and requires a `model-binding` refusal.
`TheDriverLoopRecordsEveryTurnItEnds` requires the driver to refuse a budget above the registered one and a budget below it.
Watched failing: with the model comparison removed, and with the budget refused only below.
Budgets bind takes and not walks: the committed walks ran under budgets from before Ruling 4, and their ledgers say so.

## The follow-ups

**F1 — precondition-refusal's half was not evidenced.** Folded.
The driver records the project variant it built and stage 01's exit on it, and the checker binds both to the half; a take with no such record is refused, and a walk that predates it is noted.
`TheProjectFixtureIsBound`, watched failing with the variant comparison removed.

**F2 — the take order was not enforced.** Folded.
After the freeze, `--ledger` requires each slot's first registration to fall where the seeded permutation puts it on its axis; a retry after a rehearsal or a pause is exempt.
Before the freeze there is no seed, and the check says so.
`TheTakeOrderIsEnforced` drives it on a synthetic order, watched failing with the comparison removed.

**F3 — the write detector credited a violating agent.** Folded.
It reads every segment at `|`, `||`, `&&`, `;`, `&` and, outside a heredoc, newlines, with `&>` and every redirection form, on the model of the tree's guard.
`cp` and `install` now count their destination only, since a copied source is read; `mv` counts both ends.
An older test pinned the old reading of `cp a b` as writing both; it was corrected with that reason.
A write made inside an interpreter is named as beyond a tokeniser, and a test pins the limitation.
The case suites grade exactly as recorded under the new detector.
`WriteDetectorReadsEverySegment`, watched failing with the segment split removed.

**F4 — the tree's hooks do not load at the checkout root.** Folded as a statement.
`driver_constants.deterministic_layer_note` says the takes measure the contracts and the scripts' exit codes, not the hook, and why no layer verdict turns on it.
Opening sessions in `gars/` instead was not chosen, because the first study's pilot ran the same way and the carried cell stays comparable.

**F5 — home-folder paths in ledgers.** Folded for every new ledger.
The fixture build record shows paths relative to the repository, and the copier's manifest records its relative origin; two tests require no home-folder path in a new walk ledger or build record.
The committed walk ledgers keep theirs, because they are evidence and are not edited.
No lint pattern was added, since those committed lines would trip it one by one.

**F6 — the plan-gate fixture is not committed.** Declined.
Committing it would publish a real run's outputs, which the goal does not ask for; the tree hash in the pre-registration is the pin, and the copier says plainly where it cannot rebuild the fixture.

**F7 — ledger row order when a recovery fires.** Folded.
The step row is recorded before its recovery's row in every branch, and a test drives a successful recovery through the loop and reads the order back.

**F8 — two sentences said more than the record.** Folded.
`walks_note` now says which pairs share a route and which halves were walked, and the checker's docstring counts the tasks whose halves share one fixture correctly.

**F9 — a first-turn timeout.** Folded.
A take is graded only once it has a first agent turn.
The driver routes an attempt with no session file and no agent turn to a rehearsal, and `reserved_labels_note` says so.

## Found while review 12 ran — the harness's auto-memory

Every headless session in both studies, the first study's pilot included, carried a system-prompt section offering a persistent memory folder under the operator's home.
The isolation flags did not remove it, and the smoke cited in Ruling 9 as proof of isolation carried it too.
`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, documented on the Claude Code memory page, removes it: one-turn sessions with and without it are recorded in `auto-memory-smoke.txt`.
It is now in the pre-registered isolation environment, and the checker refuses a take still offered the section.
The committed walks carry it and are noted, not refused.
The folder offered was empty in every session, so no operator material reached an agent through it.

## Blindness of this review

Recorded in `prefreeze-12-blindness.txt`, read from the reviewer's own session file.
None of the operator's own material reached its loaded context.
The one personal item it carried is the account email the harness injects into every session (Ruling 10).
It inherited nothing from outside its folder.
