prereg.json sha256: 511963d577db790298073606fd05c8dcfc289303076087f59fbd71bd935ad098

# Pre-freeze review 1 of the Gap Study, round 3

**Ruling: DO NOT FREEZE.**

`diff prereg.json study/evals/gap-study-3/prereg-draft.json` prints nothing. There is no `prereg-as-the-previous-review-read-it.json`; this is review 1. All fourteen commands in step 3 exit 0; their tails are at the end of this report. The ruling rests on four blockers, none of which any of those commands can see.

## The threat model

What this round's checks bind: the instrument's bytes to round 2's done commit (`copy_manifest.py`), the draft to its builder and 25 carried keys to round 2's frozen values (`build_draft.py --check`), every allowlist entry to a verbatim command prefix quoted from a named line of a round-2 transcript (`allowlist.py --check`), the leak verdict of five committed walks at path boundaries (`fixture_walk.py --check`), the mode each session recorded to a per-model expectation (`mode_binding.py`), and every planned cell to complete-or-unmeasured-with-a-reason (`completeness.py`). What they cannot bind: that the harness applied the allowlist at all (no session file records it; the evidence is the absence of a denial sentence), that the recorded mode is the enforced mode, that auto mode's classifier did not admit for the two larger models a command the smallest model would have been denied, that the model behind an id is the same on a later date, and anything after the freeze that lives in a file the freeze does not pin.

Against that statement: `limitations_lines` 2, 3, 9 and 10 say the first four honestly, and `not_poolable` is honest and enforced by a guard with no excusal path. `driver_change.permission_mode_binding` is not honest (blocker 3), and the `question` claims a single condition across the model axis that the design does not deliver (blocker 4). The pin list that decides what the freeze binds is round 2's, not this round's (blocker 2).

## Blocker 1 — the result publishes the graded-take count as the held count

`study/evals/gap-study-3/result.py:112` sets a cell's `graded` to the number of take folders on disk, and `result.py:201` prints that number under the column `held` as `k of 3 graded`. No grader label is read anywhere in the file. The held count `k` is computed by `run.py` from the graders' verdicts and written to `results/<task>.json`; `result.py` defines `RESULTS` at line 40 and never opens it. The earlier round's column in the same page prints `k` from its results file, so the two tables print different quantities under one header. Every complete cell in RESULT.md would read `3 of 3 graded`, and the study's own question, how many of three takes each cell holds, would not be answered by its publication. The battery's result tests check n, reasons and captions, not what the number is, so nothing goes red.

```
$ grep -n '"graded": len(takes)\|of {c\[.n.\]} graded\|RESULTS' study/evals/gap-study-3/result.py
40:RESULTS = HERE / "results"
112:    return {"task": task, "half": half, "model": model, "graded": len(takes), "n": N,
201:        held = f"{c['graded']} of {c['n']} graded" if c["state"] == "complete" else "—"
$ grep -n "k = sum\|RESULTS / f" study/evals/gap-study-3/run.py
257:    k = sum(1 for x in out_labels if x["verdict"] == "correct")
321:        (RESULTS / f"{task_id}.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
```

Fix: read `results/<task>.json` for each cell's `k` and print `k of 3` under `held`, keep the graded-take count in its own column, and add a battery test that a cell with three graded takes and one correct verdict prints 1, not 3. This is a defect a single misread would carry into every published cell; it is not a limitation.

## Blocker 2 — the freeze's pin list and rehearsal are round 2's, and the freeze cannot run

