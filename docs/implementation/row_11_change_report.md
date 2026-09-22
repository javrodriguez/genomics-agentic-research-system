# Row 11 repository change report

Status: repository-side row complete under the owner's 22 September 2026 ruling.
The row is delivered as one commit on the requested branch. Independent review,
real Bench evidence, approval and merge remain outstanding; no push or remote is
supplied. The named citation and regeneration exits pass in this resumed run.

Starting branch: `build/gars-row-11-records`.
Starting HEAD: `af4159a653db5c4ee14bc6415090d718c580a9db` (row 15's approved,
unmerged head). The separate study's done-commit merge hold remains.

## Requirement, change, acceptance and result

| Requirement | Changed files | Acceptance | Result; red-on-fault seen |
|---|---|---|---|
| R-001; owner ruling 8A | `tests/test_decision_links_resolve.py`, `docs/decisions/TEMPLATE.md`, `docs/decisions/0058-row-11-records-links-trailers-release-check.md` | Direct link module: tracked citations and all numbered record fields | PASS, `citations: 288/288 resolve`; yes, singular/plural dangling references and missing Test refuse; incorrectly rejecting legacy records and counting a bare year break their positive assertions |
| R-163; owner ruling 7A | `gars/_system/hooks/pre-commit`, `gars/tests/test_hooks_records.py` | Same checker over index blob IDs; actual hook calls in scratch | PASS; yes, an unstaged repair cannot hide either dangling form; unreadable decisions refuse while gitleaks still runs |
| R-165 | `gars/_system/hooks/pre-push`, `gars/tests/test_hooks_records.py` | Trailer parser, per-commit range selection, activation, committed snapshot reads, session inequality and Bench commit binding | PASS, including actual production-hook calls: later committed snapshot required, same-session reviews and wrong Bench hashes refuse; staged/working repairs have no effect; every outgoing ref and all inherited vetoes are checked |
| R-116; R-170 | `scripts/release_check.py`, `tests/test_release_check.py`, `docs/implementation/dod_current.md` | Regenerate all thirteen §17 cells; `--check`; `--tag`; direct module | PASS for repository regeneration/refusal mechanics; yes, hand-edited cells and stale rows refuse; release eligibility itself **NOT met** |
| Existing row 15 hook invariants | `gars/tests/test_hooks_gitleaks.py`, `gars/tests/test_secret_containment.py` | Existing modules, all assertion ASTs compared to starting HEAD | PASS. Four added fixture/import lines supply a minimal staged legacy record. Every existing assertion is unchanged; no scanner, installer, marker or threshold is weakened |
| Living documentation and generated index | `README.md`, `DEVELOPMENT.md`, `docs/decisions/CONTEXT.md`, this report | `tests/check_counts.py`; `bash docs/decisions/build_index.sh` | PASS. Current count is loader-derived; historical row 15 counts are marked historical using the existing exemption convention. The index is script-generated |

The original rule 4 already authorised extending hook tests with every assertion
preserved. The producer's extra permission question about this fixture repair was
unnecessary; no additional owner ruling is claimed for that fixture repair. The
owner has now settled snapshot ruling 1: require later committed evidence.
Record 0058 attributes this ruling and its accepted cost to the owner.

## Citation measurements and command

Before changes: `citations: 287/287 resolve`.
Prepared-tree count before this resume: `citations: 288/288 resolve`.
After the resumed change: `citations: 288/288 resolve`.
The extra occurrence is the uppercase plural reference in the new acceptance
fixture's source. Neither number is the frozen specification's "210". The owner
ruled 7A and 8A; their exact rulings are quoted in 0058, attributed to the owner.
No existing record or frozen specification was edited.

Both measurements used this Python command from the repository root, first inline
and then saved as `count_citations.py` in the designated scratch folder:

```python
import pathlib, re, subprocess
names = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
k = 0
bad = []
for name in names:
    p = pathlib.Path(name)
    if name.startswith('docs/specs/') or not (p.suffix in ('.py', '.sh', '.yml', '.yaml', '.toml') or p.name == '.gitignore' or (name.startswith('gars/') and p.suffix == '.md')):
        continue
    for number in re.findall(r'\bdecisions?\s+(\d{4})\b', p.read_text(), re.I):
        k += 1
        if not list(pathlib.Path('docs/decisions').glob(number + '-*.md')):
            bad.append((name, number))
print('citations: %d/%d resolve' % (k - len(bad), k))
if bad:
    print(bad)
    raise SystemExit(1)
```

