"""Regressions grounded in Athena's no-login Docker 29.8.1 probes, 13 Oct 2026.

No Docker or model is run by this module. Live evidence is retained separately.
"""
import signal
import sys
import json
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
                    mock.patch.object(rt, "refuse_env_files"):
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
        with mock.patch.object(rt, "read_login") as read:
            with self.assertRaisesRegex(rt.NotReady, "subscription binding not ready"):
                rt.exec_argv("a" * 64, ["codex", "exec", "prompt"], user=rt.AGENT_USER,
                             workdir="/srv/w/tree", harness=rt.CODEX, run_tree="/srv/w/tree",
                             login_file="/must-not-read", caller_env={})
            read.assert_not_called()

    def test_walk_login_and_scanner_refuse_before_open(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        try:
            import walk_builders
        finally:
            sys.path.pop(0)
        with mock.patch("os.open") as opened:
            for entry in (walk_builders.login_file_by_name, walk_builders.login_secrets):
                with self.subTest(entry=entry.__name__), self.assertRaisesRegex(
                        walk_builders.BuilderRefused, "subscription binding not ready"):
                    entry("/must-not-read", rt.CODEX)
            opened.assert_not_called()


class PublicConfigRegression(unittest.TestCase):
    def test_full_gemini_renderer_preserves_constraints_and_legacy_path(self):
        # Synthetic values exercise the renderer only; production pins stay PENDING.
        with mock.patch.object(take_config, "GEMINI_THINKING", {"path": "model.thinking", "value": "minimal"}), \
                mock.patch.object(take_config, "GEMINI_AUTH_SETTING", {"path": "security.auth.selectedType", "value": "gemini-api-key"}), \
                tempfile.TemporaryDirectory() as folder:
            record = take_config.public_record(rt.GEMINI, model="gemini-3.8-flash")
            take_config.write(folder, rt.GEMINI, model="gemini-3.8-flash")
            path = Path(folder) / ".gemini/settings.json"
            settings = json.loads(path.read_text())
            self.assertIs(settings["experimental"]["adk"]["agentSessionNoninteractiveEnabled"], False)
            self.assertEqual(settings["tools"]["exclude"], ["google_web_search", "web_fetch"])
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
        with mock.patch.object(take_config, "CODEX_REASONING_EFFORT", "medium"):
            record = take_config.public_record(rt.CODEX, model="gpt-5.4")
        config = tomllib.loads(record["files"][0]["text"])
        self.assertEqual(config["forced_login_method"], "chatgpt")
        self.assertEqual(config["cli_auth_credentials_store"], "file")
        self.assertEqual(config["web_search"], "disabled")
        self.assertIs(config["features"]["hooks"], False)
        self.assertIs(config["check_for_update_on_startup"], False)
        with self.assertRaises(rt.NotReady):
            take_config.public_record(rt.CODEX, model="gpt-5.4")
        with self.assertRaises(rt.NotReady):
            take_config.public_record(rt.GEMINI, model="gemini-3.8-flash")

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

if __name__ == "__main__":
    unittest.main()
