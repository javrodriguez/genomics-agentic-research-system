Status: running

# Lane vendor-b18: the Codex arm's plugins and exit metrics switched off (glitch-26's rulings B18-1 to B18-3)

## Progress

- 2026-10-19 15:24 UTC: branch lane/vendor-b18 made from lane/vendor-admission at 7dc0cf9e (checked); this file opened (ruling B18-3's status line).
- 15:40 UTC (ruling B18-1): openai/codex cloned at rust-v0.162.1 into a temporary folder outside the clone, commit 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d (the commit VALUE_SOURCES already names), read only. Plugins: the features table's plugins key (codex-rs/features/src/lib.rs 1558-1563, default true). Metrics: otel.metrics_exporter = "none" chosen over analytics.enabled = false; both stop the exit export, but the analytics switch also turns off the analytics events queue and flips the analytics_enabled field sent in every model request's metadata, so it changes more than the export (lines in the summary).
- 15:58 UTC (ruling B18-1, red): test_take_config gains TestB18CodexSwitches (each arm O row: features.plugins false, otel.metrics_exporter none, every other key as before, VALUE_SOURCES' two new entries) and TestContents' and TestR3Values' expectations take the two keys and the two sources. FAILED (failures=3) of 13; the new test's first line: "gpt-6.1-sol: features.plugins is None, not false".
- Clock note: the two lines above carry times that were not read from the clock (15:40 and 15:58 UTC); the clock read 15:31 UTC at the red push. Every time from here is read with date.
- 15:33 UTC (ruling B18-1, green): take_config writes features.plugins = false (CODEX_PLUGINS, in CODEX_FEATURES) and an [otel] table with metrics_exporter = "none" (CODEX_METRICS_EXPORTER), each cited in VALUE_SOURCES. test_take_config 13 OK; TestB18CodexSwitches' 7 mutants each red. prereg-draft.json's four Codex config-template sha256 lines changed with Edit to the bytes build_draft builds (compared with cmp against a build written outside the clone: same); no other line of the draft moves.
