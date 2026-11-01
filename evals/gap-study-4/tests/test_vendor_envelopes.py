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
              key for a vendor take), vendor_record_binding.bound_items reads it, each envelope carries the row's n and
              sent, its turn's stream by basename and sha256 and the CLI's own session id, and take_checker reaches
              checker_for and the vendor entry (its body stood in) with C3 adding no readers-disagree.
  EB-claude   a claude-code take through test_drive_loop's road (the real Claude Code adapter on ClaudeBox), with a
              session file, without one, and with the account address in its replies masked by the drive's scan:
              driver-ledger.json, transcript.jsonl, the take folder's listing and the records TakeDriver.drive returns
              are byte-identical under drive.py and under drive.py before edits B and C
              (check_vendor_sources.without_edits), P0's equal-before-and-after shape.
  EC-mask     edit C (glitch-b5 round 15 ruling 2; review e-71a2b94 finding 2, option (a)): the account address in a
              codex take's turn streams and rollout, and in a gemini take's turn streams and session, driven through
              the walk driver, masked in place by the real drive scan (box/scan_record.scan, the address handed to it
              as an email secret), then checked by drive.take_checker with the vendor entry's body stood in by the
              vendor readers' own event counts (check_take.vendor_event_counts, which reads the envelopes' streams
              and the ledger-named last snapshot by their sha256): account-email counts 1, the take is not held, and
              every envelope's and every ledger-named snapshot's sha256 is that of the masked bytes on disk.
  EC-gate     check_vendor_sources piece EB holds edit C's gate direction (glitch-b5 round 16, review f-981e871 NIT 4):
              drive.py with edit C's `if` test turned to `not in VENDOR_HARNESSES`, negated, widened by an `or`,
              widened in its set, or asked of a constant harness instead of the row's fails piece EB, and drive.py as
              it stands passes.
  EB-witness  drive.py compiled in memory with the writer gated off (edit B taken out), the writer also run for
              claude-code, an envelope's sent taken from another row, and an envelope's sha256 taken from another
              stream; and for edit C, the rebinding taken out (the review's masked-address mutant), the envelopes
              left on the unmasked bytes, the snapshots left on the unmasked bytes, and the rebinding also run for
              claude-code with its envelope write unguarded: each goes red.
  ED-record   edit D (lane vendor-b11 round 4, glitch-26's ruling R4-1): the drive hands each arm O and G adapter its
              take's config folder record and routes run_take.ConfigFolderRefused as the settings guard is. Piece EB
              records it as edits B and C are: drive.py's sha256 after edit D is pinned (POST_EDIT_D_DRIVE_SHA256),
              the edit names its ruling and reason, drive.py with edit D taken out (without_edit_d) and then edits B
              and C is drive.py before edit B, and drive.py with any one of edit D's hunks taken out, or one line
              moved outside the three edits, fails piece EB.

Fakes and synthetic strings only (the address is test_box_integration's synthetic .invalid one), inside
test_box_integration's process guard with test_drive_loop's checker world, in scratch folders: no take, model,
vendor, network, Docker or credential.
"""

from __future__ import annotations

import contextlib
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
ADDRESS = tbi.EMAIL          # test_box_integration's synthetic account address, never a real one
# the claude-code case's address: ClaudeBox's session context already carries ADDRESS, which scrub.py removes there and
# refuses anywhere else, so the replies carry another synthetic one
OTHER_ADDRESS = "synthetic.operator@example.invalid"


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
def addressed(test, harness) -> None:
    """The fake box's agent text "Done." carries ADDRESS in every turn stream and in the native session alike, so the
    native cross-check still agrees on the unmasked bytes: patches started now and stopped with the test's cleanups."""
    import test_pending_codex_walk as tpcw
    import test_pending_walk as tpw
    said = f"Done. Mail {ADDRESS} for the notes."
    mod, stream, native = (tpcw, "exec_stream", "rollout") if harness == "codex" else (tpw, "stream", "native")
    real_stream, real_native = getattr(mod, stream), getattr(mod, native)
    for patch in (mock.patch.object(mod, stream, lambda *a, **k: real_stream(*a, **k).replace("Done.", said)),
                  mock.patch.object(mod, native, lambda *a, **k: real_native(*a, **k).replace(
                      b"Done.", said.encode("utf-8")))):
        patch.start()
        test.addCleanup(patch.stop)


@contextlib.contextmanager
def counting_entry(ct, seen):
    """check4_walk_vendor's body stood in by the vendor readers' own event counts on the bytes the drive left
    (check_take.vendor_event_counts: the reach through the envelopes' streams and the ledger-named last snapshot, each
    by its sha256, and the account-email marker); a count those readers cannot read raises CheckRefused, which holds
    the take. checker_for, _vendor_entry, _vendor_side and drive.take_checker stay real."""
    def stand_in(path, task, half, walk, *, wording_script, arm, design, table=None):
        seen.append(ct.vendor_design_constants_sha256(design))
        events = ct.vendor_event_counts(path, design.harness)
        return {"reasons": [], "problems": [], "events": events,
                "outside_reach": sum(v for k, v in events.items() if k != ct.EVENT_EMAIL)}
    with mock.patch.object(ct, "check4_walk_vendor", stand_in):
        yield


def vendor_road(test, drive, harness, address=False):
    """One vendor take through `drive`'s WalkDriver on its fake box, its reader registered (the cross-check agrees)
    and drive.take_checker its checker: (the take folder, the checker's record, the vendor entry's calls, the files
    and scan kinds the take's commit scan stages). With `address`, the agent's text carries ADDRESS, the scan is
    handed it as an email secret, and the vendor entry's body counts with the vendor readers (counting_entry)."""
    import native_reader_registration as nrr
    import test_codex_adapter as tca
    import test_pending_codex_walk as tpcw
    import test_pending_walk as tpw
    if address:
        addressed(test, harness)
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
    if address:
        login = road.driver.secrets
        road.driver.secrets = road.repo.secrets = lambda: list(login()) + [(drive.EMAIL_SECRET, ADDRESS)]
    row = dict(road.row)
    entry = counting_entry(ct, seen) if address else tvw.vendor_entry(ct, [], seen)
    with mock.patch.object(nrr, "production_readers", lambda study=None: readers), tbi.spying(road.rig.spy), entry:
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


# ---- EC-mask (edit C; glitch-b5 round 15 ruling 2) ------------------------------------------------------------------
def mask_problems(test, drive, harness) -> list:
    out = []
    try:
        folder, records, seen, _ = vendor_road(test, drive, harness, address=True)
    except Exception as e:  # noqa: BLE001 - a held take is the finding
        return [f"{harness}: the masked take is held: {type(e).__name__}: {str(e)[:300]}"]
    led = json.loads((folder / "driver-ledger.json").read_text())
    snaps = [f"session/{s['file']}" for s in led.get("native_snapshots") or []]
    named = list(led.get("streams") or []) + snaps
    left = [n for n in named if ADDRESS.encode("utf-8") in (folder / n).read_bytes()]
    if left or not named:
        return [f"{harness}: the drive scan left the address unmasked in {left} (named {named})"]
    if not any(b"Mail " in (folder / n).read_bytes() for n in led["streams"]) or not any(
            b"Mail " in (folder / n).read_bytes() for n in snaps):
        return [f"{harness}: the address was never in both a turn stream and a snapshot, so nothing was masked there"]
    envs = [json.loads(x) for x in (folder / "transcript.jsonl").read_text().splitlines()]
    for e in envs:
        if e["sha256"] != hashlib.sha256((folder / e["stream"]).read_bytes()).hexdigest():
            out.append(f"{harness}: envelope {e['n']}'s sha256 is not that of {e['stream']}'s masked bytes")
    for s in led.get("native_snapshots") or []:
        if s["sha256"] != hashlib.sha256((folder / "session" / s["file"]).read_bytes()).hexdigest():
            out.append(f"{harness}: the ledger's sha256 of session/{s['file']} is not that of its masked bytes")
    if len(records) != 1 or len(seen) != 1:
        out.append(f"{harness}: the checker read {len(records)} record(s) through {len(seen)} vendor entry call(s)")
    elif records[0]["checker_events"].get("account-email") != 1:
        out.append(f"{harness}: the checker counts {records[0]['checker_events']}, not one account-email event")
    return out


# ---- EB-claude ------------------------------------------------------------------------------------------------------
def claude_masked(drive):
    """test_drive_loop.drive_claude's take with an account address in its replies and handed to the drive's scan
    as an email secret, so the scan masks the published transcript and the turn streams: (its _Take, the records
    drive() returned)."""
    replies = [dict(r, text=f"{r['text']} Mail {OTHER_ADDRESS}.") for r in tdl.TWO_REPLIES]
    pairs = lambda: [("token", tbi.TOKEN), (drive.EMAIL_SECRET, OTHER_ADDRESS)]  # noqa: E731
    with tbi.scratch_repo() as root:
        box = tdl.ClaudeBox(replies)
        rig = tbi.Rig(drive, root, box=box, turns=[{}] * len(replies), secrets=pairs)
        login = tbi.SCRATCH / f"login-{root.name}"
        login.write_text(f"CLAUDE_CODE_OAUTH_TOKEN={tbi.TOKEN}\n")
        os.chmod(login, 0o600)
        rig.driver.adapter_for = drive.claude_code_adapter_for(
            runtime=box, login_file=str(login), counters_for=lambda take: {"oom_kill": 0, "pids_max": 0},
            pin_for=rig.driver.pin_for, clock=rig.clock)
        rig.driver.script_for = lambda r: [dict(x) for x in tdl.TWO]
        r = tbi.row(1)
        with tbi.spying(rig.spy):
            cid = rig.driver.launch(r)
            records = rig.driver.drive(r, cid)
            rig.driver.remove(cid)
        return rig.driver._by_slot[r["slot"]], records


def claude_bytes(drive) -> list:
    """A claude-code take's driver-ledger.json, transcript.jsonl, folder listing and the records TakeDriver.drive
    returns, with a session file, without one, and with the account address masked by the drive's scan."""
    out = []
    for kw in ({}, {"no_session": True}, None):
        if kw is None:
            take, records = claude_masked(drive)
            if OTHER_ADDRESS.encode("utf-8") in (Path(take.folder) / "transcript.jsonl").read_bytes():
                raise AssertionError("the masked claude-code case: the drive scan left the address in transcript.jsonl")
        else:
            take, records, _ = tdl.drive_claude(drive, tdl.TWO, tdl.TWO_REPLIES, **kw)
        got = {"listing": sorted(os.listdir(take.folder)), "records": json.dumps(records, sort_keys=True, default=repr)}
        for name in ("driver-ledger.json", "transcript.jsonl"):
            p = Path(take.folder) / name
            got[name] = p.read_bytes() if p.is_file() else None
        out.append(got)
    return out


def claude_problems(drive, before) -> list:
    out = []
    got, want = claude_bytes(drive), claude_bytes(before)
    for case, g, w in zip(("with a session file", "with no session file", "with the address masked"), got, want):
        for key in w:
            if g[key] != w[key]:
                out.append(f"claude-code {case}: {key} differs from drive.py before edits B and C")
    return out


# ---- EB-witness -----------------------------------------------------------------------------------------------------
def edit_b_text(src: str) -> str:
    span = cvs.edit_b_span(src)
    return "".join(src.splitlines(keepends=True)[span[0] - 1:span[1]])


def claude_too(src: str) -> str:
    """drive.py with edit B's writer also run on the claude-code branch, right after the published transcript's
    cross-check."""
    anchor = ("            take.cross_check = _cc.cross_check(recs, text, session_id=ident[\"session_id\"]) "
              "if cc else []\n")
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
    # edit C (glitch-b5 round 15 ruling 2): the review's masked-address mutant first
    "the rebinding taken out": ("mask", lambda src: cvs.without_edit_c(src)),
    "the envelopes left on the unmasked bytes": ("mask", lambda src: edited(
        src, "                    env[\"sha256\"], rebound = now, True\n", "                    pass\n")),
    "the snapshots left on the unmasked bytes": ("mask", lambda src: edited(
        src, "                    snap[\"sha256\"], rebound = now, True\n", "                    pass\n")),
    # ungated alone, edit C moves no claude-code byte (its transcript lines name no stream and its ledger no
    # native_snapshots, so nothing is rebound or written); the witness also runs the envelope write unguarded
    "the rebinding run for claude-code, writing what it read": ("claude", lambda src: edited(edited(
        src, "if row[\"agent\"][\"harness\"] in VENDOR_HARNESSES and Path(", "if Path("),
        "            if rebound:\n                with open(path, \"w\"",
        "            if True:\n                with open(path, \"w\"")),
}


class EditBRoad(unittest.TestCase):
    def test_eb_a_vendor_take_carries_its_turn_envelopes(self):
        for harness in ("codex", "gemini"):
            with self.subTest(harness=harness), tvw.world():
                try:
                    self.assertEqual(road_problems(self, tbi.drive, harness), [])
                finally:
                    self.doCleanups()             # each road's patches (run_turn among them) end with its road


class EditCMask(unittest.TestCase):
    def test_ec_a_masked_vendor_take_counts_one_account_email_and_is_not_held(self):
        for harness in ("codex", "gemini"):
            with self.subTest(harness=harness), tvw.world():
                try:
                    self.assertEqual(mask_problems(self, tbi.drive, harness), [])
                finally:
                    self.doCleanups()


class EditBClaude(unittest.TestCase):
    def test_eb_a_claude_code_take_is_byte_identical(self):
        before = compiled(cvs.without_edits(drive_source()), "drive_before_edit_b")
        self.assertEqual(claude_problems(tbi.drive, before), [])


EDIT_C_TEST = ('if row["agent"]["harness"] in VENDOR_HARNESSES and '
               'Path(take.folder, "transcript.jsonl").is_file():')
EDIT_C_GATE_MUTANTS = {
    "not in": 'if row["agent"]["harness"] not in VENDOR_HARNESSES and '
              'Path(take.folder, "transcript.jsonl").is_file():',
    "negated": 'if not (row["agent"]["harness"] in VENDOR_HARNESSES and '
               'Path(take.folder, "transcript.jsonl").is_file()):',
    "widened by or": 'if row["agent"]["harness"] in VENDOR_HARNESSES or '
                     'Path(take.folder, "transcript.jsonl").is_file():',
    "widened set": 'if row["agent"]["harness"] in VENDOR_HARNESSES | {"claude-code"} and '
                   'Path(take.folder, "transcript.jsonl").is_file():',
    "a constant harness": 'if "codex" in VENDOR_HARNESSES and Path(take.folder, "transcript.jsonl").is_file():',
}


class EditCGate(unittest.TestCase):
    def test_ec_gate_piece_eb_admits_only_a_membership_test(self):
        src = drive_source()
        self.assertEqual(src.count(EDIT_C_TEST), 1, "drive.py's edit C test is not where EC-gate looks")
        self.assertEqual(cvs.edit_b_problems(src), [])
        for name, test in EDIT_C_GATE_MUTANTS.items():
            with self.subTest(mutant=name):
                self.assertNotEqual(cvs.edit_b_problems(src.replace(EDIT_C_TEST, test)), [],
                                    f"piece EB admitted edit C's gate {name}")


class EditBWitnesses(unittest.TestCase):
    def test_eb_witness_each_mutant_goes_red(self):
        src = drive_source()
        if cvs.edit_b_span(src) is None or cvs.edit_c_span(src) is None:
            self.fail("drive.py holds no edit B or no edit C, so no witness can be performed")
        before = compiled(cvs.without_edits(src), "drive_before_edit_b")
        for name, (road, edit) in WITNESSES.items():
            with self.subTest(witness=name):
                mutant = compiled(edit(src), "drive_edit_b_witness")
                if road == "claude":
                    self.assertNotEqual(claude_problems(mutant, before), [], f"witness {name} stayed green")
                    continue
                check = road_problems if road == "road" else mask_problems
                for harness in ("codex", "gemini"):
                    with tvw.world(), mock.patch.dict(sys.modules, {"drive": mutant}):
                        try:
                            self.assertNotEqual(check(self, mutant, harness), [],
                                                f"witness {name} stayed green on {harness}")
                        finally:
                            self.doCleanups()


class EditD(unittest.TestCase):
    def test_ed_record_edit_d_is_pinned_and_named(self):
        src = drive_source()
        hunks = getattr(cvs, "EDIT_D", None)
        self.assertTrue(isinstance(hunks, tuple) and hunks, "check_vendor_sources records no edit D")
        self.assertIn("R4-1", getattr(cvs, "EDIT_D_RULING", ""), "edit D does not name its ruling")
        # merge of B17 (lane vendor-b17): edit D's pin holds drive.py with piece B17's exact lines taken out (B17's lines
        # are bound by check_vendor_sources.b17_problems), as edit_d_problems reads it
        self.assertEqual(cvs.b17_problems(src), [], "piece B17's drive.py lines are off their exact form")
        # lane vendor-b25: edit E came after edit D, so edit D's pin holds drive.py with edit E taken out too
        # lane vendor-b26: and edit F after E, taken out first
        self.assertEqual(getattr(cvs, "POST_EDIT_D_DRIVE_SHA256", None),
                         hashlib.sha256(cvs.without_edit_e(cvs.without_edit_f(cvs.without_b17(src))).encode("utf-8")
                                        ).hexdigest(),
                         "drive.py after edit D is not pinned")
        self.assertEqual(cvs.problems("EB", ["drive.py"]), [])
        self.assertEqual(hashlib.sha256(cvs.without_edits(src).encode("utf-8")).hexdigest(),
                         cvs.PRE_EDIT_B_DRIVE_SHA256, "drive.py without edits B, C and D is not drive.py before B")

    def test_ed_record_a_partial_or_widened_edit_d_fails_piece_eb(self):
        src = drive_source()
        hunks = getattr(cvs, "EDIT_D", None) or ()
        self.assertTrue(hunks, "check_vendor_sources records no edit D")
        for k, (before, after) in enumerate(hunks):
            with self.subTest(hunk=k):
                self.assertEqual(src.count(after), 1, f"edit D hunk {k} is not in drive.py exactly once")
                self.assertNotEqual(cvs.edit_b_problems(src.replace(after, before)), [],
                                    f"piece EB admitted drive.py without edit D's hunk {k}")
        moved = src.replace("class TakeDriver:\n", "class TakeDriver:\n    # moved\n", 1)
        self.assertNotEqual(cvs.edit_b_problems(moved), [], "piece EB admitted a line moved outside edits B to D")
        self.assertNotEqual(cvs.edit_d_problems(moved), [], "the pinned sha256 admitted a moved drive.py")


class EditE(unittest.TestCase):
    """Lane vendor-b25, glitch-26's ruling 2: the Codex production cross-check's sent and model binding."""

    def test_ee_record_edit_e_is_pinned_and_named(self):
        src = drive_source()
        self.assertTrue(isinstance(getattr(cvs, "EDIT_E", None), tuple) and cvs.EDIT_E)
        self.assertIn("B25-2", getattr(cvs, "EDIT_E_RULING", ""), "edit E does not name its ruling")
        # lane vendor-b26: edit F came after edit E, so edit E's pin holds drive.py with edit F taken out
        self.assertEqual(cvs.POST_EDIT_E_DRIVE_SHA256,
                         hashlib.sha256(cvs.without_edit_f(cvs.without_b17(src)).encode("utf-8")).hexdigest(),
                         "drive.py after edit E is not pinned")
        self.assertEqual(cvs.edit_e_problems(src), [])
        self.assertEqual(cvs.problems("EB", ["drive.py"]), [])

    def test_ee_record_a_partial_or_moved_edit_e_fails_piece_eb(self):
        src = drive_source()
        for k, (before, after) in enumerate(cvs.EDIT_E):
            with self.subTest(hunk=k):
                self.assertEqual(src.count(after), 1, f"edit E hunk {k} is not in drive.py exactly once")
                partial = src.replace(after, before)
                self.assertNotEqual(cvs.edit_b_problems(partial) + cvs.edit_e_problems(partial), [],
                                    f"piece EB admitted drive.py without edit E's hunk {k}")
        moved = src.replace("def codex_cross_check(", "# moved\ndef codex_cross_check(", 1)
        self.assertNotEqual(cvs.edit_e_problems(moved), [], "the pinned sha256 admitted a moved drive.py")


class EditF(unittest.TestCase):
    """Lane vendor-b26, glitch-26's ruling 6: the production Gemini history join's byte-prefix invariant."""

    def test_ef_record_edit_f_is_pinned_and_named(self):
        src = drive_source()
        self.assertTrue(isinstance(getattr(cvs, "EDIT_F", None), tuple) and cvs.EDIT_F)
        self.assertIn("B26-6", getattr(cvs, "EDIT_F_RULING", ""), "edit F does not name its ruling")
        # lane fold6/kill-leftovers: edit G came after edit F, so edit F's pin holds drive.py with edit G taken out
        self.assertEqual(cvs.POST_EDIT_F_DRIVE_SHA256,
                         hashlib.sha256(cvs.without_edit_g(cvs.without_b17(src)).encode("utf-8")).hexdigest(),
                         "drive.py after edit F is not pinned")
        self.assertEqual(cvs.edit_f_problems(src), [])
        self.assertEqual(cvs.problems("EB", ["drive.py"]), [])

    def test_eg_record_edit_g_is_pinned_and_named(self):
        # lane fold6/kill-leftovers (glitch-45's ruling (a)): the one-line postflight call is edit G, pinned whole
        src = drive_source()
        self.assertIn("fold6 (a)", cvs.EDIT_G_RULING, "edit G does not name its ruling")
        self.assertEqual(cvs.POST_EDIT_G_DRIVE_SHA256, hashlib.sha256(cvs.without_b17(src).encode("utf-8")).hexdigest(),
                         "drive.py after edit G is not pinned")
        self.assertEqual(cvs.edit_g_problems(src), [])
        (before, after), = cvs.EDIT_G
        self.assertEqual(src.count(after), 1, "edit G is not in drive.py exactly once")
        self.assertNotEqual(cvs.edit_g_problems(src.replace(after, before)), [], "edit G's pin admitted drive.py without G")

    def test_ef_record_a_partial_or_moved_edit_f_fails_piece_eb(self):
        src = drive_source()
        for k, (before, after) in enumerate(cvs.EDIT_F):
            with self.subTest(hunk=k):
                self.assertEqual(src.count(after), 1, f"edit F hunk {k} is not in drive.py exactly once")
                partial = src.replace(after, before)
                self.assertNotEqual(cvs.edit_b_problems(partial) + cvs.edit_f_problems(partial), [],
                                    f"piece EB admitted drive.py without edit F's hunk {k}")
        moved = src.replace("def native_history_record(", "# moved\ndef native_history_record(", 1)
        self.assertNotEqual(cvs.edit_f_problems(moved), [], "the pinned sha256 admitted a moved drive.py")


if __name__ == "__main__":
    unittest.main()
