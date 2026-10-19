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
