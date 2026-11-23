"""Reviewer's own in-memory mutants of graders/endstate.py's found.jsonl admission, run against the full
test_endstate suite of the detached checkout. A mutant is KILLED when the suite reports a failure or error."""
import io
import sys
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parent / "wt" / "evals" / "gap-study-4"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "tests"))
import graders.endstate as es  # noqa: E402

SRC = (STUDY / "graders" / "endstate.py").read_text()

MUTANTS = {
    "M1 discoveries skips the health check": ("        self._require_watched()\n        out = []\n        for f in sorted(self._found",
                                              "        out = []\n        for f in sorted(self._found"),
    "M2 no watched-path check on found lines": ("            if self._watched is not None and f[\"path\"] not in {self.tree(w) for w in self._watched}:\n                raise EvidenceError(f\"found line {i}",
                                                "            if False:\n                raise EvidenceError(f\"found line {i}"),
    "M3 any source admitted": ("or f[\"source\"] not in FOUND_SOURCES:", ":"),
    "M4 empty found.jsonl admitted": ("if not isinstance(found, list) or not found:", "if not isinstance(found, list):"),
    "M5 discoveries leak into accesses": ("        for a in sorted(self._access, key=lambda a: a[\"at\"]):",
                                         "        for a in sorted(self._access + [dict(f, op='modify') for f in self._found], key=lambda a: a[\"at\"]):"),
    "M6 found.jsonl not admitted by load": ("OPTIONAL_FILES = (FOUND,)", "OPTIONAL_FILES = ()"),
    "M7 discoveries ignore the turn filter": ("(turn is None or w == (IN_TURN, turn)):\n                out.append(dict(f",
                                              "True:\n                out.append(dict(f"),
    "M8 discoveries 'late' always False": ("late = w[0] == IN_TURN and f[\"at\"] > self.turns[w[1] - 1].ended_at\n            if (path is None or f[",
                                           "late = False\n            if (path is None or f["),
    "M9 found path filter ignored": ("if (path is None or f[\"path\"] == path) and", "if True and"),
}


def run_suite() -> unittest.TestResult:
    loader = unittest.TestLoader()
    if "test_endstate" in sys.modules:
        del sys.modules["test_endstate"]
    suite = loader.loadTestsFromName("test_endstate")
    r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return r


def main():
    base = run_suite()
    print(f"baseline: ran {base.testsRun}, failures {len(base.failures)}, errors {len(base.errors)}")
    for name, (old, new) in MUTANTS.items():
        n = SRC.count(old)
        if n != 1:
            print(f"{name}: SKIPPED (anchor found {n} times)")
            continue
        exec(compile(SRC.replace(old, new), str(STUDY / "graders" / "endstate.py"), "exec"), es.__dict__)
        r = run_suite()
        bad = [t.id().split(".", 1)[1] for t, _ in r.failures + r.errors]
        print(f"{name}: {'KILLED' if bad else 'SURVIVED'} (ran {r.testsRun}, red {len(bad)}) {bad[:3]}")
        exec(compile(SRC, str(STUDY / "graders" / "endstate.py"), "exec"), es.__dict__)


if __name__ == "__main__":
    main()
