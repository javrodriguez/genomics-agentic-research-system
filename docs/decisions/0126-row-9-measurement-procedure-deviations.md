---
date: 2026-09-25
status: standing
kind: decision
touches:
  - evals/review-faults/run_reviews.py
symptoms:
  - the pinned measurement procedure names a harness commit whose audit has since been fixed
  - the pinned procedure deploys the working-tree isolation checker, which is now a later version
---

# Row 9 measurement procedure: deviations from the pinned instrument

## Context

Row 9's first measured run follows a pinned procedure kept with the deployment, outside this repository (the deployment's MEASURE.md, sha256 `fbe6de00a51a7c14a725c19887a74d18e23b4c9dae6329dfc3b7bed313278251`).
A pinned instrument is never amended: a change to it is a new pinned copy, recorded here.
This record is the lane's, under the owner's delegation quoted in 0072; nothing in it is attributed to the owner.
The lanes' coordinator ruled both deviations under the same delegation.

## Decision

1. **The harness head.**
   MEASURE.md pins public main `5ba82c625cec42277e463c5b4077a7dc0245389b`, whose `evals/review-faults/run_reviews.py` (sha256 `78b3814c594a6ab4f3e93a2837bbd7bb525c7d9ce7d7ab749a43b5b48c955e20`) is the audit before two false-INVALID fixes: 0125 (a relative path after an in-kit `cd`) and 0127 (a `tr` operand read as a path).
   Followed literally, it would rehearse and measure with that audit, and in the measured run an INVALID record is final.
   The procedure now runs at `84505ebd53165e59931bc66dde8995fc2a469df5` (0127's landing), whose `run_reviews.py` hashes `1e9b643275300e5c135c15411a95166a9bee3da9da97e9938154f07e83378d75`.
   Every other pinned harness file, the measured prompt (`gars/_references/prompts/review_faults_code.md`, sha256 `29d9ab7fc987849615b10d38c34a2ca419f3ca284a6cf4af87bb846e4c2d1b81`), the fixtures, `build_cases.py` and `score.py` are byte-identical at both commits.
2. **The isolation checker.**
   MEASURE.md's CP8.7 copies the deployment's working-tree isolation checker, pinned to a 19-check result.
   The working tree now holds a later 25-check version (one check is red until a host step the owner has not yet run), so following the text literally would deploy the wrong version.
   The procedure instead deploys the 19-check version extracted from the deployment's history, verified before use: sha256 `81b76e5366a1713d4ba60588a666a336068df542e1780f24ff815c8fd8bc1f80`, which is the copy already deployed on both accounts.
   The working-tree version at the time hashed `461ee65e591991e538f86ba09ae73c3b89c911c80897cedb11483b05b4ee5ae7`.

Both deviations are carried by one new pinned copy, the deployment's MEASURE-2.md, sha256 `ef3a6d49c2e02e4a60a7a3488367fcd26bb7406afb9c2d23ad00b59783cfa89a`.
It changes only those lines, and a supersession paragraph; a fresh-context reader confirmed from the diff that nothing else changed, and MEASURE.md stays byte-identical.
If the harness commit changes before it is public, a dated MEASURE-3 supersedes MEASURE-2 the same way.

## What this does not close

The first measured run waits until `84505eb` is public and its CI and Fresh clone are green, so that `harness_commit` in every manifest resolves for any reader.
The seal and the measured run are recorded in 0074.

## Test

`git show 84505ebd53165e59931bc66dde8995fc2a469df5:evals/review-faults/run_reviews.py | shasum -a 256` prints the new pin; the other harness files and the prompt hash as MEASURE.md pins them.
The checker extracted from the deployment's history hashes as stated above and counts 19 checks.

## Status

Standing.

## Date

2026-09-25

## Addendum, 2026-09-25: MEASURE-3 supersedes MEASURE-2

The end-to-end rehearsal at `84505eb` voided two honest review sessions: the reviewer's tool keeps its working directory from one Bash call to the next, and the audit placed later relative paths against the kit root (fixed in 0128).
The procedure therefore moves again, by a new pinned copy, the deployment's MEASURE-3.md (sha256 `6d5364a9804f958802d4dda393821e383a10f3c482774e396b5e816db1288829`); MEASURE.md and MEASURE-2.md stay byte-identical.
It changes only: the harness head, `84505eb` → `a77908474f2fc463f481a55f2d0c2ceeee8be660` (0128's landing); the pins of `run_reviews.py` (`5889a9b93b9154bb9ca5311517c1745152f58fee0622156d69633295d7dab213`), `review_record.py` (`853400b167303eae2b4663c2d1e442265c942d2927000950af4e35797949105c`) and the record schema (`be71b5536458a2a4c626d9bebfab40cc909e7f7de6f218ca5ba67cfca1c3d831`) there; the expected envelope and score printouts, which gain the `ambiguous` count; and the reviewer's settings file, now the deployment's measure-settings-3.json (sha256 `5f4fd164fbad2a9f22ee713c6c782430804cf8126c61c88b9113c44aa8cce144`).
That file is the old settings' bytes with only an `env` block added that stops a refused request from being retried on another model: in a direct sandbox probe on 25 Sep 2026 the requested model refused, the request was rerouted to another model, and that model attempted the reads, which the sandbox and the permission rules stopped with no content reaching the session.
That probe asked a model to read protected files; the harness flagged its framing, and by the lanes' coordinator's ruling no model is asked to attempt a protected read from here on, so the procedure's probe run is not used.
The sandbox evidence for the seal is the settings' byte-identity (the permission and sandbox blocks are unchanged), that probe's observed result kept as history (stream sha256 `2b525432ce8487e0394a1917a22fefeb872540cf0ff8037be90ec2fde1c16a97`), a second probe under the new settings that ended in a refusal with no fallback (stream sha256 `89571c512f1a56699ed579c7437a9093867e56b3c302f9c0e55be63e0e073241`), and the blindness audits of the honest rehearsal sessions.

## Addendum, 2026-09-25: MEASURE-4 supersedes MEASURE-3 (the sealer's Codex home only)

The Mac's default Codex account was at its usage limit until 28 Sep, so R9-C (a fresh Codex context on the Mac) runs as written on the owner's second Codex account, which the owner logged into a separate Codex home himself.
The deployment's MEASURE-4.md changes only CP7.4 and its correction round: they run with a fresh, seal-only Codex home whose credential file is a symbolic link to that account's (created, never copied or opened), and the procedure's instruction-file check and session lookup read that home. MEASURE.md, MEASURE-2.md and MEASURE-3.md stay byte-identical.
MEASURE-4.md's sha256 is `1869158c02d287fdf8b20514992fa3ac5b5ceb8aec0a404c2a113ee2e8356b93`; a fresh-context reader confirmed from the diff that nothing else changed.

## Addendum, 2026-09-25: one step of MEASURE-4's CP8.7 not run as written

MEASURE-4's CP8.7 copies the extracted 19-check isolation checker onto both node accounts with two `scp` commands before running it.
In the finishing session, the coordinating tool's own permission layer refused those two remote writes, and the lane did not work around the refusal.
The step's purpose, running exactly the pinned 19-check checker on both accounts, was met without them: the copy already on each account (placed on 24 Sep) hashed `81b76e5366a1713d4ba60588a666a336068df542e1780f24ff815c8fd8bc1f80`, equal to the checker extracted from the deployment's history and verified before use, and that hash was read again in the same remote session that then ran the checker.
Both accounts passed, 19 checks and 0 failures each, exit 0, at 2026-09-25T17:05:01Z.
The lanes' coordinator ruled the substitution equivalent, and it is recorded here as a named deviation; no pinned instrument was changed.
