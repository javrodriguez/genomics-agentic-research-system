#!/usr/bin/env python3
"""Lane vendor-admission T4 edit B (glitch-b5 rounds 14 and 15, Sun 18 Oct 2026; review e-71a2b94 finding 1, MAJOR):
the drive writes a vendor take's host turn envelopes. TakeDriver._take_records' vendor branch writes transcript.jsonl,
one schema-1 harness-turn per ledger turn row (vendor_record_binding's schema), and the ledger's transcript stays None
(round 15 ruling 1, option (b)), so drive.take_checker's C3 no longer reads every codex and gemini take as
readers-disagree before checker_for.

  EB-road     a codex take (test_pending_codex_walk's CodexBox) and a gemini take (test_pending_walk's GeminiBox),
              each with its reader registered so the native cross-check agrees, driven through the driver with
              drive.take_checker as its checker: the take folder holds transcript.jsonl, the take's commit scan
              covers it as a transcript, its ledger's transcript stays None (round 15 ruling 1: no reader reads that
              key for a vendor take), vendor_record_binding.bound_items reads it, each envelope carries the row's n and sent, its turn's stream
              by basename and sha256 and the CLI's own session id, and take_checker reaches checker_for and the vendor
              entry (its body stood in) with C3 adding no readers-disagree.
  EB-claude   a claude-code take through test_drive_loop's road (the real Claude Code adapter on ClaudeBox), with a
              session file and without one: driver-ledger.json, transcript.jsonl and the take folder's listing are
              byte-identical under drive.py and under drive.py before edit B (check_vendor_sources.without_edit_b),
              P0's equal-before-and-after shape.
  EB-witness  drive.py compiled in memory with the writer gated off (edit B taken out), the writer also run for
              claude-code, an envelope's sent taken from another row, and an envelope's sha256 taken from another
              stream: each goes red.

The masked-address case (review finding 2) is not here: option (a) needs a drive.py change beyond edit B, asked of
glitch-b5 in the lane file. Fakes and synthetic strings only, inside test_box_integration's process guard with
test_drive_loop's checker world, in scratch folders: no take, model, vendor, network, Docker or credential.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
HERE = TESTS.parent
for p in (HERE, TESTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import check_vendor_sources as cvs  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import test_drive_loop as tdl  # noqa: E402
import test_vendor_walk_road as tvw  # noqa: E402

READERS_DISAGREE = "readers-disagree"


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def compiled(src: str, name: str) -> types.ModuleType:
    """drive.py's text `src`, compiled in memory as its own module (never written to disk)."""
    mod = types.ModuleType(name)
    mod.__file__ = tbi.drive.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, tbi.drive.__file__ + " (edit B witness)", "exec"), mod.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(name, None)
    return mod


def drive_source() -> str:
    return Path(tbi.drive.__file__).read_text(encoding="utf-8")


# ---- EB-road --------------------------------------------------------------------------------------------------------
def vendor_road(test, drive, harness):
    """One vendor take through `drive`'s WalkDriver on its fake box, its reader registered (the cross-check agrees)
    and drive.take_checker its checker: (the take folder, the checker's record, the vendor entry's calls, the files
    and scan kinds the take's commit scan stages)."""
    import native_reader_registration as nrr
    import test_codex_adapter as tca
    import test_pending_codex_walk as tpcw
    import test_pending_walk as tpw
    if harness == "codex":
        road = tpw.Road(test, harness="codex", box=tpcw.CodexBox(), run_turn=tca.stub_run_turn,
                        row={"arm": "O", "model": tpcw.MODEL, "agent": {"harness": "codex", "version": tpcw.CLI}})
        readers = {"codex": nrr.codex_reader}
    else:
        road = tpw.Road(test)
        readers = {"gemini": nrr.gemini_reader}
    import check_take as ct
    seen, records = [], []
    checker = drive.take_checker(design_for=lambda row, take: tvw.vendor_design_for(ct)(row, take.spec.run_tree),
                                 records="walks")
    road.driver.checker = lambda row, take, turns: records.append(checker(row, take, turns)) or records[-1]
    row = dict(road.row)
    with mock.patch.object(nrr, "production_readers", lambda study=None: readers), tbi.spying(road.rig.spy), \
            tvw.vendor_entry(ct, [], seen):
        cid = road.driver.launch(row)
        try:
            road.driver.drive(row, cid)
        finally:
            road.driver.remove(cid)
    folders = sorted((road.study / "rehearsals").iterdir())
    folder = [f for f in folders if (f / "driver-ledger.json").is_file()][-1]
    take = road.driver._by_slot[row["slot"]]
    return folder, records, seen, road.driver.take_files(take)      # what the commit scan stages, by the closed map


