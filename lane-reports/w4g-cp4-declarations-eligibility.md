status: done

# Lane w4g-cp4-declarations-eligibility: CP4 gate step for the `declarations` candidate

Base: `gap4/wave3-merge` at `48f100563e68f4798defd96fb1bf483dd679c940`. Branch `gap4/w4g-cp4-declarations-eligibility`.
Written Thu 8 Oct 2026, 17:57 EDT (read from `date`).

## Result

The draft says **dropped**.
At `844a4ce`, stage 01 never asks the user for a missing or ambiguous strandedness declaration.
The helper defaults strandedness to `auto` without a prompt (`gars/_system/stage01_samplesheet.py` lines 193-196 and 242-263).
Exit 2 (needs_confirm) fires only for exclusions and existing outputs (lines 827-837).
The stage 01 contract calls an absent key legal and has no step that asks about or writes strandedness (`gars/01_prepare_samplesheets/CONTEXT.md` lines 22, 109-111, 171-216).
Round 4 runs 9 pairs.
The brief's first checkpoint is also its last on a drop, so questions 3 and 4 (the literature step) were not reached, and no web page was fetched.

## Files changed

- `evals/gap-study-4/research/declarations-eligibility.md` (new): the decision record draft.
- `evals/gap-study-4/COPIED.d/w4g-cp4-declarations-eligibility.json` (new): claims the three files under `evals/gap-study-4/`.
- `evals/gap-study-4/checks.d/w4g-cp4-declarations-eligibility.txt` (new): `python3 -B -W ignore evals/gap-study-4/copy_manifest.py --check`.
- `lane-reports/w4g-cp4-declarations-eligibility.md` (this file).

## Checks run (each after `mac_slot.py light-ok`)

- `copy_manifest.py --check`, after `git add`, at commit `fb9f4400`: "ok: 108 files from 8 fragment(s) (...): 44 identical and 5 edited (round 3 at e2979b31, shared files at 68ec902f), 59 new; 5 fixture builders byte-identical; 8 frozen paths unchanged since 68ec902f63bf", exit 0.
- `lint_language.py` on the draft and the fragment: "clean — 2 input(s) scanned, 1 excused line(s) on record", exit 0.
- Both re-run after the review fixes, with the draft and this report staged: the manifest check printed the same "ok: 108 files from 8 fragment(s)" line, exit 0; the lint printed "clean — 2 input(s) scanned, 1 excused line(s) on record" (the draft and this report), exit 0.
- Not run, by the brief: `test_round4.py`, `run_checks.py`, the whole suite (the lane lead runs them on athena). This lane adds no test.

## Review

A fresh opus-medium reviewer read the four named files at `844a4ce` with `git show` only and found no MAJOR: the drop stands.
Its three MINORs and four NITs were folded into the draft:
- question 2 now says neither half's right move has a stage 01 step (the trap's ask and the normal half's declaration alike), instead of "the halves collapse", and quotes the template's own advice at line 14;
- question 2 is no longer called an independent reason;
- line 38's rule is "illustrated by", not "scoped by", its next sentence, with why it still does not require an ask;
- step 14 is lines 213-216; the value's onward flow (line 592) is named; a hand-written `<REQUIRED` strandedness exits 1 to T3 and never reaches T4; line 223's bounded-voice exception is cited.

## Decisions (this lane's own)

1. Stopped at question 1 on the drop, as the brief directs, and answered question 2 offline because it uses only the same files.
2. Read the stage 00 contract with one in-file case-insensitive search for `strand` (no hit) plus line 393, rather than in full.
3. Quoted the counts from `plans/gap-study-round-4/CP4-requirements.md` lines 17-21 after checking them there.

## Open questions for the lane lead

1. Stage 02's contract and `_system/configure.py` were not read (outside the named files); if a later stage asks about strandedness, that is a new candidate, not this one.
2. `_references/config_schema.md` was not read.
3. `docs/validity/declarations.md` is the lane lead's to write on glitch-f3's ruling.

## Sources not reached

None attempted: no web source was fetched, so none is cited.

## Deferred to Javier

Nothing. Publishing the drop with its reason happens at publication, on his word.

## Lessons worth keeping

- The seeded settings file can make a "missing declaration" impossible by construction: the template writes `strandedness: auto`, so a project from stage 00 never lacks the key.
