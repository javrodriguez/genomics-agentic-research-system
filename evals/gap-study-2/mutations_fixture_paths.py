"""Mutations for the fixture roots (CP3), registered by mutations.register_topic_modules.

Each runs TheFixtureNamesNoPathOutsideTheRunTree unmutated first (Sandbox.control), puts round 1's build back in
the throwaway copy, and requires the class to go red naming a path outside the run tree (structural lessons 12
and 13). Both are caught by the stand-in workspace test, which is the one that runs in the sandbox.
"""

from __future__ import annotations

from mutations import Sandbox, _edit, _th

GUARD = "TheFixtureNamesNoPathOutsideTheRunTree"
RED = "the fixture names a path outside the run tree"


def m_project_fixture_built_against_the_checkout(s: Sandbox) -> tuple[int, str]:
    """The call site: the driver hands the project generator the study's checkout instead of its run tree."""
    s.control(_th(s, GUARD))
    _edit(s.study / "drive.py",
          '"--workspace", str(run_tree / "gars"), "--staging", str(run_tree / "data" / "staging")]',
          '"--workspace", str(REPO / "gars"), "--staging", str(REPO / "data" / "staging")]')
    code, out = s.run_out(_th(s, GUARD))
    return Sandbox.expect(code, out, RED), f"test_harness.py {GUARD}"


def m_project_generator_ignores_its_staging_root(s: Sandbox) -> tuple[int, str]:
    """The generator writes the source under the checkout whatever --staging says, and stage 00 records it."""
    s.control(_th(s, GUARD))
    _edit(s.study / "fixtures" / "gen_project.py",
          "    src_root = staging / name\n",
          '    src_root = REPO / "data" / "staging" / name\n')
    code, out = s.run_out(_th(s, GUARD))
    return Sandbox.expect(code, out, RED), f"test_harness.py {GUARD}"


MUTATIONS = [
    ("the project fixture built against the checkout at the driver's call site",
     m_project_fixture_built_against_the_checkout, False),
    ("the project generator ignores its --staging root", m_project_generator_ignores_its_staging_root, False),
]
