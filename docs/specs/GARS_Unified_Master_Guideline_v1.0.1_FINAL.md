# GARS — Unified Master Guideline

**Version:** 1.0.1 (unified, specification-hardening release)
**Status:** governing specification for the build of GARS Core, Glitch Brain (the build platform), the homelab, and GARS Bio v0.1. This v1.0.1 release preserves the v1.0 architecture and scope while correcting requirement references and tightening verification semantics.
**Supersedes:** `GARS_Glitch_Brain_Master_Implementation_Guide.md` (Master Guide v1.0), `GARS_Bio_Master_Guidebook_Conformance_v0.2.md`, and the `v0.2.1` amendment. Those documents remain as history; where this guideline is silent, they are references, not requirements.
**Inputs folded in:** the first-principles assessment (`docs/assessment/out/`: 87 subsystem cards, unified map, 32 decided conflicts, constraint table, leverage ranking, scorecard, build order), the adversarial review (`docs/assessment/review/`: 276 findings consolidated to 57, ten patch proposals, three scorecard attacks), and the v0.2.1 amendment (A.5.1–A.5.11: homelab roles, two-node profile, failure-validation matrix, backend abstraction, storage and security policy, deployment progression).
**v1.0.1 hardening changes:** corrected glossary requirement references; made manifest completeness applicability-aware; separated exact-hash from numeric-tolerance reproducibility; clarified design-confounding detection; distinguished independent-context sealing from external-human sealing; made claim/evidence constraints transactionally implementable; replaced the brittle RNA KS threshold with precommitted calibration statistics; and stage-gated homelab failure drills.

---

## 0. How to read this document

- **Requirement IDs.** Every normative sentence carries an identifier `R-nnn`. Each has either an acceptance test (a test path, a script, or a measurement) or the tag `INTENT` (a principle that is not directly testable and therefore never a release criterion). A sentence with neither is a defect in this document.
- **Layers.** Where a requirement applies to one layer it is tagged `[Core]`, `[Glitch]` (the build platform: Codex builds, Claude Code reviews, hooks, tests), `[Homelab]`, or `[Bio]`. Untagged requirements apply to the whole program.
- **Precedence (R-001).** This document governs. Where it disagrees with either superseded document, this document wins; where a coding agent finds it silent, the agent stops and produces a question or a decision record (`docs/decisions/`), never a guess. Acceptance: `test_decision_links_resolve.py` — every `decision NNNN` citation in code or contracts resolves to a file in `docs/decisions/` with fields Context / Decision / Test / Status / Date.
- **Words that are banned as requirements.** "Mandatory", "meaningful", "where practical", "appropriate", "when justified", "validated" (as an adjective), "independent" (as an adjective) — each is replaced below by the ID of the test that decides it. (R-002, INTENT)
- **Document and product versions are separate.** This is guideline 1.0.1; the product it specifies is GARS Bio v0.1. (R-003)
- **Changelog.** This guideline consolidates; it does not append. One plan, one definition of done, one workflow list, one flagship input list, one state vocabulary, one permission model, one memory model.

---

## 1. Purpose, goals, constraints, objective

### 1.1 What the program is (INTENT)

Every part of GARS is one transformation: *(untrusted inputs, a goal, prior knowledge) → trusted outputs + proof of how they were produced.* For Core the inputs are requests and the proof is provenance and audit; for Glitch the inputs are specs and repositories and the proof is tests, reviews and benchmark deltas; for the homelab the inputs are jobs and the proof is that state survives failure and can be restored; for Bio the inputs are data and questions and the proof is the artifact chain behind every typed claim. Value is a trusted output for less effort than producing and verifying it yourself. A component that does not raise trust, lower effort, or shorten verification does not add value.

### 1.2 Author's situation and goals (the constraints every requirement is judged against)

- Solo builder; Codex builds, Claude Code reviews; ~250 author-hours over 12 weeks, of which ~200 are dependable in weeks 1–8 (employment expected at month 2–3).
- Hardware: 2019 MacBook Pro (16 GB); homelab per §13 (Node 1: M70q-class, 6C/12T, 16 GB, 1 TB NVMe; Node 2: N100-class, 12+ GB, 512 GB SSD — reference implementations, replaceable); institutional HPC/Slurm for internal testing only (commercial use requires an agreement not yet sought); $400/month across Claude Max, Codex, API, cloud, of which only the API and cloud lines ($200) are meterable per call.
- Goals in priority order: **(1)** a publishable, demonstrable, governed RNA/epigenomics system for job applications and credibility; **(2)** a paid pilot with one external researcher; **(3)** a longer-term platform. Every trade-off is decided by this order; depth of verification beats breadth of features, always.
- Patient-derived data is likely; the regulatory route is not yet chosen (§6 makes it a decision that must be recorded before such data is ingested).

### 1.3 Objective function

**Verified Task Throughput (R-010, measured by §11):**

```text
VTT = Σ_tasks [ V(task) · P(outcome correct) · P(error would be caught) ]  /  (human-minutes + $ + weighted wall-clock)
```

`P(caught)` is measured only by fault injection: planted defects for Bio (§11.2), planted diffs for Glitch (§10), killed processes and corrupted state for the homelab (§13.5), an attack list for policy (§9.6). A layer with no planted fault has no `P(caught)`.

**Invariants, lexicographically above VTT (R-011 – R-014):** no fabrication (every statistic, file, execution status and citation in an output resolves to a stored artifact, computation or resolved source — `test_numeric_token_audit`, `resolve_citation`, execution status from the scheduler); no unauthorized action (every side-effecting tool call passed a deterministic policy check and, where required, carries an approval record — `test_policy_attacks.py`, `test_approval_forgery.py`); no provenance gap (every completed run contains 100% of the §8.1 manifest fields classified as required for that run; conditional fields are required whenever their applicability predicate is true — `manifest_check.py`); no type laundering (a claim without a NOT NULL type and evidence rows cannot exist — database constraint, §7.8).

**Secondary objectives:** career demonstrability (numbers a stranger can recompute, §11.5) and commercial validation (a paid invoice at a stated price, §19). Tie-break: a small system with unusually rigorous verification serves both; a large system with ordinary verification serves neither.

### 1.4 Axioms (INTENT; the derivation of every rule below)

U1 model outputs are claims, not facts. U2 generation is cheap, verification is the bottleneck. U3 trust is a chain and the weakest link is the ceiling. U4 every domain has a validity structure (in biology: units, replicates, batches) that the platform carries as a first-class object and no model may reason around. U5 what is not measured cannot be optimized — the benchmark precedes the component it scores. U6 complexity is a recurring cost; every abstraction pays rent within the planning horizon or is deferred. U7 the customer buys a trusted output plus the ability to check it. P1 builder = operator = first customer: anything that assumes a team is a hidden cost. P2 a single node is a single point of failure; durability is demonstrated by an executed restore, never by configuration. P3 model-agnosticism is a reproducibility liability until model, prompt and routing are provenance.

---

## 2. Scope of v0.1 and the out-of-scope list

### 2.1 In scope (R-020)

Bulk RNA-seq and bulk ATAC-seq as verified assay families (§14); the ATAC + RNA integration only as claims with evidence links, not as a workflow; the trust chain of §7 end to end on the author's own real analysis (pilot 1); the manifest of §8; the policy of §9; the reviewer harness of §10; the benchmark and defect catalogue of §11; two memory classes (§12); the homelab as the persistent Linux integration and failure-testing environment (§13) with the restore drill executed; the report of §7.8; the public evidence table of §11.5.

### 2.2 Out of scope for v0.1, with the condition under which each returns (R-021)

