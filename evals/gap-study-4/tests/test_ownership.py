"""box/ownership.py: the take's ownership road (grant before launch, restore after teardown), with a fake runtime.

No container runs here. OWN_PROGRAM itself is run on a local temporary folder (its fixed mount path replaced), as the
current user chowning to the current user, to bind its walk: links never followed, special files refused.
"""
import json
import os
import stat
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


def strip(argv):
    """An ownership or operator argv less its per-step cidfile pair (the cidfile is a fresh temporary path)."""
    argv = list(argv)
    if "--cidfile" in argv:
        i = argv.index("--cidfile")
        del argv[i:i + 2]
    return argv


class Fake:
    """docker for the ownership steps: writes each step's cidfile, answers the listing from `present` and the
    containers a step left (`leave`), fails or times out a step by its mounted source."""

    def __init__(self, fail=(), present=(), timeout=(), leave=(), no_cid=False, reply=""):
        self.calls, self.fail, self.present = [], set(fail), list(present)
        self.timeout, self.leave, self.no_cid, self.reply = set(timeout), set(leave), no_cid, reply
        self.n, self.removed = 0, []

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append(list(argv))
        if argv[1:2] == ["ps"]:
            return rt.Completed(0, "".join(i + "\n" for i in self.present), "")
        if argv[1:2] == ["rm"]:
            self.removed.append(argv[-1])
            self.present = [i for i in self.present if i != argv[-1]]
            return rt.Completed(0, "", "")
        src = [a for a in argv if a.startswith("type=bind,source=")]
        src = src[0].split("=")[2].split(",")[0] if src else None
        if "--cidfile" in argv and not self.no_cid:
            self.n += 1
            cid = f"{self.n:064x}"
            Path(argv[argv.index("--cidfile") + 1]).write_text(cid)
            if src in self.leave or src in self.timeout:
                self.present.append(cid)
        if src in self.timeout:
            raise TimeoutError("step timed out")
        if src in self.fail:
            return rt.Completed(1, "", "nonregular refused")
        return rt.Completed(0, self.reply, "")


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
        return [strip(c) for c in fake.calls if c[1:2] == ["run"]]


class Grant(Base):
    def test_both_folders_to_the_agent_run_tree_first(self):
        f = Fake()
        rec = ow.grant(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, caller_env=CALLER)
        self.assertTrue(rec["ok"])
        calls = self.own_calls(f)
        self.assertEqual(calls, [ow.own_argv(IMAGE, self.tree, 10001, strict=True),
                                 ow.own_argv(IMAGE, self.cfg, 10001, strict=True),
                                 ow.own_argv(IMAGE, self.ev, 10002, strict=True)])
        self.assertEqual(calls[0][:16], ["docker", "run", "--rm", "--pull=never", "--network", "none", "--user", "0:0",
                                         "--cap-drop", "ALL", "--cap-add", "CHOWN", "--cap-add", "DAC_READ_SEARCH",
                                         "--security-opt", "no-new-privileges"])
        self.assertEqual(calls[0][16:18], ["--mount", f"type=bind,source={self.tree},target=/scratch"])
        self.assertEqual(calls[0][18:], [IMAGE, "/usr/bin/python3", "-I", "-S", "-c", ow.OWN_PROGRAM, "10001",
                                         "strict"])
        self.assertEqual(ow.own_argv(IMAGE, self.tree, 0, strict=False)[-1], "restore")

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
                ow.own_argv(IMAGE, self.tree, uid, strict=True)


class Restore(Base):
    def test_back_to_the_host_user_after_teardown(self):
        f = Fake()
        rec = ow.restore(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, ids=IDS, caller_env=CALLER)
        self.assertTrue(rec["ok"])
        self.assertEqual(f.calls[0][:2], ["docker", "ps"])
        self.assertEqual(self.own_calls(f), [ow.own_argv(IMAGE, self.tree, 0, strict=False),
                                             ow.own_argv(IMAGE, self.cfg, 0, strict=False),
                                             ow.own_argv(IMAGE, self.ev, 0, strict=False)])

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


