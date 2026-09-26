---
date: 2026-09-26
status: standing
kind: decision
touches:
  - evals/mutants.md
  - evals/mutation-runs/
  - README.md
  - docs/decisions/0088-row-3-second-seal-preregistration.md
symptoms:
  - row 3's second sealed run needs its result recorded exactly as graded
---
# Row 3's second sealed mutation run: 10/10 killed at `8744978`, recorded as graded

The result of the run [0088](0088-row-3-second-seal-preregistration.md) pre-registered, recorded as graded.
**Read it as development evidence from one concentrated draw.**
By killing test, seven of the ten mutants were caught first by the parameter-mapping tests, so, as inferred from those tests (the sealer's class notes were unread), failure-path recovery (class 2) and data-keyed lookups (class 4) are barely sampled.
The binomial 95 % interval for 10/10 is roughly 0.69-1.0, and the README's evidence cells stay `unmeasured`.
Row 3's first run, [0086](0086-row-3-first-sealed-run.md) (5/10 killed at `2a65dbf`), stands as graded and is retained; the two runs are separate seals and are never averaged.
Paths below use 0088's placeholders.

## Context

**Order of events, 26 Sep 2026 (UTC unless stated; the private repository's times are GitHub's own push records).**

- 25 Sep, 18:25:08Z: anchor 0 pushed (aegis `8c2ca40`): 0110's runner change committed on public main `e589ce8` as `2a81999`, before any follow-up build step or seal existed.
- 25 Sep, 23:13Z: the follow-up's final head `H` = `874497829818840f81fd68490e1d65135c395d43` reviewed (APPROVE, narrow verification, review 5); frozen after CP3's gate.
- 05:41:17-05:48:16Z: the second seal written by a fresh Codex context in mode O (0088).
- 05:54:13Z: anchor A pushed (aegis `9be2575`): the seal's fingerprint and hashes.
- 05:55:43Z: 0088 committed (`d63826e`, local clock).
- 05:56:15Z: anchor B pushed (aegis `907e8d2`): 0088's commit and hash.
- 06:08:12-06:08:29Z: the census on Node 1: 50/50 (rule 1); THE run commit is `H` (rule 2).
- 06:08:29-06:52:53Z: the timing gate (rule 3): five clean runs, slowest 535.5 s against the 1080 s gate, none re-timed.
- 06:52:53-08:30:09Z: THE run (rule 6).

The local machine clocks are self-asserted; the binding below does not depend on them.

**What the binding cannot show.**
The anchors prove the seal and the rules existed in the stated form before the census; they cannot prove that no other copy of the seal was read, or that a hidden attempt was not made and discarded; an `external_human_seal` is the answer to that, not more records.

## Decision

**The measured result, as graded.**
The runner printed `10/10 killed/total` and exited 0 (`run.exit`); every one of the ten mutants was killed, none survived and none was `ineffective`.
The first failing test per mutant, from the runner's own rows: M01-M04, M06 and M07 by `test_r164_params_mapping.NfcoreBuildParamsTests.test_{atacseq,chipseq,cutandrun,methylseq,scrnaseq,spatialvi}_every_field`; M05 by `test_r164_params_mapping.NfcoreBuildParamsTests.test_rnaseq_indices_are_not_exchanged`; M08 by `test_r164_failure_recovery.FailureRecoveryTests.test_params_yaml_interrupted_mid_write_keeps_previous`; M09 by `__main__.ExecutorSeamTests.test_00_slurm_default_is_byte_identical`; M10 by `test_hooks_records.RecordHookTests.test_production_every_ref_and_independent_gate_vetoes`.
The rows are transcribed mechanically into [the run record](../../evals/mutation-runs/2026-09-26-8744978-run-2.json) and into `evals/mutants.md`'s new `## Second seal` section; the first-run table stays byte-identical.

**Row 3 exit.**
**Met as development evidence (not a public pass)**: 10/10 killed with all ten mutants effective, and the runner's baseline prints `wrapper contracts: 7/7 found/expected nf-core; 10 total wrappers`.
The public claim stays unmeasured and needs an `external_human_seal`; the first run's 5/10 at `2a65dbf` stands beside it, and the two are never averaged.

**How to read 10/10: the draw is concentrated, and it is one small draw.**
By killing test: seven of the ten mutants were caught first by the parameter-mapping tests (`test_r164_params_mapping`, the wrappers' params builders), one by a failure-recovery test (the params file's interrupted write), one by the executor seam and one by the records hook.
A mutant's first failing test does not fix its fault class, so the class spread here is inferred, not known.
As inferred, this run exercises the parameter-mapping tests heavily; failure-path recovery (class 2) and data-keyed lookups (class 4) are barely sampled, class 2 by one mutant's killing test (M08), and no killing test in this run is a keyed-lookup or boundary test.
Ten mutants are one small draw: a binomial 95 % interval for 10/10 is roughly 0.69-1.0, so the record states the count and does not generalise it to a kill rate.
The sealer's own mutant table (`SEAL-NOTES.md`) was unread until this record was committed, so the class spread above is inferred from the killing tests alone.

**The census (0088 rule 1).**
50/50: every mutant true on `format_valid`, `probe_before_match`, `applies`, `ast_changed` and `probe_after_match` at `H` on Node 1; the seal was written and its probes executed on macOS, and every probe reproduced exactly on Linux.
One fidelity check outside rule 1's five booleans came back false: `census-meta.json` records `archive_equals_committed_tree: false` for `H`, meaning the `git archive` tree the census probed in and the tree the runner's own `committed_tree` materialises at `H` hash differently under `tree_hash` (names, bytes and modes).
The first run's census, on macOS, recorded `true` for both its candidates; this is the first census on Linux.
The cause is unexplained: no existing file shows which entries differ, and the check was not re-run; a mode difference (tar applies the archive's modes under the account's umask, while `committed_tree` sets file modes explicitly) is a hypothesis, not a finding.
It does not touch the run: the runner tests its own `committed_tree` tree, the census's per-mutant tree checks (`fresh_tree_equals_base`, `apply_left_tree_unchanged`, `probe_tree_unchanged`) were true for every mutant, and `base_unchanged_after_census` is true.

**The timing gate (0088 rule 3).**
Passed: five sequential baseline runs of `H` on Node 1, each a fresh clone detached at `H` and checked clean, under the timing environment of 0088 rule 5: 535.5, 529.8, 530.6, 530.4 and 533.8 s, every run `collected 874` = `Ran 874`, `OK (skipped=80)`; slowest 535.5 s against the 1080 s gate; process snapshots at each run's start and end showed no listed foreign process above 10 % CPU, so none was re-timed.

**THE run (0088 rules 5 and 6).**
The preflight printed every check true (the scratch exists outside the clone; the mutants folder holds `M01`-`M10`; the clone is clean including ignored files; `git` on the `PATH`; interpreter 3.13.5; `HEAD` = the run commit).
`run-launch.sh` wrote `run.started` 06:52:53Z, ran the runner in the foreground with `RUN_ENV`, wrote its exit status 0 to `run.exit`, then `run.finished` 08:30:09Z.
The runner's baseline in its own tested tree (the repository-bearing tree of 0110) printed `Ran 874 tests`, `OK (skipped=80)`; stderr shows no `REFUSED`.

**The exit code is captured.**
`run.exit` holds the runner's own exit status, written by `run-launch.sh` (0088 rule 6), which closes 0086's derived-exit-code gap.

**The binding (0088 rule 8): holds.**
Every row's `mutant_diff_sha256` and `expected_sha256` equal the seal's per-file list (20/20); `run_sha` is `H` on every row and in `baseline.json`; the fingerprint, re-derived on the sealing machine and on Node 1 by the seal's own procedure, equals `SEAL.md` line 1 (`f88962326810558b5248ffec1d8e127da3182d76dc016867ef5dbe16c8c7958e`).

**Environment and skips.**
Node 1 (Linux), `/usr/bin/python3` 3.13.5, git 2.47.3; the environment exactly as 0088 rule 5 states (`run_env.sh` SHA-256 `d54b7cdd781ef9a965d0343662b1388b30376910daf1eaf7b624855f1816e3ea`).
The runner's baseline reports 80 environment skips, each listed with its reason in the run record.
The measured reasons: 62 skip because `GARS_ROW5_SCRATCH` is unset (the claims-database tests among them, gated on it before any container probe); the rest name absent pinned pipeline checkouts or modules this interpreter lacks.
`GARS_TEST_NO_CONTAINER=1` is set, as rule 5 states, but no skip in this baseline reaches it.

**Evidence.**
`<evidence>` holds `run.stdout` (SHA-256 `b3e345aa5b9cbcc26ded6c6a98c00dc2e9093fd5777f9bc81ab8ced172195587`, bound in the record as `run_stdout_sha256`), `run.stderr`, `run.exit`, `run.started`, `run.finished`, `run_commit.txt`, `census.json`, `census-meta.json`, the timing record and logs, `preflight.out`, `launch.txt`, `run-launch.sh` (SHA-256 `0eb485be2c08f8133d2a81f6e10f8f5a2376308ea572a7c3473828afabb70c77`, as 0088 rule 6 names it), `run.pid`, `run_env.sh`, `fingerprint.txt`, `fingerprint-perfile.txt`, `census.out`, `cp6-cp7.out`, `timing.out`, `binding.json`, `interpreter.json`, the process snapshots, and the runner's logs folder, moved there unopened after the run; `evidence-manifest.sha256` (93 files) has SHA-256 `fab9fa3c478db37d67b59fd392ce63cade404540b4a03b5152db0365cade9994`, recorded in the run record.

**Where the result goes: the owner's ruling 1.**
The owner, 23 Sep 2026, chose the option "Fresh model now" for the sealer, and the brief written in his window from his answers records the ruling, quoted exactly:

> 1. **Sealer:** "Fresh model now" — `independent_context` seals are enough for now; public README cells stay `unmeasured` plus one development-evidence pointer (the row 9 R9-G pattern); a human re-seal later is a separate run.

So the result is published exactly as graded, as development evidence: the README's evidence cells stay `unmeasured`, and its one row 3 pointer names this run's record and says the first run is retained.

## Known-survivor regression check (development evidence, not a sealed-run score)

The first seal's five survivors were re-planted at `H` and each run through the whole suite on Node 1 (CP3.3; M07's diff no longer applied and was re-planted by hand to the same behaviour): all five were killed (M03 by `RnaseqGarsWrapperTests.test_04_de_prepare_and_collect`; M05 by `test_r164_failure_recovery…test_finalize_interrupted_keeps_each_previous_file`; M07 by `test_r164_params_mapping…test_rnaseq_indices_are_not_exchanged`; M08 by `test_r164_keyed_lookups…test_scrnaseq_preflight_judges_protocol_against_its_own_aligner`; M10 by `test_r164_boundaries…test_spot_count_boundary (n_obs=0)`).
The follow-up's tests were written against those five, so this answers only whether they are now caught; it is not a score and never appears in `evals/mutation-runs/` or the `mutants.md` tables.
The blind development rehearsal (0088 Context: ten plants by a separate fresh Claude context, THE runner at `H` on Node 1) printed `10/10 killed/total`; it too is development evidence only.

