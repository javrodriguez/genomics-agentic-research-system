#!/usr/bin/env python3
"""Lane vendor-settle stage K: the shared plant helper for the settled vendor rows' firing cases (design
plans/gap-study-round-4/vendor-settle-DESIGN-2026-10-21.md section 2, "Firing case (F3)"; review
REVIEW-vendor-settle-DESIGN-2026-10-21.md section 3, stage K).

A firing case is ONE planted violation on a scratch copy of a RECORDED take folder (tests/fixtures/recorded-<harness>-
<walk>/, a byte copy of a committed walk folder). The committed fixture is never written: `planted` copies the files
its PROVENANCE.json lists (README.md and PROVENANCE.json stay behind, so the scratch folder holds a walk folder's files
only) to <scratch>/rehearsals/<walk>/, applies the case's edits there, and then re-binds every digest the driver wrote
over an edited file, so the plant reaches the row's reader instead of being refused by the binding first:

  - a turn stream (turn-<k>.jsonl): its envelope's "sha256" in transcript.jsonl;
  - a retained native snapshot (session/<file>): its driver-ledger.json native_snapshots[i].sha256;
  - environment.json: driver-ledger.json environment.sha256.

Each re-bind replaces the old digest's exact text in its binding file (it must occur there exactly once), so no other
byte of the binding file moves. Editing a binding file itself (transcript.jsonl, driver-ledger.json) is allowed; the
re-bind then runs on the edited bytes.

Edits are callables edit(folder) -> None. Three builders cover the usual plants, each refusing an edit that would be
silent or ambiguous:

  replace_bytes(rel, old, new, count=1)   exact text replaced; `old` must occur exactly `count` times (one logical
                                          event written into every copy that records it uses count=n, never a
                                          blanket replace)
  edit_jsonl(rel, fn)                     fn(index, record) returns a new record for a changed line or None; each
                                          changed line is re-serialised in the very style the original line was
                                          written in (one of four json.dumps styles that reproduces it byte for byte;
                                          a line no style reproduces refuses), every other line keeps its bytes
  insert_jsonl(rel, index, record)        one record inserted before line `index`, in its neighbour's style

`planted` refuses a plant that changes no byte (a hollow firing case). It yields a Plant: the scratch transcript.jsonl
(the path a site is called with), the folder, the files the edits changed and the bindings re-bound.

`added_lines(clean, planted)` and `plant_scope_problems(clean, planted, reason, siblings)` are VP-plant-scope: the
lines a plant adds to a site's (or vendor_check's) problems are non-empty and each carries the row's reason id or a
declared sibling's.

No take, model, container or network; nothing outside the scratch folder is written.
"""

from __future__ import annotations

import collections
import contextlib
import dataclasses
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FIXTURES = HERE / "tests" / "fixtures"
PROVENANCE = "PROVENANCE.json"
TRANSCRIPT = "transcript.jsonl"
LEDGER = "driver-ledger.json"
ENVIRONMENT = "environment.json"
# The json.dumps styles the CLIs and the driver write lines in; the non-ASCII ones first, so a line holding no
# non-ASCII text (which both spellings reproduce) is rewritten as the writer that kept non-ASCII raw would write it.
STYLES = (("compact, raw non-ASCII", {"separators": (",", ":"), "ensure_ascii": False}),
          ("default, raw non-ASCII", {"ensure_ascii": False}),
          ("compact", {"separators": (",", ":")}),
          ("default", {}))
_REASON = re.compile(r"^\[([a-z0-9-]+)\] ")


class PlantRefused(AssertionError):
    """The plant cannot be made as asked (hollow, ambiguous, or off the fixture's shape)."""


@dataclasses.dataclass
class Plant:
    path: Path              # the scratch copy's transcript.jsonl
    folder: Path            # the scratch walk folder, <scratch>/rehearsals/<walk>
    changed: tuple          # the walk-relative files the edits changed
    rebound: tuple          # (binding file, what it binds) for every digest re-bound


def fixture_folder(fixture) -> Path:
    """A RECORDED fixture folder from its folder name, its folder path, or any file inside it (the "<folder>/<file>"
    a SAME row names, resolved under tests/fixtures)."""
    p = Path(fixture)
    if not p.is_absolute():
        p = FIXTURES / p
    if p.is_file():
        p = p.parent
    if not (p / PROVENANCE).is_file():
        raise PlantRefused(f"{p} is no RECORDED fixture folder (it holds no {PROVENANCE})")
    return p


