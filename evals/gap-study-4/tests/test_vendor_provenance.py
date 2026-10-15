"""Synthetic source joins, not a recording of either vendor's native session."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ProvenanceTests(unittest.TestCase):
    def test_later_native_snapshots_cannot_rewrite_earlier_interactions(self):
        vp = self.module()
        self.assertTrue(callable(getattr(vp, "session_history_facts", None)), "native snapshot history join is not built")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first = {"session_id": "native-1", "requested_model": None, "version": None,
                     "cwd": None, "permission_mode": None, "sent": "first", "output": ["first output"]}
            second = dict(first, sent="second", output=["second output"])
            def retain(name, records):
                raw = json.dumps(records).encode()
                (folder / name).write_bytes(raw)
                return {"file": name, "sha256": hashlib.sha256(raw).hexdigest()}
            def reader(raw, ordinal):
                records = json.loads(raw)
                if ordinal > len(records):
                    raise vp.ProvenanceRefused("snapshot lacks requested interaction")
                return records[ordinal - 1]
            readers = {"gemini": reader}
            one = retain("snapshot-1.native", [first])
            two = retain("snapshot-2.native", [first, second])
            got = vp.session_history_facts("gemini", folder, [one, two], readers=readers)
            self.assertEqual([turn["sent"]["value"] for turn in got], ["first", "second"])
            for changed in (dict(first, sent="rewritten"), dict(first, output=["rewritten"]),
                            dict(first, session_id="other"), dict(first, version="newly asserted")):
                bad = retain("snapshot-bad.native", [changed, second])
                with self.assertRaises(vp.ProvenanceRefused):
                    vp.session_history_facts("gemini", folder, [one, bad], readers=readers)
            other = retain("other-session.native", [first, dict(second, session_id="other")])
            with self.assertRaises(vp.ProvenanceRefused):
                vp.session_history_facts("gemini", folder, [one, other], readers=readers)
            for refs in ([], [two, two], [one, retain("short.native", [first])]):
                with self.assertRaises(vp.ProvenanceRefused):
                    vp.session_history_facts("gemini", folder, refs, readers=readers)
            with self.assertRaises(vp.ProvenancePending):
                vp.session_history_facts("gemini", folder, [one, two])

    def test_native_jsonl_uses_literal_newlines(self):
        import transcript_view as tv
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            answer = "first\u2028second\u2029third"
            sent = "prompt\u2028part\u2029end"
            native = [{"type": "init", "session_id": "vendor-1", "model": "synthetic-model"},
                      {"type": "message", "role": "user", "content": sent},
                      {"type": "message", "role": "assistant", "content": answer}]
            raw = ("\n".join(json.dumps(rec, ensure_ascii=False) for rec in native) + "\n").encode()
            (folder / "turn-1.jsonl").write_bytes(raw)
            envelope = {"type": "harness-turn", "harness": "gemini", "session_id": "study-1",
                        "vendor_session_id": "vendor-1", "n": 1, "sent": sent, "stream": "turn-1.jsonl",
                        "sha256": hashlib.sha256(raw).hexdigest()}
            (folder / "transcript.jsonl").write_text(json.dumps(envelope, ensure_ascii=False) + "\n")
            (folder / "driver-ledger.json").write_text(json.dumps({"agent": {"harness": "gemini"},
                "session_id": "study-1", "turns": [{"n": 1, "sent": sent}], "streams": ["turn-1.jsonl"]}))
            try:
                events = tv.events("gemini", folder / "transcript.jsonl")
            except tv.ViewError as exc:
                self.fail(f"valid JSON string separators must not split records: {exc}")
            self.assertEqual([event.text for event in events if event.kind == tv.AGENT_TEXT], [answer])
            self.assertEqual(tv.operator_lines(events), [sent])

    def module(self):
        try:
            return importlib.import_module("vendor_provenance")
        except ImportError:
            self.fail("vendor provenance reader is not built")

    def test_actual_launch_binds_model_mode_cwd_and_prompt(self):
        vp = self.module()
        import codex_adapter as ca
        import gemini_adapter as ga
        for harness, adapter, mode in (("codex", ca, "bypass"), ("gemini", ga, "yolo")):
            with self.subTest(harness=harness):
                launch = {"schema": 1, "harness": harness, "container_id": "a" * 64,
                          "argv": adapter.argv("sent", model="synthetic-model", mode=mode,
                                               session_id=None, first=True),
                          "cwd": "/synthetic/tree", "stream": "/synthetic/record/turn-1.jsonl", "started_at": 1.0}
                want = {"harness": harness, "container_id": "a" * 64, "model": "synthetic-model",
                        "mode": mode, "run_tree": "/synthetic/tree", "stream": launch["stream"],
                        "sent": "sent", "vendor_session_id": "first-turn", "ordinal": 1}
                facts = vp.launch_facts(launch, want)
                self.assertEqual(facts["permission_mode"], {"value": mode, "source": "actual-launch"})
                self.assertEqual(facts["requested_model"], {"value": "synthetic-model", "source": "actual-launch"})
                for key, bad in (("cwd", "/elsewhere"), ("harness", "other"), ("container_id", "b" * 64),
                                 ("stream", "/elsewhere/turn-1.jsonl")):
                    with self.subTest(key=key), self.assertRaises(vp.ProvenanceRefused):
                        vp.launch_facts(dict(launch, **{key: bad}), want)
                for session, ordinal in (("session-1", 1), ("first-turn", 2), ("", 1)):    # batch-8 finding 5
                    with self.subTest(session=session, ordinal=ordinal), self.assertRaises(vp.ProvenanceRefused):
                        vp.launch_facts(launch, dict(want, vendor_session_id=session, ordinal=ordinal))
                for argv in (launch["argv"] + ["extra"], ["gemini", "-p", "sent"],
                             [s.replace("synthetic-model", "wrong-model") for s in launch["argv"]]):
                    with self.assertRaises(vp.ProvenanceRefused):
                        vp.launch_facts(dict(launch, argv=argv), want)

    def test_observed_version_and_pinned_bytes(self):
        vp = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for harness, raw in (("codex", b"codex-cli 0.162.1\n"), ("gemini", b"0.64.0\n")):
                version = "0.162.1" if harness == "codex" else "0.64.0"
                (folder / "version.stdout").write_bytes(raw)
                ref = {"file": "version.stdout", "sha256": hashlib.sha256(raw).hexdigest()}
                self.assertEqual(vp.version_fact(harness, folder, ref, expected=version),
                                 {"value": version, "source": "observed-version"})
                with self.assertRaises(vp.ProvenanceRefused):
                    vp.version_fact(harness, folder, ref, expected="PENDING")
                with self.assertRaises(vp.ProvenanceRefused):
                    vp.version_fact(harness, folder, ref, expected="0.0.0")
            raw = b"synthetic pinned instruction bytes\n"
            (folder / "instruction.txt").write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            refs = {"CLAUDE.md": {"file": "instruction.txt", "sha256": digest}}
            self.assertEqual(vp.pinned_files(folder, refs, {"CLAUDE.md": digest}, source="pinned-instructions"),
                             {"CLAUDE.md": {"value": digest, "source": "pinned-instructions"}})
            for expected in ({}, {"CLAUDE.md": "0" * 64}, {"CLAUDE.md": "PENDING"}):
                with self.assertRaises(vp.ProvenanceRefused):
                    vp.pinned_files(folder, refs, expected, source="pinned-instructions")

    def test_session_reader_is_mandatory_and_independent(self):
        vp = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = b'{"synthetic":true}\n'
            (root / "session.native").write_bytes(raw)
            ref = {"file": "session.native", "sha256": hashlib.sha256(raw).hexdigest()}
            with self.assertRaises(vp.ProvenancePending):
                vp.session_facts("gemini", root, ref, ordinal=1)
            observed = []
            def independent(raw_bytes, ordinal):
                observed.append((raw_bytes, ordinal))
                return {"session_id": "vendor-1", "requested_model": "synthetic-model", "version": "0.0.1",
                        "cwd": "/synthetic/tree", "permission_mode": None, "sent": "sent", "output": []}
            got = vp.session_facts("gemini", root, ref, ordinal=1, readers={"gemini": independent})
            self.assertEqual(observed, [(raw, 1)])
            self.assertIsNone(got["permission_mode"])
            self.assertEqual(got["requested_model"]["source"], "native-session")
            with self.assertRaises(vp.ProvenanceRefused):
                vp.session_facts("gemini", root, dict(ref, sha256="0" * 64), ordinal=1,
                                 readers={"gemini": independent})

    def test_contradictions_and_missing_crosscheck_refuse(self):
        vp = self.module()
        stream = {"session_id": "vendor-1", "requested_model": "synthetic-model", "sent": "sent", "output": []}
        session = {"session_id": {"value": "vendor-1", "source": "native-session"},
                   "requested_model": {"value": "synthetic-model", "source": "native-session"},
                   "sent": {"value": "sent", "source": "native-session"},
                   "output": {"value": [], "source": "native-session"}}
        self.assertEqual(vp.cross_check(stream, session), [])
        for key in stream:
            bad = dict(session)
            bad[key] = {"value": "contradiction", "source": "native-session"}
            self.assertIn(key, vp.cross_check(stream, bad))
            del bad[key]
            if key != "requested_model":
                self.assertIn(key, vp.cross_check(stream, bad))
        optional_missing = dict(session, requested_model=None)
        self.assertEqual(vp.cross_check(stream, optional_missing), [])


if __name__ == "__main__":
    unittest.main()
