# The environment smoke

## What it is, and what it is not

This folder holds four one-turn smokes of the driver's checkout, run on 13 September 2026 on harness 2.1.267.
Each sends one neutral line, "Reply with the single word: ready.", to an agent in a freshly built checkout of commit `f7cf4d6`.
The line names no task, the checkout holds no fixture, and no operator script is sent.
A smoke is not a walk and not a take: nothing it records is graded or used to fix a script.
It measures the environment each take starts in, which is the operator's side of every take.
Every turn's environment is built by the driver's own `child_env()`, and each `environment.json` is written by the driver's own `environment_record` and `with_turns`.

## Why four and not two

The plan named one pair on `claude-haiku-4-5-20251001`: one run with nothing stripped and one with the draft's `stripped_env`.
The lead added a second pair on `claude-sonnet-5`, beyond the plan, to answer the effort question: round 1's Haiku transcripts carry no effort key, so a Haiku pair cannot show where round 1's Opus and Sonnet "high" came from.

## The commands

```
python3 evals/gap-study-2/smoke_run_tree.py --strip none --out evals/gap-study-2/verification/env-smoke/unstripped
python3 evals/gap-study-2/smoke_run_tree.py --strip draft --out evals/gap-study-2/verification/env-smoke/stripped
python3 evals/gap-study-2/smoke_run_tree.py --compare evals/gap-study-2/verification/env-smoke/unstripped evals/gap-study-2/verification/env-smoke/stripped
python3 evals/gap-study-2/smoke_run_tree.py --strip none --model claude-sonnet-5 --out evals/gap-study-2/verification/env-smoke/unstripped-sonnet
python3 evals/gap-study-2/smoke_run_tree.py --strip draft --model claude-sonnet-5 --out evals/gap-study-2/verification/env-smoke/stripped-sonnet
python3 evals/gap-study-2/smoke_run_tree.py --compare evals/gap-study-2/verification/env-smoke/unstripped-sonnet evals/gap-study-2/verification/env-smoke/stripped-sonnet
python3 evals/gap-study-2/scrub.py <each of the four transcripts> --write
```

## What each folder records

These four folders hold the second run, driven after the exclusion below, with the same commands, each output folder removed first.
The first run is not kept: a record is replaced whole, never merged.
Each of its four smokes swept 64 hits in the exported checkout, against 4 in round 1's smokes, because documents naming the study had been added under docs/ since round 1.
Those documents are now in `run_location.excluded_from_the_run_tree`, and PROTOCOL.md (CP3) records the finding.

Each of the four runs below exited 0, recorded `failures` empty, excluded 7 paths from the checkout, and swept 5 hits: 4 in README.md and 1 in docs/RESULTS.md, the two files `run_location.permitted_sweep_files` names.

`unstripped/` (Haiku, `--strip none`): the reply "ready.", `names_present` lists `CLAUDE_CODE_MESSAGING_TOKEN` (matched by the generic shape), and `stripped_names` is empty.

`stripped/` (Haiku, `--strip draft`): the reply "ready.", `names_present` is empty, and `stripped_names` holds the twelve names of `driver_constants.stripped_env`.
Each of the twelve was present in the environment of the pane the smoke was launched from.

`unstripped-sonnet/` (Sonnet, `--strip none`): the reply "ready", with the same `names_present` and empty `stripped_names` as the Haiku run.

`stripped-sonnet/` (Sonnet, `--strip draft`): the reply "ready", with `names_present` empty and the twelve names in `stripped_names`.

Both `--compare` runs exit 0 with "the records differ only in the stripped names".
In each of the four records `api_key_set` and `billing_route_set` are false, and the one turn reports credential source "none".

The sha256 of each `environment.json`, as committed:

| folder | sha256 of environment.json |
|---|---|
| `unstripped` | `f2c8d4013079d7f3ab3bfaee5ccfbcf45f14f9ede45d255899016b6e90ded1a9` |
| `stripped` | `a5eb72538a3d315fe4632e09b5739d39dfc4882e5b2008c988c4c27d49897265` |
| `unstripped-sonnet` | `571d22c1d516230b85e2e59ae19f9836ffd8e0ce52f2ad19c9d2164f7dec4ea9` |
| `stripped-sonnet` | `178b70da1f2d8f18acd949ea38c5c8a886428a686738a04cd969f4f4372ab4f0` |

