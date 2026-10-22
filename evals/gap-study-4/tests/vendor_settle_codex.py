#!/usr/bin/env python3
"""Lane vendor-settle: the Codex rows' settlement cases (stage K made this module empty; stage C, the Codex builder, is
its only writer). tests/test_vendor_check.py imports it and merges its three tables with the other harness's module
(tests/vendor_settle_gemini.py); a key here must be a ("codex", <key>) of check_take.VENDOR_PENDING_ROWS, and no key may
appear in both modules.

  SAME_FIRES   ("codex", key) -> fire(fixture_path) -> list of problems: the row's site (or vendor_check) run on a
               planted copy of the row's RECORDED fixture (tests/vendor_plant.planted); VPSameFires requires a line
               carrying the row's reason, for every SAME row of the live map.
  CLEAN_CASES  ("codex", key) -> case() -> (got, want): the reader on the unmodified RECORDED copy against the
               independent value the case's own plain-json parser derives; VPSettleCases requires got == want.
  NC_CASES     ("codex", key) -> case() -> list of problems: a NOT COMPARABLE row's partial check on its non-hollow
               plant; VPSettleCases requires a non-empty list whose every line carries the row's reason.

RECORDED folders for this harness: tests/fixtures/recorded-codex-w-o46 (also w-o47, w-o7).

Stage C also runs this file directly (checks.d/vendor-settle-c.txt) for the tests the three tables cannot express:

  C-reach      K's open point 2, ruled by glitch-f1: the clean w-o46 copy's one read-outside-the-checkout event was a
               code-mode tool output whose printed text is a JSON document; read as encoded text, its escaped newlines
               joined a listing of run-tree files into one path outside the run tree (a false event), and an outside
               path after an escaped newline was not seen at all (a blind spot). The rollout's returned tool texts are
               read decoded when they are a JSON object or array (check_take.vendor_codex_returned_documents): the
               clean copy reads no outside path (the test's own count), and an outside path planted after an escaped
               newline in that text fires.

Every case reads the RECORDED folders through scratch copies (vendor_plant.planted); the committed fixtures are never
written. No take, model, container or network.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
_ADDED = [p for p in (str(HERE), str(HERE / "tests")) if p not in sys.path]
sys.path[:0] = _ADDED
try:
    import check_take as ct  # noqa: E402
    import vendor_plant as vp  # noqa: E402
finally:
    for _p in _ADDED:
        sys.path.remove(_p)

O46 = "recorded-codex-w-o46"
O47 = "recorded-codex-w-o47"
O7 = "recorded-codex-w-o7"
LAST_O46 = "session/native-turn-3.jsonl"


def _rollout(folder: Path) -> list:
    """The last retained rollout's records, parsed here with plain json (never a check_take helper)."""
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    name = ledger["native_snapshots"][-1]["file"]
    return [json.loads(x) for x in (folder / "session" / name).read_text(encoding="utf-8").split("\n") if x]


def _cwd(records: list) -> str:
    return records[0]["payload"]["cwd"]


# ---- C-reach: K's open point 2 ---------------------------------------------------------------------------------------
# The code-mode output part of w-o46's native-turn-3 line 16: its text is a JSON document whose "output" lists files of
# the run tree, one per line; in the file the escaped newline is written `\\n`.
LISTING = b"/tmp/run-8617d222\\\\nCLAUDE.md"
OUTSIDE = b"/tmp/run-8617d222\\\\n/tmp/run-0123abcd/notes.md\\\\nCLAUDE.md"


def independent_outside_count(folder: Path) -> int:
    """How many paths of the rollout's code-mode output texts that decode as JSON objects sit outside the run tree, by
    this test's own parse: each such text's string values split on newlines, every line naming /tmp/ checked against
    the session's cwd."""
    records = _rollout(folder)
    cwd = _cwd(records)
    n = 0

    def strings(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for v in x.values():
                yield from strings(v)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v)
    for r in records:
        p = r["payload"]
        if r["type"] != "response_item" or p.get("type") != "custom_tool_call_output":
            continue
        for part in p["output"]:
            try:
                doc = json.loads(part["text"])
            except ValueError:
                continue
            if not isinstance(doc, (dict, list)):
                continue
            for s in strings(doc):
                for line in s.split("\n"):
                    if line.startswith("/tmp/") and not (line == cwd or line.startswith(cwd + "/")):
                        n += 1
    return n


class CReach(unittest.TestCase):
    def reach(self, plant):
        return ct.vendor_reach(plant.path, "codex", run_tree=ct.vendor_session_cwd(plant.path, "codex"))

    def test_c_reach_the_clean_copy_reads_no_outside_path(self):
        with vp.planted(O46) as plant:
            self.assertEqual(independent_outside_count(plant.folder), 0)
            got = self.reach(plant)
        self.assertEqual(got["outside"], [], got["problems"])
        self.assertEqual([p for p in got["problems"] if p.startswith(f"[{ct.EVENT_OUTSIDE}]")], [])

    def test_c_reach_an_outside_path_after_an_escaped_newline_fires(self):
        with vp.planted(O46, vp.replace_bytes(LAST_O46, LISTING, OUTSIDE)) as plant:
            self.assertEqual(independent_outside_count(plant.folder), 1)
            got = self.reach(plant)
        # one path, read by both legs that judge another take's run tree (the home-and-temp leg and the temp leg), as
        # C's readers count a Claude Code take's
        self.assertTrue(got["outside"], got)
        self.assertTrue(all(x.endswith("/run-0123abcd/notes.md") for x in got["outside"]), got["outside"])


SAME_FIRES: dict = {}
CLEAN_CASES: dict = {}
NC_CASES: dict = {}


if __name__ == "__main__":
    unittest.main()
