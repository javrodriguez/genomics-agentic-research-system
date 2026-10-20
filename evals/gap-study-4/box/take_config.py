#!/usr/bin/env python3
"""The per-take config folder's files, per harness (CP2), each hashed for the freeze.

The folder is mounted at `run_take.CONFIG_MOUNT` in the take container and is the harness's user-config home there
(`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `GEMINI_CLI_HOME`, set by run_take's environment per harness). Split from
run_take.py (this lane's decision) so each file stays one owner and small.

  - claude-code: an EMPTY `settings.json` (`{}`). The plan said the per-take user settings "carry only the bypass
    acceptance"; that is departed from: the acceptance is RULED not required in -p runs (glitch-06, 14 Oct 2026;
    CLAUDE_BYPASS_RULING in run_take), so the study sends no bypass key anywhere. The host's user settings never exist
    in the box, and every turn runs --setting-sources project,local, so this user scope never loads anyway.
  - codex: `config.toml` with D8's values and the owner's subscription amendment, `model` from the caller,
    `model_reasoning_effort` the harness's default for that model at the pinned version (R3, below).
  - gemini: `settings.json` with D8's values verbatim, `model.name` from the caller; the thinking level and the API-key
    auth-type setting (name and value) are the pinned version's (R3, below). The installed0.64.0 source establishes
    the file location under GEMINI_CLI_HOME and the explicitly frozen legacy noninteractive path.
  - R3 (glitch-b5's ruling, Sun 18 Oct 2026; lane vendor-admission round 17, B6): CODEX_REASONING_EFFORT,
    GEMINI_THINKING and GEMINI_AUTH_SETTING, once PENDING, are each read statically from the pinned package (no model
    call, no network), the file and line beside each value and in VALUE_SOURCES.
  - R-6 (glitch-b5's ruling of Sat 17 Oct 2026, under Javier's delegation; lane vendor-admission T4 P2): neither vendor
    file configures an instruction-file name. D8's `project_doc_fallback_filenames = ["CLAUDE.md"]` and
    `context.fileName = ["CLAUDE.md"]` are removed: each CLI reads its native file (INSTRUCTION_FILES), which
    walk_builders.build_run_tree places in the checkout beside every CLAUDE.md (round 10 ruling 3, gars/CLAUDE.md
    included) as a byte-identical copy of it.

`write()` refuses (NotReady) while any value its harness needs is PENDING. No public function takes a PENDING value
as a parameter; tests fill them only by patching this module in memory. No key ever enters a config file: no
function here takes one. Nothing in any file names the study (interface 16). Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

from box import run_take

PENDING = run_take.PENDING
NotReady = run_take.NotReady
Refused = run_take.Refused

CLAUDE_CODE, CODEX, GEMINI = run_take.CLAUDE_CODE, run_take.CODEX, run_take.GEMINI

# claude-code: the bypass acceptance, RULED not required in -p (CLAUDE_BYPASS_RULING in run_take): no key is written. This
# mirrors run_take.CLAUDE_BYPASS_KEY as its own literal (the process audit's attribute list is not widened; tests bind
# take_config.CLAUDE_BYPASS_KEY to run_take.CLAUDE_BYPASS_KEY).
CLAUDE_BYPASS_NOT_REQUIRED = "RULED: not required in -p"
CLAUDE_BYPASS_KEY = CLAUDE_BYPASS_NOT_REQUIRED
CLAUDE_SETTINGS = "settings.json"

# Codex: D8 section 3 plus owner's 13 Oct subscription-only amendment.
CODEX_CONFIG = "config.toml"
# R3: the harness's default for that model at the pinned Codex, per model: each model entry's default_reasoning_level in
# the bundled catalog codex-rs/models-manager/models.json at rust-v0.162.1 (VALUE_SOURCES).
CODEX_REASONING_EFFORT = {
    "gpt-6.1-sol": "low",       # models.json line 213
    "gpt-6-luna": "medium",     # models.json line 560
}
CODEX_TOP = (("web_search", "disabled"), ("check_for_update_on_startup", False), ("forced_login_method", "chatgpt"),
             ("cli_auth_credentials_store", "file"))
# Lane vendor-b18 (glitch-26's ruling B18-1, Mon 19 Oct 2026; the GPT practice walk w-o7's egress log): the pinned
# CLI's plugins off (features.plugins, on by default), so no plugin startup sync or bundle download runs and no plugin
# list fetched from the backend reaches the developer message; and its metrics export at exit off (otel.metrics_exporter
# "none"; it defaults to Statsig, sent to ab.chatgpt.com when the process exits). analytics.enabled is not used: it
# also turns off the analytics events queue and changes every model request's metadata (VALUE_SOURCES).
CODEX_PLUGINS = ("plugins", False)
CODEX_FEATURES = (("hooks", False), CODEX_PLUGINS)
CODEX_METRICS_EXPORTER = ("metrics_exporter", "none")
CODEX_OTEL = (CODEX_METRICS_EXPORTER,)
# Lane vendor-b22 (glitch-26's ruling B22-10, Tue 20 Oct 2026), R-B14-2's sibling: the study refuses delegation on the
# vendor side, so arm O's collaboration tools are off as Gemini's invoke_agent is excluded (the Claude arm keeps its
# Agent tool as a named difference). The model catalog gives both arm O models multi_agent_version v2 and [agents]
# enabled defaults to true, so every committed GPT practice walk was offered spawn_agent, send_message, followup_task,
# wait_agent, interrupt_agent and list_agents; enabled = false makes the config override Disabled ahead of the catalog
# (VALUE_SOURCES; lane-reports/vendor-b22-DESIGN.md section 10).
CODEX_AGENTS = (("enabled", False),)
# R-H1 (glitch-26's ruling on the B11 design note, Mon 19 Oct 2026): the run tree trusted up front. At the pinned Codex
# (rust-v0.162.1, commit 092d3acd) a thread start whose project has no trust_level, in a git checkout (the run tree's
# .git, config/src/project_root_markers.rs), with the full access the bypass flag gives, persists
# [projects."<run tree>"] trust_level = "trusted" into config.toml by temp file and rename
# (app-server/src/request_processors/thread_processor.rs 1362-1378; core/src/config/mod.rs 2359-2441). With the table
# placed here, the active project's lookup (config/src/config_toml.rs 907-921: the cwd, then its git root) finds
# trust_level set on turn 1, nothing is written, and config.toml stays these bytes on every turn. The key is the run
# tree as project_trust_key spells it (config/src/loader/mod.rs 1381-1412): dunce::canonicalize (line 61), lowercased
# on Windows only. The project layer is then trusted from turn 1 (it was from the persisted table anyway), so the
# launcher refuses Codex's project-config paths in the working folder and its ancestors (run_take.LAUNCHER_SOURCE).
CODEX_TRUST_LEVEL = "trusted"
CODEX_NEEDS_RUN_TREE = True
_RUN_TREE_KEY = re.compile(r"/[A-Za-z0-9._@+/-]+")

# gemini: D8 section 3, verbatim, as dotted paths into settings.json.
GEMINI_SETTINGS = (("tools.exclude", ["google_web_search", "web_fetch"]), ("hooksConfig.enabled", False), ("general.enableAutoUpdate", False),
                   ("general.enableAutoUpdateNotification", False), ("privacy.usageStatisticsEnabled", False),
                   ("telemetry.enabled", False),
                   ("experimental.adk.agentSessionNoninteractiveEnabled", False))
GEMINI_MODEL_PATH = "model.name"
# R-6: the instruction file each vendor CLI reads by its own default name, configured nowhere (no fallback name is used
# or accepted): Codex's AGENTS.md, Gemini CLI's GEMINI.md. walk_builders.build_run_tree places each beside every
# CLAUDE.md of the checkout (round 10 ruling 3) as a copy of it, the file the claude-code arm reads.
INSTRUCTION_FILES = {CODEX: "AGENTS.md", GEMINI: "GEMINI.md"}
# Each {"path": "<dotted path>", "value": <JSON value>}, read statically at the pinned 0.64.0 (R3, VALUE_SOURCES).
# The thinking level: both arm G models extend the built-in alias chat-base-3 (bundle/chunk-NR7L3FXV.js lines 362349
# and 362361), whose thinkingLevel is HIGH (line 362280; ThinkingLevel.HIGH, line 258475); settings.json's
# modelConfigs.customAliases replaces an alias by name (bundle/chunk-FLKY6NH5.js line 13409; kept beside the built-in
# aliases, chunk-NR7L3FXV.js line 380852), so chat-base-3 is restated as it is: the default, pinned in the file.
GEMINI_THINKING = {"path": "modelConfigs.customAliases", "value": {"chat-base-3": {
    "extends": "chat-base", "modelConfig": {"generateContentConfig": {"thinkingConfig": {"thinkingLevel": "HIGH"}}}}}}
# The API-key auth type: security.auth.selectedType (bundle/chunk-FLKY6NH5.js line 14183) set to AuthType.USE_GEMINI,
# "gemini-api-key" (bundle/chunk-NR7L3FXV.js line 312750).
GEMINI_AUTH_SETTING = {"path": "security.auth.selectedType", "value": "gemini-api-key"}
# Folder trust off (round 18 B9, glitch-26's ruling B9): it defaults on at the pinned version (bundle/chunk-FLKY6NH5.js
# line 9599), and a headless run in a folder it does not trust stops at startup with FatalUntrustedWorkspaceError, exit
# 55 (bundle/gemini-Q2GRYIAK.js line 11153; the class at bundle/chunk-NR7L3FXV.js line 252702), before any model
# call; off, that check returns first (line 11145). Reviews r18-b9 NIT 2 and r18-b10 NIT 1 (B10): these are the files
# the bundle runs; gemini-6ESINPDZ.js, which B9 first cited, is a copy no bundle file imports (VALUE_SOURCES,
# unreached_).
GEMINI_TRUST_SETTING = {"path": "security.folderTrust.enabled", "value": False}
# R-B14-1 (glitch-26's ruling, Mon 19 Oct 2026; lane vendor-b14 round 2, from the held walk w-g5's stats naming helper
# models): every helper alias the pinned 0.64.0 reaches under these settings names the row's model. Each is an entry of
# modelConfigs.customAliases, which replaces the built-in alias of that name (bundle/chunk-NR7L3FXV.js line 342156),
# so each restates its built-in entry's other fields (only "extends") with modelConfig.model the row's. Loop detection
# stays on: its first check, "loop-detection", extends gemini-3-flash-base and so follows it (line 362486). Per-row
# aliases are those whose use depends on the row's model: chat compression picks its alias from the chat's model
# (line 337037). A Gemini model with no entry in GEMINI_ROW_ALIASES is refused: its helper aliases were not read.
GEMINI_HELPER_ALIASES = {"gemini-3-flash-base": {"extends": "base"}, "loop-detection-double-check": {"extends": "base"},
                         "chat-compression-3-flash": {}, "chat-compression-default": {},
                         "agent-history-provider-summarizer": {}}
GEMINI_ROW_ALIASES = {"gemini-3.8-flash": {}, "gemini-3.5-flash-lite": {"chat-compression-3.1-flash-lite": {}}}
# R-B14-2: tools.exclude gains the subagent tool, beside D8's two web tools (VALUE_SOURCES).
GEMINI_AGENT_EXCLUSION = ("invoke_agent",)
# R3's record of each static read: the pinned package, the file (with its sha256 for the Gemini bundle files, equal to
# the box lane's installed-package evidence of 14 Oct), the line or lines, and what was read there.
_GEMINI_PKG = {"package": "@google/gemini-cli", "version": "0.64.0",
               "tarball_sha256": "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6"}
_CODEX_PKG = {"package": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"}
VALUE_SOURCES = {
    "CODEX_REASONING_EFFORT": {
        "package": "openai/codex", "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
        "file": "codex-rs/models-manager/models.json", "lines": {"gpt-6.1-sol": 213, "gpt-6-luna": 560},
        "read": "each model entry's default_reasoning_level; the file is the bundled catalog "
                "(include_str!, codex-rs/models-manager/src/lib.rs line 15)"},
    "GEMINI_THINKING": dict(_GEMINI_PKG, file="bundle/chunk-NR7L3FXV.js",
                            file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                            lines={"chat-base-3": 362280, "gemini-3.5-flash-lite": 362349, "gemini-3.8-flash": 362361,
                                   "ThinkingLevel.HIGH": 258475, "customAliases kept": 380852},
                            setting_file="bundle/chunk-FLKY6NH5.js",
                            setting_file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                            setting_line=13409,
                            read="both arm G models extend the built-in alias chat-base-3, whose thinkingLevel is "
                                 "HIGH (packages/core/src/config/defaultModelConfigs.ts); settings.json's "
                                 "modelConfigs.customAliases replaces an alias by name, so the built-in chat-base-3 is "
                                 "restated as it is"),
    "GEMINI_AUTH_SETTING": dict(_GEMINI_PKG, file="bundle/chunk-FLKY6NH5.js",
                                file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                line=14183, value_file="bundle/chunk-NR7L3FXV.js", value_line=312750,
                                read="security.auth.selectedType (packages/cli/src/config/settingsSchema.ts), set to "
                                     "AuthType.USE_GEMINI, the API-key auth type"),
    "GEMINI_TRUST_SETTING": dict(_GEMINI_PKG, file="bundle/chunk-FLKY6NH5.js",
                                 file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                 line=9599, check_file="bundle/gemini-Q2GRYIAK.js",
                                 check_file_sha256="7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da",
                                 check_lines={"folder trust off: the check returns": 11145,
                                              "headless and untrusted: FatalUntrustedWorkspaceError (exit 55)": 11153},
                                 exit55_file="bundle/chunk-NR7L3FXV.js",
                                 exit55_file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                                 exit55_line=252702, unreached_check_file="bundle/gemini-6ESINPDZ.js",
                                 unreached_check_file_sha256=("19950cab8f7bd8b48ea89c4ede22418b2e5d836d9c1554baed6"
                                                              "2c9019d74810b"),
                                 unreached_check_lines={
                                     "folder trust off: the check returns": 11129,
                                     "headless and untrusted: FatalUntrustedWorkspaceError (exit 55)": 11137},
                                 unreached_exit55={"file": "bundle/chunk-J7SXW2FI.js", "line": 252715, "file_sha256":
                                                   "e2aca15290b02dc9845704f3fed44c577919652508624f340974f0ff588f206e"},
                                 read="security.folderTrust.enabled defaults to true (settings.security?.folderTrust"
                                      "?.enabled ?? true), although docs/cli/trusted-folders.md calls the feature off "
                                      "by default; with it on, a headless run in an untrusted folder throws "
                                      "FatalUntrustedWorkspaceError, exit 55 (super(message, 55) at exit55_file "
                                      "exit55_line, in the running bundle: bundle/gemini.js line 110 loads "
                                      "gemini-Q2GRYIAK.js, which imports chunk-NR7L3FXV.js; unreached_check_file "
                                      "and unreached_exit55 are a second copy no bundle file imports); "
                                      "set to false, the startup check returns before any trust lookup"),
    "GEMINI_HELPER_ALIASES": dict(_GEMINI_PKG, file="bundle/chunk-NR7L3FXV.js",
                                  file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                                  lines={"gemini-3-flash-base": 362386, "loop-detection-double-check": 362490,
                                         "chat-compression-3-flash": 362522, "chat-compression-3.1-flash-lite": 362527,
                                         "chat-compression-default": 362547,
                                         "agent-history-provider-summarizer": 362552},
                                  model_lines={"gemini-3-flash-base": 362389, "loop-detection-double-check": 362493,
                                               "chat-compression-3-flash": 362524,
                                               "chat-compression-3.1-flash-lite": 362529,
                                               "chat-compression-default": 362549,
                                               "agent-history-provider-summarizer": 362554},
                                  use_lines={"gemini-3-flash-base": 345269, "loop-detection extends it": 362487,
                                             "loop-detection called": 344226,
                                             "loop-detection-double-check": 343867,
                                             "compression alias by the chat's model": 337195,
                                             "chat-compression-3-flash for gemini-3.8-flash": 337044,
                                             "chat-compression-3.1-flash-lite for gemini-3.5-flash-lite": 337051,
                                             "chat-compression-default for any other model": 337060,
                                             "agent-history-provider-summarizer": 344635,
                                             "agent-history-provider-summarizer, tool output": 348760},
                                  layer_lines={"customAliases over the built-in aliases": 342156,
                                               "customAliases kept": 380852, "the alias's model wins": 342295},
                                  setting_file="bundle/chunk-FLKY6NH5.js",
                                  setting_file_sha256="f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b941098bc8",
                                  setting_line=13409, loop_detection_setting_line=13371,
                                  read="each built-in helper alias the run can reach, its model, and where it is "
                                       "used; settings.json's modelConfigs.customAliases replaces a built-in alias "
                                       "by name, so each entry restates the built-in's extends (gemini-3-flash-base "
                                       "and loop-detection-double-check extend base, the compression and summarizer "
                                       "aliases extend nothing) with the row's model; loop-detection, llm-edit-fixer "
                                       "and next-speaker-checker extend gemini-3-flash-base and follow it; "
                                       "model.disableLoopDetection (default false) is not written"),
    "GEMINI_AGENT_EXCLUSION": dict(_GEMINI_PKG, file="bundle/chunk-NR7L3FXV.js",
                                   file_sha256="d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
                                   lines={'var AGENT_TOOL_NAME = "invoke_agent";': 283421,
                                          "maybeRegister(AgentTool,": 382849,
                                          "getActiveTools leaves out the excluded tools": 313466},
                                   setting_file="bundle/chunk-FLKY6NH5.js",
                                   setting_file_sha256=("f6a4ddd46350dad40515218069d369aaa0025f194c552400b69925b"
                                                        "941098bc8"),
                                   setting_line=13925, cli_file="bundle/gemini-Q2GRYIAK.js",
                                   cli_file_sha256="7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da",
                                   cli_line=8674,
                                   read="tools.exclude (a list of tool names, merged into the CLI's excluded tools) "
                                        "with invoke_agent, the subagent tool's name, so the registry never offers "
                                        "it; the plan's vendor side counts zero Agent calls by construction"),
    # Lane vendor-b18 (ruling B18-1): read at the pinned commit, the file and line of each gate the switch reaches.
    "CODEX_PLUGINS": dict(_CODEX_PKG, file="codex-rs/features/src/lib.rs",
                          lines={'key: "plugins"': 1560, "default_enabled: true": 1562,
                                 "plugin_recommendations_enabled needs it": 577},
                          uses={"codex-rs/app-server/src/message_processor.rs": {
                                    "the plugin startup tasks, started at process start": 558},
                                "codex-rs/core-plugins/src/manager.rs": {
                                    "the startup tasks run only with plugins on": 2820,
                                    "the curated-plugins sync, gated on plugins": 754,
                                    "the remote plugin bundle sync, gated on plugins": 1599,
                                    "plugins_for_config loads nothing with plugins off": 814,
                                    "the recommended plugins mode is Legacy with plugins off": 1908},
                                "codex-rs/core-plugins/src/startup_sync.rs": {
                                    "the curated sync's source, https://github.com/openai/plugins.git": 30},
                                "codex-rs/core-plugins/src/remote_bundle.rs": {
                                    "a bundle's download URL, from the remote listing": 192},
                                "codex-rs/core/src/session/mod.rs": {
                                    "recommended plugin candidates only if plugin_recommendations_enabled": 4248,
                                    "the recommended_plugins section pushed into the developer message": 4414},
                                "codex-rs/core/src/context/recommended_plugins_instructions.rs": {
                                    "the section's markers": 43, "the section's body, one line per plugin": 53},
                                "codex-rs/core/src/context/available_plugins_instructions.rs": {
                                    "the Plugins usage section, only when a plugin is loaded": 32},
                                "codex-rs/core/src/session/world_state.rs": {
                                    "the usage section needs a loaded plugin": 304},
                                "codex-rs/core/src/tools/spec_plan.rs": {
                                    "tool_suggest_enabled needs plugins": 712,
                                    "request_plugin_install registered only then": 1328}},
                          read="features.plugins (a Stable feature, on by default) gates the plugin startup tasks "
                               "(the curated-plugins git sync and the remote installed-plugin bundle sync), the "
                               "plugin load, and the plugin recommendations fetched from the backend, which the "
                               "developer message carries as its recommended_plugins section and the tool list as "
                               "request_plugin_install; set to false, none of them runs"),
    "CODEX_AGENTS": dict(_CODEX_PKG, file="codex-rs/core/src/config/mod.rs",
                         lines={"multi_agent_version_override: Disabled when agents_enabled is false": 1607,
                                "multi_agent_version_for_model: the override before the model's version": 1629,
                                "agents_enabled defaults to true": 3897},
                         uses={"codex-rs/config/src/config_toml.rs": {"ConfigToml.agents": 481,
                                                                      "AgentsToml.enabled": 756},
                               "codex-rs/models-manager/models.json": {
                                   "gpt-6.1-sol multi_agent_version v2": 194,
                                   "gpt-6-luna multi_agent_version v2": 541},
                               "codex-rs/features/src/lib.rs": {"multi_agent_v2 default_enabled false": 1424},
                               "codex-rs/core/src/session/mod.rs": {
                                   "the session's version: the override first, resumed threads too": 772},
                               "codex-rs/core/src/tools/spec_plan.rs": {
                                   "collab_tools_enabled is false for Disabled": 721,
                                   "the collaboration handlers registered only then": 1376},
                               "codex-rs/core/src/session/multi_agents.rs": {
                                   "the usage hint only for V2": 16, "the mode section only for V2": 80}},
                         read="[agents] enabled (default true) set to false makes the config override Disabled "
                              "ahead of the model catalog's multi_agent_version v2 for both arm O models, on new, "
                              "resumed and per-turn roads; the six collaboration tools (spawn_agent, send_message, "
                              "followup_task, wait_agent, interrupt_agent, list_agents) are then not registered and "
                              "the multi_agent_role and multi_agent_mode developer sections render nothing"),
    "CODEX_METRICS_EXPORTER": dict(_CODEX_PKG, file="codex-rs/core/src/config/otel.rs",
                                   lines={"otel.metrics_exporter defaults to Statsig": 21},
                                   uses={"codex-rs/config/src/config_toml.rs": {"the otel table": 547},
                                         "codex-rs/config/src/types.rs": {
                                             "OtelExporterKind is kebab-case, so None reads none": 596,
                                             "metrics_exporter": 643},
                                         "codex-rs/otel/src/config.rs": {
                                             "Statsig's endpoint, https://ab.chatgpt.com/otlp/v1/metrics": 9,
                                             "Statsig resolved to that endpoint": 24},
                                         "codex-rs/otel/src/provider.rs": {
                                             "no metrics with the None exporter": 218,
                                             "shutdown flushes the metrics": 104, "Drop runs shutdown at exit": 359},
                                         "codex-rs/core/src/otel_init.rs": {
                                             "the metrics exporter is otel.metrics_exporter's": 74},
                                         "codex-rs/exec/src/lib.rs": {
                                             "codex exec builds the provider, analytics on by default": 668},
                                         "codex-rs/app-server/src/turn_cost_worker.rs": {
                                             "the turn cost worker reads only an explicit OTLP exporter": 106}},
                                   not_used={"analytics.enabled": {
                                       "codex-rs/core/src/otel_init.rs": 71,
                                       "codex-rs/app-server/src/analytics_utils.rs": 14,
                                       "codex-rs/analytics/src/client.rs": 321,
                                       "codex-rs/core/src/session/session.rs": 746}},
                                   read="otel.metrics_exporter defaults to Statsig, which resolves to an OTLP HTTP "
                                        "exporter at ab.chatgpt.com, flushed when the provider shuts down at exit; "
                                        "none builds no metrics exporter; the key's one other reader, the turn cost "
                                        "worker, starts only for an explicit OTLP exporter, so Statsig and none "
                                        "leave it off alike. "
                                        "analytics.enabled = false also drops the exporter, but it also turns off "
                                        "the analytics events queue and sets analytics_enabled in every model "
                                        "request's metadata, so it is not used"),
}
# The settings file's path relative to GEMINI_CLI_HOME (for example ".gemini/settings.json"), once measured.
# Installed0.64.0 Storage.getGlobalSettingsPath: GEMINI_CLI_HOME/.gemini/settings.json.
# Exact installed path/hash/offset retained in gemini-storage-source.json.
GEMINI_SETTINGS_PATH = ".gemini/settings.json"

PENDING_WHY = {
    "CLAUDE_BYPASS_KEY": "the bypass acceptance: RULED not required in -p runs (CLAUDE_BYPASS_RULING in run_take); "
                         "listed here only if it is ever set back to PENDING.",
    "CODEX_REASONING_EFFORT": "Codex's model_reasoning_effort: the harness's default for that model at the pinned "
                              "version.",
    "GEMINI_THINKING": "Gemini CLI's thinking level (setting path and value) at the pinned version.",
    "GEMINI_AUTH_SETTING": "Gemini CLI's API-key auth-type setting, name and value, at the pinned version.",
    "GEMINI_SETTINGS_PATH": "where Gemini CLI reads settings.json under GEMINI_CLI_HOME at the pinned version.",
}
NEEDS = {CLAUDE_CODE: ("CLAUDE_BYPASS_KEY",), CODEX: ("CODEX_REASONING_EFFORT",),
         GEMINI: ("GEMINI_THINKING", "GEMINI_AUTH_SETTING", "GEMINI_SETTINGS_PATH")}

_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def _pending_values() -> dict:
    return {"CLAUDE_BYPASS_KEY": CLAUDE_BYPASS_KEY, "CODEX_REASONING_EFFORT": CODEX_REASONING_EFFORT,
            "GEMINI_THINKING": GEMINI_THINKING, "GEMINI_AUTH_SETTING": GEMINI_AUTH_SETTING,
            "GEMINI_SETTINGS_PATH": GEMINI_SETTINGS_PATH}


def pending() -> dict:
    values = _pending_values()
    return {k: why for k, why in PENDING_WHY.items() if run_take._is_pending(values[k])}


def _ready(harness: str) -> None:
    values = _pending_values()
    still = [k for k in NEEDS[harness] if run_take._is_pending(values[k])]
    if still:
        raise NotReady(f"{harness} config needs {', '.join(still)}: " + " ".join(PENDING_WHY[k] for k in still))


def _json_bytes(doc) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        if not re.fullmatch(r"[A-Za-z0-9._ -]*", v):
            raise Refused("a config string holds only letters, digits, dot, dash, underscore and space")
        return f'"{v}"'
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    raise Refused(f"no TOML form for {type(v).__name__}")


def _set(doc: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    if not all(_KEY.fullmatch(p) for p in parts):
        raise Refused(f"setting path {dotted!r} is off its shape")
    cur = doc
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
        if not isinstance(cur, dict):
            raise Refused(f"setting path {dotted!r} crosses a value")
    if parts[-1] in cur:
        raise Refused(f"setting {dotted!r} is set twice")
    cur[parts[-1]] = value


def _model(model) -> str:
    if not isinstance(model, str) or not _MODEL.fullmatch(model):
        raise Refused("the model is a plain model id")
    return model


def _claude(model) -> dict:
    if model is not None:
        raise Refused("Claude Code's per-take settings are empty; the model rides as a flag")
    if CLAUDE_BYPASS_KEY != CLAUDE_BYPASS_NOT_REQUIRED:
        raise Refused("the study writes no bypass acceptance key: RULED not required in -p runs")
    return {CLAUDE_SETTINGS: _json_bytes({})}


def _codex(model) -> dict:
    model = _model(model)
    effort = CODEX_REASONING_EFFORT.get(model) if isinstance(CODEX_REASONING_EFFORT, dict) else None
    if not isinstance(effort, str):
        raise Refused(f"no reasoning effort is sourced for model {model!r} at the pinned Codex "
                      f"(CODEX_REASONING_EFFORT)")
    lines = [f"model = {_toml_value(model)}",
             f"model_reasoning_effort = {_toml_value(effort)}"]
    lines += [f"{k} = {_toml_value(v)}" for k, v in CODEX_TOP]
    lines += ["", "[features]"] + [f"{k} = {_toml_value(v)}" for k, v in CODEX_FEATURES]
    if CODEX_AGENTS:                                   # B22-10: arm O's collaboration tools off
        lines += ["", "[agents]"] + [f"{k} = {_toml_value(v)}" for k, v in CODEX_AGENTS]
    if CODEX_OTEL:
        lines += ["", "[otel]"] + [f"{k} = {_toml_value(v)}" for k, v in CODEX_OTEL]
    return {CODEX_CONFIG: ("\n".join(lines) + "\n").encode("ascii")}


def codex_project_key(run_tree) -> str:
    """The run tree as the pinned Codex's project_trust_key spells it on Linux: the canonical absolute path (no link
    on the way, no `.`, `..`, doubled or trailing slash), from a character set a TOML basic-string key carries as it
    is. The run tree is bind-mounted at the same path in the take container, so its host spelling is the container's.
    Refuses anything else: a key off the canonical spelling misses Codex's lookup, and Codex writes its own."""
    if not isinstance(run_tree, str) or not _RUN_TREE_KEY.fullmatch(run_tree):
        raise Refused("the run tree is an absolute path of letters, digits and . _ @ + - / only")
    if os.path.normpath(run_tree) != run_tree or run_tree.startswith("//") or os.path.realpath(run_tree) != run_tree:
        raise Refused(f"the run tree {run_tree!r} is not its canonical path, so Codex's trust key would not match it")
    return run_tree


