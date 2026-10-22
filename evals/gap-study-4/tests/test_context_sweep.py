#!/usr/bin/env python3
"""The loaded-context leak sweep reads DECODED text (glitch-f1's ruling "CONTEXT-SWEEP GAP read", Wed 21 Oct 2026,
22:26 EDT, option A, under Javier's standing delegation; evidence /Users/javrodher/aegis-builds/CTX-SWEEP-GAP-
20261021.md; lane vendor-settle stage K2).

context_text (check_take.py, round 3's lines) joins one swept text per attachment record and context_leaks matches
`\\b<word>\\b` over it. Until K2 that text was the RAW JSON line (minus an admitted edited_text_file's snippet), where a
newline is the two characters `\\n`: a word at a line start read `nword`, with no word boundary, so a leak word right
after an escaped newline (or tab, or any `\\uXXXX` escape) was never seen. K2 keeps the raw cut (the snippet carve-out
and its fail-closed guards, review r6 and r7, unchanged in check_take._cut_attachment_line) and sweeps its decoded
text: every key and every value of the record, strings decoded, a duplicated key's every copy kept.

  CS-plant     through check_take's own context_text and context_leaks: a leak word after an escaped newline, an
               escaped tab, a `\\u` escape of its first letter, inside a key, and inside a duplicated key's dropped
               copy, is named; the same text with a space is named too (the raw sweep already saw that).
  CS-carve     the snippet carve-out is kept: the word after an escaped newline inside an admitted edited_text_file's
               snippet names no leak; in its filename it does.
  CS-excusal   an excusal still forgives only a contained hit: the pinned allowlist phrase after an escaped newline is
               forgiven, the bare word after one is not.
  CS-callers   the two other users of the sweep read the decoded text: subagent_leak_problems names the word in a
               sub-agent file's attachment, and leak_grep's derive (the copied checker loaded by path) counts it.
  CS-witness   check_take compiled in memory with the old raw sweep (the cut line returned undecoded) turns CS-plant
               red; with the decode dropping keys, or keeping only a duplicated key's last copy, it turns red too.

Synthetic records only; no take, model, container or network.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import check_take  # noqa: E402
import prereg  # noqa: E402

W = "evaluation"
OP = {"type": "user", "message": {"content": "Run stage 00."}}


def att(**fields) -> dict:
    return {"type": "attachment", "attachment": {"type": "date", **fields}}


def sweep(ct, *lines: str) -> set:
    """context_leaks(context_text(...)) of a transcript holding the operator line and `lines`, raw."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "transcript.jsonl"
        p.write_text("\n".join([json.dumps(OP), *lines]) + "\n", encoding="utf-8")
        return ct.context_leaks(ct.context_text(p), prereg.load())


def plant_cases() -> dict:
    """{name: (raw line, the leak words the sweep must name)}."""
    return {
        "a word after an escaped newline": (json.dumps(att(date=f"intro\n{W.capitalize()} of this run")), {W}),
        "a word after an escaped tab": (json.dumps(att(date=f"intro\t{W}")), {W}),
        "a word whose first letter is a \\u escape": ('{"type": "attachment", "attachment": {"type": "date", '
                                                      '"date": "intro \\u0065' + W[1:] + '"}}', {W}),
        "a word after a newline inside a key": (json.dumps({"type": "attachment", "attachment": {
            "type": "date", f"x\n{W}": "1"}}), {W}),
        "a word after a newline in a duplicated key's first copy": (
            '{"type": "attachment", "note": "intro\\n' + W + '", "note": "x", "attachment": {"type": "date"}}', {W}),
        "a word after a space (seen raw too)": (json.dumps(att(date=f"intro {W}")), {W}),
        "no leak word": (json.dumps(att(date="intro\nordinary text")), set()),
    }


def plant_problems(ct) -> list:
    out = []
    for name, (line, want) in plant_cases().items():
        json.loads(line)
        got = sweep(ct, line)
        if got != want:
            out.append(f"CS-plant {name}: the sweep names {sorted(got)}, not {sorted(want)}")
    return out


