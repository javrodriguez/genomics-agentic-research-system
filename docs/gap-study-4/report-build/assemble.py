#!/usr/bin/env python3
"""REPORT.src.md with each include marker replaced by its generated table -> REPORT.md."""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parent      # docs/gap-study-4/report-build (build/fragments/)
DOC = ROOT.parent                          # docs/gap-study-4 (REPORT.src.md, REPORT.md)
src = (DOC / "REPORT.src.md").read_text()
used = []
def sub(m):
    used.append(m.group(1))
    return (ROOT / "build" / "fragments" / f"{m.group(1)}.md").read_text().rstrip("\n")
out = re.sub(r"<!-- include:([a-z_]+) -->", sub, src)
(DOC / "REPORT.md").write_text(out)
have = {p.stem for p in (ROOT / "build" / "fragments").glob("*.md")}
print(f"REPORT.md written: {len(out.splitlines())} lines, {len(used)} tables; fragments not used: {sorted(have - set(used))}")
