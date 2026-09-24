---
date: 2026-09-23
status: standing
kind: decision
touches:
  - evals/review-faults/
  - gars/_references/prompts/review_faults_code.md
  - tests/test_review_faults_build.py
  - tests/test_review_faults_core.py
  - tests/test_review_faults_launch.py
  - tests/test_review_faults_faults.py
  - scripts/release_check.py
  - docs/implementation/dod_current.md
  - docs/implementation/row_9_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - reviewer results lack a launch-owned identity envelope
  - vague findings pass an unstructured catch oracle
  - development seals are mistaken for public threshold evidence
---
# Row 9 review fault harness, code half

## Context

Round 1 starts at `e59dfc088fc638a801f255fc0373c139f7afbac4`, on
`build/gars-row-09-review-faults`. Specification v1.0.1 §18 row 9, §10,
§9.2, §9.3, §11.3, §17 and §21 Q3/Q9/Q10 govern the code half. The gap
assessment's Row 9 and D-22 identify the missing measurement and independence
boundary. The current round implements repository tools, never a measured run.
Existing decision records remain unchanged. Reserved records 0071–0074 are not
written here. There was no round-1 review file supplied.

## Decision

The following supplied rulings are quoted verbatim and attributed to **the owner**,
23 September 2026:

D-22, the owner:

> D-22 answered by the two OS users

R9-A … R9-G, the owner:

> defaults

R9-A, the owner:

