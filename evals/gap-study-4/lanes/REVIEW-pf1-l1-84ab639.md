VERDICT: CHANGES

# Closure check: lane pf1-l1-freeze-gates at 84ab6393 (after REVIEW-pf1-l1-53d0e9a.md)

_Reviewer: the same independent opus-medium reviewer, read-only. Clock read with `date`: Sun 25 Oct 2026 02:19 EDT (start) and 02:33 EDT (writing)._
_Candidate: `/Users/javrodher/aegis-builds/pf1-l1-20261024`, head 84ab639319252d9078e79af4e63be8fb75ef7e29._
_`git log 53d0e9a..84ab639`: 411132e2 commits my earlier review unedited; 84ab6393 is the fold. I read the diff itself (19 files, +606/-126), not the builder's account of it._
_Mac probes ran behind `mac_slot.py light-ok --tests --work gap-study-r4`, with `python3.12 -B`, in scratch git repositories only. No athena run, no GitHub call. No code changed._

## Closure of the 53d0e9a findings

| # | Was | Now |
|---|---|---|
| 1a docstring pre-registration | MAJOR | **Closed.** `order_beacon.registered_value` parses the module with ast. Probe: a docstring listing 5 rounds no longer counts; the registering commit is the one whose real assignment sets the value. |
| 1b round set twice | MAJOR | **Closed on one history.** Probe: R1 → R2 → R1 is refused (`history is [None, 33400001, 33400002, 33400001]`). The log uses `--full-history --topo-order`, so a side branch merged in that set another round is also refused. A deletion or rename-away makes `git show` fail, which refuses. |
| 1c draft not bound before the round | MAJOR | **Open in one form**; see finding 1 below. |
| 2 GH_HOST, witness unrecorded | MINOR | **Closed.** `--hostname github.com` is passed, any other GH_HOST is refused, and `take_order_witness` (both commits, their pushes and the GitHub stamps) is written and listed in FREEZE_WRITTEN_KEYS. |
| 3 citation rule | MINOR | **Mostly closed.** Every hex token must resolve, and at least one must be an edit of the file after its copy commit. A date and a made-up hash now refuse (probe). Ruling 3's "every citation" is not what the code checks; see finding 2. |
| NIT 4 stale wording | NIT | **Closed.** The `prepare` docstring is corrected, and `review_commit` is dropped from `take_order_beacon_reading`. |
| NIT 6 dirty pinned file | NIT | **Closed.** `pin_problems` compares the working bytes with the HEAD blob sha. |
| NIT 7 unreadable grade.json | NIT | **Closed.** It now counts as pending. |
| NIT 5 line-1 attestation | NIT | Moved to L4, as ruled. |

## Try-to-break results

