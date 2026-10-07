#!/usr/bin/env python3
"""The awareness furniture check: which pre-registered phrases match the harness's own records.

    python3 evals/gap-study-4/awareness_furniture.py            round 3's committed transcripts
    python3 evals/gap-study-4/awareness_furniture.py FILE ...   the named transcript.jsonl files

The plan's gotcha for `graders/awareness.py`: "Grep the phrase list against a real transcript's
attachment records before freezing. Round 3 nearly voided takes on its own harness furniture." The
grader excludes `harness` events by kind; this check shows what that exclusion keeps out. It runs
`awareness.PHRASES` against the `harness` events of every transcript, read through the view's parser
for the take's harness (round 3's takes carry none, so `transcript_view.ROUND3_HARNESS`).

It reads each transcript twice through the view: once whole (so a transcript the view refuses fails
the check), then one line at a time, so each match has one raw record type, from
`transcript_view.harness_types`. A line the view maps to no harness record is skipped unread.

It prints only, per match row: the phrase, the raw record type, the file and a count, tab-separated;
then one closing line. It NEVER prints a matched line or any text around a match. It exits 0 when
every transcript was read (whatever it found), 1 when the view refused one or none was found.

Round 3's transcripts are opened in the working tree, read-only (the brief's named exception to
`git show`; `copy_manifest.py --check` pins `evals/gap-study-3` unchanged).

No model is called anywhere in this module. Standard library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import transcript_view as view  # noqa: E402
from graders import awareness  # noqa: E402

REPO = HERE.parent.parent
ROUND3_TRANSCRIPTS = REPO / "evals" / "gap-study-3" / "transcripts"


def round3_files() -> list[Path]:
    return sorted(ROUND3_TRANSCRIPTS.glob("*/*/*/*/transcript.jsonl"))


def furniture(harness: str, path: Path) -> dict[tuple[str, str], int]:
    """{(phrase, raw record type): count} over the harness events of one transcript."""
    view.events(harness, path)  # the whole file first: a refusal fails the check
    counts: dict[tuple[str, str], int] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        types = view.harness_types(harness, [line])
        if not types:
            continue
        if len(types) != 1:
            raise view.ViewError("one line mapped to more than one harness record type")
        raw_type = next(iter(types))
        for e in view.events(harness, [line]):
            if e.kind != view.HARNESS:
                continue
            for phrase in awareness.scan(e.text):
                counts[(phrase, raw_type)] = counts.get((phrase, raw_type), 0) + 1
    return counts


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    files = [Path(a) for a in args] if args else round3_files()
    if not files:
        print("awareness_furniture: no transcript found")
        return 1
    rows = 0
    for f in files:
        try:
            counts = furniture(view.ROUND3_HARNESS, f)
        except (view.ViewError, OSError) as e:
            print(f"awareness_furniture: {f}: refused: {type(e).__name__}")
            return 1
        try:
            name = f.resolve().relative_to(REPO)
        except ValueError:
            name = f
        for (phrase, raw_type), n in sorted(counts.items()):
            print(f"{phrase}\t{raw_type}\t{name}\t{n}")
            rows += 1
    print(f"awareness_furniture: {rows} match row(s) over {len(files)} transcript(s); "
          f"{len(awareness.PHRASES)} phrases; harness events only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
