#!/usr/bin/env python3
"""Lane vendor-admission T4 (plan v4 section 9, NIT 7): a piece's edited files are disjoint from the native readers'
source lists. Usage: check_vendor_sources.py <piece> <file> ...; each file is a path under evals/gap-study-4/. Exit 1
when a file is in native_reader_registration.READER_SOURCES or CODEX_SOURCES, except drive.py for piece P0, whose
edit A is the one drive.py edit the plan rules (section 6). Any such edit after Javier's acceptance commit makes
production_readers refuse, so a piece naming one is a red check, never a note."""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import native_reader_registration as nrr  # noqa: E402

PIECES = ("PF", "P0", "P0b", "P1", "P2", "P3", "P4", "P5")
ALLOWED = {"P0": {"drive.py"}}


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
