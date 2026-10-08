# The `declarations` candidate: is it eligible at the pinned tree?

Date: Thu 8 Oct 2026, 17:53 EDT (read from `date`).
Status: DRAFT for glitch-f3's ruling.
Lane: `w4g-cp4-declarations-eligibility`, on base `48f100563e68f4798defd96fb1bf483dd679c940`, reading the pinned GARS tree `844a4ce`.
Every line cited below was read in this lane with `git show 844a4ce:<path>` on a named file; no repo-wide search was run.

## Verdict

**Dropped.**
At `844a4ce`, stage 01 never asks the user for a missing or ambiguous strandedness declaration: the helper fills `auto` without a prompt, and the contract defers to that default, so round 4 runs 9 pairs.

The gate question is answered in full by question 1, so questions 3 and 4 (the library-prep literature) were not reached, as the brief directs ("say so in one sentence and stop there").
No web page was fetched in this lane, and no literature source is cited.

## Question 1: does the pinned stage 01 ask?

No file and no line at `844a4ce` asks.
The evidence, helper first, then the two stage contracts.

### The helper, `gars/_system/stage01_samplesheet.py`

- Lines 7-9: "This script decides what is TRUE. It never prompts, never proceeds past a gate on its own, and never writes unless told which gate the user cleared."
- Line 42: `STRANDEDNESS_VALUES = {"auto", "forward", "reverse", "unstranded"}`.
- Lines 79-88: the `rnaseq_bulk` samplesheet's `strandedness` column (line 86) comes from `config:strandedness`, and the format's source is `nf-core/rnaseq 3.26.0` (line 81).
- Lines 193-196: `CONFIG_RULES = {"strandedness": {"values": STRANDEDNESS_VALUES, "default": "auto"}}`.
- Lines 238-268, `read_config_scalar`: line 242 says "Absent file or absent key -> the rule's default."
  The code does exactly that: an absent file returns the default (lines 246-247), an absent key returns it (lines 258-259), and an empty value returns it (lines 262-263).
  A value outside the allowed set is a `config` failure (lines 264-267), which reaches the user as exit 1 and template T3, a validation failure, not a question.
- Lines 541-548: the only call site of `read_config_scalar` (line 544), which records either the value or that failure.
  The value then flows on unasked, into the counts (line 592) and the samplesheet.
- Lines 594-604, `config_unfilled`: only lines carrying `<REQUIRED` are listed as decisions still outstanding.
  An absent `strandedness` key carries no such marker, and the seeded value is `auto` (below), so in the seeded file strandedness is not listed.
  A hand-written `<REQUIRED` value for strandedness would be listed, but it is not an allowed value, so it fails at lines 264-267 with exit 1 and template T3, and never reaches T4.
- Lines 24-25 and 827-837, `EXIT_NEEDS_CONFIRM` (exit 2): emitted only for exclusions without `--confirm-exclusions` (lines 828-830, template T7) and for existing samplesheets without `--force` (lines 831-833, template T5).
  No path emits it for a declaration.

### The seeded settings file, `gars/_templates/config/rnaseq_bulk.yaml`

- Line 18: `strandedness: auto`.
- Lines 11-17 are a comment for the person reading the file: `auto` delegates to nf-core's RSeQC check, "Set it explicitly if the library prep is known", and this lab's measured answer (decision 0032) is that its TALL leukemia libraries are unstranded.
  That comment is advice in a file, not a step at which the agent asks.

### The stage 01 contract, `gars/01_prepare_samplesheets/CONTEXT.md`

- Line 22: "`_config/<Assay ID>.yaml` — read for `strandedness` only; absent is legal".
- Lines 109-111: "A column sourced from `_config/<Assay ID>.yaml` (such as `strandedness`) falls back to that key's documented default when the file or key is absent; an unrecognised *value* is a `config` failure rather than a silent default."
- Lines 38-40: "Never infer a missing experimental value" is illustrated by its next sentence with a blank base column of `samples.csv` (`condition`, `group`, `replicate`).
  Even read as covering strandedness, the rule forbids the agent guessing; it does not require asking, and the helper's documented default is not an inference by the agent.
- Lines 171-216, the Process: the only waits on the user are T7 for exclusions (step 6), T5 for existing outputs (step 7) and T8 for the optional deep integrity check (step 8).
  No step asks about strandedness or any other declaration.
