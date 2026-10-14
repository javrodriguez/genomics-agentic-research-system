"""Synthetic seam proof only; no live stream or production acceptance claim."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transcript_view as tv


class BindingTests(unittest.TestCase):
    def test_factory_selects_only_explicit_harness_and_requires_rollout(self):
        import drive
        take = SimpleNamespace(launched=SimpleNamespace(take_id="take-1", spec=SimpleNamespace(run_tree="/synthetic/tree")),
                               identity={"session_id": "study-1"}, folder="/synthetic/records")
        args = dict(runtime=None, login_file="/synthetic/login", counters_for=lambda take: {},
                    pin_for=lambda row: {"permission_mode": "yolo" if row["agent"]["harness"] == "gemini" else "bypass"},
                    clock=lambda: 0)
        factory = drive.harness_adapter_for(**args, rollout_for=lambda take, n: "synthetic rollout")
        for harness in ("claude-code", "codex", "gemini"):
            row = {"agent": {"harness": harness}, "model": "synthetic-model"}
            adapter = factory(row, take)
            self.assertEqual(adapter.name, harness)
            drive.adapter_class_problems(adapter)
            if harness == "codex":
                self.assertEqual(adapter.rollout_for(1), "synthetic rollout")
        with self.assertRaises(drive.AdapterIdentityRefused):
            factory({"agent": {"harness": "unknown"}}, take)
        with self.assertRaises(drive.DriveRefused):
            drive.harness_adapter_for(**args)({"agent": {"harness": "codex"}, "model": "synthetic-model"}, take)

    def test_production_classes(self):
        import drive
        import claude_code_adapter
        import codex_adapter
        import gemini_adapter
        for cls in (claude_code_adapter.ClaudeCodeAdapter, codex_adapter.CodexAdapter, gemini_adapter.GeminiAdapter):
            adapter = object.__new__(cls)
            drive.adapter_class_problems(adapter)
            drive.adapter_identity_problems(adapter, {"agent": {"harness": cls.name}})
            with self.assertRaises(drive.AdapterIdentityRefused):
                drive.adapter_identity_problems(adapter, {"agent": {"harness": "wrong"}})
            subclass = type("Pretender", (cls,), {})
            with self.assertRaises(drive.AdapterIdentityRefused):
                drive.adapter_class_problems(object.__new__(subclass))

    def record(self, folder, harness):
        native = ([{"type": "thread.started", "thread_id": "vendor-1"},
                   {"type": "item.completed", "item": {"id": "a", "type": "agent_message", "text": "answer"}}]
                  if harness == "codex" else
                  [{"type": "init", "session_id": "vendor-1", "model": "gemini-test"},
                   {"type": "message", "role": "user", "content": "operator"},
                   {"type": "message", "role": "assistant", "content": "answer"}])
        raw = ("\n".join(json.dumps(r) for r in native) + "\n").encode()
        (folder / "turn-1.jsonl").write_bytes(raw)
        envelope = {"type": "harness-turn", "harness": harness, "session_id": "study-1",
                    "vendor_session_id": "vendor-1", "n": 1, "sent": "operator",
                    "stream": "turn-1.jsonl", "sha256": hashlib.sha256(raw).hexdigest()}
        ledger = {"agent": {"harness": harness}, "session_id": "study-1",
                  "turns": [{"n": 1, "sent": "operator"}], "streams": ["turn-1.jsonl"]}
        (folder / "driver-ledger.json").write_text(json.dumps(ledger))
        path = folder / "transcript.jsonl"
        path.write_text(json.dumps(envelope) + "\n")
        return path, envelope

    def test_bound_native_streams(self):
        for harness in ("codex", "gemini"):
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as tmp:
                path, _ = self.record(Path(tmp), harness)
                evs = tv.events(harness, path)
                self.assertEqual(tv.operator_lines(evs), ["operator"])
                self.assertEqual([(e.turn, e.text) for e in evs if e.kind == tv.AGENT_TEXT], [(1, "answer")])

    def test_binding_mutations_refuse(self):
        for harness in ("codex", "gemini"):
            for key, bad in (("harness", "claude-code"), ("session_id", "other"),
                             ("vendor_session_id", "other"), ("n", 2), ("sent", "other"),
                             ("stream", "../turn-1.jsonl"), ("sha256", "0" * 64)):
                with self.subTest(harness=harness, key=key), tempfile.TemporaryDirectory() as tmp:
                    path, envelope = self.record(Path(tmp), harness)
                    envelope[key] = bad
                    path.write_text(json.dumps(envelope) + "\n")
                    with self.assertRaises(tv.ViewError):
                        tv.events(harness, path)

    def test_native_stream_requires_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self.record(Path(tmp), "codex")
            with self.assertRaises(tv.ViewError):
                tv.events("codex", path.parent / "turn-1.jsonl")

    def test_gemini_missing_native_user_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, envelope = self.record(Path(tmp), "gemini")
            stream = path.parent / "turn-1.jsonl"
            records = [json.loads(line) for line in stream.read_text().splitlines()]
            raw = ("\n".join(json.dumps(r) for r in records if r.get("role") != "user") + "\n").encode()
            stream.write_bytes(raw)
            envelope["sha256"] = hashlib.sha256(raw).hexdigest()
            path.write_text(json.dumps(envelope) + "\n")
            with self.assertRaises(tv.ViewError):
                tv.events("gemini", path)

    def test_special_files_refuse_before_open(self):
        from unittest.mock import patch
        for name in ("turn-1.jsonl", "driver-ledger.json", "transcript.jsonl"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                path, _ = self.record(Path(tmp), "codex")
                special = path.parent / name
                special.unlink()
                os.mkfifo(special)
                original = os.open
                def bounded_open(candidate, flags, *args, **kwargs):
                    if Path(candidate) == special:
                        raise AssertionError("special file must refuse before open")
                    return original(candidate, flags, *args, **kwargs)
                with patch("vendor_record_binding.os.open", side_effect=bounded_open):
                    with self.assertRaises(tv.ViewError):
                        tv.events("codex", path)

    def test_missing_duplicate_and_linked_streams_refuse(self):
        for mutation in ("missing-ledger", "duplicate-turn", "stream-link", "unlisted-stream"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                path, envelope = self.record(Path(tmp), "codex")
                ledger_path = path.parent / "driver-ledger.json"
                if mutation == "missing-ledger":
                    ledger_path.unlink()
                elif mutation == "duplicate-turn":
                    path.write_text((json.dumps(envelope) + "\n") * 2)
                elif mutation == "stream-link":
                    stream = path.parent / "turn-1.jsonl"
                    stream.rename(path.parent / "other.jsonl")
                    stream.symlink_to("other.jsonl")
                else:
                    ledger = json.loads(ledger_path.read_text())
                    ledger["streams"].append("missing.jsonl")
                    ledger_path.write_text(json.dumps(ledger))
                with self.assertRaises(tv.ViewError):
                    tv.events("codex", path)

    def test_recovery_uses_interaction_position_not_script_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, envelope = self.record(Path(tmp), "codex")
            folder = path.parent
            (folder / "turn-2.jsonl").write_bytes((folder / "turn-1.jsonl").read_bytes())
            second = dict(envelope, n=2, stream="turn-2.jsonl")
            path.write_text(json.dumps(envelope) + "\n" + json.dumps(second) + "\n")
            ledger_path = folder / "driver-ledger.json"
            ledger = json.loads(ledger_path.read_text())
            ledger["turns"].append(dict(ledger["turns"][0]))
            ledger["streams"].append("turn-2.jsonl")
            ledger_path.write_text(json.dumps(ledger))
            evs = tv.events("codex", path)
            self.assertEqual([(e.turn, e.text) for e in evs if e.kind == tv.AGENT_TEXT],
                             [(1, "answer"), (2, "answer")])


if __name__ == "__main__":
    unittest.main()
