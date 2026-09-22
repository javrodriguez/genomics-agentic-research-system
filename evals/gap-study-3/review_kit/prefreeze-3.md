prereg.json sha256: 026a0d216f04b21b72611b138202d80c2c0952eaf27bf55f55efb04c65a606f4

# Pre-freeze review 3

**Ruling: DO NOT FREEZE.**

`diff prereg.json study/evals/gap-study-3/prereg-draft.json` prints nothing. The study checkout is at the commit named in `COMMIT`. Every command in the brief's step 3 exits 0 and their tails are in the last section.

## The threat model

What this round's checks bind: which bytes ran (the source commit, the derived pin list, the export commit whose `gars` tree equals round 2's pinned tree), that each take's row was committed before its session opened (the session id is a function of the row's commit), that the take checker, every grader and the label reader are round 2's bytes, that the ledger's `permission_mode` is what the session's own transcript recorded and not the flag passed, that each published count is a grader's count of three per planned cell, and that no published sentence adds the two rounds together. What they cannot bind: that the harness applied the allowlist (no session file records it, so the only evidence is the absence of a denial), that the mode a session recorded is the mode the harness enforced, that the model behind an id is the one round 2 measured, and that a path outside the regex's fixed roots would be seen by the fixture-walk verdict at all.

The `limitations_lines` say the first three of those honestly (lines 3, 9 and 7), `not_poolable` is honest and is enforced structurally by `result.py`, and `driver_change` is honest about the width of the list (limitation 4 says the two `arbitrary` entries are as wide as a bare binary). Two things the same statement promises are not delivered by the pinned code, and one thing it says about itself is false. Those are the blockers below. Every later finding is ruled against that statement.

## What was checked and holds

- **The previous review's copy against this one.** Every change is Ruling 7 (`auto` becomes `default` across the axis, the question rewritten to say so, limitation 2 rewritten from more to less permissive, `permission_mode_round_2` kept beside the new value) and the dropped leak word `permission mode` with its reason. Nothing else moved.
- **Byte-identical files.** `copy_manifest.py --check` re-derives 44 files from `bf065fe`; the take checker, all six graders, the label reader, the language linter and the commit-message guard have `copy_sha256` equal to `source_sha256` in `COPIED.json`.
- **Carried keys and the system under test.** The 25 keys in `carried_from_round_2` equal round 2's frozen values (`test_it_carries_round_twos_keys_byte_for_byte`). `git rev-parse 844a4ce:gars` and `bf065fe:gars` both print `8a54e0f8…`; `HEAD:gars` prints `e77b9031…`, so the export commit is deliberately not HEAD and the takes run against round 2's tree.
- **The allowlist is derived.** Every one of the 22 entries is a verbatim prefix of a command in a named round 2 transcript at a named line; no entry is a bare binary; the pinned list equals the derivation; 118 refused-by-construction calls are printed, never dropped.
- **The leak verdict is by code at path boundaries** (`under()` compares parts on the normalised and the resolved form), and the seven walks name only run-tree paths plus two harness task-output files.
- **Predictions** are derived by the stated rule, each naming round 2's results file or transcripts, seven of them null with a reason, all fixed in the draft before any take.
- **Publication.** `result.py` reads the held count from the graders' output, prints the take count in its own column, enumerates the 18 cells from the plan rather than from disk, prints round 2 in a separate table under a code-written caption, and checks structurally that every `k of n` has n = 3 in exactly one round's table. It refuses against a draft.
- **The round register.** Row 2 is closed as spent without work with its reason; row 1's report and blindness record are committed. This review's own row is not in the snapshot, as expected, since the row is committed after the kit is built.

## Blocker 1 — the pre-registered disposition for a mode-drifting take is a record the pinned ledger check refuses

`driver_change.permission_mode_binding` (`prereg.json:825`) says a take whose session records anything other than `default` is routed as a rehearsal with reason `constant-binding`. `driver_decided_reasons` (`prereg.json:1573`, a carried key) lists `constant-binding` as a reason the driver decides before a model runs, and the ledger check refuses any rehearsal that records one:

```
$ sed -n 733,740p study/evals/gap-study-3/check_results.py
        cannot = sorted(set(reasons) & set(prereg.load().get("driver_decided_reasons") or []))
        if cannot:
            problems.append(f"row {i}: the rehearsal records reason(s) {cannot}, which the driver decides "
                            f"before or without a model and refuses to run under, so it cannot have "
                            f"written this record")
```

The same check then re-runs the take checker on a normalised ledger, and the normalisation puts the constant back:

```
$ sed -n 542p study/evals/gap-study-3/check_results.py
    out["permission_mode"] = pre["driver_constants"]["permission_mode"]
```

