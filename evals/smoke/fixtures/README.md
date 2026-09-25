# SYNTHETIC development fixtures — producer-written, not evidence

Everything under this folder is **synthetic** and was written by the row 14 producer with
`generate.py`; no model session produced any of it. The model id is `fixture-model`, the
commit hashes are derived from fixed labels (they name no commit of this repository), and the
transcript hashes are hashes of fixed strings. It is the **development set** of
`tests/test_evaluator_planted_lie.py` and is never the §18 row 14 exit, which needs the sealed
set described in `../LIE-INTERFACE.md`.

| Path | Holds |
|---|---|
| `tree/` | a pinned copy of the three smoke tasks, their inputs and `benchmarks/RESPONSE.md`, so the set does not move when `benchmarks/` does |
| `clean/C01/` | a genuine-shaped chain: floor record → ordinary record (no change) → ordinary record (decrease); the last is the record under test |
| `clean/C02/` | the cold-start twin: the floor record alone, first after activation (`previous` null) |
| `lies/L01`–`L11/` | one plant per finding code other than `SCHEMA` and `UNREADABLE`, each built from `clean/C01` with one lie; `expected.json` names it (`seal_type` `producer_development`) |

Regenerate with `python3 evals/smoke/fixtures/generate.py` (and `--copy-tree` to refresh
`tree/` first); `tests/test_evaluator_planted_lie.py` checks that the generator reproduces
these bytes. This folder is protected (`repo:evals/*/fixtures/*`).
