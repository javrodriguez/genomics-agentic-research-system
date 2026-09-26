---
date: 2026-09-25
status: standing
kind: decision
touches:
  - evals/bio-faults/
  - gars/_references/prompts/review_faults_science.md
  - tests/test_bio_faults_core.py
  - tests/test_bio_faults_faults.py
  - docs/implementation/row_10_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - the required science prompt path fails the inherited code-only schema enum
  - required public manifest fields contain tokens forbidden by the science sweep
---
# Row 10 science review contracts and stopped construction

## Context

Round 1 starts from public main a77908474f2fc463f481a55f2d0c2ceeee8be660
plus the seed record 0135. Specification sections 7.2, 7.3, 7.5, 7.8, 10,
11.2, 11.3, 14, 17, row 10 of section 18 and section 21 Q3/Q9/Q10 govern
this lane. The gap assessment's Row 10 and D-11 explain the missing measurement
and partial-set threshold conflict. No round-1 review was supplied.

## Decision

**THE LANE'S SPECIFICATION: Glitch under the owner's standing delegation.**
Record 0135's rulings are Glitch's decisions under that delegation; none is
attributed to the owner. R10-5a states:

> The resume is the only path built in round 1.

Resume is the specified phase-B mechanism. Neither it nor a fresh-session
alternative has run here. No model has been run against any case.

The independent parts implemented here are the science vocabulary, row 9
imports under private aliases with safe canonical bare-name bindings, the
schema document with only the permitted differences, the pre-normalising
any-of oracle, and the two-phase prompt. The existing row 9 implementation,
all system gates, benchmarks and all base decision records remain unchanged.
The prompt is protected; this producer neither writes nor claims record 0137.
Records 0138 and 0139 remain reserved and unwritten.

Two incompatible contracts stop dependent implementation under the supplied
lane's explicit escalation rule. The inherited reviewer.prompt_path enum
admits only the code prompt, while the required science record names the
science prompt. The allowed schema differences do not include this enum.
Separately, the required public manifest's harness_commit key and prompt path
contain the forbidden substrings harness and fault. These are wholly new
manifest bytes, so row 9 item 15's unchanged-line exception cannot apply.
The change report records numbered options; no exception is silently chosen.
The builder, gate integration, base/case handoff, record adapter, launcher,
scorer and dependent release reader are not delivered as operational tools.

### Threat model

The supplied threat model is the acceptance contract, not a claim that this
partial implementation already establishes all its protections.

Covered by the required design: a measured reviewer, a model session in a kit,
must not learn class, plant/clean kind or the answer from folder names, filenames,
file stat, BRIEF.md or project bytes the plant did not add. Narrative must remain
absent until phase A ends. Model text must never supply the envelope. A reviewer
whose uid equals the producing account's uid on the same host must not be scored.
A vague finding must never count as caught: class, file, line interval and
severity must match an entry of match_any. The oracle tests establish the last
primitive; this round does not establish construction or launch protections.

Reads beyond the kit are enforced by the deployment sandbox. The harness must
bind the settings bytes used and run row 9's static audit. Its named residuals
in 0072 items 20–23 and 0125 apply unchanged, with 0127 and 0128's subsequent
data and session-placement rulings. Indirection, unparsed program text,
failed directory changes and audit-time symlink state remain sandbox concerns;
an ambiguous conditional read remains visible without becoming a hit. Import
identity and a stub stream demonstrate reuse, not sandbox efficacy.

Covered by the required reporting design: the harness reports only what it
measured. Invalid records, uncomputable zero denominators, a tampered key,
mixed prompts or models and the partial set remain visible, never silently
dropped. Invalid records count in all denominators, never caught or clean.
No scoring implementation or measured reporting is claimed in this round.

Not covered: inference from case style; sealer, auditor and producer all being
Codex contexts while the reviewer is Claude; independent_context seals being
development evidence only; the thin one-plant-per-class sample, with per-class
rates 0/1 or 1/1 (0/2 through 2/2 across the repeat); four sealed outcomes
checkable only by hash, so a stranger recomputes four of eight outcomes from
the repository; the five unplanted classes; R-093's code half, where
launch_role() still returns producer. These are the specified eventual set's
limitations, not a claim that an eight-case set exists in this commit.

