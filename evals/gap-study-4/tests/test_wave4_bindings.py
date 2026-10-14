#!/usr/bin/env python3
"""The wave 4 merge bindings (the w4a, w4b and w4c briefs, "## Merge bindings", 1-8): each pair held by one lane and
taken as a parameter by another, bound by one check on the merged code.

One class per binding. Each runs its check green on the merged modules and files, then under one in-memory mutant
that changes only a pair's value, which must turn the check red. Each mutant's red run is printed (MUTANT ... red),
and the list is printed at the end.

Carried items (the lane lead's brief):
  - binding 4 also binds preflight's typed "/srv/ev" to sidecar.EVIDENCE_MOUNT; the parsed sidecar_expect carries
    no mount `type` key (w4b's W4B2-5); `cap_add` stays PENDING until the stub take;
  - binding 5 runs run_take.read_login and scan_record.read_login over the union of both lanes' planted login
    fixtures (read from their test files by ast, never imported; every value is fake, every file is planted in a
    temporary folder), plus the four cases the merge found apart (glitch-f3's ruling, a merge-time exception to lane
    w4c), plus the placement cases of the binding 5 review, round 1 (B5R1-2): a symlinked file, inside a repository,
    a repository reached through a symlinked folder, `..` after one, a plain file through a link inside a repository,
    a missing file, a relative path, and an owner case under one uid mock both readers share. The real-path walk is
    bound here on both sides (glitch-f3): a mutant that puts abspath back on either reader goes red;
  - binding 6 binds image_lock.SIDECAR_PROGRAM to sidecar.PROGRAM;
  - binding 8 binds preflight's lock keys to w4a's schema paths, and (lane w6a, CP2-preflight-2) the loader-to-
    evaluator connection: preflight reads a take's lock only through w4a's own image_lock.load and require_ready,
    for the harness's own take image, and projects exactly LOCK_KEYS from it; each committed take lock is the
    reviewed pin (glitch-06's post-write ruling, 14 Oct 2026: schema 2 and byte-equal to what ops/write_image_lock.py
    re-derives from the committed build record) and loads through it, and a filled synthetic copy reaches evaluate's
    lock contract;
  - binding 4 also binds the sidecar's parsed evidence source (sidecar.create_argv's `evidence`) to the
    evidence_dir preflight judges (lane w6a, CP2-preflight-3).

No model, no container, no network; nothing reads a real login file.
"""

# Binding 5 review, round 1: the NITs, named and not fixed (the lane lead's call).
#   B5R1-5  clause (i) is enforced twice in scan_record (the regex's 0x80-0xff and the ascii decode), so each layer
#           alone is an equivalent mutant; neither is marked as the rule or the backstop.
#   B5R1-6  test_scan_record's (iv) mutant patches the global os.path.isabs, not a module-local helper.
#   B5R1-7  the 12 w4c fixtures asked "as written" (A_LOGIN_NAME, outside ALLOWED) all stop at the name gate in
#           both readers; the 12 asked as a real login name carry the binding.
#   B5R1-8  scan_record's `allowed` refuses a frozenset (it fails closed).
#   B5R1-9  no COPIED.d reason names the merge-time edits to box/scan_record.py and its tests.

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
sys.path.insert(0, STUDY)
sys.path.insert(0, HERE)

import agent_adapter  # noqa: E402
from box import image_lock as il  # noqa: E402
from box import preflight as pf  # noqa: E402
from box import run_take as rt  # noqa: E402
from box import scan_record as sr  # noqa: E402
from box import sidecar as sc  # noqa: E402
from box import take_config as tc  # noqa: E402
from box.egress import proxy_conf as pc  # noqa: E402


def read_fixtures(test_file: str, names: tuple) -> types.SimpleNamespace:
    """The named top-level assignments of a lane's test file, read by ast and evaluated alone (only `dict` is
    reachable), never by importing it: the lane test modules start their process guards at import."""
    with open(os.path.join(HERE, test_file), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    body = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name) and n.targets[0].id in names]
    found = [n.targets[0].id for n in body]
    if sorted(found) != sorted(names):
        raise AssertionError(f"{test_file}: the fixtures {sorted(names)} are not each assigned once ({found})")
    ns: dict = {"__builtins__": {"dict": dict}}
    exec(compile(ast.Module(body=body, type_ignores=[]), test_file, "exec"), ns)
    return types.SimpleNamespace(**{k: ns[k] for k in names})


# w4b's and w4c's planted login fixtures, read only (fake values).
fixtures_b = read_fixtures("test_run_take.py", ("FAKE_VALUE", "LOGIN_REFUSALS", "LOGIN_ACCEPTED"))
fixtures_c = read_fixtures("test_scan_record.py", ("TOKEN", "GOOD", "LOGIN_FIXTURES"))

