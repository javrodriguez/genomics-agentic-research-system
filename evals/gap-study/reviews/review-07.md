prereg.json sha256: 3876c6f30f1e8e2932ca133920830662b1b7cfc1b1e322652ecef68b423cdc28

# Pre-freeze review, seventh pass — scoped to the diff review 6 did not read

```
$ shasum -a 256 prereg.json prereg-as-review-6-read-it.json PROTOCOL.md test_harness.py
3876c6f30f1e8e2932ca133920830662b1b7cfc1b1e322652ecef68b423cdc28  prereg.json
aeb79439f1114cba27896dcf01ae9d6a51ce1adfaba76e287016c8d3e4958823  prereg-as-review-6-read-it.json
8f9926a7b33dce842efdbfa0ee3d9a79a05f1500020b4fa31ab4ad6a3a91c9ed  PROTOCOL.md
dc3f1e19ea1c90548ff52cc02b6e6f95f7001cdefcefc4e0638ea32882679257  test_harness.py
```

# The ruling

**Do not freeze.** One blocker, four sites, all in `study/prereg.json`, all one clause each.

The two changes are each correct in themselves. Every number in the sentence that changed
recomputes. The harness change does what follow-up 3 asked and the guard still goes red. The
blocker is item 3, not item 1 or 2: the two keys that were **added** state, at the top level of the
frozen file, that `confounded-design` has no walk here and that the driver sends lines this file
does not name — and four statements elsewhere in the same file still say the opposite about all six
tasks. Two of those four are false as written, and one of the two hides a real gap in test
coverage.

The fix is four clauses of the same shape as the one already applied. It costs nothing before the
freeze and an amendment after it.

---

# 1. The pre-registration diff — what changed, and is it true?

## The diff is exactly three keys, all at the end of the file

```
$ diff prereg-as-review-6-read-it.json prereg.json
1317c1317,1319
<   "what_the_walks_did_not_fix": "... 22 of the 38 lines the driver may send are frozen without
    ever having been sent to the system under test -- 10 probe lines and 12 recovery lines,
    against 26 script turns plus 12 recoveries. ..."
---
>   "what_the_walks_did_not_fix": "... 22 of the 38 lines THIS FILE scripts are frozen without
    ever having been sent to the system under test -- 10 probe lines and 12 recovery lines,
    against 26 script turns plus 12 recoveries. ...",
>   "line_count_scope": "Every line count in this file covers the 5 tasks it scripts. ...",
>   "walks_note": "'Both halves are walked' holds for the 5 tasks this file scripts.
    confounded-design has no walk here; ..."
```

Nothing else moved. Both files parse; null count is unchanged at 48 in each, so the freeze
checklist's nulls-to-fill are untouched. Top-level keys go 39 → 41, and no guard in the harness
asserts over the top-level key set.

## Is it what follow-up 6 asked for?

Follow-up 6 asked for one clause in each of two places: `prereg.json:1317` and `PROTOCOL.md:34`.

`prereg.json:1317` — **yes, at the claim.** "the 38 lines the driver may send" became "the 38 lines
THIS FILE scripts". That is the clause asked for, in the sentence pointed at.

`PROTOCOL.md:34` — **yes**, plus a second line:

```
34: Both halves are walked through the real front door before the freeze, for the five tasks this protocol scripts.
35: `confounded-design` carries its script from the first study and was walked there; it is referenced by that study's pinned shas rather than re-walked.
```

The two new prereg keys are more than follow-up 6 asked for. They are not contradicted by it.

## Is what it now says TRUE of the file it is in?

Recounted from the file rather than read off the sentence:

```
$ python3 -c '
import json
d = json.load(open("prereg.json"))
s = [t for t in d["tasks"] if isinstance(t["positive"]["operator_script"], list)]
turns = sum(len(t[h]["operator_script"]) for t in s for h in ("positive", "control"))
recs  = sum(1 for t in s for h in ("positive", "control")
              for step in t[h]["operator_script"] if step.get("recovery"))
probes = 2 * len(s)
print("tasks this file scripts :", [t["id"] for t in s])
print("carried, not scripted   :", [t["id"] for t in d["tasks"] if t not in s])
print("script turns            :", turns)
print("recovery lines          :", recs)
print("denominator 26+12       :", turns + recs)
print("probe lines             :", probes)
print("numerator 10+12         :", probes + recs)'
tasks this file scripts : ['template-adherence', 'precondition-refusal', 'number-fidelity', 'scope-read', 'plan-gate']
carried, not scripted   : ['confounded-design']
script turns            : 26
recovery lines          : 12
denominator 26+12       : 38
probe lines             : 10
numerator 10+12         : 22
```

Every number holds, and holds specifically under the new wording:

- **38** — 26 scripted operator turns plus 12 recovery lines. `confounded-design`'s
  `operator_script` is the string `"evals/prereg.json — carried verbatim"` on both halves, so it
  contributes zero. "the 38 lines THIS FILE scripts" is the correct denominator; "the 38 lines the
  driver may send" was not, and that is the defect follow-up 6 named.
