prereg.json sha256: 56285aa13beeeaa6ee41e4819898d010ab5db489c0434d97714d75caf0c2c5f3

# Pre-freeze review, ninth pass — the sentence, and the key that carries it

All commands below were run in `study/`; files are cited by bare name and line.

```
$ shasum -a 256 prereg.json prereg-as-review-8-read-it.json PROTOCOL.md
56285aa13beeeaa6ee41e4819898d010ab5db489c0434d97714d75caf0c2c5f3  prereg.json
cab99fe1dd9287c6c0033631f53bebc4766b56d4080998951db622fcc952dcc4  prereg-as-review-8-read-it.json
d0fc7ea38334cf7817d080543f977c6597d2c912b83340443fdec49a8e0c7ce8  PROTOCOL.md
```

The baseline's sha is the one review 8 reported reading, and `PROTOCOL.md` has not moved since
review 8 read it.

# The ruling

**Do not freeze.** One blocker, one site, one clause.

Review 8's blocker is fixed, and fixed at the claim: `prereg.json:1325` now reads "would have cost",
adds the factorisation that makes the magnitude checkable, and adds "and it was caught before any
take ran". Every clause of the new sentence is true of the file it sits in, and its arithmetic
recomputes. No number moved, no line count moved, both files parse, and the nulls the freeze
checklist fills are untouched.

The blocker is in the other thing the fix added. `prereg.json:1327` is a new top-level key,
`factivity_note`, and its second sentence quantifies over the whole file:

> Every statement in this file about takes being cost, spent or lost is a COUNTERFACTUAL about a
> defect that was caught, and is written in the conditional.

The file falsifies both conjuncts. `prereg.json:1252` says "the two local control takes are dropped
with the same reason" — a real loss of two takes, dated, decided at gate 2, indicative, and nothing
to do with a defect. `prereg.json:117` and its five copies say "the take publishes as
`did-not-reach`" — a defect that was caught, written in the present indicative while its sibling at
`:131` writes the same outcome as "the take **would** publish as `did-not-reach`".

That is the same class of defect as review 8's: a sentence claiming more about the record than the
record supports, inside the key whose only job is to stop exactly that. It is in the file that
becomes read-only at the freeze (`PROTOCOL.md:141`), so it is a blocker and not a follow-up.

Fix, one clause: scope the subject to what the note is actually about — statements that charge a cost
in takes **to a defect**. Under that scope every member is conditional and the sentence is true; the
check is in §3. Then freeze.

---

# 1. The diff

```
$ diff prereg-as-review-8-read-it.json prereg.json
1325,1326c1325,1327
<     "why_recorded": "the frozen file must not claim coverage the harness does not have. A probe line
      that would not render cost this study eighteen takes once already, and the one task the render
      test does not cover is the one whose lines were written for a different pre-registration."
<   }
---
>     "why_recorded": "The frozen file must not claim coverage the harness does not have. A probe line
      that would not render would have cost this study eighteen takes -- one whole task row, two halves
      by three running models by three takes -- and it was caught before any take ran. The one task the
      render test does not cover is the one whose lines were written for a different pre-registration."
>   },
>   "factivity_note": "No take has run. Every statement in this file about takes being cost, spent or
    lost is a COUNTERFACTUAL about a defect that was caught, and is written in the conditional. One of
    them was not, and said a defect 'cost this study eighteen takes' when the cost was averted -- a
    false statement about the record, inside the very key that exists to stop the file claiming what
    the record does not support. The whole file was swept for the same shape after it was found."
```

That is the whole diff, long lines wrapped, nothing elided. One string changed, one key added.

```
$ python3 -   (parse, key delta, nulls, tasks)
both parse; keys 42 -> 43
added ['factivity_note']
removed []
changed ['carried_task_coverage']
nulls 48 -> 48
tasks 6 6
```

Nothing the fix touched carries a count, and no count moved:

```
$ python3 -   (recount operator lines from the task objects in each file)
as-review-8-read-it  scripted=['template-adherence', 'precondition-refusal', 'number-fidelity',
                               'scope-read', 'plan-gate'] turns=26 recoveries=12 lines=38
prereg.json          scripted=['template-adherence', 'precondition-refusal', 'number-fidelity',
                               'scope-read', 'plan-gate'] turns=26 recoveries=12 lines=38
```

38 either side, so `prereg.json:1317`'s "22 of the 38 lines THIS FILE scripts" and `:1318`'s line-count
scope still hold unchanged, and `EveryOperatorLineRenders` has the same 38 lines to check as it had
when review 8 ran its body.

The fix also introduces nothing a guard would object to:

```
$ python3 -   (both new strings vs leak_words, the no-rates lint, the withdrawn phrases)
factivity_note        leak words present: []  percent sign: False  solidus digit/digit: False
why_recorded          leak words present: []  percent sign: False  solidus digit/digit: False
withdrawn phrase 'nothing is executed on this machine': before=1 after=1
withdrawn phrase 'every operator line, verbatim':       before=1 after=1
```

Both withdrawn phrases still occur exactly once, at the sites that quote them as withdrawn, so the C2
guard's reason for being green is unchanged by this diff.

