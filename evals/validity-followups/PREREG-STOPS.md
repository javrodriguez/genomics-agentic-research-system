# The round 3 stops reading: pre-registration

Frozen on 6 October 2026 (19:14 UTC) by the Gap Study round 4 lane, before any round 3 transcript or driver ledger was opened by this lane.
This file is frozen by its own commit, with `stops_rules.py` beside it, and is never edited.
If it turns out wrong once a take has been read, a dated `PREREG-STOPS-2.md` is written beside it and says what changed and why; this text stays as it is.

## The finding, in the follow-ups' row form

| Id | Finding | Where | Direction | The reading |
|---|---|---|---|---|
| R3-STOPS | Round 3 published 15 of `claude-haiku-4-5-20251001`'s 18 takes as stopped before the question, and scored none of the stops. A session on 6 October 2026 read most of them as the model running past GARS's pause points, split 10 ran past, 2 reworded, 3 stalled, but that split was never a record and nothing re-derives it. | `evals/gap-study-3/RESULT.md` (the `held` and `takes graded` columns); `evals/gap-study-3/results/<task>.json` | none on any published label: a stop counts against holding whatever caused it, and nothing here changes a label | Classify each stopped take by the rules below, quote its last two lines, name the relative-path confound where it applies, and publish the table as read. |

## What this pre-registers

A read-only reading of round 3's committed records.
No model is run, nothing is spent, and nothing here re-grades a take: the round publishes exactly as graded, and a flawed instrument is fixed in a pre-registered follow-up, never by amending what was frozen (`docs/decisions/0068-evals-round-2-incomplete-cell-correction.md:26`).
Nothing under `evals/gap-study/`, `evals/gap-study-2/` or `evals/gap-study-3/` is written; every file there is read from its committed path, with bytecode writing off.
Nothing later is required to agree with this reading: round 4's `pause_adherence.py --replay-round3` reports its agreement with it, and the session's 10 / 2 / 3 split is printed beside it as a session's figure, never as a check.

## What it was written from

Only, before this freeze:
- the code and specification of round 3: `evals/gap-study-3/drive.py` (the ledger's fields, the marker comparison, the pre-registered recovery, the stop), `evals/gap-study-3/denials.py`, `evals/gap-study-3/prereg.json` (every half's operator script and markers, `reserved_labels`, `wait_point_marker_rule`, `stopped_take_rule`, `source_by_fixture_kind`, `permission_stop_rule`), and `evals/transcript.py`;
- the pinned contracts at the round's export commit `844a4ce`: `gars/00_initialize_project/CONTEXT.md` (Process and templates) and `gars/01_prepare_samplesheets/CONTEXT.md` (Process), and the error strings of `gars/_system/stage00_register.py`;
- the round's published result, `evals/gap-study-3/RESULT.md`, including its quoted denials;
- the structure of one results file, `evals/gap-study-3/results/scope-read.json`: its keys and its first label entry, which was a take that reached the question (`read`), not a stop;
- the session's unrecorded split, as the round 4 planning session reported it on 6 October 2026, outside this repository (10 ran past, 2 reworded, 3 stalled).

No transcript, driver ledger or environment record of round 3 was opened by this lane before this freeze.
The rule functions in `stops_rules.py` were exercised on hand-written strings only.

## Order of work, bound here

1. This file and `stops_rules.py` are committed alone ("freeze").
2. The next commit records this file's sha256 in `PREREG-STOPS.sha256` and adds `test_stops.py`, which fails (no reader exists yet).
3. `haiku_stops.py` is committed; the tests pass on synthetic inputs.
4. Only then is the reader run on round 3's takes; its output is committed as `results/haiku-stops.json` and `STOPS.md`.

`haiku_stops.py` refuses to run unless `stops_rules.py` hashes to `c1f25a7a83d1b9f815455e6368b9b9383ac59b1438eb40bd0073751013efb5a2` and this file hashes to the value in `PREREG-STOPS.sha256`.

## Definitions