- **12 recoveries** — twelve `recovery` objects, all inside the five scripted tasks, none in
  `confounded-design`. Each carries one `send` line. Counted as occurrences, not distinct texts;
  that reading is unchanged from the sentence review 6 verified.
- **10 probes** — one `probe_operator_turn` per half, five tasks, both halves, and each names a
  turn `n` that exists in its own script.
- **22 of 38** — 10 + 12. The 16 remaining are the pre-probe turns the walks sent.

`line_count_scope` — **true.** There is exactly one line count in the file, at 1317, and it covers
the five scripted tasks. I swept every string in the file containing a digit alongside
`line|turn|task|walk|half`; no other line count exists to be out of scope. The claim that the
carried lines "do not move the numerator" is also correct and is the precise thing to say:
`confounded-design`'s lines *were* sent to the system under test in the first study, including its
probe at turn 6, so adding them would grow the denominator and not the numerator.

`walks_note` — **true**, on all three clauses. It is corroborated inside the file at
`prereg.json:897`, which already said `"...this task is carried from it and has no walk here"` in
the version review 6 read.

---

# 2. The harness change — follow-up 3

Follow-up 3: `test_harness.py:531`, the C2 regression guard read `prereg-draft.json` by name; it was
the only check in the harness naming a pre-registration file instead of going through
`prereg.load()`.

**Done, and at the claim.** The guard is now `test_harness.py:517-542`:

```
536:        whole = dict(prereg.load())
537:        whole.pop("_source", None)
538:        whole.pop("_frozen", None)
539:        for t in whole.get("tasks", []):
540:            t.pop("execution_bound", None)     # the record of the withdrawal may keep it
541:        self.assertNotIn("nothing is executed", json.dumps(whole), ...)
```

```
$ grep -c "prereg-draft" test_harness.py
0
$ grep -n "['\"][A-Za-z0-9_.-]*\.json['\"]" test_harness.py
658:        (self.analyse.RESULTS / "precondition-refusal.json").write_text(_j.dumps({
```

No pre-registration file is named by any literal in the harness. That one remaining literal is a
results file, not a pre-registration.

**Does it still measure anything?** Yes. I ran the guard's body against the file about to be frozen,
then put the defect back:

```
$ python3 - (the guard's body, verbatim, against prereg.json)
phrase in whole file            : True
phrase after popping the scope  : False
guard fires on top-level mutant : True
guard fires on in-task mutant   : True
```

Line 1 shows the withdrawn claim is present in the file — at `prereg.json:868`, inside
`plan-gate.execution_bound.what_was_claimed`, where it is quoted as the thing being withdrawn. Line
2 shows the scoping pop removes exactly that occurrence and no other, so the guard passes for the
right reason rather than because the string is absent everywhere. Lines 3 and 4 show it goes red
when the claim is reintroduced at a top-level key — the copy that survived four passes — and when
it is reintroduced inside a task object outside `execution_bound`. Both scopes review 5 and review 6
widened it to are intact after the change.

Nothing in the change narrowed the guard. It reads the whole loaded file and the short phrase, as
review 6 recorded.

**Not a finding, but state it:** the fix's correctness now rests entirely on `prereg.load()`
resolving to the file in force. `prereg.py` is not in this directory, so I could not execute that.
`PROTOCOL.md:23` says the pre-registration "is drafted in `prereg-draft.json` and becomes
`prereg.json` at the freeze", and every other check in the harness already depends on the loader, so
a loader that resolved wrongly would be a defect in all of them and not only in this guard. One
command settles it at the freeze commit: `prereg.load()["_source"]` — the key this guard pops —
should name `prereg.json`.

---

# 3. What the change contradicted — the blocker

The two new keys are true. Four statements elsewhere in the same file are not, and it is the new
keys that make them checkable.

```
$ grep -n "the pre-probe turns of each task\|from every message the committed walks produced\|Each task still gets its own walk\|every line the driver may send\|has no walk here" prereg.json
 897:  "source": "the FIRST study's committed transcripts, because this task is carried from it and has no walk here",
1265:    "the operator lines the walks SENT, verbatim -- the pre-probe turns of each task",
1268:    "the hand-labelled case suites, from every message the committed walks produced"
1295:  "walk_coverage_note": "... Each task still gets its own walk, because ..."
1316:  "operator_line_rule": "... EveryOperatorLineRenders asserts every line the driver may send renders ..."
1319:  "walks_note": "'Both halves are walked' holds for the 5 tasks this file scripts. confounded-design has no walk here; ..."
```

`tasks` has six entries. All four of 1265, 1268, 1295 and 1316 quantify over all of them.

## B — the scoping clause landed at two sites of six; four remain, two of them false

### B.1 `prereg.json:1316` — a false claim about what a named test covers

> `test_harness.py EveryOperatorLineRenders asserts every line the driver may send renders with
> those two and nothing more.`

It does not. The test skips any half whose script is not a list:

