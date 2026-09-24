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

## Addendum — W2 review fixes, 2026-09-23

THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.
This addendum addresses W1 F1 and F2. Every preceding byte is preserved; no new
words are attributed to the owner. The record remains 0072; reserved 0073 is
protected approval and 0074 covers the seal and first measured run. Neither is
written by this round.

W1 F1 corrects the V1 separator exemption: a separator-only shell argument is
the filesystem root and is a blindness hit, including quoted arguments, repeated
separators, root-valued path options and nested shell commands. Field context
keeps write/edit content separate from path fields. The root-word audit exempts
awk/cut delimiter values and interpreter program text, while the ordinary audit
still scans named absolute paths and home/parent spellings inside every field.
An option is a delimiter only in its command's context: directory-listing options
cannot excuse root access. The V1 claim that all outside paths invalidate reviews
was incorrect for root-only words; the W2 regression and mutation controls cover
that gap without editing the earlier account.

W1 F2 treats a directory change with only the option words --, -L or -P as home
access. Prefix recognition now includes eval, exec and time. Explicit in-kit
directory arguments remain clear. Stub-launch tests confirm these escapes make
the code-owned envelope INVALID; disposable-copy controls remove each detection
and require the named test to fail after its unchanged control passes.

These remain static post-run checks, not a complete shell interpreter or an OS
sandbox. Item 19's exact own-session output allowance is unchanged. The uid-check
meaning and every residual in the preceding record remain unchanged. No prompt,
fixture, schema, threshold, policy or CI change is made. No model runs against a
case, no seal or first-run evidence is produced, and row 9 exit stays NOT met.
Real fixture secret verification, protected approval, external deployment
evidence, public external-human seals, R-093's code half, science and trailer
JSON consumption remain open. Required command results are appended to
`docs/implementation/row_9_change_report.md`.

## Addendum — X1 two walls and W2 findings, 2026-09-23

THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.
Item 20 supersedes the earlier THREAT MODEL claim of reading beyond the kit
by any spelling, item 8's blindness paragraph wherever they differ, and the
W2 addendum's unrestricted claims about quoted roots and nested commands.
Every preceding byte remains unchanged. This is the lane's specification;
no new words are attributed to the owner. Numbering remains 0072 for this
record, 0073 for protected approval, and 0074 for the combined seal and first
measured run. Neither reserved record is written here.

Enforcement is the reviewer's sandbox. Every launch requires --settings and
refuses before starting the tool when it is absent. The exact settings bytes
copied into the kit are bound by envelope.sandbox_settings_sha256. The schema,
stdlib validator, contract fixtures and published copy carry that required hash;
the published value is unchanged, not masked. Scoring refuses missing or malformed
hashes and disagreements between records, including invalid and earlier attempts.
The deployment supplies settings denying reads outside the kit and all network.
The harness binds WHICH file was used and never judges its content. This records
configuration provenance; real sandbox enforcement remains deployment evidence.

Detection is a static blindness audit, not a claim to decide what a shell reads.
Its contract is exactly item 20(b):

1. Every token in command or path-valued fields that is absolute, starts with
a tilde or a HOME expansion in any modifier form, or contains a parent component,
is placed against the kit and is a hit unless inside the kit, item 19's own-session
store, or the system allowlist. The allowlist is the usr, bin, sbin, lib and lib64
root trees and the null, stdin, stdout and stderr device files. Symlinks resolve.
2. Separator-only command words default to hits. Exemptions are delimiter-option
values (-F, -d, --delimiter, --field-separator in their command option context),
interpreter -c/-e program text and write/edit content fields. The inversion is
allow by listed context, never deny by listed spelling. Named path tokens in
these fields still receive rule 1.
3. Prose fields (description, Grep pattern, agent prompt) get rule 1 only, never
rule 2. This corrects W2 F2's false INVALID.
4. cd is detected as a shell word from shlex after any shell keyword, any prefix
command with its options, or a leading backslash. It is bare and a hit when all
its arguments are option words. This answers W2 F3 without a prefix regex.