class RestoreGuards(Base):
    """Review minors 3, 4 and 5: every restore refusal is an OwnershipError; a step's container is named by a
    cidfile, removed on a timeout and never left; and the host-side verify's own sub-guards are bound."""

    def restore(self, fake, **over):
        kw = dict(image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, ids=IDS,
                  caller_env=CALLER)
        kw.update(over)
        return ow.restore(fake, **kw)

    def test_a_link_or_a_missing_folder_is_an_ownership_error_before_any_step(self):
        os.symlink(self.tree, os.path.join(self.d, "link"))
        for over in (dict(run_tree=os.path.join(self.d, "link")), dict(evidence_dir=os.path.join(self.d, "gone")),
                     dict(image="sha256:" + "1" * 12)):
            f = Fake()
            with self.subTest(over=over), self.assertRaises(ow.OwnershipError):
                self.restore(f, **over)
            self.assertEqual(self.own_calls(f), [])

    def test_a_failed_listing_is_an_ownership_error(self):
        class BadList(Fake):
            def run(self, argv, **kw):
                if argv[1:2] == ["ps"]:
                    return rt.Completed(1, "", "daemon gone")
                return super().run(argv, **kw)
        with self.assertRaises(ow.OwnershipError):
            self.restore(BadList())

    def test_a_timed_out_step_is_removed_and_fails(self):
        f = Fake(timeout={self.tree})
        with self.assertRaises(ow.OwnershipError) as cm:
            self.restore(f)
        step = cm.exception.record["steps"][0]
        self.assertTrue(step["timed_out"])
        self.assertEqual(f.removed, [step["container_id"]])
        self.assertIn("restore-run_tree exited None", cm.exception.record["problems"])
        self.assertEqual(len(cm.exception.record["steps"]), 3)          # every step still ran

    def test_a_left_container_or_an_unreadable_id_fails_the_step(self):
        for f in (Fake(leave={self.cfg}), Fake(no_cid=True)):
            with self.subTest(f=vars(f).get("no_cid")), self.assertRaises(ow.OwnershipError) as cm:
                self.restore(f)
            self.assertTrue([s for s in cm.exception.record["steps"] if s.get("left")])
        f = Fake(timeout={self.tree})
        with self.assertRaises(ow.OwnershipError):
            ow.grant(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, evidence_dir=self.ev, caller_env=CALLER)
        self.assertEqual(len(f.removed), 1)

    def test_the_verify_never_follows_a_link(self):
        os.symlink("/etc/hosts", os.path.join(self.tree, "to-root-file"))
        os.symlink("/etc", os.path.join(self.tree, "to-root-folder"))
        self.assertEqual(os.stat("/etc/hosts").st_uid, 0)
        self.assertEqual(ow.owner_problems(self.tree, os.getuid()), [])

    def test_the_verify_reports_an_unreadable_folder(self):
        locked = os.path.join(self.tree, "locked")
        os.mkdir(locked)
        Path(locked, "f").write_text("x")
        os.chmod(locked, 0)
        try:
            self.assertTrue(any("unreadable" in p for p in ow.owner_problems(self.tree, os.getuid())))
        finally:
            os.chmod(locked, 0o700)

    def test_the_verify_checks_the_top_folder_itself(self):
        empty = os.path.join(self.d, "empty")
        os.mkdir(empty)
        self.assertEqual(ow.owner_problems(empty, os.getuid() + 1), [f"{empty}: owner is not the host user"])