> R9-A (Does this plan also run the row's exit (seal + first measured run, CP7-CP9)?): Yes. A row whose metric never moved is not done (R-181), and the harness is only proven by one real run

R9-B, the owner:

> R9-B (Which 3 of the 10 classes are sealed (written by the sealer, never by the producer)?): The seeded draw below: `race`, `hardcoded-secret`, `weakened-criterion`

R9-C, the owner:

> R9-C (Who seals?): A fresh Codex context on the Mac, as row 3's mutants were sealed ([the row 3 seal record's location on the owner's machine, elided from this quote]), seal type `independent_context`

R9-D, the owner:

> R9-D (What counts as a false alarm on a clean case?): Any finding of severity MINOR or above; a NOTE is not an alarm. Per class: a clean case with a MINOR+ finding of that class. Overall: clean cases with any MINOR+ finding ÷ 5 (§17's ≤ 1/5)

R9-E, the owner:

> R9-E (Where do the seal shas go in `docs/ledger.csv`? It has a `seal_type` column but no sha column (`docs/ledger.csv:1`)): In the existing columns, with no schema change: `fixture` = `review-faults:<slot>`, `seal_type` = the type, `notes` starts `seal_sha256=<64 hex>; plant_sha256=<64 hex>`

R9-F, the owner:

> R9-F (Public `main` has moved past `e59dfc0` (`701368f`: CITATION, CONTRIBUTING, issue templates, README +4 lines, and a new CI job `fresh-clone.yml` that checks README's skip counts). How does the row land?): Build from `e59dfc0`, per every lane's rule (STATE `:95`). Land it as a merge commit onto current `main` made by [the owner], keeping the reviewed head as a parent so the review covers exactly what it read. Then every CI job re-runs at the merge result, `fresh-clone.yml` included, before the push

R9-G, the owner:

> R9-G (What does the public README row say after an `independent_context`-sealed first run? The spec keeps public credibility claims `unmeasured` until `external_human_seal` (§10, §21 Q9), and `README.md:431-433` says so): The public cell stays `unmeasured`. One owner-approved pointer is added beside it: "development evidence (independent_context seals): `<run file>`". `release_check.py` renders the code half as development-only and never as meeting the threshold

Everything below is **THE LANE'S SPECIFICATION and implementation account**, not
additional words attributed to the owner.

### D-22 boundary

Deployment runs Codex as producer and Claude Code as reviewer under two separate
unprivileged OS users with separate read-only credentials. The launcher records
its own os.getuid() and resolves the producing account with pwd on that same host.
It rejects root and uid equality; no role or reviewer-identity override exists.
Deployment evidence lives outside this repository. GARS's `launch_role()` is
unchanged and still returns producer.

What the uid check proves, exactly: on the host where the review ran, the reviewing OS account is not the producing OS account. It does not prove which machine built the cases, and it does not bind GARS's own role decision.

### Threat model

Covered, the measured reviewer, a model session in a kit, must not be able to:

- Learn the case's class, plant/clean kind or answer from folder names, commit
  metadata, Git history, BRIEF.md or the base tree. The full-base literal vocabulary
  sweep has the unresolved contradiction described below; that acceptance is NOT met.
- Read beyond its kit by absolute, tilde, home-variable or parent-component path
  spelling without the resulting record becoming INVALID. This is the item-8
  post-run tool-input audit, not an OS sandbox. System allowlist exceptions are
  the ones in that item, assembled from path components in source.
- Supply its own envelope: identity, model, prompt hash and blindness come from
  launch code and captured process evidence. Invalid model output is preserved
  under an invalid review object, never accepted as envelope metadata.
- Be scored under the same reviewing and producing uid on the recorded host.
- Count as caught with a vague finding: class, normalized file, line interval
  expanded by three lines and severity floor all match deterministically.

Covered, the harness must report only what it measured. Invalid attempts are
retained and printed. Zero denominators say uncomputable. Hashed-answer drift and
mixed models refuse scoring; mismatched prompt records are explicitly INVALID.
A latest valid attempt may be scored while earlier or later invalid attempts
remain visible. Headline denominators stay ten plants, five clean, fifteen total;
per-class denominators use valid available cases. Partial sets never meet thresholds.

### Repository implementation

Only the seven assigned producer plants and five clean changes are authored.
All are unified diffs against the base. Sealed slots remain empty. A case builder
exports the full base tree, creates two fixed-author/date commits without source
history, and keeps the salted identity map and exact answer hashes outside the
case folders. The shuffled manifest contains only the neutral ids, base SHA,
repository-relative prompt path, prompt hash and harness commit. The private salt
is stored only in key.json; supplied salts exist for deterministic test replay.

The JSON Schema document and stdlib validator share required fields and enums;
tests traverse those contracts with valid and invalid instances. The launcher
uses a no-local clone with remote removed and reflogs expired, exact copied
settings, the fixed command from item 8, sanitized environment and owned regular
no-follow output. Captured init events supply model identity. Synthetic messages
never substitute a model. Usage-limit signatures are implemented directly from
item 8 and preserve attempts for a fresh-login resume.

The publication mask is pre-registered in `score.masked_copy`: exact declared
literals, kit/home prefixes and identity text are masked; uid and host digests
become salt-keyed HMAC-SHA256, preserving within-run equality. Remaining rooted
paths are conservatively masked to a home marker and their leaf name so that
nonstandard home locations cannot leak. Only os_user fields
are removed, as explicitly specified. Other fields and invalid submitted outputs
are retained. Original records, streams, key and salt stay private. A run file's
first-run-at-sha status is keyed by prompt SHA only, including across model changes.

The release reader reports code evidence as development and science as unmeasured.
Independent-context seals cannot satisfy the public threshold. The README evidence
row is not edited; a later approved run pointer is outside this commit. The prompt
and fixtures are protected paths. Their approval is the separate commit and record
0071 at merge, in the shape of [0066](0066-row-12-owner-approval-of-protected-changes.md).
This producer record neither supplies nor claims that approval.

### Unresolved acceptance conflict

Item 6 requires the entire base tree as the root commit. Item 12 requires sweeping
every case byte for every class id and finding none. Base specification §10 line
243 already contains `off-by-one` and `race`; the base cannot both remain complete
and omit those bytes. The regression test reproduces their presence and explicitly
prints NOT met. It does not silently exempt inherited bytes. Options and the
stopped acceptance are recorded under Owner rulings needed in the change report.

## What this does not close

Every item below is **NOT met**, not implied by green repository tests:

- Full row 9 exit: three sealed slots, seal hashes in the later ledger commit,
  actual separate-user deployment evidence and one real measured run remain later.
- The literal every-byte class/id/path absence acceptance, pending its ruling.
- Preventing a reviewer from guessing the measurement from a diff's style.
- Independence of model family between sealer and producer: R9-C uses a fresh
  context in the same family.
- Public credibility: independent_context is development evidence only;
  external_human_seal remains required by §10 and §21 Q9.
- R-093's code half: `launch_role()` still returns producer until a later record.
- The science half, row 10.
- Trailer-gate consumption of JSON reviews: row 11 still reads one session line.
- A statistically broad per-class estimate: one plant gives only 0/1 or 1/1.
- Public recomputation of the three private sealed outcomes: hashes are checkable,
  but a stranger recomputes only twelve of fifteen outcomes from repository inputs.
- Protected-path approval, independent review, merge-result CI and deployment.
- Docker mode A and native Python 3.6 execution in this account.
- The real fixture secret scan: the unchanged pre-commit hook refused because
  gitleaks is absent from PATH; its citation check passed. No scanner was bypassed.

## Test

`tests/test_review_faults_*.py` use stdlib unittest, disposable scratch, synthetic
records and a locally created stub executable; no model or network is used.
The fault-list test mutates disposable copies and requires a named red unittest
for each guard. The [change report](../implementation/row_9_change_report.md)
records each guard, red witness and the exact required command summaries.
All new Python is parsed with feature_version=(3, 6). Existing tests and thresholds
are preserved. The full suite and the frozen evaluation checks are rerun.

## Status

Standing implementation account, pending independent review and the unresolved
byte-sweep ruling. Repository code half only; row 9 exit NOT met. No seal, measured
run, ledger row, approval, merge, push or pull request is supplied by this commit.

## Date

2026-09-23
## Addendum — R1 rulings, 2026-09-23

Starting commit: `767a986d6477ba1fae50e0d5a9dd214811549b39`.
This addendum preserves every preceding byte. R1 answers the round-1 ruling
requests; no review was supplied or consulted.

The owner, 23 September 2026, answering the two round-1 questions:

> Q1 A, Q2 A

The questions and chosen options, attributed to the owner as supplied with that
answer (the bracketed substitutions below are edits of the quote):

> Q1 (Each test case ships the full GARS repo, and the repo's own spec already names every fault type. So "no fault name anywhere in a case" can never pass. Which rule wins?): A: check only the bytes the case ADDS (the planted change, the commit, folder names, manifest). The spec text is identical in all 15 cases, so it can't reveal which fault is in one.

> Q2 (gitleaks isn't installed on [the build host], so the fixture secret scan can't run there.): A: leave it NOT met on [the build host]; [the lane's independent verification] runs both gitleaks rulesets over the fixtures.

Edits of the Q2 quote: both host references are replaced by `[the build host]`;
the first-person verification reference is replaced by
`[the lane's independent verification]`. No other wording is changed.

### The lane's specification of the R1 rulings

This section describes implementation, not additional words of the owner.
Item 14(a) replaces the stopped literal whole-tree absence test with a sweep of
the plant diff, decoded metadata of both commits, case and repository folder
names, manifest, and every file whose bytes differ from the base blob at the
same path. Only byte identity at that path grants an exemption. Controls change
the inherited spec in place and copy its identical contents to a new path;
both must be scanned. Disposable-copy controls inject class and case ids into
commit messages, a changed file, folder names, manifest and plant diff.

Item 14(b) leaves the real fixture pre-commit secret scan NOT met on this host;
no installation or substitute scanner is used. The later independent verification
must run both rulesets. Item 14(c) changes the README reference to repository-relative
text and builds the masking test's suffix with `os.path.join`. The inherited
spelling in this record is unchanged.

The exact full-file sweep also sees inherited vocabulary in files changed by
P02, P04 and P06. Whether to replace these plants or exempt unchanged portions
requires a further scope ruling; the change report records the failing witness
and options. The exemption has not been broadened to make this pass.

All prior residuals remain except that Q1 and Q2 now have explicit answers.
Row 9 exit, sealing, the first measured run, deployment evidence, R-093's code
half, external-human public evidence and protected-path approval remain open.

Further R1 witness, 2026-09-23 (the lane's specification): the literal file sweep
also scans Git storage; those files have no identical base blob at the same path.
Compressed inherited objects contain incidental short case-id byte strings.
No storage-path exemption was introduced. The report therefore also asks whether
Git objects should be compared to decoded base objects, with metadata still
scanned, or literal storage bytes must be free of these strings. Small synthetic
repositories isolate the leak controls from these pre-existing full-tree matches;
the separate all-twelve acceptance test retains its failure on the real cases.

## Addendum — S1 rulings, 2026-09-23

Starting commit: `6af7e2a15308008e366e1f7f61aabb49e17a1b9a`.
Earlier bytes are preserved. No review was supplied, read or requested.

The owner, 23 September 2026, answering the two questions round R1 raised:

> Q3 A, Q4 A

The questions and options as put to the owner, reproduced exactly:

> Q3 (Three planted changes edit files that already contain words like "race" (and "traceback" contains it). The whole-file scan can never pass on those.): A: scan only the lines the change adds, not the untouched rest of the file. That's what "only the bytes the case adds" meant.

> Q4 (Git's compressed storage files happen to contain short strings like "P04" by chance, in every case, even clean ones.): A: read git's contents decoded; skip anything identical to the original repo; always scan the new commit and its message.

In the same message, the owner delegated the rest of the row:

> I delegate to you all the decisions necssary to finish row9, use your best judgement. Only ask me for critical choices

### THE LANE'S SPECIFICATION — item 15

This is the lane's specification, not additional words attributed to the owner.
Item 15 supersedes item 14(a)'s wording where the two differ. Item 14(b)'s unmet
fixture secret scan and item 14(c)'s path spellings stand. This round exercises
no further delegated choice; no threshold, schema or CI change is introduced.

The sweep covers exactly (i) the committed diff's added lines and the full bytes
of added files, (ii) decoded reachable Git content introduced over the base tree,
including the second commit's entire object and message, (iii) case and repo
folder names, and (iv) the manifest. The case's history-free parent has the exact
base tree; its tree, rather than the original history, supplies the comparison.
All class ids, case ids and fixture paths remain forbidden tokens.

Q3's explicit unchanged-line exemption applies when reading a modified blob in
part (ii) as well as the diff in part (i). Decoding that blob does not reintroduce
its unchanged lines. New files are read in full even when they copy an inherited
blob; new tree entries and commit objects are decoded and scanned. Inherited
objects and decoded contents identical to base objects are exempt from part (ii).
Raw Git storage is never swept. No filename allowlist substitutes for comparison.
The existing root-commit metadata control also remains covered: that commit is
new, reachable content even though its tree is the base tree.

Disposable copies inject class and case ids into each covered surface; each
named acceptance test must turn red. Separate unchanged-line injections must
stay green. Widening modified-blob scanning back to whole content turns its
named acceptance test red. An inherited blob copied into an added file remains
a red witness. Unreachable objects are outside the sweep; repacking reachable
objects leaves its answer unchanged. Twelve shipped cases pass without fixture,
answer-key, manifest-format or reviewer-prompt changes.

The report records observed controls and required command summaries. No model
was run. No seal, measured rate, first-run claim or row-exit claim is made.
All earlier residuals remain except the now-resolved byte-sweep scope questions:
fixture gitleaks verification, separate-user deployment, R-093's code half,
protected-path approval, sealed slots, the first measured run, public external
human seals, science, trailer JSON consumption and merge-result CI remain open.
Diff-style inference, shared model family, thin per-class samples and hash-only
public checking of three sealed outcomes remain limitations.

## Addendum — T1 review fixes and renumbering, 2026-09-23

THE LANE, UNDER THE OWNER'S DELEGATION.

This record moves from 0070 to 0071 because public main has since assigned 0070
to row 12's owner approval. Every preceding byte is preserved. Earlier mentions
of 0070 as this record mean 0071; earlier reservations of 0071–0074 mean
0072–0074. References to this row's protected approval mean 0072, its seal record
0073, and its first measured run 0074. The producer writes none of those three
reserved records and does not touch public main's 0070.

S1 findings F1–F6 are addressed: P07's post-change match is line 73; a test checks
all file-lines answers against changed-line intervals. The blindness audit also
recognizes paths inside quoted interpreter arguments, brace-form home variables,
variable-prefixed parent steps, attached options and bare directory changes.
The neutral-name rule covers created kit directories, not existing ancestors.
Fault controls must first pass unfaulted in the same disposable source copy with
scratch outside its work tree, then fail on the expected assertion. Determinism
compares streamed per-file SHA-256 digests and Git object ids with bounded
mismatch messages, never whole-tree byte dictionaries. The README restores
measured skip counts; the sealer is assigned P08, P09 and P10 before sealing.

F7 requires no identity/configuration edit. For F8, publication mask v1 also
replaces word-bounded prose numbers equal to raw uids; this conservative masking
can obscure a coincident count or line number. Private originals govern scoring.
For F9, every finding's full line interval is already retained in the published
run, so wide spans are visible; the specified overlap rule remains unchanged.

No new words are attributed to the owner here. The prompt is unchanged and no
model runs against any case. All residual limits in the earlier record still
apply except the resolved acceptance and implementation defects documented by
this addendum and the T1 change report. Row exit remains NOT met; R-093's code
half, external deployment evidence, three seals, measured run, protected approval,
real fixture secret scanning and public credibility remain open.

T1 additional implementation, THE LANE, UNDER THE OWNER'S DELEGATION: F10 is
closed by moving the existing item-15 sweep into `case_sweep.py`, shared by the
builder and its controls. Every case, including externally supplied sealed inputs,
is checked before the key and manifest are written. No sealed plant is authored
or inspected by the producer. A disposable renamed copy of a public producer
fixture exercises the external-input path; it is never evidence or a seal.

## Addendum — U1 second renumbering, 2026-09-23

THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.
This is item 18's supplied specification, not additional words of the owner.

This record is renumbered again, from 0071 to 0072, because public main has
since also landed its own 0071, row 12's owner record. Item 18 supersedes item
16's numbers. Every preceding byte, including the T1 addendum, is preserved.
Earlier bytes' mentions of 0070 or 0071 as this record mean 0072; mentions of
any reserved number mean 0073 (the owner's approval of the protected changes)
or 0074 (ONE record covering both the seal and the first measured run).
Public main's 0070 and 0071 are not this row's and are never touched here.
The producer never writes reserved 0073 or 0074 and claims neither approval
nor sealing nor a measured run. Live references and the regenerated index use
these numbers; earlier report sections retain their historical wording.

U1 changes only this numbering and its documentation. T1's fixes stand; no
schema, threshold, scope, guard, test or CI decision is changed. All previously
open residual gaps remain, including the NOT-met fixture secret scan and row
9 exit. Protected approval, sealing and the first measured run wait on the
owner and later independent verification.

## Addendum — V1 review fixes and session output, 2026-09-23

THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.
This addendum implements U1 findings F1–F3 and head item 19. No new words
are attributed to the owner. Every earlier byte of this record is preserved.
Record numbering remains 0072 for this account, 0073 for protected approval,
and 0074 for the seal and first measured run; neither reserved record is written.

F1: attached short options are split only when their letters are immediately
followed by a root separator; long option values are checked as ordinary tokens.
Relative option paths and bare separator or division text do not become rooted
paths. Tests include the reported test-directory option, Git-directory option,
awk and cut delimiters, integer division and review JSON prose.
F2: bare directory changes are recognized after newlines, shell groups, then,
do, else, builtin and command. HOME and PWD brace expansions are inspected;
exact forms resolve against the launch account or kit, and unresolved shell
modifiers fail closed. Outside paths and parent steps still invalidate reviews.
F3: the complete sealer interface now states case-sensitive substring rejection,
including race inside trace, and gives the coordinator's existing builder command
for a pre-seal check without showing the sealer producer inputs or implementation.
All reserved case ids are forbidden even when their inputs are not yet present.

Item 19's saved-output allowance is exactly the reviewer's home, the tool's
`.claude/projects` folder, the encoded kit path, the session id passed by code
to the launch command, and `tool-results`. Encoding replaces each character
other than an ASCII letter, digit or hyphen with a hyphen. Paths are built at
runtime; no machine-specific name is stored in source. Reading one's own saved
tool output is allowed. The transcript beside that store, the memory folder,
another session and another kit remain hits. Resolved symlink escapes remain
hits. The session id is launch-owned and cannot be supplied by model output.
A runtime-path test independently checks the encoding and both allowance
boundaries; widening to the projects folder turns that named test red.

These are static post-run audit fixes, not a shell sandbox or a claim to model
every shell program. Deterministic mutation controls exercise the reported
spellings, both saved-output boundaries and launch-to-audit session binding.
The prompt and fixture bytes are unchanged; no model is run against any case.
All earlier residual limits remain: row exit NOT met, three seals and a first
measured run outstanding, protected approval and real fixture secret scanning
outstanding, public credibility unmeasured, deployment evidence external,
R-093 code half NOT met, science and JSON trailer consumption deferred.
