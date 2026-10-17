#!/usr/bin/env python3
"""box/scan_record.py: the commit scan, on planted fake values only.

Every planted value is obviously fake and carries no vendor's key prefix. The holdout matcher here is an injected
fake over obviously synthetic strings that are not wordings of any task (ruling C4); no holdout wording, digest or
count appears in this file. The rules scanner is a fake. Nothing reads a real login file or anything under
~/.config/: every login fixture is written into a temporary folder. A module guard (setUpModule) makes every
process start and every signal raise, and a planted test proves it is armed.

Every guard is also run against an in-memory mutant, which must turn its check red; each mutant's red run is
printed (MUTANT ... red), and the list at the end.
"""

from __future__ import annotations

import contextlib
import hashlib
import inspect
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
STUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDY)

import scrub  # noqa: E402
from box import scan_record as sr  # noqa: E402

TOKEN = "FAKEVALUE-0123456789abcdef-PLANTED"
KEY = "FAKEKEY-fedcba9876543210-PLANTED-TOO"
EMAIL = "planted.person@example.invalid"
SECRETS = [("token", TOKEN), ("key", KEY), ("email", EMAIL)]
VALUES = (TOKEN, KEY, EMAIL)
SYNTHETIC = "ZEBRA-QUOKKA-SYNTHETIC-PHRASE"      # stands in for a holdout wording; it is not one


def synthetic_matcher(text):
    out, i = [], text.find(SYNTHETIC)
    while i != -1:
        out.append((i, i + len(SYNTHETIC)))
        i = text.find(SYNTHETIC, i + 1)
    return out


def no_findings(paths):
    return []


def holdout_record_ok(result, matcher_given: bool) -> bool:
    return result["holdout"] == ("checked" if matcher_given else "not-checked")


# ------------------------------------------------------------------------------------------------- the process guard
_GUARD = [("subprocess", "run"), ("subprocess", "Popen"), ("os", "system"), ("os", "kill"), ("os", "killpg"),
          ("os", "posix_spawn"), ("os", "posix_spawnp"), ("os", "fork")]
_GUARD += [("os", n) for n in dir(os) if n.startswith(("exec", "spawn"))]
_PATCHES: list = []
MUTANTS: list = []


class ProcessStartRefused(BaseException):
    pass


def _refuse(*a, **k):
    raise ProcessStartRefused("a test reached a process start or a signal")


def setUpModule():
    mods = {"subprocess": subprocess, "os": os}
    for mod, name in _GUARD:
        if hasattr(mods[mod], name):
            p = mock.patch.object(mods[mod], name, _refuse)
            p.start()
            _PATCHES.append(p)


def tearDownModule():
    while _PATCHES:
        _PATCHES.pop().stop()
    print("\n".join(["", f"mutants run red in this file ({len(MUTANTS)}):"] + [f"  {m}" for m in MUTANTS]))


def red(name):
    MUTANTS.append(name)
    print(f"\nMUTANT {name}: red", end=" ")


# ------------------------------------------------------------------------------------------------- a fake commit
def jl(*recs) -> bytes:
    return b"".join(json.dumps(r).encode() + b"\n" for r in recs)


class Commit:
    """One file per kind in a temporary record folder; `plant` puts a value into the file of one kind."""

    def __init__(self, plant: dict | None = None):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        plant = plant or {}
        self.paths = {}
        for kind in sr.KINDS:
            extra = plant.get(kind)
            body = jl({"type": "assistant", "text": "a constructed line"}, {"type": "user", "text": "plain"})
            if extra is not None:
                body += jl({"type": "assistant", "text": f"the agent printed {extra} here"})
            body += jl({"type": "result", "n": 3})
            name = {"blob": hashlib.sha256(body).hexdigest()}.get(kind, f"{kind}.jsonl")
            p = os.path.join(self.root, name)
            with open(p, "wb") as fh:
                fh.write(body)
            self.paths[kind] = p

    def files(self):
        return [(self.paths[k], k) for k in sr.KINDS]

    def read(self, kind) -> bytes:
        with open(self.paths[kind], "rb") as fh:
            return fh.read()

    def close(self):
        self._tmp.cleanup()


class Case(unittest.TestCase):
    def commit(self, plant=None) -> Commit:
        c = Commit(plant)
        self.addCleanup(c.close)
        return c


class TestGuard(unittest.TestCase):
    def test_the_process_guard_is_armed(self):
        self.assertIs(subprocess.run, _refuse)
        self.assertIs(subprocess.Popen, _refuse)
        self.assertIs(os.kill, _refuse)
        for call in (lambda: subprocess.run(["true"]), lambda: subprocess.Popen(["true"]), lambda: os.kill(-1, 0)):
            with self.assertRaises(ProcessStartRefused):
                call()

    def test_the_module_is_this_rounds_file(self):
        self.assertEqual(os.path.abspath(sr.__file__), os.path.join(STUDY, "box", "scan_record.py"))


# ------------------------------------------------------------------------------------------------- the plan's checks
class TestScan(Case):
    def test_a_clean_commit_passes(self):
        c = self.commit()
        before = {k: c.read(k) for k in sr.KINDS}
        r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(list(r), list(sr.RESULT_FIELDS))
        self.assertEqual((r["masked"], r["events"], r["refused"]), ([], 0, []))
        self.assertTrue(sr.passed(r))
        self.assertEqual(r["holdout"], "not-checked")
        for f in r["files"]:
            self.assertEqual(f["sha256_before"], f["sha256_after"])
        self.assertEqual({k: c.read(k) for k in sr.KINDS}, before)

    def test_a_planted_value_in_each_maskable_kind_is_found_and_masked(self):
        for kind in sr.MASKABLE:
            for skind, value in SECRETS:
                with self.subTest(kind=kind, secret=skind):
                    c = self.commit({kind: value})
                    before = c.read(kind)
                    r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
                    after = c.read(kind)
                    self.assertEqual(r["masked"], [{"path": c.paths[kind], "line": 3, "kind": skind,
                                                    "offset": before.split(b"\n")[2].find(value.encode())}])
                    self.assertEqual(r["events"], 1)
                    self.assertEqual(r["refused"], [])
                    self.assertNotIn(value.encode(), after)
                    self.assertIn(sr.MARKERS[skind].encode(), after)
                    b, a = before.split(b"\n"), after.split(b"\n")
                    self.assertEqual(len(a), len(b))
                    self.assertEqual([x for i, x in enumerate(a) if i != 2], [x for i, x in enumerate(b) if i != 2])
                    for line in a[:-1]:
                        json.loads(line)
                    rec = next(f for f in r["files"] if f["path"] == c.paths[kind])
                    self.assertEqual(rec, {"path": c.paths[kind], "sha256_before": hashlib.sha256(before).hexdigest(),
                                           "sha256_after": hashlib.sha256(after).hexdigest()})

    def test_the_email_marker_is_scrubs(self):
        self.assertIs(sr.MARKERS["email"], scrub.NOTE)
        self.assertEqual(set(sr.MARKERS), set(sr.SECRET_KINDS))

    def test_for_each_non_maskable_kind_the_value_is_refused(self):
        for kind in sorted(set(sr.KINDS) - set(sr.MASKABLE)):
            with self.subTest(kind=kind):
                c = self.commit({kind: TOKEN})
                before = c.read(kind)
                r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
                self.assertEqual(r["masked"], [])
                self.assertEqual([(x["path"], x["line"], x["kind"]) for x in r["refused"]],
                                 [(c.paths[kind], 3, "token")])
                self.assertFalse(sr.passed(r))
                self.assertEqual(c.read(kind), before)          # never edited (a blob's name is its own sha256)

    def test_rules_scanner_findings_are_refused(self):
        c = self.commit()
        seen = []

        def finder(paths):
            seen.append(paths)
            return [{"path": c.paths["stream"], "line": 2, "rule": "generic-api-key"}]
        r = sr.scan(c.files(), SECRETS, rules_scanner=finder)
        self.assertEqual(seen, [[p for p, _ in c.files()]])
        self.assertEqual(r["refused"], [{"path": c.paths["stream"], "line": 2, "kind": "rule",
                                         "why": "the rules scanner's rule 'generic-api-key'"}])
        self.assertFalse(sr.passed(r))

    def test_a_scan_without_a_rules_scanner_refuses(self):
        c = self.commit()
        with self.assertRaises(sr.NotReady):
            sr.scan(c.files(), SECRETS, rules_scanner=None)

    def test_several_hits_on_one_line_and_overlaps(self):
        c = self.commit({"session": f"{TOKEN} and {EMAIL} and {TOKEN}"})
        r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual([m["kind"] for m in r["masked"]], ["token", "email", "token"])
        self.assertEqual(r["events"], 3)
        # a value inside a longer one is masked once, as the longer one
        c2 = self.commit({"stream": TOKEN})
        r2 = sr.scan(c2.files(), [("token", TOKEN), ("key", TOKEN[:22])], rules_scanner=no_findings)
        self.assertEqual([m["kind"] for m in r2["masked"]], ["token"])

    def test_bad_inputs_are_refused(self):
        c = self.commit()
        for files, secrets in [([(c.paths["stream"], "notes")], SECRETS), ([("rel/path", "stream")], SECRETS),
                               ([(c.paths["stream"], "stream")] * 2, SECRETS),
                               ([(c.paths["stream"], "stream")], [("holdout", "x" * 30)]),
                               ([(c.paths["stream"], "stream")], [("token", "short")]),
                               ([(c.paths["stream"], "stream")], [("email", "a\nb@c.de")])]:
            with self.subTest(files=files, secrets=[k for k, _ in secrets]):
                with self.assertRaises(sr.ScanError):
                    sr.scan(files, secrets, rules_scanner=no_findings)
        link = os.path.join(c.root, "link.jsonl")
        os.symlink(c.paths["stream"], link)
        with self.assertRaises(sr.ScanError):
            sr.scan([(link, "stream")], SECRETS, rules_scanner=no_findings)

    def test_named_residuals(self):
        # A value split across a line break is not found by the exact-value search (named residual).
        c = self.commit()
        with open(c.paths["transcript"], "ab") as fh:
            fh.write(TOKEN[:15].encode() + b"\n" + TOKEN[15:].encode() + b"\n")
        r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(r["masked"], [])
        # A value present only in a JSON escape is not found either (named residual).
        c2 = self.commit()
        escaped = json.dumps({"text": TOKEN.replace("-", "‑")}, ensure_ascii=True).replace(
            "\\u2011", "\\u002d")
        self.assertEqual(json.loads(escaped)["text"], TOKEN)
        with open(c2.paths["stream"], "ab") as fh:
            fh.write(escaped.encode() + b"\n")
        r2 = sr.scan(c2.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(r2["masked"], [])


# ------------------------------------------------------------------------------------------------- the holdout seam
class TestHoldout(Case):
    def test_no_matcher_records_not_checked(self):
        c = self.commit({"stream": SYNTHETIC})
        r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(r["holdout"], "not-checked")
        self.assertEqual(r["refused"], [])

    def test_a_matcher_refuses_every_hit_by_path_line_and_kind_only(self):
        c = self.commit({"stream": SYNTHETIC, "ledger": SYNTHETIC})
        r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings, holdout_matcher=synthetic_matcher)
        self.assertEqual(r["holdout"], "checked")
        self.assertEqual(sorted((x["path"], x["line"], x["kind"]) for x in r["refused"]),
                         sorted([(c.paths["stream"], 3, "holdout"), (c.paths["ledger"], 3, "holdout")]))
        self.assertTrue(all(set(x) == {"path", "line", "kind", "why"} for x in r["refused"]))
        self.assertIn(SYNTHETIC.encode(), c.read("stream"))       # refused, never masked
        self.assertNotIn(SYNTHETIC, json.dumps(r))
        self.assertNotIn(hashlib.sha256(SYNTHETIC.encode()).hexdigest(), json.dumps(r))
        self.assertFalse(sr.passed(r))

    def test_a_matcher_out_of_bounds_is_refused(self):
        c = self.commit()
        with self.assertRaises(sr.ScanError):
            sr.scan(c.files(), SECRETS, rules_scanner=no_findings, holdout_matcher=lambda t: [(0, len(t) + 5)])

    def test_mutant_dropping_not_checked_goes_red(self):
        c = self.commit()
        with mock.patch.object(sr, "NOT_CHECKED", sr.CHECKED):   # mutant: no matcher still reads "checked"
            r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertFalse(holdout_record_ok(r, matcher_given=False))
        red("the not-checked record dropped with no matcher")

    def test_the_holdout_record_check(self):
        c = self.commit()
        self.assertTrue(holdout_record_ok(sr.scan(c.files(), SECRETS, rules_scanner=no_findings), False))
        self.assertTrue(holdout_record_ok(sr.scan(c.files(), SECRETS, rules_scanner=no_findings,
                                                  holdout_matcher=synthetic_matcher), True))

    def test_mutant_matched_text_in_the_result_goes_red(self):
        c = self.commit({"stream": SYNTHETIC})
        real = sr._holdout

        def leaky(m, path, data):
            out = real(m, path, data)
            for x in out:
                x["why"] += " (" + data.decode()[slice(*m(data.decode())[0])] + ")"
            return out
        with mock.patch.object(sr, "_holdout", leaky):
            r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings, holdout_matcher=synthetic_matcher)
        self.assertIn(SYNTHETIC, json.dumps(r))
        red("the matched holdout text put into a result")


