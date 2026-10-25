VERDICT: CHANGES

# Independent review: lane pf1-l1-freeze-gates at 53d0e9af

_Reviewer: fresh opus-medium, read-only. Clock read with `date`: Sun 25 Oct 2026 01:01 EDT._
_Candidate: `/Users/javrodher/aegis-builds/pf1-l1-20261024`, branch lane/pf1-l1-freeze-gates, head 53d0e9afbcbce52944a4d3a2eafd628f8a7c6e67, base 96c1d959 (6 commits, 31 files, +2150/-97)._
_No code was changed, and `git status --porcelain` is empty apart from this file._
_Mac probes ran behind `mac_slot.py light-ok --tests --work gap-study-r4` (light ok, load1 2.89 and then 1.63), with `python3.12 -B`, in scratch git repositories only. No athena run, no GitHub API call, no network read._

## Summary

Most of the lane is sound and does what the fold plan and rulings 2-10 ask.
The pins expand, a pattern that matches nothing is refused, the line-1 review check is in place, prepare refuses PENDING inputs, `--check` has 7 legs, coverage is gated with `--require-run-arms`, walk_pins and the walk_regrade counts are in, and the vendor legs are bound to bytes.
No READER_SOURCES file changed.
No file under `rehearsals/`, `native-readers/` or `review_kit/` changed.
The 10 battery reds are the ones the brief names: the unclaimed `rounds.json` (copy_manifest ×5, test_round4), `rounds.py --check` ×2, and `freeze.py --check` ×3 on PENDING, coverage and the PENDING round.

One MAJOR stays open.
The MAJOR 9 anchor still lets the operator choose the take order after the randomness is public.
The witness proves only that *some* commit once contained the registering line early enough.
It does not prove that the round was registered once, or that the draft the order permutes was fixed before the round was published.

## Findings

### 1. MAJOR: the take order can still be ground after the round is published

Three gaps, each reproduced or read in code:

(a) **A pre-registration in prose passes as the registering commit.**
`freeze.registering_commit` (freeze.py:157-168) returns the first commit whose `order_beacon.py` holds the exact line `REGISTERED_ROUND: int | None = <round>` anywhere in the file, including inside a docstring.
Probe (scratch repo, real `freeze` and `order_beacon` modules):
commit A has the variable `None` and a docstring listing 5 candidate rounds as bare lines, and is pushed 2 h before the rounds.
Commit B, pushed a day *after* the chosen round was published, sets the variable to one of them.
Output:
```
registering_commit -> A (docstring commit)
push_witness_problem -> None
```
One early push can pre-register any number of rounds, and the operator picks among them once their values are public.

(b) **REGISTERED_ROUND set twice in history passes.**
Probe: the variable goes 33400001 → 33400002 → 33400001, and the third commit is pushed after round 33400001 is published.
`registering_commit(33400001)` returns the *first* commit, and `push_witness_problem` returns None.
Nothing refuses a history that registered more than one round.
The check reads only local HEAD history, so a local reset can also hide earlier registrations that the mirror still records.

(c) **Nothing binds the draft, or the review, to a time before the round.**
`planned_order` sorts rows by `sha256(seed + row bytes)` (freeze.py:95-103).
Each row carries the `half_cell` and `slot` hashes, so any design edit moves the permutation.
The seed is public from the round's time onward (`prereg.py --order <seed>` previews any draft).
So an operator can, after publication, try draft variants offline, keep the one whose order suits, and get that one draft reviewed.
The line-1 check is then satisfied, because the review did read those bytes.
`take_order_beacon_reading` takes `review_commit` but never uses it (freeze.py:196-226).
No code compares `round_time` with the review commit, with the last commit that changed `prereg-draft.json`, or with any push of either.
REGISTRATION_ORDER step 1 says "re-derive the draft, in one commit", but nothing checks that the frozen draft is the draft of the witnessed commit.
The test module's docstring still claims "the real freeze refuses a review committed at or after a --beacon-reading file" (tests/test_pf1_freeze_gates.py, G9 paragraph).
No clause tests that, and the code does not do it.

`residual()` and the prereg.py docstring say that the round "is fixed before its value exists" and that what is left is GitHub or its clock.
Given (a)-(c), that overstates what is bound, which is the same pattern as the original MAJOR 9 claim.

