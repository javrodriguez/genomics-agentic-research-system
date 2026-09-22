---
date: 2026-09-22
status: standing # provisional; owner confirmation pending
kind: decision
touches:
  - gars/_system/stage03_analysis.py
  - gars/_system/executorlib.py
  - gars/_system/wrapperlib.py
  - gars/_system/wrappers/
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/_system/tools/
  - gars/02_bioinformatics/
  - tests/run_tests.py
  - gars/tests/
  - benchmarks/tasks/
  - docs/implementation/row_4_change_report.md
symptoms:
  - workspace approval sidecar authenticates after a hook bypass
  - direct collect lacks the prepared config hash check
  - characterization expectations conflict with the restricted typed surface
---
# Row 4 provisional owner rulings

Addendum to [0058](0058-row-4-typed-surface-and-attack-list.md), which remains byte-identical.
No review has run. These are the owner's provisional instructions of 22 September 2026,
applied while the owner is away; the owner confirms or reverses each afterwards.
Number 0054 follows 0053; 0052 remains reserved to row 15 as 0053 records.

## Rulings

1. **Approval trust and expiry — option A: provisional ruling, to be confirmed by the owner.**
   Attributed to the owner. `approve` creates a human-owned store at
   `<workspace parent>/.gars-approvals/`, outside the installed workspace root. The store
   must be a real directory, owned by the launching UID, mode 0700; records must be regular
   files owned by that UID, mode 0600. Symlinks and permissive modes refuse. The guard and
   settings protect the store; guarded filesystem reads stay inside the workspace, including
   resolved symlinks, and Read/Glob/Grep are included in the hook matcher. The human runs the
   original approval CLI outside the agent harness. Its actor is captured at import/launch
   from `os.getuid()` and `pwd.getpwuid()`, never USER, LOGNAME, another environment variable,
   or a role/actor flag. The CLI cannot use `--workspace` to relocate the store.

   A record contains `{actor, timestamp, plan_sha256, expiry}` plus `plan_path`, the resolved
   identity that prevents copying a valid record to another plan, even with identical bytes.
   Its filename is SHA-256 of that identity. Timestamp and expiry are explicit UTC ISO-8601
   instants (`YYYY-MM-DDTHH:MM:SSZ`). **Default lifetime: 24 hours**: one bounded execution
   window rather than an indefinite grant, with enough time for a normal working day and
   queue delay. Longer runs or delayed verification may require a new analysis and approval;
   expiry is checked at verification and submission, not merely issuance. There is no
   expiry-extension flag or silent reapproval. The existing once-per-analysis rule remains.
   `--date` affects only the readable plan stamp, never timestamp or expiry.

   `verify` reads only the derived store record, checks expiry, lifetime, actor, plan identity
   and current plan bytes, and repeats the plan-content gates. A forged status line or a
   hand-written workspace `PLAN.md.approved` is never evidence. `submit` uses the same store
   check for custom analyses. Records are created exclusively; a failed write leaves refusal,
   never a fallback to the old sidecar. No cryptographic library or third-party dependency.

2. **Existing characterization tests — option A: provisional ruling, to be confirmed by the owner.**
   Attributed to the owner. Only expectations invalidated by R-073, R-075, R-092, R-096 or
   R-098 change. Every changed test is listed with its source line, old/new expectation and
   requirement in the round-2 report. Unprepared fixtures now expect the named R-073 refusal.
   Their original content assertions remain, and a row-4 companion test supplies fixture
   manifests through the real reproducibility helper and reruns those assertions. Prepared
   local execution, failure, resume and completed re-entry also have a positive regression.
   The benchmark's own `evals/bench.py:file_sha` re-derives changed input pins; no digest is
   authored by hand. The observed seven benchmark errors arise from two wrapper pins; the
   literal-contract changes also require their two contract pins to be re-derived. Only
   these four `sha256` lines in the two public task files change. No sealed slice is accessed.

3. **Collect placement — option A: provisional ruling, to be confirmed by the owner.**
   Attributed to the owner. Each of the ten wrappers adds exactly one call at the beginning
   of `cmd_collect`: `wl.require_collect_config(args.project, ASSAY, SUBSTAGE)`. The shared
   helper reuses `config_holds` and refuses with its reason before reading result artifacts
   or writing STATUS/OUTPUTS.tsv. Missing projects retain usage exit 3; missing/unreadable
   manifests and mismatches refuse with exit 2. Collect never establishes a new baseline.

4. **Contract shell spellings — option A: provisional ruling, to be confirmed by the owner.**
   Attributed to the owner. Wrapper command lines in `gars/**/CONTEXT.md` use literal
   registered `_system/wrappers/...` paths. Only those command spellings change in the
   contracts. No substitution mechanism is introduced. Contract lint and the literal-path
   registry coverage test must pass.

5. **Missing cancel — option A: provisional ruling, to be confirmed by the owner.**
   Attributed to the owner. The registry retains `executor.cancel` as unavailable until
   **row 12** supplies the verb. Authorization returns that declared reason for every role,
   before a role decision could obscure it. No cancellation implementation is added.

## What this does not close

- **NOT met: R-093 separate OS user.** A guard-protected, mode-0700 store does not isolate
  two processes owned by the same OS user. Such an unguarded agent process can access that
  user's store, change its contents/permissions, or launch the human CLI with the same UID.
  UID identity proves the operating-system principal, not that a person clicked approve.
  The tests exercise guarded access and workspace-sidecar forgery after a hook bypass;
  they do not prove same-user isolation. Deployment needs the separate-OS-user half already
  recorded as NOT met; trusted approval/verification access across that boundary remains
  deployment work. This implementation does not claim it exists.
- **NOT met: injection resistance 20/20 with a positive control.** Synthetic inputs are not
  an agent-scored run. The five deterministic attack classes are a separate measurement.
- **NOT met: external-harness R-099 loading enforcement**, global-resource inventory and
  pre-hook loading; workspace pins remain unreviewed until an independent review.
- The unchanged `gars/03_custom_analysis/CONTEXT.md:58` definition still describes the
  legacy sidecar and dialogue-triggered agent approval. This round authorizes only wrapper
  command spelling changes in contracts, so that prose is not rewritten. The protected
  store/human CLI behavior above is authoritative; a later contract-prose correction is
  still needed. A successful contract lint checks structure/vocabulary, not this semantic drift.
- Actual Python 3.6.8 execution and live Slurm/Nextflow validation remain unmeasured.
- The 24-hour window can expire before a long queued analysis reaches verify. No implicit
  renewal is introduced; the owner can reverse the provisional lifetime policy.
- No row-15 hooks/gitleaks/secret-containment work, lifecycle writer, merge, push or remote
  operation. The standing merge-after-study condition remains. No producer exit claim
  substitutes for the named tests' results in the appended change report.

## Owner rulings needed

No unanswered implementation choice remains for this round. The owner still must confirm
or reverse each of the five provisional rulings above; no independent review is asserted.

_Renumbered at merge, 2026-09-22: this record was written as 0054 on its branch and takes 0059 on main, because the row-5 fix and rows 15, 4, 11 and 12 numbered their decisions independently (merge order: row-5 fix, 15, 4, 11, 12). Its number, link targets and the numbers of other rows' records it cites are the only edits; branch-time number notes are left as written._