# ------------------------------------------------------------------------------------------------- mutants
class TestMutants(Case):
    def test_mutant_skipping_a_kind_goes_red(self):
        real = sr._scan_file
        with mock.patch.object(sr, "_scan_file",
                               lambda p, k, d, n: (None, [], []) if k == "proxy-log" else real(p, k, d, n)):
            c = self.commit({"proxy-log": TOKEN})
            r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(r["refused"], [])
        red("a kind skipped (the proxy log)")

    def test_mutant_deleting_instead_of_masking_goes_red(self):
        with mock.patch.object(sr, "_mask", lambda line, spans: b""):   # mutant: the hit's line emptied
            c = self.commit({"session": TOKEN})
            before = c.read("session")
            r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(r["masked"], [])                 # the masking test's expectations go red:
        self.assertEqual([x["why"] for x in r["refused"]], ["masking would leave a JSON line invalid"])
        self.assertEqual(c.read("session"), before)       # and the JSON guard wrote nothing
        red("delete instead of mask (the line emptied)")
        with mock.patch.dict(sr.MARKERS, {"token": ""}):
            c = self.commit({"session": TOKEN})
            sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertNotIn(b"[masked: token]", c.read("session"))
        red("an empty marker (the value deleted from its line)")

    def test_the_line_guard_refuses_a_dropped_line(self):
        real = sr._scan_file

        def dropping(p, k, d, n):   # mutant: the masked file loses an untouched line
            new, m, r = real(p, k, d, n)
            return (b"".join(new.split(b"\n", 1)[1:]) if new else new), m, r
        with mock.patch.object(sr, "_scan_file", dropping):
            c = self.commit({"session": TOKEN})
            before = c.read("session")
            with self.assertRaisesRegex(sr.ScanError, "changed a line it should not touch"):
                sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(c.read("session"), before)
        red("an untouched line dropped (refused by the line guard)")

    def test_mutant_masking_a_non_maskable_kind_goes_red(self):
        with mock.patch.object(sr, "MASKABLE", sr.MASKABLE + ("ledger",)):
            c = self.commit({"ledger": TOKEN})
            r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(r["refused"], [])
        self.assertEqual(len(r["masked"]), 1)
        red("a non-maskable kind masked (the ledger)")

    def test_mutant_dropping_rules_findings_goes_red(self):
        c = self.commit()
        with mock.patch.object(sr, "_rules", lambda scanner, files: ([], [])):
            r = sr.scan(c.files(), SECRETS,
                        rules_scanner=lambda p: [{"path": p[0], "line": 1, "rule": "generic-api-key"}])
        self.assertEqual(r["refused"], [])
        red("the rules scanner's findings dropped")

    def test_mutant_letting_refused_pass_goes_red(self):
        # mutant: the commit decision reads only the masked list; the refusal check goes red on a refused scan
        c = self.commit({"ledger": TOKEN})
        r = sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertFalse(sr.passed(r))
        with mock.patch.object(sr, "passed", lambda result: not result["masked"]):
            self.assertTrue(sr.passed(r))
        red("a refused scan passed")


# ------------------------------------------------------------------------------------------------- no value leaks
class TestNoValueInAnyOutput(Case):
    def test_no_output_carries_a_value(self):
        outputs = []
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            plant = {k: v for k, v in zip(sr.KINDS, VALUES * 4)}
            c = self.commit(plant)
            r = sr.scan(c.files(), SECRETS, rules_scanner=lambda p: [{"path": p[0], "line": 1, "rule": "x"}],
                        holdout_matcher=synthetic_matcher)
            outputs.append(json.dumps(r))
            for bad in ([("token", TOKEN[:10])], [("email", EMAIL + "\n")], [("holdout", TOKEN)]):
                try:
                    sr.scan(c.files(), bad, rules_scanner=no_findings)
                except Exception as e:  # noqa: BLE001
                    outputs.append(f"{type(e).__name__}: {e} {e.args!r}")
            with mock.patch.object(sr, "_mask", lambda line, spans: line):   # forces "a value survived"
                c2 = self.commit({"stream": TOKEN})
                try:
                    sr.scan(c2.files(), SECRETS, rules_scanner=no_findings)
                except sr.ScanError as e:
                    outputs.append(f"{e} {e.args!r}")
            d = tempfile.mkdtemp()
            self.addCleanup(lambda: [os.unlink(os.path.join(d, n)) for n in os.listdir(d)] and None)
            for body in (f"CODEX_API_KEY={TOKEN}\n\n", f"CODEX_API_KEY={TOKEN} \n", f"OTHER={TOKEN}\n"):
                p = os.path.join(d, "x.env")
                with open(p, "w") as fh:
                    fh.write(body)
                os.chmod(p, 0o600)
                try:
                    sr.read_login(p, "CODEX_API_KEY", allowed=("CODEX_API_KEY",))
                except sr.LoginError as e:
                    outputs.append(f"{e} {e.args!r}")
                os.unlink(p)
        outputs += [buf_out.getvalue(), buf_err.getvalue()]
        self.assertGreaterEqual(len(outputs), 9)
        blob = "\n".join(outputs)
        for v in VALUES:
            self.assertNotIn(v, blob)
        self.assertNotIn(SYNTHETIC, blob)

    def test_the_leak_check_can_fail(self):
        self.assertIn(TOKEN, f"{sr.ScanError('x ' + TOKEN)}")   # a message that did carry it would be seen
        red("a message carrying a value (seen by the check)")


# ------------------------------------------------------------------------------------------------- login files
# The planted login fixtures (merge binding 5: run_take.read_login and this module's run on the union, and agree).
GOOD = "A_LOGIN_NAME"
LOGIN_FIXTURES = {
    "good": (f"{GOOD}={TOKEN}\n", 0o600, True),
    "mode 644": (f"{GOOD}={TOKEN}\n", 0o644, False),
    "two lines": (f"{GOOD}={TOKEN}\n{GOOD}={TOKEN}\n", 0o600, False),
    "a blank second line": (f"{GOOD}={TOKEN}\n\n", 0o600, False),
    "no newline": (f"{GOOD}={TOKEN}", 0o600, False),
    "short": (f"{GOOD}=FAKE-short\n", 0o600, False),
    "a space": (f"{GOOD}=FAKEVALUE 0123456789abcdef\n", 0o600, False),
    "a trailing space": (f"{GOOD}={TOKEN} \n", 0o600, False),
    "a quote": (f'{GOOD}="{TOKEN}"\n', 0o600, False),
    "a carriage return": (f"{GOOD}={TOKEN}\r\n", 0o600, False),
    "another name": (f"OTHER_NAME={TOKEN}\n", 0o600, False),
    "export prefix": (f"export {GOOD}={TOKEN}\n", 0o600, False),
}