`study/evals/gap-study-3/freeze.py:58` carries round 2's `PINNED` list byte for byte. Six of its paths do not exist in this round, and `freeze.py:596` returns 1 on any missing pin, so `freeze.py --write` cannot succeed as the code stands. Its globs `tests_*.py` and `mutations*.py` match nothing here, so none of this round's own guards is pinned: `result.py`, `mode_binding.py`, `completeness.py`, `lint_pooling.py`, `test_round3.py`, `allowlist.py`, `round2.py`, `fixture_walk.py`, `leak_grep.py`, `build_draft.py`, `copy_manifest.py`, `study.py`, `allowlist-derivation.json` and `COPIED.json`. After a freeze any of them could be edited and `check_results.py` would stay clean. `freeze_rehearsal.py` likewise runs `test_harness.py`, `check_results.py --controls`, `check_results.py --regrade`, `regrade_environment.py` and `clean_clone_battery.sh`, none of which exists here, so no rehearsal can end `all green`. `COPIED.json` describes the `freeze.py` edit as three call sites with "No rule changes; only where each rule looks"; the pin list is not mentioned. Today this fails closed, which is why it is a blocker rather than a hole: it has to be fixed before the freeze, and the fix decides what the freeze binds.

```
$ ls study/evals/gap-study-3/test_harness.py study/evals/gap-study-3/analyse.py study/evals/gap-study-3/mutations.py study/evals/gap-study-3/clean_clone_battery.sh study/evals/gap-study-3/controls
ls: study/evals/gap-study-3/analyse.py: No such file or directory
ls: study/evals/gap-study-3/clean_clone_battery.sh: No such file or directory
ls: study/evals/gap-study-3/controls: No such file or directory
ls: study/evals/gap-study-3/mutations.py: No such file or directory
ls: study/evals/gap-study-3/test_harness.py: No such file or directory
$ grep -n "MISSING, so nothing" -A1 study/evals/gap-study-3/freeze.py
596:        print(f"\nMISSING, so nothing can pin them: {missing}")
597-        return 1
$ grep -n 'test_harness.py"\|clean_clone_battery.sh\|regrade_environment.py\|--controls"\|--regrade"' study/evals/gap-study-3/freeze_rehearsal.py
145:            step("regrade_environment.py --write (the record names the frozen file)",
155:            ("test_harness.py", [sys.executable, f"{S}/test_harness.py"]),
161:            ("check_results.py --controls", [sys.executable, f"{S}/check_results.py", "--controls"]),
162:            ("check_results.py --regrade", [sys.executable, f"{S}/check_results.py", "--regrade"]),
167:            ("test_harness.py --mutations", [sys.executable, f"{S}/test_harness.py", "--mutations"]),
168:            ("clean_clone_battery.sh --source <clone>", ["bash", f"{S}/clean_clone_battery.sh", "--source", str(clon
```

