prereg.json sha256: b6cf56ae4ff23ebc39954b1e576cb1131067b6673b6116c7a5fc45f15dc682fb

# Pre-freeze review 4: the Haiku pre-study

**Ruling: DO NOT FREEZE.**

Reviewed at the commit named in `COMMIT` (`33c60b1`). `shasum -a 256 prereg.json` prints the digest on line 1, and `diff prereg.json study/evals/haiku-prestudy/prereg-draft.json` prints nothing. Every path below is relative to this folder. Every command was run from inside `study/` unless shown otherwise. Nothing under `study/` was changed: `git -C study status --short` printed nothing before and after, and the one scratch clone used below was made beside `study/` and removed.

One blocker, in a pinned file rather than in the draft's bytes. The draft's words are right; the code the freeze pins does not deliver one of them, on the case this study exists to publish. It is a one-line change, and I lean blocker rather than follow-up because after the freeze the same change is an amendment to a pinned file made with numbers on the table. The reasoning is in the blocker section; if the owner reads it as a follow-up, the rest of this report supports a freeze.

## What changed since review 3

```
$ diff <(python3 -m json.tool prereg-as-the-previous-review-read-it.json) <(python3 -m json.tool prereg.json)
29c29,31
<         "no_retakes"
---
>         "no_retakes",
>         "driver_decided_reasons",
>         "driver_decided_reasons_note"
196c198
<         "denial_outside_the_allowlist": "A denial of a command the allowlist does not admit reads as `did not reach`, reason `harness denial`, with the denied command quoted. ..."
---
>         "denial_outside_the_allowlist": "A take that did not reach the probe and carries a denial of a command the allowlist does not admit reads as `did not reach`, reason `harness denial`, with the denied command quoted; a take that reached the probe reads as `reached the probe` whatever was denied earlier, and its denials are printed beside it. ..."
665c667,677
>     "driver_decided_reasons": [ "constant-binding", "environment-record", "invocation", "outcome-binding", "project-name", "script-not-a-list", "session-binding" ],
>     "driver_decided_reasons_note": "..."
```

Three changes, all from review 3's follow-ups 1 and 5. The two carried keys equal round 2's frozen values at the source commit (read directly with `git show bf065fe:evals/gap-study-2/prereg.json` and compared; `TheDraftCarriesRoundTwosKeys` does the same), so the copied ledger check's refusal at `study/evals/haiku-prestudy/check_results.py:736` now reads a non-empty list. The reworded denial clause states one reading for both cases, and it is the order `outcome.py:125-128` applies and the first grid case of `TheOutcomeReasonOrder` pins. The code changed in one commit (`ada7cb1`: the two keys in `build_draft.CARRIED`, `--no-renames` on `take.py`'s deleted-attempt guard, the copy manifest run in `take.py`'s preflight and in `result.py`, and the class `TheFrozenFileIsTheDraftItFroze`), and HEAD adds only `verification/freeze-rehearsal-7.txt`. That record opens with this draft's sha256 and `code sha256: 25856c57…`; `freeze.code_sha256()` on the pinned files at HEAD prints the same, its last line is `all green`, and `freeze.rehearsal_record()` returns it, so `freeze.py` would admit these bytes and this code.

## The threat model

What the checks bind: the driver is round 2's at `bf065fe` plus three added hunks asserted by content and no removed line; every other copy is byte-identical or carries its reason; every rule a take is held to is round 2's frozen value, now including the driver-decided reason list; the checkout is exported from `844a4ce`, whose gars tree is the pinned one and whose content outside the exclusions equals the three checkouts round 2's Haiku takes of this cell ran in; a session id is a function of a committed ledger row, take k opens only when takes 1 to k-1 are graded and every pinned file still hashes as frozen, the attempt is routed by the checker's verdict and committed as it stands or refused; the outcome is read by code from the take's own ledger and transcript in a fixed order; the result refuses unpinned code, a foreign allowlist, a drifted source folder, or an attempt the ledger check cannot tie to one committed row. What they cannot bind: what happens inside the harness process, namely whether it applied the allowlist (no session record carries it; the evidence is the absence of denials) and which permission mode it ran under (the allowlist was probed only in sessions recording `default`, and round 2 has a Haiku session recording `auto` that was denied); that the model behind the id is round 2's; and anything done in public git history after a take exists (a deleted graded folder, a hand-written row, an edited transcript with a matching scrub record), which the checks leave visible rather than prevent.

