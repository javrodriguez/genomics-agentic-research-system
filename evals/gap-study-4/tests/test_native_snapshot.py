#!/usr/bin/env python3
"""Live harness step 3c: each native session snapshot is retained before the next resume.

A Gemini take resumes one native session file turn after turn (resumedSessionData.filePath, appended to), so the only
proof of what the session held after turn n is a copy taken after turn n's quiescence and before turn n+1's exec.
native_snapshot locates the file only where the pinned 0.64.0 source writes it (GEMINI_CLI_HOME/.gemini/tmp/<project
identifier>/chats/session-<YYYY-MM-DDTHH-MM>[-<k>]-<first 8 of the session id>.jsonl), reading directory names only,
and copies it into the take folder's session/ as native-turn-<n>.jsonl with a {file, sha256} reference. The driver
calls it after each turn's post-n snapshot, for an adapter that names a native session; a failure stops the take for
a human after cleanup and scan. step 1's session_history_facts then joins the retained snapshots.

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import agent_adapter as aa  # noqa: E402
import batch  # noqa: E402
import test_box_integration as tbi  # noqa: E402
from graders import labels4  # noqa: E402

SID = "1a2b3c4d-0000-4000-8000-00000000abcd"


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def ns():
    import native_snapshot
    return native_snapshot


def chats(home: Path, project="synthetic-project") -> Path:
    d = home / ".gemini" / "tmp" / project / "chats"
    d.mkdir(parents=True, exist_ok=True)
    return d


class Locate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_source_named_file_is_found_and_nothing_else(self):
        m = ns()
        d = chats(self.home)
        want = d / f"session-2026-10-14T04-20-{SID[:8]}.jsonl"
        want.write_text("{}\n")
        (d / "session-2026-10-14T04-20-ffffffff.jsonl").write_text("{}\n")      # another session
        sub = d / SID
        sub.mkdir()
        (sub / "child.jsonl").write_text("{}\n")                                 # a subagent's file
        self.assertEqual(m.gemini_session_file(str(self.home), SID), str(want))
        want.unlink()
        (d / f"session-2026-10-14T04-20-2-{SID[:8]}.jsonl").write_text("{}\n")   # a collision index
        self.assertTrue(m.gemini_session_file(str(self.home), SID).endswith(f"-2-{SID[:8]}.jsonl"))

    def test_none_two_or_a_link_refuses(self):
        m = ns()
        with self.assertRaises(m.SnapshotRefused):
            m.gemini_session_file(str(self.home), SID)                           # none
        d = chats(self.home)
        (d / f"session-2026-10-14T04-20-{SID[:8]}.jsonl").write_text("{}\n")
        (d / f"session-2026-10-14T04-21-{SID[:8]}.jsonl").write_text("{}\n")
        with self.assertRaises(m.SnapshotRefused):
            m.gemini_session_file(str(self.home), SID)                           # two
        (d / f"session-2026-10-14T04-21-{SID[:8]}.jsonl").unlink()
        other = chats(self.home, "second-project")
        (other / f"session-2026-10-14T04-20-{SID[:8]}.jsonl").write_text("{}\n")
        with self.assertRaises(m.SnapshotRefused):
            m.gemini_session_file(str(self.home), SID)                           # two projects
        (other / f"session-2026-10-14T04-20-{SID[:8]}.jsonl").unlink()
        real = d / f"session-2026-10-14T04-20-{SID[:8]}.jsonl"
        real.rename(d / "elsewhere.txt")
        os.symlink(d / "elsewhere.txt", real)
        with self.assertRaises(m.SnapshotRefused):
            m.gemini_session_file(str(self.home), SID)                           # a symbolic link
        for bad in ("", "../x", "latest", None):
            with self.subTest(bad=bad), self.assertRaises(m.SnapshotRefused):
                m.gemini_session_file(str(self.home), bad)

    def test_a_linked_directory_on_the_way_refuses(self):
        m = ns()
        real = Path(self.tmp.name) / "outside"
        (real / "synthetic-project" / "chats").mkdir(parents=True)
        (real / "synthetic-project" / "chats" / f"session-2026-10-14T04-20-{SID[:8]}.jsonl").write_text("{}\n")
        (self.home / ".gemini").mkdir()
        os.symlink(real, self.home / ".gemini" / "tmp")
        with self.assertRaises(m.SnapshotRefused):
            m.gemini_session_file(str(self.home), SID)


class Retain(unittest.TestCase):
    def test_bytes_are_copied_once_with_their_reference(self):
        m = ns()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.jsonl"
            src.write_bytes(b'{"sessionId": "s"}\n')
            take = Path(tmp) / "take"
            take.mkdir()
            ref = m.retain(str(take), 1, str(src))
            self.assertEqual(ref, {"file": "native-turn-1.jsonl",
                                   "sha256": hashlib.sha256(src.read_bytes()).hexdigest()})
            self.assertEqual((take / "session" / "native-turn-1.jsonl").read_bytes(), src.read_bytes())
            src.write_bytes(b'{"sessionId": "s"}\n{"later": 1}\n')
            with self.assertRaises(m.SnapshotRefused):
                m.retain(str(take), 1, str(src))                                  # never overwritten
            self.assertEqual(m.retain(str(take), 2, str(src))["file"], "native-turn-2.jsonl")
            link = Path(tmp) / "link.jsonl"
            os.symlink(src, link)
            for bad_src, n in ((str(link), 3), (tmp, 4)):
                with self.subTest(src=bad_src), self.assertRaises(m.SnapshotRefused):
                    m.retain(str(take), n, bad_src)
            empty = Path(tmp) / "empty.jsonl"
            empty.write_bytes(b"")
            with self.assertRaises(m.SnapshotRefused) as cm:
                m.retain(str(take), 5, str(empty))                                # an empty session: never a snapshot
            self.assertIn("turn 5", str(cm.exception))
            self.assertFalse((take / "session" / "native-turn-5.jsonl").exists())
            for n in (0, -1, True, "1"):
                with self.subTest(n=n), self.assertRaises(m.SnapshotRefused):
                    m.retain(str(take), n, str(src))


class NativeAdapter(tbi.FakeAdapter):
    """FakeAdapter that keeps a growing native session file in the take's config folder (its home, the agent's during
    the take, written as the container would), as a resumed Gemini session does; the driver finds it through the box's
    listing (drive-wiring review MAJOR 1)."""

    def __init__(self, *a, home, fail_at=None, **kw):
        super().__init__(*a, **kw)
        self.home, self.fail_at, self.seen_before = Path(home), fail_at, []
        with tbi.FakeBox.as_container(str(self.home)):
            self.file = chats(self.home) / f"session-2026-10-14T04-20-{SID[:8]}.jsonl"

    def native_session_path(self, home):
        if self.fail_at == self._turns:
            raise ns().SnapshotRefused("synthetic: no session file")
        return ns().gemini_session_file(str(self.home), SID)

    def native_session_rel(self, lister):
        if self.fail_at == self._turns:
            raise ns().SnapshotRefused("synthetic: no session file")
        return ns().gemini_session_rel(lister, SID)

    def _turn(self, line, *, first, budget_s):
        n = self._turns + 1
        self.seen_before.append(sorted(p.name for p in (Path(self.take.folder) / "session").glob("native-turn-*"))
                                if (Path(self.take.folder) / "session").is_dir() else [])
        with tbi.FakeBox.as_container(str(self.home)), open(self.file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"turn": n, "line": line}) + "\n")
        return super()._turn(line, first=first, budget_s=budget_s)


class DriverRetains(unittest.TestCase):
    def drive(self, fail_at=None, plain=False):
        tbi.need(self, "TakeDriver", "TakeRepo", "DriveRefused", "sidecar_health")
        root_cm = tbi.scratch_repo()
        root = root_cm.__enter__()
        self.addCleanup(root_cm.__exit__, None, None, None)
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        rig = tbi.Rig(tbi.drive, root, turns=[{"text": "a"}, {"text": "b"}, {"text": "c"}])
        if not plain:
            def make(r, take):
                rig.adapters.append(NativeAdapter(rig.box, take, rig.turns, home=take.config_dir, fail_at=fail_at))
                return rig.adapters[-1]
            rig.adapter_for = rig.driver.adapter_for = make
        b, got = tbi.run_batch(rig, [tbi.row(1)])
        folder = Path(rig.take().folder)
        ledger = json.loads((folder / "driver-ledger.json").read_text()) if (folder / "driver-ledger.json").is_file() else None
        return rig, got[0], folder, ledger

    def test_each_snapshot_is_retained_before_the_next_resume(self):
        rig, o, folder, ledger = self.drive()
        a = rig.adapters[0]
        self.assertEqual(o["state"], labels4.GRADED)
        self.assertEqual(a.seen_before, [[], ["native-turn-1.jsonl"], ["native-turn-1.jsonl", "native-turn-2.jsonl"]])
        refs = ledger["native_snapshots"]
        self.assertEqual([r["file"] for r in refs], [f"native-turn-{n}.jsonl" for n in (1, 2, 3)])
        for n, r in enumerate(refs, 1):
            raw = (folder / "session" / r["file"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), r["sha256"])
            self.assertEqual(len(raw.decode().splitlines()), n, "snapshot n holds the session after turn n")

    def test_a_retention_failure_stops_the_take_for_a_human(self):
        rig, o, folder, ledger = self.drive(fail_at=2)
        self.assertEqual(o["state"], labels4.FAILED)
        self.assertIn("native session snapshot", o["reason"])
        self.assertTrue(batch.needs_ruling(o))
        self.assertIs(o["rerun"], False)
        self.assertEqual(len(rig.adapters[0].lines), 2, "nothing is sent after a snapshot that was not retained")
        self.assertEqual([r["file"] for r in ledger["native_snapshots"]], ["native-turn-1.jsonl"])
        self.assertIn("native session snapshot", ledger["native_snapshot_refusal"])
        self.assertEqual(rig.checked, [])
        self.assertEqual(rig.box.empty(), [])

    def test_an_adapter_without_a_native_session_is_unchanged(self):
        rig, o, folder, ledger = self.drive(plain=True)
        self.assertEqual(o["state"], labels4.GRADED)
        self.assertNotIn("native_snapshots", ledger)
        self.assertFalse((folder / "session").exists())

    def test_retained_snapshots_join_through_session_history_facts(self):
        import vendor_provenance as vp
        rig, o, folder, ledger = self.drive()
        def reader(raw, ordinal):
            rows = [json.loads(x) for x in raw.decode().splitlines()]
            if ordinal > len(rows):
                raise vp.ProvenanceRefused("snapshot lacks requested interaction")
            r = rows[ordinal - 1]
            return {"session_id": SID, "requested_model": None, "version": None, "cwd": None,
                    "permission_mode": None, "sent": r["line"], "output": [r["turn"]]}
        got = vp.session_history_facts("gemini", folder / "session", ledger["native_snapshots"],
                                       readers={"gemini": reader})
        self.assertEqual([g["sent"]["value"] for g in got], ["line 1", "line 2", "line 3"])
        (folder / "session" / "native-turn-2.jsonl").write_bytes(b'{"turn": 1, "line": "rewritten"}\n')
        with self.assertRaises(vp.ProvenanceRefused):
            vp.session_history_facts("gemini", folder / "session", ledger["native_snapshots"],
                                     readers={"gemini": reader})


class GeminiAdapterNamesItsSession(unittest.TestCase):
    def test_the_session_is_located_by_the_id_turn_one_named(self):
        import gemini_adapter as ga
        m = ns()
        a = ga.GeminiAdapter.__new__(ga.GeminiAdapter)
        a.session_id = None
        with self.assertRaises(m.SnapshotRefused):
            a.native_session_path("/nonexistent")
        with tempfile.TemporaryDirectory() as tmp:
            f = chats(Path(tmp)) / f"session-2026-10-14T04-20-{SID[:8]}.jsonl"
            f.write_text("{}\n")
            a.session_id = SID
            self.assertEqual(a.native_session_path(tmp), str(f))


class CodexRollout(unittest.TestCase):
    """Codex slice 3: <home>/sessions/<Y>/<MM>/<DD>/rollout-<YYYY-MM-DDTHH-MM-SS>-<thread>.jsonl, exactly (audit
    Addendum B); a reverted or compressed rollout, a name dated off its folder, none or two refuse."""
    TID = "00000000-0000-7000-8000-0000000000c1"

    def home(self, names, folder=("2026", "10", "14")):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name, "sessions", *folder)
        d.mkdir(parents=True)
        for name in names:
            (d / name).write_text("{}\n")
        return tmp.name, d

    def test_the_one_rollout(self):
        home, d = self.home([f"rollout-2026-10-14T05-00-00-{self.TID}.jsonl",
                             "rollout-2026-10-14T05-00-00-00000000-0000-7000-8000-0000000000c2.jsonl"])
        self.assertEqual(ns().codex_rollout_file(home, self.TID), str(d / f"rollout-2026-10-14T05-00-00-{self.TID}.jsonl"))

    def test_each_refusal(self):
        t = self.TID
        for why, names, folder in (
                ("none", [], ("2026", "10", "14")),
                ("two", [f"rollout-2026-10-14T05-00-00-{t}.jsonl", f"rollout-2026-10-14T06-00-00-{t}.jsonl"],
                 ("2026", "10", "14")),
                ("reverted", [f"rollout-2026-10-14T05-00-00-{t}_11111111-0000-7000-8000-000000000001.jsonl"],
                 ("2026", "10", "14")),
                ("compressed", [f"rollout-2026-10-14T05-00-00-{t}.jsonl.zst"], ("2026", "10", "14")),
                ("dated off its folder", [f"rollout-2026-10-13T05-00-00-{t}.jsonl"], ("2026", "10", "14")),
                ("a name with fractional seconds", [f"rollout-2026-10-14T05-00-00.123-{t}.jsonl"], ("2026", "10", "14")),
                ("a padded year folder", [f"rollout-2026-10-14T05-00-00-{t}.jsonl"], ("02026", "10", "14")),
                ("a one-digit month folder", [f"rollout-2026-10-14T05-00-00-{t}.jsonl"], ("2026", "1", "14")),
                ("a zero-padded year folder and name", [f"rollout-02026-10-14T05-00-00-{t}.jsonl"],
                 ("02026", "10", "14")),
                ("a revert beside the rollout", [f"rollout-2026-10-14T05-00-00-{t}.jsonl",
                                                 f"rollout-2026-10-14T05-00-00-{t}_11111111-0000-7000-8000-0000000001.jsonl"],
                 ("2026", "10", "14")),
                ("a compressed copy beside the rollout", [f"rollout-2026-10-14T05-00-00-{t}.jsonl",
                                                          f"rollout-2026-10-13T05-00-00-{t}.jsonl.zst"],
                 ("2026", "10", "14"))):
            with self.subTest(why=why):
                home, _ = self.home(names, folder)
                with self.assertRaises(ns().SnapshotRefused):
                    ns().codex_rollout_file(home, t)
        home, _ = self.home([])
        for bad in ("", "a/b", "../x", None):
            with self.subTest(thread=bad), self.assertRaises(ns().SnapshotRefused):
                ns().codex_rollout_file(home, bad)

    def test_a_linked_rollout_refuses(self):
        home, d = self.home([])
        target = d / "elsewhere.json"
        target.write_text("{}\n")
        os.symlink(target, d / f"rollout-2026-10-14T05-00-00-{self.TID}.jsonl")
        with self.assertRaises(ns().SnapshotRefused):
            ns().codex_rollout_file(home, self.TID)



# ---- B16-1 (glitch-26's ruling, Mon 19 Oct 2026; the GPT practice walk held on SnapshotRefused) ----------------------
# Each locator walks the config folder through the box's operator_list, which names the folder's root "." (box/ownership
# _rel_dir) and refuses any other path that _rel refuses, the empty one included. The lister here puts the real
# _rel_dir and _no_credential_path in front of a fake listing (no container), and turns a failure into the
# SnapshotRefused TakeDriver.config_view raises, so a locator that names the root any other way fails as the walk did.
def ownership():
    from box import ownership as ow
    return ow


def box_rules_lister(listing: dict, asked: list):
    """lister(rel_dir) -> [(name, kind)] or None, from `listing` (rel_dir -> entries) behind ownership's own path rules
    for the config root; every rel_dir the locator asked is appended to `asked`."""
    ow = ownership()

    def lister(rel_dir):
        asked.append(rel_dir)
        try:
            rel = ow._rel_dir(rel_dir)
            ow._no_credential_path("config", rel)
        except Exception as e:  # noqa: BLE001 - as config_view: the box step's failure, named
            raise ns().SnapshotRefused(f"the box's operator_list of the config folder failed "
                                       f"({type(e).__name__}: {str(e)[:200]})") from None
        return listing.get(rel)
    return lister


class BoxRootNaming(unittest.TestCase):
    """B16-1: the Codex and Gemini locators name the config folder's root as the box's contract does (".")."""
    TID = "00000000-0000-7000-8000-0000000000c1"
    ROLLOUT = f"rollout-2026-10-14T05-00-00-{TID}.jsonl"
    SESSION = f"session-2026-10-14T04-20-{SID[:8]}.jsonl"

    def codex(self, mod=None):
        asked = []
        lister = box_rules_lister({".": [("config.toml", "file"), ("sessions", "dir")], "sessions": [("2026", "dir")],
                                   "sessions/2026": [("10", "dir")], "sessions/2026/10": [("14", "dir")],
                                   "sessions/2026/10/14": [(self.ROLLOUT, "file")]}, asked)
        return (mod or ns()).codex_rollout_rel(lister, self.TID), asked

    def gemini(self, mod=None):
        asked = []
        lister = box_rules_lister({".": [(".gemini", "dir")], ".gemini": [("settings.json", "file"), ("tmp", "dir")],
                                   ".gemini/tmp": [("synthetic-project", "dir")],
                                   ".gemini/tmp/synthetic-project": [("chats", "dir")],
                                   ".gemini/tmp/synthetic-project/chats": [(self.SESSION, "file")]}, asked)
        return (mod or ns()).gemini_session_rel(lister, SID), asked

    def test_codex_locator_through_the_box_rules(self):
        rel, asked = self.codex()
        self.assertEqual(rel, f"sessions/2026/10/14/{self.ROLLOUT}")
        self.assertEqual(asked[0], ".")

    def test_gemini_locator_through_the_box_rules(self):
        rel, asked = self.gemini()
        self.assertEqual(rel, f".gemini/tmp/synthetic-project/chats/{self.SESSION}")
        self.assertEqual(asked[0], ".")

    def test_the_box_rules_refuse_the_empty_root(self):
        with self.assertRaisesRegex(ns().SnapshotRefused, "never leaving it"):
            box_rules_lister({}, [])("")



# ---- B16-1 witnesses: one locator's root named "" again, compiled in memory; each must turn BoxRootNaming red -------
WITNESSES = {
    "codex-root-empty": ('    _dir(_entries(lister, "."), "sessions", ".")\n',
                         '    _dir(_entries(lister, ""), "sessions", ".")\n', "codex"),
    "gemini-root-empty": ('    _dir(_entries(lister, "."), ".gemini", ".")\n',
                          '    _dir(_entries(lister, ""), ".gemini", ".")\n', "gemini"),
}


def witnesses() -> int:
    import types
    src = Path(ns().__file__).read_text(encoding="utf-8")
    red = 0
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    def unmutated():                                 # both locators pass on the real module, each on its own
        out = []
        for locator in ("codex", "gemini"):
            rel, asked = getattr(BoxRootNaming(), locator)()
            if not rel or not asked or asked[0] != ".":
                out.append(f"{locator}: located {rel!r}, first asked {asked[:1]}")
        return out
    mutation_baseline.require_clean("test_native_snapshot witnesses", unmutated)
    for name, (old, new, locator) in WITNESSES.items():
        if src.count(old) != 1:
            print(f"NOT PERFORMED {name}: the anchor occurs {src.count(old)} times in native_snapshot.py")
            continue
        mod = types.ModuleType("native_snapshot_b16_witness")
        mod.__file__ = ns().__file__
        exec(compile(src.replace(old, new), mod.__file__ + " (witness)", "exec"), mod.__dict__)
        mod.SnapshotRefused = ns().SnapshotRefused          # the lister raises the real module's refusal
        others = [n for n in ("codex", "gemini") if n != locator]
        try:
            getattr(BoxRootNaming(), locator)(mod)
        except ns().SnapshotRefused as e:
            try:
                for other in others:                         # red alone: the other locator still passes
                    getattr(BoxRootNaming(), other)(mod)
            except ns().SnapshotRefused as e2:
                print(f"NOT ALONE {name}: the other locator also refuses: {e2}")
                continue
            red += 1
            print(f"red   {name}: {e}")
            continue
        print(f"GREEN {name}: the mutant passes BoxRootNaming")
    print(f"test_native_snapshot witnesses: {red}/{len(WITNESSES)} red")
    return 0 if red == len(WITNESSES) else 1


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(witnesses())
    unittest.main()
