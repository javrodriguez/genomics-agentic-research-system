Status: running

Clock: 2026-10-19 02:48 EDT (lane vendor-b14, cloud executor, branch from lane/vendor-admission at 00942460).

Progress:
- 2026-10-19 02:48 EDT: branch lane/vendor-b14 created at 00942460 (rev-parse verified); round 1 under glitch-26's rulings B15 (arm O usage table, red first) and B14 (arm G design note, no code).
- 02:53 EDT: B15 source read: openai/codex tag rust-v0.162.1 peels to 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d (git ls-remote); codex-rs/exec/src/exec_events.rs (sha256 dafa872d...) Usage at lines 59-73 has five i64 fields, cache_write_input_tokens at 68 under serde(default) at 67, no skip_serializing_if on any; the stream is serde_json::to_string of ThreadEvent (event_processor_with_jsonl_output.rs:105-116, sha256 bc296541...), turn.completed built at :533-535 from usage_from_last_total (:118-130), which sets all five.
- 02:53 EDT: baseline on 00942460 under env -i, all OK: test_codex_adapter 55, test_codex_native 15, test_pending_codex_walk 11, test_codex_executed_refusal 5, test_vendor_pins 5, test_vendor_record_binding 12, test_vendor_envelopes 5, test_vendor_session 5, test_labelling 109, test_freeze_shapes 9, test_take_config 10, test_vendor_roads 13, test_env_allowlist 29, test_build_draft 49, test_run_take 68, test_walk_builders 94, vendor_check_fixtures --check ok.
