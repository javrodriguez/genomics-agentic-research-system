#!/usr/bin/env python3
"""Refuse a commit message this study may not commit.

    python3 evals/gap-study-2/commit_msg.py <message-file>

WHY. Round 1's take loop wrote 109 commit subjects carrying a take's position over the total, and every
one of them needed an excusal after the fact (structural lesson 8). A rule in a plan did not stop it; a
program run on the message before `git commit -F <file>` does.

WHAT IT REFUSES, each as one line `[reason-id] sentence`, all of them in one run:

  * [solidus-count]   a digit, a solidus, a digit (`\\d+\\s*/\\s*\\d+`) anywhere in the subject or body. A
                      path segment such as `<model>/1` is refused too: that is the exact shape round 1
                      had to excuse, and a message can say "take 1" instead. An ISO date (2026-09-13) has
                      no solidus and passes; a slashed date (13/09/2026) is refused, so write ISO dates.
  * [subject-prefix]  a subject that does not open with one of `slice NN:` (two digits), `take:`,
                      `takes:`, `walk:`, `rehearsal:`, `ruling:`, followed by a space and words.
  * [language:<name>] a finding of the study's own language guard (lint_language.PATTERNS) on the whole
                      message. The allowlist is not consulted: every excusal is pinned to a file, and a
                      commit message is not one.
  * [empty-message]   a file with no subject line.

A `Co-Authored-By:` trailer passes because it carries none of the shapes above, not because it is
exempt: nothing in the message is skipped.

Exit 0 prints `clean`; 1 refusals; 2 usage or an unreadable file. stdlib only, no network, no model.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SOLIDUS_COUNT = re.compile(r"\d+\s*/\s*\d+")
SUBJECT_PREFIX = re.compile(r"^(?:slice \d{2}|take|takes|walk|rehearsal|ruling): \S")
PREFIXES = "`slice NN:` (two digits), `take:`, `takes:`, `walk:`, `rehearsal:` or `ruling:`"


def _lint_module():
    """The study's language guard, loaded by path so a same-named module elsewhere cannot answer."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))  # lint_language imports `study`, which lives beside it
    spec = importlib.util.spec_from_file_location("gap_study_2_lint_language", HERE / "lint_language.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def language_findings(text: str) -> list[dict]:
    return _lint_module().scan_text(text, "commit-message", [])


def refusals(text: str) -> list[str]:
    lines = text.splitlines()
    subject = next((ln for ln in lines if ln.strip()), "")
    out: list[str] = []
    if not subject:
        return ["[empty-message] the message has no subject line"]

    for lineno, line in enumerate(lines, start=1):
        m = SOLIDUS_COUNT.search(line)
        if m:
            out.append(f"[solidus-count] line {lineno} carries {m.group(0)!r}, a digit-solidus-digit shape "
                       f"that reads as a count over a total; write 'k of n' or name the item instead")

    if not SUBJECT_PREFIX.match(subject):
        out.append(f"[subject-prefix] the subject {subject[:60]!r} does not open with {PREFIXES} "
                   f"followed by a space and words")

    findings = language_findings(text)
    for f in findings:
        out.append(f"[language:{f['pattern']}] line {f['line']} carries {f['matched']!r}: {f['why']}")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1].startswith("-"):
        print("usage: commit_msg.py <message-file>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"cannot read {path.name}: {exc}", file=sys.stderr)
        return 2
    found = refusals(text)
    if found:
        for line in found:
            print(line)
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
