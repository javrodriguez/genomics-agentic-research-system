# Owner agent-run records

No agent records are committed yet. Three intact repeats (`intact-1`, `intact-2`, `intact-3`), `degraded-1`, and a sealed held-out slice are NOT met; the noise floor is uncomputable. See [the complete run and sealing interface](../../benchmarks/HOLDOUT.md). Only genuine exported Claude Code runs belong here; scorer unit-test fixtures do not.

## Smoke records (row 14)

`smoke/` holds the per-`_system/`-landing smoke records (schema `gars-smoke/1`) and their
retained outputs, named by each landing's `Bench:` trailer and re-graded by CI on every push.
They are not cohort records: the cohort reads only `evals/runs/*.json`, and `bench.read_record`
refuses a smoke record by schema. A smoke delta is a regression signal, never a capability
score. See [smoke/README.md](smoke/README.md) and [SMOKE.md](../smoke/SMOKE.md).
