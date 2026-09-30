---
date: 2026-09-30
status: standing
kind: decision
touches:
  - gars/_system/claims/render_methods.py
  - gars/tests/test_render_methods.py
  - gars/tests/fixtures/methods/
  - README.md
  - DEVELOPMENT.md
symptoms:
  - a Methods paragraph states a software version, parameter, reference or approval the run's records do not hold
  - a missing manifest field is guessed or given a default instead of read as not recorded
  - a generated Methods paragraph prints the approval record's actor (the OS user name) or an absolute path from the run
---
# The Methods paragraph, rendered from the run's own records

The owner's reply "defaults" of 29 September 2026 took the launch plan's default for this renderer: build it, and have the paragraph name "the approver" rather than the owner.
It reached this lane relayed by the lane's coordinator.
Every other ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026; no other sentence in this record is the owner's.
0237 is the delegated approval of the protected addition; this record does not write it.

## Context

A paper built on a GARS run needs a Methods section, and the specification's first invariant is no fabrication: every statistic, file, execution status and citation in an output resolves to a stored artifact, computation or resolved source (§1.3).
A model can write a fluent Methods paragraph, and nothing would stop it stating a version, a parameter or an approval the run never recorded.
GARS already records the facts a Methods section needs: manifest groups 2 to 7, 13, 16 and 18 (§8.1), the stage 03 plan and its approval record (decision 0042), and the project's `HISTORY.md`.
The report's methods section ([0155](0155-row-7-report-shows-manifest-values.md)) shows some of them as a structured block, with no paragraph a paper can use, no "Software used" list and no citation.
Two facts bound what can be said. No manifest group records who chose each value, and the approval record's `actor` is the operating-system user the approval ran as (`stage03_analysis.py`, `LAUNCH_ACTOR`), not a named person.
So the paragraph can say what ran, with what, and when the plan was approved; it cannot say which choices a model proposed or who, by name, approved them.

## Decision

1. **A new command, `gars/_system/claims/render_methods.py`** (Python 3.6, standard library only, no model, no network, no subprocess), run by a person after the run:
   `python3 _system/claims/render_methods.py --manifest <sub-stage>/reproducibility/manifest.json [--manifest ...] [--plan <analysis>/PLAN.md --approval <approval record> [--history HISTORY.md]] --out methods.md`.
   It opens only the files named on its command line, validates every one before writing, and writes the output atomically; a refusal exits 1 with `methods refused: <reason>` and leaves an earlier output byte-identical; a usage error exits 2.
   An `--out` that is one of the inputs is refused, so a record is never replaced by the page rendered from it: the same resolved path, or the same file under another spelling (a case variant on a case-insensitive filesystem, a hard link).
   The page keeps the mode of the output it replaces, or takes the umask's for a new one, since it is written to be shared.
   `--plan` and `--approval` come together, and `--history` needs them.
