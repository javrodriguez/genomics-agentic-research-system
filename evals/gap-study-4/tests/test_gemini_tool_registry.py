#!/usr/bin/env python3
"""Arm G's tool table, read from the pinned Gemini CLI 0.64.0's own tool registry (lane vendor-admission round 18 B12;
glitch-26's ruling, Sun 18 Oct 2026, under Javier's standing delegation).

Practice walk w-g3 on ship head 779097fc executed turn 1 (exit 0) and the drive refused its record: "the stream holds a
record off the pre-registered tables: tool_use: tool name with no entry in the parser's table: 'update_topic'". The
table (transcript_gemini.GEMINI_TOOLS) was the documented guess of lane w11b, never read against the pinned package.
B12 completes it from the package's registry (Config.createToolRegistry, bundle/chunk-NR7L3FXV.js), each entry with
its source lines and file sha256 (gemini_tool_sources.SOURCES), its class one of the view's existing kinds.

  R1  update_topic: a SYNTHETIC tool_use line built from the tool's own schema (title, summary, strategic_intent and
      the wait_for_previous key every tool without its own getSchema carries) passes check_record, GeminiParser maps
      it to an `other` call, and gemini_adapter.read_stream reads a synthetic stream that carries it.
  R2  the table is the registry: exactly REGISTRY's names, each with its view kind, its key map and its allowed keys;
      a call with every allowed key maps to its kind and its view args, and a call with each key alone is accepted.
  R3  every entry carries its source: gemini_tool_sources.SOURCES names exactly the table's tools, each with the pinned package
      and tarball sha256, a pinned bundle file and its sha256, the lines read (each a positive line and a non-empty
      text), the package's own Kind word and the view kind, which is the table's.
  R4  still refused, by the record check and the parser: D8's excluded web tools (google_web_search, web_fetch), the
      tools the pinned package defines but a headless arm G run never offers (ask_user, excluded headless; the MCP
      resource tools, offered only with an MCP resource; the tracker tools, off by default; read_many_files and
      get_internal_docs, never registered in the main registry; complete_task, a sub-agent's own), names absent from
      the package, and a key the schema does not declare (read_file's offset and limit, the table's earlier guess).
  R5  `--sources <the unpacked package's bundle folder>` (on demand, never in the battery: the package is not in the
      repository): each cited file's sha256 is the recorded one and each cited line holds its recorded text.

`--witnesses` runs each table mutant in this process (the table patched for the run, never written): every entry
removed, every entry given another kind, and every entry with one allowed key dropped turns R1 or R2 red by
assertion, and each R4 name added to the table turns R4 red.

Synthetic strings only: no recorded stream, no held take's bytes, no model, network or vendor package is read by the
battery. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gemini_adapter as ga  # noqa: E402
import gemini_tool_sources as gts  # noqa: E402
import transcript_gemini as tg  # noqa: E402
import transcript_view as tv  # noqa: E402

FIXTURES = HERE / "tests" / "fixtures" / "gemini-streams"
MODEL = "gemini-3.8-flash"
TARBALL_SHA256 = "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6"
FILE_SHA256 = {"bundle/chunk-NR7L3FXV.js": "d566e81b1df8d4d44a91bf7aeea96a58ec0e6c8934fa424315ef060507dcbb8c",
               "bundle/gemini-Q2GRYIAK.js": "7702da31cf099ca3e1d64fd195f15b7726b2c2829ec21e955558eb9dbfba47da"}

# The spec, read from the pinned package by this lane (each entry's source lines are in gemini_tool_sources.SOURCES):
# name -> (view kind, {raw key: view arg}, allowed raw keys, one synthetic value per allowed key).
GREP_KEYS = ("pattern", "dir_path", "include_pattern", "exclude_pattern", "names_only", "case_sensitive",
             "fixed_strings", "context", "after", "before", "no_ignore", "max_matches_per_file", "total_max_matches")
GREP_VALUES = ("def", "src", "*.py", "*.md", False, False, False, 1, 1, 1, False, 3, 10)
REGISTRY = {
    "run_shell_command": (tv.SHELL, {"command": "command", "is_background": "background"},
                          ("command", "description", "dir_path", "is_background", "delay_ms"),
                          ("ls", "list the folder", "src", True, 100)),
    "read_file": (tv.READ, {"file_path": "path"}, ("file_path", "start_line", "end_line"), ("a.txt", 1, 5)),
    "write_file": (tv.WRITE, {"file_path": "path"}, ("file_path", "content"), ("a.txt", "x")),
    "replace": (tv.EDIT, {"file_path": "path"}, ("file_path", "instruction", "old_string", "new_string",
                                                 "allow_multiple"), ("b.py", "i", "a", "b", False)),
    "glob": (tv.SEARCH, {"pattern": "pattern", "dir_path": "path"},
             ("pattern", "dir_path", "case_sensitive", "respect_git_ignore", "respect_gemini_ignore"),
             ("*.py", "src", False, True, True)),
    "grep_search": (tv.SEARCH, {"pattern": "pattern", "dir_path": "path"}, GREP_KEYS, GREP_VALUES),
    "search_file_content": (tv.SEARCH, {"pattern": "pattern", "dir_path": "path"}, GREP_KEYS, GREP_VALUES),
    "list_directory": (tv.OTHER, {}, ("dir_path", "ignore", "file_filtering_options"), (".", ["x"], {})),
    "write_todos": (tv.OTHER, {}, ("todos",), ([],)),
    "update_topic": (tv.OTHER, {}, ("title", "summary", "strategic_intent", "wait_for_previous"),
                     ("Synthetic chapter", "A synthetic summary.", "A synthetic intent.", False)),
    "activate_skill": (tv.OTHER, {}, ("name",), ("synthetic-skill",)),
    "enter_plan_mode": (tv.OTHER, {}, ("reason",), ("a synthetic reason",)),
    "exit_plan_mode": (tv.OTHER, {}, ("plan_filename",), ("synthetic-plan.md",)),
    "list_background_processes": (tv.OTHER, {}, ("wait_for_previous",), (False,)),
    "read_background_output": (tv.OTHER, {}, ("pid", "lines", "delay_ms", "wait_for_previous"), (4242, 10, 0, False)),
    "invoke_agent": (tv.DELEGATE, {}, ("agent_name", "prompt", "wait_for_previous"),
                     ("codebase_investigator", "a synthetic task", False)),
}
# Defined by the pinned package and never offered to a headless arm G model (R4), and names it does not define.
NOT_OFFERED = ("google_web_search", "web_fetch", "ask_user", "read_mcp_resource", "list_mcp_resources",
               "tracker_create_task", "tracker_update_task", "tracker_get_task", "tracker_list_tasks",
               "tracker_add_dependency", "tracker_visualize", "read_many_files", "get_internal_docs", "complete_task")
ABSENT = ("save_memory", "no_such_tool", "Bash", "shell")
SOURCE_KEYS = ("package", "version", "tarball_sha256", "file", "file_sha256", "lines", "kind_in_package", "view_kind",
               "read")


def ev(**kw) -> dict:
    return dict({"type": "tool_use", "timestamp": "2026-10-18T00:00:01.000Z", "tool_id": "t1"}, **kw)


def use_line(name, params) -> str:
    return json.dumps(ev(tool_name=name, parameters=params))


def check_refuses(rec) -> bool:
    try:
        tg.check_record(rec)
    except tg.ShapeError:
        return True
    return False


def parser_refuses(line) -> bool:
    try:
        tg.GeminiParser().items(line)
    except tv.ViewError:
        return True
    return False


def r1_problems() -> list:
    out = []
    params = dict(zip(*REGISTRY["update_topic"][2:4]))
    line = use_line("update_topic", params)
    if check_refuses(json.loads(line)):
        out.append("R1: check_record refuses a synthetic update_topic call")
    if parser_refuses(line):
        out.append("R1: GeminiParser refuses a synthetic update_topic call")
    else:
        item = tg.GeminiParser().items(line)[0]
        if (item.kind, item.tool, item.args) != (tv.TOOL_CALL, tv.OTHER, {}):
            out.append(f"R1: update_topic maps to {item.kind} {item.tool} {item.args}, not a tool-call of kind other")
    lines = (FIXTURES / "turn1-tools.jsonl").read_text().split("\n")
    lines = [x for x in lines if x.strip()]
    stream = lines[:-1] + [line, json.dumps({"type": "tool_result", "timestamp": "2026-10-18T00:00:02.000Z",
                                             "tool_id": "t1", "status": "success",
                                             "output": "Current topic: \"Synthetic chapter\""}), lines[-1]]
    try:
        got = ga.read_stream("\n".join(stream) + "\n", model=MODEL)
    except ga.StreamError as e:
        out.append(f"R1: read_stream refuses a synthetic stream carrying update_topic: {e}")
    else:
        if got["tool_ids"][-1:] != ["t1"]:
            out.append(f"R1: read_stream's tool ids are {got['tool_ids']}, not ending with the update_topic call")
    return out


def r2_problems() -> list:
    out = []
    table = tg.GEMINI_TOOLS
    if sorted(table) != sorted(REGISTRY):
        out.append(f"R2: the table's names differ from the registry's: missing {sorted(set(REGISTRY) - set(table))}, "
                   f"extra {sorted(set(table) - set(REGISTRY))}")
    for name, (kind, keymap, allowed, values) in REGISTRY.items():
        if name not in table:
            continue
        got_kind, got_map, got_allowed = table[name]
        if (got_kind, dict(got_map), tuple(sorted(got_allowed))) != (kind, keymap, tuple(sorted(allowed))):
            out.append(f"R2: {name} is {got_kind} {got_map} {sorted(got_allowed)}, not {kind} {keymap} "
                       f"{sorted(allowed)}")
            continue
        params = dict(zip(allowed, values))
        line = use_line(name, params)
        if check_refuses(json.loads(line)) or parser_refuses(line):
            out.append(f"R2: {name} with every allowed key is refused")
            continue
        item = tg.GeminiParser().items(line)[0]
        want = {view: params[raw] for raw, view in keymap.items()}
        if kind == tv.SEARCH:
            want.setdefault("path", None)
        if (item.tool, item.args) != (kind, want):
            out.append(f"R2: {name} maps to {item.tool} {item.args}, not {kind} {want}")
        defaulted = {tv.SHELL: ("background",), tv.SEARCH: ("path",)}.get(kind, ())
        for key in allowed:
            needed = {raw: params[raw] for raw, view in keymap.items()
                      if view in tv.ARG_SHAPES[kind] and view not in defaulted}
            alone = dict(needed, **{key: params[key]})
            if parser_refuses(use_line(name, alone)):
                out.append(f"R2: {name} with {sorted(alone)} is refused")
    return out


def r3_problems() -> list:
    out = []
    sources = getattr(gts, "SOURCES", None)
    if not isinstance(sources, dict):
        return ["R3: gemini_tool_sources carries no SOURCES"]
    if sorted(sources) != sorted(tg.GEMINI_TOOLS):
        out.append(f"R3: the sources name {sorted(sources)}, not the table's {sorted(tg.GEMINI_TOOLS)}")
    for name, src in sources.items():
        if not isinstance(src, dict) or set(src) != set(SOURCE_KEYS):
            out.append(f"R3: {name}'s source is not exactly {list(SOURCE_KEYS)}")
            continue
        if (src["package"], src["version"], src["tarball_sha256"]) != ("@google/gemini-cli", "0.64.0", TARBALL_SHA256):
            out.append(f"R3: {name}'s source is not the pinned package")
        if FILE_SHA256.get(src["file"]) != src["file_sha256"]:
            out.append(f"R3: {name}'s file {src['file']!r} is not a pinned bundle file with its sha256")
        lines = src["lines"]
        if not (isinstance(lines, list) and lines and all(
                isinstance(x, list) and len(x) == 3 and x[0] in FILE_SHA256 and isinstance(x[1], int)
                and not isinstance(x[1], bool) and x[1] > 0 and isinstance(x[2], str) and x[2].strip()
                for x in lines)):
            out.append(f"R3: {name}'s lines are not [[file, line, text], ...] in the pinned files")
        if name in tg.GEMINI_TOOLS and src["view_kind"] != tg.GEMINI_TOOLS[name][0]:
            out.append(f"R3: {name}'s source names view kind {src['view_kind']!r}, the table {tg.GEMINI_TOOLS[name][0]!r}")
        if not (isinstance(src["kind_in_package"], str) and src["kind_in_package"].startswith("Kind.")):
            out.append(f"R3: {name}'s package Kind is not a Kind word")
        if not (isinstance(src["read"], str) and src["read"].strip()):
            out.append(f"R3: {name}'s source says nothing of what was read")
    return out


def r4_problems() -> list:
    out = []
    for name in NOT_OFFERED + ABSENT:
        if name in tg.GEMINI_TOOLS:
            out.append(f"R4: {name} has an entry")
        line = use_line(name, {"query": "x"})
        if not check_refuses(json.loads(line)):
            out.append(f"R4: check_record accepts a {name} call")
        if not parser_refuses(line):
            out.append(f"R4: GeminiParser accepts a {name} call")
    for params in ({"file_path": "a.txt", "offset": 1}, {"file_path": "a.txt", "limit": 5},
                   {"file_path": "a.txt", "absolute_path": "/a"}):
        line = use_line("read_file", params)
        if not check_refuses(json.loads(line)) or not parser_refuses(line):
            out.append(f"R4: read_file with {sorted(params)} is accepted")
    if not parser_refuses(use_line("update_topic", {"strategic_intent": "x", "topic": "y"})):
        out.append("R4: update_topic with a key off its schema is accepted")
    return out


def source_problems(bundle: Path) -> list:
    """R5: every cited line of gemini_tool_sources.SOURCES, read from the unpacked package's files (never run or imported)."""
    out = []
    texts = {}
    for rel, want in FILE_SHA256.items():
        data = (Path(bundle).parent / rel).read_bytes()
        if hashlib.sha256(data).hexdigest() != want:
            out.append(f"R5: {rel} is not sha256 {want[:12]}")
        texts[rel] = data.decode("utf-8").split("\n")
    for name, src in getattr(gts, "SOURCES", {}).items():
        for rel, n, text in src["lines"]:
            got = texts[rel][n - 1] if 0 < n <= len(texts[rel]) else ""
            if text not in got:
                out.append(f"R5: {name}: {rel} line {n} does not hold {text!r} (it reads {got.strip()[:120]!r})")
    return out