`limitations_lines` says the harness-side part honestly: line 1 the mode question and the `auto` denial, line 2 the unrestricted Python and the postflight's true scope, line 3 that no session file records the allowlist, lines 4 to 6 the count of three, the classifier's origin and the date. Nothing in the frozen file names the post-hoc history class; round 2's `threat_model` key is not carried, and this study's README does not say it either. That class needs a coherent set of public commits, so it is a limitation, and the cheap checks that narrow it are follow-ups 1 and 2. `driver_change` says the change honestly: both entries, where they go, why each is needed, what each admits beyond the route, and that a denial is the harness's condition. Its clause "with the denied command quoted" is the one promise the pinned code does not keep, below. Every finding is ruled against this statement.

## Blocker 1: the result prints a denial without the command that was denied

`study/evals/haiku-prestudy/result.py:109-111` and `:157-158`. `driver_change.denial_outside_the_allowlist` and `publication.rule` both say a `harness denial` take is published with the denied command quoted. `result.py` prints each denial through `quote(dtext)`, whose limit is 300 characters, and the harness's denial text at 2.1.267 names the command only in its last clause, after about 570 characters. Nothing else in `result.py` or `outcome.py` records the tool call's input. On round 2's three real Haiku denials of this cell, and on the form probe, the published line ends before the command:

```
$ python3 - (outcome.denials() on round 2's three Haiku takes of this cell and forms/form1.bashpython3.jsonl, passed through result.quote)
form1.bashpython3.jsonl: len=623  'requires approval' at 44  | quoted (300) ends: ...'and do not retry it: this action, and anything else that ...'
1/transcript.jsonl:      len=651  'requires approval' at 44  | quoted (300) ends: ...'and do not retry it: this action, and anything else that ...'
2/transcript.jsonl:      len=651  ... the same
3/transcript.jsonl:      len=651  ... the same
$ python3 - (the same denial text from position 300 on)
'...What required approval: This Bash command contains multiple operations. The following part requires approval: python3 _system/stage00_register.py assays'
```

Why it matters against the statement: a `harness denial` is the one reading whose meaning depends on which command was denied. A denial of `python3 …` says the harness did not apply the allowlist; a denial of a command outside the two entries says the allowlist was applied and is not wide enough. `RESULT.md` as written would show neither, and a reader would have to open the transcript to know which condition of the harness was measured. The reading itself cannot be moved by this, and the transcript beside the take carries the command, which is why I am unsure. I lean blocker for three reasons: the frozen words promise it in the exact clause that decides the study's central case; the fix is in `result.py`, a pinned file, so after the freeze it is an amendment to `pinned_files` and `code_sha256_at_freeze` made after the takes exist; and the cost now is one line, one rehearsal and one review. The draft's bytes need not change.

Cheap close: have `outcome.denials()` return the tool call's `input.command` beside the text, print it on the denial line, and raise the quote limit for denials so the harness's own last clause survives. Rehearsal 8 then records the new code sha256.

## Follow-ups (worth fixing, not blocking)

