"""box/stub_take.py, CP2's real-box step as a measurement road (glitch-06's rulings, 14 Oct 2026).

Fakes only: no container, model, network, login or scanner runs here. The live run's evidence is retained under
lane-reports/stub-take-20261014/. What is bound:
  - the road refuses before any runtime call without full image ids, with ids its committed locks do not name, or
    with an output outside a stub-take-* folder or under a study record folder;
  - the production driver can never select it: no production module imports it, it never calls the harness exec,
    the turn or the login read, drive.adapter_class_problems is unchanged and still refuses any non-production
    adapter, and no harness of run_take's is a stub;
  - its records are labelled stub-take and the walk and batch readers refuse its folder;
  - its launch mirror is run_take.launch's steps, argv for argv, and run_take.launch itself is used once
    INSPECT_STATUS is filled.
"""
import argparse
import ast
import hashlib
import inspect
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from box import preflight, run_take as rt, sidecar, sidecar_contract  # noqa: E402
from box import stub_take as st  # noqa: E402
import drive  # noqa: E402
import mode_binding  # noqa: E402
import walk_register  # noqa: E402

BOX = str(STUDY / "box")
LOCK_IDS = {role: json.loads((STUDY / "box" / rel).read_text())["image_id"]
            for role, rel in (("take", "image.lock"), ("sidecar", "sidecar/image.lock"),
                              ("egress", "egress/image.lock"), ("codex", "codex/image.lock"),
                              ("gemini", "gemini/image.lock"))}
# drive.adapter_class_problems as it stands on the merged head (ruling 1: the stub road never changes it). The box
# branch pinned 6fb87b70...9d6a; the reviewed harness commit c35fc915 rewrote the function for three harnesses, and
# glitch-06 (14 Oct 2026) ruled the repin on the merged head to that version, byte for byte (the integration lane).
ADAPTER_CHECK_SHA256 = "47cdad3847800a32b04755f40ec11ba1f78678a6b45ba52bf0ab330559b62717"


def _ns(**over):
    d = {"box": BOX, "scratch_parent": "/nonexistent-parent", "output": "/tmp/stub-take-x/stub-take.json",
         "gitleaks": "/nonexistent", "gitleaks_sha256": "0" * 64, "memory_reservation": 1 << 30, "cpus": "1",
         "pids_limit": 64, "seed_tree": None}
    d.update({f"{r}_image": LOCK_IDS[r] for r in st.IMAGE_ROLES})
    d.update(over)
    return argparse.Namespace(**d)


class NoRuntime:
    def __init__(self):
        raise AssertionError("a runtime was built before the refusal")