## Gaps between the seal and the interface

None of the first seal's four gaps (0086) recurs:
(a) the source SHA was supplied to the sealer (`SEAL.md` line 10 names `H`);
(b) the probe observations were executed by the sealer on the source export, and the census re-ran every probe at `H` on Node 1 (50/50);
(c) the environment and skips come from the runner's own `baseline.json`, as before;
(d) the sealer did not fill `mutants.md`: the coordinator's transcriber filled it mechanically from the runner's stdout, and `mutants.md` says so.

## Deviations, named

- **The producer was a headless Claude Code session (Opus 5.5), not Codex**, by the coordinator's ruling under the owner's standing delegation (the Mac's Codex account was at its limit; the second account was kept for seals); 0087 names the same-model cost with the reviewers and the sealer's different family.
- **The runner change is wider than the plan's cap-only path B.**
  At `a779084` the runner's own baseline was red (its tested tree carried no repository), so [0110](0110-row-3-mutation-runner-suite-cap-approval.md) approved a repository-bearing tested tree, a commit of each applied mutant, and a whole-suite cap of 1800 s (gate 1080 s) instead of the plan's 900/540 s; all of it anchored before any follow-up build step.
- **The host moved to Node 1** for the timings, the evidence suites, the rehearsal, the census, the gate and THE run (0088 states why); the sealer and the producer stayed on the Mac.
- **Rounds beyond the plan's single extra fix cycle:** round 4 (the extra cycle, class 2 by principle), rulings rounds 5 and 7 (non-atomic writers recorded as class-2 residuals), and round 6 (a bounded round ruled by the coordinator, then a narrow verification review); record [0111](0111-row-3-followup-suite-index-addendum.md) indexes modules added after 0087's first round.
- **The blindness scanner was hardened on the follow-up's own sessions** (versions 2 to 7b, each a false-hit shape fixed and kept as a clean case beside planted escapes); the lane's verdict reader was made fail-closed after a review's table-form findings read as none.
- **The seal ran in mode O**, because Codex's own sandbox could not run inside the read-denial profile; the model-driven nesting check used an honest task only, never an attempted forbidden read.
- **The seal launcher's own sandbox-log extraction used the wrong window** (UTC stamps where `log show` reads local time); the log was re-extracted for the correct local window by hand, and the launcher is fixed.
- **Public main moved before the build** (lane pg landed, `e589ce8`); the runner commit was re-made on it, and the base timings of 0110 were taken at `a779084`, before that landing (no runner or test-runner file differs).

## What this does not close

- **Public credibility.**
  An `independent_context` seal is a development seal; public claims need `external_human_seal` evidence (§21 Q9), and the README cells stay `unmeasured`.
- **The Definition-of-Done cell** stays `unmeasured` (no mutants reader yet).
- **Ten mutants are one small draw.**
  The count, 10/10, is stated and not generalised.
  By killing test the draw is concentrated (seven of ten caught first by the parameter-mapping tests), so, as inferred, classes 2 and 4 are barely sampled (see Decision).
- **Model family and correlation**, the **mode O** network residual, the threat model's residuals, and the **named class-2 residuals** stand as 0088 states them.
- **R-166 Linux integration.**
  A Linux run of the offline suite is not the Linux integration runner.
- **The first run stays THE first result.**
  5/10 at `2a65dbf` (0086) is never re-graded or replaced; this is a separately sealed run of a changed suite.

## Test

This record changes no code.
With it placed and `bash docs/decisions/build_index.sh` re-run, `python3 tests/test_decision_links_resolve.py` passes.
The transcriber is not in the repository: it is `<builds>/gars-row-3-followup-evidence/transcribe.py` (SHA-256 `9743a47d0ce7ac478b8024ec2da60ed1552d0423a74761f014238c239a22069e`), and it reads `run.stdout`, `run.stderr`, `run.exit`, `binding.json`, `census.json`, the timing record, `interpreter.json` and `baseline.json`.
The `mutants.md` checker beside it is `<builds>/gars-row-3-followup-evidence/check_mutants_md.py` (SHA-256 `2d8dc48524df8d79334d4b9360d2311b010bfebb443586e8d974c78e4c8ede5e`).
Neither script is in the evidence manifest, which was sealed at the run's end and is not edited; they are bound only by the two hashes stated here.
Each check below reproduces a part of the record from its inputs and can fail:

- The record parses: `python3 -c "import json;json.load(open('evals/mutation-runs/2026-09-26-8744978-run-2.json'))"`.
- The score and exit: `tail -1 <evidence>/run.stdout` prints `10/10 killed/total`; `cat <evidence>/run.exit` prints `0`; `grep -c REFUSED <evidence>/run.stderr` prints `0`.
- The binding: each row's two hashes against `SEAL.md`'s payload list, `python3 -c "import json,re;t=open('<seal>/SEAL.md').read();s=dict((p,h) for h,p in re.findall(r'^([0-9a-f]{64})  (mutants/\S+)$',t,re.M));r=[json.loads(l) for l in open('<evidence>/run.stdout') if l[0]=='{'];print(sum((s['mutants/%s/expected.json'%x['id']]==x['expected_sha256'])+(s['mutants/%s/mutant.diff'%x['id']]==x['mutant_diff_sha256']) for x in r), set(x['run_sha'] for x in r))"` prints `20 {'874497829818840f81fd68490e1d65135c395d43'}`.
- The census, 0088's read command in `<evidence>`: prints `[10, 10, 10, 10, 10]` for `H`.
- The timing gate: `python3 -c "import json,glob;t=json.load(open(glob.glob('<evidence>/timing/timing-*.json')[0]));print(t['slowest_s']<=1080, t['all_green'], t['retimes'], t['gate_pass'])"` prints `True True 0 True`.
- `mutants.md`: the first section is byte-identical to `2781ec6`'s except line 3, and the second table equals the run record (`python3 <builds>/gars-row-3-followup-evidence/check_mutants_md.py --repo . --record-2 evals/mutation-runs/2026-09-26-8744978-run-2.json`, run at the repository root, prints `ALL PASS`).
- The evidence: `shasum -a 256 <evidence>/evidence-manifest.sha256` prints `fab9fa3c478db37d67b59fd392ce63cade404540b4a03b5152db0365cade9994`, and `shasum -a 256 -c evidence-manifest.sha256` run in `<evidence>` reports every file `OK`.

## Status

standing

## Date

2026-09-26