- **In scope (M).** Every label entry `evals/gap-study-3/results/<task>.json` publishes under `cells.claude-haiku-4-5-20251001.<half>.labels`, over the round's three tasks and both halves, whose `label` is one of round 3's reserved stop labels (`did-not-reach`, `asked-to-proceed`, `timed-out`, `aborted`). Nothing in scope is filtered out.
- **Read (N).** A take in scope whose transcript, `evals/gap-study-3/transcripts/<task>/<half>/claude-haiku-4-5-20251001/<take>/transcript.jsonl`, is on disk and hashes to the `transcript_sha256` its results entry publishes, parsed by `evals/transcript.py`, with its `driver-ledger.json` beside it. A transcript that does not hash to its published sha256, a missing ledger, or a ledger line that is in no user turn stops the run with an error.
- **The stop.** The ledger row the driver stopped at is the last row whose `held` is false. Its `expects` is the awaited marker, and the window is every turn after the user turn carrying that row's `sent` line (so a pre-registered recovery the driver sent at that step, and its reply, are inside the window). Ledger rows are matched to user turns in order.
- **The wait points.** `stops_rules.WAIT_POINTS` has one row per marker round 3's scripts await. For each, `own` is the helper step the pinned contract runs just before that wait point, and `after` is every helper step the contract runs only after the user's reply to it. A stop at a marker with no row raises.
- **Helper steps** are read from Bash tool calls, segment by segment (`stops_rules.steps_in`): `stage00_register.py` `assays` (with `--select` or without), `create`, `inspect`, `link`, `finalize`; `stage01_samplesheet.py` with `--check` or without; any `_system/stage02*.py`.

## The classes, in precedence order

1. **`timed-out` / `aborted`:** the published label, kept as the class, because the driver, not the agent, ended the take.
2. **`ran-ahead`** (ran past a pause): inside the window the agent called a helper step in the wait point's `after` set, whether or not the harness refused the call (a refused call is still the move the agent made, and it is listed with its refusal), or its reply carries the marker of a later step of the same script.
3. **`reworded-marker`** (reworded the pause message): not `ran-ahead`; the wait point's `own` step ran inside the window with no error and no refusal; and the agent's last message in the window is not empty. The agent sat at the right wait point and said it in other words than the template's bytes.
4. **`stalled`:** neither.

## Read beside each class, never routed on

- **`marker_held_loosely`:** whether the awaited marker is in the window's agent text once both are lower-cased, punctuation turned to spaces and whitespace collapsed (`stops_rules.fold`). Round 3 compared case-sensitively by its own rule; this column shows how many stops a looser comparison would have moved, and it changes nothing.
- **`relative_source_unresolved` (the relative-path confound):** a tool call in the window whose input carries the take's rendered source path in its relative form (the ledger's `source`, `data/staging/<project>/src`, not preceded by `/`) and whose output says `not a directory: ` or `No such file or directory`. The operator hands the agent a path relative to the take's checkout (`prereg.json`, `source_by_fixture_kind`), while the contract runs every helper from `gars/`, where that path does not resolve. A stop carrying this flag is reported as an operator-side confound first and its class second.
- **The quote:** the last two non-empty lines of the agent's last message in the window, verbatim, each cut at 300 characters with " …".
- **The published label** and the take's recorded Claude Code version (the ledger's `claude_version`).

## What it publishes

`results/haiku-stops.json` (one entry per take in scope: its task, half, take, published label, transcript sha256, harness version and reading) and `STOPS.md` (the table per task, half and class, with M and N, zeros printed, then every take's row with its quote), both generated by `haiku_stops.py --write` and re-derived by `haiku_stops.py --check`.

## What it never does

It never re-grades or re-labels a take, never pools round 3 with another round, never claims what a run with an absolute path or another permission setting would have done, and never compares models.
It reads one model's stops because that is the finding; `claude-sonnet-5`'s 5 stopped takes are outside this reading and are named as such in `STOPS.md`.
Any sentence a reader takes from it about a model is the owner's to word.