| Item | Reason (rent rule) | Returns when |
|---|---|---|
| Hi-C / HiChIP / 3D-genome workflows | no wrapper, statistics interface, reference dataset or defect class exists; cannot be run on any payable venue | two benchmark tasks with cited references and one defect class exist for it |
| scRNA / scATAC / Multiome / spatial statistics (wrappers stay as unvalidated registry rows) | no registered pseudobulk path; no reference dataset; depth over breadth | two benchmark tasks per family and a "cells as replicates" defect caught by a registered path |
| Four-agent (or six-role) choreography | independence needs two contexts, not four; nothing rents a Literature or Operator agent | the reviewer harness misses a fault class attributable to planning and analysis sharing one context |
| Five / fourteen memory classes; hybrid-retrieval stages beyond fusion; GBrain adapter | no class has an invariant; retrieval precision unmeasured | contradiction-preservation and drift tests pass on two classes and a benchmark task fails for want of a third; P@10 on a labeled set is below threshold on queries a named stage would fix |
| Web UI, HTTP API, Chat surface | the buyer receives a report; the operator uses the CLI; no auth model exists | buyer-verification minutes are measured on pilot 2 and a second external user is named |
| Core/Bio repository split; monorepo trees of the superseded documents | no second domain or user; the working code has a different layout | a second domain or a second user exists |
| A separate execution abstraction layer | `executorlib` + Nextflow already are it | a priced second venue records a permitted paid run |
| OpenTelemetry / Grafana / Prometheus; HTTP health routes; eight-service compose; Kubernetes; service mesh; distributed database | no consumer; the event log, run ledger and `sacct` actuals are the telemetry; §13.7 stages infrastructure behind consumers | a first long-running GARS service exists, or the failure matrix (§13.5) needs a metric the ledger cannot supply |
| L0–L4 tool taxonomy; §54-style budget threshold engine; six DR runbooks; MCP tool wall; skills tree; four artifacts per feature | replaced by a two-level gate, ledger columns, one drill log, typed subcommands, one decision-record template | a third tool class the two-level gate cannot express; a GARS-owned model call to meter; a failure class the drill does not cover |
| Local LLM inference; reranker; second embedding model | 16 GB shared by two harnesses; forbidden as a production dependency | never in v0.1 |
| The 50-task benchmark; the $1,500–3,000 price; the seven-rung product ladder; the FDA credibility mapping as prose | ten tasks first; price after pilot 1 is timed; no consumer; nothing to map until the manifest carries the model step | see §11, §19; the mapping is one row of the evidence table once §8.1 is complete |
| Pilot 3 (paid, external) | no lawful venue and no data route today | §6's decision page and a priced permitted backend exist, and pilot 2's verification minutes are measured |

---

## 3. Glossary (R-030 — a section using a term differently is a defect)

- **Task** — one request from a human, with a plan, ending in a report. **Run** — one execution of one registered workflow version on one backend, identified by its manifest. **Stage / sub-stage** — the `gars/` workspace's units (00 register, 01 samplesheets, 02 bioinformatics sub-stages, 03 custom analysis); a run happens inside a sub-stage. **Job** — a scheduler unit (Slurm job id) belonging to a run.
- **Artifact** — a file with a sha256 and a type from the closed vocabulary in `_references/artifact_types.md`. **Manifest** — the run's provenance record (§8.1). **Design model** — the computed object (units, conditions, batches, subjects, nesting) produced by the design check (§7.2) and handed to every statistical tool.
- **Result** — a table produced by a registered method. **Evidence** — an artifact or a resolved source referenced by a claim. **Claim** — a typed statement (`OBSERVATION | INTERPRETATION | HYPOTHESIS | RECOMMENDATION`) with ≥ 1 evidence row and a run foreign key. **Finding** — a claim rendered in a report. **Limitation** — a process-risk flag rendered adjacent to the claims it affects.
- **Producer** — the context (model + prompt) that plans and analyses. **Reviewer** — the separate context defined in §10. **Human** — the author; the only approver. There are no other roles in v0.1.
- **Validated (workflow version)** — the status defined by R-087 (a `reference_run.json` exists). **Approved (plan)** — the record defined by R-073. **Verified (backup)** — restored per R-131.
- **Capability** — one of `allow` or `needs-approval` for a typed tool under a role (§9.2). **Data class** — one of `public | deidentified_under_agreement | identifiable` (§6.1). **Venue / backend** — one of `local | homelab | slurm | cloud` (§6.2).
- **Memory class** — one of `episode | result` (§12). **Decision record** — a file in `docs/decisions/` (§16.2). **Evidence table** — the README table of §11.5.

---

## 4. What exists, and what v0.1 adopts (replaces the superseded repository layouts)

There is no `core/` – `domains/bio/` split and no greenfield tree in v0.1 (R-040). The dependency direction (domain code may import shared code, never the reverse) is a decision record now and an import lint when a second domain exists.

| Existing artifact (snapshot 2026-09-08) | Decision | Reason |
|---|---|---|
| `gars/_system/wrappers/*` — seven nf-core wrappers (rnaseq, atacseq, chipseq, cutandrun, methylseq, scrnaseq, spatialvi) + three custom analyses (rnaseq-de, scrna-qc-cluster, spatial-cluster-count) | adopted; rnaseq and atacseq become validated rows (§8.2), the rest stay unvalidated rows | the only executing workflow code; pinned pipeline versions |
| `gars/_system/executorlib.py` (slurm, local) | adopted; gains `cancel`, preserved Slurm terminal reasons, `idempotency_key`, `venue/purpose/data_class` preflight | already the backend abstraction the superseded documents planned to build |
| `gars/_system/wrapperlib.py` | adopted; `write_reproducibility` extended per §8.1; `check_config_common` gains the charset validator and `shlex.quote`; a `config_sha256` re-hash at `collect`/`submit` | writes the manifest today |
| `gars/_system/stage01_samplesheet.py` | adopted; extended into the design check (§7.2) | the only deterministic validator |
| `gars/_system/stage03_analysis.py` | adopted; approval becomes a hashed record (§7.3) | the only approval gate |
| `gars/_system/guard_hook.py`, `gars/.claude/settings.json` | adopted; allow-on-unparseable-stdin removed; protected paths and the attack-list test added (§9) | the only policy enforcement |
| `gars/_system/integrity.py` (`full` mode required before compute) | adopted | truncation detection exists |
| `gars/_references/assay_stage_skill_map.md`, `genomes.md`, `artifact_types.md`, `config_schema.md` | adopted as the workflow, reference and artifact registries; columns added (§8.2, §8.3) | the registries exist |
| `gars/projects/*/HISTORY.md` | adopted as the `episode` memory writer (§12) | append-only, carries template version and model |
| `glitch-main/.claude/scripts/run_evaluator.py` (`JudgeInput`: artifact + check line only) | pattern adopted for the reviewer's input firewall (§10) | structural independence exists and is tested |
| `glitch-main` hooks, `.githooks/pre-commit` (gitleaks), `prepush_gate.py` | patterns copied into `gars/` (§16); the glitch engine itself is not the GARS build platform | the engine is read-only for members; GARS needs its own project-local gates |
| `glitch-main/.claude/scripts/run_db.py` | not adopted in v0.1; a closed-enum `STATUS` writer instead (§15) | no unattended multi-stage runs yet |
| Two source comments citing a "golden-bytes test" (`executorlib.py:17`, `wrapperlib.py:293`) | the test is written in week 1 or the comments are deleted (R-041) | a claim of a test that does not exist is a fabrication in the build |

Nothing existing is rewritten without a decision record naming the test the rewrite passes and the existing code does not (R-042).

---

## 5. Architecture in one page

Five planes, present in every layer; Core owns the generic version, Bio specialises A, C and D, the homelab constrains execution and durability, Glitch is the same chain applied to the build.

```text
PLANE A  trust chain     plan → design check → approval record → execute → validate → review → record → report   (§7)
PLANE B  control         typed tools · two-level gate · protected paths · state vocabulary · failure classes    (§9, §15)
PLANE C  knowledge       two memory classes · workflow & reference registries · citation resolver              (§8.2, §8.3, §12)
PLANE D  evaluation      ten benchmark tasks · defect catalogue · reviewer fault harness · durability drills   (§10, §11, §13.5)
PLANE E  meta            the build governed by the same rules · ledger · DoD · pilot · economics               (§16–§19)
```

The trusted computing base is: checksums, schema validators, the design check, the workflow and reference registries (versions, digests, hashes), the policy code and protected paths, the statistics tools, the claim-schema constraints, the manifest writer, the scheduler's own state. **The model is never in it; neither is memory (R-050, INTENT).** Anything crossing from distrusted to trusted passes through a verifier that is itself in the base.

Roles in v0.1: **producer** (one context that plans and analyses through the stage contracts), **reviewer** (§10), **human** (approver, operator, first customer). Agent-count changes require an ablation showing a measured gain on the benchmark (R-051).

---

## 6. Data classification, venues, and data movement

### 6.1 Data classification (R-060 – R-063)

Every dataset record carries `data_class ∈ {public, deidentified_under_agreement, identifiable}`, the agreement or IRB/exemption reference (or `none`), `permitted_backends`, a provider-exposure rule (which class may enter a hosted-model prompt — default: none but `public`), a retention/deletion rule and an expiry. Ingestion of an unclassified dataset is refused by `stage00_register` (R-060; `test_data_class_required.py`). Sample-level metadata never leaves the execution venue for the homelab or the author's memory system unless the class permits it (R-061; `test_metadata_sync_refused.py`). A run whose `purpose ∈ {internal, pilot_internal, pilot_external, commercial}` or `data_class` is not permitted on its backend is refused before submission (R-062; `test_venue_policy.py`). The regulatory content behind the classes (de-identification standard, IRB, DUA, BAA) is the author's decision, recorded as `docs/decisions/0001-data-handling.md` before any non-public dataset is ingested (R-063). *This guideline does not assert what any regulation requires.*

