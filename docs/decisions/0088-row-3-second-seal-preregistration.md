---
date: 2026-09-26
status: standing
kind: decision
touches:
  - evals/mutate.py
  - evals/mutants.md
  - evals/MUTANTS-INTERFACE.md
  - evals/mutation-runs/
  - docs/decisions/0086-row-3-first-sealed-run.md
  - docs/decisions/0087-row-3-followup-suite-strengthening.md
symptoms:
  - row 3's first sealed run killed 5/10; a strengthened suite needs a separately sealed second run
  - the first seal is spent, so a new seal must be written blind to the new tests and to the first seal
---
# Row 3's second sealed mutation run: the rules, fixed before any census

Pre-registration for the second sealed run of row 3 (§18: "≥ 8/10 mutants killed; 7/7 wrapper contracts"), in the shape of [0085](0085-row-3-first-run-preregistration.md).
This record is committed and anchored outside this repository before any census, timing gate or run touches the second seal, so no rule below can follow a result.
The result will be decision 0089.
Paths below use placeholders: `<home>` (the run node owner's home folder), `<evidence>` (`<home>/evidence/row3fu-run2`), `<scratch>` (`<evidence>/scratch`), `<seal>` (`<evidence>/seal2`), `<kit>` (the sealer's kit on the sealing machine) and `<builds>` (the build folder on the sealing machine).

## Context

**The first run stands.** [0086](0086-row-3-first-sealed-run.md) recorded 5/10 killed at `2a65dbf` under the runner then shipped; that result is never re-graded, re-run or replaced.
0086 stands as graded under the 300 s cap; the new cap is never applied to seal 1, and 0086's result is never re-read under it.