So an honest drift (the transcript really records another mode) is refused twice: once as a reason the driver cannot have written, and once as a refusal that "disappears when the ledger's driver-written fields are read as the driver writes them", which is the ledger-edit finding. The driver routes it there regardless (`study/evals/gap-study-3/drive.py:835-842` routes any checker refusal to `rehearsals/` by its reason ids, and `constant-binding` is in `rehearsal_reasons`).

Under round 2's meaning the two statements agreed: `permission_mode` was a constant, so a rehearsal carrying `constant-binding` could only come from an edited ledger. Ruling 7 made the field a session reading and left the carried refusal in place. The result is that the only route the design gives a drifting take ends in a red ledger check, so the round cannot reach DONE with such a take on record, and the honest publication the purpose asks for (a cell unmeasured with its reason) is not producible for this case. The `driver_decided_reasons_note` already admits this shape for `outcome-binding` ("would have no route"); it does not admit it for the case this round pins as its disposition.

This is a defect, not a limitation: it needs no fabricated record, only a session that records a mode other than `default`. It has not fired on any committed walk because the two walks under `default` recorded `default`.

**Fix before the freeze**, in one of two ways, and the frozen text must say which:

- Take `constant-binding` off `driver_decided_reasons` for this round (recording the edit to the carried key with its reason), and make `_normalised_ledger` re-derive `permission_mode` from the transcript the way `drive.mode_recorded` does, rather than resetting it to the constant. Then an edited `permission_mode` is still caught (the re-run reads the transcript, the refusal disappears, the rehearsal is refused as ledger-made) and an honest drift survives. A battery test should drive both cases on synthetic input.
- Or state in `permission_mode_binding` that such a take has no route and blocks the round, as the note does for `outcome-binding`. This is honest but leaves the smallest model's six cells hostage to a harness behaviour round 2 already observed 34 times.

Fixing it changes a reading: which records are admissible after a take runs.

## Blocker 2 — denials are promised beside every take and nothing pinned can read one

`driver_change.denial_outside_the_allowlist` (`prereg.json:824`) says a denial "is published as such with the denied command quoted" and that a take's "denials are printed beside it". Limitation 8 repeats it. The harness writes a denial as the sentence `Permission for this tool use was denied` into the tool result; 36 of round 2's transcripts of the smallest model carry it, and the pre-study's `outcome.py` reads it. Nothing in this round does:

```
$ grep -c -i "denied" study/evals/gap-study-3/result.py study/evals/gap-study-3/run.py study/evals/gap-study-3/check_take.py study/evals/gap-study-3/completeness.py
study/evals/gap-study-3/result.py:0
study/evals/gap-study-3/run.py:0
study/evals/gap-study-3/check_take.py:0
study/evals/gap-study-3/completeness.py:0
```

The only reader is a test over the walks (`test_round3.py:851`, `test_no_walk_met_a_denial`), which grades walks and not takes. `result.py`'s row has no denial column (`study/evals/gap-study-3/result.py:238-244`), and the driver's ledger records no denial per turn.

Why it matters: a take whose route meets a denial and then stops short of the probe is graded `did-not-reach`, a reading of the model, with nothing beside it saying the harness refused a command. That is the exact shape the pre-study found in round 2 and the reason this round exists. `result.py` is pinned at the freeze, so the column cannot be added afterwards.

**Fix before the freeze:** a denial reader in `result.py` (or a small module it imports) that reads each graded take's tool results for the harness's own sentence, prints per cell the count of denied calls and quotes the commands, and a battery mutation that drives it on a synthetic transcript carrying one denial. Fixing it changes a claim: what the published table says about a cell.

## Blocker 3 — the record of the driver change misstates the one thing the round changes

The brief's step 5 asks whether the driver differs from round 2's only by what its docstring names and whether each edited copy is what its reason says. Neither holds:

```
$ sed -n 57,58p study/evals/gap-study-3/drive.py
THE CHANGES FROM ROUND 2'S DRIVER. This file is a byte copy of evals/gap-study-2/drive.py at bf065fe
with four changes, and nothing else moves:
$ sed -n 64p study/evals/gap-study-3/drive.py
     working permission condition. `--permission-mode auto` is still passed.
$ sed -n 131p study/evals/gap-study-3/drive.py
PERMISSION_MODE = "default"
```