def road_problems(test, drive, harness) -> list:
    import vendor_record_binding as vrb
    import transcript_view as tv
    import test_pending_codex_walk as tpcw
    import test_pending_walk as tpw
    out = []
    folder, records, seen, scanned = vendor_road(test, drive, harness)
    led = json.loads((folder / "driver-ledger.json").read_text())
    if led.get("cross_check") != []:
        return [f"{harness}: the native cross-check does not agree ({led.get('cross_check')}), so nothing is read"]
    path = folder / "transcript.jsonl"
    if not path.is_file():
        out.append(f"{harness}: the take folder holds no transcript.jsonl")
    if led.get("transcript") is not None:     # round 15 ruling 1: None for a vendor take, as the registration reads it
        out.append(f"{harness}: the ledger records transcript {led.get('transcript')!r}, not None")
    if (str(path), "transcript") not in [(str(p), kind) for p, kind in scanned]:
        out.append(f"{harness}: the take's commit scan does not cover transcript.jsonl as a transcript ({scanned})")
    if path.is_file():
        try:
            vrb.bound_items(harness, path)
        except tv.ViewError as e:
            out.append(f"{harness}: bound_items refuses the envelopes: {e}")
        envs = [json.loads(x) for x in path.read_text().splitlines()]
        vid = tpcw.TID if harness == "codex" else tpw.SID
        want = [{"type": "harness-turn", "harness": harness, "session_id": led["session_id"],
                 "vendor_session_id": vid, "n": k, "sent": turn["sent"], "stream": name,
                 "sha256": hashlib.sha256((folder / name).read_bytes()).hexdigest()}
                for k, (name, turn) in enumerate(zip(led["streams"], led["turns"]), 1)]
        if envs != want or len(envs) != len(led["turns"]):
            out.append(f"{harness}: the envelopes read {envs}, not one per ledger turn row {want}")
    if len(seen) != 1:
        out.append(f"{harness}: take_checker reached the vendor entry {len(seen)} times, not once")
    reasons = [r for rec in records for r in rec["checker_reasons"]]
    if len(records) != 1 or READERS_DISAGREE in reasons:
        out.append(f"{harness}: the checker's records {records} (C3's readers-disagree, or no reading)")
    return out


# ---- EB-claude ------------------------------------------------------------------------------------------------------
def claude_bytes(drive) -> list:
    """A claude-code take's driver-ledger.json, transcript.jsonl and folder listing, with a session file and
    without one."""
    out = []
    for kw in ({}, {"no_session": True}):
        take, _, _ = tdl.drive_claude(drive, tdl.TWO, tdl.TWO_REPLIES, **kw)
        got = {"listing": sorted(os.listdir(take.folder))}
        for name in ("driver-ledger.json", "transcript.jsonl"):
            p = Path(take.folder) / name
            got[name] = p.read_bytes() if p.is_file() else None
        out.append(got)
    return out


def claude_problems(drive, before) -> list:
    out = []
    got, want = claude_bytes(drive), claude_bytes(before)
    for case, g, w in zip(("with a session file", "with no session file"), got, want):
        for key in w:
            if g[key] != w[key]:
                out.append(f"claude-code {case}: {key} differs from drive.py before edit B")
    return out


# ---- EB-witness -----------------------------------------------------------------------------------------------------
def edit_b_text(src: str) -> str:
    span = cvs.edit_b_span(src)
    return "".join(src.splitlines(keepends=True)[span[0] - 1:span[1]])


def claude_too(src: str) -> str:
    """drive.py with edit B's writer also run on the claude-code branch, right after the published transcript's
    cross-check."""
    anchor = "            take.cross_check = _cc.cross_check(recs, text, session_id=ident[\"session_id\"]) if cc else []\n"
    if src.count(anchor) != 1:
        raise tbi.WitnessNotPerformed("the claude-code branch's anchor moved")
    return src.replace(anchor, anchor + edit_b_text(src))


def edited(src: str, old: str, new: str) -> str:
    if src.count(old) != 1:
        raise tbi.WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
    return src.replace(old, new)


WITNESSES = {
    "the writer gated off": ("road", lambda src: cvs.without_edit_b(src)),
    "the writer run for claude-code": ("claude", claude_too),
    "an envelope's sent from another row": ("road", lambda src: edited(
        src, "\"n\": k, \"sent\": r.get(\"sent\"),", "\"n\": k, \"sent\": rows[0].get(\"sent\"),")),
    "an envelope's sha256 of another stream": ("road", lambda src: edited(
        src, "\"sha256\": hashlib.sha256(raw).hexdigest() if stream else None})",
        "\"sha256\": hashlib.sha256(Path(turns[0].stream_path).read_bytes()).hexdigest() if stream else None})")),
}


class EditBRoad(unittest.TestCase):
    def test_eb_a_vendor_take_carries_its_turn_envelopes(self):
        for harness in ("codex", "gemini"):
            with self.subTest(harness=harness), tvw.world():
                try:
                    self.assertEqual(road_problems(self, tbi.drive, harness), [])
                finally:
                    self.doCleanups()             # each road's patches (run_turn among them) end with its road


class EditBClaude(unittest.TestCase):
    def test_eb_a_claude_code_take_is_byte_identical(self):
        before = compiled(cvs.without_edit_b(drive_source()), "drive_before_edit_b")
        self.assertEqual(claude_problems(tbi.drive, before), [])


class EditBWitnesses(unittest.TestCase):
    def test_eb_witness_each_mutant_goes_red(self):
        src = drive_source()
        if cvs.edit_b_span(src) is None:
            self.fail("drive.py holds no edit B, so no witness can be performed")
        before = compiled(cvs.without_edit_b(src), "drive_before_edit_b")
        for name, (road, edit) in WITNESSES.items():
            with self.subTest(witness=name):
                mutant = compiled(edit(src), "drive_edit_b_witness")
                if road == "claude":
                    self.assertNotEqual(claude_problems(mutant, before), [], f"witness {name} stayed green")
                    continue
                for harness in ("codex", "gemini"):
                    with tvw.world(), mock.patch.dict(sys.modules, {"drive": mutant}):
                        try:
                            self.assertNotEqual(road_problems(self, mutant, harness), [],
                                                f"witness {name} stayed green on {harness}")
                        finally:
                            self.doCleanups()


if __name__ == "__main__":
    unittest.main()
