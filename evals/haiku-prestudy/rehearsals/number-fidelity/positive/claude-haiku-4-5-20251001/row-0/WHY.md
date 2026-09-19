# Why this attempt is a rehearsal

Row 0 of the take ledger: `number-fidelity` / `positive` / `claude-haiku-4-5-20251001` / take 1.

It is kept and never graded. Its reasons, from the pre-registered list:

- `leak-in-loaded-context` — the session's loaded context contains a leak word outside a pinned excusal

The checker's own output is reproduced by:

```
python3 evals/gap-study-2/check_take.py evals/haiku-prestudy/rehearsals/number-fidelity/positive/claude-haiku-4-5-20251001/row-0/transcript.jsonl --task number-fidelity --half positive --row 0
```
