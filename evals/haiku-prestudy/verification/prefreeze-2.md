prereg.json sha256: 3d4ed66a2a673feb39ade6cfb3fc7802c6ab008aaf47031bb20e6601451c3c5e

# Pre-freeze review 2: the Haiku pre-study

**Ruling: DO FREEZE.**

Reviewed at the commit named in `COMMIT` (`b353706`). `shasum -a 256 prereg.json` prints the digest on line 1, and `diff prereg.json study/evals/haiku-prestudy/prereg-draft.json` prints nothing. Every path below is relative to this folder. Every command in this report was run from inside `study/` unless shown otherwise, nothing under `study/` was changed, and `git -C study status --short` printed nothing afterwards.

## What changed since review 1

```
$ diff <(python3 -m json.tool prereg-as-the-previous-review-read-it.json) <(python3 -m json.tool prereg.json)
194c194
<         "why": "... So both entries are needed for Haiku to walk the route the other two models walked, and neither admits a program the stage does not already run.",
---
>         "why": "... So both entries are needed for Haiku to walk the route the other two models walked. The stage 00 contract names only python3; echo is a form Opus added in round 2 (`echo \"exit=$?\"` in each of its three takes of this cell), so neither entry admits a program beyond those Sonnet and Opus ran before the probe on this cell. Bash(echo:*) also admits `echo ... > file`; a write it makes outside the take's own folders is caught by take.py's postflight.",
```

One field changed, `driver_change.why`, which is review 1's follow-up 4 taken. Its first two new sentences are what the bytes show (confirmed below). Its third sentence claims more of the postflight than the code does; that is follow-up 1.

The code changed in one commit since review 1 (`a614fde`, twelve files: the outcome reader's denial tag, the result's binding and attempt sections, the take-order check in `take.py`, the driver-argv probe, the tests for each) and HEAD (`b353706`) adds only `verification/freeze-rehearsal-5.txt`. That record opens with this draft's sha256 and `code sha256: cb210138d7d9…`; `freeze.code_sha256()` computed on the files as committed prints the same value, and its last line is `all green`, so `freeze.py`'s rehearsal rule admits these draft bytes and this code.

## The threat model

What the checks bind: the driver is round 2's at `bf065fe` plus three added hunks and no removed line, every other copy is byte-identical or carries its reason, every rule a take is held to is round 2's frozen value byte for byte and the half is round 2's; the checkout is exported from `844a4ce`, whose content outside the pre-registered exclusions equals the three checkouts round 2's Haiku takes of this cell ran in and whose gars tree is the pinned one, re-read by the driver before each session opens; a take's session id is a function of a committed ledger row, take k opens only when takes 1 to k-1 are graded, the attempt is routed by the checker's verdict and committed as it stands; the outcome is read by code from the take's own ledger and transcript in a fixed reason order; the result refuses code the freeze did not pin or a ledger with another allowlist, and prints counts with round 2's cells beside them. What they cannot bind: that the harness applied the allowlist inside a take (no session record carries it; the ledger's `allowed_tools` is the driver's own word and the evidence is the absence of denials), which permission mode the harness runs the session under (the allowlist was probed only in sessions recording `default`, and round 2's Haiku take 3 of this cell recorded `auto` and was denied the same command), that the model behind the id is round 2's, and anything done in public git history after the takes exist, since the raw session file never enters the repository and a graded folder deleted and its row re-driven is visible only as commits.

`limitations_lines` says this honestly: line 1 names the mode question and the `auto` denial, line 2 names that `Bash(python3:*)` is unrestricted Python and states the postflight at its true scope (the study repository), line 3 the count of three, line 4 the classifier's origin, line 5 the date. `driver_change.denial_outside_the_allowlist` commits in advance to reading any further denial as a harness condition with the command quoted, and `outcome.py` applies that before any other reason. Two things the statement does not say: that nothing in a session file records the allowlist, so its application is evidenced only by the stage commands running without a denial (unstated since review 1, follow-up 7), and, in the new sentence of `driver_change.why`, that the postflight reads only the study repository (follow-up 1). Neither can move a reading. Every finding below is ruled against this statement.

## Blockers

None. I looked for a way a single edited record or a misfiled attempt could move a reading and did not find one. The session id is fixed by the row commit before the session opens; `drive.py:1052-1060` refuses a graded folder that exists and a row already attempted; `take.py:89-91` refuses a take that is not next in the pre-registered order and `take.py:136-145` refuses to commit when anything outside the attempt folders changed; `outcome.py` takes a folder and nothing else, and `result.py` refuses when any pinned file or any ledger's allowlist differs from the frozen file. What remains needs public commits (an edited driver committed and reverted, a graded folder deleted and re-driven, a transcript edited before its commit). Each is a limitation the threat model names, and each has a cheap check listed below.

## Follow-ups (worth fixing, not blocking)

1. **The new sentence in `driver_change.why` overstates the postflight.** `prereg.json:194`, built by `study/evals/haiku-prestudy/build_draft.py:126-128`, says a write `echo` makes "outside the take's own folders" is caught by take.py's postflight. `study/evals/haiku-prestudy/take.py:136-145` diffs the study repository's git status before and after the drive and nothing else; a write anywhere else on the machine is not read, for `echo` and for `python3` alike, which limitations line 2 says correctly. This is a statement, not a reading: nothing the session writes can reach the attempt, which sits in a temporary directory until the driver routes it. I lean follow-up because the same file's limitations line 2 states the guard's scope exactly and a reader has both. If the draft is rebuilt for any other reason before the freeze, reword it to "a write into the study repository outside the attempt folders is caught"; after the freeze it is an amendment.

   ```
   $ sed -n 136,139p evals/haiku-prestudy/take.py
       after = status()
       changed = sorted(after - before)
       # --untracked-files=all lists files, never folders, so a prefix test is exact.
       outside = [c for c in changed if not c[3:].startswith(ATTEMPT_DIRS)]
   ```

2. **`TheDriverHasOneDiff` admits an added top-level line.** `study/evals/haiku-prestudy/test_prestudy.py:80` classifies an added line as prose when it begins with a letter, a backtick or `(`, so a one-line top-level statement appended to the driver reads as prose and the test passes. Replicating the test's own logic on an in-memory copy of `drive.py` with one line appended near the end of the module (no file written):

   ```
   as committed: passes (9 added lines, 2 code)
   with 'PERMISSION_MODE = "default"' appended: passes
   with 'ISOLATION_FLAGS = ()' appended: passes
   with 'STRIPPED_ENV = ()' appended: passes
   with 'import os as _o; _o.environ["X"]="1"' appended: passes
   ```

   The first is caught by `TheDriverPassesTheAllowlist`; the other three by nothing in the suite. Backstops: the freeze pins `drive.py`'s sha256 and `result.py:74-77` refuses at result time, and `take.py:100-106` requires a clean tree even with origin, so the edit would be a public commit. A guard that reads less than it claims; exploitation is limitation-class. Cheap close: assert the added lines are exactly the seven docstring lines and the two code lines, by content.

3. **Pinned files are checked at result time, not at take time.** `study/evals/haiku-prestudy/take.py:88-109` checks the harness version, the reservation, the root `CLAUDE.md`, a clean tree and parity with origin, but not that the seventeen files in `prereg.json`'s `pinned_files` still hash as frozen; `result.py:69-82` checks them only when the result is written. Between the two, a committed edit drives the takes and a committed revert restores the hashes, both public. The same preflight could refuse a row whose session id already appears anywhere in the repository's history: `drive.py:1052-1060` and `takes.py:130-146` read the attempt folders, not the history, so a graded folder deleted in one commit makes its row look unattempted.

   ```
   $ grep -n "pinned_files" evals/haiku-prestudy/take.py evals/haiku-prestudy/result.py
   evals/haiku-prestudy/result.py:74:    for f, sha in (pre.get("pinned_files") or {}).items():
   ```

4. **`result.py` lists graded folders without the ledger check.** `study/evals/haiku-prestudy/result.py:53-55` takes every numeric folder under `transcripts/<task>/<half>/<model>/`. `check_results.py --ledger`, which binds each folder to its row, kind and session id, is run by neither `result.py`, the rehearsal (`freeze_rehearsal.py`), nor CI: `study/.github/workflows/ci.yml:186-201` runs `check_take.py` per transcript with the row the ledger names for itself, and `result.py --check`; the `--ledger` steps at `ci.yml:89` and `ci.yml:144` are round 1's and round 2's. `check_take.py` does bind the session id to the row commit, so a foreign folder fails CI after a push. Note also that the copied `check_results.py:163-164` and `:237` read `pinned_files` as a list of records with a `path`, and this study's `freeze.py:140` writes it as a name-to-hash map, so the copied frozen-content check would not read this study's frozen file as it stands. Cheap close: `render()` calls `check_results.check_ledger()` and refuses on any problem.

   ```
   $ grep -n "check_ledger\|check_results" evals/haiku-prestudy/result.py evals/haiku-prestudy/freeze_rehearsal.py
   (nothing)
   ```

5. **`README.md` says three copies differ; `COPIED.json` records four.** `study/evals/haiku-prestudy/README.md:16` lists `drive.py`, `study.py` and `prereg.py`; `review_kit/blindness.py` is the fourth edited copy, with its reason in the manifest.

   ```
   $ grep -c '"edited": true' evals/haiku-prestudy/COPIED.json
   4
   ```

6. **The published harness range is not read from the ledgers.** The carried `harness.version_range_note` says the published range is read from the takes' own ledgers; `result.py` prints nothing from each ledger's `claude_version`. `take.py:92-94` refuses a version other than the frozen one, but the driver run alone does not. Cheap: one column in the per-take table.

7. **A limitations line for the allowlist's evidence.** Nothing in a session file records `--allowedTools`: the probes' `system/init` records carry the model, the mode and a tool count only. A take's `allowed_tools` is the driver's own ledger entry, and the evidence that the harness applied it is that the stage commands ran without a denial. Review 1 named this; the follow-ups taken bind the ledger to the pre-registration but the frozen file still does not say it.

## What was confirmed

- **One change (step 5).** `diff <(git -C study show bf065fe…:evals/gap-study-2/drive.py) study/evals/haiku-prestudy/drive.py` prints three added hunks and no removed line: the docstring paragraph at 56-62, `argv += ["--allowedTools", *prereg.load()["driver_change"]["allowed_tools"]]` at 621, `"allowed_tools": list(pre["driver_change"]["allowed_tools"])` at 1114. `study.py` differs in seven name and marker constants, `prereg.py` in the one line of `cells()` that reads only the halves a task lists, `review_kit/blindness.py` in adding this study's goal id and keeping round 2's; each matches its reason in `COPIED.json`, and the other ten copies are byte-identical. Compared directly against `git show bf065fe…:evals/gap-study-2/prereg.json`: all 21 carried keys equal round 2's frozen values, the task equals round 2's minus its control half, and `leak_words` is round 2's list plus the four added. `git diff --quiet 844a4ce <c> -- . ':(exclude)…'` exits 0 for each of `58cfd3b`, `a4bcecd`, `844a4ce`, and round 2's three Haiku ledgers of this cell record exactly those three as `run_tree_built_from`; `git rev-parse 844a4ce:gars` prints the pinned tree `8a54e0f8…`. The session namespace differs from round 2's.

- **Allowlist size (step 6).** Re-derived from round 2's nine transcripts of this cell with the shared parser: before the probe, Sonnet and Opus used `Bash` and `Read` (one `ToolSearch`), no `Write` or `Edit`; the first words of their Bash commands were `cat`, `cd`, `find`, `grep`, `ls`, `pwd`, `python3`, `sed`; Opus ran an `echo` in each of its three takes (5, 4 and 4 commands), Sonnet in each of its three (2 each). Reading each of the eighteen per-form probe sessions: under `Bash(python3:*)` alone, form 1 (`…; echo "exit=$?"`) is denied and forms 2 to 9 ran verbatim; with `Bash(echo:*)` added all nine ran verbatim; the all-nine session ends at form 1's denial; the driver-argv session (both entries followed by `--session-id`, the driver's own environment) ran form 1 with no denial. The stage 00 contract at `844a4ce` names six commands, all `python3 _system/stage00_register.py …`. Both entries are needed for the walked route; neither admits a program beyond those the other two models ran before the probe on this cell; a denial outside them reads `did not reach`, `harness denial`, with the command quoted, which is the honest reading. `finding.py --check` re-derives every count above.

- **Outcome by code (step 7).** `outcome.py` reads only `driver-ledger.json` and `transcript.jsonl`. `reached the probe` needs the ledger's non-recovery row for turn 3 with the probe line as sent and a user turn carrying that line verbatim followed by an assistant turn with text the harness did not write; otherwise `harness denial` (the sentence in a tool result, or the harness's `toolDenialKind` tag), then `asked` (round 2's classifier by path, only on a stopped take, only the final agent message, harness records skipped), then `other` with the driver's outcome quoted. That is the order `outcomes` states; `test_order_is_the_prereg_order` reads it back from the file and `TheOutcomeReasonOrder` holds the grid. On round 2's nine takes it reads Haiku's three as `harness denial` (each a denial of `… python3 _system/stage00_register.py assays`, each tagged once) and the six others as `reached`. A reply to the probe with no text reads `did not reach (other: …)` with the driver's outcome printed, as the outcomes text says. No argument, flag or field lets a person choose a reading.

- **Predictions and publication (step 8).** Three predictions, each `reached the probe`, `informed_by_round_2: true`, one stated rule, written by `build_draft.py:156-162` and so fixed before any take. `result.py` prints per take the outcome, reason, denials, ask phrases, recorded mode, the ledger's allowlist and round 2's grader label under a heading that says it is for information; counts of three with no rate and no verb about the model; every rehearsal and pause with its reason ids and the `incomplete — mechanical` line at the cap; round 2's twelve Haiku cells from `analysis.json` under a heading that names the changed driver and says they are not added; the limitations lines. It refuses a pinned file or a ledger allowlist that differs from the frozen file.

- **Trying to break it (step 9).** Re-run: the row commit fixes the session id, `drive.py` refuses an existing graded folder or an attempted row, `takes.py --add` refuses a slot that is registered or graded, a take index outside 1..n, a row registered while an earlier one is unattempted, and a cell at its rehearsal or pause cap. Re-route: `route_attempt` decides by the checker's verdict against the pre-registered reason list and refuses an unlisted reason. Re-read: `outcome.py` has no switch. Re-file: `take.py` commits only the attempt folder the driver routed, and refuses when anything else changed. What remains needs public commits and is listed above with its cheap check.

## The study's own checks (step 3), run from inside `study/`

```
$ python3 -W ignore evals/haiku-prestudy/test_prestudy.py
.....................
----------------------------------------------------------------------
Ran 21 tests in 9.796s

OK

$ python3 evals/haiku-prestudy/copy_manifest.py --check
ok: 14 files trace to bf065feedccc, 4 edited with a reason; round 2, round 1 and the parser unchanged

$ python3 evals/haiku-prestudy/finding.py --check
  "forms_denied": {
    "Bash(python3:*)": [
      1
    ],
    "Bash(python3:*) Bash(echo:*)": []
  },
  "forms_run": 9,
  "all_nine_in_one_session_denied": true
}
ok: the finding re-derives from the bytes

$ python3 evals/haiku-prestudy/build_draft.py --check
ok: the draft is what build_draft.py builds

$ python3 evals/haiku-prestudy/lint_language.py evals/haiku-prestudy/
clean — 7 input(s) scanned, 0 excused line(s) on record

$ python3 evals/haiku-prestudy/prereg.py --status
in force : prereg-draft.json
frozen   : False
status   : DRAFT. Changes until the freeze; nothing may be run or graded against it.
tasks    : 1  (number-fidelity)
models   : 1 in the fixed list, 1 running
           claude-haiku-4-5-20251001    runs
n        : 3  -> 3 planned takes
take order: not yet — seeded at the freeze

This is a DRAFT. No take may run against it and no number may be graded from it. The walks are what turn it into the frozen file.

$ python3 evals/haiku-prestudy/takes.py --plan
tasks   1  number-fidelity
models  1 in the fixed list, 1 running
        claude-haiku-4-5-20251001    runs
n       3 graded takes per half per model, no retakes
planned 3 takes
registered so far: 0
```

Every command exited 0. `git -C study status --short` printed nothing afterwards.
