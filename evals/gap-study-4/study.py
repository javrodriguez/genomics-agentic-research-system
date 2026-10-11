"""The one owner of this study's name, its paths, its arms and its published-section markers.

Round 4 is a copy of round 3's instrument as it stood at round 3's done commit e2979b31, built beside the
frozen rounds and never editing them; what each copied file is (identical, edited with a reason, or new) is
recorded per build lane in COPIED.d/ and bound by copy_manifest.py --check. Every place the copy builds a path
to its own tree, reads its own history, or names its section in docs/EVALS.md takes that from here, and
nowhere else: a literal copied from round 3 names round 3, and a check that reads `evals/gap-study-3` reads the
study that is finished.

ROUND1 is the prior round's tree -- round 3's -- read as DATA only. Nothing in this study imports from it or
writes to it. The constant keeps the name every copied file reads it by (round 2 named it so); what it points
at is this study's prior round. PRIOR_STUDY and PRIOR_REL name the same folder under an honest name for new code.

ARMS is the arms this round runs, A, C, O and G (the plan's arms; arm C is the first cut if the freeze slips).

The leak and sweep patterns (smoke_run_tree.TREE_SWEEP, check_take.study_paths_read, the draft's leak_words)
are deliberately NOT built from here: they are substring and regex matches that must catch every round's name.

No model, no network, stdlib only.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

STUDY = "gap-study-4"
STUDY_REL = "evals/gap-study-4"
STUDY_TITLE = "The Gap Study, round 4"

# The published section in docs/EVALS.md. Rounds 1-3 use `gap-study:summary`, `gap-study-2:summary` and
# `gap-study-3:summary` with their closing markers; these differ from all three, so no study's guards can
# read another's section.
SECTION_TITLE = "# The Gap Study, round 4"
SUMMARY_START = "<!-- gap-study-4:summary -->"
SUMMARY_END = "<!-- /gap-study-4:summary -->"
SECTION_END = "<!-- /gap-study-4 -->"

# WHERE THE TWO KINDS OF REPORT LIVE (carried from round 3). Round 2 wrote its pre-freeze reviews and its final
# verifications into one folder, so `ls verification/` counted both at once. Round 3 keeps them apart
# so a fresh run counts each from `ls` alone: pre-freeze reviews with their blindness records in
# review_kit/, final verifications with theirs in verification/. Every file that builds one of those
# paths takes it from here.
REVIEW_DIR = "review_kit"
VERIFY_DIR = "verification"

# The prior round, as data only.
PRIOR_STUDY = "gap-study-3"
PRIOR_REL = "evals/gap-study-3"
ROUND1_REL = PRIOR_REL
ROUND1 = REPO / "evals" / PRIOR_STUDY

# The arms this round runs.
ARMS = ("A", "C", "O", "G")


def rel(*parts: str) -> str:
    """A repository-relative path inside this study: rel("graders", "labels.py")."""
    return "/".join((STUDY_REL, *parts))