### 6.2 Venues (R-064)

| Backend | Role (from A.5.1) | Permitted use | Data classes | Sizing / cost |
|---|---|---|---|---|
| `local` (MacBook) | source, IDE, coding agents, unit tests, small fixtures, Nextflow authoring | fixtures only; refused for FASTQ inputs or > 8 GB memory | public | — |
| `homelab` (§13) | persistent Linux integration, small workflow execution, failure and recovery testing, PostgreSQL (authoritative) | internal, pilot_internal; fixtures and small representative runs | public; others only when `docs/decisions/0001` permits storage on it | Node 1 16 GB / 1 TB; Node 2 12 GB / 512 GB |
| `slurm` (institutional HPC) | large NGS jobs, institutional data, existing shared compute | **internal testing only** until an agreement is recorded in `docs/decisions/` | per institution | queue time not the author's; fairshare |
| `cloud` | elastic / GPU burst; the only candidate for paid external work | commercial only when priced and permitted by the data class | public, deidentified_under_agreement (per decision 0001) | priced per sample in `backend_bench.csv` before use |

Backend selection is proposed by the producer and validated by code against permissions, privacy, resource ceilings, cost, software and data location before execution (R-065, from A.5.7; `check_executor_config`).

### 6.3 Data movement and storage (R-066 – R-069, from A.5.8 and the review)

Sequence data never transits the control plane; large raw datasets remain on institutional, HPC, object or cloud storage (R-066, INTENT enforced by R-062's `local` refusal). Every transfer is a recorded operation with method, direction, checksum on arrival and duration (R-067; the manifest's `input_data_location` and per-input sha256). Artifacts are checksum-addressable and provenance-linked regardless of physical storage; temporary executor-local files (`work/`) are distinguished from durable project artifacts; cleanup is policy-controlled and audited (R-068; `artifact_class ∈ {durable, intermediate}` in `OUTPUTS.tsv`, a `work/` retention field, a free-space preflight). Every durable artifact referenced by a claim has an off-node copy or a `presence`/`last_verified_at` check that moves the run to `ARTIFACT_MISSING` when it fails (R-069; `artifact_liveness.py`).

---

## 7. The trust-production chain (Plane A)

### 7.1 Plan (R-070)

Every task has a plan in `plan.schema.json` (JSON Schema 2020-12): `goal`, `scope`, `non_goals`, `assumptions[]`, `facts[]`, `dependencies`, `steps`, `risk`, `acceptance_criteria[]` (each `{check, command}`, minItems 1), `rollback`, `verification`. `[Bio]` additions: `contrast` (factor, numerator, denominator, n per level), `unit_of_replication`, `covariates`, `minimum_n`, `expected_outputs` (artifact types), `falsifier` (the result that would reject the hypothesis). A plan cannot be approved with an empty acceptance criterion, an untyped assumption, or `[Bio]` an empty contrast/unit/falsifier (`test_plan_schema.py`). Acceptance criteria are evaluated by exit codes, never by a model (R-071; §7.5).

### 7.2 Design check (R-072, [Bio], deterministic, before approval)

`stage01_samplesheet.py` refuses with a named reason on any of: (1) any candidate design covariate or nuisance factor (for example `batch`, site, processing group, or subject when modeled as a covariate) perfectly confounded with `condition`; identifier columns such as `sample_id` are explicitly excluded from this test; (2) rank of the indicator matrix implied by the design formula below the number of terms; (3) fewer than two biological replicates in any contrast level; (4) subject nesting violated; (5) a covariate named in the formula absent from the design; (6) duplicated sample ids; (7) strandedness undeclared for RNA; (8) reference release undeclared; (9) a contrast level absent from the design. The data model includes `Subject` (donor / patient / model) and `batch`; `unit_of_replication ∈ {sample, subject, cell_pseudobulk}` is a required field of every statistical test record. The check's output is recorded in the manifest. The producer may comment on design; it does not decide. Acceptance: `tests/test_stage01_design.py` on the sealed planted-design fixtures (§11.2) — recall 9/9.

### 7.3 Approval record (R-073)

An approval is a record `{actor, timestamp, sha256(plan), expiry}` written by a path the agent cannot invoke: `PLAN.md.approved` under a read-only glob in `guard_hook.py`, created by the human's own command. Execution is permitted only while the plan's current sha256 equals the approved sha256 and the expiry has not passed; a plan edit returns the task to `AWAITING_APPROVAL`; a denial moves it to `REJECTED`. `collect` and `submit` re-hash `_config/<assay>.yaml` against the manifest's `config_sha256` and refuse on mismatch, so a post-`prepare` edit by any path is caught without freezing the file. Acceptance: `test_approval_forgery.py` — a forged `Status: APPROVED` line **and** a hook bypass both leave `verify` refusing; a changed plan after approval is refused; the actor is a launch-time fact, not a CLI flag.