class TestReadLogin(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)

    def write(self, body, mode, name="login.env", folder=None):
        p = os.path.join(folder or self.d.name, name)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
        os.chmod(p, mode)
        return p

    def test_the_fixtures(self):
        for label, (body, mode, ok) in LOGIN_FIXTURES.items():
            with self.subTest(label):
                p = self.write(body, mode, name=f"{label.replace(' ', '-')}.env")
                if ok:
                    self.assertEqual(sr.read_login(p, GOOD, allowed=(GOOD,)), TOKEN)
                else:
                    with self.assertRaises(sr.LoginError):
                        sr.read_login(p, GOOD, allowed=(GOOD,))

    def test_a_link_and_a_repository_are_refused(self):
        p = self.write(LOGIN_FIXTURES["good"][0], 0o600)
        link = os.path.join(self.d.name, "link.env")
        os.symlink(p, link)
        with self.assertRaises(sr.LoginError):
            sr.read_login(link, GOOD, allowed=(GOOD,))
        repo = os.path.join(self.d.name, "repo")
        os.makedirs(os.path.join(repo, ".git"))
        os.makedirs(os.path.join(repo, "deep"))
        with self.assertRaises(sr.LoginError):
            sr.read_login(self.write(LOGIN_FIXTURES["good"][0], 0o600, folder=os.path.join(repo, "deep")), GOOD, allowed=(GOOD,))

    def test_a_long_file_is_refused(self):
        p = self.write(LOGIN_FIXTURES["good"][0] + "#" * 70000 + "\n", 0o600)
        with self.assertRaises(sr.LoginError):
            sr.read_login(p, GOOD, allowed=(GOOD,))

    def test_mutant_without_the_mode_check_goes_red(self):
        p = self.write(LOGIN_FIXTURES["mode 644"][0], 0o644)
        with mock.patch.object(sr.stat, "S_IMODE", lambda m: 0o600):
            self.assertEqual(sr.read_login(p, GOOD, allowed=(GOOD,)), TOKEN)
        red("a login file of mode 644 accepted")

    def test_mutant_loose_line_rule_goes_red(self):
        import re
        p = self.write(LOGIN_FIXTURES["a trailing space"][0], 0o600)
        with mock.patch.object(sr, "_LOGIN_LINE", re.compile(rb"([A-Z_][A-Z0-9_]*)=(\S{20,})\s*")):
            self.assertEqual(sr.read_login(p, GOOD, allowed=(GOOD,)), TOKEN)
        red("a login line with trailing whitespace accepted")


# W4 merge, binding 5 (glitch-f3's ruling under Javier's delegation; a merge-time exception to lane w4c): read_login
# keeps run_take.read_login's rule on the four points the merge found apart. One red test per point, then one
# in-memory mutant per point, each turning its check red.
def _login(path, name, allowed):
    if "allowed" in inspect.signature(sr.read_login).parameters:
        return sr.read_login(path, name, allowed=allowed)
    return sr.read_login(path, name)


class TestLoginBinding5(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)

    def write(self, body, name="b5.line"):
        p = os.path.join(self.d.name, name)
        with open(p, "wb") as fh:
            fh.write(body.encode("utf-8"))
        os.chmod(p, 0o600)
        return p

    # (i) ASCII only
    def test_a_non_ascii_value_is_refused(self):
        p = self.write(f"{GOOD}={TOKEN}é\n")
        with self.assertRaises(sr.LoginError):
            _login(p, GOOD, (GOOD,))

    # (ii) the allowed names come from the caller
    def test_a_name_outside_the_allowed_names_is_refused(self):
        p = self.write(f"OTHER_NAME={TOKEN}\n")
        with self.assertRaises(sr.LoginError):
            _login(p, "OTHER_NAME", (GOOD,))
        self.assertEqual(_login(p, "OTHER_NAME", ("OTHER_NAME",)), TOKEN)

    def test_the_allowed_names_are_required(self):
        p = self.write(f"{GOOD}={TOKEN}\n")
        with self.assertRaises(TypeError):
            sr.read_login(p, GOOD)
        for bad in (None, "A_LOGIN_NAME", (), {GOOD: 1}, (GOOD, 3)):
            with self.subTest(bad=bad), self.assertRaises(sr.LoginError):
                sr.read_login(p, GOOD, allowed=bad)

    # (iii) the 4096-byte cap
    def test_a_file_over_4096_bytes_is_refused(self):
        head = f"{GOOD}="
        at_cap = self.write(head + "F" * (4096 - len(head) - 1) + "\n", "cap.line")
        self.assertEqual(os.path.getsize(at_cap), 4096)
        self.assertEqual(_login(at_cap, GOOD, (GOOD,)), "F" * (4096 - len(head) - 1))
        over = self.write(head + "F" * (4096 - len(head)) + "\n", "over.line")
        self.assertEqual(os.path.getsize(over), 4097)
        with self.assertRaises(sr.LoginError):
            _login(over, GOOD, (GOOD,))

    # (iv) a relative path is refused
    def test_a_relative_path_is_refused(self):
        p = self.write(f"{GOOD}={TOKEN}\n")
        self.assertEqual(_login(p, GOOD, (GOOD,)), TOKEN)
        with self.assertRaises(sr.LoginError):
            _login(os.path.relpath(p), GOOD, (GOOD,))

    def test_mutant_utf8_value_goes_red(self):
        p = self.write(f"{GOOD}={TOKEN}é\n")
        with mock.patch.object(sr, "_LOGIN_LINE", re.compile(rb"([A-Z_][A-Z0-9_]*)=([^\s\"]{20,})\n")), \
                mock.patch.object(sr, "_value_text", lambda b: b.decode("utf-8")):
            self.assertEqual(sr.read_login(p, GOOD, allowed=(GOOD,)), TOKEN + "é")
        red("a non-ASCII login value accepted")

    def test_mutant_any_name_goes_red(self):
        p = self.write(f"OTHER_NAME={TOKEN}\n")
        with mock.patch.object(sr, "_name_allowed", lambda name, allowed: True):
            self.assertEqual(sr.read_login(p, "OTHER_NAME", allowed=(GOOD,)), TOKEN)
        red("a login name outside the caller's allowed names accepted")

    def test_mutant_64k_cap_goes_red(self):
        head = f"{GOOD}="
        over = self.write(head + "F" * (4096 - len(head)) + "\n", "over.line")
        with mock.patch.object(sr, "LOGIN_MAX_BYTES", 1 << 16):
            self.assertEqual(sr.read_login(over, GOOD, allowed=(GOOD,)), "F" * (4096 - len(head)))
        red("a login file over 4096 bytes accepted")

    def test_mutant_relative_path_goes_red(self):
        p = self.write(f"{GOOD}={TOKEN}\n")
        rel = os.path.relpath(p)       # before the patch: 3.12's relpath reads isabs through abspath (3.13's does not)
        with mock.patch.object(sr.os.path, "isabs", lambda q: True):
            self.assertEqual(sr.read_login(rel, GOOD, allowed=(GOOD,)), TOKEN)
        red("a relative login path accepted")