## What this does not close

The two contract rulings, the rest of the implementation and its acceptance
remain open. No producer plant or clean case is published before construction
can satisfy its contract. The two required statistical rationales are therefore
not supplied. The sealer interface is not published as complete without its
base trees, fixed ids/seeds, layout and working gate integration.

Row 10 exit remains NOT met: sealed slots, honesty audit, deployment and a
scored first run and repeat remain later work. Section 17 cannot be met by the
partial set. No public README evidence cell is changed. Protected approval,
independent review, native Python 3.6, mode A and merge-result CI remain outside
this producer evidence. The change report states exact verification outcomes.

## Test

`tests/test_bio_faults_core.py`: vocabulary, schema drift, same-object imports,
a stub-stream audit, both import orders in one interpreter, oracle any-of grid,
pre-normalisation drift, repo-prefix rejection, shared alarms/ratios, prompt
constraints, and concrete witnesses for both stopped contracts.
`tests/test_bio_faults_faults.py`: seven isolated mutations, each with an unchanged
green control and a named red witness. These do not substitute for the remaining
lane acceptance or red-on-fault requirements. Full command summaries and direct
module wall times are recorded in the change report.

## Status

Standing partial implementation account, pending the two rulings and independent
review. This is not an approval, seal, measured run or row-exit claim.

## Date

2026-09-25

## Addendum — 2026-09-25, rulings round R1

The following are glitch-09's rulings, **Glitch under the owner's standing
delegation of 23 Sep 2026**, never the owner's words. They settle both questions
recorded above. R1 chooses option (a): the science schema additionally pins
`envelope.reviewer.prompt_path` to its science path. The adapter first checks
record == manifest == that path; only then a pure function projects the path
in copies of the record and manifest. It changes no hash or other field:
**row 9's validator is reused by projecting the prompt path; the science-path equality is checked first and separately**.
R2 chooses option (a): only the whole top-level `harness_commit` key and the
whole science path string under `prompt_path` in the public manifest are exempt
from the substring sweep. They carry no per-case information. A substring,
another key or value, and the same bytes anywhere in a case remain refused.
The scope-of-stop ruling applies only to R1/R2; surrounding work is built here.

Three deterministic bases, the complete sealer interface, four public fixtures,
the gate-driven builder, science adapter, two-phase launcher, scorer, release
reader and acceptance/mutation tests now accompany the initial contracts.
P01 and P02 carry the two authorized producer classes; C01 and C02 are clean.
No other plant, clean case, seal, protected approval or measurement is supplied.
The fixture rationales live only in the implementation change report.

Stage 01 and catalogue integrity run through their real check entry point;
wrapper collectors run with scratch execution scaffolds. The group/replicate
tokens come from wrapperlib and are checked against the matrix and normalized
result identifiers. Stage 03 now runs real verify: the supplied historical
approval hash, timestamp and expiry are preserved; actor/path store bindings
are mapped to the scratch process and the clock is one second after approval.
Its real output, plan and executor-evidence checks run with synthetic content
execution sidecars, as do the wrapper collectors. No real job, approval command,
production approval or live scheduler is represented by these scaffolds.
Row 7's evidence emitter and renderer process the snapshot and manifest.
All scaffold mutations stay in scratch; none is copied into a case.

Resume is the only phase-B mechanism implemented. Only the runtime stub has
exercised it. No model has run against any case, and no fresh-session alternative
is implemented. A's launch-owned session and B's stream init session are both
recorded; B's equality boolean is code-stamped, and each phase's audit uses its
own session. Session disagreement is INVALID. Model text cannot supply an
envelope. First-run-at-sha evidence therefore remains available to the later
first measured run; this branch contains no measured run file.

The threat model stated above remains the acceptance contract. Construction
now sweeps all public bytes and names, fixes modes/mtimes, and keeps answers
private. Launch identity, phase ordering, static audit, path projection and
strict field matching have stub/contract evidence. INVALID cases remain in all
denominators; zero denominators, tampered inputs, prompt/model differences,
first-run values and partial-set status remain visible. Publication uses row 9's
masking object. The release science clause is always development evidence and
cannot satisfy the full threshold. Code-half release text is pinned unchanged.

