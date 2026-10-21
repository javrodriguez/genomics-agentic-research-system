"""box/stub_model_probe.py and its walk_launch entries (lane vendor-b27, glitch-f1's rulings 1 and 4, 21 Oct 2026).

Fakes only: no container, CLI, network, login or athena runs here. What is bound (the B27 design's test plan):
  - exactly three environment changes from the arm G row (GOOGLE_GEMINI_BASE_URL the stub on 127.0.0.1, the fixed
    dummy key, no HTTPS_PROXY); any other difference, a proxy, a non-dummy key or another host refuses;
  - the exec is exec_argv's form, its launcher pairs differing from exec_argv's by exactly those changes;
  - run_take still refuses GOOGLE_GEMINI_BASE_URL for every arm (the production take road stays closed);
  - the container: create_argv with the locked take-g image by id and `--pull=never`, on a network made with
    `--internal`; no proxy, no sidecar, no network connect; teardown by recorded id leaves nothing (run_take.leaked);
  - settings from take_config.write with their sha256 recorded; argv from gemini_adapter.argv with `-r` only after
    process 1; each snapshot retained after its process and before the next exec; a held stub stops the scenario;
  - the A1-fake cross-check appends --fake-responses to the study argv check_model read;
  - the road never calls run_take.exec_argv, run_turn or read_login, and no production module imports it;
  - records labelled, the output folder outside the record roots and never over a path, the dry run runs nothing;
  - walk_launch: run_command byte-unchanged by the factoring (sha256 pinned from the base 04c4e774), the probe's
    command under its own hold, fetch-probe's tar, sha256, unpacking, manifest and scan refusals.
"""
import ast
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from box import ownership, run_take as rt, stub_model_probe as smp, stub_model_server as sms  # noqa: E402
from box import walk_launch as wl  # noqa: E402
import gemini_adapter  # noqa: E402

BOX = str(STUDY / "box")
GEMINI_IMAGE = json.loads((STUDY / "box" / "gemini" / "image.lock").read_text())["image_id"]
RESOURCES = {"memory_reservation": 2 * 1024 ** 3, "memory": 6 * 1024 ** 3, "cpus": "8", "pids_limit": 4096}
TREE = "/scratch/sp-x/t"
ID = "a" * 64
# walk_launch.run_command's output for this input at the base 04c4e774 (computed there, 21 Oct 2026 15:31 EDT)
RUN_COMMAND_SHA256 = "7eb86a1eaec3846a5469b4f75995d461728323d004f8fe0e6eb601ba9af881b8"
CHILD = "/home/javier/w-AbCdEf12"


def pairs(argv) -> dict:
    """The launcher's NAME=VALUE pairs of an exec argv."""
    i = argv.index(rt.LAUNCHER[-1])
    n = int(argv[i + 2])
    return dict(p.split("=", 1) for p in argv[i + 3:i + 3 + n])


class Environment(unittest.TestCase):
    def test_exactly_the_three_changes(self):
        env = smp.probe_environment(TREE, 41234)
        row = rt.take_environment(rt.GEMINI, TREE)
        self.assertEqual(sorted(set(env) - set(row)), ["GOOGLE_GEMINI_BASE_URL"])
        self.assertEqual(sorted(set(row) - set(env)), ["HTTPS_PROXY"])
        self.assertEqual(sorted(k for k in set(env) & set(row) if env[k] != row[k]), ["GEMINI_API_KEY"])
        self.assertEqual(env["GOOGLE_GEMINI_BASE_URL"], "http://127.0.0.1:41234")
        self.assertEqual(env["GEMINI_API_KEY"], smp.DUMMY_KEY)

    def test_any_other_difference_refuses(self):
        good = smp.probe_environment(TREE, 41234)
        bad = [dict(good, HTTPS_PROXY=rt.PROXY_URL), dict(good, GEMINI_API_KEY_FILE="/home/javier/key"),
               dict(good, GEMINI_API_KEY="AIza" + "x" * 35), dict(good, GOOGLE_GEMINI_BASE_URL="http://10.0.0.2:80"),
               dict(good, GOOGLE_GEMINI_BASE_URL="https://generativelanguage.googleapis.com"),
               {k: v for k, v in good.items() if k != "GOOGLE_GEMINI_BASE_URL"},
               dict(good, LANG="en_US.UTF-8")]
        for env in bad:
            with self.subTest(env=sorted(set(env) ^ set(good))), self.assertRaises(smp.ProbeRefused):
                smp.environment_changes(env, TREE)

    def test_the_dummy_key_is_a_fixed_low_entropy_string(self):
        self.assertEqual(set(smp.DUMMY_KEY), set("dumy"))