# W4 merge, binding 5 review round 1 (glitch-f3's ruling under Javier's delegation; the merge-time exception to
# lane w4c, extended): B5R1-1 the repository walk reads the real path, B5R1-3 the owner is the real uid, B5R1-4 the
# 0x1c-0x1f bytes are refused. One test per point, then one in-memory mutant per point, each turning its check red.
class TestLoginBinding5Round1(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.root = self.d.name

    def plant(self, folder, body=None):
        os.makedirs(folder, exist_ok=True)
        p = os.path.join(folder, "f.line")
        with open(p, "wb") as fh:
            fh.write((body if body is not None else f"{GOOD}={TOKEN}\n").encode("utf-8"))
        os.chmod(p, 0o600)
        return p

    def repo_through_links(self):
        """A login file inside a repository, and two paths to it that never name the repository lexically."""
        repo = os.path.join(self.root, "repo")
        os.makedirs(os.path.join(repo, ".git"))
        self.plant(os.path.join(repo, "sub"))
        link = os.path.join(self.root, "lnk")
        os.symlink(os.path.join(repo, "sub"), link)
        return os.path.join(link, "f.line"), os.path.join(link, "..", "sub", "f.line")

    # B5R1-1: the real path, as run_take.outside_every_repository reads it
    def test_a_repo_file_reached_through_a_symlinked_folder_is_refused(self):
        via_link, via_dotdot = self.repo_through_links()
        for p in (via_link, via_dotdot):
            with self.subTest(p=p), self.assertRaises(sr.LoginError):
                sr.read_login(p, GOOD, allowed=(GOOD,))

    def test_a_plain_file_reached_through_a_link_inside_a_repo_is_read(self):
        out = self.plant(os.path.join(self.root, "out"))
        repo = os.path.join(self.root, "repo2")
        os.makedirs(os.path.join(repo, ".git"))
        os.symlink(os.path.dirname(out), os.path.join(repo, "l"))
        self.assertEqual(sr.read_login(os.path.join(repo, "l", "f.line"), GOOD, allowed=(GOOD,)), TOKEN)

    # B5R1-3: the real uid, as run_take.read_login reads it
    def test_the_owner_is_the_real_uid(self):
        p = self.plant(os.path.join(self.root, "o"))
        real = os.getuid()
        with mock.patch.object(sr.os, "getuid", lambda: real + 1), self.assertRaises(sr.LoginError):
            sr.read_login(p, GOOD, allowed=(GOOD,))
        with mock.patch.object(sr.os, "geteuid", lambda: real + 1):
            self.assertEqual(sr.read_login(p, GOOD, allowed=(GOOD,)), TOKEN)

    # B5R1-4: the bytes a str regex reads as whitespace
    def test_the_0x1c_to_0x1f_bytes_are_refused(self):
        for b in ("\x1c", "\x1d", "\x1e", "\x1f"):
            p = self.plant(os.path.join(self.root, f"c{ord(b)}"), f"{GOOD}={TOKEN}{b}\n")
            with self.subTest(byte=hex(ord(b))), self.assertRaises(sr.LoginError):
                sr.read_login(p, GOOD, allowed=(GOOD,))

    def test_mutant_lexical_repository_walk_goes_red(self):
        via_link, _ = self.repo_through_links()
        with mock.patch.object(sr, "_real_path", os.path.abspath):
            self.assertEqual(sr.read_login(via_link, GOOD, allowed=(GOOD,)), TOKEN)
        red("a repo login file reached through a symlinked folder accepted (lexical walk)")

    def test_mutant_effective_uid_goes_red(self):
        p = self.plant(os.path.join(self.root, "o"))
        real = os.getuid()
        with mock.patch.object(sr.os, "getuid", lambda: real + 1), \
                mock.patch.object(sr, "_owned", lambda st: st.st_uid == os.geteuid()):
            self.assertEqual(sr.read_login(p, GOOD, allowed=(GOOD,)), TOKEN)
        red("a login file accepted on the effective uid while the real uid differs")

    def test_mutant_without_0x1c_to_0x1f_goes_red(self):
        p = self.plant(os.path.join(self.root, "c"), f"{GOOD}={TOKEN}\x1f\n")
        with mock.patch.object(sr, "_LOGIN_LINE", re.compile(rb"([A-Z_][A-Z0-9_]*)=([^\s\"\x80-\xff]{20,})\n")):
            self.assertEqual(sr.read_login(p, GOOD, allowed=(GOOD,)), TOKEN + "\x1f")
        red("a login value with 0x1f accepted")


# ------------------------------------------------------------------------------------------------- PENDING values
class TestPending(unittest.TestCase):
    # RULES_SCANNER FILLED 14 Oct 2026 (glitch-06, box row 8): the reviewed box/rules_scanner.py (TestRulesScannerFilled).
    def test_the_pending_set(self):
        self.assertEqual(set(sr.pending()), {"furniture"})
        self.assertEqual(sr.FURNITURE, "PENDING")
        self.assertNotEqual(sr.RULES_SCANNER, "PENDING")

    def test_each_refuses_a_real_use(self):
        with mock.patch.object(sr, "RULES_SCANNER", sr.PENDING):
            with self.assertRaises(sr.NotReady):
                sr.real_rules_scanner()
            self.assertEqual(set(sr.pending()), {"rules_scanner", "furniture"})
        with self.assertRaises(sr.NotReady):
            sr.furniture_positions("a-harness")
        with mock.patch.object(sr, "FURNITURE", {"a-harness": [("session", "line 1")]}):
            self.assertEqual(sr.furniture_positions("a-harness"), [("session", "line 1")])
            self.assertEqual(set(sr.pending()), set())

    def test_mutants_dropping_a_refusal_go_red(self):
        with mock.patch.object(sr, "PENDING", "never-equal"), mock.patch.object(sr, "FURNITURE", "PENDING"):
            self.assertEqual(sr.pending(), {})
        red("the PENDING refusals dropped")


    def test_no_parameter_overrides_a_pending_value(self):
        names = set(sr._PENDING_WHY)       # every value that is or was PENDING (rules_scanner FILLED 14 Oct 2026)
        hits = []
        for n, obj in vars(sr).items():
            if inspect.isfunction(obj) and obj.__module__ == sr.__name__:
                hits += [f"{n}({p})" for p in inspect.signature(obj).parameters if p.lower() in names]
        # The named exemptions: interface 14 pins scan's injected rules_scanner callable; it overrides no
        # constant (RULES_SCANNER is read only by real_rules_scanner), and a scan without one refuses.
        # scan_with_witness is the same interface through the same core (gap4 box lane, 14 Oct: the witness).
        self.assertEqual(hits, ["scan(rules_scanner)", "scan_with_witness(rules_scanner)"])

    def test_scan_never_reads_the_pending_constant(self):
        c = Commit()
        self.addCleanup(c.close)
        with mock.patch.object(sr, "RULES_SCANNER", lambda paths: [{"path": paths[0], "line": 1, "rule": "x"}]):
            with self.assertRaises(sr.NotReady):
                sr.scan(c.files(), SECRETS, rules_scanner=None)


from box import rules_scanner as _rs  # noqa: E402
ORIG_GITLEAKS_SCANNER = _rs.gitleaks_scanner     # the reviewed factory, taken before any test patches the module


class TestRulesScannerFilled(unittest.TestCase):
    """Box row 8 (glitch-06, 14 Oct 2026): RULES_SCANNER names the reviewed adapter, box/rules_scanner.py, and its pin;
    real_rules_scanner refuses a drifted pin or a swapped factory, and what it returns builds the pinned scanner."""

    PIN = ("8.30.1", "88f91962aa2f93ac6ab281d553b9e125f5197bbbce38f9f2437f7299c32e5509",
           "/home/javier/gap4-tools/gitleaks-8.30.1/gitleaks")

    def check(self):
        out = []
        from box import rules_scanner as rs
        rec = sr.RULES_SCANNER
        if (rec.get("version"), rec.get("sha256"), rec.get("binary")) != self.PIN:
            out.append(f"the record's pin is {rec!r}")
        if (rs.GITLEAKS_VERSION, rs.GITLEAKS_SHA256, rs.GITLEAKS_PATH) != self.PIN:
            out.append("the adapter module's pin is not the reviewed one")
        try:
            real = _rs.real_rules_scanner()
        except sr.NotReady as e:
            return out + [f"refused: {e}"]
        if real.build is not ORIG_GITLEAKS_SCANNER:
            out.append("the real rules scanner is not box/rules_scanner.gitleaks_scanner")
        if (real.version, real.sha256, real.binary) != self.PIN:
            out.append("the real rules scanner carries another pin")
        if callable(real):
            out.append("the real rules scanner itself is callable: it could be passed as scan's rules_scanner")
        if "rules_scanner" in sr.pending():
            out.append("rules_scanner is still pending")
        if sr.real_rules_scanner() != rec or sr.real_rules_scanner() is rec:
            out.append("scan_record.real_rules_scanner does not return a copy of the record")
        return out

    def test_the_constant_is_bound_to_the_module(self):
        self.assertEqual(self.check(), [])
        from box import rules_scanner as rs
        mutants = {
            "pin sha drifts in the adapter": lambda: mock.patch.object(rs, "GITLEAKS_SHA256", "0" * 64),
            "pin sha drifts in the record": lambda: mock.patch.dict(sr.RULES_SCANNER, sha256="1" * 64),
            "version drifts": lambda: mock.patch.object(rs, "GITLEAKS_VERSION", "8.30.2"),
            "binary path drifts": lambda: mock.patch.object(rs, "GITLEAKS_PATH", "/tmp/gitleaks"),
            "scanner silently swapped": lambda: mock.patch.object(rs, "gitleaks_scanner",
                                                                  lambda runtime, report_dir, **kw: (lambda p: [])),
            "factory renamed in the record": lambda: mock.patch.dict(sr.RULES_SCANNER, factory="other"),
            "adapter renamed in the record": lambda: mock.patch.dict(sr.RULES_SCANNER, adapter="box.stub_take"),
            "drift check dropped": lambda: mock.patch.object(_rs, "real_rules_scanner", lambda: _rs.RealRulesScanner(
                lambda runtime, report_dir: (lambda p: []), "8.30.1", "0" * 64, "/tmp/gitleaks")),
        }
        for name, ctx in mutants.items():
            with self.subTest(name), ctx():
                self.assertNotEqual(self.check(), [], f"mutant {name} survived")
            red(f"rules scanner: {name}")

    # Review S-1: each of real_rules_scanner's three structural guards, bound alone (each mutant leaves the others).
    def test_the_record_key_set_is_closed(self):
        for name, ctx in {"extra key": lambda: mock.patch.dict(sr.RULES_SCANNER, note="x"),
                          "missing key": lambda: mock.patch.object(sr, "RULES_SCANNER", {
                              k: v for k, v in sr.RULES_SCANNER.items() if k != "binary"})}.items():
            with self.subTest(name), ctx():
                with self.assertRaises(sr.NotReady):
                    _rs.real_rules_scanner()

    def factory_named(self, module, name):
        def fake(runtime, report_dir, **kw):
            return lambda paths: []
        fake.__module__, fake.__name__ = module, name
        return fake

    def test_a_drifted_pin_refuses_the_binding(self):
        """The binding itself refuses each drift (the check above also reads the constants directly)."""
        for attr, value in (("GITLEAKS_SHA256", "0" * 64), ("GITLEAKS_VERSION", "8.30.2"),
                            ("GITLEAKS_PATH", "/tmp/gitleaks")):
            with self.subTest(attr), mock.patch.object(_rs, attr, value), self.assertRaises(sr.NotReady):
                _rs.real_rules_scanner()

    def test_the_factory_module_is_the_adapter(self):
        from box import rules_scanner as rs
        with mock.patch.object(rs, "gitleaks_scanner", self.factory_named("box.stub_take", "gitleaks_scanner")):
            with self.assertRaises(sr.NotReady):
                _rs.real_rules_scanner()

    def test_the_factory_name_is_its_own(self):
        from box import rules_scanner as rs
        with mock.patch.object(rs, "gitleaks_scanner", self.factory_named("box.rules_scanner", "fake_scanner")):
            with self.assertRaises(sr.NotReady):
                _rs.real_rules_scanner()

    def test_passing_the_unbuilt_scanner_names_the_build(self):
        c = Commit()
        self.addCleanup(c.close)
        with self.assertRaises(sr.NotReady) as cm:
            sr.scan(c.files(), SECRETS, rules_scanner=_rs.real_rules_scanner())
        self.assertIn("real_rules_scanner().build(runtime, report_dir)", str(cm.exception))
        self.assertNotIn("PENDING", str(cm.exception))

    def test_the_built_scanner_is_the_pinned_gate(self):
        """What real_rules_scanner returns builds through the reviewed factory, which refuses a binary off the pin."""
        d = tempfile.mkdtemp(prefix="rs-")
        self.addCleanup(lambda: __import__("shutil").rmtree(d))
        binary = os.path.join(d, "gitleaks")
        with open(binary, "wb") as fh:
            fh.write(b"not the pinned binary")
        os.mkdir(os.path.join(d, "reports"))
        from box import rules_scanner as rs
        with self.assertRaises(rs.ScannerRefused):
            _rs.real_rules_scanner().build(object(), os.path.join(d, "reports"), binary=binary)


class TestWalkLoginMask(Case):
    """Review-walk-token W-3 (glitch-06's ruling, 14 Oct 2026): the model under test can read its own sign-in token
    inside the box, so the records' exact-value mask must catch it. The scan's secrets come through the walk's own
    road, walk_builders.login_secrets over a walk login file. The value is SYNTHETIC: Claude Code's docs give no
    format for a setup-token value, so it is read_login's accepted shape (ASCII, 20+ characters, no whitespace or
    quote), with no vendor prefix; never a real token."""

    SYNTH = "SYNTHETIC0walk0login0value0" + "Ab9_-" * 12 + "AA"

    def login_file(self):
        d = tempfile.mkdtemp(prefix="wl-")
        self.addCleanup(lambda: __import__("shutil").rmtree(d))
        sub = os.path.join(d, "claude1")
        os.mkdir(sub, 0o700)
        path = os.path.join(sub, "walk-login-file")
        with open(path, "w") as fh:
            fh.write(f"CLAUDE_CODE_OAUTH_TOKEN={self.SYNTH}\n")
        os.chmod(path, 0o600)
        return path

    def test_the_walk_login_value_is_masked_in_records(self):
        import walk_builders
        secrets = walk_builders.login_secrets(self.login_file(), "claude-code")()
        self.assertEqual(secrets, [("token", self.SYNTH)])
        c = self.commit({"stream": self.SYNTH, "transcript": self.SYNTH, "session": self.SYNTH})
        r = sr.scan(c.files(), secrets, rules_scanner=no_findings)
        self.assertTrue(sr.passed(r), r.get("refused"))
        for kind in ("stream", "transcript", "session"):
            body = c.read(kind)
            self.assertNotIn(self.SYNTH.encode(), body, kind)
            self.assertIn(sr.MARKERS["token"].encode(), body, kind)
        c2 = self.commit({"ledger": self.SYNTH})
        r2 = sr.scan(c2.files(), secrets, rules_scanner=no_findings)
        self.assertFalse(sr.passed(r2))                  # outside the maskable kinds: refused, never shipped
        self.assertNotIn(self.SYNTH, json.dumps(r2))

    def test_mutant_no_secrets_goes_red(self):
        import walk_builders
        with mock.patch.object(walk_builders, "login_secrets",
                               lambda path, harness: (lambda: [("token", "OTHER-not-the-walk-value-0123456789")])):
            secrets = walk_builders.login_secrets(self.login_file(), "claude-code")()
        c = self.commit({"stream": self.SYNTH})
        r = sr.scan(c.files(), secrets, rules_scanner=no_findings)
        self.assertIn(self.SYNTH.encode(), c.read("stream"))  # without the walk value the value ships: the mask is the guard
        red("walk login value not handed to the scan")


# ------------------------------------------------------------------------------------------------- fold 2 (lane review 1)
class TestFold2(Case):
    """Lane review round 1's findings, folded on the lane lead's decisions (W4C1-3, -4c, -10, -11)."""

    # W4C1-3: an empty input never passes
    def test_an_empty_file_list_is_refused(self):
        with self.assertRaises(sr.ScanError):
            sr.scan([], SECRETS, rules_scanner=no_findings)

    def test_mutant_empty_files_pass_goes_red(self):
        with mock.patch.object(sr, "_require_files", lambda files: None):
            self.assertTrue(sr.passed(sr.scan([], SECRETS, rules_scanner=no_findings)))
        red("an empty file list passed")

    def test_secrets_without_a_token_or_key_are_refused(self):
        c = self.commit({"transcript": TOKEN})
        for secrets in ([], [("email", EMAIL)]):
            with self.subTest(secrets=[k for k, _ in secrets]):
                with self.assertRaises(sr.ScanError):
                    sr.scan(c.files(), secrets, rules_scanner=no_findings)
        for secrets in ([("token", TOKEN)], [("key", KEY)]):
            with self.subTest(secrets=[k for k, _ in secrets]):
                sr.scan(self.commit().files(), secrets, rules_scanner=no_findings)

    def test_mutant_no_secret_searched_passes_goes_red(self):
        c = self.commit({"transcript": TOKEN})
        with mock.patch.object(sr, "_require_search", lambda secrets: None):
            r = sr.scan(c.files(), [], rules_scanner=no_findings)
        self.assertTrue(sr.passed(r))
        self.assertEqual(r["events"], 0)
        red("a scan with no token or key searched passed")

    # W4C1-4 (c): a login file not owned by its reader is refused
    def login(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "login.env")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(f"{GOOD}={TOKEN}\n")
        os.chmod(p, 0o600)
        self.addCleanup(lambda: (os.unlink(p), os.rmdir(d)))
        return p

    def test_a_login_file_owned_by_another_is_refused(self):
        p = self.login()
        real = os.getuid()
        with mock.patch.object(sr.os, "getuid", lambda: real + 1):
            with self.assertRaisesRegex(sr.LoginError, "not owned by its reader"):
                sr.read_login(p, GOOD, allowed=(GOOD,))

    def test_mutant_owner_unchecked_goes_red(self):
        p = self.login()
        real = os.getuid()
        with mock.patch.object(sr.os, "getuid", lambda: real + 1), \
                mock.patch.object(sr, "_owned", lambda st: True):
            self.assertEqual(sr.read_login(p, GOOD, allowed=(GOOD,)), TOKEN)
        red("a login file owned by another accepted")

    # W4C1-10: the email's minimum length, a value surviving its mask, the rules finding's shape
    def test_the_email_minimum_length(self):
        c = self.commit()
        with self.assertRaises(sr.ScanError):
            sr.scan(c.files(), SECRETS[:2] + [("email", "a@b.c")], rules_scanner=no_findings)
        sr.scan(c.files(), SECRETS[:2] + [("email", "a@b.cd")], rules_scanner=no_findings)

    def test_mutant_email_minimum_one_goes_red(self):
        c = self.commit()
        with mock.patch.dict(sr.MIN_LENGTH, {"email": 1}):
            sr.scan(c.files(), SECRETS[:2] + [("email", "a@b.c")], rules_scanner=no_findings)
        red("MIN_LENGTH email 1")

    def test_a_value_surviving_its_mask_raises(self):
        c = self.commit({"stream": TOKEN})
        before = c.read("stream")
        with mock.patch.object(sr, "_mask", lambda line, spans: line + b" "):
            with self.assertRaisesRegex(sr.ScanError, "survived"):
                sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertEqual(c.read("stream"), before)

    def test_mutant_survival_unchecked_goes_red(self):
        c = self.commit({"stream": TOKEN})
        # The witness's rebuild check (scan_with_witness's shared core) is a second guard on the same write; it is
        # removed here too, so this mutant still shows the survival check alone (test_scan_witness has its own).
        with mock.patch.object(sr, "_mask", lambda line, spans: line + b" "), \
                mock.patch.object(sr, "_survived", lambda after, needles: False), \
                mock.patch.object(sr, "_witness", lambda path, before, after, replacements: {}):
            sr.scan(c.files(), SECRETS, rules_scanner=no_findings)
        self.assertIn(TOKEN.encode(), c.read("stream"))   # the value was written back
        red("a value surviving its mask written")

    def test_a_malformed_rules_finding_is_refused(self):
        c = self.commit()
        with self.assertRaises(sr.ScanError):
            sr.scan(c.files(), SECRETS, rules_scanner=lambda p: [{"path": p[0], "line": 1}])

    def test_mutant_finding_shape_unchecked_goes_red(self):
        c = self.commit()
        with mock.patch.object(sr, "_finding_ok", lambda f: True):
            with self.assertRaises(KeyError):
                sr.scan(c.files(), SECRETS, rules_scanner=lambda p: [{"path": p[0], "line": 1}])
        red("a malformed rules finding read")

    # W4C1-11: a non-callable rules scanner is NotReady
    def test_a_non_callable_rules_scanner(self):
        c = self.commit()
        for bad in (sr.RULES_SCANNER, "x", 3):
            with self.subTest(bad):
                with self.assertRaises(sr.NotReady):
                    sr.scan(c.files(), SECRETS, rules_scanner=bad)

    def test_mutant_only_none_refused_goes_red(self):
        c = self.commit()

        def none_only(rs):
            if rs is None:
                raise sr.NotReady("none")
        with mock.patch.object(sr, "_require_scanner", none_only):
            with self.assertRaises(TypeError):
                sr.scan(c.files(), SECRETS, rules_scanner=sr.RULES_SCANNER)
        red("a non-callable rules scanner reaching the scan")



# ------------------------------------------------------------------------- the Codex lease's tokens (glitch-06, 14 Oct)
# glitch-06's ruling on the lease postflight review's MINOR 3: every login value is in the exact-value scan, so a
# Codex take's secrets() carries the lease's access and refresh tokens, read from the registered auth.json at take
# start (and again at each scan, so a refresh in the take adds the new values and drops none); and postflight.json,
# whose listing can carry a value used as a file name, goes through the same scan as every other record before commit.
# Near-copies (base64, gzip, a split value, a trailing byte) are a named residual, not detected here.
LEASE_ACCESS = "FAKEACCESS-0123456789abcdef-PLANTED"
LEASE_REFRESH = "FAKEREFRESH-fedcba9876543210-PLANTED"
LEASE_VALUES = (LEASE_ACCESS, LEASE_REFRESH)


def _lease_body(access=LEASE_ACCESS, refresh=LEASE_REFRESH) -> dict:
    return {"OPENAI_API_KEY": None, "tokens": {"id_token": "fake-id", "access_token": access,
                                               "refresh_token": refresh, "account_id": "acct-fake"}}


def lease_auth(folder: str, body=None, mode=0o600, raw: bytes | None = None) -> str:
    p = os.path.join(folder, "auth.json")
    if os.path.lexists(p):
        os.unlink(p)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(fd, raw if raw is not None else json.dumps(_lease_body() if body is None else body).encode())
    os.close(fd)
    os.chmod(p, mode)
    return p


def _walk_builders():
    import walk_builders
    return walk_builders


class TestLeaseTokens(unittest.TestCase):
    def folder(self) -> str:
        t = tempfile.TemporaryDirectory(prefix="lease-")
        self.addCleanup(t.cleanup)
        return t.name

    def account_record(self):
        """Round 10 ruling 2 (glitch-b5, Sat 17 Oct 2026; the T4 plan's section 9): a Codex take refuses before launch
        without the account record, so the lease road runs here on a TEST DATA one (clearly fake .invalid addresses),
        walk_builders.account_emails_path patched to it for the test's life."""
        wb = _walk_builders()
        f = os.path.join(self.folder(), "account-emails.json")
        with open(f, "w", encoding="utf-8") as fh:
            json.dump({"operator": "operator@example.invalid", "codex": "codex-account@example.invalid",
                       "gemini": "gemini-account@example.invalid"}, fh)
        os.chmod(f, 0o600)
        patch = mock.patch.object(wb, "account_emails_path", lambda: f)
        patch.start()
        self.addCleanup(patch.stop)

    def refused(self, path, rule_word):
        with self.assertRaises(sr.LoginError) as cm:
            sr.read_lease_tokens(path)
        msg = str(cm.exception)
        self.assertIn(rule_word, msg)
        for v in LEASE_VALUES:
            self.assertNotIn(v, msg)

    def test_reads_the_access_and_refresh_tokens(self):
        self.assertEqual(sorted(sr.read_lease_tokens(lease_auth(self.folder()))), sorted(LEASE_VALUES))

    def test_refuses_a_lease_file_off_the_rule(self):
        d = self.folder()
        self.refused(lease_auth(d, body={"tokens": {"access_token": LEASE_ACCESS}}), "refresh_token")
        self.refused(lease_auth(d, body={"tokens": {"refresh_token": LEASE_REFRESH}}), "access_token")
        self.refused(lease_auth(d, body=_lease_body(access="short")), "at least 20")
        self.refused(lease_auth(d, body=_lease_body(refresh=LEASE_REFRESH + "\n")), "single-line")
        self.refused(lease_auth(d, raw=b"not json " + LEASE_ACCESS.encode()), "not JSON")
        self.refused(lease_auth(d, raw=b" " * (sr.LEASE_MAX_BYTES + 1)), "at most")
        self.refused(lease_auth(d, mode=0o644), "mode")
        self.refused(os.path.join(d, "missing.json"), "cannot be found")
        self.refused("auth.json", "absolute")
        real = lease_auth(d)
        link = os.path.join(d, "link.json")
        os.symlink(real, link)
        self.refused(link, "not a plain file")
        fifo = os.path.join(d, "fifo")
        os.mkfifo(fifo, 0o600)
        self.refused(fifo, "not a plain file")
        with mock.patch.object(sr, "_owned", lambda st: False):
            self.refused(real, "owned")

    def test_refuses_deep_nesting_and_a_folder_swapped_in_never_crashing(self):
        """The review of b9f876b5, MINOR 2: a JSON nesting past the recursion limit, and a folder swapped in after the
        lstat (open succeeds on a folder, the read fails), each refuse by rule, never crash."""
        d = self.folder()
        deep = b"[" * 100000 + b"]" * 100000
        self.refused(lease_auth(d, raw=deep[:sr.LEASE_MAX_BYTES]), "not JSON")
        with mock.patch.object(sr, "_lease_values", side_effect=RecursionError("planted")):   # the walk's own limit
            self.refused(lease_auth(d), "not JSON")
        real = lease_auth(d)
        folder = os.path.join(d, "swapped-in")
        os.mkdir(folder, 0o700)
        checked = os.lstat(real)                      # the check saw the regular file; a folder is what gets opened
        with mock.patch.object(sr.os, "lstat", lambda p, _st=checked: _st):
            self.refused(folder, "cannot be read")

    def test_a_codex_row_has_no_environment_login(self):
        """glitch-06's ruling 1: run_take.LOGIN_VARIABLE[codex] is NO_LOGIN ("-"); read_login refuses it by name,
        explicitly, whatever the allowed set holds, and never reads the file."""
        d = self.folder()
        p = os.path.join(d, "login")
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, b"-=" + LEASE_ACCESS.encode() + b"\n")
        os.close(fd)
        for allowed in (("-",), ("-", "CLAUDE_CODE_OAUTH_TOKEN")):
            with self.assertRaises(sr.LoginError) as cm:
                sr.read_login(p, "-", allowed=allowed)
            self.assertIn("no environment login", str(cm.exception))
            self.assertNotIn(LEASE_ACCESS, str(cm.exception))

    def test_lease_secrets_reads_at_take_start_and_keeps_every_value(self):
        self.account_record()
        d = self.folder()
        path = lease_auth(d)
        secrets = _walk_builders().lease_secrets(path)            # take start: read now
        os.unlink(path)                                           # gone before the scan: the take-start values stay
        with self.assertRaises(sr.LoginError):
            secrets()
        lease_auth(d, body=_lease_body(access="FAKEACCESS-NEW-0123456789-PLANTED",
                                       refresh="FAKEREFRESH-NEW-0123456789-PLANTED"))
        got = secrets()                                           # a refresh in the take: both pairs are searched
        # round 10 ruling 4 (the T4 plan's section 9): the token pairs, then the account record's two addresses
        self.assertTrue(all(k == "token" for k, _ in got[:-2]))
        self.assertEqual(got[-2:], [("email", "operator@example.invalid"), ("email", "codex-account@example.invalid")])
        self.assertEqual(sorted(v for _, v in got[:-2]), sorted(LEASE_VALUES + ("FAKEACCESS-NEW-0123456789-PLANTED",
                                                                                "FAKEREFRESH-NEW-0123456789-PLANTED")))
        with self.assertRaises(sr.LoginError):                    # no lease file at take start: the take never starts
            _walk_builders().lease_secrets(os.path.join(d, "nope.json"))

    def test_a_token_used_as_a_file_name_is_refused_by_the_commit_scan(self):
        import drive
        from box import preflight as pf
        from box import run_take as rt
        self.account_record()
        home, takef = self.folder(), self.folder()
        lease_auth(home)
        os.makedirs(os.path.join(home, "sessions", LEASE_ACCESS))   # the synthetic value as a name
        post = pf.postflight(home, rt.CODEX)
        self.assertTrue(post["ok"], post["checks"][0]["detail"])  # the name rule cannot see it: the scan must
        self.assertIn(f"sessions/{LEASE_ACCESS}", post["recorded"]["listing"])
        rec = os.path.join(takef, drive.POSTFLIGHT_RECORD)
        with open(rec, "w", encoding="utf-8") as fh:
            json.dump(post, fh, indent=2, sort_keys=True)
        before = Path(rec).read_bytes()
        kind = drive.record_kind([drive.POSTFLIGHT_RECORD])
        self.assertNotIn(kind, sr.MASKABLE)
        secrets = _walk_builders().lease_secrets(os.path.join(home, "auth.json"))
        result = sr.scan([(rec, kind)], secrets(), rules_scanner=no_findings)
        self.assertFalse(sr.passed(result))                       # the commit is refused
        self.assertEqual([(r["path"], r["kind"]) for r in result["refused"]], [(rec, "token")])
        self.assertNotIn(LEASE_ACCESS, json.dumps(result))
        self.assertEqual(Path(rec).read_bytes(), before)          # refused, never masked in a non-agent record


