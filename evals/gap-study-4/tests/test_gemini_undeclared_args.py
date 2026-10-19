#!/usr/bin/env python3
"""A model-invented argument key on a known Gemini tool, read as named, ignored input (lane vendor-b16 round 2;
glitch-26's ruling R-B16-2, Mon 19 Oct 2026; the Gemini practice walk held with StreamError "tool_use: tool
'grep_search': argument keys with no entry: ['file_path']").

The pinned Gemini CLI 0.64.0 runs such a call: Ajv passes a key the schema does not declare when the schema leaves its
properties open, the invocation never reads it, and the stream records the model's parameters verbatim with a success
result (lane-reports/B16-DESIGN-NOTE.md sections 2 and 4). transcript_gemini.OPEN_INPUT names the tools where both
hold; each entry is cited in gemini_tool_sources.OPEN_INPUT from the pinned package.

  U1  the held walk's shape, SYNTHETIC (grep_search with pattern and file_path, and the same on the legacy alias
      search_file_content): check_record passes it, GeminiParser reads a search call whose args are what ran (path
      None, the working directory), the item names the undeclared keys in the record's order (undeclared_args), a
      re-bound copy of the item keeps them (dataclasses.replace, as vendor_record_binding re-binds each ref), and
      gemini_adapter.read_stream reads a synthetic stream that carries the call.
  U2  still refused: an unknown tool name; a declared key off its type; a known tool with no OPEN_INPUT entry
      (read_file, update_topic, write_todos, whose schema closes its properties); an undeclared key the pinned run
      reads (wait_for_previous, read by the scheduler off every call); a tool whose entry says its schema closes its
      properties; a tool whose entry says the run reads the key. A call with no undeclared key is the plain view item.
  U3  every OPEN_INPUT entry is cited: gemini_tool_sources.OPEN_INPUT names exactly the table's tools, each with the
      pinned package and file sha256, closes_properties False and the read keys equal to the table's, and its lines
      as [file, line, text] in the pinned files.

`--witnesses` runs each mutant in this process, never written: the per-tool citation removed (U3 red), a closed schema
assumed (U1 red) and the name dropped from the view item (U1 red), each red alone. `--sources <the unpacked package's
bundle folder>` re-reads every cited line (on demand, never in the battery: the package is not in the repository).

Synthetic strings only: no recorded stream, no held take's bytes, no model, network or vendor package is read by the
battery. Standard library only.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import types
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
# The held walk's shape, synthetic: a pattern the model meant for one file, and the file it named.
HELD = {"pattern": "synthetic_marker", "file_path": "synthetic/notes.txt"}
OPEN_TOOLS = ("grep_search", "search_file_content")
CITATION_KEYS = ("package", "version", "tarball_sha256", "file", "file_sha256", "closes_properties", "reads", "lines",
                 "read")


def ev(**kw) -> dict:
    return dict({"type": "tool_use", "timestamp": "2026-10-19T00:00:01.000Z", "tool_id": "t1"}, **kw)


def use_line(name, params) -> str:
    return json.dumps(ev(tool_name=name, parameters=params))


def refused(mod, line) -> bool:
    try:
        mod.check_record(json.loads(line))
        mod.GeminiParser().items(line)
    except tv.ViewError:
        return True
    return False


def stream_with(line) -> str:
    lines = [x for x in (FIXTURES / "turn1-tools.jsonl").read_text().split("\n") if x.strip()]
    result = json.dumps({"type": "tool_result", "timestamp": "2026-10-19T00:00:02.000Z", "tool_id": "t1",
                         "status": "success", "output": "No matches found"})
    return "\n".join(lines[:-1] + [line, result, lines[-1]]) + "\n"


def u1_problems(mod=tg) -> list:
    out = []
    for name in OPEN_TOOLS:
        line = use_line(name, HELD)
        try:
            mod.check_record(json.loads(line))
            items = mod.GeminiParser().items(line)
        except tv.ViewError as e:
            out.append(f"U1: {name} with {sorted(HELD)} is refused: {e}")
            continue
        item = items[0]
        if (len(items), item.kind, item.tool, item.args) != (1, tv.TOOL_CALL, tv.SEARCH,
                                                              {"pattern": HELD["pattern"], "path": None}):
            out.append(f"U1: {name} reads as {item.kind} {item.tool} {item.args}, not the search that ran")
        if getattr(item, "undeclared_args", None) != ("file_path",):
            out.append(f"U1: {name}'s view item does not name the undeclared key: "
                       f"{getattr(item, 'undeclared_args', None)!r}")
        elif getattr(dataclasses.replace(item, ref="1:t1"), "undeclared_args", None) != ("file_path",):
            out.append(f"U1: {name}'s re-bound item drops the undeclared key")
        for params, want in (({"include": "*.txt", "pattern": "p", "file_path": "a.txt"}, ("include", "file_path")),
                             ({"file_path": "a.txt", "pattern": "p", "include": "*.txt"}, ("file_path", "include"))):
            try:
                got = getattr(mod.GeminiParser().items(use_line(name, params))[0], "undeclared_args", None)
            except tv.ViewError as e:
                got = f"refused: {e}"
            if got != want:
                out.append(f"U1: {name} with {list(params)} names {got!r}, not {want!r} in the record's order")
        try:
            got = ga.read_stream(stream_with(line), model=MODEL)
        except ga.StreamError as e:
            out.append(f"U1: read_stream refuses a synthetic stream carrying {name} with file_path: {e}")
        else:
            if got["tool_ids"][-1:] != ["t1"]:
                out.append(f"U1: read_stream's tool ids are {got['tool_ids']}, not ending with the {name} call")
    return out


def u2_problems(mod=tg) -> list:
    out = []
    cases = [
        ("an unknown tool name", use_line("grep_files", HELD)),
        ("a declared, mapped key off its type (pattern)", use_line("grep_search", dict(HELD, pattern=5))),
        ("a declared, mapped key off its type (dir_path)", use_line("grep_search", dict(HELD, dir_path=7))),
        ("a known tool with no entry (read_file)",
         use_line("read_file", {"file_path": "a.txt", "absolute_path": "/a"})),
        ("a known tool with no entry (update_topic)", use_line("update_topic", {"title": "t", "topic": "y"})),
        ("a closed schema (write_todos)", use_line("write_todos", {"todos": [], "file_path": "a.txt"})),
        ("a key the run reads (wait_for_previous)", use_line("grep_search", dict(HELD, wait_for_previous=True))),
    ]
    for what, line in cases:
        if not refused(mod, line):
            out.append(f"U2: {what} is accepted")
    table = getattr(mod, "OPEN_INPUT", None)
    if not isinstance(table, dict) or "grep_search" not in table:
        return out + ["U2: transcript_gemini carries no OPEN_INPUT entry for grep_search"]
    reads = table["grep_search"][1]
    line = use_line("grep_search", HELD)
    with mock.patch.dict(table, {"grep_search": (True, reads)}):
        if not refused(mod, line):
            out.append("U2: grep_search with file_path is accepted under an entry whose schema closes its properties")
    with mock.patch.dict(table, {"grep_search": (False, tuple(reads) + ("file_path",))}):
        if not refused(mod, line):
            out.append("U2: grep_search with file_path is accepted under an entry whose run reads file_path")
    with mock.patch.dict(table, {"write_todos": (True, ("todos",))}):
        if not refused(mod, use_line("write_todos", {"todos": [], "file_path": "a.txt"})):
            out.append("U2: write_todos with an undeclared key is accepted under a closed-schema entry")
    plain = mod.GeminiParser().items(use_line("grep_search", {"pattern": "p"}))[0]
    if type(plain) is not tv.RawItem:
        out.append(f"U2: a call with no undeclared key is a {type(plain).__name__}, not the plain view item")
    return out


def u3_problems(mod=tg, src=gts) -> list:
    out = []
    table = getattr(mod, "OPEN_INPUT", None)
    cited = getattr(src, "OPEN_INPUT", None)
    if not isinstance(table, dict) or not isinstance(cited, dict):
        return ["U3: OPEN_INPUT is missing from transcript_gemini or gemini_tool_sources"]
    if sorted(table) != sorted(OPEN_TOOLS):
        out.append(f"U3: the table names {sorted(table)}, not {sorted(OPEN_TOOLS)}")
    if sorted(cited) != sorted(table):
        out.append(f"U3: the citations name {sorted(cited)}, not the table's {sorted(table)}")
    for name, (closes, reads) in table.items():
        if name not in mod.GEMINI_TOOLS:
            out.append(f"U3: {name} has an OPEN_INPUT entry and no GEMINI_TOOLS entry")
        c = cited.get(name)
        if not isinstance(c, dict) or set(c) != set(CITATION_KEYS):
            out.append(f"U3: {name}'s citation is not exactly {list(CITATION_KEYS)}")
            continue
        if (c["package"], c["version"], c["tarball_sha256"]) != ("@google/gemini-cli", "0.64.0", TARBALL_SHA256):
            out.append(f"U3: {name}'s citation is not the pinned package")
        if FILE_SHA256.get(c["file"]) != c["file_sha256"]:
            out.append(f"U3: {name}'s file {c['file']!r} is not a pinned bundle file with its sha256")
        if c["closes_properties"] is not False or closes is not False:
            out.append(f"U3: {name}: the citation says closes_properties {c['closes_properties']!r}, the table "
                       f"{closes!r}; an entry stands only on an open schema")
        if sorted(c["reads"]) != sorted(reads):
            out.append(f"U3: {name}: the citation's read keys {sorted(c['reads'])} are not the table's {sorted(reads)}")
        lines = c["lines"]
        if not (isinstance(lines, list) and lines and all(
                isinstance(x, list) and len(x) == 3 and x[0] in FILE_SHA256 and type(x[1]) is int and x[1] > 0
                and isinstance(x[2], str) and x[2].strip() for x in lines)):
            out.append(f"U3: {name}'s lines are not [[file, line, text], ...] in the pinned files")
        if not (isinstance(c["read"], str) and c["read"].strip()):
            out.append(f"U3: {name}'s citation says nothing of what was read")
    return out


def source_problems(bundle: Path) -> list:
    """Every cited line of gemini_tool_sources.OPEN_INPUT, read from the unpacked package (never run or imported)."""
    out, texts = [], {}
    for rel, want in FILE_SHA256.items():
        data = (Path(bundle).parent / rel).read_bytes()
        if hashlib.sha256(data).hexdigest() != want:
            out.append(f"sources: {rel} is not sha256 {want[:12]}")
        texts[rel] = data.decode("utf-8").split("\n")
    for name, c in getattr(gts, "OPEN_INPUT", {}).items():
        for rel, n, text in c["lines"]:
            got = texts[rel][n - 1] if 0 < n <= len(texts[rel]) else ""
            if text not in got:
                out.append(f"sources: {name}: {rel} line {n} does not hold {text!r} (it reads {got.strip()[:120]!r})")
    return out


class U1HeldShape(unittest.TestCase):
    def test_the_held_walks_shape_is_read_with_the_key_named(self):
        self.assertEqual(u1_problems(), [])


class U2StillRefused(unittest.TestCase):
    def test_unknown_off_type_uncited_closed_and_read_keys_refuse(self):
        self.assertEqual(u2_problems(), [])


class U3Cited(unittest.TestCase):
    def test_every_entry_is_cited_from_the_pinned_package(self):
        self.assertEqual(u3_problems(), [])


# ---- R-B16-2 witnesses, in this process, never written; each must turn its battery red ------------------------------
VIEW_ANCHOR = "undeclared_args=ignored"


def _view_mutant():
    path = Path(tg.__file__)
    text = path.read_text(encoding="utf-8")
    if text.count(VIEW_ANCHOR) != 1:
        return None
    mod = types.ModuleType("transcript_gemini_b16_witness")
    mod.__file__ = str(path)
    sys.modules[mod.__name__] = mod                  # dataclass reads its module's namespace while it builds
    try:
        exec(compile(text.replace(VIEW_ANCHOR, "undeclared_args=()"), str(path) + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(mod.__name__, None)
    return mod


def witnesses() -> int:
    if u1_problems() + u2_problems() + u3_problems():
        print("witnesses: the unmutated reader is not green; no witness is meaningful")
        return 1
    red, total = 0, 3
    with mock.patch.dict(gts.OPEN_INPUT):
        del gts.OPEN_INPUT["grep_search"]
        got, others = u3_problems(), u1_problems() + u2_problems()
    print(f"witness citation-removed: {'RED' if got else 'SURVIVED'}{' (not alone)' if others else ''}"
          + (f": {got[0]}" if got else ""))
    red += bool(got) and not others
    reads = tg.OPEN_INPUT["grep_search"][1]
    with mock.patch.dict(tg.OPEN_INPUT, {"grep_search": (True, reads)}):
        got = u1_problems()
    print(f"witness closed-schema-assumed: {'RED' if got else 'SURVIVED'}" + (f": {got[0]}" if got else ""))
    red += bool(got)
    mod = _view_mutant()
    if mod is None:
        print(f"NOT PERFORMED name-dropped-from-view: {VIEW_ANCHOR!r} does not occur once in transcript_gemini.py")
    else:
        got, others = u1_problems(mod), u3_problems(mod)
        print(f"witness name-dropped-from-view: {'RED' if got else 'SURVIVED'}{' (not alone)' if others else ''}"
              + (f": {got[0]}" if got else ""))
        red += bool(got) and not others
    print(f"test_gemini_undeclared_args witnesses: {red}/{total} red")
    return 0 if red == total else 1


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(witnesses())
    if "--sources" in sys.argv:
        found = source_problems(Path(sys.argv[sys.argv.index("--sources") + 1]))
        for p in found:
            print(p)
        print(f"test_gemini_undeclared_args sources: {len(found)} problems over "
              f"{sum(len(c['lines']) for c in getattr(gts, 'OPEN_INPUT', {}).values())} cited lines")
        raise SystemExit(1 if found else 0)
    result = unittest.main(verbosity=2, exit=False).result
    print(f"test_gemini_undeclared_args: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    raise SystemExit(0 if result.wasSuccessful() else 1)
