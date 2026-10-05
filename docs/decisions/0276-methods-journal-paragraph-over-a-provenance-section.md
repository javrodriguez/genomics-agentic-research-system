---
date: 2026-10-05
status: standing
kind: decision
touches:
  - gars/_system/claims/render_methods.py
  - gars/tests/test_render_methods.py
  - gars/tests/fixtures/methods/complete.md
  - gars/tests/fixtures/methods/sparse.md
symptoms:
  - a generated Methods section reads as a manifest dump, with hashes and withheld-path notes in the paragraph
  - a journal-paragraph sentence states a tool, step, order or person that no record field holds
  - a missing record field leaves a guessed or misleading clause in the Methods paragraph
---
# The Methods page opens with a journal paragraph; the record trail becomes its Provenance section

The owner typed "B" on 5 October 2026 in the Row-orchestrator's window, after reading the renderer's golden page: a short journal-style paragraph on top, filled by fixed frames from record fields, with hashes, withheld-path notes and the Sources map moved into a Provenance section below it.
It reached this lane relayed by the Row-orchestrator.
The sentence frames below are the lane's, under the owner's standing delegation of 23 September 2026; the owner approves them before any public use, and no other sentence in this record is his.
This record amends [0236](0236-methods-paragraph-rendered-from-the-record.md), which stays byte-identical; everything 0236 decides holds unless this record says otherwise.

## Context

0236's page is accurate but reads as a manifest dump: its paragraph states hashes, record fingerprints and withheld-path notes, one workflow field after another.
A reader of a paper needs a few sentences that say what was run, against which reference, with which design, and how the plan was approved, and the trail that proves each value somewhere below.
The owner's readability rule (5 October): the paragraph carries only what changes a reader's understanding of the method; hashes and caveats go in Provenance; three to six sentences for a typical two-workflow run.

## Decision

1. **Layout.** `# Methods` holds the journal paragraph, one sentence per physical line.
   Then `## Provenance` holds 0236's paragraph lines unchanged, and 0236's sections follow as `### Parameters`, `### Software used`, `### Citation`, `### Records read` and `### Sources`. Nothing is dropped.
2. **Every sentence is one fixed frame**, no model, no network. A clause appears only when its field is recorded and can be shown; a missing, empty or path-like field drops its clause, and Provenance states the field as `not recorded` or withheld. The paragraph never says "not recorded" except where a frame names it below.
3. **Plain words or a code span.** A value made only of ASCII letters and digits joined singly by `. _ + : / -` (`3.26.0`, `star_salmon`, `nf-core/rnaseq`) is shown as plain words, since no Markdown can be built from those characters; any other value keeps 0236's code span, and a path-like value is withheld as in 0236.
4. **The frames** (`[ ]` is a clause that is dropped when its field is not shown):
   - `prose-run`, per manifest whose `predicate_facts/status` is `COMPLETE`: `{subject} was run[ through the GARS wrapper {workflow_name}][ against the {reference/build} reference genome[ (annotation release {reference/annotation_release})]][ with {items}].`
   - `prose-configured`, the same frame for any other status: `… was configured …; its run status is {status | not recorded | a path-like value, withheld}.` A manifest that does not record completion is never said to have run.
   - The subject is the pipeline's own name and version when the run's versions files hold exactly one `Workflow/<name>` entry other than `Workflow/Nextflow` (nf-core's `software_versions.yml`), and the wrapper clause then names `workflow_name`; otherwise it is `{workflow_name} {workflow_version}`, or `A workflow whose name is not recorded` / `A workflow whose recorded name is withheld` (with ` (version {workflow_version})`).
   - The reference clause appears only when `reference/comparison` is `matched`, so the build named is the registry's and the run's own files matched it; any other registry result stays a Provenance line.
   - `{items}` are, in this order and joined as a list: `the {params/aligner} aligner`, `the design formula {params/formula}`, `the contrast {params/contrast}`. A contrast of exactly three plain parts reads `{numerator} versus {denominator} (factor {factor})`, GARS's own `factor,numerator,denominator` form (`_templates/config/rnaseq_bulk.yaml`); any other contrast is shown whole.
   - `prose-agent-all`: `Every workflow records the agent model {agent_model}.`, when two or more manifests record one identical agent model other than `none`; otherwise, per manifest, `prose-agent`: `{subject name} records the agent model {agent_model}.` or `prose-agent-none`: `{subject name} records no agent model.`; an absent agent model adds no sentence.
   - `prose-approval`, only after 0236's binding check holds: `The analysis plan was approved[ on {D Month YYYY} at {HH:MM:SS} UTC] {by the approver the run recorded | with no approver named in its approval record}, and its approval record is bound to the plan's exact text.` The timestamp is the record's own, already validated; the actor is consulted for presence and never printed.
   - `prose-history`, per history entry 0236 matches to the approved analysis: `The project's history records the approved analysis as complete[ on {date}][, with the agent model {Model}].`
   - `prose-closing`, always: `Parameters, software versions and container images are listed below; every value traces to the run's records (Provenance).`
5. **Traced like every other line.** Each sentence has a Sources entry listing the fields it used, and the test's oracle rebuilds each sentence from those fields and derives from the records which sentences and clauses must appear.

## Rejected alternatives

- **"Approved before execution".** No field the renderer reads orders the approval against the analysis run: `cmd_verify` checks that the approval holds at verification, and the history's date has no time. The frame states the approval's time and its binding to the plan, and no order.
- **A table of display names and methods** (`star_salmon` as "STAR–Salmon", `rnaseq-de` as "differential expression was tested with PyDESeq2"). Each would state knowledge the renderer holds about a wrapper, not a value the run recorded, and would drift silently when a wrapper changes. The pipeline's own name is taken only from its own versions file.
- **Plain text for every value.** Record text could then add emphasis, links or HTML to the paragraph; values outside the plain set keep their code span.

## What this does not close

- **D1** The paragraph names no tool beyond the pipeline's own versions entry: a local wrapper's statistics package (PyDESeq2 for `rnaseq-de`) is listed under Software used, not named in a sentence.
- **D2** Only `aligner`, `formula` and `contrast` reach the paragraph; every other parameter stays a Provenance line.
- **D3** A plain value can read like the fixed words around it; Provenance shows the same value in a code span, and the Sources entry names its field.
- **D4** The wording is the lane's; the owner judges the frames before any public use (0236 D6 stands).
- **D5** 0236's residuals stand, D5 above all: no real run's records have been rendered.

## Test

`python3 -m unittest discover -s gars/tests -p test_render_methods.py` (still 16 tests, so the suite total does not move) on Python 3.8 and 3.12.
Both goldens carry the paragraph; the oracle restates every frame and rebuilds each sentence from its cited fields; `test_missing_and_empty_values_read_not_recorded` drives each dropped-clause path (name missing or withheld, version, status missing, failed or withheld, reference missing, unmatched or without build or release, formula, contrast, parameters, agent model missing or `none`, the pipeline's own name found, ambiguous or without a version, the approval time and approver, the history's model, an unmatched history) and pins each resulting paragraph.
It must fail when a paragraph value differs from its field, a dropped clause is filled, "configured" becomes "run" without a `COMPLETE` status, a sentence is added or cites the wrong manifest or field, the approver is named, or a path-like value reaches the paragraph through any clause.

## Status

Standing. The change record for the Methods paragraph's frames; the protected-change approval is written at the landing as 0277, and the public push waits for the owner's word.

## Date

2026-10-05