# ------------------------------------------------------------------------------------------------- OD57's exact ruling
# The ruled line is read at test time from the repository's own copy of the doc (blob 2c0ea574), never typed here.
ENV_DOC = os.path.join(os.path.dirname(STUDY), "..", "gars", "_references", "environment.md")
OD57_RULE = "generic-api-key"


def _env_line() -> str:
    with open(ENV_DOC, "rb") as fh:
        return fh.read().split(b"\n")[174].decode()


def _one_char_off(text: str) -> str:
    return text[:-2] + ("x" if text[-2] != "x" else "y") + text[-1]


class _Gitleaks:
    """A fake rules scanner: generic-api-key on every line holding the doc line's first 40 characters (so a one-
    character change at its end is still flagged, as gitleaks would), plus `extra` {marker: rule} on lines holding a
    marker. It records every path it is handed (the probe's included) and whether each existed then."""

    def __init__(self, head: str, extra=None):
        self.head, self.extra, self.calls = head.encode(), dict(extra or {}), []

    def __call__(self, paths):
        self.calls.append([(p, os.path.exists(p)) for p in paths])
        out = []
        for p in paths:
            with open(p, "rb") as fh:
                for n, line in enumerate(fh.read().split(b"\n"), 1):
                    if self.head in line:
                        out.append({"path": p, "line": n, "rule": OD57_RULE})
                    out += [{"path": p, "line": n, "rule": r} for m, r in self.extra.items() if m.encode() in line]
        return out


