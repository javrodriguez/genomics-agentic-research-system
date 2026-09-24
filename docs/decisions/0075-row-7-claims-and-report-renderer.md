---
date: 2026-09-23
status: standing
kind: decision
touches:
  - gars/_system/claims/
  - gars/tests/test_claim_constraints.py
  - gars/tests/test_render_report.py
  - gars/tests/fixtures/claims/
  - README.md
  - DEVELOPMENT.md
  - docs/implementation/row_7_change_report.md
symptoms:
  - a committed claim can lose its last evidence link
  - a report can omit a section or strip a DEGRADE limitation
---
# Row 7 claims and report renderer

## Context

Row 7 of §18, R-080/R-081/R-082, R-083's UNKNOWN rule, R-141 rendering,
§8.3's mismatch flag and §17's orphan metric govern this repository work.
The starting commit is `701368f`. The methods and reproduction implementation
belongs to row 6. The rnaseq-de report and its gate remain unchanged.

The owner's words, 23 September 2026, verbatim:

> D-10 yes (throwaway local PostgreSQL; R-131 binds only the authoritative DB), methods/reproduction sections left to row 6, decisions 0075-0079, fresh Claude review, push on my word.

The owner first gave "D-10 yes" when approving the parallel lanes on
22–23 September; only those two words of that earlier reply concern this row.
D-10 asks whether R-131 prevents development against a throwaway local database.
The answer is no: R-131 binds the authoritative PostgreSQL. All test claim rows
are confined to scratch-backed, disposable PostgreSQL 16 compose stacks.
No claim row is written to a persistent or authoritative database by this row.

Everything in the following implementation specification is **the lane's
specification, not the owner's words**. It must not be attributed to the owner.

## Decision

The schema is applied by `psql -1 -v ON_ERROR_STOP=1`. Its leading role block
creates the cluster-global owner and writer only if absent; the next statement
refuses re-application when `to_regclass('claims.claim')` is present. Transactional
DDL makes that refusal preserve all existing rows, constraints and triggers.
A second empty database reuses the roles and initializes independently.

All objects live in `claims`, owned by NOLOGIN `gars_claims_owner`. The LOGIN
`gars_claims_writer` is neither superuser nor role creator, and has no ownership.
Tests generate its password in row 5's scratch folder, never in source. PUBLIC
function execution is revoked before explicit grants. The writer can select
tables, insert artifact/source/evidence parents, execute claim insertion/export,
and update/delete evidence links. It cannot directly insert claims or runs,
truncate, delete evidence, disable triggers, or assume the owner role.
Run registration authority remains the separately numbered unresolved ruling
in the change report; it is not silently supplied by SECURITY DEFINER.

`run` binds question, manifest path/hash and mandatory exploratory status.
`artifact` and `source` are minimal evidence parents. Claims carry their run FK,
one of four types, text, the two JSONB groups, reference release and workflow
version. Evidence carries exactly one parent, a closed kind and a closed relation.
Both claim-evidence FKs restrict deletion. `claim_insert` inserts a claim and
at least one link in one transaction, refuses exploratory runs and empty arrays,
and is SECURITY DEFINER with `search_path = claims, pg_temp`. Deferred row
constraint triggers check new claims, deleted links, and both old/new claim IDs
on link updates. A deleted claim is skipped, permitting whole-claim deletion by
its owner in a transaction. Writer attacks use a real writer login and assert
its identity and non-superuser status before each attempt.

Biological support permits only statistical_support, replication, orthogonal_assay,
effect_size and literature. Process risk permits data_quality, confounding_risk,
provenance_completeness, qc_disposition and limitation. The last two keys are an
explicit departure from the spec's three-key process-risk list, required here to
carry R-141's DEGRADE and adjacent limitation text. Both groups require JSON
objects; empty objects are allowed and render as present empty groups, not as
absent fields. Whitespace-only strings render UNKNOWN. JSON null, scalars, arrays and other keys
are refused. Reserved `confidence` and `score` keys are also refused inside nested
objects and arrays. No scalar confidence column or reviewer-verdict column exists.

