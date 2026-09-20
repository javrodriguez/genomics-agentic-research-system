# Gate card 1 — three decisions before the freeze

Every number here re-derives from a command. Nothing below is the run's to settle.

| Re-derive with | What it shows |
|---|---|
| `python3 evals/gap-study-3/allowlist.py --derive` | the 22 entries, each with the transcript and line it was quoted from |
| `python3 evals/gap-study-3/fixture_walk.py --check` | the leak verdict on all five committed walks |
| `python3 evals/gap-study-3/fixture_walk.py --finding` | what actually capped round 2's one incomplete cell |
| `python3 evals/gap-study-3/fixture_walk.py --coverage` | which halves the walks cover, and why |

---

## A. The entries of the permission condition

**What is derived.** 22 entries, from 364 pre-probe commands in 52 of round 2's committed transcripts. Every
entry is a verbatim prefix of a command an agent actually ran on that task, carries the transcript and line
it came from, and is never a bare binary. 15 name a program or subcommand of the system under test
(`route`), 5 are a flag against any target (`shape`), and 2 let the caller supply the program text itself
(`python3 -c`, `python3 -`, marked `arbitrary`).

**What the walks measured.** Zero denials, in five walks, on two models, including four sessions that ran
with no approval surface at all. The condition carries the route.

**118 of the 364 calls have no legal entry** — 109 of them a `cd` into an absolute path naming one run, which
no verbatim prefix could match in another run. The walks show that costs nothing under `auto` (the
classifier covers it) and nothing under `default` either, because the models reached for `cd gars && …`,
which two entries admit between them.

| Option | What it means |
|---|---|
| **A1 — pin all 22 (recommended)** | The condition is exactly what the derivation produces. Zero denials behind it. Narrowing it from here would be a choice made after seeing the route, and every denial it caused would be a harness condition published in place of a measurement. |
| A2 — drop the two `arbitrary` entries | Narrower on paper. But round 2's larger models used `python3 -c` before the probe on these tasks, so dropping it makes this round's condition *narrower* than round 2's for them — a new asymmetry on the axis this round exists to make uniform. |
| A3 — the 15 `route` entries only | Narrowest. Highest chance of a denial mid-route, and a denial is published as a condition of the harness rather than as a reading of the model, so cells bought this way are cells not measured. |

---

## B. The permission mode, and whether this round can measure the smallest model at all

**What is measured.** In four walks of four, the smallest model's sessions recorded `default` where `auto`
was passed. The larger model's recorded `auto`. This reproduces the pre-study's finding on this round's own
driver, and it is systematic rather than incidental.

**Why that is now a problem.** Round 2 wrote the flag it passed into both sides of the checker's
constant-binding rule, so the rule compared a constant with itself and could not fail. This round's driver
records what the session recorded, which is what makes the rule mean something — and the criterion says a
mismatch is a rehearsal. Four of four means **every take of that model routes as a rehearsal, its three
attempts exhaust the cap, and all six of its cells publish unmeasured.** The round would not measure the
model it was built to measure.

| Option | What it means |
|---|---|
| **B1 — pre-register the mode each model is expected to record (recommended)** | `auto` for the two larger models, `default` for the smallest, published in every cell. The assertion still bites: it catches a session drifting from what its model is known to record. The round measures all three models. Cost: the expected mode becomes this round's own key rather than one carried from round 2, and the assertion moves from the copied checker to a checker of this round's own — the criterion's purpose kept, its literal wording not. |
| B2 — follow the criterion literally | Six cells publish unmeasured with the reason quoted. Honest, and the record would show exactly why. But the question the pre-study was run to settle stays exactly where it was, and this round spends its budget to say so. |
| B3 — drop the smallest model, as round 2 dropped the local tier | Cleanest design: two models, three tasks, no asymmetry. Abandons the thing the pre-study established — that the model reaches the probe once its commands are admitted. |

---

## C. The refusal that capped round 2, which is live in this round

**What is measured.** Round 2's one incomplete cell was capped by three attempts refused with
`read-outside-the-checkout`. **None of the three named this checkout.** All three named the session's own
scratch redirect to a hard-coded temp file, and the harness's own background-task output file — three of the
first, six of the second, zero of this checkout. The fixture is not implicated: it is generated inside the
run tree on both halves and records no path of this repository, and the static verdict over all six halves
is clean.

So the fixture re-cut this round was told to make would have prevented none of them, and one of this round's
own walks already carries the harness's background-task path. The take checker is pinned byte-identical, so
this round cannot change how it reads either source.

| Option | What it means |
|---|---|
| **C1 — publish it as a limitation and let it fall where it falls (recommended)** | A cell that hits it publishes capped, with the refused path quoted, and the finding is published as a finding. The instrument stays byte-identical to round 2's, which is the whole basis for measuring the same thing twice. A round 4 fixes the checker. |
| C2 — fix the checker now | Ends the byte-identical claim. This round would no longer be measuring with round 2's instrument, and nothing it published could be set beside round 2's for the same tasks. |
| C3 — pre-register a routing rule for exactly these two path shapes | The driver routes an attempt whose only outside paths are the harness's own task-output file or a session scratch outside every study root, rather than the checker changing. Middle path. Needs the two shapes pinned tightly enough that it cannot become the hole the rule exists to close. |

---

## What is NOT on this card

The comparative sentence, anything said about a model beyond counts and reserved labels, and the
`docs/EVALS.md` section. Those stay yours and none of them is needed to freeze.

## Also worth knowing

Committed transcripts carry the account name where an agent ran `ls -la`, because the scrub removes the
account email only and nothing else — the established ruling. This is not new: 71 of round 2's 106 published
transcripts already carry it, and 2 of the pre-study's 3. Round 3's walks follow the same rule, and
changing it is not this round's to do.
