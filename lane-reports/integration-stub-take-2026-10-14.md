# Stub take through the production path: no supported road on the merged head, 14 Oct 2026 07:41 EDT

Writer: the integration lane, on glitch-06's milestone request ("stub-take, no model").
Head: `9a92e4ce`, which re-merges box `1bbc2e77` (`e05805c1` and `1bbc2e77` are tests and evidence only).
- After it, the Mac gives: test_run_take 46 OK, `copy_manifest.py --check` ok, `build_draft.py --check` ok.

**Outcome: no take was run.** Nothing was sent to athena, no image was started, and no value was filled.
The merged head has no supported road that drives one no-model stub take through run_take's create, preflight, the sidecar and egress, teardown, the records, the scan and the checker.
The road is designed to wait on values that are defined as measured at that very stub take.
Running it would need values injected or a guard bypassed, which the request rules out.

## What exists, and why none of it is that road

1. `box/stub_agents/take.py`: an in-memory stub take, graded by the task's v4 grader.
   Its own docstring: "No model, no container, no network, standard library only. Writes nothing."
   Its runtime (`box/stub_agents/runtime.py`) "stands in for the box (the take container, the sidecar's snapshots and watcher, the driver's ledger)".
   So it is not the production path.
2. `box/measure_live.py`, with `--mode component|stub|gap|candidate|latency`: component measurements on provisional or candidate images, written as measurement reports.
   Its docstring says it "does not fill production pins or establish full walk admission".
   No mode calls preflight, the take records, the scan or the checker.
3. The production driver refuses a stub adapter by construction.
   `drive.adapter_class_problems`: "The adapter is its harness's captured production class, never a stub or subclass."
   Anything else raises `AdapterIdentityRefused`.
4. The plan names the step but no entry point builds it.
   `tests/test_box_integration.py` `REAL_BOX_STEP`: "CP2's real-box step: one stub take on athena's box with no model (plan, CREATE tests/test_box_integration.py), which waits on J1, 'athena box setup done'".

## PENDING values the production path needs, read on the merged head (verbatim reasons)

These come from `run_take.pending()`, `preflight.pending()` and `scan_record.pending()`.
- run_take FALLBACK_ENV: "Claude Code's refusal-fallback and model-fallback variables, names and values: confirmed at the pinned version (plan, run_take task)."
- run_take VENDOR_BILLING_ROUTE_VARIABLES: "arms O and G's own billing-route variables: named from each harness's documentation at the pinned version (D8 B2 item 7)."
- run_take TOP_FORMAT: "the column form `docker top` prints under rootless Docker: measured on the box."
- run_take INSPECT_STATUS: "the inspect spellings, taken from the Docker Engine API: confirmed when the stub take reads one inspect."
  The module's own comment adds: "while it is, every comparison and every state read refuses (NotReady)".
- run_take TakeSpec.resources: "the take's memory reservation, CPU and pids values: measured at the cold-start stub take ('all recorded')."
- preflight VERSION_PATTERNS: "every `--version` output form: a walk-only value; no parse pattern is invented."
- preflight STUDY_PATHS: "the pre-registered list of study folders absent from the run tree: CP5's."
- preflight LEAK_WORDS: "the round's own leak words: CP5's (it adds the box users' names, image.lock users.*.name)."
- scan_record rules_scanner: "the real rules scanner: gitleaks' rules on athena, over the take's record folder only (never the Brain root); its adapter and pinned version are measured there".
- scan_record furniture: "per-harness positions of the fields a CLI writes itself into its stream or session file (an email, an account id), so the drive step can separate furniture from the agent's hits; measured per harness on the stub take (W4BR-w4c-10)".

Preflight's own rule (its docstring): "a check whose expected value (from `spec`, `lock`, `sidecar_expect` or a constant here) is PENDING fails".
So, with the real locks in place, preflight would still fail at least its version-pattern, study-path and leak-word checks.
I did not run it on athena, so I name no check as passed.

Arm A also execs the Claude harness with its login read from a login file (`run_take.exec_argv` reads `LOGIN_VARIABLE["claude-code"]`).
No credential was used or read.

## The take loop's readiness (Mac, read-only)

`python3 -B -W ignore evals/gap-study-4/batch.py --check` exited 1 and printed:

```
batch: not ready: pin_profiles is empty in routing.json (CP5 pre-registers them)
batch: not ready: pin_profiles_status is not ruled in routing.json (RULED or FILLED, with no PENDING)
```

## What the milestone needs (a ruling, not this lane's to build)

The milestone needs one of two things:
- A supported stub-take entry point that runs the measurement step itself, filling TOP_FORMAT, INSPECT_STATUS, TakeSpec.resources, the furniture and the rest from what it reads.
- A ruled measurement road that fills those values first, through the box lane's dated-record discipline, before a production-path stub take can run.

The production driver also needs a ruled way to carry a stub agent, since `adapter_class_problems` refuses any non-production adapter.
