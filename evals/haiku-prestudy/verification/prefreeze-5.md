prereg.json sha256: b6cf56ae4ff23ebc39954b1e576cb1131067b6673b6116c7a5fc45f15dc682fb

# Pre-freeze review 5: the Haiku pre-study

**Ruling: DO FREEZE.**

Reviewed at the commit named in `COMMIT` (`3fc699f`). `shasum -a 256 prereg.json` prints the digest on line 1, and `diff prereg.json study/evals/haiku-prestudy/prereg-draft.json` prints nothing. Every path below is relative to this folder. Every command was run from inside `study/` unless shown otherwise. Nothing under `study/` was changed: `git -C study status --short` printed nothing before and after, and the one scratch clone used below was made beside `study/` and removed.

No blocker. Review 4's blocker is closed by code the freeze pins, and its five follow-ups are taken. Three follow-ups remain, none of which moves a reading; each is a guard that reads a little less than it says, with a cheap close.

## What changed since review 4

```
$ diff <(python3 -m json.tool prereg-as-the-previous-review-read-it.json) <(python3 -m json.tool prereg.json)
(nothing)
```

The draft's bytes are the ones review 4 read. What moved is code, in one slice commit (`f41026d`) and two rehearsal commits:

- `outcome.denials()` now returns, for each denied call, the call's own command, the harness's "what required approval" clause, and the refusal text; `result.denial_lines()` publishes all three, with the refusal quoted to 800 characters. `TheDeniedCommandIsPublished` drives that on round 2's three real Haiku denials of this cell and on the form probe.
- `result.py` runs the copied skipped-row guard and holds the registration order to `take_order` (review 4, follow-up 1), runs the deleted-attempt history guard with `--no-renames` (follow-up 2), and refuses to write while the cell is neither complete nor at a cap (follow-up 5).
- The README names the fail-closed route for a take refused on a driver-decided reason, and says the carried notes cite round 2's review numbers (follow-ups 3 and 4).
- Rehearsal 8 went NOT green because the rehearsal still expected a written result; the rehearsal now expects the refusal, and rehearsal 9 is all green on these draft bytes and this code.

The freeze would admit the record: `freeze.code_sha256()` at HEAD prints `9e1f8ba8fb60…`, rehearsal 9's `code sha256:` line is the same, its first line is this draft's sha256 and its last line is `all green`, and `freeze.rehearsal_record(<draft sha>)` returns `verification/freeze-rehearsal-9.txt`. The 17 files `freeze.PINNED` names are the 17 the rehearsal pinned.

## The threat model

What the checks bind: the driver is round 2's at `bf065fe` plus three added hunks asserted by content with no removed line; every other copy is byte-identical or carries its reason; every rule a take is held to is round 2's frozen value, including the driver-decided reason list; the checkout is exported from `844a4ce`, whose gars tree is the pinned one and whose content outside the exclusions equals the three checkouts round 2's Haiku takes of this cell ran in; a session id is a function of a committed ledger row, take k opens only when takes 1 to k-1 are graded and every pinned file still hashes as frozen, and the attempt is routed by the checker's verdict and committed as it stands or refused; the outcome is read by code from the take's own ledger and transcript in a fixed order; the result refuses unpinned code, a foreign allowlist, a drifted source folder, a deleted attempt in history, a skipped or reordered row, an attempt no committed row implies, and a cell that is neither complete nor capped. What they cannot bind: what happens inside the harness process, namely whether it applied the allowlist (no session record carries it; the evidence is the absence of denials, and the published denied command says which condition was measured when there is one) and which permission mode it ran under (the allowlist was probed only in sessions recording `default`, and round 2's Haiku take 3 of this cell records `auto` and was denied all the same); that the model behind the id is round 2's; and a coherent set of public commits made after a take exists, which the checks leave visible rather than prevent.

`limitations_lines` says the harness-side part honestly: line 1 the mode question and the `auto` denial, line 2 the unrestricted Python and the postflight's true scope, line 3 that no session file records the allowlist, lines 4 to 6 the count of three, the classifier's origin and the date. `driver_change` says the change honestly: both entries, where they go in the argv, why each is needed with the probe that showed it, what each admits beyond the walked route, and that a denial is the harness's condition. Its promise that a `harness denial` publishes with the denied command quoted is now kept by `result.denial_lines()`, shown below. The post-hoc history class is not named in the frozen file; it is a limitation, not a defect, and the two cheap checks review 4 asked for are now in `result.py`. Every finding below is ruled against this statement.

## Blockers

None.

## Follow-ups (worth fixing, not blocking)