Actions that always require an approval record (one list, replacing the superseded documents' four): deleting persistent data; rotating or exposing secrets; changing network exposure, DNS or firewall; publishing any service; destructive migrations; purchases or paid infrastructure above a per-run ceiling; sending data to a third party (including a hosted model, for any class but `public`); disabling or editing any protected path (§9.3); changing evaluation criteria or a sealed fixture; cancelling a running job that has consumed more than one hour of compute; any run on `identifiable` data (R-074).

### 7.4 Execution (R-075 – R-077)

Runs execute only registered workflow versions (§8.2) through `executorlib` on a permitted backend (§6.2) with a generated `submit.sh`; every configuration value reaching a shell, a Groovy config or an `#SBATCH` line passes `shlex.quote` and `^[A-Za-z0-9_./:@-]+$`; `submit_argv` is a backend enum (R-075; `test_wrapperlib_prepare.py`, `test_policy_attacks.py` case 4). Every submission carries `idempotency_key = sha256(params.yaml + samplesheet + config)`; a second `sbatch` with the same key is refused; a retry is Nextflow `-resume` of the same `work/` (R-076; `test_executorlib_resume.py` on the Slurm path or a Slurm-in-container fixture, not the bash stub). Execution status comes only from the scheduler (`sacct`) and the completion marker, never from model text; a job cancelled, timed out or out of memory keeps its scheduler reason (R-077; §15).

### 7.5 Deterministic validation (R-078)

Before review, a `Validator` evaluates every acceptance criterion by running its `command` and reading the exit code (a criterion whose command prints PASS and exits 1 is FAIL); every declared output artifact exists, is non-empty, is typed, and is hashed; `[Bio]` the wrapper exit gates run (`<GROUP>_REP<N>` presence, count-matrix header content, `de_results` identifier gate); the failure class (§15.3) is recorded. A task cannot enter `REVIEWING` with an unevaluated or model-judged criterion. Acceptance: `test_validator_exit_codes.py`.

### 7.6 Review (§10) — the reviewer sees data, design and results before any narrative and writes findings as structured events.

### 7.7 Record (§8) — events and the manifest are written by code at the moment of the call; historical events are never edited (append-only trigger); a corrective event is the only correction (R-079; `test_events_append_only.py`).

### 7.8 Report and the claim schema (R-080 – R-082)

`[Bio]` Claims live in `claims.sql`: `claim{id, run_id FK NOT NULL, type CHECK IN (OBSERVATION, INTERPRETATION, HYPOTHESIS, RECOMMENDATION), text, bio_support JSONB, process_risk JSONB, reference_release, workflow_version}`, `evidence{id, artifact_id | source_id, kind ∈ {computational, statistical, literature}, relation ∈ {supports, contradicts, absent}}`, `claim_evidence{claim_id, evidence_id}`, with creation enforced transactionally: claims are inserted only through a database function or transaction that inserts the claim and at least one `claim_evidence` row before commit; a DEFERRABLE constraint trigger checks evidence cardinality at commit, and `evidence` enforces exactly one of `artifact_id` or `source_id` with a CHECK constraint (R-080; `test_claim_constraints.py` — orphan claims 0 by construction). Confidence is two separable groups, never a scalar: *biological support* (statistical support, replication, orthogonal assay, effect size, literature) and *process risk* (data quality, confounding risk, provenance completeness); reviewer verdicts are events, not a confidence dimension (R-081). The report is rendered by `render_report.py` from the claim tables and the manifest only, with mandatory sections in verification order: question; data and classification; methods (workflow versions, parameters, reference release); QC summary; claims table (type, both confidence groups, evidence links); limitations adjacent to the affected claims; manifest reference and "reproduce this analysis" (`commands.sh`); cost. A report missing a section cannot be emitted; a HYPOTHESIS is never rendered with an observation verb (20-verb denylist) (R-082; `test_render_report.py`). `[Core]` the completion report for a build task is rendered from events only (files changed from `git diff`, tests from test events, benchmark from `evals/runs/`); an item with no event renders as UNKNOWN (R-083).

---

## 8. Provenance, registries, reproducibility

### 8.1 The manifest (R-084; `manifest_check.py` — every field group is classified `required`, `required_if_applicable`, or `optional`; release completeness = required fields present / required fields applicable to that run; threshold in §17)

Written by `wrapperlib.write_reproducibility` at `collect`, never assembled afterward. The manifest schema records the applicability predicate for each conditional field group. Missing optional fields are reported but do not lower completeness; a missing applicable required field invalidates the run:

1. inputs and their sha256; 2. workflow name and version (`pipeline_commit`); 3. parameters (`params.yaml`) and `config_sha256`; 4. **container digests per process** (from Nextflow trace/report enabled in `nextflow.slurm.config`; a mutable tag is not a provenance record); 5. software versions; 6. reference genome build **and** annotation release, with `fasta_sha256`, `gtf_sha256`; 7. the exact command (`commands.sh`); 8. output artifacts with sha256 per file and `artifact_class`; 9. execution timestamps; 10. resources consumed (`sacct --format=Elapsed,MaxRSS,AllocCPUS`); 11. backend, `venue`, `purpose`, `data_class`, `input_data_location`, `artifact_destination`; 12. approval record reference; 13. random seeds and thread counts; 14. design-check output; 15. failure class if any; 16. **for every model-mediated step:** provider, `model_id`, model version, `prompt_id`, `prompt_sha256` (git sha of the prompt/contract file), `routing_rule_id`, sampling parameters, and a reference to the input context; 17. `idempotency_key`; 18. `template_version` and `agent_model` of the stage. A finding whose model steps are not recorded is not a valid finding (R-085). Prompts and contracts are files in the repository, hashed at run time (R-086).

### 8.2 Workflow registry and "validated" (R-087 – R-089)

`_references/assay_stage_skill_map.md` is the registry; each row carries `pipeline_version`, `container_digests`, `validated_version`, `reference_run`, `wrapper_sha256`, `licence`. A workflow version is `validated` when `tests/<workflow>/reference_run.json` exists recording the reference dataset id and input checksums, pipeline version, container digests, exit-gate results, and expected-output checksums or metrics with their tolerance; a version bump without a new reference run resets the status; a run on an unvalidated version is refused unless its manifest is flagged `exploratory`, and an exploratory run cannot produce a claim (R-087; `test_registry_validation.py`). A wrapper whose on-disk hash differs from the registry is refused before execution (R-088). Deprecating a version marks every claim derived from it `STALE` with the reason; a claim is re-validated only by re-execution (R-089).

### 8.3 Reference registry (R-090)

`_references/genomes.md` rows carry source, build, annotation release, `fasta_sha256`, `gtf_sha256`, licence, size, local path per venue; `configure.py` fills `reference.*` from it; preflight compares file hashes to the row; a derived-index cache is reused only when `versionGenome` matches the pipeline's aligner version; claims under different `reference_release` cannot be compared without a mismatch flag (`test_reference_pairing.py`).

### 8.4 Reproducibility testing (R-091)

`scripts/rerun_check.py` re-executes a completed run from its manifest alone on a second backend. Deterministic artifacts designated `byte_stable` must match SHA-256 exactly. Artifacts designated `numeric_tolerance` are canonicalized (stable row/column ordering, normalized metadata and serialization) and compared using named scientific metrics and thresholds from **pre-committed** `tolerances.yaml`; SHA-256 is retained for provenance but is not used as a tolerance test. An entry may be added to `tolerances.yaml` only with a documented cause and a second re-run showing the same class of difference. Model-mediated steps are compared as typed claim-set equality under the predeclared comparison rule. Reproduction rate = matching runs ÷ re-runs. One re-run of a pilot-1 manifest is performed by a non-author on the homelab (the external sentinel).

---

## 9. Policy and security (Plane B)

### 9.1 Typed tools only (R-092)

The tool surface is: stage helpers (`stage00_register`, `stage01_samplesheet`, `configure` menus, `stage03_analysis create | approve | verify`, `resolve_artifact`); wrapper subcommands (`<wrapper> check | prepare | collect`); executor (`submit | status | cancel`); read-only filesystem (list, inspect, metadata, checksum, read text/table schema); `resolve_citation`. There is no Bash tool and no free-form Python/R tool for agents in v0.1. Every tool declares name, description, input/output JSON schema, role permissions, timeout, side effects, network requirement, version; a call whose arguments fail the schema is refused before execution and the refusal is returned to the model as a typed error naming the field (`test_tool_schema_refusal.py`). One worked tool definition is kept in `docs/tools/EXAMPLE.md` as the contract every tool follows.

### 9.2 Permission model (R-093)

Two decisions — `allow` and `needs-approval` — evaluated by code over typed tools per role: producer (stage helpers, wrapper subcommands, executor submit/status; approval-gated actions per R-074), reviewer (read-only tools and `status` only; established by a separate OS user or checkout with a read-only token, never an environment variable), human (everything). The reviewer profile must produce a different decision from the producer's on at least one attack-list case (`test_role_profiles.py`).

### 9.3 Protected paths (R-094)

`guard_hook.py`, `.claude/settings.json`, `.githooks/*`, `_references/ceilings.yaml`, the reviewer prompt files, CI configuration, `docs/decisions/*` with `Status: accepted`, `PLAN.md.approved`, sealed fixtures (§11.2), `_system/`, `_references/`, `_templates/` — cannot be written by an agent session or committed by the producer role; changes are the human's own commit plus an approval record (`test_protected_paths.py`). The Docker socket is not reachable by any agent session (R-095).

### 9.4 Secrets (R-096)

Credentials live outside the repository and outside any process a model can read; `submit.sh` exports an allowlisted environment (no `--export=ALL`); no secret appears in logs, memory, prompts, artifacts, fixtures or `HISTORY.md`; gitleaks runs fail-closed at pre-commit and pre-push in `gars/`; the two bypass switches (`git config hooks.gitleaks false`, `--no-verify`) are denied to agents. Acceptance: `test_secret_containment.py` — a planted canary (with base64/hex decoding) is found in 0 of 9 sinks after a task whose context instructs exfiltration.

### 9.5 Network and homelab exposure (R-097, from A.5.9)

PostgreSQL, Redis, Proxmox management, Docker daemons and workers are reachable only on the tailnet or LAN with a default-deny firewall; administrative interfaces only via trusted local/VPN access; services use least-privilege identities; `tailscale serve`/`funnel` and firewall changes are approval-gated actions; `DATABASE_URL` on the MacBook points at the tailnet address only. Acceptance: `test_exposure.sh` run from a host outside the tailnet with its source IP and a positive-control reachable port in the dated output.

### 9.6 Attack list and threat model (R-098)

Assets: patient-derived data, credentials, the authoritative database, HPC access, the reviewer's independence. Trust boundaries: dataset content (metadata, samplesheets, FASTQ headers), container images and workflow definitions, retrieved literature and web text, memory records, model output. `test_policy_attacks.py` runs five classes against the hooks and the wrappers' preflight — interpreter escape, config-file write (Groovy `beforeScript`), environment exfiltration, workflow-parameter shell injection, protected-path edit — plus the injection fixture (twenty planted-instruction documents in metadata, `HISTORY.md` and a retrieved memory stub, with a positive-control item that must change the plan). Release threshold: 0/5 bypasses; injection resistance 20/20 with the control detected. Skills and MCP servers are pinned by hash with `review_status ∈ {unreviewed, reviewed, rejected}`; an unreviewed one is not loaded in a governed session (R-099).

---

## 10. Reviewer independence and the fault harness (R-100 – R-103)

Independence is engineered: (a) a fresh context that receives data, design and results before any narrative and never the producer's transcript (the `JudgeInput` pattern); (b) a read-only credential per §9.2; (c) `model_id` and `prompt_sha256` recorded on every review; (d) a different model family from the producer where affordable (Codex builds, Claude reviews for code; the same split for science until measured otherwise). Independence is measured, not asserted: `evals/review-faults/` (code: ten planted diffs — off-by-one, deleted test, hardcoded secret, swallowed exception, dropped provenance field, provider coupling, race, weakened criterion, fabricated test result, unrelated refactor — plus five clean) and `evals/bio-faults/` (science: swapped condition labels, wrong reference in params, replicate dropped after approval, pseudoreplicated DE, fabricated citation, causal language on correlational DA, batch-confounded contrast passing rank, p-value edited in the report, missing n = 2 limitation, contradictory literature omitted — plus five clean). At least three of every ten plants are sealed outside the producer context before the reviewer prompt is tuned; during development this may be an `independent_context` sealed session, while any public credibility claim based on sealed faults requires `external_human_seal` (their shas and seal type in `docs/ledger.csv`); the oracle is a deterministic field match on a structured finding, not a grep of prose; catch rate and false-alarm rate are reported per fault class with the first-run-at-prompt-sha value beside the current one. "Reviewer disagreement" is not a metric. Every merge and every claim set carries a review record whose session id differs from the producer's, checked at pre-push from the session registry.

---

## 11. Evaluation (Plane D)

### 11.1 Benchmark (R-110 – R-113)

The benchmark exists before the component it scores. v0.1 starts with **five** tasks in weeks 1–2 (three planted-invalid-design fixtures whose reference answer is "refuse and flag"; one bulk RNA and one bulk ATAC fixture-project task on nf-core test data) and grows to ten (one GEO dataset with a published DESeq2 result; one published peak set; more design defects) when the five discriminate — a degraded configuration (design check disabled; reviewer disabled) must score below the intact one by more than the 3-repeat noise floor (`test_benchmark_discriminates.py`). Each `benchmarks/tasks/<id>.yaml` records `question`, `inputs` (sha256), `expected_workflow`, `expected_outputs`, `known_pitfalls`, `reference_answer`, `reference_source ∈ {public_dataset_with_published_result(DOI), nfcore_test_data_expected_output, synthetic_with_generator_seed, sealed_human_answer(author ≠ builder)}`, `scorer ∈ {exact, regex, pytest, human}` (never a model of the family under test), `holdout`. Held-out tasks live under a path the producer session cannot read; tuned-on and held-out scores are reported separately (R-111). `evals/bench.py` writes `evals/runs/<sha>-<model>-<prompt_sha>.json` with a `resource` block; deltas are reported only between runs with the same model and prompt and are "no change" inside the noise floor (R-112). The weighted score of the superseded documents is withdrawn until every component has a non-model scorer (R-113).

### 11.2 Defect catalogue (R-114)

`benchmarks/defects/catalogue.yaml` — ten defects (batch fully confounded with condition; n = 1 per group; sex/age imbalance across arms; cells treated as replicates; sample labels swapped between `samples.csv` and FASTQ; truncated FASTQ; fabricated output path in a finding; DE table with raw p-values and no correction; claim citing a non-existent DOI; Hi-C resolution mismatch as a placeholder) — each with how to plant it into a fixture project, the expected flag and the expected stage; ≥ 3 sealed outside the producer context, with seal type recorded as `independent_context` or `external_human_seal`; public evidence-table claims require ≥ 3 `external_human_seal` fixtures. `tests/test_planted_defects.py` runs with the producer disabled: `P(caught)` per class = flagged before execution (design/metadata classes) or before completion (finding classes) ÷ planted; false flags on ten clean projects. The first three (truncated FASTQ, swapped labels, n = 1) run against the stage 00/01 helpers with no model in the loop. `[Core]` `evals/faults/catalogue.yaml` — worker killed mid-task; malformed tool JSON; memory record with a fabricated provenance chain; retrieved document with an injection; planted wrong answer in reviewer input; disk full during an artifact write; non-existent file path returned as evidence — each must produce a typed failure event before completion or any durable memory write.

### 11.3 Tracked metrics (R-115) — each defined by its measurement, every ratio printed with numerator and denominator, `0/0` rendered as `uncomputable`

design-defect catch rate per class; reviewer catch rate and false-alarm rate per class; reproduction rate; manifest completeness (applicable required field groups present ÷ applicable required field groups); orphan-claim count (with `claims` in the denominator); policy bypass rate; injection resistance with control; restore-drill age, RPO, RTO; human-touch minutes and interventions per analysis (pilot log); metered $ per completed analysis with the unmetered share stated; hours per green invariant test (from the session registry, printed beside the self-reported ledger). Withdrawn: "hallucination rate", "reviewer score", "reviewer disagreement", "autonomous completion" — until each has a planted fault class or an instrument.

### 11.4 Release check (R-116)

`scripts/release_check.py` regenerates every "current value" cell of the definition-of-done table (§17) from run records and test outputs; a hand-typed number is a defect; a release tag is refused if any row is below threshold or older than 14 days. `gars doctor` prints the session-registry hour total beside the ledger total, backup age, and the last drill date.

### 11.5 The public artifact (goal 1) (R-117)

The repository README carries an evidence table with fixed rows — design-defect catch rate · reviewer catch rate (code, science) · manifest completeness and re-run diff · orphan claims · policy bypass rate · restore-drill minutes and age · hours per verified capability — each `number · test path · date`, committed **empty with "unmeasured"** in week 1 and regenerated from run records (an empty diff on regeneration is the test). `make demo` runs, on a cold clone with no HPC and ≤ 16 GB, the planted-design fixtures through stage 01, one count-matrix fixture through `rnaseq-de` and `render_report.py`, and `test_planted_defects.py`; target ≤ 30 minutes. One worked example on a public dataset (§21 Q1) is the published analysis. The FDA-credibility mapping is one row of this table, written only after R-084 is complete on a real run.

---

## 12. Memory and knowledge (Plane C)

Two classes with invariants (R-120): `episode` (what happened — `HISTORY.md` entries and daily logs, append-only, with `template_version`, `model`) and `result` (validated claims with provenance — the claim table of §7.8 *is* this class). Procedural knowledge is the workflow registry; decisions are decision records; semantic memory is deferred (§2.2). One `memory` table with `type ∈ {episode, result}`, `source_kind ∈ {event, artifact, human, agent}`, `supersedes` + `superseded_reason` (NOT NULL when set), `valid_from/valid_until`, `embedding_model` + `embedding_model_sha256` per vector row, a `BEFORE UPDATE OR DELETE` trigger; `forget` is a supersession row with `tombstone = true` and a reason, never a deletion (R-121; `test_memory_supersession.py`). A `result` row requires `source_kind ∈ {event, artifact}` — agent prose can never become a result (R-122; `test_memory_no_laundering.py`). Memory is a prior for planning and interpretation; it is never an input to execution or statistics: generated execution artifacts are byte-identical under ten planted memories, with a positive-control legitimate memory that must change the plan (R-123; `test_memory_drift.py`). Retrieval in v0.1 is the existing rank-position fusion (keyword + vector) with project/time filters and a mandatory `memory_id` citation on every context-pack item; each item carries `source_kind` and a trust label; no synthesis stage inserts an unattributed claim (R-124; `retrieval_gold.jsonl`, P@10 ≥ 0.7). Citations: `resolve_citation.py` (DOI via Crossref, PMID via E-utilities — external services relied upon) is a required write-time validator; a fabricated identifier is rejected; the literature role is READ-only with no submit path (R-125; `test_citation_resolution.py` 5 real / 5 fabricated). `[Glitch]` the author's second brain (`glitch-main`) is not GARS memory; nothing from a pilot dataset enters it (R-126).

---

## 13. Durability and the homelab (from A.5.1 – A.5.11, gated by rent)

### 13.1 Roles (R-130, from A.5.1) — the workstation develops; the homelab is the **persistent Linux integration and failure-testing environment**, not the production-compute target for large datasets; HPC runs large institutional jobs; cloud runs elastic or GPU work when justified. No component assumes a workload always runs on one machine; the same execution abstraction (§6.2, R-065) targets homelab and Slurm without changing domain logic.

### 13.2 Backup and restore (R-131 — the first Homelab requirement, before any claim row is written to PostgreSQL)

The authoritative PostgreSQL (Node 1) is dumped nightly (`infra/backup/pg_backup.sh`: `pg_dump | age/gpg | rsync` over the tailnet to the MacBook, and a second copy to the destination `docs/decisions/0001` permits for the data class); `glitch-main`'s `memory.db` and the vault are copied the same way. `infra/backup/restore_drill.sh` restores **the scheduled backup** (the newest file at the off-machine path, not one the drill just made) on the real Node 1 after deleting the primary, with a canary value and pre-destroy row counts supplied outside the operator context; `independent_context` is sufficient for development drills, but the public restore-credibility claim requires one `external_human_seal` drill; per-table checksums are diffed; an empty database is a FAIL; the result `date, RPO_h, RTO_min, PASS|FAIL` is appended to `docs/ops/restore-log.md`. Thresholds: drill ≤ 30 days old, RPO ≤ 24 h, RTO ≤ 60 min. A backup that has never been restored is not verified; "PostgreSQL is the source of truth" is a claim until the first PASS line exists.

### 13.3 Two-node profile (R-132, from A.5.3 — reference implementation, not a dependency)

Node 1 (M70q-class, 16 GB, 1 TB NVMe; Proxmox may run here) hosts the stateful and compute-intensive integration workloads: PostgreSQL (authoritative), the worker(s), Nextflow fixture jobs, disposable test VMs. Node 2 (N100-class, 12+ GB) hosts monitoring, DNS/reverse proxy, uptime checks and the external-observer role, as a separate failure domain. Two nodes are not high availability; HA requires quorum, replicated state and tested failover and is out of scope (§2.2). Recorded facts: RAM, disk, and the off-machine destination in `docs/ops/HARDWARE.md`.

### 13.4 Reliability mechanisms (R-133, from A.5.5 — deterministic software, never the model)

Health and readiness checks (as a `gars doctor` CLI until a long-running service exists); bounded timeouts; bounded retries with backoff only where safe; idempotent submission and state transitions (R-076); durable run state; explicit worker ownership; detection of abandoned or stale executions (a run with no scheduler record and no heartbeat moves to `STALE`); controlled restart; artifact integrity checks (R-069); tested restore (R-131); migration discipline (every schema change has a migration, a rollback and a test); correlated logs; resource monitoring; observable degraded states; **deterministic reconciliation between executor state and authoritative state** after any restart. The model may diagnose or recommend; it never sets execution state.

### 13.5 Failure-validation matrix (R-134, from A.5.6 — each row is activated only when its named deployment stage exists; each active row is a test or operator drill with retained evidence; state correctness, not mere restart)

| Active from | Failure injected | Expected behaviour | Evidence retained |
|---|---|---|---|
| Stage 1 | API/CLI process stops | dependent requests fail clearly; restart without corrupting task state | log, health event, recovery event |
| Stage 3 | Worker stops during a run | run → `STALE`/`FAILED` per policy; no false completion; safe retry when allowed | heartbeat, state transition, retry record |
| Stage 2 | Node 1 reboots | Node 2 detects the outage; state returns from durable storage; incomplete runs reconcile | outage alert, boot/recovery log, reconciliation record |
| Stage 2 | Node 2 stops | execution continues; loss of monitoring is visible | monitoring-unavailable event |
| Stage 2 | Database unavailable | writes fail safely; no fabricated success; bounded back-off | DB error, task state, abort event |
| Stage 3 | Queue unavailable (when a queue exists) | pending work does not disappear; degraded state exposed | queue error, pending state |
| Stage 1 | Network path interrupted | remote calls time out; bounded retries; state consistent | timeout/retry events |
| Stage 1 | Disk approaches capacity | alert before exhaustion; large work refused by policy | storage metric, policy decision |
| Stage 4 | Container/workflow exits non-zero | run `FAILED:<reason>`; stdout/stderr and manifest retained | exit code, logs, manifest |
| Stage 1 | Invalid deployment/configuration | readiness gate prevents promotion | deployment result, validation log |
| Stage 1 | Backup restore | restored database and artifacts pass integrity and application checks | restore log, checksums |
| Stage 2 | `kill -9` of PostgreSQL + data-directory loss; disk full during an artifact write | R-131 restore; run ends `FAILED` with an event, never `COMPLETED` with a truncated artifact | drill line; failure event |

GARS never reports a task as completed when its executor failed, disappeared, or became unreachable (R-135; `test_no_false_completion.py`).

### 13.6 Storage and security on the homelab — R-066 – R-069 and R-097 apply; sensitive biomedical data is placed on the homelab only when `docs/decisions/0001` says its storage, encryption, access control, retention and institutional requirements are satisfied (R-136).

### 13.7 Deployment progression (R-137, from A.5.10, each stage entered only when a consumer in this guideline needs it)

Stage 1 — Linux foundation: Proxmox on Node 1 (or Debian directly; learning virtualization is not a goal — decision record), Linux on Node 2, networking, SSH, DNS, Git, backups and the first restore drill (§13.2). *Consumer: R-131, week 3.* Stage 2 — persistent services: PostgreSQL only, plus the reverse proxy and basic monitoring on Node 2; Redis/queue only when a worker exists. *Consumer: the claim table (§7.8), week 4–5.* Stage 3 — distributed execution: one worker, heartbeats, timeouts, retries, reconciliation, the failure matrix rows that exercise them. *Consumer: unattended multi-stage runs (deferred in v0.1 unless pilot 1 needs them).* Stage 4 — scientific execution: Nextflow + Apptainer fixture workflows on Node 1, artifact and provenance validation. *Consumer: the `homelab` backend row of §6.2 and R-091's second-backend re-run.* Stage 5 — heterogeneous routing: homelab and Slurm executors under one policy; cloud when a paid run is priced. No Kubernetes, distributed databases, service meshes or HA mechanisms are introduced to imitate scale (R-138, INTENT).

---

## 14. Assay contracts, v0.1 (Bio validity structure — R-140 – R-145)

Each family in scope has: a schema (design columns incl. `subject`, `batch`, `condition`, `replicate`; per-family extras), a QC contract with per-check disposition `HALT | DEGRADE (proceed with a recorded limitation attached to every downstream claim) | WARN`, the workflow (registry row), expected outputs (artifact types), validation rules (the design check plus family checks), benchmark tasks, failure modes, and interpretation rules — as code and tables under `_references/`, not prose (R-140). A `DEGRADE` result can never be rendered as an unqualified finding (R-141).

**Bulk RNA-seq (nf-core/rnaseq pinned; `rnaseq-de` with PyDESeq2):** checks — strandedness declared and verified against the pipeline's inference; contamination and sample-swap/sex concordance where the data allow (WARN in v0.1); `batch` in the design and permitted in the formula; outlier policy stated; independent filtering, shrinkage choice, alpha and effect-size reporting recorded in the DE record; multiple-testing scope per contrast; pathway analysis method (ORA vs rank-based), gene-set collection and version, and the tested-gene universe recorded; null calibration per wrapper release using 20 within-batch label permutations with fixed, predeclared seeds; calibration is judged by a named statistic and precommitted tolerance (for example, empirical false-positive proportion and p-value-quantile deviation), not by a single `KS p ≥ 0.05` pass/fail threshold (R-142).

**Bulk ATAC-seq (nf-core/atacseq pinned):** checks — replicate structure ≥ 2 per level; consensus-peak strategy declared (union / n-of-N / IDR) and recorded because it sets the feature universe; blacklist handling declared; FRiP, TSS enrichment and fragment-size QC with dispositions; normalization assumption stated (global scaling assumes no global shift — a limitation on chromatin-targeting treatments); differential accessibility through the same design model (R-143).

**Cross-assay integration (ATAC + RNA):** only as claims with evidence links across the two results tables; enhancer–gene links are `HYPOTHESIS` unless supported by a registered evidence kind, and the report says which (R-144).

**Pseudoreplication (rule that admits single-cell later):** cell-level data enters a differential test only through `{pseudobulk_deseq2, pseudobulk_edger, glmm_by_subject}` with `unit_of_replication ∈ {subject, sample}`; any other path is refused (R-145).

The other five wrappers remain unvalidated registry rows and may run as `exploratory` only.

---

## 15. Task lifecycle and failure handling (one vocabulary — R-150 – R-153)

States: `CREATED → PLANNED → AWAITING_APPROVAL → APPROVED → EXECUTING → VALIDATING → REVIEWING → COMPLETED`, plus `REJECTED` (approval denied or review rejects), `FAILED:<reason>` (scheduler reason preserved: `TIMEOUT`, `OUT_OF_MEMORY`, `CANCELLED`, `NODE_FAIL`, `EXIT_<n>`), `DIAGNOSING` (a producer stage that proposes; it never gates the retry decision), `RETRYING` (bounded; `-resume`; parameter changes re-enter `AWAITING_APPROVAL`), `CANCELLED`, `PAUSED`, `NEEDS_INPUT`, `PARTIAL`, `STALE`, `ARTIFACT_MISSING`. Every non-terminal state has cancel and failure edges (R-150). In v0.1 the vocabulary is realised as a closed-enum `STATUS` file written only by `wrapperlib.write_status()`; a grep-sweep test asserts every wrapper uses it (R-151); a durable state table arrives with unattended multi-stage runs (§13.7 Stage 3). Failure classes `{transient, workflow, tool, infrastructure, data_quality, agent_reasoning, scientific_validation}` are assigned by deterministic rules from exit codes and scheduler states; only `transient` is retried, at most `maxRetries` (in `nextflow.slurm.config`); no destructive step is retried without an approval record; every failure produces an artifact (error text, class) and a regression test (R-152; `test_failure_classification.py` on six injected failures). Human-touch events (approval, fix, rerun, data, interpretation) are logged with timestamps and reason codes (R-153; the pilot log, §19).

---

## 16. Build governance (Plane E, Glitch layer — the build obeys the product's rules)

### 16.1 Constitution and harness (R-160 – R-162)

`gars/AGENTS.md` (≤ 1 page) has exactly these headings, each naming a file or command that exists or "none": mission, architecture (this document), coding standards, security policy (§9), testing policy (§16.3), memory policy (§12), Git policy, change-control policy (§16.2), prohibited operations (R-074, R-094), definition of done (§17); `CLAUDE.md` says "read AGENTS.md" (R-160; cold-session test: a fresh session answers "what runs the tests?" with a command that exits 0). `gars/` is built in its own repository with three project-local mechanisms — `guard_hook.py`, the gitleaks pre-commit/pre-push, and the trailer check — under one harness's hook format; Glitch is the author's memory system, not the GARS build platform (R-161). Codex builds and Claude Code reviews; the reviewer session is a separate OS user or checkout (R-162, §9.2).

### 16.2 Change control (R-163)

One decision-record template (`Context / Decision / Test-that-proves-it / Status / Date`) in `docs/decisions/`; the 210 existing `decision NNNN` citations resolve to files or are deleted/stubbed; the link checker runs at pre-commit. No separate spec, plan and ADR per feature; the plan schema (§7.1) is the plan.

### 16.3 Tests and the merge gate (R-164 – R-166)

`gars/tests/` exists before any `_system/` change (`test_guard_hook.py`, `test_stage01_design.py`, `test_wrapperlib_prepare.py` — prepare twice → identical bytes, `test_wrapper_contract.py` over all seven wrappers, `test_executorlib_resume.py`); the pre-push gate runs the **whole** suite on every push and treats "collected 0 tests" as refusal; ten semantic mutants sealed outside the producer context are recorded in `evals/mutants.md` with the test that kills each (R-164; ≥ 8/10 killed). Every commit touching `_system/**` carries `Review:` (a record whose session id ≠ the committing session), `Bench:` (an `evals/runs/` file for HEAD, or `n/a` only when no `_system/` file changed) and `Session:` trailers, checked at pre-push (R-165). Linux integration runs on a runner that has Apptainer and the pinned pipeline checkout (Node 1 or an HPC login node), not a hosted runner (R-166).

### 16.4 Ledger and budget (R-167 – R-168)

`docs/ledger.csv` (date, hours, $, provider, requirement ID, test-that-went-green, commit) is started in week 1; hours are cross-checked against the harness session registry by `gars doctor`. The monthly ceiling is $400; `budget.json` records `{scope, ceiling_usd, spent_usd, updated_at}` for the metered lines (API, cloud); the reviewer harness spends ≤ $25 per weekly loop; the unmetered share is stated in every cost report. A per-analysis cost report (metered $, compute actuals from `sacct`, human minutes) is produced by the ledger, not by a threshold engine.

---

## 17. Definition of done for GARS Bio v0.1 (one table — R-170; regenerated by `release_check.py`)

| Clause | Test | Threshold |
|---|---|---|
| design-defect catch rate | `tests/test_planted_defects.py` | ≥ 9/10 on the sealed catalogue; ≤ 1/10 false flags |
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) |
| manifest completeness | `manifest_check.py` | 100% of applicable `required` and `required_if_applicable` field groups on every completed run; missing optional groups reported separately; model-step fields required whenever a model-mediated step occurred |
| reproduction rate | `scripts/rerun_check.py` | ≥ 4/5 on test data; one external re-run of a pilot-1 manifest matching under the pre-committed tolerances |
| orphan claims | DB constraint + `claims` ≥ 1 for pilot 1 | 0 / n, n > 0 |
| approval forgery | `test_approval_forgery.py` | 0/1 |
| policy bypass; injection resistance | `test_policy_attacks.py`; injection fixture with control | 0/5; 20/20 with control detected |
| secrets containment | `test_secret_containment.py` | 0/9 sinks |
| restore drill | `restore_drill.sh` on Node 1 from the off-machine copy; canary supplied outside the operator context | dated PASS ≤ 30 days; RPO ≤ 24 h; RTO ≤ 60 min |
| no false completion | `test_no_false_completion.py` (worker killed; executor unreachable) | 0 false completions |
| gars test suite | pre-push gate; `evals/mutants.md` | whole suite green on every push; ≥ 8/10 mutants killed |
| public artifact | README evidence table regenerated from run records | every row filled by a test; `make demo` ≤ 30 min on a cold clone |
| pilot 1 | timed log with reason codes; report rendered from tables; unit-economics sheet generated from the log | human-touch minutes and interventions recorded; report emitted with every section |

