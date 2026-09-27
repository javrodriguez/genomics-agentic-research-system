---
date: 2026-09-27
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/_system/tools/policy.py
symptoms:
  - follow-up 0165 changes the guard and its Bash tokenizer under the protected prefix gars/_system/ with no owner approval record
---
# Guard-lexer follow-up 0165: approval of its protected change, under the owner's delegation

Addendum to [0165](0165-guard-lexer.md), which stays byte-identical.
The two files this record approves are protected (`gars/_system/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0161](0161-front-door-0160-delegated-approval-of-protected-change.md).

## Context

Follow-up 0165 stops a bare filesystem command from crashing the guard, judges an operand-free filesystem call at its default path, and lets a filesystem command carry a quoted shell operator as the literal byte bash passes it, while refusing every shell construct that survives quote removal.
The lane's coordinator (glitch-a1, writing under the owner's standing delegation and not in the owner's words) asked before the build whether any installed ripgrep flag that runs a program is allowed; none is, because the flag vocabulary is already an allow-list (0165, Decision 5), so no flag change was made.
It was built on its own branch from public main `4597dd4` by a Codex producer in an isolated clone (session `01a0e2a0-2d44-7563-b564-c714e2f1637a`, five rounds), and reviewed twice by a fresh Claude Code context (Opus 5.5) from a separate checkout with no remote that never saw the producer's transcript.
Producer commits, each under the repository's own identity, red-first (the failing tests committed before each fix):
round 1 `1815775`, `504b023` (the bounds check), `a734520`, `29e511a` (the quote-state scan);
round 2 `0d03023`, `1b2c059` (the default path judged), `d93167b`, `73b684d` (word-start comments), both from the lane's own probe of round 1;
round 3 `c14a3e7`, `91a1274` (unquoted braces and tildes), `b54509b` (the zsh comparison leg), from review r1;
round 4 `7abf2e7`, `792a4cf` (unquoted closing brace), from the zsh leg's first finding;
round 5 `926e244`, `dbebd7c` (unquoted parentheses, and witness rows for the opening brace), from review r2 and the lane's mutation proof.
The lane's own commit `2dd0361` adds 0165, the index and the suite totals.
Reviews, kept outside the repository and cited by their kit folders:
`gars-guard-lexer/reviews/r1` APPROVE WITH CHANGES on `4597dd4..73b684d` (three MINOR, three NOTE; no BLOCKER or MAJOR). F-1, MINOR on a refusal path: braces and tildes expand after quote removal, so `ls {..,"|"}` and `ls ~/"|"` had become allowed; answered in round 3. F-2, MINOR on a refusal path, pre-existing: a brace word was judged unexpanded, so `cat {../projects/closed/…,x}` reached a closed project's file at `4597dd4`; answered by the same change, except its `.*`-matches-`..` part, deferred as 0165's D8. F-3: README totals, answered by the lane's commit. F-4, NOTE: a zsh leg; answered in round 3. F-5 and F-6, NOTE: recorded in 0165.
`gars-guard-lexer/reviews/r2` APPROVE WITH CHANGES on `73b684d..792a4cf` (one MINOR, three NOTE). F-1, MINOR on a refusal path: zsh runs a glob qualifier's string and `=(…)` as commands, so `ls *(e:'touch a;touch b':)` had become allowed; answered in round 5 with the reviewer's own proposed fix, which the reviewer had verified on a patched copy. F-2, NOTE, pre-existing: the single-command qualifier form, a closed-file read included, was allowed at `4597dd4`; closed by the same fix. F-3, NOTE: deferred as 0165's D9. F-4, NOTE: message wording, 0165's D5.
A third review of `792a4cf..dbebd7c` was stopped by Claude's safety classifier at 13:57:41Z and not retried; that range is exactly r2's proposed fix plus test rows, and the lane's coordinator ruled r2 the last review (0165, "What this does not close").

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected changes as merged.

1. **`gars/_system/guard_hook.py`**: the pilot-log check applies only when the call has an operand (`len(tokens) > 1`); a non-dispatcher filesystem call whose paths are `parse_argv`'s default has `.` judged as if typed. The line `tokens = simple_tokens(command)` is byte-identical.
2. **`gars/_system/tools/policy.py`** (`simple_tokens` only, same signature and return value): a POSIX quote-state scan; `$`, backtick, CR and LF refused anywhere; an unquoted or escaped `; | & < >` refused; a quoted one tolerated only when the first word is a registry filesystem executable; an open quote refused; an unquoted word-start `#`, and an unquoted `{`, `}`, `~`, `(` or `)`, refused for every command.

Outside the protected prefixes, recorded for completeness: `gars/tests/test_bash_lexer.py` (new), the three new tests in `test_guard_hook.py` and the four changed expectations in `test_nonpublic_read_block.py` named in 0165, 0165 itself, the index, and the README and DEVELOPMENT counts and skip figures.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0165, the coordinator's pre-build flag question and its answer, the round 2 to 5 briefs, the review dispositions above, and the coordinator's ruling that r2 is the last review.

## What this does not close

- 0165's D1 to D3 and D5 to D9, the zsh `=word` exclusion, and the unheld third review.
- The visitor-visible side effect named in 0165: a literal `~`, `{`, `}`, `(` or `)`, or a word-start `#`, must now be quoted.

## Test

Glitch verified the landing merge `eb1afc6` (branch head `2dd0361` merged onto public main `4597dd4`), each evidence run under its machine's booking, with a process snapshot at its start and end.

- This Mac (macOS, Python 3.8.2), a fresh clone of the merge, with Docker answering and row 5's scratch folder and `TMPDIR` set as CI sets them: `Ran 1144 tests`, `OK (skipped=14)`, README's mode-A figure; contracts, counts and the pre-registration check clean; the repository status clean after the run. Its `evals/test_harness.py` step ended with 13 errors, all `str.removesuffix`, `str.removeprefix` or `ast.unparse`, Python 3.9 APIs this Mac's Python 3.8.2 lacks; `evals/` has no change in this landing, 0156 and 0161 recorded the same red, and the build node ran the harness 44 OK at the merge, so the red is the interpreter's, not this change's. Only other sessions' waiting schedulers were present at the start, after the suite and at the end.
- The build node's owner account (Linux, Python 3.13.5), fresh bundle clone of the merge: `Ran 1144 tests`, `OK (skipped=82)` without containers, and `OK (skipped=124)` with `TMPDIR` also unset; each is one more than at 0161 because the new zsh comparison skips where zsh is absent; contracts and counts clean; the evaluation harness 44 OK and the pre-registration check clean; the snapshots at the start, between the runs, after them and at the end show no other suite, Codex or Claude. **Caveat:** another lane disclosed that its mutation attempt ran on the same account from about 14:10:45Z to 14:13:10Z, inside the `TMPDIR`-set run (it started 8 s after that run's start snapshot and ended before the next, so neither saw it; it was stopped by process id and its module restored under a hash check). That run passed with the expected figure, so its result is kept and the overlap is recorded here.
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the records commit's `README.md` with the `TMPDIR`-unset Linux run's log: `plain run: Ran 1144 tests, OK, skipped 124` and `ok: 124 skips, at most 124 documented` (a planted 125 fails it).
- At the merge's tree: `check_counts` 1144 clean; `check_contracts` 14 clean; `test_decision_links_resolve` OK; `release_check.py --check` 13/13.
- A mutation proof at the branch's last code commit `dbebd7c` on the build node: seventeen mutants (the bounds check removed; the default path not judged; the quote state dropped; a backslash escaping inside single quotes; `\\` not escaping inside double quotes; `$` let through; the filesystem-first-word condition dropped; an escaped unquoted operator accepted; the open-quote refusal dropped; a word-start `#` let through; a tab not ending a word; a quoted operator never flagged; each of `{`, `}`, `~`, `(`, `)` let through alone); sixteen killed with the unchanged control green; the open-quote mutant survives because `shlex` raises the same refusal, and it is not counted as a kill.
- The real-shell comparison: every command the scan accepts in the committed corpus gives the tokenizer's argv exactly under bash and under zsh (`printf` in place of the command); the producer's wider 238-row corpus had 108 accepted rows per shell and no disagreement.
- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at `eb1afc6`'s tree, prompt and suite hashes equal to the previous record's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260927-front-door.json`, floor `evals/runs/smoke/smoke-20260926-row-14-activation.json`; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20260927-guard-lexer.json`).
- The outgoing range `4597dd4..` the records commit has no gitleaks finding under either ruleset, no canary and no private address or path.

## Status

Standing. Approval of follow-up 0165's protected changes only.

## Date

2026-09-27
