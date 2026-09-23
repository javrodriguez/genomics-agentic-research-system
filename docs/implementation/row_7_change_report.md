# Row 7 change report

Repository-side implementation from `701368f`, on `build/gars-row-7-claims`.
**Full row exit NOT met:** run-registration authority and its specified writer
positive control are stopped at owner ruling 1 below. The independent schema,
renderer, fixture and attack checks are implemented; their measured results do
not resolve that authority question. No deployment, push, merge or self-approval.

## Requirements and acceptance

| Requirement | Changed files | Acceptance | Result and red-on-fault |
|---|---|---|---|
| R-080 cardinality and evidence parents | `gars/_system/claims/claims.sql`; `gars/tests/test_claim_constraints.py`; `gars/tests/fixtures/claims/fixture.sql` | Deferred insert, delete, update, immediate-constraint games, privilege and FK attacks; populated-fixture orphan query | Implemented independent of registration; red-on-fault seen: yes, six SQL plants below |
| R-081 two separate JSON objects | same schema and DB test | Empty objects accepted; null/scalar/array and unknown keys refused with 23514 | Red-on-fault seen: yes, accepting `confidence` (including nested reserved keys) causes `test_confidence_groups` to fail |
| R-082 sections, deterministic rendering, hypothesis vocabulary | `gars/_system/claims/report_template.md`, `render_report.py`; `gars/tests/test_render_report.py`; snapshot/manifest/golden fixture | CLI golden equality, section-source refusals, 20 verb families, spec-list drift and three-input sweep | Red-on-fault seen: yes, section/absence/verb/fourth-file plants below |
| R-083 absence rule only | renderer and fixture | Exact `UNKNOWN (owned by <owner>)` strings | Named unknown-source test passes; no event-report implementation claimed |
| R-141 rendering only | renderer, template, fixture, rendering tests | DEGRADE requires visible limitation, directly under its claim row | Red-on-fault seen: yes, removed DEGRADE guard fails its named test |
| §8.3 mismatch flag only | renderer and fixture | Both releases produce a visible flag beside each affected claim | Golden and fixture assertions; pairing test/R-090 NOT met |
| Export binding and container input | schema, DB tests, committed `snapshot.json` and `report.md` | Loaded export equals snapshot bytes; `--from-db` equals golden bytes; cold twin and re-apply preservation | Live PostgreSQL 16, no database skip in direct acceptance |
| R-087 exploratory refusal | schema and DB tests | Existing exploratory run cannot produce claims; writer cannot change its flag | Existing-run refusal passes; registration authority and combined positive control NOT met |
| §17 pilot metric | README test-path cell only | Populated synthetic-fixture query | Fixture measured below; pilot 1 NOT met, number/date cells remain unchanged |
| R-163 documentation | record 0075 and regenerated decision index; this report | Existing decision checks and contracts | Protected-prefix owner approval reserved to 0079, NOT supplied here |

The measured fixture line, verbatim:

```text
orphan claims: 0/4
```

Positive additional claims produce `orphan claims: 0/5`; neither line is pilot 1.
README's existing number/date cells remain `unmeasured`. Its only evidence-row
change is the test path. `docs/implementation/dod_current.md` and its generator
are unchanged.

## Fault witnesses

Every fault was applied to a disposable copy and run against the named test.
The database runner used one new row-5 scratch compose stack, reapplied a separate
mutant schema to a newly created test database per case, and retained the first
real assertion failure. No production file was mutated for these controls.
The renderer runner copied the claims directory per fault and pointed the real
CLI tests at that copy. All eleven controls are producer-visible, not sealed
reviewer-catch or mutation-score evidence.

