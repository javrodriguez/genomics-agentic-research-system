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
