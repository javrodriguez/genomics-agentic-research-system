#!/usr/bin/env python3
"""The prereg draft's checked_against reads a vendor session's loaded context through that harness's own settled T-10
reader (glitch-f1's stage W ruling 2, Thu 22 Oct 2026, under Javier's standing delegation; lane vendor-settle).

build_draft.checked_sessions derives checked_against from leak_grep.derive, which read every session through
check_take.context_text, Claude Code's attachment sweep: on a Codex or Gemini session that reads 0 bytes, so the
draft's leak check saw none of the vendor CLIs' context. Now leak_grep.session_context reads a codex or gemini session
(its driver ledger's agent.harness) through check_take.vendor_loaded_context_text, the very text the settled T-10
readers sweep (vendor_codex_loaded_context_reads, vendor_gemini_loaded_context_reads), and any other session through
context_text as before.

  LG-bytes     SYNTHETIC codex and gemini takes (tests/vendor_check_fixtures.py) read non-zero context bytes through
               the vendor reader, and void nothing.
  LG-plant     a leak word planted in the SYNTHETIC instruction file (AGENTS.md for codex, the GEMINI.md block for
               gemini) is named by derive and makes build_draft.checked_sessions refuse (the draft's leak check).
  LG-witness   leak_grep.session_context put back to context_text alone (the vendor leg removed): the plant reads
               clean.
  LG-live      over this tree's recorded sessions: every vendor session is read through its harness's reader, every
               readable one non-zero, an unreadable one named as unreadable (never 0 read as clean), and none voided.

SYNTHETIC records and the committed walk records (read in place) only; no take, model, container or network.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_draft  # noqa: E402
import leak_grep  # noqa: E402
import prereg  # noqa: E402

sys.path.insert(0, str(HERE / "tests"))
try:
    import vendor_check_fixtures as vcf  # noqa: E402
finally:
    sys.path.remove(str(HERE / "tests"))

WORD = "evaluation"                                   # a pre-registered leak word (prereg leak_words)
PLANTED = "# Synthetic orientation\n\nThis repository is an evaluation fixture.\n"


def takes(folder: Path, instructions: str = vcf.INSTRUCTIONS) -> list:
    """A SYNTHETIC codex and gemini take folder each under `folder`, their instruction file `instructions`."""
    out = []
    for h in ("codex", "gemini"):
        parts = (vcf.codex_parts(instructions=instructions) if h == "codex"
                 else vcf.gemini_parts(instructions=instructions))
        out.append(vcf.write(folder / h, h, parts))
    return out


CT = leak_grep.checker()                           # the copied checker, loaded by path once (HERE is patched below)


def derive_on(paths: list, root: Path) -> dict:
    with mock.patch.object(leak_grep, "sessions", lambda base=None: list(paths)), \
            mock.patch.object(leak_grep, "checker", lambda: CT), mock.patch.object(leak_grep, "HERE", root):
        return leak_grep.derive()


def claude_only(ct, s):
    """The vendor leg removed: every session read through context_text, as before stage W."""
    return {"harness": None, "reader": "context_text", "ctx": ct.context_text(s), "unreadable": None}


class LGSynthetic(unittest.TestCase):
    def test_lg_bytes_a_clean_synthetic_take_reads_its_context(self):
        self.assertIn(WORD, prereg.load()["leak_words"])
        with tempfile.TemporaryDirectory() as d:
            rec = derive_on(takes(Path(d)), Path(d))
        self.assertEqual(rec["sessions_read"], 2)
        for s in rec["per_session"]:
            with self.subTest(session=s["session"]):
                self.assertGreater(s["context_records_bytes"], 0)
                self.assertEqual(s["words_the_checker_would_void_on"], [])
        self.assertEqual(rec["words_that_would_void_a_session"], [])

    def test_lg_plant_the_drafts_leak_check_fires(self):
        with tempfile.TemporaryDirectory() as d:
            paths = takes(Path(d), PLANTED)
            rec = derive_on(paths, Path(d))
            self.assertEqual(rec["words_that_would_void_a_session"], [WORD])
            self.assertEqual([s["words_the_checker_would_void_on"] for s in rec["per_session"]], [[WORD], [WORD]])
            with mock.patch.object(leak_grep, "sessions", lambda base=None: list(paths)), \
                    mock.patch.object(leak_grep, "checker", lambda: CT), mock.patch.object(leak_grep, "HERE", Path(d)), \
                    self.assertRaises(ValueError):
                build_draft.checked_sessions(prereg.load())

    def test_lg_witness_the_vendor_leg_removed_reads_the_plant_clean(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(leak_grep, "session_context", claude_only):
            rec = derive_on(takes(Path(d), PLANTED), Path(d))
        self.assertEqual(rec["words_that_would_void_a_session"], [])
        self.assertEqual([s["context_records_bytes"] for s in rec["per_session"]], [0, 0])


class LGLive(unittest.TestCase):
    def test_lg_live_every_vendor_session_is_read_by_its_reader(self):
        rec = leak_grep.derive()
        self.assertEqual(rec["words_that_would_void_a_session"], [])
        vendor = [s for s in rec["per_session"] if s.get("harness") in ("codex", "gemini")]
        self.assertTrue(vendor)
        for s in vendor:
            with self.subTest(session=s["session"]):
                self.assertTrue(s["reader"].startswith("vendor_loaded_context_text"), s["reader"])
                if s["context_unreadable"] is None:
                    self.assertGreater(s["context_records_bytes"], 0)
                else:
                    self.assertEqual(s["context_records_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