---

# 2. Review 8's blocker: fixed, and the new sentence is true

`prereg.json:1325`, in full:

> The frozen file must not claim coverage the harness does not have. A probe line that would not render
> would have cost this study eighteen takes -- one whole task row, two halves by three running models
> by three takes -- and it was caught before any take ran. The one task the render test does not cover
> is the one whose lines were written for a different pre-registration.

Clause by clause.

**"would have cost"** — the auxiliary review 8 asked for, and the fix went further than the one word:
"and it was caught before any take ran" states the factivity outright instead of leaving it to the
verb. Supported by `prereg.json:3` ("No take may run against this file"), `PROTOCOL.md:21` ("Nothing
here has been graded") and `PROTOCOL.md:24` ("No take runs before the freeze commit is pushed").

**"eighteen takes -- one whole task row, two halves by three running models by three takes"** — the
factorisation is new, and it recomputes from the file rather than from the sentence:

```
$ python3 -   (n, model_status, row arithmetic)
n=3 running models=3 (claude-haiku-4-5-20251001, claude-sonnet-5, claude-opus-5)
one task row = 2 halves x 3 running models x 3 takes = 18
all six tasks = 108
```

```
$ awk 'NR==87||NR==88||NR==89' PROTOCOL.md
Exactly **n = 3** graded takes per half per model, and no retakes.
Six tasks, two halves, three running models, three takes: **108** takes.
The two local control takes are dropped with the tier.
```

18 x 6 = 108, so "one whole task row" is the right unit and the words are `PROTOCOL.md:88`'s own.
"three running models" is right because `model_status` carries `runs: false` for the two local models.

**The defect it describes is real and is the one the file records.** The probe line was
`number-fidelity`'s, at `prereg.json` `tasks[2].positive.operator_script[2]`, whose `line_note` says
the driver "could not render the template at all. This task would have raised on its first take."
That task is scripted here, so the render test covers it — which is the sentence's point: the gap it
warns about is the one place that check does not reach.

**"The one task the render test does not cover is the one whose lines were written for a different
pre-registration."** True and corroborated in the same file: `carried_task_coverage.task` is
`confounded-design`; `:1323` says the render test "skips it"; `:1316` says it "does NOT cover
confounded-design, whose operator script is carried from the first study"; and the task's
`operator_script` is the reference string `evals/prereg.json — carried verbatim`, a different
pre-registration file.

Review 8's blocker is closed. Nothing in the rewritten sentence contradicts the file.

---

# 3. BLOCKER — `prereg.json:1327`: the sweep report claims more than the sweep found

The added key:

```
$ sed -n '1327p' prereg.json
  "factivity_note": "No take has run. Every statement in this file about takes being cost, spent or lost
  is a COUNTERFACTUAL about a defect that was caught, and is written in the conditional. One of them was
  not, and said a defect 'cost this study eighteen takes' when the cost was averted -- a false statement
  about the record, inside the very key that exists to stop the file claiming what the record does not
  support. The whole file was swept for the same shape after it was found."
```

Sentence 1 is true. Sentence 3 is true: the quoted fragment is verbatim from the pre-fix string, and
the key it sat in is `carried_task_coverage`, whose first clause is the coverage rule. Sentence 2 is
the blocker.

I ran the same sweep the note reports — every string in the file mentioning a take, split to the
sentence, kept where the sentence says something happens to a take, and classified by whether it is
written in the conditional:

```
$ python3 -   (walk every string; keep sentences matching \btakes?\b and a loss verb; mark COND on would/could)
strings mentioning take/takes: 25 distinct, 56 occurrences

COND  x6   tasks[0].positive.operator_script[1].recovery.why  ... the take would publish as `did-not-reach`
                                                              -- a model failure the model did not earn,
                                                              across three tasks and half the takes.
COND  x2   tasks[2].positive.operator_script[2].line_note     This task would have raised on its first take.
COND  x1   tasks[5].label_mapping                             Without the mapping ... every control take
                                                              would grade incorrect while looking like a result.
COND  x1   carried_task_coverage.why_recorded                 A probe line that would not render would have
                                                              cost this study eighteen takes ...
INDIC x6   tasks[0].positive.operator_script[0].recovery.why  An agent that sends T1 and stops leaves the menu
                                                              marker unheld on turn 1, and the take publishes
                                                              as `did-not-reach` -- the same defect the T3b
                                                              recovery closes ...
INDIC x1   local_tier.dropped.control_takes                   the two local control takes are dropped with the
                                                              same reason
INDIC x12  predictions[3].note                                ... is never scored, because the cell produced
                                                              no take.
INDIC x1   tasks[5].pilot.note                                ... never counted as one of its three takes ...
INDIC x1   models_note                                        A model that never produces a graded take
                                                              publishes as `not run — <reason>` ...
```

Four sites are conditional counterfactuals about caught defects, exactly as the note says. Five are
not, and two of them break the note outright.

**`prereg.json:1252` breaks the first conjunct.** "the two local control takes are dropped with the
same reason" is a statement about takes being lost that is not a counterfactual and not about a
defect. It is a real, dated decision, recorded as fact three keys deep in a block named `dropped`,
beside a key named `what_it_costs` (`:1253`), and repeated in the protocol at `PROTOCOL.md:89`. It
is the largest take loss the study has: `model_status` carries `runs: false` for both local models,
which is 2 models x 6 tasks x 2 halves x 3 takes of planned measurement that will not happen, plus
the two control takes at `:1252`. The note tells a reader that every such statement in the file is
counterfactual. This one is not, and a reader who believes the note will misread the one loss the
study actually took as a hypothetical.

**`prereg.json:117` breaks the second conjunct**, six times, inside the note's own subject matter.
The T1 recovery's `why` describes a defect that was caught — "the same defect the T3b recovery
closes ... Found by a reviewer reading the contract's Process" — and describes its cost to a take in
the present indicative: "the take publishes as `did-not-reach`". Its sibling recovery at `:131`
describes the identical outcome with "would leave", "would send", "the take would publish". The file
writes the same shape both ways; the note says it writes it one way.

The counter-reading, stated so the ruling is auditable: read "cost, spent or lost" as three literal
verbs and the note's extension shrinks to the four COND rows, and it is true. I do not think that
saves it. A note whose job is to stop a stranger reading take-loss language too broadly cannot itself
depend on being read narrowly, and the two sites above are found by the first grep a stranger runs —
`grep -n takes prereg.json` returns `:1252` on the same screen as `:1327`.

Why a blocker and not a follow-up: it is false as written in the file `PROTOCOL.md:141` makes
read-only, changeable afterwards only by amendment, and it is a false claim about the record inside
the key added to prevent false claims about the record. That is review 8's blocker in a new sentence.

**Fix, one clause.** Scope the subject to what the note is for:

> Every statement in this file that charges a cost in takes **to a defect** is a COUNTERFACTUAL about
> a defect that was caught, and is written in the conditional.

Checked against the sweep above, that scope admits exactly `carried_task_coverage.why_recorded`,
`tasks[0].positive.operator_script[1].recovery.why`, `tasks[2].positive.operator_script[2].line_note`
and `tasks[5].label_mapping` — all four conditional, so the sentence becomes true. `:1252` and `:117`
fall outside it, correctly: neither charges anything to a defect. Optionally, and worth the words, a
second clause naming the real loss: "The only takes this file records as actually lost are the local
tier's, dropped by decision at `local_tier.dropped`."

---

# Findings, non-blocking

**F1. `prereg.json:1327`, "One of them was not" has no referent in the set it quantifies over.**
Sentence 2 is present tense and describes the file as it now stands; the statement that "was not" a
counterfactual no longer exists in that file, because this diff rewrote it. The note conflates the
current set with the pre-fix one. Nothing false, and the scoping fix above is the natural place to
also write "One of them was not, before this fix". One clause.

**F2. `prereg.json:954`, the pilot is a real run and "No take has run" survives only by definition.**
`tasks[5].pilot` records a model (`claude-opus-5`) and a `transcripts_commit` (`050d0d7`), so
something was run and its transcripts are committed. The note's first sentence stays true only
because the same key says the pilot is "never counted as one of its three takes". That is a
deliberate and correctly written distinction, not an error — but the note is the file's factivity
key, and a reader who finds the pilot after reading "No take has run" has to reconstruct the
distinction for themselves. Follow-up: name the pilot in the note, one clause.

**F3. `prereg.json` `harness.version_range_note` writes a take in the indicative past.** "the
published section states the range every take ran under" — a rule about what the published section
will say, not a claim that a take has run, so nothing is false. It is the one other place a factivity
sweep stops, and it is worth a "will have run" if the note is being edited anyway.

**F4. Review 8's F1 through F9 are unresolved and are not re-argued here.** None was fixed by this
diff, which touched one string and added one key. They remain follow-ups on review 8's terms.

---

# Limitations of this pass

- `test_harness.py` and `prereg.py` are not in this directory, so no harness check was executed or
  re-executed:

```
$ ls test_harness.py prereg.py
ls: prereg.py: No such file or directory
ls: test_harness.py: No such file or directory
```

  `EveryOperatorLineRenders`, `MarkersAreTemplateBytes` and the C2 guard were verified only to the
  extent the file itself allows: the 38 scripted lines are unchanged either side of the diff, and
  both withdrawn phrases still occur exactly once. Review 8's verification of those tests' bodies is
  taken as read and was not reproduced.
- **The fix adds a top-level key, and the check that this is safe could not be re-run here.** Review
  8 established with `grep -n "len(.*keys\|assertEqual(set\|sorted(.*keys" test_harness.py` that no
  check asserts over the top-level key set; that grep cannot be repeated in this directory. Whoever
  freezes should re-run it against the harness in force, since this diff takes the file from 42 keys
  to 43.
- Review 8's F9 (the shallow copy in the C2 guard) and its open item on `prereg.load()` resolving to
  the file in force are both untestable from here and still open.
- Scope was the one-string, one-key diff and what it reaches. The design was not re-reviewed, and no
  finding review 8 carried as a follow-up was re-raised as anything else.