def _cc(*recs) -> bytes:   # Claude Code writes its JSONL with non-ASCII kept raw
    return b"".join(json.dumps(r, ensure_ascii=False).encode() + b"\n" for r in recs)


def _use(uid, name, inp, sidechain=False):
    return {"type": "assistant", "isSidechain": sidechain,
            "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}


def _result(uid, content, tool_use_result=None, sidechain=False):
    rec = {"type": "user", "isSidechain": sidechain,
           "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": content}]}}
    if tool_use_result is not None:
        rec["toolUseResult"] = tool_use_result
    return rec


class TestOD57Ruling(Case):
    """OD57 (Javier's ruling "scan-envmd-1 safe", 16 Oct 2026): generic-api-key on line 175 of
    gars/_references/environment.md, inside a Read or a Bash cat/grep result, is admitted by its exact text; nothing
    else is."""

    def setUp(self):
        self.text = _env_line()
        self.doc = "/run/gars/_references/environment.md"
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, body: bytes):
        p = os.path.join(self.tmp.name, name)
        with open(p, "wb") as fh:
            fh.write(body)
        return p

    def read_record(self, text=None, sidechain=False):
        t = self.text if text is None else text
        return _cc({"type": "system", "subtype": "init"},
                   _use("toolu_R", "Read", {"file_path": self.doc}, sidechain),
                   _result("toolu_R", f"174\tline before\n175\t{t}\n176\tline after\n",
                           {"type": "text", "file": {"filePath": self.doc, "content": f"line before\n{t}\nline after"}},
                           sidechain))

    def bash_record(self, command, output, sidechain=False):
        return _cc(_use("toolu_B", "Bash", {"command": command}, sidechain),
                   _result("toolu_B", output, {"stdout": output, "stderr": "", "interrupted": False}, sidechain))

    def scan(self, files, scanner=None):
        scanner = scanner or _Gitleaks(self.text[:40])
        return sr.scan(files, SECRETS, rules_scanner=scanner), scanner

    def test_the_pin_is_the_docs_line_175(self):
        b = self.text.encode()
        (ruling,) = sr.RULED_LINES
        self.assertEqual((ruling["ruling"], ruling["rule"]), ("OD57", OD57_RULE))
        self.assertEqual((len(b), hashlib.sha256(b).hexdigest()), (ruling["bytes"], ruling["sha256"]))
        self.assertTrue(self.text.startswith("Key pinned versions:"))

    def test_witness_the_exact_line_is_admitted_from_a_read_result(self):
        p = self.write("transcript.jsonl", self.read_record())
        before = Path(p).read_bytes()
        r, g = self.scan([(p, "transcript")])
        self.assertEqual(r["refused"], [])
        self.assertEqual(r["ruled"], [{"path": p, "line": 3, "rule": OD57_RULE, "ruling": "OD57"}])
        self.assertTrue(sr.passed(r))
        self.assertEqual(Path(p).read_bytes(), before)                 # admitted, never edited
        self.assertEqual(len(g.calls), 2)                              # the scan, then the probe
        (probe, existed), = g.calls[1]
        self.assertTrue(existed)
        self.assertNotEqual(os.path.dirname(probe), self.tmp.name)    # never in the record folder
        self.assertFalse(os.path.lexists(probe) or os.path.lexists(os.path.dirname(probe)))

    def test_witness_the_exact_line_is_admitted_from_bash_results_main_and_sub_agent(self):
        for cmd, out, kind, side in (
                (f"grep -n 'pinned' {self.doc}", f"175:{self.text}\n", "session", True),
                (f"grep 'pinned' {self.doc}", f"{self.text}\n", "transcript", False),
                (f"grep -rn pinned {self.doc}", f"/run/gars/_references/environment.md:175:{self.text}\n",
                 "stream", False),
                (f"cat -n {self.doc}", f"   174\tline before\n   175\t{self.text}\n", "session", True),
                (f"cat {self.doc}", f"line before\n{self.text}\nline after\n", "transcript", False)):
            with self.subTest(cmd=cmd.split()[0:2], kind=kind):
                p = self.write(f"{kind}-{len(cmd)}.jsonl", self.bash_record(cmd, out, side))
                r, _ = self.scan([(p, kind)])
                self.assertEqual(r["refused"], [])
                self.assertEqual(r["ruled"], [{"path": p, "line": 2, "rule": OD57_RULE, "ruling": "OD57"}])

    def test_witness_a_one_character_change_refuses(self):
        for rec in (self.read_record(_one_char_off(self.text)),
                    self.bash_record(f"cat {self.doc}", _one_char_off(self.text) + "\n")):
            with self.subTest(rec=rec[:30]):
                p = self.write("transcript.jsonl", rec)
                r, _ = self.scan([(p, "transcript")])
                self.assertEqual(r["ruled"], [])
                self.assertEqual([(x["line"], x["why"]) for x in r["refused"]],
                                 [(rec.count(b"\n", 0, rec.find(_one_char_off(self.text)[:40].encode())) + 1,
                                   f"the rules scanner's rule {OD57_RULE!r}")])
                self.assertFalse(sr.passed(r))

    def test_witness_another_rule_on_the_same_line_refuses(self):
        p = self.write("transcript.jsonl", self.read_record())
        r, _ = self.scan([(p, "transcript")], _Gitleaks(self.text[:40], {self.text[:20]: "curl-auth-header"}))
        self.assertEqual(r["ruled"], [{"path": p, "line": 3, "rule": OD57_RULE, "ruling": "OD57"}])
        self.assertEqual([(x["line"], x["why"]) for x in r["refused"]],
                         [(3, "the rules scanner's rule 'curl-auth-header'")])
        self.assertFalse(sr.passed(r))

    def test_the_line_outside_a_ruled_tool_result_refuses(self):
        cases = {
            "an agent's own text": _cc({"type": "assistant", "message": {"content": [
                {"type": "text", "text": f"the doc says:\n{self.text}\n"}]}}),
            "a tool result plus the agent's text on one record": _cc(
                _use("toolu_R", "Read", {"file_path": self.doc}),
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "toolu_R", "content": f"175\t{self.text}"},
                    {"type": "text", "text": self.text}]}}),
            "a Bash that is not cat or grep": self.bash_record(f"sed -n 175p {self.doc}", self.text + "\n"),
            "a Bash that only starts with grep's letters": self.bash_record(f"grepx {self.doc}", self.text + "\n"),
            "a result whose tool_use is missing": _cc(_result("toolu_X", f"175\t{self.text}")),
            "an Agent's result": _cc(_use("toolu_A", "Agent", {"prompt": "read it"}),
                                     _result("toolu_A", f"{self.text}\n")),
            "the line with more on it": self.bash_record(f"cat {self.doc}", f"{self.text} and more\n"),
        }
        for name, body in cases.items():
            with self.subTest(name):
                p = self.write("transcript.jsonl", body)
                r, _ = self.scan([(p, "transcript")])
                self.assertEqual(r["ruled"], [])
                self.assertEqual([x["why"] for x in r["refused"]], [f"the rules scanner's rule {OD57_RULE!r}"])

    def test_a_match_the_line_does_not_explain_refuses(self):
        p = self.write("transcript.jsonl", self.bash_record(f"cat {self.doc}", f"{self.text}\napi_key_SECOND\n"))
        r, g = self.scan([(p, "transcript")], _Gitleaks(self.text[:40], {"api_key_SECOND": OD57_RULE}))
        self.assertEqual(r["ruled"], [])
        self.assertEqual([x["line"] for x in r["refused"]], [2, 2])
        self.assertEqual(len(g.calls), 2)                              # the probe ran and still saw the rule

    def test_a_non_agent_kind_refuses(self):
        for kind in ("ledger", "evidence", "launch"):
            with self.subTest(kind=kind):
                p = self.write(f"{kind}.jsonl", self.read_record())
                r, g = self.scan([(p, kind)])
                self.assertEqual(r["ruled"], [])
                self.assertEqual(len(r["refused"]), 1)
                self.assertEqual(len(g.calls), 1)                      # no probe

    def test_mutant_without_the_ruling_goes_red(self):
        p = self.write("transcript.jsonl", self.read_record())
        with mock.patch.object(sr, "RULED_LINES", ()):
            r, _ = self.scan([(p, "transcript")])
        self.assertEqual((r["ruled"], len(r["refused"])), ([], 1))
        red("OD57's ruling removed (the exact line refused)")

    def test_mutant_any_tool_goes_red(self):
        p = self.write("transcript.jsonl", self.bash_record(f"sed -n 175p {self.doc}", self.text + "\n"))
        with mock.patch.object(sr, "_ruled_tool", lambda uses, uid: True):
            r, _ = self.scan([(p, "transcript")])
        self.assertEqual(len(r["ruled"]), 1)
        red("the tool binding dropped (a sed result admitted)")

    def test_mutant_without_the_probe_goes_red(self):
        p = self.write("transcript.jsonl", self.bash_record(f"cat {self.doc}", f"{self.text}\napi_key_SECOND\n"))
        g = _Gitleaks(self.text[:40], {"api_key_SECOND": OD57_RULE})
        first = []

        def once(paths):
            if first:
                return []                     # the mutant: the probe sees nothing
            first.append(1)
            return g(paths)
        r, _ = self.scan([(p, "transcript")], once)
        self.assertEqual(len(r["ruled"]), 2)
        red("the probe dropped (a second match on the line admitted)")