The named residuals also remain unchanged: deployment enforces reads beyond the
kit; 0072 items 20–23 and 0125 apply with the later session-placement rules.
Case-style inference, common Codex context family for the non-reviewer roles,
independent-context seals' development-only status, thin per-class samples,
four eventual private hash-only outcomes, five unplanted classes and R-093's
code half remain outside this evidence. Neither sandbox efficacy nor independent
statistical honesty is established by producer tests.

Tests include the two exact R1 failures, exact R2 exemptions and a widened
exemption mutation, schema/import/oracle drift, both import orders in one
interpreter, every gate refusal, construction bytes/stats, two-phase stubs,
invalid denominators, masking, release rendering and repeat observations.
Twenty-five isolated red-on-fault controls require a green unchanged control
first. The dated change-report addendum carries exact verification summaries.
Mode A, native Python 3.6, deployment, seals and measurement remain unverified.
Record 0135 and all earlier decision bytes are unchanged. Records 0137, 0138
and 0139 are reserved and unwritten; no approval or row exit is claimed.

Historical-clock clarification for this addendum: verify evaluates approval expiry
at the manifest's recorded execution finish, rather than one second after approval.
Thus an approval expired before collection is refused. The hash, timestamp and
expiry remain supplied data; the real verifier evaluates them.

Final implementation checks also reject residual dot prefixes before delegating
to row 9's oracle, so row 9 cannot strip a second prefix and expose `repo/`.
Missing or unreadable gate inputs are recorded as named refusals, including a
missing declared output, with a private key retained for the refused build.

Invocation discipline failed this round: the initial workspace check, a hook
location inspection and the manual fixture-hook invocation each used a literal
rooted null-device redirect, contrary to the lane's command-path rule. Passing
functional tests does not repair those three violations. The fixture hook also
refused because gitleaks was absent; no secret-scan pass is claimed. These facts
are separate from implementation acceptance and are recorded in the change report.

## Addendum — 2026-09-25, review round R2

The following rulings are **Glitch under the owner's standing delegation of
23 Sep 2026**, never the owner's words. R1 and R2 remain settled as option (a):
**row 9's validator is reused by projecting the prompt path; the science-path equality is checked first and separately**.
The projection changes only the prompt path after the three-way equality check;
the science hash comparison remains unchanged. The only public-manifest sweep
exceptions remain the whole `harness_commit` key and the whole science prompt
path value under `prompt_path`. No case bytes receive either exception.
The scope-of-stop ruling applied only to those two questions; the complete
surrounding harness from the preceding addendum remains implemented.

Glitch's lane ruling on review F5 supersedes this record's earlier sentence
"Session disagreement is INVALID": phase-B disagreement is recorded, never an
INVALID reason. The launcher still stamps both session ids and their equality,
and audits B using B's own stream-init id. The scorer reports
`resume id differs: n/total`, over the records read, including retained attempts.
The named test `ScoreTests.test_resume_id_differs_count` requires the disagreement
to remain valid and the count to print; separate mutations drop the count and
restore the rejected invalidation. Resume remains the only implementation;
CP5.6 on the deployment host settles whether it continues the actual session.
No model was run against any case.

Glitch's lane ruling on F1 replaces the earlier four-feature permutation bases
with 240 negative-binomial features, dispersion 0.015, a skewed lognormal
baseline, differing library exposures and 24 seeded effects of absolute log2
size 1 to 3 in both directions. The approved method is median-of-ratios
normalisation, log2(normalised count + 1), a two-sided pooled Student t-test
with df = 4, and BH across every tested feature at alpha 0.05. The standard
library implementation evaluates the regularised incomplete beta function.
Tests compare it with reference tails and an independent df=4 integral, then
recompute normalisation, statistics, p-values, BH and report counts. Reports
state directions and n = 3 per group limits, with association rather than
causation. QC and configuration text are specific to the assay. The three
fixed seeds are listed in INTERFACE.md and the private case definitions;
neither those seeds nor base ids occur in built reviewer-visible bytes.
P01 and P02 were re-derived against these bases; the provenance-only diffs
remain byte-identical. Their statistical rationales are in the R2 change
report only. Exactly P01, P02, C01 and C02 exist; reserved slots stay empty.

