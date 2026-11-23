"""Lane vendor-b27 stage 3 (glitch-f1's rulings 2 and 3, 21 Oct 2026): the reader harness (box/stub_model_reading.py)
and the b27 structure-only cutter (tests/fixtures/b27-stub/cut_structure.py), on synthetic probe folders only.

The harness: lane vendor-b26's readers, unchanged, over each scenario's snapshots; one line per scenario with each
snapshot's PASS or refusal reason, the history join, the design's prediction marked "as predicted" or "DIFFERS", and the
stub log's masked, truncated, snapshot and helper requests placed in their processes. The synthetic folders reuse lane
vendor-b26's committed structure-only fixtures (w-g47's masking re-record, which the reader admits) and a third
snapshot that records a retired id again (the resume after a re-record, which it refuses by name).

The cutter: the truncation wrapper with its numbers and the <state_snapshot> wrapper kept around synthetic text, the
CLI's acknowledgement kept verbatim, every other string synthetic, a snapshot that was a byte prefix of the next still
one, and its PROVENANCE.
"""
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from box import stub_model_reading as smr  # noqa: E402

B26 = STUDY / "tests" / "fixtures" / "b26-rewrites"
_cut = importlib.util.spec_from_file_location("b27_cut_structure", STUDY / "tests" / "fixtures" / "b27-stub" /
                                              "cut_structure.py")
cut = importlib.util.module_from_spec(_cut)
_cut.loader.exec_module(cut)


def retired_again(raw: bytes) -> bytes:
    """The snapshot with one message a re-record retired recorded again: the resume-after-re-record shape."""
    lines = raw.decode("utf-8").splitlines()
    records = [json.loads(x) for x in lines if x.strip()]
    removed = next(r["$patch"]["removeIds"] for r in records if "$patch" in r and r["$patch"].get("removeIds"))
    original = next(r for r in records if r.get("id") == removed[0])
    return raw + (json.dumps(original) + "\n").encode("utf-8")