# ------------------------------------------------------------------------------------------------- OD57, after w167
# glitch-b5's ruling (16 Oct 2026, applying OD57 to the same bytes): walk w167's sub-agent read the line through
# `cd <run>/gars && grep -n -i "..." _references/environment.md <two more files> 2>/dev/null | head -30`. A Bash
# command is admitted when, split on &&, ||, ; and | and shell-tokenised, its first segment after any leading cd is a
# grep or cat naming a path that ends in _references/environment.md. Plus the aegis review of 4043a29's findings 2
# and 3 on this twin: a probe finding of the rule without an int line refuses, and each conjunct of the "nowhere else
# on the record" guard has its own witness.
W167 = ('cd /tmp/run-c8021046/gars && grep -n -i "deseq\\|sklearn\\|scikit\\|pydeseq" _references/environment.md '
        '_references/gars-bio.conda.txt _references/gars-bio.lock.txt 2>/dev/null | head -30')
NOT_ESCAPED = "json.dumps(found)[1:-1] != found"
DECODED_ELSEWHERE = "sum(x.count(found) for x in _strings(rec, [])) != hits"
RAW_ELSEWHERE = "body.count(found.encode()) != hits"


def _mutant(fn_name, *edits):
    """sr.<fn_name> rebuilt from its source with each (old, new) edit applied once, as a mock patch."""
    src = textwrap.dedent(inspect.getsource(getattr(sr, fn_name)))
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"mutant edit {old!r} matches {src.count(old)} times in {fn_name}")
        src = src.replace(old, new)
    ns = dict(vars(sr))
    exec(compile(src, f"{fn_name}_mutant", "exec"), ns)
    return mock.patch.object(sr, fn_name, ns[fn_name])


