---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/.claude/settings.json
  - gars/_references/config_schema.md
  - gars/_references/contract_standard.md
  - gars/_references/tool_pins.json
  - gars/_system/authoring/SKILL.md
  - gars/_system/authoring/create_bioinformatics_skill.py
  - gars/_system/codex_hook.py
  - gars/_system/configure.py
  - gars/_system/executorlib.py
  - gars/_system/guard_hook.py
  - gars/_system/resolve_artifact.py
  - gars/_system/session_state.sh
  - gars/_system/stage00_register.py
  - gars/_system/stage01_samplesheet.py
  - gars/_system/stage03_analysis.py
  - gars/_system/workspace.py
  - gars/_system/wrappers/nfcore-atacseq-wrapper/SKILL.md
  - gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py
  - gars/_system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py
  - gars/_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py
  - gars/_system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py
  - gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py
  - gars/_system/wrappers/nfcore-scrnaseq-wrapper/SKILL.md
  - gars/_system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py
  - gars/_system/wrappers/nfcore-spatialvi-wrapper/SKILL.md
  - gars/_system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/_system/wrappers/scrna-qc-cluster/SKILL.md
  - gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py
  - gars/_system/wrappers/spatial-cluster-count/SKILL.md
  - gars/_system/wrappers/spatial-cluster-count/spatial_cluster_count.py
symptoms:
  - GARS fixes 1-9 of lane gars-t74 (0297-0311) have no landing approval record
  - GARS fixes 1-9 and the four commits applied at their landing change files under the protected prefixes gars/_system/, gars/_references/ and gars/.claude/ with no owner-approval record
---
# Lane gars-t74 GARS fixes 1-9: approval of their landing and their protected change

Approval of the landing of [0297](0297-stage-00-link-gate-closes-on-one-fixed-word.md), [0298](0298-stage-01-exit-table-a-clean-check-is-not-the-end.md), [0299](0299-stage-01-gates-fixed-words-bound-to-the-check.md), [0300](0300-stage-01-check-record-single-use-in-its-folder.md), [0301](0301-router-offers-the-single-cell-chemistry-menu.md), [0302](0302-config-write-equals-the-dry-run-shown.md), [0303](0303-the-model-comes-from-the-harness.md), [0304](0304-the-fold-closes-the-authoring-road-and-a-kept-dry-run.md), [0305](0305-downstream-input-and-supplier-from-the-resolver.md), [0306](0306-stage03-scripts-are-approved-with-the-plan.md), [0307](0307-stage03-runs-the-plans-scripts-in-order.md), [0308](0308-fold-of-review-85a1b4a.md), [0309](0309-fold-of-review-8f5ae09.md), [0310](0310-fold-of-review-de77fe0.md) and [0311](0311-fold-of-review-f3c7520.md), which stay as the lane wrote them, and of the four commits applied at the landing.
The landing changes files under protected prefixes (§9.3, R-094: `gars/_system/`, `gars/_references/` and `gars/.claude/` in `guard_hook.PROTECTED_PREFIXES`), so this record is both the landing's approval and the approval of its protected change.
Its shape follows [0292](0292-ms21-landing-a-approval.md) and [0296](0296-ms21-landing-c-0295-approval-of-protected-change.md).

Two things approve it, and they are kept apart here:

- **The coordinating session, on the lane and the landing commits as reviewed.** The owner delegated approval of protected changes on 23 September 2026, and since 6 October 2026 every non-money build decision is the lane coordinator's, reported to him after; the lane was built and reviewed under that delegation, and its rulings are glitch-b5's, the lane's coordinating session, as are the four landing commits: **approved by glitch-b5 under Javier's standing delegation; to land only on Javier's typed word.**
  No sentence in this record is the owner's.
- **The owner's own word, on the push.** Landing on public main waits for the owner's own typed push word; it is recorded on the line below when he gives it, and nothing else here records it.

Javier's word: "push GARS to public main now", typed in the coordinating session's window after its push card named this landing, recorded at 07:54 EDT on 18 October 2026.

## Context

Lane `gars-t74` (GARS fixes 1-9: the first nine of the fifteen step-map fixes, in the order a visitor or a design partner meets them) was built red first on its own branch from the frozen Landings A and C head `2d819179`, merged in as its build base, by Claude Code producers, and reviewed by fresh-context reviewers, each in a separate checkout, never shown a producer's transcript.
**Same-model cost.** Producers and reviewers are Claude Code sessions; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent).
The reviews were kept independent by fresh contexts, separate checkouts and no access to the producer's transcript.

