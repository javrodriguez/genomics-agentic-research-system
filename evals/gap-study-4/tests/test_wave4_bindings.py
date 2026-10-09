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
    temporary folder),
    plus the four cases the merge found apart (glitch-f3's ruling, a merge-time exception to lane w4c);
  - binding 6 binds image_lock.SIDECAR_PROGRAM to sidecar.PROGRAM;
  - binding 8 binds preflight's lock keys to w4a's schema paths only: preflight does not yet read the locks through
    image_lock.load. Binding 8: load wiring is CP2's first sequential lane.

No model, no container, no network; nothing reads a real login file.
"""

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
        # USER is PENDING on both sides until a built egress image tells it: both refuse.
        with self.assertRaises(pc.NotReady):
            pc.launch_fields()
        pending_launch = rt.ProxyLaunch(image=IMAGE, conf_source="/srv/w/t1/proxy.conf", conf_target=pc.CONF_PATH,
                                        command=pc.COMMAND, user=pc.USER, alias=pc.ALIAS)
        with self.assertRaises(rt.NotReady):
            rt.proxy_create_argv("b" * 64, pending_launch)
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
    def expect(self):
        return sc.expect_from_argv(sc.create_argv(image=IMAGE, run_tree=RUN_TREE, evidence="/srv/e/t1",
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
        if exp["cap_add"] != [rt.PENDING]:
            out.append(f"cap_add is {exp['cap_add']}, not one PENDING (PENDING until the stub take)")
        spec = types.SimpleNamespace(run_tree=RUN_TREE)
        # As parsed: preflight's check refuses only on the PENDING cap_add.
        try:
            pf._check_sidecar({}, spec, None, None, None, exp)
            out.append("preflight passed a sidecar expectation that holds PENDING")
        except pf._Fail as e:
            if str(e) != "sidecar_expect PENDING: cap_add":
                out.append(f"as parsed, preflight refuses for another reason: {e}")
        # With cap_add filled in memory, every field rule passes: the check reaches the inspect probe.
        try:
            pf._check_sidecar({}, spec, None, None, None, dict(exp, cap_add=["DAC_READ_SEARCH"]))
            out.append("preflight passed without the sidecar inspect")
        except pf._Fail as e:
            if str(e) != "probe sidecar-inspect is missing":
                out.append(f"a field of the parsed expectation fails preflight: {e}")
        return out

    def test_binding_4(self):
        self.green_then_red("binding 4: sidecar.EVIDENCE_MOUNT moved off preflight's /srv/ev",
                            mock.patch.object(sc, "EVIDENCE_MOUNT", "/srv/ex"))


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

    def check(self):
        out = []
        fixtures = login_fixtures()
        if len([k for k in fixtures if k.startswith("w4b:")]) != 15 or len(fixtures_c.LOGIN_FIXTURES) != 12:
            out.append("the union is not w4b's 15 and w4c's 12 planted fixtures")
        with tempfile.TemporaryDirectory(prefix="w-") as d:
            for i, (label, (name, body, mode, relative)) in enumerate(sorted(fixtures.items())):
                p = os.path.join(d, f"f{i}.line")
                with open(p, "wb") as fh:
                    fh.write(body.encode("utf-8"))
                os.chmod(p, mode)
                if relative:
                    p = os.path.relpath(p)
                b = self.outcome(rt.read_login, rt.LoginRefused, p, name)
                c = self.outcome(lambda q, n: sr.read_login(q, n, allowed=ALLOWED), sr.LoginError, p, name)
                if b != c:
                    out.append(f"{label}: run_take {b[0]}, scan_record {c[0]}")
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
    """Key paths only. Binding 8: load wiring is CP2's first sequential lane (preflight does not yet call
    image_lock.load)."""

    def check(self):
        out = []
        loaded = locks()
        for key in pf.LOCK_KEYS:
            top = key.split(".")[0]
            if top not in il.KEYS:
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