def _codex_trust_table(run_tree) -> bytes:
    return f'\n[projects."{codex_project_key(run_tree)}"]\ntrust_level = "{CODEX_TRUST_LEVEL}"\n'.encode("ascii")


def _gemini(model) -> dict:
    doc = {}
    for path, value in GEMINI_SETTINGS:
        _set(doc, path, value)
    _set(doc, GEMINI_MODEL_PATH, _model(model))
    if model not in GEMINI_ROW_ALIASES:
        raise Refused(f"no helper aliases are read for model {model!r} at the pinned Gemini CLI (GEMINI_ROW_ALIASES)")
    for measured in (GEMINI_THINKING, GEMINI_AUTH_SETTING, GEMINI_TRUST_SETTING):
        if not (isinstance(measured, dict) and set(measured) == {"path", "value"}):
            raise Refused("a measured setting is {'path', 'value'}")
        _set(doc, measured["path"], measured["value"])
    # R-B14-2: the subagent tool joins D8's excluded tools.
    tools = doc.setdefault("tools", {})
    tools["exclude"] = list(tools.get("exclude", [])) + list(GEMINI_AGENT_EXCLUSION)
    # R-B14-1: every helper alias repointed at the row's model, beside R3's restated chat-base-3.
    # A new mapping: the restated chat-base-3 is GEMINI_THINKING's own value, never changed in place.
    configs = doc.setdefault("modelConfigs", {})
    aliases = dict(configs.get("customAliases", {}))
    for alias, rest in dict(GEMINI_HELPER_ALIASES, **GEMINI_ROW_ALIASES[model]).items():
        if alias in aliases:
            raise Refused(f"helper alias {alias!r} is set twice")
        aliases[alias] = dict(rest, modelConfig={"model": model})
    configs["customAliases"] = aliases
    rel = GEMINI_SETTINGS_PATH
    if not isinstance(rel, str) or rel.startswith("/") or ".." in rel.split("/") or not rel.endswith(".json"):
        raise Refused("the settings path is a relative .json path under GEMINI_CLI_HOME")
    return {rel: _json_bytes(doc)}


