#!/usr/bin/env python3
"""Where each entry of transcript_gemini.GEMINI_TOOLS was read in the pinned Gemini CLI 0.64.0 (lane vendor-admission
round 18 B12; glitch-26's ruling, Sun 18 Oct 2026, under Javier's standing delegation; practice walk w-g3 on 779097fc
held on "tool name with no entry in the parser's table: 'update_topic'").

SOURCES names exactly the table's tools (tests/test_gemini_tool_registry.py R3), each with the pinned package and its
tarball sha256, the bundle file and its sha256, the lines read as [file, line, the text the line holds], the package's
own Kind and the view kind, and a sentence on what the tool does in the pinned code. The package was read statically
from the unpacked tarball, never run or imported; `tests/test_gemini_tool_registry.py --sources <bundle folder>`
re-reads every cited line on demand. The citations are kept apart from transcript_gemini.py so the reader's generated
mutation sweep (tests/test_gemini_adapter.py) mutates the table, which the battery reads, and not its documentation.

No model is called anywhere in this module. Standard library only.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import transcript_view as tv  # noqa: E402

# Each entry's source: the pinned package, the bundle file and its sha256, the lines read ([file, line, the text the
# line holds]), the package's own Kind and the view kind. tests/test_gemini_tool_registry.py --sources re-reads every
# cited line in the unpacked package. NOT OFFERED, so refused (no entry): google_web_search and web_fetch (D8's
# tools.exclude); ask_user (excluded in every non-interactive run, bundle/gemini-Q2GRYIAK.js lines 8422-8424);
# read_mcp_resource and list_mcp_resources (active only with an MCP resource, chunk-NR7L3FXV.js lines 313503-313507; the
# take configures no MCP server); the six tracker_* tools (registered only with experimental.taskTracker, default off,
# line 380825); read_many_files and get_internal_docs (defined, never registered in the main registry); complete_task (a
# sub-agent registry's own, line 350507); run_shell_command's additional_permissions key (declared only with tool
# sandboxing, line 282021; no take runs with --sandbox).
_PKG = {"package": "@google/gemini-cli", "version": "0.64.0",
        "tarball_sha256": "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6"}
_C = "bundle/chunk-NR7L3FXV.js"
_C_SHA256 = "d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c"
_Q = "bundle/gemini-Q2GRYIAK.js"
_WAIT = [_C, 274302, "wait_for_previous: {"]


def _src(name, view_kind, kind_in_package, lines, read):
    return dict(_PKG, file=_C, file_sha256=_C_SHA256, lines=[list(x) for x in lines], kind_in_package=kind_in_package,
                view_kind=view_kind, read=read)


SOURCES = {
    "run_shell_command": _src("run_shell_command", tv.SHELL, "Kind.Execute", (
        [_C, 280624, 'var SHELL_TOOL_NAME = "run_shell_command";'], [_C, 382829, "maybeRegister(ShellTool,"],
        [_C, 326403, "Kind.Execute"], [_C, 282923, "run_shell_command: (enableInteractiveShell"],
        [_C, 282001, "[SHELL_PARAM_COMMAND]: {"], [_C, 282005, "[PARAM_DESCRIPTION]: {"],
        [_C, 282009, "[PARAM_DIR_PATH]: {"], [_C, 282013, "[SHELL_PARAM_IS_BACKGROUND]: {"],
        [_C, 282017, "delay_ms: {"], [_C, 282021, "...enableToolSandboxing ? {"]),
        "ShellTool runs the command in a shell (Kind.Execute): shell; command and is_background are the view's"),
    "read_file": _src("read_file", tv.READ, "Kind.Read", (
        [_C, 280621, 'var READ_FILE_TOOL_NAME = "read_file";'], [_C, 382803, "maybeRegister(ReadFileTool,"],
        [_C, 314479, "Kind.Read"], [_C, 282709, "read_file: {"], [_C, 282715, "[PARAM_FILE_PATH]: {"],
        [_C, 282719, "[READ_FILE_PARAM_START_LINE]: {"], [_C, 282724, "[READ_FILE_PARAM_END_LINE]: {"],
        [_C, 280622, 'READ_FILE_PARAM_START_LINE = "start_line"'], [_C, 280623, 'READ_FILE_PARAM_END_LINE = "end_line"']),
        "ReadFileTool reads one file (Kind.Read): read; file_path is the view's path (start_line and end_line, not the "
        "documented offset and limit)"),
    "write_file": _src("write_file", tv.WRITE, "Kind.Edit", (
        [_C, 280627, 'var WRITE_FILE_TOOL_NAME = "write_file";'], [_C, 382825, "maybeRegister(WriteFileTool,"],
        [_C, 311154, "Kind.Edit"], [_C, 282733, "write_file: {"], [_C, 282739, "[PARAM_FILE_PATH]: {"],
        [_C, 282743, "[WRITE_FILE_PARAM_CONTENT]: {"]),
        "WriteFileTool writes a whole file's content: write; file_path is the view's path"),
    "replace": _src("replace", tv.EDIT, "Kind.Edit", (
        [_C, 280629, 'var EDIT_TOOL_NAME = "replace";'], [_C, 382824, "maybeRegister(EditTool,"],
        [_C, 310469, "Kind.Edit"], [_C, 282924, "replace: {"], [_C, 282931, "[PARAM_FILE_PATH]: {"],
        [_C, 282935, "[EDIT_PARAM_INSTRUCTION]: {"], [_C, 282939, "[EDIT_PARAM_OLD_STRING]: {"],
        [_C, 282943, "[EDIT_PARAM_NEW_STRING]: {"], [_C, 282947, "[EDIT_PARAM_ALLOW_MULTIPLE]: {"],
        [_C, 280633, 'EDIT_PARAM_ALLOW_MULTIPLE = "allow_multiple"']),
        "EditTool replaces old_string by new_string in one file: edit; file_path is the view's path (allow_multiple, "
        "not the documented expected_replacements)"),
    "glob": _src("glob", tv.SEARCH, "Kind.Search", (
        [_C, 280607, 'var GLOB_TOOL_NAME = "glob";'], [_C, 382822, "maybeRegister(GlobTool,"],
        [_C, 322804, "Kind.Search"], [_C, 282858, "glob: {"], [_C, 282864, "[PARAM_PATTERN]: {"],
        [_C, 282868, "[PARAM_DIR_PATH]: {"], [_C, 282872, "[PARAM_CASE_SENSITIVE]: {"],
        [_C, 282876, "[PARAM_RESPECT_GIT_IGNORE]: {"], [_C, 282880, "[PARAM_RESPECT_GEMINI_IGNORE]: {"]),
        "GlobTool finds paths by a pattern: search; pattern and dir_path are the view's"),
    "grep_search": _src("grep_search", tv.SEARCH, "Kind.Search", (
        [_C, 280608, 'var GREP_TOOL_NAME = "grep_search";'], [_C, 382813, "maybeRegister(RipGrepTool,"],
        [_C, 382817, "maybeRegister(GrepTool,"], [_C, 322558, "Kind.Search"], [_C, 322148, "Kind.Search"],
        [_C, 282751, "grep_search: {"], [_C, 282791, "grep_search_ripgrep: {"], [_C, 282797, "[PARAM_PATTERN]: {"],
        [_C, 282801, "[PARAM_DIR_PATH]: {"], [_C, 282805, "[GREP_PARAM_INCLUDE_PATTERN]: {"],
        [_C, 282809, "[GREP_PARAM_EXCLUDE_PATTERN]: {"], [_C, 282813, "[GREP_PARAM_NAMES_ONLY]: {"],
        [_C, 282817, "[PARAM_CASE_SENSITIVE]: {"], [_C, 282821, "[GREP_PARAM_FIXED_STRINGS]: {"],
        [_C, 282825, "[GREP_PARAM_CONTEXT]: {"], [_C, 282830, "[GREP_PARAM_AFTER]: {"],
        [_C, 282835, "[GREP_PARAM_BEFORE]: {"], [_C, 282840, "[GREP_PARAM_NO_IGNORE]: {"],
        [_C, 282844, "[GREP_PARAM_MAX_MATCHES_PER_FILE]: {"], [_C, 282849, "[GREP_PARAM_TOTAL_MAX_MATCHES]: {"]),
        "RipGrepTool, or GrepTool where ripgrep is not usable, under one name, searches file contents: search; the keys "
        "are the ripgrep schema's, which hold the grep schema's (lines 282751-282788)"),
    "search_file_content": _src("search_file_content", tv.SEARCH, "Kind.Search", (
        [_C, 283434, "search_file_content: GREP_TOOL_NAME"],
        [_C, 313636, "const currentName = TOOL_LEGACY_ALIASES[name3];"], [_Q, 12226, "tool_name: event.value.name,"],
        [_C, 282791, "grep_search_ripgrep: {"]),
        "the legacy alias the registry resolves to grep_search (never offered, but run if the model names it, and the "
        "stream carries the model's own name): grep_search's kind and keys"),
    "list_directory": _src("list_directory", tv.OTHER, "Kind.Search", (
        [_C, 280619, 'var LS_TOOL_NAME = "list_directory";'], [_C, 382802, "maybeRegister(LSTool,"],
        [_C, 313838, "Kind.Search"], [_C, 282888, "list_directory: {"], [_C, 282894, "[PARAM_DIR_PATH]: {"],
        [_C, 282898, "[LS_PARAM_IGNORE]: {"], [_C, 282905, "[PARAM_FILE_FILTERING_OPTIONS]: {"]),
        "LSTool lists one folder; it takes no pattern, which the view's search requires, so other, the class the table "
        "already gave it"),
    "write_todos": _src("write_todos", tv.OTHER, "Kind.Other", (
        [_C, 280636, 'var WRITE_TODOS_TOOL_NAME = "write_todos";'], [_C, 382835, "maybeRegister(WriteTodosTool,"],
        [_C, 382834, "if (this.getUseWriteTodos()) {"], [_C, 380941, "this.useWriteTodos = isGemini2"],
        [_C, 360818, "Kind.Other"], [_C, 283049, "write_todos: {"]),
        "WriteTodosTool keeps the agent's own todo list (Kind.Other): other; registered only for a gemini-2 model, so "
        "neither arm G model is offered it (the entry the table already held is kept)"),
    "update_topic": _src("update_topic", tv.OTHER, "Kind.Think", (
        [_C, 280666, 'var UPDATE_TOPIC_TOOL_NAME = "update_topic";'], [_C, 382801, "maybeRegister(UpdateTopicTool,"],
        [_C, 332603, "Kind.Think"], [_C, 282094, "[TOPIC_PARAM_TITLE]: {"], [_C, 282098, "[TOPIC_PARAM_SUMMARY]: {"],
        [_C, 282102, "[TOPIC_PARAM_STRATEGIC_INTENT]: {"], _WAIT,
        [_C, 313499, "if (tool.name === UPDATE_TOPIC_TOOL_NAME) {"],
        [_C, 380892, "this.topicUpdateNarration = params.topicUpdateNarration ?? true;"]),
        "UpdateTopicTool sets the session's in-memory topic title and intent and touches no file (Kind.Think): other; "
        "offered while topic narration is on, its default"),
    "activate_skill": _src("activate_skill", tv.OTHER, "Kind.Other", (
        [_C, 280649, 'var ACTIVATE_SKILL_TOOL_NAME = "activate_skill";'], [_C, 382823, "maybeRegister(ActivateSkillTool,"],
        [_C, 323127, "Kind.Other"], [_C, 283245, "activate_skill: (skillNames) => getActivateSkillDeclaration"],
        [_C, 282074, "[SKILL_PARAM_NAME]: external_exports.string()"],
        [_C, 282078, "[SKILL_PARAM_NAME]: external_exports.enum(skillNames)"]),
        "ActivateSkillTool hands the model a named skill's instructions (Kind.Other): other; registered at startup "
        "with or without a skill"),
    "enter_plan_mode": _src("enter_plan_mode", tv.OTHER, "Kind.Plan", (
        [_C, 280663, 'var ENTER_PLAN_MODE_TOOL_NAME = "enter_plan_mode";'], [_C, 382839, "maybeRegister(EnterPlanModeTool,"],
        [_C, 380823, "this.planEnabled = params.plan ?? true;"], [_C, 355331, "Kind.Plan"],
        [_C, 283231, "enter_plan_mode: {"], [_C, 283237, "[PLAN_MODE_PARAM_REASON]: {"]),
        "EnterPlanModeTool switches the session's approval mode to plan and touches no file (Kind.Plan): other, as "
        "the harness-state tools are (ScheduleWakeup); plan mode is on by default"),
    "exit_plan_mode": _src("exit_plan_mode", tv.OTHER, "Kind.Plan", (
        [_C, 280661, 'var EXIT_PLAN_MODE_TOOL_NAME = "exit_plan_mode";'], [_C, 382838, "maybeRegister(ExitPlanModeTool,"],
        [_C, 355182, "Kind.Plan"], [_C, 283244, "exit_plan_mode: () => getExitPlanModeDeclaration(),"],
        [_C, 282061, "[EXIT_PLAN_PARAM_PLAN_FILENAME]: {"],
        [_C, 313511, "tool.name === EXIT_PLAN_MODE_TOOL_NAME && !isPlanMode"]),
        "ExitPlanModeTool presents a plan file for approval and leaves plan mode (Kind.Plan): other; offered only "
        "once enter_plan_mode has switched the session to plan mode"),
    "list_background_processes": _src("list_background_processes", tv.OTHER, "Kind.Read", (
        [_C, 355422, 'static Name = "list_background_processes";'],
        [_C, 382830, "maybeRegister(ListBackgroundProcessesTool,"], [_C, 355424, "Kind.Read"], _WAIT),
        "ListBackgroundProcessesTool lists the session's background shell processes, reading no workspace file: "
        "other, as Monitor is"),
    "read_background_output": _src("read_background_output", tv.OTHER, "Kind.Read", (
        [_C, 355534, 'static Name = "read_background_output";'],
        [_C, 382831, "maybeRegister(ReadBackgroundOutputTool,"], [_C, 355536, "Kind.Read"], [_C, 355539, "pid: {"],
        [_C, 355543, "lines: {"], [_C, 355548, "delay_ms: {"], _WAIT),
        "ReadBackgroundOutputTool reads a background process's output log by pid, never a workspace path: other, as "
        "Monitor is"),
    "invoke_agent": _src("invoke_agent", tv.DELEGATE, "Kind.Agent", (
        [_C, 283421, 'var AGENT_TOOL_NAME = "invoke_agent";'], [_C, 382849, "maybeRegister(AgentTool,"],
        [_C, 355009, "Kind.Agent"], [_C, 355013, "agent_name: {"], [_C, 355017, "prompt: {"], _WAIT),
        "AgentTool hands a prompt to a named sub-agent (Kind.Agent): delegate, as Claude Code's Agent is"),
}

# ---- OPEN_INPUT's citations (lane vendor-b16 round 2, glitch-26's ruling R-B16-2, Mon 19 Oct 2026) -----------------
# For each tool in transcript_gemini.OPEN_INPUT, where the pinned package shows both of the ruling's conditions: the
# schema leaves its properties open (no additionalProperties false in either family's grep schema, and Ajv run with
# strictSchema false only), and the run reads only the keys named in `reads` off the call's arguments.
# tests/test_gemini_undeclared_args.py U3 binds these to the table; its --sources re-reads every cited line.
_GREP_READS = ("pattern", "dir_path", "include_pattern", "exclude_pattern", "names_only", "case_sensitive",
               "fixed_strings", "context", "after", "before", "no_ignore", "max_matches_per_file", "total_max_matches",
               "wait_for_previous")
_GREP_OPEN_LINES = (
    # the schemas, gemini-3 family (both arm G models) and default-legacy (the one build validates): no
    # additionalProperties between each opening line and its required line (only write_todos sets it, 282573/282578)
    [_C, 282751, "grep_search: {"], [_C, 282788, "required: [PARAM_PATTERN]"],
    [_C, 282791, "grep_search_ripgrep: {"], [_C, 282855, "required: [PARAM_PATTERN]"],
    [_C, 282158, "grep_search: {"], [_C, 282195, "required: [PARAM_PATTERN]"],
    [_C, 282198, "grep_search_ripgrep: {"], [_C, 282262, "required: [PARAM_PATTERN]"],
    # build validates this.schema (the base declaration) with Ajv, whose only option is strictSchema false
    [_C, 274389, "build(params) {"], [_C, 274396, "validateToolParams(params) {"],
    [_C, 274310, "return this.getSchema();"],
    [_C, 273788, "var SchemaValidator = class {"], [_C, 273774, "strictSchema: false"],
    # GrepTool's invocation: its reads off this.params, and the two helpers it hands this.params to
    [_C, 321704, "var GrepToolInvocation = class extends BaseToolInvocation {"],
    [_C, 321746, "const pathParam = this.params.dir_path;"],
    [_C, 321815, "const totalMaxMatches = this.params.total_max_matches ?? DEFAULT_TOTAL_MAX_MATCHES;"],
    [_C, 321834, "pattern: this.params.pattern,"], [_C, 321836, "include_pattern: this.params.include_pattern,"],
    [_C, 321837, "exclude_pattern: this.params.exclude_pattern,"],
    [_C, 321839, "max_matches_per_file: this.params.max_matches_per_file,"],
    [_C, 321866, "formatGrepResults(allMatches, this.params, searchLocationDescription, totalMaxMatches);"],
    [_C, 321637, "const { pattern, names_only, include_pattern } = params;"],
    [_C, 321597, "const { names_only, context: context2, before, after } = params;"],
    [_C, 322156, "validateToolParamValues(params) {"],
    # RipGrepTool's invocation (GrepToolInvocation2): its reads off this.params
    [_C, 322248, "var GrepToolInvocation2 = class extends BaseToolInvocation {"],
    [_C, 322258, 'const pathParam = this.params.dir_path || ".";'],
    [_C, 322309, "const totalMaxMatches = this.params.total_max_matches ?? DEFAULT_TOTAL_MAX_MATCHES;"],
    [_C, 322328, "pattern: this.params.pattern,"], [_C, 322330, "include_pattern: this.params.include_pattern,"],
    [_C, 322331, "exclude_pattern: this.params.exclude_pattern,"],
    [_C, 322332, "case_sensitive: this.params.case_sensitive,"],
    [_C, 322333, "fixed_strings: this.params.fixed_strings,"],
    [_C, 322334, "context: this.params.context,"], [_C, 322335, "after: this.params.after,"],
    [_C, 322336, "before: this.params.before,"], [_C, 322337, "no_ignore: this.params.no_ignore,"],
    [_C, 322339, "max_matches_per_file: this.params.max_matches_per_file,"],
    [_C, 322361, "formatGrepResults(allMatches, this.params, searchLocationDescription, totalMaxMatches);"],
    [_C, 322384, "!this.params.names_only && this.params.context === void 0"],
    [_C, 322578, "validateToolParamValues(params) {"],
    # the scheduler reads wait_for_previous off every call's arguments
    [_C, 349439, 'const wait = request.args["wait_for_previous"];'],
    # the base invocation reads file_path only on an ask-user decision, which a headless run never reaches: the
    # invocation is built without respectsAutoEdit (default false), and checkPolicy refuses ask-user non-interactively
    [_C, 321708, "super(params, messageBus, _toolName, _toolDisplayName);"],
    [_C, 274078, "const filePath = extractFilePathFromArgs(this.params);"],
    [_C, 274035, "const target = args2.file_path ?? args2.path ?? args2.filePath ?? args2.file;"],
    [_C, 349488, "if (decision === PolicyDecision.ASK_USER) {"],
    [_C, 343497, "if (decision === PolicyDecision.ASK_USER) {"], [_C, 343498, "if (!config2.isInteractive()) {"],
    # the stream records the model's own parameters on tool_use
    [_Q, 12228, "parameters: event.value.args"],
    # two readers outside the invocation take the whole args, undeclared keys included (ruling R-B16-5). The loop
    # detector hashes the tool name with the whole args on every tool call request; a detected loop ends the turn, an
    # event the record carries; it is on in the takes (model.disableLoopDetection is not written, so it is false)
    [_C, 343947, "getToolCallKey(toolCall) {"], [_C, 343948, "const argsString = JSON.stringify(toolCall.args);"],
    [_C, 343949, "const keyString = `${toolCall.name}:${argsString}`;"],
    [_C, 343973, "isLoop = this.checkToolCallLoop(event.value);"],
    [_C, 344042, "const key = this.getToolCallKey(toolCall);"],
    [_C, 348323, "const loopResult2 = this.loopDetector.addAndCheck(event);"],
    [_C, 348325, "yield { type: GeminiEventType.LoopDetected };"],
    [_Q, 8614, "disableLoopDetection: settings.model?.disableLoopDetection,"],
    [_C, 380818, "this.disableLoopDetection = params.disableLoopDetection ?? false;"],
    # the policy engine stringifies the whole args only while a loaded rule or checker carries an argsPattern, and
    # tests a rule's modes and tool name before its argsPattern; Conseca is off unless security.enableConseca is set;
    # the takes turn hooks off (hooksConfig.enabled false in box/take_config.py GEMINI_SETTINGS)
    [_C, 364402, "if (toolCall.args && (this.rules.some((rule) => rule.argsPattern)"],
    [_C, 364403, "stringifiedArgs = stableStringify(toolCall.args);"],
    [_C, 364076, "if (rule.modes && rule.modes.length > 0) {"], [_C, 364095, "if (rule.toolName !== void 0) {"],
    [_C, 364130, "if (rule.argsPattern) {"],
    [_C, 366841, "rule: external_exports.array(PolicyRuleSchema).optional(),"],
    [_Q, 8669, "enableConseca: settings.security?.enableConseca"],
    [_C, 380958, "this.enableConseca = params.enableConseca ?? false;"],
    [_C, 368888, "if (!this.context.config.enableConseca) {"],
    [_Q, 8656, "enableHooks: settings.hooksConfig.enabled,"],
    # the loop detector's two outcomes (review c2c7e1e finding 1): a first detection breaks the stream before the
    # tripping request is yielded, so that call is neither recorded nor run, and a new turn sends the model a loop
    # warning; a second ends the turn, which the stream records as an error event of severity warning
    [_C, 348328, "} else if (loopResult2.count === 1) {"], [_C, 348334, "loopRecoverResult = loopResult2;"],
    [_C, 348356, "return yield* this._recoverFromLoop(loopRecoverResult"],
    [_C, 348608, "return this.sendMessageStream(feedback, signal, prompt_id, boundedTurns - 1, displayContent);"],
    [_Q, 12232, "} else if (event.type === GeminiEventType.LoopDetected) {"],
    [_Q, 12236, "type: JsonStreamEventType.ERROR,"], [_Q, 12238, 'severity: "warning",'],
    # the policy tiers and the runtime rules (review c2c7e1e finding 2): the admin, user, workspace and default tiers;
    # the workspace tier is off at the pin; policyPaths and adminPolicyPaths come from settings, which the takes never
    # set; the user tier is the config home's policies folder, which no take places; the runtime rules carry an
    # argsPattern only on a confirmed always-allow (an ask-user decision) or for a remote agent's invoke_agent
    [_C, 367769, "function getPolicyDirectories(defaultPoliciesDir, policyPaths, workspacePoliciesDir, adminPolicyPaths) {"],
    [_C, 367772, "Storage.getSystemPoliciesDir(),"],
    [_C, 367775, "...policyPaths && policyPaths.length > 0 ? policyPaths : [Storage.getUserPoliciesDir()],"],
    [_C, 253248, 'return path4.join(_Storage.getGlobalGeminiDir(), "policies");'],
    [_C, 253278, 'return path4.join(_Storage.getSystemConfigDir(), "policies");'],
    [_C, 253268, 'return "/etc/gemini-cli";'],
    [_Q, 7881, "var disableWorkspacePolicies = true;"], [_Q, 7906, "if (trustedFolder && !disableWorkspacePolicies) {"],
    [_Q, 7887, "policyPaths: settings.policyPaths,"], [_Q, 7888, "adminPolicyPaths: settings.adminPolicyPaths,"],
    [_C, 368100, "argsPattern: new RegExp(pattern),"], [_C, 342701, 'argsPattern: new RegExp(`"agent_name":'],
)
_GREP_OPEN_READ = (
    "both grep schemas, in both families, leave their properties open, so Ajv passes an undeclared key; GrepTool's "
    "and RipGrepTool's invocations (either serves grep_search) read only declared keys off this.params, and the "
    "scheduler reads wait_for_previous off every call; the base invocation's file_path read (extractFilePathFromArgs) "
    "runs only on an ask-user decision, which a headless --approval-mode yolo run never reaches (policies/yolo.toml "
    "lines 51-55 allow every tool, and checkPolicy refuses ask-user when not interactive), so an undeclared key such "
    "as file_path changes nothing the call does; the invocation reads only declared keys. Two readers outside it take "
    "the whole args, undeclared keys included, and neither changes what this call does. The loop detector hashes the "
    "tool name with the whole args, so an undeclared key's value decides whether a repeated call counts as a loop: a "
    "first detection drops the call that tripped it before the stream records it and starts a new turn with a loop "
    "warning to the model, and a second ends the turn, recorded as an error event of severity warning; the record "
    "shows what ran, and the reader reads that record, not the detector. The policy engine stringifies the whole args "
    "only for a loaded rule or checker with an argsPattern and tests each rule's modes and tool name first, and in a "
    "yolo take no such rule applies to grep_search: the default tier's argsPattern rules (policies/plan.toml) name "
    "invoke_agent, write_file and replace in plan mode only; policies/sandbox-default.toml's rules table is no policy "
    "rule (the policy file schema reads the key rule); the workspace tier is off at the pin; the takes set no "
    "policyPaths or adminPolicyPaths, and the user tier is the config home's policies folder, which no take places; "
    "the runtime rules carry an argsPattern only on a confirmed always-allow (an ask-user decision, never reached "
    "headless) or for a remote agent's invoke_agent (excluded); Conseca's checker carries no argsPattern and is off; "
    "the takes turn hooks off. The system tier (/etc/gemini-cli/policies in the take image) is not read here; the "
    "image's Dockerfile (box/gemini/Dockerfile) writes nothing there")
_ALIAS = [_C, 283434, "search_file_content: GREP_TOOL_NAME"]
OPEN_INPUT = {
    "grep_search": dict(_PKG, file=_C, file_sha256=_C_SHA256, closes_properties=False, reads=list(_GREP_READS),
                        lines=[list(x) for x in _GREP_OPEN_LINES], read=_GREP_OPEN_READ),
    "search_file_content": dict(_PKG, file=_C, file_sha256=_C_SHA256, closes_properties=False,
                                reads=list(_GREP_READS),
                                lines=[list(x) for x in _GREP_OPEN_LINES + (_ALIAS,)],
                                read="the legacy alias the registry resolves to grep_search: " + _GREP_OPEN_READ),
}