Review F2 binds the harness commit to the source repository instead of the
caller's working directory, with an outside-cwd regression. F3 now refuses
stage-01 design flags, including catalogue covariate_imbalance DEGRADE output.
F4 removes the seed metadata and tests every built case byte. F6's renamed
module mutation supplies a live shim under the prohibited bare name and must
reach `FAIL: test_one_process_both_import_orders`, without an import failure.

F7's direct stub-stream comparison reduces to object-identity drift test (a):
both launchers import the same blindness function. The distinct phase call
site is exercised by `LaunchTests.test_phase_b_session_audit` and both-phase
hit tests; a mutation using A's id for B fails the named call-site test.
For F8, a refused build retains the private key and gate log but publishes no
manifest. For F9, a phase-A-created report directory records a named invalid
output with B unstarted and a nonzero phase exit; the launcher continues through
the remaining ids. It adds no validity rule or schema field.

For F10, RNA wrappers expose no membership gate to import. The shared adapter
uses the imported wrapperlib token function; the new
`BuildTests.test_group_rep_collector_drift` drives that adapter and the actual
ATAC collector over identical intact and missing-token inputs. This tests the
membership comparison against production behavior without editing a wrapper.
F11: this addendum also touches `tests/test_bio_faults_pipeline.py`; the frozen
frontmatter is intentionally not rewritten. R2 uses the required report heading.
F12 requires no identity change; repository configuration remains untouched.

The threat model and its named residuals above remain in force: deployment
bounds reads, the harness binds settings and runs row 9's audit, and 0072 items
20–23 and 0125 apply unchanged. Style-based guesses, common Codex context family,
independent-context seals as development evidence only, thin per-class samples,
four eventual hash-only sealed outcomes, five unplanted classes and R-093's code
half remain outside these checks. Invalid records remain in denominators;
science remains a partial set and never meets the full threshold. The R2 report
records executed checks and limitations. Protected approval belongs to later
record 0137; neither it nor 0138 or 0139 is written or claimed here.

R2 invocation limitation: an initial outside-cwd regression probe inherited
relative temporary-directory settings and fell back to the system temporary
folder. This breached scratch containment. Final verification uses a
runtime-resolved scratch twin; it does not erase the initial breach. The
fixture hook also refused because gitleaks is absent. Neither complete
invocation compliance nor a secret-scan pass is claimed.

## Addendum — 2026-09-25, review round S1

The continuation guidance and the earlier scope and lane rulings are **Glitch
under the owner's standing delegation of 23 Sep 2026**, never the owner's
words. For review R2 F1 this implements option (ii), the delegated preference:
count-matrix analysis inputs, no raw reads, per-library analysed read totals
and checksums. None of the five in-scope classes requires reads. The totals
are explicitly the sum over supplied features, not invented total sequencing
depths. Each checksum binds a per-library feature-count export; the aggregate
matrix must equal those exports. RNA and ATAC read-level QC is unavailable
from these inputs. The QC disposition is DEGRADE, with the limitation beside
the rendered claim; no mapping fraction, inferred strandedness, FRiP, TSS
value or fragment-periodicity observation is invented. All samples remain,
and the original pre-specified pooled Student t/BH analysis is retained.

Stage 01 still runs its real check against the unchanged design and config.
Its scratch registration view projects the count registry's sample ids to the
required sample/lane/FASTQ header, with both FASTQ columns empty. It asserts no
raw input. The supplied count artifacts instead run through the imported
integrity.check_many entry point, with checksum, per-library total and matrix
column consistency checks in catalogue_integrity. No gate is omitted, no
system file changes, and the scratch registration is never copied into a
case. Missing, empty or inconsistent count inputs refuse. Raw-read-specific
catalogue checks are inapplicable without raw reads; no fabricated FASTQ is
introduced merely to satisfy a gate. Wrapper and approval execution scaffolds
remain content-check scaffolds, not evidence of a real pipeline run.

F2 replaces floating sums in the analysis with math.fsum and serializes all
numeric CSV values at twelve significant digits. All base files use explicit
UTF-8 and LF. Integer counts and integer event counts still use integer sum.
The base fingerprint is SHA-256 over the compact ASCII JSON encoding of the
sorted (relative file path, file SHA-256) list. The pinned hashes are:

| Base | SHA-256 |
|---|---|
| rna-a | 42418064a7d2ede5a797cbb6792e48989c7e79266c83f0a2c1aeedf39d579f4e |
| rna-b | 890c7988af399fdf168bd916ed00f134e2fe901a65060ba8466426b9566eb9f7 |
| atac-a | 52a704ff3e389c8614756f7d80de46dbaa3b90406284d2f6bf2a257143eae9fb |

Python 3.13.5 produced these hashes. python3 and python3.13 both identify that
same version; no distinct Python 3.6–3.12 interpreter is available here.
Cross-version and cross-platform equality therefore remains unverified, not
inferred from the grammar parse. The named fingerprint test pins these bytes
for the lane's other interpreters. Separate mutations restoring built-in
floating sum and removing fixed formatting each fail that named test.

F3 narrows the resume observation to records with a phase-B stream-init id:
not-started, missing-init and absent ids contribute to neither its numerator
nor denominator. Retained attempts with a phase-B init still each contribute.
The printed line is resume id differs: n/d, with 0/0 uncomputable when none
started. A disagreement remains recorded rather than INVALID, as the earlier
lane ruling requires. The test includes an unstarted B and missing-init, and a
mutation counting unstarted B goes red. CP5.6 still settles actual resume
behavior on the deployment host; only stubs ran here.

F4 assigns the ATAC consensus features seeded widths of 150–900 bases, gaps
of 500–25000 bases, and three chromosomes. Counts, effects and inference retain
the same seeded draws; the new coordinate stream is separate. A coordinate
regression and a mutation restoring adjacent single-chromosome tiles cover it.
P01/P02's provenance-only patches were re-derived on these bases; they remain
byte-identical. Their plan match intervals move to the method lines after the
new input declaration. Statistical rationales are only in the S1 change report.

F5 needs no repository fix: the prior round's disclosed scratch-containment
breach remains a process fact. This round resolves scratch settings before
running children, including outside-cwd regressions; mode C unsets TMPDIR only.
Tests added or extended in tests/test_bio_faults_pipeline.py and mutation
entries in tests/test_bio_faults_faults.py cover F1–F4. The change report records
all required command summaries and direct module wall times.

The threat model and named residuals above remain unchanged. R1/R2 projection
and exact manifest exemptions remain unchanged; row 9's validator is reused by
projecting the prompt path; the science-path equality is checked first and
separately. No measured reviewer, prompt tuning, seal, independent honesty
audit, protected approval or row exit is claimed. 0135 remains unchanged;
0137, 0138 and 0139 are not written. Sealed slots, measurement, repeat, deployment
sandbox and actual resume remain later work; the partial set never meets the
full science threshold.

## Addendum — 2026-09-25, review round T1

The continuation-T ruling is glitch-09's ruling as coordinator, **Glitch under
 the owner's standing delegation of 23 Sep 2026**, never the owner's words.
This round is a continuation beyond the lane's stop rule of at most one continuation, ruled by glitch-09 to protect the clean half of the measurement.
It answers review S1's NOTE F2 and nothing else: every base's qc.md now carries
one QC disposition, DEGRADE, matching the rendered report. The n = 3 per group
point is a limitation line. No data, analysis, claim, plan, approval, or
provenance changes. P01, P02, C01 and C02 keep their flaws and rationales as
recorded in the S1 change report; neither fixture patch needs a line adjustment.

The existing S1 fingerprints passed on Linux with Python 3.13.5 before editing
(Ran 1 test in 0.085s; OK). S1 NOTE F1 therefore requires no numerical change.
Last-ulp libm sensitivity on other platforms remains a stated residual. Comparing
all generated files against the pre-T1 generator found only qc.md changed in
each base, exactly the replacement of the second disposition's label by
Limitation. The sorted (relative file path, file SHA-256) compact-JSON tree
hashes are re-pinned in test_base_fingerprints:

| Base | SHA-256 |
|---|---|
| rna-a | c6f3092d4287fe25910fab7006297d8c926e92a087771442a4a9b3fdf8f5c4ea |
| rna-b | 9aa55910efa9a81f5f3c38d7bc044c22edffc781127f32cec852deb55e842c0d |
| atac-a | 91a844b99329c176a7c206bf311a7a81d12dcca0eb90f8e77ae5f71b5a7d4a12 |

Tests: tests/test_bio_faults_pipeline.py adds
BuildTests.test_single_qc_disposition_matches_report, building all four cases
and checking exactly one DEGRADE line, the retained n = 3 limitation, and
equality with the report's QC summary. tests/test_bio_faults_faults.py adds
second QC disposition restored, reverting the label in a disposable copy
and requiring that named test to fail after its unchanged control passes.
Full command summaries and the mutation outcome are in the T1 change report.
The decision index is regenerated; all prior record bytes are preserved.

Invocation limitation: the first command mistakenly used a rooted null-device
redirect. This breached the lane's command-path rule. Subsequent relative
commands and passing tests cannot undo it; complete invocation compliance is
not claimed. Scratch settings are runtime-resolved before child processes.

The existing threat model, named residuals, schema projection and sweep rules
remain unchanged. No model runs against a case, no prompt tuning occurs, and
no protected approval, seal, measured run, repeat or row exit is claimed.
0135 stays unchanged and 0137–0139 remain unwritten. The partial set cannot
meet the full science threshold; deployment rehearsal remains later work.

## Addendum — 2026-09-25, rulings round U1

U-1 and U-2 are glitch-09's rulings, **Glitch under the owner's standing
delegation of 23 Sep 2026**, never the owner's words. This round is a further
continuation beyond the lane's stop rule, ruled by glitch-09. The lane reports
that deployment rehearsal drove phase-B resume with equal session ids and
otherwise VALID records; this producer does not claim to have run that rehearsal.

Pre-registration, before any sealed case exists: a phase ending on the system
event with subtype `model_refusal_no_fallback` before its first tool call is
recorded and never scored. That case receives EXACTLY ONE retry as a new
attempt, with identical prompt, case, settings and command bytes, nothing
reworded. A refusal after a tool call remains ordinary INVALID and final.
A second refusal, or any other retry failure, is INVALID and final, including
a usage limit on that retry. Every other INVALID remains final under R10-1;
the existing non-safeguard usage-limit continuation rule remains unchanged.
The code stamps `safeguard_refusal`; scoring excludes flagged attempts from
rates, selects the retry for the case, retains both attempts, and reports
per-case refusal/retry validity and safeguard refusals over sessions launched.
The single-retry budget persists across invocations, including `--only`.

U-2 requires supplied data classification, reference release in the execution
manifest, reproducible commands from the counts, cost or a justified N/A,
and an ATAC limitation naming the unverifiable consensus-peak and blacklist
choices. Counts, inference and the two producer flaws remain unchanged.
Base hashes will be re-pinned; fixture patches need changes only if their
source lines move. The prompt stays unchanged and no model runs here.

A newly found boundary stops only U-2's final rendering acceptance: the imported
row-7 render_report.render hard-codes UNKNOWN for data/classification, commands,
cost and genome/model methods fields, ignoring supplied values. Changing that
function is prohibited by the head's gars/_system/ boundary. No renderer copy,
post-render substitution or monkeypatch will hide this conflict. The change
report records options for that part; the remaining U-1 and U-2 work proceeds.

U-1 implementation retains both attempts, their streams and their separate kits.
The retry preserves both phase argv lists, including the launch-owned session id;
its fresh working directory differs, leaving the first kit untouched. A binding
hash covers all source case files, prompt/settings bytes, both argv lists and tool
version. The launch checks it before a retry; scoring checks the retained binding
and history budget. `next_attempt` remains imported and handles non-safeguard
attempts unchanged. The added schema properties are optional for historical
records, code-stamped on new launches and removed only in the row-9 adapter view.
Schema drift tests name both additions. A flagged attempt is unscored even if
its review text has a valid finding shape; a twice-refused case remains INVALID
in its original denominator. Safeguard-session totals count launched attempts,
each intended as one two-phase session; per-phase streams remain available.