MUTANTS: list = []
IMAGE = "sha256:" + "a" * 64
RUN_TREE = "/srv/w/t1/tree"
EVIDENCE = "/srv/e/t1"


def tearDownModule():
    print("\n".join(["", f"mutants run red in this file ({len(MUTANTS)}):"] + [f"  {m}" for m in MUTANTS]))


class Binding(unittest.TestCase):
    """check() returns every way the pair departs ([] when it holds)."""

    def check(self) -> list:
        raise NotImplementedError

    def green_then_red(self, name, patcher):
        self.assertEqual(self.check(), [])
        with patcher:
            self.assertNotEqual(self.check(), [], f"mutant {name} stayed green")
        MUTANTS.append(name)
        print(f"\nMUTANT {name}: red", end=" ")


def rederived(image: str):
    """The lock writer's re-derivation of `image`'s committed lock from the committed build record (bytes), or the
    refusal's text. Imported from ops/ by path; it runs git, read-only."""
    import importlib.util
    repo = os.path.dirname(os.path.dirname(STUDY))
    spec = importlib.util.spec_from_file_location("write_image_lock_for_bindings",
                                                  os.path.join(repo, "ops", "write_image_lock.py"))
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    record = os.path.join(repo, "lane-reports", "build-20261014c", "athena-out-20261014", "build-record.json")
    path = os.path.join(il.BOX_DIR, os.path.dirname(il.DOCKERFILES[image]), "image.lock")
    try:
        return w.rederive(il, repo, record, path, image)
    except (w.Refused, il.LockError, ValueError, OSError, __import__("subprocess").TimeoutExpired) as e:
        return f"refused: {type(e).__name__}: {e}"


RECORD_SHA256 = "c55c75cc7bffea5c202a19bc25e1a9f8490e4c22975e6248486008b96bd65914"   # the reviewed build record


def lock_bytes(image: str) -> bytes:
    """The committed lock file's bytes (the binding 8 pin mutants replace this read)."""
    with open(os.path.join(il.BOX_DIR, os.path.dirname(il.DOCKERFILES[image]), "image.lock"), "rb") as fh:
        return fh.read()


def _pin_text(lock: dict) -> bytes:
    return (json.dumps(lock, indent=1, sort_keys=True) + "\n").encode()


def _edited_digest(image: str) -> bytes:
    lock = json.loads(_REAL_LOCK_BYTES(image))
    d = lock["manifest_digest"]
    lock["manifest_digest"] = d[:-1] + ("0" if d[-1] != "0" else "1")
    return _pin_text(lock)


def _another_row(image: str) -> bytes:
    repo = os.path.dirname(os.path.dirname(STUDY))
    with open(os.path.join(repo, "lane-reports", "build-20261014c", "athena-out-20261014", "build-record.json"),
              encoding="utf-8") as fh:
        rows = {r["image"]: r for r in json.load(fh)["images"]}
    other = rows["take-o" if image != "take-o" else "take-a"]
    lock = json.loads(_REAL_LOCK_BYTES(image))
    lock.update({k: other[k] for k in ("image_id", "manifest_digest", "config_digest")})
    return _pin_text(lock)


def _unfilled(image: str) -> bytes:
    lock = {k: v for k, v in json.loads(_REAL_LOCK_BYTES(image)).items() if k not in il.SCHEMA_2_KEYS}
    lock.update(schema=il.SCHEMA, base=il.PENDING, image_id=il.PENDING,
                pending={"base": "synthetic", "image_id": "synthetic"})
    return _pin_text(lock)


_REAL_LOCK_BYTES = lock_bytes


def locks() -> dict:
    return {n: il.load(os.path.join(il.BOX_DIR, os.path.dirname(il.DOCKERFILES[n]), "image.lock")) for n in il.IMAGES}


def dockerfile(image: str) -> list:
    with open(os.path.join(il.BOX_DIR, il.DOCKERFILES[image]), encoding="utf-8") as fh:
        return il.parse_dockerfile(fh.read())


def path_get(doc, dotted):
    for part in dotted.split("."):
        if not isinstance(doc, dict) or part not in doc:
            raise KeyError(dotted)
        doc = doc[part]
    return doc


