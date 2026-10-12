#!/usr/bin/env python3
"""Generated, exhaustive mutation over the CP6 walk road (lane w10-walk-runner, ruling w10-R3-fold). Stdlib only.

Three review rounds each found a guard on the walk road that could be weakened with every test green, each time in a
shape the previous fold's hand-written list had not named. So the mutants are generated from the code: for every
function on the walk road (ROAD), every

  delete     statement, replaced by `pass` (a docstring and an existing `pass` aside);
  cond-true  / cond-false   `if` or `while` condition, replaced by True and by False;
  drop-N     operand N of an `and` / `or`, dropped;
  negate     comparison, wrapped in `not (...)`;
  empty      assignment's right-hand side (=, :=-free annotated, +=), replaced by an empty value of its kind
             (a list, dict, set, tuple, string or number literal's empty or zero, a slice's [], a call to a builtin
             container's empty one, a boolean's opposite; anything else None; a None right-hand side is skipped).

Each mutant is spliced into the module's own bytes at the node's source position, so every other byte, comment and
line of the file is unchanged, and the file still compiles (a mutant that does not compile is dropped and counted).
A mutant's id names its module, function, kind, line relative to the function, column and a short hash of the text
it replaces and the text it puts there, so it is stable while that function's text is, and goes when it changes.

tests/test_walk_runner.py runs them (`--generated-mutants`, `--shard i/n`, `--sample k`) and keeps the EQUIVALENT
allow-list; this file only generates.
"""
from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# The walk road: ruling w10-R3-fold's list, plus the helpers they call that exist only for walks. Shared take-and-walk
# code (record_kind, take_checker, TakeDriver, WalkRepo's commit step, walk_launch_problems from lane w9) is bound by
# its own lanes' suites and is not mutated here.
ROAD = {
    "check_take": ("walk_session_id", "check_walk", "check4_walk"),
    "drive": ("walk_identity_problems", "walk_files"),
    "run": ("died_before_turn_one", "grade_walk", "walk_row"),
    "walk_runner": ("driver_namespace", "walk_entry", "check_record", "write_check", "_record", "clean_drive",
                    "_publish", "_remove", "run_one", "_run_one", "run_walks", "main"),
}
EMPTY_CALLS = {"list": "[]", "dict": "{}", "set": "set()", "tuple": "()", "str": '""', "sorted": "[]"}


@dataclass(frozen=True)
class Mutant:
    id: str
    module: str
    function: str
    kind: str
    line: int          # absolute line in the module, for the report
    original: str
    replacement: str
    start: int         # byte offsets of the replaced span in the module's UTF-8 bytes
    end: int

    def source(self, text: str) -> str:
        raw = text.encode("utf-8")
        return (raw[:self.start] + self.replacement.encode("utf-8") + raw[self.end:]).decode("utf-8")


def _offsets(raw: bytes) -> list[int]:
    starts = [0]
    for line in raw.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _span(starts, node) -> tuple[int, int]:
    return starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset


def _empty(value: ast.AST) -> str | None:
    if isinstance(value, (ast.List, ast.ListComp)):
        return "[]"
    if isinstance(value, (ast.Dict, ast.DictComp)):
        return "{}"
    if isinstance(value, (ast.Set, ast.SetComp)):
        return "set()"
    if isinstance(value, ast.Tuple):
        return "()"
    if isinstance(value, ast.JoinedStr):
        return '""'
    if isinstance(value, ast.Constant):
        v = value.value
        if v is None:
            return None
        if isinstance(v, bool):
            return "False" if v else "True"
        if isinstance(v, str):
            return '""'
        if isinstance(v, bytes):
            return 'b""'
        if isinstance(v, (int, float)):
            return "1" if v == 0 else "0"
        return None
    if isinstance(value, ast.Subscript) and isinstance(value.slice, ast.Slice):
        return "[]"
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in EMPTY_CALLS:
        return EMPTY_CALLS[value.func.id]
    return "None"


def _statements(body):
    for st in body:
        yield st
        for field in ("body", "orelse", "finalbody"):
            yield from _statements(getattr(st, field, []) or [])
        for handler in getattr(st, "handlers", []) or []:
            yield from _statements(handler.body)


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    found = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        raise LookupError(f"no single top-level def {name}")
    return found[0]


def generate_module(module: str, text: str | None = None) -> tuple[list[Mutant], int]:
    """(mutants of every ROAD function in `module`, how many generated texts did not compile and were dropped)."""
    text = (HERE / f"{module}.py").read_text() if text is None else text
    raw = text.encode("utf-8")
    starts = _offsets(raw)
    tree = ast.parse(text)
    out, dropped = [], 0
    for fname in ROAD[module]:
        fn = _function(tree, fname)
        body = fn.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]
        cands = []
        for st in _statements(body):
            if not isinstance(st, ast.Pass):
                cands.append(("delete", st, "pass"))
            if isinstance(st, (ast.If, ast.While)):
                cands.append(("cond-true", st.test, "True"))
                cands.append(("cond-false", st.test, "False"))
            if isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and st.value is not None:
                rep = _empty(st.value)
                if rep is not None:
                    cands.append(("empty", st.value, rep))
        for node in ast.walk(fn):
            if isinstance(node, ast.BoolOp):
                joiner = " and " if isinstance(node.op, ast.And) else " or "
                segs = [raw[slice(*_span(starts, v))].decode("utf-8") for v in node.values]
                for i in range(len(segs)):
                    rest = segs[:i] + segs[i + 1:]
                    cands.append((f"drop-{i}", node, "(" + joiner.join(rest) + ")"))
            elif isinstance(node, ast.Compare):
                seg = raw[slice(*_span(starts, node))].decode("utf-8")
                cands.append(("negate", node, f"(not ({seg}))"))
        seen = set()
        for kind, node, rep in cands:
            a, b = _span(starts, node)
            orig = raw[a:b].decode("utf-8")
            if rep == orig:
                continue
            h = hashlib.sha1(f"{orig}\0{rep}".encode()).hexdigest()[:8]
            mid = f"{module}.{fname}:{kind}:L{node.lineno - fn.lineno}:C{node.col_offset}:{h}"
            if mid in seen:
                continue
            seen.add(mid)
            m = Mutant(mid, module, fname, kind, node.lineno, orig, rep, a, b)
            try:
                compile(m.source(text), f"{module}.py (mutant)", "exec")
            except SyntaxError:
                dropped += 1
                continue
            out.append(m)
    return out, dropped


def generate() -> tuple[list[Mutant], int]:
    """Every mutant of the walk road, in a fixed order, and how many were dropped for not compiling."""
    allm, dropped = [], 0
    for module in ROAD:
        got, d = generate_module(module)
        allm += got
        dropped += d
    return allm, dropped


def by_id() -> dict:
    return {m.id: m for m in generate()[0]}


if __name__ == "__main__":
    ms, dropped = generate()
    from collections import Counter
    print(f"generated {len(ms)} mutants ({dropped} dropped for not compiling)")
    for (mod, kind), n in sorted(Counter((m.module, m.kind.split('-')[0]) for m in ms).items()):
        print(f"  {mod:12} {kind:7} {n}")