The docstring's numbered list names four changes and says `auto` is still passed; the diff against `bf065fe:evals/gap-study-2/drive.py` shows a fifth executable change, `PERMISSION_MODE = "auto"` to `"default"`, which is named only in a comment at line 126 and inside change 2's Ruling 7 paragraph. `COPIED.json:22` opens "Three changes", lists four numbered (1), (2), (4), (3), and describes the superseded Ruling 2 design for change 2: "permission_mode keeps round 2's meaning, so the byte-identical checker keeps reading what round 2's did; the recorded mode is asserted by this round's own mode_binding.py against the per-model expectation". The driver does the opposite (`drive.py:1401`, `ledger["permission_mode"] = recorded`), and the pre-registration's own `driver_constants_note` says so. `README.md:33` says "three changes". `copy_manifest.py --check` passes because it compares the reason string in `copy_manifest.py:94-108` with the one it wrote into `COPIED.json`, not with the code.

These are the two files a reader is told to open to learn what changed, both are pinned at the freeze, and on the one variable of the round they say the wrong flag and the wrong ledger semantics. I lean blocker rather than follow-up because the freeze is irreversible and the fix touches no criterion, no reading and no code path: rewrite the docstring's list to five changes with the mode flag named, update the reason in `copy_manifest.py` and regenerate `COPIED.json`, and correct `README.md`. Fixing it changes a claim about the design, not a count.

## Follow-ups

**SHOULD**

- **The result caption's "run date" is the write date, and `--check` goes red the next day.** `study/evals/gap-study-3/result.py:176` writes `date.today()` into the caption; `result.py:294` compares `RESULT.md` with a fresh render, so a page written on one day fails `--check` on the next and the only way to green is to rewrite it with a later date. Derive the date from the takes' ledgers (`started` of the first and last graded take) and print that. Fixing it changes a caption, not a count; `result.py` is pinned, so it must land before the freeze.
- **The fixture-walk verdict binds the study root to wherever the checker runs.** `study/evals/gap-study-3/fixture_walk.py:91` (the `study_roots` function) takes the study roots from the file's own location and `:61` limits absolute paths to seven fixed roots. A walk naming the operator's real checkout classifies as `elsewhere`, and passes, when the check runs in CI, in the rehearsal clone, or in a review copy like this one. Today's seven walks carry no such path (the `--check` output shows only `run-tree` and two harness task-output files), and the take checker's `read-outside-the-checkout` rule refuses any outside path wherever it runs, so no reading changes. Make any path that is neither run-tree nor system a failure of the verdict, or bind the root to a value the ledger records. Fixing it changes no reading today.
- **`not_poolable.enforced_by` names a commit-body scan the round does not run.** `prereg.json:1190` says "every commit body since the kickoff"; `.github/workflows/ci.yml:268` scans since the freeze, and the since-kickoff scan prints two findings (`lint_pooling.py --commits-since ddf12ebc…` prints `2 finding(s) across 0 file(s) and 23 commit(s)`), which `verification/commit-body-note.md` explains. The frozen text should say "since the freeze" and name the note. Fixing it changes a claim about enforcement.
- **`mode_binding.py` compares the transcript with `permission_mode_recorded` only.** `study/evals/gap-study-3/mode_binding.py:105-107` never reads `permission_mode`, the field the copied checker actually compares. An edit to `permission_mode` alone leaves this check green; today the ledger check catches that edit only through the refusal Blocker 1 asks to remove, so the fix for Blocker 1 should add `permission_mode` to this comparison. Fixing it changes a reading only together with Blocker 1.

**NIT**

- **Two entries end in a semicolon and one admits `find -exec`.** `prereg.json:794-796` pins `Bash(cat gars/CLAUDE.md;:*)`, `Bash(cd gars;:*)` and `Bash(find .:*)`. Each is a verbatim prefix, so the derivation's rule holds lexically, but a semicolon-terminated prefix admits whatever follows the semicolon, and `find .` admits `-exec`. In practice moot: `Bash(python3 -c:*)` already admits any program and limitation 4 says so. Worth one more clause in that limitation.
- **The mode is read by a regex over the whole transcript text.** `drive.py:523`, `mode_binding.py:55` and `round2.py:160` match `"permissionMode": "<word>"` anywhere; the field sits in user-type records, which are also the transport for tool results, so a tool result echoing that JSON would count. Read the field from the record instead. No committed session shows the case.
- **No walk on the smallest model was driven with `default` passed.** Its four walks passed `auto` and recorded `default`; the two `default` walks are on the larger models. The zero-denial claim for that model under this round's exact argv rests on those four walks plus the pre-study. One walk on `scope-read` or `confounded-design`, both under their cap, would close it.

## The study's own checks (step 3), from inside `study/`