1. **The result's completeness refusal counts pauses toward the rehearsal cap, and never prints the cap line for a pause-capped cell.** `study/evals/haiku-prestudy/result.py:216` refuses only while `len(rows) < n and not (len(others) >= rehearsal_cap)`, where `others` holds rehearsals and pauses together; `result.py:211` prints `incomplete — mechanical` only when the rehearsals alone reach the cap. `takes.py:279-290` caps the two kinds separately. So with two graded takes and one rehearsal plus two pauses, the result writes a two-of-three cell with no cap line while `takes.py --add` would still register a third row; with three pauses it writes a two-of-three cell that `takes.py` refuses to continue, and says nothing about why. Evaluated from the two conditions as written:

   ```
   ['rehearsal', 'pause', 'pause']: graded 2 of 3; writes=True; prints 'incomplete — mechanical'=False
   ['rehearsal', 'rehearsal', 'rehearsal']: graded 2 of 3; writes=True; prints 'incomplete — mechanical'=True
   ['pause', 'pause', 'pause']: graded 2 of 3; writes=True; prints 'incomplete — mechanical'=False
   ```

   The counts printed are still true, no reading moves, and a written result is overwritten by the next `--write` and refused by `--check` until it is. Cheap close: count rehearsals against `rehearsal_cap` and pauses against `pause_cap` separately, refuse unless the cell is complete or one cap is reached, and print the cap line for whichever was.

2. **The copy-manifest check reads two commits, not the working tree, so an uncommitted edit to round 2's classifier or the shared parser passes it at result time.** `study/evals/haiku-prestudy/copy_manifest.py:85` runs `git diff --quiet <source> HEAD -- <path>`, which compares committed trees only. `result.py:171` relies on it to bind `evals/gap-study-2/graders/labels.py` (the `asked` reason), `number_fidelity.py` (the informational label) and `evals/transcript.py`, none of which `freeze.py` pins. `take.py`'s preflight refuses an unclean tree, so a take cannot be driven this way; `result.py` has no such check. In a scratch clone made beside `study/`:

   ```
   $ git clone -q --no-local study scratch-clone && cd scratch-clone
   $ python3 evals/haiku-prestudy/copy_manifest.py --check
   ok: 14 files trace to bf065feedccc, 4 edited with a reason; round 2, round 1 and the parser unchanged
   $ printf '\n# an uncommitted working-tree edit\n' >> evals/gap-study-2/graders/labels.py
   $ printf '\n# an uncommitted working-tree edit\n' >> evals/transcript.py
   $ git status --short
    M evals/gap-study-2/graders/labels.py
    M evals/transcript.py
   $ python3 evals/haiku-prestudy/copy_manifest.py --check
   ok: 14 files trace to bf065feedccc, 4 edited with a reason; round 2, round 1 and the parser unchanged
   $ git diff --quiet bf065fe -- evals/gap-study-2/graders/labels.py; echo $?
   1
   ```

   A `RESULT.md` written this way fails `result.py --check` in CI's clean checkout unless the edit is committed, and a committed edit fails the manifest, so the route is caught, not prevented: a limitation with a cheap close. Add `git diff --quiet <source> -- <path>` (working tree against the source commit) beside the existing line, or have `result.py` refuse an unclean `evals/` as `take.py` does.

3. **The published denied-command line can carry the run tree's absolute temporary path.** `study/evals/haiku-prestudy/result.py:152` prints `den['command']` as the model wrote it. In round 2's Haiku takes 1 and 3 of this cell the model used `cd <absolute run-tree path>/gars && python3 …`, so the same line in this study's `RESULT.md` would print a path under the machine's temporary directory. Round 2's committed transcripts already carry those paths and the scrub removes only the account email, so this is hygiene rather than a reading; but `MASKING.json` shows the study masking exactly this kind of path in its probes. Cheap close: replace the run-tree prefix (the ledger's `cwd`) with a marker before quoting.

## What was confirmed

