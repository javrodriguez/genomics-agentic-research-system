#!/usr/bin/env python3
"""The Gemini native-reader registration road: the shared join and the check tool.

SYNTHETIC FIXTURES ONLY, labelled as such. The acceptance check and the production cross-check are one function
(join_session); an incomplete interaction is refused by both; the check tool prints the exercised and unverified
shapes, the floor, the source hash and HEAD. The registration gates themselves (committed tree, the runner-made walk,
the derived label, the principals, the floor, the synthetic-marker gate last, a positive registration and its single
mutations) run on walks made by the real road in tests/test_pending_walk.py.
"""
from __future__ import annotations

import io
import json
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


class NoRecord(unittest.TestCase):
    def test_the_study_has_no_acceptance_record_and_the_registry_is_empty(self):
        m = nrr()
        self.assertFalse((HERE / m.ACCEPTANCE_FILE).exists(), "an acceptance record must never be committed by a lane")
        self.assertEqual(m.production_readers(), {})


# The registration gates, the positive registration and its single mutations run on walks made by the real road
# (WalkDriver, GeminiAdapter, walk_runner, WalkRepo) in tests/test_pending_walk.py (registration review finding 2): a
# hand-built walk folder now stops at the finding-1 gates, so the hand fixtures of fd4177e0 and cfe5269a moved there.

if __name__ == "__main__":
    unittest.main()