The landed commits, red first, re-created onto public main `faeb99dd` from the lane's commits, each with its tree change, message, author, committer and dates kept, and named here by its re-created id (the lane's own working files under `lanes/` do not land, nor does the lane's later run, records 0312-0315):

- 1, S00-yes (0297): red `45b4cd02`, fix `fe1a8efb`; stage 00's link gate T4a closes on the one word `link`.
- 2, S01-table (0298): red `fce7816e`, fix `1a42ec62`; stage 01's exit-code table sends a clean check to steps 6-8, and only the writer's exit 0 completes the stage.
- 3, S01-yes (0299): red `1e3aeea6`, fix `39161d98` (code); red `7199731e`, fix `cdfffaed` (contract); the exclusion and overwrite switches clear a gate only against the check's record, and T7 and T5 close on `exclude` and `overwrite`.
  Fold of the run 1 review (0300): red `b27f20a3`, fix `3d551653`, record `24164919`; the stage 01 check record is single-use and lives under `01_samplesheets/`.
- 4, R-protocol (0301): red `2c52cfa8`, fix `7012e8cd`; the router offers and confirms the single-cell chemistry menu.
- 5, R-confirm (0302): red `13ecbd83`, fix `a408db07` (code), fix `815f732e` (contract); a config write equals the dry run the user was shown, and T9 closes on `write`.
- 6, G-model (0303): red `fcf3a1aa`, fix `39897f26` (code); red `7e5b4a6b`, fix `0106ab21` (contract); history and run records name the harness's model, never the agent's flag.
  Fold of the runs 2 to 4 review (0304): red `091f6880`, fix `336eb8be` (the authoring road reads the session model); red `8dd0c0d8`, fix `a0d15bc5` (a dry-run record is tied to the file it read).
- 7, D-input with D-supplier (0305): red `d2f4a313`, fix `4a0e9c40`; the two h5ad consumers resolve their own input, and every supplier line comes from the resolver.
- 8, S03-scripts (0306): red `e167e5a3`, fix `a7abe562`; approve binds every `scripts/` file, and submit and verify refuse any other.
- 9, S03-order (0307): red `c0325617`, fix `c4d8e966`; the plan orders its scripts, and approve writes the one runner that runs them in that order.
- Fold of the run 5 review (0308): red `2fe5c2b1`, fix `2e29cccc` (the runner carries the scripts' directives); red `556afcf8`, fix `38ebc25f` (the supplier line is bound to what was read); red `e8853e96`, fix `9e41c383` (conform's flag rule); residuals `93ae1fb8`.
- Fold of the run 6 review (0309): fixture `45d56a1d`; red `be08ed94`, fix `f28efe60`; red `d92489bd`, fix `d35484e0`; red `89ec35f4`, fix `1c2b970d`; record `76431d02`.
- Fold of the run 7 review (0310): red `e6783c12`, fix `ccda0a4b`; red `3e87cd60`, fix `500228bf`; red `e2014bc9`, fix `b2fd98f9`; record `f33f8edd`.
- Fold of the run 8 review (0311): red `40cdc8e2`, fixes `280776a6` and `c1a6b0dd`, witness row `aa70152d`, record `616593f6`.

The four commits applied at the landing, by glitch-b5, from the lane's patch files and its rulings, re-created after the lane's commits in the same way:

- `3af7e701`: the lane's pin-skills patch; five wrapper SKILL.md usage lines lose `--model`, the two h5ad wrappers' SKILL.md lines name the resolver and its supplier, `gars/_system/authoring/SKILL.md` names the model from `ws.history_model`, and `gars/_references/tool_pins.json` re-pins those six files.
- `baa78b23`: one `guard_hook.py` READ_ONLY line for `.gars_session_model` (0303's guard hunk).
- `a11707bd`: one `guard_hook.py` READ_ONLY line for `projects/*/_config/.*.dry_run.json` (0302's guard hunk).
- `548adad6`: the two `gars/.claude/settings.json` deny entries that mirror those two lines.

Reviews of the lane, of commit ranges on the lane's own branch, kept outside the repository and cited by the sha256 of the review file as held on the lane branch at `ddd978e7`:

- run 1 (S00-yes, S01-table, S01-yes), `a5d6786e..2f00b8f3`: CHANGES (three MINOR, four NIT), review_sha256 `62bea40ffc84f25e47d06323d2d2bf78bd467bb1dd6042b3bffd090f0787679a`; folded in run 2 as glitch-b5 ruled (0300).
- runs 2 to 4 (the fold, R-protocol, R-confirm, G-model), `2f00b8f3..9eb28d94`: CHANGES (two MINOR, four NIT), review_sha256 `73f94b0654257cd04b255f9caea957d82c17c82ff24a4b49c42505ae521c354b`; folded in run 5 as glitch-b5 ruled (0304).
- run 5 (the fold, D-input with D-supplier, S03-scripts, S03-order), `8b2e0d29..85a1b4a3`: CHANGES (one MAJOR, two MINOR, five NIT), review_sha256 `a969165e0b59017e06707559296598a397c825c37ad4a86cbd51b972559988f9`; folded in run 6 as glitch-b5 ruled (0308).
- run 6, `12dde309..8f5ae09b`: CHANGES (three MINOR, two NIT), review_sha256 `da69675a627148159896ccfc876309a2bdf891820568c0c8e1d40a8381967fa9`; folded in run 7 (0309).
- run 7, `40e1dc1a..de77fe0a`: CHANGES (two MINOR, two NIT), review_sha256 `b019015000c353caa42f4237123229475c1d948384b81b81dcf9c857b2a7843a`; folded in run 8 (0310).
- run 8, `d8791a04..f3c7520d`: CHANGES (one MINOR, one NIT), review_sha256 `78d1203b3892e564a0a8bca3eb619e97066eec4abf6557c06aa01e1d3eae19a0`; folded in run 9 (0311).
- run 9, `e168a2e1..ef55d244`: PASS (no finding, two NIT, not folded in this landing), review_sha256 `96e04780e89e7bcfdd080c82acee31dab497a39e58212cb1a440a54e8283377e`, so the loop ended at run 9.

Review of the four landing commits, `ddd978e7..b7f2754a` on the lane's landing branch (fresh context, its own worktree, never shown the producer's transcript): PASS (no finding, two NIT, not folded), review_sha256 `f7615501a0fba091a161c211e01bf252c7cdbd134a6fd05fae235e42a13a58b6`.
It checked that each of the first three commits is exactly its patch, that the settings commit adds exactly the two mirroring entries, that the two guard lines refuse the agent's Write, Edit and MultiEdit on both records while the sanctioned writers still work (and that the same probe at `ddd978e7` lets those writes through), and that nothing else changed.

## Decision

glitch-b5, under the owner's 23 September 2026 delegation as extended on 6 October 2026, approves landing on public main, as re-created at the build-branch commits named above:

1. **GARS fixes 1-9 and their folds** (0297-0311): the code, contract, reference and test changes of the lane commits listed above, as lane `gars-t74` built them and its reviews passed them.
2. **The protected change** in the 31 files this record touches, which are all of the landing's files under `gars/_system/`, `gars/_references/` and `gars/.claude/`: the lane's changes to stage 00, 01 and 03 code, `configure.py`, `workspace.py`, `resolve_artifact.py`, `executorlib.py`, `codex_hook.py`, `session_state.sh`, the authoring tool, the ten wrappers' code and `gars/_references/config_schema.md` and `contract_standard.md`; and the four landing commits' SKILL.md lines and re-pin, the two `guard_hook.py` READ_ONLY lines and the two `gars/.claude/settings.json` deny entries.
   `gars/_system/tools/registry.json`, `gars/_system/tools/policy.py` and `gars/_system/hooks/` are unchanged.

Outside the protected prefixes, recorded for completeness: the stage contracts and `gars/CLAUDE.md`, the tests and fixtures under `gars/tests/` and `tests/run_tests.py` (among them the frozen Landing C file `gars/tests/test_r164_writer_recovery.py`, changed under glitch-b5's rulings, as the lane names), `.gitignore`, the suite totals in README.md and DEVELOPMENT.md, 0297-0311, this record and the index.
The suite totals move from 1415 to 1507 tests; the skip figures do not move.

## Test

- Full suite at the lane head `ddd978e7` on a separate test machine (Linux): run `gars-t74-final-ddd978e-ddd978e-20261017T235207Z`, `PASS kind=gars commit=ddd978e7cf02 state=done rc=0 ran=1507 passed=1425 failures=0 errors=0 skipped=82`.
- Full suite at the landing branch head `b7f2754a` (the lane head with the four landing commits; outside `lanes/` its tree differs from the landing's only by what Landings A and C added on public main, this record, its index row and the suite-total sentences) on a separate test machine (Linux): run `gars-t74-landing-b7f2754-b7f2754-20261018T001913Z`, `PASS kind=gars commit=b7f2754a6a96 state=done rc=0 ran=1507 passed=1425 failures=0 errors=0 skipped=82`.
- The landing's own checks, on 17 October 2026, recorded in the landing's evidence commit, the merge's child:

Glitch verified the landing merge `7cd0a1dd01a1a2337eec9cdf34f4a9aa044db144` (first parent public main `faeb99dd`, second parent the build branch's head `334b633a`), a true merge.
The build branch is the lane's 57 commits outside `lanes/` (of the 93 non-merge commits in `2d819179..ddd978e7`; 36 touch only `lanes/` and none mixes the two), re-created in lane order with the same authors, committers, dates and messages, then the four landing commits, this record and the suite-total sentences; each re-created commit's patch equals its original's, except that in 17 of them the hunk positions and context lines of the generated index `docs/decisions/CONTEXT.md` differ.

- Full suite at the merge itself on a separate test machine (Linux): run `gars-t74-land-7cd0a1d-7cd0a1d-20261018T021548Z`, `PASS kind=gars commit=7cd0a1dd01a1 state=done rc=0 ran=1507 passed=1425 failures=0 errors=0 skipped=82`.
- At the merge: `tests/check_counts.py` is clean, `tests/check_contracts.py` has 14 contracts clean, `test_decision_links_resolve` passes (622 of 622 citations resolve), `build_refusal_corpus --check` passes and `gars/tests/test_protected_paths.py` passes; the README's skip bar (fresh-clone.yml's own gate script, run on that run's log against the merge's README) prints `ok: 82 skips, at most 124 documented` and exits 0.
- The outgoing range `faeb99dd..7cd0a1dd` (64 commits): no gitleaks finding under either ruleset (gitleaks 8.30.0, its default rules and the build machine's push rules, 63 non-merge commits); no home path, user name, private e-mail address or internal machine or project name appears in any added line or message; the identities are `Claude <noreply@anthropic.com>` (57) and the owner's GitHub noreply address (7).
- The smoke delta (row 14's ceremony), with the build Mac's exclusive booking held for it (a timed booking, which keeps heavy and other timed work off the Mac but not light work, from 22:21:21 to 22:23:50 EDT, in the machine scheduler's log): one run of three `claude-opus-5-5` sessions at the merge's tree (17 October 2026, 22:21-22:23 EDT), prompt and suite hashes equal to the previous record's (`prompt_sha256` `cf32c619…`, `suite_sha256` `ea2f1cde…`); run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20261017-ms21-ac.json`, floor `0/1` from `evals/runs/smoke/smoke-20260926-row-14-activation.json`; the evaluator found nothing (15 outputs hashed, 15 tasks regraded).
- A fresh-context review of the landing merge (Claude Code, Opus 5.5, its own clone with no remote, never shown the producer's transcript; threat model: the landing carries more than the approved lane and landing commits, a public fact is false, a private value leaks, or the merge has the wrong shape): PASS (no MAJOR, one MINOR, three NIT), review_sha256 `7dc872414947fbef3d9b37bcd45fbe9b2e66839b15c61ba70327c38d0247b77c`.
  Its MINOR (README's suite-total sentence named the landings "since" the Gap Study token correction but left out two that did not move the total) and its NIT on this record's wording are folded in this evidence commit; its NIT on the CI sentence (the run was green on a re-run of one Windows checkout job, whose first attempt failed on a runner network fault before any repository code ran) and its NIT on the re-created messages citing lane patch files are not folded.
- `python3 gars/_system/hooks/audit_trailers.py`, from the landing worktree's root at this records commit: `verified 7cd0a1dd01a1a2337eec9cdf34f4a9aa044db144 (Bench previous: evals/runs/smoke/smoke-20261017-ms21-ac.json)` and `trailers audit: 17/17 _system first-parent commits since activation f3abe50 verified; graded 17 of 17 seen`, exit 0 (re-run after each amendment of this commit, with the same output).

## Status

Standing. Approval of GARS fixes 1-9's landing and of its protected change; the owner's typed push word is recorded above.

## Date

2026-10-17