# ------------------------------------------------------------------------------------------------ binding 1
class TestBinding1Users(Binding):
    def check(self):
        out = []
        with_users = {n: lk for n, lk in locks().items() if lk["users"] is not None}
        if sorted(with_users) != sorted(il.TAKE_IMAGES + (il.SIDECAR_IMAGE,)):
            out.append(f"the locks with users are {sorted(with_users)}")
        default_user = inspect.signature(sc.create_argv).parameters["user"].default
        for n, lk in with_users.items():
            u = lk["users"]
            pairs = (("agent", f"{u['agent']['uid']}:{u['agent']['gid']}", rt.AGENT_USER),
                     ("keepalive", f"{u['keepalive']['uid']}:{u['keepalive']['gid']}", rt.KEEPALIVE_USER),
                     ("watcher", f"{u['watcher']['uid']}:{u['watcher']['gid']}", f"{pf.WATCHER_UID}:{pf.WATCHER_UID}"),
                     ("watcher (sidecar default)", f"{u['watcher']['uid']}:{u['watcher']['gid']}", default_user))
            out += [f"{n}: users.{role} {got} != {want}" for role, got, want in pairs if got != want]
            users = [i.args for i in dockerfile(n) if i.keyword == "USER"]
            want_user = rt.AGENT_USER if n in il.TAKE_IMAGES else default_user
            if users[-1:] != [want_user]:
                out.append(f"{n}: the Dockerfile's last USER is {users[-1:]}, not {want_user}")
        if pf.AGENT_UID != int(rt.AGENT_USER.split(":")[0]) or pf.KEEPALIVE_UID != int(rt.KEEPALIVE_USER.split(":")[0]):
            out.append("preflight's agent or keep-alive uid is not run_take's")
        return out

    def test_binding_1(self):
        self.green_then_red("binding 1: run_take.AGENT_USER moved off the locks",
                            mock.patch.object(rt, "AGENT_USER", "10009:10009"))


# ------------------------------------------------------------------------------------------------ binding 2
class TestBinding2Hosts(Binding):
    def check(self):
        out = []
        keys = set(pc.HOSTS)
        for what, other in (("run_take.HARNESS_ENV", rt.HARNESS_ENV), ("run_take.LOGIN_VARIABLE", rt.LOGIN_VARIABLE),
                            ("take_config.WRITERS", tc.WRITERS)):
            if set(other) != keys:
                out.append(f"{what} keys {sorted(other)} != proxy_conf.HOSTS keys {sorted(keys)}")
        try:
            for h in sorted(keys):
                want = list(pf.BLOCKED_NAMES) + sorted(v for k, v in pc.HOSTS.items() if k != h)
                if pf.refused_names(h, pc.HOSTS) != want:
                    out.append(f"{h}: preflight's refused names are not derived from HOSTS")
                if pf._check_hosts(pc.HOSTS)[h] != pc.host_for(h):
                    out.append(f"{h}: preflight's allowed host is not proxy_conf's")
        except Exception as e:  # a refusal of HOSTS by preflight is a broken pair
            out.append(f"preflight refuses proxy_conf.HOSTS ({type(e).__name__}: {e})")
        return out

    def test_binding_2(self):
        self.green_then_red("binding 2: take_config.WRITERS gains a harness HOSTS lacks",
                            mock.patch.object(tc, "WRITERS", dict(tc.WRITERS, other=None)))


# ------------------------------------------------------------------------------------------------ binding 3
class TestBinding3Proxy(Binding):
    def check(self):
        out = []
        if pc.PROXY_URL != rt.PROXY_URL:
            out.append(f"PROXY_URL {pc.PROXY_URL} != {rt.PROXY_URL}")
        if pc.ALIAS != rt.PROXY_ALIAS:
            out.append(f"ALIAS {pc.ALIAS} != {rt.PROXY_ALIAS}")
        if rt.PROXY_URL != f"http://{pc.ALIAS}:{pc.PORT}" or pf._proxy_port() != str(pc.PORT):
            out.append(f"the proxy URL or preflight's port is not proxy_conf's PORT {pc.PORT}")
        with open(pc.TEMPLATE_PATH, encoding="utf-8") as fh:
            ports = [args for _, d, args in pc.parse(fh.read()) if d == "http_port"]
        if ports != [[str(pc.PORT)]]:
            out.append(f"proxy.conf listens on {ports}, not {pc.PORT}")
        # USER is FILLED (13:13, 14 Oct 2026); while it is PENDING both sides refuse (kept red-tested by patching it back).
        with mock.patch.object(pc, "USER", pc.PENDING):
            with self.assertRaises(pc.NotReady):
                pc.launch_fields()
            pending_launch = rt.ProxyLaunch(image=IMAGE, conf_source="/srv/w/t1/proxy.conf",
                                            conf_target=pc.CONF_PATH, command=pc.COMMAND, user=pc.USER,
                                            alias=pc.ALIAS)
            with self.assertRaises(rt.NotReady):
                rt.proxy_create_argv("b" * 64, pending_launch)
        if pc.launch_fields()["user"] != "13:13":
            out.append("the committed USER is not squid's measured 13:13")
        # The drive step puts launch_fields() into ProxyLaunch: with USER filled in memory only, every field lands.
        with mock.patch.object(pc, "USER", "13:13"):
            fields = pc.launch_fields()
            names = {f.name for f in dataclasses.fields(rt.ProxyLaunch)}
            if not set(fields) <= names:
                out.append(f"launch_fields {sorted(fields)} are not ProxyLaunch fields")
                return out
            launch = rt.ProxyLaunch(image=IMAGE, conf_source="/srv/w/t1/proxy.conf", **fields)
            argv = rt.proxy_create_argv("b" * 64, launch)
        if (launch.conf_target, launch.command, launch.user) != (pc.CONF_PATH, pc.COMMAND, "13:13"):
            out.append("ProxyLaunch does not carry CONF_PATH, COMMAND and USER")
        if f"target={pc.CONF_PATH}" not in ",".join(argv) or argv[-len(pc.COMMAND):] != list(pc.COMMAND) \
                or argv[argv.index("--user") + 1] != "13:13":
            out.append("the proxy's create argv does not carry CONF_PATH, COMMAND and USER")
        return out

    def test_binding_3(self):
        self.green_then_red("binding 3: proxy_conf.PORT moved off proxy.conf and PROXY_URL",
                            mock.patch.object(pc, "PORT", 3129))


