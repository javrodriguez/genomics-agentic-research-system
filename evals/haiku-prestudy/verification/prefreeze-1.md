prereg.json sha256: 4c3926975bb40f78819e4e2c56456d85f12069c4e44ba32f4fc863aaca4fc520

# Pre-freeze review 1: the Haiku pre-study

**Ruling: DO FREEZE.**

Reviewed at the commit named in `COMMIT` (`7c4adfc`). `diff prereg.json study/evals/haiku-prestudy/prereg-draft.json` prints nothing. There is no `prereg-as-the-previous-review-read-it.json`; this is review 1. Every path below is relative to this folder.

## The threat model

What the checks bind: that the driver is round 2's at `bf065fe` plus three added hunks (a docstring paragraph, one argv line, one ledger key), that every rule a take is held to is round 2's frozen value byte for byte, that the checkout is the content round 2's three Haiku takes of this cell ran in with the same gars tree, that each take's session id is a function of a committed ledger row, that the outcome is read by code from the take's own ledger and transcript in a fixed reason order, and that the freeze admits only these draft bytes and this code after a green rehearsal. What they cannot bind: that the harness honoured the allowlist inside a take (no session record carries `--allowedTools`; the ledger's `allowed_tools` is the driver's own word, and the evidence is the absence of denials), which permission mode the harness will actually run under (the allowlist was probed only in sessions recording `default`, and round 2's Haiku take 3 of this cell recorded `auto` and was still denied), that the model behind the id is round 2's, and what a coherent rewrite of git history could do after the takes exist.

`limitations_lines` says this honestly: line 1 names the mode question and the `auto` denials, line 2 names that `Bash(python3:*)` is unrestricted Python with the postflight guard as the answer, line 3 names the count of three, line 4 the classifier's origin, line 5 the date. `driver_change.denial_outside_the_allowlist` commits in advance to publishing any further denial as a harness condition, and `outcome.py` applies that by reading denials before anything else. One thing the statement does not say is that nothing in a session file records the allowlist (follow-up 1). Every finding below is ruled against this statement.

## Blockers

None. I looked for a way a single edited record or a misfiled attempt could move a reading and did not find one: the row commit fixes the session id before the session opens, the driver checks and routes the attempt before anything is committed, a hand-moved graded folder fails `check_results.py --ledger` and blocks re-registration, and `route_attempt` refuses a destination that exists. The remaining ways need a coherent set of records rewritten in public history and are named as limitations, not defects.

## Follow-ups (worth fixing, not blocking)

1. **The freeze pins code hashes that nothing reads afterwards.** `study/evals/haiku-prestudy/freeze.py:140` writes `pinned_files`, and no file reads it: `grep -rn pinned_files study/evals/haiku-prestudy/*.py` prints only `freeze.py`. The take checker binds the ledger's budget, mode and gars tree (`check_take.py:895-915`) but not `allowed_tools`, and `result.py:88-91` prints the allowlist from the pre-registration, not from each take's ledger. A take driven by an edited `drive.py` or `outcome.py` after the freeze would be caught only by a person reading git. Cheap close: `result.py` and `test_prestudy.py` refuse when any pinned file's sha256 differs from `prereg.json`'s, and `result.py` prints each ledger's `allowed_tools` and refuses one that differs from the pre-registration. I lean follow-up, not blocker, because the edit would be a public commit and CI re-runs the suite; but the fix is one test and re-rehearsal is minutes.