class ExecForm(unittest.TestCase):
    def test_the_probe_exec_is_exec_argv_s_form_with_the_three_changes(self):
        inner = gemini_adapter.argv("Read a.", model="gemini-3.8-flash", mode="yolo", session_id=None, first=True)
        with tempfile.TemporaryDirectory() as d:
            folder = os.path.join(d, "login")
            os.mkdir(folder, 0o700)
            login = os.path.join(folder, "key")
            Path(login).write_text("GEMINI_API_KEY=" + "y" * 24 + "\n")
            os.chmod(login, 0o600)
            with mock.patch.object(rt, "_own_environment", lambda: {}):
                prod, prod_env = rt.exec_argv(ID, inner, user=rt.AGENT_USER, workdir=TREE, harness=rt.GEMINI,
                                              run_tree=TREE, login_file=login, caller_env={})
        mine, mine_env = smp.process_argv(ID, inner, run_tree=TREE, port=41234, caller_env={})
        head = prod.index(rt.LAUNCHER[0])
        self.assertEqual(mine[:head], prod[:head])
        self.assertEqual(mine[-len(inner):], prod[-len(inner):])
        want = {k: v for k, v in pairs(prod).items() if k != "HTTPS_PROXY"}
        want["GOOGLE_GEMINI_BASE_URL"] = "http://127.0.0.1:41234"
        self.assertEqual(pairs(mine), want)
        self.assertEqual(set(mine_env), set(prod_env))
        self.assertEqual(mine_env["GEMINI_API_KEY"], smp.DUMMY_KEY)
        self.assertNotIn(smp.DUMMY_KEY, " ".join(mine))

    def test_resume_only_after_process_one_and_the_fake_flag_after_the_study_argv(self):
        doc = smp.load_scenario("A1")
        self.assertNotIn("-r", smp.cli_inner(doc, 1, None))
        self.assertEqual(smp.cli_inner(doc, 2, "sess0001-aaaa")[-2:], ["-r", "sess0001-aaaa"])
        fake = smp.cli_inner(smp.load_scenario("A1-fake"), 2, "sess0001-aaaa", fake_file="/t/f.jsonl")
        self.assertEqual(fake[-4:], ["-r", "sess0001-aaaa", "--fake-responses", "/t/f.jsonl"])
        with self.assertRaises(rt.Refused):     # check_model refuses the flag: it reads the study argv only
            rt.check_model(rt.GEMINI, fake)


class ProductionRoadStaysClosed(unittest.TestCase):
    def test_run_take_still_refuses_the_base_url_for_every_arm(self):
        self.assertIn("GOOGLE_GEMINI_BASE_URL", rt.GEMINI_PACKAGE_SWEEP_REFUSED)
        for harness in (rt.GEMINI, rt.CLAUDE_CODE):
            with self.subTest(harness=harness), self.assertRaises(rt.Refused):
                rt.check_environment(harness, {}, {"GOOGLE_GEMINI_BASE_URL"})
        with self.assertRaises(rt.Refused), mock.patch.object(rt, "_own_environment", lambda: {}):
            rt.exec_argv(ID, ["gemini", "-p", "x", "-m", "gemini-3.8-flash"], user=rt.AGENT_USER, workdir=TREE,
                         harness=rt.GEMINI, run_tree=TREE, login_file="/nonexistent/key",
                         caller_env={"GOOGLE_GEMINI_BASE_URL": "http://127.0.0.1:1"})


def _attrs(tree, base):
    return {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == base}


def _imports(tree) -> set:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(n.module or "")
            out |= {f"{n.module}.{a.name}" for a in n.names}
    return out