`claims_export` returns one PostgreSQL JSONB document, whose deterministic
serialization orders object keys and whose arrays explicitly order claims and
evidence by ID. It includes the run, evidence parents and claim-evidence links.
The container psql export is the renderer's only database input. Snapshot mode
reads exactly snapshot JSON, manifest JSON and the shipped template. Database
mode substitutes the export for the snapshot file, using row 5's static
container-client transport and in-container password read. No manifest path,
evidence path, ledger, agent prose or reproduction script is opened.

The report preserves all eight §7.8 headings in order and verifies each named
source placeholder before rendering. Validation completes before an atomic
write; refusals preserve any existing output. Source text is escaped so it
cannot inject headings or table rows. Every claim has an adjacent limitation
row; DEGRADE without nonblank limitation text refuses the report. Different
reference releases flag every affected claim. The manifest's supplied hash is
verified against the actual input bytes when present.

The twenty observation verbs denied for HYPOTHESIS, case-insensitively at word
boundaries, with base, third-person, past, past participle and present-participle
forms, are: **show, demonstrate, prove, confirm, establish, reveal, observe,
detect, measure, find, identify, verify, validate, determine, record, document,
quantify, indicate, exhibit, display**. Irregular forms include shown, proven and
found. This lexical rule deliberately refuses even a negated use of these verbs;
it is not a scientific truth classifier.

Fresh Claude review identified a REPEATABLE READ write-skew case with two
concurrent link deletions. The checker now performs a real, value-preserving
claim-row UPDATE, so PostgreSQL detects the competing row version and refuses
one transaction with 40001. A two-session writer regression exercises this.
Unsafe writer attributes, memberships, replication-parameter privileges and role
defaults refuse within the role block; this is not an audit of all cluster roles.
The renderer validates snapshot types, supplied digest syntax and QC dispositions.
For lexical checks it decomposes Unicode, preserves whitespace boundaries, and
checks both deleted and space-separated interpretations of invisible marks and
fillers. Snapshot IDs must be bigint-compatible integers, group keys obey the
schema rules, and template sources must be actual unformatted replacement fields. A DEGRADE limitation must retain a letter or number.
This does not transliterate cross-script lookalikes into English verbs. These are
implementation corrections, not new owner rulings.

### UNKNOWN sources

| Section or field | Source or owner awaited |
|---|---|
| question | `run.question`; absent: run registration |
| data and classification | `row 6: data_class, venue, purpose` |
| methods | manifest `pipeline_commit` and `params`; claims' workflow/version and reference release |
| genome hashes, model/prompt/routing | `row 6` |
| QC summary | claims' `qc_disposition`; absent: `§14 QC dispositions` |
| claims and adjacent limitations | `claims snapshot` |
| manifest reference | run registration's path and sha256 |
| reproduction command | `row 6` |
| cost | `row 11: docs/ledger.csv has no per-run cost source` |

Every absence uses `UNKNOWN (owned by <owner>)`. No missing value is inferred
from prose. No row-6 manifest fields, checks, reruns, tolerances or pairing tests
are built here.

### THREAT MODEL

Covered: a client connected as `gars_claims_writer` (not owner, not superuser), and any code path in this repository. It must not be able to:
  - leave a committed claim with zero evidence links by any statement sequence: a direct INSERT on claim; claim_insert with an empty evidence list; DELETE or UPDATE of claim_evidence rows (in the same transaction or later ones); SET CONSTRAINTS ALL IMMEDIATE games; TRUNCATE; deleting a referenced evidence row; ALTER TABLE … DISABLE TRIGGER; DROP TRIGGER; SET session_replication_role = replica;
  - create evidence with both or neither of artifact_id/source_id;
  - store a scalar confidence, or a key outside the two groups;
  - register a run, or mark one non-exploratory, and so produce a claim from an exploratory run;
  - emit a report missing a section, a HYPOTHESIS with an observation verb, a DEGRADE claim without its limitation, or any text sourced outside the snapshot, the manifest and the shipped template.
Not covered, named as residual in 0075: the owner role or a superuser (they can disable triggers); the content truth of a claim's text or evidence; deployment, backup and restore of the authoritative database (R-131); concurrency beyond PostgreSQL's own transaction semantics.

## What this does not close

- **NOT met:** deployment to the authoritative database; it waits on R-131's
  standing verified restore. No deployment occurs here.
