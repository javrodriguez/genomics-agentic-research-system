prereg.json sha256: 3a9269f0813ca874a4540fb08fb571c4b3c62e06855d2f36b72afa112490ec2b

# Pre-freeze review, tenth pass — the key, rewritten

Commands were run in `study/evals/gap-study/` unless the prompt shows otherwise; files are cited by
bare name and line.

```
$ shasum -a 256 prereg.json prereg-draft.json prereg-as-review-9-read-it.json PROTOCOL.md
3a9269f0813ca874a4540fb08fb571c4b3c62e06855d2f36b72afa112490ec2b  prereg.json
3a9269f0813ca874a4540fb08fb571c4b3c62e06855d2f36b72afa112490ec2b  prereg-draft.json
56285aa13beeeaa6ee41e4819898d010ab5db489c0434d97714d75caf0c2c5f3  prereg-as-review-9-read-it.json
d0fc7ea38334cf7817d080543f977c6597d2c912b83340443fdec49a8e0c7ce8  PROTOCOL.md
```

The baseline's sha is the one review 9 reported reading, and `PROTOCOL.md` has not moved since review
9 read it. `prereg-draft.json` and `prereg.json` are byte-identical here, which is the rename the
brief describes and not a second file to review.

# The ruling

**Freeze.** No blocker. Review 9's blocker is fixed; every clause of the new `factivity_note` is true
of the file it sits in; every one of its five citations resolves and says what the note says it says;
and the departure from review 9's proposed clause was correct — review 9's clause would have been
false in this file, for the reason the brief gives.

Three follow-ups are recorded in §6. None is a wrong number in the published table and none is a
false statement in the file that becomes read-only at `PROTOCOL.md:141`.

---

# 1. The diff

```
$ diff prereg-as-review-9-read-it.json prereg.json
1327c1327
<   "factivity_note": "No take has run. Every statement in this file about takes being cost, spent or
    lost is a COUNTERFACTUAL about a defect that was caught, and is written in the conditional. One of
    them was not, and said a defect 'cost this study eighteen takes' when the cost was averted -- a
    false statement about the record, inside the very key that exists to stop the file claiming what
    the record does not support. The whole file was swept for the same shape after it was found."
---
>   "factivity_note": "No take has run against this file. The pilot at `tasks[5].pilot` is a real run
    and is deliberately never counted as one of that cell's three takes, which is why the first
    sentence stands. Every place this file charges a cost in takes to a DEFECT -- a probe line that
    would not render, a wait point left unclosed, a control label that could never be produced --
    describes what that defect would have done had it survived to a take. Each was caught first, and
    that is guaranteed rather than claimed, because no take has run at all. Those sentences are NOT
    uniformly conditional and this key does not pretend they are:
    `tasks[0].positive.operator_script[0].recovery.why` writes the outcome as `the take publishes as
    did-not-reach` where its sibling at `[1]` writes `the take would publish`, and the mood carries no
    claim about the record either way. The one loss of takes this file records as REAL is the local
    tier's, decided at gate 2 and recorded at `local_tier.dropped` -- neither a defect nor a
    counterfactual. This key exists because an earlier draft of `carried_task_coverage.why_recorded`
    said a defect 'cost this study eighteen takes' when the cost was averted; that sentence now reads
    `would have cost`, and the whole file was swept for the same shape after it was found."
```

One line, long lines wrapped, nothing elided. Line 1327 either side; 1328 lines either side.

```
$ python3 -   (parse, key delta, nulls, tasks, scripted lines)
keys 43 -> 43
added [] removed [] changed ['factivity_note']
nulls 48 -> 48
tasks 6 6
base (['template-adherence','precondition-refusal','number-fidelity','scope-read','plan-gate'], 13, 6, 19)
new  (['template-adherence','precondition-refusal','number-fidelity','scope-read','plan-gate'], 13, 6, 19)
```

19 positive-half lines either side, so 38 across both halves — the number `:1317` counts against — and
no null the freeze checklist fills has moved.

```
$ python3 -   (recount the file's own arithmetic)
scripted tasks: ['template-adherence','precondition-refusal','number-fidelity','scope-read','plan-gate']
script turns: 26  recoveries: 12  total lines: 38
planned takes: 6 tasks x 2 halves x 3 running x n=3 = 108
one task row  : 2 x 3 x 3 = 18
```

