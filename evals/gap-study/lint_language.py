#!/usr/bin/env python3
"""Refuse the words and number-shapes this study is not allowed to publish.

    python3 evals/gap-study/lint_language.py <path> [<path> ...]
    python3 evals/gap-study/lint_language.py --commits-since <sha>     # commit BODIES
    python3 evals/gap-study/lint_language.py --list-patterns

WHY THIS EXISTS AS A PROGRAM RATHER THAN A RULE. With n = 3 per cell, a rate is not a thing this
study is entitled to state, and the difference between "held in three of three takes" and "holds
reliably" is the difference between a record and a claim. That difference is invisible at the
moment of writing -- the second sentence reads better, which is exactly the pressure. A guard that
runs is the only version of that rule that survives a tired afternoon.

The banned list is fixed by the pre-registration and is not this file's to soften. It bans:

  * any percentage, and any `n / m` shape, and the words that smuggle a rate in prose
    ("out of", "reliab", "consisten", "robust", "perfect", "unanim");
  * the absolutes a three-take study cannot support ("always", "all models", "all takes",
    "every model");
  * the marketing words this project has ruled out ("compliant", "GxP", "production-ready",
    "LLM-agnostic"), the claims about a local model it will not make ("works", "free"), and the
    privacy sentence it will never write.

THE EXCEPTION MECHANISM, AND WHY IT IS SHAPED LIKE THE SECRET SCANNER'S. A blunt pattern fires on
honest prose: this repository holds two studies, so "the first study" is a name, not a claim to be
first at anything. Weakening the pattern to let that through would also let through the sentence
the pattern exists to stop.

So the pattern stays strict and an occurrence is excused one at a time, in
`language-allowlist.json`, pinned to the EXACT TEXT of the line it sits on. Edit the line and the
exception stops matching and the finding comes back. An exception carries a reason a stranger can
read. Nothing here can switch a pattern off; it can only excuse a line somebody has read.

Exit 0 clean, 1 findings, 2 usage. stdlib only, no network, no model.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ALLOWLIST = HERE / "language-allowlist.json"

# (name, regex, why it is banned). The name is what an allowlist entry refers to, so renaming one
# orphans its exceptions rather than silently widening them.
PATTERNS: list[tuple[str, str, str]] = [
    ("percentage", r"\d+\s*(?:%|percent\b)",
     "n = 3 does not support a rate; the table publishes counts"),
    ("ratio-slash", r"\d+\s*/\s*\d+",
     "a `k / n` shape reads as a rate; the study writes 'k of n'"),
    ("out-of", r"\bout of\b",
     "'three out of three' is a rate in words"),
    ("one-point-zero", r"(?<![\w.])1\.0(?![\w.])",
     "a proportion of one is still a proportion"),
    ("hundred", r"(?<![\w.])100(?![\w.])",
     "a count of one hundred is almost never what this study means, and reads as a percentage"),
    ("reliab", r"reliab", "reliability is a claim about a rate"),
    ("consisten", r"consisten", "consistency is a claim about a rate"),
    ("robust", r"robust", "robustness is a claim this study cannot support"),
    ("perfect", r"perfect", "no cell in a three-take study is perfect"),
    ("unanim", r"unanim", "unanimity across three takes is a count, and is written as one"),
    ("always", r"\balways\b", "an absolute the takes cannot evidence"),
    ("all-models", r"\ball models\b", "an absolute across an axis with a `not run` cell in it"),
    ("all-takes", r"\ball takes\b", "an absolute across takes"),
    ("every-model", r"\bevery model\b", "an absolute across an axis with a `not run` cell in it"),
    ("compliant", r"\bcompliant\b", "ruled out for any public artifact"),
    ("gxp", r"\bGxP\b", "ruled out for any public artifact"),
    ("production-ready", r"production[- ]ready", "ruled out for any public artifact"),
    ("llm-agnostic", r"LLM[- ]agnostic",
     "ruled OUT until Javier lifts it; Claude variants plus two local models never evidence it"),
    ("local-works", r"\bworks\b",
     "the local tier reports takes graded per label, never that a model 'works'"),
    ("free", r"\bfree\b",
     "'free' about a local model hides the machine time and the electricity"),
    ("data-never-leaves", r"data never leaves", "a claim about where a lab's data goes is not the run's to make"),
]


def load_allowlist() -> list[dict]:
    if not ALLOWLIST.is_file():
        return []
    raw = json.loads(ALLOWLIST.read_text())
    return raw.get("excused", [])


def excused(entries: list[dict], rel: str, pattern: str, line_text: str) -> dict | None:
    """An exception matches only when file, pattern AND the exact line text all agree.

    The line text is compared after stripping trailing whitespace and nothing else. Anything
    looser would let an edited line inherit the ruling made about the old one.
    """
    for e in entries:
        if e.get("file") == rel and e.get("pattern") == pattern:
            if e.get("line_text", "").rstrip() == line_text.rstrip():
                return e
    return None


def scan_text(text: str, rel: str, entries: list[dict]) -> list[dict]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, rx, why in PATTERNS:
            for m in re.finditer(rx, line, flags=re.IGNORECASE):
                if excused(entries, rel, name, line):
                    continue
                findings.append({"file": rel, "line": lineno, "pattern": name,
                                 "matched": m.group(0), "why": why, "text": line.strip()})
    return findings


# Two files are never scanned, and neither is an exception to the rule.
#
# This file holds the banned patterns as literal strings, so scanning it reports its own table
# back as findings -- a category error, not a violation. The allowlist holds the exact text of
# every excused line, so scanning it reports every excusal as a fresh finding, forever.
#
# Neither is a claim about the study's results, which is what the ban is about. They are named
# here rather than filtered by a rule, so a reader can see the whole list at once and no third
# file can join it quietly.
NEVER_SCANNED = {"lint_language.py", "language-allowlist.json"}

# Prose and data are scanned by default. Source is scanned only when asked for: a docstring that
# explains why a word is banned is not a published claim, and the pre-registration's own test
# points this tool at the published set explicitly.
DEFAULT_SUFFIXES = {".md", ".json"}


def iter_files(paths: list[str], include_code: bool = False):
    suffixes = DEFAULT_SUFFIXES | ({".py"} if include_code else set())
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if (f.is_file() and f.suffix in suffixes
                        and f.name not in NEVER_SCANNED
                        and "__pycache__" not in f.parts):
                    yield f
        elif path.is_file():
            if path.name in NEVER_SCANNED:
                print(f"note: {path.name} is never scanned (it holds the patterns themselves)")
                continue
            yield path


def commit_bodies(since: str) -> list[tuple[str, str]]:
    """Every commit touching this study since <sha>, as (sha, body)."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "log", "--format=%H", f"{since}..HEAD", "--", "evals/gap-study"],
        capture_output=True, text=True)
    if out.returncode != 0:
        print(f"git log failed: {out.stderr.strip()}", file=sys.stderr)
        return []
    bodies = []
    for sha in out.stdout.split():
        body = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%B", sha],
                              capture_output=True, text=True).stdout
        bodies.append((sha, body))
    return bodies