```
$ python3 -W ignore evals/gap-study-3/test_round3.py
Ran 125 tests in 49.194s
OK
$ python3 evals/gap-study-3/copy_manifest.py --check
ok: 44 files trace to bf065feedccc, 13 edited with a reason, 10 pinned byte-identical; round 2, round 1, the pre-study and the parser unchanged
$ python3 evals/gap-study-3/allowlist.py --check
ok: 22 candidate entries re-derive from 364 pre-probe call(s) in 52 transcript(s); the pre-registration pins 22, every one of them derived
$ python3 evals/gap-study-3/build_draft.py --check
ok: the draft is what build_draft.py builds
$ python3 evals/gap-study-3/leak_grep.py --check
  allowlist              in 7 session(s), 0 of them would be voided
ok: 23 leak word(s) grepped against 7 real session(s); none would void one
$ python3 evals/gap-study-3/fixture_walk.py --check
evals/gap-study-3/walks/template-adherence/2/transcript.jsonl: clean — 7 absolute path(s), {'run-tree': 5, 'elsewhere': 2}
ok: 7 committed walk(s) graded, none names this checkout
$ python3 evals/gap-study-3/mode_binding.py --check
ok, having graded 0 attempts: none is committed yet, so nothing here is evidence about any session's permission mode.
$ python3 evals/gap-study-3/mode_binding.py --walks --check
  walks/template-adherence/3   claude-sonnet-5   passed=default recorded=default expected=default
  walks/template-adherence/4   claude-opus-5     passed=default recorded=default expected=default
5 walk(s) superseded: driven under a condition the design has since replaced, named here and never silently dropped.
ok: 2 walk(s) graded, every one recording the mode its model is pinned to
$ python3 evals/gap-study-3/completeness.py --check
complete cells 0 of 18; 18 unmeasured, every one of them named with a reason
not applicable — not frozen. The denominator is the frozen plan, and there is not one yet, so this green claims nothing about any cell.
$ python3 evals/gap-study-3/lint_language.py evals/gap-study-3/
clean — 42 input(s) scanned, 1 excused line(s) on record
$ python3 evals/gap-study-3/lint_pooling.py evals/gap-study-3/
clean — 39 file(s) and 0 commit(s) scanned, no excusal path
$ python3 evals/gap-study-3/prereg.py --status
in force : prereg-draft.json
frozen   : False
n        : 3  -> 54 planned takes
take order: not yet — seeded at the freeze
$ python3 evals/gap-study-3/takes.py --plan
planned 54 takes
registered so far: 0
$ python3 evals/gap-study-3/review_kit/rounds.py --check
1 row(s) closed as spent without work (a rate limit or an interruption before the first agent turn). Not voids: they do not count against the two-void rule.
ok: 1 registered round(s) graded, every report committed, 0 voided; prompt pinned at 0910589c8290
```

Also run, read-only: `lint_pooling.py --commits-since ddf12ebc…` (two findings, both pre-freeze commit bodies, as the note records), `fixture_walk.py --replay` on each walk, `git rev-parse` on the three `gars` trees, and `diff` of the driver against `bf065fe`.

## Closing table

| # | Finding | Class | Would fixing it change a criterion, a reading or a claim? |
|---|---|---|---|
| 1 | A take whose session records a mode other than `default` is routed to a rehearsal with reason `constant-binding`, and the pinned ledger check refuses that rehearsal twice as a record the driver cannot have written. The design's one disposition ends in a red gate. | BLOCKER | A reading: which records are admissible after a take runs. |
| 2 | The pre-registration promises every take's denials printed beside it with the command quoted; no pinned code reads a denial, and `result.py` has no column for one. | BLOCKER | A claim: what the published table says about a cell whose route met a denial. |
| 3 | The driver's docstring says `auto` is still passed and names four changes; the code passes `default` in a fifth. `COPIED.json` and the README say three changes and describe the superseded semantics of `permission_mode`. | BLOCKER | A claim about the design; no criterion and no reading. |
| 4 | The result caption's run date is the write date, so `result.py --check` fails the day after `RESULT.md` is written. | SHOULD | A caption; no count. |
| 5 | The fixture-walk verdict takes the study root from the checker's own location, so a walk naming the real checkout reads clean when checked elsewhere. | SHOULD | No reading today; the take checker still refuses the path. |
| 6 | `not_poolable.enforced_by` names a since-kickoff commit scan that CI does not run and that fails on two pre-freeze commits. | SHOULD | A claim about enforcement. |
| 7 | `mode_binding.py` checks `permission_mode_recorded` against the transcript but not `permission_mode`, the field the copied checker reads. | SHOULD | A reading, only together with finding 1. |
| 8 | Two allowlist entries end in a semicolon and `find .` admits `-exec`; lexically derived, semantically wide, and moot beside `python3 -c`. | NIT | A limitation's wording. |
| 9 | The permission mode is read by a regex over the whole transcript rather than from the record's field. | NIT | Nothing on any committed session. |
| 10 | No walk on the smallest model was driven with `default` passed. | NIT | Nothing; one walk would add evidence. |