# ------------------------------------------------------------------------------------------------ binding 4
class TestBinding4SidecarExpect(Binding):
    # The registered boot set's inspect spellings (the statically accepted, measured setpriv delta; review
    # review-box-witness-locks.md B-3, 14 Oct, glitch-06's narrow ownership extension): what fills cap_add in memory.
    FILL = list(sc.BOOT_INSPECT_CAPABILITIES)

    def expect(self):
        return sc.expect_from_argv(sc.create_argv(image=IMAGE, run_tree=RUN_TREE, evidence=EVIDENCE,
                                                  watch=["out/result.txt", "notes.md"]))

    def check(self):
        out = []
        if pf.SIDECAR_EVIDENCE_MOUNT != sc.EVIDENCE_MOUNT:
            out.append(f"preflight's {pf.SIDECAR_EVIDENCE_MOUNT} != sidecar.EVIDENCE_MOUNT {sc.EVIDENCE_MOUNT}")
        exp = self.expect()
        if set(exp) != set(pf.SIDECAR_EXPECT_KEYS):
            out.append(f"the parsed expectation names {sorted(exp)}, not {sorted(pf.SIDECAR_EXPECT_KEYS)}")
            return out
        for m in exp["mounts"]:
            if "type" in m:
                out.append("a parsed mount carries `type` (W4B2-5)")
            if not set(m) <= set(pf._MOUNT_FIELDS):
                out.append(f"a parsed mount names {sorted(m)}, outside preflight's mount fields")
        if exp["cap_add"] != [rt.PENDING] * len(sc.BOOT_CAPABILITIES):
            out.append(f"cap_add is {exp['cap_add']}, not one PENDING per boot capability "
                       f"(PENDING until the stub take)")
        spec = types.SimpleNamespace(run_tree=RUN_TREE)
        # As parsed: preflight's check refuses only on the PENDING cap_add.
        try:
            pf._check_sidecar({}, spec, None, None, None, exp, EVIDENCE)
            out.append("preflight passed a sidecar expectation that holds PENDING")
        except pf._Fail as e:
            if str(e) != "sidecar_expect PENDING: cap_add":
                out.append(f"as parsed, preflight refuses for another reason: {e}")
        # With cap_add filled in memory, every field rule passes: the check reaches the inspect probe.
        try:
            pf._check_sidecar({}, spec, None, None, None, dict(exp, cap_add=list(self.FILL)), EVIDENCE)
            out.append("preflight passed without the sidecar inspect")
        except pf._Fail as e:
            if str(e) != "probe sidecar-inspect is missing":
                out.append(f"a field of the parsed expectation fails preflight: {e}")
        # Lane w6a: the parsed evidence source is the folder preflight judges; any other folder fails before the
        # inspect is read.
        try:
            pf._check_sidecar({}, spec, None, None, None, dict(exp, cap_add=list(self.FILL)), "/srv/e/t2")
            out.append("preflight passed a sidecar whose evidence source is not the judged folder")
        except pf._Fail as e:
            if "evidence" not in str(e) or str(e) == "probe sidecar-inspect is missing":
                out.append(f"another evidence folder fails for another reason: {e}")
        return out

    def test_binding_4(self):
        self.green_then_red("binding 4: sidecar.EVIDENCE_MOUNT moved off preflight's /srv/ev",
                            mock.patch.object(sc, "EVIDENCE_MOUNT", "/srv/ex"))

    def test_binding_4_boot_set(self):
        self.green_then_red("binding 4: the filled boot set gains a fifth capability",
                            mock.patch.object(type(self), "FILL", self.FILL + ["CAP_SYS_ADMIN"]))
        self.green_then_red("binding 4: the filled boot set drops SETPCAP",
                            mock.patch.object(type(self), "FILL", [c for c in self.FILL if c != "CAP_SETPCAP"]))