Fix: rewrite `PINNED` for this round (drop the six absent paths, add every file named above and the walks' ledgers), make `freeze_rehearsal.py` run this round's gate (the step-3 commands, `check_results.py` in the modes that exist here, `check_take.py` over the walks), record both edits in `COPIED.json`, and run the rehearsal so `verification/freeze-rehearsal-1.txt` exists before review 2. The brief names that file and it is absent.

## Blocker 3 — a take that records the wrong mode has no pre-registered disposition, and the draft describes two

The draft says two contradictory things about what happens to a take whose session records a mode other than its model's expectation. `driver_change.permission_mode_binding` says the copied checker's constant-binding rule reads the recorded mode and routes such a take as a rehearsal with reason `constant-binding`. That is false: `check_take.py:907` compares the ledger's `permission_mode`, which `drive.py:1157` sets to the flag passed, `auto`, whichever of the three models runs. `driver_constants.permission_mode_expected_why` says instead that such a take "is a rehearsal with reason `mode-drift`, read by mode_binding.py". `mode-drift` is not in `rehearsal_reasons`, which is carried byte-identical from round 2; `drive.py` never calls `mode_binding` (its two mentions are comments); `route_attempt` routes only on the checker's reason ids. So a drifting take is filed in `transcripts/` as graded, `result.py` counts it, and `mode_binding.py --check` goes red afterwards with no rule saying what to do. That is a reading chosen after the take exists, and it is on the one axis this round was built around.

```
$ python3 -c "import json;d=json.load(open('prereg.json'));print('mode-drift' in d['rehearsal_reasons'])"
False
$ sed -n 902p study/evals/gap-study-3/check_take.py; sed -n 907p study/evals/gap-study-3/check_take.py
    want_mode = pre["driver_constants"]["permission_mode"]
    if ledger.get("permission_mode") != want_mode:
$ grep -c "mode_binding\." study/evals/gap-study-3/drive.py
2
$ grep -n "mode-drift\|routed as a rehearsal with reason .constant-binding" prereg.json | cut -c1-60
1543:      "permission_mode_binding": "The driver records in each
1653:    "permission_mode_expected_why": "The mode each model's se
```

Fix: pick one disposition before the freeze and make the text and the code agree. Either the driver routes recorded-not-equal-to-expected as a rehearsal under a reason this round pre-registers in a key of its own (the carried `rehearsal_reasons` cannot gain one), or the take is graded and published with its recorded mode flagged and `mode_binding.py --check` is pre-registered as a publication gate that refuses RESULT.md. Then rewrite `permission_mode_binding` in `build_draft.py` to describe the checker as it is. Either way the freeze must not carry a sentence that names a reason no code can emit.

## Blocker 4 — the question claims one permission condition across the model axis; the design pins two

`question` ends "measured under one permission condition pre-registered for the whole model axis". `driver_constants.permission_mode_expected` pins `auto` for two models and `default` for the third, and `limitations_lines[1]` says the two larger models run under the allowlist plus auto's classifier, "the MORE PERMISSIVE of the two". So a command outside the 22 entries is denied for the smallest model and may be admitted for the other two. A difference between the smallest model's counts and the others' can still be a condition of the harness, which is the reading this round exists to rule out. The limitation admits this against round 2; the question denies it within round 3.

```
$ python3 -c "import json;d=json.load(open('prereg.json'));print(d['driver_constants']['permission_mode_expected'])"
{'claude-opus-5': 'auto', 'claude-sonnet-5': 'auto', 'claude-haiku-4-5-20251001': 'default'}
```

Two honest fixes, either sufficient to lift this. The cheaper one is text: reword `question` and `why` to say the allowlist is the shared part of the condition and the recorded modes differ by model, and add a limitations line saying a difference between the smallest model's cells and the others' may still be the classifier's. The stronger one is to pass `--permission-mode default` on the whole axis: `check_take.py:902` reads the wanted mode from `driver_constants.permission_mode`, so the byte-identical checker needs no change, `permission_mode_expected` collapses to one value, and the two larger models then need a committed walk under `default` to show the 22 entries carry their route too. I lean blocker rather than should because the sentence is the study's question, the freeze is irreversible, and the smaller fix costs one rebuild of the draft.

## Follow-ups

- **SHOULD. Denials are promised in print and nothing records them.** `driver_change.denial_outside_the_allowlist` and `limitations_lines[7]` say a denied command is published quoted beside the count. `drive.py`, `check_take.py` and `result.py` contain no reading of the harness's denial sentence, `Permission for this tool use was denied`, which the pre-study's `finding.py` and this round's battery both use. A cell at 0 of 3 because of denials would print like a cell the model failed. `grep -c "was denied"` over the three files prints 0, 0, 0. Fix in `result.py`: count and quote denials per take from its transcript and print them in a column. I lean should rather than blocker only because the five walks met no denial and `result.py` is this round's own file; if blocker 2's pin list lands first, this becomes a post-freeze code change and should be done before it.
- **SHOULD. The five committed walks were driven by the previous driver.** The walks landed at commit `23dcd1b`; the driver under review landed at `53a55a4`. Their ledgers hold the recorded mode in `permission_mode` and carry `permission_mode_recorded: null` and `permission_mode_expected: null` (`walks/scope-read/1/driver-ledger.json`). No committed session shows the ledger the current driver writes, `mode_binding.py`'s ledger-versus-transcript branch is vacuous on all five, and `test_round3.py:817` asserts the old shape. Drive one walk with the driver as it stands and commit it.
- **SHOULD. The result's caption stamps the day it was written as this round's run date.** `result.py:150` uses `date.today()`, so RESULT.md written on one day fails `result.py --check` the next, and the date is not the takes' date. Read the run dates from the takes' ledgers. Line 152 prints the earlier round's title where a commit is implied.
- **NIT. Three prose counts of the edited copies disagree.** `README.md:17` says eight files edited; `copy_manifest.py --check` prints 12; `PROGRESS.md` slice 1 says 11. The manifest is the record; fix the two sentences.
- **NIT. A live path names round 2.** `freeze_rehearsal.py:60` clones under a home folder named for round 2; the battery's path test looks only for round 2's study folder.
- **NIT. The recorded mode is read by substring over the whole transcript.** `drive.mode_recorded`, `mode_binding.mode_of` and `round2.cell_modes` regex-match `"permissionMode"` anywhere in the file, so a tool result that echoed that text would flip a reading. Nothing in the run tree carries it today; reading the field of the session's own init record would close it.
- **NIT. Three entries are compound forms the harness splits.** `Bash(cat gars/CLAUDE.md;:*)`, `Bash(cd gars;:*)` and `Bash(pwd; ls:*)` have a semicolon in their second token. If the harness splits a compound command and rules on each part, as slice 2 of `PROGRESS.md` says it does, no split part can match these and they are dead entries. They are not wider than their quoted forms, so nothing is admitted by them; they only overstate the list's size. The same caveat applies to `Bash(cd "$(git:*)`.
- **NIT. One battery test's name says the opposite of what it asserts.** `test_round3.py:222` is called `test_the_checker_reads_that_field`; it asserts the checker reads `permission_mode`, the flag, which is the arrangement the docstring says the change avoids.
- **NIT. The brief names two files that do not exist yet.** `verification/freeze-rehearsal-*.txt` (no rehearsal has run; see blocker 2) and `review_kit/rounds.json` (the register is written by its first row).

What I looked for and did not find: the allowlist has no bare binary wildcard, every entry is a verbatim prefix with its transcript and line printed, and the pinned 22 equal the derived 22; the two `arbitrary` entries are named as such in the limitations. The leak verdict is decided on path parts on both the normalised and the resolved form, and the finding about round 2's capped cell re-derives from its bytes. The 25 carried keys equal round 2's frozen values at the source commit, the three tasks are byte-identical to round 2's, the ten pinned files are byte-identical, and `export_at` carries the gars tree every round-2 take ran against. The 18 predictions derive by the stated rule, each names the file or transcripts it read, the seven with no count are exactly the six cells whose transcripts recorded `default` plus round 2's incomplete cell, and the take order is unseeded until the review commit exists. One walk covers both halves of `scope-read` and of `template-adherence` because their pre-probe scripts and fixture hashes are identical, derived by code, and `confounded-design` has one walk per half. I found no way for a single edited record to move a reading other than blocker 3, and no place two rounds' counts could be added by the code.

## The step-3 commands and the tails of their output

```
$ python3 -W ignore evals/gap-study-3/test_round3.py
Ran 113 tests in 14.141s
OK
[exit 0]
$ python3 evals/gap-study-3/copy_manifest.py --check
ok: 44 files trace to bf065feedccc, 12 edited with a reason, 10 pinned byte-identical; round 2, round 1, the pre-study and the parser unchanged
[exit 0]
$ python3 evals/gap-study-3/allowlist.py --check
ok: 22 candidate entries re-derive from 364 pre-probe call(s) in 52 transcript(s); the pre-registration pins 22, every one of them derived
[exit 0]
$ python3 evals/gap-study-3/build_draft.py --check
ok: the draft is what build_draft.py builds
[exit 0]
$ python3 evals/gap-study-3/leak_grep.py --check
  permission mode        in 5 session(s), 0 of them would be voided
ok: 24 leak word(s) grepped against 5 real session(s); none would void one
[exit 0]
$ python3 evals/gap-study-3/fixture_walk.py --check
evals/gap-study-3/walks/template-adherence/2/transcript.jsonl: clean — 7 absolute path(s), {'run-tree': 5, 'elsewhere': 2}
ok: 5 committed walk(s) graded, none names this checkout
[exit 0]
$ python3 evals/gap-study-3/mode_binding.py --check
ok, having graded 0 attempts: none is committed yet, so nothing here is evidence about any session's permission mode.
[exit 0]
$ python3 evals/gap-study-3/mode_binding.py --walks --check
  walks/template-adherence/2                     claude-haiku-4-5-20251001      passed=auto recorded=default expected=default
ok: 5 walk(s) graded, every one recording the mode its model is pinned to
[exit 0]
$ python3 evals/gap-study-3/completeness.py --check
complete cells 0 of 18; 18 unmeasured, every one of them named with a reason
not applicable — not frozen. The denominator is the frozen plan, and there is not one yet, so this green claims nothing about any cell.
[exit 0]
$ python3 evals/gap-study-3/lint_language.py evals/gap-study-3/
clean — 33 input(s) scanned, 1 excused line(s) on record
[exit 0]
$ python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/
clean — 30 file(s) and 0 commit(s) scanned, no excusal path
[exit 0]
$ python3 evals/gap-study-3/prereg.py --status
n        : 3  -> 54 planned takes
take order: not yet — seeded at the freeze
This is a DRAFT. No take may run against it and no number may be graded from it. The walks are what turn it into the frozen file.
[exit 0]
$ python3 evals/gap-study-3/takes.py --plan
planned 54 takes
registered so far: 0
[exit 0]
$ python3 evals/gap-study-3/review_kit/rounds.py --check
ok, having graded 0 rounds: the register is empty, so nothing here is evidence about any round. Prompt pinned at 0910589c8290.
[exit 0]
```

Also run, not in the brief: `fixture_walk.py --coverage` (every task covered; one walk suffices for two of the three tasks, derived from identical pre-probe scripts and fixture hashes) and `fixture_walk.py --finding` (`ok: the finding re-derives from round 2's own bytes`).

## Every finding, classified

| # | Finding, in my words | Class | Would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|
| 1 | RESULT.md prints the number of graded takes under `held`; the graders' `k` is never read | BLOCKER | A claim: every complete cell's published count |
| 2 | The freeze's pin list and rehearsal are round 2's; six pins are absent so the freeze refuses, and none of this round's own guards is pinned | BLOCKER | A reading: what the freeze binds, and whether a post-freeze edit to a guard is visible |
| 3 | A take recording an unexpected mode has no disposition in code, and the draft describes two, one naming a reason that does not exist | BLOCKER | A criterion: how such a take is routed and counted |
| 4 | The question claims one permission condition across the model axis while the design pins `auto` for two models and `default` for one | BLOCKER | A claim: what a difference between the smallest model and the others may be said to show |
| 5 | Denials are promised beside each count and nothing records or prints them | SHOULD | A claim: whether a 0 of 3 is read as the model's or the harness's |
| 6 | The committed walks were driven by the previous driver, so the current ledger shape is unexercised on a real session | SHOULD | Neither; it verifies the driver that will run |
| 7 | The result caption stamps the writing date as the run date and breaks its own `--check` a day later | SHOULD | A claim: the run date printed per column |
| 8 | Three prose counts of the edited copies disagree | NIT | Neither |
| 9 | A live clone path names round 2 | NIT | Neither |
| 10 | The recorded mode is read by substring over the whole transcript | NIT | Neither today; a reading only if a tool result echoed the field |
| 11 | Three compound-form entries can match nothing if the harness splits on `;` | NIT | Neither; they admit nothing |
| 12 | A battery test's name contradicts what it asserts | NIT | Neither |
| 13 | The brief names a rehearsal record and a register that do not exist yet | NIT | Neither |
