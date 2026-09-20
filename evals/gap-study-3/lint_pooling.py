#!/usr/bin/env python3
"""Refuse any sentence that adds two instruments together. NO EXCUSAL PATH.

    python3 evals/gap-study-3/lint_pooling.py <path> [<path> ...]
    python3 evals/gap-study-3/lint_pooling.py --commits-since <sha> [--at <sha>]   # commit BODIES
    python3 evals/gap-study-3/lint_pooling.py --list-patterns

WHY THIS FILE EXISTS AND WHY IT IS NOT AN EDIT TO lint_language.py. Round 2's language linter is copied
here byte-identical, because a study that may change its instrument between rounds is not measuring the
same thing twice. It has no pooling pattern -- round 2 had nothing to pool with, having published round
1's counts beside its own under a heading and never in one figure. Round 3 does: its three tasks were
measured in round 2 too, under a different permission condition, and the single most attractive wrong
sentence anyone could write about this round is one that adds the two together. So the guard is a file
of round 3's own, run beside the copied one, and the copied one stays as it was.

NO EXCUSAL PATH, DELIBERATELY. lint_language.py can excuse a line somebody has read, because a blunt
word pattern fires on honest prose. These patterns do not need that relief: the words below have no
honest use in this study's published files, and the way past a finding is to write the sentence
differently. There is no allowlist, no flag and no per-line ruling, and adding one would be the exact
shape of the mistake this guard exists to prevent.

WHAT IT DOES NOT DO, SAID PLAINLY. The rule "every `k of n` has n = 3" is a rule about the result's
cells, and a text pattern cannot tell a cell count from `slice 4 of 20` or `graded 54 of 54`, both of
which this study is required to write. That rule is therefore enforced structurally, by result.py
--check, over the table's own fields, and not here. What is here is the vocabulary: the words that
join two instruments in a sentence.

Exit 0 clean, 1 findings, 2 usage. stdlib only, no network, no model.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import lint_language as ll  # noqa: E402  the copied linter, for its file walk and its commit reader

# The patterns hold the file that defines them out of their own scan, as the copied linter does.
NEVER_SCANNED = {"lint_pooling.py"}

# (name, regex, why it is banned). Word-bounded throughout: an unbounded `total` matches `totally`,
# and an unbounded `average` matches nothing this study would write but costs nothing to bound.
PATTERNS: list[tuple[str, str, str]] = [
    ("combined", r"\bcombined\b",
     "two rounds measured under different conditions are never added; they print side by side"),
    ("across-rounds", r"\bacross (?:the )?rounds\b",
     "a figure across rounds pools two instruments into one number"),
    ("across-halves", r"\bacross (?:the )?halves\b",
     "the two halves are the comparison; a figure across them erases it"),
    ("overall", r"\boverall\b",
     "an overall figure is a pooled figure wearing a shorter word"),
    ("average", r"\baverages?\b|\baveraged\b|\baveraging\b",
     "an average over cells of three takes is a rate, and over two instruments it is also a pool"),
    ("mean-of", r"\bmean of\b",
     "the same figure as an average, spelled differently"),
    ("pooled", r"\bpool(?:ed|ing|s)?\b",
     "the word for the thing itself; the study says what it did instead of naming the shortcut"),
    ("total-of", r"\btotal of\b",
     "a total over cells or rounds is a pooled figure"),
    ("in-total", r"\bin total\b", "the same figure as a total, spelled differently"),
    ("aggregate", r"\baggregat(?:e|ed|es|ing|ion)\b", "the same figure as a total, in a longer word"),
    ("summed", r"\bsummed\b|\bsum of\b", "two cells' counts are never added"),
    ("both-rounds", r"\bboth rounds\b",
     "a sentence about both rounds at once is a comparison, and a comparison is the owner's to write"),
    ("improved", r"\bimprov(?:e|ed|es|ement|ements)\b",
     "an improvement is a claim across two instruments, which this study may not make"),
    ("better-than", r"\bbetter than\b|\bworse than\b",
     "a comparison between rounds or models is the owner's to write, never the run's"),
    # NARROWED, on a false positive this guard raised against round 2's carried text: "the driver walks UP
    # FROM the checkout" is a direction of travel, not a count moving. What makes the phrase pooling is what
    # it moves from -- a number, a nothing, or the other round -- so the pattern now names those and the
    # bare preposition passes. The carried keys are byte-identical to round 2's and are not this round's to
    # reword, so the fix had to be here; it binds the pattern to the rule rather than approximating it.
    ("up-from", r"\b(?:up|down) from (?:\d|none\b|zero\b|no\b|nothing\b|round\b|the (?:earlier|previous|last)\b|last round\b)",
     "a movement between two rounds' counts reads them as one series"),
]


def scan_text(text: str, rel: str) -> list[dict]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, rx, why in PATTERNS:
            for m in re.finditer(rx, line, re.I):
                findings.append({"file": rel, "line": lineno, "pattern": name,
                                 "match": m.group(0), "text": line.strip()[:160], "why": why})
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--commits-since", help="also scan commit bodies touching the study since <sha>")
    ap.add_argument("--at", default=ll.DEFAULT_AT, metavar="<sha>",
                    help="with --commits-since: scan up to this commit (default: HEAD)")
    ap.add_argument("--include-code", action="store_true", help="also scan .py sources")
    ap.add_argument("--list-patterns", action="store_true")
    args = ap.parse_args()

    if args.list_patterns:
        for name, rx, why in PATTERNS:
            print(f"{name:16} {rx:46} {why}")
        return 0
    if not args.paths and not args.commits_since:
        ap.error("give at least one path, or --commits-since <sha>")

    findings: list[dict] = []
    scanned = 0
    for f in ll.iter_files(args.paths, include_code=args.include_code):
        if f.name in NEVER_SCANNED:
            continue
        try:
            rel = str(f.resolve().relative_to(REPO))
        except ValueError:
            rel = str(f)
        scanned += 1
        findings.extend(scan_text(f.read_text(errors="replace"), rel))

    commits = 0
    if args.commits_since:
        for sha, body in ll.commit_bodies(args.commits_since, args.at):
            commits += 1
            findings.extend(scan_text(body, f"commit {sha[:12]}"))

    if scanned == 0 and commits == 0:
        # An empty gate is said out loud. A guard that graded nothing has not passed.
        print("nothing scanned — no files matched and no commits were named. Not a pass.")
        return 2

    if not findings:
        print(f"clean — {scanned} file(s) and {commits} commit(s) scanned, no excusal path")
        return 0

    print(f"{len(findings)} finding(s) across {scanned} file(s) and {commits} commit(s):\n")
    for f in findings:
        print(f"  {f['file']}:{f['line']}  [{f['pattern']}] {f['match']!r}")
        print(f"      {f['text']}")
        print(f"      why banned: {f['why']}")
    print("\nThere is no allowlist for these. Write the sentence a different way.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
