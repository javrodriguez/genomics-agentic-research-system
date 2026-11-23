#!/usr/bin/env python3
"""test_egress.py: the egress proxy's configuration (box/egress/proxy_conf.py and proxy.conf), with no proxy at all.

Nothing here builds the egress image or starts squid; `squid -k parse` on a built image is a real-box check. A
module-level guard (interface 10) makes every process start and every signal raise for the whole module, armed right
after the one read of round 3's leak words (interface 16).

"Exactly one allowed host per take, its arm's" (D8 B2 item 8): each harness's rendered configuration allows exactly
its own host, and every mutant of MUTANT_CONFS is refused by `check`. Run alone, the module first prints every mutant
with its red run, then runs the tests.
"""

from __future__ import annotations

import inspect as pyinspect
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))
# Round 3's done commit (copy_manifest.SOURCE_COMMIT), where its leak words are read.
ROUND3 = "e2979b3143081824aadea73523ec41af30c1ddb1"
# The lane lead's additions to round 3's leak words (interface 16).
ADDED_LEAK_WORDS = ("gap4", "round 4", "sidecar", "watcher", "evidence", "holdout", "sealed", "probe", "trap",
                    "grader")


def _round3_leak_words() -> tuple:
    """Round 3's `leak_words`, read once with git show (the only process this module starts), never written down."""
    out = subprocess.run(["git", "-C", REPO, "show", f"{ROUND3}:evals/gap-study-3/prereg.json"],
                         capture_output=True, text=True, check=True).stdout
    words = json.loads(out)["leak_words"]
    if not words or not all(isinstance(w, str) and w for w in words):
        raise AssertionError("round 3's leak_words is not a non-empty list of words")
    return tuple(words)


LEAK_WORDS = _round3_leak_words() + ADDED_LEAK_WORDS


# Interface 10: from here on no test can start a process or signal one.
def _blocked(*_a, **_k):
    raise AssertionError("process start or signal blocked in the box tests")


