# Two commit bodies this round's own guard refuses, permanently

Re-derive with:

```
python3 evals/gap-study-3/lint_pooling.py --commits-since ddf12ebc130e9d18de5ffcb429f7996ebe77baeb
```

That command prints two findings and will keep printing them. Nothing here is going to fix them, and this
page exists so no reader meets them without the reason.

## What they are

| commit | which rule fires | the line |
|---|---|---|
| `1caf072` | the rule against adding two cells' counts | a sentence quoted as an EXAMPLE of what the guard stops, inside the commit message that added the rule stopping it |
| `703d8f4` | the rule against the word for the thing itself | that word, used while explaining why a pattern was narrowed |

The two rule names are given in words rather than spelled, for the reason the last section of this page
gives. `--list-patterns` prints them.

Both are commit messages in which this run **described** the guard by quoting the vocabulary the guard
forbids. Neither joins two rounds' counts into a figure. Neither is in a published artifact: they are build
chatter from before the freeze.

## Why they are not fixed

Three reasons, in order of how much they settle:

1. **The history is pushed, and history is never rewritten here.** Not by this run and not by the door it
   pushes through. A commit body is immutable once it is online, which is most of why commit bodies are
   scanned at all.
2. **The guard has no excusal path, by design, and is not getting one.** Its own file says that adding one
   would be the exact shape of the mistake it exists to prevent. That does not stop applying when the line
   it refuses is one this run wrote.
3. **The criterion scopes this scan to the commits SINCE THE FREEZE**, which is where a commit body can
   carry a finding. The CI step ran it since the kickoff instead — wider than asked — and that is what went
   red. It is scoped back to the criterion, and the two commits sit before the freeze either way.

## The lesson, which is the useful part

A guard written to refuse a vocabulary will refuse the commit message that documents it. When describing
what a rule stops, name the SHAPE rather than quoting the sentence — "a sentence that adds two cells'
counts" rather than the sentence itself. This page had to be written twice for exactly that reason: its
first draft named the two rules by their ids, and the guard refused it. The battery is the place for the literal examples, where they are
data rather than prose, and where they are already.

This cost nothing here because the commits are pre-freeze build chatter. The same carelessness after the
freeze would put a refused line into the record that carries the study's findings, where it could not be
scoped away and would have to be lived with in public.
