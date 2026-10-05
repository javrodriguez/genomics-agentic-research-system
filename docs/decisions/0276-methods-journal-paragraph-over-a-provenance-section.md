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
  - an s3:// or other storage URI in a parameter or command line prints a runs bucket name, which can hold the cloud account id
  - Records read prints the sha256 of a record holding the actor's user name, a home path or a bucket, an offline oracle for the withheld value
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
3. **Plain words or a code span.** A list, dict, number or boolean is set in a code span with every control, format and separator character flattened, as under Provenance. A string made only of ASCII letters and digits joined singly by `. _ + : / -` (`3.26.0`, `star_salmon`, `nf-core/rnaseq`), and not starting with `www.` (which GitHub's Markdown turns into a link), is shown as plain words, since no Markdown structure or link can be built from it; any other value, and every number or boolean, keeps 0236's code span, and a path-like value is withheld as in 0236.
4. **The frames** (`[ ]` is a clause that is dropped when its field is not shown):
   - `prose-run`, per manifest whose `predicate_facts/status` is `COMPLETE`: `{Subject} was run[ through the GARS workflow {workflow_name}][ against the {reference/build} reference genome[ (annotation release {reference/annotation_release})]][ with {items}].`
   - `prose-configured`, the same frame for any other status: `… was configured …[; its run status is {status | not recorded}].` A manifest that does not record completion is never said to have run; a path-like status drops the clause.
   - The subject is the pipeline's own name and version when the manifest's `predicate_facts/wrapper_kind` is `nextflow` and its versions files hold exactly one `Workflow/<name>` entry other than `Workflow/Nextflow` (nf-core's `software_versions.yml`), and the workflow clause then names `workflow_name`; otherwise it is `{workflow_name} (workflow version {workflow_version})`, or `A workflow whose name is not recorded` / `A workflow whose recorded name is withheld`, so the pinned version is never read as the wrapper's own.
   - The reference clause appears only for an aligning pipeline (`predicate_facts/wrapper_kind` is `nextflow`) whose `reference/comparison` is `matched`, so the build named is the registry's and the pipeline's own FASTA matched it; a counts-based step reads no genome, and any other registry result stays a Provenance line. The annotation release is added only when the run passed an annotation (`params` holds a `gtf` key, cited for its presence as `params/gtf?`): a FASTA-only pipeline such as nf-core/methylseq still records `matched` with the registry row's release, which it never used.
   - `{items}` are, in this order and joined as a list: `the {params/aligner} aligner`, `the design formula {params/formula}`, `the contrast {params/contrast}`. A contrast of exactly three plain parts reads `{numerator} versus {denominator} (factor {factor})`, GARS's own `factor,numerator,denominator` form (`_templates/config/rnaseq_bulk.yaml`, read by `rnaseq_de.py`); any other contrast is shown whole.
   - `prose-agent-all`: `The agent model recorded for every workflow was {agent_model}.`, when two or more manifests record one identical agent model other than `none`; otherwise, per manifest, `prose-agent`: `The agent model recorded for {name} was {agent_model}.` or `prose-agent-none`: `The record for {name} names no agent model.`, where `{name}` is the pipeline's name when the run sentence named it, else the workflow's. An absent agent model adds no sentence, and `none` beside a recorded model step adds none either (the record contradicts itself; Provenance states both halves).
   - `prose-approval`, only after 0236's binding check holds. When the approval record's `plan_path` names a stage 03 plan (`03_custom_analysis/<slug>/PLAN.md`, consulted, never printed): `A separate custom analysis was planned, and its plan was approved {by the approver named in its approval record | with no approver named in its approval record}.` Otherwise (unreachable from `cmd_approve`, which always writes a stage 03 path) the sentence opens `An analysis plan was approved …`. The paragraph says "named in its approval record" rather than 0236's "the run recorded", because in the paragraph "the run" would point back at the workflows, which record no approval; 0236's Provenance line keeps its phrase. Neither names anyone. The binding to the plan's bytes is a Provenance fact: the approval line appears only when it holds. The workflows are never said to be approved; both fixture manifests record `approval_gated: false`. No date is stated: the approval's timestamp is a UTC instant and the history's date is the agent's local day, so two zone-free dates side by side could read as the analysis completing before its plan was approved (review r3 reproduced it: approved 01:30Z on 30 September, completed on the local 29 September). Both dates stay in Provenance with their own form.
   - `prose-history`, per history entry 0236 matches to the approved analysis: `The project's history records that custom analysis as complete[, with the agent model {Model}].` No date, as above.
   - `prose-closing`, always: `Parameters, software versions and container images are listed below, or marked not recorded; every value traces to the run's records (Provenance).`
5. **A storage URI is withheld** (amends 0236's point 5, which showed `s3://…`): a value holding `s3://`, `s3a://`, `s3n://`, `gs://`, `gcs://`, `az://`, `abfs://`, `abfss://`, `wasb://`, `wasbs://` or `file://`, in any letter case, with no letter, digit or one of `+ . -` glued before the scheme, reads `a path-like value, withheld` under Provenance and drops its clause in the paragraph.
   A runs bucket's name can hold the cloud account id, and nextflow's `-work-dir s3://<bucket>/…` reaches a parameter or the command line; the Row-orchestrator relayed this leak on 5 October 2026, found and reproduced by the reproduction-package plan's reviewers.
6. **A record's sha256 is not published when it would confirm a withheld value** (amends 0236's `## Records read`): a printed hash of a record that holds a user name, a home path or a bucket lets anyone confirm a guess offline.
   A manifest or approval record holding a path-like string anywhere (a storage URI included), an approval record that names an actor or a plan path at all, and a history whose text holds a path-like value read `- <record>: sha256 not published, since the record holds values this page does not print.`, cited `<record>:withheld`; any other record keeps its hash.
   The plan keeps its hash: it is the binding the approval line states (D11). The Row-orchestrator relayed this finding from the reproduction-package plan's review on 5 October 2026.
7. **The hashes of commands.sh and the assay config are not printed** (amends 0236's `config` and `command` lines): the producer writes the absolute home path into both (`commands.sh`'s submit line, the config's `work_dir`), and both are templated, so a printed hash confirms a guessed user name and project offline (review r2, reproduced with 28 guesses, one match). Each reads `not published, since the file names local paths`, cited from its field; an absent field still reads `not recorded`.
8. **Traced like every other line.** Each sentence has a Sources entry listing the fields it used, and the test's oracle rebuilds each sentence from those fields and derives from the records which sentences and clauses must appear.

## Rejected alternatives

- **"Approved before execution".** No field the renderer reads orders the approval against the analysis run: `cmd_verify` checks that the approval holds at verification, and the history's date has no time. The paragraph states no date and no order; the binding and both dates stay in Provenance.
- **A table of display names and methods** (`star_salmon` as "STAR–Salmon", `rnaseq-de` as "differential expression was tested with PyDESeq2"). Each would state knowledge the renderer holds about a wrapper, not a value the run recorded, and would drift silently when a wrapper changes. The pipeline's own name is taken only from its own versions file.
- **Plain text for every value.** Record text could then add emphasis, links or HTML to the paragraph; values outside the plain set keep their code span.

## What this does not close

- **D1** The paragraph names no tool beyond the pipeline's own versions entry: a local wrapper's statistics package (PyDESeq2 for `rnaseq-de`) is listed under Software used, not named in a sentence.
- **D2** Only `aligner`, `formula` and `contrast` reach the paragraph; every other parameter stays a Provenance line.
- **D3** A plain value can read like the fixed words around it; Provenance shows the same value in a code span, and the Sources entry names its field.
- **D4** The wording is the lane's; the owner judges the frames before any public use (0236 D6 stands).
- **D5** 0236's residuals stand, D5 above all: no real run's records have been rendered.
- **D6** The golden's nf-core sentence shows the fallback subject, since the fixture's versions file carries no `Workflow/` entry; a real nf-core run reads `nf-core/rnaseq v3.26.0 was run through the GARS workflow nfcore-rnaseq-wrapper …`, which a test case pins.
- **D7** Provenance's 0236 line labels the `wrapper` field (`rnaseq_bulk`) "GARS wrapper", while the paragraph names `workflow_name` as the GARS workflow; 0236's line stays byte-identical.
- **D8** The contrast reading follows the one wrapper that records a contrast today (`rnaseq-de`); a future wrapper writing another order would be misread until the manifest records the form.
- **D9** Two manifests of one workflow give indistinguishable sentences (0236 D10, now in the paragraph).
- **D10** A relative path or a bare number in a paragraph field (0236 D4) prints as plain words; no paragraph field realistically carries an account id, and no rule detects one beyond the storage-URI rule.
- **D11** The plan's sha256 stays published, in Records read and as the approval's `plan_sha256`: it is the approval's binding. A plan is free text, and confirming a guessed value in it means reproducing the whole document byte for byte.
- **D12** A GRCh38 run names no genome in the paragraph: the registry row's hashes are UNKNOWN, so the run records `comparison: missing`, and the build stays a Provenance line. A frame for a registry-named build with unverified hashes is the owner's call; the goldens use a matched fixture row.
- **D13** The storage-URI rule is a scheme list: an `https://` form of a bucket or an ECR registry host (`<account>.dkr.ecr…`) prints with its account digits under Provenance. No GARS producer writes these today.
- **D14** A pinned pipeline run with a local patch (nf-core/cutandrun 3.2.2, decision 0037) reads as the stock release: no manifest field records the patch.
- **D15** Two history entries matched to the approved analysis give two sentences, word for word alike when they name one model (the dates that told them apart stay in Provenance); a second verify of one analysis is rare.
- **D16** A model recorded as the producers' sentinel `unknown` (no `--model` given) reads as the plain word "unknown" in the paragraph.
- **D17** A versions file's sha256 is printed beside every key and value of that file; were a producer to write a path into one, its hash would become an oracle. None does today.

## Test

`python3 -m unittest discover -s gars/tests -p test_render_methods.py` (still 16 tests, so the suite total does not move) on Python 3.8 and 3.12.
Both goldens carry the paragraph; the oracle restates every frame and rebuilds each sentence from its cited fields; `test_missing_and_empty_values_read_not_recorded` drives each dropped-clause path (name missing or withheld, version, status missing, failed or withheld, reference missing, unmatched or without build or release, formula, contrast, parameters, agent model missing, shared, path-like or `none`, the pipeline's own name found, ambiguous, path-like, in a local wrapper or without a version, the approver, the history's model, an unmatched history; the reference clause on the nextflow manifest, where it can appear, with a path-like or bucket build or release), drives a path-like value into each clause on its own, pins that an approval at 01:30Z beside a completion on the previous local day states no date, and pins each resulting paragraph; `test_approval_binds_the_plan_and_never_names_the_actor` fails when the sha256 of an approval record naming an actor or a plan path, of a manifest or history holding a path or bucket, or of a manifest whose bucket sits only in a field the page never prints, appears on the page, or when a clean record's or the plan's hash goes missing, or when a manifest's `command.sha256` or `config_sha256` is printed.
It must fail when a paragraph value differs from its field, a dropped clause is filled, "configured" becomes "run" without a `COMPLETE` status, a sentence is added or cites the wrong manifest or field, the approver is named, or a path-like value reaches the paragraph through any clause; and `test_local_paths_are_never_printed` fails when a bucket URI in a parameter or a command line (`nextflow run … -work-dir s3://<bucket>/work`), or its account-id digits, reach the page.

## Status

Standing. The change record for the Methods paragraph's frames; the protected-change approval is written at the landing as 0277, and the public push waits for the owner's word.

## Date

2026-10-05
