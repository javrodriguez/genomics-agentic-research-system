VERDICT: PASS

Review of lane vendor-b18, range 7dc0cf9e..446dd9f4 (glitch-26's rulings B18-1 to B18-4), by a fresh cloud reviewer
who did not write the change. 2026-10-19. No MAJOR, no MINOR; two NITs, neither blocking.

## Findings

1. NIT, lane-reports/vendor-b18-LANE.md line 45 (B18-2 "Kept"), and evals/gap-study-4/box/take_config.py line 211
   (VALUE_SOURCES "CODEX_PLUGINS" uses). The record says no other Feature::Plugins reader in core reaches what the
   model sees beyond core/src/config/mod.rs 1738 and core/src/agent/role.rs 97. At 092d3acd there are more:
   codex-rs/core/src/mcp.rs 213, 257, 283, 342 and 380 (plugin-contributed MCP servers, and the plugin connector
   snapshot that feeds the apps connector list at core/src/session/turn.rs 1051-1067), and
   codex-rs/ext/mcp/src/plugin.rs 127 and 231 (cloud-plugin contributions and a selected plugin's MCP servers). The
   record names mcp.rs 257 and 342 only for the usage section. In practice nothing more changes for arm O: each of
   these acts only on a loaded or selected plugin. In a fresh config folder no plugin is loaded while the bundle
   downloads and the curated sync are denied. And codex exec never sets the cloud plugin provider:
   ext/mcp/src/plugin_providers.rs 18 sets cloud: None, and with_cloud_provider has no caller in the tree. So with
   plugins on, these readers had nothing to contribute, and turning plugins off removes nothing from them. The gap
   is in the record's wording, not in the behaviour. A missing citation; I did not edit the lane file.
2. NIT, evals/gap-study-4/tests/test_take_config.py lines 480-548 (B18_SOURCES). The test binds VALUE_SOURCES to a
   literal copy of itself. A wrong line number written the same way in both places would pass, because nothing in
   the tree reads the pinned source. This is the existing R3/B14 pattern (TestR3Values), and the gap is inherent
   without a vendored copy of the source. This review covered it by reading every cited line at the pinned commit
   (below).

## Threat model

(1) Scope. `git diff --stat 7dc0cf9e..446dd9f4` lists 5 files: box/take_config.py, checks.d/vendor-admission.txt,
prereg-draft.json, tests/test_take_config.py and the lane file. The writer change adds CODEX_PLUGINS to
CODEX_FEATURES, adds a CODEX_OTEL table rendered as `[otel] metrics_exporter = "none"`, and adds two VALUE_SOURCES
entries. Every other Codex key is unchanged (model, model_reasoning_effort, web_search, check_for_update_on_startup,
forced_login_method, cli_auth_credentials_store, features.hooks). The Gemini and Claude Code writers, the instruction
file, drive.py, scan_record.py, transcript_view.py and the Codex gate are untouched. TestB18CodexSwitches parses the
written config.toml for each arm O row in prereg-draft.json (gpt-6.1-sol, gpt-6-luna) and compares the rest of the
document exactly. TestContents compares the whole Codex document plus Gemini's and Claude Code's settings.

(2) Sources. I cloned openai/codex at tag rust-v0.162.1 into /tmp/b18rev.lUt8 (outside the clone; read only). HEAD
is 092d3acd6bec3e3a14bdc7e7a2810ab628ab759d. I printed and read every cited line; each says what VALUE_SOURCES says.

Plugins:
- features/src/lib.rs 1560 (key "plugins") and 1562 (default true); 577 (plugin_recommendations_enabled needs
  Plugins).
- app-server/src/message_processor.rs 558 (maybe_start_plugin_startup_tasks_for_config).
- core-plugins/src/manager.rs 2820 (if config.plugins_enabled), 754 (curated sync gate), 1599 (bundle sync returns
  when plugins are off), 814 (plugins_for_config returns the default) and 1908 (Legacy mode).
- core-plugins/src/startup_sync.rs 30 (https://github.com/openai/plugins.git).
- core-plugins/src/remote_bundle.rs 192 (bundle_download_url).
- core/src/session/mod.rs 4248 and 4414 (candidates gated; section pushed).
- core/src/context/recommended_plugins_instructions.rs 43 and 53 (markers; body).
- core/src/context/available_plugins_instructions.rs 32 ("## Plugins").
- core/src/session/world_state.rs 304 (plugins_available).
- core/src/tools/spec_plan.rs 712 and 1328 (tool_suggest_enabled needs Plugins; request_plugin_install is
  registered only then).
- config/mod.rs 1738 confirms that PluginsConfigInput.plugins_enabled is Feature::Plugins.

Metrics:
- core/src/config/otel.rs 21 (the default is Statsig; log and trace default to None at 17 and 20).
- config/src/config_toml.rs 547 (the otel table).
- config/src/types.rs 596 (kebab-case; None at 598) and 643.
- otel/src/config.rs 9 (https://ab.chatgpt.com/otlp/v1/metrics) and 24.
- otel/src/provider.rs 218 (no metrics for None), 104 (shutdown flushes metrics) and 359 (Drop runs shutdown).
- core/src/otel_init.rs 74.
- exec/src/lib.rs 668 (DEFAULT_ANALYTICS_ENABLED, true at 174).
- app-server/src/turn_cost_worker.rs 106 (only OtlpHttp or OtlpGrpc start it).

The not_used lines are correct too: otel_init.rs 71, analytics_utils.rs 14, analytics/src/client.rs 321 and
session/session.rs 746.

Each key stops what the lane says it stops. Beyond the two plugin sections and the tool-suggest tools accepted under
B18-4, plugins off changes nothing else the model sees for arm O (with the wording gap in finding 1). AGENTS.md
loading has no plugin gate.

(3) Choice of key. otel.metrics_exporter = "none" is right. analytics.enabled = false would also drop the exporter
(otel_init.rs 70-77), but it would turn off the analytics events queue and set analytics_enabled false in every
model request's metadata (session.rs 746). The model-facing request would change, which the ruling avoids. The
metrics key's only other reader, the turn cost worker, is off under both Statsig and none.

(4) Tests and the draft.
- TestB18CodexSwitches' 7 mutants are each red alone with the expected message. They bind both keys, their values,
  every other key and both VALUE_SOURCES entries.
- TestR3Values now requires R3, B14 and B18 sources together; it is stricter, not weaker. TestContents' expectation
  gains the two keys.
- No test or check was removed or loosened.
- prereg-draft.json changes exactly the four Codex config-template sha256 lines (a file hash and a template hash per
  row). build_draft --check reports that the committed draft is what build_draft.py builds.
- The two new checks.d lines register the test and the P2 source-list check.

## Checks run

Each check ran in the foreground under `env -i PATH HOME LANG TMPDIR`, with TMPDIR=/tmp/b18tmp.KHXZ (outside the
clone), on 446dd9f4:

- `python3 -B -W ignore evals/gap-study-4/tests/test_take_config.py`: Ran 13, OK. TestB18CodexSwitches alone: 1 OK,
  its 7 mutants red ("plugins key dropped", "plugins left on", "metrics switch dropped", "metrics left on Statsig",
  "another key changed", "plugins source dropped", "metrics source's line moved").
- `python3 -B evals/gap-study-4/tests/check_vendor_sources.py P2 box/take_config.py prereg-draft.json
  tests/test_take_config.py`: exit 0, no refusal.
- `python3 -B -W ignore evals/gap-study-4/build_draft.py --check`: "ok: the committed draft is what build_draft.py
  builds", exit 0.
- Witness run, every command line of evals/gap-study-4/checks.d/vendor-admission.txt: 61 of 61 exit 0. The working
  tree stayed clean afterwards.
- My own mutant, on a scratch clone at /tmp/b18mut2.hZrv/r (outside this clone, left in place): _codex wrote
  CODEX_OTEL's pair as a top-level key with no [otel] header. test_take_config came back FAILED (failures=2):
  TestB18CodexSwitches ("gpt-6.1-sol: otel is None, not metrics_exporter none") and TestContents. Caught.
- Source reading: openai/codex rust-v0.162.1 at /tmp/b18rev.lUt8/codex, commit 092d3acd, read only.

Not done: no walk, take, login, container or vendor call. Codex, the Gemini CLI and Claude Code were not run. No
login, token, lease or account file was opened. No safety check refused a tool call.
