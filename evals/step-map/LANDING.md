# Landing card: the GARS step map

_Written 8 Oct 2026 for Javier, by the step-map builder under glitch-f3 (the Lane-orchestrator)._
_Branch `lane/step-map`, cut from GARS `a626cdc2`; the work this card describes is at `df59ccfa`, and this card is the only file added after it._

## What lands on GARS main

One new folder, `evals/step-map/`, and nothing else: no file outside it changes, and no GARS code, contract or test is touched (`git diff a626cdc2 -- gars` is empty).
It merges cleanly: public main (`3e82629b` when checked on 8 Oct) has no `evals/step-map/` folder, and the branch only adds files.

What is in it:
- `MAP.md` and `map/`: every numbered step of the 14 GARS stage contracts (142 steps), who acts at each, and the 43 decisions the AI makes on its own, scored and ranked.
- `REVIEW.md`: the 15-item page you answered on 7 Oct, with your answers exactly as you typed them.
- `FIXES.md`: what your answers become in the fix batch after the freeze (T50); your item 1 fix in your words, with the migration and the tests it needs.
- `DEFECTS.md`: 22 GARS defects found along the way, for the same batch.
- `extract.py`, `build_map.py`, `rulings.json`, `facts/`, `judgment/` and `tests/`: the code that re-derives the map from GARS, and its tests.

**Your answers, folded as written.**
The 14 "agree" items take the fix your page proposed, in the page's words.
Item 1 (dataset class and purpose) takes your different fix, in your words: public versus restricted data, test or real analysis derived from the workflow when it settles it, internal/pilot/commercial out of routine registration.
The build reads your answers from `REVIEW.md` itself and refuses to build if anything misreads them; `REVIEW.md` is byte-for-byte what you committed, and a test checks that.

## The freeze: the step map is not an exception

The feature freeze has held since Tue 6 Oct.
It lets in fixes, evaluations E2 and E5a, whatever a partner conversation asks for, and five named items until Fri 16 Oct; nothing else.
- The freeze's terms: aegis `orgos/seed/SEED.md` lines 25 and 30 (MS12: "fixes, evaluations E2 and E5a, and whatever a partner conversation asks for, nothing else").
- The named items: decision OD28 (the GEO recomputation, the Methods generator, one recorded end-to-end run) and later ones such as OD41, your "gars-repro yes" (the reproduction package, logged on 5 Oct as the fifth freeze exception in the Brain's daily log).
- The step map is task T68 under milestone MS14. It is not E2 (E2 is the validity pages for the Gap Study tasks, decision 0018), not E5a, not a fix and not a partner ask, and no decision names it.
- The freeze lifts only on your word (OD24).

**The earliest it can land: Fri 16 Oct**, together with the post-freeze GARS fix batch (T50), on your word.
It can land sooner only if you name it a freeze exception yourself.

## The athena verdict

**PASS.**
Run `step-map-df59ccf-20261008T204823Z`, solo, on the exact commit `df59ccfa`: 1303 tests ran, 1221 passed, 0 failures, 0 errors, 82 allowed skips, in 515 seconds; the verdict was derived on the Mac from athena's log.

The full GARS suite does not include the step map's own tests, so those ran separately on the Mac, light, at the same commit:
- `test_build_map.py`: 44 tests, all pass, including 21 new ones for your answers and FIXES.md.
- `test_extract.py`: 102 tests, all pass.
- `test_mutants.py`: 4 tests, all pass.
- `build_map.py --check`: the committed map equals a fresh build.
- The extractor and its tests are unchanged since its 67-of-67 mutant pass (7 Oct), so that pass was not re-run (it is heavy work, which tonight's limits keep off the Mac).
  The new answer rules got their own throwaway mutant pass: 10 of 10 caught.

One fresh claude-opus-5-5 review (medium) of the answers fold found nothing major (8 minor, 2 nits), and all ten are folded.

## What you type to land it and push it public

On or after Fri 16 Oct:

```
step-map: land on GARS main and push public
```

To land it before then as a freeze exception instead:

```
step-map: freeze exception, land on GARS main and push public
```

Either line covers the merge into main, the scanned push to the public GARS repository, and nothing else.
Until you type one, the branch exists only here and on the private mirror.

## What changes publicly

- Public GARS gains the `evals/step-map/` folder: about 59,000 added lines, most of them the generated facts and map.
- **Your REVIEW.md answers become public, in your own words**, including your item 1 reasoning about data policy.
- `DEFECTS.md` becomes public: 22 places where GARS's contracts and code disagree, including how the safety layer refuses some commands as the contracts spell them.
  GARS's code is already public, so this describes behaviour anyone can read, but it is a public list of known gaps until T50 fixes them.
- GARS itself behaves exactly as before: no contract, script or test outside `evals/step-map/` changes, and CI is unchanged (it has no job for the step map's tests).