class Refusals(unittest.TestCase):
    def test_every_role_needs_a_full_image_id(self):
        good = dict(LOCK_IDS)
        self.assertEqual(st.check_images(good), good)
        for role in st.IMAGE_ROLES:
            for bad in (None, "", "take-a:latest", good[role][:19], good[role][7:], good[role] + "0",
                        good[role].upper()):
                with self.subTest(role=role, bad=bad), self.assertRaises(st.StubTakeRefused):
                    st.check_images(dict(good, **{role: bad}))
        with self.assertRaises(st.StubTakeRefused):
            st.check_images({k: v for k, v in good.items() if k != "egress"})

    def test_a_short_id_refuses_before_any_runtime_call(self):
        for role in st.IMAGE_ROLES:
            with self.subTest(role=role), mock.patch.object(rt, "DockerRuntime", NoRuntime), \
                    mock.patch.object(st, "Recorder", NoRuntime):
                with self.assertRaises(st.StubTakeRefused):
                    st.run_stub_take(_ns(**{f"{role}_image": LOCK_IDS[role][:19]}))
                with self.assertRaises(st.StubTakeRefused):
                    st.main(["--box", BOX, "--scratch-parent", "/x", "--output", "/tmp/stub-take-x/o.json",
                             "--gitleaks", "/x", "--gitleaks-sha256", "0" * 64, "--memory-reservation", "1",
                             "--cpus", "1", "--pids-limit", "1",
                             *sum(([f"--{r}-image", LOCK_IDS[r][:19] if r == role else LOCK_IDS[r]]
                                   for r in st.IMAGE_ROLES), [])])

    def test_ids_the_locks_do_not_name_refuse(self):
        self.assertEqual({k: st.load_locks(BOX, dict(LOCK_IDS))[k]["image_id"] for k in st.IMAGE_ROLES}, LOCK_IDS)
        for role in st.IMAGE_ROLES:
            other = LOCK_IDS[role][:-1] + ("0" if LOCK_IDS[role][-1] != "0" else "1")
            with self.subTest(role=role), self.assertRaises(st.StubTakeRefused):
                st.load_locks(BOX, dict(LOCK_IDS, **{role: other}))
            with self.subTest(role=role, swapped=True), self.assertRaises(st.StubTakeRefused):
                swap = "sidecar" if role != "sidecar" else "egress"
                st.load_locks(BOX, dict(LOCK_IDS, **{role: LOCK_IDS[swap]}))

    def test_the_output_rule(self):
        with tempfile.TemporaryDirectory() as d:
            ok = os.path.join(d, "stub-take-20261014", "stub-take.json")
            self.assertEqual(st.check_output(ok), ok)
            for bad in ("relative/stub-take-x/o.json", os.path.join(d, "out", "o.json"),
                        os.path.join(d, "rehearsals", "stub-take-x", "o.json"),
                        os.path.join(d, "takes", "s1", "stub-take-x", "o.json"),
                        os.path.join(d, "stub-take-x", "..", "stub-take-y", "o.json")):
                with self.subTest(bad=bad), self.assertRaises(st.StubTakeRefused):
                    st.check_output(bad)
            os.makedirs(os.path.dirname(ok))
            Path(ok).write_text("{}")
            with self.assertRaises(st.StubTakeRefused):
                st.check_output(ok)

    def test_study_record_dirs_are_mode_bindings(self):
        self.assertEqual(set(st.STUDY_RECORD_DIRS), {mode_binding.WALKS_DIR, mode_binding.TAKES_DIR})

    def test_the_scan_uses_the_production_scanner(self):
        src = Path(st.__file__).read_text(encoding="utf-8")
        self.assertNotIn("def gitleaks_rules_scanner", src)
        tree = ast.parse(src)
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                and isinstance(n.value, ast.Name) and n.value.id == "rules_scanner"}
        self.assertEqual(used, {"gitleaks_scanner", "GITLEAKS_SHA256"})


def _imports(tree) -> set:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(n.module or "")
            out |= {f"{n.module}.{a.name}" for a in n.names}
    return out


class NeverSelected(unittest.TestCase):
    def test_no_production_module_imports_the_road(self):
        hits = []
        for p in sorted(STUDY.rglob("*.py")):
            rel = p.relative_to(STUDY).as_posix()
            if rel.startswith("tests/") or rel == "box/stub_take.py":
                continue
            src = p.read_text(encoding="utf-8")
            names = _imports(ast.parse(src))
            # an import of the road in any spelling, or the module named as a string (importlib, __import__)
            if [n for n in names if n.split(".")[-1] == "stub_take"] or "box.stub_take" in src \
                    or "box/stub_take" in src or '"stub_take"' in src or "'stub_take'" in src:
                hits.append(rel)
        self.assertEqual(hits, [])

    def test_the_road_never_execs_a_harness_or_reads_a_login(self):
        tree = ast.parse(Path(st.__file__).read_text(encoding="utf-8"))
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                and isinstance(n.value, ast.Name) and n.value.id == "run_take"}
        for name in ("exec_argv", "run_turn", "read_login", "LOGIN_VARIABLE", "launcher_argv", "take_environment",
                     "exec_values", "remove_config_dir"):
            self.assertNotIn(name, used)
        self.assertIn("agent_exec_argv", used)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(names & {"exec_argv", "run_turn", "read_login"})

    def test_the_road_uses_the_ownership_road(self):
        tree = ast.parse(Path(st.__file__).read_text(encoding="utf-8"))
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                and isinstance(n.value, ast.Name) and n.value.id == "ownership"}
        self.assertEqual(used, {"grant", "restore", "OwnershipError"})

    def test_turns_go_through_the_plain_agent_exec(self):
        calls = []

        class R:
            def run(self, argv, **kw):
                calls.append(argv)
                return rt.Completed(0, "", "")
        out = st._turn(R(), {}, "a" * 64, "/srv/tree", "reads-planted", st.TURNS[1][1], st.TURNS[1][2])
        self.assertEqual(calls[0], rt.agent_exec_argv("a" * 64, ["/usr/bin/python3", "-I", "-S", "-c", st.TURNS[1][1],
                                                                 "/srv/tree/plan/approved.json"], workdir="/srv/tree"))
        self.assertEqual(calls[0][:4], ["docker", "exec", "--user", rt.AGENT_USER])
        self.assertFalse([a for a in calls[0] if a == "-e"])
        self.assertEqual(out["argv_seam"], "run_take.agent_exec_argv")
        self.assertEqual([t[0] for t in st.TURNS], ["reads-nothing", "reads-planted", "background-writer"])
        self.assertEqual(st.TURNS[0][1], "pass")
        for _n, script, _a in st.TURNS:
            compile(script, "<turn>", "exec")

    def test_the_production_driver_still_refuses_a_stub_adapter(self):
        src = inspect.getsource(drive.adapter_class_problems)
        self.assertEqual(hashlib.sha256(src.encode()).hexdigest(), ADAPTER_CHECK_SHA256)
        from box.stub_agents import agents
        for cls in agents.STUBS.values():
            with self.subTest(stub=cls.stub), self.assertRaises(drive.AdapterIdentityRefused):
                drive.adapter_class_problems(object.__new__(cls))

    def test_no_harness_is_a_stub(self):
        for name in ("stub", st.RECORD_KIND, "stub-take", None):
            with self.subTest(name=name), self.assertRaises(rt.Refused):
                rt._known_harness(name)
        self.assertEqual(st.HARNESS, rt.CLAUDE_CODE)


