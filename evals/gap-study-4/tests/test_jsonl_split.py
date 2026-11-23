#!/usr/bin/env python3
"""Transcripts are split on newline only (review r7's observation, glitch-b5, 16 Oct 2026; the standing lesson "split
JSONL on newline only").

str.splitlines() also splits on \\x0b, \\x0c, \\x1c-\\x1e, \\x85, U+2028 and U+2029. JSON.stringify writes U+2028 and
U+2029 raw inside strings, so a record carrying one (a file's content, an agent's words) became two half-lines: the
checker's readers skipped both halves (an attachment's leak word dropped out of the sweep), and the view refused the
take. Every JSONL reader of check_take, transcript_view and vendor_record_binding now splits on "\\n" alone; no
committed .jsonl file in the repository carries any of the other separators (392 files read when this was built), so
nothing committed reads differently.

  J-sweep    an attachment whose string carries a raw U+2028 is swept whole: its leak word is named (the reviewer's
             ls.py).
  J-records  check_take's record reader reads an operator line carrying U+2028 as one line.
  J-view     the view reads a transcript whose agent text carries U+2028, U+2029 and \\x85, and BoundTranscript holds
             one line per record.
  J-source   no transcript reader in the three modules calls splitlines(); check_take's only two splitlines() calls
             read git output (a commit list and a tree listing), never a transcript.
  J-witness  a reader put back on splitlines() turns a check red.

Synthetic fixtures only.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import transcript_view as tv  # noqa: E402

ct = None


def setUpModule():
    global ct
    saved = list(sys.path)
    import check_take as ct
    sys.path[:] = saved


CC = tv.ROUND3_HARNESS
LS = " "
OP = {"type": "user", "message": {"role": "user", "content": "Run stage 00" + LS + " of the pipeline."}}
SAID = {"type": "assistant", "message": {"model": "m", "content": [
    {"type": "text", "text": "Done." + LS + "Next" + " " + "step\x85here."}]}}
MEMORY = {"type": "attachment", "attachment": {"type": "nested_memory", "content": "a" + LS + " evaluation notes"}}
GIT_SPLITS = ('gs.split("Recent commits:", 1)[1].strip().splitlines()',
              '_git_pinned("ls-tree", "-r", "--name-only", tree).decode("utf-8").splitlines()')


def write(*recs) -> Path:
    d = Path(tempfile.mkdtemp())
    p = d / "transcript.jsonl"
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
    assert LS in p.read_text(encoding="utf-8")
    return p


def sweep_problems(mod=None) -> list:
    import prereg
    mod = mod or ct
    got = mod.context_leaks(mod.context_text(write(OP, MEMORY)), prereg.load())
    return [] if got == {"evaluation"} else [f"J-sweep: the sweep names {sorted(got)}"]


def records_problems(mod=None) -> list:
    mod = mod or ct
    pre = {"harness_delivered_user_records": ct.CHECKER_CONSTANTS["harness_delivered_user_records"]}
    ops, harness, unknown = mod.user_text_records(write(OP, SAID), pre)
    return [] if (ops, harness, unknown) == ([OP["message"]["content"]], [], []) else [f"J-records: {ops}"]


def view_problems(view=None) -> list:
    view = view or tv
    p = write(OP, SAID, MEMORY)
    out = []
    try:
        evs = view.events(CC, p)
        if [e.text for e in evs if e.kind == view.AGENT_TEXT] != [SAID["message"]["content"][0]["text"]]:
            out.append("J-view: the agent's text is not one event")
    except view.ViewError as e:
        out.append(f"J-view: refused: {e}")
    if len(view.BoundTranscript(p)) != 3:
        out.append(f"J-view: BoundTranscript holds {len(view.BoundTranscript(p))} lines, not 3")
    return out


def source_problems() -> list:
    out = []
    for name in ("check_take.py", "transcript_view.py", "vendor_record_binding.py"):
        src = (HERE / name).read_text(encoding="utf-8")
        calls = [m.group(0) for m in re.finditer(r"[^\n]*\.splitlines\(\)", src)]
        allowed = GIT_SPLITS if name == "check_take.py" else ()
        stray = [c.strip() for c in calls if not any(a in c for a in allowed)]
        if stray:
            out.append(f"J-source: {name} still splits with splitlines(): {stray[:2]}")
        if name == "check_take.py" and len(calls) != len(GIT_SPLITS):
            out.append(f"J-source: check_take.py has {len(calls)} splitlines() calls, not the two git reads")
    return out


def mutant(mod, old: str, new: str):
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) < 1:
        raise AssertionError(f"mutation site occurs 0 times in {mod.__file__}: {old!r}")
    m = types.ModuleType(mod.__name__ + "_mutant")
    m.__file__ = mod.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


class TheNewlineSplit(unittest.TestCase):
    def test_j_sweep(self):
        self.assertEqual(sweep_problems(), [])

    def test_j_records(self):
        self.assertEqual(records_problems(), [])

    def test_j_view(self):
        self.assertEqual(view_problems(), [])

    def test_j_source(self):
        self.assertEqual(source_problems(), [])

    def test_j_witnesses(self):
        cases = (
            ("check_take readers on splitlines", lambda: sweep_problems(mutant(
                ct, '.read_text(errors="replace").split("\\n")', '.read_text(errors="replace").splitlines()'))
             + records_problems(mutant(ct, '.read_text(errors="replace").split("\\n")',
                                        '.read_text(errors="replace").splitlines()'))),
            ("the view on splitlines", lambda: view_problems(mutant(tv, 'text.split("\\n")', "text.splitlines()"))),
        )
        for name, run in cases:
            with self.subTest(witness=name):
                try:
                    got = run()
                except Exception as e:  # noqa: BLE001 - a mutant that crashes a reader is red too
                    got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main()