def provenance(fixture) -> dict:
    return json.loads((fixture_folder(fixture) / PROVENANCE).read_text(encoding="utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def _style(line: bytes) -> dict:
    rec = json.loads(line)
    for _, kw in STYLES:
        if json.dumps(rec, **kw).encode("utf-8") == line:
            return kw
    raise PlantRefused(f"no json.dumps style reproduces the line {line[:80]!r}, so it cannot be rewritten in place")


def _lines(data: bytes) -> tuple:
    if not data.endswith(b"\n"):
        raise PlantRefused("a JSONL file that does not end in a newline is not rewritten")
    return data[:-1].split(b"\n")


def replace_bytes(rel: str, old, new, count: int = 1):
    """An edit replacing the exact text `old` with `new` in walk-relative file `rel`; `old` must occur exactly
    `count` times."""
    old_b = old.encode("utf-8") if isinstance(old, str) else old
    new_b = new.encode("utf-8") if isinstance(new, str) else new

    def edit(folder: Path) -> None:
        f = folder / rel
        data = f.read_bytes()
        n = data.count(old_b)
        if n != count:
            raise PlantRefused(f"{rel}: the planted text occurs {n} time(s), not {count}: {old_b[:80]!r}")
        f.write_bytes(data.replace(old_b, new_b))
    return edit


def edit_jsonl(rel: str, fn):
    """An edit calling fn(index, record) on each line of walk-relative JSONL file `rel`; a returned record replaces
    the line in the original line's own style, None keeps the line's bytes."""
    def edit(folder: Path) -> None:
        f = folder / rel
        out = []
        for i, line in enumerate(_lines(f.read_bytes())):
            got = fn(i, json.loads(line))
            out.append(line if got is None else json.dumps(got, **_style(line)).encode("utf-8"))
        f.write_bytes(b"\n".join(out) + b"\n")
    return edit


def insert_jsonl(rel: str, index: int, record):
    """An edit inserting `record` before line `index` of walk-relative JSONL file `rel`, in the style of the line it
    lands before (or the last line's, at the end)."""
    def edit(folder: Path) -> None:
        f = folder / rel
        lines = list(_lines(f.read_bytes()))
        if not 0 <= index <= len(lines):
            raise PlantRefused(f"{rel}: no line {index} to insert before ({len(lines)} lines)")
        style = _style(lines[min(index, len(lines) - 1)])
        lines.insert(index, json.dumps(record, **style).encode("utf-8"))
        f.write_bytes(b"\n".join(lines) + b"\n")
    return edit


def _rebind_one(folder: Path, binding: str, old: str, new: str) -> None:
    f = folder / binding
    data = f.read_text(encoding="utf-8")
    if data.count(old) != 1:
        raise PlantRefused(f"{binding}: the digest {old} occurs {data.count(old)} time(s), not once")
    f.write_text(data.replace(old, new), encoding="utf-8")


def rebind(folder: Path) -> list:
    """Re-bind every digest the driver wrote over a file of the walk folder whose bytes no longer match it; returns
    [(binding file, what it binds)]."""
    out = []
    for line in _lines((folder / TRANSCRIPT).read_bytes()):
        env = json.loads(line)
        if not (isinstance(env, dict) and isinstance(env.get("stream"), str) and isinstance(env.get("sha256"), str)):
            continue
        new = _sha((folder / env["stream"]).read_bytes())
        if new != env["sha256"]:
            _rebind_one(folder, TRANSCRIPT, env["sha256"], new)
            out.append((TRANSCRIPT, env["stream"]))
    ledger = json.loads((folder / LEDGER).read_text(encoding="utf-8"))
    bound = [(f"session/{s['file']}", s["sha256"]) for s in ledger.get("native_snapshots") or []]
    env = ledger.get("environment")
    if isinstance(env, dict) and isinstance(env.get("file"), str):
        bound.append((env["file"], env.get("sha256")))
    for rel, old in bound:
        new = _sha((folder / rel).read_bytes())
        if new != old:
            _rebind_one(folder, LEDGER, old, new)
            out.append((LEDGER, rel))
    return out


@contextlib.contextmanager
def planted(fixture, *edits, rebind_digests: bool = True):
    """A scratch copy of the RECORDED fixture with `edits` applied and its digests re-bound; yields a Plant. With no
    edits it is the clean copy; with edits that change no byte it refuses (a hollow plant). `rebind_digests=False`
    leaves the bindings as written (a case proving a binding is read)."""
    src = fixture_folder(fixture)
    prov = provenance(src)
    with tempfile.TemporaryDirectory(prefix="vendor-plant-") as tmp:
        folder = Path(tmp) / "rehearsals" / prov["walk"]
        for rel in prov["files"]:
            (folder / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / rel, folder / rel)
        before = _snapshot(folder)
        for edit in edits:
            edit(folder)
        after = _snapshot(folder)
        changed = tuple(sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k)))
        if edits and not changed:
            raise PlantRefused(f"the plant on {src.name} changed no byte: a firing case on it would be hollow")
        rebound = tuple(rebind(folder)) if rebind_digests else ()
        yield Plant(path=folder / TRANSCRIPT, folder=folder, changed=changed, rebound=rebound)


def reason_of(line: str):
    m = _REASON.match(line) if isinstance(line, str) else None
    return m.group(1) if m else None


def added_lines(clean: list, planted_lines: list) -> list:
    """The lines `planted_lines` holds beyond `clean`, counted as multisets, in their order."""
    left = collections.Counter(clean)
    out = []
    for line in planted_lines:
        if left[line]:
            left[line] -= 1
        else:
            out.append(line)
    return out


def plant_scope_problems(clean: list, planted_lines: list, reason: str, siblings=()) -> list:
    """VP-plant-scope: [] when the plant adds at least one line, each carrying `reason` or a declared sibling reason,
    and removes none; else each problem."""
    added = added_lines(clean, planted_lines)
    out = [] if added else [f"the plant adds no problem line (expected [{reason}])"]
    if not any(reason_of(x) == reason for x in added):
        out.append(f"no added line carries [{reason}]: {added}")
    allowed = {reason, *siblings}
    out += [f"an added line carries an undeclared reason: {x}" for x in added if reason_of(x) not in allowed]
    removed = added_lines(planted_lines, clean)
    out += [f"the plant removed a clean line: {x}" for x in removed]
    return out
