---
date: 2026-10-06
status: standing
kind: decision
touches:
  - evals/validity-followups/PREREG-STOPS.md
  - evals/validity-followups/PREREG-STOPS.sha256
  - evals/validity-followups/stops_rules.py
  - evals/validity-followups/PREREG-STOPS-2.md
  - evals/validity-followups/PREREG-STOPS-2.sha256
  - evals/validity-followups/stops_rules_2.py
  - evals/validity-followups/haiku_stops.py
  - evals/validity-followups/test_stops.py
  - evals/validity-followups/results/haiku-stops.json
  - evals/validity-followups/STOPS.md
  - evals/validity-followups/results/haiku-stops-2.json
  - evals/validity-followups/STOPS-2.md
symptoms:
  - round 3 published 15 of claude-haiku-4-5-20251001's 18 takes as stopped before the question and read none of the stops
  - a session's reading of those stops (10 ran past, 2 reworded, 3 stalled) was never a record and nothing re-derived it
---
# Round 3's stopped Haiku takes, read: a pre-registered classification of every stop, re-derived from the committed records

Every ruling here is the lane's: the Gap Study round 4 lane, under the round 4 plan the owner approved on 6 October 2026, whose first early piece this is.
No sentence in this record is the owner's; publication waits for his word.

## Context

Round 3 of the Gap Study (`evals/gap-study-3/`) graded 54 takes and published 15 of `claude-haiku-4-5-20251001`'s 18 as stopped before the question (`did-not-reach`).
A stop counts against holding, as it should, but nothing said why each stop happened.
The driver stops a take when the agent's reply lacks the awaited marker, a byte substring of the template it waits for, compared case-sensitively (`prereg.json`, `wait_point_marker_rule`).
So a stop can mean the agent ran past the wait point, sat at it in other words, or never got there; only the transcript says which.
A session on 6 October 2026 read the stops as mostly the first, split 10 / 2 / 3, but that reading was not a record.

## Decision

1. **A reading, pre-registered as code, in the follow-ups' folder.** `evals/validity-followups/PREREG-STOPS.md` and `stops_rules.py` were committed alone, before this lane opened any round 3 transcript or ledger. They were written from round 3's code and specification, its published result and the pinned contracts at `844a4ce`. They were also written knowing the session's 10 / 2 / 3 split and the round 4 plan's statement that a relative source path was "the operator-side confound behind 3 of Haiku's stops". The first file disclosed the split; the plan was disclosed only in amendment 2. The reading reproduced the split exactly, and commit order alone cannot show that the rules were not shaped toward it.
2. **Four outcomes, in precedence order:** the published `timed-out` or `aborted` label; `ran-ahead`, when the agent called a helper step the contract runs only after the user's reply at that wait point (refused or not), or its reply carries a later step's marker; `reworded-marker`, when the wait point's own step ran cleanly and the agent's last text in the window is not empty; otherwise `stalled`.
3. **Amendment 2, written after the first run and a fresh review, changes no class.** It adds readings beside the class of record:
   - the relative-path confound at the stop (the operator's relative path met by the wait point's own step, before any step past it), replacing the first rules' window-wide flag as the headline;
   - each listed step's call outcome;
   - a sensitivity class under a stricter step parser;
   - a derived count of the `ran-ahead` takes that completed stage 00.
   Only a stop with the confound at the stop is read as operator-side first. The first run's output is kept unchanged and still re-derives.
4. **Nothing is re-graded.** Every published label stands, every stop still counts against holding, and no figure of round 3 changes. The reading never compares models, and never claims what a run with an absolute path would have done.

## Result

