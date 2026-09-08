# What was done with each finding of `prefreeze-1.md`

The reviewer read a copy of the draft pre-registration whose sha256 is the first line of its report,
in a directory holding only the study's own files and the system under test. It had no access to
this repository, to any record of how the study was built, or to anything about who commissioned it.

**Blindness was verified rather than asserted.** Its report and its full session log were searched
for every term that would indicate it had reached outside its inputs. Zero hits, both files.

The draft it read is byte-identical to the draft at the moment of the freeze, except for the folds
below, and the freeze commit body carries that diff.

## Folded — blocking, before the freeze

**F1 · four of five wait-point markers were not substrings of their templates.** Reproduced
independently before fixing: `comma-separated list of ids`, `confirm to create symlinks`,
`cannot start stage 01` and `approve as written?` were lowercased renderings of their template's
opening words and matched only case-insensitively. The driver happened to compare that way, and
that comparison was pre-registered nowhere. A stranger reimplementing the check from the frozen file
would have held no stage-00 or stage-01 marker, sent no probe turn, and published four of the six
tasks as each model failing — on letter case in a JSON string.

All five markers are now the templates' own bytes. The comparison rule is written into the
pre-registration as case-sensitive, the driver and the template grader both compare exactly, and
`test_harness.py MarkersAreTemplateBytes` asserts every marker is a byte substring of a pinned
contract. Proven to go red: lowercasing the markers fails that test.

This is the finding the reviewer said it would stop the freeze for, and it was right.

**F2 · the layer verdict was recorded per task but is only true per behaviour.** A task can enforce
one incorrect behaviour and be silent about another. `precondition-refusal` stops `ran-anyway` with
exit 3 and does not stop `invented` — and `invented` is the behaviour its probe elicits. Under the
old definition a model holding that task would not have counted as covering a gap; under the
corrected one it does.

Each task now records `layer.probed_behaviour` and the verdict observed for that behaviour, and
`covers the gap` is defined over the probed behaviour rather than the task.

**F3 · plan-gate's note said all twelve artifact rows were stubs.** True of the memory copy of that
project, which the system refuses outright; false of the completed run this fixture is taken from,
where all twelve are real. The note is removed rather than reworded, and the fixture's name-invariant
tree hash is pinned in its place.

**F4 · `reach_turn` was null on five of six tasks.** Set from each half's probe turn, and recorded
as an operator-turn index rather than a raw transcript index, which would shift with however many
tool calls an agent happens to make.

**F6 · two sources were named for the number `number-fidelity` grades against.** `cmd_inspect`'s
counts are now authoritative, because that is what the agent sees and what the contract calls the
only source of truth. The generator's manifest is named as a cross-check, and the fixture checker
asserts the two agree on every build.

**F7 · the no-rates rule forbade the shape the analysis plan prescribes.** Settled in one sentence:
the percentage sign and the solidus fraction are forbidden, the spelled form is the study's own
prescribed shape and is permitted. Written before the numbers exist, because afterwards choosing the
reading is choosing the presentation.

**F5 · the label decisions are written down** — the bounded answer to the recommendation probe, a
half-correction on `number-fidelity`, and what `proceeded` is read from on `plan-gate`.

**F12 · a committed control output carried an absolute path from the operator's machine.**
Normalised out.

## Declined, with a reason

**F5(a) · a distinct label string per half.** The reviewer asked that no one string be correct on
one half and incorrect on the other, as `proceeded` is on `plan-gate`. Not changed. A label names
what the agent did; correctness is a lookup against the half. Giving one behaviour two names by half
would put the verdict back inside the label, which is the split this design exists to keep. The pair
still does its job: an agent that proceeds on both halves fails the positive one, which is what a
matched control is for.

## Open, and named rather than closed

**F8, F9, F10, F11, F13** concern `confounded-design`'s key set, how walk coverage is described, the
scoreable prediction count, and a stage-00 wait point with no operator turn. They change no number
that exists today. They are recorded here so a reader can see they were raised and not yet acted on,
rather than discovering their absence.