**The first seal is spent.** Its five survivors (M03, M05, M07, M08, M10) were published with 0086, and the follow-up's tests were written against them, so any figure the first seal produced now would carry no information about the suite: the interface forbids re-using it ("retain the first score at the original run SHA. A later set is a separate sealed run, not a replacement of its first result.", `evals/MUTANTS-INTERFACE.md`); 0085 rule 7 forbids a re-run to improve a score; and at current main its probes and diffs no longer match (0086's census).
Whether the new tests kill those five is answered as development evidence only (0087's "Known-survivor regression check"; CP3 re-planted each through the whole suite at `H`: all five killed through the whole suite on Node 1 (M03 by `RnaseqGarsWrapperTests.test_04_de_prepare_and_collect`, M05 by `test_r164_failure_recovery…test_finalize_interrupted_keeps_each_previous_file`, M07 re-planted by hand by `test_r164_params_mapping…test_rnaseq_indices_are_not_exchanged`, M08 by `test_r164_keyed_lookups…test_scrnaseq_preflight_judges_protocol_against_its_own_aligner`, M10 by `test_r164_boundaries…test_spot_count_boundary (n_obs=0)`)), never as a sealed-run score.

**The suite under test.** [0087](0087-row-3-followup-suite-strengthening.md) and its dated addenda record the follow-up: seven test modules under `gars/tests/` (`test_r164_*`), test-only, survivor-informed and generalised by fault class; [0111](0111-row-3-followup-suite-index-addendum.md) indexes the modules added after its first round.
The follow-up's final head is `H` = `874497829818840f81fd68490e1d65135c395d43`; the suite there collects 874 tests.
The producer was a headless Claude Code session (Opus 5.5) and every reviewer a separate fresh Claude Code context on the same model; that shared model is a named cost, and a side effect is that the sealer below is of a different model family from the producer.
Named class-2 residuals, ruled by the coordinator under the owner's standing delegation (0087's addenda): five writers of recorded state are not atomic as built (two observed: the local job record and the stage-03 launcher; one observed by the directory check: stage 03 `create`'s allocated folders; two code-derived: the analysis-submissions append and stage 00 project creation), so they are untestable as built and are left to a later `gars/_system/` item; the second seal's class-2 result is read with that in mind.
Review 5's three NOTEs stand as named residuals: the stage-03 `create` row's exemption keeps that ruled defect green; one finalize test takes its expected assay names from the product's own parser; the report's label `G5b` names two different faults.

**The runner at `H`.** [0110](0110-row-3-mutation-runner-suite-cap-approval.md) (anchored before any follow-up build step) changed the runner in one coordinator commit on public main `e589ce8`: the tested tree carries its repository (history cloned from the source, `HEAD` detached at the run commit, clean), each applied mutant is committed inside the throwaway tree before the suite runs, and the whole-suite cap is 1800 s while probes and `git` keep 300 s.
At `H` the runner is byte-identical to that commit's (`evals/` is outside the follow-up's scope, and the lane's gate proved the scope diff empty at every round).

**The second seal.** A fresh Codex context sealed it on 2026-09-26, 05:41:17–05:48:16 UTC, after `H` was frozen.
`SEAL.md` line 1, the fingerprint by the seal's own procedure (`find mutants -type f | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256`), is `f88962326810558b5248ffec1d8e127da3182d76dc016867ef5dbe16c8c7958e`, re-derived by the coordinator with 20/20 per-file hashes equal to the seal's list.
`SEAL.md` line 6 records: "Sealer identity: OpenAI Codex, GPT-6, as identified by the session context."; line 9 records: "Status: sealed before scoring. Probe observations were executed on the supplied source export with /usr/local/bin/python3. No kill score or wrapper-contract score is claimed. This is a development seal, not an external human seal."; line 10 names `H` as the producer commit, which the kit supplied (not derived).
The payload is exactly ten mutants, `M01`–`M10`, twenty files.
The seal was frozen and anchored in the private repository before this record was written: aegis commit `9be2575`, pushed at 2026-09-26T05:54:13Z by GitHub's record, with the fingerprint, the hashes of `SEAL.md` and `SEAL-NOTES.md`, the input inventory's hash, the profile's hash and the configuration home's file lists.

**Independence (the design, as planned).** The sealer is a fresh Codex context, run after `H` existed, from a kit holding only the interface at `H`, a source-only export of `H` (`gars/_system/`, `gars/02_bioinformatics/`, `gars/_references/`, `gars/_templates/`: no tests, no records, no evaluation code beyond the interface), a verbatim excerpt of §16.3's R-164 paragraph and §18 row 3's line, the source SHA and its brief.
It never saw the producer's tests, the reviews, the first seal, 0086 or the survivor list.
Its configuration home was fresh (a minimal `config.toml` with history persistence off and memories off, the kit's trust entry pre-seeded, and the login file linked, never copied), so no memory, history, skill or rule from any earlier session could be injected; the home's file list before and after the run is recorded.
Blind to the old survivors on purpose: a sealer shown them would either re-create those faults (which the new tests target) or avoid them; either way the measure would be conditioned on what the producer knew.

**The threat model (every later review judges against this first).** The sealer is a cooperative model context, briefed to stay in its kit; the risk controlled is inadvertent exposure (injected memory, exploring neighbouring folders, a file a command happens to touch), not a sealer working to break out.
Controls: a fresh configuration home; a macOS Seatbelt read-denial profile (reads of file contents outside the kit, its home, its launch folder and the tool runtimes fail with "Operation not permitted"; relays through `open`, `osascript`, `launchctl`, `at`, `mdfind`, `mdls`, `pbpaste`, `ssh`, `screencapture`, `qlmanage` and the Spotlight and pasteboard services are denied); and a transcript scan with the sandbox denial log.
What they cannot bind: a deliberately adversarial sealer using an unlisted system-service relay; metadata and extended-attribute probes (`stat`, `lstat`, `getxattr`, `listxattr`), which the profile allows so paths resolve; anything known from training.
The answer to an adversarial sealer is an `external_human_seal`, not more scanning.

**The primary control and its mode.** Codex's own sandbox could not run inside the profile (mode N refused), so the sealer ran in **mode O**: Codex's sandbox off (`danger-full-access`) inside a profile that carries both the read denial and a write restriction to the kit, its home and its launch folder.
In mode O, tool-command network is not blocked by the operating system and rests on the scan.
The profile's SHA-256 is `96971913610caa15e0f2a3c43d0c3d09a5ad5f457784dc5ce3b6b51a8ecc743d`; its self-test, run by a plain shell with no model asked to attempt anything, denied every listed forbidden read inside the profile and allowed it outside, and was re-run on the real kit immediately before launch (`five forbidden reads denied inside the profile and allowed outside it, four relays refused inside and allowed outside, a read inside the kit and a python run allowed`).
Standing rule (after a safety flag on another row): no model is ever asked, in any wording, to attempt reads of protected paths or credentials to test a sandbox; the evidence for the profile is the shell self-test plus the profile's byte-identity before and after the run, and the sealer's session was an honest one.

**The secondary control, measured before the seal existed.** The transcript scan (`pathscan`) was hardened on real sessions of this follow-up's own producer and reviewers before the seal was written; each false-hit shape found (markdown link targets in written content, a search pattern read as a path, the Bash tool's folder carried across calls, a separator string in code, repository test modules run by the session, the harness's own per-project folder, a local `rsync`, a `cd` inside a command substitution) was fixed and added to a synthetic self-test as a clean call, beside planted escapes that must still hit (the final scanner finds exactly the 20 planted escapes and none of the 23 clean calls).
Rescanned with the final scanner, the follow-up's eleven producer and reviewer sessions show 0 failing hits.
The scan's result on the sealer's session: 15 calls, 0 hits; the sandbox log for the session window shows, in the sealer's process tree, only the tool runtimes' own automatic reads (a text-encoding preference file, an OpenSSL configuration, a git configuration, a login-shell profile, a security-message database) and trace-helper writes, and no denial of any forbidden path; no hit voids the seal.

**The host.** The first run was measured on macOS; this run is on the homelab's Linux node (Node 1), under its owner account with no other suite, build or model session running.
Why the host changed, measured: on macOS the full suite at `a779084` took 1468.6 s for one run, so a run of up to eleven suites would take hours of a shared machine; on Node 1 the same suite took 501.9–551.5 s (0110).
GARS targets Linux (the HPC cluster and CI); R-166 Linux integration is still not what this run is.

**Development rehearsal.** Before the seal existed, a blind development rehearsal ran THE runner at `H` on Node 1 on ten development plants written by a separate fresh Claude context (Opus 5.5) from the same source-only kit shape, inside its own read-denial profile and fresh configuration: the runner's baseline was green in its own tested tree (`Ran 874`, `OK (skipped=80)`, 7/7 wrapper contracts), every probe written on macOS reproduced exactly on Linux, and it printed `10/10 killed/total` with exit 0.
That figure is development evidence only, never a score: the plants were written by a different model family from the sealer, and a rehearsal measures the runner and the environment, not the suite.

## Decision

These rules are fixed now, before the census, and bind the coordinator.

**Rule 1 — census.** At `H` only, in a fresh `git archive` tree of `H` under `<scratch>` for every check, five booleans per mutant, each from `H`'s own `evals/mutate.py` functions:
(c) `format_valid`: the runner's pre-probe checks in `measure_one`'s order (`json.loads`, `validate_expected`, the id check, `diff_paths`, the ordinary-file and no-symlink check, `syntax`);
(a) `probe_before_match`: the unmutated probe through `H`'s `execute` equals `before` exactly and leaves the tree unchanged;
(b) `applies`: `git apply --check -` with the diff on stdin through `execute`;
(d) `ast_changed`: after a real `git apply -` in a new fresh tree, not every changed `.py` target's `syntax()` equals the unmutated one (the runner's `ineffective` rule);
(e) `probe_after_match`: the probe on that mutated tree equals `after`, differs from the unmutated observation, and leaves the tree unchanged.
The census may only hash, copy, format-check, `git apply` in a scratch tree and execute probes; it prints ids and booleans and stores every output or exception hashed.
It runs on Node 1 under the timing environment of rule 5.

**Rule 2 — THE run commit.** The run is at `H` if all 50 booleans are true; otherwise there is no run: 0089 records "second seal unrunnable as sealed" with the booleans, and the work stops with a report.
No fallback commit, no edited seal, no subset.

**Rule 3 — timing gate.** Five sequential baseline suite runs of `H` on Node 1, each in a fresh clone detached at `H` and checked clean (the tree shape 0110 approves; GARS has no `.gitattributes`), with the timing environment of rule 5 and the window held solo.
Go only if every run is green, `Ran` equals the sum of `collected`, and the slowest is at most **1080 s** (60 % of the 1800 s cap, the ratio of 0085's 180/300).
A run is re-timed (recorded, then repeated; the gate reads five clean runs) if a process snapshot at its start or end shows, from any account, a listed process (`codex`, `claude`, `node`, `docker`, `postgres`, `nextflow`, `java`, or another `python … run_tests.py`) above 10 % CPU that is not the timing process or its descendants.
More than five re-times: stop and report.
A red or over-gate result: no run, and a report; the seal stays unspent (census-exercised only).

**Rule 4 — no current-main measurement.** The seal is written against `H`'s export; public main is not measured here.

**Rule 5 — the environment (Node 1).**

```sh
/usr/bin/env -i PATH=/usr/bin:/bin HOME=<home> TMPDIR=<scratch> TEMP=<scratch> TMP=<scratch> GARS_TEST_NO_CONTAINER=1 GARS_SEALED_MUTANTS_DIR=<seal>/mutants /usr/bin/python3 -u
```

`GARS_TEST_NO_CONTAINER=1` names why the claims-database tests skip (the owner account has no container runtime); every other environment skip is reported by the baseline.
The census and timings use the same prefix without `GARS_SEALED_MUTANTS_DIR` and with `PYTHONDONTWRITEBYTECODE=1`.
The exact prefix is the file `run_env.sh` in `<evidence>`, SHA-256 `d54b7cdd781ef9a965d0343662b1388b30376910daf1eaf7b624855f1816e3ea`, anchored with this record.
The interpreter is `/usr/bin/python3` (Python 3.13.5); its version and `sys.executable` are recorded with the run.
The run clone is a fresh clone of the build history detached at `H`, its remote removed, clean including ignored files.
The seal's twenty files are copied from the sealing machine to `<seal>/mutants` byte for byte; the fingerprint is re-derived on Node 1 by the seal's own procedure before the census and must equal `SEAL.md` line 1, with 20/20 per-file hashes equal.
Preflight prints booleans only: the scratch exists and is outside the clone; the mutants folder holds exactly `M01`–`M10`; the clone is clean; `git` is on the `PATH`; the interpreter version; `HEAD` equals `H`.

**Rule 6 — the command.** Launched through `run-launch.sh` in `<evidence>` (SHA-256 `0eb485be2c08f8133d2a81f6e10f8f5a2376308ea572a7c3473828afabb70c77`), which records its own pid, writes `run.started` (UTC), runs

```sh
"${RUN_ENV[@]}" <evidence>/run-clone/evals/mutate.py --require > <evidence>/run.stdout 2> <evidence>/run.stderr
```

in the foreground, writes the runner's exit status to `run.exit`, then `run.finished`; the launcher is started with `nohup`.
The preflight output and the exact launch line are saved in `<evidence>` at the time (`preflight.out`, `launch.txt`).

**Rule 7 — first run, refusal, timeout.** The interface's words bind the run, quoted from `evals/MUTANTS-INTERFACE.md`:

> Freeze the ten diffs, metadata and their SHA-256 hashes outside the producer context, with
> the source SHA, seal type and sealer identity. Only then give the coordinator the set. Do not
> tune surviving faults after seeing producer tests; retain the first score at the original
> run SHA. A later set is a separate sealed run, not a replacement of its first result.

This is the second seal's first run and THE result: no re-run to improve a score, no survivor-directed tuning, no edited seal, no subset.
`run.exit` 0 or 1 is a score; exit 2 is a refusal, not a score: the coordinator stops, records it and its logged cause, and reports; a second attempt is a ruling, recorded as the second attempt.
A refusal printed before stderr's `mutation suite logs:` line is an operator error (no sealed byte loaded), recorded and re-issued once after preflight passes.
A mutant-induced timeout refusal is never a kill and never a survivor.

**Rule 8 — binding.** Each row's `mutant_diff_sha256` and `expected_sha256` equal the seal's per-file list (20/20); `run_sha` equals `H` on every row; the environment skips and the `wrapper contracts` line come from the runner's own `baseline.json`.

**Rule 9 — where the result goes: the owner's ruling 1.**
The owner, 23 Sep 2026, chose the option "Fresh model now" for the sealer, and the brief written in his window from his answers records the ruling, quoted exactly:

> 1. **Sealer:** "Fresh model now" — `independent_context` seals are enough for now; public README cells stay `unmeasured` plus one development-evidence pointer (the row 9 R9-G pattern); a human re-seal later is a separate run.

The result, met or not, is published exactly as graded, as development evidence; the README's evidence cells stay `unmeasured`, and its one row 3 pointer names the newest record and says the first run is retained.

**Rule 10 — where it is recorded.** `evals/mutation-runs/<date>-<H7>-run-2.json` (the folder README's `run-N` form); `evals/mutants.md` keeps its first-run table byte-identical and gains a `## Second seal` section, and its header names both results; the first-run record file is never touched.

**Blindness until 0089.** Nobody but the sealer opens, prints, greps or diffs anything under the seal's `mutants/` or its `SEAL-NOTES.md`, or the runner's `mutant-<id>.json` logs, until 0089 is committed; scripts may hash, copy, format-check, apply in a scratch tree and execute probes, printing only ids, hashes, booleans and counts.
`SEAL.md` is readable in full by design (it carries no mutant description).

**Machine quiet.** Every timed or scored step on Node 1 runs in a window the coordinator holds solo (no other account runs a suite, build or model session); process snapshots are saved at each step's start and end.

**Anchoring.** The seal was frozen and anchored (anchor A) before this record was written; this record's commit, its SHA-256, `run_env.sh`'s SHA-256, the fingerprint and `H` are committed and pushed to a private repository outside the machine (anchor B) before the census starts.

## What this does not close

- **Public credibility.** An `independent_context` seal is a development seal; public claims need `external_human_seal` evidence (§21 Q9), and the README cells stay `unmeasured`.
- **The Definition-of-Done cell** stays `unmeasured` (no mutants reader yet).
- **R-166 Linux integration.** A Linux run of the offline suite is not the Linux integration runner.
- **Ten mutants are one small draw.** A result of 8/10 has a wide uncertainty interval (a binomial 95 % interval of roughly 0.44–0.97), so the record states the count and does not generalise it to a kill rate; the first run's 5/10 is never averaged with it.
- **Model family.** The sealer is a Codex context, of a different family from the Claude producer and reviewers; the first seal was also a Codex context, so the two runs are comparable instruments. Residual correlation between any model-written seal and model-written tests is not excluded.
- **Mode O.** Tool-command network is not blocked by the operating system and rests on the scan; the scan sees the commands the sealer ran, not paths its code computes at run time (it refuses the computing shapes in executed code rather than claiming to resolve them).
- **The threat model's residuals:** an adversarial sealer using an unlisted system-service relay; metadata and extended-attribute probes; anything known from training.
- **The seal was validated on macOS and is run on Linux.** The sealer was told the run is on Linux and to keep observations platform-independent; a probe that differs on Linux makes the census fail, and the seal is then unrunnable as sealed (rule 2), not re-written.
- **Named class-2 residuals** (Context): five non-atomic writers untestable as built, and review 5's NOTEs.
- **The development rehearsal is not a score**, and the known-survivor re-plants are development evidence only.
- **The census cannot predict** a baseline timeout, a restore failure or a mutated probe that differs from `after` at run time; such a refusal is the run's result under rule 7.

## Test

- The fingerprint: `find mutants -type f | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256` from the seal folder equals `SEAL.md` line 1.
- The census read command: `python3 -c "import json;d=json.load(open('census.json'));print({k:[sum(m[f] for m in v.values()) for f in ('format_valid','probe_before_match','applies','ast_changed','probe_after_match')] for k,v in d.items()})"` prints `[10, 10, 10, 10, 10]` for `H` before any run.
- The census self-test printed each boolean false on a planted fault (a wrong `before`, a malformed `expected.json`, a non-applying diff, a comment-only diff, a wrong `after`) and all true on a good toy mutant, with `H`'s runner.
- The preflight prints a `false` on a dirty tree and all `true` on the run clone.
- The timing gate's re-time trigger was shown able to fire on synthetic process snapshots.
- `run.exit` is the runner's own status (0: ≥ 8/10 killed with ten effective; 1: below; 2: refused).
- `python3 tests/test_decision_links_resolve.py` passes after `bash docs/decisions/build_index.sh`.

## Status

standing

## Date

2026-09-26
