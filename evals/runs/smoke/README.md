# Smoke records (row 14)

One record per `_system/` landing on main's first-parent line: `<run_id>.json`, schema
`gars-smoke/1`, named by the `Bench:` trailer of the landing it is bound to. Retained outputs
live at `outputs/<run_id>/<run_label>/<task_id>/response.json` and nothing else is under
`outputs/`. Records and outputs are committed in the landing's one child commit and never
edited afterwards; CI re-grades every one of them on every push.

No smoke record is committed yet. A smoke delta is a regression signal between landings, not a
capability score; see [SMOKE.md](../../smoke/SMOKE.md). These records are not bench cohort
records: `bench.read_record` refuses them by schema, and the cohort test reads only
`evals/runs/*.json`, not this folder.
