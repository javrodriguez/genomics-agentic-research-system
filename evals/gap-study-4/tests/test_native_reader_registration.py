#!/usr/bin/env python3
"""The Gemini native-reader registration road. SYNTHETIC FIXTURES ONLY, labelled as such: no recorded session
exists, and no acceptance record is ever committed by this lane or written into the study folder by these tests.

The production registry stays empty without a committed acceptance record; a record that is forged, hash-mismatched
or labelled synthetic refuses; the acceptance check prints PASS or the exact disagreement. The one positive
registration test runs inside a temporary copy of the reader's sources with a temporary register, to prove the
mechanism, never the study's own folder.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

LABEL = "SYNTHETIC FIXTURE (test-only; never acceptance evidence)"
MODEL = "gemini-3.8-flash"
SID = "1a2b3c4d-0000-4000-8000-00000000abcd"
TS = "2026-10-14T00:00:00.000Z"


def nrr():
    import native_reader_registration
    return native_reader_registration


def jl(records):
    return "".join(json.dumps(r) + "\n" for r in records)


def synthetic_native() -> bytes:
    call = {"id": "call-1", "name": "read_file", "args": {"file_path": "synthetic.txt"}}
    return jl([{"sessionId": SID, "projectHash": "project-1", "summary": LABEL},
               {"id": "u1", "type": "user", "content": [{"text": "exact sent"}]},
               {"id": "a1", "type": "gemini", "model": MODEL, "content": "I'll read it.",
                "toolCalls": [dict(call, status="success", resultDisplay="display text",
                                   result=[{"functionResponse": {"id": "call-1", "name": "read_file",
                                                                 "response": {"output": "x"}}}])]},
               {"id": "rt1", "type": "user", "content": [
                   {"functionResponse": {"id": "call-1", "name": "read_file", "response": {"output": "x"}}}]},
               {"id": "a2", "type": "gemini", "model": MODEL, "content": "Done."}]).encode()


STATS = {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0, "input": 2, "duration_ms": 5,
         "tool_calls": 1, "models": {MODEL: {"total_tokens": 3, "input_tokens": 2, "output_tokens": 1, "cached": 0,
                                             "input": 2}}}


def synthetic_stream(done="Done.", status="success") -> str:
    ev = lambda t, **kw: dict({"type": t, "timestamp": TS}, **kw)
    return jl([ev("init", session_id=SID, model=MODEL), ev("message", role="user", content="exact sent"),
               ev("message", role="assistant", content="I'll read it.", delta=True),
               ev("tool_use", tool_name="read_file", tool_id="call-1", parameters={"file_path": "synthetic.txt"}),
               ev("tool_result", tool_id="call-1", status="success", output="display text"),
               ev("message", role="assistant", content=done, delta=True),
               ev("result", status=status, stats=STATS)])


class CheckSession(unittest.TestCase):
    def test_pass_and_each_disagreement(self):
        m = nrr()
        self.assertEqual(m.check_session(synthetic_native(), [synthetic_stream()])["status"], "PASS")
        for why, streams in (("interaction 1", [synthetic_stream(done="Different.")]),
                             ("native interactions for 2 streams", [synthetic_stream(), synthetic_stream()]),
                             ("not complete", [synthetic_stream(status="error")])):
            with self.subTest(why=why):
                got = m.check_session(synthetic_native(), streams)
                self.assertEqual(got["status"], "DISAGREE")
                self.assertIn(why, got["why"])

    def test_the_tool_prints_pass_or_the_exact_disagreement(self):
        m = nrr()
        with tempfile.TemporaryDirectory() as tmp:
            native, good, bad = (Path(tmp) / n for n in ("native.jsonl", "turn-1.jsonl", "bad.jsonl"))
            native.write_bytes(synthetic_native())
            good.write_text(synthetic_stream())
            bad.write_text(synthetic_stream(done="Different."))
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(m.main(["check", "--native", str(native), "--stream", str(good)]), 0)
            self.assertTrue(out.getvalue().startswith("PASS: 1 interaction(s)"))
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(m.main(["check", "--native", str(native), "--stream", str(bad)]), 1)
            self.assertTrue(out.getvalue().startswith("DISAGREE: interaction 1: recorded text disagrees"))


class Registration(unittest.TestCase):
    def test_the_study_has_no_acceptance_record_and_the_registry_is_empty(self):
        m = nrr()
        self.assertFalse((HERE / m.ACCEPTANCE_FILE).exists(), "an acceptance record must never be committed by a lane")
        self.assertEqual(m.production_readers(), {})
        import vendor_provenance
        self.assertEqual(dict(vendor_provenance.NATIVE_SESSION_READERS), {})

    def study(self):
        """A temporary study: the reader's sources, a register listing one arm-G walk, its retained files, a review."""
        m = nrr()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name in m.READER_SOURCES:
            shutil.copyfile(HERE / name, root / name)
        walk = root / "rehearsals" / "synthetic-walk-g1"
        (walk / "session").mkdir(parents=True)
        (walk / "session" / "native-turn-1.jsonl").write_bytes(synthetic_native())
        (walk / "turn-1.jsonl").write_text(synthetic_stream())
        (root / "rehearsals" / "register.json").write_text(json.dumps({"schema": 1, "walks": [
            {"walk": "synthetic-walk-g1", "task": "t", "half": "h", "wording": "w", "arm": "G", "model": MODEL,
             "reason": LABEL, "counted": False}]}))
        (root / m.READER_DIR).mkdir()
        review = root / m.READER_DIR / "review.md"
        review.write_text(f"# {LABEL}\nVerdict: PASS\n")
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        record = {"schema": 1, "harness": "gemini", "cli_version": m.PINNED_CLI,
                  "reader_sources_sha256": m.reader_sources_sha256(root), "walk": "synthetic-walk-g1",
                  "evidence_label": m.RECORDED,
                  "native": {"file": "session/native-turn-1.jsonl", "sha256": sha(walk / "session" / "native-turn-1.jsonl")},
                  "streams": [{"file": "turn-1.jsonl", "sha256": sha(walk / "turn-1.jsonl")}],
                  "join": {"status": "PASS", "interactions": 1},
                  "review": {"verdict": "PASS", "file": "review.md", "sha256": sha(review), "reviewer": "test-reviewer"},
                  "accepted_by": "test-only"}
        return root, record

    def write(self, root, record):
        (root / nrr().ACCEPTANCE_FILE).write_text(json.dumps(record))

    def test_the_mechanism_registers_only_a_record_that_re_derives(self):
        m = nrr()
        root, record = self.study()
        self.assertEqual(m.production_readers(root), {})
        self.write(root, record)
        self.assertEqual(set(m.production_readers(root)), {"gemini"})

    def test_a_forged_mismatched_or_synthetic_record_refuses(self):
        m = nrr()
        cases = {
            "synthetic label": lambda r, root: r.__setitem__("evidence_label", "synthetic"),
            "native hash": lambda r, root: r["native"].__setitem__("sha256", "0" * 64),
            "stream hash": lambda r, root: r["streams"][0].__setitem__("sha256", "f" * 64),
            "reader sources": lambda r, root: r.__setitem__("reader_sources_sha256", "1" * 64),
            "reader source edited": lambda r, root: (root / "gemini_projection.py").write_text("# edited\n"),
            "review verdict": lambda r, root: r["review"].__setitem__("verdict", "CHANGES"),
            "review hash": lambda r, root: (root / m.READER_DIR / "review.md").write_text("tampered\n"),
            "join count": lambda r, root: r["join"].__setitem__("interactions", 2),
            "evidence that does not join": lambda r, root: (
                (root / "rehearsals" / "synthetic-walk-g1" / "turn-1.jsonl").write_text(synthetic_stream(done="Other.")),
                r["streams"][0].__setitem__("sha256", hashlib.sha256(
                    (root / "rehearsals" / "synthetic-walk-g1" / "turn-1.jsonl").read_bytes()).hexdigest())),
            "unregistered walk": lambda r, root: r.__setitem__("walk", "another-walk"),
            "another arm": lambda r, root: (root / "rehearsals" / "register.json").write_text(json.dumps(
                {"schema": 1, "walks": [{"walk": "synthetic-walk-g1", "arm": "O"}]})),
            "a traversing file name": lambda r, root: r["native"].__setitem__("file", "../session/native-turn-1.jsonl"),
            "an extra key": lambda r, root: r.__setitem__("note", "x"),
            "another CLI": lambda r, root: r.__setitem__("cli_version", "0.65.0"),
            "nobody accepted": lambda r, root: r.__setitem__("accepted_by", " "),
        }
        for name, edit in cases.items():
            with self.subTest(name):
                root, record = self.study()
                record = copy.deepcopy(record)
                edit(record, root)
                self.write(root, record)
                with self.assertRaises(m.RegistrationRefused):
                    m.production_readers(root)
        root, _ = self.study()
        (root / m.ACCEPTANCE_FILE).write_text("{not json")
        with self.assertRaises(m.RegistrationRefused):
            m.production_readers(root)