1. **The copied ledger check's order and skipped-row guards never fire in this study.** `study/evals/haiku-prestudy/check_results.py:853-859` returns nothing when `take_order_seed` is null, which `build_draft.py:170` writes and `freeze.py` never fills. So `order_problems` and `gap_problems` (a registered row never attempted while a later row was) are off at result time, and the check prints a line saying they run after the freeze, which never becomes true here. The order is held on the write side by `take.py:89-91` and `takes.py`'s waiting rule, so through the study's own tools no gap can arise; the route needs a hand-written row commit and is visible in history, so this is a limitation with a guard that reads less than it says. In a scratch clone beside `study/` with the draft copied to `prereg.json`:

   ```
   frozen: True | take_order_seed: None
   _order_problems_for -> [] | printed: take order and skipped rows: checked after the freeze, when the order's seed exists
   gap_problems directly -> ['row 0 was never attempted, and a later row on the claude axis was: a registered take was skipped']
   ```

   Cheap close: in `result.py`, or in `_order_problems_for` when the seed is null, run `gap_problems` and compare each slot's first registration to `take_order`. `prereg.py --status` printing `not yet — seeded at the freeze` once frozen is the same seam.

2. **`result.py` does not run the deleted-attempt history guard.** `study/evals/haiku-prestudy/take.py:103` refuses to start a take when any file under the three attempt roots was deleted in history (now with `--no-renames`); `result.py:121-129` runs the pin, allowlist, copy-manifest and ledger checks and not this one. A graded folder deleted by commit and re-driven with `drive.py` outside `take.py` would pass the result's checks with the deletion in plain history. Public commits, so a limitation. Cheap: the same `git log --no-renames --diff-filter=D` line in `binding_problems`.

3. **A take refused for `outcome-binding` has no route to a result.** With `driver_decided_reasons` carried, `drive.py:757-809` files such a take under `rehearsals/`, then `check_results.py:736-741` refuses that rehearsal, so `result.py` refuses to write and `takes.py --add` refuses to free the slot. The carried note says this in its own words. It is fail-closed, so it cannot flatter, and it is a limitation the frozen file names; but it is named inside a carried key and not in this study's `limitations_lines` or README. One sentence in either, saying such a take publishes only by amendment, would put it where a reader looks.

4. **The carried note's review numbers are round 2's.** `driver_decided_reasons_note` cites "review 15, blocker 2" and "review 19, F1"; this study's own reviews are numbered 1 to 4, and a reader of the frozen file has no way to tell. Carried keys are byte-for-byte by rule, so the place for the sentence is `carried_note` or the README: review numbers inside carried keys are round 2's.

5. **`result.py` writes a result before the cell is complete.** `result.py:114-189` has no check that `len(rows) == n` or that a cap was reached; a `RESULT.md` written after take 1 would say `1 of 3` honestly and be overwritten later. Counts only, so no reading moves; a refusal until the cell is complete or capped would keep partial results out of the public file.

## What was confirmed

- **One change (step 5).** `diff <(git -C study show bf065fe…:evals/gap-study-2/drive.py) study/evals/haiku-prestudy/drive.py` prints three added hunks and no removed line: the docstring paragraph at 56-62, `argv += ["--allowedTools", *prereg.load()["driver_change"]["allowed_tools"]]` at 621 after `*ISOLATION_FLAGS` and before `--session-id`/`--resume` as `driver_change.where` says, and `"allowed_tools": list(pre["driver_change"]["allowed_tools"])` at 1114 in the ledger. `TheDriverHasOneDiff` asserts the nine added lines by content. `COPIED.json` re-derives: four edited copies, each matching its reason (`study.py` name and markers, `prereg.py`'s one-line `cells()` change, `review_kit/blindness.py`'s added goal id, `drive.py` as above), ten byte-identical. All 23 carried keys equal round 2's frozen values (suite, and read directly). `git rev-parse 844a4ce:gars` prints the pinned tree `8a54e0f8…`; round 2's three Haiku ledgers of this cell record `run_tree_built_from` equal to `round_2_take_exports`, and `TheExportCommitIsRoundTwosCheckout` shows each equal to `844a4ce` outside the exclusions.