2. **The output is a closed vocabulary of 33 line kinds.**
   `# Methods` holds the paragraph, one sentence per physical line (Markdown joins them): per manifest, the workflow and its version, pipeline commit, GARS wrapper, GARS commit, template version and status; the failure class when one is recorded; the reference build, annotation release and the registry's FASTA and GTF sha256 (and, when the registry check is not `matched`, its result and the FASTA and GTF sha256 the run observed); the configuration sha256; the thread count; the `commands.sh` path and sha256; the agent model and each model-mediated step (model, provider, contract, and the contract's hash with the hash algorithm the record names, never assumed).
   Then, with a plan: "The analysis plan with sha256 … was approved at … by the approver the run recorded."; with a history, each entry recording that analysis as complete, with its date, model and template version.
   `## Parameters` lists each parameter in sorted-key order and the random seeds; `## Software used` lists GARS's commit and template version, each workflow's version and pipeline commit, every tool version the run recorded (from the pipeline's own versions file) and every container image with its digest or image-file sha256; `## Citation` names the GARS commit to cite and points at the repository's `CITATION.cff`; `## Records read` gives the sha256 of every input's bytes.
3. **Every line is traced.** `## Sources` lists, for every line above it, its kind and the record fields its values came from (`manifest1:/reference/build`, `manifest2:/params#3.value` for the fourth parameter in sorted-key order, `approval:/timestamp`, `history:#3/model`); a reference is always a fixed name or an index, never record text.
   Record values are set in CommonMark code spans and fixed words in plain text, so a reader sees which words are data; the span's fence is one backtick longer than any run inside the value, and every control, format, surrogate, line or paragraph separator character is shown as a space, so no record text can add a heading, a line, a list item, a table or HTML.
   A number is shown in the canonical form Python's JSON writer gives it, the form every GARS producer writes: a hand-written `1E2` reads `100.0`, the same double-precision value, and a subnormal such as `3e-324` reads in its rounded form (`5e-324`, the same double); refusing subnormals would also refuse real p-values such as `1e-310`, which print exactly.
4. **Absence is said, never filled.** A field that is missing, `null`, `[]`, `{}` or blank reads `not recorded`; a whole missing group reads as its own sentence ("Its reference genome is not recorded."). No default, no inference from another field, no model.
   One field decides another's sentence, once: an agent model recorded as `none` means no model-mediated step, so a missing `model_steps` then adds no absence sentence.
5. **A path-like value is withheld.** A value holding an absolute path reads `a path-like value, withheld`, because every wrapper records absolute input and output paths in `params` and those name a machine, not a method.
   An absolute path starts with `/`, `\`, `~/`, `~user/` or a drive letter (`C:\`, `C:/`) that no letter, digit or one of `. _ ~ / : \ -` precedes, or, right after a colon, with a single `/` (`host:/x`), three (a URL with no host, `https:///x`), `~/` or `~user/` (`user@host:~user/x`) or a drive letter (`x:C:\x`), or is a `file:` scheme (the letters are ASCII only); so `user@host:/x`, `>/x`, `|/x` and `--out=/x` are withheld, while `a/b`, `./b`, `~ condition` (a formula), `quay.io/…`, `s3://…` and `https://…` are shown.
6. **The approval binds the plan and names no one.** The approval line appears only when the approval record's `plan_sha256` is the sha256 of the plan's bytes (a mismatch, a missing or malformed `plan_sha256`, a malformed or impossible `timestamp` and a non-string `actor` are refused).
   It states the record's own UTC timestamp and says "by the approver the run recorded" when the record names an actor, or "with no approver named in its approval record" when it does not; the `actor` value and the absolute `plan_path` are never printed.
7. **The history names only the approved analysis.** An entry counts when its header reads `03_custom_analysis/<slug> — analysis complete`, `<slug>` being the folder of the approval record's `plan_path`; entries inside fenced blocks are not entries (`HISTORY.md`'s own header shows the entry format in one), fences read as CommonMark reads them (up to three spaces, three or more backticks or tildes, closed only by as long a run of the same character, an unclosed fence running to the end); each matching entry is rendered, and none reads "The approved analysis's completion is not recorded in the project's history."
8. **Refusals, not guesses, for malformed records**: unreadable or non-UTF-8 input, invalid JSON, a repeated key, `NaN` or `Infinity`, a number too large to hold (`1e400`) or a nonzero number too small to hold (`1e-400`, which would print as zero), a record nested too deeply to read, an input that is not a JSON object, or a present group of the wrong JSON type (an object group given as a list or text, an array group given as an object, a list entry that should be an object).
9. **Placement.** The renderer sits beside the report renderer under `gars/_system/claims/`, so it ships in every workspace; its approval (0237) and the smoke ceremony run at the landing.
   `render_report.py`, its template and its golden are byte-identical; the report's methods block (0155) is unchanged.
10. **Fixtures.** `gars/tests/fixtures/methods/` holds an nf-core collect manifest, a local-wrapper collect manifest and a prepare-only manifest, each written by the real `prepare` and `collect` through `test_manifest_groups`' own fixture machinery and then scrubbed: the run's temporary root is replaced by `/fixture-workspace`, and the `idempotency_key` by the 64-zero digest (a real key under a field named `*_key` reads to the secret scanner as a credential); both collect manifests still grade complete under `manifest_check.py`.
    The plan is `approved-plan.md` (the repository ignores every file named `PLAN.md`), the approval record has `cmd_approve`'s five keys with the actor `fixture-operator`, and the history carries `cmd_verify`'s stage 03 entry; `complete.md` and `sparse.md` are the renderer's goldens.

