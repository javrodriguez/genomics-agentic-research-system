# Review {N} — the pre-freeze review of a pre-registered pre-study

You are a fresh reviewer and have not seen this study before.
Everything you need is in this folder, and nothing outside it is to be read: if a command would read outside this folder, do not run it.

## What is being decided

The pre-registration in `prereg.json` is about to be frozen.
Freezing is irreversible: afterwards the file is read-only, three model sessions ("takes") are run against it, and what each did is published.
Your ruling is DO FREEZE or DO NOT FREEZE.

Read `why.md` first. It is the first lens for everything below: does the design serve that purpose? Do not quote it in your report.

## What is in this folder

- `prereg.json` — the bytes under review, a copy of `study/evals/haiku-prestudy/prereg-draft.json`.
- `{PREVIOUS}` — the bytes the previous review read, if there was one; absent for review 1.
- `study/` — the repository at the commit named in `COMMIT`, with its full history and no remote. The pre-study is `study/evals/haiku-prestudy/`. The study it copies from, round 2, is `study/evals/gap-study-2/` and is read as data only. The system under test is `study/gars/` as it stands at the pre-registration's `export_at` commit (not at HEAD: read it with `git -C study show <export_at>:gars/...`).
- `why.md` — the purpose.

Start inside `study/evals/haiku-prestudy/` with `README.md` and `verification/finding.md`, then `prereg-draft.json`, `COPIED.json` and the rehearsal records `verification/freeze-rehearsal-*.txt`.
Then read the code: `drive.py` and its diff against round 2's (`diff <(git -C study show <source_commit>:evals/gap-study-2/drive.py) study/evals/haiku-prestudy/drive.py`), `build_draft.py`, `outcome.py`, `result.py`, `take.py`, `freeze.py`, `freeze_rehearsal.py`, `finding.py`, `copy_manifest.py`, `test_prestudy.py`, and the probes in `verification/probes/`.

## What to do

1. Record the bytes: `shasum -a 256 prereg.json`, and confirm `diff prereg.json study/evals/haiku-prestudy/prereg-draft.json` prints nothing.
2. If `{PREVIOUS}` exists, compare: `diff <(python3 -m json.tool {PREVIOUS}) <(python3 -m json.tool prereg.json)`, and read every change.
3. From inside `study/`, run the study's own checks and keep each command with the tail of its output:
   - `python3 -W ignore evals/haiku-prestudy/test_prestudy.py`
   - `python3 evals/haiku-prestudy/copy_manifest.py --check`
   - `python3 evals/haiku-prestudy/finding.py --check`
   - `python3 evals/haiku-prestudy/build_draft.py --check`
   - `python3 evals/haiku-prestudy/lint_language.py evals/haiku-prestudy/`
   - `python3 evals/haiku-prestudy/prereg.py --status` and `python3 evals/haiku-prestudy/takes.py --plan`
   Do not run `drive.py` or `take.py` (they call a model), `freeze.py --write`, `freeze_rehearsal.py`, `build_draft.py` without `--check`, or `takes.py --add`, and change nothing under `study/` except inside a copy you make.
4. **The threat model first.** State in two or three sentences what this pre-study's checks bind and what they cannot bind, from what you read. Then judge whether the pre-registration's `limitations_lines` and `driver_change` say that honestly. Every later finding is ruled against that statement.
5. **Is the change one change?** Confirm from the diff and `COPIED.json` that the driver differs from round 2's only by the allowlist on every turn and its ledger record, and that each other edited copy is what its reason says. Confirm the carried keys equal round 2's frozen values (`build_draft.CARRIED`), and that the takes run against the system under test round 2's takes of this half ran against (`export_at`, `round_2_take_exports`).
6. **Is the allowlist the right size?** Read `driver_change.why` and the probes in `verification/probes/forms/`. Is each entry needed, does either admit a program the route does not already use, and would a denial of a command outside it be read honestly?
7. **Is the outcome decidable by code, and only by code?** Read `outcomes` and `outcome.py`. Could a take be read as `reached the probe` when it did not, or the reverse? Is the reason order stated and applied? Does anything let a person choose a take's reading after seeing it?
8. **Predictions and publication.** Are the predictions derived by their stated rule, stated as informed, and fixed before any take? Does `result.py` print counts only, with round 2's cells beside and never pooled, and with nothing about the model beyond what each take did?
9. **Try to break it.** Think as someone who wants a flattering answer after the takes exist: where could a take be re-run, re-routed, re-read, or filed under another row? Where does a guard read less than it claims, or pass without having measured anything? A way for a single edited record or a misfiled attempt to move a reading is a defect. A way that needs a complete, coherent set of fabricated records is a limitation, and a blocker only if the statement does not name it and no cheap check closes it. Say which each finding is, and say plainly if you find nothing that blocks a freeze.

## The report

Write it to `prefreeze-{N}.md` in this folder, not inside `study/`.

- Line 1, exactly: `prereg.json sha256: <the hex digest from step 1>`
- Then a heading and one bold line: `**Ruling: DO FREEZE.**` or `**Ruling: DO NOT FREEZE.**`
- Your threat-model statement (step 4).
- A section for each blocker (a defect that must be fixed before the freeze), and a list of follow-ups (worth fixing, not blocking). Each with the file and line, and the command and output that show it.
- The commands from step 3 with the tails of their output.

The report is public. It names no person, contains no absolute path (write every path relative to this folder), and quotes nothing from `why.md`.
Where you are unsure whether something is a blocker, say which way you lean and why.

Write the report to `prefreeze-{N}.md`. Stop when the report is written.