_GUARDED = [(subprocess, "run"), (subprocess, "Popen")]
_GUARDED += [(os, n) for n in ("system", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork") if hasattr(os, n)]
_GUARDED += [(os, n) for n in sorted(dir(os)) if n.startswith(("exec", "spawn")) and callable(getattr(os, n))]
_PATCHERS = [mock.patch.object(_mod, _name, _blocked) for _mod, _name in _GUARDED]


def setUpModule():
    """Arm the guard for every test of this module (the wave 4 merge's fix: never at import, because test_round4
    imports every test module in one process and an import-time guard would trip in the others)."""
    for patcher in _PATCHERS:
        patcher.start()


def tearDownModule():
    for patcher in reversed(_PATCHERS):
        patcher.stop()

import harness_bookkeeping as hb  # noqa: E402
from box import image_lock as il  # noqa: E402
from box.egress import proxy_conf as pc  # noqa: E402

# The allowed hosts as D8 B2 item 8 states them, keyed by the module's own harness constants; arm O's is chatgpt.com by
# glitch-b5's ruling R1 (Sun 18 Oct 2026, lane vendor-admission round 17, B4), the host of the pinned Codex's
# CHATGPT_CODEX_BASE_URL (CODEX_SOURCE below).
HOSTS = {hb.CLAUDE_CODE: "api.anthropic.com", pc.CODEX: "chatgpt.com",
         pc.GEMINI: "generativelanguage.googleapis.com"}
# R1's source, read statically at the pinned tag (the executor's read of rust-v0.162.1, commit 092d3acd, line 80:
# pub const CHATGPT_CODEX_BASE_URL: &str = "https://chatgpt.com/backend-api/codex";).
CODEX_SOURCE = {"constant": "CHATGPT_CODEX_BASE_URL", "value": "https://chatgpt.com/backend-api/codex",
                "tag": "rust-v0.162.1", "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
                "file": "codex-rs/model-provider-info/src/lib.rs", "line": 80,
                "url": "https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/model-provider-info/src/lib.rs#L80"}
CC = hb.CLAUDE_CODE


def rendered(harness: str = CC) -> str:
    return pc.render(harness)


# Each policy clause, mutated in a rendered configuration: (harness, old, new). Every one must be refused by check.
MUTANT_CONFS = {
    "a second dstdomain value": (CC, "dstdomain -n api.anthropic.com", "dstdomain -n api.anthropic.com example.org"),
    "a leading-dot domain": (CC, "dstdomain -n api.anthropic.com", "dstdomain -n .anthropic.com"),
    "a dstdom_regex": (CC, "dstdomain -n api.anthropic.com", "dstdom_regex -n ^api.anthropic.com$"),
    "a reverse lookup allowed": (CC, "dstdomain -n api.anthropic.com", "dstdomain api.anthropic.com"),
    "a second dstdomain flag": (CC, "dstdomain -n api.anthropic.com", "dstdomain -n -i api.anthropic.com"),
    "a host with a trailing dot": (CC, "dstdomain -n api.anthropic.com", "dstdomain -n api.anthropic.com."),
    "a second dstdomain acl": (CC, "http_access deny !tunnel", "acl other dstdomain -n example.org\n"
                               "http_access deny !tunnel"),
    # Fold 3 (W4A1-4 a): the extra definition comes FIRST, so only the duplicate refusal can catch it (squid would
    # merge the two and allow example.org).
    "the same acl defined twice": (CC, "acl api_host dstdomain -n api.anthropic.com",
                                   "acl api_host dstdomain -n example.org\nacl api_host dstdomain -n api.anthropic.com"),
    "an http_access allow all": (CC, "http_access deny all", "http_access allow all\nhttp_access deny all"),
    "an allow that is not CONNECT": (CC, "http_access allow tunnel api_host", "http_access allow api_host"),
    "a second allow line": (CC, "http_access deny all", "http_access allow tunnel api_host\nhttp_access deny all"),
    "an allow with a negation": (CC, "http_access allow tunnel api_host", "http_access allow tunnel !api_host"),
    "deny all missing": (CC, "http_access deny all\n", ""),
    "deny all not last": (CC, "http_access allow tunnel api_host\nhttp_access deny all",
                          "http_access deny all\nhttp_access allow tunnel api_host"),
    "deny !CONNECT missing": (CC, "http_access deny !tunnel\n", ""),
    "deny CONNECT to other ports missing": (CC, "http_access deny tunnel !tls_port\n", ""),
    "port 443 changed": (CC, "acl tls_port port 443", "acl tls_port port 8443"),
    "a second port": (CC, "acl tls_port port 443", "acl tls_port port 443 80"),
    "a port range": (CC, "acl tls_port port 443", "acl tls_port port 1-65535"),
    "a second port acl": (CC, "http_access deny !tunnel", "acl web port 80\nhttp_access deny !tunnel"),
    "a second method": (CC, "acl tunnel method CONNECT", "acl tunnel method CONNECT GET"),
    "the codex render carrying the Anthropic host": (pc.CODEX, "dstdomain -n chatgpt.com",
                                                    "dstdomain -n api.anthropic.com"),
    "the gemini render carrying the OpenAI host": (pc.GEMINI, "dstdomain -n generativelanguage.googleapis.com",
                                                  "dstdomain -n chatgpt.com"),
    # round 17 B4 (R1): arm O's host exactly, never its subdomains, never the sign-in host, never the old API host
    "the codex host with a leading dot": (pc.CODEX, "dstdomain -n chatgpt.com", "dstdomain -n .chatgpt.com"),
    "the codex render adding the sign-in host": (pc.CODEX, "dstdomain -n chatgpt.com",
                                                 "dstdomain -n chatgpt.com auth.openai.com"),
    "the codex render back on the API host": (pc.CODEX, "dstdomain -n chatgpt.com", "dstdomain -n api.openai.com"),
    "an unrendered slot": (CC, "dstdomain -n api.anthropic.com", "dstdomain -n " + "@ALLOWED_HOST@"),
    "an unknown directive": (CC, "cache deny all", "cache deny all\nalways_direct allow all"),
    "an unknown acl type": (CC, "acl tls_port port 443", "acl tls_port dst 0.0.0.0/0"),
    "a second listening port": (CC, "http_port 3128", "http_port 3128\nhttp_port 8080"),
    "the listening port moved": (CC, "http_port 3128", "http_port 8080"),
    "a listening address": (CC, "http_port 3128", "http_port 0.0.0.0:3128"),
    "a cache": (CC, "cache deny all\n", ""),
    "the access log off": (CC, "access_log stdio:/dev/stdout", "access_log none"),
    "a pid file": (CC, "pid_filename none", "pid_filename /run/squid.pid"),
    "a continuation": (CC, "http_access deny all", "http_access deny \\\nall"),
    # Fold 3 (W4A1-2): squid reads a physical line with fgets(BUFSIZ); a comment longer than BUFSIZ-1 (8191) ends
    # early and its tail is read as a directive, here the first http_access rule.
    "P2 a long comment hiding a directive": (CC, "http_access deny !tunnel", "#" + "x" * 8190
                                             + "http_access allow all\nhttp_access deny !tunnel"),
    "a line over 512 characters": (CC, "cache deny all", "cache deny all" + " " * 499),
    "a carriage return": (CC, "cache deny all", "cache deny all\r"),
    "a non-breaking space": (CC, "http_access deny all", "http_access deny\u00a0all"),
    "a control character in a comment": (CC, "pid_filename none", "pid_filename none\n# \x0b"),
}


def conf_mutated(name: str) -> tuple:
    harness, old, new = MUTANT_CONFS[name]
    text = rendered(harness)
    if text.count(old) != 1:
        raise AssertionError(f"mutant {name!r}: {old!r} is not once in {harness}'s rendered configuration")
    return harness, text.replace(old, new)


def leak_hits(strings) -> list:
    return [s for s in strings if any(re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])", s,
                                                re.IGNORECASE) for w in LEAK_WORDS)]