def main() -> int:
    ap = argparse.ArgumentParser(description="Refuse the words this study may not publish.")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--commits-since", help="also scan commit bodies touching the study since <sha>")
    ap.add_argument("--include-code", action="store_true",
                    help="also scan .py sources (off by default; see NEVER_SCANNED)")
    ap.add_argument("--list-patterns", action="store_true")
    args = ap.parse_args()

    if args.list_patterns:
        for name, rx, why in PATTERNS:
            print(f"{name:20} {rx:32} {why}")
        return 0

    if not args.paths and not args.commits_since:
        ap.error("give at least one path, or --commits-since <sha>")

    entries = load_allowlist()
    findings: list[dict] = []
    scanned = 0

    for f in iter_files(args.paths, include_code=args.include_code):
        try:
            rel = str(f.resolve().relative_to(REPO))
        except ValueError:
            rel = str(f)
        scanned += 1
        findings.extend(scan_text(f.read_text(errors="replace"), rel, entries))

    if args.commits_since:
        for sha, body in commit_bodies(args.commits_since):
            scanned += 1
            findings.extend(scan_text(body, f"commit:{sha[:12]}", entries))

    # A scan that saw nothing is reported as such. "No findings" over zero inputs is not a pass;
    # it is the absence of a measurement, and this study has been bitten by that shape before.
    if scanned == 0:
        print("nothing scanned — no files matched and no commits were named. Not a pass.")
        return 2

    if not findings:
        print(f"clean — {scanned} input(s) scanned, {len(entries)} excused line(s) on record")
        return 0

    print(f"{len(findings)} finding(s) across {scanned} input(s):\n")
    for f in findings:
        print(f"  {f['file']}:{f['line']}  [{f['pattern']}] {f['matched']!r}")
        print(f"      {f['text'][:120]}")
        print(f"      why banned: {f['why']}")
    print("\nFix the text, or excuse the exact line in language-allowlist.json with a reason.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
