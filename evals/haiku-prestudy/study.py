"""The one owner of this study's name, its paths and its published-section markers.

Round 2 began as a byte copy of round 1's harness (see COPIED.json). Every place the copy built a
path to its own tree, read its own history, or named its section in docs/EVALS.md took that from a
literal string, and a literal string copied from round 1 names round 1: a check that reads
`evals/gap-study` reads the study that is finished, and passes on bytes it was never meant to judge.
So code that builds a path or a marker takes it from here, and nowhere else.

ROUND1 is round 1's tree, read as DATA only (its transcripts and walk messages). Nothing in this
study imports from it or writes to it; the draft lists every round-1 path it names in
`round_1_data_paths`, and EveryPinnedPathIsRoundTwos refuses any other.

The leak and sweep patterns (smoke_run_tree.TREE_SWEEP, check_take.study_paths_read, the draft's
leak_words) are deliberately NOT built from here: they are substring and regex matches that must
catch this study's name as well as round 1's, and TheLeakPatternsStillSeeRoundTwo proves they do.

No model, no network, stdlib only.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

STUDY = "haiku-prestudy"
STUDY_REL = "evals/haiku-prestudy"
STUDY_TITLE = "The Haiku pre-study"

# The published section in docs/EVALS.md. Round 1's markers are `gap-study:summary` and `/gap-study`;
# these differ from them, so neither study's guards can read the other's section.
SECTION_TITLE = "# The Haiku pre-study"
SUMMARY_START = "<!-- haiku-prestudy:summary -->"
SUMMARY_END = "<!-- /haiku-prestudy:summary -->"
SECTION_END = "<!-- /haiku-prestudy -->"

# Round 1, as data only.
ROUND1_REL = "evals/gap-study"
ROUND1 = REPO / "evals" / "gap-study"


def rel(*parts: str) -> str:
    """A repository-relative path inside this study: rel("graders", "labels.py")."""
    return "/".join((STUDY_REL, *parts))
