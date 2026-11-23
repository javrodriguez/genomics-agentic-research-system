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
                  '   if stat.S_ISLNK(lst.st_mode) or (restore and stat.S_ISSOCK(lst.st_mode)):\n'
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

    def test_a_socket_is_chowned_in_place_by_a_restore_only(self):
        # lane fold4/records (glitch-45's ruling): a claude-code take killed at its budget leaves Claude Code's Unix
        # socket (.tmp/cc-socks/<n>.sock) in the run tree; opening it fails (ENXIO), so the restore chowns it in place,
        # never opening it, as it does a link. A grant still refuses it, and a fifo still refuses either way.
        import socket
        with tempfile.TemporaryDirectory(dir="/tmp") as d:
            root = os.path.join(d, "r")
            os.makedirs(os.path.join(root, "cc-socks"))
            path = os.path.join(root, "cc-socks", "1.sock")
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.bind(path)
                self.assertTrue(stat.S_ISSOCK(os.lstat(path).st_mode))
                p = self.run_on(root, "restore")
                self.assertEqual(p.returncode, 0, f"a restore over a socket failed: {p.stderr}")
                self.assertEqual(os.lstat(path).st_uid, os.getuid())
                self.assertTrue(stat.S_ISSOCK(os.lstat(path).st_mode), "the socket is left in place")
                p = self.run_on(root, "strict")
                self.assertNotEqual(p.returncode, 0, "a grant chowned a socket")
            finally:
                sock.close()
            os.unlink(path)
            os.mkfifo(os.path.join(root, "cc-socks", "fifo"))
            p = self.run_on(root, "restore")
            self.assertNotEqual(p.returncode, 0, "a restore chowned a fifo")
            self.assertIn("nonregular refused", p.stderr)


def read_reply(data: bytes) -> str:
    import base64
    import hashlib
    return json.dumps({"exists": True, "b64": base64.b64encode(data).decode(), "sha256": hashlib.sha256(data).hexdigest(),
                       "bytes": len(data)})


