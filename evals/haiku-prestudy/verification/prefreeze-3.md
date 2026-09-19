prereg.json sha256: 0969b7514acdee9ff082e8874596c4f53dd79231d153f385121c146d1d663b06

# Pre-freeze review 3: the Haiku pre-study

**Ruling: DO FREEZE.**

Reviewed at the commit named in `COMMIT` (`f187712`). `shasum -a 256 prereg.json` prints the digest on line 1, and `diff prereg.json study/evals/haiku-prestudy/prereg-draft.json` prints nothing. Every path below is relative to this folder; every command was run from inside `study/` unless shown otherwise. Nothing under `study/` was changed: the one scratch clone used below was made beside `study/`, not inside it, and removed afterwards. `git -C study status --short` printed nothing before and after.

## What changed since review 2

```
$ diff <(python3 -m json.tool prereg-as-the-previous-review-read-it.json) <(python3 -m json.tool prereg.json)
194c194
<         "why": "... Bash(echo:*) also admits `echo ... > file`; a write it makes outside the take's own folders is caught by take.py's postflight.",
---
>         "why": "... Bash(echo:*) also admits `echo ... > file`, as Bash(python3:*) admits any Python: a write that changes the study repository's git status outside the attempt folders is caught by take.py's postflight; a write to a path git ignores, or anywhere else on the machine, is not read (limitations).",
280c280,281
<         "Bash(python3:*) lets the session under test run any Python, ... refuses to file a take after which it changed outside the take's own folders.",
---
>         "Bash(python3:*) lets the session under test run any Python, ... refuses to file a take after which it changed outside the attempt folders; a write to a path git ignores, or outside the repository, does not show in that status and is not read.",
>         "No session file records --allowedTools: a take's `allowed_tools` is the driver's own ledger entry, and the evidence that the harness applied the allowlist is that the stage commands ran without a denial.",
```

Two fields moved, both review 2's follow-ups taken: `driver_change.why` now states the postflight at its true scope (follow-up 1), limitations line 2 says the same, and a sixth limitations line names that no session file records the allowlist (follow-up 7). Both new sentences are what the code does (`study/evals/haiku-prestudy/take.py:145-154` diffs `git status --porcelain --untracked-files=all` of the study repository and nothing else).

The code changed in one commit since review 2 (`ccccb5f`: CI's ledger step, the README's count of four edited copies and its note on the unused frozen-content check, `take.py`'s pinned-file and deleted-attempt preflight, `result.py`'s ledger check and harness column, `test_prestudy.py`'s by-content driver diff, the rehearsal's ledger step) and HEAD (`f187712`) adds only `verification/freeze-rehearsal-6.txt`. That record opens with this draft's sha256 and `code sha256: 134dc80b…`; `freeze.code_sha256()` computed on the pinned files as committed prints `134dc80b11bcaad23f3aa318a08c3c3ad7c2418998fb229fc477348447ec717f`, and its last line is `all green`, so `freeze.py`'s rehearsal rule admits these draft bytes and this code. All seven of review 2's follow-ups are taken; I checked each against the code rather than the commit message.

## The threat model

