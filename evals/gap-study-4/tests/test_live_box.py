"""Regressions grounded in Athena's no-login Docker 29.8.1 probes, 13 Oct 2026.

No Docker or model is run by this module. Live evidence is retained separately.
"""
import signal
import sys
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_saved_path = sys.path[:]
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from box import run_take as rt
    from box import sidecar, preflight, take_config
finally:
    sys.path[:] = _saved_path


class Runtime:
    def __init__(self, output=""):
        self.output = output
        self.calls = []

    def run(self, argv, **kwargs):
        self.calls.append(argv)
        return rt.Completed(0, self.output, "")


class LiveProcessRegression(unittest.TestCase):
    def test_top_uid_namespace_is_measured_and_used(self):
        form = {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID", "uid_column": "UID"}
        table = "PID UID COMMAND\n4100 10003 sleep\n4200 10001 sleep\n4300 110000 other\n"
        for namespace, expected in (("container", [4200]), ("host", [4300])):
            with self.subTest(namespace=namespace), mock.patch.object(rt, "TOP_FORMAT", dict(form, uid_namespace=namespace)):
                self.assertEqual(rt.agent_processes(Runtime(table), "a" * 64, agent_uid=10001,
                                                     uid_map=((0, 1000, 1), (1, 100000, 65536))), expected)

    def test_unknown_top_uid_namespace_refuses(self):
        form = {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID", "uid_column": "UID"}
        for namespace in (None, "unknown"):
            with self.subTest(namespace=namespace), mock.patch.object(rt, "TOP_FORMAT", dict(form, uid_namespace=namespace)):
                with self.assertRaises(rt.Refused):
                    rt.agent_processes(Runtime("PID UID COMMAND\n4200 10001 sleep\n"), "a" * 64,
                                       agent_uid=10001, uid_map=((0, 1000, 1), (1, 100000, 65536)))

    def test_kill_uses_working_same_user_primitive(self):
        runtime = Runtime()
        rt.kill_agent(runtime, "a" * 64, agent_user=rt.AGENT_USER)
        argv = runtime.calls[0]
        self.assertEqual(argv[:5], ["docker", "exec", "--user", "10001:10001", "a" * 64])
        self.assertEqual(argv[5:9], ["/usr/bin/python3", "-I", "-S", "-c"])
        with mock.patch("os.kill") as kill:
            exec(argv[9], {})
        kill.assert_called_once_with(-1, signal.SIGKILL)

    def test_empty_agent_cleanup_accepts_only_esrch(self):
        runtime = Runtime()
        rt.kill_agent(runtime, "a" * 64, agent_user=rt.AGENT_USER)
        program = runtime.calls[0][-1]
        with mock.patch("os.kill", side_effect=ProcessLookupError):
            exec(program, {})
        for error in (PermissionError, OSError):
            with self.subTest(error=error), mock.patch("os.kill", side_effect=error):
                with self.assertRaises(error):
                    exec(program, {})


class LaunchJournalRegression(unittest.TestCase):
    def test_journal_exists_before_exec_and_excludes_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            stream = str(Path(folder) / "turn-1.jsonl")
            inner = ["gemini", "--approval-mode", "yolo", "-m", "gemini-3.8-flash"]
            launch = Path(stream + ".launch.json")
            expected = {"schema": 1, "harness": "gemini", "container_id": "a" * 64,
                        "argv": inner, "cwd": "/srv/w/tree", "stream": stream, "started_at": 1.0}

            def execute(argv, **kwargs):
                self.assertTrue(launch.exists(), "launch journal missing before runtime exec")
                self.assertEqual(json.loads(launch.read_text()), expected)
                self.assertEqual(launch.stat().st_mode & 0o777, 0o600)
                self.assertNotIn("synthetic credential value", launch.read_text())
                return rt.Completed(0, "synthetic stream", "")

            runtime = mock.Mock(run=execute)
            with mock.patch.object(rt, "exec_argv", return_value=(["docker", "exec"], {"credential": "synthetic credential value"})), \
                    mock.patch.object(rt, "refuse_env_files"), \
                    mock.patch.object(rt, "check_config_folder"):   # B11's own tests: tests/test_config_folder.py
                got = rt.run_turn(runtime, "a" * 64, inner, harness="gemini", run_tree="/srv/w/tree",
                                  login_file="/unused", stream_path=stream, budget_s=2,
                                  clock=iter((1.0, 2.0)).__next__)
            self.assertEqual(got["launch_path"], str(launch))
            self.assertEqual(Path(stream).read_text(), "synthetic stream")

    def test_existing_launch_refuses_before_exec(self):
        with tempfile.TemporaryDirectory() as folder:
            stream = str(Path(folder) / "turn-1.jsonl")
            Path(stream + ".launch.json").write_text("kept")
            runtime = mock.Mock()
            with self.assertRaisesRegex(rt.Refused, "launch"):
                rt.run_turn(runtime, "a" * 64, ["gemini"], harness="gemini", run_tree="/srv/w/tree",
                            login_file="/unused", stream_path=stream, budget_s=2, clock=lambda: 1)
            runtime.run.assert_not_called()


class SubscriptionTransitionRegression(unittest.TestCase):
    def test_codex_refuses_before_credential_read_or_runtime(self):
        # the closed gate, pinned (B8-1; review REVIEW-vendor-r18-b8-ddef2f4 MAJOR 1): it refuses before any read
        with mock.patch.object(rt, "read_login") as read, mock.patch.object(rt, "CODEX_SUBSCRIPTION_READY", False):
            with self.assertRaisesRegex(rt.NotReady, "subscription binding not ready"):
                rt.exec_argv("a" * 64, ["codex", "exec", "prompt"], user=rt.AGENT_USER,
                             workdir="/srv/w/tree", harness=rt.CODEX, run_tree="/srv/w/tree",
                             login_file="/must-not-read", caller_env={})
            read.assert_not_called()

    def test_walk_login_and_scanner_refuse_before_open(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        try:
            import walk_builders
            from box import scan_record  # noqa: F401  imported here, so no import runs under the patches below
        finally:
            sys.path.pop(0)
        # glitch-6b's ruling (14 Oct 2026, under Javier's delegation) on glitch-5a's ruled NO_LOGIN for a Codex row:
        # a tree whose walk_builders carries NO_LOGIN (the harness's lease road) refuses a Codex row's login file with
        # "its login is the lease"; a box-alone tree keeps the closed subscription binding's refusal. Either way the
        # refusal comes before anything is looked up, opened or read.
        if hasattr(walk_builders, "NO_LOGIN"):
            self.assertEqual(walk_builders.NO_LOGIN, rt.NO_LOGIN)
            self.assertEqual(walk_builders.login_name(rt.CODEX), rt.NO_LOGIN)

            def expected(name):
                return rf"a Codex row has no login file \({name}\): its login is the lease"
        else:
            def expected(name):
                return "subscription binding not ready"
        for entry in (walk_builders.login_file_by_name, walk_builders.login_secrets):
            with self.subTest(entry=entry.__name__), \
                    mock.patch("os.open") as opened, mock.patch("os.lstat") as looked, \
                    mock.patch("builtins.open") as read_open:
                with self.assertRaisesRegex(walk_builders.BuilderRefused, expected(entry.__name__)):
                    entry("/must-not-read", rt.CODEX)
                opened.assert_not_called()
                looked.assert_not_called()
                read_open.assert_not_called()


class PublicConfigRegression(unittest.TestCase):
    def test_full_gemini_renderer_preserves_constraints_and_legacy_path(self):
        # Synthetic values exercise the renderer only (the pinned values, sourced by R3, are test_take_config's).
        with mock.patch.object(take_config, "GEMINI_THINKING", {"path": "model.thinking", "value": "minimal"}), \
                mock.patch.object(take_config, "GEMINI_AUTH_SETTING", {"path": "security.auth.selectedType", "value": "gemini-api-key"}), \
                tempfile.TemporaryDirectory() as folder:
            record = take_config.public_record(rt.GEMINI, model="gemini-3.8-flash")
            take_config.write(folder, rt.GEMINI, model="gemini-3.8-flash")
            path = Path(folder) / ".gemini/settings.json"
            settings = json.loads(path.read_text())
            self.assertIs(settings["experimental"]["adk"]["agentSessionNoninteractiveEnabled"], False)
            # Lane vendor-b14 round 2 (glitch-26's ruling R-B14-2): invoke_agent joins D8's excluded tools.
            self.assertEqual(settings["tools"]["exclude"], ["google_web_search", "web_fetch", "invoke_agent"])
            self.assertIs(settings["hooksConfig"]["enabled"], False)
            self.assertIs(settings["telemetry"]["enabled"], False)
            self.assertEqual(record["files"][0]["text"], path.read_text())
            with self.assertRaises(rt.Refused):
                take_config.write(folder, rt.GEMINI, model="gemini-3.8-flash")
        for value in ("false", "true", ""):
            with self.subTest(value=value), self.assertRaises(rt.Refused):
                rt.check_environment(rt.GEMINI, {"GEMINI_CLI_EXP_AGENT": value})

    def test_subscription_full_config_preserves_other_constraints_and_readiness(self):
        import tomllib
        with mock.patch.object(take_config, "CODEX_REASONING_EFFORT", {"gpt-5.4": "medium"}):
            record = take_config.public_record(rt.CODEX, model="gpt-5.4")
        config = tomllib.loads(record["files"][0]["text"])
        self.assertEqual(config["forced_login_method"], "chatgpt")
        self.assertEqual(config["cli_auth_credentials_store"], "file")
        self.assertEqual(config["web_search"], "disabled")
        self.assertIs(config["features"]["hooks"], False)
        self.assertIs(config["check_for_update_on_startup"], False)
        # Round 17 B6 (glitch-b5's ruling R3): the three values are sourced, so readiness is read by putting each back
        # to PENDING (this moved by that ruling from the unpatched module's NotReady); a model with no sourced effort
        # is refused.
        with mock.patch.object(take_config, "CODEX_REASONING_EFFORT", take_config.PENDING), \
                self.assertRaises(rt.NotReady):
            take_config.public_record(rt.CODEX, model="gpt-6.1-sol")
        for name in ("GEMINI_THINKING", "GEMINI_AUTH_SETTING"):
            with mock.patch.object(take_config, name, take_config.PENDING), self.assertRaises(rt.NotReady):
                take_config.public_record(rt.GEMINI, model="gemini-3.8-flash")
        with self.assertRaises(rt.Refused):
            take_config.public_record(rt.CODEX, model="gpt-5.4")

    def test_image_environment_cannot_switch_gemini_path(self):
        with mock.patch.object(rt, "INSPECT_STATUS", {}), \
                mock.patch.object(preflight, "_json_out", return_value={"present": [], "docker_host": False}), \
                mock.patch.object(preflight, "_inspect_obj", return_value={}), \
                mock.patch.object(preflight, "_facts", return_value={"env": ["GEMINI_CLI_EXP_AGENT=false"]}):
            with self.assertRaisesRegex(preflight._Fail, "mode-route"):
                preflight._check_socket({}, None)


class SidecarPrivilegeRegression(unittest.TestCase):
    def row(self, pid):
        return {"pid": pid, "uid": 10002, "uids": [10002] * 4, "gids": [10002] * 4,
                "groups": [], "cap_eff": 4, "cap_prm": 4, "cap_inh": 4, "cap_bnd": 4,
                "cap_amb": 4, "no_new_privs": 1, "name": "python3" if pid == 1 else "inotifywait"}

    def test_actual_watcher_and_pid1_have_exact_final_privileges(self):
        rows = [self.row(1), self.row(9)]
        with mock.patch.object(preflight, "_json_out", return_value=rows):
            preflight._check_watcher_cap({})
        for field, value in (("uid", 0), ("uids", [10002, 10002, 0, 10002]),
                             ("gids", [0] * 4), ("groups", [10002]), ("cap_bnd", 260),
                             ("cap_amb", 0), ("cap_prm", 260), ("no_new_privs", 0)):
            for index in (0, 1):
                changed = [self.row(1), self.row(9)]
                changed[index][field] = value
                with self.subTest(field=field, pid=changed[index]["pid"]), \
                        mock.patch.object(preflight, "_json_out", return_value=changed):
                    with self.assertRaises(preflight._Fail):
                        preflight._check_watcher_cap({})

    def test_launch_is_fixed_bootstrap_and_control_never_root(self):
        argv = sidecar.create_argv(image="sha256:" + "a" * 64, run_tree="/srv/w/tree",
                                   evidence="/srv/operator/record", watch=["file"])
        self.assertEqual(argv[argv.index("--user") + 1], "0:0")
        start = argv.index("/usr/bin/setpriv")
        self.assertIn("--reuid=10002", argv[start:])
        self.assertIn("--regid=10002", argv[start:])
        self.assertIn("--bounding-set=-all,+dac_read_search", argv[start:])
        self.assertIn("--clear-groups", argv[start:])
        self.assertEqual(sidecar.ctl_argv("a" * 64, "status")[:4],
                         ["docker", "exec", "--user", "10002:10002"])



# The sidecar launch contract (glitch-06 ruling 1, 14 Oct): the fixed launch constants live in one constants-only
# module, box/sidecar_contract.py, which preflight imports plainly and the sidecar image carries beside the program.
CONTRACT_NAMES = ("ADDED_CAPABILITY", "BOOT_USER", "BOOT_CAPABILITIES", "BOOT_INSPECT_CAPABILITIES", "WATCHER_USER",
                  "WATCHER_LAUNCHER", "INTERPRETER", "PROGRAM")
BOX = Path(__file__).resolve().parents[1] / "box"


class SidecarContractRegression(unittest.TestCase):
    def contract(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("contract_under_test", BOX / "sidecar_contract.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_contract_is_constants_only(self):
        import ast
        tree = ast.parse((BOX / "sidecar_contract.py").read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue                                                  # the docstring
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            self.assertIsInstance(node, ast.Assign, ast.dump(node)[:80])
            self.assertTrue(all(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets))
        self.assertEqual(sorted(n for n in vars(self.contract()) if n.isupper()), sorted(CONTRACT_NAMES))

    def test_sidecar_and_preflight_read_the_contract(self):
        c = self.contract()
        for name in CONTRACT_NAMES:
            self.assertEqual(getattr(sidecar, name), getattr(c, name), name)
        import ast
        side = ast.parse((BOX / "sidecar.py").read_text(encoding="utf-8"))
        # sidecar.py carries each contract value literally (its own audit admits no import of another file); the
        # equality above binds the two, and each must be a literal assignment, never derived elsewhere.
        literal = {t.id for n in side.body if isinstance(n, ast.Assign) for t in n.targets
                   if isinstance(t, ast.Name) and t.id in CONTRACT_NAMES}
        self.assertEqual(sorted(literal), sorted(CONTRACT_NAMES))
        # Review nit 1 (14 Oct): the whole module, not only its top level, assigns each contract name exactly once.
        every = [t.id for n in ast.walk(side) if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                 for t in (n.targets if isinstance(n, ast.Assign) else [n.target])
                 if isinstance(t, ast.Name) and t.id in CONTRACT_NAMES]
        self.assertEqual(sorted(every), sorted(CONTRACT_NAMES))
        pre = ast.parse((BOX / "preflight.py").read_text(encoding="utf-8"))
        froms = [(n.module, a.name, a.asname) for n in ast.walk(pre) if isinstance(n, ast.ImportFrom)
                 for a in n.names]
        self.assertIn(("box", "sidecar_contract", None), froms)
        self.assertEqual([f for f in froms if f[1] == "sidecar"], [], "preflight imports the sidecar program")

    def test_sidecar_image_carries_the_program_alone(self):
        from box import image_lock as il
        self.assertFalse(hasattr(il, "SIDECAR_COPIES"))
        lines = [ln.strip() for ln in (BOX / "sidecar" / "Dockerfile").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([ln for ln in lines if ln.startswith("COPY ")], ["COPY " + il.SIDECAR_COPY])

    def test_a_drifted_sidecar_value_is_caught(self):
        c = self.contract()
        with mock.patch.object(sidecar, "BOOT_USER", "10002:10002"):
            self.assertNotEqual(sidecar.BOOT_USER, c.BOOT_USER)
            with self.assertRaises(AssertionError):
                self.test_sidecar_and_preflight_read_the_contract()

# The new-folder watch gap (glitch-06 ruling 2, 14 Oct): athena's stub measurement (evidence stub-20261014) shows a
# file written straight into a just-created folder (`fresh/inner.txt`) never reached inotifywait's stream, while the
# same write a second later (`slow/inner.txt`) did. These tests replay that stream byte for byte through the real
# line parser and the sidecar's own event logging.
STUB_EVIDENCE = (Path(__file__).resolve().parents[3] / "lane-reports" / "live-box-evidence-2026-10-13" /
                 "stub-20261014" / "stub-result-20261014.json")
STUB_FORMAT = {"fields": ["path", "events"], "separator": "|", "established": "Watches established.",
               "setup_lines": ["Setting up watches.  Beware: since -r was given, this may take a while!"]}


class _Pipe:
    def __init__(self, data: bytes):
        import os
        r, w = os.pipe()
        os.write(w, data)
        os.close(w)
        self._r = open(r, "rb", buffering=0)

    def fileno(self):
        return self._r.fileno()

    def close(self):
        self._r.close()


class _Proc:
    def __init__(self, out: bytes, err: bytes):
        self.stdout, self.stderr = _Pipe(out), _Pipe(err)

    def poll(self):
        return None


class NewFolderGap(unittest.TestCase):
    WATCH = ("fresh/inner.txt", "slow/inner.txt", "plan/approved.json")

    def events(self):
        stub = json.loads(STUB_EVIDENCE.read_text())["stub"]["watchers"]["candidate"]
        proc = _Proc(stub["stdout"].encode(), stub["stderr"].encode())
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.stderr.close)
        with mock.patch.object(sidecar, "INOTIFYWAIT_FORMAT", STUB_FORMAT), \
                mock.patch.object(sidecar, "INOTIFYWAIT_SUBSECOND", False):
            w = sidecar._InotifyWatcher(proc, "/tree")
            self.assertTrue(w.established())
            return w.read_ready()

    def run_sidecar(self, evs):
        d = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__("shutil").rmtree(d))
        tree, ev = d / "tree", d / "ev"
        for rel in self.WATCH:
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            (tree / rel).write_text("x")
        ev.mkdir()
        sc = sidecar.Sidecar(run_tree=str(tree), evidence=str(ev), watch=list(self.WATCH), factory=None,
                             clock=lambda: 1.0e9)
        for e in evs:
            self.assertTrue(sc._event(e), e)
        read = lambda name: [json.loads(x) for x in (ev / name).read_text().splitlines()] if (ev / name).exists() else []
        return read(sidecar.ACCESS), read(sidecar.FOUND)

    def test_the_gap_reproduces_from_the_stub_stream(self):
        evs = self.events()
        paths = {e.path for e in evs}
        self.assertIn("fresh", paths)                       # the folder's CREATE reached the stream
        self.assertNotIn("fresh/inner.txt", paths)          # the file written straight into it did not
        self.assertIn("slow/inner.txt", paths)              # the file written 1 s later did
        with mock.patch.object(sidecar.Sidecar, "_present_beneath", lambda self, folder: []):
            access, found = self.run_sidecar(evs)
        self.assertEqual([a for a in access if a["path"] == "fresh/inner.txt"], [])
        self.assertTrue([a for a in access if a["path"] == "slow/inner.txt"])
        self.assertEqual(found, [])

    def test_the_rescan_records_what_the_stream_missed_apart_from_accesses(self):
        access, found = self.run_sidecar(self.events())
        self.assertEqual([a for a in access if a["path"] == "fresh/inner.txt"], [])   # never an inotify event
        self.assertEqual([(f["path"], f["source"]) for f in found],
                         [("fresh/inner.txt", sidecar.FOUND_SOURCE), ("slow/inner.txt", sidecar.FOUND_SOURCE)])
        self.assertEqual(set(found[0]), {"at", "path", "source"})



# Review of the candidate (14 Oct, finding 1 MAJOR): a file NAME was parsed as events. inotifywait 3.22.6.0 frames
# fields with NUL under --format '%w%f%0%e%0' --no-newline (probed on athena: a name cannot hold a NUL, so a '|', a
# newline or an '|OPEN' tail stays inside the path field).
NUL_FORMAT = {"fields": ["path", "events"], "separator": "\x00", "established": "Watches established.",
              "setup_lines": ["Setting up watches.  Beware: since -r was given, this may take a while!"]}
SETUP = b"Setting up watches.  Beware: since -r was given, this may take a while!\nWatches established.\n"


class HostileNames(unittest.TestCase):
    def parse(self, out: bytes):
        proc = _Proc(out, SETUP)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.stderr.close)
        with mock.patch.object(sidecar, "INOTIFYWAIT_FORMAT", NUL_FORMAT), \
                mock.patch.object(sidecar, "INOTIFYWAIT_SUBSECOND", False):
            w = sidecar._InotifyWatcher(proc, "/tree")
            self.assertTrue(w.established())
            return w.read_ready()

    def test_the_candidate_frames_with_nul(self):
        self.assertEqual(sidecar.INOTIFYWAIT_FORMAT["separator"], "\x00")
        self.assertIn("--no-newline", sidecar.INOTIFYWAIT_ARGV)
        self.assertIn("%w%f%0%e%0", sidecar.INOTIFYWAIT_ARGV)

    def test_a_name_never_becomes_events(self):
        # the bytes athena's probe printed for these names (paths rebased onto /tree)
        out = (b"/tree/a|b.txt\x00CREATE\x00/tree/x\nqc|OPEN\x00CREATE\x00/tree/qc/planted.tsv|OPEN\x00CREATE\x00"
               b"/tree/.git|CREATE,ISDIR\x00CREATE\x00")
        evs = self.parse(out)
        self.assertEqual([(e.path, e.names) for e in evs],
                         [("a|b.txt", ("CREATE",)), ("x\nqc|OPEN", ("CREATE",)),
                          ("qc/planted.tsv|OPEN", ("CREATE",)), (".git|CREATE,ISDIR", ("CREATE",))])

    def test_a_partial_record_waits_for_its_end(self):
        evs = self.parse(b"/tree/a\x00CREATE\x00/tree/b\x00")
        self.assertEqual([(e.path, e.names) for e in evs], [("a", ("CREATE",))])

    def test_a_malformed_events_field_is_a_fault(self):
        d = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__("shutil").rmtree(d))
        (d / "ev").mkdir(); (d / "tree").mkdir()
        sc = sidecar.Sidecar(run_tree=str(d / "tree"), evidence=str(d / "ev"), watch=["a.txt"], factory=None,
                             clock=lambda: 1.0e9)
        for e in self.parse(b"/tree/a.txt\x00OPEN|x\x00"):
            self.assertFalse(sc._event(e))


class LineFraming(unittest.TestCase):
    """The non-NUL road kept for other formats: the path keeps any separator, and a short line is a fault."""

    def test_separators_in_a_name_stay_in_the_path(self):
        fmt = {"fields": ["path", "events"], "separator": "|"}
        recs, rest = sidecar._split_records(b"/t/a|b.txt|CREATE\n/t/p.tsv|OPEN|CREATE\n/t/x\nqc|OPEN|CREATE\npart", fmt)
        self.assertEqual(recs, [[b"/t/a|b.txt", b"CREATE"], [b"/t/p.tsv|OPEN", b"CREATE"], [b"/t/x"],
                                [b"qc|OPEN", b"CREATE"]])
        self.assertEqual(rest, b"part")
        fmt3 = {"fields": ["at", "path", "events"], "separator": "\t"}
        recs, _ = sidecar._split_records(b"1.5\t/t/a\tb\tOPEN\n", fmt3)
        self.assertEqual(recs, [[b"1.5", b"/t/a\tb", b"OPEN"]])


    def test_a_short_line_is_a_fault_event(self):
        proc = _Proc(b"/tree/x\n/tree/a|b.txt|CREATE\n", SETUP)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.stderr.close)
        fmt = dict(NUL_FORMAT, separator="|")
        with mock.patch.object(sidecar, "INOTIFYWAIT_FORMAT", fmt), mock.patch.object(sidecar, "INOTIFYWAIT_SUBSECOND", False):
            w = sidecar._InotifyWatcher(proc, "/tree")
            self.assertTrue(w.established())
            evs = w.read_ready()
        self.assertEqual([(e.path, e.names) for e in evs], [(None, ()), ("a|b.txt", ("CREATE",))])


    def test_any_read_split_gives_the_same_records(self):
        """Reviewer r2's witness R2 (14 Oct, ported): a partial read at every byte offset yields exactly the records
        of one whole read, with nothing left over (kills mutant P4)."""
        rec = lambda path, ev: f"/tree/{path}".encode() + b"\0" + ev.encode() + b"\0"  # noqa: E731
        stream = rec("a", "CREATE") + rec("x\nq|OPEN", "CREATE") + rec("dir/", "CREATE,ISDIR") + rec("b", "MODIFY")
        whole, rest = sidecar._split_records(stream, NUL_FORMAT)
        self.assertEqual(rest, b"")
        for cut in range(len(stream) + 1):
            got, buf = sidecar._split_records(stream[:cut], NUL_FORMAT)
            more, buf = sidecar._split_records(buf + stream[cut:], NUL_FORMAT)
            self.assertEqual(got + more, whole, cut)
            self.assertEqual(buf, b"")


class RescanReach(unittest.TestCase):
    """Review findings 2 and 3: the rescan reports only paths that exist, through folders only, on folder CREATEs."""

    def make(self, watch):
        d = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__("shutil").rmtree(d))
        tree, ev = d / "tree", d / "ev"
        tree.mkdir(); ev.mkdir()
        sc = sidecar.Sidecar(run_tree=str(tree), evidence=str(ev), watch=list(watch), factory=None,
                             clock=lambda: 1.0e9)
        found = lambda: [json.loads(x)["path"] for x in (ev / sidecar.FOUND).read_text().splitlines()] \
            if (ev / sidecar.FOUND).exists() else []
        return tree, sc, found

    def test_an_absent_watched_path_is_not_found(self):
        tree, sc, found = self.make(["new/here.txt", "new/absent.txt"])
        (tree / "new").mkdir(); (tree / "new" / "here.txt").write_text("x")
        sc._event(sidecar.WatchEvent(None, "new", ("CREATE", "ISDIR")))
        self.assertEqual(found(), ["new/here.txt"])

    def test_a_path_behind_a_link_folder_is_not_found(self):
        tree, sc, found = self.make(["new/a/b.txt"])
        outside = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__("shutil").rmtree(outside))
        (outside / "b.txt").write_text("x")
        (tree / "new").mkdir(); (tree / "new" / "a").symlink_to(outside)
        sc._event(sidecar.WatchEvent(None, "new", ("CREATE", "ISDIR")))
        self.assertEqual(found(), [])

    def test_a_watched_link_itself_is_found(self):
        tree, sc, found = self.make(["new/l.txt"])
        (tree / "new").mkdir(); (tree / "new" / "l.txt").symlink_to("/nonexistent")
        sc._event(sidecar.WatchEvent(None, "new", ("CREATE", "ISDIR")))
        self.assertEqual(found(), ["new/l.txt"])        # lstat: the link exists, never followed

    def test_only_a_folder_create_rescans(self):
        tree, sc, found = self.make(["new/here.txt"])
        (tree / "new").mkdir(); (tree / "new" / "here.txt").write_text("x")
        for names in (("CREATE",), ("MODIFY", "ISDIR"), ("OPEN", "ISDIR")):
            sc._event(sidecar.WatchEvent(None, "new", names))
        self.assertEqual(found(), [])