class OperatorSteps(unittest.TestCase):
    """Review finding 2: the operator's mid-take reads and writes run in a one-shot container as the agent's uid,
    through directory descriptors with O_NOFOLLOW."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="op-")
        self.root = os.path.join(self.d, "tree")
        os.makedirs(os.path.join(self.root, "p", "00_data"))
        self.cfg = os.path.join(self.d, "cfg")
        os.mkdir(self.cfg)
        self.pair = {"run_tree": self.root, "config_dir": self.cfg}

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

    def test_argv_runs_as_the_agent_without_capabilities(self):  # the write's argv (reads: _only_its_root_read_only)
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
        for kind in ("run_tree", "config"):
            self.assertIsNone(ow.operator_read(Reply('{"exists": false}'), image=IMAGE, root_kind=kind,
                                               **self.pair, rel_path="p/x"))
            self.assertEqual(ow.operator_read(Reply(read_reply(b"x")), image=IMAGE, root_kind=kind,
                                              **self.pair, rel_path="p/x"), b"x")
            bad_sha = json.dumps(dict(json.loads(read_reply(b"x")), sha256="0" * 64))
            bad_len = json.dumps(dict(json.loads(read_reply(b"x")), bytes=2))
            for reply in ('{"exists": true}', '{"exists": false, "b64": ""}', "nope",
                          '{"exists": true, "b64": "eA=="}', bad_sha, bad_len):
                with self.subTest(kind=kind, reply=reply), self.assertRaises(ow.OwnershipError):
                    ow.operator_read(Reply(reply), image=IMAGE, root_kind=kind, **self.pair, rel_path="p/x")

    def test_a_read_mounts_only_its_root_read_only(self):
        """glitch-06 (14 Oct 2026): a mid-take read of the agent-owned config folder (native sessions) or of the run
        tree is one container as the agent, no capabilities, no network, no new privileges, ONLY the named root
        mounted, read-only, with the root's own cap."""
        cfg = self.cfg
        for kind, root, cap in (("config", cfg, ow.CONFIG_READ_MAX_BYTES),
                                ("run_tree", self.root, ow.OPERATOR_READ_MAX_BYTES)):
            f = Fake(reply='{"exists": false}')
            with self.subTest(kind=kind):
                self.assertIsNone(ow.operator_read(f, image=IMAGE, root_kind=kind, **self.pair,
                                                   rel_path="sessions/s1.jsonl", caller_env=CALLER))
                runs = [strip(c) for c in f.calls if c[1:2] == ["run"]]
                self.assertEqual(len(runs), 1)
                argv = runs[0]
                self.assertEqual(argv[:12], ["docker", "run", "--rm", "--pull=never", "--network", "none", "--user",
                                             rt.AGENT_USER, "--cap-drop", "ALL", "--security-opt",
                                             "no-new-privileges"])
                self.assertNotIn("--cap-add", argv)
                self.assertNotIn("--privileged", argv)
                mounts = [argv[i + 1] for i, a in enumerate(argv) if a in ("--mount", "-v", "--volume")]
                self.assertEqual(mounts, [f"type=bind,source={root},target=/scratch,readonly"])
                self.assertEqual(argv[argv.index(ow.READ_PROGRAM) + 1:], ["sessions/s1.jsonl", str(cap)])
        self.assertEqual(ow.CONFIG_READ_MAX_BYTES, 32 * 1024 * 1024)
        for kind in ("home", "", None, "evidence"):
            f = Fake()
            with self.subTest(kind=kind), self.assertRaises(rt.Refused):
                ow.operator_read(f, image=IMAGE, root_kind=kind, **self.pair, rel_path="x")
            self.assertEqual(f.calls, [])
        with self.assertRaises(TypeError):
            ow.operator_read(Fake(), image=IMAGE, run_tree=self.root, rel_path="x")   # no implicit root
        with self.assertRaises(TypeError):
            ow.operator_read(Fake(), image=IMAGE, root_kind="config", root=self.cfg, rel_path="x")  # the old API

    # review-operator-read O-2: credential files in the config folder are never read or listed by the host
    def test_credential_names_refuse_under_the_config_root(self):
        from box import preflight
        self.assertIn("auth.json", [n for n, _ in preflight.CREDENTIAL_FILES[rt.CODEX]])
        src = dict(preflight.CREDENTIAL_FILES[rt.CODEX])["auth.json"]
        self.assertIn("subscription amendment", src)
        self.assertIn("cli_auth_credentials_store file", src)
        for rel in ("auth.json", ".credentials.json", "oauth_creds.json", "google_accounts.json", "x/token.txt",
                    "secrets/s.jsonl", "a/b/key.pem", "AUTH.JSON"):
            for fn, kw in ((ow.operator_read, {"rel_path": rel}), (ow.operator_list, {"rel_dir": rel})):
                f = Fake(reply='{"exists": false}')
                with self.subTest(rel=rel, fn=fn.__name__), self.assertRaises(rt.Refused):
                    fn(f, image=IMAGE, root_kind="config", **self.pair, **kw)
                self.assertEqual(f.calls, [])
        # a session path passes, and the run tree is not under this rule (its files are the task's)
        self.assertIsNone(ow.operator_read(Fake(reply='{"exists": false}'), image=IMAGE, root_kind="config",
                                           **self.pair, rel_path="sessions/2026/10/14/rollout-1.jsonl"))
        self.assertIsNone(ow.operator_read(Fake(reply='{"exists": false}'), image=IMAGE, root_kind="run_tree",
                                           **self.pair, rel_path="p/tokenize.py"))
        listed = ow.operator_list(Fake(reply=list_reply([(b"auth.json", "file"), (b"sessions", "dir")])), image=IMAGE,
                                  root_kind="config", **self.pair, rel_dir=".")
        self.assertEqual(listed, [("auth.json", "other"), ("sessions", "dir")])

    # review-operator-read O-3: the root is the take's own, an existing folder, never a link
    def test_the_root_is_the_takes_own_folder(self):
        link = os.path.join(self.d, "cfglink")
        os.symlink(self.cfg, link)
        repo = os.path.join(self.d, "repo")
        os.makedirs(os.path.join(repo, ".git"))
        os.mkdir(os.path.join(repo, "cfg"))
        cases = {"config a link": dict(self.pair, config_dir=link),
                 "config absent": dict(self.pair, config_dir=os.path.join(self.d, "none")),
                 "config inside the tree": dict(self.pair, config_dir=os.path.join(self.root, "p")),
                 "tree inside the config": dict(self.pair, run_tree=self.cfg + "/x"),
                 "config in a repository": dict(self.pair, config_dir=os.path.join(repo, "cfg")),
                 "relative": dict(self.pair, run_tree="tree")}
        os.mkdir(self.cfg + "/x")
        for name, pair in cases.items():
            for fn, kw in ((ow.operator_read, {"rel_path": "a"}), (ow.operator_list, {"rel_dir": "."})):
                f = Fake(reply='{"exists": false}')
                with self.subTest(name, fn=fn.__name__), self.assertRaises(rt.Refused):
                    fn(f, image=IMAGE, root_kind="config", **pair, **kw)
                self.assertEqual(f.calls, [])

    # review-operator-read O-1: a torn read refuses, never retried
    def test_a_torn_read_refuses(self):
        path = os.path.join(self.cfg, "s.jsonl")
        Path(path).write_bytes(b"x" * 200000)
        prog = ow.READ_PROGRAM.replace('"/scratch"', repr(self.cfg))
        hook = " c=os.read(f,65536)\n"
        self.assertEqual(prog.count(hook), 1)
        writer = prog.replace(hook, hook + f" if c and not data:open({path!r},'ab').write(b'y')\n")   # one append mid-read
        p = subprocess.run([sys.executable, "-I", "-S", "-c", writer, "s.jsonl", str(10 ** 7)], capture_output=True,
                           text=True, timeout=60)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("changed during the read", p.stderr)
        truncate = prog.replace(hook, hook + f" if c and not data:os.truncate({path!r},10)\n")   # shrinks mid-read
        p = subprocess.run([sys.executable, "-I", "-S", "-c", truncate, "s.jsonl", str(10 ** 7)], capture_output=True,
                           text=True, timeout=60)
        self.assertNotEqual(p.returncode, 0)
        Path(path).write_bytes(b"z" * 200000)
        rewrite = prog.replace(hook, hook + f" if c and not data:import time;time.sleep(0.05);fd2=os.open({path!r},os.O_WRONLY);os.pwrite(fd2,b'q',0);os.close(fd2)\n")
        p = subprocess.run([sys.executable, "-I", "-S", "-c", rewrite, "s.jsonl", str(10 ** 7)],    # same size, new mtime
                           capture_output=True, text=True, timeout=60)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("changed during the read", p.stderr)
        # review-operator-list L-1: the name replaced or removed during the read (the open descriptor alone sees neither)
        same = (f"open({path!r}+'.new','wb').write(b'z'*200000);m=os.stat({path!r}).st_mtime_ns;"
                f"os.utime({path!r}+'.new',ns=(m,m));os.replace({path!r}+'.new',{path!r})")
        for label, act in (("replaced", f"open({path!r}+'.new','wb').write(b'z'*200000);os.replace({path!r}+'.new',{path!r})"),
                           ("replaced by a twin (same size and mtime, another inode)", same),
                           ("removed", f"os.unlink({path!r})")):
            Path(path).write_bytes(b"z" * 200000)
            swap = prog.replace(hook, hook + f" if c and not data:{act}\n")
            p = subprocess.run([sys.executable, "-I", "-S", "-c", swap, "s.jsonl", str(10 ** 7)], capture_output=True,
                               text=True, timeout=60)
            with self.subTest(label):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("changed during the read", p.stderr)
        # review-walk-token W-4: truncated to the read offset and regrown to the same size with the mtime put back,
        # so the name's inode, size and mtime all match: only the short read shows it
        Path(path).write_bytes(b"z" * 200000)
        post = "try:post="
        self.assertEqual(prog.count(post), 1)
        regrow = prog.replace(hook, hook + f" if c and not data:M=os.stat({path!r}).st_mtime_ns;"
                                           f"os.truncate({path!r},len(c))\n").replace(
            post, f"os.truncate({path!r},200000);os.utime({path!r},ns=(M,M))\n" + post)
        p = subprocess.run([sys.executable, "-I", "-S", "-c", regrow, "s.jsonl", str(10 ** 7)], capture_output=True,
                           text=True, timeout=60)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("changed during the read", p.stderr)
        Path(path).write_bytes(b"z" * 200000)
        p = subprocess.run([sys.executable, "-I", "-S", "-c", prog, "s.jsonl", str(10 ** 7)], capture_output=True,
                           text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_the_read_program_over_a_config_folder(self):
        """A Codex rollout and a Gemini session file read back with their sha256; a hard-linked file, a link, a
        link-folder and a fifo refuse; the cap holds."""
        import base64
        import hashlib
        cfg = os.path.join(self.d, "cfg")
        os.makedirs(os.path.join(cfg, "sessions", "2026", "10", "14"))
        os.makedirs(os.path.join(cfg, ".gemini", "tmp", "h", "chats"))
        roll = b'{"type":"session_meta"}\n{"type":"response_item"}\n'
        Path(cfg, "sessions", "2026", "10", "14", "rollout-1.jsonl").write_bytes(roll)
        Path(cfg, ".gemini", "tmp", "h", "chats", "session-1.json").write_bytes(b'{"messages":[]}')
        prog = ow.READ_PROGRAM.replace('"/scratch"', repr(cfg))

        def run(rel, limit=str(ow.CONFIG_READ_MAX_BYTES)):
            return subprocess.run([sys.executable, "-I", "-S", "-c", prog, rel, limit], capture_output=True,
                                  text=True, timeout=60)
        p = run("sessions/2026/10/14/rollout-1.jsonl")
        got = json.loads(p.stdout)
        self.assertEqual(base64.b64decode(got["b64"]), roll)
        self.assertEqual((got["sha256"], got["bytes"]), (hashlib.sha256(roll).hexdigest(), len(roll)))
        self.assertEqual(run(".gemini/tmp/h/chats/session-1.json").returncode, 0)
        outside = os.path.join(self.d, "host.json")
        Path(outside).write_text("host")
        os.symlink(outside, os.path.join(cfg, "sessions", "link.jsonl"))
        os.symlink(self.d, os.path.join(cfg, "sessions", "dirlink"))
        os.link(os.path.join(cfg, "sessions", "2026", "10", "14", "rollout-1.jsonl"),
                os.path.join(cfg, "sessions", "hard.jsonl"))
        os.mkfifo(os.path.join(cfg, "sessions", "fifo.jsonl"))
        for rel, limit in (("sessions/link.jsonl", "100"), ("sessions/dirlink/host.json", "100"),
                           ("sessions/hard.jsonl", "100"), ("sessions/fifo.jsonl", "100"),
                           (".gemini/tmp/h/chats/session-1.json", "3")):
            with self.subTest(rel=rel):
                self.assertNotEqual(run(rel, limit).returncode, 0)
        self.assertEqual(Path(outside).read_text(), "host")



def list_reply(entries) -> str:
    """The list program's reply for [(raw name bytes, kind)], canonical as the program prints it."""
    import base64
    import hashlib
    out = [[base64.b64encode(r).decode(), k] for r, k in sorted(entries)]
    return json.dumps({"exists": True, "entries": out,
                       "sha256": hashlib.sha256(json.dumps(out, separators=(",", ":")).encode()).hexdigest()})


class OperatorList(unittest.TestCase):
    """glitch-06 (14 Oct 2026): the harness discovers native session files it cannot name in advance (Gemini's
    tmp/<project>/chats/session-*.jsonl, Codex's sessions/YYYY/MM/DD/rollout-*.jsonl) by listing ONE folder at a time,
    under the operator read's container, mount and refusal rules."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="ol-")
        self.tree = os.path.join(self.d, "tree")
        os.mkdir(self.tree)
        self.cfg = os.path.join(self.d, "cfg")
        day = os.path.join(self.cfg, "sessions", "2026", "10", "14")
        os.makedirs(day)
        Path(day, "rollout-2026-10-14T12-00-00-abc.jsonl").write_text("{}\n")
        os.makedirs(os.path.join(self.cfg, "tmp", "proj1", "chats"))
        Path(self.cfg, "tmp", "proj1", "chats", "session-2026-10-14T12-00-ab12cd34.jsonl").write_text("{}\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def run_program(self, rel, limit="4096", program=None):
        prog = (program or ow.LIST_PROGRAM).replace('"/scratch"', repr(self.cfg))
        return subprocess.run([sys.executable, "-I", "-S", "-c", prog, rel, limit], capture_output=True, text=True,
                              timeout=60)

    def listed(self, rel, **kw):
        p = self.run_program(rel, **kw)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def via_host(self, rel):
        """The real program's output fed through operator_list's own checks (a fake runtime answering with it)."""
        out = self.listed(rel)
        return ow.operator_list(Fake(reply=out), image=IMAGE, root_kind="config", run_tree=self.tree,
                                config_dir=self.cfg, rel_dir=rel,
                                caller_env=CALLER)

    def test_the_dated_folders_walk_level_by_level(self):
        self.assertEqual(self.via_host("."), [("sessions", "dir"), ("tmp", "dir")])
        self.assertEqual(self.via_host("sessions"), [("2026", "dir")])
        self.assertEqual(self.via_host("sessions/2026/10/14"), [("rollout-2026-10-14T12-00-00-abc.jsonl", "file")])
        self.assertEqual(self.via_host("tmp/proj1/chats"), [("session-2026-10-14T12-00-ab12cd34.jsonl", "file")])
        self.assertIsNone(self.via_host("sessions/2026/10/15"))

    def test_one_folder_only_never_recursive(self):
        got = self.via_host("sessions/2026")
        self.assertEqual(got, [("10", "dir")])
        self.assertTrue(all("/" not in n for n, _ in self.via_host("tmp")))

    def test_links_and_others_are_reported_never_followed(self):
        outside = os.path.join(self.d, "outside")
        os.mkdir(outside)
        Path(outside, "secret.jsonl").write_text("host")
        chats = os.path.join(self.cfg, "tmp", "proj1", "chats")
        os.symlink(outside, os.path.join(chats, "dirlink"))
        os.symlink(os.path.join(outside, "secret.jsonl"), os.path.join(chats, "filelink.jsonl"))
        os.mkfifo(os.path.join(chats, "fifo"))
        got = dict(self.via_host("tmp/proj1/chats"))
        self.assertEqual(got["dirlink"], "link")
        self.assertEqual(got["filelink.jsonl"], "link")
        self.assertEqual(got["fifo"], "other")
        os.symlink(outside, os.path.join(self.cfg, "tmp", "linkproj"))
        self.assertNotEqual(self.run_program("tmp/linkproj").returncode, 0)          # never listed through a link
        Path(self.cfg, "tmp", "afile").write_text("x")
        self.assertNotEqual(self.run_program("tmp/afile").returncode, 0)             # a file is not a folder

    def test_names_are_byte_exact(self):
        if sys.platform == "darwin":
            raw = "caf\u00e9-\u2603.jsonl".encode()       # APFS keeps names as valid UTF-8
        else:
            raw = b"bad-\xff.jsonl"
        Path(os.fsdecode(os.path.join(os.fsencode(self.cfg), b"sessions", raw))).write_text("x")
        got = dict(self.via_host("sessions"))
        names = [os.fsencode(n) if k == "other" else n.encode() for n, k in got.items()]
        self.assertIn(raw, names)

    def test_a_non_utf8_name_lists_as_other(self):
        """Review-operator-list L-2: a name that is not valid UTF-8 comes back byte-exact (surrogateescape) as "other",
        so the caller never reads it. The host path is tested everywhere; the program path on a file system that keeps
        such names (APFS refuses them)."""
        raw = b"session-\xff\xfe.jsonl"
        got = ow.operator_list(Fake(reply=list_reply([(raw, "file"), (b"ok.jsonl", "file")])), image=IMAGE,
                               root_kind="config", run_tree=self.tree, config_dir=self.cfg, rel_dir="x")
        self.assertEqual([(os.fsencode(n) if k == "other" else n.encode(), k) for n, k in got],
                         [(b"ok.jsonl", "file"), (raw, "other")])
        try:
            Path(os.fsdecode(os.path.join(os.fsencode(self.cfg), b"sessions", raw))).write_text("x")
        except OSError:
            return                                       # this file system refuses the name (macOS APFS)
        got = dict((os.fsencode(n), k) for n, k in self.via_host("sessions"))
        self.assertEqual(got[raw], "other")

    def test_the_entry_cap_refuses(self):
        for i in range(3):
            Path(self.cfg, "sessions", "2026", f"x{i}").write_text("x")
        self.assertNotEqual(self.run_program("sessions/2026", limit="3").returncode, 0)
        self.assertEqual(self.run_program("sessions/2026", limit="4").returncode, 0)
        self.assertEqual(ow.LIST_MAX_ENTRIES, 4096)

    def test_the_container_and_its_one_read_only_mount(self):
        for kind, root in (("config", self.cfg), ("run_tree", self.tree)):
            f = Fake(reply='{"exists": false}')
            with self.subTest(kind=kind):
                self.assertIsNone(ow.operator_list(f, image=IMAGE, root_kind=kind, run_tree=self.tree,
                                                   config_dir=self.cfg, rel_dir="sessions", caller_env=CALLER))
                runs = [strip(c) for c in f.calls if c[1:2] == ["run"]]
                self.assertEqual(len(runs), 1)
                argv = runs[0]
                self.assertEqual(argv[:12], ["docker", "run", "--rm", "--pull=never", "--network", "none", "--user",
                                             rt.AGENT_USER, "--cap-drop", "ALL", "--security-opt",
                                             "no-new-privileges"])
                self.assertNotIn("--cap-add", argv)
                mounts = [argv[i + 1] for i, a in enumerate(argv) if a in ("--mount", "-v", "--volume")]
                self.assertEqual(mounts, [f"type=bind,source={root},target=/scratch,readonly"])
                self.assertEqual(argv[argv.index(ow.LIST_PROGRAM) + 1:], ["sessions", str(ow.LIST_MAX_ENTRIES)])
        for kind, rel in (("home", "sessions"), ("config", "../x"), ("config", "/abs"), ("config", ""),
                          ("config", "a//b")):
            f = Fake()
            with self.subTest(kind=kind, rel=rel), self.assertRaises(rt.Refused):
                ow.operator_list(f, image=IMAGE, root_kind=kind, run_tree=self.tree, config_dir=self.cfg,
                                 rel_dir=rel)
            self.assertEqual(f.calls, [])

    def test_the_reply_is_checked(self):
        good = list_reply([(b"a.jsonl", "file"), (b"d", "dir")])
        self.assertEqual(ow.operator_list(Fake(reply=good), image=IMAGE, root_kind="config", run_tree=self.tree,
                                          config_dir=self.cfg, rel_dir="x"), [("a.jsonl", "file"), ("d", "dir")])
        doc = json.loads(good)
        bad = {
            "hash": dict(doc, sha256="0" * 64),
            "kind": json.loads(list_reply([(b"a", "symlink")])),
            "slash": json.loads(list_reply([(b"a/b", "file")])),
            "dot": json.loads(list_reply([(b"..", "dir")])),
            "dupe": json.loads(list_reply([(b"a", "file"), (b"a", "dir")])),
            "shape": {"exists": True, "entries": doc["entries"]},
            "too-many": json.loads(list_reply([(f"f{i}".encode(), "file") for i in range(ow.LIST_MAX_ENTRIES + 1)])),
        }
        for name, reply in bad.items():
            with self.subTest(name), self.assertRaises(ow.OwnershipError):
                ow.operator_list(Fake(reply=json.dumps(reply)), image=IMAGE, root_kind="config", run_tree=self.tree,
                                 config_dir=self.cfg,
                                 rel_dir="x")
        with self.assertRaises(ow.OwnershipError):
            ow.operator_list(Fake(reply=good, fail=(self.cfg,)), image=IMAGE, root_kind="config", run_tree=self.tree,
                             config_dir=self.cfg,
                             rel_dir="x")


def census_reply(rows) -> str:
    """The census program's reply for rows [raw path bytes, kind, mode, nlink, uid, size, dev, ino, raw target or
    None], canonical as the program prints it."""
    import base64
    import hashlib
    b64 = lambda r: None if r is None else base64.b64encode(r).decode()  # noqa: E731
    out = [[b64(r[0]), *r[1:8], b64(r[8])] for r in sorted(rows, key=lambda r: r[0])]
    return json.dumps({"exists": True, "entries": out,
                       "sha256": hashlib.sha256(json.dumps(out, separators=(",", ":")).encode()).hexdigest()})


ROOT_ROW = [b".", "dir", stat.S_IFDIR | 0o700, 2, rt._uid_of(rt.AGENT_USER), 4096, 7, 1, None]


class OperatorCensus(unittest.TestCase):
    """R-C (glitch-26's ruling on lane vendor-b11, round 3): one census program, a sibling of LIST_PROGRAM, returns the
    whole config folder's lstat facts in ONE reply (kind, mode, nlink, uid, size, dev, ino, and a link's readlink
    target), never a byte of any file; O_NOFOLLOW at every level; the credential-name rule unchanged;
    LIST_MAX_ENTRIES still refuses loudly. So B11's per-turn check costs one operator container."""

    MARK = "R-C-FILE-BYTES-NEVER-IN-THE-REPLY"

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="oc-")
        self.tree = os.path.join(self.d, "tree")
        os.mkdir(self.tree)
        self.cfg = os.path.join(self.d, "cfg")
        os.mkdir(self.cfg, 0o700)
        Path(self.cfg, "config.toml").write_text(self.MARK)
        os.makedirs(os.path.join(self.cfg, "sessions", "2026", "10", "19"))
        Path(self.cfg, "sessions", "2026", "10", "19", "rollout-x.jsonl").write_text(self.MARK * 3)
        os.makedirs(os.path.join(self.cfg, "tmp", "arg0", "codex-arg0AbC123"))
        os.symlink("/usr/bin/true", os.path.join(self.cfg, "tmp", "arg0", "codex-arg0AbC123", "apply_patch"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def census_api(self):
        self.assertTrue(callable(getattr(ow, "operator_census", None)) and isinstance(
            getattr(ow, "CENSUS_PROGRAM", None), str), "R-C: ownership has no census (CENSUS_PROGRAM, operator_census)")
        return ow.operator_census

    def run_program(self, limit="4096"):
        self.census_api()
        prog = ow.CENSUS_PROGRAM.replace('"/scratch"', repr(self.cfg))
        return subprocess.run([sys.executable, "-I", "-S", "-c", prog, limit], capture_output=True, text=True,
                              timeout=60)

    def via_host(self):
        p = self.run_program()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn(self.MARK, p.stdout, "R-C: a file's bytes reached the census reply")
        return self.census_api()(Fake(reply=p.stdout), image=IMAGE, run_tree=self.tree, config_dir=self.cfg,
                                 caller_env=CALLER)

    def test_one_reply_holds_the_whole_folder_with_its_lstat_facts(self):
        got = self.via_host()
        by = {e["path"]: e for e in got}
        self.assertEqual(sorted(by), [".", "config.toml", "sessions", "sessions/2026", "sessions/2026/10",
                                      "sessions/2026/10/19", "sessions/2026/10/19/rollout-x.jsonl", "tmp",
                                      "tmp/arg0", "tmp/arg0/codex-arg0AbC123",
                                      "tmp/arg0/codex-arg0AbC123/apply_patch"])
        for rel, e in by.items():
            st = os.lstat(os.path.join(self.cfg, rel))
            self.assertEqual((e["mode"], e["nlink"], e["uid"], e["size"], e["dev"], e["ino"]),
                             (st.st_mode, st.st_nlink, st.st_uid, st.st_size, st.st_dev, st.st_ino), rel)
        self.assertEqual(by["config.toml"]["kind"], "file")
        self.assertEqual(by["sessions/2026"]["kind"], "dir")
        link = by["tmp/arg0/codex-arg0AbC123/apply_patch"]
        self.assertEqual((link["kind"], link["target"]), ("link", "/usr/bin/true"))
        self.assertTrue(all(e["target"] is None for p, e in by.items() if e["kind"] != "link"))

    def test_a_link_is_reported_never_followed(self):
        outside = os.path.join(self.d, "outside")
        os.makedirs(os.path.join(outside, "deep"))
        Path(outside, "deep", "secret.txt").write_text(self.MARK)
        os.symlink(outside, os.path.join(self.cfg, "dirlink"))
        os.mkfifo(os.path.join(self.cfg, "fifo"))
        by = {e["path"]: e for e in self.via_host()}
        self.assertEqual((by["dirlink"]["kind"], by["dirlink"]["target"]), ("link", outside))
        self.assertFalse([p for p in by if p.startswith("dirlink/")], "R-C: the census followed a link")
        self.assertEqual(by["fifo"]["kind"], "other")
        self.assertIn("O_NOFOLLOW", ow.CENSUS_PROGRAM)
        self.assertNotIn("os.read(", ow.CENSUS_PROGRAM, "R-C: the census program reads a file's bytes")

    def test_the_credential_name_rule_is_unchanged(self):
        """A credential-named entry is reported with its facts as "other" (never a file the caller may read); nothing
        below a credential-named folder is returned."""
        Path(self.cfg, "auth.json").write_text(self.MARK)
        os.chmod(os.path.join(self.cfg, "auth.json"), 0o600)
        os.makedirs(os.path.join(self.cfg, "oauth_creds.json", "inner"))
        by = {e["path"]: e for e in self.via_host()}
        st = os.lstat(os.path.join(self.cfg, "auth.json"))
        self.assertEqual(by["auth.json"]["kind"], "other")
        self.assertEqual((by["auth.json"]["mode"], by["auth.json"]["ino"]), (st.st_mode, st.st_ino))
        self.assertEqual(by["oauth_creds.json"]["kind"], "other")
        self.assertFalse([p for p in by if p.startswith("oauth_creds.json/")],
                         "R-C: the census returned a path through a credential name")

    def test_the_entry_cap_refuses_loudly(self):
        self.assertEqual(self.run_program(limit="10").returncode, 0)
        self.assertNotEqual(self.run_program(limit="9").returncode, 0, "R-C: the census truncated past its cap")
        rows = [ROOT_ROW] + [[f"f{i}".encode(), "file", stat.S_IFREG | 0o600, 1, 0, 1, 7, 10 + i, None]
                             for i in range(ow.LIST_MAX_ENTRIES + 1)]
        with self.assertRaises(ow.OwnershipError):
            self.census_api()(Fake(reply=census_reply(rows)), image=IMAGE, run_tree=self.tree, config_dir=self.cfg)

    def test_one_container_one_read_only_mount(self):
        f = Fake(reply=census_reply([ROOT_ROW]))
        got = self.census_api()(f, image=IMAGE, run_tree=self.tree, config_dir=self.cfg, caller_env=CALLER)
        self.assertEqual([e["path"] for e in got], ["."])
        runs = [strip(c) for c in f.calls if c[1:2] == ["run"]]
        self.assertEqual(len(runs), 1, "R-C: the census costs exactly one operator container")
        argv = runs[0]
        self.assertEqual(argv[:12], ["docker", "run", "--rm", "--pull=never", "--network", "none", "--user",
                                     rt.AGENT_USER, "--cap-drop", "ALL", "--security-opt", "no-new-privileges"])
        mounts = [argv[i + 1] for i, a in enumerate(argv) if a in ("--mount", "-v", "--volume")]
        self.assertEqual(mounts, [f"type=bind,source={self.cfg},target=/scratch,readonly"])
        self.assertEqual(argv[argv.index(ow.CENSUS_PROGRAM) + 1:], [str(ow.LIST_MAX_ENTRIES)])

    def test_the_reply_is_checked(self):
        good = [ROOT_ROW, [b"a", "file", stat.S_IFREG | 0o600, 1, 10001, 3, 7, 2, None],
                [b"d", "dir", stat.S_IFDIR | 0o700, 2, 10001, 4096, 7, 3, None],
                [b"d/l", "link", stat.S_IFLNK | 0o777, 1, 10001, 4, 7, 4, b"/x/y"]]
        got = self.census_api()(Fake(reply=census_reply(good)), image=IMAGE, run_tree=self.tree, config_dir=self.cfg)
        self.assertEqual([(e["path"], e["kind"], e["target"]) for e in got],
                         [(".", "dir", None), ("a", "file", None), ("d", "dir", None), ("d/l", "link", "/x/y")])
        doc = json.loads(census_reply(good))
        bad = {
            "hash": json.dumps(dict(doc, sha256="0" * 64)),
            "kind": census_reply([ROOT_ROW, [b"a", "symlink", 0, 1, 0, 1, 7, 2, None]]),
            "no-root": census_reply(good[1:]),
            "orphan": census_reply([ROOT_ROW, [b"x/a", "file", stat.S_IFREG, 1, 0, 1, 7, 2, None]]),
            "parent-not-dir": census_reply([ROOT_ROW, good[1], [b"a/b", "file", stat.S_IFREG, 1, 0, 1, 7, 9, None]]),
            "dotdot": census_reply([ROOT_ROW, [b"../a", "file", stat.S_IFREG, 1, 0, 1, 7, 2, None]]),
            "absolute": census_reply([ROOT_ROW, [b"/a", "file", stat.S_IFREG, 1, 0, 1, 7, 2, None]]),
            "dupe": census_reply([ROOT_ROW, good[1], good[1]]),
            "target-on-file": census_reply([ROOT_ROW, [b"a", "file", stat.S_IFREG, 1, 0, 1, 7, 2, b"/x"]]),
            "negative": census_reply([ROOT_ROW, [b"a", "file", stat.S_IFREG, 1, -1, 1, 7, 2, None]]),
            "bool": census_reply([ROOT_ROW, [b"a", "file", stat.S_IFREG, True, 0, 1, 7, 2, None]]),
            "shape": json.dumps({"exists": True, "entries": doc["entries"]}),
        }
        for name, reply in bad.items():
            with self.subTest(name), self.assertRaises(ow.OwnershipError, msg=f"R-C: reply {name} admitted"):
                ow.operator_census(Fake(reply=reply), image=IMAGE, run_tree=self.tree, config_dir=self.cfg)
        with self.assertRaises(ow.OwnershipError):
            ow.operator_census(Fake(reply=census_reply(good), fail=(self.cfg,)), image=IMAGE, run_tree=self.tree,
                               config_dir=self.cfg)


if __name__ == "__main__":
    unittest.main()
