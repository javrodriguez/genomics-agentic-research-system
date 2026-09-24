---
date: 2026-09-23
status: standing
kind: decision
touches:
  - evals/mutants.md
  - evals/mutation-runs/
  - evals/mutate.py
  - evals/MUTANTS-INTERFACE.md
  - docs/decisions/0085-row-3-first-run-preregistration.md
  - docs/decisions/0050-row-3-test-suite-gate-and-mutants.md
symptoms:
  - row 3's first sealed mutation run killed 5 of 10 mutants at 2a65dbf, below the ≥ 8/10 exit
  - five sealed mutants survive the row 3 suite (M03, M05, M07, M08, M10)
  - current main refuses the sealed set before scoring (probe-before 6/10, one diff no longer applies)
  - the first run's exit status was derived from its output, not captured from the process
---
# Row 3's first sealed mutation run, recorded as graded: 5/10 killed at 2a65dbf

The result of the run that [0085](0085-row-3-first-run-preregistration.md) pre-registered, for [0050](0050-row-3-test-suite-gate-and-mutants.md)'s sealed-mutation interface; 0050 and 0085 stay as written.
This is the first run under 0085's rules, and it is THE result: it is published exactly as graded, as development evidence, and it is not re-run.

## Context

0085 fixed the rules before any census, timing or run touched the seal: which commit the run uses (rule 2), the timing gate (rule 3), current main (rule 4), one environment (rule 5), one command (rule 6), the first-run rule (rule 7), the binding (rule 8) and where the result goes (rule 9).
Paths below use 0085 rule 5's placeholders: `<home>`, `<builds>`, `<scratch>`, `<seal>`, `<evidence>` and `<reservation>`.

**Order of events, all 23 Sep 2026, Eastern time.**

- 20:15:34: 0085 committed as `bd90cc3` on the build branch `build/gars-row-3-exit` (parent `dc6a72a`), file SHA-256 `6b32a55e9ac3de894fe46444b032123b7127c7423fe9179b6157f6cd6bc3f13a`.
- 20:15:53: the anchor committed in the private aegis repository as `8bbf2e3` ("evidence: anchor GARS row 3 pre-registration (0085) before its census"), carrying the GARS commit, the 0085 file hash, the re-derived fingerprint and `run_env.sh` (SHA-256 `3b9a9c1dc22224cb0d7e946d70d34adeac4e6139a353af7bb352cca51d474296`); its anchor file reads "census: not started at the time of this commit".
- 20:16:03: `8bbf2e3` pushed, by GitHub's own push record for the aegis repository (`2026-09-24T00:16:03Z`, `coordinator-record.txt` item 5); the remote branch equals the local commit and the repository is private.
- 20:20:32 to 20:23:18: the census ran (`census-meta.json` `started_utc` and `finished_utc`), after the anchor push.
- 21:34:49 to 21:41:32: the five timing runs (rule 3).
- 21:41:44 to 21:56:20: THE run, pid 38233 (`run.started`, `run.finished`, `run.pid`).

**What the binding cannot show.**
- **Whose clock.** Every time above except the push is this machine's own clock (the census, timing and run files, and the commit times).
  The only server-side time is GitHub's push record for the anchor: `{"activity_type":"push","after":"8bbf2e3e5b19f14202506c0a754571a3a8cad68d","ref":"refs/heads/master","timestamp":"2026-09-24T00:16:03Z"}` (20:16:03 ET), read with `gh api repos/javrodriguez/aegis/activity` and transcribed in `coordinator-record.txt` item 5.