def carve_problems(ct) -> list:
    out = []
    snippet = {"type": "attachment", "attachment": {"type": "edited_text_file", "filename": "/a/HISTORY.md",
                                                    "snippet": f"     1\tintro\n{W} notes\n"}}
    if sweep(ct, json.dumps(snippet)) != set():
        out.append("CS-carve: a word in an admitted snippet after an escaped newline names a leak")
    named = dict(snippet, attachment=dict(snippet["attachment"], filename=f"/a/x\n{W}/HISTORY.md"))
    if sweep(ct, json.dumps(named)) != {W}:
        out.append("CS-carve: a word in the filename after an escaped newline names no leak")
    return out


def excusal_problems(ct) -> list:
    pre = prereg.load()
    phrases = [e["phrase"] for e in pre.get("leak_context_excusals", []) if "allowlist" in e["phrase"].lower()]
    if not phrases or "allowlist" not in pre["leak_words"]:
        return ["CS-excusal: the pre-registration no longer pins an allowlist excusal; the case needs another"]
    out = []
    if sweep(ct, json.dumps(att(date=f"skills:\n{phrases[0]}"))) != set():
        out.append("CS-excusal: the pinned phrase after an escaped newline is not forgiven")
    if sweep(ct, json.dumps(att(date="skills:\nallowlist"))) != {"allowlist"}:
        out.append("CS-excusal: the bare word after an escaped newline is forgiven")
    return out


def callers_problems(ct) -> list:
    out = []
    line = json.dumps(att(date=f"intro\n{W}"))
    with tempfile.TemporaryDirectory() as d:
        sub = Path(d) / "agent-0001.jsonl"
        sub.write_text(line + "\n", encoding="utf-8")
        with mock.patch.object(ct, "subagent_files", lambda path: {"0001": sub}):
            got = ct.subagent_leak_problems(Path(d) / "transcript.jsonl", prereg.load())
        if not any(p.startswith("[leak-in-loaded-context] ") and W in p for p in got):
            out.append(f"CS-callers: subagent_leak_problems does not name the word: {got}")
    import leak_grep
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "transcript.jsonl"
        p.write_text("\n".join([json.dumps(OP), line]) + "\n", encoding="utf-8")
        # lane vendor-settle stage X (review 0df1437 MINOR 3): leak_grep reads a session's ledger for its harness and
        # refuses one it cannot read, so the synthetic Claude Code session carries one
        (Path(d) / "driver-ledger.json").write_text(json.dumps({"agent": {"harness": "claude-code"}}), encoding="utf-8")
        with mock.patch.object(leak_grep, "sessions", lambda base=None: [p]), \
                mock.patch.object(leak_grep, "checker", lambda: ct), \
                mock.patch.object(leak_grep, "HERE", Path(d)):
            rec = leak_grep.derive()
    if rec["words_that_would_void_a_session"] != [W]:
        out.append(f"CS-callers: leak_grep's derive does not count the word: {rec['words_that_would_void_a_session']}")
    return out


def all_problems(ct) -> list:
    return plant_problems(ct) + carve_problems(ct) + excusal_problems(ct) + callers_problems(ct)


def ct_mutant(old: str, new: str):
    src = Path(check_take.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times: {old!r}")
    m = types.ModuleType("check_take_cs_mutant")
    m.__file__ = check_take.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), check_take.__file__ + " (witness)", "exec"), m.__dict__)  # noqa: S102
    finally:
        del sys.modules[m.__name__]
    return m


WITNESSES = (
    ("the raw cut swept undecoded (before K2)", "    return _decoded_text(_cut_attachment_line(rec, line))\n",
     "    return _cut_attachment_line(rec, line)\n"),
    ("keys dropped from the decoded text", "            out.append(key)\n", "            pass\n"),
    ("a duplicated key's last copy only", "        doc = json.loads(line, object_pairs_hook=_AllPairs)\n",
     "        doc = json.loads(line, object_pairs_hook=lambda pairs: _AllPairs(dict(pairs).items()))\n"),
)


class TheDecodedSweep(unittest.TestCase):
    def test_cs_plant_carve_excusal_callers(self):
        self.assertEqual(all_problems(check_take), [])

    def test_cs_witness_each_mutant_goes_red(self):
        for name, old, new in WITNESSES:
            with self.subTest(witness=name):
                self.assertNotEqual(plant_problems(ct_mutant(old, new)), [], f"witness {name} stayed green")


if __name__ == "__main__":
    unittest.main()
