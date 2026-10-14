#!/usr/bin/env python3
"""The Gemini native-reader registration road, after the registration review (finding 1, MAJOR: self-certifying).

SYNTHETIC FIXTURES ONLY, labelled as such inside the evidence itself. So no fixture here can ever register: every
consistent synthetic record ends at the synthetic-marker gate, which runs last. The other gates run earlier and each
refusal is asserted by its own reason, so each gate is witnessed on its own. A positive registration needs a real
recorded walk and has never been demonstrated; no acceptance record exists in the study.

Every input is read from a throwaway git repository's committed tree (git show HEAD), never the working tree; a bound
path that differs in the working tree refuses. The walk must pass drive.walk_files and be added by a WalkRepo commit,
and the native snapshot and streams must be the ones that walk's own driver ledger names. The acceptor is "javier",
never the reviewer. The acceptance check and the production cross-check are one function; an incomplete interaction is
refused by both; acceptance needs at least two interactions and one tool round trip.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

LABEL = "SYNTHETIC FIXTURE (test-only; never acceptance evidence)"
MODEL = "gemini-3.8-flash"
SID = "1a2b3c4d-0000-4000-8000-00000000abcd"
TS = "2026-10-14T00:00:00.000Z"
ENV = {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test",
       "GIT_COMMITTER_EMAIL": "test@example.invalid", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}


def nrr():
    import native_reader_registration
    return native_reader_registration


def jl(records):
    return "".join(json.dumps(r) + "\n" for r in records)


def tool_call(cid):
    return {"id": cid, "name": "read_file", "args": {"file_path": "synthetic.txt"}, "status": "success",
            "resultDisplay": "display text",
            "result": [{"functionResponse": {"id": cid, "name": "read_file", "response": {"output": "x"}}}]}


def synthetic_native(turns=2, summary=LABEL) -> bytes:
    recs = [{"sessionId": SID, "projectHash": "project-1", "summary": summary}]
    for k in range(1, turns + 1):
        recs += [{"id": f"u{k}", "type": "user", "content": [{"text": f"sent {k}"}]},
                 {"id": f"a{k}", "type": "gemini", "model": MODEL, "content": "I'll read it.",
                  "toolCalls": [tool_call(f"call-{k}")]},
                 {"id": f"rt{k}", "type": "user", "content": [
                     {"functionResponse": {"id": f"call-{k}", "name": "read_file", "response": {"output": "x"}}}]},
                 {"id": f"b{k}", "type": "gemini", "model": MODEL, "content": "Done."}]
    return jl(recs).encode()


STATS = {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0, "input": 2, "duration_ms": 5,
         "tool_calls": 1, "models": {MODEL: {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0,
                                             "input": 2}}}


def synthetic_stream(k=1, done="Done.", status="success") -> str:
    ev = lambda t, **kw: dict({"type": t, "timestamp": TS}, **kw)
    return jl([ev("init", session_id=SID, model=MODEL), ev("message", role="user", content=f"sent {k}"),
               ev("message", role="assistant", content="I'll read it.", delta=True),
               ev("tool_use", tool_name="read_file", tool_id=f"call-{k}", parameters={"file_path": "synthetic.txt"}),
               ev("tool_result", tool_id=f"call-{k}", status="success", output="display text"),
               ev("message", role="assistant", content=done, delta=True),
               ev("result", status=status, stats=STATS)])


class CheckSession(unittest.TestCase):
    def test_one_shared_check_refuses_disagreement_and_incomplete(self):
        m = nrr()
        streams = [synthetic_stream(1), synthetic_stream(2)]
        got = m.check_session(synthetic_native(), streams)
        self.assertEqual(got["status"], "PASS")
        self.assertEqual((got["shapes"]["interactions"], got["shapes"]["tool_round_trips"]), (2, 2))
        for why, s in (("interaction 1", [synthetic_stream(1, done="Different."), streams[1]]),
                       ("native interactions for 1 streams", streams[:1]),
                       ("not complete", [streams[0], synthetic_stream(2, status="error")])):
            with self.subTest(why=why):
                got = m.check_session(synthetic_native(), s)
                self.assertEqual(got["status"], "DISAGREE")
                self.assertIn(why, got["why"])

    def test_the_driver_uses_the_same_function_and_refuses_incomplete(self):
        import drive
        accepted = {"gemini": nrr().gemini_reader}
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "n.jsonl"
            src.write_bytes(synthetic_native())
            import native_snapshot
            refs = [native_snapshot.retain(tmp, 1, str(src))]
            (Path(tmp) / "turn-1.jsonl").write_text(synthetic_stream(1))
            (Path(tmp) / "turn-2.jsonl").write_text(synthetic_stream(2, status="error"))
            got = drive.gemini_cross_check(Path(tmp), refs, 2, readers=accepted)
            self.assertEqual(got["status"], "refused")
            self.assertIn("not complete", got["why"])
            (Path(tmp) / "turn-2.jsonl").write_text(synthetic_stream(2))
            self.assertEqual(drive.gemini_cross_check(Path(tmp), refs, 2, readers=accepted)["status"], "agreed")
            self.assertEqual(drive.gemini_cross_check(Path(tmp), refs, 2)["status"], "pending")

    def test_the_tool_prints_pass_with_shapes_head_and_hash(self):
        m = nrr()
        with tempfile.TemporaryDirectory() as tmp:
            native = Path(tmp) / "native.jsonl"
            native.write_bytes(synthetic_native())
            s = [Path(tmp) / f"turn-{k}.jsonl" for k in (1, 2)]
            for k, p in enumerate(s, 1):
                p.write_text(synthetic_stream(k))
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(m.main(["check", "--native", str(native), "--stream", str(s[0]),
                                         "--stream", str(s[1])]), 0)
            text = out.getvalue()
            self.assertTrue(text.startswith("PASS: 2 interaction(s)"))
            self.assertIn("exercised:", text)
            self.assertIn("unverified:", text)
            self.assertIn("reader sources sha256", text)
            self.assertIn("HEAD", text)

    def test_drive_and_vendor_provenance_are_bound_sources(self):
        self.assertIn("drive.py", nrr().READER_SOURCES)
        self.assertIn("vendor_provenance.py", nrr().READER_SOURCES)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


class Registration(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.dict(os.environ, ENV)
        patch.start()
        self.addCleanup(patch.stop)

    def test_the_study_has_no_acceptance_record_and_the_registry_is_empty(self):
        m = nrr()
        self.assertFalse((HERE / m.ACCEPTANCE_FILE).exists(), "an acceptance record must never be committed by a lane")
        self.assertEqual(m.production_readers(), {})

    def repo(self, *, summary=LABEL, reason=LABEL, review=LABEL, turns=2, walk_subject=None, ledger_edit=None):
        """A throwaway repository: the reader's sources, one arm-G walk committed as WalkRepo commits it, a review."""
        import drive
        m = nrr()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        git(root, "init", "-q")
        git(root, "config", "maintenance.auto", "false")
        study = root / "study"
        study.mkdir()
        for name in m.READER_SOURCES:
            shutil.copyfile(HERE / name, study / name)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "the reader's sources")
        walk = study / "rehearsals" / "walk-g1"
        (walk / "session").mkdir(parents=True)
        snaps = []
        for k in range(1, turns + 1):              # one retained snapshot per turn, each a resume of the last
            native = synthetic_native(k, summary)
            (walk / "session" / f"native-turn-{k}.jsonl").write_bytes(native)
            snaps.append({"file": f"native-turn-{k}.jsonl", "sha256": hashlib.sha256(native).hexdigest()})
            (walk / f"turn-{k}.jsonl").write_text(synthetic_stream(k))
        ledger = {"kind": "take", "native_snapshots": snaps,
                  "native_history": {"status": "pending", "why": "x", "interactions": None,
                                     "basis": "unmasked retained originals, before the drive scan"},
                  "streams": [f"turn-{k}.jsonl" for k in range(1, turns + 1)], "first_agent_turn": True}
        if ledger_edit:
            ledger_edit(ledger)
        (walk / "driver-ledger.json").write_text(json.dumps(ledger))
        (walk / "check.json").write_text("{}\n")
        (walk / drive.WALK_GRADE).write_text("{}\n")
        (study / "rehearsals" / "register.json").write_text(json.dumps({"schema": 1, "walks": [
            {"walk": "walk-g1", "task": "t", "half": "h", "wording": "w", "arm": "G", "model": MODEL,
             "reason": reason, "counted": False}]}))
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", walk_subject or drive.WALK_SUBJECT)
        (study / m.READER_DIR).mkdir()
        (study / m.READER_DIR / "review.md").write_text(f"# {review}\nVerdict: PASS\n")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "an independent review")
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        record = {"schema": 1, "harness": "gemini", "cli_version": m.PINNED_CLI,
                  "reader_sources_sha256": m.reader_sources_sha256(study), "walk": "walk-g1",
                  "native": {"file": f"session/native-turn-{turns}.jsonl",
                             "sha256": sha(walk / "session" / f"native-turn-{turns}.jsonl")},
                  "streams": [{"file": f"turn-{k}.jsonl", "sha256": sha(walk / f"turn-{k}.jsonl")}
                              for k in range(1, turns + 1)],
                  "join": {"status": "PASS", "interactions": turns},
                  "review": {"verdict": "PASS", "file": "review.md", "sha256": sha(study / m.READER_DIR / "review.md"),
                             "reviewer": "a-fresh-reviewer"},
                  "accepted_by": "javier"}
        return root, study, record

    def commit_record(self, root, study, record):
        (study / nrr().ACCEPTANCE_FILE).write_text(json.dumps(record))
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "acceptance")

    def reason(self, study):
        m = nrr()
        with self.assertRaises(m.RegistrationRefused) as cm:
            m.production_readers(study)
        return str(cm.exception)

    def test_a_consistent_synthetic_record_ends_at_the_synthetic_gate(self):
        root, study, record = self.repo()
        self.commit_record(root, study, record)
        self.assertIn("synthetic marker", self.reason(study))

    def test_each_gate_refuses_for_its_own_reason(self):
        m = nrr()
        cases = {
            "uncommitted": ({}, lambda root, study, r: (study / m.ACCEPTANCE_FILE).write_text(json.dumps(r)), False),
            "differs from the committed tree": ({}, lambda root, study, r: (
                study / "rehearsals" / "walk-g1" / "turn-1.jsonl").write_text("changed\n"), True),
            "acceptor": ({}, lambda root, study, r: r.__setitem__("accepted_by", "the-producer"), None),
            "reviewer and the acceptor": ({}, lambda root, study, r: r["review"].__setitem__("reviewer", "javier"), None),
            "asserted": ({}, lambda root, study, r: r.__setitem__("evidence_label", "recorded-walk"), None),
            "reader's sources changed": ({}, lambda root, study, r: r.__setitem__("reader_sources_sha256", "1" * 64), None),
            "WalkRepo": ({"walk_subject": "a hand commit"}, None, None),
            "walk_files": ({"ledger_edit": None}, lambda root, study, r: None, "drop-grade"),
            "driver ledger": ({"ledger_edit": lambda L: L["native_snapshots"][-1].__setitem__("sha256", "0" * 64)},
                              None, None),
            "streams the driver ledger names": ({"ledger_edit": lambda L: L.__setitem__("streams", ["turn-1.jsonl"])},
                                                None, None),
            "native hash": ({}, lambda root, study, r: r["native"].__setitem__("sha256", "0" * 64), None),
            "review hash": ({}, lambda root, study, r: r["review"].__setitem__("sha256", "0" * 64), None),
            "at least 2 interactions": ({"turns": 1}, lambda root, study, r: None, None),
            "join does not re-derive": ({}, lambda root, study, r: r["join"].__setitem__("interactions", 3), None),
            "arm-G walk": ({}, lambda root, study, r: r.__setitem__("walk", "another-walk"), None),
        }
        for why, (kw, edit, mode) in cases.items():
            with self.subTest(why=why):
                root, study, record = self.repo(**kw)
                if mode == "drop-grade":
                    import drive
                    git(root, "rm", "-q", f"study/rehearsals/walk-g1/{drive.WALK_GRADE}")
                    git(root, "commit", "-q", "-m", "drop the grade")
                if mode is False:
                    edit(root, study, record)
                else:
                    if edit is not None and mode is not True:
                        edit(root, study, record)
                    self.commit_record(root, study, record)
                    if mode is True:
                        edit(root, study, record)
                self.assertIn(why, self.reason(study))

    def test_synthetic_markers_anywhere_refuse(self):
        for kw in ({"summary": "x", "reason": "x", "review": LABEL}, {"summary": "x", "reason": LABEL, "review": "x"},
                   {"summary": LABEL, "reason": "x", "review": "x"}):
            with self.subTest(kw=kw):
                root, study, record = self.repo(**kw)
                self.commit_record(root, study, record)
                self.assertIn("synthetic marker", self.reason(study))

    def test_the_registration_report_names_the_commits(self):
        m = nrr()
        root, study, record = self.repo()
        self.commit_record(root, study, record)
        prov = m.acceptance_provenance(study)
        self.assertEqual(prov["acceptance_commit"], git(root, "rev-parse", "HEAD"))
        self.assertEqual(prov["acceptance_author"], "test")
        self.assertEqual(prov["review_commit"], git(root, "rev-parse", "HEAD~1"))


if __name__ == "__main__":
    unittest.main()
