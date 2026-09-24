---
date: 2026-09-23
status: standing
kind: decision
touches:
  - evals/mutate.py
  - evals/mutants.md
  - evals/MUTANTS-INTERFACE.md
  - evals/mutation-runs/
  - docs/decisions/0050-row-3-test-suite-gate-and-mutants.md
symptoms:
  - row 3's independent_context seal of ten mutants was sealed on 15 Sep and never run
  - the seal names no source commit, and main has moved away from the source it was written against
  - the runner refuses the whole run when a sealed probe or diff does not match the tested commit
  - every runner command, the full suite included, is capped at 300 s and a timeout refuses the run
---
# Row 3's first sealed mutation run: the rules, fixed before any census

Pre-registration for [0050](0050-row-3-test-suite-gate-and-mutants.md)'s sealed-mutation interface; 0050 stays as written.
This record is committed before any census, timing or run touches the seal, so the choice of run commit cannot follow a result.
The result itself will be decision 0086.

## Context

Row 3 of the v1.0.1 guideline (§18) exits on "≥ 8/10 mutants killed; 7/7 wrapper contracts"; §18 defines a row's exit as its test "red at the parent commit and green at the row's commit".
Row 3 shipped its runner (`evals/mutate.py`), its interface (`evals/MUTANTS-INTERFACE.md`) and an empty record (`evals/mutants.md`, "State: **unsealed**"), and 0050 left the ten sealed mutants and the score NOT met.

**The seal.** A separate context sealed ten mutants on 15 September 2026, outside the producer context and outside this repository.
Its header records:

- line 1, the fingerprint: `b7685d96ad05e65d6904d0ff0a6a747da1a04566337e951528bb46760191227e`, produced by the seal's own procedure (`find mutants -type f | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256`, run from the seal folder);
- "Seal type: `independent_context`";
- "Sealer identity: independent Codex assistant context; model identified by the session instructions as GPT-6. No more specific backend model identifier was supplied.";
- "Status: sealed before scoring. Probe observations are static predictions, not executed measurements. No kill score or wrapper-contract score is claimed. This is a development seal, not an external human seal.";
- "Producer commit SHA: not supplied in the available handoff."

The payload is twenty files: `mutants/M01`–`M10`, each an `expected.json` and a `mutant.diff`, with one SHA-256 per file listed in the seal.
The fingerprint was re-derived on 23 September 2026 by that procedure, with the temporary-directory variables pointed at a scratch folder outside the seal, and equals line 1.

**The seal's source commit, derived from hashes.** The seal lists the 55 supplied input files it was written against, with their hashes, but no commit.
Hashing each candidate commit's blobs against that inventory gives:

| Commit | Inventory match | Differs |
|---|---|---|
| `f76492b` "Add Row 3 test suite, pre-push gate and sealed mutant interface" (15 Sep 08:38) | **55/55** | — |
| `2a65dbf` (row 3 branch final head, merged via `07cc532`) | 53/55 | `evals/MUTANTS-INTERFACE.md`, `gars/_system/hooks/install.py` (5-line change) |
| `07cc532` (merge onto main) | 50/55 | + executorlib, stage01_samplesheet, wrapperlib |
| `c41ca7c` main | 18/55 | 37 files |

The current main base is `dc6a72a`, which differs from `c41ca7c` only by decision 0071 and the regenerated decision index; its inventory count was not re-derived for this record.
The match is derived, not supplied: it proves the seal was written against `f76492b`'s bytes, not that its sealer saw a commit.

**The runner, as each candidate commit ships it.**
At `2a65dbf` (`evals/mutate.py`, 305 lines; byte-identical at `dc6a72a`):