class GuardTest(unittest.TestCase):
    def test_the_guard_starts_no_patch_at_import(self):
        # Recorded at the very end of this module's import: no guarded name was patched then.
        self.assertEqual(_PATCHED_AT_IMPORT, [])
        # And the same record, taken now inside a test, holds every guarded name (setUpModule armed them), so the
        # record can see a patch. The mutant that starts the guard at import is a whole-file swap (lane report).
        self.assertEqual(len(_patched_now()), len(_GUARDED))

    def test_the_process_guard_is_armed(self):
        self.assertEqual(len(_patched_now()), len(_GUARDED))
        with self.assertRaises(AssertionError):
            subprocess.run(["true"])
        with self.assertRaises(AssertionError):
            os.kill(0, 0)
        self.assertIn((os, "posix_spawn"), _GUARDED)

    def test_the_modules_are_this_rounds(self):
        self.assertTrue(os.path.abspath(pc.__file__).startswith(os.path.join(HERE, "box", "egress") + os.sep))
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(pc.__file__), "__init__.py")))


class ConstantsTest(unittest.TestCase):
    def test_the_shared_values(self):
        self.assertEqual(pc.HOSTS, HOSTS)
        self.assertEqual((pc.CODEX, pc.GEMINI), ("codex", "gemini"))
        self.assertIn(hb.CLAUDE_CODE, pc.HOSTS)
        self.assertEqual((pc.ALIAS, pc.PORT, pc.PROXY_URL), ("proxy", 3128, "http://proxy:3128"))
        self.assertEqual(pc.CONF_PATH, "/etc/squid/squid.conf")
        self.assertEqual(list(pc.COMMAND), ["squid", "-N", "-f", "/etc/squid/squid.conf"])
        self.assertEqual(pc.TLS_PORT, 443)

    def test_each_constant_change_goes_red(self):
        for const, value in (("PORT", 3129), ("TLS_PORT", 8443), ("ACCESS_LOG", "none")):
            with self.subTest(const), mock.patch.object(pc, const, value):
                self.assertTrue(pc.check(pc._template_text().replace(pc.SLOT, HOSTS[CC]), CC))
        for harness in HOSTS:
            with self.subTest(harness), mock.patch.dict(pc.HOSTS, {harness: "example.org"}):
                self.assertTrue(pc.check(pc._template_text().replace(pc.SLOT, HOSTS[harness]), harness))

    def test_the_pending_user(self):
        # FILLED 14 Oct 2026 (glitch-06's ruling): squid's package user measured in the locked egress image; the
        # PENDING clause stays red-tested by putting PENDING back.
        with mock.patch.object(pc, "USER", pc.PENDING):
            self.assertEqual(set(pc.pending()), {"USER"})
            self.assertTrue(pc.pending()["USER"].strip())
            with self.assertRaises(pc.NotReady):
                pc.launch_fields()
        self.assertEqual(pc.USER, "13:13")
        self.assertEqual(pc.pending(), {})
        with mock.patch.object(pc, "USER", "13:13"):
            self.assertEqual(pc.pending(), {})
            self.assertEqual(pc.launch_fields(), {"conf_target": "/etc/squid/squid.conf", "command": pc.COMMAND,
                                                  "user": "13:13", "alias": "proxy"})
        # The mutant that drops the refusal hands out the PENDING user.
        with mock.patch.object(pc, "USER", pc.PENDING), mock.patch.object(pc, "pending", lambda: {}):
            self.assertEqual(pc.launch_fields()["user"], pc.PENDING)

    def test_the_user_is_the_measured_one(self):
        """The egress image's `getent passwd proxy`, read in each stub take on athena (lane-reports/stub-take-20261014,
        stub-take-run1..4.json `squid_user`), is proxy:x:13:13; USER is its uid:gid, and never root."""
        runs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lane-reports",
                            "stub-take-20261014")
        seen = set()
        for i in (1, 2, 3, 4):
            with open(os.path.join(runs, f"stub-take-run{i}.json"), encoding="utf-8") as fh:
                seen.add(json.load(fh)["squid_user"]["getent"])
        self.assertEqual(seen, {"proxy:x:13:13:proxy:/bin:/usr/sbin/nologin\n"})
        f = next(iter(seen)).split(":")
        self.assertEqual(pc.USER, f"{f[2]}:{f[3]}")
        self.assertNotEqual(f[2], "0")

    def test_no_parameter_can_override_a_pending_value(self):
        self.assertEqual(list(pyinspect.signature(pc.launch_fields).parameters), [])
        self.assertEqual(list(pyinspect.signature(pc.pending).parameters), [])
        self.assertEqual(list(pyinspect.signature(pc.render).parameters), ["harness"])
        self.assertEqual(list(pyinspect.signature(pc.check).parameters), ["text", "harness"])
        self.assertEqual(list(pyinspect.signature(pc.allowed_hosts).parameters), ["text"])