The starting-HEAD count was re-derived in this resume from Git objects: substitute
`git ls-tree -r --name-only -z af4159a653db5c4ee14bc6415090d718c580a9db`
for `git ls-files -z`, read each file with `git show <starting-HEAD>:<path>`, and
resolve record names against that same tree. It again printed
`citations: 287/287 resolve`. The working-tree command above printed
`citations: 288/288 resolve` both before and after the resumed change.
New paths were staged by explicit name before the final tracked-tree measurement.
The named acceptance additionally checks record fields and prints:

```text
citations: 288/288 resolve
```

## Fault observations

| Planted fault / positive control | Red-on-fault seen | How |
|---|---|---|
| Dangling singular form | yes | Stage the invalid reference, replace the working copy with clean text; the index check and actual pre-commit refuse |
| Dangling plural form | yes | Same actual-hook exercise with plural spelling |
| Bare `(2024)` must not count | yes | Correct checker prints zero citations; temporarily replace its pattern with a bare-parenthesis matcher, then observe the correct-acceptance assertion fail |
| New record missing Test | yes | Stage a record dated 2026-09-22 without Test; refusal; add Test and it passes |
| Legacy record must still pass | yes | Valid old frontmatter passes; temporarily move the legacy cutoff back, and the legacy-acceptance assertion fails |
| System commit without trailers | yes | Real scratch commit objects, including an earlier outgoing commit behind a well-formed tip; helper and production pre-push refuse |
| Equal Review and Session IDs | yes | Equality refuses in the helper and production hook; a distinct committed reviewer ID passes; duplicates and absent IDs also refuse |
| Hand-typed DoD cell | yes | Replace a generated `unmeasured` cell with `100%`; both `--check` and `--tag` refuse; regeneration restores the exact original bytes |
| Stale release row | yes | Fourteen days passes the age boundary; fifteen days refuses. The actual `--tag` entry point also refuses a mocked stale producer result whose generated bytes match |
| Unreadable decisions folder | yes | Set a scratch decisions directory's mode to zero; actual pre-commit refuses and still runs gitleaks; restore permissions in `finally` |

Additional snapshot controls use the actual shipped pre-push in disposable repos:

- Code-tip/self-reference: REFUSED; later committed evidence tip: PASS.
- Evidence missing from the outgoing snapshot: REFUSED despite correct staged files.
- Same-session review or wrong Bench hash committed at the tip: REFUSED despite
  repaired working/index bytes. A valid committed snapshot passes even with bad
  staged evidence or both working evidence files removed.
- Earlier snapshot, invalid paths and symlink evidence: REFUSED.
- A multi-ref push with one code-only tip: REFUSED even when another ref has evidence.
- Previous-hook, scanner and suite vetoes still refuse independently; trailer
  refusal still runs the scanner and suite. Source HEAD need not equal the pushed tip.

These are producer-visible controls, not independent sealed evidence.
The parent lacks the three named new acceptance artifacts: `git cat-file -e`
against the starting HEAD returned 128 for the link module, release script and
template. That is an absent-artifact observation, not a claim of a parent
behavioral test failure.

## Command environment and verification

Every shell invocation began by setting `TMPDIR`, `TEMP` and `TMP` to the owner's
designated sibling scratch directory. No system-temp fallback
was used. A portable spelling of the same environment, without a machine path, is:

```bash
ROW11_SCRATCH="$(cd ../gars-row-11-scratch && pwd)/"
export TMPDIR="$ROW11_SCRATCH" TEMP="$ROW11_SCRATCH" TMP="$ROW11_SCRATCH"
```