class Labelled(unittest.TestCase):
    def test_every_record_is_labelled(self):
        self.assertEqual(st._labelled({"a": 1})["record_kind"], "stub-take-measurement")
        self.assertIn("never a study take", st._labelled({})["not_a_study_record"])
        for k in ("record_kind", "not_a_study_record"):
            with self.subTest(k=k), self.assertRaises(st.StubTakeRefused):
                st._labelled({k: "take"})
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "stub-take-t", "stub-take.json")
            os.makedirs(os.path.dirname(out))
            argv = ["--box", BOX, "--scratch-parent", d, "--output", out, "--gitleaks", "/x", "--gitleaks-sha256",
                    "0" * 64, "--memory-reservation", "1", "--cpus", "1", "--pids-limit", "1",
                    *sum(([f"--{r}-image", LOCK_IDS[r]] for r in st.IMAGE_ROLES), [])]
            with mock.patch.object(st, "run_stub_take", lambda a: {"x": 1}), \
                    mock.patch("sys.stdout"):
                st.main(argv)
            doc = json.loads(Path(out).read_text())
            self.assertEqual(doc["record_kind"], st.RECORD_KIND)

    def test_the_walk_reader_refuses_the_folder(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "stub-take-20261014"
            folder.mkdir()
            (folder / "stub-take.json").write_text(json.dumps(st._labelled({})))
            with self.assertRaises(drive.DriveRefused):
                drive.walk_files(folder)
            (folder / "launch.json").write_text("{}")
            (folder / "proxy.log").write_text("")
            with self.assertRaises(drive.DriveRefused):
                drive.walk_files(folder)
            self.assertEqual(walk_register.registered(Path(d)), [])

    def test_batch_never_takes_its_folder_as_an_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            take = mock.Mock(folder=os.path.join(d, "stub-take-20261014"))
            with self.assertRaises(drive.DriveRefused):
                drive.take_k_problems(d, {"slot": "s1"}, 1, take)


class FakeRuntime:
    def __init__(self):
        self.calls, self.n = [], 0

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append(list(argv))
        if argv[1:3] == ["network", "create"] or argv[1] == "create":
            self.n += 1
            return rt.Completed(0, f"{self.n:064x}\n", "")
        if argv[1:3] == ["container", "inspect"]:
            return rt.Completed(0, json.dumps([{"Id": argv[3], "State": {"Running": False}}]), "")
        return rt.Completed(0, "", "")


class MirrorIsLaunch(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.tree, self.ev, self.cfg = (os.path.join(self.d, n) for n in ("tree", "ev", "cfg"))
        for p in (self.tree, self.ev, self.cfg):
            os.mkdir(p)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def parts(self):
        sl = st.sidecar_launch(image=LOCK_IDS["sidecar"], run_tree=self.tree, evidence=self.ev)
        proxy = rt.ProxyLaunch(image=LOCK_IDS["egress"], conf_source="/srv/p.conf", conf_target="/etc/squid/squid.conf",
                               command=("squid", "-N"), user="13:13", alias=rt.PROXY_ALIAS)
        spec = rt.TakeSpec(image=LOCK_IDS["take"], run_tree=self.tree, config_dir=self.cfg, network="0" * 64,
                           memory_reservation=1 << 30, memory=3 << 30, cpus="2", pids_limit=512)
        return sl, proxy, spec

    def records(self, n):
        r = os.path.join(self.d, f"r{n}")
        os.mkdir(r)
        return r

    def test_the_mirror_runs_launchs_steps_argv_for_argv(self):
        sl, proxy, spec = self.parts()
        with mock.patch.object(rt, "network_name", lambda: "nfixed"), \
                mock.patch.object(rt, "INSPECT_STATUS", "confirmed-in-test"), \
                mock.patch.object(preflight, "inspect_mismatches", lambda *a, **k: []):
            a = rt.launch(FakeRuntime(), spec, sidecar=sl, proxy=proxy, record_dir=self.records(1))
        self.assertTrue(st.use_launch())        # INSPECT_STATUS is filled (14 Oct 2026): the road uses launch itself
        with mock.patch.object(rt, "network_name", lambda: "nfixed"), \
                mock.patch.object(rt, "INSPECT_STATUS", rt.PENDING):
            b = st.launch_mirror(FakeRuntime(), spec, sidecar=sl, proxy=proxy, record_dir=self.records(2))
            self.assertFalse(st.use_launch())
        steps = lambda x: [(s["step"], s["argv"]) for s in x.steps]  # noqa: E731
        self.assertEqual(steps(a), steps(b))
        self.assertEqual([s[0] for s in steps(b)], list(st.LAUNCH_STEPS))
        self.assertEqual(a.to_record()["take_id"], b.to_record()["take_id"])
        self.assertEqual(b.spec, a.spec)
        self.assertTrue(b.ok)
        self.assertEqual(json.loads(Path(self.d, "r2", rt.LAUNCH_RECORD).read_text())["ok"], True)

    def test_launch_itself_refuses_while_inspect_status_is_pending(self):
        sl, proxy, spec = self.parts()
        self.assertFalse(rt._is_pending(rt.INSPECT_STATUS))
        with mock.patch.object(rt, "INSPECT_STATUS", rt.PENDING), self.assertRaises(rt.NotReady):
            rt.launch(FakeRuntime(), spec, sidecar=sl, proxy=proxy, record_dir=self.records(3))
        with mock.patch.object(preflight, "inspect_mismatches", side_effect=AssertionError("compared")):
            st.launch_mirror(FakeRuntime(), spec, sidecar=sl, proxy=proxy, record_dir=self.records(4))

    def test_the_mirror_tears_down_a_failed_launch_by_id(self):
        sl, proxy, spec = self.parts()

        class Failing(FakeRuntime):
            def run(self, argv, **kw):
                if argv[1:2] == ["start"] and len(self.calls) > 8:
                    self.calls.append(list(argv))
                    return rt.Completed(1, "", "boom")
                return super().run(argv, **kw)
        f = Failing()
        with self.assertRaises(rt.LaunchError) as cm:
            st.launch_mirror(f, spec, sidecar=sl, proxy=proxy, record_dir=self.records(5))
        removed = [c for c in f.calls if c[1] in ("rm",) or c[1:3] == ["network", "rm"]]
        self.assertEqual(len(removed), 4)
        self.assertFalse(cm.exception.launched.ok)

    def test_the_sidecar_expectation_departure_is_the_contracts_spelling_only(self):
        sl = st.sidecar_launch(image=LOCK_IDS["sidecar"], run_tree=self.tree, evidence=self.ev)
        base = sidecar.expect_from_argv(list(sl.create_argv))
        self.assertTrue(rt._is_pending(base["cap_add"]))
        self.assertEqual({k: v for k, v in sl.expect.items() if k != "cap_add"},
                         {k: v for k, v in base.items() if k != "cap_add"})
        self.assertEqual(sl.expect["cap_add"], list(sidecar_contract.BOOT_INSPECT_CAPABILITIES))
        self.assertEqual(len(sl.expect["cap_add"]), len(base["cap_add"]))


if __name__ == "__main__":
    unittest.main()
