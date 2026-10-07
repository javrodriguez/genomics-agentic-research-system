# The round 3 stops reading: pre-registration, amendment 2

Dated 6 October 2026 (written about 19:56 UTC) by the Gap Study round 4 lane, after the first run of `haiku_stops.py` (`results/haiku-stops.json`, `STOPS.md`) and after one fresh review of it.
`PREREG-STOPS.md` and `stops_rules.py` are unchanged and stay the reading of record for every class; this file adds readings beside them, frozen by its own commit with `stops_rules_2.py`.
**This amendment was written knowing the first run's output and the review's findings.** Nothing in it was designed blind, so nothing it adds is a pre-registered result; it corrects how the first reading is reported and closes gaps the review found.

## Why

A fresh review (claude-opus-5-5, 6 October 2026) re-derived every class and found one major and several minor problems:
1. **The relative-path flag is read over the whole window**, so it marks 7 of the 15 stops. In 4 of those 7, all `ran-ahead` at the assay menu, the agent had already run past the menu before the relative path failed, so the confound cannot have caused those stops. `PREREG-STOPS.md` says a flagged stop "is reported as an operator-side confound first and its class second", which, applied to the window-wide flag, would misattribute those 4. The confound is at the stop in 3 takes: the 3 `stalled` ones.
2. **The step parser over-matches and under-matches.** A file read that names a helper counts as a step, `--help` counts as a run, and a global option before the subcommand hides one. No class changes on these 15 stops, but one table row lists five calls that ran nothing.
3. **The disclosure of what was read before the freeze is incomplete.** It omits the round 4 plan. That plan was read before the freeze, and it names "the operator-side confound behind 3 of Haiku's stops (the contract runs from `gars/`)" and the session's 10 / 2 / 3 split. A rule written knowing that split reproduced it exactly. Commit order cannot tell a faithful rule from one shaped toward a known target, and a reader needs to know both.
4. **Smaller ones:** the freeze time in the first file (19:14 UTC) is 2 minutes before its commit (19:16:19 UTC); the quotes strip trailing whitespace from each line, so they are verbatim up to trailing whitespace; the `reworded-marker` rule takes the last non-empty text block of the window (the first file says "the agent's last message"), and the two `reworded-marker` takes were confirmed by reading (the review); the table did not print M and N per task and half, or the stopped-take count of `claude-sonnet-5` it says is outside the reading.

## What this adds (all in `stops_rules_2.py`, sha256 recorded below)

- **The confound at the stop** (`confound_at_the_stop`): the call that met the unresolved relative source is the wait point's own step, and no step past the wait point and no later step's marker came before it in the window. It is the confound's headline count. The first rules' window-wide flag is kept as a second count, labelled as such. Only a stop with the confound at the stop is reported as an operator-side confound first.
- **Each listed step annotated** (`annotated_steps`): refused, errored, a help call, a usage error. This is for the table only, and it changes no class.
- **A sensitivity class** (`strict_class`), printed beside the class of record and never replacing it. A helper step is a python invocation of the script, global options allowed before the subcommand, never a help call; a call whose result is a usage error is left out. The reader prints whether any class moves.
- **The completed-stage-00 count:** the `ran-ahead` takes whose window ran `link` and `finalize` with neither refusal, error, help call nor usage error (`ran_without_error`). The decision record's "went on to link and finalize" sentence cites it.

## Rules for any reuse

Before `stops_rules.py` is reused on other takes (the round 4 replay, or `claude-sonnet-5`'s stops), two things must change. The class of record must use the stricter parser, and `reworded-marker` must test that the wait point's own template body was shown. Both are left out here because neither moves a class of these 15 stops; the sensitivity class proves the first, and the review's reading the second.

## What the reader does now

`haiku_stops.py --check` re-derives both outputs:
- the first run's, `results/haiku-stops.json` and `STOPS.md`, byte for byte as committed, by the first rules and the first render;
- this amendment's, `results/haiku-stops-2.json` and `STOPS-2.md`, which add the readings above.

It reads the sha256 of each rules file from the text of its own pre-registration file and refuses unless the file hashes to it. Each pre-registration file must also hash to its `.sha256` record. The rules files are `stops_rules.py` (`c1f25a7a83d1b9f815455e6368b9b9383ac59b1438eb40bd0073751013efb5a2`) and `stops_rules_2.py` (`2f5f092214c0e5d4a6d12a3a1ec809b73111ec51581cba4c7fdabbda7b5cee23`).

## What it never does

Everything `PREREG-STOPS.md` says it never does still holds: no re-grade, no re-label, no pooling, no model comparison, no claim about what a run with an absolute path or another permission setting would have done.