| Planted fault | Named failing test | Red seen |
|---|---|---|
| INSERT deferred trigger dropped | `ClaimConstraintTests.test_deferred_insert_and_owner_whole_claim_deletion` | yes; orphan INSERT commits |
| INSERT trigger made IMMEDIATE-only | same | yes; valid insert-then-link transaction refuses |
| TRUNCATE granted to writer | `test_direct_writes_and_privilege_escalation` | yes; TRUNCATE commits |
| Evidence exactly-one CHECK dropped | `test_evidence_exactly_one_and_enums` | yes; both/neither parent accepted |
| Evidence FK changed to CASCADE | `test_fk_restrict_as_owner` | yes; owner deletion succeeds instead of 23503 |
| `confidence` key accepted in bio_support | `test_confidence_groups` | yes; top-level allowlist widened and recursive reserved-key check disabled |
| Template cost section removed | `RenderReportTests.test_fixture_every_section_golden_and_deterministic` | yes; valid fixture no longer renders |
| Missing section source allowed to render empty | `test_missing_section_source_refused` | yes; section-source refusal replaced by pass |
| `show` verb family removed | `test_hypothesis_all_verbs_and_inflections` | yes; independent oracle still requires refusal |
| DEGRADE rule removed | `test_degrade_requires_limitation` | yes; unqualified claim renders |
| Renderer opens `agent_prose.md` as fourth file | `test_three_inputs_invariant_sweep` | yes; read allowlist assertion fails |

## Execution and command record

All commands ran from the repository root unless stated. Python was 3.13.2,
including the harness (above its 3.9 minimum). Production code remains stdlib and
Python 3.6-parseable; actual 3.6.8 execution is NOT met. Every invocation set
`TMPDIR`, `TEMP` and `TMP` to the designated existing scratch sibling. Paths below
are repository-relative; no system-temp fallback was used.

```bash
export TMPDIR="$(cd ../gars-row-7-scratch && pwd)"
export TEMP="$TMPDIR" TMP="$TMPDIR" GARS_ROW5_SCRATCH="$TMPDIR"
export PYTHONDONTWRITEBYTECODE=1
```

`docker info` returned exit 0. The direct DB test uses the unchanged
`infra/compose/postgres.compose.yml` (`postgres:16`), row 5's unique project,
scratch bind volume/password, and health-plus-loopback readiness probe. Attacks
execute container `psql -U gars_claims_writer`, asserting current_user and
non-superuser status first. The password is a fresh scratch UUID, read inside
the container. It is never committed or printed. Each stack finished with
`docker compose ... down -v`; no persistent database was contacted.

Schema and fixture loading use `psql -1 -v ON_ERROR_STOP=1 -f -`, with SQL on
stdin. The fixture snapshot was generated by `SELECT claims.claims_export(1)`
from the loaded fixture, after which the stack was torn down before writing the
committed snapshot. The golden was generated with:

```bash
python3 gars/_system/claims/render_report.py --snapshot gars/tests/fixtures/claims/snapshot.json --manifest gars/tests/fixtures/claims/manifest.json --out gars/tests/fixtures/claims/report.md
```

The following required commands were run; exact final summary lines follow:

```bash
python3 tests/run_tests.py
python3 tests/check_contracts.py
python3 tests/check_counts.py
python3 evals/test_harness.py
python3 evals/check_results.py --controls --lexicon
python3 gars/tests/test_claim_constraints.py
python3 gars/tests/test_render_report.py
```

For the broad suite only, `GARS_TEST_NO_CONTAINER=1` explicitly selected the
existing no-container mode; the direct DB command separately ran with that
variable unset and Docker answering. Offline environment controls verify that
this explicit skip precedes CI, a missing runtime fails under CI, and the same
probe skips outside CI. These controls do not require a new environment variable.

| Command | Final summary, verbatim |
|---|---|
| `python3 tests/run_tests.py` | `Ran 412 tests in 405.567s` / `OK (skipped=29)` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/check_counts.py` | `suite: 426 tests, from unittest's loader` / `enforced=3` / `clean — every current claim matches the suite` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 241.397s` / `OK` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` |
| `python3 gars/tests/test_claim_constraints.py` | `Ran 17 tests in 272.595s` / `OK` |
| `python3 gars/tests/test_render_report.py` | `Ran 12 tests in 32.605s` / `OK` |

The renderer also printed `template renders fixture: 8/8 sections`. The broad
suite's class-level skip omits the 14 database methods from its run count;
426 is the loader total, while the direct database run executes those methods
plus three offline environment controls. The results checker retained two
pre-existing skipped controls; its lexicons passed 42/42, 24/24, 21/21 and 69/69.
The final prohibited-path diff was empty, and container inspection confirmed
that none of this row's compose stacks remained. Unrelated stacks were untouched.