# ------------------------------------------------------------------------------------------------ binding 5
NAME = rt.LOGIN_VARIABLE[rt.CLAUDE_CODE]
ALLOWED = tuple(rt.LOGIN_VARIABLE.values())


def login_fixtures() -> dict:
    """The union of both lanes' planted fixtures, as {label: (asked name, body, mode, relative)}."""
    out = {}
    fb = fixtures_b
    for k, v in fb.LOGIN_ACCEPTED.items():
        out[f"w4b:{k}"] = (NAME, f"{NAME}={v}\n", 0o600, False)
    for k, kw in fb.LOGIN_REFUSALS.items():
        out[f"w4b:{k}"] = (NAME, kw.get("text", f"{NAME}={fb.FAKE_VALUE}\n"), kw.get("mode", 0o600), False)
    fc = fixtures_c
    for k, (body, mode, _ok) in fc.LOGIN_FIXTURES.items():
        out[f"w4c:{k} (as written)"] = (fc.GOOD, body, mode, False)
        out[f"w4c:{k} (as {NAME})"] = (NAME, body.replace(fc.GOOD, NAME), mode, False)
    head = f"{NAME}="
    # The four cases the merge found apart (glitch-f3's ruling), and their edges.
    out["case i: non-ASCII value"] = (NAME, f"{NAME}={fb.FAKE_VALUE}é\n", 0o600, False)
    out["case i: unit separator 0x1f"] = (NAME, f"{NAME}={fb.FAKE_VALUE}\x1f\n", 0o600, False)
    out["case i: control 0x01"] = (NAME, f"{NAME}={fb.FAKE_VALUE}\x01\n", 0o600, False)
    out["case ii: a name outside the allowed"] = ("A_LOGIN_NAME", f"A_LOGIN_NAME={fb.FAKE_VALUE}\n", 0o600, False)
    out["case iii: exactly 4096 bytes"] = (NAME, head + "F" * (4096 - len(head) - 1) + "\n", 0o600, False)
    out["case iii: 4097 bytes"] = (NAME, head + "F" * (4096 - len(head)) + "\n", 0o600, False)
    out["case iv: a relative path"] = (NAME, f"{NAME}={fb.FAKE_VALUE}\n", 0o600, True)
    return out


class TestBinding5Login(Binding):
    def outcome(self, fn, errors, path, name):
        try:
            return ("accept", fn(path, name))
        except errors:
            return ("refuse", None)

    def agree(self, label, path, name) -> list:
        b = self.outcome(rt.read_login, rt.LoginRefused, path, name)
        c = self.outcome(lambda q, n: sr.read_login(q, n, allowed=ALLOWED), sr.LoginError, path, name)
        return [] if b == c else [f"{label}: run_take {b[0]}, scan_record {c[0]}"]

    def placement(self) -> list:
        """B5R1-2: where the file sits and who owns it, both readers on each case."""
        out = []
        good = f"{NAME}={fixtures_b.FAKE_VALUE}\n"
        with tempfile.TemporaryDirectory(prefix="w-") as d:
            def plant(folder):
                os.makedirs(folder, exist_ok=True)
                p = os.path.join(folder, "f.line")
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(good)
                os.chmod(p, 0o600)
                return p
            plain = plant(os.path.join(d, "plain"))
            repo = os.path.join(d, "repo")
            os.makedirs(os.path.join(repo, ".git"))
            inside = plant(os.path.join(repo, "sub"))
            os.symlink(plain, os.path.join(d, "link.line"))
            os.symlink(os.path.join(repo, "sub"), os.path.join(d, "lnk"))
            os.symlink(os.path.join(d, "plain"), os.path.join(repo, "out"))
            cases = {"a plain file": (plain, "accept"),
                     "a symlinked file": (os.path.join(d, "link.line"), "refuse"),
                     "inside a repository": (inside, "refuse"),
                     "a repository through a symlinked folder": (os.path.join(d, "lnk", "f.line"), "refuse"),
                     "`..` after a symlinked folder": (os.path.join(d, "lnk", "..", "sub", "f.line"), "refuse"),
                     "a plain file through a link inside a repository": (os.path.join(repo, "out", "f.line"), "accept"),
                     "a missing file": (os.path.join(d, "nope.line"), "refuse"),
                     "a relative path": (os.path.relpath(plain), "refuse")}
            for label, (path, want) in cases.items():
                out += self.agree(f"placement: {label}", path, NAME)
                got = self.outcome(rt.read_login, rt.LoginRefused, path, NAME)[0]
                if got != want:
                    out.append(f"placement: {label}: run_take {got}, expected {want} (the case does not bite)")
            real = os.getuid()
            if rt.os is not sr.os:
                out.append("the two readers do not share one os module, so one uid mock cannot reach both")
            with mock.patch.object(os, "getuid", lambda: real + 1):
                out += self.agree("owner: another uid", plain, NAME)
                if self.outcome(rt.read_login, rt.LoginRefused, plain, NAME)[0] != "refuse":
                    out.append("owner: another uid: run_take accepted (the mock does not bite)")
        return out

    def check(self):
        out = []
        fixtures = login_fixtures()
        if len([k for k in fixtures if k.startswith("w4b:")]) != 15 or len(fixtures_c.LOGIN_FIXTURES) != 12:
            out.append("the union is not w4b's 15 and w4c's 12 planted fixtures")
        for k, kw in fixtures_b.LOGIN_REFUSALS.items():
            if not set(kw) <= {"text", "mode"}:
                out.append(f"w4b:{k} uses {sorted(set(kw) - {'text', 'mode'})}, which the union does not read")
        out += self.placement()
        with tempfile.TemporaryDirectory(prefix="w-") as d:
            for i, (label, (name, body, mode, relative)) in enumerate(sorted(fixtures.items())):
                p = os.path.join(d, f"f{i}.line")
                with open(p, "wb") as fh:
                    fh.write(body.encode("utf-8"))
                os.chmod(p, mode)
                if relative:
                    p = os.path.relpath(p)
                out += self.agree(label, p, name)
        return out

    def test_the_union_holds_both_outcomes(self):
        self.assertEqual(self.check(), [])
        kinds = set()
        with tempfile.TemporaryDirectory(prefix="w-") as d:
            for i, (name, body, mode, relative) in enumerate(login_fixtures().values()):
                p = os.path.join(d, f"g{i}.line")
                with open(p, "wb") as fh:
                    fh.write(body.encode("utf-8"))
                os.chmod(p, mode)
                kinds.add(self.outcome(rt.read_login, rt.LoginRefused, os.path.relpath(p) if relative else p, name)[0])
        self.assertEqual(kinds, {"accept", "refuse"})

    def test_binding_5(self):
        self.green_then_red("binding 5: scan_record's login cap back at 64 KiB",
                            mock.patch.object(sr, "LOGIN_MAX_BYTES", 1 << 16))

    def test_binding_5_real_path_on_both_sides(self):
        """glitch-f3: the real-path walk is bound here, so a change on either side shows."""
        self.green_then_red("binding 5: abspath back in scan_record's repository walk",
                            mock.patch.object(sr, "_real_path", os.path.abspath))
        self.green_then_red("binding 5: abspath back in run_take's repository walk",
                            mock.patch.object(rt, "outside_every_repository", lexical_outside_every_repository))