The good and bad lists in LaunchTests.test_blindness_every_spelling exercise
each rule; disposable-copy mutations require the named test to turn red after
an unchanged control passes. W2 F1 is answered under item 20(b)(ii), with visible
separator words in quoted and assignment text, and item 20(c) for indirection.
The uid check still proves exactly: on the host where the review ran, the
reviewing OS account is not the producing OS account. It does not prove which
machine built the cases, and it does not bind GARS's own role decision.

### Not covered

The scan does not follow shell indirection it cannot see statically (variables
and assignments, command substitution, evaluated strings, aliases, functions,
nested shells beyond those it parses) or interpreter program text (W2 F4).
Those reads are the sandbox's to refuse; if the sandbox allowed one, the scan
may not see it. Visible tokens detected in some examples are not proof of shell
interpretation. The README states this limit beside the two separate walls.

All other residuals stand: guessing from diff style, shared sealer/producer model
family, independent-context evidence only, science and trailer JSON in later
rows, thin per-class samples, and hash-only recomputation of three sealed outcomes.
R-093's code half remains NOT met because launch_role() still returns producer.
Separate-user and read-only-credential deployment evidence stays outside this
repository. The protected prompt and fixtures are unchanged. No model is run,
no sealed slot filled, no ledger row written and no measured run claimed.
Real fixture secret scanning awaits independent verification under Q2 A;
row 9 exit and public credibility remain NOT met and unmeasured respectively.

## Addendum — Y2 review fixes and item 20, 2026-09-24

THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.
This addendum answers the supplied Y1 review. Every preceding byte is preserved;
no new words are attributed to the owner. This record remains 0072; protected
approval is reserved 0073, and the seal and first measured run share reserved
0074. Neither reserved record is written here.

Item 20 continues to supersede the original THREAT MODEL's claim of detecting
reading beyond the kit by any spelling, and item 8's blindness paragraph wherever
they differ. Enforcement and detection are separate walls:

- Enforcement is the reviewer's deployment sandbox, which must deny reads outside
  the kit and all network. The launcher requires --settings, copies its exact
  bytes, and binds envelope.sandbox_settings_sha256. The schema, validator and
  contract fixtures require this field. Scoring refuses a missing or malformed
  hash and disagreement across records, including earlier and invalid attempts.
  The published copy retains the hash unchanged. The harness binds WHICH file
  was used and never judges its content or proves sandbox enforcement.
- Detection is the static audit of item 20(b)(i)-(iv). Absolute, tilde, HOME
  expansion and parent-component tokens are checked against the kit, item 19's
  exact own-session output store, and the system allowlist. Separator-only
  command words default to hits; exemptions remain delimiter-option values in
  their command context, interpreter -c/-e program text and write/edit content.
  Prose fields receive the path-token rule only. Shell words identify cd after
  shell keywords, prefix commands and options, or a leading backslash; a cd
  with only option arguments is bare and a hit. The good and bad lists and the
  existing per-rule mutation controls remain in force.

Y1 F1: numeric redirect descriptors, redirect operators and their targets are
not directory arguments. Skipping them preserves bare-cd detection while allowing
an explicit in-kit directory before or after a redirect. Y1 F2: the dollar that
shlex leaves before an ANSI-C or locale quoted separator no longer hides the
separator word. Runtime-built probes cover both forms, with in-kit controls.
Y1 F3: bare-cd recursion recognizes shell option clusters ending in c and the
basename of full-path shell names. These restore the two reported spellings;
they do not establish general shell interpretation. Stub launches bind each
reported escape to an INVALID code-owned envelope; disposable mutations remove
each fix and require the named regression to fail after its unchanged control.
No prompt, fixture, threshold or public evidence row changes, and no model runs.

### Not covered