- Lines 213-216, step 14: "Offer to write values they give you; never choose one yourself" applies to the `config_unfilled` keys, which never include strandedness (helper lines 594-604).
- Lines 271-275, the T4 note: name the `config_unfilled` keys and stop, because stage 02 resolves them from menus.
- Line 236, template T2: the stage reports the strandedness value in its table; it reports, it does not ask.
- Lines 219-221: "Add nothing else: no observations, no suggestions, no offers, no commentary about the data".
  An unprompted question about the library prep at stage 01 would itself break this rule, the same reason D5 dropped `confounded-design-unprompted`.
- Line 223, the standing "bounded voice" exception: if the user asks a direct question, the agent answers it from the workspace's own files and restates the pending wait point.
  It allows answering, not asking, so it adds no declaration step.
- Line 50: "If you believe a step should deviate, stop and ask" is the general deviation rule, not a declaration step.

### The stage 00 contract, `gars/00_initialize_project/CONTEXT.md`

- A case-insensitive search for `strand` inside this one file's `git show` output finds no line.
- Line 393: stage 00 seeds `_config/<Assay ID>.yaml` "with every derivable value filled and the scientific decisions marked `<REQUIRED>`"; the template seeds strandedness as `auto` (template line 18), so it is seeded as filled, not as a decision outstanding.

## Question 2: `auto` is an allowed value

The contract supports one reading: `auto` is the documented default (contract lines 22 and 109-111; helper lines 193-196 and 242) and the seeded value (template line 18).
On the trap half, a model that keeps or declares `auto` would be following the contract, and "ask, don't guess" has no contract step behind it.
The seeded file's own comment does separate the halves for a reader ("Set it explicitly if the library prep is known", template line 14).
But the stage 01 contract has no step that either asks about or writes strandedness: step 14's offer to write values covers only `config_unfilled` keys (lines 213-216), and lines 219-221 forbid other offers.
So neither half's right move is a stage 01 contract move: the trap's ask has no step, and the normal half's declaration has no step either.
This answer was reached offline and rests on the same evidence as question 1; it does not change the verdict.

## Questions 3 and 4: ambiguity and the mapping to the pinned values

Not reached: question 1 drops the candidate, and the brief says to stop there.
The per-wording value table is therefore empty, by design, and no kit, manual or nf-core page was opened.

| Wording | Allowed values that fit | Kits and sources |
|---|---|---|
| (not reached) | (not reached) | (not reached) |

## Question 5: the verdict

Dropped, for the reason in question 1: no file or line at `844a4ce` asks the user for a missing declaration; the helper defaults strandedness to `auto` and the contract calls an absent key legal.
Question 2 sharpens the same reason: on the pinned stage 01 contract neither half's right move has a step behind it.

## The counts that follow

Quoted from `plans/gap-study-round-4/CP4-requirements.md`, lines 17-21, without re-typing a figure:

- **Counts that follow**, the same in CP5's pre-registration:
  - arm A: 9 pairs × 2 halves × 10 tries × 3 models = 540 tries, or 600 with `declarations`;
  - arms O and G (D8 B2): 9 × 2 × 10 × 2 = 360 tries each, or 400 with `declarations`;
  - in all: 1,260, or 1,400 with `declarations`;
  - cells: (arm, task, half, model) = 9 × 2 × 7 = 126, or 140 with `declarations`.

With the candidate dropped, round 4 takes the 9-pair figures on each line.

## Open questions for glitch-f3

1. Stage 02 was not read: the gate D5 names is stage 01, and stage 02's contract and `_system/configure.py` are outside this lane's named files.
   If a later stage turns out to ask about strandedness, that is a new candidate, cut and gated on its own, not this one.
2. `_references/config_schema.md` (cited by template line 8) was not read; it is not a stage 01 file.
3. The drop's reason, if glitch-f3 rules it, goes into `docs/validity/declarations.md` by the lane lead; this draft does not write it.

## Sources

All offline, read with `git show 844a4ce:<path>`:

- `gars/_system/stage01_samplesheet.py`, lines 7-9, 24-25, 42, 79-88, 193-198, 238-268, 541-548, 592, 594-604, 827-837.
- `gars/_templates/config/rnaseq_bulk.yaml`, lines 8, 11-18 (line 14 quoted).
- `gars/01_prepare_samplesheets/CONTEXT.md`, read in full (355 lines); cited lines 22, 38-40, 50, 109-111, 171-216, 213-216, 219-221, 223, 236, 271-275.
- `gars/00_initialize_project/CONTEXT.md`, line 393, and the in-file search for `strand` (no hit).
- `plans/gap-study-round-4/CP4-requirements.md`, lines 17-21 (the counts).

No web source was fetched, so none is cited.
