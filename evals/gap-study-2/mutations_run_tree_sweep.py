"""Mutations for the run tree's permitted sweep hits (CP3), registered by mutations.register_topic_modules.

Each runs TheRunTreeCarriesOnlyPermittedSweepHits unmutated first (Sandbox.control), breaks one part of the
guard in the throwaway copy, and requires the class to go red naming the planted defect (structural lessons 12
and 13).

THE SANDBOX IS GIVEN THE FILES THE SWEEP READS. Sandbox copies the study, docs/EVALS.md and parts of gars/, but not
README.md, docs/RESULTS.md or the docs folders the draft excludes. Without them the sweep matches nothing, the
whitelist test's non-vacuity check is red before any mutation, and removing an exclusion would change nothing. So
each mutation copies those paths from this repository's working tree into the sandbox and commits them, since the
run tree is exported from the sandbox's own commit.
"""

from __future__ import annotations

import shutil

from mutations import NotYetApplicable, Sandbox, _edit, _prereg, _th, REPO

GUARD = "TheRunTreeCarriesOnlyPermittedSweepHits"
SWEEP_PATHS = ("README.md", "docs/RESULTS.md", "docs/implementation", "docs/reviews", "docs/specs",
               "docs/decisions/0041-glitch-produces-the-v1-0-1-gap-assessment.md")


def _with_the_swept_docs(s: Sandbox) -> None:
    for rel in SWEEP_PATHS:
        src = REPO / rel
        if not src.exists():
            raise NotYetApplicable(f"{rel} is not in this tree, so the sweep has nothing to find there")
        dest = s.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
    s.commit("the swept docs")


def m_implementation_docs_left_in_the_run_tree(s: Sandbox) -> tuple[int, str]:
    """One exclusion entry removed: docs/implementation is exported into the run tree again."""
    _with_the_swept_docs(s)
    s.control(_th(s, GUARD))
    text = _prereg(s).read_text()
    start = text.index('      {\n        "path": "docs/implementation",')
    end = text.index("      },\n", start) + len("      },\n")
    _edit(_prereg(s), text[start:end], "")
    code, out = s.run_out(_th(s, GUARD))
    return (Sandbox.expect(code, out, "docs/implementation/v1.0.1_gap_assessment.md names the study"),
            f"test_harness.py {GUARD}")


def m_permitted_set_never_checked(s: Sandbox) -> tuple[int, str]:
    """The call site: the permitted-set check returns no problem whatever the sweep found."""
    _with_the_swept_docs(s)
    s.control(_th(s, GUARD))
    _edit(s.study / "tests_run_tree_sweep.py", "    problems = []\n    for name in sorted(",
          "    return []\n    problems = []\n    for name in sorted(")
    code, out = s.run_out(_th(s, GUARD))
    return Sandbox.expect(code, out, "a planted file naming the study went unrefused"), f"test_harness.py {GUARD}"


MUTATIONS = [
    ("docs/implementation left in the run tree (one exclusion entry removed)",
     m_implementation_docs_left_in_the_run_tree, True),
    ("the run tree's permitted sweep set is never checked", m_permitted_set_never_checked, True),
]
