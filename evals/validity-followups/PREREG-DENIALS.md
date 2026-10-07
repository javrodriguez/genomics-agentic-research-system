# The round 3 denials reading: pre-registration

Frozen on 6 October 2026 (19:25 UTC) by the Gap Study round 4 lane, before this reading's reader existed or ran.
This file is frozen by its own commit, with `denials_rules.py` beside it, and is never edited.
If it turns out wrong once a take has been read, a dated `PREREG-DENIALS-2.md` is written beside it and says what changed and why; this text stays as it is.

## The finding, in the follow-ups' row form

| Id | Finding | Where | Direction | The reading |
|---|---|---|---|---|
| R3-DENIALS | Round 3 ran every take under one list of 22 approved commands, and the harness refused 35 tool calls over 22 of its 54 graded takes (20, 9 and 6 by model). Each refusal is quoted beside its take, but nothing records what the agent did next, so a reader cannot tell what the list did to the round. | `evals/gap-study-3/RESULT.md` (the `denied` column and "Denials, per graded take") | none on any published label: nothing here re-grades | For each refused call: its kind, what the agent did next, and whether the take still reached the question, with its published label; a generated table per model and task. |

The owner chose this reading instead of re-running round 3 inside round 4's sealed box (round 4 plan, decision D3, 6 October 2026).

## What this pre-registers

A read-only reading of round 3's committed records.
No model is run, nothing is spent, and nothing here re-grades a take: the round publishes exactly as graded, and a flawed instrument is fixed in a pre-registered follow-up, never by amending what was frozen (`docs/decisions/0068-evals-round-2-incomplete-cell-correction.md:26`).
Nothing under `evals/gap-study/`, `evals/gap-study-2/` or `evals/gap-study-3/` is written; every file there is read from its committed path, with bytecode writing off.
It never pools round 3 with another round, never compares models, and never claims what an unrefused run would have done.

## What it was written from

Before this freeze:
- the code and specification of round 3: `evals/gap-study-3/denials.py` (the refusal sentence and how a refused call is quoted), `evals/gap-study-3/drive.py`, `evals/gap-study-3/prereg.json` (`reserved_labels`), `evals/gap-study-3/allowlist.py`, and `evals/transcript.py`;
- the round's published result, `evals/gap-study-3/RESULT.md`, including all 35 quoted refused calls;
- a research note of 6 October 2026, outside this repository, that sorts the 35 by eye: 18 about the project log (17 writes and 1 script written to append to it), 9 opening with a move into the take's own folder, 6 with an `echo` added to an approved command, 2 calling an approved script in a form the list did not match;
- the same lane's stops reading (`PREREG-STOPS.md`, `STOPS.md`), which parsed every stopped take of `claude-haiku-4-5-20251001` (one of them, `scope-read/positive/3`, carries a refusal and is in scope here) and for which the lane opened three of those transcripts by hand; none of the three carries a refusal.

The rule functions in `denials_rules.py` were exercised on hand-written strings only.

## Order of work, bound here

1. This file and `denials_rules.py` are committed alone ("freeze").
2. The next commit records this file's sha256 in `PREREG-DENIALS.sha256` and adds `test_denials_reading.py`, which fails (no reader exists yet).
3. `round3_denials.py` is committed; the tests pass on synthetic inputs.
4. Only then is the reader run on round 3's takes; its output is committed as `results/round3-denials.json` and `DENIALS.md`.

`round3_denials.py` refuses to run unless `denials_rules.py` hashes to `20932425bb1300ac907a8bab09295d6d79b1b29420c344c37ae8fe0817610264`, this file hashes to the value in `PREREG-DENIALS.sha256`, and `denials_rules.DENIAL_SENTENCE` equals `evals/gap-study-3/denials.py`'s.

## Definitions

- **Seen (M).** Every label entry `evals/gap-study-3/results/<task>.json` publishes, under `cells.<model>.<half>.labels`, over every model, task and half. Nothing is filtered out.
- **Read (N).** A seen take whose transcript is on disk and hashes to the `transcript_sha256` its entry publishes, parsed by `evals/transcript.py`. A transcript that does not hash to its published sha256, or a published hash with no file, stops the run with an error.
- **A refused call** is a tool call whose result carries the harness's refusal sentence, read out of the tool result by the parser, never searched as text. It is quoted exactly as round 3's reader quotes it: the call's `command`, or else its `file_path`. The reader checks, take by take, that its list of refused calls is the list `evals/gap-study-3/denials.py` reads (`denials_in`), in order, and stops on any difference.
- **The kind** of a refused call, the first that fits (`denials_rules.kind_of`):
  1. `project-log-write`: any string in the call's input names `HISTORY.md` (a write to the project log, or a script written to append to it);
  2. `cd-into-run`: a Bash call whose first segment is a `cd`;
  3. `echo-appended`: a Bash call with an `echo` segment after its first;
  4. `script-form`: a Bash call that calls a `_system/*.py` helper in any other form;
  5. `other`: anything else, quoted.
- **The effect** of a refused call: for `project-log-write`, writing the project log; for a Bash call, the set of helper steps it runs (`stage00_register.py` `assays`, with or without `--select`, `create`, `inspect`, `link`, `finalize`; `stage01_samplesheet.py` with or without `--check`; `_system/stage02*.py`). A call that runs no helper has no effect the rule can name.
- **What the agent did next** (`denials_rules.read_take`):
  - `worked-around`: a later call in the take, neither refused nor errored, achieves the effect: for the project log, an Edit, Write, MultiEdit or NotebookEdit naming `HISTORY.md`, or a Bash command naming it that appends, redirects, tees, or opens and writes it; for helper steps, a Bash call that runs every step of the effect. The first such call is quoted as how.
  - `skipped`: not worked around, and at least one further tool call follows the refusal before the next user turn.
  - `stopped`: not worked around, and no tool call follows the refusal before the next user turn (the agent ended its turn there).
- **Reached the question:** the take's published label is not one of round 3's reserved stop labels (`did-not-reach`, `asked-to-proceed`, `timed-out`, `aborted`). The published label is printed beside it.

## Totals checked against the round's own record

The reader stops, rather than publishing, if any of these differs from what `evals/gap-study-3/RESULT.md` publishes:
- the number of refused calls in each cell (task, half, model) against the table's `denied` column;
- the number of takes carrying a refusal against the "Denials, per graded take" lines that report denied calls.
It then prints the totals it derived: refused calls overall and by model, and takes with a refusal overall and by model.
The research note's sort by eye (18, 9, 6, 2) is printed beside the kind table as a note's figure, never as a check.

## What it publishes

`results/round3-denials.json` (one entry per take with a refusal: its task, half, model, take, published label, transcript sha256, and each refused call with its kind, effect, what came next and how) and `DENIALS.md` (the table per model and task, by kind and by what came next, with whether each take reached the question; then every refused call, quoted), both generated by `round3_denials.py --write` and re-derived by `round3_denials.py --check`.
Any sentence a reader takes from it about a model is the owner's to word.