- `REPO` is the checkout holding `mutate.py` (`:17`); `run_sha` is its `HEAD` (`:253`); the run is refused unless `git status --porcelain --untracked-files=all` is empty (`:248-251`).
- The tested tree is materialized from Git objects at `run_sha` (`committed_tree`, `:54-83`); the baseline is `tests/run_tests.py` in a copy (`:270-275`), and a red baseline refuses the run.
- Every command goes through `execute` (`:91-99`) with `timeout=300`, the full suite included (`:103`); `TimeoutExpired` is a `SubprocessError`, caught at `:299-301` as `mutation runner: REFUSED`, exit 2.
- Per mutant, the unmutated probe runs first (`:205`), must leave the tree unchanged (`:207`) and must equal `expected.json`'s `before` exactly (`:208-209`), else the whole run is refused; only then does `git apply --check -` run with the diff on stdin (`:210-212`), and a diff that does not apply also refuses the whole run, with no rows printed.
- An unchanged Python AST (`:221-224`) or an unchanged probe after mutation (`:225-229`) is `ineffective`; a mutated probe that differs from `after` refuses the run (`:230-231`).
- It never checks the seal fingerprint; each row carries `mutant_diff_sha256` and `expected_sha256` (`:190-191`), which 0086 compares with the seal's per-file list.
- It announces `mutation suite logs: <path>` on stderr (`:262-263`) after its setup checks (`:248-261`) and before the baseline suite, and writes `baseline.json` and `mutant-<id>.json` there.
- `--require` (`:285`) exits 1 unless there are ten records, none `ineffective`, and at least eight `killed` (`:297-298`); without `GARS_SEALED_MUTANTS_DIR` it prints `unmeasured` and exits 1 (`:287-290`). Neither mode edits `evals/mutants.md`.

At `f76492b` (`evals/mutate.py`, 251 lines) the runner predates the row 3 review fixes (`5502db1`) and differs materially:

- `REPO` is `:16`; the cleanliness refusal is `:199-202`; `execute` is `:58-66`, with the same `timeout=300`; the refusal handler is `:245-247`.
- It snapshots the clone's **working tree** (`copy_tree(root, snapshot)`, `:216`), not committed objects.
- Its rows carry `id`, `requirement`, `run_sha`, `status`, `test` and optional `reason` only (`:151-152`): no `snapshot_hash`, `mutant_diff_sha256`, `expected_sha256` or log paths.
- It writes no `gars-mutation-logs-*` folder and no `baseline.json`, and prints no logs-path line.
- The probe, comparison and apply check are the same code at `:163`, `:165`, `:166-167` and `:168-170`; `--require` and `GARS_SEALED_MUTANTS_DIR` behave as at `2a65dbf` (`:231`, `:233-236`, `:243-244`).

**The 300 s limit.** At plan time the row 3 era suite (151 tests) took 103–385 s and main's suite (421 tests) 94–1134 s on this machine.
The runner runs the suite up to eleven times (the baseline and each effective mutant), each under the 300 s cap, and a single timeout refuses the run.
Raising the cap is a change to evaluation code, which needs an approval record (§7.3, R-073) **before** a first run; the timing gate below exists to find out before the seal is spent.

## Decision

These rules are fixed now, before the census, and bind the coordinator and every builder.

**Rule 1 — the census.** The census may do only these things with the sealed files: hash them, copy them, run `git apply --check` with them, run the candidate runner's own format validation on them, and execute a mutant's unmutated probe; nothing else.
For each candidate commit (`2a65dbf`, `f76492b`, and the main base `dc6a72a`), a `git archive` of that commit is extracted under `<scratch>` (rule 5), a fresh tree for every mutant check so one check cannot dirty the next.
No candidate has a `.gitattributes` file, so the archive holds the same tracked blobs the `2a65dbf` runner materializes, and the same files the `f76492b` runner copies from a clean clone with no ignored or untracked files.
Per mutant:

- (a) `probe_before_match`: its `expected.json` `probe` runs unmutated, exactly as that commit's `mutate.py` `execute` runs it.
  Both runners do this identically (`2a65dbf` `:91-99`, `f76492b` `:58-66`): the child environment is the runner process's own environment plus `PYTHONDONTWRITEBYTECODE=1`, with `GARS_SEALED_MUTANTS_DIR` removed; every argument exactly equal to `{python}` is replaced by the runner's `sys.executable`; `cwd` is the tree; stdin is the probe's `stdin` encoded as UTF-8; stdout and stderr are captured and decoded as UTF-8 with `replace`; `timeout=300`.
  The census process is therefore launched with the timing prefix of rule 5, so its environment and its children's are the runner's; `{python}` becomes the interpreter's own `sys.executable`, which is recorded with the census and with the run.
  The boolean is true only if the observation `{returncode, stdout, stderr}` equals `before` exactly and the probe left the tree byte-unchanged (the runner's `assert_unchanged`, `2a65dbf` `:207`, `f76492b` `:165`).
- (b) `applies`: `git apply --check -` with the diff on stdin and `cwd` = the tree, as `2a65dbf` `:210` and `f76492b` `:168` run it.
- (c) `format_valid`: the checks that candidate's `measure_one` runs on a mutant folder before its probe, called from that candidate's own `mutate.py`, imported from its `git archive` copy under `<scratch>`, in the runner's order.
  At `2a65dbf` (`measure_one`, `:178-203`): `json.loads` of `expected.json` (`:180`); `validate_expected` (`:181`, defined `:152-175`); `expected['id'] == mutant.name` (`:182-183`); `diff_paths` on the `mutant.diff` text (`:184-185`, defined `:120-136`); then, per target path in the fresh tree, the ordinary-existing-file and no-symlink-lineage check (`:197-202`) and `syntax` on the unmutated target (`:203`, defined `:139-149`, which parses `.py` targets with `ast.parse`).
  At `f76492b` (`measure_one`, `:142-161`): the same sequence at `:144`, `:145` (`validate_expected`, defined `:116-139`), `:146-147`, `:148-149` (`diff_paths`, defined `:84-100`), `:155-160` and `:161` (`syntax`, defined `:103-113`).
  The functions are the same code in both runners; each candidate's boolean still comes from its own copy.
  True only if every check returns without an exception; any exception makes it false, and its text is stored hashed, never printed.

Output is the mutant id and the three booleans only; probe output, stderr and exception text are never printed, only their SHA-256.
Because the two runners run these checks, the probe and the apply check with the same code, each candidate's census follows its own runner and the method is the same for all three.

**Rule 2 — THE run commit.** The run is at `2a65dbf` if it is eligible, meaning all 30 booleans are true; else at `f76492b` if eligible; else there is no run, the record states "seal unrunnable as sealed" with the per-mutant booleans, and the work stops with a report to the owner.
`2a65dbf` comes first because the exit is "green at the row's commit" and it is row 3's own final commit, merged onto main, carrying the reviewed runner; `f76492b` is the source the seal was written against, with the older runner.

**Rule 3 — the timing gate.** Five baseline suite runs, sequential, from a fresh `git archive` copy of THE run commit under scratch, with the timing prefix of rule 5 and the machine reservation held.
The run goes ahead only if every run is green and the slowest is at most 180 s, because the runner runs the suite up to eleven times, each under the 300 s cap.
A red baseline means no run and a report to the owner, never a fall-back to the other commit.

**Rule 4 — current main.** Main gets the census and five timings too.
A main mutation run happens only if main is eligible under rule 1 and its five timings are green with the slowest at most 180 s; otherwise the record states "current-main score unmeasurable with the as-built runner" and names the failing condition.
It is never a subset of the mutants and never a rewritten diff; a main run is labelled "current-main measurement, not the first-run result".

**Rule 5 — the environment.** This record names the machine's folders by placeholder, each an absolute path on the run machine:
`<home>` is the owner's home folder; `<builds>` is `<home>/aegis-builds`; `<scratch>` is `<builds>/gars-row-3-exit-scratch`; `<seal>` is `<builds>/sealed-row-3`; `<evidence>` is `<builds>/gars-row-3-exit-evidence`; `<reservation>` is the machine reservation file in the owner's workspaces folder.
Every row 3 timing and run uses exactly one environment:

```sh
/usr/bin/env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=<home> TMPDIR=<scratch> TEMP=<scratch> TMP=<scratch> GARS_SEALED_MUTANTS_DIR=<seal>/mutants /usr/local/bin/python3 -u
```

The exact prefix, with every path spelled out, is the file `run_env.sh` in `<evidence>`, whose SHA-256 is `3b9a9c1dc22224cb0d7e946d70d34adeac4e6139a353af7bb352cca51d474296`; it is anchored with this record in the private repository (see Anchoring below).
The census and timings use the same prefix without `GARS_SEALED_MUTANTS_DIR` and with `PYTHONDONTWRITEBYTECODE=1`, the runner's own child setting.
The interpreter is `/usr/local/bin/python3`; its version and its own `sys.executable` are recorded with the run.
Under this prefix the interpreter itself adds `LC_CTYPE=C.UTF-8` (locale coercion) and macOS adds `__CF_USER_TEXT_ENCODING`; both are inherited identically by runner and census children.
Before the run, a preflight script prints booleans only: the scratch folder exists and is outside the clone; the mutants folder holds exactly the ten folders `M01`–`M10`; the run clone is clean including ignored files; `git` is on that `PATH`; the interpreter version; `HEAD` equals the chosen run commit.

**Rule 6 — the command.** No folder-step; `mutate.py` finds `REPO` from its own path (`2a65dbf` `:17`, `f76492b` `:16`), and both runners take `--require` and read the mutants folder from `GARS_SEALED_MUTANTS_DIR`, so the command differs between candidates only in the clone path.
At `2a65dbf`:

```sh
nohup /usr/bin/env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=<home> TMPDIR=<scratch> TEMP=<scratch> TMP=<scratch> GARS_SEALED_MUTANTS_DIR=<seal>/mutants /usr/local/bin/python3 -u <builds>/gars-row-3-run-2a65dbf/evals/mutate.py --require > <evidence>/run.stdout 2> <evidence>/run.stderr &
```

At `f76492b`, the same line with `<builds>/gars-row-3-run-f76492b/evals/mutate.py`.
A main run (rule 4), the same line with `<builds>/gars-row-3-run-main/evals/mutate.py` and output to `main-run.stdout` and `main-run.stderr` in `<evidence>`.
The launching shell records `$!` into a `.pid` file beside the output; the process is watched, and stopped only by that pid.
The clones are fresh clones of the public repository, checked out detached at the named commit, and nothing runs inside them before the run.

**Rule 7 — first run, refusal, timeout.** The interface's own words bind the run, quoted from `evals/MUTANTS-INTERFACE.md:120-123`:

> Freeze the ten diffs, metadata and their SHA-256 hashes outside the producer context, with
> the source SHA, seal type and sealer identity. Only then give the coordinator the set. Do not
> tune surviving faults after seeing producer tests; retain the first score at the original
> run SHA. A later set is a separate sealed run, not a replacement of its first result.

and from `evals/mutants.md:25-27`:

> Record `ineffective` explicitly if returned; never convert it into a kill or silently remove
> it from the denominator. A changed seal is a separate run with retained first-run evidence.
> The sealer fills this document from its own run after the producer commit.

The first run is THE result: no re-run to improve a score, no survivor-directed tuning, no edited seal, no subset.
A refused run (exit 2) is not a score: the coordinator stops, records the refusal and its logged cause, and reports to the owner; any second attempt is the owner's ruling and is recorded as the second attempt.
A mutant-induced timeout refusal is recorded as such, never as a kill and never as a survivor.
Exit 1 with `unmeasured` on stdout is not a score either: it means the mutants folder was never named.
Who fills `evals/mutants.md` is recorded in 0086: here the coordinator transcribes it mechanically from the runner's stdout, not the sealer.

**The operator-error exception.** A refusal raised before any sealed byte is loaded is an operator error, not a use of the seal: it is recorded, and the run is re-issued once after the preflight passes.
At `2a65dbf` that is a refusal printed before stderr's `mutation suite logs:` line, which follows every setup check (`:248-261`).
The `f76492b` runner prints no such line, so there the test is the refusal's reason: one of its setup refusals, raised before the baseline suite (`source checkout must be clean…` `:201-202`, an unreadable or empty mutants folder `:205-207`, `TMPDIR must name an existing scratch directory` `:209-210`, `scratch must be outside the source tree` `:211-212`), or `unmeasured` (`:233-236`).
Every other refusal at either commit, a baseline failure or timeout included, is the first run's result.

**Rule 8 — binding the run to the seal if it runs at `f76492b`.** That runner emits no per-mutant hashes and no logs folder, so the binding is:
the fingerprint is re-derived by the seal's procedure immediately before and immediately after the run, and both must equal `b7685d96ad05e65d6904d0ff0a6a747da1a04566337e951528bb46760191227e`;
`run_sha` is read from the runner's own rows (`:151-152`) and compared with the clone's `HEAD`, recorded at launch;
the environment skips and the 7/7 wrapper-contract line come from the rule 3 timing runs of the same commit in a `git archive` copy, labelled "not from the runner".
At `2a65dbf` the binding is each row's `mutant_diff_sha256` and `expected_sha256` against the seal's per-file list (20/20), `run_sha` against the chosen commit, and the skips and 7/7 line from the runner's own `baseline.json`.

**Rule 9 — where the result goes: the owner's ruling 1.**
The owner, 23 Sep 2026, chose the option "Fresh model now" for the sealer, and the brief written in his window from his answers records the ruling, quoted exactly:

> 1. **Sealer:** "Fresh model now" — `independent_context` seals are enough for now; public README cells stay `unmeasured` plus one development-evidence pointer (the row 9 R9-G pattern); a human re-seal later is a separate run.

So the result, pass or fail, is published exactly as graded as development evidence: the public README cells stay `unmeasured`, and the README carries one development-evidence pointer to the run record.

**Rule 10 — two deviations from the brief.**

1. The brief says a mutant that no longer applies is recorded `ineffective`.
   The as-built runner instead refuses the whole run on a diff that does not apply, so non-application is handled by eligibility (rules 1 and 2); at main it is recorded per mutant in the census, not as a runner status.
2. The brief lists evidence for the Definition-of-Done cell.
   That cell stays `unmeasured`: the release check has no mutants reader yet, and rendering row 3's development line there is a follow-up after row 9's reader pattern merges.

**The procedure's blindness.** Nobody opens, prints, greps or diffs anything under `<seal>/mutants`.
Scripts may hash those files, copy them, run `git apply --check` with them, run the candidate runner's own format validation on them (rule 1c) and execute a mutant's unmutated probe; a script prints only ids, hashes, booleans and counts, and stores any stderr hashed, never in clear.
The coordinator reads only the seal's `SEAL.md` lines 1–11, 29–64 and 104–164 and the runner's own output; lines 12–28 (the mutant descriptions) and 65–103, and everything under `mutants/`, stay unread until 0086 is committed.
The runner's `mutant-<id>.json` logs hold the full mutated-suite output, and tracebacks can quote mutated lines, so they are never opened before 0086 is committed; on any exit the coordinator reads only `run.stdout`, the stderr `REFUSED` and logs-path lines, `baseline.json`, and the file names in the logs folder.

**The procedure's machine quiet.** Before any timed or scored run, `<reservation>` must be absent (if it appears, the coordinator waits for it to come and go), no build queue hold (`<builds>/queue/.hold-*`) may exist, and `uptime` and a `ps -Ao pcpu,comm -r | head` snapshot are recorded in `<evidence>`.
No other benchmark run may be in progress on the machine, confirmed with that run's owner and never inferred from silence.
During THE run the coordinator writes `<reservation>` (`{"by":"gars-row-3-exit","until":"<ET time>"}`) and removes it the moment the run exits.

**Anchoring.** Before the census starts, this record's commit, the file's SHA-256, the fingerprint and `run_env.sh` (whose SHA-256 rule 5 states) are committed and pushed to a private repository outside this machine, because a local commit's date is self-asserted; 0086 cites that push.

## What this does not close

- **No score.** This record measures nothing; the census, timings, run and binding are 0086's.
- **Public credibility.** An `independent_context` seal is a development seal; public claims need `external_human_seal` evidence (§21 Q9: public claims "remain `unmeasured` until a trusted scientist provides `external_human_seal` evidence"), and ruling 1 keeps the README cells `unmeasured`.
- **The Definition-of-Done cell** stays `unmeasured` until a mutants reader exists (rule 10, deviation 2).
- **The census predicts only the pre-mutation refusal causes.** It tests the seal's format checks, the unmutated probe and the apply check; the run can still be refused by what it does not test: a mutated probe that differs from `after` (`2a65dbf` `:230-231`, `f76492b` `:188-189`), a tree that fails its restore hash, a timeout, or anything checked only after mutation (the real `git apply`, a deleted target, a probe that changes the mutated tree); such a refusal is the first run's result under rule 7.
- **The source commit is derived, not sealed.** The seal supplied no commit; the 55/55 match is a hash derivation, and the seal's probe observations are static predictions that the run itself tests.
- **At `f76492b`** the runner snapshots the working tree and emits no per-mutant hashes or logs; rule 8's fingerprint binding is weaker than per-row hashes, and 0086 names it as a limitation.
- **R-166 Linux integration.** This is a macOS run with no Apptainer or pinned pipeline checkout; the interface says the runner is "not R-166 Linux integration".
- **Current main** may be unmeasurable with the as-built runner (rule 4); if so, 0086 names why and no current-main score exists.

## Test

This record changes no code.
With it placed and `bash docs/decisions/build_index.sh` re-run, `python3 tests/test_decision_links_resolve.py` passes and row 11's record checker (`decision_links` in `gars/_system/hooks/pre-commit`) accepts every record.
The procedure's own checks, each able to fail:

- Fingerprint: the seal's procedure, run from `<seal>` with `TMPDIR`, `TEMP` and `TMP` at `<scratch>`, prints `b7685d96ad05e65d6904d0ff0a6a747da1a04566337e951528bb46760191227e`, and the twenty per-file hashes equal the seal's list; a mismatch stops the work.
- Census (rule 1): `census.json` holds `{sha: {Mxx: {"format_valid": bool, "probe_before_match": bool, "applies": bool}}}` and the counts, read with `python3 -c "import json;d=json.load(open('census.json'));print({k:tuple(sum(m[f] for m in v.values()) for f in ('format_valid','probe_before_match','applies')) for k,v in d.items()})"`; run against the runner's own toy set in `gars/tests/test_mutation_runner.py` with one deliberately wrong `before`, it must print a `false` for `probe_before_match`, and with one deliberately malformed `expected.json`, a `false` for `format_valid`.
- Preflight (rule 5): on a deliberately dirty scratch copy it prints a `false`, then all `true` on the run clone.
- Timing (rule 3): each of the five logs shows `collected N tests`, `Ran N tests` and `OK`, and the slowest wall time is at most 180 s.
- Run (rule 6): exit 0 or 1 is a score (0: ten effective and at least eight killed; 1: below); exit 2 is a refusal under rule 7; the binding of rule 8 holds.

## Status

standing; pre-registration only, committed before any census, timing or run; no result exists at this commit and no owner approval is claimed.

## Date

2026-09-23
