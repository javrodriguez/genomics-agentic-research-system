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