- **NOT met:** R-120 and R-122. The spec says "the claim table of §7.8 *is* this class",
  but the result-class memory store and `test_memory_no_laundering.py` are not built here.
- **NOT met:** R-089 STALE on workflow deprecation.
- **NOT met:** §8.3's pairing test and R-090; both belong to row 6. Rendering a
  mismatch flag is not the pairing test or registry validation.
- **NOT met:** row 6's methods and reproduction fields, checks and reruns.
- **NOT met:** per-run cost figures.
- **NOT met:** pilot-1 orphan-claims measurement. A synthetic fixture does not
  satisfy §17's pilot threshold; README's number/date cells retain `unmeasured` for that pilot metric.
- **NOT met:** superuser/owner containment; these principals can disable triggers.
  Content truth and concurrency beyond PostgreSQL transaction semantics also
  remain outside this threat model.
- **NOT met:** availability guarantees, authentication of supplied snapshot files,
  and cross-script homoglyph classification. Malformed claims may be stored but
  refuse rendering; the owner can delete a whole claim and its links. Installation
  without the required single transaction is outside this application contract.
- **NOT met:** unresolved run-registration authority and its positive control,
  pending the owner's ruling listed in the change report.
- **NOT met:** owner approval of this protected-prefix addition. Reserved record
  0079 is the owner's approval of this row's new `gars/_system/` code, committed
  by the owner at merge. The producer neither writes it nor claims that approval.

## Test

`python3 gars/tests/test_claim_constraints.py` and
`python3 gars/tests/test_render_report.py` run directly and through existing suite
discovery. The change report records exact results, the fixture's measured
`orphan claims` line, all eleven disposable fault plants and baseline red.
The observed fixture measurement is `orphan claims: 0/4`; this is not pilot 1.
The row-5 scratch helper/gate is reused. Explicit `GARS_TEST_NO_CONTAINER=1`
skips; otherwise a failed runtime probe fails under CI and skips outside CI,
with the probe named. Every started stack is torn down with `down -v`.

## Status

Standing implementation record, subject to fresh independent review and owner
approval. Registration authority is stopped pending a ruling; full row exit is
not claimed. Records 0076–0078 remain unused; reserved 0079 belongs to the owner.

## Date

2026-09-23

## Addendum — owner ruling 1, 2026-09-23

The question put to the owner was the lane's wording. It is reproduced below
with only the deployment machine name redacted to obey this round's explicit
prohibition on committing personal names, logins or machine names:

  Who may register a run that can carry claims?
  1. The owner only (recommended). The writer can register runs, but they're always exploratory, so they can never carry claims.
     Matches R-087 as written: nothing the agent does can make its own run claim-eligible. No new table. Cost: each real run needs one owner-side registration step (on [deployment host redacted], at deployment).
  2. The writer, but only against a list the owner approved in advance.
     More automatic, but adds an approved-runs table and a new surface for the reviewer to attack.
  With either answer, the positive control becomes: the owner registers a claim-eligible run, then the writer adds a claim to it and that commits.

The owner's answer, verbatim: **"1"**.

Everything below is **the lane's implementation specification of option 1,
not the owner's words**. This addendum resolves the registration stop recorded
above without changing any preceding byte of 0075.

- `claims.run_register(bigint,text,text,text)` is SECURITY DEFINER with
  `SET search_path = claims, pg_temp`. The writer may execute it. It inserts
  `exploratory = true` and accepts no eligibility parameter.
- `claims.run_register_eligible(bigint,text,text,text)` is the owner-only
  registration function, with the same fixed search path. It inserts
  `exploratory = false`. PUBLIC execution is revoked and the writer receives
  no execution grant. The schema owner owns both functions.
- The writer still has neither INSERT nor UPDATE on `claims.run`; neither
  registration function changes an existing run. The threat-model sentence
  above about registration now means the writer cannot register a claim-eligible
  run, or change eligibility, through any writer-accessible path.
- The corrected positive control is owner registration followed by a committed
  writer `claim_insert` with evidence. A writer-registered run refuses claims
  with the exploratory message. The owner-only call, direct INSERT and flag
  UPDATE each refuse the writer with SQLSTATE 42501. Tests assert the actual
  writer identity and non-superuser status before writer statements.
