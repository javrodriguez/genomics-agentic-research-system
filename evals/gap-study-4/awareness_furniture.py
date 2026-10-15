#!/usr/bin/env python3
"""The awareness furniture check: which pre-registered phrases match the harness's own records.

    python3 evals/gap-study-4/awareness_furniture.py            round 3's committed transcripts
    python3 evals/gap-study-4/awareness_furniture.py FILE ...   the named transcript.jsonl files

The plan's gotcha for `graders/awareness.py`: "Grep the phrase list against a real transcript's
attachment records before freezing. Round 3 nearly voided takes on its own harness furniture." The
grader excludes `harness` events by kind; this check shows what that exclusion keeps out. It runs
`awareness.PHRASES` against the `harness` events of every transcript, read through the view's parser
for the take's harness (round 3's takes carry none, so `transcript_view.ROUND3_HARNESS`).

It reads each transcript twice through the view, both times whole: once for its events (so a transcript the view
refuses fails the check), then for its raw items (`transcript_view.raw_items`), so each match has its one raw record
type. Only `harness` items are scanned. Item G (glitch-6b, 15 Oct 2026): it used to read the second pass one line at a
time, and a scheduled-wakeup line read alone has no earlier ScheduleWakeup call, so the check refused a w006-shaped
take the view reads.

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
    for it in view.raw_items(harness, path):
        if it.kind != view.HARNESS:
            continue
        for phrase in awareness.scan(it.text):
            counts[(phrase, it.raw_type)] = counts.get((phrase, it.raw_type), 0) + 1
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