class R1UpdateTopic(unittest.TestCase):
    def test_a_synthetic_update_topic_call_is_read(self):
        self.assertEqual(r1_problems(), [])


class R2Registry(unittest.TestCase):
    def test_the_table_is_the_pinned_registry(self):
        self.assertEqual(r2_problems(), [])


class R3Sources(unittest.TestCase):
    def test_every_entry_carries_its_source(self):
        self.assertEqual(r3_problems(), [])


class R4StillRefused(unittest.TestCase):
    def test_tools_not_offered_absent_or_off_schema_refuse(self):
        self.assertEqual(r4_problems(), [])


def witnesses() -> int:
    """Each table mutant, in this process: the table patched for the run (mock.patch.dict, restored), never written."""
    base = dict(tg.GEMINI_TOOLS)
    if r1_problems() + r2_problems() + r4_problems():
        print("witnesses: the unmutated table is not green; no witness is meaningful")
        return 1
    mutants = []
    for name, (kind, keymap, allowed) in base.items():
        mutants.append((f"{name}: removed", {k: v for k, v in base.items() if k != name}))
        other = tv.OTHER if kind != tv.OTHER else tv.READ
        mutants.append((f"{name}: kind {other}", dict(base, **{name: (other, keymap, allowed)})))
        for key in allowed:
            mutants.append((f"{name}: {key} dropped",
                            dict(base, **{name: (kind, keymap, tuple(k for k in allowed if k != key))})))
    for name in NOT_OFFERED + ABSENT:
        mutants.append((f"{name}: added", dict(base, **{name: (tv.OTHER, {}, ("query",))})))
    red = 0
    for label, table in mutants:
        with mock.patch.dict(tg.GEMINI_TOOLS, table, clear=True):
            got = r1_problems() + r2_problems() + r4_problems()
        print(f"witness {label}: {'RED' if got else 'SURVIVED'}", flush=True)
        red += bool(got)
    print(f"test_gemini_tool_registry witnesses: {red}/{len(mutants)} red")
    return 0 if red == len(mutants) else 1


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(witnesses())
    if "--sources" in sys.argv:
        found = source_problems(Path(sys.argv[sys.argv.index("--sources") + 1]))
        for p in found:
            print(p)
        print(f"test_gemini_tool_registry sources: {len(found)} problems over "
              f"{sum(len(s['lines']) for s in getattr(gts, 'SOURCES', {}).values())} cited lines")
        raise SystemExit(1 if found else 0)
    result = unittest.main(verbosity=2, exit=False).result
    print(f"test_gemini_tool_registry: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    raise SystemExit(0 if result.wasSuccessful() else 1)
