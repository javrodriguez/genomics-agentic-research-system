---
date: 2026-09-28
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/_system/tools/policy.py
  - gars/_system/tool_call.py
symptoms:
  - follow-up 0175 changes the guard and the dispatcher under the protected prefix gars/_system/ with no owner approval record
---
# Guard messages follow-up 0175: approval of its protected change, under the owner's delegation

Addendum to [0175](0175-guard-messages.md), which stays byte-identical.
The files this record approves are protected (`gars/_system/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0171](0171-executor-env-0170-delegated-approval-of-protected-change.md).

## Context

Follow-up 0175 changes the text of the guard's and the dispatcher's refusals, never what they refuse.
The lane's coordinator (glitch-a1, writing under the owner's standing delegation and not in the owner's words) ruled on 27 Sep 2026 that the lane runs from the build Mac that night rather than as an observed lane on the build node, with a Codex producer on the Mac's default account.
It was built from public main `a80df2d` by that producer in an isolated clone with no remote (session `01a0e5c7-97e7-77d0-9d22-1968756e2f76`, seven rounds), and reviewed five times by a fresh Claude Code context (Opus 5.5) from a separate checkout with no remote that never saw the producer's transcript.

**The producer's history is private and is not published.**
Its first decision pin carried the build machine's absolute scratch path, written with JSON escapes and inside compressed snapshots where no text scanner reads it; round 2 regenerated the fixture without it, but the earlier commits still held it.
Later, the full suite on this Mac found that the repository's own committed-tree secret scan flagged two fixture rows (below), and removing the file from the fixture would still have left it in the pin commit's history.
Under the coordinator's rulings (the lane's, under the owner's delegation), the branch was rebuilt on `a80df2d` twice, each time in the same order with the final content only, and every earlier line of work stays on local branches that are never pushed:
the producer's rounds 1 to 4 and the lane's first records, `67d1c34` `5891795` `7a22ce5` `145ac23` `8ee8d98` `c360033` `21a08f7` `07cc6f8` `2fb6c01` `29867dd` `bd8b5ee` `2383f6f` `2220f2a` `587a5f6` `3120436` `aa900bd` `98e56c1` `764a745` `fa6dcce`;
the first clean rebuild and the producer's rounds 5 and 6 on it, `8331d07` `b5f3afa` `a89b7a5` `a24ed01` `28398e6` `4a70851` `32c0f54` `2f8c84e` `932fb00` `7776585` `300657b` `cb1b41c`.
The build log keeps citing those private ids.
The published branch is `62ea514` (inventory) · `0dd9dca` (the pin, alone) · `b4a58b6` (red tests) · `fce9b65` (wording and moved assertions) · `e949aaf` (build log) · `35aeee4` (0175, index, counts); its tree is byte-identical to `cb1b41c`'s (`8266467bebd9…`).
Public main then moved to the filesystem-tool vocabulary follow-up ([0185](0185-filesystem-tool-vocabulary.md)); the published branch continues with round 7, `f8d56b5` (the merge of that main, resolving `tools/policy.py` so every 0185 refusal is refused exactly as there and reads in this change's shape), `f950965` (the pin regenerated at that main's own guard, 2606 rows), `0d9444e` (build log), and the lane's `5809ff9` (0175 after the merge).
Re-shown on the published branch: the pin alone reads `decision pin: 1709 refused, 470 allowed; OK`; `test_refusal_messages.py` is `FAILED (failures=3270)` at `b4a58b6` with the pin green, and `OK` (15 tests) at `fce9b65`, where the committed-tree secret scan also reads `0 findings`.
The range from `a80df2d` to the landing merge has no gitleaks finding under either ruleset in any commit, and no owner name, node name, home path, address or canary.

Reviews, kept outside the repository and cited by their folders:
`gars-guard-messages/review-1` APPROVE WITH CHANGES on `a80df2d..2220f2a` (one MAJOR, one MINOR, five NOTE). F1, MAJOR: an unregistered typed tool sent through the dispatcher over Bash was told its JSON could not be read; fixed in round 4. F2, MINOR: the R-096 texts said a command disables the secret scan when it only contained the words; fixed in round 4. F3, NOTE: a guard letting a two-path `find` through passed the pin; 13 rows added in round 4, and that plant now turns the pin red. F4 to F7, NOTE: recorded in 0175.
`gars-guard-messages/review-2` APPROVE on `2220f2a..98e56c1` (six NOTE); F1 to F4 closed, each red when reverted; its new NOTEs are recorded in 0175.
`gars-guard-messages/review-3` APPROVE on `4a70851..932fb00` (round 5, one NOTE): no run in the producer's evidence replayed the corpus with the temp variables unset against the system default; the build node's run without `TMPDIR` below is that run.
`gars-guard-messages/review-4` APPROVE on `7776585..cb1b41c` (round 6, one NOTE, below).
`gars-guard-messages/review-5` APPROVE on `35aeee4..0d9444e` (round 7, the merge onto 0185, no findings): what 0185 refuses is unchanged, and each of 0185's four new refusals carries this change's shape with a next step the guard allows.
The lane's own read before review found the fixture's machine path; the lane's checks used json-built hook payloads only, and no model was asked to test the guard.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged.

1. **`gars/_system/guard_hook.py`**: `deny()` without its suffix; every refusal text with its own rule citation and one `Next: ` sentence; the outside-read sentence; the R-096 texts. Every check, its order, and the lines `tokens = simple_tokens(command)` and `command = tool_input.get("command")` are as at `a80df2d`.
2. **`gars/_system/tools/policy.py`**: `Refusal`'s `alternative` and each site's text; the vocabulary and unregistered-command advice read from the registry; the name check's refusal inside `parse_argv` given its own text. Every `field`, `rule` and `type`, and every exit code, is as at `a80df2d`.
3. **`gars/_system/tool_call.py`**: each refusal's text and alternative.

Outside the protected prefixes, recorded for completeness: `gars/tests/test_refusal_messages.py`, `gars/tests/build_refusal_corpus.py`, `gars/tests/fixtures/refusal_decisions.jsonl`, the moved assertions named in 0175, the inventory and build log under `docs/implementation/`, 0175, the index, and the README and DEVELOPMENT counts and skip figures.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0175 and its four question defaults, the Mac road, the privacy repair and the recursive privacy scan, the round 4 brief, the review dispositions, and the private rebuild.

## What this does not close

- 0175's named NOTEs.
- Round 6's fixture change: two rows (`test_pilot_doors-1329` and `-1341`) captured a pilot-doors fixture file holding a 64-hex cache key after `key=` (with `key_formula: downstream-v1`), a hash, not a credential, which gitleaks' `generic-api-key` rule flagged in the committed tree (`gars/tests/test_secret_containment.py`); the captured `submit.sh` and `reproducibility/manifest.json` were dropped from exactly those rows after both rows, regenerated at `a80df2d` without them, gave identical decisions, and `gars/.gitleaks.toml` is unchanged. Review r4's NOTE: to keep the other 2177 rows byte-identical, the two shared texts were blanked under their content-hash ids, which four other rows (`test_pilot_doors-1355`, `-1358`, `-1382`, `-1518`) also reference, so they replay two empty files whose ids no longer match their content; their decisions are unchanged, and a future regeneration should drop the files at capture instead.
- On the published branch the pin commit was committed with the lane's staged-diff check reading two hits, both the agent-id pattern matching two `test_nonpublic_read_block` row names; gitleaks read 0; read and judged innocent before the commit. On the first clean rebuild the same commit had gone in with six hits unread (the check's exit code was lost in a pipe); that line of history is private.

## Test

Glitch verified the merge `4d7d83b` (branch head `5809ff9` merged onto public main `868a1b2`, 0185's landing), each evidence run with a process snapshot at its start and end, then carried it to the landing merge (addendum below).

- This Mac (macOS, Python 3.8.2), a fresh clone of the merge, with Docker answering and row 5's scratch folder and `TMPDIR` set as CI sets them: `Ran 1187 tests`, `OK (skipped=14)`, README's mode-A figure; contracts, counts and the pre-registration check clean; the repository status clean after the run. Its `evals/test_harness.py` step ended with 13 errors, all Python 3.9 APIs this Mac's Python 3.8.2 lacks; `evals/` has no change here, earlier landings recorded the same red, and the build node's Python 3.13.5 ran the harness 44 OK.
- The build node's owner account (Linux, Python 3.13.5), a fresh bundle clone of the merge, with no other account running a suite, Codex or Claude at the start, between the runs or at the end: `Ran 1187 tests`, `OK (skipped=82)` without containers, and `OK (skipped=124)` with `TMPDIR` also unset, which replays the decision pin against the system's own temp folder (review r3's NOTE); contracts and counts clean; the evaluation harness 44 OK and the pre-registration check clean.
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the records commit's `README.md` with that Linux run's log: `plain run: Ran 1187 tests, OK, skipped 124` and `ok: 124 skips, at most 124 documented` (a planted 125 fails it).
- At the merge's tree: `check_counts` 1187 clean; `check_contracts` 14 clean; `test_decision_links_resolve` OK; `release_check.py --check` 13/13.
- The decision pin: 2606 rows regenerated at `868a1b2`'s own guard replay there as `decision pin: 1995 refused, 611 allowed; OK`, and replay identically through the merge's guard; against the pin at `a80df2d`, exactly the five rows 0175 names changed, each by 0185.
- 0185's own probe table (92 cases) gives the same exit code, record rule and field at `868a1b2` and at the merge.
- The model-free probe of this lane's reported rows (json-built hook payloads, never a model): every row keeps its exit code, each refusal text names one next step, and none names an "approval store".
- Mutation proof on the producer's branch: the generic suffix restored, one site's alternative dropped, a refused payload allowed (including a two-path `find`), a record `rule` changed, and "approval store" restored each turn `test_refusal_messages.py` red; a home path planted in plain, escaped or compressed form turns its privacy scan red; each unchanged control green.
- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at the landing merge `c62867d`'s tree, prompt and suite hashes equal to the previous record's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260928-fs-vocab.json`, floor `evals/runs/smoke/smoke-20260926-row-14-activation.json`; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (record `evals/runs/smoke/smoke-20260928-guard-messages.json`).
- The outgoing range from `2992188` to the records commit has no gitleaks finding under either ruleset and no canary, owner name, node name, private address or home path in any commit.

## Addendum: carried over onto the bio-faults speed landing

Public main moved, after the evidence above, from `868a1b2` to `2992188` (the bio-faults speed follow-up, [0181](0181-science-fault-module-one-control-per-case-and-a-bounded-pool.md)).
Under the coordinator's carry-over ruling (the lane's, under the owner's delegation), the merge was rebuilt as `c62867d` (first parent `2992188`, second parent the same branch head `5809ff9`) and the suite evidence above is carried to it without a re-run, on three conditions, each checked:

- (a) The tree difference from the evidenced merge `4d7d83b` to `c62867d` is exactly the speed landing's own change: 0181, one added index row and `tests/test_bio_faults_faults.py`, each file's difference byte-identical to `868a1b2..2992188`; the index regenerated at `c62867d` is unchanged; no other file differs.
- (b) No file this follow-up adds or changes reads 0181, the decisions index or the fault module.
- (c) 0181's own evidence shows the new fault module gives the old one's verdicts, and the old module ran green inside all three suites above.

Done at the landing merge: the smoke ceremony above (it ran only there), the trailer audit, the secret and privacy sweep over `2992188..` the records commit, and the Fresh-clone gate against the records commit's README.

## Status

Standing. Approval of follow-up 0175's protected change only.

## Date

2026-09-28
