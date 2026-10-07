# The round 3 denials reading: pre-registration, amendment 2

Dated 6 October 2026 (written about 20:03 UTC) by the Gap Study round 4 lane, after the first run of `round3_denials.py` (`results/round3-denials.json`, `DENIALS.md`) and after one fresh review of it.
`PREREG-DENIALS.md` and `denials_rules.py` are unchanged, and every first-run field stays as they define it; this file adds readings beside them, frozen by its own commit with `denials_rules_2.py`.
**This amendment was written knowing the first run's output and the review's findings.** Nothing it adds is a pre-registered result; it corrects how the first reading names and glosses what it found, and closes gaps the review found.

## Why

A fresh review (claude-opus-5-5, 6 October 2026) re-derived every first-run figure (35 refused calls in 22 takes; kinds 18 / 9 / 6 / 2 / 0; next 19 / 9 / 7). It found two major and several minor problems:
1. **The kind `cd-into-run` names a feature the harness admitted.** Over every round 3 Bash call, all 15 calls with an `echo` of `$?` after their first segment were refused, on both harness versions. All 9 refused calls that open with `cd` carry that echo, and no call that opens with `cd` without it was refused. Each admitted retry kept the `cd` and dropped only the echo. One refused feature was split into two kinds, and the decision record's "anything else was refused automatically" and "a form the list admitted" are contradicted by the same data: the harness admitted many calls outside the 22 entries.
2. **`skipped` was glossed as "the agent went on without it"**, but for 7 of the 9 skipped project-log writes the agent's next move in the same turn was another attempt at the same write, itself refused.
3. **Smaller ones:**
   - the shell-write rule is looser than its text (an `open(` alone or any `>` counts, while `sed -i` or `cp` would not), though it affects no call here;
   - the tests did not drive every kind, refusal and mutation the record said they did;
   - the cross-check against round 3's own reader shares its predicate, so it cannot catch a refusal worded differently;
   - the record's take-level sentences were typed, not generated;
   - the table printed no definitions and no harness versions;
   - the freeze time (19:25 UTC) is a minute before its commit (19:26:09 UTC).

## What this adds (all in `denials_rules_2.py`, sha256 recorded below)

- **A second kind, `status-echo`, ahead of `cd-into-run`** (`kind_2`): a Bash call with an `echo` segment containing `$?` after its first segment. The first-run kind is kept beside it.
- **A second "next", `retried`, ahead of `skipped`** (`read_take_2`): not worked around, and a later call in the same turn makes another attempt at the same effect. For the project log, an attempt is any non-read call naming `HISTORY.md`; for helper steps, a Bash call running every step of the effect, refused, errored or not. The first-run "next" is kept beside it.
- **The segments an admitted retry dropped** from the refused call, for every worked-around Bash call.
- **A take-level reading of the project log** (`project_log_reading`), for each take with a refused log write: was the log written by a later call, and did the agent's turn end right after its last refused attempt.
- **A cross-tab of every round 3 Bash call**, not only the refused ones (`cross_tab_key`): by opens-with-`cd`, `$?` echo and other echo, against refused or admitted.
- **An independent sweep** (`refusal_like_without_sentence`): every errored tool result in the round worded like a refusal but without the pinned sentence. It is printed with each hit's first line, so a refusal worded differently by either harness version would show.
- **The harness version of each take**, read from its `driver-ledger.json` (`claude_version`), printed beside the by-model counts.
- **The definitions**, printed verbatim above the tables.

## Rules for any reuse

Before `denials_rules.py` is reused on other takes, two things change. The shell-write rule must require a write (an append or redirect into the file, `tee`, `sed -i`, `cp` or `mv` onto it, or an `open` in a write mode followed by a write), and the work-around must be the same entry. The helper-step parser must ignore helper names inside a Python string. Neither moves a figure here: the one log work-around appends the same stage 01 entry, and the one call with a helper name inside a Python string was not refused.

## What the reader does now

`round3_denials.py --check` re-derives both outputs:
- the first run's, `results/round3-denials.json` and `DENIALS.md`, byte for byte as committed, by the first rules and the first render;
- this amendment's, `results/round3-denials-2.json` and `DENIALS-2.md`.

It reads the sha256 of each rules file from the text of its own pre-registration file and refuses unless the file hashes to it. Each pre-registration file must also hash to its `.sha256` record. The rules files are `denials_rules.py` (`20932425bb1300ac907a8bab09295d6d79b1b29420c344c37ae8fe0817610264`) and `denials_rules_2.py` (`e0bdd282a3c072cb26a0d5703c704e7f343ed362b0439e2f1b8d4d259703cb85`).

## What it never does

Everything `PREREG-DENIALS.md` says it never does still holds: no re-grade, no pooling, no model comparison, and no claim about what an unrefused run would have done.
The cross-tab describes which calls the harness admitted and refused; it does not claim why the harness decided as it did.