class CandidateMode(unittest.TestCase):
    """Review item 14 (14 Oct): candidate mode names both built images by id, binds the baked program's sha256,
    runs the factory probe, and serves every scenario with nothing injected. No Docker: Proof is a fake."""

    def run_main(self, argv):
        from box import measure_live as ml
        d = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__("shutil").rmtree(d))
        calls = []

        class FakeProof:
            def __init__(self, take=None, watch=None):
                self.take_image, self.watch_image, self.calls = take, watch, []
                calls.append(("proof", take, watch))

            def scenario(self, parent, name, **kw):
                calls.append(("scenario", name, kw.get("inject", True), kw.get("source")))
                return {"scenario": name}
        out = d / "out.json"
        with mock.patch.object(ml, "Proof", FakeProof), mock.patch.object(ml.sys, "platform", "linux"), \
                mock.patch.object(ml, "factory_probe", lambda proof, parent: {"probe": True}), \
                mock.patch.object(ml, "baked_program_sha256", lambda proof: "f" * 64), \
                mock.patch.object(ml.sys, "argv", ["measure_live", "--scratch-parent", str(d), "--output", str(out)]
                                  + argv):
            ml.main()
        return json.loads(out.read_text()), calls

    def test_candidate_mode_binds_images_and_injects_nothing(self):
        a, b = "sha256:" + "a" * 64, "sha256:" + "b" * 64
        rep, calls = self.run_main(["--mode", "candidate", "--take-image", a, "--watch-image", b])
        self.assertEqual(calls[0], ("proof", a, b))
        self.assertEqual([c[1:] for c in calls[1:]], [(n, False, None) for n in
                                                    ("oracle", "always-act", "always-hold", "background-writer",
                                                     "gap-fresh")])
        self.assertEqual((rep["baked_sidecar_sha256"], rep["factory_probe"]), ("f" * 64, {"probe": True}))
        self.assertIn("candidate-image evidence", rep["scope"])

    def test_candidate_mode_refuses_an_image_not_named_by_id(self):
        for take, watch in (("take-a", "sha256:" + "b" * 64), ("sha256:" + "a" * 64, "sha256:" + "B" * 64)):
            with self.subTest(take=take), self.assertRaisesRegex(ValueError, "by sha256 id"):
                self.run_main(["--mode", "candidate", "--take-image", take, "--watch-image", watch])