Tests in tests/test_bio_faults_pipeline.py cover A/B refusal, ordered tool-call
rejection, unchanged retry bytes/argv, automatic and later --only retry, changed
input refusal, finality after refusal or usage limit, history tampering, rates
and the count lines. Mutation controls require a green control before a second
retry, after-tool exemption, changed retry, or scored refused attempt turns red.
Actual Claude behavior for reusing a session argument in a fresh kit remains
unverified here; only stubs run, with no prompt change or model measurement.

U-2 supplies count-only reproduction code and commands, public classification,
reference release in the execution manifest and config, and a justified N/A cost.
Both numerical CSVs reproduce byte-identically. ATAC limitations name the
consensus-peak union and blacklist exclusion as unverifiable from supplied files.
The inherited renderer still hard-codes UNKNOWN: complete clean-render acceptance
and its requested mutation proof remain stopped, not passed. The independent
input/reproduction regression has a missing-classification mutation witness.
The report records the required ruling options without changing protected code.

The base fingerprints are re-pinned in test_base_fingerprints:

| Base | SHA-256 |
|---|---|
| atac-a | 4c04cfd75e2707adc365364bc320b15479b717246ba04918b1eb0cb123aa4f6f |
| rna-a | 1426c71a803af9c131f659e932242c290e02a76be6f015158082a53953d6dff5 |
| rna-b | 8d7711776ff6f068361e11a595de4a4ed3929a96370ae8b3e9761cb3732f0500 |

P01 and P02 were re-derived with difflib on these bases. Their provenance-only
patches remain identical, and plan/provenance match lines did not move. Their
flaws and the S1 statistical rationales remain unchanged. C01 and C02 have the
same counts and inference; their rendered completeness is explicitly unresolved.
No fixture or prompt byte changes, seal, protected approval or reserved record
is supplied. The existing threat model, row-9 imports, R1 path projection,
R2 exact sweep exemptions and deployment-audit residuals remain unchanged.
This round neither certifies statistical honesty nor claims row 10's exit.

## Addendum — 2026-09-26, review round V1

Round V1 is a further continuation beyond the lane's stop rule, ruled by
glitch-09 under the owner's standing delegation of 23 Sep 2026. It answers the
round U1 owner ruling and review U1. None of its rulings are the owner's words.

