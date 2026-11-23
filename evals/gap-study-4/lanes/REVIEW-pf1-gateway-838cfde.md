VERDICT: PASS
lane-tag: instrument
purpose: round-1

# Review: lane pf1-gateway, 7a866455..838cfdef (round 1)

Reviewer: a fresh Opus 5.5 reviewer, assigned by glitch-45 (Lane-orchestrator), Mon 26 Oct 2026 20:28 EDT.
Range: 9161cfd5 (the fix) and 838cfdef (the reworded residual, draft regenerated), on lane/pf1-gateway.
Placed beside the other REVIEW-pf1-* files in `evals/gap-study-4/lanes/` (no `lane-reports/` folder exists in this tree).
I did not read the builder's transcript, changed no code and did not touch athena.

## What I checked, with evidence

- Red first, reproduced. I extracted 7a866455's `evals/gap-study-4` with `git archive` into my scratch space, overlaid the head's `tests/test_pf1_egress_probe.py`, and ran it.
  22 tests, 5 failures, all in E4HostRecord.
  `test_w_o48_recorded_input_passes_with_the_host_record` fails at H on its "the w-o48 refusal reproduced" assertion, with the detail
  `the take inspect names no gateway for network(s) ['nc381ca9735e8e95c6361eedd']: the addresses tried cannot be bound to the take's own gateway (fail closed)`,
  which is word for word the `egress-gateway-refused` detail in w-o48's `preflight.json` (blob 13674507 on walk/w-kptgozIX, commit e81b6f2f).
- Recorded inputs are faithful. `W_O48_NETWORKS` equals `NetworkSettings.Networks` in the take-inspect step of w-o48's `launch.json` (blob f76b847c), key for key; `W_O48_NETWORK_ID` equals its `network_id` and its `HostConfig.NetworkMode`.
  The route table and IPAM gateway are labelled as athena live readings, not w-o48 records, which is honest (preflight.json keeps no probe output).
- At the head (838cfdef), after `mac_slot.py light-ok --tests --work gap-study-r4` said `light ok: load1 3.94 < 16.00`, with /usr/local/bin/python3.12 and TMPDIR in my scratch space:
  test_pf1_egress_probe 22 OK; test_preflight 60 OK (break witnesses all red by their own guard); test_live_box 38 OK; test_run_take 68 OK (run under `env -u CLAUDE_CODE_MESSAGING_TOKEN`); test_build_draft 74 OK; test_prereg_status 10 OK; test_prereg_order 10 OK.

## Judgement on the five questions

1. Binding. The host record is the output of `docker network inspect <spec.network>`, run host-side; `spec.network` is pinned to a full 64-hex id by run_take (line 924) and replaced by launch with the network it created (`_on_network`).
   `_host_network_gateways` needs exactly one object whose `Id` equals that id, a non-empty `Name`, and well-shaped IPAM; anything else fails the check.
   The record binds to a take-inspect network only by the same name and, where the take inspect gives a NetworkID, the same id.
   The take holds no input to either record: both are host-side inspects, and its route table (the only take-produced input) is still checked against them, never trusted alone.
   A second network on the take with no Gateway still refuses; a missing or empty IPAM, or one with only empty gateways, still refuses when the take inspect names none.
2. No widened pass outside the intended case. The only input that refused at H and passes now is a take-inspect network with an empty Gateway whose name (and id, if given) matches the host record of `spec.network` and whose IPAM names at least one gateway, every one of which was tried and refused on all GATEWAY_PORTS.
   Every other change is stricter: when the take inspect does name a Gateway, the bound IPAM gateways are wanted too, and an unreadable host record now fails even a non-internal network.
3. Host-side and the guard. The probe is `(RUNTIME_CLIENT, "network", "inspect", spec.network)`, run by `run()` like every other inspect, not through `agent_exec_argv`.
   The TestPrograms allowance is `p.id == "take-network-inspect" and list(p.argv) == ["docker", "network", "inspect", w.spec.network]`: that one command, exactly.
4. Red-first: yes, as above, failing at H for the recorded reason, on the recorded take inspect.
5. The reworded residual (build_draft.py `PF1_READS_EGRESS_RESIDUAL`, identical text in prereg-draft.json; test_build_draft green) says what the code does, with the narrow exception in finding 2.

## Findings

1. MINOR (class C, provenance). The w-o48 take inspect the test copies is the launch step's inspect, taken after `take-create` and before `take-start` (EndpointID, IPAddress and NetworkID all ""). Preflight's own take inspect, after start, is not recorded, so the NetworkID branch the live box will take (a populated NetworkID that must equal `spec.network`) is exercised only on synthetic input. Any mismatch there fails closed, not open, so this is not a widened pass; the running athena battery or the next real walk shows it. Suggest the test comment say "pre-start take inspect" so no reader takes it for preflight's.
2. MINOR (class C, wording and a small strictness gap). The residual says every gateway the host record names "must be among the addresses tried". In code that holds only when the record binds to a network in the take inspect; a host record of `spec.network` whose name matches none of the take's networks is ignored when those networks name their own Gateway. That is a host-side inconsistency (the take not on its own spec network), not something the take can cause, and take-inspect-matches-spec pins HostConfig.NetworkMode separately, so it is not a containment hole. Either refuse an unbound host record, or narrow the sentence to "for the take's network".
3. MINOR (class C, record). preflight.json still keeps no probe output, so a pass on this check cannot later be re-graded from the record: which gateway the host record named is not kept, only the candidates in the detail. This is the pre-existing record shape, not introduced here, and noted for the record-integrity backlog.
4. INFO. An IPv6 gateway in the IPAM record would be wanted but never tried (the probe is IPv4 only), so a dual-stack take network refuses every take, fail closed. Launch creates `--internal` without `--ipv6`, so it does not arise today; the residual's IPv6 sentence covers the probe side.

No BLOCKER or MAJOR.