Item 20(c) remains explicit: the scan does not follow shell indirection it cannot
see statically (variables and assignments, command substitution, evaluated strings,
aliases, functions, nested shells beyond those it parses) or interpreter program
text. Brace expansion, parameter-default expansion and URL-embedded paths,
including file-scheme URLs, are also named residuals under Y1 F3. Those reads
are the sandbox's to refuse; if the sandbox allowed one, the scan may not see it.

Y1 F4: conservative false positives follow the specified context list. Quoted
text with a spaced separator, awk division, sed substitution text and git log
formats can invalidate ordinary review commands. Prefixes can obscure delimiter
context, and echoed cd words can trigger the bare-directory audit. This round
names those costs in the README without widening the listed exemptions.

Y1 F5: the unchanged, unsalted settings hash required by item 20(a) can confirm
a guessed settings file and account or home-folder text within it. It proves
configuration identity, not privacy of that file's contents. The README names
this disclosure limit; no alternate hash, schema change or unapproved deployment
requirement is introduced.

The uid check proves exactly: on the host where the review ran, the reviewing OS
account is not the producing OS account. It does not prove which machine built
the cases, and it does not bind GARS's own role decision.
All earlier residuals remain: separate-user and read-only-credential deployment
evidence is external; launch_role() still returns producer, so R-093's code half
stays NOT met; guessing from diff style and shared sealer/producer model family
are not prevented. Independent-context seals are development evidence only;
public credibility requires external-human seals. Science and trailer-gate JSON
consumption remain later work. Per-class samples are thin, and only twelve of
fifteen outcomes are publicly recomputable, with three sealed outcomes checkable
by hash. Fixture gitleaks verification remains subject to Q2 A. No seal, ledger
entry or measured run is supplied; row 9 exit remains NOT met.


## 2026-09-24 addendum — review round Z1

**THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.**
No new words in this addendum are attributed to the owner. Record 0072 remains
this row's decision; 0073 is reserved for protected approval, and 0074 for the
seal and first measured run together. Earlier bytes remain unchanged.

### Items 20 and 21; Y2 F1

Item 20 continues to supersede the earlier threat-model claim of detecting reads
beyond the kit by any spelling. Enforcement is the deployment sandbox, configured
by required settings; launch records sandbox_settings_sha256, and scoring refuses
missing or mixed hashes. The harness binds the settings bytes without judging
content or proving filesystem and network denial. The unchanged settings hash is
configuration provenance, not privacy: it can confirm a guessed settings file.

Detection is the bounded audit in item 20(b)(i)-(iv). Path tokens in commands and
path-valued fields are checked against the kit, the exact own-session output
store and the system allowlist. Separator-only command words default to hits;
listed delimiter values, interpreter program text and write/edit content are
exempt. Prose gets rule (i) only. The shlex stream identifies bare cd after shell
keywords, prefix commands and options, or a leading backslash. Redirects and
both numeric and named descriptors do not supply a directory argument (Y2 F1).
Good and bad lists plus an isolated mutation prove the named-descriptor fix;
a stub stream proves the hit produces an INVALID record.

Item 21 extends item 20(b)(ii)'s listed contexts: program text for awk, gawk,
mawk and sed (first non-option argument or an -e or --expression value), git
--format=, --pretty=format: and --pretty=tformat: values, printf and echo format
and argument text, and grep, egrep, fgrep and rg patterns (first non-option
argument or an -e or --regexp value). The parser recognizes these after prefix
commands and options. Separator text in these contexts names no directory.
Rule (i) remains unchanged and scans the original field, including these words.
Good lists require zero hits, corresponding absolute-path probes require one,
and a listing, find or cd of the root after each command still requires one.
Removing the new contexts turns the named test red. Earlier expected hits for
awk program text, printf format text and echo argument text are superseded by
item 21, with the same spellings retained as zero-hit controls. No model runs,
prompt changes, fixture changes or thresholds are involved.