```
374:                script = t[half].get("operator_script")
375:                if not isinstance(script, list):
376:                    continue
```

`confounded-design`'s `operator_script` is a string on both halves, so the test checks the 38 lines
this file scripts and none of the lines the driver sends for that task. The new
`line_count_scope` at 1318 states in the same file that "the driver may send more lines than this
file names", which makes 1316 false on the file's own terms.

This is not a wording nicety. `EveryOperatorLineRenders` exists because a probe line carrying
`{wrong_files}` would have raised `KeyError` on that turn and cost eighteen takes. The one task the
test does not cover is the one whose lines were written for a different pre-registration and are
carried verbatim. Whether they render under this driver's two substitutions is not checked here and
cannot be checked from this directory — and the frozen file says it is.

**Fix, one clause:** "...asserts every line this file scripts renders...". Then carry a follow-up to
render `confounded-design`'s carried lines under `{project}`/`{source}` before the first take of that
row. The frozen file must not claim coverage the harness does not have.

### B.2 `prereg.json:1295` — "Each task still gets its own walk"

False for `confounded-design`, which gets none, as 897 and the new 1319 both say. A stranger
reconstructing the study from the frozen file counts six walks and will find five. That is the same
failure mode as the "38 lines" sentence — a number a stranger recomputes and gets a different answer
for — which is why follow-up 6 was closed before the freeze rather than carried.

The scoping was applied to this exact claim in `PROTOCOL.md:34` and, in the frozen file, was written
as a note two keys later instead of at the claim. Review 6's own standard on the previous round was
that the fix must land at the claim, not only where the reviewer pointed.

**Fix, one clause:** "Each task this file scripts still gets its own walk".

### B.3 `prereg.json:1265` and `1268` — what the walks fix

`"the pre-probe turns of each task"` and `"the hand-labelled case suites, from every message the
committed walks produced"`. Neither holds for `confounded-design`: the walks fixed none of its
turns, and its case suite is built from the first study's committed transcripts, per 897. Overreach
rather than a wrong number, and in the same list the new keys scope.

**Fix, one clause each:** "...of each task this file scripts", and name the carried suite's source.

## Why this is a blocker and not a follow-up

By the standard in force: a false statement in a file that cannot be changed afterwards without an
amendment. 1316 and 1295 are false statements in the file about to be frozen. 1316 additionally
conceals a coverage gap of exactly the class that has already cost this study once.

Stated plainly against my own scope: these four are unchanged bytes that review 6 read, and 897
already contradicted them then. I am not raising them because they are old. I am raising them
because the question I was asked — did either change contradict something else in the file — has the
answer *yes, at four sites*, and two of those sites are false rather than merely loose. The
contradiction is with the two keys this diff added.

---

# Findings, non-blocking

**F1. `PROTOCOL.md:35` — "was walked there".**
A walk in this protocol is a pre-freeze rehearsal that turns draft text into fixed text
(`PROTOCOL.md:25`), committed under `walks/`, consuming one of a task's walk slots
(`PROTOCOL.md:297-298`). The first study has no such thing; it graded takes and committed
transcripts. The frozen file's own new key at 1319 says "driven in the first study", and 897 says
"has no walk here" — both deliberately avoid the word. `PROTOCOL.md:35` imports this study's term of
art into a study where it names nothing.

Not a blocker: the operative content — the script was sent to the same system under test there, and
is referenced here by that study's pinned shas rather than re-walked — is true, and I can confirm
the task was really driven there from `carried_from_first_study`, `reproduces_first_study` and the
pilot's `transcripts_commit`. It is imprecise, not false. One word: "driven there". Free now.

**F2. `prereg.json:1319` quotes a sentence that is not in `prereg.json`.**
`"'Both halves are walked' holds for the 5 tasks this file scripts."` That phrase occurs once in the
file — inside this key, as the quotation. It is `PROTOCOL.md:34`. The frozen file's own version of
the claim is at 1295, "A walk therefore covers both halves of its task". A reader holding only the
frozen file cannot locate what is being scoped. Fixing B.2 at 1295 makes this moot.

**F3. The brief describes the protocol change as one line; it is one line changed and one added**
(`PROTOCOL.md:34` and `35`). Both new lines run past the file's ~100-column wrap. Cosmetic, recorded
because the diff was meant to be exactly enumerable.

# Limitations of this pass

- `prereg.py`, the graders and the driver are not in this directory. `python3 test_harness.py` stops
  at `ModuleNotFoundError: No module named 'labels'`. I could not execute the harness. The C2 guard
  was verified by running its body verbatim against `prereg.json`, including the two mutants above;
  `EveryOperatorLineRenders` was verified by reading `test_harness.py:370-392` and confirming the
  `continue` at 375-376 against the six task objects.
- No prior `PROTOCOL.md` was supplied, so its change is verified against review 6's citation of
  `PROTOCOL.md:34` and against the current text, not by byte diff.
- Everything outside the three-key prereg diff, the two protocol lines and the C2 guard was read
  only where those changes reach it. Six passes have ruled on the rest.
