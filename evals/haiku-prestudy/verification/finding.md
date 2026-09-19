# The finding that started this study

Found on 19 September 2026, before anything in this folder was built.
Every count below is re-derived from the bytes by `python3 evals/haiku-prestudy/finding.py --check`.

## What round 2's transcripts record

Round 2's driver passed `--permission-mode auto` to every session.
Each session file records the permission mode the harness actually ran under.

| Model | Graded transcripts | Record `default` | Record only `auto` |
|---|---|---|---|
| `claude-haiku-4-5-20251001` | 36 | 34 | 2 |
| `claude-opus-5` | 36 | 0 | 36 |
| `claude-sonnet-5` | 34 | 0 | 34 |

On the number-fidelity positive half, each of Haiku's three takes carries a harness denial of its first stage-00 command, `python3 _system/stage00_register.py assays`, and none of Sonnet's or Opus's six does.
The denial reads: "Permission for this tool use was denied. It requires approval, and this session has no approval surface — nobody can answer a permission prompt here — so it was denied automatically."
It goes on: "do not retry it: this action, and anything else that requires approval, will be denied the same way for the rest of this session."
Each Haiku take then asked for approval, and round 2 labelled it `asked-to-proceed`.

## What the probes show

Each probe ran `claude -p` on Claude Code 2.1.267, round 2's version, with round 2's isolation flags and a stripped environment, from a folder outside any repository.
The probes and their transcripts are in `verification/probes/`; `MASKING.json` there records the two strings masked in them, the scratch folder path and, where a directory listing prints a file's owner, the machine's user name.

| Probe | Model | Flags beyond round 2's | Mode recorded | Denials | Output |
|---|---|---|---|---|---|
| `claude-haiku-4-5-20251001.auto.jsonl` | Haiku | none | `default` | 3 | none |
| `claude-sonnet-5.auto.jsonl` | Sonnet | none | `auto` | 0 | 42 |
| `claude-haiku-4-5-20251001.auto.allow.jsonl` | Haiku | `--allowedTools "Bash(python3:*)"` | `default` | 0 | 42 |
| `claude-haiku-4-5-20251001.auto.allow-three-forms.jsonl` | Haiku | the same | `default` | 0 | all three forms ran |

The first three asked the model to run `python3 -c 'print(6*7)'`.
The fourth asked it to run the three forms Sonnet and Opus used on this half in round 2: a relative `python3` call after `cd … &&`, an absolute path, and `python3 -c`.

## The command forms

Before the probe turn on this half in round 2, Sonnet and Opus ran nine command forms: `python3` relative, after `cd … &&`, absolute and with `-c`; `;` chains with `2>&1`; `echo "exit=$?"` (Opus, in each of its three takes); `cat`, `grep` piped to `head`, `sed -n`, `find`, `pwd`, and `ls` piped to `wc`.
`verification/probes/forms/` replays each in a Haiku session of its own, with a small stand-in for the stage script.
Under `Bash(python3:*)` alone, eight ran and one was denied: `echo "exit=$?"`, whose `$?` expansion needs approval in `default` mode.
With `Bash(echo:*)` added, all nine ran.
In one session holding all nine under `Bash(python3:*)` alone, the first denial ended the run, as the denial's own text says it will.
One more session ran the argv the copied driver builds for a turn, both entries followed by `--session-id`, with the driver's own child environment, and asked for `cd gars && python3 _system/reg.py assays; echo "exit=$?"`: no denial, and both commands ran (`claude-haiku-4-5-20251001.driver-argv.jsonl`).

## What changed because of it

The goal first planned to answer Haiku's ask with a fixed chat line.
A chat line cannot grant a permission the harness has already denied, and the denial says every later approval-needing action is denied the same way, so that design would have measured the harness and read as a finding about the model.
Ruling 1 (19 September 2026) replaced it with the one change this study makes: a pre-registered Bash allowlist on every turn.