The initial implemented independent DB tests printed `Ran 12 tests in 292.831s`
and `OK`; the initial renderer printed `Ran 10 tests in 32.083s` and `OK`.
Additional review regressions are included in the final summaries above.

Parent red used `git archive 701368f gars/tests/support.py` extracted under a
scratch `row7-parent-*` directory, overlaid only the two new test modules, then
ran each direct command above from that directory. Both exit nonzero at import:
`test_claim_constraints.py` names missing `gars/_system/claims/claims.sql`, and
`test_render_report.py` names missing `gars/_system/claims/render_report.py`.
The same independent acceptance tests are green with this commit's files. This
is not a claim that the unresolved whole-row registration acceptance is green.

Fault commands were `python3 ../gars-row-7-scratch/db_faults.py` and
`python3 ../gars-row-7-scratch/render_faults.py`. Each scratch driver constructs
the substitutions listed above, invokes the actual named unittest, and asserts
failures exist with no setup error. An initial DB-fault invocation without
`GARS_ROW5_SCRATCH` refused before starting a stack; it was rerun with the stated
environment and all six SQL faults were observed red.

The index was regenerated, never hand-edited, with
`bash docs/decisions/build_index.sh`. Counts in README/DEVELOPMENT state the
loader's new total while preserving the prior dated 397-case measurement.
The first broad run printed `Ran 410 tests in 554.827s` and
`FAILED (errors=3, skipped=29)`: the new probe-control mock failed to preserve a
classmethod interface. That test defect was repaired. After quote escaping was
corrected, two golden checks correctly failed until the fixture report was
regenerated by its CLI. No inherited expectation was changed.

No existing test expectation changed:

| Existing expectation changed | Reason |
|---|---|
| none | All changes are new row-7 tests; no inherited acceptance was weakened |

## Fresh review and corrections

A fresh Claude CLI context received only a supplied source bundle, with tools,
customizations, MCP and persistence disabled:

```bash
claude --print --safe-mode --no-session-persistence --tools '' --strict-mcp-config --setting-sources '' --output-format json < ../gars-row-7-scratch/review-input.txt > ../gars-row-7-scratch/claude-review.json
```

The review is `independent_context`, not `external_human_seal`, and not owner
approval. Its known registration-authority gap remains unresolved. Review
findings and producer corrections: REPEATABLE READ write skew is prevented by
a real claim-row version update in the deferred checker; Unicode-normalized
verb checks, strict snapshot types and QC dispositions reject the reported
renderer evasions; invisible-only limitations refuse; the read sweep resolves
both allowed and observed paths; unsafe pre-existing roles refuse at apply;
apostrophes remain readable; malformed JSON shapes produce readable refusals.
Follow-up source reviews found additional cases: nested reserved scalar keys,
preconfigured replication privileges/defaults, blank Unicode fillers, malformed
supplied hashes and unescaped markup. The final implementation refuses those
cases, and the read sweep now covers `os.open` and import-time data reads too.
A later review caught a whitespace-boundary regression in Unicode normalization.
Whitespace is preserved, and invisible separators are checked both joined and
separated. Claim IDs and snapshot group keys are validated; source placeholders
are parsed as real formatting fields, so escaped braces cannot hide an absent
source. Empty JSON objects are explicitly permitted by the lane and remain
present empty groups; whitespace-only strings are UNKNOWN. Owner-side FK attacks
now explicitly `SET ROLE gars_claims_owner` before the statement.
The password interpolation is restricted to row 5's generated 32-character
UUID hexadecimal alphabet before constructing SQL.
Named regressions cover the reproduced integrity and rendering failures. The scratch password-sharing concern
is bounded by this lane's mandated row-5 test transport: it tests a connected
writer principal, not production credential isolation. Deployment credentials
remain NOT met; no new secret configuration or deployment path was invented.

Three separate fresh source reviews completed. The second and third used the
same CLI flags with `review-final-input.txt` / `claude-review-final.json` and
`review-latest-input.txt` / `claude-review-latest.json`, respectively, in the
scratch sibling. SHA-256 of the raw returned review artifacts:

| Artifact | SHA-256 |
|---|---|
| `claude-review.json` | `cc03d7eadcf53c1645859c803ae38634b90ae2d645fe4c93a28248e510860ccd` |
| `claude-review-final.json` | `b957201bd3d796dfb0e3e53332312c402c4b108c44e4d8fd1d7528a8c953e843` |
| `claude-review-latest.json` | `61a5caed5bca8cf1f14cf565a8e8dfb2462a42bf12e31fcfb696fbb090767e21` |

These reviews executed no tests. The producer applied the last corrections
and then obtained the final test results above; no subsequent independent
approval of those corrections is claimed. Review artifacts remain scratch
records, not a fabricated committed review-evidence seal.

Review dispositions outside those fixes:

| Finding | Disposition |
|---|---|
| Applying without `-1` | Outside the explicit application contract; the supported CLI and tests always use one transaction |
| Invalid claim text can prevent report generation | Intentional refusal required by R-082/R-141; report availability and writer correction rights are not added |
| Cross-script homoglyphs | NOT met as a classifier; the specified English lexical denylist is not a universal visual-equivalence test |
| Other principals inheriting owner privileges | Owner-role residual; writer inheritance and parameter access are checked |
| Arbitrary nested group values | Values remain JSON; reserved `confidence`/`score` keys are forbidden at every depth |
| Snapshot provenance / empty evidence in supplied files | Snapshot authenticity is NOT met; R-080 is enforced on the database, and absent report inputs use UNKNOWN |
| HALT execution behavior | Row 14 execution policy, outside this row's R-141 DEGRADE rendering requirement |
| Explicit table locks / bad-claim availability | NOT met; no availability guarantee is inferred from the integrity threat model |

After the review correction, a disposable reversion to the old lock-only checker
made `test_repeatable_read_cannot_orphan` red. The deferred/IMMEDIATE trigger
faults and renderer faults were rerun against the revised code. The final SQL
fault run also tests nested-key protection; it must actually accept the bad key,
not merely alter an unused allowlist. These commands use the same scratch driver
pattern, including `python3 ../gars-row-7-scratch/db-review-faults.py`.

## Hours

Human-touch hours and model/provider cost are **UNKNOWN (not metered)**. Test
wall times are reported above; they are not substituted for human hours, pilot
cost or the row's budget. No ledger entry or cost figure is invented.

## Residual gaps

Every item below is **NOT met** by this row:

- Complete run registration and the required writer registration-plus-insertion
  positive control, pending ruling 1.
- Authoritative deployment and its R-131 standing verified restore prerequisite.
- R-120/R-122 result-class memory store and `test_memory_no_laundering.py`.
- R-089 STALE on workflow deprecation.
- R-090 and §8.3's pairing test, owned by row 6.
- Row 6's full methods/reproduction fields, manifest checks, reruns and tolerances.
- Per-run cost figures and pilot-1 orphan-claims measurement.
- Owner/superuser containment, content truth, and concurrency beyond PostgreSQL
  transaction semantics. The new two-session regression covers the reported
  REPEATABLE READ case only, not an exhaustive concurrency proof.
- Actual Python 3.6.8/cluster execution and deployment credential separation.
- Snapshot authenticity, universal homoglyph classification and availability guarantees.
- R-165 later committed review/Bench evidence snapshot; this code commit is not
  claimed pushable, and no out-of-bounds evidence producer is modified.
- Protected-prefix owner approval: reserved 0079 is the owner's separate commit
  at merge. Records 0076–0078 are unused. No producer approval or merge occurs.

## Owner rulings needed

1. **Authority for non-exploratory run registration.** The lane grants the writer
   EXECUTE on `run_register` and requires successful writer registration followed
   by claim insertion, but forbids the writer from choosing a non-exploratory
   status. SECURITY DEFINER grants privilege; it does not establish the truth of
   an agent-supplied exploratory flag. No authoritative eligibility source or
   binding is specified. This part is stopped; no registration function or
   permissive substitute is shipped. Options:
   - owner pre-registers eligibility; the writer may register non-exploratory
     runs only against that binding, otherwise exploratory;
   - writer registration always creates exploratory runs; the owner separately
     registers non-exploratory runs, and the positive-control requirement is
     clarified accordingly.
   The question was sent during implementation. No answer has been received,
   and neither option is attributed to the owner or chosen silently.
