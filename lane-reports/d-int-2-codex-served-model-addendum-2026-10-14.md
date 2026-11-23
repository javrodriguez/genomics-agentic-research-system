# Departure D-INT-2: its home, its history, and two corrections (addendum)

Writer: Claude Code harness lane, 14 Oct 2026 06:08 EDT, under glitch-06's order after `gap4-review-harness-dint2-cov.md` (19ec4c41 and a36a5743: PASS, three MINORs).
The note `d-int-2-codex-served-model-2026-10-14.md` stays as written; this addendum corrects it.

## Its home in the draft

The note said the limit sentence had no place in `prereg-draft.json` and named that as the draft owner's follow-up.
That was wrong: the draft already has the slot, `served_model_rule` (declared at `build_draft.py:914`, set at `:1216`), whose `codex` entry was PENDING and must be filled before the freeze.
Under glitch-06's narrow ownership extension (this field only), `build_draft.py` now fills `served_model_rule.codex` from `routing.SERVED_MODEL_LIMIT`, the one sentence.
`test_build_draft` binds it in R15.values: Codex holds routing's sentence, and every other harness stays PENDING.
The draft is regenerated, and `build_draft.py --check` reads it at the commit.

## Its history

`plans/gap-study-round-4.md:67`: "The OpenAI route is not open for round 4: D8 B2 chose API-key projects with hard caps, because Codex on a ChatGPT login doesn't record the model it served."
D8 B2 chose the API-key road precisely to keep the served model checkable: the per-turn log line and the usage page by model, which exists only on the API road.
The 13 Oct subscription amendment moved arm O onto a ChatGPT subscription, where neither exists.
That amendment is what makes D-INT-2 necessary.

## Corrections

- "two reroutes still refuse" should read "two different reroutes still refuse".
  Two reroute items naming the same model read as one served model (`codex_adapter.read_stream`).
- `fixture_walk.walk_coverage` now applies walk_plan's one rule: a walk counts only when `pending_walk.coverage_status` is None.
  A test binds a walk holding a transcript whose verified regrade refused.
- `test_codex_identity` now also binds a rerouted turn's record: `{"value": <to>, "source": "stream-reroute"}`.
