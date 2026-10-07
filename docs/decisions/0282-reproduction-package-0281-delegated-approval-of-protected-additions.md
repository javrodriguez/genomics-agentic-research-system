---
date: 2026-10-06
status: standing
kind: decision
touches:
  - gars/_system/claims/package_run.py
  - gars/_system/claims/package/verify.py
  - gars/_system/claims/package/compare.py
  - gars/_system/claims/package/rerun.sh
  - .gitignore
  - .github/workflows/reproduction-yeast-atac.yml
symptoms:
  - the reproduction package (0281) adds four files under the protected prefix gars/_system/ and one under .github/ with no owner-approval record
---
# The reproduction package 0281: approval of its protected additions

Addendum to [0281](0281-reproduction-package-harvest-and-render.md), which describes the design.
The five files this record approves are under protected paths (§9.3, R-094: `gars/_system/` in `guard_hook.PROTECTED_PREFIXES`, and the repository's `.github/`), so the additions need an owner-approval record.
Its shape follows [0277](0277-methods-journal-paragraph-0276-approval-of-protected-change.md).

Two things approve it, and they are kept apart here:

- **The owner's own words, on the plan.** On 5 October 2026 Javier typed "A1 B1 C2" and "gars-repro yes".
  A1 approves the reproduction package plan as written (the plan is the owner's private working document and is not published), which names these additions; B1 and C2 are its two other decisions.
  Those words reached this record relayed by the coordinating session; this record was not written where he typed them.
- **Glitch, on the code as built, under the owner's delegation.** The owner delegated approval of protected changes on 23 September 2026, so the approval of the five files as built is written by Glitch under that delegation and labelled as such: **approved by Glitch under Javier's 23 Sep delegation**.
  No sentence in this record is the owner's except the quoted words.

**Not given yet: the public push.** Landing these additions on public main waits for the owner's own typed push word, which also stands as his approval of the result line and the package's sentence frames; nothing here records it.

## Context

0281 was built on the branch `lane/repro-package` from public main `d6963f7`, with public main `0f602ea0` (the Methods journal paragraph, 0276 and 0277) merged in as `e2cf18dc`, by Claude Code producers (Opus 5.5) in the build branch's own working copy, and reviewed by fresh Claude Code contexts (Opus 5.5) in separate checkouts with no remote, never shown a producer's transcript.
**Same-model cost.** The producers and the reviewers are the same model; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent).
The reviews were kept independent by fresh contexts, separate checkouts, a stated threat model and no access to the producer's transcript.

**The harvest reviews** (5 October 2026, threat model: a package built from a run's records claims more than the records attest, or carries a private value), each finding reproduced before it was fixed: r1 CHANGES (3 MAJOR), folded in `3a96c3fe`; r2 CHANGES (3 MAJOR), folded in `f384850a`; r3 CHANGES (1 MAJOR), folded in `cf610146`, the last round under the cap.

**The hash-oracle reviews** (6 October 2026, threat model in the coordinating session's words: the bucket name, the account id, or any hash that could reveal either must never leave in a package), of a change an earlier session of the builders had left uncommitted; it was adopted only after these rounds:
The review_sha256 values below are hashes of the owner's held evidence, published now so the files can be checked when they are released.
`r1` CHANGES (2 MAJOR, 2 MINOR), review_sha256 `8462c13af5056c2b931c8ebe565ebece840f43d09c9f14a9f183102a762f0de3`: a directory output's tree hash bound a withheld member; a bucket inside a compressed `presence` member was invisible to a byte search.
`r2` CHANGES (1 MAJOR, 6 MINOR), review_sha256 `e05cae8a1a0ddfe44b3957d9cf0a61a74674c1250ea462032b942d353790f3db`: a member over 5 MB that harvest did not read had its sha256 printed (older than the change).
`r3` PASS (no MAJOR, 5 MINOR), review_sha256 `264286e1d575bacfc748aef147043f0e97a9126a69d0a239c22a8f745711442d`, so the loop ended at round 3; its MINORs are pre-existing gaps none shown on real inputs, named in 0281 "What this does not close".
Every MAJOR, and every MINOR that tightened a check, is folded in `70983396`, with the bare-bucket rule pinned in `c614a39e`.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected additions as built at the build-branch commit that lands them (four under `gars/_system/`, one under `.github/`):

1. **`gars/_system/claims/package_run.py`** (new): the `harvest`, `render` and `rerun-note` verbs of 0281; standard library only, no model; `render` opens only the harvest, named files at the recorded GARS commit by `git show`, and the exemplar's own files beside the package; `harvest` reads GARS's own checks read-only.
2. **`gars/_system/claims/package/verify.py`**, **`compare.py`** and **`rerun.sh`** (new): the templates copied into every package; `verify.py` and `compare.py` are standard library and offline; `rerun.sh` downloads only the pinned inputs and runs only the pinned pipeline.

3. **`.github/workflows/reproduction-yeast-atac.yml`** (new, under the protected `.github/`): on manual dispatch and monthly, never per push, it runs the package's offline `verify.py` and shellcheck, then the package's own `rerun.sh` and `verify.py --against` on a GitHub-hosted runner after freeing disk, passes only when the result line equals the landing README's, no output holds a file the run did not record, and every member's mode and result equals `agreed-members.tsv` (a finding's members may match or differ, never go missing), and uploads the pass artifact; read-only permissions, no secret. It has not run anywhere yet: its first run is the post-landing dispatch, on the owner's word.

None of the five is a typed tool the agent can call, and none edits a GARS record.
Outside the protected prefix, recorded for completeness: `.gitignore` gains `.gars-approvals/` (review H10, so a project's approval store is never committed), and the build branch adds `gars/tests/test_package_run.py`, its golden packages, `scripts/repro_exemplar_run.py`, `scripts/repro_s2b_probe.py` and their tests, the exemplar and its own files beside the package under `reproduction/yeast-atac/`, 0281, 0283 and this record.
`scripts/rerun_check.py`, `_references/tolerances.yaml`, `executorlib.py` and the wrapper templates are untouched.

## Test

- Full suite on a separate test machine at every build-branch commit that changed these files, each verdict derived on the build machine; the latest, on the landing merge itself, is recorded in the landing's evidence commit.
- Mutation, on byte backups restored and sha-verified: the 5 October runs (84 mutants, all killed, named in 0281) and the 6 October hash-oracle runs (21 of 21 killed), named in 0281.
- The landing's own checks, on 7 October 2026, each on a byte backup restored and sha-verified: `rerun-note`'s result-line binding (3 of 3 mutants killed); the exemplar's binding test, driven on doctored agreed tables (two results swapped inside one output; a finding's member agreed as missing), each failing it while the committed table passes; the workflow's member step, driven on seven cases, each as designed.

Glitch verified the landing merge `db146434ab3d202576c93ad6e6cbc1016a05d11f` (first parent public main `a626cdc2`, second parent the build branch's head `1638a86a`), a true merge.
The branch's commits up to the render commit `f1dc0931` are kept as built; the seven after it were re-created before landing with the same trees, authors, committers and dates, six of them with reworded messages.

- The combination: public main had moved past the branch's base by two record commits (0287 and 0288), which share no file with the branch but the generated `docs/decisions/CONTEXT.md`, rebuilt by `build_index.sh`; `tests/check_counts.py` clean (1403 tests), `tests/check_contracts.py` 14 contracts clean, `scripts/release_check.py --check` 13 of 13 byte-stable.
- Full suite at the merge on a separate test machine (Linux), sent as a bundle after a gitleaks scan of the commits the public remote does not yet serve: run `land-repro6-db14643-20261007T055537Z`, verdict derived on the build machine: `PASS kind=gars commit=db146434ab3d state=done rc=0 ran=1403 passed=1321 failures=0 errors=0 skipped=82`.
- The outgoing range `a626cdc2..db146434` (33 commits: the branch's 32, two of them merges, and the landing merge): no gitleaks finding under either ruleset (gitleaks 8.30.0, 30 non-merge commits); the run's bucket, the AWS account id (plain and dashed), the run's workspace path, and the owner's user name and e-mail appear in no file version, commit message or identity in it (252 file versions read).
- The smoke delta (row 14's ceremony), with the build Mac booked exclusively for it: one run of three `claude-opus-5-5` sessions at the merge's tree (7 October 2026, 02:55-02:57 EDT, booking `repro-smoke`), prompt and suite hashes equal to the previous record's (`prompt_sha256` `cf32c619…`, `suite_sha256` `ea2f1cde…`); run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20261005-methods-prose.json` (the nearest earlier checked first-parent Bench, `1a6e4a77`), floor `evals/runs/smoke/smoke-20260926-row-14-activation.json` (`0/1`); an ordinary record; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20261007-repro-package.json`).
- Fresh-context reviews of the landing (Claude Code, Opus 5.5, each in its own checkout with no remote, never shown the producer's transcript; threat model: a check passes a wrong re-run or doctored input, a public text says more than its evidence or keeps an internal reference, or a private value leaks); each review_sha256 is a hash of the owner's held evidence, as labelled above:
  - round 1, on the first landing merge: CHANGES (3 MAJOR, 10 MINOR), review_sha256 `d7a4868fbb6e126e16f98846642b5f14c4afa8b25ff6c34cfce181a1f3b2f19c`; every MAJOR and each check-loosening MINOR folded;
  - round 2, on the second: PASS (no MAJOR, 7 MINOR), review_sha256 `9eea6db94f9b25c4b36d459d9bc947853427d8a9b37d8bb58476739af2ae8ffe`; its two check-loosening MINORs folded, and three false or stale sentences fixed beyond the stop rule (a named departure);
  - one-round checks of each fold, until one found no MAJOR: CHANGES (1 MAJOR), review_sha256 `74bbc4116312a17724315540e0a76d48c76def300fd384d840386cb04d837a03`; CHANGES (1 MAJOR), review_sha256 `541e98b6a030b3f185f95ef2761356e61d22e96b2af7aef06b730f1aaa62466d`; CHANGES (1 MAJOR, on the merge message), review_sha256 `6de52c3aa6249c044ccc5cdca9ac7129e4a8c3e3c4c372386eb932009144170d`; PASS (no MAJOR, one MINOR on the merge message's wording, not folded: it loosens no check), review_sha256 `823310ea1534dd1de6410848877168c20ca526b04eb417ea3e38d0fc71a8b704`.
- `python3 gars/_system/hooks/audit_trailers.py`, from the landing worktree's root at this records commit: `verified db146434ab3d202576c93ad6e6cbc1016a05d11f (Bench previous: evals/runs/smoke/smoke-20261005-methods-prose.json)` and `trailers audit: 15/15 _system first-parent commits since activation f3abe50 verified; graded 15 of 15 seen`, exit 0 (run on this commit before its last amendment, which added only this line, and again after it).

## Status

Standing. Approval of the reproduction package's protected additions only; the public push is not approved here.

## Date

2026-10-06