The probe count was checked by listing every scripted turn rather than by matching `means`: each of
the five scripted tasks ends each half with one probe-position turn carrying `marker: null` and no
recovery, which is 10, and 10 + 12 recoveries = 22.


`:1317`'s "22 of the 38 lines", `:1318`'s "26 script turns plus 12 recoveries", and `:1325`'s
"eighteen takes -- one whole task row" all recompute unchanged. Nothing the fix touched carries a
number of its own except `n` and the gate index, both checked in §3.

```
$ python3 evals/gap-study/lint_language.py evals/gap-study/prereg.json        (run in study/)
clean — 1 input(s) scanned, 1 excused line(s) on record
exit=0
$ python3 evals/gap-study/lint_language.py evals/gap-study/prereg-as-review-9-read-it.json
clean — 1 input(s) scanned, 1 excused line(s) on record
exit=0
```

Clean either side: the new string introduces no leak word and no rate.

---

# 2. Review 9's blocker: fixed

Review 9's blocker was that `factivity_note`'s second sentence quantified over the whole file — "Every
statement in this file about takes being cost, spent or lost is a COUNTERFACTUAL about a defect that
was caught, and is written in the conditional" — and that the file falsified both conjuncts at
`:1252` and at `:117`.

That sentence is gone. Nothing in the new key quantifies over grammatical mood, and both sites review
9 named are now stated in the key itself as facts: `:117` is quoted by path as the indicative case
(§3, S5), and `:1252` is named as the one real take loss (§3, S6). The blocker is closed at the claim
rather than narrowed around it.

---

# 3. The new key, clause by clause

The key is one string at `prereg.json:1327`. Seven sentences, each checked against the file.