WRITERS = {CLAUDE_CODE: _claude, CODEX: _codex, GEMINI: _gemini}


def files_for(harness: str, *, model, run_tree=None) -> dict:
    """{relative path: bytes} for one harness's per-take config. Refuses while a value it needs is PENDING. With the
    take's run tree, a codex config.toml ends in that tree's trust table (R-H1); without it, the file is the template
    the draft records (config_templates), which write() never places for codex. Gemini's and Claude Code's files do
    not depend on the run tree."""
    run_take._known_harness(harness)
    if harness not in WRITERS:
        raise Refused(f"no config writer for {harness!r}")
    _ready(harness)
    files = WRITERS[harness](model)
    if harness == CODEX and run_tree is not None:
        files = dict(files, **{CODEX_CONFIG: files[CODEX_CONFIG] + _codex_trust_table(run_tree)})
    return files


def public_record(harness: str, *, model, run_tree=None) -> dict:
    """Submitted public settings only, rendered through every existing readiness check.

    No config-home file or credential is read. This is not proof of loaded settings;
    actual launch/preflight/native-session evidence must bind these generated bytes.
    Codex's subscription execution remains independently refused by run_take.
    """
    files = files_for(harness, model=model, run_tree=run_tree)
    return {"schema": 1, "harness": harness,
            "files": [{"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                       "text": data.decode("ascii")} for path, data in sorted(files.items())]}


def write(config_dir: str, harness: str, *, model, run_tree=None) -> dict:
    """Write the files into a fresh, empty per-take config folder outside every repository; return their hash. A
    codex take's config names its run tree (R-H1): without it, refused."""
    config_dir = run_take._abs_path(config_dir, "config_dir")
    if harness == CODEX and CODEX_NEEDS_RUN_TREE and run_tree is None:
        raise Refused("a codex take's config.toml names its run tree (R-H1): without the trust table Codex rewrites "
                      "the file on turn 1")
    files = files_for(harness, model=model, run_tree=run_tree)
    if os.path.islink(config_dir) or not os.path.isdir(config_dir) or os.listdir(config_dir):
        raise Refused("the per-take config folder must exist and be empty")
    if not run_take.outside_every_repository(config_dir):
        raise Refused("the per-take config folder must sit outside every repository")
    for rel, data in sorted(files.items()):
        path = os.path.join(config_dir, rel)
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
    return {"harness": harness, "files": sorted(files), "sha256": config_sha256(config_dir, harness)}


# R-H3 (glitch-26's ruling on lane vendor-b11, round 3, Mon 19 Oct 2026): a Codex turn that is killed (a timeout,
# kill_agent), or a Codex process that exits without unwinding (clap's own exit after --version), leaves its arg0
# helper folder behind: CODEX_HOME/tmp/arg0/codex-arg0<6 tempfile characters>/ with .lock and four links, each to
# std::env::current_exe() (codex-rs/arg0/src/lib.rs at rust-v0.162.1: names 21-24 and sandboxing/src/landlock.rs 7,
# .lock 25, the folder 358 and 373-375, the links 387-401). Those four are the only links admitted in the config folder,
# and only with their target the take image's codex executable: CODEX_EXECUTABLE, the binary_path the pinned take-o
# image's environment-name sweep measured (lane-reports/stub-take-20261014/probes/codex-env-name-sweep-athena-20261014.json,
# sha256 ddb31eec...; its image is box/codex/image.lock's image_id, sha256:21b21415...). They are hashed by name and
# target string, never followed; every other link refuses.
CODEX_ARG0_LINKS = run_take.CODEX_ARG0_LINKS
CODEX_ARG0_DIR = run_take.CODEX_ARG0_DIR
CODEX_EXECUTABLE = run_take.CODEX_EXECUTABLE


def codex_arg0_link(rel: str, target: str) -> bool:
    """run_take.codex_arg0_link: the one rule, shared with B11's per-turn check (run_take.check_config_folder)."""
    return run_take.codex_arg0_link(rel, target)


def config_sha256(folder: str, harness: str | None = None) -> str:
    """One sha256 over every file of the folder: sorted relative paths and their bytes' sha256. Links refused, but
    for a codex folder R-H3's four arg0 links, each hashed by its name and target string (never followed). R5-4 (lane
    vendor-b11 round 5): the link rule is the codex harness's alone, as run_take.check_config_folder's is; a claude-code
    or gemini folder, or one hashed with no harness named, refuses every link exactly as before R-H3."""
    entries = []
    for root, dirs, names in os.walk(folder, followlinks=False):
        for d in dirs:
            if os.path.islink(os.path.join(root, d)):
                raise Refused("a link in the config folder")
        for n in names:
            path = os.path.join(root, n)
            if harness == CODEX and os.path.islink(path):
                rel = os.path.relpath(path, folder).replace(os.sep, "/")
                target = os.readlink(path)
                if not codex_arg0_link(rel, target):
                    raise Refused(f"a link in the config folder: {rel}")
                entries.append((rel, "link:" + target))
                continue
            if os.path.islink(path) or not os.path.isfile(path):
                raise Refused("a link or a special file in the config folder")
            with open(path, "rb") as fh:
                entries.append((os.path.relpath(path, folder), hashlib.sha256(fh.read()).hexdigest()))
    h = hashlib.sha256()
    for rel, digest in sorted(entries):
        h.update(f"{rel}\0{digest}\n".encode("utf-8"))
    return h.hexdigest()