**Producer.** Round V1 was produced by Claude Opus 5.5 (a headless Claude Code
session), because every Codex route available to the lane was at its usage
limit (glitch-09's ruling under the delegation, 26 Sep 2026). The same-model
cost is stated. The bytes this round adds were written by the same model family
as the measured reviewer: the prompt's scoping passage, the tests, the script
rename and the usage-limit stop. Codex wrote the case analyses in earlier rounds,
and they are unchanged apart from the rename.

**Ruling (c) on the renderer placeholders** is glitch-09's under the delegation.
The science prompt is scoped and the renderer is left alone. The prompt gains one
passage in Phase 2. It names the renderer's literal placeholder `UNKNOWN (owned by ...)`,
the form row 7's `render_report.py` `unknown()` writes. It calls such a placeholder
a GARS process placeholder outside the science review, and it caps a finding
about one at NOTE. The cap covers only text of that literal form, and every other
part of the report stays fully in scope. The reason: this row measures scientific
judgment, not how complete the renderer is. Nothing else in the prompt changed.
The prompt's sha256 moves from cea64d1ce7b7d3719959b533a19e7606b6abfc0327135e6af6c1dd2544d251bf
to c4aebae5fc878c9b0b0401ad22efd47a7163036a67080d53c4cc85da2c9de04c. No model has run
against any case at either sha, so the first measured run stays first-run-at-sha.

The renderer gap is a product defect of row 7's `gars/_system/claims/render_report.py`.
Four sections are hard-coded UNKNOWN: data and classification, genome/model
hashes in methods, the `commands.sh` reproduction line, and cost. The renderer
ignores the values the bases supply for them. It is to be fixed in its own
follow-up, not in this lane. The U-2 bases stay as built.

**Review U1.** F1 (MINOR): a new test,
`BuildTests.test_clean_report_unknown_only_renderer_placeholders`, asserts that
every UNKNOWN line in each built clean report is one of the renderer's four
hard-coded placeholders, each under its own section heading, and nothing else.
The boundary witness in `test_report_inputs_and_reproduction` is kept.
F3: the reviewer-visible `3-results/bio_analysis.py` is now `3-results/analysis.py`.
F4: when a refused attempt also ended on a usage limit, the launcher now stops,
prints the remaining ids, and names the case as awaiting its one retry through
`--only`. It no longer spends the retry on the limit. F2 belongs to the lane. Its
deployment rehearsal checks whether the real client accepts a reused session id
from a new folder. That result has not reached this round, and a later addendum
records it when the lane sends it.

The rename re-pins the base fingerprints in test_base_fingerprints:

| Base | SHA-256 |
|---|---|
| atac-a | bdf4bf80ead09c3c510f8f3f3db060a8e0f8cdc02d33788029c4300c11ca533e |
| rna-a | be88dcba9955867adf823cb58b819b4a19c207b11e4bb533ffa160731e1389f1 |
| rna-b | 5251e84915762f0c3485cd3a84f7f9c255a4cbc70734aa42245ca964c1e5bc89 |

These hashes were measured under Python 3.8.2 on macOS. The previous pins
(Linux) were also green on that interpreter in review U1. P01 and P02 are
provenance-only patches, so they apply unchanged. No fixture byte changed.
Red-on-fault entries: the placeholder scope widened to the claims and limitations;
a cap added on a real report section; the passage removed; `pipeline_commit`
removed from a base; the refusal-on-limit stop removed. Each turns its named test
red after a green control. The threat model, row-9 imports, the R1 path projection,
the R2 exact sweep exemptions and the U-1 retry budget are unchanged. This round
does not claim row 10's exit and does not certify statistical honesty.

## Addendum, 26 Sep 2026 (round W1, review V1)

This round is a further continuation beyond the lane's stop rule, ruled by
glitch-09 under the owner's standing delegation of 23 Sep 2026 (ruling (D)).
These are glitch-09's rulings, not the owner's words.

**Producer.** Round W1 was produced by a headless Claude Opus 5.5 session,
because every Codex route available to the lane was at its usage limit. The
same-model cost: the bytes this round adds (the prompt pin test, its two
red-on-fault entries, and INTERFACE.md's absent-report-value line) were written
by the same model family as the measured reviewer. This round changes no prompt
byte. The case analyses were written by Codex in earlier rounds and are unchanged.

**The stopped first attempt.** A first attempt at this round was stopped when the
Claude Code auto-mode permission classifier denied an edit narrowing the science
prompt's scoping passage (reason given: "Instruction Poisoning"). Nothing was
worked around. The narrowing was dropped by glitch-09's ruling (D), and ruling
(c) stays as round V shipped it.

**W-2 (V1's F1).** `ContractTests.test_prompt_pinned` pins the whole science
prompt, byte for byte, to its bytes at round V's head
`1eb60cf18ab765ffb99491b5e6a0a2b3fc793144`, sha256
c4aebae5fc878c9b0b0401ad22efd47a7163036a67080d53c4cc85da2c9de04c. Any added or
changed text turns it red, including a cap written in other words. Two
red-on-fault entries cover that: a NOTE cap on the cost and limitations sections
worded without "at most a NOTE", and a one-byte change to a heading.

**W-3 (V1's F2).** The change report's new section ends with
`## Owner rulings needed` reading exactly `None.`. Earlier sections are unedited.

**W-4 (V1's F3).** INTERFACE.md now says, outside 0135's verbatim block, that a
plant must not be expressed as an absent report value (a value the renderer
would print as `UNKNOWN (owned by …)`). The flaw must be present in the case's
own data, design, results or narrative text.

**Named residual (V1's F3).** Round V's cap matches the literal
`UNKNOWN (owned by …)` form. `render_report.py` writes that same form for any
missing claim or manifest value, not only for its four hard-coded sections. So
a plant expressed as an absent report value would be uncatchable at
min_severity MINOR. W-4 forbids such plants to the sealer, and the lane's
sealed-case audit checks each sealed plant for it explicitly.

V1's F4 (the reused session id on retry) and F5 (the fault module's wall time on
macOS) are the lane's. Nothing else changes: the threat model, the row 9 imports,
the R1 projection, the R2 exemptions, the U-1 retry budget and the bases are as
before. This round does not claim row 10's exit.