### Not covered — Y2 F2 and F3

A spaced numeric directory before a redirect, and a dollar directly before a
separator outside listed text contexts, can invalidate a record. Item 21 exempts
echo and printf text from the latter; the numeric-directory ambiguity remains.
An echoed cd word can still trigger the bare-directory audit. These conservative
false positives are detection limits, not evidence of sandbox enforcement.

Item 20(c)'s named residual remains shell indirection the audit cannot resolve:
variables and assignments, command substitution, evaluated strings, aliases,
functions, nested shells beyond those parsed, and interpreter program text.
The unparsed nested-shell forms include separated options, clusters where c is
not last, and an end-of-options marker before the program (Y2 F3). Brace and
parameter-default expansion and URL-embedded paths remain residuals. These reads
are the sandbox's to refuse; if allowed, the scan may not see them. Very long
encoded project folder names remain unverified against the deployed tool.

The uid check proves exactly: on the host where the review ran, the reviewing OS
account is not the producing OS account. It does not prove which machine built
the cases, and it does not bind GARS's own role decision. Separate-user and
read-only-credential deployment evidence remains external; launch_role() returns
producer and R-093's code half remains NOT met. Diff-style inference, shared
sealer/producer model family, science and trailer-gate JSON remain residuals.
Independent-context seals are development evidence only; public credibility
needs external-human seals. One sample per class remains thin; twelve of fifteen
outcomes can be publicly recomputed and three sealed outcomes checked by hash.
Real fixture gitleaks verification remains NOT met here under Q2 A. No seal,
measured run or ledger entry is supplied. Row 9 exit remains NOT met.


## 2026-09-24 addendum — review round AA1

**THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.**
No new words are attributed to the owner. Item 22 amends items 20 and 21 where
these differ. Earlier bytes remain unchanged; 0072 remains this row's record,
0073 is reserved for protected approval, and 0074 for the seal and first run.

### Item 22: honest calls and shell syntax

The corpus comes from seven real review sessions of this row on the deployment,
sanitized before delivery. Each label is the lane's reading of the contract;
no account, host or owner identity is in it. Both supplied files were copied
byte-for-byte into tests/data. The 278 whole calls comprise 277 honest calls and
one contract hit. Before the change the corpus test graded 278/278 and failed
36 labels, reproducing 35 honest calls with hits and the missed contract hit.
Tests substitute paths recursively in string values only, using the supplied
README's order and neutral stand-ins. The original byte count represented by
NUM-A is unavailable in the supplied files; a neutral five-digit value is used
in this exempt content field. No identity is reconstructed or requested.

(a) Program, format and pattern data in the item 21 contexts is exempt from
both path rules: awk, gawk, mawk and sed programs; git format and pretty values;
printf and echo text; grep, egrep, fgrep and rg patterns. This supersedes item
21's statement that rule (i) continues inside those contexts. File operands
remain scanned. Z1 F1 is fixed by consuming prefix-option values before choosing
the command and consuming attached or following e/f option-cluster arguments.
Z1 F2 is fixed: patternless rg modes leave all file operands scanned.

(b) Content and prose fields get neither rule. This withdraws item 20(b)(iii).
Only command and path-valued fields are scanned. Only command fields receive
shell parsing; an unmatched quote in a content or prose field is never a hit.

(c) Heredoc bodies are content, removed before all audit rules. Headers and
commands after the delimiter remain audited. Unquoted, single-quoted,
double-quoted and tab-stripping delimiters are covered, including multiple
bodies attached to one header.

(d) Shell comments are not scanned. Operators separate glued words; adjacent
quoted pieces join before path tests. Separator pieces of a longer word are
not separator-only operands. Shell words replace regex fragments; the earlier
regex remains only inside the interpreter text it already inspected.

(e) Nested shell programs are found by basename for sh, bash, dash, zsh and ksh,
after any run of option words, including separated options, an end-of-options
marker, and clusters ending in c. Their program text is audited as a command.
The corpus's one contract hit is now detected. The separate-option forms named
as residual in the Z1 addendum are covered to this stated extent.

