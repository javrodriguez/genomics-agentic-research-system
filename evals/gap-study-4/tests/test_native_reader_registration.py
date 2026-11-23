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
            # Lane freeze-gates-fix S8 (glitch-f1's ruling 3, 21 Oct 2026): readers=None is the production registry,
            # which holds the accepted Gemini reader since 5457e75e, so it reads as the accepted reader does; a
            # registry without it keeps the take pending.
            self.assertEqual(drive.gemini_cross_check(Path(tmp), refs, 2)["status"], "agreed")
            from unittest import mock
            with mock.patch.object(nrr(), "production_readers", lambda study=None: {}):
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


class ManifestClaim(unittest.TestCase):
    """glitch-06's ruling (14 Oct 2026): native-readers/ is pre-declared by one pattern entry, so Javier's acceptance
    commit never touches a manifest; it claims only <harness>-acceptance.json and <harness>-review.md for a vendor
    harness, and nothing else there."""

    def test_only_the_named_records_are_claimed(self):
        import copy_manifest as cm
        extra = {"native-readers/gemini-acceptance.json", "native-readers/gemini-review.md",
                 "native-readers/codex-acceptance.json", "native-readers/codex-review.md",
                 "native-readers/notes.txt", "native-readers/claude-code-acceptance.json",
                 "native-readers/gemini-review.json", "native-readers/sub/gemini-review.md"}
        got = cm.problems(present=cm.files_here() | extra, pinned=False)
        unclaimed = sorted(n for n in extra if any(n + " is under" in g for g in got))
        self.assertEqual(unclaimed, ["native-readers/claude-code-acceptance.json", "native-readers/gemini-review.json",
                                     "native-readers/notes.txt", "native-readers/sub/gemini-review.md"])
        self.assertEqual(nrr().ACCEPTANCE_FILE, "native-readers/gemini-acceptance.json")
        self.assertTrue(nrr()._REVIEW_FILE.fullmatch("gemini-review.md"))

    def test_a_fragment_cannot_claim_inside_the_folder(self):
        import json
        import shutil
        import copy_manifest as cm
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "COPIED.d"
            shutil.copytree(cm.FRAGMENTS, folder)
            frag = folder / "live-harness-foundation.json"
            doc = json.loads(frag.read_text())
            for entry, why in (({"path": "native-readers/notes.txt", "status": "new", "reason": "x"}, "claimed only by"),
                               ({"path": "native-readers/**", "status": "new", "reason": "x"}, "claimed only by")):
                with self.subTest(entry=entry):
                    frag.write_text(json.dumps(dict(doc, files=doc["files"] + [entry])))
                    self.assertTrue(any(why in g for g in cm.problems(folder=folder, pinned=False)))
            pattern = [e for e in doc["files"] if e["path"] == "native-readers/**"]
            others = [e for e in doc["files"] if e["path"] != "native-readers/**"]
            frag.write_text(json.dumps(dict(doc, files=others + [dict(pattern[0], source="native-readers/x.json")])))
            self.assertTrue(any("claimed only by" in g for g in cm.problems(folder=folder, pinned=False)),
                            "a stray source key on the pattern entry is refused (batch-8 fix NIT)")
            frag.write_text(json.dumps(dict(doc, files=[e for e in doc["files"] if e["path"] != "native-readers/**"]
                                            + [dict(pattern[0], reason=" ")])))
            self.assertTrue(any("claimed only by" in g for g in cm.problems(folder=folder, pinned=False)))
            frag.write_text(json.dumps(dict(doc, files=[e for e in doc["files"] if e["path"] != "native-readers/**"])))
            got = cm.problems(folder=folder, present=cm.files_here() | {"native-readers/gemini-acceptance.json"},
                              pinned=False)                # without the pattern entry nothing there is claimed
            self.assertTrue(any("native-readers/gemini-acceptance.json is under" in g for g in got))


# Lane freeze-gates-fix S8 (glitch-f1's ruling 3, 21 Oct 2026): Javier accepted both readers in one commit, 5457e75e.
# He accepted the Gemini reader again at 5292df49 (22 Oct 2026, the vendor-b28 reader at 60a41247), the accepted head
# this lane was merged onto (freeze merge 1), so the last commit touching gemini-acceptance.json is that one. Read from
# git at 6cf546bf: `git log -- native-readers/<harness>-acceptance.json` lists 5457e75e for codex, 5292df49 then
# 5457e75e for gemini.
# Javier accepted the Codex reader again at 46132ace (Tue 27 Oct 2026 12:22, the pf1-codex-turnitem and
# pf1-codex-fcdelete reader at dc95f44b), merged here by lane L6f, so the last commit touching codex-acceptance.json
# is that one. Read from git at the L6f merge 61a63419: `git log -- native-readers/codex-acceptance.json` lists
# 46132ace then 5457e75e.
# Javier accepted both readers again in one commit, 63bb03e5 (Sun 1 Nov 2026 09:24, OD173), after lane
# fold6/kill-leftovers' drive.py line at ec62dec8, so the last commit touching each acceptance record is that one. Read
# from git at 63bb03e5: `git log -- native-readers/<harness>-acceptance.json` lists 63bb03e5, 46132ace, 5457e75e for
# codex and 63bb03e5, 5292df49, 5457e75e for gemini.
ACCEPTED_AT = {"codex": "63bb03e523ccc9e523c8a9251f761cd8406f28fd",
               "gemini": "63bb03e523ccc9e523c8a9251f761cd8406f28fd"}


class AcceptedRecords(unittest.TestCase):
    def test_the_study_holds_javiers_two_records_and_the_registry_both_readers(self):
        m = nrr()
        for harness, prof in sorted(m.PROFILES.items()):
            with self.subTest(harness=harness):
                self.assertTrue((HERE / prof["acceptance"]).exists(), f"{harness}'s acceptance record is gone")
                # a lane never commits or rewrites an acceptance record: the last commit touching it is his
                self.assertEqual(m.acceptance_provenance(HERE, harness)["acceptance_commit"], ACCEPTED_AT[harness],
                                 f"{harness}'s acceptance record was committed after Javier's acceptance commit")
        self.assertEqual(m.production_readers(), {"codex": m.codex_reader, "gemini": m.gemini_reader})


# The registration gates, the positive registration and its single mutations run on walks made by the real road
# (WalkDriver, GeminiAdapter, walk_runner, WalkRepo) in tests/test_pending_walk.py (registration review finding 2): a
# hand-built walk folder now stops at the finding-1 gates, so the hand fixtures of fd4177e0 and cfe5269a moved there.

if __name__ == "__main__":
    unittest.main()