def lexical_outside_every_repository(path: str) -> bool:
    """run_take.outside_every_repository with abspath in place of realpath: the mutant's body, nothing else changed."""
    p = os.path.abspath(path)
    cur = p if os.path.isdir(p) else os.path.dirname(p)
    while True:
        if os.path.lexists(os.path.join(cur, ".git")):
            return False
        parent = os.path.dirname(cur)
        if parent == cur:
            return True
        cur = parent


# ------------------------------------------------------------------------------------------------ binding 6
class TestBinding6Program(Binding):
    def check(self):
        out = []
        copies = [i.args for i in dockerfile(il.SIDECAR_IMAGE) if i.keyword == "COPY"]
        if len(copies) != 1 or copies[0].split()[-1] != sc.PROGRAM:
            out.append(f"the sidecar Dockerfile copies to {copies}, not {sc.PROGRAM}")
        if il.SIDECAR_PROGRAM != sc.PROGRAM:
            out.append(f"image_lock.SIDECAR_PROGRAM {il.SIDECAR_PROGRAM} != sidecar.PROGRAM {sc.PROGRAM}")
        if copies != [il.SIDECAR_COPY]:
            out.append("the Dockerfile's COPY is not image_lock.SIDECAR_COPY")
        argv = sc.create_argv(image=IMAGE, run_tree=RUN_TREE, evidence="/srv/e/t1", watch=["a"])
        if sc.PROGRAM not in argv:
            out.append("the sidecar's create argv does not run sidecar.PROGRAM")
        return out

    def test_binding_6(self):
        self.green_then_red("binding 6: sidecar.PROGRAM moved off the Dockerfile's copy target",
                            mock.patch.object(sc, "PROGRAM", "/opt/w/other.py"))


# ------------------------------------------------------------------------------------------------ binding 7
C3 = {"UNREADABLE_CONSEQUENTIAL_KEY": "unreadable_consequential",
      "UNREADABLE_CONSEQUENTIAL_ROW": "unreadable-consequential-path",
      "QUIESCENCE_CAP_SURVIVORS_KEY": "quiescence_cap_survivors",
      "QUIESCENCE_CAP_ROW": "quiescence-cap-reached"}