class NewlinePaths(unittest.TestCase):
    """Review r2-1 (glitch-06's ruling, 14 Oct): a newline in a name under the tree is ignored, never a fault, and
    counted in the watcher-stop health record as ignored_newline_paths (no watched path or chain folder can hold one)."""

    def make(self):
        d = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__("shutil").rmtree(d))
        (d / "tree").mkdir(); (d / "ev").mkdir()
        return d, sidecar.Sidecar(run_tree=str(d / "tree"), evidence=str(d / "ev"), watch=["a.txt"], factory=None,
                                  clock=lambda: 1.0e9)

    def test_ignored_and_counted(self):
        d, sc = self.make()
        for path in ("x\ny.txt", "deep/q\n|OPEN", "a.txt"):
            self.assertTrue(sc._event(sidecar.WatchEvent(None, path, ("CREATE",))), path)
        self.assertEqual(sc._ignored_newline, 2)
        acc = [json.loads(x)["path"] for x in (d / "ev" / sidecar.ACCESS).read_text().splitlines()] \
            if (d / "ev" / sidecar.ACCESS).exists() else []
        self.assertNotIn("x\ny.txt", acc)

    def test_outside_the_tree_still_faults(self):
        _, sc = self.make()
        self.assertFalse(sc._event(sidecar.WatchEvent(None, None, ("CREATE",))))

    def test_the_stop_record_carries_the_count(self):
        d, sc = self.make()

        class W:
            def poll(self): return 0 if self.stopped else None
            def request_stop(self): self.stopped = True
            def read_ready(self): return []
            stopped = False
        sc.watcher, sc.state = W(), "running"
        sc._ignored_newline = 3
        sc._stop()
        recs = [json.loads(x) for x in (d / "ev" / sidecar.HEALTH).read_text().splitlines()]
        self.assertEqual(recs[-1]["ignored_newline_paths"], 3)
        self.assertEqual(set(recs[-1]), {"kind", "at", "exit_code", "ignored_newline_paths"})


