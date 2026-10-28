#!/usr/bin/env python3
"""Lane gap-rewalk-fix (Gap Study round 4): the rewalk merge's walk gate, with the Lane-orchestrator's rulings.

glitch-45's rulings on the battery diagnosis of the rewalk merge 13e8301f (Tue 27 Oct 2026, under Javier's standing
delegation). fixture_walk.py --check read five walks unplaced; each is a recorded per-walk exception in the class of
its precedent, never a general class:
  - w172 `/tmp/run-e680031a-finalize.json` and w194 `/tmp/s01.json`: the agent's own temp files (w023's class);
  - w179, w180 and w198 `/home/<user`: the GARS fixture's quoted placeholder `/gpfs/home/<user>` (w142/w158's class).

  RW1-exceptions  each of the five reads unplaced on exactly its one path with no exception of its own, and
                  `excepted` on that path at exactly its recorded lines with it; the same path named on one more line
                  of a copy is not excused; the walk's lines under another walk's name are not excused; and no
                  committed exception is stale.

Reads committed walk records and copies them into temporary folders only; no model, network or container.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)
sys.path.insert(0, str(HERE))

import fixture_walk as fw  # noqa: E402

sys.path[:] = _PATH

# walk -> (the one path, the transcript lines naming it), as glitch-45 ruled them
NEW = {"w172": ("/tmp/run-e680031a-finalize.json", [86, 93, 94]),
       "w194": ("/tmp/s01.json", [69]),
       "w179": ("/home/<user", [11, 57]),
       "w180": ("/home/<user", [11, 86]),
       "w198": ("/home/<user", [11, 41])}


def rw1_exceptions(mod, p="RW1-exceptions"):
    out = []
    try:
        for walk, (path, lines) in NEW.items():
            t = mod.WALKS / walk / "transcript.jsonl"
            others = tuple(e for e in mod.RECORDED_EXCEPTIONS if e["walk"] != walk)
            with mock.patch.object(mod, "RECORDED_EXCEPTIONS", others):
                rec = mod.replay(t)
            if rec["verdict"] != "unplaced" or rec["unplaced_paths"] != [path]:
                out.append(f"{p}: {walk} without its exception: {rec['verdict']} {rec['unplaced_paths']}")
            rec = mod.replay(t)
            got = [(e["path"], e["lines"]) for e in rec["recorded_exceptions"]]
            if rec["verdict"] != "excepted" or got != [(path, lines)]:
                out.append(f"{p}: {walk} with its exception: {rec['verdict']} {got}")
            with tempfile.TemporaryDirectory() as d:
                extra = Path(d) / walk
                shutil.copytree(t.parent, extra)
                with open(extra / "transcript.jsonl", "a") as f:
                    f.write(json.dumps({"type": "assistant", "message": {"content": [
                        {"type": "text", "text": f"and again {path}> here"}]}}) + "\n")
                rec = mod.replay(extra / "transcript.jsonl")
                if rec["verdict"] != "unplaced":
                    out.append(f"{p}: {walk}'s path on one more line: {rec['verdict']}")
                other = Path(d) / "w999"
                shutil.copytree(t.parent, other)
                rec = mod.replay(other / "transcript.jsonl")
                if rec["verdict"] != "unplaced":
                    out.append(f"{p}: {walk}'s lines under another walk's name: {rec['verdict']}")
        stale = mod.stale_exception_problems(sorted(str(t) for t in mod.WALKS.glob("*/transcript.jsonl")))
        if stale:
            out.append(f"{p}: stale exceptions: {stale}")
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]
    return out


class TestGapRewalkFix(unittest.TestCase):
    def test_rw1_the_five_rewalk_exceptions_are_bound_to_their_lines(self):
        self.assertEqual(rw1_exceptions(fw), [])


if __name__ == "__main__":
    unittest.main()