class DriverUsesTheRegistry(unittest.TestCase):
    def test_the_driver_reads_the_production_registry(self):
        import drive
        self.assertEqual(drive._registration.production_readers.__module__, "native_reader_registration")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "native.jsonl"
            src.write_bytes(synthetic_native())
            import native_snapshot
            refs = [native_snapshot.retain(tmp, 1, str(src))]
            got = drive.native_history_record("gemini", Path(tmp) / "session", refs)
            self.assertEqual(got["status"], "pending", "no acceptance record: the production registry is empty")
            accepted = {"gemini": nrr().gemini_reader}
            got = drive.native_history_record("gemini", Path(tmp) / "session", refs, readers=accepted)
            self.assertEqual(got["status"], "joined")
            (Path(tmp) / "turn-1.jsonl").write_text(synthetic_stream())
            ok = drive.gemini_cross_check(Path(tmp), refs, 1, readers=accepted)
            self.assertEqual(ok, {"status": "agreed", "why": None})
            (Path(tmp) / "turn-1.jsonl").write_text(synthetic_stream(done="Other."))
            bad = drive.gemini_cross_check(Path(tmp), refs, 1, readers=accepted)
            self.assertEqual(bad["status"], "refused")
            self.assertIn("recorded text disagrees", bad["why"])
            self.assertEqual(drive.gemini_cross_check(Path(tmp), refs, 1)["status"], "pending")
            (Path(tmp) / "turn-1.jsonl").write_text(synthetic_stream())
            extra = drive.gemini_cross_check(Path(tmp), refs, 0, readers=accepted)
            self.assertEqual(extra["status"], "refused")                  # a native interaction the take never ran
            self.assertIn("more than", extra["why"])


if __name__ == "__main__":
    unittest.main()