Fix (all inside ruling 1; the seed stays round + randomness only):
- Read the registered value by parsing each version's `REGISTERED_ROUND` assignment (ast), not by matching a line of text.
- Refuse unless HEAD's history sets it from None to exactly one integer, once, and never to another.
- Witness the commit that last changed `prereg-draft.json` (or require its blob to equal the frozen draft's), not only the round's commit: a push holding it must be stamped at least WITNESS_LEAD_S before `round_time`.
  That fixes the draft, and so the rows, before the value exists.
  Since the review must then read those same bytes, a change to the draft after the round forces a new round, which this check refuses.
- Optionally, where this clone has the objects, scan the mirror's push records for other registered values, so a rewritten local history is caught.
- Add clauses with witnesses for the docstring line, the round set twice, and a draft changed after the push.
- Correct the test docstring.

### 2. MINOR: the push witness can be redirected unseen, and is not recorded

- `push_records` runs `gh api` with no `--hostname github.com`.
  gh follows `GH_HOST` (and the `GH_ENTERPRISE_TOKEN` setup), so an environment variable can point the "GitHub" read at a host the operator runs.
  Nothing committed would show it.
  Pin the host, and clear the GH_* variables for that call.
- The frozen file records the drand reading but not the witness itself (registering commit, pushed sha, GitHub stamp).
  GitHub documents no retention for the activity API (the lane's own RETENTION_NOTE), so a later reader may be unable to re-check the one fact the anchor rests on.
  Write `take_order_witness` into the frozen file beside `take_order_beacon_reading`, and add it to FREEZE_WRITTEN_KEYS.

### 3. MINOR: the m8 near-rewrite rule accepts a reason that cites nothing real (ruling 10)

- `LANE_RECORD` accepts any run of 8-40 hex characters, so a commit that does not exist, or a date such as `20261024`, satisfies it.
  Nothing calls `git cat-file`.
  For a near-rewrite, require a cited sha to resolve to a commit (or a cited fragment, checks file or report to exist).
- All 13 appended reasons pass on the token `ad88d14d82f8`.
  That commit is the study's first copy commit, so it says where the history starts, not which record explains the edits.
  The rule is met by construction rather than by tying edits to reasons, which was m8's aim.
  The fold plan allowed m8 to be named as a known gap, so naming it is an acceptable alternative.

Checked against the repository: each of the 13 citations is true as stated.
- Every file is above 50% changed (lowest study.py 0.52, highest costs.py 0.91).
- `ad88d14d` is each file's first commit.
- Every cited COPIED.d fragment exists and names the file.
- The six hex tokens already in the seven untagged near-rewrite reasons all resolve to commits.

One is incomplete: the reasons for **freeze.py, prereg.py and freeze_rehearsal.py** say "the edits beyond this reason are recorded in …" but leave out `COPIED.d/pf1-l1-freeze-gates.json`, this lane's own fragment, which records its edits to all three.
Add it.

### 4. NIT: stale wording

- `freeze.prepare`'s docstring says the seed is "over the review commit and the registered drand round's reading … alone".
  Since ruling 1, the review commit is not in the seed.
- The `take_order_beacon_reading` parameter `review_commit` is unused (see 1c): use it or drop it.

### 5. NIT: the line-1 check is an attestation, not a binding

`review_file_problems` compares only the report's line 1 with the draft's sha256.
A report whose line 1 is right but whose body reviewed other bytes cannot be detected, because the kit's `prereg.json` is not committed and "committed unedited" is not enforced.
This is inherent and within the operator-trust class.
Name it in `limitations` (or bind the kit sha in the launcher's own record) rather than imply more.

### 6. NIT: `--check` reads a dirty pinned file as ok

`pin_problems` flags only missing or not-in-HEAD paths.
A committed file with uncommitted edits gives ok in `--check`.
The real freeze is safe because it requires a clean `git status`.
Compare the working bytes with the HEAD blob in `--check`, or print the dirty state.

### 7. NIT: walk_regrade's all-or-nothing count skips unparseable grade.json

`regrade_problems` treats a `grade.json` that does not parse as not pending (`continue`), so such a walk escapes the "regrade has begun" rule.
The coverage gate catches it ("grade unreadable" is uncounted), so nothing passes falsely today.
Count it as a problem here too.

## Verified as holding (try-to-break items)

- Pattern matching nothing: refused (`pinned_paths`); `[` classes refused; the live expansion gives the four reader records; the `--check` pins leg reads 735 paths, ok.
- Push record that does not hold the registering commit: not counted (`history_contains` via `merge-base --is-ancestor`, fail-closed on an unknown sha).
- Push 59 min early: refused (`held[0] > deadline`; tested at lead − 60 s).
- Missing push record: refused by name, naming retention (ruling 4).
- Relays that disagree, a wrong round, randomness ≠ sha256(signature), an unpublished round (no network read): all refused, tested.
- A synthetic signature: refused on the real path; the rehearsal step fails on it.
- Seed: `sha256("gap-study-4 take order\n<round>\n<randomness>")[:40]`; the review commit does not move the order (ruling 1).
- Witness repository `javrodriguez/gars-cloud-mirror` (ruling 2).
  The standing word is verbatim at `/Users/javrodher/glitch/plans/gap-study-round-4/next-slices-2026-10-11.md:209`, scoped to waves that pass athena, which matches REGISTRATION_ORDER step 2.
- walk_regrade after one regrade: every other pending walk without a regrade.json is refused; an empty derivation over committed walks is refused; outside a git repository it is refused.
- READER_SOURCES (native_reader_registration.py:85-87): none in the diff; codex_adapter.py and gemini_adapter.py are not reader sources.
- Walk records and acceptances are untouched; `walk_register`, `run.py --walks`, `walk_regrade`, `walk_pins`, `probes4` and `build_draft --check` all PASS in the battery log.

## Evidence

- Battery log: `/Users/javrodher/aegis-builds/athena-suites/pf1-l1-battery-53d0e9a-20261025T030626Z/run.log` ("run_checks: 432 of 442"; FAIL lines 3086, 3163, 3169, 3232, 3243, 3386, 3449, 3484, 3563, 3573).
- Probe scripts (scratch, not committed): `/private/tmp/claude-501/-Users-javrodher-glitch/5da39513-9adc-4587-8d29-3722641cf776/scratchpad/probe.py`, `share.py`, `cit.py`, `cit2.py`.
