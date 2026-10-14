"""box/ownership.py: the take's ownership road (grant before launch, restore after teardown), with a fake runtime.

No container runs here. OWN_PROGRAM itself is run on a local temporary folder (its fixed mount path replaced), as the
current user chowning to the current user, to bind its walk: links never followed, special files refused.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from box import measure_live, ownership as ow, run_take as rt  # noqa: E402

IMAGE = json.loads((STUDY / "box" / "image.lock").read_text())["image_id"]
CALLER = {"PATH": "/usr/bin:/bin", "DOCKER_HOST": "unix:///run/user/1000/docker.sock"}
IDS = ["a" * 64, "b" * 64]


class Fake:
    def __init__(self, fail=(), present=()):
        self.calls, self.fail, self.present = [], set(fail), list(present)

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append(list(argv))
        if argv[1:2] == ["ps"]:
            return rt.Completed(0, "".join(i + "\n" for i in self.present), "")
        src = [a for a in argv if a.startswith("type=bind,source=")]
        if src and src[0].split("=")[2].split(",")[0] in self.fail:
            return rt.Completed(1, "", "nonregular refused")
        return rt.Completed(0, "", "")


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="own-")
        self.tree, self.cfg, self.ev = (os.path.join(self.d, n) for n in ("t", "c", "e"))
        for p in (self.tree, self.cfg, self.ev):
            os.mkdir(p)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def own_calls(self, fake):
        return [c for c in fake.calls if c[1:2] == ["run"]]


class Grant(Base):
    def test_both_folders_to_the_agent_run_tree_first(self):
        f = Fake()
        rec = ow.grant(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, caller_env=CALLER)
        self.assertTrue(rec["ok"])
        calls = self.own_calls(f)
        self.assertEqual(calls, [ow.own_argv(IMAGE, self.tree, 10001), ow.own_argv(IMAGE, self.cfg, 10001),
                                 ow.own_argv(IMAGE, self.ev, 10002)])
        self.assertEqual(calls[0][:16], ["docker", "run", "--rm", "--pull=never", "--network", "none", "--user", "0:0",
                                         "--cap-drop", "ALL", "--cap-add", "CHOWN", "--cap-add", "DAC_OVERRIDE",
                                         "--security-opt", "no-new-privileges"])
        self.assertEqual(calls[0][16:18], ["--mount", f"type=bind,source={self.tree},target=/scratch"])
        self.assertEqual(calls[0][18:], [IMAGE, "/usr/bin/python3", "-I", "-S", "-c", ow.OWN_PROGRAM, "10001"])

    def test_the_first_failure_refuses_before_launch(self):
        f = Fake(fail={self.tree})
        with self.assertRaises(ow.OwnershipError) as cm:
            ow.grant(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, caller_env=CALLER)
        self.assertEqual(len(self.own_calls(f)), 1)
        self.assertFalse(cm.exception.record["ok"])

    def test_refusals_before_any_call(self):
        os.symlink(self.tree, os.path.join(self.d, "link"))
        os.mkdir(os.path.join(self.d, "repo"))
        os.mkdir(os.path.join(self.d, "repo", ".git"))
        os.mkdir(os.path.join(self.d, "repo", "cfg"))
        cases = [dict(image=IMAGE[:19]), dict(image="take-a:latest"), dict(run_tree="relative/t"),
                 dict(run_tree=os.path.join(self.d, "link")), dict(run_tree=os.path.join(self.d, "absent")),
                 dict(config_dir=os.path.join(self.tree, "inner")), dict(config_dir=os.path.join(self.d, "repo", "cfg")),
                 dict(run_tree=self.d), dict(evidence_dir=os.path.join(self.tree, "inner")),
                 dict(evidence_dir=os.path.join(self.d, "link"))]
        os.mkdir(os.path.join(self.tree, "inner"))
        for over in cases:
            kw = dict(image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev)
            kw.update(over)
            f = Fake()
            with self.subTest(over=over), self.assertRaises(rt.Refused):
                ow.grant(f, caller_env=CALLER, **kw)
            self.assertEqual(f.calls, [])

    def test_only_the_agent_or_the_host_user(self):
        for uid in (10003, 1, -1, 110000):
            with self.subTest(uid=uid), self.assertRaises(rt.Refused):
                ow.own_argv(IMAGE, self.tree, uid)


class Restore(Base):
    def test_back_to_the_host_user_after_teardown(self):
        f = Fake()
        rec = ow.restore(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, ids=IDS, caller_env=CALLER)
        self.assertTrue(rec["ok"])
        self.assertEqual(f.calls[0][:2], ["docker", "ps"])
        self.assertEqual(self.own_calls(f), [ow.own_argv(IMAGE, self.tree, 0), ow.own_argv(IMAGE, self.cfg, 0),
                                             ow.own_argv(IMAGE, self.ev, 0)])

    def test_a_present_container_refuses_the_restore(self):
        f = Fake(present=[IDS[1]])
        with self.assertRaises(ow.OwnershipError):
            ow.restore(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, ids=IDS, caller_env=CALLER)
        self.assertEqual(self.own_calls(f), [])

    def test_every_step_runs_and_a_failure_raises(self):
        f = Fake(fail={self.tree})
        with self.assertRaises(ow.OwnershipError) as cm:
            ow.restore(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, ids=IDS, caller_env=CALLER)
        self.assertEqual(len(self.own_calls(f)), 3)
        self.assertIn("restore-run_tree exited 1", cm.exception.record["problems"])

    def test_the_host_side_owner_is_verified(self):
        Path(self.cfg, "settings.json").write_text("{}")
        real = os.getuid()
        with mock.patch.object(ow.os, "getuid", lambda: real + 1), self.assertRaises(ow.OwnershipError) as cm:
            ow.restore(Fake(), image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, ids=IDS, caller_env=CALLER)
        self.assertTrue(any("settings.json" in p for p in cm.exception.record["problems"]))
        self.assertEqual(ow.owner_problems(self.cfg, real), [])


class Bindings(unittest.TestCase):
    def test_the_uids_are_the_locks(self):
        for rel in ("image.lock", "codex/image.lock", "gemini/image.lock"):
            users = json.loads((STUDY / "box" / rel).read_text())["users"]
            self.assertEqual((users["agent"]["uid"], users["watcher"]["uid"]), (ow.AGENT_UID, ow.WATCHER_UID))
        self.assertEqual(ow.HOST_UID, 0)


class OwnProgram(unittest.TestCase):
    def test_it_is_the_reviewed_walk_plus_the_link_branch(self):
        branch = ('   lst=os.stat(name,dir_fd=fd,follow_symlinks=False)\n'
                  '   if stat.S_ISLNK(lst.st_mode):\n'
                  '    os.chown(name,uid,uid,dir_fd=fd,follow_symlinks=False)\n'
                  '    continue\n')
        self.assertEqual(ow.OWN_PROGRAM.count(branch), 1)
        self.assertEqual(ow.OWN_PROGRAM.replace(branch, ""), measure_live.OWN)

    def run_on(self, root):
        # Run as the current user: its folder replaces /scratch, and the group is left unchanged (-1), since a host
        # user may not belong to a group numbered as its uid; the walk itself is the program's, untouched.
        prog = ow.OWN_PROGRAM.replace('"/scratch"', repr(root)).replace("uid,uid", "uid,-1")
        self.assertEqual(prog.count("uid,-1"), 2)
        return subprocess.run([sys.executable, "-I", "-S", "-c", prog, str(os.getuid())], capture_output=True,
                              text=True, timeout=60)

    def test_links_are_never_followed_and_specials_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "r")
            os.makedirs(os.path.join(root, "a", "b"))
            Path(root, "a", "b", "f.txt").write_text("x")
            outside = os.path.join(d, "outside")
            os.mkdir(outside)
            os.symlink(outside, os.path.join(root, "a", "to-outside"))
            os.symlink("/nonexistent/target", os.path.join(root, "dangling"))
            p = self.run_on(root)
            self.assertEqual(p.returncode, 0, p.stderr)
            os.mkfifo(os.path.join(root, "a", "fifo"))
            p = self.run_on(root)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("nonregular refused", p.stderr)


if __name__ == "__main__":
    unittest.main()