class MemoryCaps(unittest.TestCase):
    """glitch-06's ruling on P-2 (14 Oct 2026): the sidecar and the egress proxy each run under a 512 MiB memory cap,
    so the host reserve beside three takes is bounded. The watcher's full-tree measurement ran under 256 MiB
    (live-box-evidence-2026-10-13/measure-20261014), and the stub takes' peaks are recorded beside the cap."""
    CAP = 512 * 1024 * 1024

    def test_the_caps(self):
        self.assertEqual(rt.SIDECAR_MEMORY_BYTES, self.CAP)
        self.assertEqual(rt.PROXY_MEMORY_BYTES, self.CAP)

    def test_the_sidecar_is_created_under_its_cap(self):
        base = sidecar.create_argv(image="sha256:" + "1" * 64, run_tree="/srv/w/t", evidence="/srv/w/e",
                                   watch=["plan/approved.json"])
        launch = rt.SidecarLaunch(tuple(base), sidecar.start_argv, sidecar.ctl_argv, sidecar.rm_argv,
                                  sidecar.expect_from_argv(base))
        argv = rt.sidecar_create_argv(launch)
        self.assertEqual(argv, base[:2] + ["--memory", str(self.CAP)] + base[2:])
        for own in (["--memory", "1"], ["--memory=1"], ["-m", "1"], ["-m1"], ["--memory-swap", "1"]):   # R2-9: -m too
            bad = rt.SidecarLaunch(tuple(base[:2] + own + base[2:]), sidecar.start_argv, sidecar.ctl_argv,
                                 sidecar.rm_argv, launch.expect)
            with self.subTest(own=own), self.assertRaises(rt.Refused):
                rt.sidecar_create_argv(bad)
        # launch runs exactly that argv for the sidecar (the box's one launch road), on a fake runtime
        d = tempfile.mkdtemp()
        tree, ev, cfg, rec = (os.path.join(d, n) for n in ("t", "e", "c", "r"))
        for p in (tree, ev, cfg, rec):
            os.mkdir(p)
        base = sidecar.create_argv(image="sha256:" + "1" * 64, run_tree=tree, evidence=ev, watch=["plan/approved.json"])
        exp = dict(sidecar.expect_from_argv(base), cap_add=["CAP_DAC_READ_SEARCH"])
        launch = rt.SidecarLaunch(tuple(base), sidecar.start_argv, sidecar.ctl_argv, sidecar.rm_argv, exp)
        proxy = rt.ProxyLaunch(image="sha256:" + "5" * 64, conf_source="/srv/p.conf",
                               conf_target="/etc/squid/squid.conf", command=("squid", "-N"), user="13:13",
                               alias=rt.PROXY_ALIAS)
        spec = rt.TakeSpec(image="sha256:" + "2" * 64, run_tree=tree, config_dir=cfg, network="0" * 64,
                           memory_reservation=1 << 30, memory=3 << 30, cpus="2", pids_limit=64)

        class Fake:
            n = 0

            def run(self, argv, **kw):
                if argv[1:3] == ["network", "create"] or argv[1] == "create":
                    Fake.n += 1
                    return rt.Completed(0, f"{Fake.n:064x}\n", "")
                if argv[1:3] == ["container", "inspect"]:
                    return rt.Completed(0, json.dumps([{"Id": argv[3]}]), "")
                return rt.Completed(0, "", "")
        with mock.patch("box.preflight.inspect_mismatches", lambda *a, **k: []):
            launched = rt.launch(Fake(), spec, sidecar=launch, proxy=proxy, record_dir=rec)
        step = [x for x in launched.steps if x["step"] == "sidecar-create"][0]
        self.assertEqual(step["argv"], base[:2] + ["--memory", str(self.CAP)] + base[2:])
        import shutil
        shutil.rmtree(d)

    def test_the_proxy_is_created_under_its_cap(self):
        proxy = rt.ProxyLaunch(image="sha256:" + "5" * 64, conf_source="/srv/p.conf", conf_target="/etc/squid/squid.conf",
                               command=("squid", "-N"), user="13:13", alias=rt.PROXY_ALIAS)
        argv = rt.proxy_create_argv("a" * 64, proxy)
        i = argv.index("--memory")
        self.assertEqual(argv[i + 1], str(self.CAP))
        self.assertEqual(argv.count("--memory"), 1)
        self.assertLess(i, argv.index("sha256:" + "5" * 64))


if __name__ == "__main__":
    unittest.main()