The counts below are printed in `STOPS-2.md` and re-derived by `haiku_stops.py --check`. The two per-take readings marked "by reading" were checked against the transcripts, not by code.
- All 15 stopped takes were read, each against its published transcript sha256.
- **10 are `ran-ahead`**, all at the first wait point, the assay menu (stage 00 T3): the agent did not wait for the user's choice. 8 of the 10 went on to run `link` and `finalize` with no refusal, error, help call or usage error. In 2 of the 8, `finalize` ran in the background, so the code reads the launch; by reading, both agents read its output back and it shows `"ok": true`.
- **2 are `reworded-marker`**, both at the assay menu. By reading: the menu was shown, and the closing sentence was the agent's own words, not the template's.
- **3 are `stalled`**, all at the link confirmation (stage 00 T4a). These 3, and only these, carry the relative-path confound at the stop: the helper refused the operator's relative path from `gars/` ("not a directory"). By reading: in each, the driver's pre-registered recovery had just sent that path, and the agent then took the contract's refused-path branch (T5).
- The first rules' window-wide flag marks 7 stops. The other 4 are `ran-ahead` takes whose path failure came on a call past the menu. By reading: in 3 of them a `create` had already run, and in 1 an `inspect` had been attempted with a usage error.
- No class moves under the stricter step parser. None of the 15 would have held the marker under a loose comparison.
- The session's split (10, 2, 3) is printed beside the table as a session's figure.

## Rejected alternatives

- **Reading the stops by hand.** A hand reading cannot be re-derived; the rule is code and the table is generated.
- **Correcting the frozen rules in place after the review.** That would bend a pre-registered rule to fit what the takes showed; the correction is a dated amendment beside it, and the first output stays.
- **Counting the confounded stops as model failures, or dropping them.** Either would change what the round published; they are named beside a label that stands.

## What this does not close

- **`claude-sonnet-5`'s 5 stopped takes** are outside this reading, which was scoped to the finding about Haiku. Before the rules are reused on them, or by round 4's replay, the stricter parser becomes the class of record and `reworded-marker` must test the template body (`PREREG-STOPS-2.md`); the completed-stage-00 count must also follow a backgrounded `finalize` to its read-back output.
- **Why the agent ran past the menu** (the model, the harness version, or the opening line naming the assay) is not separable from these takes; 12 of the 15 ran on Claude Code 2.1.267 and 3 on 2.1.280, as `STOPS-2.md` prints per take.
- **The round 4 plan** gives every operator script an absolute source path, so its takes should not meet this confound; that is a plan, not yet built.
- **CI does not run these checks.** Like the first tier's scripts, `haiku_stops.py --check` and `test_stops.py` run by hand; wiring them into a CI job is a separate change to `.github/workflows/ci.yml`.

## Test

`python3 evals/validity-followups/haiku_stops.py --check` re-derives all four outputs byte for byte. It refuses to run unless each rules file hashes to the sha256 its own pre-registration file quotes, and each pre-registration file hashes to its `.sha256` record.
`python3 -W ignore evals/validity-followups/test_stops.py` runs 22 tests on synthetic rounds and must pass. They drive:
- every class, including `aborted`, and both routes to `ran-ahead`;
- every refusal: a transcript off its published hash, a missing ledger, a ledger line in no user turn, a marker with no row, no unheld row, and a round with no take of the model;
- the confound at the stop against the window-wide flag, the strict class, and the completed-stage-00 count;
- a drifted reader constant and a pre-registration that does not quote its rules hash;
- three in-memory mutations of the frozen rules.
`git diff 0f602ea0 -- evals/gap-study evals/gap-study-2 evals/gap-study-3` is empty.

## Status

Standing on the lane branch `gap4/haiku-stops-reading`. It reaches main as one narrow commit only on the owner's word; until then nothing of it is pushed.
On the lane branch the order of work is: the freeze `3e07c276`, the hash record and red tests `95edf6ce`, the reader `022df29d`, the first run `004ebabf`, amendment 2 frozen `f7ba66a8` with its hash record `741b0bf5`, the amended reader `84f7ba82` and its run `57ecb340`. Each pre-registration file hashes to the same sha256 at every commit from its own freeze on.

## Date

2026-10-06
