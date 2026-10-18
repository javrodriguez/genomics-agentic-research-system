#!/usr/bin/env python3
"""Lane vendor-admission T4 (plan v4 section 9, NIT 7): a piece's edited files are disjoint from the native readers'
source lists. Usage: check_vendor_sources.py <piece> <file> ...; each file is a path under evals/gap-study-4/. Exit 1
when a file is in native_reader_registration.READER_SOURCES or CODEX_SOURCES, except drive.py for piece P0, whose
edit A is the drive.py edit the plan rules (section 6), and for piece EB, edits B and C (glitch-b5 rounds 14 and 15,
review e-71a2b94 findings 1 and 2: the vendor turn envelopes, and their and the snapshots' sha256 rebound to the
scan's masked bytes). Piece EB naming drive.py also checks both edits' whole diff: each edit must be present, and
drive.py with edit B's lines (TakeDriver._take_records' first `if vendor:` branch after its first statement) and edit
C's lines (the one statement of TakeDriver.drive right after the drive scan's `if not _scan_record.passed(scan):`, an
`if` whose test requires the row's harness in VENDOR_HARNESSES, round 16) taken out must be, byte for byte, drive.py
before edit B (PRE_EDIT_B_DRIVE_SHA256, its text at f628e9d8), so no other drive.py line moves. Any such edit after
Javier's acceptance commit makes production_readers refuse, so a piece naming one is a red check, never a note."""

from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import native_reader_registration as nrr  # noqa: E402

PIECES = ("PF", "P0", "P0b", "P1", "P2", "P3", "P4", "P5", "EB")
ALLOWED = {"P0": {"drive.py"}, "EB": {"drive.py"}}
PRE_EDIT_B_DRIVE_SHA256 = "ea3917d4e4c1acc2078b1779bab0c6c47304aee920c8d2f2dc3423ec33934906"


def edit_b_span(src: str):
    """(first, last), the 1-based lines of edit B in drive.py's text: every line of TakeDriver._take_records' first
    `if vendor:` branch after the branch's first statement (its cross_check), or None when the branch holds that
    statement alone; raises ValueError when there is no such branch."""
    for cls in ast.parse(src).body:
        if isinstance(cls, ast.ClassDef) and cls.name == "TakeDriver":
            for fn in cls.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == "_take_records":
                    for node in fn.body:
                        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "vendor":
                            body = node.body
                            return (body[0].end_lineno + 1, body[-1].end_lineno) if len(body) > 1 else None
    raise ValueError("drive.py has no TakeDriver._take_records `if vendor:` branch")


def without_edit_b(src: str) -> str:
    """drive.py's text with edit B's lines taken out (before edit B, the text itself)."""
    return _cut(src, edit_b_span(src))


def _scan_check(node) -> bool:
    """Whether `node` is the drive scan's `if not _scan_record.passed(scan):`."""
    t = node.test if isinstance(node, ast.If) else None
    return (isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not) and isinstance(t.operand, ast.Call)
            and isinstance(t.operand.func, ast.Attribute) and t.operand.func.attr == "passed"
            and isinstance(t.operand.func.value, ast.Name) and t.operand.func.value.id == "_scan_record")


ROW_HARNESS = ast.dump(ast.parse('row["agent"]["harness"]', mode="eval").body)


def _requires_vendor(test) -> bool:
    """Whether an `if` test requires the row's harness to be in VENDOR_HARNESSES (glitch-b5 round 16, review f-981e871
    NIT 4): the test is `row["agent"]["harness"] in VENDOR_HARNESSES` itself or an `and` holding it as one operand, so
    every other operand only narrows it; a `not in`, a negation, an `or`, a widened set or another left side is not."""
    def member(t) -> bool:
        return (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.In)
                and ast.dump(t.left) == ROW_HARNESS
                and isinstance(t.comparators[0], ast.Name) and t.comparators[0].id == "VENDOR_HARNESSES")
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        return any(member(v) for v in test.values)
    return member(test)


def edit_c_span(src: str):
    """(first, last), the 1-based lines of edit C in drive.py's text: the one statement of TakeDriver.drive right after
    the drive scan's `if not _scan_record.passed(scan):`, when it is an `if` whose test requires the row's harness to be
    in VENDOR_HARNESSES (_requires_vendor), or None when it is not; raises ValueError when TakeDriver.drive holds no
    such scan check."""
    for cls in ast.parse(src).body:
        if isinstance(cls, ast.ClassDef) and cls.name == "TakeDriver":
            for fn in cls.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == "drive":
                    for k, node in enumerate(fn.body):
                        if _scan_check(node):
                            nxt = fn.body[k + 1] if k + 1 < len(fn.body) else None
                            if isinstance(nxt, ast.If) and _requires_vendor(nxt.test):
                                return (nxt.lineno, nxt.end_lineno)
                            return None
    raise ValueError("drive.py has no TakeDriver.drive `if not _scan_record.passed(scan):`")


def _cut(src: str, span) -> str:
    if span is None:
        return src
    lines = src.splitlines(keepends=True)
    return "".join(lines[:span[0] - 1] + lines[span[1]:])


def without_edit_c(src: str) -> str:
    """drive.py's text with edit C's lines taken out (before edit C, the text itself)."""
    return _cut(src, edit_c_span(src))


def without_edits(src: str) -> str:
    """drive.py's text with edits C and B taken out: C first, as it lies below B, so B's lines do not move."""
    return without_edit_b(without_edit_c(src))


def edit_b_problems(src: str) -> list:
    """Edits B and C, each present, and drive.py outside both their spans drive.py before edit B."""
    try:
        span, span_c = edit_b_span(src), edit_c_span(src)
    except (SyntaxError, ValueError) as e:
        return [f"edit B or C: {e}"]
    out = []
    if span is None:
        out.append("edit B: TakeDriver._take_records' vendor branch writes no turn envelopes (its one statement only)")
    if span_c is None:
        out.append("edit C: TakeDriver.drive rebinds nothing to the masked bytes right after the drive scan (no `if` "
                   "there whose test requires the row's harness in VENDOR_HARNESSES)")
    if out:
        return out
    if hashlib.sha256(without_edits(src).encode("utf-8")).hexdigest() != PRE_EDIT_B_DRIVE_SHA256:
        return [f"edits B and C: drive.py outside lines {span[0]}-{span[1]} (the vendor branch) and "
                f"{span_c[0]}-{span_c[1]} (after the drive scan) is not drive.py before edit B"]
    return []


def problems(piece: str, files: list) -> list:
    if piece not in PIECES:
        return [f"{piece!r} is not a piece of the plan ({', '.join(PIECES)})"]
    if not files:
        return [f"piece {piece} names no file"]
    listed = set(nrr.READER_SOURCES) | set(nrr.CODEX_SOURCES)
    out = [f"piece {piece} edits {f}, which is in READER_SOURCES or CODEX_SOURCES" for f in files
           if f in listed and f not in ALLOWED.get(piece, set())]
    out += [f"piece {piece} names {f}, which is not a file under evals/gap-study-4/" for f in files
            if not (HERE / f).is_file()]
    if piece == "EB" and "drive.py" in files and (HERE / "drive.py").is_file():
        out += edit_b_problems((HERE / "drive.py").read_text(encoding="utf-8"))
    return out


def main(argv) -> int:
    if not argv:
        print("usage: check_vendor_sources.py <piece> <file> ...")
        return 2
    bad = problems(argv[0], argv[1:])
    for b in bad:
        print(f"check_vendor_sources: REFUSE: {b}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