- **ast, `if False:` assignment:** ignored by the parser and never run, so harmless.
- **ast, `if True:` override:** the runtime value differs from the parsed one. The draft's round must equal the parsed history's round, so a draft carrying the override's round is refused (probe: `REGISTERED_ROUND's history is [None, 33400003], not …`). It fails closed.
- **ast, second module-level assignment:** refused ("assigns REGISTERED_ROUND 2 times").
- **ast, `+=`:** not counted, but it cannot make the runtime value differ from the parsed one without the draft check refusing.
- **Renamed file:** `git log -- order_beacon.py` has no `--follow`. A rename away and back shows a deletion commit where `git show` fails, which refuses. Recreating the file in place shows its new value in the sequence, which refuses. Only rewritten history escapes, and that is named in `residual()`.
- **Draft changed in a merge commit:** passes when the merge takes an early-pushed candidate; finding 1.
- **Citation that resolves only on another branch:** passes, because `rev-parse --verify <t>^{commit}` resolves any object in the clone; finding 2.

## Findings

### 1. MAJOR: candidate drafts (or rounds) on parallel pushed branches still let the order be chosen after the round

`draft_commit` is `git log -1 -- prereg-draft.json`, with default history simplification.
A merge that is TREESAME to one parent on the draft path follows that parent.
So the "last commit that changed the draft" can be an old commit from a side branch.

Probe (scratch repo, real `freeze.draft_commit` and `freeze.take_order_witness`):
- commit `register` sets the round and draft v1;
- branch `candB` (draft "B") and main (draft "A") are each pushed 2 h before the round;
- after the round, main merges candB, keeps B's draft and edits another file;
- the merge itself is pushed a day after the round.

```
P4 draft_commit -> cand B (early-pushed branch)
P4 take_order_witness -> PASSES; draft witnessed by push of cand B
```

The same grind needs no merge at all: freeze on whichever candidate branch's order suits.
Each pushed branch has a clean None → R history and a draft pushed before the round.
The same holds for rounds: branches registering R1, R2, … each read as "registered once" on their own history.
Each candidate costs one mirrored wave (an athena pass, under the standing word), and nothing refuses it.

`residual()` names only "a local history rewritten to hide an earlier registration … since the mirror's other pushes are not scanned".
This case needs no rewriting: it is ordinary branches the mirror already holds.

Fix (same data, no new network read): `push_records()` already returns every pushed sha.
For each one, refuse if this clone does not hold it.
Otherwise parse its `order_beacon.py` (registered_value) and refuse the freeze if any pushed commit that sets REGISTERED_ROUND to an integer is not an ancestor of HEAD.
That is one rule covering both other rounds and other drafts with this round.
Wave branches from other lanes carry None and are unaffected.
Add a scratch-history clause and a witness for "a candidate branch pushed", and reword the residual to drop "rewritten".

### 2. MINOR: ruling 3 says every citation must be an edit; the code requires only one

`copy_manifest.citation_problem` requires every token to resolve to *some* commit and at least one to be an edit of the file after its copy commit.
Probe at HEAD: `citation_problem("study.py", "cites 411132e2 and e337fe44")` returns None, although 411132e2 (my review's commit) touched only COPIED.d, lanes/ and language-allowlist.json.
A token on another branch, or a dangling object in this clone, resolves the same way.
It then passes here and refuses on a fresh clone, so the gate's answer depends on the clone.
Fix: resolve each token within HEAD's history (`merge-base --is-ancestor`).
Then either apply the ruling literally (every cited commit in `edits`), or exempt by rule the prose citations every reason carries ("the review of 53d0e9af").

### 3. NIT: three re-cited lists are one commit short at HEAD

Checked against `git log -- <file>` at 84ab6393.
In all 18 re-cited reasons ("The commits that changed it after its copy commit, oldest first: …"), every cited sha resolves, changed that file after its copy commit, and is in order.
15 of the 18 lists are complete.
For **prereg.py, copy_manifest.py and freeze.py**, the list omits 84ab6393 itself, which also changed them.
A commit cannot cite itself, so add "up to 53d0e9af" (or "before this fold") so the sentence stays true.
The other 15 are complete: review_kit/BRIEF.md 3, why.md 1, drive.py 83, check_take.py 87, graders/confounded_design.py 6, takes.py 11, check_results.py 20, result.py 3, completeness.py 7, costs.py 9, study.py 1, mode_binding.py 7, run.py 18, build_draft.py 66, freeze_rehearsal.py 12.

## Also checked

- `copy_manifest.problems()` at HEAD returns only the known unclaimed `review_kit/rounds.json` (another lane's).
- language-allowlist.json: the w3c line text was updated to the re-cited reason, and an entry was added for my committed review's "50%" line. Both are quotations of records, with the ruling date given.
- No READER_SOURCES file is in `git diff --stat 53d0e9a..84ab639`. No file under `rehearsals/` or `native-readers/` changed.
- The lane tests add G9b (docstring, history, draft unwitnessed, GH_HOST) and G10 (nits). No clause covers a branch or merge history.
- Lane test run on the Mac at 84ab6393: `tests/test_pf1_freeze_gates.py` ran 13 tests, OK, in 893.8 s (finished 02:38 EDT by `date`; the Mac is throttled).

## Evidence

- Probes (scratch, uncommitted): `/private/tmp/claude-501/-Users-javrodher-glitch/5da39513-9adc-4587-8d29-3722641cf776/scratchpad/probe2.py` (ast, history, merge), `probe4.py` (citation), `cit3.py` (the 18 lists).