The corpus test prints graded-against-seen and asserts every row was scored.
Each part (a)-(e) has an isolated mutation that makes that test red, identifying
the failed calls. Earlier bad lists remain hits except the expressly superseded
expectations for program data and prose; those probes remain as zero-hit tests
with matching operand controls. Existing mutation guards remain exercised at
their refactored locations. No model, prompt tuning or measured case run is used.

### Enforcement and detection; not covered

Item 20 continues to supersede the original threat-model claim about every
possible path spelling. Enforcement belongs to the deployment sandbox. Required
settings bytes are copied and bound by sandbox_settings_sha256; missing or mixed
hashes are refused. The harness does not judge the settings or prove their
filesystem and network restrictions. The published unsalted hash may confirm a
guessed configuration; it is provenance, not privacy of the settings contents.
Detection is only the bounded audit above, with the exact own-session saved
output store and the existing system allowlist unchanged.

File access within awk program text (including getline) and sed program text
(including r or w) joins interpreter text among item 20(c)'s named residuals.
Command substitutions inside exempt echo and printf text are not separately
audited (Z1 F3). Variables and assignments, command substitution, evaluated
strings, aliases, functions, unparsed nested shells, brace and parameter-default
expansions and URL-embedded paths remain sandbox responsibilities. If the
sandbox allows such a read, the static audit may not see it. Conservative
false positives remain for unlisted contexts such as git grep patterns (Z1 F4),
and for the earlier numeric-directory redirect ambiguity. Long encoded project
folder names remain unverified against the deployed tool.

The uid check proves exactly: on the host where the review ran, the reviewing OS
account is not the producing OS account. It does not prove which machine built
the cases, and it does not bind GARS's own role decision. Separate-user and
read-only-credential deployment evidence is external; launch_role() remains
producer and R-093's code half stays NOT met. Diff-style inference, shared model
family, science, trailer-gate JSON, thin samples and three hash-only sealed
outcomes remain residuals. Public recomputation covers twelve of fifteen cases.
Independent-context seals are development evidence only; public claims need
external-human seals. Real fixture secret verification remains NOT met under
Q2 A. No sealed slots, measured run or ledger entries are supplied. Row 9 exit
remains NOT met.


## 2026-09-24 addendum — review round AA2

**THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.**
No new words are attributed to the owner. This addendum preserves all earlier
bytes. Record 0072 remains this row's decision; 0073 and 0074 remain reserved
for protected approval and the seal with first measured run respectively.

AA1 F1: shell comments begin only at an unquoted word boundary. A hash within
a word, including parameter expressions, does not discard subsequent commands.
AA1 F2: heredoc body removal recognizes only unquoted, unescaped operators.
Quoted operator text is ordinary data and cannot suppress later lines. A small
source pass retains quote state and word boundaries before shlex removes quotes;
comment removal preserves newlines. Real heredoc bodies remain exempt content.
AA1 F3: the tool name accompanies its input fields. Glob pattern is path-valued,
while Grep pattern remains exempt prose. Both directions have named tests.
AA1 F4: a visible command operand with an identifier and equals sign has its
value path-tested, including dd input operands. Ordinary absolute paths with
an equals sign are preserved. This is a literal value check, not evaluation.
Each change has a named regression and an isolated red-on-fault entry.

Item 22 continues to amend items 20 and 21: neither path rule scans the listed
program, pattern and format data; file operands are scanned. Content and prose
remain exempt, heredoc bodies are removed, and shell word boundaries and nested
shell options retain the previous coverage. The supplied corpus files were
copied again with cp and are byte-identical to the committed copies. Their
provenance is seven real review sessions of this row on the deployment,
sanitized before delivery; labels are the lane's reading of the contract and
contain no account, host or owner identity. All 278 calls and the earlier
item 22 mutation entries remain part of verification.

