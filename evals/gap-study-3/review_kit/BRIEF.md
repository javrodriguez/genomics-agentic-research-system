# Review {N} — the pre-freeze review of a pre-registered round

You are a fresh reviewer and have not seen this study before.
Everything you need is in this folder, and nothing outside it is to be read: if a command would read outside this folder, do not run it.

## What is being decided

The pre-registration in `prereg.json` is about to be frozen.
Freezing is irreversible: afterwards the file is read-only, the planned model sessions ("takes") are run against it, and what each did is published.
Your ruling is DO FREEZE or DO NOT FREEZE.

Read `why.md` first. It is the first lens for everything below: does the design serve that purpose? Do not quote it in your report.

## What is in this folder

- `prereg.json` — the bytes under review, a copy of `study/evals/gap-study-3/prereg-draft.json`.
- `{PREVIOUS}` — the bytes the previous review read, if there was one; absent for review 1.
- `study/` — the repository at the commit named in `COMMIT`, with its full history and no remote. This round is `study/evals/gap-study-3/`. The round it copies from is `study/evals/gap-study-2/` and the pre-study is `study/evals/haiku-prestudy/`; both are read as data only. The system under test is `study/gars/` as it stands at the pre-registration's `export_at` commit (not at HEAD: read it with `git -C study show <export_at>:gars/...`).
- `why.md` — the purpose.

Start inside `study/evals/gap-study-3/` with `README.md` and `PROGRESS.md`, then `prereg-draft.json`, `COPIED.json`, the fixture walks under `walks/` and their leak verdicts, and the rehearsal records `verification/freeze-rehearsal-*.txt`.
Then read the code: `drive.py` and its diff against the round it copies from (`diff <(git -C study show <source_commit>:evals/gap-study-2/drive.py) study/evals/gap-study-3/drive.py`), `build_draft.py`, `allowlist.py`, `round2.py`, `fixture_walk.py`, `mode_binding.py`, `result.py`, `completeness.py`, `leak_grep.py`, `lint_pooling.py`, `freeze.py`, `copy_manifest.py`, `test_round3.py`, and `review_kit/rounds.py` with the register in `review_kit/rounds.json`.

## What to do

1. Record the bytes: `shasum -a 256 prereg.json`, and confirm `diff prereg.json study/evals/gap-study-3/prereg-draft.json` prints nothing.
2. If `{PREVIOUS}` exists, compare: `diff <(python3 -m json.tool {PREVIOUS}) <(python3 -m json.tool prereg.json)`, and read every change.
3. From inside `study/`, run the study's own checks and keep each command with the tail of its output:
   - `python3 -W ignore evals/gap-study-3/test_round3.py`
   - `python3 evals/gap-study-3/copy_manifest.py --check`
   - `python3 evals/gap-study-3/allowlist.py --check`
   - `python3 evals/gap-study-3/build_draft.py --check`
   - `python3 evals/gap-study-3/leak_grep.py --check`
   - `python3 evals/gap-study-3/fixture_walk.py --check`
   - `python3 evals/gap-study-3/mode_binding.py --check` and `--walks --check`
   - `python3 evals/gap-study-3/completeness.py --check`
   - `python3 evals/gap-study-3/lint_language.py evals/gap-study-3/`
   - `python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/`
   - `python3 evals/gap-study-3/prereg.py --status` and `python3 evals/gap-study-3/takes.py --plan`
   - `python3 evals/gap-study-3/review_kit/rounds.py --check`
   Do not run `drive.py` or `run.py` (they call a model or grade against a freeze), `freeze.py --write`, `freeze_rehearsal.py`, `build_draft.py` without `--check`, or `takes.py --add`, and change nothing under `study/` except inside a copy you make.
4. **The threat model first.** State in two or three sentences what this round's checks bind and what they cannot bind, from what you read. Then judge whether the pre-registration's `limitations_lines`, `driver_change` and `not_poolable` say that honestly. Every later finding is ruled against that statement.
5. **Is the change one change?** Confirm from the diff and `COPIED.json` that the driver differs from the copied round's only by what its docstring names, and that each other edited copy is what its reason says. Confirm that the files `COPIED.json` marks byte-identical really are, in particular the take checker, every grader and the label reader. Confirm the carried keys equal the copied round's frozen values (`build_draft.CARRIED`), and that the takes run against the system under test that round's takes ran against (`export_at`, `system_under_test`).
6. **Is the allowlist the right size, and is it derived?** Read `driver_change.why`, `allowlist.py` and the derivation output the draft records. Every entry must trace to a command form quoted verbatim from a committed transcript of the task whose route uses it, with the transcript path and line printed. Is any entry a bare binary wildcard? Is any entry wider than the form it came from? Does any entry admit a program the routes do not already use? Would a denial of a command outside it be read honestly?
7. **Is the fixture re-cut proved, and by code?** Read `fixture_walk.py` and the committed walk per half. The leak verdict must be decided by code, asserting every path the agent read at path boundaries and never by substring. Could a leaking path pass? Could a clean walk be read as leaking?
8. **Is the outcome decidable by code, and only by code?** Read `outcomes` and the graders. Could a take be read as reaching the probe when it did not, or the reverse? Is the reason order stated and applied? Does anything let a person choose a take's reading after seeing it? Is the permission mode asserted from the session's own record rather than from a flag the driver passed?
9. **Predictions and publication.** Are the predictions derived by their stated rule, each naming the earlier round's evidence it read, stated as informed, and fixed before any take? Does `result.py` print counts only, with the earlier round's cells beside them under a caption that names the condition, the date and the instrument, never added together, and with nothing about a model beyond what each take did? Is every `k of n` in it n = 3 and traceable to exactly one round's table?
10. **Try to break it.** Think as someone who wants a flattering answer after the takes exist: where could a take be re-run, re-routed, re-read, or filed under another row? Where could two rounds' counts be added together? Where does a guard read less than it claims, or pass without having measured anything — a check that grades zero items and prints a pass is a defect, not a pass. A way for a single edited record or a misfiled attempt to move a reading is a defect. A way that needs a complete, coherent set of fabricated records is a limitation, and a blocker only if the statement does not name it and no cheap check closes it. Say which each finding is, and say plainly if you find nothing that blocks a freeze.

## The report

Write it to `prefreeze-{N}.md` in this folder, not inside `study/`.

- Line 1, exactly: `prereg.json sha256: <the hex digest from step 1>`
- Then a heading and one bold line: `**Ruling: DO FREEZE.**` or `**Ruling: DO NOT FREEZE.**`
- Your threat-model statement (step 4).
- A section for each blocker (a defect that must be fixed before the freeze), and a list of follow-ups (worth fixing, not blocking). Each with the file and line, and the command and output that show it.
- The commands from step 3 with the tails of their output.
- **A closing table of every finding you raised, in your own words, one row each: the finding, its class — BLOCKER, SHOULD or NIT — and your own statement of whether fixing it would change a criterion, a reading or a claim.** Classify every finding; the table is yours and nobody else assigns a row. A freeze follows a round whose table is all NITs.

**The materiality bar, for every row of that table.** Material — would change what the study may claim. Actionable — a change to something the study controls. Verifiable — checkable by a command. A false "all clear" and a padded list are equal failures; a weakness only fixable by lying is a limitation, not a finding.

The report is public. It names no person, contains no absolute path (write every path relative to this folder), and quotes nothing from `why.md`.
Where you are unsure whether something is a blocker, say which way you lean and why.

Write the report to `prefreeze-{N}.md`. Stop when the report is written.
