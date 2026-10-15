"""Reviewer's own in-memory mutants of box/sidecar.py's new-folder rescan, run against test_sidecar + test_live_box
of the detached checkout. KILLED when either suite reports a failure or error."""
import io
import sys
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parent / "wt" / "evals" / "gap-study-4"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "tests"))
from box import sidecar  # noqa: E402

PATH = STUDY / "box" / "sidecar.py"
SRC = PATH.read_text()
MUTANTS = {
    "S1 rescan on any CREATE (ISDIR dropped)": ('if "CREATE" in names and "ISDIR" in names and isinstance(ev.path, str):\n            for p in self._present_beneath',
                                               'if "CREATE" in names and isinstance(ev.path, str):\n            for p in self._present_beneath'),
    "S2 stat follows the last link": ("                os.lstat(os.path.join(self.run_tree, p))", "                os.stat(os.path.join(self.run_tree, p))"),
    "S3 discoveries written as accesses": ('_append_line(self._ev(FOUND), {"at": at, "path": path, "source": FOUND_SOURCE})',
                                          '_append_line(self._ev(ACCESS), {"at": at, "path": path, "op": "modify"})'),
    "S4 rescan reports absent paths too": ("            except OSError:\n                continue\n            out.append(p)",
                                           "            except OSError:\n                pass\n            out.append(p)"),
    "S5 rescan of every watched path": ("        for p in self._beneath(folder):\n            try:\n                os.lstat",
                                        "        for p in self.watch:\n            try:\n                os.lstat"),
    "S6 rescan removed": ("            for p in self._present_beneath(ev.path):\n                self._found(",
                          "            for p in []:\n                self._found("),
    "S7 wrong source": ('FOUND, FOUND_SOURCE = "found.jsonl", "rescan-after-create"', 'FOUND, FOUND_SOURCE = "found.jsonl", "rescan"'),
}


def run() -> list:
    bad = []
    for name in ("test_sidecar", "test_live_box"):
        sys.modules.pop(name, None)
        suite = unittest.TestLoader().loadTestsFromName(name)
        r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        bad += [f"{name}:{t.id().split('.', 1)[1]}" for t, _ in r.failures + r.errors]
    return bad


def main():
    print("baseline red:", run())
    for name, (old, new) in MUTANTS.items():
        n = SRC.count(old)
        if n != 1:
            print(f"{name}: SKIPPED (anchor x{n})")
            continue
        exec(compile(SRC.replace(old, new), str(PATH), "exec"), sidecar.__dict__)
        bad = run()
        print(f"{name}: {'KILLED' if bad else 'SURVIVED'} ({len(bad)} red) {bad[:2]}")
        exec(compile(SRC, str(PATH), "exec"), sidecar.__dict__)


if __name__ == "__main__":
    main()
