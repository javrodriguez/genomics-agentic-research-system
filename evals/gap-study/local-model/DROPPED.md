# The local tier was dropped, and this is the record of it

**Status: DROPPED, 2026-09-08, by the repository owner, at gate 2.**

The study was designed with five models on its axis: three Claude tiers and two open-weights models
served locally on this machine. The local half is not being run.

## The reason, stated exactly

> not run — the local tier was dropped at gate 2 on 2026-09-08, by the member's decision when
> the window was put to them. Not the day-10 default, which is a different reason.

The protocol has a second, similar-looking exit: if nobody names a window by working day 10, the
local cells publish `not run — no window named by day 10`. **That is not what happened here**, and
the two reasons are not interchangeable. One says the schedule ran out. This one says it was
decided. The record carries the one that is true.

## What the two models publish

`llama3.1:8b` and `qwen2:7b` keep their columns in every table and carry the reason above.

They are not deleted from the model list, deliberately. A model that never produces a graded take
publishes as `not run`, never as absent: removing them would make the table read as though the axis
had been three wide from the start, which is a quieter and less honest claim than the one the
record supports. The two local control takes are dropped with the tier, under the same reason.

The predictions made for those ten cells stand exactly as they were pre-registered, and are never
scored. A prediction resolved against no data is not a prediction that was right.

## What this costs the study, said plainly

The central question is where the deterministic layer does not cover a failure mode, which model
catches it, and how often. The sharpest form of that question was whether a model with **no
per-token fee** holds the cells an expensive one holds. That form is no longer measured here.

What remains is still the question, across three Claude tiers: whether the cheapest of them covers
the gaps the most expensive one covers. That is a real result and it is worth having. It is a
narrower one, and this file exists so nobody has to reconstruct that from a missing column.

## What is kept, and why

- `unsupported-line.md`, `login-line.md`, `floor-line.md` — the three sentences a reader needs
  before trusting any local-tier result, each with its source URL and retrieval date.
- `fit/2026-09-08-llama3.1-64k.log` — the server log from the 64k probe on this machine: 25 of 33
  layers on the GPU, prompt processing at 3.85 tokens a second, and the server stopping mid-prompt.

These stay committed because they are the record of what was considered and on what evidence. A
reader deciding whether to try this configuration themselves should still meet them, and the fit
probe is a measured fact about an 8B model on an M1 Pro whether or not this study went on to use it.

## If it is ever picked up again

The design is intact in the pre-registration: window order 64k, 48k, 32k with a full-precision
cache and then `q8_0`, nothing below 32k, the first window whose load line puts the whole model on
the GPU, a fit walk inside 60 minutes, and a per-turn budget of three times the slowest fit-walk
turn. Reinstating it means naming a window and setting `model_status` back to running. It does not
mean redesigning anything.