# Which CP2 module holds which mirror today (a module holding none says so in its lane report).
HOLDERS = {"run_take": (rt, ("QUIESCENCE_CAP_SURVIVORS_KEY", "QUIESCENCE_CAP_ROW")),
           "preflight": (pf, ("UNREADABLE_CONSEQUENTIAL_KEY", "UNREADABLE_CONSEQUENTIAL_ROW")),
           "sidecar": (sc, ("UNREADABLE_CONSEQUENTIAL_KEY", "UNREADABLE_CONSEQUENTIAL_ROW")),
           "take_config": (tc, ()), "scan_record": (sr, ())}


class TestBinding7RoutingNames(Binding):
    def check(self):
        out = []
        with open(os.path.join(STUDY, "routing.json"), encoding="utf-8") as fh:
            rows = {r["id"] for r in json.load(fh)["rows"]}
        for const, value in C3.items():
            where = set(agent_adapter.BOX_KEYS) if const.endswith("_KEY") else rows
            if value not in where:
                out.append(f"w4h does not hold {value}")
        for mod_name, (mod, held) in HOLDERS.items():
            for const in C3:
                has = hasattr(mod, const)
                if has != (const in held):
                    out.append(f"{mod_name}: holds {const} is {has}, expected {const in held}")
                if has and getattr(mod, const) != C3[const]:
                    out.append(f"{mod_name}.{const} {getattr(mod, const)!r} != w4h's {C3[const]!r}")
        if C3["UNREADABLE_CONSEQUENTIAL_KEY"] not in sc.REPLY_FIELDS:
            out.append("the sidecar's reply field is not spelled unreadable_consequential")
        return out

    def test_binding_7(self):
        self.green_then_red("binding 7: preflight's C3 key respelled",
                            mock.patch.object(pf, "UNREADABLE_CONSEQUENTIAL_KEY", "unreadable-consequential"))