def codex_host_problems() -> list:
    """Round 17 B4 (glitch-b5's ruling R1): arm O's one host is exactly the host of the pinned Codex's
    CHATGPT_CODEX_BASE_URL, recorded in proxy_conf with its tag, commit, file, line and URL, and a codex take's
    rendered configuration allows that host alone (no subdomain, no sign-in host, no API host)."""
    from urllib.parse import urlsplit
    import codex_native
    out = []
    src = getattr(pc, "CODEX_HOST_SOURCE", None)
    if src != CODEX_SOURCE:
        out.append(f"proxy_conf records no or another source for arm O's host: {src!r}")
    if CODEX_SOURCE["tag"] != "rust-v" + codex_native.PINNED_CLI:
        out.append(f"the source's tag is not the pinned Codex's ({codex_native.PINNED_CLI})")
    if not CODEX_SOURCE["url"].endswith(f"/{CODEX_SOURCE['tag']}/{CODEX_SOURCE['file']}#L{CODEX_SOURCE['line']}"):
        out.append("the source's URL does not name its tag, file and line")
    want = urlsplit(CODEX_SOURCE["value"]).hostname
    if pc.HOSTS.get(pc.CODEX) != want:
        out.append(f"arm O's host is {pc.HOSTS.get(pc.CODEX)!r}, not the pinned base URL's host {want!r}")
    try:
        text = pc.render(pc.CODEX)
        if pc.allowed_hosts(text) != [want] or pc.check(text, pc.CODEX):
            out.append(f"a codex take's configuration allows {pc.allowed_hosts(text)}: {pc.check(text, pc.CODEX)}")
    except pc.ProxyConfError as e:
        out.append(f"a codex take's configuration is refused: {e}")
    return out