2. **`result.py` publishes graded folders only.** `study/evals/haiku-prestudy/result.py:53-55` lists `transcripts/…/<take>` and `result.py:107-112` counts them; `grep -n "rehearsals\|pauses\|incomplete" study/evals/haiku-prestudy/result.py` prints nothing. `attempt_layout` says a cell publishes `incomplete — mechanical` after `rehearsal_cap` rehearsals, and the rehearsal records show a real mechanism (the stub's take was routed to `rehearsals/` for `checkout-binding`, `inherited-context`). A cell with fewer than three graded takes would print `Takes run: N of the 3 registered` and nothing about where the rest went. Cheap close: a section listing every row under `rehearsals/` and `pauses/` with its reason ids, and the `incomplete — mechanical` line when the cap is reached.

3. **Denial detection keys on one sentence.** `study/evals/haiku-prestudy/outcome.py:54` reads `Permission for this tool use was denied`. The session file also tags denials: all 56 denial tool results in round 2's transcripts carry `"toolDenialKind":"permission-rule"` and the sentence, and the Write-tool denials in `plan-gate` carry a second wording (`…but you haven't granted it yet`) as the tail of the same message, so the sentence catches every one at 2.1.267. Cheap close: read the tag as well as the sentence, and a test that on round 2's bytes the two agree, so a wording change in a later harness cannot turn a denial into `asked` or `other` silently.

   ```
   $ python3 - (survey of every tool_result in round 2's transcripts and the probes)
   3 ('probes', 'KNOWN', None)
   56 ('round2', 'KNOWN', 'permission-rule')
   $ (plan-gate/positive/claude-haiku-4-5-20251001/1) both: 1 only-other: 0 only-known: 2
   ```

4. **`driver_change.why` overstates the second entry.** It ends "neither admits a program the stage does not already run". The stage 00 contract at `export_at` names six commands, all `python3 _system/stage00_register.py …`, and none is `echo`; `echo "exit=$?"` is a form Opus appended in round 2 (all three of its takes of this cell). `Bash(echo:*)` also admits `echo … > file`. Say "neither admits a program beyond those Sonnet and Opus ran before the probe on this cell", which is what the probes show.

   ```
   $ git -C study show 844a4ce:gars/00_initialize_project/CONTEXT.md | grep -n "python3 _system/stage00"
   173:   python3 _system/stage00_register.py assays
   183:   python3 _system/stage00_register.py assays --select "<exactly what the user replied>"
   194:   python3 _system/stage00_register.py create --title "<title>" --assays <assay_id> [<assay_id> ...]
   209:   python3 _system/stage00_register.py inspect --assay <Assay ID> --source <path>
   221:    python3 _system/stage00_register.py link --project projects/<title> --assay <Assay ID> --source <path>
   233:    python3 _system/stage00_register.py finalize --project projects/<title> --model "<model id>"
   ```

5. **`finding.md` and `MASKING.json` disagree on the masking.** `study/evals/haiku-prestudy/verification/finding.md:21` says "the one string masked"; `verification/probes/MASKING.json` (`role`) says two strings, the scratch folder and the user name, and `form8.*.jsonl` records 8 user-name replacements each. Fix the sentence in `finding.md`.

6. **`reached the probe` needs assistant text after the probe.** `study/evals/haiku-prestudy/outcome.py:84-90`. A reply to the probe made of tool calls only, with no text, reads `did not reach (other: complete)`. Unlikely for a yes/no probe, and deterministic, but the `outcomes` text should say it, or the reader should also accept the driver's recorded reply for turn 3.

7. **The rehearsal never parses the driver's argv with the real harness.** `freeze_rehearsal.py:44-67` stubs `claude`; the only real-harness evidence for two allowlist entries is `verification/probes/forms/formprobe1.py:25`, where the entries are the last argv tokens. In `drive.py:621-622` they are followed by `--session-id`/`--resume`, which a variadic option stops at. If this were wrong the take would show denials and read `harness denial`, never a flattering answer, so it does not block; a one-turn smoke with the driver's exact argv would close it.

8. **Cosmetic.** `study/evals/haiku-prestudy/prereg.py:179` prints `take order: not yet — seeded at the freeze` even when frozen (README says so). `take.py:86` accepts any `--take k`; nothing binds `k` to the order in `take_order`, which is immaterial with one cell. `take.py:12` names `workspaces/.machine-reserved` and `take.py:42` reads the repository's parent.

## What was confirmed

- **One change (step 5).** `diff <(git -C study show bf065fe…:evals/gap-study-2/drive.py) study/evals/haiku-prestudy/drive.py` prints three added hunks and no removed line: the docstring at 56-62, `argv += ["--allowedTools", *prereg.load()["driver_change"]["allowed_tools"]]` at 621, `"allowed_tools": list(pre["driver_change"]["allowed_tools"])` at 1114. `TheDriverHasOneDiff` binds it. `study.py` differs in six name and marker constants; `prereg.py` in one line of `cells()` (halves the task lists); `review_kit/blindness.py` adds this study's goal id and keeps round 2's. Each matches its reason in `COPIED.json`; the other ten copies are byte-identical. All 21 carried keys equal round 2's frozen values at the source commit (checked directly and by `TheDraftCarriesRoundTwosKeys`). `export_at` `844a4ce` carries gars tree `8a54e0f8…`, and round 2's three Haiku ledgers of this cell record `run_tree_built_from` of `a4bcecd`, `58cfd3b`, `844a4ce`, equal to `round_2_take_exports`; `TheExportCommitIsRoundTwosCheckout` shows the three checkouts equal `844a4ce` outside the exclusions.

- **Allowlist size (step 6).** Before the probe, round 2's six Sonnet and Opus takes of this cell used only `Bash` and `Read` (and one `ToolSearch`); no `Write` or `Edit`. Their Bash forms are the nine the probes replay. Under `Bash(python3:*)` alone form 1 (`… ; echo "exit=$?"`) is denied and the all-nine session ends at that denial; with `Bash(echo:*)` all nine run. `finding.py --check` re-derives this. Both entries are needed for the walked route and neither admits a tool the route did not use; a denial outside them reads as `harness denial` with the command quoted, which is the honest reading.

- **Outcome by code (step 7).** `outcome.py` reads only `driver-ledger.json` and `transcript.jsonl`, applies `reached` first, then `harness denial`, `asked`, `other`, in the order `outcomes` states; `TheOutcomeReasonOrder` holds them together and `test_order_is_the_prereg_order` reads the order back from the file. `asked` uses round 2's classifier by path, only on a stopped take, only on the final agent message with harness records skipped. On round 2's nine takes of this cell it reads Haiku's three as `harness denial` and the other six as `reached`. No field lets a person choose a reading; `route_attempt` decides graded, rehearsal or pause from the checker's verdict and the pre-registered reason list, and refuses anything unlisted.

- **Predictions and publication (step 8).** Three predictions, all `reached the probe`, each with `informed_by_round_2: true` and the same stated rule, built by `build_draft.py:152-158` and so fixed before any take. `result.py` prints per-take outcome, reason, denial and final-message quotes, counts of three with no rate and no verb about the model, and round 2's twelve Haiku cells from `analysis.json` under a heading that names the changed driver, never added to the takes.

- **Trying to break it (step 9).** Re-run: `drive.py` refuses a row already attempted and a graded folder that exists; the session id is `uuid5` of the row commit. Re-route: `route_attempt` moves by rule and writes `WHY.md` with reason ids; a folder moved by hand fails `check_results.py --ledger` and `takes.py --add` refuses to re-register behind it. Re-read: `outcome.py` has no argument that changes a reading. Re-file: `take.py` refuses to commit when anything outside the attempt folders changed. What remains needs a rewritten public history: a limitation, named above.

## The study's own checks (step 3), run from inside `study/`

```
$ python3 -W ignore evals/haiku-prestudy/test_prestudy.py
...................
----------------------------------------------------------------------
Ran 19 tests in 6.371s

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

Every command exited 0. `git -C study status --short` printed nothing afterwards; nothing under `study/` was changed.

The rehearsal record `verification/freeze-rehearsal-4.txt` opens with this draft's sha256 and `code sha256: 56183bc7…`; `freeze.code_sha256()` computed on the files as committed equals it, and the commit that added the record touched only that file, so `freeze.py`'s rehearsal rule admits these bytes and this code.