class OwnProgram(unittest.TestCase):
    def test_it_is_the_reviewed_walk_plus_the_link_branch(self):
        branch = ('   lst=os.stat(name,dir_fd=fd,follow_symlinks=False)\n'
                  '   if stat.S_ISLNK(lst.st_mode):\n'
                  '    os.chown(name,uid,uid,dir_fd=fd,follow_symlinks=False)\n'
                  '    continue\n')
        strict = ('strict=sys.argv[2]=="strict"\n',
                  ' if strict and (st.st_dev!=root_dev or (stat.S_ISREG(st.st_mode) and st.st_nlink!=1)):'
                  'raise RuntimeError("hard link or foreign device refused")\n',
                  'root_dev=os.fstat(fd).st_dev\n',
                  'restore=sys.argv[2]=="restore"\n',
                  ' if restore:os.fchmod(fd,stat.S_IMODE(os.fstat(fd).st_mode)|(0o700 if stat.S_ISDIR(st.st_mode) else '
                  '0o600))\n')
        prog = ow.OWN_PROGRAM
        for added in (branch,) + strict:
            self.assertEqual(prog.count(added), 1, added)
            prog = prog.replace(added, "")
        self.assertEqual(prog, measure_live.OWN)

    def run_on(self, root, mode="loose"):
        # Run as the current user: its folder replaces /scratch, and the group is left unchanged (-1), since a host
        # user may not belong to a group numbered as its uid; the walk itself is the program's, untouched.
        prog = ow.OWN_PROGRAM.replace('"/scratch"', repr(root)).replace("uid,uid", "uid,-1")
        self.assertEqual(prog.count("uid,-1"), 2)
        return subprocess.run([sys.executable, "-I", "-S", "-c", prog, str(os.getuid()), mode], capture_output=True,
                              text=True, timeout=60)

    def test_restore_adds_only_the_owners_bits(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "r")
            os.makedirs(os.path.join(root, "sub"))
            for name, mode in (("ro.txt", 0o400), ("grp.txt", 0o444), ("odd.txt", 0o640)):
                Path(root, "sub", name).write_text("x")
                os.chmod(os.path.join(root, "sub", name), mode)
            os.chmod(os.path.join(root, "sub"), 0o500)
            os.symlink("/etc/hosts", os.path.join(root, "link"))
            hosts = os.stat("/etc/hosts").st_mode
            p = self.run_on(root, "restore")
            self.assertEqual(p.returncode, 0, p.stderr)
            got = {n: stat.S_IMODE(os.lstat(os.path.join(root, "sub", n)).st_mode)
                   for n in ("ro.txt", "grp.txt", "odd.txt")}
            self.assertEqual(got, {"ro.txt": 0o600, "grp.txt": 0o644, "odd.txt": 0o640})
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(root, "sub")).st_mode), 0o700)
            self.assertEqual(os.stat("/etc/hosts").st_mode, hosts)
            Path(root, "sub", "strict.txt").write_text("x")
            os.chmod(os.path.join(root, "sub", "strict.txt"), 0o400)
            self.assertEqual(self.run_on(root, "strict").returncode, 0)          # a grant changes no mode
            self.assertEqual(stat.S_IMODE(os.lstat(os.path.join(root, "sub", "strict.txt")).st_mode), 0o400)

    def test_strict_refuses_hard_links_and_loose_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "r")
            os.makedirs(root)
            Path(root, "a.txt").write_text("x")
            self.assertEqual(self.run_on(root, "strict").returncode, 0)
            os.link(os.path.join(root, "a.txt"), os.path.join(d, "outside-link.txt"))
            p = self.run_on(root, "strict")
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("hard link or foreign device refused", p.stderr)
            self.assertEqual(self.run_on(root, "loose").returncode, 0)

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