class CodexHostTest(unittest.TestCase):
    def test_arm_o_reaches_the_pinned_base_urls_host_alone(self):
        self.assertEqual(codex_host_problems(), [])

    def test_mutants(self):
        """Each mutant red (round 17 B4): the API host restored, the host with a leading dot (subdomains admitted),
        the sign-in host added to a take, the source record gone or its tag moved."""
        self.assertEqual(codex_host_problems(), [])
        loose = lambda extra: (lambda: pc._template_text().replace(pc.SLOT, "chatgpt.com" + extra))  # noqa: E731
        for name, ctx in (
                ("api.openai.com restored", lambda: mock.patch.dict(pc.HOSTS, {pc.CODEX: "api.openai.com"})),
                ("chatgpt.com with a leading dot", lambda: mock.patch.dict(pc.HOSTS, {pc.CODEX: ".chatgpt.com"})),
                ("auth.openai.com added to a take",
                 lambda: mock.patch.object(pc, "render", lambda h, _t=loose(" auth.openai.com"): _t())),
                ("the source record dropped", lambda: mock.patch.object(pc, "CODEX_HOST_SOURCE", None, create=True)),
                ("the source at another tag", lambda: mock.patch.object(
                    pc, "CODEX_HOST_SOURCE", dict(CODEX_SOURCE, tag="rust-v0.162.0"), create=True))):
            with self.subTest(name), ctx():
                got = codex_host_problems()
                print(f"  mutant {name}: {'red' if got else 'GREEN (survived)'}")
                self.assertTrue(got, f"mutant {name} survived")


class CodexHostResidualTest(unittest.TestCase):
    def test_r1s_residual_is_in_the_drafts_box_residuals(self):
        """R1's named residual is pre-registered with the study's box limitations (prereg-draft's box_residuals)."""
        draft = json.loads((Path(HERE) / "prereg-draft.json").read_text(encoding="utf-8"))
        rows = [r for r in draft["box_residuals"] if r.get("name") == "arm O egress host"]
        self.assertEqual(len(rows), 1)
        for words in ("chatgpt.com", "CHATGPT_CODEX_BASE_URL", "rust-v0.162.1", "lib.rs line 80", "hosts, not paths",
                      "does not intercept TLS", "a copy of the lease", "Codex2"):
            self.assertIn(words, rows[0]["text"])
        self.assertIn("R1", rows[0]["ruling"])
        self.assertIn("tests/test_egress.py CodexHostTest", rows[0]["closed_check"])


class RenderTest(unittest.TestCase):
    def test_each_harness_allows_exactly_its_host(self):
        for harness, host in HOSTS.items():
            with self.subTest(harness):
                text = rendered(harness)
                self.assertEqual(pc.allowed_hosts(text), [host])
                self.assertEqual(pc.check(text, harness), [])
                for other, other_host in HOSTS.items():
                    if other != harness:
                        self.assertNotIn(other_host, text)
                        self.assertTrue(pc.check(text, other))   # one take's conf never passes for another arm

    def test_the_template(self):
        text = pc._template_text()
        self.assertEqual(text.count(pc.SLOT), 1)
        self.assertEqual(text.count("@"), 2)
        self.assertTrue(pc.check(text, CC))   # the unrendered template itself is refused
        lines = [ln for ln in text.split("\n") if ln and not ln.startswith("#")]
        self.assertEqual(lines, ["http_port 3128", "acl tls_port port 443", "acl tunnel method CONNECT",
                                 "acl api_host dstdomain -n @ALLOWED_HOST@", "http_access deny !tunnel",
                                 "http_access deny tunnel !tls_port", "http_access allow tunnel api_host",
                                 "http_access deny all", "cache deny all", "access_log stdio:/dev/stdout",
                                 "pid_filename none"])

    def test_an_unknown_harness_is_refused(self):
        for name in ("fake-second", "", "Claude-Code", "claude"):
            with self.subTest(name):
                with self.assertRaises(pc.ProxyConfError):
                    pc.render(name)
                self.assertTrue(pc.check(rendered(CC), name))

    def test_a_template_slot_twice_or_missing_is_refused(self):
        twice = pc._template_text() + "acl x dstdomain " + pc.SLOT + "\n"
        with mock.patch.object(pc, "_template_text", lambda: twice), self.assertRaises(pc.ProxyConfError):
            pc.render(CC)
        none = pc._template_text().replace(pc.SLOT, HOSTS[CC])
        with mock.patch.object(pc, "_template_text", lambda: none), self.assertRaises(pc.ProxyConfError):
            pc.render(CC)

    def test_render_refuses_a_template_that_fails_its_check(self):
        loose = pc._template_text().replace("http_access deny all\n", "")
        with mock.patch.object(pc, "_template_text", lambda: loose), self.assertRaises(pc.ProxyConfError):
            pc.render(CC)

    def test_every_conf_mutant_is_refused(self):
        for name in MUTANT_CONFS:
            with self.subTest(name):
                harness, text = conf_mutated(name)
                self.assertTrue(pc.check(text, harness), name)

    def test_allowed_hosts_refuses_an_unbounded_allow(self):
        for name in ("an http_access allow all", "an allow with a negation"):
            with self.subTest(name), self.assertRaises(pc.ProxyConfError):
                pc.allowed_hosts(conf_mutated(name)[1])
        self.assertEqual(pc.allowed_hosts(conf_mutated("a second dstdomain value")[1]),
                         ["api.anthropic.com", "example.org"])
        self.assertEqual(pc.allowed_hosts(conf_mutated("an allow that is not CONNECT")[1]), ["api.anthropic.com"])
        with self.assertRaises(pc.ProxyConfError):
            pc.allowed_hosts(conf_mutated("an unknown directive")[1])