### Not covered and row exit

Item 20's two walls remain distinct: the deployment sandbox enforces filesystem
and network restrictions; required settings bytes are hashed into the envelope.
The harness binds which settings were used and never proves their efficacy.
The audit detects its named spellings, not arbitrary shell behavior. Variables
and assignments beyond their visible operand values, substitutions, evaluated
strings, aliases, functions, unparsed nested shells, interpreter text and file
access within exempt awk or sed programs remain sandbox responsibilities.
The unsalted settings hash can confirm guessed configuration contents; long
encoded session-store names remain unverified against the deployed tool.

The uid check proves exactly: on the host where the review ran, the reviewing OS
account is not the producing OS account. It does not prove which machine built
the cases, and it does not bind GARS's own role decision. Separate-user and
read-only-credential deployment evidence remains external. launch_role() still
returns producer; R-093's code half remains NOT met. Diff-style inference,
shared sealer and producer model family, the science half, trailer-gate JSON,
thin one-per-class samples and three sealed outcomes checkable only by hash
remain residuals. Public recomputation covers twelve of fifteen outcomes.
Independent-context seals remain development evidence; public credibility
requires external-human seals. Real fixture gitleaks verification remains
NOT met under Q2 A. No model is run, no prompt is tuned, and no seal, measured
run or ledger entry is supplied. Row 9 exit remains NOT met.


## Addendum — AB1 fail-closed text removal, 2026-09-24

**THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.**
This addendum implements head item 23 and answers review AA2 F1 and F2.
It amends item 22(c) and (d) wherever they differ. It attributes no new
words or choices to the owner. Earlier bytes, including previous numbering,
remain unchanged. This record is 0072; protected approval is reserved 0073;
the seal and first measured run share reserved 0074. Neither is written here.

### Removal only with unambiguous evidence

The audit removes text in exactly two contexts: shell comments and heredoc
bodies. Otherwise it scans. A comment hash must start a shell word at quote
depth zero. A heredoc operator must be unquoted and unescaped at quote depth
zero, followed directly by its delimiter word (optionally quoted, with optional
intervening whitespace), and its closing delimiter line must be found.
Unquoted, single-quoted, double-quoted and tab-stripping delimiter forms remain
supported. For multiple bodies on one header, every closing delimiter must be
found before any body is removed; otherwise all following lines are scanned
as commands. Headers and commands following confirmed closers stay scanned.

For BOTH contexts, removal is forbidden when the physical line holding the cue
contains a dollar immediately followed by an opening parenthesis, a backquote,
or two opening parentheses. This test covers the whole physical line, including
text before and after the cue, without trying to evaluate shell constructs.
Thus substitution endings cannot turn their following hash into a removal cue,
and arithmetic shifts cannot authorize heredoc removal. A missing delimiter
also cannot hide later commands. Ambiguity always means scan it: the permitted
failure direction is an honest record becoming INVALID, never hiding a read.

LaunchTests.test_ambiguous_removal_cues_scan_instead covers AA2's substitution
hashes and arithmetic shifts, backquotes, and AA1's mid-word hashes and argument
count expansion, with outside reads, root listings and bare directory changes.
Existing quoted-operator tests retain their bad lists and now include plausible
closer lines, so their fault witness depends on retaining quote information
rather than only on the new missing-delimiter guard.
LaunchTests.test_heredoc_removal_requires_delimiter covers absent and incomplete
closers, missing delimiter words, and multiple queued bodies, with valid heredoc
controls. Disposable mutations remove the line guard and the closer requirement;
each must turn its named test red after an unchanged green control. All previous
bad lists and mutation witnesses remain required.

The sanitized 278-call corpus from real deployment review sessions remains the
item-22 compatibility test. Its labels are the lane's reading of the contract;
no account, host or owner identity is included. This change produces no new
honest-call hits: 277 honest calls remain clear and the one contract hit remains
detected. No corpus body or label was changed.

