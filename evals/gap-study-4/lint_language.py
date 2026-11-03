#!/usr/bin/env python3
"""Refuse the words and number-shapes this study is not allowed to publish.

    python3 evals/gap-study-2/lint_language.py <path> [<path> ...]
    python3 evals/gap-study-2/lint_language.py --commits-since <sha>     # commit BODIES
    python3 evals/gap-study-2/lint_language.py --commits-since <sha> --at <sha>   # up to that commit
    python3 evals/gap-study-2/lint_language.py --list-patterns

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
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import study

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ALLOWLIST = HERE / "language-allowlist.json"

# (name, regex, why it is banned). The name is what an allowlist entry refers to, so renaming one
# orphans its exceptions rather than silently widening them.
PATTERNS: list[tuple[str, str, str]] = [
    ("percentage", r"\d+\s*(?:%|percent\b)",
     "n = 3 does not support a rate; the table publishes counts"),
    # WORD-BOUNDED, as requirement 5 says. Unbounded, it matched walk 2's driver ledger across a
    # neutral project name ending in a digit and the path segment after it -- and a neutral name is
    # `run-` plus eight hex characters, so most take ledgers would have tripped it.
    ("ratio-slash", r"\b\d+\s*/\s*\d+\b",
     "a `k / n` shape reads as a rate; the study writes 'k of n'"),
    ("out-of", r"\bout of\b",
     "'three out of three' is a rate in words"),
    ("one-point-zero", r"(?<![\w.])1\.0(?![\w.])",
     "a proportion of one is still a proportion"),
    # AMENDMENT 4 (17 September 2026): a comma followed by three digits is a digit-group separator, so a comma-grouped six-figure count is a
    # count of tokens and not a hundred; the costs table's first six-figure count stopped the take loop on this rule.
    # AMENDMENT 6 (17 September 2026): a hundred in the study's own count form, `100 of 100` or `5 of 100`, is a count
    # and not a rate; the costs table's dollar line said "evidenced by 100 of 100 environment records" at the
    # hundredth graded take and the loop stopped on it.
    ("hundred", r"(?<![\w.])(?<!\d,)(?<!of )100(?![\w.])(?!,\d{3})(?! of \d)",
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
    # PRE-FREEZE REVIEW 1, m14 (lane pf1-l2b, Sat 24 Oct 2026): three comparatives that passed the guard. A sentence
    # comparing models stays Javier's (stats.py: "stats prints numbers and family labels only"), so the study's own
    # words never say one model outperforms, beats or is stronger than another. FAMILY_LABEL_EXCEPTIONS below.
    ("outperform", r"outperform", "a sentence comparing models is Javier's to write, never the study's"),
    ("stronger", r"\bstronger\b", "a sentence comparing models is Javier's to write, never the study's"),
    ("beats", r"\bbeats\b", "a sentence comparing models is Javier's to write, never the study's"),
]

# THE FAMILY-LABEL EXCEPTION (m14). A comparative inside one of these exact strings is a registered name, not a claim:
# the four family labels stats prints (stats.FAMILIES, which check_families holds every comparison row to), the
# contrast family's short name in stats' own prose, and the design's registered power-grid field as a JSON key. A
# comparative anywhere else on the line is still a finding. Read from stats, never copied.
COMPARATIVES = ("outperform", "stronger", "beats")


def family_label_exceptions() -> tuple:
    import stats  # noqa: E402  (this study's, first on sys.path)
    return tuple(stats.FAMILIES) + (stats.CONTRAST_NAME, '"stronger":')


def inside_label(line: str, start: int, end: int, labels) -> bool:
    for label in labels:
        i = line.find(label)
        while i != -1:
            if i <= start and end <= i + len(label):
                return True
            i = line.find(label, i + 1)
    return False


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
    labels = family_label_exceptions()
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, rx, why in PATTERNS:
            for m in re.finditer(rx, line, flags=re.IGNORECASE):
                if name in COMPARATIVES and inside_label(line, m.start(), m.end(), labels):
                    continue
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

# A REPORT WRITTEN BY AN OUTSIDE AGENT IS EVIDENCE, NOT A CLAIM BY THIS STUDY.
#
# The protocol requires every review and verifier report to be committed verbatim, whatever it
# says, and NEVER edited -- a report carrying something it should not is discarded whole and the
# agent re-run, not tidied. So the study cannot both commit a report unedited and hold that report
# to its own publication vocabulary.
#
# The same reasoning already excludes transcripts: what somebody else said is a record, and editing
# a record to satisfy a linter is the thing the protocol forbids outright.
#
# This exempts REPORTS ONLY, by name. Anything this study writes about a report -- a disposition
# note, a summary, a commit body -- is a claim by the study and is scanned like everything else.
REPORT_NAMES = (
    re.compile(r"^prefreeze-\d+\.md$"),          # a pre-freeze review
    re.compile(r"^\d{4}-\d{2}-\d{2}-[0-9a-f]+\.md$"),  # a dated verifier report
)


# A REPORT WRITTEN BY SOMEONE OUTSIDE THIS STUDY IS EVIDENCE, NOT A CLAIM THIS STUDY MAKES.
#
# `verification/` holds fresh-context verifier reports and `reviews/` holds the pre-freeze reviewers'
# reports. Both are committed verbatim, including the ones that turned out to be wrong, because a
# report edited into agreement with what happened next is no longer evidence of anything.
#
# So they are not scanned. This is the only exemption in this file that covers whole documents, and
# it is narrow on purpose: it applies to two named directories, and every word the STUDY writes about
# those reports -- the README beside them, the rulings that cite them, the commit bodies -- is scanned
# exactly as before. Scanning them instead would leave two bad options, editing another author's words
# or carrying dozens of allowlist lines that dilute the guard for the prose it exists to police.
def is_outside_report(path: Path) -> bool:
    if "reviews" in path.parts and path.name != "README.md":
        return True
    return ("verification" in path.parts
            and any(rx.match(path.name) for rx in REPORT_NAMES))


# A CASE FILE QUOTES THE AGENT VERBATIM, AND THE STUDY'S OWN WORDS SIT IN THE SAME FILE.
#
# cases/<task>.json carries an excerpt of each agent message, so scanning it whole reports the
# agent's language as the study's claims -- and editing an excerpt to satisfy this guard would
# corrupt the record the file exists to be.
#
# But the same file carries `hand_note` and `hand_labelling_rule`, which ARE the study's words about
# those messages. Exempting the file wholesale would stop scanning them.
#
# So the file is not scanned line by line; its own fields are scanned instead, by name. The agent's
# words are a record and are left alone; the study's words are claims and are checked.
CASE_OWN_FIELDS = ("hand_note", "hand_labelling_rule", "role", "not_a_claim")


def is_case_file(path: Path) -> bool:
    return "cases" in path.parts and path.suffix == ".json"


def case_file_own_words(path: Path) -> str:
    """Only the text this study wrote about the messages, never the messages."""
    try:
        doc = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return ""
    out = [str(doc.get(k, "")) for k in CASE_OWN_FIELDS]
    for c in doc.get("cases", []):
        out.extend(str(c.get(k, "")) for k in CASE_OWN_FIELDS)
    return "\n".join(x for x in out if x)

# A TAKE'S MACHINE RECORD IS A RECORD, NOT A CLAIM BY THIS STUDY. Amendment 2, 12 September 2026.
#
# Beside every graded, rehearsed or paused attempt the pinned driver writes `driver-ledger.json` and the
# scrubber writes `scrub.json`: session ids, file paths, hashes, exit codes, token counts and times.
# The transcript beside them is already outside this guard, for the reason given above: what happened
# is a record, and editing a record to satisfy a linter is what the protocol forbids. These two files
# are the same kind of record in another format. The run's first scan of real take output reported 109
# findings in them, 108 of them the `k / n` rule matching a path segment such as
# `claude-haiku-4-5-20251001/1`, and none of the 109 was a sentence the study wrote.
#
# NARROW ON PURPOSE. Only those file names, and only under the three directories an attempt is
# filed in. A walk's ledger is still scanned, and so is every file this study writes about a take:
# the results, the analysis, the cost tables and the published section. No pattern is changed.
#
# ROUND 2, CP3: `environment.json` is the third, the driver's record of the environment a take ran in (variable
# names, absent/empty/set, the credential source per turn). Its published name patterns carry shapes such as
# `_TOKEN$`, and a record is never edited to satisfy this guard. A walk's environment.json is still scanned.
#
# ROUND 4 (lane w8a, ruling W8-layout-1, closing W7B-R1-3; this file moved from lane w1a to lane w8a under ruling
# W8A-gap4-1). The record folders are named once, in mode_binding (RECORD_ROOTS: takes/ and rehearsals/), and every
# file INSIDE a record folder (takes/<slot>/<k>/**, rehearsals/<walk>/**) is a record, never linted as prose: round
# 4's walk folder holds a take folder's records plus its grade. rehearsals/README.md and rehearsals/register.json
# (whose `reason` is the study's own prose) sit beside the walk folders, not in one, and are still linted. Round 3's
# own roots (transcripts/, pauses/) are never written in round 4.
import mode_binding  # noqa: E402

TAKE_ROOTS = mode_binding.RECORD_ROOTS


def is_take_record(path: Path) -> bool:
    try:
        parts = path.resolve().relative_to(HERE).parts
    except ValueError:
        parts = path.parts
    return mode_binding.record_parts(parts, TAKE_ROOTS) is not None


# ROUND 4, LANE VENDOR-SETTLE STAGE K (glitch-f1's settle-design rulings, Wed 21 Oct 2026: the RECORDED fixture copies
# are treated as the walk files are). A RECORDED take folder, tests/fixtures/recorded-<harness>-<walk>/, is a byte
# copy of a committed walk folder's records (rehearsals/<walk>/**, never linted, above), which the vendor readers are
# re-tested on; its first lint reported 18 findings, every one the `k / n` rule on a dated session path such as
# `sessions/2026/10/20`. NARROW ON PURPOSE: a file there is a record only while its bytes are the sha256 its folder's
# PROVENANCE.json lists for it, so an edited copy is linted again; the folder's README.md and PROVENANCE.json are the
# study's own words and are linted as before; no pattern changes.
_RECORDED_FIXTURE = re.compile(r"recorded-(codex|gemini)-w-[og][0-9]+")


def is_recorded_fixture_copy(path: Path) -> bool:
    folder = path.parent
    rel_parts = []
    while folder != folder.parent and not _RECORDED_FIXTURE.fullmatch(folder.name):
        rel_parts.insert(0, folder.name)
        folder = folder.parent
    if not (_RECORDED_FIXTURE.fullmatch(folder.name) and folder.parent.name == "fixtures"
            and folder.parent.parent.name == "tests"):
        return False
    rel = "/".join([*rel_parts, path.name])
    try:
        listed = json.loads((folder / "PROVENANCE.json").read_text(encoding="utf-8"))["files"][rel]["sha256"]
        return hashlib.sha256(path.read_bytes()).hexdigest() == listed
    except (OSError, ValueError, KeyError, TypeError):
        return False


# Prose and data are scanned by default. Source is scanned only when asked for: a docstring that
# explains why a word is banned is not a published claim, and the pre-registration's own test
# points this tool at the published set explicitly.
DEFAULT_SUFFIXES = {".md", ".json"}


# Lane fold11/freeze-recheck (the fold's gate review, m6): the same reasoning, for this study's review folder, by rule. A
# seed round's report lands after its launch commit, and any edit to a pinned file then needs a new round, so a report
# cannot be listed or cured by that file after the fact. From round 9 on, a report is outside this scan and lint_pooling's
# when it is review_kit/prefreeze-<N>.md and its sha256 is the digest the blindness record beside it states: an edited copy
# is no longer the record, and is scanned. Rounds before 9 keep their excusals and BOUND_REVIEW_RECORDS. Named on its own
# path, a report is still scanned, and a walk says what it skipped.
BOUND_RULE_FROM_ROUND = 9
REPORT_DIGEST_LINE = "report sha256, as the reviewer's session wrote it: "     # review_kit/blindness.py REPORT_DIGEST


def is_bound_review_report(path: Path) -> bool:
    got = re.fullmatch(r"prefreeze-(\d+)\.md", path.name)
    if not got or int(got.group(1)) < BOUND_RULE_FROM_ROUND or path.parent.name != "review_kit":
        return False
    try:
        stated = re.findall(rf"^{re.escape(REPORT_DIGEST_LINE)}([0-9a-f]{{64}})$",
                            path.with_name(f"prefreeze-{got.group(1)}-blindness.txt").read_text(errors="replace"), re.M)
        return len(stated) == 1 and stated[0] == hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return False


def named_bound_report(path: Path) -> bool:
    if not is_bound_review_report(path):
        return False
    print(f"not scanned: {path.name}, a bound review report (is_bound_review_report)")
    return True


def iter_files(paths: list[str], include_code: bool = False):
    suffixes = DEFAULT_SUFFIXES | ({".py"} if include_code else set())
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if (f.is_file() and f.suffix in suffixes
                        and f.name not in NEVER_SCANNED
                        and not is_outside_report(f)
                        and not named_bound_report(f)
                        and not is_case_file(f)
                        and not is_take_record(f)
                        and not is_recorded_fixture_copy(f)
                        and "__pycache__" not in f.parts):
                    yield f
        elif path.is_file():
            if path.name in NEVER_SCANNED:
                print(f"note: {path.name} is never scanned (it holds the patterns themselves)")
                continue
            yield path


# ROUND 2, CP2 (structural lesson 7): the commit the body scan stops at. HEAD unless `--at <sha>` names
# another; the draft's `head_readers` lists this line, and EveryHeadReaderIsListed refuses an unlisted one.
DEFAULT_AT = "HEAD"


def commit_bodies(since: str, at: str = DEFAULT_AT) -> list[tuple[str, str]]:
    """Every commit touching this study since <sha>, up to <at>, as (sha, body)."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "log", "--format=%H", f"{since}..{at}", "--", study.STUDY_REL],
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