class ParseTest(unittest.TestCase):
    def test_tokens_split_on_space_and_tab_only(self):
        text = rendered(CC).replace("http_access deny all", "http_access\tdeny \t all")
        self.assertEqual(pc.check(text, CC), [])   # squid splits on space and tab alike
        self.assertIn(("http_access", ["deny", "all"]), [(d, a) for _, d, a in pc.parse(text)])

    def test_the_line_length_limit(self):
        self.assertEqual(pc.MAX_LINE, 512)
        ok = rendered(CC).replace("cache deny all", "cache deny all" + " " * (512 - len("cache deny all")))
        self.assertEqual(pc.check(ok, CC), [])     # exactly 512 is read
        with self.assertRaises(pc.ProxyConfError):
            pc.parse(ok.replace("cache deny all", "cache deny all "))


# The committed egress lock is the reviewed pin (glitch-06's post-write ruling, 14 Oct 2026): the lock writer
# re-derives it from the committed build record, here at import (git, before setUpModule arms the guard).
EGRESS_UNFILLED_PENDING = ("base", "image_id", "squid")
EGRESS_LOCK_PATH = os.path.join(il.BOX_DIR, "egress", "image.lock")


def _rederived_egress():
    import importlib.util
    spec = importlib.util.spec_from_file_location("write_image_lock_for_test_egress",
                                                  os.path.join(REPO, "ops", "write_image_lock.py"))
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    record = os.path.join(REPO, "lane-reports", "build-20261014c", "athena-out-20261014", "build-record.json")
    try:
        return w.rederive(il, REPO, record, EGRESS_LOCK_PATH, il.EGRESS_IMAGE)
    except (w.Refused, il.LockError, ValueError, OSError, subprocess.TimeoutExpired) as e:
        return f"refused: {type(e).__name__}: {e}"


EGRESS_REDERIVED = _rederived_egress()


def unfilled_egress() -> dict:
    """A synthetic unfilled (schema-1) egress lock: the committed lock with its schema-2 fields removed and
    EGRESS_UNFILLED_PENDING PENDING again (never written to a lock path)."""
    lock = {k: v for k, v in il.load(EGRESS_LOCK_PATH).items() if k not in il.SCHEMA_2_KEYS}
    lock["schema"] = il.SCHEMA
    for field in EGRESS_UNFILLED_PENDING:
        lock[field] = il.PENDING
    lock["pending"] = {f: "synthetic: re-PENDINGed from the committed lock" for f in EGRESS_UNFILLED_PENDING}
    return il.validate(lock)


def egress_pin_problems(text: bytes) -> list:
    """[] when `text` is the committed egress lock the lock writer re-derives from the reviewed record."""
    if not isinstance(EGRESS_REDERIVED, bytes):
        return [f"the lock writer does not re-derive the egress lock ({EGRESS_REDERIVED})"]
    out = []
    try:
        if json.loads(text).get("schema") != il.SCHEMA_2:
            out.append("the committed egress lock is not schema 2")
    except (TypeError, ValueError, AttributeError):
        out.append("the committed egress lock is not JSON")
    if text != EGRESS_REDERIVED:
        out.append("the committed egress lock is not the lock writer's re-derivation from the record")
    return out