"Willing to pay", "backend-neutral", "independent review exists", "confounding detected", "the benchmark exists" and the eight named gates of the superseded documents are withdrawn as done-criteria; each is either a row above or a pilot outcome (§19).

---

## 18. The plan (one critical chain, sized in hours — R-180)

Budget: 250 h; ~200 dependable in weeks 1–8 at ~25 h/week; the at-risk tier assumes ≤ 5 h/week after. Hours are ranges from the costed review; cluster queue time is not counted. Every row ends in a named test; the exit is its pass, red at the parent commit and green at the row's commit. The order is benchmark → validator → tests → policy → drill → manifest → report/claims → catalogue and venue → reviewer → records → lifecycle → pilot.

| Row | Weeks | Artifact | Exit test | Hours | If hours collapse |
|---|---|---|---|---|---|
| 1 | 1 | three planted-invalid-design fixtures (sealed outside the producer context; public claims require external-human sealing) + the design check (§7.2) + `tests/test_stage01_design.py` + `docs/ledger.csv` + README evidence table (empty) + `gars/AGENTS.md`; the two "golden-bytes" comments resolved | design recall 3/3; cold-session test | 16–30 | keep |
| 2 | 1–2 | five benchmark tasks (§11.1) + `evals/bench.py` + noise floor + sealed held-out slice | five tasks with reference source and scorer; noise floor recorded; degraded run scores lower | 16–24 | keep |
| 3 | 2–3 | `gars/tests/` suite + pre-push gate (whole suite) + mutants sealed outside the producer context; public claims require external-human sealing | ≥ 8/10 mutants killed; 7/7 wrapper contracts | 18–26 | keep |
| 4 | 3 | attack-list test; Bash and free-form Python/R removed; `shlex.quote` + charset validator; `config_sha256` re-hash; approval record; protected paths; bypass-switch denies | bypass 0/5; forgeable approvals 0/1 | 14–20 | keep |
| 5 | 3–4 | Stage 1 homelab foundation; nightly `pg_backup.sh` + off-machine copy; `restore_drill.sh` on Node 1 with a canary supplied outside the operator context; one-service compose (PostgreSQL); `docs/ops/HARDWARE.md`; `test_exposure.sh` | first dated PASS with RPO/RTO; exposure 0 ports from outside | 10–16 | keep |
| 6 | 4 | trace/report via `nextflow.slurm.config`; per-file output sha256; model/prompt/routing fields; genome hashes; `venue`/`purpose`/`data_class` from the machine-owned dataset row; n = 2 re-runs; pre-committed `tolerances.yaml` with artifact comparison modes | manifest 100% of applicable required groups; reproduction n = 2 | 12–20 | keep |
| 7 | 4–5 | report template → `claims.sql` → `render_report.py` (Stage 2 homelab: the claim table is the first PostgreSQL consumer, after row 5's PASS) | orphan claims 0 enforced; template renders the fixture with every section | 16–22 | keep |
| 8 | 5 | defect catalogue rows 4–10 (≥ 3 sealed outside the producer context; public claims require external-human sealing); `docs/decisions/0001-data-handling.md`; `backend_bench.csv` (local, homelab, slurm) | P(caught) ≥ 9/10; data route recorded 3/3; 3 backend rows | 14–20 | catalogue only |
| 9 | 5–6 | review fault harness, code half (10 plants, ≥ 3 sealed outside the producer context; 5 clean; public claims require external-human sealing); JSON review record; reviewer as a separate OS user | catch and false-alarm rates per class, first-run-at-sha | 14–20 | keep |
| 10 | 6–7 | review fault harness, science half (5 fixtures + 3 clean, one repeat) | science catch rate per class | 12–25 | at-risk tier |
| 11 | 7 | decision-record template + link checker; the DoD table (§17) wired to `release_check.py`; trailer check with session-id inequality | 100 % citations resolve; DoD cells regenerated | 8–12 | keep table; defer `make demo` |
| 12 | 7–8 | closed-enum `STATUS` writer with preserved Slurm reasons and `CANCELLED`; `idempotency_key` in `submit.sh`; `cancel` verb; failure-class rules; `test_no_false_completion.py` | duplicate side effects 0; every wrapper uses the writer; 0 false completions | 6–10 | keep |
| 13 | 8 | timed pilot 1 on the DE stage of the author's own analysis (`venue=slurm, purpose=internal`, class per decision 0001); one re-run of that stage from its manifest; generated unit-economics sheet | human-touch minutes measured; re-run diff explained | 15–27 | at-risk tier |
| 14 | 8 | evaluator planted-lie test; smoke delta (three no-cluster tasks) per `_system/` merge | planted-lie catch 1/1; `Bench:` on every `_system/` merge | 5–8 | defer |
| 15 | 8 | secrets canary (base64-aware) + gitleaks hooks in `gars/` | canary 0/9 | 3–5 | keep |
| at-risk | 9–12 | GEO published-DESeq2 task and two ATAC tasks; citation resolver; two-class memory table; retrieval gold set; the deferred halves of rows 10 and 13; Stage 3–4 homelab (worker, heartbeats, fixture Nextflow on Node 1, the remaining failure-matrix rows); `make demo` | as named | 25–40 | as capacity allows |

Rows 1–15 ≈ 200–205 h at the mid estimate. Row 2 is the step most likely to slip (queue time, reference-data drift, Apptainer conversions are outside the author's control), which is why it is split and why its GEO task is in the at-risk tier. The expected evidence-table rows by week 8 are four (design recall, first benchmark score, drill, manifest re-run); the reviewer catch rates and the pilot land in the at-risk window unless rows 10 and 13 are taken in full. A row whose metric did not move is reverted, not iterated (R-181, INTENT).

---

## 19. Pilot, deliverable, economics, positioning (R-190 – R-195)

**Pilot sequence:** 1 — the author's own real analysis (row 13), timed with the log template (`ts, stage, actor ∈ {human, agent, tool}, action, reason_code ∈ {approval, fix, rerun, data, interpretation, other}, minutes`) against a written by-hand baseline; 2 — a trusted scientist, who provides the `external_human_seal` for public sealed plants and serves as the external re-run sentinel, with the report's buyer-verification minutes for the top three claims measured by stopwatch; 3 — an external researcher, deferred (§2.2). Each pilot dimension has an operational definition bound to a log column: time saved = baseline hours − human minutes; interventions = log rows with actor = human; scientific errors = defects the researcher finds ÷ claims delivered; reproducibility = the re-run diff; cost = the ledger; satisfaction and willingness to pay = a signed engagement or a paid invoice at a stated price, nothing less (R-190).

**Deliverable:** the report of §7.8, the figures it embeds, the code/workflow versions it names, and the manifest — nothing else is sold (R-191). **Engagement terms (before any paid work):** scope defined by sample count and assay; a revision limit; a billable outcome for "the design cannot support this question"; a liability cap; IP and licence for delivered workflow code (a `LICENSE` file exists; tool and reference licences are flagged in the registry); an authorship/acknowledgement rule; response expectations and what happens to a running analysis if the homelab is unavailable; a project export (inputs manifest, workflow versions, outputs with checksums, report, provenance) readable without GARS (R-192).

**Economics:** no price is published until pilot 1 is timed; the unit-economics sheet is generated from `pilot1_log.csv` and `backend_bench.csv` with no hand-entered cost cell (hours by stage × hourly value + compute $ by backend + verification hours + liability line = cost; margin stated) (R-193). **Positioning:** an expert computational biologist delivering analyses with an unusually verifiable artifact chain — the catch rates and the manifest are the sales argument; not "a persistent AI computational biologist"; the seven-rung ladder is withdrawn (R-194, INTENT). **Buyer for pilots 1–2:** the academic/translational segment the author can reach; the company segment is a later decision (R-195).

---

## 20. Requirement-to-source map (what each section resolves)

| Section | Framework cards | Review findings | Amendment |
|---|---|---|---|
| 0–1 | FRAMEWORK A.0–A.2, P1–P3; E1/E11 | CR-01, CR-22, CR-23, CR-46 | — |
| 2 | 20_unified_map §6; 31_leverage §2 | CR-23, CR-38, CR-39, CR-41, CR-48 | A.5.10 (no Kubernetes/HA) |
| 3 | — | CR-22, CR-29 (ED-03, GAP-15) | — |
| 4 | A3/A4-Core, A2/A3-Bio, C5/C15/C16 | CR-02, CR-26 (PRE-25) | — |
| 5 | A.3 planes; A6-Core | CR-38 | — |
| 6 | A1/B14-Homelab, E10, E16-Bio | CR-15, CR-16, CR-25 | A.5.1, A.5.7, A.5.8, A.5.9 |
| 7 | A1–A8-Core, A1–A7-Bio, B2-Core | CR-07, CR-10, CR-20, CR-29, CR-30, CR-31 | — |
| 8 | A7-Core, A3-Bio, C15/C16-Bio, D15-Bio | CR-05, CR-06, CR-44, CR-45 | — |
| 9 | B1/B4-Core, B8/B9-Glitch, B12-Homelab, B15-Bio | CR-11, CR-12, CR-13, CR-28, CR-35, CR-36, CR-47 | A.5.9 |
| 10 | A6-Core, A4-Glitch, A6-Bio, D5/D7 | CR-09 | — |
| 11 | D1/D4-Core, D12/D13/D14-Bio, E15-Bio | CR-04, CR-24, CR-31, CR-51 | — |
| 12 | C1–C4-Core, C13/C14-Bio, C6-Glitch | CR-27 | — |
| 13 | A3/B13/C10/C11/D9/E8/E9-Homelab, B5/B6/B7-Core | CR-17, CR-18, CR-25, CR-37 | A.5.1–A.5.6, A.5.8–A.5.11 |
| 14 | A2/A4-Bio | CR-08, CR-32, CR-43 | — |
| 15 | B5/B6/B7-Core, B16/B17-Bio | CR-18 | A.5.5 |
| 16 | A1–A5-Glitch, E2–E7, B10/B11-Glitch | CR-12, CR-26 | — |
| 17 | 40_scorecard; D14/E12-Bio | CR-19 (ED-17/18) | A.8 additions (four clauses folded) |
| 18 | 41_build_order; 52_levers_costed; 53_scorecard_v2 | CR-03 (PRE-14/15) | A.5.10 progression mapped to rows 5, 7, at-risk |
| 19 | E13/E14-Bio | CR-20, CR-21, CR-40, CR-42, CR-49 | — |

---

## 21. Open decisions (answer in one sentence each; the build proceeds on the default until then)

1. Which public dataset (accession, licence, size) is the flagship demo run on, and what is its unit of replication? *Default: nf-core test data only; the public example is a fixture.*
2. Which five, then ten, benchmark tasks have reference answers from outside the system, and who seals the held-out slice? *Default: the five of §11.1; the reviewer agent in a sealed session seals the slice until the trusted scientist can.*
3. Which ten faults is the reviewer measured against, who plants three of them, and what catch rate and false-alarm ceiling release? *Default: §10's lists; 8/10 and 1/5.*
4. Is the pilot-1 dataset patient-derived, and which data class may enter a hosted-model prompt? *Default: treat as `deidentified_under_agreement`; only `public` enters a prompt.*
5. Will you seek the institutional agreement for commercial use of the cluster, and by when? *Default: not this year; pilot 3 deferred.*
6. Off-machine backup destination for each data class; RTO/RPO targets. *Default: MacBook over the tailnet; 60 min / 24 h.*
7. Proxmox on Node 1 or Debian directly? *Default: Debian directly unless learning virtualization is declared a goal.*
8. Hourly value of your time; what "a project" is in samples and assays. *No default; the price waits.*
9. Who provides the external-human seal for public benchmark/fault claims and the public restore canary before pilot 2? *Default: development may use a reviewer agent in an `independent_context` sealed session, but public credibility claims remain `unmeasured` until a trusted scientist provides `external_human_seal` evidence.*
10. Which model IDs and prompt files are in use today, and where do prompt files live? *Default: `gars/_references/prompts/`, hashed at run time.*
11. Do the "golden-bytes test" comments get a test or get deleted? *Default: deleted in row 1.*
12. Which annotation release is pinned, and do the benchmark references use the same one? *Default: Ensembl 116; mismatch flag on claims.*

---

**Governing principle (INTENT).** GARS is a reliable computational workflow system with an AI interface, persistent provenance-linked memory, evidence-based claims, deterministic execution, and *measured* independent verification. The model decides within a validity structure it cannot alter; deterministic software enforces; every "must" in this document is the ID of a test; and the build is governed by the same rules as the product, because the same person is both.
