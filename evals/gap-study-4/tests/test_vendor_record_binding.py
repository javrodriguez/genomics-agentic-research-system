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
        # Codex slice 3: without a rollout_for, the rollout is read where Codex writes it, in the take's config
        # folder (CODEX_HOME), by the adapter's own thread id; none there refuses, never a guess.
        import tempfile
        import native_snapshot
        # Drive-wiring review MAJOR 1 (573b5a61): the read goes only through the box's view of the config folder
        # (TakeDriver.config_view: operator_list one level as (name, kind), operator_read bytes or None); the view here
        # is a faithful host-side stand-in over a scratch folder. With no view the read refuses, never host-side.
        def view_of(home):
            def lister(rel):
                d = Path(home) / rel
                if not d.is_dir():
                    return None
                return [(e.name, "link" if e.is_symlink() else "dir" if e.is_dir() else "file") for e in d.iterdir()]

            def reader(rel):
                f = Path(home) / rel
                return f.read_bytes() if f.is_file() else None
            return lambda take: (lister, reader)
        with tempfile.TemporaryDirectory() as home:
            take.config_dir = home
            folder = Path(home) / "sessions" / "2026" / "10" / "14"
            folder.mkdir(parents=True)
            (folder / "rollout-2026-10-14T05-00-00-0000-thread-1.jsonl").write_text("the live rollout\n")
            blind = drive.harness_adapter_for(**args)({"agent": {"harness": "codex"}, "model": "synthetic-model"},
                                                       take)
            blind.thread_id = "0000-thread-1"
            with self.assertRaises(native_snapshot.SnapshotRefused):
                blind.rollout_for(1)                  # no box road: refused although the file is on the host
            (folder / "rollout-2026-10-14T05-00-00-0000-thread-1.jsonl").unlink()
            adapter = drive.harness_adapter_for(**args, config_view=view_of(home))(
                {"agent": {"harness": "codex"}, "model": "synthetic-model"}, take)
            adapter.thread_id = "0000-thread-1"
            with self.assertRaises(native_snapshot.SnapshotRefused):
                adapter.rollout_for(1)
            (folder / "rollout-2026-10-14T05-00-00-0000-thread-1.jsonl").write_text("the live rollout\n")
            self.assertEqual(adapter.rollout_for(1), "the live rollout\n")

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

    def test_a_bound_transcript_binds_by_its_path_and_its_lines(self):
        """Item E's review (glitch-6b, 15 Oct 2026): run hands the graders a transcript_view.BoundTranscript, the
        file's lines carrying its path; the binding reads it by its path and refuses when the file's lines are no
        longer the carried ones; it is never a str, bytes or path, so a grader's bare-path guard still refuses one."""
        import os
        for harness in ("codex", "gemini"):
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as tmp:
                path, envelope = self.record(Path(tmp), harness)
                bound = tv.BoundTranscript(path)
                self.assertEqual(list(bound), path.read_text().splitlines())
                self.assertEqual(tv.events(harness, bound), tv.events(harness, path))
                self.assertFalse(isinstance(bound, (str, bytes, os.PathLike)))
                with self.assertRaises(AttributeError):
                    bound.x = 1
                self.assertEqual(tv.events(harness, list(bound)), tv.events(harness, path))   # a grader's copy
                with self.assertRaises(tv.ViewError):              # a plain list of the same lines is unbound
                    tv.events(harness, [str(x) for x in bound])
                with self.assertRaises(tv.ViewError):              # so is a part of the copy
                    tv.events(harness, list(bound)[:-1] or [str(bound[0])])
                path.write_text(path.read_text() + json.dumps(dict(envelope, n=2)) + "\n")
                with self.assertRaisesRegex(tv.ViewError, "lines are not its file's lines"):
                    tv.events(harness, bound)                       # one value never carries two transcripts

    def test_only_the_whole_ordered_copy_is_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "t.jsonl"
            f.write_text('{"a": 1}\n{"b": 2}\n{"c": 3}\n')
            b = tv.BoundTranscript(f)
            other = tv.BoundTranscript(f)                          # the same bytes, another value
            self.assertIs(tv.BoundTranscript.of(b), b)
            self.assertIs(tv.BoundTranscript.of(list(b)), b)
            self.assertIs(tv.BoundTranscript.of(tuple(b)), b)
            for bad in (list(b)[:2], list(b)[1:], list(b)[::-1], [str(x) for x in b], list(b)[:2] + [other[2]],
                        [], f, str(f), "".join(b)):
                with self.subTest(bad=type(bad).__name__):
                    self.assertIsNone(tv.BoundTranscript.of(bad))

    def test_the_grader_guard_still_refuses_a_bare_path(self):
        from graders import endstate, plan_gate
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self.record(Path(tmp), "codex")
            ev = object.__new__(endstate.Evidence)
            for bare in (path, str(path)):
                with self.assertRaises(TypeError):
                    plan_gate.take_events(bare, ev)

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
