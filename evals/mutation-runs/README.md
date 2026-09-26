# Row 3 sealed mutation-run records

This folder holds one JSON record per sealed mutation run.
A file is named `<date>-<run_sha7>-first-run.json`, or `<date>-<run_sha7>-run-N.json` for a later, separately sealed run.
Each file is an immutable first-run record: it is never edited and never re-scored.
A later seal or a re-run is a new file, never a replacement, as [MUTANTS-INTERFACE.md](../MUTANTS-INTERFACE.md) lines 122–123 require: "retain the first score at the original run SHA. A later set is a separate sealed run, not a replacement of its first result."
The records are development evidence under an `independent_context` seal; public credibility claims stay unmeasured until an `external_human_seal`.
Each record's rows are the runner's stdout with machine paths replaced by placeholders (`<scratch>`, `<home>`), and `run_stdout_sha256` binds the raw stdout.
This folder is deliberately not `evals/runs/`: that folder holds `bench.py`'s agent-run records, and `tests/test_benchmark_discriminates.py` globs `evals/runs/*.json`.
The human-readable table is [mutants.md](../mutants.md).

| File | Score | Kind | Row 3 exit |
|---|---|---|---|
| [2026-09-23-2a65dbf-first-run.json](2026-09-23-2a65dbf-first-run.json) | 5/10 killed | first run, development evidence | NOT met |
| [2026-09-26-8744978-run-2.json](2026-09-26-8744978-run-2.json) | 10/10 killed | second seal's first run, development evidence (decisions 0088, 0089) | met as development evidence (not a public pass) |
