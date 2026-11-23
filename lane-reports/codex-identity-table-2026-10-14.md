# Codex slice 2: the identity-source table

Writer: Claude Code harness lane, 14 Oct 2026 04:37 EDT, under glitch-06's order (Codex slices after the batch-8 fold).
Parent: `9649aa0a`. Synthetic fixtures only; no CLI ran.

## The table

| Field | Accepted source | Where it comes from |
|---|---|---|
| model | `stream-reroute` | exec's reroute item: `item.completed` of an `error` item whose message is exactly `model rerouted: <from> -> <to> (<reason>)` (`exec/src/exec_events.rs:132, 310-312`; `exec/src/event_processor_with_jsonl_output.rs:494-507`); the identity is `<to>` |
| version | `version-exec` | `codex --version` in the take container, observed before the exec |
| permission_mode | `submitted-argv` | the turn's launch journal (`<stream>.launch.json`), its whole argv checked by `vendor_provenance.launch_facts` against the registered invocation |

`routing.ACCEPTED_IDENTITY_SOURCES["codex"]` holds exactly this; `stream-reroute` joins `IDENTITY_SOURCES` (agent_adapter and routing, kept equal) and `OBSERVED_IDENTITY_SOURCES`.

## What changed in the adapter

- `init` is always None.
  The rollout's `turn_context.model` is the requested model, so it is never proof; the rollout context is kept in the turn record as `requested_context`.
- `read_stream` reads one exact shape of error item, the reroute, as `served_model`.
  Two reroutes naming different models refuse the turn.
  Any other error item stays off the tables and refuses the turn, as before.
- `turn_identity`: the model is the reroute's `to` model, else unobserved; the version is version-exec; the mode comes from `submitted_mode`.
- `submitted_mode`: no journal, a link, unreadable bytes or no argv list give unobserved.
  Otherwise `launch_facts` must hold (exact argv, container, folder, stream, sent line, `first-turn` on turn 1 and the thread after), giving the pinned mode; anything else gives `launch-differs-from-registered-invocation`.
  Unlike Gemini's reading, no other approval flag is enumerated: exec's shared option list (`ExecSharedCliOptions`) is not in the retained source, so exact argv equality is the only admission.

## What can never be observed (stated exactly)

- **The served model when no reroute happened.**
  The exec stream carries no model (D8:168), the rollout's `turn_context.model` is the requested model, and the `model_reroute` event is never persisted to the rollout (`rollout/src/policy.rs`, the never-persisted arm).
  So on an ordinary turn the served model is unobservable, and `identity.model` is `unobserved`.
- **The effective approval and sandbox policy the CLI applied.**
  The rollout's `turn_context.approval_policy` and `sandbox_policy` spellings are placeholders the audit did not verify, so they are carried raw and never accepted.
  A configuration file inside the take could change them without changing the argv; only the submitted argv is observed.
- **The version the running process reports about itself mid-turn.**
  Only the separate `codex --version` exec is observed; the rollout's `session_meta.cli_version` is the writer's self-report and is not accepted as the version here.

## Consequence, named for a ruling (not decided here)

Routing's init-mismatch row (`differs_from_pin`) reads any unobserved field as a mismatch, exactly as a missing init was.
So after the first turn, every Codex turn with no reroute (the ordinary case) reads as an init mismatch.
The pin refusal before the first turn reads only an observed difference, so a reroute to another model, or another version, refuses there.
Before this slice, Codex's `init` carried the rollout's requested model, which matched the pin and passed silently; that was the requested model read as proof.
A ruling is needed: either accept an unobserved served model for Codex in that row (and say so in the study's limits), or keep arm O stopped there.
No Codex walk or take can run today anyway (the subscription transition refuses the exec, and `rollout_for` has no road yet).

## Verification (behind a light gate)

- Red: the new and changed checks against HEAD's modules, in memory.
  `test_codex_identity` gave 3 errors; A1, A5, A8 and B9 of `test_codex_adapter` gave 4 failures.
- Green on the Mac:

| Suite | Result |
|---|---|
| `test_codex_adapter` | 47/47, witnesses 15/15 red (model-defaulted re-anchored; reroute-unread and requested-model-as-served added) |
| `test_codex_adapter --generated-mutants` | 1044 mutants, 0 survivors, 0 stale (four reroute-shape survivors were bound by malformed-record cases) |
| `test_codex_identity` (new) | 3/3 |
| `test_routing` | 276 |
| `test_agent_adapter` | 35 |
| `test_batch` | 118 |
| `test_identity_evidence` | 9 |
| `test_identity_mode_evidence` | 8 |
| `test_codex_executed_refusal` | 5 |
| `test_vendor_take_records` | 4 |
| `test_vendor_checker_road` | 5 |
| `test_drive_loop` | 27 |
| `test_walk_wiring` | 20 |
| `test_gemini_adapter` | 143 |
| `test_pending_walk` | 18 |