`check_take.environment_problems` reads each of the four records, against a ledger built from its `report.json` and the draft with `subscription_source` set, and returns no problem for any of them.

## What a take driven from a Claude Code pane inherits

The stripped run's `stripped_names` shows what the pane hands a child process: all twelve names J4 lists, `CLAUDECODE`, `CLAUDE_AGENT_SDK_VERSION`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING`, `CLAUDE_CODE_ENABLE_TASKS`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_EXECPATH`, `CLAUDE_CODE_MESSAGING_SOCKET`, `CLAUDE_CODE_MESSAGING_TOKEN`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_EFFORT` and `CLAUDE_PID`.
The unstripped record lists only one of them, `CLAUDE_CODE_MESSAGING_TOKEN`, because it is the only one that matches a recorded name pattern (the generic `_TOKEN$`); the other eleven match none and the record names only matching variables.
Names only: no value is read or written.

## Headless login under J4

The stripped runs show that a headless session opens and answers under a subscription login with the twelve names removed.
So J4's strip costs no login, on this harness.

## The subscription value "none", and why it is not null

On harness 2.1.267 a subscription login makes the harness report `apiKeySource` "none" in the stream's `system/init` record.
Every turn of the four smokes reported that string.
It is the harness's own report, and it is now the draft's `environment_record.subscription_source`.
It is distinct from null: the driver writes null, never "none", when a turn's stream carries no init source, and `costs.py` names a null turn as a gap.
A record whose turns say "none" under the pre-registered source evidences the turn; a record whose turn says null does not.

## Effort, and its limit

Haiku, both runs: no effort key, and `perTurnEffort` null on 2 records each.
Sonnet, both runs: `"effort": "high"` on 1 record and `perTurnEffort` null on 1 record, the same with `CLAUDE_EFFORT` stripped as without it.
So on harness 2.1.267, a Sonnet session records "high" whether or not `CLAUDE_EFFORT` is inherited: "high" is the model's default here, not an inherited value.
Round 1's 108 driver ledgers each record harness 2.1.267, the same version string.
That is evidence about where round 1's Opus and Sonnet "high" came from, not proof: the smoke measured one turn on Sonnet and none on Opus, in a different session from round 1's.

## The scrub

`scrub.py --write` removed one field from each of the four transcripts, `session_context.userEmail`, and each `scrub.json` records the hashes before and after.
No account identifier is left.
Each transcript still carries machine paths, as round 1's committed smoke transcripts do; they are records, and records are not edited.

## The run tree's own temp folder (ruling C, 14 September 2026)

After ruling C the driver sets TMPDIR, TMP and TEMP to `.tmp/` inside each take's run tree, excluded from the checkout's git status.
A fifth smoke was run under that environment, with the twelve names stripped:

    python3 evals/gap-study-2/smoke_run_tree.py --strip draft --out evals/gap-study-2/verification/env-smoke/tmpdir

It exited 0; `claude-haiku-4-5-20251001` replied "ready."; `failures` was empty; `apiKeySource` was "none"; the sweep found 5 hits, in README.md and docs/RESULTS.md only.
The sha256 of its `environment.json` is `bcca3fd054a7e35c5de221bf4d604bf99015e4c71f5527f6288eb5318a90ddc4`.
TMPDIR, TMP and TEMP match no recorded pattern and sit on no list, so the record carries no new name and no temp path.
Its `scratch` counts were 0 files in the run tree's `.tmp`, 0 harness session folders there, and 0 harness session folders under the OS temp root.
That reading has a limit: a one-line session that runs no tool creates no harness task or scratch folder anywhere, so this smoke cannot say where the harness would place one.
The take checker admits both places a take's own files can be, the run tree (with its `.tmp`) and the harness's session folder bound to that take's run-tree slug and session id, and refuses every other path under the temp root or `/tmp`.
The first walk that runs a tool shows where the harness writes, and a write anywhere else is refused, not graded.
`scrub.py --write` removed `session_context.userEmail` from its transcript.