class Bindings(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(Path(smp.__file__).read_text(encoding="utf-8"))

    def test_never_the_harness_exec_the_turn_or_the_login(self):
        used = _attrs(self.tree, "run_take")
        for name in ("exec_argv", "run_turn", "read_login", "check_login_place", "launch", "teardown",
                     "proxy_create_argv", "sidecar_create_argv"):
            self.assertNotIn(name, used)
        names = {n.id for n in ast.walk(self.tree) if isinstance(n, ast.Name)}
        self.assertFalse(names & {"exec_argv", "run_turn", "read_login"})

    def test_the_walks_own_code_is_used(self):
        self.assertTrue({"create_argv", "take_environment", "launcher_argv", "check_model", "agent_exec_argv",
                         "make_config_dir", "_teardown_partial", "leaked", "network_name"} <= _attrs(self.tree, "run_take"))
        self.assertIn("write", _attrs(self.tree, "take_config"))
        self.assertIn("argv", _attrs(self.tree, "gemini_adapter"))
        self.assertTrue({"gemini_session_rel", "retain_bytes"} <= _attrs(self.tree, "native_snapshot"))
        self.assertTrue({"grant", "restore", "operator_list", "operator_read"} <= _attrs(self.tree, "ownership"))

    def test_no_production_module_imports_the_probe(self):
        hits = []
        for p in sorted(STUDY.rglob("*.py")):
            rel = p.relative_to(STUDY).as_posix()
            if rel.startswith("tests/") or rel == "box/stub_model_probe.py":
                continue
            src = p.read_text(encoding="utf-8")
            names = _imports(ast.parse(src))
            if [n for n in names if n.split(".")[-1] == "stub_model_probe"] or "box.stub_model_probe" in src \
                    or '"stub_model_probe"' in src or "'stub_model_probe'" in src:
                hits.append(rel)
        self.assertEqual(hits, [])
        # walk_launch names it only as the remote command's path
        src = (STUDY / "box" / "walk_launch.py").read_text(encoding="utf-8")
        self.assertEqual([ln.strip() for ln in src.splitlines() if "stub_model_probe.py\"" in ln],
                         ['PROBE_MODULE = "evals/gap-study-4/box/stub_model_probe.py"'])

    def test_the_resources_are_the_walks(self):
        import walk_builders
        self.assertEqual(smp.take_resources(), walk_builders.TAKE_RESOURCES)


class Refusals(unittest.TestCase):
    def test_the_output_rule(self):
        for bad in ("relative/stub-probe-x", "/a/b/../stub-probe-x", "/a/probe-x", f"/a/{smp.STUDY_RECORD_DIRS[0]}/stub-probe-x"):
            with self.subTest(path=bad), self.assertRaises(smp.ProbeRefused):
                smp.check_output(bad)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(smp.check_output(os.path.join(d, "stub-probe-x")), os.path.join(d, "stub-probe-x"))
            os.mkdir(os.path.join(d, "stub-probe-x"))
            with self.assertRaises(smp.ProbeRefused):
                smp.check_output(os.path.join(d, "stub-probe-x"))

    def test_the_image_is_the_lock_s_by_full_id(self):
        smp.check_image(BOX, GEMINI_IMAGE)
        for bad in ("gemini:latest", GEMINI_IMAGE[:20], "sha256:" + "0" * 64):
            with self.subTest(image=bad), self.assertRaises(smp.ProbeRefused):
                smp.check_image(BOX, bad)

    def test_scenario_names(self):
        self.assertEqual(smp.scenario_names("all"), list(smp.ALL))
        self.assertEqual(smp.scenario_names("A1,C2"), ["A1", "C2"])
        for bad in ("", "A1,A1", "A9", "a1"):
            with self.subTest(spec=bad), self.assertRaises(smp.ProbeRefused):
                smp.scenario_names(bad)

    def test_labels(self):
        self.assertEqual(smp.labelled({"a": 1})["record_kind"], "stub-model-probe")
        self.assertIn("never a study take", smp.labelled({})["not_a_study_record"])
        with self.assertRaises(smp.ProbeRefused):
            smp.labelled({"record_kind": "walk"})

    def test_the_real_run_refuses_off_linux(self):
        with mock.patch.object(smp.sys, "platform", "darwin"), self.assertRaises(smp.ProbeRefused):
            smp.run_probe(mock.Mock(scratch_parent="/x", output="/y/stub-probe-z"), ["A1"])


class DryRun(unittest.TestCase):
    def test_the_dry_run_prints_every_argv_and_runs_nothing(self):
        buf = io.StringIO()
        with mock.patch.object(rt, "DockerRuntime", side_effect=AssertionError("a runtime was built")), \
                mock.patch.object(smp, "take_resources", lambda: dict(RESOURCES)), redirect_stdout(buf):
            smp.main(["--box", BOX, "--scratch-parent", "/nonexistent", "--output", "/nonexistent/stub-probe-d",
                      "--gemini-image", GEMINI_IMAGE, "--scenarios", "A1,A1-fake", "--dry-run"])
        rows = [json.loads(x) for x in buf.getvalue().splitlines()]
        steps = [(r["scenario"], r["step"]) for r in rows]
        self.assertEqual([s for n, s in steps if n == "A1"],
                         ["grant-run_tree", "grant-config_dir", "grant-evidence_dir", "network-create", "take-create",
                          "take-inspect", "take-start", "stub-start", "cli-version", "process-1", "process-2",
                          "process-3", "take-rm", "network-rm", "client-environment"])
        by = {(r["scenario"], r["step"]): r for r in rows}
        self.assertIn("--internal", by[("A1", "network-create")]["argv"])
        create = by[("A1", "take-create")]["argv"]
        self.assertEqual(create[:3], ["docker", "create", "--pull=never"])
        self.assertIn(GEMINI_IMAGE, create)
        self.assertFalse([r for r in rows if "argv" in r and ("proxy" in " ".join(r["argv"]).lower()
                                                               or "connect" in r["argv"])])
        self.assertIn("--fake-responses", by[("A1-fake", "process-3")]["argv"])
        self.assertNotIn("--fake-responses", by[("A1", "process-3")]["argv"])
        self.assertEqual(by[("A1", "client-environment")]["changes"],
                         {"added": ["GOOGLE_GEMINI_BASE_URL"], "removed": ["HTTPS_PROXY"], "replaced": ["GEMINI_API_KEY"]})


# --------------------------------------------------------------------------------------------- the fake box
SESSION = "sess0001-aaaa"


class FakeBox:
    """A fake Docker client for one scenario: ids for creates, the operator programs answered from the host folders,
    the stub's start, and a CLI that appends to its session file and writes the stub's state. It checks the design's
    order: snapshot n is retained before exec n+1."""

    def __init__(self, out_root, name, *, held_after=None, fail_exit=None):
        self.calls, self.n, self.out_root, self.name = [], 0, out_root, name
        self.cfg = self.tree = None
        self.process = 0
        self.held_after, self.fail_exit = held_after, fail_exit
        self.order_problems = []

    def _id(self):
        self.n += 1
        return f"{self.n:064x}"

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append((list(argv), dict(env or {})))
        a = list(argv)
        if a[:2] == ["docker", "run"]:
            cid = self._id()
            Path(a[a.index("--cidfile") + 1]).write_text(cid)
            mount = a[a.index("--mount") + 1]
            src = mount.split("source=", 1)[1].split(",", 1)[0]
            if ownership.READ_PROGRAM in a:
                rel = a[a.index(ownership.READ_PROGRAM) + 1]
                p = os.path.join(src, rel)
                if not os.path.exists(p):
                    return rt.Completed(0, json.dumps({"exists": False}), "")
                data = Path(p).read_bytes()
                import base64
                return rt.Completed(0, json.dumps({"exists": True, "b64": base64.b64encode(data).decode(),
                                                   "sha256": hashlib.sha256(data).hexdigest(),
                                                   "bytes": len(data)}), "")
            if ownership.LIST_PROGRAM in a:
                import base64
                rel = a[a.index(ownership.LIST_PROGRAM) + 1]
                p = src if rel == "." else os.path.join(src, rel)
                if not os.path.isdir(p):
                    return rt.Completed(0, json.dumps({"exists": False}), "")
                ents = sorted([base64.b64encode(n.encode()).decode(), "dir" if os.path.isdir(os.path.join(p, n))
                               else "file"] for n in os.listdir(p))
                canon = json.dumps(ents, separators=(",", ":"))
                return rt.Completed(0, json.dumps({"exists": True, "entries": ents,
                                                   "sha256": hashlib.sha256(canon.encode()).hexdigest()}), "")
            return rt.Completed(0, "", "")
        if a[1:3] == ["network", "create"]:
            return rt.Completed(0, self._id() + "\n", "")
        if a[1] == "create":
            self.cfg = [m for m in a if m.endswith(f"target={rt.CONFIG_MOUNT}")][0].split("source=")[1].split(",")[0]
            self.tree = a[a.index("--workdir") + 1]
            return rt.Completed(0, self._id() + "\n", "")
        if a[1:3] == ["container", "inspect"]:
            return rt.Completed(0, json.dumps([{"Id": a[3]}]), "")
        if a[1] == "exec":
            joined = " ".join(a)
            if smp.STUB_FILE in joined:
                return rt.Completed(0, json.dumps({"ready": True, "port": 41234, "pid": 77}) + "\n", "")
            if a[-1] == "--version":
                return rt.Completed(0, "0.64.0\n", "")
            self.process += 1
            k = self.process
            if k > 1 and not os.path.exists(os.path.join(self.out_root, self.name, "session",
                                                         f"native-turn-{k - 1}.jsonl")):
                self.order_problems.append(f"process {k} ran before snapshot {k - 1} was retained")
            chats = Path(self.cfg, ".gemini", "tmp", "proj1", "chats")
            chats.mkdir(parents=True, exist_ok=True)
            with open(chats / f"session-2026-10-21T15-00-{SESSION[:8]}.jsonl", "a") as fh:
                if k == 1:
                    fh.write(json.dumps({"sessionId": SESSION, "projectHash": "p"}) + "\n")
                fh.write(json.dumps({"id": f"m{k}", "type": "user", "content": [{"text": "x"}]}) + "\n")
            held = f"request {k}: synthetic" if self.held_after == k else None
            Path(self.tree, smp.STUB_OUT, "state.json").write_text(json.dumps({"held": held, "done": False}))
            out = json.dumps({"type": "init", "session_id": SESSION, "model": "gemini-3.8-flash"}) + "\n" if k == 1 \
                else json.dumps({"type": "message"}) + "\n"
            return rt.Completed(self.fail_exit if self.fail_exit and k == 2 else 0, out, "")
        if a[1:3] == ["ps", "--all"]:
            return rt.Completed(0, "", "")
        return rt.Completed(0, "", "")


def run_fake(name, **kw):
    d = tempfile.mkdtemp(prefix="b27-")
    parent = os.path.join(d, "parent")
    out = os.path.join(d, "stub-probe-t")
    os.mkdir(parent, 0o700)
    os.mkdir(out)
    box = FakeBox(out, name, **kw)
    rec = smp.run_scenario(box, {"PATH": "/usr/bin"}, name, image=GEMINI_IMAGE, scratch_parent=parent, out_root=out,
                           resources=dict(RESOURCES))
    return d, out, box, rec


class FullRunOnFakes(unittest.TestCase):
    def setUp(self):
        self.d, self.out, self.box, self.rec = run_fake("A1")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_no_failure_and_every_process_ran_in_order(self):
        self.assertNotIn("failure", self.rec, self.rec.get("failure"))
        self.assertEqual([p["process"] for p in self.rec["processes"]], [1, 2, 3])
        self.assertEqual(self.box.order_problems, [])

    def test_the_container_argv(self):
        argvs = [a for a, _e in self.box.calls]
        net = [a for a in argvs if a[1:3] == ["network", "create"]]
        self.assertEqual(len(net), 1)
        self.assertEqual(net[0][3], "--internal")
        create = [a for a in argvs if a[1] == "create"][0]
        spec = smp.take_spec(GEMINI_IMAGE, self.rec["scratch"]["run_tree"], self.rec["scratch"]["config"],
                             f"{1 + 3:064x}", RESOURCES)
        self.assertEqual(create[:3], ["docker", "create", "--pull=never"])
        self.assertEqual(create[create.index("--network") + 1], self.rec["launch"]["network_id"])
        self.assertEqual(create, rt.create_argv(rt.dataclasses.replace(spec, network=self.rec["launch"]["network_id"])))
        self.assertFalse([a for a in argvs if a[1:3] == ["network", "connect"] or "proxy" in " ".join(a)])

    def test_every_cli_exec_carries_the_three_changes(self):
        cli = [(a, e) for a, e in self.box.calls if a[1] == "exec" and "gemini" in a and smp.STUB_FILE not in " ".join(a)]
        self.assertEqual(len(cli), 4)                        # the version, then three processes
        for a, e in cli:
            p = pairs(a)
            self.assertEqual(p["GOOGLE_GEMINI_BASE_URL"], "http://127.0.0.1:41234")
            self.assertNotIn("HTTPS_PROXY", p)
            self.assertEqual(e["GEMINI_API_KEY"], smp.DUMMY_KEY)
        procs = [a for a, _e in cli if "-p" in a]
        self.assertEqual(["-r" in a for a in procs], [False, True, True])

    def test_the_settings_are_the_study_s(self):
        from box import take_config
        files = take_config.files_for(rt.GEMINI, model="gemini-3.8-flash")
        self.assertEqual(self.rec["config"]["files"], sorted(files))
        self.assertRegex(self.rec["config"]["sha256"], r"^[0-9a-f]{64}$")

    def test_the_records_and_the_teardown(self):
        names = sorted(os.listdir(os.path.join(self.out, "A1")))
        for want in ("ledger.json", "probe.json", "scenario.json", "session", "stub", "turn-1.jsonl", "turn-3.jsonl"):
            self.assertIn(want, names)
        self.assertEqual(sorted(os.listdir(os.path.join(self.out, "A1", "session"))),
                         ["native-turn-1.jsonl", "native-turn-2.jsonl", "native-turn-3.jsonl"])
        doc = json.loads(Path(self.out, "A1", "probe.json").read_text())
        self.assertEqual(doc["record_kind"], "stub-model-probe")
        self.assertEqual(json.loads(Path(self.out, "A1", "ledger.json").read_text())["turns"][1]["sent"],
                         "Summarise what you read.")
        teardown = [a for a, _e in self.box.calls if a[1] == "rm" or a[1:3] == ["network", "rm"]]
        self.assertEqual([a[1] for a in teardown], ["rm", "network"])
        self.assertEqual(self.rec["leaked_after_teardown"], [])
        self.assertTrue(self.rec["scratch_removed"])
        self.assertIn("${RUN_TREE}", (STUDY / "box" / "stub_model_scenarios" / "A1.json").read_text())
        self.assertNotIn("${RUN_TREE}", Path(self.out, "A1", "scenario.json").read_text())


class StopsAndCrossCheck(unittest.TestCase):
    def test_a_held_stub_stops_the_scenario(self):
        d, out, box, rec = run_fake("A1", held_after=1)
        try:
            self.assertEqual([p["process"] for p in rec["processes"]], [1])
            self.assertEqual(rec["stopped_after"]["process"], 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_failed_process_stops_the_scenario(self):
        d, out, box, rec = run_fake("A1", fail_exit=1)
        try:
            self.assertEqual([p["process"] for p in rec["processes"]], [1, 2])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_fake_cross_check(self):
        d, out, box, rec = run_fake("A1-fake")
        try:
            procs = [a for a, _e in box.calls if a[1] == "exec" and "-p" in a]
            self.assertTrue(all(a[-2] == "--fake-responses" for a in procs))
            got = [json.loads(x) for x in Path(out, "A1-fake", "fake-responses.jsonl").read_text().splitlines()]
            want = sms.fake_records(smp.materialise(smp.load_scenario("A1"), rec["scratch"]["run_tree"]))
            self.assertEqual(got, want)
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ------------------------------------------------------------------------------------------- walk_launch
_tw = importlib.util.spec_from_file_location("b27_test_walk_launch", STUDY / "tests" / "test_walk_launch.py")
twl = importlib.util.module_from_spec(_tw)
_tw.loader.exec_module(twl)


class WalkLaunchProbe(unittest.TestCase):
    def test_run_command_is_byte_unchanged_by_the_factoring(self):
        cmd = wl.run_command(child=CHILD, walk="w-test1", cell={"task": "t", "half": "h", "wording": "w", "arm": "G",
                                                                "model": "gemini-3.8-flash"}, reason="a reason")
        self.assertEqual(hashlib.sha256(cmd.encode()).hexdigest(), RUN_COMMAND_SHA256)

    def test_the_probe_starts_under_its_own_hold(self):
        cmd = wl.probe_command(child=CHILD, probe="smoke1", scenarios="A1", image=GEMINI_IMAGE, reason="smoke run")
        self.assertIn("athena-reserve hold --by gap4-probe-smoke1 -- ", cmd)
        self.assertIn(f"{CHILD}/repo/evals/gap-study-4/box/stub_model_probe.py", cmd)
        self.assertIn(f"--output {CHILD}/stub-probe-smoke1", cmd)
        self.assertIn(f"--scratch-parent {wl.CONFIG_PARENT}", cmd)
        self.assertIn("machine_gate.py athena-check", cmd)
        self.assertIn("os.O_EXCL", cmd)
        self.assertNotIn("GIT_AUTHOR_NAME", cmd)
        self.assertIn(f"echo $? > {CHILD}/walk.exit", cmd)

    def test_the_probe_command_refuses_off_its_shape(self):
        ok = dict(child=CHILD, probe="smoke1", scenarios="A1", image=GEMINI_IMAGE, reason="r")
        for k, v in (("probe", "../x"), ("probe", ""), ("scenarios", "A1;rm -rf"), ("image", "gemini:latest"),
                     ("reason", " "), ("child", "/tmp/x")):
            with self.subTest(**{k: v}), self.assertRaises(wl.LaunchRefused):
                wl.probe_command(**dict(ok, **{k: v}))

    def _rig(self, t, *, tamper=None, planted=False, link=False, state="exit=0"):
        athena = os.path.join(t, "athena")
        top = os.path.join(athena, "stub-probe-p1")
        os.makedirs(os.path.join(top, "A1", "session"))
        Path(top, "A1", "session", "native-turn-1.jsonl").write_text('{"sessionId": "s"}\n')
        Path(top, "A1", "probe.json").write_text(json.dumps(smp.labelled({"x": 1})) + "\n")
        if planted:
            Path(top, "A1", "turn-1.jsonl").write_text("ghp_" + "A" * 36 + "\n")
        Path(top, "manifest.json").write_text(json.dumps(smp.manifest(top)))
        if tamper:
            Path(top, "A1", "probe.json").write_text("{}\n")
        if link:
            os.symlink("/etc/passwd", os.path.join(top, "A1", "evil"))

        class R(wl.Runner):
            calls = []

            def remote(self, cmd, *, timeout=3600):
                self.calls.append(cmd)
                if cmd.startswith("if kill -0"):
                    return 0, state + "\n", ""
                if cmd.startswith("test -d "):
                    with tarfile.open(os.path.join(athena, "stub-probe-p1.tar"), "w") as tar:
                        tar.add(top, arcname="stub-probe-p1")
                    return 0, "", ""
                if cmd.startswith("sha256sum "):
                    p = os.path.join(athena, os.path.basename(cmd.split()[1]))
                    return 0, hashlib.sha256(Path(p).read_bytes()).hexdigest() + "  x\n", ""
                return 1, "", ""

            def copy_from(self, src, dst):
                shutil.copyfile(os.path.join(athena, os.path.basename(src)), dst)
                return 0, "", ""
        return R()

    def _fetch(self, t, runner):
        return wl.fetch_probe(runner, child=CHILD, probe_id="p1", out=os.path.join(t, "mac", "stub-probe-p1"),
                              gitleaks=twl.fake_gitleaks(t), work=os.path.join(t, "work"))

    def test_a_clean_fetch_lands_the_folder(self):
        with tempfile.TemporaryDirectory() as t:
            os.mkdir(os.path.join(t, "mac"))
            got = self._fetch(t, self._rig(t))
            self.assertEqual(got["fetched"], os.path.join(t, "mac", "stub-probe-p1"))
            self.assertTrue(Path(got["fetched"], "A1", "session", "native-turn-1.jsonl").is_file())
            self.assertEqual(wl.probe_manifest_problems(got["fetched"]), [])

    def test_each_refusal(self):
        for kw, words in (({"tamper": True}, "manifest"), ({"planted": True}, "scan refused"),
                          ({"link": True}, "not a regular file"), ({"state": "running"}, "still running")):
            with self.subTest(**kw), tempfile.TemporaryDirectory() as t:
                os.mkdir(os.path.join(t, "mac"))
                with self.assertRaises(wl.LaunchRefused) as cm:
                    self._fetch(t, self._rig(t, **kw))
                self.assertIn(words, str(cm.exception))
                self.assertFalse(os.path.lexists(os.path.join(t, "mac", "stub-probe-p1")))

    def test_a_member_outside_the_folder_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            tar_path = os.path.join(t, "x.tar")
            with tarfile.open(tar_path, "w") as tar:
                data = b"x"
                info = tarfile.TarInfo("stub-probe-p1/../../escape")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            with self.assertRaises(wl.LaunchRefused):
                wl._extract_probe(tar_path, "stub-probe-p1", os.path.join(t, "u"))


if __name__ == "__main__":
    unittest.main()