- **One change (step 5).** `diff <(git -C study show bf065fe…:evals/gap-study-2/drive.py) study/evals/haiku-prestudy/drive.py` prints three added hunks and no removed line: the docstring paragraph at 56-62, the argv line at 621 (`--allowedTools` with the pre-registration's entries, after the isolation flags and before `--session-id`/`--resume`, with `--permission-mode auto` still passed, as `driver_change.where` says), and the ledger key at 1114. `TheDriverHasOneDiff` asserts the nine added lines by content. `COPIED.json` re-derives: four edited copies, each matching its reason (`study.py` name and markers, `prereg.py`'s one-line `cells()` change, `review_kit/blindness.py`'s added goal id, `drive.py` as above), ten byte-identical. All 23 carried keys equal round 2's frozen values (`TheDraftCarriesRoundTwosKeys`; `carried_from_round_2` equals `build_draft.CARRIED`). `git rev-parse 844a4ce:gars` prints the pinned tree; round 2's three Haiku ledgers of this cell record `run_tree_built_from` equal to `round_2_take_exports`, and `TheExportCommitIsRoundTwosCheckout` shows each equal to `844a4ce` outside the exclusions.

- **Allowlist size (step 6).** Re-derived from round 2's nine transcripts of this cell with the shared parser: before the probe, Sonnet and Opus used `Bash` and `Read` (one `ToolSearch`), and the programs at the head of their Bash segments were `cat`, `cd`, `echo`, `find`, `grep`, `head`, `ls`, `pwd`, `python3`, `sed`, `wc`; every one of the six used `echo`. The stage 00 contract at `844a4ce` (`gars/00_initialize_project/CONTEXT.md`, Process steps 3 to 15) names only `python3 _system/stage00_register.py …`. In the eighteen per-form probe sessions, form 1 (`…; echo "exit=$?"`) is denied under `Bash(python3:*)` alone and the other eight ran; with `Bash(echo:*)` all nine ran; the all-nine session ends at form 1's denial; the driver-argv session, with both entries followed by `--session-id`, ran form 1 with no denial. No probe transcript records `allowedTools`, as limitations line 3 says. Both entries are needed for the walked route, neither admits a program beyond those the other two models ran before the probe on this cell, and a denial outside them reads `did not reach`, `harness denial`, with the command now printed beside it.

- **Outcome by code (step 7).** `outcome.py` reads only `driver-ledger.json` and `transcript.jsonl`. `reached the probe` needs both the ledger's non-recovery row for turn 3 with the probe line as sent and a user turn carrying that line verbatim followed by an assistant turn with text the harness did not write; neither file alone can claim it. Otherwise `harness denial` (the sentence in a tool result, or the harness's own `toolDenialKind` tag, which agree on every round-2 transcript), then `asked` (round 2's classifier by path, only on a `stopped` take, only the final agent message), then `other` with the driver's outcome quoted. `test_order_is_the_prereg_order` reads that order back from the file. On round 2's nine takes it reads Haiku's three as `harness denial` (take 3 with mode `auto` recorded) and the six others as `reached`. No argument, flag or field lets a person choose a reading; `route_attempt` decides graded, rehearsal or pause from the checker's verdict against the pre-registered reason list and refuses anything unlisted or a destination that exists. The published denial lines on round 2's Haiku take 2 and on the form probe:

  ```
  - Denied command: `cd gars && python3 _system/stage00_register.py assays`
  - The harness said it required approval for: This Bash command contains multiple operations. The following par…
  - Denial quoted: "Permission for this tool use was denied. It requires approval, and this session has no appro…
  - Denied command: `cd gars && python3 _system/reg.py assays; echo "exit=$?"`
  ```

- **Predictions and publication (step 8).** Three predictions, each `reached the probe`, `informed_by_round_2: true`, one stated rule, written by `build_draft.py:162-168` and so fixed before any take. `result.py` prints per take the outcome, reason, denial count, ask phrases, recorded mode, the ledger's allowlist and harness version, and round 2's grader label under a heading that says it is for information; counts with no rate and no verb about the model; every rehearsal and pause with its reason ids; round 2's twelve Haiku cells under a heading that names the changed driver and says they are not added (the `analysis.json` shape it reads exists for all six tasks); the limitations lines. `result.py --ledger` at HEAD prints `ok: every attempt is tied to one committed row`, and `result.py --check` refuses because the file in force is the draft.

- **Trying to break it (step 9).** Re-run: the row commit fixes the session id; `drive.py` refuses an existing graded folder or an attempted row; `takes.py --add` refuses a registered or graded slot, a take index outside 1..n, a waiting row, a cell at either cap, and a freed slot whose attempt the ledger check refuses; `take.py` refuses a take out of order, a drifted pin, a deleted attempt in history, an unclean tree or a `main` not even with origin. Re-route: by the checker's verdict only; a graded take moved into `rehearsals/` fails the ledger check because the checker passes it, and a rehearsal moved into `transcripts/` fails it because the checker refuses it; an edited ledger is re-checked with its driver-written fields normalised, and a rehearsal citing a driver-decided reason is refused, which the README now names as fail-closed. Re-read: `outcome.py` has no switch, and `result.py` refuses unpinned code. Re-file: a take driven for one row cannot land under another, since the transcript's session id is bound to the row commit, and the result now refuses a skipped or reordered row. Re-freeze: `freeze.py` refuses when `prereg.json` exists and admits only a rehearsal of these bytes and this code. What remains is the three follow-ups above, each caught after the fact by CI or by the next write rather than prevented, and none moves a reading. I found nothing that lets a single edited record or a misfiled attempt move a reading, and nothing that blocks a freeze.

## The study's own checks (step 3), run from inside `study/`

```
$ python3 -W ignore evals/haiku-prestudy/test_prestudy.py
..............ss.........
----------------------------------------------------------------------
Ran 25 tests in 7.550s

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

Every command exited 0. The two skipped tests are the class that reads the frozen file, which does not exist yet; rehearsal 9 ran them in its frozen clone. `git -C study status --short` printed nothing afterwards.