Commands ran from the repository root through the shell tool. The resumed suite,
named checks and direct modules used `python3`, **Python 3.8.2**, in the non-login
shell. The required `evals/test_harness.py` run used **Python 3.13.2** (the login
shell's `python3`) to meet its 3.9 floor. An earlier non-login harness invocation
ended with the following failure because that inherited harness uses
`ast.unparse` and `str.removesuffix`, which require Python 3.9 or later:

```text
Ran 44 tests in 348.629s
FAILED (errors=13)
```

This is retained as a failed attempt, not the required acceptance; the 3.13.2
rerun below supplies that acceptance without changing any eval file.
Gitleaks was **8.30.0**. New Python
syntax also parsed using Python's 3.6 grammar mode; that is not a 3.6.8 runtime test.
`GARS_ROW5_SCRATCH` was unset, as in the inherited row 15 validation. The 50 suite skips
are 39 row 5 scratch-dependent tests, seven missing pipeline checkouts, one unavailable
analysis dependency, one missing registry reference, one absent owner benchmark cohort,
and one absent sealed-design set. No row 11 test skipped.

Stdout and stderr were captured together under scratch (`> "$TMPDIR/name.log" 2>&1`).
The following summaries are verbatim from the resumed run; durations are preserved.

`python3 tests/run_tests.py` — exit 0; `resume-suite.log`:

```text
collected 217 tests from tests
collected 53 tests from gars/tests
citations: 288/288 resolve
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
Ran 270 tests in 320.071s
OK (skipped=50)
```

`python3 tests/check_contracts.py` — exit 0; `resume-contracts.log`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py` — exit 0; `resume-counts.log`:

```text
collected 217 tests from tests
collected 53 tests from gars/tests
suite: 270 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py (Python 3.13.2)` — exit 0; `resume-harness-py313.log`:

```text
Ran 44 tests in 328.474s
OK
```

`python3 evals/check_results.py --controls --lexicon` — exit 0; `resume-results.log`:

```text
clean — graded=1
```

`python3 tests/test_decision_links_resolve.py` — exit 0; `resume-links.log`:

```text
Ran 3 tests in 1.320s
OK
citations: 288/288 resolve
```

`python3 tests/test_release_check.py` — exit 0; `resume-release.log`:

```text
Ran 4 tests in 0.050s
OK
DoD cells regenerated: 13/13
DoD cells verified: 13/13 byte-stable
```

`python3 gars/tests/test_hooks_records.py` — exit 0; `resume-hooks-records-final.log`:

```text
Ran 11 tests in 31.486s
OK
```

`python3 gars/tests/test_hooks_gitleaks.py` — exit 0; `resume-gitleaks-hooks.log`:

```text
Ran 12 tests in 72.980s
OK
```

`python3 gars/tests/test_secret_containment.py` — exit 0; `resume-containment.log`:

```text
Ran 4 tests in 29.385s
OK
```

`python3 gars/tests/test_pre_push.py` — exit 0; `resume-prepush-inherited.log`:

```text
Ran 7 tests in 33.739s
OK
```

`python3 scripts/release_check.py` — exit 0; `resume-dod-generate.log`:

```text
DoD cells regenerated: 13/13
```

`python3 scripts/release_check.py --check` — exit 0; `resume-dod-check.log`:

```text
DoD cells verified: 13/13 byte-stable
```

`python3 scripts/release_check.py --tag` — exit 1; `resume-dod-tag.log`:

```text
DoD cells verified: 13/13 byte-stable
release tag: REFUSED (design-defect catch rate: unmeasured)
release tag: REFUSED (design-defect catch rate: threshold not established)
release tag: REFUSED (reviewer catch rate (code; science): unmeasured)
release tag: REFUSED (reviewer catch rate (code; science): threshold not established)
release tag: REFUSED (manifest completeness: unmeasured)
release tag: REFUSED (manifest completeness: threshold not established)
release tag: REFUSED (reproduction rate: unmeasured)
release tag: REFUSED (reproduction rate: threshold not established)
release tag: REFUSED (orphan claims: unmeasured)
release tag: REFUSED (orphan claims: threshold not established)
release tag: REFUSED (approval forgery: unmeasured)
release tag: REFUSED (approval forgery: threshold not established)
release tag: REFUSED (policy bypass; injection resistance: unmeasured)
release tag: REFUSED (policy bypass; injection resistance: threshold not established)
release tag: REFUSED (secrets containment: unmeasured)
release tag: REFUSED (secrets containment: threshold not established)
release tag: REFUSED (restore drill: unmeasured)
release tag: REFUSED (restore drill: threshold not established)
release tag: REFUSED (no false completion: unmeasured)
release tag: REFUSED (no false completion: threshold not established)
release tag: REFUSED (gars test suite: unmeasured)
release tag: REFUSED (gars test suite: threshold not established)
release tag: REFUSED (public artifact: unmeasured)
release tag: REFUSED (public artifact: threshold not established)
release tag: REFUSED (pilot 1: unmeasured)
release tag: REFUSED (pilot 1: threshold not established)
```

Before this resume, the initial integration run ended `Ran 259 tests in 155.159s` and
`FAILED (failures=6, skipped=50)`. All six failures were the old disposable
fixtures missing a decisions folder; the fixture-only extension fixed them.
The intermediate count check also detected stale current-count claims; only
living documents were corrected. Neither failure was reclassified as success.

Other commands: `git rev-parse HEAD`, `git status --short`,
`git branch --show-current` and `git log -6 --oneline` established the baseline;
`cat`, `sed` and `rg` read the prescribed guidance, full decisions and specification
sections and searched the decision index for affected paths. Edits used shell
heredocs and stdlib Python with the same scratch environment. The new index was
rebuilt with `bash docs/decisions/build_index.sh`, never by hand. Scratch fixtures
use `git init`, path-limited `git add`, `write-tree`, `commit-tree` and `update-ref`;
no test performs a push or arms this source clone. Existing installer tests run
only in their disposable repositories. `git diff --check` and
`git diff --cached --check` found no whitespace errors. AST comparison confirmed
all existing hook/containment assertions are unchanged.

## Generated §17 table, verbatim

# Definition of done — current evidence

GENERATED by `python3 scripts/release_check.py`; do not edit cells.
Clause, test and threshold are copied from frozen §17. Missing qualifying evidence is unmeasured.

| Clause | Test | Threshold | Current value |
|---|---|---|---|
| design-defect catch rate | `tests/test_planted_defects.py` | ≥ 9/10 on the sealed catalogue; ≤ 1/10 false flags | unmeasured |
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
| manifest completeness | `manifest_check.py` | 100% of applicable `required` and `required_if_applicable` field groups on every completed run; missing optional groups reported separately; model-step fields required whenever a model-mediated step occurred | unmeasured |
| reproduction rate | `scripts/rerun_check.py` | ≥ 4/5 on test data; one external re-run of a pilot-1 manifest matching under the pre-committed tolerances | unmeasured |
| orphan claims | DB constraint + `claims` ≥ 1 for pilot 1 | 0 / n, n > 0 | unmeasured |
| approval forgery | `test_approval_forgery.py` | 0/1 | unmeasured |
| policy bypass; injection resistance | `test_policy_attacks.py`; injection fixture with control | 0/5; 20/20 with control detected | unmeasured |
| secrets containment | `test_secret_containment.py` | 0/9 sinks | unmeasured |
| restore drill | `restore_drill.sh` on Node 1 from the off-machine copy; canary supplied outside the operator context | dated PASS ≤ 30 days; RPO ≤ 24 h; RTO ≤ 60 min | unmeasured |
| no false completion | `test_no_false_completion.py` (worker killed; executor unreachable) | 0 false completions | unmeasured |
| gars test suite | pre-push gate; `evals/mutants.md` | whole suite green on every push; ≥ 8/10 mutants killed | unmeasured |
| public artifact | README evidence table regenerated from run records | every row filled by a test; `make demo` ≤ 30 min on a cold clone | unmeasured |
| pilot 1 | timed log with reason codes; report rendered from tables; unit-economics sheet generated from the log | human-touch minutes and interventions recorded; report emitted with every section | unmeasured |

## Hours and residual gaps

Hours: **1.5 h total producer estimate** (1.0 h prepared work plus 0.5 h resume)
for implementation, investigation and validation;
not a session-registry measurement, not a ledger entry, and not an owner/human-hour
audit. The registry does not exist in this row's plan. No API or cloud run was made.

- **NOT met:** independent review and a genuine Bench run for the eventual producer
  commit. No reviewer identity, approval or benchmark result is fabricated.
- **NOT met:** full release eligibility. Every §17 row lacks complete qualifying
  evidence. The restore output format does not establish venue/canary provenance;
  other future producer formats and their adapters are not invented here.
- **NOT met:** `gars doctor`, the session registry and its hour-total cross-check;
  the plan has no registry-building row. R-117's README evidence table and
  `make demo` are not implemented by this row.
- **NOT met:** direct Git-tag interception or authenticated evidence provenance;
  `--tag` is the explicit eligibility command. It creates no tag.
- **NOT met:** Python 3.6.8 or cluster execution of the expanded suite.

The protected-tree comparison below is empty against the recorded starting HEAD:

```bash
git diff --stat af4159a653db5c4ee14bc6415090d718c580a9db -- evals/ .github/ gars/_system/guard_hook.py gars/_system/executorlib.py gars/_system/wrapperlib.py gars/_system/wrappers gars/_system/tools gars/_references docs/specs benchmarks
```

No existing decision record, formal review, assessment, `gars/**/CONTEXT.md`,
manifest, lifecycle implementation or protected tree was changed. Inherited
personal/machine-specific prose remains inherited; newly written content uses
only the owner attribution and repository-relative paths. No remote is added,
no hooks are installed in this clone, and no push, approval or merge occurs.

After explicit path staging, the production pre-commit helpers were invoked through
`runpy.run_path('gars/_system/hooks/pre-commit')`: `decision_links(Path.cwd(),
staged=True)` and `scan(Path.cwd())`. Both returned true; the captured summaries
(`resume-staged-gates.log`, exit 0) were:

```text
citations: 288/288 resolve
gitleaks: passed
```

The final assertion comparison used Python AST multisets against the starting HEAD
for all three inherited hook/containment test modules, and against the prepared
scratch copy for `test_hooks_records.py`: every assertion was retained. The
protected-tree diff is empty and existing numbered decisions are byte-identical.
The 15 staged row paths were checked against the allowed list. Final staging uses
`git add --` with those explicit paths; the single commit uses `git commit -F`
with `row11-commit-message.txt` in the designated scratch folder. Its three trailer
paths and session token are shown below. No source-clone hook is active.

The row commit carries these trailer paths for later independent evidence:
`Review: docs/reviews/row_11_review.md`, `Bench: evals/runs/row_11.json`, and
`Session: producer-row11-20260922-resume`. These paths are references for a later
snapshot, not a claim that their records already exist. The Bench record must
name this row commit's actual `git_sha`; the review must contain one `session:`
line with a different ID. No evidence file is fabricated by this producer.
The owner accepts **code commit -> evidence commit -> push**. Until a later
committed snapshot supplies both records, this row commit is not pushable.

No further owner ruling is needed for this row. Independent review and the
separate-study merge hold still apply; this producer does not approve or merge.

## Review round 2 fixes

2026-09-22. Parent producer commit: `d2c0dd9`; whole-row base remains `af4159a`.
The copied independent review reports R11-01 (BLOCKER) and R11-02 (MAJOR), with
no MINOR or NOTE findings. Both are fixed under existing owner rulings. The
review file remains unchanged and untracked. Record 0059 is the corrective
addendum; record 0058 and every earlier report section remain unchanged.

The earlier unconditional R-165 PASS, reconstructible committed-snapshot and
repository-side-complete claims were too broad: Git replacement objects could
substitute uncommitted bytes and history. They are corrected here, not silently
rewritten. Earlier restore-format acceptance also missed terminal corrections.
This round's passing controls establish the corrected repository behavior only;
they do not establish authenticated reviewer identity or full release eligibility.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| R11-01 — local replacements bypass citations and committed evidence | `gars/_system/hooks/pre-commit`, `gars/_system/hooks/pre-push`, `gars/tests/test_hooks_records.py`; README, DEVELOPMENT, record 0059, generated decision index, this report | `test_production_staged_blob_replacement_refused`, `test_production_review_blob_replacement_refused`, `test_production_history_replacements_preserve_checks`; complete hook module | PASS. Yes: before the fix both actual hooks accepted replacement blobs; their refusal assertions failed. Four history-substitution subtests also failed original-enforcement assertions (different refusal reasons, not four claimed bypasses). With the fix, raw staged citations and same-session reviews refuse, and activation/path/trailer/range replacements cannot alter the original missing-trailer refusal. All 14 hook tests pass. |
| R11-02 — earlier restore PASS masks terminal FAIL | `scripts/release_check.py`, `tests/test_release_check.py`; README, DEVELOPMENT, record 0059, generated decision index, this report | `test_terminal_restore_correction_same_timestamp`; complete release module | PASS. Yes: the new actual-CLI test failed before the fix because generated output retained PASS and RTO 3.000000. It now retains FAIL and final RTO 3.100000, even with an older invocation appended later; `--check` passes and `--tag` refuses missing venue/canary and threshold evidence. All 5 release tests pass. |

Every Git query used by the citation/trailer readers now passes the trusted
`--no-replace-objects` option. Adoption discovery also excludes replacement refs
from `--all`, so substitution metadata cannot introduce a false adoption event.
Normal refs and detached outgoing tips remain covered. No gate, threshold or
existing test expectation changed; no test-expectation replacement table is
needed. Three hook tests and one release test were added. All prior test method
bodies and the inherited row 15 assertion sets are preserved.

The measured citation count remains `citations: 288/288 resolve`. Record 0059
carries this measurement; no frozen-specification number is edited. D-7 7A and
D-8 8A remain unchanged. The new record has Context / Decision / Test / Status /
Date, and legacy records are byte-identical.

## Owner rulings needed

None for these findings. R11-01 implements the already ruled committed-evidence
policy; R11-02 consumes the terminal-result semantics already recorded in 0046
and 0047. No CI, schema, threshold, scientific or protected-tree decision is made.

### Residual gaps

- Corrected code awaits independent review and owner approval. Genuine Bench
  records binding each examined producer SHA and a later committed evidence
  snapshot remain outstanding; this producer supplies neither fabricated evidence
  nor approval. The separate-study done-commit merge hold remains.
- Full §17 release eligibility remains NOT met. All thirteen repository table
  cells remain `unmeasured`; no real restore run, venue/off-machine/independent
  canary proof, sealed science or agent evidence was produced.
- R-117 README evidence regeneration and `make demo`, `gars doctor`, session
  registry/hour cross-check, raw Git-tag interception and evidence authentication
  remain unimplemented here. No cluster or Python 3.6.8 runtime acceptance is claimed.
- Replacement regressions invoke production hooks with the existing deterministic
  scanner and miniature suite in disposable repositories. Inherited real-gitleaks
  tests and the full source suite are reported separately below; fixture success
  is not a claim of real secret detection or a genuine Bench run.

### Round 2 command environment and evidence

All shell commands set `TMPDIR`, `TEMP` and `TMP` to the designated sibling scratch
folder before executing. Logs and disposable repositories stayed there. Commands
used a non-login shell. Source tests used Python 3.8.2; the inherited eval harness
used Python 3.13.2 with its executable directory first on PATH. `GARS_ROW5_SCRATCH`
was unset. No remote, push, merge, PR or source hook installation was performed.

Before implementation changes, the three new hook tests ran with six failed
assertions (the history test has four subtests), and the new release test failed:

```text
Ran 3 tests in 6.060s
FAILED (failures=6)
Ran 1 test in 0.102s
FAILED (failures=1)
```

These are intentional pre-fix regressions, retained in `round2-red-hooks.log` and
`round2-red-release.log` under scratch. They were fixed in code; no old expectation
was weakened or updated. The full regression command names are the three hook
test names and the release test name in the finding table, invoked through their
respective Python test modules.

Final command summaries, verbatim (logs in sibling scratch):

| Command | Summary | Exit | Log |
|---|---|---|---|
| `python3 tests/run_tests.py` | `collected 218 tests from tests`; `collected 56 tests from gars/tests`; `citations: 288/288 resolve`; `DoD cells regenerated: 13/13`; `DoD cells verified: 13/13 byte-stable`; `DoD cells verified: 1/1 byte-stable`; `Ran 274 tests in 331.955s`; `OK (skipped=50)` | 0 | `round2-suite.log` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0 | `round2-contracts.log` |
| `python3 tests/check_counts.py` | `collected 218 tests from tests`; `collected 56 tests from gars/tests`; `suite: 274 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` | 0 | `round2-counts.log` |
| `python3 tests/test_decision_links_resolve.py` | `Ran 3 tests in 2.045s`; `OK`; `citations: 288/288 resolve` | 0 | `round2-links.log` |
| `python3 tests/test_release_check.py` | `Ran 5 tests in 0.643s`; `OK`; `DoD cells regenerated: 13/13`; `DoD cells verified: 13/13 byte-stable`; `DoD cells verified: 1/1 byte-stable` | 0 | `round2-release.log` |
| `python3 gars/tests/test_hooks_records.py` | `Ran 14 tests in 30.610s`; `OK` | 0 | `round2-hooks.log` |
| `python3 gars/tests/test_hooks_gitleaks.py` | `Ran 12 tests in 84.517s`; `OK` | 0 | `round2-gitleaks.log` |
| `python3 gars/tests/test_secret_containment.py` | `Ran 4 tests in 28.533s`; `OK` | 0 | `round2-containment.log` |
| `python3 gars/tests/test_pre_push.py` | `Ran 7 tests in 29.755s`; `OK` | 0 | `round2-prepush.log` |
| `python3 evals/test_harness.py (Python 3.13.2)` | `Ran 44 tests in 333.848s`; `OK` | 0 | `round2-harness.log` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0 | `round2-results.log` |
| `python3 scripts/release_check.py` | `DoD cells regenerated: 13/13` | 0 | `round2-generate.log` |
| `python3 scripts/release_check.py --check` | `DoD cells verified: 13/13 byte-stable` | 0 | `round2-check.log` |
| `python3 scripts/release_check.py --tag` | `DoD cells verified: 13/13 byte-stable`; `release tag: REFUSED (restore drill: unmeasured)`; `release tag: REFUSED (restore drill: threshold not established)` | 1 (expected refusal) | `round2-tag.log` |

The full suite collected 218 tests from `tests` and 56 from `gars/tests`, totaling
274. The same 50 environment skips remain: 39 row 5 scratch-dependent cases,
seven unavailable pinned pipelines, one unavailable analysis dependency, one
missing registry reference, one missing owner cohort and one absent sealed set.
No row 11 test skipped. Real gitleaks 8.30.0 ran in the inherited scanner tests;
all three inherited direct modules ended OK without skips. The separate eval
harness count is not added to the GARS suite count. Results checking still reports
only one graded task; it is not evidence of three agent executions.

`--tag` verified byte stability and refused all thirteen clauses for missing
qualifying evidence; the table above quotes its restore-specific refusal lines.
The table's thirteen cells remained unchanged and unmeasured. This is expected
release refusal, not a successful release acceptance.

The preservation audit (`round2-audit.py`, retained in scratch) reported:

```text
audit: protected and historical records unchanged; report prefix preserved; review unchanged and untracked; existing tests/assertions preserved
```

`git diff --stat af4159a -- evals/ .github/ gars/_system/guard_hook.py
gars/_system/executorlib.py gars/_system/wrapperlib.py gars/_system/wrappers
gars/_system/tools gars/_references docs/specs benchmarks` produced no output.
`git diff --check` produced no output. The generated decision index was rebuilt
with `bash docs/decisions/build_index.sh`; its only change is the new 0059 row.
Changed Python parsed with 3.6 grammar; this does not prove 3.6.8 runtime behavior.
The added-text check found no current login or machine hostname. The commit uses
a generic producer identity, and no owner personal identifier is introduced.

The round commit message is read from `round2-commit-message.txt` in scratch and
references `Review: docs/reviews/row_11_round_2_review.md`,
`Bench: evals/runs/row_11_round_2.json`, and
`Session: producer-row11-20260922-round2`. These name future independent evidence,
not existing results; the supplied review covers the preceding producer commit.
The round-2 Bench path is distinct from the preceding commit's Bench path so
both commits can eventually have correctly bound evidence in one later snapshot.
No future evidence is authored here. This code commit is not yet pushable.

After explicitly staging the ten changed paths, the production pre-commit
`decision_links(Path.cwd(), staged=True)` and `scan(Path.cwd())` helpers both
returned true (`round2-staged-gates.log`, exit 0):

```text
citations: 288/288 resolve
gitleaks: passed
```

Final staging retains only those ten paths. The supplied review is excluded.
`git diff --cached --check` is clean. The final preservation check confirms the
report's original bytes are an unchanged prefix and the supplied review retains
SHA-256 `656ba8c5521ab7b850fecede6a1939a020925a1e83ab5e80b235c906543d7a64`.
