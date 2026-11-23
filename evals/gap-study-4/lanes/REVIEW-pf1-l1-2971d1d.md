VERDICT: PASS

# Second closure check: lane pf1-l1-freeze-gates at 2971d1d7

_Reviewer: the same independent opus-medium reviewer, read-only. Clock read with `date`: Sun 25 Oct 2026 04:33 EDT at the start._
_Candidate: `/Users/javrodher/aegis-builds/pf1-l1-20261024`, head 2971d1d7086439c0c0d206ebde4bca6663032365. `git log 84ab639..2971d1d`: ee3600fe commits my closure check unedited; 2971d1d7 is the fold (17 files, +422/-63). I read the diff itself._
_Mac work ran behind `mac_slot.py light-ok --tests --work gap-study-r4`, with `python3.12 -B`, in scratch repositories. GitHub was read only, with `gh api --hostname github.com` GETs of activity and branches for gars-cloud-mirror, aegis and genomics-agentic-research-system. No athena run, no fetch into the candidate clone, no code changed._

## Closure of the 84ab639 findings

| # | Was | Now |
|---|---|---|
| 1 parallel pushed candidates | MAJOR | **Closed** for every road this clone can see; see the probes below. The one road left (a record GitHub stops returning) is minor 1. |
| 2 citation rule | MINOR | **Closed.** Every hex token must be a commit in HEAD's history that changed the file after its copy commit. Probe: `cites 411132e2 and e337fe44` now refuses ("411132e2, which did not change it after its copy commit"). |
| 3 lists one commit short | NIT | **Closed.** All 18 lists now read "after its copy commit and before this lane's review folds". Re-checked against `git log`: every cited sha is a real edit, in order. 15 lists are complete, and prereg.py, copy_manifest.py and freeze.py stop correctly before 84ab6393 and 2971d1d7. |

## Grind roads on the new code (scratch repos, real `freeze.take_order_witness`)

```
legit single line -> PASSES
A deleted+dangling candidate -> REFUSED: the mirror holds d5cb0a2de638, off HEAD's line, which changes prereg-draft.json after the registering commit …
B force-pushed-away candidate -> REFUSED: the mirror holds 5bcac66dbe9d, off HEAD's line, …
C candidate record absent -> PASSES
D mirrored sha missing locally -> REFUSED: 1 sha(s) the mirror records are not in this clone …
E merge draft_commit is merge? -> True
E merge pushed late -> REFUSED: the draft commit: GitHub's first push … is stamped … later than …
```

- A pushed branch later deleted, or a sha that is present but unreachable: refused, because `cat-file -e` and `rev-list` both read dangling objects.
- A force-pushed branch: refused, because the overwritten sha is still the `after` of its earlier record.
- The 84ab639 probes re-run unchanged:
  - the docstring pre-registration is not counted;
  - a round set twice is refused;
  - `if False:` is ignored;
  - an `if True:` override and a second module-level assignment are refused;
  - the merge that takes a side branch's draft is now the draft commit itself, and refuses when pushed late.
- I also reasoned through candidate lines that branch before the registration (each would need its own registering commit, and the one off-line is refused) and candidates that were never pushed (they cannot be witnessed). Neither opens a road.

## Questions 1-3

**1. The five rewritten citations.**
The owner files are not edited.
`git diff --quiet 96c1d959 2971d1d` holds for `review_kit/BRIEF.md` and `graders/confounded_design.py`.
`build_draft.py` and `copy_manifest.py` are unchanged by this fold except copy_manifest's own rule change; `git diff --stat 53d0e9a 2971d1d` shows nothing for BRIEF.md, graders/ or build_draft.py.
What changed are the five sha citations inside **COPIED.d reason strings** about those files.
So:
- `rounds.py --check` gives only its known red ("prefreeze round 1 is OPEN … not committed"), with no prompt-sha red, so BRIEF.md still hashes as registered.
- No grade can move, because no grader byte changed.
- The round 2 kit carries the new fragment text, which is study bookkeeping, not prompt bytes.

Each rewrite quotes the right commit's subject, checked with `git log -1 --format=%s`:
- c41b7d50 → 'review: fold glitch-f1's rulings into the round 4 review kit (lane review-kit-port)'
- d1839653 → 'gap4 w3c fold 2: lane report (review round 2 folded; audits at 9dd2aa9d)'; the inner 9dd2aa9d is a genuine edit of the grader, so it passes
- a76b4dd2 and b0c917ff → their subjects verbatim
- e2979b31 → "round 3's done commit (copy_manifest.SOURCE_COMMIT)"; SOURCE_COMMIT is e2979b3143081824aadea73523ec41af30c1ddb1, which is true