- **Who can check the anchor.** The aegis repository is private, so a public reader cannot check the anchor or its push record themselves.
- **An earlier hidden attempt.** These records cannot exclude an earlier attempt run with another `TMPDIR`.
  What speaks to it: `<scratch>` holds 48 other `gars-mutation-logs-*` folders, each containing only `baseline.json` and `mutant-toy.json` (the runner's own self-test inside suite runs), none with a sealed mutant id (`coordinator-record.txt` item 5); and the anchor was pushed before the census, the census before the timing runs, the timing runs before THE run.

**The seal** is as 0085 describes it: `independent_context`, sealed 15 Sep 2026, fingerprint `b7685d96ad05e65d6904d0ff0a6a747da1a04566337e951528bb46760191227e`, re-derived by the seal's own procedure and equal to line 1, with 20/20 per-file hashes equal to the seal's list (`fingerprint.txt`, `fingerprint-perfile.txt`).

## Decision

**The measured result, as graded.**
At run commit `2a65dbf0c6383cc71b97bf19f0838482d542f1be`, the runner printed ten rows and the line `5/10 killed/total`: **5 killed, 5 survived, 0 ineffective**, and no refusal.

| Mutant | Runner status | First failing test (runner's `test` field) |
|---|---|---|
| M01 | killed | `__main__.GuardHookTests.test_denies` |
| M02 | killed | `test_pre_push.PrePushTests.test_each_empty_tree_refuses (tree='tests/test_gate_sample.py')` |
| M03 | survived | — |
| M04 | killed | `__main__.ExecutorSeamTests.test_00_slurm_default_is_byte_identical` |
| M05 | survived | — |
| M06 | killed | `__main__.ExecutorSeamTests.test_05_local_backend_walks_submit_to_completed` |
| M07 | survived | — |
| M08 | survived | — |
| M09 | killed | `__main__.SpatialviTests.test_04_collect_gates_per_sample_and_never_takes_the_raw_h5ad` |
| M10 | survived | — |

Every row names requirement `R-164`.
`survived` is the runner's own status: with that mutant applied, the whole suite passed (`mutate.py` at `2a65dbf` `:237-240`).
This record says nothing more about what any mutant changes: the seal's mutant descriptions stay unread until this record is committed (0085, "The procedure's blindness").
The record is `evals/mutation-runs/2026-09-23-2a65dbf-first-run.json`, and the table is `evals/mutants.md`.

**Row 3 exit.**
The exit is "≥ 8/10 mutants killed; 7/7 wrapper contracts" (§18).
**NOT met as development evidence**: 5/10 killed.
The 7/7 wrapper-contract line holds at `2a65dbf`.
The public claim is unmeasured: ruling 1 keeps the public README cells `unmeasured`, and a public claim needs `external_human_seal` evidence.

**The seal's static predictions held when executed.**
The runner refuses the whole run if an unmutated probe differs from `before` (`:208-209`) or a mutated probe differs from `after` (`:230-231`), and marks a mutant `ineffective` if its probe does not change (`:227-229`).
Ten rows with no refusal and none `ineffective` therefore mean that all twenty of the seal's predicted observations matched what the probes did at `2a65dbf`.

**The run commit, and why (0085 rules 1 and 2).**
The census (`census.json`, read with 0085's command) gave, as (`format_valid`, `probe_before_match`, `applies`) counts out of 10:

- `2a65dbf`: (10, 10, 10), eligible;
- `f76492b`: (10, 10, 10), eligible;
- `dc6a72a` (current main): (10, 6, 9), not eligible; `probe_before_match` false for M01, M02, M09 and M10, and M01's diff no longer applies.

Rule 2 puts THE run at `2a65dbf`, row 3's own final commit, because it is eligible.
The census's base tree hash for `2a65dbf` (`census-meta.json`), the runner's `snapshot_hash` on every row and `baseline.json`'s `tested_tree_hash` are the same value, `6f13a2d335b21b2d2fffc5f5f86b5f8e501c82e5cc624af3b819235574dce686`: the census and the run tested the same tree.
Before the census, a self-test on the runner's toy set showed each boolean able to fail (a wrong `before`, a malformed `expected.json`, an id mismatch, a probe that dirties the tree, a diff that does not apply and one outside scope; `census-selftest.json`).

**The timing gate (0085 rule 3): passed.**
Five sequential baseline runs of `2a65dbf` from fresh `git archive` copies, under the rule 5 prefix with the reservation held (`timing-2a65dbf.json`):

- wall times 97.55, 76.41, 71.44, 81.1 and 73.29 s; the slowest, 97.55 s, is under the 180 s gate;
- every run green (exit 0, `OK (skipped=9)`), `collected 151` and `Ran 151` in every run (125 from `tests`, 26 from `gars/tests`);
- `wrapper contracts: 7/7 found/expected nf-core; 10 total wrappers` in every run.

The machine was not fully quiet for run 1, a departure from 0085's machine-quiet procedure ("No other benchmark run may be in progress on the machine, confirmed with that run's owner and never inferred from silence").
Another lane reported that its database test module started at ~21:34:26 (reported) and that it suspended the module (SIGSTOP) at 21:35:57 (reported), overlapping about the first 68 s of run 1 (which began 21:34:49); the coordinator observed neither itself (`coordinator-record.txt`, item 4).
Contention can only lengthen a wall time, and run 1 still passed the gate, so it was kept and is recorded here rather than re-run; keeping it was the coordinator's judgment, not a pre-registered rule.

**THE run (0085 rules 5 and 6).**
The launch was the rule 6 command at `2a65dbf`, with stdout to `<evidence>/run.stdout` and stderr to `<evidence>/run.stderr`; the preflight printed its six checks true, interpreter 3.13.2, exit 0, beforehand, and the machine snapshot is `run-quiet.txt` (load 4.95).
The launch line, the preflight output and the anchor push's verification are transcribed verbatim in `<evidence>/coordinator-record.txt` (SHA-256 `64a0df0ef57714c6b2baa3ee7428f8ec1dfac0cb4b80752d6b2c7a95a53f4529`), written after the run from the coordinator's own session output, with item 5 (GitHub's push record and the `<scratch>` listing) appended after a fresh review; it is the coordinator's statement, not runner output, and sits outside the evidence manifest.
The runner's stderr holds one line, `mutation suite logs: <scratch>/gars-mutation-logs-igqies5b`, and no `REFUSED`.
Its own baseline inside the run: exit 0, `Ran 151 tests in 80.174s`, `OK (skipped=9)`.

**The exit code is derived, not captured: a coordinator gap.**
The launch did not wrap the process to record its exit status, so the code is derived from the runner's output and code: no `REFUSED` on stderr, ten records, none `ineffective`, 5 killed below 8, so `--require` returns 1 (`mutate.py` `:297-298`); the only statement after the summary line is that `return`.
The derivation is `run.exit-derived`, and the record says `exit_code: 1` with `exit_code_source` naming it as derived.
Exit 1 is a score under 0085's Test section.
The gap does not change the score, which is read from the rows, and the run is not repeated to capture it: the first run is THE result (rule 7).

**The binding (0085 rule 8, at `2a65dbf`): holds.**
Each row's `mutant_diff_sha256` and `expected_sha256` equal the seal's per-file list: 20/20.
`run_sha` is `2a65dbf0c6383cc71b97bf19f0838482d542f1be` on every row and equals the chosen run commit (`run_commit.txt`).
The 7/7 wrapper-contract line and the nine skips come from the runner's own `baseline.json` (`binding.json`).
Rule 8's weaker `f76492b` binding was not needed.

**Environment and skips.**
macOS (Darwin 25.6.0, x86_64); `/usr/local/bin/python3`, whose `sys.executable` is `/usr/local/opt/python@3.13/bin/python3.13`, Python 3.13.2 (taken from the timing runs and the census under the same prefix, because the runner does not print its interpreter).
The nine skips in the runner's baseline are all environmental: no pinned nf-core checkout for atacseq 2.1.2, chipseq 2.1.0, cutandrun 3.2.2, methylseq 4.2.0, rnaseq 3.26.0 (two tests) and scrnaseq; `anndata` not importable in this interpreter; and the GRCh38 registry reference not on this machine.
The record lists each by its test id with its skip reason.

**Evidence.**
Everything named here is in `<evidence>` and listed in `evidence-manifest.sha256` (50 files: every file in `<evidence>`, the runner's logs folder included, except the manifest itself, `coordinator-record.txt` and `__pycache__`), whose own SHA-256 is `db75f27bc9a4c958a6e01c2cada28b7266d7ae0d820e5c2e03fe36d76e24b837`; the record carries the same value as `evidence_manifest_sha256`.
The manifest also lists an aborted pass/fail gate launch (`gate.sh`, `gate.pid`, `gate-aborted-for-row7.log`): `tests/run_tests.py` on the build tree, launched after THE run and stopped by pid within about two minutes when another lane reserved the machine; it is not a mutation run, created no mutation-logs folder and touched no sealed file.
It also lists `check_mutants_md.py`, the checker that ties `evals/mutants.md` to the record.
Files written to `<evidence>` after the manifest (the completed gate's log and main's informational timings) are outside it.
The record's rows are the runner's stdout with `<scratch>` in place of the machine path, and `run_stdout_sha256` (`cd93a0d89aa90a8c2c0fd660e47eb01d73ebf9f92a8f4f0e7248851c65b080ae`) binds the raw bytes.

**Where the result goes: the owner's ruling 1.**
The owner, 23 Sep 2026, chose the option "Fresh model now" for the sealer, and the brief written in his window from his answers records the ruling, quoted exactly:

> 1. **Sealer:** "Fresh model now" — `independent_context` seals are enough for now; public README cells stay `unmeasured` plus one development-evidence pointer (the row 9 R9-G pattern); a human re-seal later is a separate run.

So the public README cells stay `unmeasured`, and the README carries one development-evidence pointer to the run record.

**Current main (0085 rule 4): unmeasurable with the as-built runner.**
Main (`dc6a72a`, still the public head) fails eligibility: `probe_before_match` 6/10 and `applies` 9/10, and the runner refuses the whole run on either (`main-unmeasurable.md`).
No current-main score exists: no subset, no rewritten diff.
Main's five timings are informational only once eligibility fails; they are pending, to be taken after another benchmark on this machine finishes, and main's 7/7 line is not yet taken.

## Gaps between the seal and the interface

The seal does not fully satisfy `evals/MUTANTS-INTERFACE.md` as written.
Each gap is recorded here and none was fixed by editing the seal:

- **(a) No source SHA.** The seal records "Producer commit SHA: not supplied in the available handoff."
  The source is derived as `f76492b` from a 55/55 hash match of the seal's input inventory (0085); it is stated as derived, never as sealed.
- **(b) Expected outputs are static predictions.** The seal says "Probe observations are static predictions, not executed measurements."
  The run itself tested them, and all twenty held at `2a65dbf` (see Decision).
- **(c) Environment and skips are not in the seal.** The run records them from the runner's own `baseline.json`: nine environmental skips.
- **(d) The sealer does not fill `mutants.md`.** `evals/mutants.md` says "The sealer fills this document from its own run after the producer commit." (`:27` before this commit, `:32` in the filled file).
  Here the coordinator's transcriber filled it mechanically from the runner's stdout, and `mutants.md` says so.

## Deviations, named

- **The census gained `format_valid`** beyond the plan's two booleans: rule 1(c), written into 0085 before the census ran.
- **Placeholders, not machine paths.** 0085 and this record name folders by placeholder; the run record's rows replace the scratch path with `<scratch>`, and its skip reasons replace the home folder with `<home>`, with the raw stdout bound by `run_stdout_sha256`.
- **The census metadata is a separate file**, `census-meta.json`, because 0085's read command needs `census.json` flat (`{sha: {Mxx: booleans}}`).
- **`mutants.md` was filled by the coordinator's transcriber, not the sealer** (gap d).
- **The exit code was derived, not captured** (see Decision).
- **Run 1 of the timing gate overlapped another lane's test module** for about 68 s, against 0085's machine-quiet procedure; keeping it was the coordinator's judgment (see Decision).
- **Main's five timings follow THE run instead of preceding it**: main was already ineligible, so they cannot change rule 4's outcome, and the order kept the run's machine window short.
- **The row 3 status text is not in this repository**: `STATE.md` is the live, gitignored cross-lane workspace file, and the coordinating session applied the row 3 status text there.
- **The brief's two deviations**, as 0085 rule 10 named them: a diff that no longer applies is handled by eligibility, not recorded `ineffective`; and the Definition-of-Done cell stays `unmeasured`.

## What this does not close

- **Public credibility.** An `independent_context` seal is a development seal; public claims need `external_human_seal` evidence (§21 Q9: public claims "remain `unmeasured` until a trusted scientist provides `external_human_seal` evidence").
- **Row 3's exit**, which is NOT met: 5/10 is below 8/10.
- **The survivors are not investigated here.** Any strengthening of the suite that follows cannot be measured against this seal: the interface says "Do not tune surviving faults after seeing producer tests; retain the first score at the original run SHA. A later set is a separate sealed run, not a replacement of its first result." (`evals/MUTANTS-INTERFACE.md:121-123`).
  A later score needs a new seal, run as a separate run with this first result retained.
- **The Definition-of-Done cell** stays `unmeasured`: the release check has no mutants reader; rendering row 3's development line there is a follow-up after row 9's reader pattern merges.
- **Current main has no score** with the as-built runner, and main's informational timings and 7/7 line are pending.
- **What the binding cannot show** (see Context): the times are this machine's clock except GitHub's push record for the anchor; the anchor repository is private, so a public reader cannot check it; and an earlier hidden attempt with another `TMPDIR` is not excluded, only spoken to by the `<scratch>` listing and the anchor order.
- **R-166 Linux integration.** This is a macOS run with no Apptainer and no pinned pipeline checkouts; the interface says the runner is "not R-166 Linux integration".

## Test

This record changes no code.
With it placed and `bash docs/decisions/build_index.sh` re-run, `python3 tests/test_decision_links_resolve.py` passes and row 11's record checker (`record_fields` in `gars/_system/hooks/pre-commit`) accepts it.
The transcriber is not in the repository: it is `transcribe.py` in `<evidence>`, listed in the evidence manifest, and it reads `run.stdout`, `binding.json`, `census.json`, `census-meta.json`, `timing-2a65dbf.json`, `run.exit-derived` and `baseline.json`.
Each check below reproduces a part of the record from its inputs and can fail:

- The record parses: `python3 -c "import json;json.load(open('evals/mutation-runs/2026-09-23-2a65dbf-first-run.json'))"`.
- The rows are the runner's stdout: with `S` set to the absolute `<scratch>` path, `python3 -c "import json,hashlib,os;raw=open('<evidence>/run.stdout','rb').read();rec=json.load(open('evals/mutation-runs/2026-09-23-2a65dbf-first-run.json'));rows=[json.loads(l.replace(os.environ['S'],'<scratch>')) for l in raw.decode().splitlines() if l.startswith('{')];print(hashlib.sha256(raw).hexdigest()==rec['run_stdout_sha256'],rows==rec['rows'],raw.decode().splitlines()[-1]==rec['summary_line'])"` prints `True True True`.
- The binding: `python3 -c "import json;s=dict(reversed(l.split()) for l in open('<seal>/SEAL.md').read().splitlines()[42:62]);r=[json.loads(l) for l in open('<evidence>/run.stdout') if l[0]=='{'];print(sum((s['mutants/%s/expected.json'%x['id']]==x['expected_sha256'])+(s['mutants/%s/mutant.diff'%x['id']]==x['mutant_diff_sha256']) for x in r),{x['run_sha'] for x in r})"` prints `20` and the one run commit; it reads only the seal's hash list (lines 43-62).
- The census, read in `<evidence>` with 0085's command: `python3 -c "import json;d=json.load(open('census.json'));print({k:tuple(sum(m[f] for m in v.values()) for f in ('format_valid','probe_before_match','applies')) for k,v in d.items()})"` prints (10, 10, 10) for `2a65dbf` and `f76492b` and (10, 6, 9) for `dc6a72a`.
- The baseline, skips and 7/7 line: `python3 -c "import json;b=json.load(open('<evidence>/gars-mutation-logs-igqies5b/baseline.json'));print(b['returncode'],b['run_sha'][:7],[l for l in b['stdout'].splitlines()+b['stderr'].splitlines() if l.startswith(('wrapper contracts','Ran ','OK'))])"` prints `0 2a65dbf`, the 7/7 line twice (the suite prints it twice, both times on its stdout), `Ran 151 tests` and `OK (skipped=9)`.
- No refusal: `grep -c REFUSED <evidence>/run.stderr` prints `0`.
- The evidence: `shasum -a 256 <evidence>/evidence-manifest.sha256` prints `db75f27bc9a4c958a6e01c2cada28b7266d7ae0d820e5c2e03fe36d76e24b837`, and `shasum -a 256 -c evidence-manifest.sha256` run in `<evidence>` reports every file `OK`.

## Status

standing; row 3's first sealed run recorded as graded, 5/10 killed at `2a65dbf`, development evidence; Row 3 exit NOT met; public claim unmeasured; no owner approval is claimed.

## Date

2026-09-23