**S1. "No take has run against this file."** Supported by `:3` ("No take may run against this file,
and no number may be graded from it"), `PROTOCOL.md:21` and `PROTOCOL.md:24`. Nothing in the file
records a take of this study as having run: every Claude prediction carries no `outcome`, and the
twelve that carry `outcome: "not run"` are the two local models' cells.

```
$ python3 -   (predictions by outcome and axis)
Counter({(None, False): 18, ('not run', True): 12})
not-run models: ['llama3.1:8b', 'qwen2:7b']
non-local not-run: []
```

**S2. "The pilot at `tasks[5].pilot` is a real run and is deliberately never counted as one of that
cell's three takes, which is why the first sentence stands."** The path resolves. `tasks[5].pilot`
carries `model: claude-opus-5` and `transcripts_commit: 050d0d7`, so something was run and its
transcripts are committed; `tasks[5].pilot.note` reads "published beside the cell, never counted as
one of its three takes" (`:954`), which is what S2 says it says. "That cell" is `tasks[5]` =
`confounded-design`, and "three takes" is `n = 3`. The pilot is corroborated as a real run by
`predictions`, where the `confounded-design`/`claude-opus-5` row is the only non-blind one in the
file: `basis: "informed by evals/transcripts/confounded-refusal/ at 050d0d7"`, and that directory
exists in this tree. This clause is review 9's F2, closed.

**S3. "Every place this file charges a cost in takes to a DEFECT — a probe line that would not
render, a wait point left unclosed, a control label that could never be produced — describes what
that defect would have done had it survived to a take."**

I swept every string in the file, split to the sentence, and kept every sentence that names a defect
and charges it a cost expressed in takes. The extension is five distinct strings, and the three
appositives in S3 are quoted from them:

| site | defect | how the cost is written |
|---|---|---|
| `carried_task_coverage.why_recorded` (`:1325`) | probe line that would not render | "would have cost this study eighteen takes" |
| `tasks[2].{positive,control}.operator_script[2].line_note` | probe line that would not render | "This task would have raised on its first take." |
| `tasks[{0,2,3}].{positive,control}.operator_script[0].recovery.why` (`:117` and 5 copies) | wait point left unclosed | "the take publishes as `did-not-reach`" |
| `tasks[{0,2,3}].{positive,control}.operator_script[1].recovery.why` (`:131` and 5 copies) | wait point left unclosed | "the take would publish as `did-not-reach`" |
| `tasks[5].label_mapping` | control label that could never be produced | "every control take would grade incorrect" |

```
$ python3 -   (locate every occurrence of the cited fragments)
'the take publishes as': 7 -> [tasks[0].positive…[0].recovery.why, tasks[0].control…, tasks[2].positive…,
                               tasks[2].control…, tasks[3].positive…, tasks[3].control…, factivity_note]
'the take would publish': 7 -> [tasks[0].positive…[1].recovery.why, tasks[0].control…, tasks[2].positive…,
                               tasks[2].control…, tasks[3].positive…, tasks[3].control…, factivity_note]
'would have raised on its first take': 2 -> [tasks[2].positive…[2].line_note, tasks[2].control…]
'every control take would grade incorrect': 1 -> [tasks[5].label_mapping]
'would have cost this study eighteen takes': 1 -> [carried_task_coverage.why_recorded]
```

Every one of the five describes what the defect would have done had it survived to a take, including
the indicative one: `:117` states its antecedent explicitly — "An agent that sends T1 and stops leaves
the menu marker unheld on turn 1, and the take publishes as `did-not-reach`" — so the outcome is
consequent on a hypothesis, whatever the mood of the verb. S3 is true.

The sweep found nothing else that charges a cost in takes to a defect. The near misses, all outside
the scope and none falsifying it: `tasks[0].positive.reach_turn_note` (a raw transcript index "would
name a different point in every take" — a cost in indexing, not in takes, and conditional);
`probe_located_by` (a counting grader "would read one turn early" — a cost in grading, and
conditional); `tasks[4].execution_bound` (a risk, no take charged); `models_note` and
`predictions[3].note` (consequences of the local-tier drop, which is S6's subject).

**S4. "Each was caught first, and that is guaranteed rather than claimed, because no take has run at
all."** True and, as claimed, entailed rather than asserted: if no take of this study has run, then
no defect can have cost one, so each was necessarily caught before a take. Each of the five is also
independently shown as caught in the file — the probe-line draft was replaced (`line_note`), both
wait points have a pre-registered recovery in the same object, and `label_mapping` is the mapping
whose absence the sentence describes.

**S5. "Those sentences are NOT uniformly conditional and this key does not pretend they are:
`tasks[0].positive.operator_script[0].recovery.why` writes the outcome as `the take publishes as
did-not-reach` where its sibling at `[1]` writes `the take would publish` …"** Both citations resolve
and read as quoted; `[1]` is a sibling of `[0]` in the same `operator_script` array; the split is real
at six sites each, listed above. The quote drops the inner backticks around `did-not-reach` that the
file carries, which is a limit of quoting inside a backticked span, not a misquotation.

**S6. "The one loss of takes this file records as REAL is the local tier's, decided at gate 2 and
recorded at `local_tier.dropped` — neither a defect nor a counterfactual."**

```
$ python3 -   (citation resolution)
tasks[5].pilot                                     resolves  contains('never counted as one of its three takes') = True
tasks[0].positive.operator_script[0].recovery.why  resolves  contains('the take publishes as `did-not-reach`') = True
tasks[0].positive.operator_script[1].recovery.why  resolves  contains('the take would publish as `did-not-reach`') = True
local_tier.dropped                                 resolves  contains('gate') = True
carried_task_coverage.why_recorded                 resolves  contains('would have cost this study eighteen takes') = True

n = 3 | local_tier.dropped.gate = 2
local_tier.dropped.control_takes = the two local control takes are dropped with the same reason
```

`local_tier.dropped.gate` is `2` and `local_tier.dropped.by` reads "at gate 2", so "decided at gate 2"
is the file's own word. The loss is `:1252`'s two control takes plus the two local models' cells,
which `model_status` marks `runs: false` and `predictions` marks `not run` — one decision, one tier,
and the only real take loss the file records. It is a decision and not a defect, so the "neither"
holds. This is the site review 9 named as breaking the old key's first conjunct; the new key states it.

**S7. "This key exists because an earlier draft of `carried_task_coverage.why_recorded` said a defect
'cost this study eighteen takes' when the cost was averted; that sentence now reads `would have
cost` …"** The path resolves and now reads "A probe line that would not render would have cost this
study eighteen takes". The quoted fragment is verbatim from the pre-fix string as review 9 recorded it
in its own §1 diff ("A probe line that would not render cost this study eighteen takes once already"),
and the key it sat in was `carried_task_coverage`. The pre-fix bytes are not in this directory; this
clause is verified against review 9's transcription of them and against the current file, not against
the original.

This also closes review 9's **F1**: the old key's "One of them was not" had no referent in the set it
quantified over. The rewrite moves that history into S7, where it is explicitly about an earlier
draft, and drops the quantifier that made it dangle.

---

# 4. The departure from review 9's proposed clause was correct

Review 9 proposed:

> Every statement in this file that charges a cost in takes **to a defect** is a COUNTERFACTUAL about
> a defect that was caught, and is written in the conditional.

and asserted that this scope "admits exactly `carried_task_coverage.why_recorded`,
`tasks[0].positive.operator_script[1].recovery.why`, `tasks[2].positive.operator_script[2].line_note`
and `tasks[5].label_mapping` — all four conditional", with `:117` falling outside because it does not
charge anything to a defect.

That is wrong, and it is wrong on review 9's own evidence. `:117` reads:

> An agent that sends T1 and stops leaves the menu marker unheld on turn 1, and the take publishes as
> `did-not-reach` — **the same defect the T3b recovery closes**, at the wait point one turn earlier.
> Found by a reviewer reading the contract's Process rather than the walk …

The subject is named as a defect, by the file, in the same sentence; the cost is a take publishing as
`did-not-reach`, which `reserved_labels` and `reserved_labels_note` make a take that counts against
holding. So `:117` is inside review 9's proposed scope and is present indicative, and review 9's
clause would have been false in the file for the same reason the clause it replaced was false — one
round smaller, exactly as the brief says.

The two sites are not separable on any ground but mood. `:131`, which review 9 admits, has the
identical shape: an agent-behaviour antecedent, a study defect as subject ("This is the F1 class of
defect …"), and the same `did-not-reach` consequent. A scope that takes `:131` takes `:117`. Since
review 9's clause conjoins "and is written in the conditional", admitting `:117` falsifies it.

The rewrite's response — stop quantifying over mood, state the factivity directly (S3, S4), name the
split as a fact with both sites cited (S5), and name the real loss (S6) — is the correct one, and it
is checkable in a way a mood quantifier over 711 strings is not. Review 9's optional second clause
("The only takes this file records as actually lost are the local tier's …") was taken up as S6.

---

# 5. Contradiction sweep on what the fix added

Nothing the new key adds contradicts the file. What I looked for:

- **A number.** The key states three: "three takes" (`n = 3`), "gate 2" (`local_tier.dropped.gate = 2`),
  and "eighteen takes" quoted from the earlier draft (`:1325` still factors it as 2 x 3 x 3). All check.
- **A citation that does not resolve or does not say what the note says.** Five citations, all
  resolve, all verified above.
- **An exhaustiveness claim the file breaks.** S3's "every place" and S6's "the one loss" are the two.
  Both were swept over all 711 strings in the file and both hold; the sweep output is in §3.
- **A claim the withdrawn phrases guard would object to.** The key contains neither withdrawn phrase:
  "nothing is executed" occurs once, at `tasks[4].execution_bound.what_was_claimed`, and "every
  operator line, verbatim" once, at `what_the_walks_did_not_fix` — the sites that quote them as
  withdrawn, unchanged from review 9's count.
- **A cross-file contradiction.** `grep -rn factivity` finds the key in no other file, so no document
  restates or depends on it.

Two things I checked because they look like contradictions and are not:

- **The walks.** The file records real runs other than the pilot — `walk_coverage_note`,
  `menu_position_note`, `tasks[0].positive.operator_script[1].fixed_by_walk` and others. They do not
  falsify S1 or S4: `COSTS.md:30` states the rule, "A walk is not a take and is never graded", and no
  string in `prereg.json` calls a walk a take. See F2.
- **The first study's takes.** `COSTS.md:39` and `COSTS.md:80` record "a six-turn take of the first
  study" and "One completed take of the first study's pair 2". `COSTS.md:80` sits under the header
  "## Notes recorded before any take", which is the convention: an unqualified "take" is this study's,
  and a first-study take is always qualified. `prereg.json` records no first-study run as a take
  anywhere, so S4's "no take has run at all" is not falsified from inside the file. See F3.

---

# 6. Findings, non-blocking

**F1. `prereg.json:1327`, three clauses are present-tense claims about the record that invert at the
first take, in a key that can then only be amended.** "No take has run against this file" (S1),
"because no take has run at all" (S4) and "The one loss of takes this file records as REAL" (S6) are
true now and false once takes run — and `PROTOCOL.md:141` makes the file read-only to the run at the
freeze, so `PROTOCOL.md:142` puts the only remedy at "published as `amended`, with before and after
and both regrades side by side". Not a blocker: the test is whether the clauses are true of the file
they sit in, and they are; the file also already carries as-of-drafting content that the freeze does
not rewrite (`tasks[5].draft: true`). The cheapest fix is three words before the freeze — "As of the
freeze, no take has run against this file" — and it costs nothing to make now and an amendment to
make later. `freeze.py` rewrites `status` and would not touch this key.

**F2. `prereg.json:1327`, S2 names the pilot as the exclusion that makes S1 stand, and the walks are
excluded by a different file.** The pilot is the run most easily mistaken for a take of a graded cell,
so naming it is right. But the walks are also real runs recorded in this file, and the only written
statement that a walk is not a take is `COSTS.md:30`, outside the file that becomes read-only. One
clause in S2 — "the pilot and the walks are runs; neither is a take" — would keep the distinction
inside the frozen file. Follow-up.

**F3. `prereg.json:1327`, S4 drops S1's scope.** S1 says "against this file"; S4 says "no take has run
at all". The unqualified form is contradicted only by first-study takes, which `COSTS.md:39` and
`COSTS.md:80` name and always qualify, and which `prereg.json` never calls takes. Nothing false; the
scope word is free if the key is being edited for F1 anyway. Follow-up.

**F4. Review 8's F1–F9 and review 9's F3 are unresolved and are not re-argued here.** This diff
touched one string. They remain follow-ups on the terms those passes set. Review 9's F1 and F2 are
closed by this fix, in §3.

---

# 7. The three verifications review 9 left open

The harness runs in this copy, so all three are answered.

```
$ python3 evals/gap-study/test_harness.py          (run in study/)
...................................................
Ran 51 tests in 0.124s
OK
```

Green on these bytes, and green on the baseline too — I copied the tree, swapped
`prereg-as-review-9-read-it.json` in as `prereg.json`, and re-ran:

```
$ python3 evals/gap-study/test_harness.py          (baseline bytes, scratch copy)
Ran 51 tests in 0.119s
OK
```

51 either side, so the diff is harness-neutral.

**(a) The 43rd top-level key is safe.** Review 9 could not repeat review 8's grep. It returns nothing
here, and neither does a wider one:

```
$ grep -n "\.keys()\|set(\|len(pre)\|top_level\|assertEqual(sorted" test_harness.py
(no output, exit 1)
```

No check in the harness asserts over the top-level key set. `freeze.py` is also clear: it reads the
draft, adds its own keys, walks for nulls and writes — there is no key allowlist and nothing that
counts top-level keys. The count was 43 either side of this diff in any case; the 42-to-43 step was
review 9's diff, not this one.

**(b) `prereg.load()` resolves to the file in force.** The C2 guard reads through the loader rather
than by filename, and the loader takes `prereg.json` when it exists:

```
$ python3 evals/gap-study/prereg.py --status       (run in study/)
in force : prereg.json
frozen   : True
status   : DRAFT — not frozen. No take may run against this file, and no number may be graded from it.
tasks    : 6  (template-adherence, precondition-refusal, number-fidelity, scope-read, plan-gate, confounded-design)
models   : 5 in the fixed list, 3 running
n        : 3  -> 108 planned takes
take order: not yet — seeded at the freeze
```

`frozen: True` beside a `DRAFT` status is the rename described in the brief, not a state of the
repository.

**(c) Review 8's F9, the shallow copy in the C2 guard, is real and is currently inert.** The guard at
`test_harness.py:539-541` does `whole = dict(prereg.load())` and then pops `execution_bound` off each
task, which mutates the loader's cached dict rather than a copy:

```
$ python3 -   (load, run the guard's copy-and-pop, re-read through the loader)
execution_bound present in the loader cache before the guard: True
execution_bound present in the loader cache after  the guard: False
```

It does not bite today because `execution_bound` has exactly one reader in the harness,
`test_harness.py:519`, inside the same test and before the pop. It bites the moment a second test
reads it. Not re-argued here; recorded as confirmed, since review 9 could not run it.

---

# Limitations of this pass

- Scope was the one-line diff and what it reaches. The design was not re-reviewed and no finding
  carried as a follow-up by an earlier pass was re-raised as anything else.
- S7's claim about the pre-fix bytes is verified against review 9's transcription of them, not
  against the bytes; the earlier draft is not in this directory.
- The committed transcripts under `study/evals/transcripts/` were confirmed to exist at the path the
  `confounded-design` prediction cites and were not read or quoted.
- The published table itself was not re-derived; the diff moves no number, and the four numbers the
  file states about its own scripts and takes were recomputed from the file in §1.