# ------------------------------------------------------------------------------------------------ binding 8
class TestBinding8LockKeys(Binding):
    """Key paths, then (lane w6a, CP2-preflight-2) the real loader-to-evaluator connection: preflight.load_take_lock
    reads through w4a's image_lock.load and require_ready, for the harness's own take image, and projects exactly
    LOCK_KEYS by their schema paths."""

    def loader(self) -> list:
        out = []
        if pf.image_lock is not il:
            out.append("preflight's image_lock is not w4a's module")
        if set(pf.TAKE_IMAGE) != set(rt.LOGIN_VARIABLE) or sorted(pf.TAKE_IMAGE.values()) != sorted(il.TAKE_IMAGES):
            out.append(f"preflight's TAKE_IMAGE {pf.TAKE_IMAGE} does not pair every harness with one take image")
        for h, image in pf.TAKE_IMAGE.items():
            if il.HARNESS_PACKAGES.get(image, "").split("/")[-1] not in (h, h + "-cli"):
                out.append(f"{h}: {image}'s package {il.HARNESS_PACKAGES.get(image)} is not that harness")
        loaded = locks()
        # Closure C-1: the record the pins re-derive from is the reviewed one, so this module holds on its own.
        import hashlib
        repo = os.path.dirname(os.path.dirname(STUDY))
        record = os.path.join(repo, "lane-reports", "build-20261014c", "athena-out-20261014", "build-record.json")
        with open(record, "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != RECORD_SHA256:
                out.append("the committed build record is not the reviewed one (sha256 c55c75cc...)")
        for h, image in sorted(pf.TAKE_IMAGE.items()):
            path = os.path.join(il.BOX_DIR, os.path.dirname(il.DOCKERFILES[image]), "image.lock")
            # The committed lock is the reviewed pin: schema 2, byte-equal to the lock writer's re-derivation from
            # the committed build record, and preflight's loader projects exactly its schema paths.
            text = lock_bytes(image)
            if json.loads(text).get("schema") != il.SCHEMA_2 or text != rederived(image):
                out.append(f"{h}: the committed {image} lock is not the reviewed pin re-derived from the record")
            try:
                projected = pf.load_take_lock(path, harness=h)
                if projected != {k: path_get(loaded[image], k) for k in pf.LOCK_KEYS}:
                    out.append(f"{h}: the committed {image} lock projects {projected}")
            except Exception as e:
                out.append(f"{h}: the committed {image} lock refused ({type(e).__name__}: {e})")
            # a filled lock is schema 2, as the lock writer writes it (lock-writer rulings, 14 Oct 2026)
            filled = dict(loaded[image], base="registry.example/fake-base@sha256:" + "a" * 64, image_id=IMAGE,
                          python="3.12.99", harness=dict(loaded[image]["harness"], version="9.8.7"), pending={},
                          schema=il.SCHEMA_2, manifest_digest="sha256:" + "c" * 64,
                          config_digest="sha256:" + "d" * 64, source_commit="e" * 40)
            with tempfile.TemporaryDirectory(prefix="w-") as d:
                p = os.path.join(d, os.path.dirname(il.DOCKERFILES[image]), "image.lock")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as fh:
                    json.dump(filled, fh)
                with mock.patch.object(il, "BOX_DIR", d):
                    try:
                        got = pf.load_take_lock(p, harness=h)
                    except Exception as e:
                        out.append(f"{h}: a filled {image} lock refused ({type(e).__name__}: {e})")
                        continue
            want = {k: path_get(filled, k) for k in pf.LOCK_KEYS}
            if got != want:
                out.append(f"{h}: projected {got}, not the schema paths' {want}")
            spec = rt.TakeSpec(image=IMAGE, run_tree=RUN_TREE, config_dir="/srv/w/t1/cfg", network="b" * 64,
                               memory_reservation=512, memory=1536, cpus="1", pids_limit=64)
            try:
                rec = pf.evaluate({}, spec=spec, lock=got, sidecar_expect={}, harness=h, hosts=pc.HOSTS,
                                  evidence_dir=EVIDENCE,
                                  sidecar_lock={"image_id": IMAGE, "manifest_digest": "sha256:" + "5" * 64},
                                  egress_lock={"image_id": IMAGE, "manifest_digest": "sha256:" + "7" * 64})
                if rec["ok"] or [c["id"] for c in rec["checks"]] != list(pf.PREFLIGHT_CHECKS):
                    out.append(f"{h}: evaluate over no probes is not a full failing record")
            except Exception as e:
                out.append(f"{h}: evaluate refuses the projected lock ({type(e).__name__}: {e})")
        return out

    def check(self):
        out = self.loader()
        loaded = locks()
        for key in pf.LOCK_KEYS:
            top = key.split(".")[0]
            if top not in il.KEYS and top not in il.SCHEMA_2_KEYS:
                out.append(f"{key}: {top} is not a key of w4a's schema")
            for n in il.TAKE_IMAGES:
                try:
                    v = path_get(loaded[n], key)
                except KeyError:
                    out.append(f"{n}: {key} is not a path of its lock")
                    continue
                if key.endswith(".uid") and not (isinstance(v, int) and not isinstance(v, bool)):
                    out.append(f"{n}: {key} is not an int")
                if not key.endswith(".uid") and not isinstance(v, str):
                    out.append(f"{n}: {key} is not a string")
        for key in ("image_id", "harness.version"):
            if key in pf.LOCK_KEYS and key not in il.PENDABLE:
                out.append(f"{key} is not one of w4a's pendable fields")
        return out

    def test_binding_8(self):
        self.green_then_red("binding 8: preflight reads a lock key w4a's schema lacks",
                            mock.patch.object(pf, "LOCK_KEYS", pf.LOCK_KEYS[:-1] + ("users.keepalive.name",)))

    def test_binding_8_loader(self):
        """Lane w6a: the loader-to-evaluator connection, red when preflight pairs a harness with another image."""
        self.green_then_red("binding 8: preflight pairs claude-code with the codex take image",
                            mock.patch.object(pf, "TAKE_IMAGE", dict(pf.TAKE_IMAGE, **{rt.CLAUDE_CODE: "take-o"})))
        self.green_then_red("binding 8: preflight projects a key the lock does not carry",
                            mock.patch.object(pf, "LOCK_KEYS", pf.LOCK_KEYS + ("users.keepalive.name",)))
        # The post-write ruling: a pin that is not the lock writer's re-derivation goes red.
        for name, fake in (("a lock hand-edited by one digest", _edited_digest),
                           ("a lock from a different record row", _another_row),
                           ("a schema-1 PENDING lock where a filled one is required", _unfilled)):
            self.green_then_red(f"binding 8: {name}", mock.patch(__name__ + ".lock_bytes", fake))
        self.green_then_red("binding 8: a record other than the reviewed one",
                            mock.patch(__name__ + ".RECORD_SHA256", "0" * 64))


# Lane w6a, criterion 7: every test of this module at the base 89b54db4 (Ran 10, OK) still exists and runs.
BASE_TESTS = ("TestBinding1Users.test_binding_1", "TestBinding2Hosts.test_binding_2",
              "TestBinding3Proxy.test_binding_3",
              "TestBinding4SidecarExpect.test_binding_4", "TestBinding5Login.test_binding_5",
              "TestBinding5Login.test_binding_5_real_path_on_both_sides",
              "TestBinding5Login.test_the_union_holds_both_outcomes", "TestBinding6Program.test_binding_6",
              "TestBinding7RoutingNames.test_binding_7", "TestBinding8LockKeys.test_binding_8")


class TestNothingDropped(unittest.TestCase):
    def test_every_base_binding_still_runs(self):
        names = {f"{c.__name__}.{n}" for c in Binding.__subclasses__() for n in dir(c) if n.startswith("test_")}
        self.assertEqual([b for b in BASE_TESTS if b not in names], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