- The required disposable fault grants the writer EXECUTE on the eligible-run
  function; `test_writer_cannot_register_eligible` must then fail because the
  forbidden call commits. The change report records this run's measured results.

D-10's local-only scope is unchanged: only throwaway PostgreSQL is used; R-131
still governs authoritative deployment. Methods/reproduction remain with row 6.
Reserved 0079 belongs to the owner and is not written here. This ruling resolves
the registration authority question; it does not approve a push or merge.

## Addendum — review round 2, 2026-09-23

These are the lane's review corrections, not new words or rulings from the
owner. All preceding bytes remain unchanged. This addendum supersedes the
writer link-mutation grants and sentence-only lexical gate described above.

### THREAT MODEL extension

The covered writer must not **rewrite or remove a committed claim's evidence
links**. UPDATE and DELETE on `claims.claim_evidence` are revoked; direct INSERT
remains unavailable. The writer may create evidence parents and insert a new
claim with links through `claim_insert`, but cannot change existing links.
The deferred triggers remain defence for owner paths. Deletion, reassignment,
immediate-constraint and REPEATABLE READ cases now exercise the non-superuser
owner role; separate writer attacks require SQLSTATE 42501, including all three
committed-link rewrites from the supplied review. A disposable UPDATE re-grant
must make the new writer regression fail. This does not claim owner containment.

Every snapshot claim must contain a nonempty evidence list. Missing, non-list
and empty evidence refuse with `claim N has no evidence links`, preserving an
existing output. Snapshot authenticity remains unverified; this local invariant
is enforced independently of authenticity.

The HYPOTHESIS observation-verb gate covers every free-text string rendered in
its table row and adjacent limitation row, including nested JSON keys/values,
evidence descriptions and reference release. The same Unicode normalization and
twenty verb families apply. Noun uses such as `finding`, `record`, `measure`,
`document` and `display` are also refused by this deliberately lexical rule;
no part-of-speech classifier is claimed.

UNKNOWN labels now identify `row 7: claim writer`, `row 7: run registrar` and
`row 6: manifest producer` instead of the source names `claims snapshot`,
`run registration` and `manifest`. The QC and other existing row labels remain.
No row-6 fields or methods/reproduction implementation is added.

The extra `qc_disposition` and `limitation` process-risk keys remain the lane's
previously documented departure for R-141. The owner may ratify it in reserved
0079; the producer neither writes that record nor supplies that approval.

Verification and the responses to R7-01 through R7-06 are appended to the row-7
change report. D-10's disposable-only scope and all other residual gaps remain.

### Fresh review clarification — 2026-09-23

The same HYPOTHESIS gate also covers its workflow-version text in the methods
section. With constraints already IMMEDIATE, `claim_insert` refuses at the claim
INSERT before inserting links; the tests assert that fail-closed behavior for
both principals separately from immediate deletion of already committed links.

### Default privileges hardening — 2026-09-23

Fresh source review also identified administrator-configured default ACLs that
could expand the writer's privileges at installation. Before explicit grants,
the installer now revokes all schema, table and function privileges from PUBLIC
and the writer. The cold-twin regression installs under deliberately permissive
schema/table/function defaults, then requires 42501 on direct writes, link
rewrites, TRUNCATE, eligible registration and schema creation. Export bytes
remain identical. This is installation hardening, not containment of an owner
or superuser who later grants privileges or disables triggers. The schema's
application contract and explicit writer surface remain unchanged.

### Lexical boundaries clarification — 2026-09-23

The final fresh source review found that regex word boundaries treat underscores
and digits as word characters, permitting readable verbs such as `__proves__`
and `confirms2`. The gate now uses letter boundaries after the existing Unicode
normalization: digits and underscores delimit verbs, while letters keep words
such as `showingly` and `unconfirmed` intact. Tests cover these cases in every
gated claim surface; a disposable reversion to word boundaries must fail them.
This clarifies and strengthens the lane's lexical implementation; it does not
change the twenty verb families or introduce a scientific classifier.

The escaping comment is narrowed to headings, table rows and executable HTML.
Suppression of GFM's extended automatic links is not claimed or verified.