See nit 3 for a duplicated phrase.
Should the rule have read only the near-rewrite sentence?
I think it should have; see minor 2.

**2. Grind roads:** see above.

**3. The freezing clone must hold every mirrored commit.**
This is sound for integrity, because it fails closed (probe D).
It is not written into the freeze steps; see minor 3.
Measured now: the mirror's activity returns 610 records (536 push, 74 branch_creation) with 608 distinct shas, and **29 of them are not in this clone**.
They are earlier pushes on lane/geo-recompute, lane/validity-followups, gap4/briefs, gap4/cloud-briefs, gap4/live-merge-20261014 and cloud/guard-and-env-fixes.
All 74 mirror branches are live, and the mirror has no force_push record, so these should arrive with a fetch of every mirror ref.
I did not fetch, so that is inferred, not verified.

## Findings (all minor or nit; no gate is open)

### 1. MINOR: a candidate whose records GitHub stops returning is invisible, and the residual says the opposite

`mirror_problem` can only scan the records the activity API returns (probe C passes).
`residual()` says "a push record GitHub no longer returns refuses the freeze, never passes it".
That is true for the two witness pushes, but false for candidate records: those pass by being absent.
Whether GitHub keeps a deleted branch's records could not be checked.
There has never been a branch deletion on the mirror, aegis or GARS: every ref in their activity is still a live branch, and there are no `branch_deletion` records.
Fix:
- Say so in `residual()`, for example "a candidate whose push records GitHub no longer returns (for instance, if it drops a deleted branch's) is not seen".
- Optionally, close it with a mirror ruleset that restricts deletions and blocks force pushes. The freeze would read it with a read-only `gh api` and refuse without it. Repository settings are an owner change.

### 2. MINOR: the strict citation rule reaches the owners' prose, so five owner citations were rewritten

The rule's job is that a near-rewrite cites the commits that edited it.
Applying "every hex token must be an edit" to the *whole* reason made five legitimate owner citations fail:
- a review of another commit;
- the source commit;
- another lane's report.

So they were reworded into commit subjects, which are weaker references, inside other lanes' records.
This lane's own fragment once said "recorded here only so the owners' fragments stay untouched".
Simpler and less invasive: read only this lane's citation sentence ("The commits that changed it after its copy commit …").
Require there every token to be an edit on HEAD's line, and require any other hex token in the reason to resolve within HEAD's history.
Then put the five sha citations back.
This is not blocking: the rewrites are accurate.

### 3. NIT: freeze steps omit the fetch, and one rewritten reason doubles a phrase

- REGISTRATION_ORDER (the four steps written into the draft) has no step "fetch every mirror ref into the freezing clone". Only the refusal message names it.
  Add a step 5, and the fact that a force push the mirror cannot serve again would block the freeze.
- The copy_manifest.py reason in `COPIED.d/w8a-walk-layout.json` now reads "sources read from round 3's done commit round 3's done commit (copy_manifest.SOURCE_COMMIT)".

## Also checked

- `copy_manifest.py --check` at HEAD fails only on the known unclaimed `review_kit/rounds.json`.
- No READER_SOURCES file, and nothing under `rehearsals/` or `native-readers/`, is in the fold's diff.
- `draft_commit` now uses `--full-history --topo-order` and refuses two candidate lines in HEAD's history. Legitimate lane merges pass, as long as the draft is regenerated last on the freeze line, which is the plan's L4 order.

## Evidence

- Probes (scratch, uncommitted), in `/private/tmp/claude-501/-Users-javrodher-glitch/5da39513-9adc-4587-8d29-3722641cf776/scratchpad/`:
  - `probe5.py` (roads A-E)
  - `probe2.py` and `probe4.py` (re-runs)
  - `cit3.py` (the 18 lists)
  - `act.tsv` (mirror activity, read-only)
- Lane test at 2971d1d7 on the Mac: `tests/test_pf1_freeze_gates.py` ran 14 tests, 1 failure, in 1657 s (finished 05:06 EDT by `date`).
  The failure is G8.copies, and this uncommitted file causes it: "lanes/REVIEW-pf1-l1-2971d1d.md is under evals/gap-study-4/ and no fragment in COPIED.d/ claims it".
  Re-run alone with the file moved out of the tree, `-k test_g8` reads OK. With the file in place, it reproduces the failure.
  The other 13 tests passed in the full run.
  The file needs a fragment entry when it is committed, as the two earlier reviews got.
- Verdict note: PASS means no gate is open. Minors 1 and 3 are text and step fixes, and they should land before the round is registered, because the residual and REGISTRATION_ORDER are written into the draft the round-2 reviewer reads.