# Pre-freeze review 2, m5 (lane fold2-lb): a page with no round-4 section is NOT_RUN, never 0, unless the caller says
# --allow-absent (CI, only while the study has no RESULT.md), so round-4 prose written outside the markers after
# publication can never pass this lint by having no section. lint_pooling --section-of reads the same two values.
NOT_RUN = 3


def section_main(page: Path, allow_absent: bool = False) -> int:
    """Lane review 3 (pf1-l2b): the public page's round 4 section, read as lint_pooling --section-of reads it (only this
    round's marked block; the earlier rounds' sections are theirs), against every pattern here, the comparatives
    included. An excusal names the page's repository path and the exact line, as everywhere. No section: NOT_RUN, or 0
    under allow_absent (m5); the words say "Not a pass" either way."""
    text = page.read_text(errors="replace") if page.is_file() else ""
    if study.SUMMARY_START not in text or study.SUMMARY_END not in text:
        print(f"no section yet: {page} carries no {study.SUMMARY_START} block, so this scan has read nothing and "
              f"claims nothing. Not a pass" + (" (--allow-absent: exit 0)." if allow_absent else
                                               f" (exit {NOT_RUN}: not run)."))
        return 0 if allow_absent else NOT_RUN
    start = text.index(study.SUMMARY_START)
    end = text.index(study.SUMMARY_END, start)
    before = text[:start].count("\n")
    section = text[start:end]
    try:
        rel = str(page.resolve().relative_to(REPO))
    except ValueError:
        rel = str(page)
    found = scan_text(section, rel, load_allowlist())
    for f in found:
        f["line"] += before
    if not found:
        print(f"clean — this round's section of {page} scanned ({section.count(chr(10))} line(s))")
        return 0
    print(f"{len(found)} finding(s) in this round's section of {page}:\n")
    for f in found:
        print(f"  {f['file']}:{f['line']}  [{f['pattern']}] {f['matched']!r}")
        print(f"      {f['text'][:120]}")
        print(f"      why banned: {f['why']}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Refuse the words this study may not publish.")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--commits-since", help="also scan commit bodies touching the study since <sha>")
    ap.add_argument("--at", default=DEFAULT_AT, metavar="<sha>",
                    help="with --commits-since: scan up to this commit (default: HEAD)")
    ap.add_argument("--include-code", action="store_true",
                    help="also scan .py sources (off by default; see NEVER_SCANNED)")
    ap.add_argument("--list-patterns", action="store_true")
    ap.add_argument("--section-of", type=Path, metavar="FILE",
                    help="scan only this round's marked section of FILE (study.SUMMARY_START..SUMMARY_END), as "
                         "lint_pooling --section-of does; says so when the section does not exist yet")
    ap.add_argument("--allow-absent", action="store_true",
                    help=f"with --section-of: a page with no round-4 section exits 0, not {NOT_RUN} (m5; CI passes it "
                         f"only while the study has no RESULT.md)")
    args = ap.parse_args()

    if args.allow_absent and args.section_of is None:
        ap.error("--allow-absent is read only with --section-of")
    if args.section_of is not None:
        return section_main(args.section_of, allow_absent=args.allow_absent)

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

    # the study's own words inside the case files, scanned by field
    for p in args.paths:
        base = Path(p)
        pool = sorted(base.rglob("*.json")) if base.is_dir() else [base]
        for f in pool:
            if not is_case_file(f):
                continue
            scanned += 1
            try:
                rel = str(f.resolve().relative_to(REPO))
            except ValueError:
                rel = str(f)
            findings.extend(scan_text(case_file_own_words(f), rel + " (own words)", entries))

    if args.commits_since:
        for sha, body in commit_bodies(args.commits_since, args.at):
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