What the checks bind: the driver is round 2's at `bf065fe` plus nine added lines whose exact content the suite asserts and no removed line; every other copy is byte-identical or carries its reason; every rule a take is held to is round 2's frozen value byte for byte and the half is round 2's; the checkout is exported from `844a4ce`, whose content outside the pre-registered exclusions equals the three checkouts round 2's Haiku takes of this cell ran in and whose gars tree is the pinned one, re-read by the driver before each session opens; a take's session id is a function of a committed ledger row, take k opens only when takes 1 to k-1 are graded and every pinned file still hashes as frozen, the attempt is routed by the checker's verdict and committed as it stands or refused; the outcome is read by code from the take's own ledger and transcript in a fixed reason order; the result refuses code the freeze did not pin, a ledger with another allowlist, or an attempt the copied ledger check cannot tie to one committed row, and prints counts with round 2's cells beside them. What they cannot bind: what happens inside the harness process, namely whether it applied the allowlist (no session record carries it; the ledger's `allowed_tools` is the driver's own word and the evidence is the absence of denials) and which permission mode it runs the session under (the allowlist was probed only in sessions recording `default`, and round 2's Haiku take 3 of this cell recorded `auto` and was denied the same command); that the model behind the id is round 2's; and anything done in public git history after the takes exist, which the checks leave visible rather than prevent, since the raw session file never enters the repository.

`limitations_lines` says this honestly. Line 1 names the mode question and the `auto` denial; line 2 names that `Bash(python3:*)` is unrestricted Python and states the postflight's true scope, including what git status cannot see; line 3 names that the allowlist's application is evidenced only by the absence of denials; lines 4 to 6 name the count of three, the classifier's origin and the date. `driver_change.why` now says the same of `echo`, and `driver_change.denial_outside_the_allowlist` commits in advance to reading a further denial as a harness condition with the command quoted. One thing the frozen file will not say is that one refusal of the copied ledger check reads a round 2 key the draft does not carry and so never fires here (follow-up 1); round 2's own note calls that refusal a belt over a rule the same file still implements, so it does not move a reading. Every finding below is ruled against this statement.

## Blockers

None. I looked for a way a single edited record or a misfiled attempt could move a reading and did not find one. The session id is fixed by the row commit before the session opens; `study/evals/haiku-prestudy/drive.py:1052-1060` refuses a graded folder that exists and a row already attempted; `take.py:89-100` refuses a take that is not next in the pre-registered order, a pinned file that differs from the freeze and a history in which an attempt file was deleted, and `take.py:145-154` refuses to commit when anything outside the attempt folders changed; `outcome.py` takes a folder and nothing else; `result.py:69-94` refuses when any pinned file or any ledger's allowlist differs from the frozen file or when the copied ledger check reports anything. The misfiling that came closest, a graded folder moved into `rehearsals/` so that its slot is freed, is refused by the copied check because the take checker passes the moved take (`check_results.py:750-752`), and `takes.py:224-249` runs that check before it frees a slot. What remains needs public commits and a coherent set of edited records; each is a limitation the statement names, and each has a cheap check listed below.

## Follow-ups (worth fixing, not blocking)

1. **The copied ledger check reads a round 2 key the draft does not carry.** `study/evals/haiku-prestudy/check_results.py:736` reads `prereg.load().get("driver_decided_reasons") or []` to refuse a rehearsal whose recorded reason is one the driver decides before a session (`constant-binding`, `environment-record`, `invocation`, `outcome-binding`, `project-name`, `script-not-a-list`, `session-binding` in round 2's frozen file). `build_draft.CARRIED` (`build_draft.py:44-48`) does not carry it, so in this study the list is empty and that refusal never fires, although `attempt_problems` is exactly the function `takes.py --add` and `result.py` run. It reads less than round 2's did, and the builder's own docstring says every rule the copied checker reads is carried. I lean follow-up, not blocker: round 2's note calls the list a belt over `ledger_made_refusal_rule`, which `check_results.py:596-633` implements without reading any key, by re-running the checker with the ledger's driver-written fields restored and refusing a rehearsal whose reason disappears; and founding a rehearsal on an edited ledger needs the edit, a `WHY.md`, a moved folder and a public commit. Cheap close: add `driver_decided_reasons` and `driver_decided_reasons_note` to `CARRIED`, rebuild, re-rehearse. That changes the draft's bytes, so it is either done before the freeze with a fourth review or published as an amendment after it; either is honest.

   ```
   $ python3 - (round 2's top-level keys the draft omits, grepped in the copied files)
   'driver_decided_reasons' is read by ['check_results.py:736']
   driver_decided_reasons in round 2's file: True
   $ git show bf065fe:evals/gap-study-2/prereg.json | python3 -c "import json,sys; print(json.load(sys.stdin)['driver_decided_reasons'])"
   ['constant-binding', 'environment-record', 'invocation', 'outcome-binding', 'project-name', 'script-not-a-list', 'session-binding']
   ```

   The other omitted keys the copied code reads (`amendments`, `frozen_at_commit_parent`, `pinned_files` as a list, `rehearsed_study_tree_sha256`) are all inside the frozen-content check at `check_results.py:153-265`, which the README says this study does not use; `frozen_at` is written by `freeze.py`.

2. **`take.py`'s deleted-attempt guard misses a move inside the attempt roots.** `study/evals/haiku-prestudy/take.py:97` runs `git log --diff-filter=D --name-only -- <the three attempt roots>`; git's default rename detection classifies a `git mv` of a graded folder into `rehearsals/` as a rename, so it is not listed, while a move out of the roots or an outright removal is. In a scratch clone beside `study/`:

   ```
   $ git mv evals/haiku-prestudy/transcripts/.../1 evals/haiku-prestudy/rehearsals/.../row-0 && git commit -q -m x
   $ git log --diff-filter=D --name-only --format= -- evals/haiku-prestudy/transcripts/ evals/haiku-prestudy/rehearsals/ evals/haiku-prestudy/pauses/
   (nothing)
   $ git log --no-renames --diff-filter=D --name-only --format= -- <the same three>
   evals/haiku-prestudy/transcripts/number-fidelity/positive/claude-haiku-4-5-20251001/1/driver-ledger.json
   evals/haiku-prestudy/transcripts/number-fidelity/positive/claude-haiku-4-5-20251001/1/transcript.jsonl
   ```

   The reading is protected elsewhere (the moved take fails `attempt_problems`, above), so this is a guard that reads less than it claims, not a route. Cheap close: `--no-renames`.

3. **Nothing after the freeze re-derives the frozen file's body against the draft it froze.** `study/evals/haiku-prestudy/freeze.py:137-138` writes `draft_sha256_at_freeze` and `code_sha256_at_freeze`; no file reads either, and `build_draft.py --check` is skipped once frozen (`test_prestudy.py:232-236`). A post-freeze edit to `prereg.json` (say, to `driver_change.allowed_tools`) is a public commit, but `result.py:78-81` compares each ledger's allowlist to the file as it then stands. Cheap close: a test that, when frozen, compares `build_draft.build(approved_by_owner, approved_at)` to the frozen file minus the keys `freeze.py` adds, or re-serialises that and compares its sha256 to `draft_sha256_at_freeze`.

   ```
   $ grep -rn "draft_sha256_at_freeze\|code_sha256_at_freeze" evals/haiku-prestudy/*.py .github/workflows/ci.yml
   evals/haiku-prestudy/freeze.py:137:    frozen["draft_sha256_at_freeze"] = draft_sha
   evals/haiku-prestudy/freeze.py:138:    frozen["code_sha256_at_freeze"] = code_sha256()
   ```

4. **No suite test compares the pinned files to `pinned_files` once frozen.** `TheResultIsBoundToTheFreeze` (`test_prestudy.py:300-312`) exercises `binding_problems` on synthetic input only. The real comparison runs at take time (`take.py:93-96`) and at result time (`result.py:74-77`); CI's `result.py --ledger` step (`.github/workflows/ci.yml:200-201`) runs `ledger_problems` alone, so between the freeze and `RESULT.md` no CI step compares the hashes. An edited `result.py` is itself a pinned file, so the check it carries is the one an editor would remove. Cheap close: one test reading `in_force()["pinned_files"]` when it exists.

5. **Two texts disagree on a take that was denied and still reached the probe.** `driver_change.denial_outside_the_allowlist` says such a denial "reads as `did not reach`, reason `harness denial`"; `outcomes` reads `reached the probe` first and `did not reach` as "anything else", and `study/evals/haiku-prestudy/outcome.py:125-128` applies that order, with the first grid case of `TheOutcomeReasonOrder` (`test_prestudy.py:181`) pinning it. The code decides, the denial is quoted and counted beside the take, and no argument changes it, so a person cannot choose; but a reader holding the frozen file has two sentences for one case. Say "a take that did not reach the probe and carries such a denial reads as `harness denial`". An amendment after the freeze, or a rebuild with follow-up 1.

6. **Two files `outcome.py` reads at result time are bound by CI only.** `study/evals/haiku-prestudy/outcome.py:44-46` imports `evals/transcript.py` and round 2's `graders/labels.py` by path; neither is in `freeze.PINNED`, and `copy_manifest.py --check` (which refuses when either changed since the source commit) runs in the suite and CI, not in `take.py` or `result.py`. Cheap: `take.py`'s preflight and `result.py` call `copy_manifest.problems(copy_manifest.derive())`.

## What was confirmed

- **One change (step 5).** `diff <(git -C study show bf065fe…:evals/gap-study-2/drive.py) study/evals/haiku-prestudy/drive.py` prints three added hunks and no removed line: the docstring paragraph at 56-62, `argv += ["--allowedTools", *prereg.load()["driver_change"]["allowed_tools"]]` at 621, placed after `*ISOLATION_FLAGS` and before `--session-id`/`--resume` as `driver_change.where` says, and `"allowed_tools": list(pre["driver_change"]["allowed_tools"])` at 1114. `TheDriverHasOneDiff` now asserts the nine added lines by content. `study.py` differs in seven name and marker constants, `prereg.py` in the one line of `cells()` that reads only the halves a task lists, `review_kit/blindness.py` in adding this study's goal id beside round 2's; each matches its reason in `COPIED.json`, and the other ten copies are byte-identical. All 21 carried keys equal round 2's frozen values at the source commit (`TheDraftCarriesRoundTwosKeys`, and read directly). `git rev-parse 844a4ce:gars` prints the pinned tree `8a54e0f8…`; round 2's three Haiku ledgers of this cell record `run_tree_built_from` of `a4bcecd`, `58cfd3b`, `844a4ce`, equal to `round_2_take_exports`, and `TheExportCommitIsRoundTwosCheckout` shows each equal to `844a4ce` outside the exclusions.

- **Allowlist size (step 6).** Re-derived from round 2's nine transcripts of this cell with the shared parser: before the probe, Sonnet and Opus used `Bash` and `Read` (one `ToolSearch`), no `Write` or `Edit`; the first words of their Bash commands were `cat`, `cd`, `echo`, `find`, `grep`, `head`, `ls`, `pwd`, `python3`, `sed`, `wc`; Opus ran `echo` in each of its three takes, Sonnet in each of its three. The stage 00 contract at `844a4ce` names six commands, all `python3 _system/stage00_register.py …`. In the eighteen per-form probe sessions, form 1 (`…; echo "exit=$?"`) is denied under `Bash(python3:*)` alone and every other form ran; with `Bash(echo:*)` all nine ran; the all-nine session ends at form 1's denial; the driver-argv session, with both entries followed by `--session-id`, ran form 1 with no denial. No probe session file mentions `--allowedTools` (`grep -l allowedTools *.jsonl forms/*.jsonl` prints nothing), which is what limitations line 3 says. Both entries are needed for the walked route; neither admits a program beyond those the other two models ran before the probe on this cell; a denial outside them reads `did not reach`, `harness denial`, with the command quoted, which is the honest reading. `finding.py --check` re-derives every count.

- **Outcome by code (step 7).** `outcome.py` reads only `driver-ledger.json` and `transcript.jsonl`. `reached the probe` needs the ledger's non-recovery row for turn 3 with the probe line as sent and a user turn carrying that line verbatim followed by an assistant turn with text the harness did not write; otherwise `harness denial` (the sentence in a tool result or the harness's `toolDenialKind` tag, which `TheDenialTagAgreesWithTheSentence` shows agree on every round 2 transcript), then `asked` (round 2's classifier by path, only on a stopped take, only the final agent message), then `other` with the driver's outcome quoted. That is the order `outcomes` states; `test_order_is_the_prereg_order` reads it back from the file. On round 2's nine takes it reads Haiku's three as `harness denial` and the six others as `reached`. No argument, flag or field lets a person choose a reading; `route_attempt` (`drive.py:757-809`) decides graded, rehearsal or pause from the checker's verdict against the pre-registered reason list and refuses anything unlisted or a destination that exists.

- **Predictions and publication (step 8).** Three predictions, each `reached the probe`, `informed_by_round_2: true`, one stated rule, written by `build_draft.py:160-166` and so fixed before any take. `result.py` prints per take the outcome, reason, denials, ask phrases, recorded mode, the ledger's allowlist, the ledger's harness version and round 2's grader label under a heading that says it is for information; counts of three with no rate and no verb about the model; every rehearsal and pause with its reason ids and the `incomplete — mechanical` line at the cap; round 2's twelve Haiku cells from `analysis.json` under a heading that names the changed driver and says they are not added; the limitations lines. It refuses a pinned file or a ledger allowlist that differs from the frozen file and any ledger-check problem at `export_at`.

- **Trying to break it (step 9).** Re-run: the row commit fixes the session id, `drive.py` refuses an existing graded folder or an attempted row, `takes.py --add` refuses a registered or graded slot, a take index outside 1..n and a cell at its cap. Re-route: by the checker's verdict only; a graded take moved into `rehearsals/` is refused because the checker passes it. Re-read: `outcome.py` has no switch. Re-file: `take.py` commits only what the driver routed and refuses when anything else changed. Re-freeze: `freeze.py` refuses when `prereg.json` exists and admits only a rehearsal of these bytes and this code. What remains needs public commits and is listed above with its cheap check.

## The study's own checks (step 3), run from inside `study/`

```
$ python3 -W ignore evals/haiku-prestudy/test_prestudy.py
.....................
----------------------------------------------------------------------
Ran 21 tests in 8.160s

OK

$ python3 evals/haiku-prestudy/copy_manifest.py --check
ok: 14 files trace to bf065feedccc, 4 edited with a reason; round 2, round 1 and the parser unchanged

$ python3 evals/haiku-prestudy/finding.py --check
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