Tests move with the change: `gars/tests/test_render_methods.py` adds 16 tests, and the suite total moves from 1229 to 1245.

## Rejected alternatives

- **A model writes the paragraph from the record.** Fluent, and the one thing this renderer exists to rule out: nothing would bind its sentences to the fields.
- **Naming the approver.** The record holds an operating-system user, not a person; printing it would also publish a login name.
- **A parsed `CITATION.cff` citation.** Its `version` field reads `v0.10.0`, the tag 1,201 commits before this record's base commit `37a8d94`, so a citation parsed from it would not identify the code a run used; the citation line names the run's own GARS commit instead.
- **Quoting the plan's Method section.** It is intent, approved but not executed; stating it as what ran would say more than the record binds.
- **Extending `render_report.py`.** Its methods block and golden are a pinned coupling for another row's instrument (0155 D1); a separate command leaves them untouched.

## What this does not close

- **D1** Per-choice attribution: which value a model proposed and which a person chose is not in any record, so no sentence says it.
- **D2** A citation parsed from `CITATION.cff`, and citations for the pipelines themselves (nf-core asks users to cite each pipeline and its tools; those texts are not in the run's record).
- **D3** The truth of the records: the renderer states what they hold; `manifest_check.py` and the producers own whether they are right, and the history's entries are appended by the agent, which is why the paragraph attributes them to "the project's history".
- **D4** A path glued to a letter or digit before it (`x/abs/...`) reads as relative and is shown, and a relative path can still name a folder; the rule also withholds some values that are not paths (`x / y`, a closing HTML tag), which says less, never more.
- **D5** No real run's records have been rendered yet; the fixtures and the two real-producer tests are synthetic runs.
- **D6** The wording is the lane's; the owner judges the paragraph before any public use.
- **D7** A container pulled by tag on a backend that records no digest reads "digest not recorded"; the renderer says so and adds nothing.
- **D8** Any process running as the same operating-system user can still write an approval record (the residual [0042](0042-a-call-the-guard-cannot-judge-is-refused.md) names); the renderer binds the record to the plan's bytes, not to a person.
- **D9** The approved analysis is found by splitting the record's `plan_path` on `/`; the approval store is POSIX-only today (`stage03_analysis.py` imports `pwd`), and a path written with backslashes would read as not recorded.
- **D10** Two manifests of one workflow share their label in the Parameters and Software used lists; the Sources lines say which manifest each line came from.
- **D11** The history reader skips fenced blocks only: an entry inside an HTML comment or another HTML block, which a Markdown viewer hides, is read as an entry. It adds nothing an agent could not do by appending a visible entry (D3).

## Test

`python3 -m unittest discover -s gars/tests -p test_render_methods.py` (16 tests) is the acceptance, on Python 3.8 and 3.12.
Its oracle is the test's own restatement of the 33 line kinds, independent of the renderer's code: it derives from the input files which lines a set of records must produce and in what order, compares that sequence with the lines the page lists, rebuilds every line from the fields its Sources entry cites, and requires byte equality.
It must fail when a rendered value differs from its field, when `not recorded` is replaced by a plausible value, when a line is added, uncited, cited from the wrong field or moved under another workflow, when the renderer is changed in-process to guess a default or invent a version (the mutation proof in `test_an_invented_value_is_caught`), when a path-like value or the actor is printed, when the approval is not bound to the plan, when a fenced or another analysis's history entry is rendered, when record text adds structure, when a malformed input is rendered instead of refused, when the output would replace an input, or when a file other than the named inputs is opened.
Two tests render records written at test time by the real `prepare`/`collect` and the real `cmd_approve`/`cmd_verify`.

## Status

Standing. The change record for the Methods renderer; its protected-change approval is 0237.

## Date

2026-09-30
