"""The one owner of this study's name, its paths and its published-section markers.

Round 3 is a byte copy of round 2's harness (see COPIED.json), as round 2 was of round 1's. Every
place the copy built a path to its own tree, read its own history, or named its section in
docs/EVALS.md took that from a literal string, and a literal string copied from round 2 names round
2: a check that reads `evals/gap-study-2` reads the study that is finished, and passes on bytes it
was never meant to judge. So code that builds a path or a marker takes it from here, and nowhere
else.

ROUND1 is round 2's tree, read as DATA only (its transcripts, its committed results and its walk
messages). Nothing in this study imports from it or writes to it. The constant keeps round 2's name
because every copied file reads it by that name; what it points at is this study's prior round.

The leak and sweep patterns (smoke_run_tree.TREE_SWEEP, check_take.study_paths_read, the draft's
leak_words) are deliberately NOT built from here: they are substring and regex matches that must
catch this study's name as well as round 1's, and TheLeakPatternsStillSeeRoundTwo proves they do.

No model, no network, stdlib only.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

STUDY = "gap-study-3"
STUDY_REL = "evals/gap-study-3"
STUDY_TITLE = "The Gap Study, round 3"

# The published section in docs/EVALS.md. Round 1's markers are `gap-study:summary` and `/gap-study`,
# round 2's are `gap-study-2:summary` and `/gap-study-2`; these differ from both, so no study's guards
# can read another's section.
SECTION_TITLE = "# The Gap Study, round 3"
SUMMARY_START = "<!-- gap-study-3:summary -->"
SUMMARY_END = "<!-- /gap-study-3:summary -->"
SECTION_END = "<!-- /gap-study-3 -->"

# WHERE THE TWO KINDS OF REPORT LIVE (round 3). Round 2 wrote its pre-freeze reviews and its final
# verifications into one folder, so `ls verification/` counted both at once. Round 3 keeps them apart
# so a fresh run counts each from `ls` alone: pre-freeze reviews with their blindness records in
# review_kit/, final verifications with theirs in verification/. Every file that builds one of those
# paths takes it from here.
REVIEW_DIR = "review_kit"
VERIFY_DIR = "verification"

# The prior round, as data only.
ROUND1_REL = "evals/gap-study-2"
ROUND1 = REPO / "evals" / "gap-study-2"


def rel(*parts: str) -> str:
    """A repository-relative path inside this study: rel("graders", "labels.py")."""
    return "/".join((STUDY_REL, *parts))