class OperatorSteps(unittest.TestCase):
    """Review finding 2: the operator's mid-take reads and writes run in a one-shot container as the agent's uid,
    through directory descriptors with O_NOFOLLOW."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="op-")
        self.root = os.path.join(self.d, "tree")
        os.makedirs(os.path.join(self.root, "p", "00_data"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def run_program(self, program, *args):
        prog = program.replace('"/scratch"', repr(self.root))
        return subprocess.run([sys.executable, "-I", "-S", "-c", prog, *args], capture_output=True, text=True,
                              timeout=60)

    def write(self, rel, data=b"sample_id\nS1\n"):
        import base64
        return self.run_program(ow.WRITE_PROGRAM, rel, base64.b64encode(data).decode())

    def test_argv_runs_as_the_agent_without_capabilities(self):
        argv = ow.operator_argv(IMAGE, self.root, ow.WRITE_PROGRAM, "p/x.csv", "eA==")
        self.assertEqual(argv[:12], ["docker", "run", "--rm", "--pull=never", "--network", "none", "--user",
                                     rt.AGENT_USER, "--cap-drop", "ALL", "--security-opt", "no-new-privileges"])
        self.assertNotIn("--cap-add", argv)
        self.assertEqual(argv[12:14], ["--mount", f"type=bind,source={self.root},target=/scratch"])

    def test_the_write_program(self):
        p = self.write("p/00_data/samples.csv")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(Path(self.root, "p", "00_data", "samples.csv").read_bytes(), b"sample_id\nS1\n")
        self.assertEqual(json.loads(p.stdout)["bytes"], 13)
        self.assertEqual(self.write("p/00_data/samples.csv", b"x").returncode, 0)          # an overwrite
        self.assertEqual(Path(self.root, "p", "00_data", "samples.csv").read_bytes(), b"x")
        outside = os.path.join(self.d, "outside.txt")
        Path(outside).write_text("host")
        os.symlink(outside, os.path.join(self.root, "p", "00_data", "link.csv"))
        os.symlink(os.path.join(self.d), os.path.join(self.root, "p", "dirlink"))
        os.mkfifo(os.path.join(self.root, "p", "fifo.csv"))
        os.link(os.path.join(self.root, "p", "00_data", "samples.csv"), os.path.join(self.root, "p", "hard.csv"))
        for rel in ("p/00_data/link.csv", "p/dirlink/outside.txt", "p/fifo.csv", "p/hard.csv", "p/absent/x.csv"):
            with self.subTest(rel=rel):
                self.assertNotEqual(self.write(rel).returncode, 0)
        self.assertEqual(Path(outside).read_text(), "host")
        # R2-2: the one-link check comes before any truncation: the hard-linked file keeps its bytes
        self.assertEqual(Path(self.root, "p", "00_data", "samples.csv").read_bytes(), b"x")

    def test_the_read_program(self):
        Path(self.root, "p", "00_data", "samples.csv").write_bytes(b"sample_id\n")
        import base64
        p = self.run_program(ow.READ_PROGRAM, "p/00_data/samples.csv", "1048576")
        self.assertEqual(base64.b64decode(json.loads(p.stdout)["b64"]), b"sample_id\n")
        for rel in ("p/00_data/none.csv", "p/none/x.csv"):
            self.assertEqual(json.loads(self.run_program(ow.READ_PROGRAM, rel, "10").stdout), {"exists": False})
        outside = os.path.join(self.d, "secret.txt")
        Path(outside).write_text("host")
        os.symlink(outside, os.path.join(self.root, "p", "link.csv"))
        os.symlink(self.d, os.path.join(self.root, "p", "dirlink"))
        os.mkfifo(os.path.join(self.root, "p", "fifo.csv"))
        for rel, limit in (("p/link.csv", "100"), ("p/fifo.csv", "100"), ("p/00_data/samples.csv", "3"),
                           ("p/dirlink/secret.txt", "100")):    # R2-2: never read through a parent-folder link
            with self.subTest(rel=rel):
                self.assertNotEqual(self.run_program(ow.READ_PROGRAM, rel, limit).returncode, 0)

    def test_paths_and_sizes_refuse_before_any_call(self):
        for rel in ("", "/abs", "../x", "p/../x", "p//x", ".", "p/\0x"):
            f = Fake()
            with self.subTest(rel=rel), self.assertRaises(rt.Refused):
                ow.operator_write(f, image=IMAGE, run_tree=self.root, rel_path=rel, data=b"x")
            self.assertEqual(f.calls, [])
        with self.assertRaises(rt.Refused):
            ow.operator_write(Fake(), image=IMAGE, run_tree=self.root, rel_path="p/x", data=b"x" * 65537)

    def test_the_reply_must_be_the_data(self):
        class Reply(Fake):
            def __init__(self, out, rc=0):
                super().__init__()
                self.out, self.rc = out, rc

            def run(self, argv, *, env=None, timeout=None):
                self.calls.append(list(argv))
                if argv[1:2] == ["ps"]:
                    return rt.Completed(0, "", "")
                if "--cidfile" in argv:
                    Path(argv[argv.index("--cidfile") + 1]).write_text("c" * 64)
                return rt.Completed(self.rc, self.out, "refused" if self.rc else "")
        import hashlib
        good = json.dumps({"sha256": hashlib.sha256(b"x").hexdigest(), "bytes": 1})
        self.assertTrue(ow.operator_write(Reply(good), image=IMAGE, run_tree=self.root, rel_path="p/x",
                                          data=b"x")["ok"])
        for reply, rc in ((good, 1), ("{}", 0), ("", 0), (json.dumps({"sha256": "0" * 64, "bytes": 1}), 0)):
            with self.subTest(reply=reply, rc=rc), self.assertRaises(ow.OwnershipError):
                ow.operator_write(Reply(reply, rc), image=IMAGE, run_tree=self.root, rel_path="p/x", data=b"x")
        self.assertIsNone(ow.operator_read(Reply('{"exists": false}'), image=IMAGE, run_tree=self.root,
                                           rel_path="p/x"))
        self.assertEqual(ow.operator_read(Reply('{"exists": true, "b64": "eA=="}'), image=IMAGE,
                                          run_tree=self.root, rel_path="p/x"), b"x")
        for reply in ('{"exists": true}', '{"exists": false, "b64": ""}', "nope"):
            with self.subTest(reply=reply), self.assertRaises(ow.OwnershipError):
                ow.operator_read(Reply(reply), image=IMAGE, run_tree=self.root, rel_path="p/x")


if __name__ == "__main__":
    unittest.main()