### Two walls and not covered

Item 20 still supersedes the original threat-model claim about detecting every
possible spelling. Enforcement is the deployment sandbox, whose required
settings bytes are bound by sandbox_settings_sha256; the harness never judges
the file's content or proves filesystem and network denial. Detection is only
the bounded audit, with kit, exact own-session output store and system allowlist
unchanged. The published settings hash may confirm a guessed configuration.

Under item 23(e), a new spelling whose escape depends on unparsed substitutions,
arithmetic, eval, aliases, functions or nested quoting is a named residual:
grade it a NOTE asking that it be named. Do not extend this audit into a shell
evaluator. The sandbox must refuse such reads; the audit may miss them if it
does not. The existing residuals include variables and assignments, command
substitution, evaluated strings, unparsed nested shells, interpreter text,
brace and parameter-default expansion, URL-embedded paths, and file access
inside exempt awk and sed programs. Conservative false positives remain.
No model is run against a case and no prompt is tuned in this round.

The uid check proves exactly: on the host where the review ran, the reviewing
OS account is not the producing OS account. It does not prove which machine
built the cases, and it does not bind GARS's own role decision. Separate-user
and read-only-credential deployment evidence remains external; launch_role()
still returns producer and R-093's code half stays NOT met. Diff-style inference,
a sealer and producer sharing a model family, science, the trailer gate's JSON
integration, thin per-class samples and hash-only checks of the three sealed
outcomes remain residuals. Public recomputation covers twelve of fifteen cases.
Independent-context seals provide development evidence only; public credibility
needs external-human seals. Row 9 exit remains NOT met pending sealing and the
first measured run. Protected approval and ledger updates remain later work.
Real fixture secret scanning remains NOT met on this build host when gitleaks
is absent, under Q2 A. Docker mode A is unavailable; native Python 3.6, deployment
sandbox efficacy, long encoded store names, cluster execution and merge-result
CI remain unverified. Verification for AB1 is appended to
`docs/implementation/row_9_change_report.md`.


## Addendum — AC1 shell blanks and named residuals, 2026-09-24

**THE LANE, UNDER THE OWNER'S DELEGATION — THE LANE'S SPECIFICATION.**
This final fix round answers review AB1 F1 and F2 within items 22 and 23.
No new words or choices are attributed to the owner. Earlier bytes remain
unchanged; this record is 0072, with protected approval reserved as 0073 and
the seal and first measured run reserved together as 0074.

For F1, the comment scanner recognizes only space, tab and newline as shell
blanks, alongside its existing operator characters. Python's broader whitespace
classification is no longer used to establish a comment boundary. Form feed,
vertical tab, carriage return and no-break space each precede a hash in the
existing test_hash_comment_boundaries, with an outside read, a root listing
and a bare directory change. The existing midword-hash mutation covers this
test. No parser refactor or new audit rule is introduced.

For F2, the named residual list now explicitly includes backslash-newline
continuation across the physical-line removal guard, legacy dollar-bracket
arithmetic, operators inside parameter expansion, and ANSI-C quoted heredoc
delimiters. Under item 23(e), these unparsed constructs are documentation
residuals. Their handling in code is unchanged. The deployment sandbox must
refuse these reads; the bounded audit may miss them. Required settings hashing
binds the file used, without proving filesystem or network enforcement.

All earlier residuals and the two-wall distinction remain in force. Row 9 exit
remains NOT met: no model is run against a case, no prompt is tuned, and no seal,
measured run, protected approval or ledger entry is supplied. Independent-context
seals remain development evidence only; public credibility requires external-human
seals. The uid check proves exactly: on the host where the review ran, the reviewing
OS account is not the producing OS account. It does not prove which machine built
the cases, and it does not bind GARS's own role decision. Verification and remaining
gaps are appended to `docs/implementation/row_9_change_report.md`.