def make_probe(root: Path, *, expect_3="refused") -> Path:
    probe = root / "stub-probe-t"
    s = probe / "A1" / "session"
    s.mkdir(parents=True)
    t1 = (B26 / "w-g47-native-turn-1.jsonl").read_bytes()
    t2 = (B26 / "w-g47-native-turn-2.jsonl").read_bytes()
    (s / "native-turn-1.jsonl").write_bytes(t1)
    (s / "native-turn-2.jsonl").write_bytes(t2)
    (s / "native-turn-3.jsonl").write_bytes(retired_again(t2))
    third = {"verdict": "PASS"} if expect_3 == "PASS" else \
        {"verdict": "refused", "reason_contains": "a retired native message id is recorded again"}
    (probe / "A1" / "scenario.json").write_text(json.dumps({"scenario": "A1", "processes": ["a", "b", "c"], "expect": {
        "snapshots": {"1": {"verdict": "PASS"}, "2": {"verdict": "PASS"}, "3": third}}}))
    (probe / "A1" / "probe.json").write_text(json.dumps({"processes": [
        {"process": 1, "started_at": 10.0, "ended_at": 20.0}, {"process": 2, "started_at": 30.0, "ended_at": 40.0},
        {"process": 3, "started_at": 50.0, "ended_at": 60.0}]}))
    (probe / "A1" / "stub").mkdir()
    rows = [{"n": 1, "at": 11.0, "endpoint": "stream", "verdict": "answered", "flags": {}},
            {"n": 2, "at": 15.0, "endpoint": "stream", "verdict": "answered", "flags": {"masked_tag": True}},
            {"n": 3, "at": 31.0, "endpoint": "generate", "verdict": "answered", "flags": {"state_snapshot": True}},
            {"n": 4, "at": 55.0, "endpoint": "stream", "verdict": "refused", "why": "unscripted", "flags": {}}]
    (probe / "A1" / "stub" / "requests.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return probe


class Isolation(unittest.TestCase):
    """Stage 7 (athena's battery on 931f946a, 5 failures and 7 errors in test_round4): load_readers deleted the
    readers from sys.modules and imported fresh copies, so in one battery process drive kept the old
    native_reader_registration while later tests' lazy imports patched the new one, and their takes read as having no
    reviewed reader. The harness must leave sys.modules and sys.path exactly as it found them."""

    def test_reading_this_study_reuses_the_loaded_readers(self):
        import native_reader_registration
        import gemini_session_replay
        before_path = list(sys.path)
        replay, nrr = smr.load_readers(STUDY)
        self.assertIs(nrr, native_reader_registration)
        self.assertIs(replay, gemini_session_replay)
        self.assertIs(sys.modules["native_reader_registration"], native_reader_registration)
        self.assertEqual(sys.path, before_path)

    def test_reading_another_study_folder_leaves_sys_modules_untouched(self):
        import native_reader_registration
        d = Path(tempfile.mkdtemp(prefix="b27i-"))
        try:
            other = d / "gap-study-4"
            shutil.copytree(STUDY, other, ignore=shutil.ignore_patterns("tests", "rehearsals", "__pycache__"))
            before = dict(sys.modules)
            before_path = list(sys.path)
            replay, nrr = smr.load_readers(other)
            self.assertEqual(Path(nrr.__file__).resolve().parent, other.resolve())
            self.assertEqual(Path(replay.__file__).resolve().parent, other.resolve())
            self.assertIs(sys.modules["native_reader_registration"], native_reader_registration)
            self.assertEqual({k: id(v) for k, v in sys.modules.items()}, {k: id(v) for k, v in before.items()})
            self.assertEqual(sys.path, before_path)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Harness(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="b27r-"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_each_snapshot_s_verdict_beside_its_prediction(self):
        r = smr.read_probe(make_probe(self.d), STUDY)[0]
        self.assertEqual([o["verdict"] for o in r["observed"]], ["PASS", "PASS", "refused"])
        self.assertIn("a retired native message id is recorded again", r["observed"][2]["reason"])
        self.assertGreater(r["observed"][1]["properties"]["tool_outputs_masked"], 0)
        self.assertEqual(r["marks"], ["as predicted", "as predicted", "as predicted"])
        self.assertTrue(r["outcome"].startswith("refused: a retired native message id"))

    def test_a_prediction_the_reader_does_not_meet_is_marked(self):
        r = smr.read_probe(make_probe(self.d, expect_3="PASS"), STUDY)[0]
        self.assertEqual(r["marks"][2], "DIFFERS")

    def test_a_refusal_for_another_reason_is_marked(self):
        probe = make_probe(self.d)
        doc = json.loads((probe / "A1" / "scenario.json").read_text())
        doc["expect"]["snapshots"]["3"] = {"verdict": "refused", "reason_contains": "native chat compression"}
        (probe / "A1" / "scenario.json").write_text(json.dumps(doc))
        self.assertEqual(smr.read_probe(probe, STUDY)[0]["marks"][2], "DIFFERS")

    def test_a_refused_prediction_without_its_reason_is_never_met(self):
        # REVIEW-vendor-b27-25ffff5 NIT 8
        probe = make_probe(self.d)
        doc = json.loads((probe / "A1" / "scenario.json").read_text())
        doc["expect"]["snapshots"]["3"] = {"verdict": "refused"}
        (probe / "A1" / "scenario.json").write_text(json.dumps(doc))
        self.assertEqual(smr.read_probe(probe, STUDY)[0]["marks"][2], "DIFFERS (the prediction names no reason)")

    def test_every_reading_names_the_workspace_differences(self):
        # REVIEW-vendor-b27-25ffff5 MINOR 6 and glitch-f1's ruling 3
        r = smr.read_probe(make_probe(self.d), STUDY)[0]
        for words in (".stub-probe/", "not a git checkout", "no GEMINI.md"):
            self.assertIn(words, r["workspace_differences"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            smr.main([str(make_probe(self.d / "x")), "--code", str(STUDY)])
        self.assertTrue(buf.getvalue().splitlines()[0].startswith("workspace differences from a walk: "))

    def test_the_stub_log_is_placed_in_its_processes(self):
        stub = smr.read_probe(make_probe(self.d), STUDY)[0]["stub"]
        self.assertEqual(stub["masked"], "request 2 (process 1)")
        self.assertEqual(stub["state_snapshot"], "request 3 (process 2)")
        self.assertEqual(stub["helpers"], ["request 3 (process 2)"])
        self.assertEqual(stub["refused"], ["request 4 (process 3): unscripted"])
        self.assertIsNone(stub["truncation"])

    def test_the_history_join_on_an_admitted_pair(self):
        probe = make_probe(self.d)
        (probe / "A1" / "session" / "native-turn-3.jsonl").unlink()
        r = smr.read_probe(probe, STUDY)[0]
        self.assertEqual(r["history"]["verdict"], "joined")
        self.assertEqual(r["outcome"], "admitted")

    def test_a_snapshot_that_is_not_a_byte_extension_refuses_the_join(self):
        probe = make_probe(self.d)
        s = probe / "A1" / "session"
        (s / "native-turn-3.jsonl").unlink()
        (s / "native-turn-1.jsonl").write_bytes((s / "native-turn-1.jsonl").read_bytes() + b"\n")
        r = smr.read_probe(probe, STUDY)[0]
        self.assertEqual(r["history"]["verdict"], "refused")
        self.assertIn("byte extension", r["history"]["reason"])

    def test_one_line_per_scenario(self):
        probe = make_probe(self.d)
        shutil.copytree(probe / "A1", probe / "B1")
        buf = io.StringIO()
        with redirect_stdout(buf):
            smr.main([str(probe), "--code", str(STUDY)])
        out = buf.getvalue().splitlines()[1:]          # the first line names the workspace differences (MINOR 6)
        self.assertEqual([x.split(":")[0] for x in out], ["A1", "B1"])
        self.assertIn("[as predicted]", out[0])
        self.assertIn("masked request 2 (process 1)", out[0])

    def test_fewer_snapshots_than_processes_is_said(self):
        probe = make_probe(self.d)
        (probe / "A1" / "session" / "native-turn-3.jsonl").unlink()
        self.assertIn("only 2 of 3 snapshots", smr.line(smr.read_probe(probe, STUDY)[0]))


TRUNC = ("Output too large. Showing first 8,000 and last 32,000 characters. For full output see: "
         "/scratch/sp-x/t/.home/tool-outputs/read_file_call_1.txt\nr01.txt line 0000 abc\n\n"
         "... [22,000 characters omitted] ...\n\nr01.txt line 1999 xyz")
CTX = cut.b26.b25.ENV_OPEN + "Today is a synthetic day.\n" + cut.b26.b25.ENV_CLOSE


def snapshot_lines():
    env_id = cut.b26.b25.ENV_ID
    return [
        {"sessionId": "sess0001-aaaa", "projectHash": "p", "startTime": "t", "kind": "main"},
        {"id": env_id, "timestamp": "t1", "type": "user", "content": [{"text": CTX}]},
        {"id": "u1", "timestamp": "t2", "type": "user", "content": [{"text": "Read r01.txt to r04.txt one by one."}]},
        {"id": "g1", "timestamp": "t3", "type": "gemini", "content": [], "toolCalls": [
            {"id": "read_file__call_1", "name": "read_file", "args": {"file_path": "/scratch/sp-x/t/r01.txt"},
             "result": [{"functionResponse": {"id": "read_file__call_1", "name": "read_file",
                                              "response": {"output": TRUNC}}}], "status": "success"}]},
        {"id": "u2", "timestamp": "t4", "type": "user",
         "content": [{"text": "<state_snapshot>The user asked for four files.</state_snapshot>"}]},
        {"id": "g2", "timestamp": "t5", "type": "gemini", "content": [{"text": cut.ACKNOWLEDGEMENT}]},
    ]


class Cutter(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="b27c-"))
        probe = self.d / "stub-probe-t"
        s = probe / "C1" / "session"
        s.mkdir(parents=True)
        lines = [json.dumps(x) for x in snapshot_lines()]
        (s / "native-turn-1.jsonl").write_text("\n".join(lines[:3]) + "\n")
        (s / "native-turn-2.jsonl").write_text("\n".join(lines) + "\n")
        (probe / "C1" / "turn-1.jsonl").write_text(json.dumps({"type": "init", "session_id": "sess0001-aaaa",
                                                               "model": "gemini-3.8-flash"}) + "\n")
        (probe / "manifest.json").write_text("{}\n")
        self.prov = cut.main(probe, "C1", self.d / "out")
        self.out = self.d / "out"

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _records(self, name):
        return [json.loads(x) for x in (self.out / name).read_text().splitlines() if x.strip()]

    def test_the_truncation_wrapper_and_its_numbers_are_kept_around_synthetic_text(self):
        out = self._records("C1-native-turn-2.jsonl")[3]["toolCalls"][0]["result"][0]["functionResponse"]["response"]
        m = cut.TRUNCATED.fullmatch(out["output"])
        self.assertIsNotNone(m)
        self.assertEqual((m.group(1), m.group(2), m.group(5)), ("8,000", "32,000", "22,000"))
        self.assertTrue(m.group(3).startswith("/work/synthetic-text-"))
        self.assertTrue(m.group(4).startswith("synthetic text ") and m.group(6).startswith("synthetic text "))

    def test_the_snapshot_wrapper_and_the_acknowledgement(self):
        recs = self._records("C1-native-turn-2.jsonl")
        text = recs[4]["content"][0]["text"]
        self.assertTrue(text.startswith("<state_snapshot>synthetic text ") and text.endswith("</state_snapshot>"))
        self.assertEqual(recs[5]["content"][0]["text"], "Got it. Thanks for the additional context!")

    def test_nothing_of_the_source_text_survives_and_the_prefix_holds(self):
        both = (self.out / "C1-native-turn-2.jsonl").read_text()
        for word in ("r01.txt line", "Read r01.txt", "four files", "/scratch/sp-x", "synthetic day"):
            self.assertNotIn(word, both)
        self.assertTrue(both.startswith((self.out / "C1-native-turn-1.jsonl").read_text()))
        self.assertEqual(self._records("C1-native-turn-2.jsonl")[1]["content"][0]["text"], cut.b26.CONTEXT_TEXT)

    def test_provenance(self):
        got = json.loads((self.out / "PROVENANCE.json").read_text())
        self.assertEqual(got["made_by"], "cut_structure.py (lane vendor-b27)")
        self.assertEqual(sorted(got["files"]), ["C1-native-turn-1.jsonl", "C1-native-turn-2.jsonl", "C1-turn-1.jsonl"])
        src = self.d / "stub-probe-t" / "C1" / "session" / "native-turn-2.jsonl"
        self.assertEqual(got["files"]["C1-native-turn-2.jsonl"]["sha256"], hashlib.sha256(src.read_bytes()).hexdigest())
        self.assertEqual(got["probe_manifest_sha256"], hashlib.sha256(b"{}\n").hexdigest())


if __name__ == "__main__":
    unittest.main()