class TestOD57Chain(TestOD57Ruling):
    """Inherits TestOD57Ruling's fixtures; its own tests below (the parent's run once, in the parent)."""

    def grep_out(self, text=None):
        return f"_references/environment.md:175:{self.text if text is None else text}\n"

    def admitted(self, body, kind="transcript", scanner=None):
        p = self.write(f"{kind}.jsonl", body)
        r, _ = self.scan([(p, kind)], scanner)
        return r["ruled"] != [] and r["refused"] == []

    def test_witness_w167s_command_is_admitted_in_its_transcript_and_its_stream(self):
        for kind, side in (("transcript", False), ("stream", True)):
            with self.subTest(kind=kind):
                self.assertTrue(self.admitted(self.bash_record(W167, self.grep_out(), side), kind))

    def test_the_bash_shapes(self):
        doc = "_references/environment.md"
        admitted = [W167, "grep -n pinned " + doc, "cat " + doc, "cat -n /run/gars/" + doc,
                    "cd /run/gars && grep -n Key " + doc + " | sort | uniq | wc -l",
                    "grep -n Key " + doc + " 2>&1 | head", "grep -n Key " + doc + " | tail -3",
                    "grep 'Key pinned' " + doc, 'grep -n "a\\|b" ' + doc]
        refused = ["cd x && sed -n 175p " + doc, "grep -n pinned _references/other.md", "echo $(cat " + doc + ")",
                   'cat "$(cat x)/' + doc + '"', 'cat "`cat x`/' + doc + '"', "eval cat " + doc,
                   "sh -c 'cat " + doc + "'", "bash -c 'grep -n Key " + doc + "'", "cat " + doc + " | sh -c 'cat y'",
                   'grep "unclosed ' + doc, "echo hi && grep -n Key " + doc, "cat <(" + doc + ")",
                   "grep -n Key " + doc + " &", "(cat " + doc + ")", "cd && grep -n Key " + doc,
                   "grep -rn Key /run/gars/_references", "cat " + doc + "x", "cat " + doc + ".bak", "cat my" + doc,
                   "", "&& cat " + doc, "xargs cat " + doc, None, 3,
                   # the allow-list (review of 41de680): one leading cd only, and no first word off the list
                   "cd /run/gars && cd gars && grep -n Key " + doc, "grep -n Key " + doc + "; echo done",
                   "grep 'Key pinned' " + doc + " || true", "head -200 " + doc, "sed -n 175p " + doc,
                   # the review's repros: a newline or carriage return separator, a prefix command carrying a shell
                   "grep k " + doc + "\nsh -c 'cat /tmp/other'", "grep k " + doc + "\r\nsh -c 'cat /tmp/other'",
                   "grep k " + doc + "\nxargs cat /tmp/other", "grep k " + doc + "; time sh -c x",
                   "grep k " + doc + "; nice sh -c x", "grep k " + doc + " | stdbuf -o0 cat",
                   "nice grep k " + doc, "time grep k " + doc, "grep k " + doc + " | xargs cat",
                   "grep k " + doc + " | find . -exec cat {} +", "grep k " + doc + " | busybox cat",
                   "grep k " + doc + " | head; sh", "grep k " + doc + " sh", "grep k " + doc + " | cat - eval",
                   # the exact token: no path prefix, no backslash; a sort takes no long option
                   "/bin/grep k " + doc, "/usr/bin/cat " + doc, "\\grep k " + doc, "gr\\ep k " + doc,
                   "grep k " + doc + " | sort --compress-program=x", "grep k " + doc + " | sort --com=x",
                   # the review of b2738e2: shlex starts a comment at a mid-word #, bash does not; # refuses anywhere
                   "grep -n Key " + doc + " x#; sh -c 'cat /tmp/other'", "cat " + doc + "#;python3 -c 'print(1)'",
                   'grep -n "#Key" ' + doc, "grep -n Key " + doc + " # a comment"]
        for cmd in admitted:
            with self.subTest(admitted=cmd):
                self.assertTrue(sr._ruled_bash(cmd))
        for cmd in refused:
            with self.subTest(refused=cmd):
                self.assertFalse(sr._ruled_bash(cmd))

    def test_the_named_refusals_refuse_end_to_end(self):
        cases = {
            "cd x && sed": self.bash_record("cd x && sed -n 175p _references/environment.md", self.text + "\n"),
            "grep another file": self.bash_record("grep -n pinned _references/other.md", f"175:{self.text}\n"),
            "echo $(cat ...)": self.bash_record("echo $(cat _references/environment.md)", self.text + "\n"),
            "newline then sh -c": self.bash_record("grep k _references/environment.md\nsh -c 'cat /tmp/other'",
                                                   f"175:{self.text}\n"),
            "time sh -c": self.bash_record("grep -n k _references/environment.md; time sh -c x", f"175:{self.text}\n"),
            "a mid-word # then sh -c": self.bash_record("grep -n Key _references/environment.md x#; sh -c 'cat /tmp/other'", f"175:{self.text}\n"),
            "a # glued to the doc": self.bash_record("cat _references/environment.md#;python3 -c 'print(1)'", self.text + "\n"),
            "a user-text copy": _cc({"type": "user", "message": {"content": f"please check:\n{self.text}\n"}}),
        }
        for name, body in cases.items():
            with self.subTest(name):
                self.assertFalse(self.admitted(body))

    def test_mutation_witnesses_of_the_bash_shapes(self):
        LINE = self.text
        cases = (
            ("the doc path dropped", "grep -n pinned _references/other.md", "175:%s\n" % LINE,
             ('return any(t == _RULED_DOC or t.endswith("/" + _RULED_DOC) for t in segments[i][1:])',
              "return True")),
            ("the grep-or-cat first word dropped", "cd x && head -200 _references/environment.md", LINE + "\n",
             ('segments[i][0] not in ("grep", "cat")', "False")),
            ("the substitution guard dropped", 'cat "$(cat x)/_references/environment.md"', LINE + "\n",
             ('"$(", "`", ', "")),
            ("the allow-list dropped", "grep -n Key _references/environment.md; xargs cat /tmp/other",
             "175:%s\n" % LINE, ("seg[0] not in _RULED_FIRST_WORDS", "False")),
            ("the newline refusal dropped", "grep -n Key _references/environment.md\nxargs cat /tmp/other",
             "175:%s\n" % LINE, (r'"\n", "\r", ', "")),
            ("the backslash refusal dropped", "\\grep -n Key _references/environment.md", "175:%s\n" % LINE,
             ("if _ruled_unquoted_backslash(cmd):", "if False:")),
        )
        for name, cmd, out, edit in cases:
            with self.subTest(name):
                self.assertFalse(self.admitted(self.bash_record(cmd, out)))
                with _mutant("_ruled_bash", edit):
                    self.assertTrue(self.admitted(self.bash_record(cmd, out)), f"{name}: the mutant still refuses")
                red(f"OD57 w167: {name}")

    def test_mutation_witnesses_of_the_hash_fixes(self):
        """The review of b2738e2: the # refusal and the empty commenters, each with its own witness."""
        # the # refusal: a # anywhere refuses, so a pattern holding one refuses; dropped, it admits
        benign = 'grep -n "#Key" _references/environment.md'
        self.assertFalse(sr._ruled_bash(benign))
        with _mutant("_ruled_bash", ('"#", ', '')):
            self.assertTrue(sr._ruled_bash(benign), "the # refusal dropped: still refused")
        red("OD57 #: the # refusal dropped")
        # the empty commenters: with the # refusal dropped, they alone still refuse the review's repros; with both
        # dropped, shlex's comment hides the shell and the repros admit
        for repro in ("grep -n Key _references/environment.md x#; sh -c 'cat /tmp/other'", "cat _references/environment.md#;python3 -c 'print(1)'"):
            with self.subTest(repro=repro):
                self.assertFalse(sr._ruled_bash(repro))
                with _mutant("_ruled_bash", ('"#", ', '')):
                    self.assertFalse(sr._ruled_bash(repro), "the empty commenters do not refuse it alone")
                with _mutant("_ruled_bash", ('"#", ', ''), ('lex.commenters = ""', 'pass')):
                    self.assertTrue(sr._ruled_bash(repro), "both dropped: still refused")
                red("OD57 #: the empty commenters dropped too")

    def test_a_probe_finding_of_the_rule_without_an_int_line_refuses(self):
        body = self.bash_record(W167, self.grep_out())
        for line, rule, admit in ((None, OD57_RULE, False), ("2", OD57_RULE, False), (True, OD57_RULE, False),
                                  (None, "curl-auth-header", True)):
            with self.subTest(line=line, rule=rule):
                g = _Gitleaks(self.text[:40])
                calls = []

                def scanner(paths):
                    calls.append(1)
                    if len(calls) == 1:
                        return g(paths)
                    return [{"path": paths[0], "line": line, "rule": rule}]
                self.assertEqual(self.admitted(body, scanner=scanner), admit)
        g = _Gitleaks(self.text[:40])
        calls = []

        def malformed(paths):
            calls.append(1)
            return g(paths) if len(calls) == 1 else [{"path": paths[0], "line": None, "rule": OD57_RULE}]
        with _mutant("_ruled_findings", ('type(g["line"]) is not int or ', "")):
            self.assertTrue(self.admitted(body, scanner=malformed))
        red("OD57 probe: a line that is not an int read as no finding")

    def same_record(self, extra):
        """A Read and its result, where the result's user record also carries `extra` (raw JSON members)."""
        rec = json.dumps(_result("toolu_R", f"174\tline before\n175\t{self.text}\n176\tline after\n"),
                         ensure_ascii=False)
        return _cc(_use("toolu_R", "Read", {"file_path": self.doc})) + (rec[:-1] + ", " + extra + "}\n").encode()

    def check_conjunct(self, body, conjunct, rulings=None):
        """Refuses as is; admits with only `conjunct` replaced by False."""
        with mock.patch.object(sr, "RULED_LINES", rulings or sr.RULED_LINES):
            self.assertFalse(self.admitted(body))
            with _mutant("_ruled_text", (conjunct, "False")):
                self.assertTrue(self.admitted(body), f"the mutant still refuses: no witness of {conjunct!r}")
        red(f"OD57 nowhere-else: {conjunct}")

    def test_the_same_record_case_refuses_and_the_whole_guard_is_what_refuses_it(self):
        rec = _result("toolu_R", [{"type": "text", "text": f"175\t{self.text}\n"}])
        rec["message"]["content"].append({"type": "text", "text": f"please check this:\n{self.text}\n"})
        body = _cc(_use("toolu_R", "Read", {"file_path": self.doc}), rec)
        self.assertFalse(self.admitted(body))
        with _mutant("_ruled_text", (NOT_ESCAPED, "False"), (DECODED_ELSEWHERE, "False"), (RAW_ELSEWHERE, "False")):
            self.assertTrue(self.admitted(body))
        red("OD57 nowhere-else: the whole guard")

    def test_witness_an_escaped_copy_is_caught_decoded(self):
        hidden = json.dumps({"type": "text", "text": self.text}).replace("`", "\\u0060")
        self.check_conjunct(self.same_record('"note": ' + hidden), DECODED_ELSEWHERE)

    def test_witness_a_copy_the_parser_drops_is_caught_raw(self):
        self.check_conjunct(self.same_record('"note": %s, "note": "x"' % json.dumps(self.text)), RAW_ELSEWHERE)

    def test_witness_a_ruled_text_json_escapes_is_refused(self):
        line = self.text + " é"
        ruling = dict(sr.RULED_LINES[0], bytes=len(line.encode()), sha256=hashlib.sha256(line.encode()).hexdigest())
        self.check_conjunct(self.read_record(line), NOT_ESCAPED, (ruling,))


for _name in [n for n in vars(TestOD57Ruling) if n.startswith("test_")]:
    setattr(TestOD57Chain, _name, None)      # the parent's tests run once, in the parent

if __name__ == "__main__":
    unittest.main(verbosity=2)