class EgressImageTest(unittest.TestCase):
    def dockerfile(self) -> str:
        with open(os.path.join(il.BOX_DIR, il.DOCKERFILES[il.EGRESS_IMAGE]), encoding="utf-8") as fh:
            return fh.read()

    def lock(self) -> dict:
        return il.load(os.path.join(il.BOX_DIR, "egress", "image.lock"))

    def test_the_egress_image_is_by_digest_and_copies_nothing(self):
        text, lock = self.dockerfile(), self.lock()
        self.assertEqual(il.check_dockerfile(text, lock), [])
        ins = il.parse_dockerfile(text)
        self.assertEqual((ins[0].args, ins[1].keyword, ins[1].args), ("BASE", "FROM", "${BASE}"))
        self.assertFalse([i for i in ins if i.keyword in ("COPY", "ADD")])
        self.assertEqual(il.pending(unfilled_egress()), EGRESS_UNFILLED_PENDING)
        self.assertEqual(il.pending(lock), ())                   # the committed lock is the filled, reviewed pin
        for old, new in (("FROM ${BASE}", "FROM debian:13"), ("ENTRYPOINT []", "COPY proxy.conf /etc/x\nENTRYPOINT []"),
                         ('"squid=${SQUID_VERSION}"', "squid")):
            with self.subTest(new):
                self.assertTrue(il.check_dockerfile(text.replace(old, new), lock))

    def test_the_committed_egress_lock_is_the_reviewed_pin(self):
        with open(EGRESS_LOCK_PATH, "rb") as fh:
            text = fh.read()
        self.assertEqual(egress_pin_problems(text), [])
        doc = json.loads(text)
        edited = dict(doc, manifest_digest=doc["manifest_digest"][:-1] + ("0" if doc["manifest_digest"][-1] != "0" else "1"))
        for name, bad in (("a pin hand-edited by one digest", (json.dumps(edited, indent=1, sort_keys=True) + "\n").encode()),
                          ("an unfilled lock", (json.dumps(unfilled_egress(), indent=1, sort_keys=True) + "\n").encode())):
            with self.subTest(name):
                self.assertTrue(egress_pin_problems(bad), name)

    def test_the_egress_build_takes_squid_from_the_lock(self):
        lock = unfilled_egress()
        with self.assertRaises(il.NotReady):
            il.build_argv(lock, context="/srv/ctx")
        lock.update(base="registry.example/fake-base@sha256:" + "a" * 64, squid="6.99-1+fake1", pending={
            "image_id": "the build makes it"})
        argv = il.build_argv(lock, context="/srv/ctx")
        self.assertIn("SQUID_VERSION=6.99-1+fake1", argv)
        self.assertIn(il.SQUID_LABEL + "=6.99-1+fake1", argv)


class NeutralityTest(unittest.TestCase):
    def test_the_agent_visible_proxy_strings_carry_no_study_word(self):
        # The take container's exec environment carries HTTPS_PROXY=PROXY_URL; the alias names the proxy there.
        self.assertEqual(leak_hits([pc.PROXY_URL, pc.ALIAS]), [])

    def test_a_planted_study_word_goes_red(self):
        with mock.patch.object(pc, "ALIAS", "probe"):
            self.assertEqual(leak_hits([pc.ALIAS]), ["probe"])
        self.assertTrue(leak_hits(["http://" + LEAK_WORDS[0].replace(" ", "-") + ":3128"]))


def print_mutants() -> None:
    for name in MUTANT_CONFS:
        harness, text = conf_mutated(name)
        found = pc.check(text, harness)
        print(f"mutant conf {name!r} ({harness}): {'red' if found else 'GREEN'} ({found[0] if found else '-'})")


def _patched_now() -> list:
    """The guarded names that are patched to the guard right now."""
    return [f"{getattr(m, '__name__', m)}.{n}" for m, n in _GUARDED if getattr(m, n) is _blocked]


# Taken last, after every import-time statement of this module: must be empty (setUpModule arms the guard).
_PATCHED_AT_IMPORT = _patched_now()


if __name__ == "__main__":
    print_mutants()
    unittest.main()