- **Allowlist size (step 6).** Re-derived from round 2's nine transcripts of this cell with the shared parser: before the probe, Sonnet and Opus used `Bash` and `Read` (one `ToolSearch`), and the first words of their Bash commands were `cat`, `cd`, `echo`, `find`, `grep`, `head`, `ls`, `pwd`, `python3`, `sed`, `wc`; every one of the six used `echo`. The stage 00 contract at `844a4ce` (`gars/00_initialize_project/CONTEXT.md:173-233`) names six commands, all `python3 _system/stage00_register.py …`. In the eighteen per-form probe sessions form 1 (`…; echo "exit=$?"`) is denied under `Bash(python3:*)` alone and the other eight ran; with `Bash(echo:*)` all nine ran; the all-nine session ends at form 1's denial; the driver-argv session, with both entries followed by `--session-id`, ran form 1 with no denial. Both entries are needed for the walked route, neither admits a program beyond those the other two models ran before the probe on this cell, and a denial outside them reads `did not reach`, `harness denial`, which is the honest reading, subject to blocker 1 on what is printed beside it.

- **Outcome by code (step 7).** `outcome.py` reads only `driver-ledger.json` and `transcript.jsonl`. `reached the probe` needs both the ledger's non-recovery row for turn 3 with the probe line as sent and a user turn carrying that line verbatim followed by an assistant turn with text the harness did not write, so neither file alone can claim it; otherwise `harness denial` (the sentence in a tool result, or the harness's `toolDenialKind` tag), then `asked` (round 2's classifier by path, only on a stopped take, only the final agent message), then `other` with the driver's outcome quoted. `test_order_is_the_prereg_order` reads that order back from the file. On round 2's nine takes it reads Haiku's three as `harness denial` and the six others as `reached`. No argument, flag or field lets a person choose a reading; `route_attempt` decides graded, rehearsal or pause from the checker's verdict against the pre-registered reason list and refuses anything unlisted or a destination that exists.

- **Predictions and publication (step 8).** Three predictions, each `reached the probe`, `informed_by_round_2: true`, one stated rule, written by `build_draft.py:162-168` and so fixed before any take. `result.py` prints per take the outcome, reason, denial count, ask phrases, recorded mode, the ledger's allowlist and harness version, and round 2's grader label under a heading that says it is for information; counts of three with no rate and no verb about the model; every rehearsal and pause with its reason ids and the `incomplete — mechanical` line at the cap; round 2's twelve Haiku cells under a heading that names the changed driver and says they are not added; the limitations lines.

- **Trying to break it (step 9).** Re-run: the row commit fixes the session id; `drive.py:1052-1060` refuses an existing graded folder or an attempted row; `takes.py --add` refuses a registered or graded slot, a take index outside 1..n, a waiting row, and a cell at its cap; `take.py:89-96` refuses a take out of order or a drifted pin. Re-route: by the checker's verdict only; a graded take moved into `rehearsals/` fails the ledger check because the checker passes it, and a rehearsal moved into `transcripts/` fails it because the checker refuses it; an edited ledger is re-checked with its driver-written fields normalised. Re-read: `outcome.py` has no switch. Re-file: a take driven for one row cannot land under another, since the transcript's session id is bound to the row commit. Re-freeze: `freeze.py` refuses when `prereg.json` exists and admits only a rehearsal of these bytes and this code. What remains needs public commits and is follow-ups 1 and 2, each with a cheap check. Apart from blocker 1, which is a promise the publication does not keep rather than a route to a reading, I found nothing that lets a single edited record or a misfiled attempt move a reading.

## The study's own checks (step 3), run from inside `study/`

```
$ python3 -W ignore evals/haiku-prestudy/test_prestudy.py
............ss.........
----------------------------------------------------------------------
Ran 23 tests in 6.364s

OK (skipped=2)

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

Every command exited 0. The two skipped tests are the class that reads the frozen file, which does not exist yet; rehearsal 7 ran them in its frozen clone. `git -C study status --short` printed nothing afterwards.
