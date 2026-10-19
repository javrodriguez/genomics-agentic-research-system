Status: running

Goal: the measured run's take loop (evals/gap-study-4/batch.py) moves from fixed blocks of three drives to a rolling window of at most three drives, with registration and commits still serial and in row order, so that slow Gemini-arm drives no longer hold two finished slots idle; round 1 is design and red tests only.

Plan:
- Round 1 (rulings B19-1 to B19-4): a design note listing every block-dependent behaviour of batch.py, with its source line, the proposed rolling behaviour, what it can move, and the re-rulings it needs; red tests against stub drives; no change to batch.py; the checks; then stop for glitch-26's rulings.

RESUME HERE: round 1 under way (design note, red tests, checks)

Clock: 2026-10-19 13:39 EDT (lane vendor-b19, cloud executor, branch from lane/vendor-admission at 7dc0cf9e).

Progress:
- 2026-10-19 13:39 EDT: branch lane/vendor-b19 created at 7dc0cf9e (rev-parse verified); round 1 under glitch-26's rulings B19-1 (the goal), B19-2 (the design note), B19-3 (red tests) and B19-4 (batch.py unchanged).
